//! Instance-side LLM assessment: buyer qualification + duration estimation.
//!
//! Platform discipline (verified): model inference is NON-deterministic, so it
//! may only run in instance functions (`http_request` egress is instance-only);
//! the result is then committed to network state via a separate network call
//! (the documented two-step pattern). Nothing here ever touches consensus
//! replay. `shopping-assistant` is the official precedent for the lyquid-llm
//! call shape (lyquid-examples/shopping-assistant/src/lib.rs:113-131);
//! refinement loops exist in lyquid-flow if needed later.
//!
//! B1 reproducibility: prompts request JsonSchema output; the agent-side
//! ScriptedMock (agents/common/llm.py) can replay identical responses for
//! tests; real backends only for the recorded demo.
//!
//! W1-B2 S3 wiring (was SPIKE(W1) items at :14/:63/:90 — all resolved and
//! rewritten as conclusions below; ledger in workflow-out/implementation.md):
//!   - import/API face pinned against ldk v0.8.1 (rev fd575e8, read this
//!     round): `lyquid_llm::call_model` (lyquid-llm/src/lib.rs:459,
//!     feature "ldk" — the shopping-assistant Cargo.toml:11 form), backend
//!     construction per plan R1#4: custom endpoint =
//!     `OpenAiCompatBackend::chat_completions(provider, base_url)
//!     .bearer_auth(api_key)` (backend/openai_compat.rs:114-132); default
//!     OpenAI endpoint only = `openai(api_key)` (:94-98, hardcoded
//!     api.openai.com/v1/responses); `.output_format(OutputFormat::json_schema(..))`
//!     (:146-155); `ModelRequest::new(model, prompt).system(..).timeout_ms(..)
//!     .max_output_tokens(..)` (lib.rs:390-431); `OutputFormat::JsonSchema
//!     {name, schema}` (lib.rs:40-47).
//!   - HeuristicModel is now the shipped "TB_LLM replay mode" component (not
//!     a placeholder): with empty api_key/base_url params the chain runs it
//!     so demos/tests behave identically to the recorded scripts.
//!   - serde_json is the explicit json-crate choice (already the locked
//!     transitive dep of the git-pinned ldk crates; declaration comment in
//!     lyquid/Cargo.toml — no crates.io addition).

use crate::types::AssessmentReport;
use serde::Deserialize;
use lyquid_llm::backend::openai_compat::OpenAiCompatBackend;
use lyquid_llm::{call_model, ModelRequest, OutputFormat};

pub struct DealBrief {
    pub buyer_profile_digest: String,
    pub seller_profile_digest: String,
    pub terms_digest: String,
    pub license_scope: String,
}

const QUALIFICATION_SYSTEM: &str = r#"
You are the risk assessor of an agent-to-agent licensing marketplace.
Score the BUYER agent's qualification for this license purchase and estimate
fulfillment duration. Respond ONLY with JSON:
{"qualification_score": 0-100,
 "risks": ["..."],
 "est_duration_ms": <p90 milliseconds for the seller to deliver the license grant>,
 "est_confidence": 0-100}
Be conservative on duration: the number drives an enforceable on-chain timeout;
overestimation delays refunds, underestimation causes spurious refunds.
"#;

/// Pure prompt builder (unit-testable without any backend).
pub fn build_request(brief: &DealBrief) -> String {
    format!(
        "{}\n\nbuyer_profile_sha256={}\nseller_profile_sha256={}\nterms_sha256={}\nlicense_scope={}",
        QUALIFICATION_SYSTEM.trim(),
        brief.buyer_profile_digest,
        brief.seller_profile_digest,
        brief.terms_digest,
        brief.license_scope,
    )
}

/// Backend seam: production = lyquid-llm `call_model` (LyquidLlmModel below);
/// replay/tests = HeuristicModel; unit tests = any local mock.
pub trait AssessmentModel {
    fn complete_json(&self, prompt: &str) -> Result<String, String>;
}

/// TB_LLM 回放模式（W1-B2 转正，非占位）：确定性固定输出，与
/// agents/common/llm.py DEFAULT_ASSESSMENT_SCRIPT 保持 lockstep（同 75 /
/// heuristic-mode / 60000ms / 40 四元组）。assess_brief 在 api_key/base_url
/// 参数任一为空时走本模型（R1#4 模式契约），离线演示与回归测试由此不依赖
/// 外网——真实后端走 LyquidLlmModel。
pub struct HeuristicModel;

