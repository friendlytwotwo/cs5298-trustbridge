# TrustBridge 期末报告 — 构建说明 / 证据索引 / 开工基线

> 方案：`workflow-out/plan.md`（R4-D1，终裁官定稿，2026-10-30）。
> 本文件为方案 §0 清单 #6：构建说明 + 证据索引 + 逐字复现命令 + 开工基线存证。
> 交付产物：`trustbridge-final-report.pdf`（A4，**12 页**，中文），源文件 `build_report.py`。

| 文件 | 说明 |
|---|---|
| `build_report.py` | 报告**唯一源文件**：全文（封面 + 5 节 + 附录）以 Python 数据结构内嵌；reportlab Platypus 构建 |
| `trustbridge-final-report.pdf` | 构建产物：A4，12 页，中文，MSYH 子集嵌入；md5 `18c90f03c89d622b1eece0024ff25385` |
| `README.md` | 本文件（构建 / 验证 / 复现 / 证据索引 / 开工基线） |

---

## 1. 环境与依赖

| 项 | 实测值 | 取得方式 |
|---|---|---|
| 宿主 | Windows（win32 10.0.26300）+ Git Bash | 本轮执行环境 |
| Python | 3.14.5 | `python --version` |
| reportlab | **5.0.1** | `python -c "import reportlab; print(reportlab.Version)"` |
| 中文字体 | `C:\Windows\Fonts\msyh.ttc`（Microsoft YaHei；注册名 `TB-CJK`，粗体 `msyhbd.ttc`） | 构建输出 `FONT_FILE=` / `FONT_FAMILY=` |
| 页数复核 | pypdf 6.19.0 | `python -c "import pypdf; print(pypdf.__version__)"` |
| 目视复核 | PyMuPDF 1.28.2（仅验证用，不参与构建） | `import pymupdf` |

不可用的工具（如实登记）：**pandoc / xelatex / pdflatex** —— 规划期 `where` 查询均失败，故主路径为 reportlab（方案 §4）。

---

## 2. 构建（逐字）

```bash
cd trustbridge
python workflow-out/report/build_report.py
```

本轮实跑输出（逐字，2026-10-30）：

```
FONT_FILE=C:\Windows\Fonts\msyh.ttc
FONT_FAMILY=Microsoft YaHei
OUTPUT=F:\canvus auto\downloads\202609CS5298\trustbridge\workflow-out\report\trustbridge-final-report.pdf
SIZE_BYTES=478929
TOTAL_PAGES=12
DOC_PAGE=12
BUILD_OK
```

- `TOTAL_PAGES` 来自脚本内 `NumberedCanvas`（`showPage` 收集页状态、`save` 时逐页画「第 X / Y 页」并回填总数）——即方案 §4「主：脚本内 onPage/canvasmaker 回调计数」。
- 脚本为两遍构建：第一遍到临时文件统计页数，第二遍把「总页数 12 页」写进附录 B 的构建信息，然后输出最终 PDF。
- 退出码 `EXIT=0`（页数 ≥6 且文件非空且两遍页数一致时才返回 0）。

---

## 3. 验证（逐字命令 + 实跑输出）

**(a) 页数与纸张（pypdf 独立复核，方案 §4「复核」路径）**

```bash
python -c "import pypdf; P='workflow-out/report/trustbridge-final-report.pdf'; r=pypdf.PdfReader(P); print('PAGES=%d'%len(r.pages)); print('A4_ALL=%s'%all(abs(float(p.mediabox.width)-595.276)<1.0 and abs(float(p.mediabox.height)-841.89)<1.0 for p in r.pages))"
```

```
PAGES=12
A4_ALL=True
```

**(b) 正文关键字面值抽查（27 项，提取全文比对）**

