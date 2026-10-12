//! Instance-side LLM assessment: buyer qualification + duration estimation.
//!
//! Platform discipline (verified): model inference is NON-deterministic, so it
//! may only run in instance functions (`http_request` egress is instance-only);
//! the result is then committed to network state via a separate network call
//! (the documented two-step pattern). Nothing here ever touches consensus
//! replay. `shopping-assistant` is the official precedent for the lyquid-llm
//! call shape; refinement loops exist in lyquid-flow if needed later.
//!
//! B1 reproducibility: prompts request JsonSchema output; the agent-side
//! ScriptedMock (agents/common/llm.py) can replay identical responses for
//! tests; real backends only for the recorded demo.

// Verified API surface (docs/source, v0.7.3) — exact import paths SPIKE(W1):
//   lyquid_llm::call_model::<B>(&backend, &ModelRequest) -> LlmResult<ModelResponse>
//   lyquid_llm::backend::openai_compat::OpenAiCompatBackend::openai(...)
//   lyquid_llm::backend::gemini::GeminiBackend::google_ai(...)
//   ModelRequest::new(...).system(...).timeout_ms(..).max_output_tokens(..)
//   OutputFormat::Json / JsonSchema
//
// The functions below are written against that surface with a mock seam so the
// logic is testable before the spike lands.

use crate::types::AssessmentReport;

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

/// Backend seam: production = lyquid-llm `call_model`; tests = mock.
pub trait AssessmentModel {
    fn complete_json(&self, prompt: &str) -> Result<String, String>;
}

/// Deterministic fallback used until SPIKE(W1) wires the real backend.
pub struct HeuristicModel;

impl AssessmentModel for HeuristicModel {
    fn complete_json(&self, prompt: &str) -> Result<String, String> {
        let _ = prompt;
        // Conservative fixed estimate: 60s p90 x safety handled by
        // timeout_slots_from_estimate. Replaced by the real backend in W2.
        Ok(r#"{"qualification_score":75,"risks":["heuristic-mode"],"est_duration_ms":60000,"est_confidence":40}"#.to_string())
    }
}

pub fn parse_report(raw: &str) -> Result<AssessmentReport, String> {
    // Minimal hand parse to avoid a serde_json dependency in the WASM build
    // until SPIKE(W1) decides the json crate story inside Lyquids.
    // TODO(W2): replace with real JsonSchema-validated parse.
    let get = |k: &str| raw
        .split(&format!("\"{}\"", k))
        .nth(1)
        .and_then(|r| r.split(':').nth(1))
        .and_then(|r| r.split(|c: char| !c.is_ascii_digit() && c != '-' || c == '"').next().map(|s| s.to_string()))
        .ok_or_else(|| format!("missing field {}", k))?;
    Ok(AssessmentReport {
        qualification_score: get("qualification_score")?.parse().map_err(|e| format!("{}", e))?,
        est_duration_ms: get("est_duration_ms")?.parse().map_err(|e| format!("{}", e))?,
        est_confidence: get("est_confidence")?.parse().map_err(|e| format!("{}", e))?,
        risks: vec!["parsed-in-heuristic-mode".to_string()],
    })
}

/// Instance entry point: assess a brief and return the report. The CALLER
/// (agent-broker) then submits `create_deal` — the two-step commit.
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
}