impl AssessmentModel for HeuristicModel {
    fn complete_json(&self, prompt: &str) -> Result<String, String> {
        let _ = prompt;
        // Conservative fixed estimate: 60s p90 x safety handled by
        // timeout_slots_from_estimate.
        Ok(r#"{"qualification_score":75,"risks":["heuristic-mode"],"est_duration_ms":60000,"est_confidence":40}"#.to_string())
    }
}

/// JsonSchema constraint sent to the provider — mirrors the four-field
/// RawAssessment contract below exactly (the parse is the local backstop;
/// schema-constrained output minimizes the parse-failure surface).
fn assessment_schema() -> serde_json::Value {
    serde_json::json!({
        "type": "object",
        "properties": {
            "qualification_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "risks": {"type": "array", "items": {"type": "string"}},
            "est_duration_ms": {"type": "integer", "minimum": 0},
            "est_confidence": {"type": "integer", "minimum": 0, "maximum": 100}
        },
        "required": ["qualification_score", "risks", "est_duration_ms", "est_confidence"],
        "additionalProperties": false
    })
}

/// Real backend (W1-B2 S3): OpenAI-compatible chat-completions endpoint via
/// lyquid-llm. Constructed per plan R1#4 — a non-empty `base_url` selects
/// `chat_completions(provider, base_url).bearer_auth(api_key)`; an EMPTY
/// base_url (with non-empty key) means the stock OpenAI endpoint, whose only
/// legal constructor is `openai(api_key)` (hardcoded
/// https://api.openai.com/v1/responses, openai_compat.rs:94-98).
pub struct LyquidLlmModel {
    backend: OpenAiCompatBackend,
    model: String,
}

impl LyquidLlmModel {
    pub fn new(base_url: &str, api_key: &str, model: &str) -> Result<Self, String> {
        let backend = if base_url.is_empty() {
            OpenAiCompatBackend::openai(api_key).map_err(|e| format!("llm backend: {e}"))?
        } else {
            OpenAiCompatBackend::chat_completions("openai-compat", base_url)
                .bearer_auth(api_key)
        }
        .output_format(OutputFormat::json_schema("trustbridge_assessment", assessment_schema()));
        Ok(Self { backend, model: model.to_string() })
    }
}

impl AssessmentModel for LyquidLlmModel {
    fn complete_json(&self, prompt: &str) -> Result<String, String> {
        let req = ModelRequest::new(&self.model, prompt)
            .timeout_ms(30_000)
            .max_output_tokens(1_024);
        let resp = call_model(&self.backend, &req).map_err(|e| format!("llm call: {e}"))?;
        resp.text.ok_or_else(|| "llm call: empty response text".to_string())
    }
}

/// Wire contract mirror of the prompt schema (QUALIFICATION_SYSTEM above):
/// exactly four fields. Missing field = error（与旧解析器 ok_or_else 同严），
/// unknown fields ignored（与旧 split-scan 同宽，收严属阶段四评估）。
/// risks 原样透传，不再伪造——与 agents/common/llm.py:73-82 的
/// DEFAULT_ASSESSMENT_SCRIPT 保持 lockstep（四字段逐一对应）。
#[derive(Deserialize)]
struct RawAssessment {
    qualification_score: u8,
    risks: Vec<String>,
    est_duration_ms: u64,
    est_confidence: u8,
}

/// Serialization single point (R2#1): the ONLY place the report's JSON wire
/// shape is produced. types.rs is frozen and `AssessmentReport` has no
/// Serialize derive (types.rs:186-192), so this local view borrows the four
/// fields; lib.rs's `assess_brief` returns exactly this string over the
/// export=eth face, keeping the wire shape defined in one file.
pub(crate) fn report_json(r: &AssessmentReport) -> Result<String, String> {
    #[derive(serde::Serialize)]
    struct ReportView<'a> {
        qualification_score: u8,
        risks: &'a [String],
        est_duration_ms: u64,
        est_confidence: u8,
    }
    serde_json::to_string(&ReportView {
        qualification_score: r.qualification_score,
        risks: &r.risks,
        est_duration_ms: r.est_duration_ms,
        est_confidence: r.est_confidence,
    })
    .map_err(|e| format!("assessment serialize: {e}"))
}