```bash
python -c "import pypdf; t=''.join(p.extract_text() or '' for p in pypdf.PdfReader('workflow-out/report/trustbridge-final-report.pdf').pages); keys=['0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838','3,843,041','3,707,457','1,936,008','0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589','0x942ED2fa862887Dc698682cc6a86355324F0f01e','0xFD6F7A6a5c21A3f503EBaE7a473639974379c351','0x3297eeb6','non-member signer','misconduct','inputs=4','signers=4','1000002','999002','77000','3920','81000','407','2083','1323','2933','2173','980','8d093b5','2026-10-30','无数据（原因）','第 5 节']; miss=[k for k in keys if k not in t]; print('KEY_HITS=%d/%d'%(len(keys)-len(miss),len(keys))); print('MISSING=%s'%miss)"
```

```
KEY_HITS=27/27
MISSING=[]
```

**(c) 字体覆盖（无缺字方块的程序化佐证）**

```bash
python -c "import pypdf; from fontTools.ttLib import TTCollection; r=pypdf.PdfReader('workflow-out/report/trustbridge-final-report.pdf'); txt=''.join((p.extract_text() or '') for p in r.pages); chars=set(txt)-set('\n\r\t '); tc=TTCollection(r'C:\Windows\Fonts\msyh.ttc'); cmap=set(); [cmap.update(t.cmap.keys()) for f in tc.fonts for t in f['cmap'].tables]; missing=sorted(c for c in chars if ord(c) not in cmap); print('UNIQUE_CHARS=%d'%len(chars)); print('MISSING_IN_MSYH=%d'%len(missing)); print('MISSING_SAMPLE=%s'%''.join(missing).encode('unicode_escape').decode())"
```

```
UNIQUE_CHARS=779
MISSING_IN_MSYH=1
MISSING_SAMPLE=\x00
```

唯一「缺失」是文本抽取产生的 `U+0000` 控制字符（非可见字符）；779 个实际字符全部在 MSYH cmap 内。

**(d) 目视复核（人工开档，方案 GT-a 口径）**

```bash
python -c "import pymupdf, tempfile, os; out=os.path.join(tempfile.gettempdir(),'tb-report-png'); os.makedirs(out,exist_ok=True); doc=pymupdf.open('workflow-out/report/trustbridge-final-report.pdf'); print('pages',doc.page_count); [doc[n-1].get_pixmap(dpi=100).save(os.path.join(out,'p%02d.png'%n)) for n in range(1,doc.page_count+1)]"
```

12 页全部落图（827×1170 px @100dpi），逐页阅图检查：中文渲染正常、表格/代码块/组件图对齐、无缺字方块；页眉（除封面）与「第 X / 12 页」页脚正常。**本轮发现并修复的两处渲染缺陷**：`❌/✅` 表情符号在 MSYH 中无字形（已改为文字「否 / 是」）；ASCII 组件图与 console 引文原先按 CJK 折行导致错位（已改为 `Preformatted` 固定宽度 + 程序化对齐）。

---

## 4. 降级路径登记（方案 §4 / GT-f）

**未触发。** reportlab 5.0.1 主路径构建成功（见 §2），因此未走「Markdown 源 + PDF 未构建登记」的降级路径。

---

## 5. 证据索引（正文 → 档内文件）

正文所有数字 / 地址 / tx hash / 状态字面值均标注「文件:行」；路径相对 `trustbridge/`（课程目录素材另注）。浓缩索引（与 PDF 附录 A 同源）：

