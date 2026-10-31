#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TrustBridge 期末报告构建脚本（reportlab Platypus，A4，中文）。

唯一源文件：报告全文以本脚本内的数据结构内嵌。
用法（在 trustbridge/ 目录下）：
    python workflow-out/report/build_report.py
输出：
    workflow-out/report/trustbridge-final-report.pdf   （A4，>= 6 页）

诚实口径：正文每个数字 / 地址 / tx hash / 状态字面值均标注「文件:行」，
出处限定为 workflow-out/ 下既有证据档与课程目录下的方向总结 / 计划书；
无数据处写「无数据（原因）」。本脚本不读取、不修改任何证据档。
"""

from __future__ import annotations

import os
import sys
import tempfile

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PDF = os.path.join(HERE, "trustbridge-final-report.pdf")

REPORT_DATE = "2026-10-30"
HEAD = "8d093b5"

# 字体候选（plan §4 风险 R2 的备选顺序：msyh -> simhei -> simsun）
FONT_CANDIDATES = [
    (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc", "Microsoft YaHei"),
    (r"C:\Windows\Fonts\simhei.ttf", None, "SimHei"),
    (r"C:\Windows\Fonts\simsun.ttc", None, "SimSun"),
]

FONT = "TB-CJK"
FONT_B = "TB-CJK-Bold"
FONT_USED = {"file": "", "family": "", "bold": ""}

TOTAL_PAGES = {"value": 0, "doc": 0}

# ---------------------------------------------------------------------------
# 样式
# ---------------------------------------------------------------------------

STYLES: dict[str, ParagraphStyle] = {}


def register_fonts() -> None:
    """注册中文字体；失败时抛出明确异常（不静默降级）。"""
    for path, bold, family in FONT_CANDIDATES:
        if not os.path.exists(path):
            continue
        pdfmetrics.registerFont(TTFont(FONT, path))
        if bold and os.path.exists(bold):
            pdfmetrics.registerFont(TTFont(FONT_B, bold))
            FONT_USED["bold"] = bold
        else:
            pdfmetrics.registerFont(TTFont(FONT_B, path))
            FONT_USED["bold"] = path
        FONT_USED["file"] = path
        FONT_USED["family"] = family
        return
    raise RuntimeError("no CJK font found in %r" % (FONT_CANDIDATES,))


def init_styles() -> None:
    STYLES["title"] = ParagraphStyle(
        "title", fontName=FONT_B, fontSize=21, leading=30,
        alignment=TA_CENTER, spaceBefore=6, spaceAfter=4, wordWrap="CJK",
    )
    STYLES["subtitle"] = ParagraphStyle(
        "subtitle", fontName=FONT, fontSize=13.5, leading=20,
        alignment=TA_CENTER, spaceAfter=14, textColor=colors.HexColor("#333333"),
        wordWrap="CJK",
    )
    STYLES["h1"] = ParagraphStyle(
        "h1", fontName=FONT_B, fontSize=15.5, leading=22,
        spaceBefore=6, spaceAfter=8, textColor=colors.HexColor("#0B3D6B"),
        wordWrap="CJK",
    )
    STYLES["h2"] = ParagraphStyle(
        "h2", fontName=FONT_B, fontSize=12, leading=18,
        spaceBefore=9, spaceAfter=4, textColor=colors.HexColor("#123B5C"),
        wordWrap="CJK", keepWithNext=1,
    )
    STYLES["h3"] = ParagraphStyle(
        "h3", fontName=FONT_B, fontSize=10.8, leading=16,
        spaceBefore=6, spaceAfter=3, wordWrap="CJK",
    )
    STYLES["body"] = ParagraphStyle(
        "body", fontName=FONT, fontSize=10.2, leading=16.4,
        alignment=TA_JUSTIFY, spaceAfter=5, wordWrap="CJK",
    )
    STYLES["bullet"] = ParagraphStyle(
        "bullet", parent=STYLES["body"], leftIndent=12, bulletIndent=2,
        spaceAfter=2.5,
    )
    STYLES["note"] = ParagraphStyle(
        "note", parent=STYLES["body"], fontSize=9.2, leading=14,
        textColor=colors.HexColor("#444444"),
    )
    STYLES["cell"] = ParagraphStyle(
        "cell", fontName=FONT, fontSize=8.6, leading=12.2,
        alignment=TA_LEFT, wordWrap="CJK",
    )
    STYLES["cellc"] = ParagraphStyle(
        "cellc", parent=STYLES["cell"], alignment=TA_CENTER,
    )
    STYLES["cellm"] = ParagraphStyle(
        "cellm", fontName="Courier", fontSize=7.6, leading=11.0,
        alignment=TA_LEFT, wordWrap="CJK",
    )
    STYLES["th"] = ParagraphStyle(
        "th", fontName=FONT_B, fontSize=9, leading=12.5,
        alignment=TA_CENTER, wordWrap="CJK", textColor=colors.HexColor("#10263B"),
    )
    STYLES["cells"] = ParagraphStyle(
        "cells", fontName=FONT, fontSize=7.9, leading=11.2,
        alignment=TA_LEFT, wordWrap="CJK", textColor=colors.HexColor("#33404C"),
    )
    STYLES["codef"] = ParagraphStyle(
        "codef", fontName="Courier", fontSize=6.8, leading=9.9,
        leftIndent=6, spaceBefore=2, spaceAfter=7,
        backColor=colors.HexColor("#F5F7F9"),
        borderPadding=4, borderWidth=0.4,
        borderColor=colors.HexColor("#C9D2DA"),
    )
    STYLES["cover_kv"] = ParagraphStyle(
        "cover_kv", parent=STYLES["cell"], fontSize=9.4, leading=14,
    )


def esc(text: str) -> str:
    """Paragraph 内的 XML 转义（代码块 / 表格里含 < > & 时用）。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def H1(text: str) -> list:
    return [
        P(text, "h1"),
        HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#0B3D6B"),
                   spaceBefore=0, spaceAfter=9),
    ]


def H2(text: str) -> Paragraph:
    return P(text, "h2")


def bullets(items: list[str]) -> list:
    # 内容由本脚本控制（可含 <b> 等标记），不做 XML 转义
    return [Paragraph(i, STYLES["bullet"], bulletText="•") for i in items]


def code(text: str) -> Preformatted:
    """固定宽度代码块（不折行；调用方保证每行可放进版心）。"""
    return Preformatted(text, STYLES["codef"])


def C(cite: str) -> str:
    """行内出处标注（灰小字）。"""
    return '<font size="8.4" color="#5A6672">（%s）</font>' % esc(cite)


def cell(value, style: str = "cell"):
    if isinstance(value, Paragraph):
        return value
    text = str(value).replace("\r\n", "\n").replace("\n", "<br/>")
    return Paragraph(text, STYLES[style])


def table(headers, rows, widths, mono_cols=(), small_cols=()) -> Table:
    data = [[Paragraph(esc(h), STYLES["th"]) for h in headers]]
    for row in rows:
        out = []
        for i, v in enumerate(row):
            if i in mono_cols:
                out.append(cell(v, "cellm"))
            elif i in small_cols:
                out.append(cell(v, "cells"))
            else:
                out.append(cell(v, "cell"))
        data.append(out)
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E4EBF2")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FB")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA7B4")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 2.6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
    ]))
    return t


# ---------------------------------------------------------------------------
# 页眉 / 页脚 / 页数统计
# ---------------------------------------------------------------------------