pub fn parse_report(raw: &str) -> Result<AssessmentReport, String> {
    // serde_json contract parse replaces the hand split-scan (its E0277×4 and
    // delimiter fragility) — serde_json is the explicit contract choice, same
    // dep as the lib.rs getters (declaration comment in lyquid/Cargo.toml).
    // TODO(W2): real JsonSchema-validated parse — serde 字段集校验 ≠ schema
    // 校验（区间/语义约束仍缺）。
    let r: RawAssessment = serde_json::from_str(raw)
        .map_err(|e| format!("assessment contract parse failed: {e}"))?;
    Ok(AssessmentReport {
        qualification_score: r.qualification_score,
        risks: r.risks,
        est_duration_ms: r.est_duration_ms,
        est_confidence: r.est_confidence,
    })
}

/// Instance entry point: assess a brief and return the report. The CALLER
/// (agent-broker) then submits `create_deal` — the two-step commit.
/// 接线说明（阶段二）：调用方（agent-broker）提交 `create_deal` 时受 lib.rs
/// `require(Access::Broker)` 守卫——两步提交的第二步在平台层有权限门。
pub fn assess<M: AssessmentModel>(model: &M, brief: &DealBrief) -> Result<AssessmentReport, String> {
    let raw = model.complete_json(&build_request(brief))?;
    parse_report(&raw)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn heuristic_model_parses() {
        let r = assess(&HeuristicModel, &DealBrief {
            buyer_profile_digest: "b".into(),
            seller_profile_digest: "s".into(),
            terms_digest: "t".into(),
            license_scope: "online-video,12mo,EU".into(),
        })
        .unwrap();
        assert_eq!(r.qualification_score, 75);
        assert_eq!(r.est_duration_ms, 60_000);
        assert!(r.est_confidence <= 100);
    }

    #[test]
    fn prompt_carries_conservatism_instruction() {
        let p = build_request(&DealBrief {
            buyer_profile_digest: "b".into(),
            seller_profile_digest: "s".into(),
            terms_digest: "t".into(),
            license_scope: "x".into(),
        });
        assert!(p.contains("enforceable on-chain timeout"));
        assert!(p.contains("terms_sha256="));
    }

    #[test]
    fn parse_report_rejects_malformed_json() {
        assert!(parse_report("not json").is_err());
        assert!(parse_report("").is_err());
        assert!(parse_report("{\"qualification_score\":75,}").is_err());
    }

    #[test]
    fn parse_report_rejects_missing_field() {
        // est_confidence dropped from the four-field contract -> Err,
        // same strictness as the old parser's ok_or_else.
        let raw = r#"{"qualification_score":75,"risks":["x"],"est_duration_ms":60000}"#;
        assert!(parse_report(raw).is_err());
    }

    #[test]
    fn parse_report_passes_risks_through() {
        // risks 透传（不再伪造 "parsed-in-heuristic-mode"）——钉死与
        // agents/common/llm.py DEFAULT_ASSESSMENT_SCRIPT 的 lockstep。
        let raw = r#"{"qualification_score":80,"risks":["heuristic-mode","regulatory"],"est_duration_ms":1000,"est_confidence":50}"#;
        let r = parse_report(raw).unwrap();
        assert_eq!(r.risks, vec!["heuristic-mode".to_string(), "regulatory".to_string()]);
        assert_eq!(r.qualification_score, 80);
        assert_eq!(r.est_duration_ms, 1000);
        assert_eq!(r.est_confidence, 50);
    }

    #[test]
    fn report_json_roundtrip_is_the_wire_shape() {
        // R2#1 pin: report_json emits exactly the four-field contract string.
        let r = parse_report(r#"{"qualification_score":80,"risks":["a","b"],"est_duration_ms":1000,"est_confidence":50}"#).unwrap();
        let j = report_json(&r).unwrap();
        assert_eq!(j, r#"{"qualification_score":80,"risks":["a","b"],"est_duration_ms":1000,"est_confidence":50}"#);
    }
}