| 数据点 | 值 | 出处 |
|---|---|---|
| R0 退款交易 | `0x85e4e39b628a358ef7cd61bfc8c87e67a730c76617a823a6001a87ea86ae0838` | `workflow-out/w1b2-refunded-evidence.md:14、:24` |
| R0 回执 / 余额勾稽 | status 0x1 / block 104 / gasUsed 35996；999002 → 1000002（+1000） | `workflow-out/w1b2-refunded-evidence.md:20-:25、:51-:54` |
| R0 状态字面 / 边界 | `"state": "Funded"` → `"state": "Refunded"`；deadline_slot 102；claim@104 | `workflow-out/w1b2-refunded-evidence.md:37、:43、:46-:47` |
| R0 判读纪律 | status 0x1 ≠ 方法成功（平台吞 Err） | `workflow-out/w1b2-refunded-evidence.md:28-:30` |
| R1 assess_brief | 7×string → 4×string（Stack too deep）；selector `0x3297eeb6`；heuristic 75/["heuristic-mode"]/60000/40 | `workflow-out/w1b2-r1-s3-assess.md:184、:78-:79、:83-:86` |
| R1 正常流 | Settled；alice=9000 bob=980 broker=20；9000+980+20=10000 | `workflow-out/w1b2-r1-demo-normal.md:29、:79` |
| R1 真实 LLM | egress 拒绝私网 `172.18.0.2`；无 `TB_LLM_*` 凭据 | `workflow-out/w1b2-r1-s3-assess.md:151、:161-:163` |
| R2 三裁决 | Malicious→Refunded（misconduct 1→2）/ Fulfilled→Settled（bob +980、broker +20）/ NotFulfilled→Refunded（计数不增） | `workflow-out/w1b2-r2-adversarial.md:86-:90、:102-:105` |
| R2 编码器缺陷 | string[] head_size 偏移多 0x20；修复后 cast calldata MATCH | `workflow-out/w1b2-r2-adversarial.md:113-:135` |
| R2 实例守恒 | alice=77000 bob=3920 broker=80（sum=81000） | `workflow-out/w1b2-r2-adversarial.md:146-:157` |
| R3 判级 L2 | agreed … from 4 input(s) (avg_num=4)；cert.signers RAW = [0, 1, 2, 3] (len=4) | `workflow-out/w1b2-r3-e2-committee.md:71、:73`；`workflow-out/_r3-t3-console-raw.txt:24、:31` |
| R3 实例 / 合约 | `Lyquid-ybidj3krshf4gqcjk3m3px6mooi6tg74twwaa` @ `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589` | `workflow-out/w1b2-r3-e2-committee.md:42` |
| R3 退款守恒 | alice 10000 → 9000（fund −1000）→ 10000（退款 +1000）；bob/broker 恒 0 | `workflow-out/w1b2-r3-e2-committee.md:98` |
| R3 T7 复验 | `Lyquid-dpp6…unqa` @ `0x942ED2fa…f01e`；exit 0 / DEMO COMPLETE；faucet read-back OK / refund check OK | `workflow-out/w1b2-r3-e2-committee.md` §T7 :164-:179；`workflow-out/_r3-t7-dt31-verify-raw.txt:22、:31、:69、:72-:73` |
| EVM 创建 gas | 1,936,008 / 3,843,041 / 3,707,457 | `workflow-out/r3-t4-contrast-report.md:180-:187` |
| EVM 代码量 | Escrow.sol 407；Lyquid 六文件 2083（1323 去测）；含 lib.rs 2933（2173 去测） | `workflow-out/r3-t4-contrast-report.md:60-:83` |
| EVM 信任假设 / 负对照 | 地址表委员会（Escrow.sol:81-83/:108）；deal-3 三签重放 deal-4 被拒（`non-member signer`，rc=1） | `workflow-out/r3-t4-contrast-report.md:85-:97、:104、:232` |
| 判级口径 | L2 = 4 提案 + 4 签；L1 = 1 提案 + 4 签；L0 = 单签送达 | `docs/b3-user-test/通过判据.md:23-:36` |
| 局限清单 | 真实 LLM 未接 / misconduct 无 getter / B3 未收集 / 对抗流复跑未执行 / 对照口径限制 / 单机 devnet | `workflow-out/r3-t4-contrast-report.md:107、:212-:221`；`workflow-out/implementation.md:28、:407、:511、:603` |