class NumberedCanvas(rl_canvas.Canvas):
    """两遍式页码（第 X / Y 页），同时作为总页数计数器。"""

    def __init__(self, *args, **kwargs):
        rl_canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_footer(total)
            rl_canvas.Canvas.showPage(self)
        rl_canvas.Canvas.save(self)
        TOTAL_PAGES["value"] = total

    def _draw_footer(self, total: int) -> None:
        page = self._pageNumber
        if page == 1:  # 封面不排页眉页脚
            return
        self.saveState()
        self.setFont(FONT, 7.6)
        self.setFillColor(colors.HexColor("#5A6672"))
        self.drawString(20 * mm, 11.5 * mm, "TrustBridge 期末报告 · CS5298 · %s" % REPORT_DATE)
        self.setFont(FONT, 8.2)
        self.drawRightString(A4[0] - 20 * mm, 11.5 * mm, "第 %d / %d 页" % (page, total))
        self.setStrokeColor(colors.HexColor("#B8C2CC"))
        self.setLineWidth(0.4)
        self.line(20 * mm, 14.6 * mm, A4[0] - 20 * mm, 14.6 * mm)
        self.restoreState()


def draw_header(canvas: rl_canvas.Canvas, doc) -> None:
    if canvas.getPageNumber() == 1:
        return
    canvas.saveState()
    canvas.setFont(FONT, 7.6)
    canvas.setFillColor(colors.HexColor("#5A6672"))
    canvas.drawString(20 * mm, A4[1] - 12.5 * mm,
                      "TrustBridge — 委员会背书的 A2A 履约信任层")
    canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 12.5 * mm,
                           "CS5298 Final Project · %s" % REPORT_DATE)
    canvas.setStrokeColor(colors.HexColor("#B8C2CC"))
    canvas.setLineWidth(0.4)
    canvas.line(20 * mm, A4[1] - 14.6 * mm, A4[0] - 20 * mm, A4[1] - 14.6 * mm)
    canvas.restoreState()


# ---------------------------------------------------------------------------
# 封面
# ---------------------------------------------------------------------------

def cover() -> list:
    story: list = [Spacer(1, 26 * mm)]
    story.append(P("TrustBridge：委员会背书的<br/>A2A 履约信任层", "title"))
    story.append(Spacer(1, 2 * mm))
    story.append(P("期末报告 · CS5298 Final Project", "subtitle"))
    story.append(HRFlowable(width="72%", thickness=1.0, color=colors.HexColor("#0B3D6B"),
                            spaceBefore=0, spaceAfter=10))

    meta = [
        ["报告日期", "%s" % REPORT_DATE],
        ["仓库状态", "HEAD <font face=\"Courier\">%s</font>（<font face=\"Courier\">git log --oneline -1</font>，"
                     "本轮实跑；零 git 写操作）" % HEAD],
        ["运行环境", "单机 7 容器 devnet（multi-tools / node1–4 / registry / anvil）；"
                     "宿主 Python 3.14.5；容器 cast / forge 1.7.1" + C("implementation.md:28-:31")],
        ["构建链", "reportlab 5.0.1（Platypus；A4；中文字体 Microsoft YaHei）"],
        ["证据约定", "正文每个数字 / 地址 / tx hash / 状态字面值均标注「文件:行」；"
                     "无数据处写「无数据（原因）」"],
    ]
    rows = [[Paragraph(k, STYLES["th"]), Paragraph(v, STYLES["cover_kv"])] for k, v in meta]
    t = Table(rows, colWidths=[30 * mm, 140 * mm])
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#A9B4BF")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF2F7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)

    story.append(Spacer(1, 10 * mm))
    story.append(P("摘要", "h2"))
    story.append(P(
        "TrustBridge 在 Lyquor 网络上实现一个面向 AI Agent 之间交易的信任保障层：两个互不信任的"
        "自主 Agent 在 Lyquor 上完成一笔版权授权交易——资金托管、通信哈希存证、LLM 估时超时、"
        "委员会裁决赔付全部由链上强制执行" + C("计划书:29") + "。核心主张四条" + C("计划书:30") +
        "：<b>①</b> 委员会背书的履约过程可信（对比 ERC-8183 的「客户自选无抵押评估者」）；"
        "<b>②</b> A2A 通信轨迹哈希公证作为中立证据（兼容 x402 #2833 提案格式）；"
        "<b>③</b> LLM 估时驱动强制超时（现有系统 deadline 均为人工常量）；"
        "<b>④</b> 单链集成：UPC 让中介＝委员会＝账本合一。"))
    story.append(P(
        "本报告报告四阶段实验与一项对照：<b>R0</b> 超时退款（链上 Funded→Refunded，全额 1000）；"
        "<b>R1</b> 接线收尾（assess / 角色 / 通道；真实 LLM 被平台 egress 策略拦截、如实登记）；"
        "<b>R2</b> 对抗流三裁决（Malicious / Fulfilled / NotFulfilled）；"
        "<b>R3</b> 四节点委员会认证（判级 <b>L2</b>：inputs=4 + signers=4）与纯 EVM Escrow 四维对照。"
        "§4 列出七项局限（真实 LLM 未接、B3 用户测试未收集、misconduct 无 getter 等），"
        "§5 为 AI 使用声明。"))
    story.append(P(
        "阅读提示：本报告的证据体例沿用项目既有证据档——「文件:行」指向 trustbridge/workflow-out/ "
        "下的原始记录；课程目录素材（方向总结 / 计划书）以「方向总结」「计划书」简称标注。",
        "note"))
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# 第 1 节 问题定义
# ---------------------------------------------------------------------------

