#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TrustBridge 期末幻灯片构建脚本（python-pptx，16:9，12 页，中文）。

唯一源文件：全部页面文字与 speaker notes 以本脚本内的数据结构内嵌
（仿 `workflow-out/report/build_report.py` 的「内容内嵌 + 构建 + 自检」模式）。

用法（在 trustbridge/ 目录下）：
    python workflow-out/slides/build_slides.py
输出：
    workflow-out/slides/trustbridge-final-slides.pptx （16:9，12 页，每页含 notes）

诚实口径：
- 正文每个数字 / 地址 / tx hash / 状态字面值均标注「文件:行」；
- 数字唯一事实源 = `workflow-out/report/README.md` §3 KEY_HITS 与 §5 证据索引；
- 无数据处写「无数据（原因）」；本脚本不读取、不修改任何证据档；
- 字体不嵌入（标题/正文 Microsoft YaHei，console 块 Consolas），缺字体时由目标机
  系统替代；登记见 `workflow-out/slides/README.md`。

构建后同进程重开产物做自检（页数 / notes / KEY_HITS 抽查 / 三数口径护栏 /
退款链字样 / console 行宽 / 字体覆盖），全部通过才打印 BUILD_OK 并返回 0。
"""

from __future__ import annotations

import os
import re
import sys

from lxml import etree

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PPTX = os.path.join(HERE, "trustbridge-final-slides.pptx")

DATE = "2026-10-30"
HEAD = "8d093b5"

SLIDE_W_IN = 13.333          # 16:9
SLIDE_H_IN = 7.5
EXPECTED_PAGES = 12

FONT_CJK = "Microsoft YaHei"  # 中文字体（不嵌入）
FONT_MONO = "Consolas"        # console 块

ARROW = "\u2192"              # 「→」：程序化拼接退款链，供自检比对
CHAIN_P5 = "10000 %s 9000 %s 10000" % (ARROW, ARROW)

# 颜色
NAVY = RGBColor(0x0B, 0x3D, 0x6B)
INK = RGBColor(0x1B, 0x25, 0x30)
GRAY = RGBColor(0x5A, 0x66, 0x72)
LIGHT = RGBColor(0xF2, 0xF4, 0xF7)
RULE = RGBColor(0xB8, 0xC2, 0xCC)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
CODE_INK = RGBColor(0x10, 0x2A, 0x43)

# 版式（英寸）
MARGIN = 0.55
BODY_W = SLIDE_W_IN - 2 * MARGIN
BODY_TOP = 1.20
BODY_BOTTOM = 6.82

# ---------------------------------------------------------------------------
# 基础绘制工具
# ---------------------------------------------------------------------------


def _set_run_font(run, name, size_pt, bold=False, color=None, italic=False):
    """设置 run 字体：同时写 a:latin / a:ea / a:cs，保证中文走同一字族。"""
    f = run.font
    f.name = name
    f.size = Pt(size_pt)
    f.bold = bold
    f.italic = italic
    if color is not None:
        f.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    latin = rPr.find(qn("a:latin"))
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = etree.SubElement(rPr, qn("a:ea"))
        if latin is not None:
            latin.addnext(ea)
    ea.set("typeface", name)
    cs = rPr.find(qn("a:cs"))
    if cs is None:
        cs = etree.SubElement(rPr, qn("a:cs"))
        ea.addnext(cs)
    cs.set("typeface", name)


def add_paragraphs(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP):
    """paras: list of dict(text, size, bold, color, mono, space_before, align, level)。"""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, spec in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(spec.get("space_before", 0))
        p.space_after = Pt(0)
        p.alignment = spec.get("align", PP_ALIGN.LEFT)
        if spec.get("level"):
            p.level = spec["level"]
        run = p.add_run()
        run.text = spec["text"]
        _set_run_font(
            run,
            FONT_MONO if spec.get("mono") else FONT_CJK,
            spec.get("size", 13),
            spec.get("bold", False),
            spec.get("color", INK),
        )
    return box


def add_title(slide, title, page_no, total=EXPECTED_PAGES):
    add_paragraphs(
        slide, MARGIN, 0.30, BODY_W, 0.62,
        [dict(text=title, size=25, bold=True, color=NAVY)],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    rule = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(MARGIN), Inches(0.98), Inches(BODY_W), Inches(0.025)
    )
    rule.fill.solid()
    rule.fill.fore_color.rgb = NAVY
    rule.line.fill.background()
    rule.shadow.inherit = False
    add_footer(slide, page_no, total)


def add_footer(slide, page_no, total=EXPECTED_PAGES):
    add_paragraphs(
        slide, MARGIN, 6.95, BODY_W, 0.30,
        [dict(text="TrustBridge · CS5298 · %s · 第 %d / %d 页" % (DATE, page_no, total),
              size=9, color=GRAY)],
    )


def add_console_block(slide, x, y, w, lines, size_pt=12.5, caption=None):
    """等宽 console 摘录块：浅底 + 不折行（行宽由 assert_console_fit 预检）。"""
    line_h_in = size_pt * 1.35 / 72.0
    cap_h = 0.26 if caption else 0.0
    h = 0.16 + cap_h + line_h_in * len(lines) + 0.08
    bg = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    bg.fill.solid()
    bg.fill.fore_color.rgb = LIGHT
    bg.line.color.rgb = RULE
    bg.line.width = Pt(0.75)
    bg.shadow.inherit = False
    bg.adjustments[0] = 0.06
    if caption:
        add_paragraphs(
            slide, x + 0.12, y + 0.06, w - 0.24, 0.24,
            [dict(text=caption, size=9.5, color=GRAY)],
        )
    box = slide.shapes.add_textbox(
        Inches(x + 0.12), Inches(y + 0.08 + cap_h), Inches(w - 0.24),
        Inches(h - 0.12 - cap_h),
    )
    tf = box.text_frame
    tf.word_wrap = False           # 长行不折断（计划 §3.1）
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_before = Pt(0)
        p.space_after = Pt(0)
        run = p.add_run()
        run.text = line
        _set_run_font(run, FONT_MONO, size_pt, False, CODE_INK)
    return h


def assert_console_fit(lines, size_pt, w_in, label):
    """Consolas 单字符前进宽度按 0.55em 估算，断言不折行且不出框。"""
    usable_pt = (w_in - 0.24 - 0.08) * 72.0
    worst = max(lines, key=len)
    need_pt = len(worst) * 0.55 * size_pt
    if need_pt > usable_pt:
        raise SystemExit(
            "CONSOLE_FIT_FAIL %s: 最长行 %d 字符需 %.1fpt > 可用 %.1fpt"
            % (label, len(worst), need_pt, usable_pt)
        )
    return len(worst), need_pt, usable_pt


def add_table(slide, x, y, w, rows, col_ratios, font_pt=10.5, header_pt=11.0,
              header_ok=True):
    n_rows = len(rows)
    n_cols = len(rows[0])
    total = sum(col_ratios)
    col_w = [Inches(w * r / total) for r in col_ratios]
    # 行高按字数粗估，python-pptx 会自动增高
    box = slide.shapes.add_table(n_rows, n_cols, Inches(x), Inches(y),
                                 Inches(w), Inches(0.32 * n_rows))
    table = box.table
    for j, cw in enumerate(col_w):
        table.columns[j].width = cw
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.TOP
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.space_before = Pt(0)
            p.space_after = Pt(0)
            run = p.add_run()
            run.text = val
            if i == 0 and header_ok:
                _set_run_font(run, FONT_CJK, header_pt, True, WHITE)
                cell.fill.solid()
                cell.fill.fore_color.rgb = NAVY
            else:
                _set_run_font(run, FONT_CJK, font_pt, False, INK)
                cell.fill.solid()
                cell.fill.fore_color.rgb = WHITE if i % 2 == 1 else LIGHT
    return table


def set_notes(slide, text):
    tf = slide.notes_slide.notes_text_frame
    tf.text = text
    for p in tf.paragraphs:
        for run in p.runs:
            _set_run_font(run, FONT_CJK, 11, False, INK)


def new_slide(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])  # blank


def bullets(items, size=12.5, space_before=5):
    """把要点字符串列表转成段落规格（手动「• 」前缀，要点式排版）。"""
    out = []
    for i, text in enumerate(items):
        out.append(dict(text="• " + text, size=size,
                        space_before=space_before if i else 0))
    return out


def section_block(slide, x, y, w, h, heading, items, size=12.5):
    paras = [dict(text=heading, size=14, bold=True, color=NAVY)]
    paras += bullets(items, size=size, space_before=4)
    add_paragraphs(slide, x, y, w, h, paras)


def src(text, size=10.5):
    return dict(text=text, size=size, color=GRAY, space_before=6)


# ---------------------------------------------------------------------------
# 逐页内容（12 页；每页含 speaker notes）
# ---------------------------------------------------------------------------


def slide_01(prs):
    """P1 封面"""
    s = new_slide(prs)
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
                              Inches(SLIDE_W_IN), Inches(0.42))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    band.shadow.inherit = False

    add_paragraphs(
        s, 0.95, 1.35, SLIDE_W_IN - 1.9, 1.30,
        [dict(text="TrustBridge：基于 Lyquid 平台的 A2A 交易信任桥",
              size=36, bold=True, color=NAVY)],
        anchor=MSO_ANCHOR.MIDDLE,
    )
    add_paragraphs(
        s, 0.95, 2.72, SLIDE_W_IN - 1.9, 0.55,
        [dict(text="CS5298 期末项目 · 演示幻灯片（12 页）", size=19, color=GRAY)],
    )
    rule = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.95), Inches(3.32),
                              Inches(4.2), Inches(0.035))
    rule.fill.solid()
    rule.fill.fore_color.rgb = NAVY
    rule.line.fill.background()
    rule.shadow.inherit = False

    add_paragraphs(
        s, 0.95, 3.55, SLIDE_W_IN - 1.9, 2.6,
        [
            dict(text="作者：人工作者（阶段决策 / 提交确认）+ 多模型协作工作流"
                      "（规划 / 编码 / 审查 / 仲裁）", size=15, color=INK),
            dict(text="日期：%s" % DATE, size=15, color=INK, space_before=8),
            dict(text="基线 HEAD：%s（git log --oneline -1，零 git 写操作）" % HEAD,
                 size=15, color=INK, space_before=8),
            dict(text="配套产物：期末报告 PDF 12 页 + 预录 demo 分镜脚本"
                      "（workflow-out/demo-script.md）", size=15, color=INK, space_before=8),
        ],
    )
    add_footer(s, 1, EXPECTED_PAGES)
    set_notes(
        s,
        "一句话定位：四阶段（R0–R3）+ EVM 对照 + 12 页期末报告已交付；本片为 D2 幻灯片，"
        "配套 D3 预录 demo 分镜脚本 workflow-out/demo-script.md。\n"
        "基线 HEAD 8d093b5 = git log --oneline -1 逐字（plan §8 规划期实跑；本轮 T1 复跑同值），"
        "全程零 git 写操作（只读 log/status/diff）。\n"
        "作者一栏与报告 §5 AI 使用声明同源：规划/编码/审查/仲裁由多模型工作流完成，"
        "人工作者负责阶段决策、提交确认与终裁记录复核（report/build_report.py:786-:796 同口径）。\n"
        "数字出处：DATE / HEAD 均属 KEY_HITS（workflow-out/report/README.md §3）。"
    )
    return s


def slide_02(prs):
    """P2 动机：A2A 信任桥问题"""
    s = new_slide(prs)
    add_title(s, "动机：A2A 信任桥问题", 2)
    add_paragraphs(
        s, MARGIN, BODY_TOP, BODY_W, 4.6,
        bullets([
            "Agent-to-agent 交易缺托管与仲裁层：谁保证先付钱的买方不被骗、先交付的卖方收得到钱"
            "——没有可信中央平台做担保（方向总结:102；报告 §1）",
            "LLM 评估不可信：真实 LLM 未接——节点 egress 策略拒绝私网地址 172.18.0.2，"
            "宿主无 TB_LLM_* 凭据（w1b2-r1-s3-assess.md:151、:161-163）；实跑一律 "
            "heuristic 回放 75 / [\"heuristic-mode\"] / 60000 / 40（:83、:86）",
            "跨主体资金安全：退款、分账、违约计数都必须可读回、可核账"
            "（R0 退款、R1 分账、R2 三裁决分别给出读回证据）",
            "为什么不是纯 EVM escrow：EVM 的「委员会」是 deployer 可覆写的地址表，"
            "本轮配置还包含买卖双方本人（r3-t4-contrast-report.md:91、:248）"
            "——对照细节见 P6",
        ], size=15.0, space_before=13),
    )
    add_paragraphs(
        s, MARGIN, 5.55, BODY_W, 1.1,
        [dict(text="信任桥要解决的三个问题：托管谁持有、裁决谁背书、违约怎么留下痕迹。",
              size=13, color=GRAY)],
    )
    set_notes(
        s,
        "为什么不是纯 EVM escrow：对照实验（r3-t4）证明 EVM 侧的委员会只是合约内一张地址表"
        "（Escrow.sol:81-83、:108 仅 deployer 可配置），本轮 4 个成员里包含 buyer 与 seller 本人"
        "（_r3-t4-flows-raw.txt:23 读回；判决见 r3-t4-contrast-report.md:91），"
        "因此在该配置下它不构成交易外的独立信任锚（同文 :248）。\n"
        "LLM 评估：R1 用容器内 cast call 真实打到 mock 端点，被节点 egress 策略拒绝"
        "（w1b2-r1-s3-assess.md:151 原文 blocked private/internal address 172.18.0.2）；"
        "宿主 env 中不存在 TB_LLM_* 凭据（:161-163 的 G-init ④ 复核），故按方案走回放兜底"
        "并如实登记，不写成「真实 LLM 已接入」。\n"
        "回放定值 75 / [\"heuristic-mode\"] / 60000 / 40 出自 assessor.rs HeuristicModel，"
        "实测返回见 w1b2-r1-s3-assess.md:83。"
    )
    return s


def slide_03(prs):
    """P3 架构一页"""
    s = new_slide(prs)
    add_title(s, "架构一页：四件组件", 3)
    section_block(
        s, MARGIN, BODY_TOP, 5.95, 2.5,
        "① deal 状态机",
        [
            "Qualified → Funded →（Disputed）→ Settled / Refunded",
            "R0 读回字面：\"state\": \"Funded\" → \"state\": \"Refunded\""
            "（w1b2-refunded-evidence.md:37、:43）",
        ],
    )
    section_block(
        s, 6.83, BODY_TOP, 5.95, 2.5,
        "② oracle 两阶段委员会",
        [
            "staging：e2_configure 写入 4 NodeID + threshold=4"
            "（_r3-t3-console-raw.txt:5）",
            "advance / finalize epoch → propose / aggregate（avg_num=4，console:19、:24）",
            "committee_verdict_certified：cert.signers + validate_cert 四查"
            "（committee_certified.rs:341-374）",
        ],
    )
    section_block(
        s, MARGIN, 3.62, 5.95, 2.6,
        "③ keeper 守门人",
        [
            "claim_timeout 到期退款（deadline_slot 判定，core::claim_timeout）",
            "R2 实证：deal-3 deadline 213，keeper 挖出过线块后 claimed"
            "（_r2-keeper-loop-raw.txt:10、:27-:28）",
        ],
    )
    section_block(
        s, 6.83, 3.62, 5.95, 2.6,
        "④ NodeClient 双通道",
        [
            "eth JSON-RPC（宿主直连）+ 容器内 cast（docker exec）",
            "宿主直连四端口 10087 / 11087 / 12087 / 13087（agents/common/rpc.py:91；"
            "w1b2-r3-e2-committee.md:18）",
        ],
    )
    set_notes(
        s,
        "组件与轮次对应（R3 版 implementation.md §2 同源，取回：git show 8d093b5:workflow-out/implementation.md）："
        "状态机 = R0 退款实证；接线 = R1（assess / 角色 / 通道）；"
        "三裁决 = R2（Malicious / Fulfilled / NotFulfilled）；四节点委员会 = R3（E2，判级 L2）。\n"
        "① 状态机：R0 keeper 触发 claim_timeout，deal-1 由 Funded 变 Refunded，"
        "余额 999002 → 1000002（w1b2-refunded-evidence.md:20-:25、:51-:54）；deadline_slot=102、"
        "claim 发生在 block 104（:46-:47），边界语义 now >= deadline 成立。\n"
        "② 两阶段：e2_configure 只做 staging（console:5 原文 dest epoch advance/finalize required），"
        "真正激活要先 __lyquor_oracle_advance_epoch 再 finalize_epoch（_r3-t3-committee-raw.txt:18、:20），"
        "激活后 current.epoch=1、threshold=4（:21）。认证落地前 core::validate_cert 做四查"
        "（全员 ∈ committee_members + 去重 + |signers| ≥ threshold + evidence_root 匹配，"
        "committee_certified.rs:341-352 注释）。\n"
        "③ keeper：R2-T6-A 用显式 --deals deal-3 + 5s 轮询，keeper 自己的 nudge 挖出过线块（block 213），"
        "下一块 214 由 keeper 送 claim_timeout（_r2-keeper-loop-raw.txt:27-:28），归因判定 PASS（:30）。\n"
        "④ 通道：R3-T1 实测宿主 eth_call 可直连 node2–4 三端口（w1b2-r3-e2-committee.md:18），"
        "故无需 docker_exec_cast 降级。"
    )
    return s


def slide_04(prs):
    """P4 演示实录摘录：R3-T3 E2 判级 L2"""
    s = new_slide(prs)
    add_title(s, "演示实录摘录：R3-T3 E2 判级 L2", 4)
    lines = [
        "e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)",
        "committee_verdict_certified: cert.signers RAW = [0, 1, 2, 3] (Vec<SignerID>=Vec<u32>, len=4) deal=deal-1 verdict=1",
    ]
    worst, need, usable = assert_console_fit(lines, 12.5, BODY_W, "P4")
    add_console_block(
        s, MARGIN, BODY_TOP, BODY_W, lines, size_pt=12.5,
        caption="console 原文逐字（node1 取证）：_r3-t3-console-raw.txt:24（上）、:31（下）",
    )
    add_paragraphs(
        s, MARGIN, 2.70, BODY_W, 3.4,
        bullets([
            "判级口径：L2 = 4 提案（inputs=4）+ 4 签（signers=4）"
            "（docs/b3-user-test/通过判据.md:27）",
            "inputs=4 有四个不同 Node 输入行佐证（console:20-:23）；signers=4 见 :31",
            "四条 signer → Node 映射互不相同（console:32-:35），与喂给 e2_configure 的四个 NodeID 逐字一致",
            "agreed 行出现两次（:24、:29）但 certified call 仅一次（:30）、apply_verdict 仅一次（:36）"
            "→ 无重复结算（w1b2-r3-e2-committee.md:87-89）",
        ], size=14.5, space_before=11),
    )
    add_paragraphs(
        s, MARGIN, 6.30, BODY_W, 0.45,
        [dict(text="console 行宽预检：最长 %d 字符 / 需 %.0fpt / 可用 %.0fpt（12.5pt Consolas，不折行）"
                   % (worst, need, usable), size=9.5, color=GRAY)],
    )
    set_notes(
        s,
        "读法讲解：inputs=4 指这一轮聚合收到 4 条来自不同 Node 的提案输入（console:20-:23 四行，"
        "ts_ms 1793328719418/…458/…460/…460），agreed 行 :24 给出 from 4 input(s) (avg_num=4)；"
        "signers=4 指认证证书里 Vec<SignerID> 为 [0, 1, 2, 3]（:31），"
        "并且 :32-:35 把 0/1/2/3 逐个映射到四个互不相同的 NodeID，"
        "与 _r3-t3-committee-raw.txt:12-:15 的四行 nodeN node_id 逐字一致（签者身份闭环）。\n"
        "重复性核验：aggregate 的 agreed 行在 console 中重复两次（:24 与 :29，同一 4 输入集的重复回放），"
        "但 e2_run_verdict_round: certified call submitted 仅一次（:30）、committee_verdict_certified 仅一次（:31）、"
        "apply_verdict 仅一次（:36）——因此没有重复结算（w1b2-r3-e2-committee.md:87-89 如实注记）。\n"
        "纪律：e2_arm 只发一次、run_round 只由 node1 单次触发（禁多次触发；N 次触发 = N 个独立回合，"
        "首回合已把 deal 推到终态，后续 certified call 必败，docs/b3-user-test/通过判据.md:27）。\n"
        + "行宽：最长行 {0} 字符，12.5pt Consolas 约需 {1:.0f}pt，块内可用 {2:.0f}pt，不折行不出框。".format(
            worst, need, usable)
    )
    return s


def slide_05(prs):
    """P5 退款守恒与读回勾稽"""
    s = new_slide(prs)
    add_title(s, "退款守恒与读回勾稽（R3 实例 + T7 复验）", 5)
    add_paragraphs(
        s, MARGIN, BODY_TOP, 6.15, 5.2,
        bullets([
            "实例 Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa"
            " @ 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589"
            "（KEY_HITS；w1b2-r3-e2-committee.md:42）",
            "alice 余额链：%s（faucet +10000 → fund −1000 → NotFulfilled 全额退款 +1000）"
            "（w1b2-r3-e2-committee.md:98）" % CHAIN_P5,
            "bob / broker 恒 0（新实例零起点，无分账）",
            "faucet 全链仅 1 笔（block 333）→ alice 的 10000 基线唯一、无双重 faucet（:98）",
        ], size=14.0, space_before=12),
    )
    add_paragraphs(
        s, 7.05, BODY_TOP, 5.73, 5.2,
        [
            dict(text="T7 复验（D-T3-1 修复后，新实例）", size=14, bold=True, color=NAVY),
            dict(text="• Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa"
                      " @ 0x942ED2fa862887Dc698682cc6a86355324F0f01e", size=12.5, space_before=6),
            dict(text="• exit 0 + DEMO COMPLETE（w1b2-r3-e2-committee.md:164-179；"
                      "_r3-t7-dt31-verify-raw.txt:69、:72-73）", size=12.5, space_before=6),
            dict(text="• faucet read-back OK + refund check OK 两行齐备"
                      "（_r3-t7-dt31-verify-raw.txt:22、:31）", size=12.5, space_before=6),
            dict(text="口径强调", size=14, bold=True, color=NAVY, space_before=14),
            dict(text="• 9000 在此是 funding 中间态（不是结算值）："
                      "三数口径见 P8", size=12.5, space_before=6),
            dict(text="• status≠effect：一切以读回为准（KEY_HITS R0 判读纪律，"
                      "w1b2-refunded-evidence.md:28-:30）", size=12.5, space_before=6),
        ],
    )
    t7_line = ("[committee] refund check OK: alice 10000 -> 9000 (after fund) -> 10000 "
               "(after verdict); bob/broker unchanged")
    assert_console_fit([t7_line], 12.0, BODY_W, "P5")
    add_console_block(
        s, MARGIN, 5.28, BODY_W, [t7_line], size_pt=12.0,
        caption="T7 实录行（demo 内建断言自身证明，无 RuntimeError）："
                "_r3-t7-dt31-verify-raw.txt:31",
    )
    set_notes(
        s,
        "口径强调（冻结条款 2 三数口径铁律）：本页的 9000 是 R3 认证流里的 funding 中间态——"
        "alice 从 faucet 拿 10000，fund 时锁定 1000 剩 9000，NotFulfilled 裁决全额退款 1000 回到 10000；"
        "它不是 R1 正常流分账里的 9000（那是 alice 付给 escrow 后的余额；R1 三数见 P8 R1 行）。\n"
        "来源：w1b2-r3-e2-committee.md:98 逐项勾稽（faucet +10000 / fund −1000 / 退款 +1000，bob/broker 恒 0）；"
        "链上 faucet 单次实证 = blocks 0–341 全量扫描仅 1 笔 faucet(string,uint128)（block 333，from broker，"
        "agent=alice，amount=10000）。\n"
        "T7 复验：D-T3-1（demo 内建余额断言 stale baseline）于 d1e6f5f 修复后在新实例 "
        "Lyquid-dpp6…unqa @ 0x942ED2fa…f01e 上端到端重跑，exit 0、DEMO COMPLETE"
        "（_r3-t7-dt31-verify-raw.txt:69；:72-:73 记录 EXIT=0），"
        "refund check OK: alice 10000 -> 9000 (after fund) -> 10000 (after verdict); bob/broker unchanged（:31）。\n"
        "判读纪律：status=0x1 仅代表已上序，平台会吞方法 Err，成功判定以 deal_info / balance_of 读回为准"
        "（w1b2-refunded-evidence.md:28-:30）。"
    )
    return s


def slide_06(prs):
    """P6 实验对照表：纯 EVM Escrow vs Lyquid（四维）"""
    s = new_slide(prs)
    add_title(s, "实验对照：纯 EVM Escrow vs Lyquid（四维）", 6)
    rows = [
        ["维度", "纯 EVM Escrow（run-3）", "Lyquid（R3 / R2）"],
        ["① 创建 gas",
         "1,936,008（to=null 创建交易，block 384）",
         "3,843,041（R3，block 327）/ 3,707,457（R2，block 199）"
         "（r3-t4-contrast-report.md:180-187）"],
        ["② 代码量（wc -l，含/去测试）",
         "Escrow.sol 407（无单元测试）",
         "六文件 2083 / 1323（去测）；计入 lib.rs 双口径 2933 / 2173（:60-83）"],
        ["③ 信任假设",
         "合约内地址表委员会（Escrow.sol:81-83、:108，仅 deployer 可配），"
         "本轮含买卖双方本人；3-of-4",
         "平台注册 4 个 NodeID + threshold=4（_r3-t3-final-state-raw.txt:10）；"
         "认证落地前 validate_cert 四查（:85-97）"],
        ["④ 裁决不可篡改",
         "负对照实证：deal-3 三签重放 deal-4 被拒，原文 non-member signer，rc=1（:104、:232）",
         "无数据（本轮未做 Lyquid 侧同型重放实验，仅代码路径证据，:104、:109）"],
    ]
    add_table(s, MARGIN, BODY_TOP, BODY_W, rows, col_ratios=[1.45, 4.3, 5.2],
              font_pt=11.5, header_pt=12.0)
    add_paragraphs(
        s, MARGIN, 3.72, BODY_W, 0.55,
        [dict(text="口径声明：R2 / R3 两个不同实例并列不合并；「无数据（原因）」写法沿用报告纪律；"
                   "代码量为 wc -l 口径（含空行注释，未折算有效代码行）。",
              size=11.5, color=GRAY)],
    )
    set_notes(
        s,
        "口径声明：R2 与 R3 是两个不同实例、不同轮次，数字并列给出，不合并统计"
        "（r3-t4-contrast-report.md:220 数据缺口表）。R2 实例 0xFD6F7A6a5c21A3f503EBaE7a473639974379c351"
        "（Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa；_r2-normal-assess-raw.txt:2）。\n"
        "① gas：三者同为 anvil#0 签名、同链、同一 to=null 创建交易形态，故部署 gas 可直接对比"
        "（:187）；Lyquid 的 shaker deploy 还含 OCI 镜像 / registry 环节，该环节无链上对应物，不进表。\n"
        "② 代码量：wc -l 计数含空行与注释、未折算有效代码行；solloc/cloc 本机不可用（:81）；"
        "去测试口径 = 起始行号 − 1（三处 #[cfg(test)] 均延至文件尾）；Escrow.sol 无单元测试，"
        "其行为验证等价物是 run-contrast.sh 的三流 + 负对照（:81）。\n"
        "③ 信任假设：EVM 侧委员会是合约存储里的地址表，deployer 可用 require(msg.sender == deployer) "
        "覆写（Escrow.sol:108），本轮成员含 buyer / seller 本人，故不构成交易外独立信任锚；"
        "Lyquid 侧是平台注册的 4 个 NodeID、threshold=4（4-of-4），认证回调读平台已验证的 cert.signers 再做 "
        "validate_cert 四查（:85-97）。\n"
        "④ 不可篡改：EVM 侧有实证（同签名集不能跨 deal 复用，rc=1 non-member signer，"
        "_r3-t4-flows-raw.txt:40-41 / _r3-t4-evidence-recheck-raw.txt:100-104）；"
        "Lyquid 侧本轮没有做同型实验，只有 core::validate_cert 的 evidence_root 匹配作为机制证据，"
        "按报告纪律写「无数据（原因）」，不把「代码里有校验」写成「已实测」（:109）。"
    )
    return s


def slide_07(prs):
    """P7 对照要点解读（诚实口径）"""
    s = new_slide(prs)
    add_title(s, "对照要点解读：不做单向结论", 7)
    add_paragraphs(
        s, MARGIN, BODY_TOP, BODY_W, 5.2,
        bullets([
            "部署环节 EVM 更低：1,936,008 vs 3,843,041，约 1.98×（r3-t4-contrast-report.md:250）",
            "单笔操作无单向结论：create_deal 47,908 明显低于 createDeal 226,658；"
            "但 fund 反而是 EVM 更低（32,713 vs 36,014）（:251）",
            "行数差不能直接读成复杂度差：Escrow 无单元测试，验证等价物 = 三流（normal / timeout / "
            "adversarial）+ 负对照（:252）",
            "两侧工作量不同：EVM 一轮 20 笔交易 vs Lyquid R3 14 笔（含认证回合），"
            "交易数与总量不构成同工作量对比（:193、:197）",
            "结算单位不同：gasUsed 可比，但 block.timestamp 与 slot 的时间语义不同（:219）",
        ], size=15.0, space_before=15),
    )
    add_paragraphs(
        s, MARGIN, 5.95, BODY_W, 0.75,
        [dict(text="结论克制：E2 认证买到的是额外的身份信任层，代价可量化；"
                   "「谁更便宜」需要同工作量口径，本轮不具备。", size=13, color=GRAY)],
    )
    set_notes(
        s,
        "解读口径（逐条对应 r3-t4-contrast-report.md §4）：报告结论 3 承认 Lyquid 四节点认证是额外信任层，"
        "代价可量化（部署 gas 3,843,041 vs 1,936,008 约 1.98×；认证回合 propose 1 + aggregate 10 行 + "
        "回调 1 笔，:250）；结论 4 明确单笔操作没有单向结论（:251）；结论 5 强调代码量对比必须带口径（:252）。\n"
        "工作量差异：EVM 侧一轮实验含 3 条完整业务流 + 1 次负对照（20 笔 = deploy + 19），"
        "Lyquid R3 只有 1 条业务流 + 认证回合（14 笔 = 创建 + 13，:193），因此本片不引用任何「总量更省」说法。\n"
        "口径限制（同 :219/:220）：两侧结算单位不同（gasUsed 可比，block.timestamp 与 slot 时间语义不同）；"
        "单机 devnet 共享同一 anvil，EVM 实验的 evm_increaseTime 会推进共享时间源（plan §5-R4 已登记）。"
    )
    return s


def slide_08(prs):
    """P8 里程碑时间线（R0→R3）"""
    s = new_slide(prs)
    add_title(s, "里程碑时间线：R0 → R3", 8)
    rows = [
        ["阶段 · 日期", "关键读回 / 结果", "出处"],
        ["R0 · 2026-10-28\nkeeper 退款",
         "Funded → Refunded；tx 0x85e4e39b…0838；余额 999002 → 1000002；"
         "deadline_slot 102、claim@104；gasUsed 35996",
         "w1b2-refunded-evidence.md:14、:20-25、:43、:46-47、:51-54"],
        ["R1 · 2026-10-29\n接线 + 正常流",
         "Settled，分账 alice=9000 / bob=980 / broker=20（守恒 9000+980+20=10000）；"
         "assess_brief 7→4 string（Stack too deep），selector 0x3297eeb6",
         "w1b2-r1-demo-normal.md:29、:79；w1b2-r1-s3-assess.md:184、:78"],
        ["R2 · 2026-10-29\n三裁决",
         "Malicious→Refunded（misconduct 1→2）/ Fulfilled→Settled（bob +980 / broker +20，"
         "alice 49000→48000→48000）/ NotFulfilled→Refunded（计数不增）；"
         "实例守恒 77000 / 3920 / 80（sum 81000）",
         "w1b2-r2-adversarial.md:86-90、:77、:89、:147、:156-157"],
        ["R3 · 2026-10-30\nE2 委员会",
         "判级 L2：inputs=4（agreed, avg_num=4）+ signers=[0, 1, 2, 3]（len=4）；"
         "deal-1 → Refunded，全额退款",
         "_r3-t3-console-raw.txt:24、:31；w1b2-r3-e2-committee.md:54"],
    ]
    add_table(s, MARGIN, BODY_TOP, BODY_W, rows, col_ratios=[1.55, 7.0, 3.7],
              font_pt=11.0, header_pt=11.5)
    set_notes(
        s,
        "三数口径复述（冻结条款 2 铁律，逐条对 KEY_HITS）：\n"
        "(1) 9000 / 980 / 20 三数同现 = R1 正常流分账（w1b2-r1-demo-normal.md:29 原文 "
        "final state=Settled balances: alice=9000 bob=980 broker=20；:79 守恒式 9000 + 980 + 20 = 10000）。"
        "fee_bps=200，即 1000 × 200 / 10000 = 20。\n"
        "(2) R2 Fulfilled 结算 = bob +980 / broker +20，alice 49000 → 48000（fund）→ 48000（verdict，"
        "refund_to_buyer=0 不再变动）——本行是 split check 与 G6B 表的字面值（w1b2-r2-adversarial.md:77-:78、:89）。"
        "R2 对抗流档内没有这组三数（alice 侧是 49000/48000/47000 量级），三数只属 R1 语境。\n"
        "(3) 9000 作为独立数值出现在 R3 = funding 中间态：alice 10000 →（fund −1000）9000 →（退款 +1000）10000"
        "（w1b2-r3-e2-committee.md:98），与 R1 的 9000 语义不同。\n"
        "R0 行：tx 0x85e4e39b…0838 完整哈希见 w1b2-refunded-evidence.md:14/:24；status 0x1、block 104、"
        "gasUsed 35996（:20-:25）；余额 999002（block 103）→ 1000002（block 104）（:51-:54）；"
        "deadline_slot=102 而 claim 在 104（:46-:47）。\n"
        "R1 行：7×string → 4×string 因 solc Stack too deep（w1b2-r1-s3-assess.md:184 偏离登记 S3-1），"
        "selector 0x3297eeb6 冻结进 agents/common/rpc.py 的 _ABI 表（:78、:87）。\n"
        "R2 行：三裁决终态表见 w1b2-r2-adversarial.md:86-90；misconduct 1→2 见 :103；"
        "实例终态 77000 / 3920 / 80（sum 81000）见 :147、:156-157。\n"
        "R3 行：判级 L2 = 4 提案 + 4 签（docs/b3-user-test/通过判据.md:27），console 原文见 _r3-t3-console-raw.txt:24、:31。\n"
        "如实提示：R1 的真实 LLM 未接入（egress 拒绝私网 + 无 TB_LLM_* 凭据，w1b2-r1-s3-assess.md:151、:161-163），"
        "本次 assess 全程为 heuristic 回放。"
    )
    return s


def slide_09(prs):
    """P9 信任假设与局限（七条，诚实清单）"""
    s = new_slide(prs)
    add_title(s, "信任假设与局限（诚实清单，七条）", 9)
    add_paragraphs(
        s, MARGIN, BODY_TOP, BODY_W, 5.3,
        bullets([
            "真实 LLM 未接：heuristic 回放 75 / [\"heuristic-mode\"] / 60000 / 40"
            "（w1b2-r1-s3-assess.md:83、:151）",
            "misconduct 无 getter：只有 console 行 apply_verdict: … misconduct=[]，无链上读回"
            "（r3-t4-contrast-report.md:107）",
            "B3 线下用户测试未收集（三文档已备：docs/b3-user-test/；R3 版 implementation.md:603）",
            "对抗流 node 复跑未执行（R3 版 implementation.md:511；r3-t4-contrast-report.md:212-221）",
            "对照口径限制：R2/R3 两实例不合并、单机 devnet 共享时间源"
            "（r3-t4-contrast-report.md:212-221；R3 版 implementation.md:28）",
            "eth 直调路径弱门：apply_committee_verdict 只做地址门、不验签名，源码自述 TODO(W4)"
            "（lib.rs:222）",
            "status≠effect：平台吞方法 Err，交易 status 0x1 但方法未生效（_r2-adversarial-raw.txt:6）",
        ], size=14.0, space_before=10),
    )
    add_paragraphs(
        s, MARGIN, 4.30, BODY_W, 0.85,
        [
            dict(text="与期末报告 §4 局限表同源（workflow-out/report/trustbridge-final-report.pdf；"
                      "证据索引见 report/README.md §5）。", size=10.5, color=GRAY),
            dict(text="指针口径：implementation.md 已于 R4-D2+D3 重写，本页「R3 版」指针一律指 R3 版，"
                      "以 git show 8d093b5:workflow-out/implementation.md 取回。",
                 size=10.5, color=GRAY, space_before=4),
        ],
    )
    set_notes(
        s,
        "每条「为什么留着」：\n"
        "1) 真实 LLM：平台 egress 策略拒私网 / 内部地址（原文 blocked private/internal address 172.18.0.2），"
        "宿主无 TB_LLM_* 凭据，按方案走回放兜底并如实登记，不宣称已接入（w1b2-r1-s3-assess.md:151、:161-163）。\n"
        "2) misconduct：方法清单已冻结、无 getter，println 是既有观测缝（先例 fund:deal_view / deal_info），"
        "非共识状态、语义零影响（w1b2-r2-adversarial.md:110-111；r3-t4-contrast-report.md:107）。\n"
        "3) B3 用户测试：三份文档（操作手册 / 反馈收集表 / 通过判据）已备，线下收集需人工组织，本轮未做"
        "（R3 版 implementation.md:603 文档交付行，git show 8d093b5:workflow-out/implementation.md 取回）。\n"
        "4) 对抗流 node 复跑：R3 授权面无链写实跑，留作后续（R3 版 implementation.md:511）；"
        "数据缺口表同 r3-t4-contrast-report.md:212-221。\n"
        "5) 对照口径：两实例并列不合并；单机 devnet 共享同一 anvil 时间源，EVM 的 evm_increaseTime 会推进它"
        "（R3 版 implementation.md:28 devnet 行；r3-t4-contrast-report.md:253 共同前提）。\n"
        "6) eth 直调弱门：lib.rs:222 自述 TODO(W4)——R2 轮次用的就是这条只做地址门、不验签名的路径；"
        "R3 的认证回调路径强度不同，报告并列给出不合并（r3-t4-contrast-report.md:97）。\n"
        "7) status≠effect：R2 attempt-1 的 apply_committee_verdict 交易 status 0x1 但 deal-4 停留 Disputed"
        "（_r2-adversarial-raw.txt:6），故一切结论以读回为准。\n"
        "指针口径：implementation.md 已于 R4-D2+D3 重写（D1），本页所有 implementation.md 指针均指 R3 版，"
        "以 git show 8d093b5:workflow-out/implementation.md 取回；期末报告 PDF 封面引用的 :28-:31 与"
        " report/README.md:133 的 §5 索引行同源、同以该取回源核对（report/README.md 与 PDF 按 plan.md:27 只读冻结）。"
    )
    return s


def slide_10(prs):
    """P10 结论"""
    s = new_slide(prs)
    add_title(s, "结论", 10)
    add_paragraphs(
        s, MARGIN, BODY_TOP, BODY_W, 3.9,
        bullets([
            "四阶段全链在单机 devnet 实证：R0 超时退款 / R1 正常流分账 / R2 三裁决 / R3 4-of-4 认证"
            "——每步都有读回证据（见 P8 时间线）",
            "E2 认证是额外的身份信任层，代价可量化：部署 gas 约 1.98×；认证回合 propose 1 行 + "
            "aggregate 10 行 + 回调 1 笔（r3-t4-contrast-report.md:199-208、:250）",
            "纯 EVM escrow 的负对照证明「签名不可跨单挪用」，但地址表委员会不构成交易外独立信任锚"
            "（r3-t4-contrast-report.md:248-249）",
        ], size=15.5, space_before=16),
    )
    add_paragraphs(
        s, MARGIN, 4.45, BODY_W, 2.2,
        [
            dict(text="诚实边界（同 P9）", size=14, bold=True, color=NAVY),
            dict(text="• 真实 LLM 未接、B3 用户测试未收集、对抗流 node 复跑未执行；"
                      "这些不构成「已达成」，只构成「已如实标注」", size=13, space_before=6),
            dict(text="• 一句话：信任桥的核心链路全部有读回证据；未证的如实标注。",
                 size=13, space_before=6),
        ],
    )
    set_notes(
        s,
        "一句话总结：信任桥的核心链路（托管 / 退款 / 分账 / 三裁决 / 4-of-4 认证）全部有读回证据，"
        "未证的（真实 LLM、B3 线下用户测试、对抗流 node 复跑、Lyquid 侧跨单重放）如实标注。\n"
        "代价量化出处：r3-t4-contrast-report.md:250 结论 3（部署 gas 3,843,041 vs 1,936,008 约 1.98×；"
        "认证回合 propose 1 + aggregate 10 行 + 回调 1 笔）；:199-208 是④-6 认证回合消息开销表。\n"
        "收益口径：委员会由平台注册的 4 个 NodeID 构成、threshold 4/4，认证回调读平台已校验的 cert.signers "
        "并做 validate_cert 四查（committee_certified.rs:341-374），裁决落链前多一道与地址表无关的身份校验。\n"
        "不夸大：R3 只跑了一条业务流（deal-1），不能据此宣称端到端成本全貌；P7 已声明本轮不具备"
        "同工作量总量对比。"
    )
    return s


def slide_11(prs):
    """P11 后续工作"""
    s = new_slide(prs)
    add_title(s, "后续工作", 11)
    add_paragraphs(
        s, MARGIN, BODY_TOP, BODY_W, 5.2,
        bullets([
            "W2'/W3：probe SPIKE 清理与 oracle 路线收敛",
            "真实 LLM 接入：公网可达的 HTTPS 端点 + 真实凭据（TB_LLM_*）"
            "——R1 已把 egress 策略拒私网列为阻塞原因（w1b2-r1-s3-assess.md:159-163）",
            "B3 线下用户测试：三文档已备（docs/b3-user-test/ 操作手册.md / 反馈收集表.md / 通过判据.md），"
            "待组织收集",
            "D-T3-1 已修复并 T7 复验（faucet read-back OK + refund check OK，exit 0；"
            "_r3-t7-dt31-verify-raw.txt:22、:31、:69）",
            "遗留：对抗流 node 复跑（R3 版 implementation.md:511）；Lyquid 侧跨单签名重放实验（无数据，"
            "r3-t4-contrast-report.md:217）",
        ], size=15.0, space_before=15),
    )
    set_notes(
        s,
        "与报告 §5 / 后续清单对齐（workflow-out/report/README.md §5 证据索引 + PDF §4/§5）：\n"
        "真实 LLM：R1 结论 2 明确「真实 LLM 通道需要公网可达的 HTTPS 端点 + 真实凭据」"
        "（w1b2-r1-s3-assess.md:159-160），宿主 env 无 TB_LLM_* 凭据（:161-163）。\n"
        "B3：三份文档落盘于 docs/b3-user-test/（操作手册 30,266B / 反馈收集表 5,378B / 通过判据 11,308B）。\n"
        "D-T3-1（demo 内建余额断言 stale baseline）由 T6.1 修复（d1e6f5f），T7 在新实例端到端复验："
        "exit 0、DEMO COMPLETE、faucet read-back OK、refund check OK（_r3-t7-dt31-verify-raw.txt:22、:31、:69）。\n"
        "遗留项两个：对抗流 node 复跑（R3 授权面无链写实跑，R3 版 implementation.md:511）；"
        "Lyquid 侧跨单签名重放实验（数据缺口表 r3-t4-contrast-report.md:217）。"
    )
    return s


def slide_12(prs):
    """P12 封底：证据索引与声明"""
    s = new_slide(prs)
    add_title(s, "证据索引与声明", 12)
    section_block(
        s, MARGIN, BODY_TOP, 6.05, 4.6,
        "证据索引",
        [
            "完整索引：workflow-out/report/README.md §5（浓缩表同报告 PDF 附录 A）",
            "原始实录：workflow-out/_r1-*、_r2-*、_r3-*（逐条带「文件:行」）",
            "数字唯一事实源：report/README.md §3 KEY_HITS（27 项，本轮实跑 27/27 命中）",
        ],
        size=13.0,
    )
    section_block(
        s, 6.95, BODY_TOP, 5.83, 4.6,
        "声明与产物",
        [
            "AI 使用声明：同报告 §5（规划 / 编码 / 审查 / 仲裁由多模型工作流完成，人工作者负责决策与复核）",
            "产物：报告 PDF 12 页（workflow-out/report/trustbridge-final-report.pdf）",
            "产物：本幻灯片 12 页 + 预录 demo 分镜脚本 workflow-out/demo-script.md",
        ],
        size=13.0,
    )
    add_paragraphs(
        s, MARGIN, 5.95, BODY_W, 0.75,
        [dict(text="口径：全部数字可溯源到「文件:行」；无数据处写「无数据（原因）」；"
                   "本片不引用任何规划期 / 执行期「预期值」。", size=12, color=GRAY)],
    )
    set_notes(
        s,
        "口径收尾：本片所有数字 / 地址 / tx / 状态字面值均可溯源到「文件:行」，与 KEY_HITS 不一致处以 KEY_HITS 为准。\n"
        "KEY_HITS 核对：report/README.md §3 抽查命令实跑 27/27 命中（MISSING=[]），见 report/README.md §3(b) 实跑输出；"
        "本片自带程序化抽查（≥15 项，实际覆盖 P1–P11 的 23 项候选）。\n"
        "三份产物的关系：报告 PDF（12 页，D1）讲完整论证；本幻灯片（D2，12 页）讲课上用浓缩版；"
        "demo 脚本（D3，workflow-out/demo-script.md）讲怎么录 5±1 分钟的演示视频。\n"
        "归档纪律：本片与 demo 脚本均在 workflow-out/ 下，原始实录不改一字（纯文档轮，零 git 写操作）。"
    )
    return s


SLIDE_BUILDERS = [
    slide_01, slide_02, slide_03, slide_04, slide_05, slide_06,
    slide_07, slide_08, slide_09, slide_10, slide_11, slide_12,
]

# ---------------------------------------------------------------------------
# 自检（构建后重开产物）
# ---------------------------------------------------------------------------

KEY_HITS = [
    "3,843,041", "3,707,457", "1,936,008",
    "0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589",
    "0x942ED2fa862887Dc698682cc6a86355324F0f01e",
    "0xFD6F7A6a5c21A3f503EBaE7a473639974379c351",
    "inputs=4", "[0, 1, 2, 3]", "1000002", "999002", "77000", "3920", "81000",
    "407", "2083", "1323", "2933", "2173", "980", "8d093b5", "2026-10-30",
    "non-member signer", "misconduct",
]
KEY_HITS_MIN = 15

TRIPLE_ALLOWED_PAGES = {8}    # 9000 + 980 + 20 三元组只允许出现在 P8（R1 语境）
TRIPLE_TOKENS = ("9000", "980", "20")


def _token_re(tok):
    # 「独立数值」边界：前后不能是数字或千分位逗号
    return re.compile(r"(?<![\d,])%s(?![\d,])" % re.escape(tok))


def shapes_text(shapes):
    for sh in shapes:
        if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
            for t in shapes_text(sh.shapes):
                yield t
        if getattr(sh, "has_table", False) and sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    yield cell.text
        if getattr(sh, "has_text_frame", False) and sh.has_text_frame:
            yield sh.text_frame.text


def slide_pages(prs):
    """返回 [(页码, 全文本)]，含 notes。"""
    out = []
    for idx, slide in enumerate(prs.slides, 1):
        parts = list(shapes_text(slide.shapes))
        if slide.has_notes_slide:
            parts.append(slide.notes_slide.notes_text_frame.text)
        out.append((idx, "\n".join(p for p in parts if p)))
    return out


def check_font_coverage(text):
    """可选检查：全部字符是否在 Microsoft YaHei cmap 内（缺字体方块预警）。"""
    font_file = r"C:\Windows\Fonts\msyh.ttc"
    if not os.path.exists(font_file):
        return "SKIP（未找到 %s）" % font_file
    try:
        from fontTools.ttLib import TTCollection
    except Exception as exc:  # noqa: BLE001
        return "SKIP（fontTools 不可用：%s）" % exc
    cmap = set()
    for f in TTCollection(font_file).fonts:
        for t in f["cmap"].tables:
            cmap.update(t.cmap.keys())
    chars = {c for c in text if c not in "\n\r\t "}
    missing = sorted(c for c in chars if ord(c) not in cmap)
    return "UNIQUE_CHARS=%d MISSING_IN_MSYH=%d %s" % (
        len(chars), len(missing), "MISSING=%r" % "".join(missing) if missing else "OK")


def self_check():
    failures = []
    prs = Presentation(OUT_PPTX)
    pages = slide_pages(prs)
    n = len(prs.slides)

    # (a) 页数
    print("PAGES=%d" % n)
    if n != EXPECTED_PAGES:
        failures.append("页数 %d != 方案值 %d" % (n, EXPECTED_PAGES))
    if n < 10:
        failures.append("页数 %d < 10（D2 完成判据）" % n)

    # (a') 16:9 与文件非空
    size_ok = (
        abs(prs.slide_width.inches - SLIDE_W_IN) < 0.01
        and abs(prs.slide_height.inches - SLIDE_H_IN) < 0.01
    )
    print("SLIDE_SIZE_IN=%.3f x %.3f (16:9=%s)"
          % (prs.slide_width.inches, prs.slide_height.inches, size_ok))
    if not size_ok:
        failures.append("页面尺寸非 16:9 13.333x7.5")

    # (b) notes 非空
    empty_notes = []
    for idx, slide in enumerate(prs.slides, 1):
        txt = slide.notes_slide.notes_text_frame.text.strip() if slide.has_notes_slide else ""
        if not txt:
            empty_notes.append(idx)
    print("NOTES_OK=%s (empty=%s)" % (not empty_notes, empty_notes))
    if empty_notes:
        failures.append("notes 为空：%s" % empty_notes)

    # (c) KEY_HITS 抽查
    all_text = "\n".join(t for _, t in pages)
    missing = [k for k in KEY_HITS if k not in all_text]
    hits = len(KEY_HITS) - len(missing)
    print("KEY_HITS=%d/%d (MIN=%d)" % (hits, len(KEY_HITS), KEY_HITS_MIN))
    print("MISSING=%s" % missing)
    if hits < KEY_HITS_MIN:
        failures.append("KEY_HITS 命中 %d < %d" % (hits, KEY_HITS_MIN))

    # (d) 三数口径护栏：9000 + 980 + 20 同现页集合 ⊆ {P8}
    triple_pages = []
    for idx, txt in pages:
        if all(_token_re(tok).search(txt) for tok in TRIPLE_TOKENS):
            triple_pages.append(idx)
    print("TRIPLE_PAGES=%s (allowed=%s)" % (triple_pages, sorted(TRIPLE_ALLOWED_PAGES)))
    if not set(triple_pages) <= TRIPLE_ALLOWED_PAGES:
        failures.append("9000/980/20 三元组出现在非 P8 页：%s" % triple_pages)
    if not triple_pages:
        failures.append("P8 未出现 R1 三数三元组（预期应有）")

    # (d'') P5 退款链完整字样
    p5_text = dict(pages).get(5, "")
    chain_ok = CHAIN_P5 in p5_text
    print("P5_CHAIN=%s (%r)" % (chain_ok, CHAIN_P5))
    if not chain_ok:
        failures.append("P5 缺退款链字样 %r" % CHAIN_P5)

    # (e) 字体覆盖（可选，不阻断内容判据）
    print("FONT_COVERAGE=%s" % check_font_coverage(all_text))

    # (f) 附录：逐页摘要便于人工复核
    for idx, txt in pages:
        print("PAGE %02d len=%d" % (idx, len(txt)))

    size_bytes = os.path.getsize(OUT_PPTX)
    print("SIZE_BYTES=%d" % size_bytes)
    if size_bytes <= 0:
        failures.append("产物为空文件")

    if failures:
        print("BUILD_FAILED")
        for f in failures:
            print("FAIL: %s" % f)
        return 1
    print("BUILD_OK")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    prs = Presentation()
    prs.slide_width = Inches(SLIDE_W_IN)
    prs.slide_height = Inches(SLIDE_H_IN)
    for fn in SLIDE_BUILDERS:
        fn(prs)
    prs.save(OUT_PPTX)
    print("OUTPUT=%s" % OUT_PPTX)
    print("BUILT_PAGES=%d" % len(prs.slides))
    return self_check()


if __name__ == "__main__":
    sys.exit(main())