> 口径提醒（方案 §2 仲裁修订 1）：`9000 / 980 / 20` 三数同现的记录在 **R1 正常流**（`workflow-out/w1b2-r1-demo-normal.md:29、:79`），R2 对抗流档内**没有**这组三元组；报告中两处运行分列、不合并标注。

---

## 6. 复现步骤（一键）

```bash
cd trustbridge
python -c "import reportlab, sys; print('reportlab', reportlab.Version); print(sys.version)"
python workflow-out/report/build_report.py        # 期望末行 BUILD_OK、TOTAL_PAGES=12
python -c "import pypdf; r=pypdf.PdfReader('workflow-out/report/trustbridge-final-report.pdf'); print('PAGES', len(r.pages))"
```

---

## 7. 开工基线（T1 实跑存证，2026-10-30）

`git log --oneline -1`（逐字）：

```
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)
```

`git status --short`（逐字，T1 开工第一动作）：

```
 M workflow-out/_probe_gate_a0.md
 M workflow-out/_probe_plan_r1_a0.md
 M workflow-out/plan.md
?? workflow-out/_implementation-prev-r1-backup.md
?? workflow-out/_implementation-prev-r2-backup.md
?? workflow-out/_implementation-prev-w1a-backup.md
?? workflow-out/_plan-prev-r4d1-backup.md
?? workflow-out/_pre-task-snapshot-r1.patch
?? workflow-out/_pre-task-snapshot-r2.patch
?? workflow-out/_pre-task-snapshot-r3.patch
```

**差异登记（对方案 §1 GT-d 预列基线）**：方案预列 9 条；实跑 **10 条**，多出一条
`M workflow-out/_probe_plan_r1_a0.md`（方案评审轮对既有探针档的被动更新，**非本轮编码员写入**）。
其余 9 条与方案列举逐字一致。按方案「以 T1 实跑输出为准」的条款，本节即 GT-d 的比对基准。

**收尾比对（T6）**：`git status --short` 相对上述基线**条目未减未改**，新增仅
`?? workflow-out/report/`（其下 3 个交付文件）；`git log --oneline -1` 仍为 `8d093b5`；
全程未执行任何 `git add/commit/push`。

---

## 8. 核对笔记（T1 映射表逐条核对，摘要）

- 按方案 §2 / §3 映射表逐条打开源文件核对字面值：**行号无漂移**，全部「文件:行」引用与源文件实际行号一致；本 README §5 与 PDF 正文引用的行号均为核对后的实际行号。
- 逐字核对通过的代表性字面值：`0x85e4…0838`、`35996`、`999002 → 1000002`、`deadline_slot 102`、`0x3297eeb6`、`75 / ["heuristic-mode"] / 60000 / 40`、`9000 / 980 / 20`（R1）、`48000 → 49000 / 47000 → 48000`、`misconduct 1→2`、`77000 / 3920 / 80 (sum=81000)`、`agreed … from 4 input(s) (avg_num=4)`、`cert.signers RAW = [0, 1, 2, 3] (len=4)`、`1,936,008 / 3,843,041 / 3,707,457`、`407 / 2083 / 1323 / 2933 / 2173`、`non-member signer`。
- 引用纪律：报告不引用任何规划期/执行期「预期值」；凡无数据处写「无数据（原因）」（见 PDF §3.5 数据缺口与 §4 局限表）。

---

## 9. 构建信息摘要

- 生成日期：2026-10-30；工具 reportlab 5.0.1（Platypus）；A4（595.3 × 841.9 pt）；12 页。
- 字体：Microsoft YaHei（`C:\Windows\Fonts\msyh.ttc`，子集嵌入）。
- 报告结构与方案 §2 一一对应：封面（课程背景 / HEAD / devnet）→ §1 问题定义 → §2 架构 → §3 实验结果四阶段 + R2/R3 详情 + EVM 对照 → §4 信任假设与局限（7 条）→ §5 AI 使用声明 → 附录 A 证据索引 + 附录 B 构建信息。