def section_problem() -> list:
    story: list = []
    story += H1("第 1 节  问题定义")

    story.append(H2("1.1  一句话定义与核心卖点"))
    story.append(P(
        "在 Lyquor 上实现一个<b>面向 AI Agent 之间交易的信任保障层</b>：Agent 之间照常走现成的通信协议"
        "（Google A2A / MCP），但每一次交易的<b>授权、资金托管、履约存证、结算与超时赔付</b>由链上的 "
        "Lyquid 强制执行——让两个互不信任的自主 Agent 能完成交易" + C("方向总结:11") + "。"))
    story.append(P(
        "<b>核心卖点：中介作为协议，而不是平台。</b>Web2 的中介（淘宝、App Store）本身是需要被信任的"
        "公司；把中介做成 Lyquor 节点 / 委员会后，信任对象从「一家公司」变成「可验证的协议」" +
        C("方向总结:13") + "。"))

    story.append(H2("1.2  课程要求与本报告的对应"))
    story.append(table(
        ["要求项", "课程要求（原文要义）", "本报告对应"],
        [
            ["报告", "正文 ≥6 页（建议 6–10 页），<b>必须含 AI 使用声明</b>，全组须能解释核心流程", "5 节正文 + 证据索引附录 + §5 AI 使用声明"],
            ["提交", "11 月 19 日 12:00 PM：报告 PDF（含公开 GitHub 仓库 URL）+ demo 录像 ZIP", "属课程提交流程，不在本报告范围"],
            ["展示", "Week 12（11 月 19 日）课上 8 分钟展示（5 分钟讲解 + 3 分钟预录 demo）+ 2 分钟问答", "属课堂环节，不在本报告范围"],
            ["环境", "Rust + LDK，Lyquor 本地 devnet，可配合 Ethereum Sepolia 测试网合约", "4 节点 devnet + Anvil；EVM 对照在 Anvil 同链完成"],
        ],
        [20 * mm, 90 * mm, 60 * mm]))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("课程要求出处：方向总结:17-:27。", "note"))

    story.append(H2("1.3  三层定位：本项目做信任层，不做通信层"))
    story.append(table(
        ["层", "管什么", "谁负责", "是否本项目核心"],
        [
            ["通信层", "Agent 发现与消息传递", "复用 Google A2A / MCP（链下）", "否（直接复用）"],
            ["<b>信任层</b>", "承诺凭什么算数：托管、授权、结算、超时赔付", "<b>本项目的 Lyquid + 合约</b>", "<b>是（核心）</b>"],
            ["计算层", "资格审查、任务估时等复杂判断", "LLM 跑在 Lyquid 实例状态 / 私有计算", "是（Lyquor 优势所在）"],
        ],
        [18 * mm, 52 * mm, 60 * mm, 40 * mm]))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("出处：方向总结:69-:77。", "note"))
    story.append(P(
        "类比：淘宝的核心不是聊天工具，而是支付宝担保交易。本项目给 A2A 世界做「担保交易」这一层" +
        C("方向总结:77") + "。"))

    story.append(H2("1.4  示范场景：版权授权市场"))
    story.append(P(
        "视频创作者 Alice（买方）经中介 Agent B（Lyquor 节点）向歌手 Bob（权利方）购买歌曲授权。"
        "场景流程：① 向中介发起报价 → ② 审查 A 资格（LLM）→ ③ 向 C 发起请求 → ④ 接受报价 → "
        "⑤ 资金托管 → 签约（链上）→ ⑥ 授权生效 / 到期 / 超时退款（合约强制）" + C("方向总结:79-:90") + "。"))
    story.append(P(
        "八步用户故事" + C("计划书:50-:59") + "：报价 brief → LLM 资格审查 + 估时 → 向 C 发起请求 → "
        "资金入托管（network state）→ C 接受（签名 PoA，存证）→ C 交付授权书摘要 + 全程消息哈希存证"
        "（链上、按序）→ 委员会（≥3/4 节点）核对证据 vs 验收标准 → 放款（C 收货款 − 中介费）/ "
        "超时全额退款 / 争议裁决赔付。"))
    story.append(P(
        "三条演示流程" + C("计划书:61") + "：<b>正常流</b>（①–⑧ 走通）；<b>超时流</b>（C 未按期交付 → "
        "watcher 提交 → 链上守卫复核 → 全额退款）；<b>对抗流</b>（伪造交付 / 迟到证据 → 委员会否决 → "
        "退款 + 不端记录）。这三条流在 §3 分别由 R1 / R0+R2 / R2 的链上实跑覆盖。"))

    story.append(H2("1.5  问题定义的正确写法"))
    story.append(P(
        "<b>错误写法</b>：「Agent 之间需要一种新的通信机制」——通信链下本来可用，Why Web3 答不上来。"))
    story.append(P(
        "<b>正确写法</b>：「<b>高度自主的 Agent 之间直接交易时，没有可信中央平台做担保——谁保证付了钱"
        "拿到授权？谁保证服务超时会赔付？」</b>" + C("方向总结:99-:103")))
    story.append(P(
        "对应的两条论证：Why Web3——托管与结算必须上链（去信任中介）；Why Lyquor——托管账本 + "
        "委员会背书 + 状态机在同一可编程单元内" + C("计划书:46") + "。"))

    story.append(H2("1.6  竞品与差异化空档"))
    story.append(table(
        ["协议", "阵营", "管哪层"],
        [
            ["ERC-8004", "Ethereum 标准", "Agent 身份 / 信誉"],
            ["x402", "Coinbase（AWS 已采用）", "稳定币机对机微支付轨道"],
            ["AP2", "Google", "授权委托（配合传统支付轨道）"],
            ["A2A / MCP", "Google 等", "通信与工具调用（链下，本项目复用）"],
        ],
        [30 * mm, 55 * mm, 85 * mm]))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("出处：方向总结:106-:119。", "note"))
    story.append(P(
        "<b>本项目的空档：履约过程可信</b>——通信哈希存证、任务估时与超时强制执行、托管结算；"
        "这些恰好是纯以太坊方案（合约只管状态与资产）做不了、需要 Lyquor 复杂链下运算绑定才行的能力" +
        C("方向总结:117") + "。逐篇对比的论证骨架见计划书:102 起（ERC-8183 / Virtuals ACP / "
        "x402 #2833 / Olas Mech / ASP 系 / SoK 2610.01756），本报告不重复展开。"))
    return story


# ---------------------------------------------------------------------------
# 第 2 节 架构
# ---------------------------------------------------------------------------

def component_diagram() -> str:
    """ASCII 组件图：所有框线按同一垂直轴对齐（等宽字体渲染）。"""
    l1 = ("[Alice Agent A] <--A2A/MCP--> [Broker Agent B (Lyquor node)] "
          "<--A2A/MCP--> [Bob Agent C]")
    broker_start = l1.index("[Broker")
    broker_end = l1.index("]", broker_start) + 1
    axis = (broker_start + broker_end) // 2
    inner_w = 40
    left = axis - 1 - inner_w // 2

    def box(lines, note=""):
        out = [" " * left + "+" + "-" * inner_w + "+" + note]
        for t in lines:
            out.append(" " * left + "|" + (" " + t).ljust(inner_w) + "|")
        out.append(" " * left + "+" + "-" * inner_w + "+")
        return out

    v = " " * (left + 1 + inner_w // 2) + "|"
    lines = [l1, " " * axis + "|", v]
    lines += box(["NodeClient (ETH JSON-RPC)", "eth_sendTransaction / eth_call"],
                 "  <- write / read channel")
    lines += [v]
    lines += box(["Lyquid instance (4-node devnet)", "escrow / notary / committee",
                  "certified / assessor / timeout"], "  <- 4-node devnet")
    lines += [v,
              " " * (left + 1 + inner_w // 2) + "node1:10087 .. node4:13087  (anvil chain + registry)",
              " " * (left + 1 + inner_w // 2) + "keeper.py: off-chain polling  (off-chain trigger; on-chain guard)"]
    return "\n".join(lines)


def section_architecture() -> list:
    story: list = []
    story += H1("第 2 节  架构")

    story.append(H2("2.1  分层"))
    story.append(table(
        ["层", "内容", "位置"],
        [
            ["纯核心逻辑", "交易状态机 + 守卫 + 守恒校验（无平台依赖，普通 cargo test 可测）", "lyquid/src/{types,core}.rs"],
            ["链上信任层", "network 状态托管账本 / 证据日志 / 委员会配置；network 函数 = core 的薄封装 + 调用者守卫", "src/lib.rs（escrow / notary / committee 方法）"],
            ["平台侧智能", "instance 函数：LLM 资格审查 + 估时（lyquid-llm），结果经两步模式提交 network", "src/assessor.rs"],
            ["超时执行", "「off-chain trigger; on-chain guard」：instance watcher 扫描到期交易 → 提交退款调用 → network 函数复核守卫", "src/timeout.rs"],
            ["委员会背书", "UPC 三阶段 / oracle propose_and_certify 阈值认证 → apply_committee_verdict", "src/committee.rs（R3 增 committee_certified.rs）"],
            ["Agent 端", "脚本化行为 + 可插拔 LLM（Mock 可回放，保可复现）", "trustbridge/agents/"],
        ],
        [22 * mm, 100 * mm, 48 * mm]))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("出处：计划书:65-:74。R3 新增的认证回调模块见 workflow-out/implementation.md §2.2（:77-:99）。", "note"))

    story.append(H2("2.2  escrow 状态机（按证据写全阶梯）"))
    story.append(code(
        "Qualified -fund-> Funded -submit(deliverable)-> Submitted -complete(buyer|committee)-> Settled (final)\n"
        "                     |\n"
        "                     +-claim_timeout(now >= funded+timeout, only from Funded)-> Refunded (final)\n"
        "                     +-open_dispute-> Disputed -apply_verdict(Fulfilled)-> Settled (final)\n"
        "                                      Disputed -apply_verdict(NotFulfilled|Malicious)-> Refunded (final) + misconduct"
    ))
    story.append(P(
        "上图为计划书:78-:84 状态机的 ASCII 转写；R2 三单的运行时读回阶梯均为 "
        "<font face=\"Courier\">Qualified -&gt; Funded -&gt; Submitted -&gt; Disputed</font>" +
        C("w1b2-r2-adversarial.md:74、:76、:79") + "。"))
    story.append(P("关键规则" + C("计划书:86-:89") + "：", "body"))
    story += bullets([
        "自动退款<b>仅允许从 Funded 态</b>（未提交任何交付证据）——彻底消灭「退款后迟到证据」竞态类；",
        "Submitted 态的资金去向只能经 complete（买方同意）或 Disputed → 委员会裁决；",
        "终态后无任何出边；每次结算满足资金守恒（卖方收款 + 中介费 + 退款 + 罚没 ≡ 托管金额）。",
    ])

    story.append(H2("2.3  oracle 两阶段委员会认证（路线②）"))
    story.append(P(
        "认证链 = propose → aggregate → certified call" + C("implementation.md §2.2，:82-:90") + "。"
        "<b>propose</b> 在 instance 域由各节点从链上证据独立派生裁决（shape 成立 = 0，不成立 = 1），"
        "不是脚本喂值；<b>aggregate</b> 在 UPC 聚合，inputs &lt; avg_num 或提案不一致 → None（拒证），"
        "一致 → CertifiedCallParams{origin: ZERO, method: \"committee_verdict_certified\"}；"
        "<b>认证回调</b>读平台已校验的 ctx.cert.signers（RAW u32），逐节点映射为 NodeID（未映射者剔除、"
        "不猜身份），再经 core::validate_cert 四查（全员 ∈ committee_members + 去重 + |signers| ≥ threshold "
        "+ evidence_root 匹配）落地。这是 <b>cert 门控的资金路径</b>（共享 helper → apply_payout → "
        "credit 真实结算）" + C("implementation.md:89") + "。"))
    story.append(table(
        ["方法", "行", "面 / 属性", "实现要点（implementation.md §2.2 表）"],
        [
            ["e2_configure", ":113", "network(export=eth, eth_guard=creator)", "镜像 probe_configure，落 cert_verdict staging；额外 fail-closed：空委员会 / threshold==0 拒绝"],
            ["e2_arm", ":161", "network(export=eth, eth_guard=creator)", "写 network e2_armed_deal；空串拒绝；println 回显（transcript 佐证）"],
            ["e2_net_config", ":192", "network(export=eth)，只读形 ctx: &_", "JSON dump：armed_deal + current/staging + get_epoch + dest"],
            ["propose", ":239", "instance(group = oracle::two_phase::cert_verdict)", "读 armed_deal + evidence_log + deals；派生 verdict；未 arm / 无 deal / 非 Disputed → Err"],
            ["aggregate", ":289", "instance（同组）", "inputs &lt; avg_num → None；提案不一致 → None（拒证）；一致 → CertifiedCallParams"],
            ["committee_verdict_certified", ":355", "network(group = oracle::certified::cert_verdict::two_phase)", "ctx.cert.signers → NodeID 串 → CommitteeCertWire → apply_cert_and_payout（<b>资金路径</b>）"],
            ["e2_run_verdict_round", ":401", "instance(export = eth)", "propose_and_certify + submit_certified_call；E2_AVG_NUM = 4（编码期常量，:91）"],
        ],
        [41 * mm, 11 * mm, 50 * mm, 68 * mm], small_cols=(0,)))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P(
        "先例：W1-B1 S2 已在 cert_probe 主题上完整跑通 configure（staging）→ advance → finalize → "
        "run_round 的两阶段激活链" + C("w1b1-s2-oracle.md §2–§3") + "；模块 state 声明的先例为 "
        "cert_probe（lib.rs:110）" + C("implementation.md:56") + "。"))

    story.append(H2("2.4  超时执行：keeper 驱动（native trigger 不可用的实证结果）"))
    story.append(P(
        "平台原生 trigger 实测不可用：双节点 arm（status 1×2）后网络计数 delta = 0，"
        "<b>exactly-once 不满足</b>（欠触发 0/2，非 double-fire 形态）" + C("w1b1-s1-timer.md:94") + "；"
        "TriggerMode::Once 与 Recurrent 的 instance trigger 注册成功（无节点侧报错）但调度器从未触发，"
        "四节点日志均无 trigger/fire 活动，判定<b>「native trigger 不可用」</b>" +
        C("w1b1-s1-timer.md:99") + "。"))
    story.append(P(
        "主方案因此转 keeper 模式（不算失败）：链下 keeper 轮询 due_deals → 发 claim_timeout → 链上守卫"
        "复核（仅 Funded 可退、now ≥ deadline）" + C("计划书:72、w1b2-refunded-evidence.md:102-:104") + "。"
        "keeper 的读回复核保证「Refunded 终态再次 claim 被守卫拒绝」被记为 not-due-or-reverted 而非误记 "
        "claimed，重复轮询 / 重试无副作用" + C("w1b2-refunded-evidence.md:100-:104") + "。"))

    story.append(H2("2.5  NodeClient 的 ETH 通道"))
    story.append(P(
        "写通道 = <b>eth_sendTransaction</b>（from 每调用可选；#0 与 #1 双 sender 均实跑成功），"
        "读通道 = <b>eth_call</b>，回执以 eth_getTransactionReceipt 轮询 status==\"0x1\"；"
        "<b>eth_estimateGas 对 lyquid 合约不可用</b>（ServerError(3) execution reverted），"
        "eth_sendTransaction 不带 gas 字段即可、客户端不依赖 estimateGas" +
        C("w1b2-s4-rpc.md:121、:143-:144") + "。"))
    story.append(P(
        "两条平台通道纪律（直接影响实验口径）：① 写方法在 eth_call 上恒返回 FuncNotFound，属通道属性、"
        "<b>不是「未导出」判据</b>，写方法可达性只能由 eth_sendTransaction 侧证明" +
        C("w1b2-r2-adversarial.md:52-:66") + "；② advance / finalize / run_round 的内层提交在 cast send "
        "路径静默丢失，必须走 cast call" + C("w1b1-s2-oracle.md §3、implementation.md:64-:66") + "。"))

    story.append(H2("2.6  组件图与环境"))
    story.append(code(component_diagram()))
    story.append(P(
        "环境事实：单机 7 容器（multi-tools / node1–4 / registry / anvil）全 Up；宿主 Python 3.14.5 / "
        "Git Bash；容器 cast / forge 1.7.1，jq、python3 在位" + C("implementation.md:28-:31") + "。"
        "四节点的 NodeID 与四端口 10087 / 11087 / 12087 / 13087 连通性在 R3-T1 实测 4/4 通" +
        C("w1b2-r3-e2-committee.md:13") + "。"))
    return story


# ---------------------------------------------------------------------------
# 第 3 节 实验结果
# ---------------------------------------------------------------------------

def section_experiments() -> list:
    story: list = []
    story += H1("第 3 节  实验结果：四阶段 + R2/R3 详情 + EVM 对照")

    story.append(KeepTogether([
        P("四个实验阶段严格串行推进：R0 先证「超时退款」在真实链上成立，R1 把正常流接进 node 通道，"
          "R2 打通对抗流与链上裁决，R3 完成四节点委员会认证并做纯 EVM 对照。每个阶段的数据均在"
          "独立实例上采集，实例之间不合并、不互相替代。"),
        Spacer(1, 1.2 * mm),
        table(
        ["阶段", "目标", "代表实例 / 合约", "结论（一句话）", "证据档"],
        [
            ["R0", "超时退款实测", "Lyquid-xydh5… @ 0xA4899D…776", "Funded→Refunded，全额退款 1000，余额 +1000", "w1b2-refunded-evidence.md"],
            ["R1", "接线收尾（assess / 角色 / 通道）", "Lyquid-5h2kj… @ 0x40918B…849", "正常流 Settled（9000 / 980 / 20）；真实 LLM 被 egress 拒绝（如实登记）", "w1b2-r1-s3-assess.md；w1b2-r1-demo-normal.md"],
            ["R2", "对抗流三裁决 + 超时流", "Lyquid-tldda6… @ 0xFD6F7A…351", "Malicious→Refunded（misconduct +1）；Fulfilled→Settled（bob +980 / broker +20）；NotFulfilled→Refunded（计数不增）", "w1b2-r2-adversarial.md"],
            ["R3", "四节点委员会认证（E2）", "Lyquid-ybidj… @ 0x87006e…589", "判级 L2：inputs=4 + signers=4；deal-1 Refunded（全额退款）", "w1b2-r3-e2-committee.md"],
            ["对照", "纯 EVM Escrow 四维对照", "0x976C2147…D903（Anvil 同链）", "创建 gas 1,936,008 vs Lyquid 3,843,041 / 3,707,457；代码量、信任假设、篡改面、开销四维并列", "r3-t4-contrast-report.md"],
        ],
        [11 * mm, 30 * mm, 34 * mm, 47 * mm, 48 * mm], small_cols=(4,)),
    ]))

    # ---------------- R0 ----------------
    story.append(H2("3.1  R0：超时退款实测（Funded → Refunded）"))
    story.append(P(
        "R0 在实例 Lyquid-xydh5ecomgg2rukd7qbw6gjv7cuf4uiktzbaa @ 0xA4899D35897033b927acFCf422bc745916139776 上"
        "构造 deal-1（amount 1000，timeout_slots 1），由 keeper 一轮触发 claim_timeout" +
        C("w1b2-refunded-evidence.md:4、:51-:54") + "。"))
    story.append(table(
        ["数据点", "值（原始字面）", "出处"],
        [
            ["退款交易 hash", "见下方原文行（keeper 输出与回执 txHash 同值）", "w1b2-refunded-evidence.md:14（keeper 输出）、:24（回执 txHash）"],
            ["回执", "status 0x1 / block 104 / from 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266（= anvil#0 = BROKER）/ gasUsed 35996", "w1b2-refunded-evidence.md:20-:25"],
            ["deal_info 字面", "退款前 <font face=\"Courier\">\"state\": \"Funded\"</font> → 退款后 <font face=\"Courier\">\"state\": \"Refunded\"</font>；amount 1000；timeout_slots 1；deadline_slot 102", "w1b2-refunded-evidence.md:37（后）、:43（前）"],
            ["余额勾稽", "999002（block 103）→ 1000002（block 104），+1000 = full_refund；fee_bps 不参与退款", "w1b2-refunded-evidence.md:51-:54"],
            ["边界语义", "claim 发生于 block 104；104 ≥ 102，满足 now ≥ deadline 的边界语义（core.rs claim_timeout）", "w1b2-refunded-evidence.md:46-:47"],
            ["判读纪律", "status=0x1 仅代表<b>已上序</b>（平台吞方法 Err）；成功判定以 deal_info / balance_of 读回为准", "w1b2-refunded-evidence.md:28-:30"],
        ],
        [22 * mm, 100 * mm, 48 * mm], small_cols=(2,)))
    story.append(code(
        "refund tx = 0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838"
    ))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("这条「status ≠ effect」纪律贯穿本报告全部实验结果，§3.4 与 §3.5 各有一例活证。", "note"))

    # ---------------- R1 ----------------
    story.append(H2("3.2  R1：接线收尾（assess → escrow → deliver → settle）"))
    story.append(P(
        "R1 把正常流接进 node 通道，并如实登记真实 LLM 通道的阻塞原因。"))
    story.append(table(
        ["数据点", "值（原始字面）", "出处"],
        [
            ["assess_brief 签名", "7×string → 4×string（brief_json + base_url / api_key / model）；原因：7×string instance 桩触发 solc <b>Stack too deep</b>，6×string 通过、4 参留余量（S3-1 持久登记）", "w1b2-r1-s3-assess.md:184、:11"],
            ["selector", "<font face=\"Courier\">cast sig \"assess_brief(string,string,string,string)\"</font> → <b>0x3297eeb6</b>，已冻结进 rpc.py 的 _ABI 表", "w1b2-r1-s3-assess.md:78-:79、:86-:87"],
            ["heuristic 定值", "75 / [\"heuristic-mode\"] / 60000 / 40，与 assessor.rs:89 逐字一致", "w1b2-r1-s3-assess.md:83-:86"],
            ["正常流终态", "state=Settled；balances: alice=9000 bob=980 broker=20；守恒 9000 + 980 + 20 = 10000（faucet 总量）", "w1b2-r1-demo-normal.md:29、:79"],
            ["真实 LLM 通道", "平台 egress 策略拒绝私网 / 内部地址（原文：blocked private/internal address <font face=\"Courier\">172.18.0.2</font>）；宿主无 TB_LLM_* 凭据，未做真实凭据复跑（合法路径）", "w1b2-r1-s3-assess.md:151、:161-:163"],
        ],
        [22 * mm, 98 * mm, 50 * mm], small_cols=(2,)))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P(
        "角色密钥表与 nudge / discover / assess 封装在 R1 S4 落地（git 提交 f36d24e：role key table + "
        "wrappers；通道细节见 w1b2-s4-rpc.md §B）。口径提醒：上表 9000 / 980 / 20 三数只出现在 R1 正常流"
        "运行的记录中" + C("w1b2-r1-demo-normal.md:29、:79") + "；R2 对抗流档内没有这组三元组，"
        "本报告按运行分列、不合并标注。"))

    # ---------------- R2 ----------------
    story.append(H2("3.3  R2：对抗流三裁决与链上结算"))
    story.append(P(
        "R2 在实例 Lyquid-tldda6zqdhab2kdysepcqxx73uvm3sxz7wbaa @ 0xFD6F7A6a5c21A3f503EBaE7a473639974379c351 上"
        "以一次 --flow adversarial 运行完成三裁决" + C("w1b2-r2-adversarial.md:3-:4、:68-:82") + "。"))
    story.append(table(
        ["场景（verdict 码）", "终态", "买方回流（alice）", "卖方 / 经纪人", "不端<br/>计数", "出处"],
        [
            ["Malicious（伪造交付，deal-6，verdict=2）", "Refunded", "48000 → 49000（+1_000）", "0 / 0（不变）", "<b>+1</b>（1→2）", "w1b2-r2-adversarial.md:86-:90、:102-:105"],
            ["Fulfilled（合规交付，deal-7，verdict=0）", "Settled", "48000 → 48000（<b>0</b>，Payout::settle 的 refund_to_buyer=0）", "bob +980 / broker +20", "不变", "同上"],
            ["NotFulfilled（伪造交付，deal-8，verdict=1）", "Refunded", "47000 → 48000（+1_000）", "980 / 20（不变）", "<b>不变</b>", "同上"],
        ],
        [31 * mm, 17 * mm, 36 * mm, 24 * mm, 19 * mm, 43 * mm], small_cols=(5,)))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P(
        "分账公式：<font face=\"Courier\">fee = 1_000 × 200 / 10_000 = 20</font>，与 "
        "<font face=\"Courier\">bob +980 / broker +20</font> 勾稽" + C("w1b2-r2-adversarial.md:93-:94") +
        "。三单状态阶梯均含 Disputed 读回（open_dispute 生效的直接证据；每步经 5×0.4s 读回重试，"
        "避免读到上一块旧态）" + C("w1b2-r2-adversarial.md:92-:93") + "。"))
    story.append(P(
        "misconduct 取证（console 累计视图，原文四行；依次为 deal-5 / deal-6 两次 Malicious 尝试"
        "与 deal-7 Fulfilled、deal-8 NotFulfilled，计数 1→2→2→2）" +
        C("w1b2-r2-adversarial.md:102-:105") + "："))
    story.append(code(
        "apply_verdict: deal=deal-5 verdict=2 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=1]\n"
        "apply_verdict: deal=deal-6 verdict=2 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=2]\n"
        "apply_verdict: deal=deal-7 verdict=0 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=2]\n"
        "apply_verdict: deal=deal-8 verdict=1 misconduct=[0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC=2]"
    ))
    story.append(P(
        "NotFulfilled 的证据不是「无行」，而是每行都打、计数不增（deal-8 行与 deal-7 行同值 2）；"
        "misconduct 无 getter（方法清单冻结），println 是既有观测缝（先例 fund:deal_view、deal_info），"
        "属累计视图、非共识状态、语义零影响" + C("w1b2-r2-adversarial.md:106-:111") + "。"))
    story.append(P(
        "<b>编码器缺陷（首跑暴露并修复）</b>：attempt 1 中 apply_committee_verdict 交易 status 0x1 但 deal-4 "
        "停留 Disputed（平台吞 Err）。定位到 rpc.py 的 _enc_value(\"string[]\") 把长度字也算进 head_size，"
        "元素偏移比标准多 0x20，链上解出的 signers / members 为垃圾串 → 成员 / 签名守卫拒绝；修复后与 "
        "cast calldata 逐字节 MATCH" + C("w1b2-r2-adversarial.md:113-:135") + "。"))
    story.append(P(
        "实例终态守恒：balances alice=77000 bob=3920 broker=80（sum=81000）；总注资 81_000，"
        "托管 14 × 1_000、回流 10 × 1_000 ⇒ 81_000 − 14_000 + 10_000 = 77_000，"
        "且 77_000 + 3_920 + 80 = 81_000" + C("w1b2-r2-adversarial.md:146-:157") + "。"))
    story.append(P(
        "<b>--flow all 集成连跑</b>（门控拆除验证）：FLOW 1 normal → deal-10 state=Settled "
        "balances alice=67000 bob=2940 broker=60；FLOW 2 timeout → deal-11 deadline_slot=288，"
        "nudge 287→288→289，due=['deal-11']，Refunded；FLOW 3 adversarial → deal-12 Refunded / "
        "deal-13 Settled / deal-14 Refunded，DEMO_EXIT=0" + C("w1b2-r2-adversarial.md:159-:172") + "。"))

    # ---------------- R3 ----------------
    story.append(H2("3.4  R3：四节点委员会认证（E2），判级 L2"))
    story.append(P(
        "R3 在<b>新实例</b> Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa @ "
        "0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589 上完成「4 提案 + 4 签」的委员会认证" +
        C("w1b2-r3-e2-committee.md:42") + "。"))
    story.append(table(
        ["判据 / 数据点", "原文行", "出处"],
        [
            ["inputs=4", "<font face=\"Courier\">e2_aggregate: agreed deal=deal-1 verdict=1 from 4 input(s) (avg_num=4)</font>（console :24；四个不同 Node-… 输入行 :20-:23）", "w1b2-r3-e2-committee.md:71"],
            ["signers=4", "<font face=\"Courier\">committee_verdict_certified: cert.signers RAW = [0, 1, 2, 3] (Vec&lt;SignerID&gt;=Vec&lt;u32&gt;, len=4) deal=deal-1 verdict=1</font>（console :31）", "w1b2-r3-e2-committee.md:73"],
            ["四条互异映射", "signer 0..3 → 四个互不相同的 Node-… ID（console :32-:35），且与当轮 GetNodeInfo 喂给 e2_configure 的成员集逐字一致", "w1b2-r3-e2-committee.md:82-:85"],
            ["单次纪律", "e2_arm 一次 + 读回断言（arm read-back OK: armed_deal == deal-1 (pre-arm='')）；e2_run_verdict_round 单次（cast call）；认证回调 / apply_verdict 各一次", "w1b2-r3-e2-committee.md:95-:97、:87-:89"],
            ["退款守恒", "alice 10000 → 9000（fund −1000）→ 10000（退款 +1000）；bob / broker 恒 0；链上扫描 blocks 0–341 仅 1 笔 faucet（block 333，amount=10000）", "w1b2-r3-e2-committee.md:98"],
            ["两段 agreed 注记", "aggregate 出现两次 agreed（console :24 与 :29，同一 4 输入集的重复回放），但 certified call submitted / committee_verdict_certified / apply_verdict 各仅一次 → <b>无重复结算</b>", "w1b2-r3-e2-committee.md:87-:89"],
            ["D-T3-1 缺陷", "demo 内建余额断言 stale baseline（faucet 后立即快照）→ RuntimeError；链上资金语义正确（T3.5 独立读回 + 链上扫描证明），非链上失配", "w1b2-r3-e2-committee.md:106-:121"],
            ["T7 修复复验", "新实例 Lyquid-dpp6ird6knahaun6dokpi6ki2pdnbjxdfunqa（0x942ED2fa862887Dc698682cc6a86355324F0f01e）：committee 流 exit 0、DEMO COMPLETE；faucet read-back OK（:22）、refund check OK（:31）；L2 判级复现（:44 / :51）", "w1b2-r3-e2-committee.md §T7 :164-:179；_r3-t7-dt31-verify-raw.txt:22、:31、:44、:51、:69、:72-:73"],
        ],
        [24 * mm, 100 * mm, 46 * mm], small_cols=(2,)))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P(
        "<b>判级口径</b>（三层定义）" + C("docs/b3-user-test/通过判据.md:23-:36") + "："
        "<b>L2</b>（目标形态）= 4 提案（inputs=4）+ 4 签（signers=4）；<b>L1</b>（可接受的四节点签署）= "
        "1 提案 + 4 签；<b>L0</b>（平台硬限制）= threshold&gt;1 时 certify 无法聚齐，仅能单签送达。"
        "诚实红线：绝不把「单签」写成「四节点认证」、绝不把 L1 写成 L2；判级结论必须能由 console 原文行"
        "直接读出。本轮判级 = L2，L1 / L0 均未触发（E2_AVG_NUM 保持 4，未改 lyquid 码、未重部署）" +
        C("w1b2-r3-e2-committee.md:47-:59") + "。"))

    # ---------------- EVM ----------------
    story.append(H2("3.5  EVM 对照：同一托管守卫的纯 Solidity 版本"))
    story.append(P(
        "对照实验把同一托管守卫用 Solidity 在 Anvil 上重写（experiments/evm-contrast/Escrow.sol，407 行），"
        "四维对比：代码量、信任假设、裁决不可篡改性、开销。口径约定：EVM 数据来自本轮 run-3；Lyquid 数据"
        "来自 R2 与 R3 两个不同实例，两实例不合并、不互相替代" + C("r3-t4-contrast-report.md §0、:10") + "。"))
    story.append(table(
        ["维度", "结果", "出处"],
        [
            ["创建 gas（同链、同 anvil#0 签名、同 to=null 形态）", "<b>EVM 1,936,008</b> / Lyquid R3 <b>3,843,041</b> / Lyquid R2 <b>3,707,457</b>", "r3-t4-contrast-report.md:180-:187"],
            ["代码量（wc -l，含空行与注释）", "Escrow.sol <b>407</b>；Lyquid 合约六文件 <b>2083</b>（含测）/ <b>1323</b>（去测）；含 lib.rs 为 <b>2933</b> / <b>2173</b>", "r3-t4-contrast-report.md:60-:83"],
            ["信任假设", "EVM：合约内<b>地址表</b>（deployer 可覆盖，Escrow.sol:81-83 / :108），本轮 4 成员、threshold=3，且<b>成员包含买卖双方本人</b>；Lyquid：平台注册的 4 个 NodeID、threshold=4，认证回调读平台已校验的 cert.signers", "r3-t4-contrast-report.md:85-:97"],
            ["两条路径强度", "eth 直调 apply_committee_verdict 只做地址门、<b>不验签名</b>（lib.rs:222 自述 TODO(W4)）；与认证回调路径并列给出、不合并", "r3-t4-contrast-report.md:93、:97"],
            ["负对照（重放防护）", "deal-3 三签重放 deal-4 被拒：rc=1，revert 原因 <font face=\"Courier\">non-member signer</font>，deal-4 读回仍 Disputed", "r3-t4-contrast-report.md:104、:232"],
            ["EVM 三流终态读回", "deal-1 Settled(5) / deal-2 Refunded(6) / deal-3 Refunded(6) / deal-4 Disputed(4)", "r3-t4-contrast-report.md:105、:229-:232"],
            ["单笔操作 gas", "EVM createDeal 226,658 / 209,558、notarize 138,072、openDispute 53,162、applyVerdict 93,534 均高于 Lyquid 对应方法（create_deal 47,908 / notarize 44,193 / open_dispute 38,883 / apply_committee_verdict 43,073）；<b>fund 反而 EVM 更低</b>（32,713 vs 36,014）", "r3-t4-contrast-report.md:251"],
        ],
        [32 * mm, 98 * mm, 40 * mm], small_cols=(2,)))
    story.append(Spacer(1, 1.5 * mm))
    story.append(P("六条结论（如实）" + C("r3-t4-contrast-report.md:246-:253") + "："))
    story += bullets([
        "EVM escrow <b>没有多节点委员会认证</b>：其「委员会」是合约内一张 deployer 可随时覆盖配置的地址表，k-of-n 由合约自己 ecrecover 自证，本轮该地址表还包含买卖双方本人。",
        "EVM 侧的可篡改性防护真实生效但范围有限：负对照实证「同一签名集不能跨 deal 复用」（签名绑定 dealId、裁决码与证据根），但该防护不约束「谁有资格被写进委员会」。",
        "Lyquid 的四节点认证是额外的信任层，代价可量化：部署 gas 更高（3,843,041 vs 1,936,008，约 1.98×；R2 为 3,707,457）、认证回合需要额外汇总消息，且强依赖平台通道的可用性与语义（R2 已暴露 status 0x1 但方法未生效的失败模式）。",
        "单笔操作的 gas 对比<b>没有单向结论</b>：EVM 部分操作更高、fund 反而更低；两侧结算单位与业务流内容不同，不做单一「谁更便宜」的总量结论。",
        "代码量对比必须带口径：407 行 vs 2083/1323（含/去测试）或 2933/2173（含 lib.rs）；两侧测试策略不同，行数差不能直接读成「复杂度差」。",
        "共同前提：两侧都跑在同一个 anvil 链上，EVM 实验的 evm_increaseTime 会推进共享时间源；本轮 Lyquid 侧只读，未做依赖未来 slot 的操作。",
    ])
    story.append(P(
        "<b>数据缺口（如实列出）</b>" + C("r3-t4-contrast-report.md:212-:221") + "： Lyquid 侧跨单签名"
        "重放实验<b>无数据</b>（本轮未做，仅有 core::validate_cert 的 evidence_root 校验代码路径）；"
        "两侧相同工作量的端到端 gas 对比<b>无数据</b>（业务流内容与结算单位不同）；三个平台 selector 的"
        "方法名<b>未识别</b>（仓库源码与既有 selector 表均无对应，不猜名）。"))
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# 第 4 节 信任假设与局限
# ---------------------------------------------------------------------------

def section_limits() -> list:
    story: list = []
    story += H1("第 4 节  信任假设与局限：诚实清单")
    story.append(P(
        "本节逐条列出本系统当前<b>不成立或未验证</b>的信任假设。每条都给出档内出处；"
        "没有数据的地方写「无数据」及原因，不外推。"))
    story.append(table(
        ["#", "局限 / 信任假设", "现状与依据"],
        [
            ["1", "oracle 路线② 多节点认证 vs R2 单点签署", "R3 的多节点认证（平台注册 NodeID + threshold=4 + validate_cert 四查）与 R2 的地址制委员会是两条强度不同的路径：eth 直调 apply_committee_verdict 只做地址门、不验签名（lib.rs:222 自述 TODO(W4)）。两条路径并列给出、不合并（r3-t4-contrast-report.md:93、:97）。"],
            ["2", "真实 LLM 未接", "平台 egress 策略拒绝私网 / 内部地址（原文：blocked private/internal address 172.18.0.2），宿主无 TB_LLM_* 凭据；当前形态 = heuristic 回放模式（75 / [\"heuristic-mode\"] / 60000 / 40）（w1b2-r1-s3-assess.md §3.4、:151、:161-:163；implementation.md §6-#9，:407）。"],
            ["3", "misconduct 无 getter", "只能经 println 观测缝读取（累计视图），属节点本地打印、非共识状态、语义零影响（r3-t4-contrast-report.md:107）。"],
            ["4", "B3 用户测试待线下", "反馈收集表为<b>空白表单</b>、无已收集反馈；四维表单已就绪（任务理解 / 操作顺畅度 / 结果可信度 / 开放意见）（docs/b3-user-test/反馈收集表.md；implementation.md §9.1-#6，:603）。"],
            ["5", "对抗流 node 复跑仍未执行", "R3-T6 授权面遗留项，代码已具备、未再跑（implementation.md §7.5-#2，:511）。"],
            ["6", "EVM 对照的口径限制", "两个 Lyquid 实例不合并；时间域差异（block.timestamp vs slot）；Lyquid 跨单重放无数据、仅有代码路径；单笔 gas 不做总量结论（r3-t4-contrast-report.md §0、:212-:221、:251）。"],
            ["7", "devnet 是单机 7 容器", "非真实分布式部署；E2 加分项不主张（implementation.md:28）。"],
        ],
        [9 * mm, 44 * mm, 117 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(P(
        "与此对应，本报告<b>不主张</b>以下结论：不把「代码里有校验」写成「已实测」（Lyquid 跨单重放）；"
        "不把单签写成四节点认证（R3 判级只有 L2 一条口径）；不把 B3 写成已完成（无已收集反馈）；"
        "不把 devnet 单机部署写成 E2 真实分布式。", "note"))
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# 第 5 节 AI 使用声明
# ---------------------------------------------------------------------------

def section_ai() -> list:
    story: list = []
    story += H1("第 5 节  AI 使用声明")
    story.append(P(
        "本项目采用多模型协作工作流完成方案撰写、编码、审查与仲裁；人工作者负责阶段决策、提交确认与"
        "终裁记录复核。分工如下（模型与职责按实际运行记录填写）："))
    story.append(table(
        ["角色", "模型", "职责"],
        [
            ["规划师", "GLM-5.3", "方案撰写与终裁"],
            ["编码员", "deepseek-flash", "编码实现与逐轮自审"],
            ["审查员", "deepseek-flash（原生子代理）", "方案与代码逐轮审查"],
            ["仲裁人", "GLM-5.3-Flash", "审查意见逐条处置与总结"],
            ["终裁官", "GLM-5.3（冷上下文）", "轮数耗尽时裁定"],
            ["<b>人工（作者）</b>", "—", "<b>阶段决策、提交确认、终裁记录复核</b>"],
        ],
        [30 * mm, 58 * mm, 82 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(P(
        "<b>佐证材料</b>：workflow-out/_collab/ 目录保留多模型协作痕迹（planner_sys.txt、"
        "planner_user.txt、llm_call.py、probe_bigmodel.txt、probe_deepseek.txt 等）；"
        "implementation.md 各轮「仲裁修订登记」段落（:347-:361、:663-:696）与「终裁条款」引用（:3-:4）"
        "记录了审查意见的逐条处置过程。"))
    story.append(P("<b>人工决策节点（有档可查）</b>："))
    story.append(table(
        ["#", "决策", "记录"],
        [
            ["1", "阶段重排：W1-B2 中止，改 R0–R4 重排", "git 提交 136dc23（docs: phase rearrangement plan — W1-B2 run abandoned, R0-R4 schedule with preserved review findings）；FinalProject_阶段重排_2026-10-27.md §1 / §4"],
            ["2", "提交确认：R1–R3 全部提交经人工确认落地", "implementation.md §10-1（「主控按用户指令落地」）；git acb7315…3af0460 + d292012 + 8d093b5（本轮实跑 git log --oneline -25 在案）"],
            ["3", "T7 授权：D-T3-1 修复端到端复验经用户授权「继续 R3」", "w1b2-r3-e2-committee.md §T7 头注；implementation.md §10-2"],
            ["4", "每阶段任务拆分与开工确认：R1/R2/R3 由用户明确指令启动", "FinalProject_阶段重排_2026-10-27.md §4「启动规则」；本报告撰写任务为六阶段拆分④（workflow-out/plan.md:3）"],
        ],
        [8 * mm, 58 * mm, 104 * mm], small_cols=(2,)))
    story.append(Spacer(1, 2 * mm))
    story.append(P(
        "<b>如实边界</b>：本报告与全部实验证据的代码、脚本、文档、证据档均由上述 AI 角色在人工发起的"
        "分阶段任务中产出；人工作者承担阶段决策、提交确认与终裁记录复核，未逐行改写报告。"
        "报告中所有数字均可在 §3 与附录 A 索引所指文件的行内逐字复核；凡无数据处已标注「无数据（原因）」。"))
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# 附录
# ---------------------------------------------------------------------------

def section_appendix(total_pages: int | None) -> list:
    story: list = []
    story += H1("附录 A  证据索引（浓缩）")
    story.append(P(
        "下表为正文数据的浓缩索引，供评阅溯源；完整映射见 workflow-out/plan.md §2 与各证据档原文。"
        "「:行」均指 trustbridge/workflow-out/ 下的文件（课程目录素材另注）。"))
    story.append(table(
        ["数据点", "值", "出处"],
        [
            ["R0 退款交易", "0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838", "w1b2-refunded-evidence.md:14、:24"],
            ["R0 回执 / 余额勾稽", "status 0x1 / block 104 / gasUsed 35996；999002 → 1000002（+1000）", "w1b2-refunded-evidence.md:20-:25、:51-:54"],
            ["R1 正常流终态", "Settled；alice=9000 bob=980 broker=20；9000+980+20=10000", "w1b2-r1-demo-normal.md:29、:79"],
            ["R1 assess_brief selector", "0x3297eeb6（4×string）", "w1b2-r1-s3-assess.md:78-:79"],
            ["R2 三裁决", "Malicious→Refunded（misconduct 1→2）/ Fulfilled→Settled（bob +980、broker +20）/ NotFulfilled→Refunded（计数不增）", "w1b2-r2-adversarial.md:86-:90、:102-:105"],
            ["R2 实例守恒", "alice=77000 bob=3920 broker=80（sum=81000）", "w1b2-r2-adversarial.md:146-:157"],
            ["R3 判级 L2", "agreed … from 4 input(s) (avg_num=4)；cert.signers RAW = [0, 1, 2, 3] (len=4)", "w1b2-r3-e2-committee.md:71、:73；_r3-t3-console-raw.txt:24、:31"],
            ["R3 实例 / 合约", "Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa @ 0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589", "w1b2-r3-e2-committee.md:42"],
            ["R3 退款守恒", "alice 10000 → 9000（fund −1000）→ 10000（退款 +1000）；bob/broker 恒 0", "w1b2-r3-e2-committee.md:98"],
            ["EVM 创建 gas 三值", "1,936,008 / 3,843,041 / 3,707,457", "r3-t4-contrast-report.md:180-:187"],
            ["代码量", "407 / 2083（1323）/ 2933（2173）", "r3-t4-contrast-report.md:60-:83"],
            ["负对照", "deal-3 三签重放 deal-4：rc=1，non-member signer", "r3-t4-contrast-report.md:104、:232"],
        ],
        [30 * mm, 92 * mm, 48 * mm], small_cols=(2,)))

    story.append(H2("附录 B  构建信息"))
    pages_text = ("总页数 <b>%d</b> 页" % total_pages) if total_pages else "总页数（见构建输出 TOTAL_PAGES）"
    story.append(P(
        "构建工具：<b>reportlab 5.0.1</b>（Platypus；A4；中文字体 %s）。构建命令："
        "<font face=\"Courier\">python workflow-out/report/build_report.py</font>。"
        "构建日期：%s。%s。构建脚本为报告唯一源文件（全文以本脚本内的数据结构内嵌）；"
        "复现命令、验证输出与证据索引见 <font face=\"Courier\">workflow-out/report/README.md</font>。"
        % (FONT_USED["family"] or "MSYH", REPORT_DATE, pages_text)))
    return story


# ---------------------------------------------------------------------------
# 构建
# ---------------------------------------------------------------------------

def build_story(total_pages: int | None) -> list:
    story: list = []
    story += cover()
    story += section_problem()
    story += section_architecture()
    story += section_experiments()
    story += section_limits()
    story += section_ai()
    story += section_appendix(total_pages)
    return story


def build_pdf(path: str, total_pages: int | None) -> int:
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="TrustBridge：委员会背书的 A2A 履约信任层——期末报告",
        author="CS5298 Final Project (TrustBridge)",
        subject="CS5298 Final Project Report",
        creator="reportlab 5.0.1 / build_report.py",
    )
    doc.build(build_story(total_pages), onFirstPage=draw_header, onLaterPages=draw_header,
              canvasmaker=NumberedCanvas)
    TOTAL_PAGES["doc"] = doc.page
    return TOTAL_PAGES["value"]


def main() -> int:
    register_fonts()
    init_styles()

    tmp = os.path.join(tempfile.gettempdir(), "trustbridge-report-pass1.pdf")
    n1 = build_pdf(tmp, None)
    n2 = build_pdf(OUT_PDF, n1)
    if n2 != n1:
        n1, n2 = n2, build_pdf(OUT_PDF, n2)
    if os.path.exists(tmp):
        os.remove(tmp)

    size = os.path.getsize(OUT_PDF)
    print("FONT_FILE=%s" % FONT_USED["file"])
    print("FONT_FAMILY=%s" % FONT_USED["family"])
    print("OUTPUT=%s" % OUT_PDF)
    print("SIZE_BYTES=%d" % size)
    print("TOTAL_PAGES=%d" % n1)
    print("DOC_PAGE=%d" % TOTAL_PAGES["doc"])
    print("BUILD_OK" if n1 >= 6 and size > 0 else "BUILD_WARN pages<6 or size==0")
    return 0 if (n1 >= 6 and size > 0 and n1 == n2) else 1


if __name__ == "__main__":
    sys.exit(main())
