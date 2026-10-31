# TrustBridge 期末幻灯片 — 构建说明 / 验证记录 / KEY_HITS 一致性核对

> 方案：`workflow-out/plan.md`（R4-D2+D3，审查通过后由编码员执行）。
> 本文件为方案 §0 清单 #5（slides/README.md），仿 `workflow-out/report/README.md` 体例。
> 交付产物：`trustbridge-final-slides.pptx`（16:9，**12 页**，每页含 speaker notes），
> 源文件 `build_slides.py`。

| 文件 | 说明 | md5 |
|---|---|---|
| `build_slides.py` | 幻灯片**唯一源文件**：12 页全文与 notes 均以 Python 数据结构内嵌；python-pptx 构建；尾段自检 | 见 §7 实跑值 |
| `trustbridge-final-slides.pptx` | 构建产物：13.333×7.5 in（16:9），12 页，每页 notes 非空 | 见 §7 实跑值 |
| `README.md` | 本文件（构建 / 验证 / KEY_HITS 对照 / 字体与偏离登记） | — |

---

## 1. 环境与依赖

| 项 | 实测值 | 取得方式 |
|---|---|---|
| 宿主 | Windows（win32 10.0.26300）+ Git Bash | 本轮执行环境 |
| Python | 3.14.5 | `python --version` |
| python-pptx | **1.0.2** | `python -c "import pptx; print(pptx.__version__)"` |
| 中文字体（构建期引用名） | `Microsoft YaHei`（不嵌入） | 方案 §2 冻结条款 6 |
| 等宽字体（构建期引用名） | `Consolas`（不嵌入） | 同上 |
| 缺字预检 | fontTools（读 `C:\Windows\Fonts\msyh.ttc` cmap） | 构建自检 `FONT_COVERAGE` |
| 目视复核 | LibreOffice 26.8.1.1（`soffice --headless --convert-to pdf`）+ PyMuPDF 1.28.2（仅复核用，不参与构建） | §3-(e) |

不可用工具（如实登记，与 D1 同一环境）：**pandoc / marp** —— 规划期 `where` 查询均失败，
故 D2 主路径 = python-pptx 真出 `.pptx`（无降级）。

---

## 2. 构建（逐字）

```bash
cd trustbridge
python workflow-out/slides/build_slides.py
```

本轮实跑输出（逐字，2026-10-30）：

```
OUTPUT=F:\canvus auto\downloads\202609CS5298\trustbridge\workflow-out\slides\trustbridge-final-slides.pptx
BUILT_PAGES=12
PAGES=12
SLIDE_SIZE_IN=13.333 x 7.500 (16:9=True)
NOTES_OK=True (empty=[])
KEY_HITS=23/23 (MIN=15)
MISSING=[]
TRIPLE_PAGES=[8] (allowed=[8])
P5_CHAIN=True ('10000 → 9000 → 10000')
FONT_COVERAGE=UNIQUE_CHARS=630 MISSING_IN_MSYH=0 OK
PAGE 01 len=649
PAGE 02 len=1028
PAGE 03 len=1763
PAGE 04 len=1413
PAGE 05 len=1766
PAGE 06 len=1627
PAGE 07 len=972
PAGE 08 len=2128
PAGE 09 len=2033
PAGE 10 len=893
PAGE 11 len=994
PAGE 12 len=837
SIZE_BYTES=81155
BUILD_OK
EXIT=0
```

> 上方为**最终重建**（仲裁修订：implementation.md 指针加「R3 版」限定语后的重建，2026-10-30）的逐字输出；
> 修订前的首次构建输出（`SIZE_BYTES=80761`）保留在 `_r4d2d3-verify-raw.txt` §T4。

- 脚本为「构建 → 保存 → **重开产物** → 自检」同一进程两段式：自检读的是落盘后的
  `.pptx`（`Presentation(OUT_PPTX)`），不是内存对象。
- 退出码 `EXIT=0` 仅当全部自检项通过（页数 / 页尺寸 / notes / KEY_HITS / 三数口径护栏 /
  P5 退款链 / 非空文件）；任一项不过即打印 `BUILD_FAILED` + `FAIL:` 清单并以非零退出。

---

## 3. 验证（逐字命令 + 实跑输出）

**(a) GT-a：页数 ≥10（方案值 12）、每页 notes 非空、16:9**

构建自检项（§2 实跑输出）：

```
PAGES=12
SLIDE_SIZE_IN=13.333 x 7.500 (16:9=True)
NOTES_OK=True (empty=[])
```

独立复核（python-pptx 重新打开，只数页与 notes）：

```bash
python -c "from pptx import Presentation; p=Presentation('workflow-out/slides/trustbridge-final-slides.pptx'); print('PAGES', len(p.slides)); print('NOTES_ALL', all(s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip() for s in p.slides)); print('SIZE_IN', round(p.slide_width/914400,3), round(p.slide_height/914400,3))"
```

实跑输出见 `workflow-out/_r4d2d3-verify-raw.txt`（T4 复核段）。

**(b) GT-b：KEY_HITS 字面值抽查 ≥15 项（pptx 全文本含 notes）**

脚本内清单 23 项（方案候选 23 项全取），自检实跑 `KEY_HITS=23/23  MISSING=[]`。
清单与逐项来源见 §6 核对表。

**(c) GT-b′：三数口径护栏（程序化）**

- `9000` + `980` + `20` 三数「独立数值」同现的页集合必须 ⊆ {P8}（R1 语境）：
  自检输出 `TRIPLE_PAGES=[8] (allowed=[8])`（正则边界 = 前后不得为数字或千分位逗号，
  故 `19000` / `2026` / `2083` 之类不误判）。
- P5 正文必须含完整退款链字样 `10000 → 9000 → 10000`：`P5_CHAIN=True`。
  （箭头字符以脚本常量 `ARROW` 声明后程序化拼接，比对同一来源。）
- 人工复核（本轮执行）：P5 的 9000 一律标为 **R3 funding 中间态**；R2 行只写
  `bob +980 / broker +20`（Fulfilled 结算口径），全片无「R2 且 9000/980/20 三元组」表述
  （P8 notes 的反例句已改为「没有这组三数」，不在同一句里堆三数字样，避免机械误读）；
  R1 三数只出现在 P8（`alice=9000 / bob=980 / broker=20` 与守恒式）。逐 token 上下文扫描
  输出见 `_r4d2d3-verify-raw.txt` §T7-b′。

**(d) console 摘录不折行（方案 §3.1）**

构建期 `assert_console_fit` 逐块计算：P4 最长行 114 字符 → 12.5pt Consolas 约需 784pt，
块内可用 858pt；P5 最长行 112 字符 → 12.0pt 约需 739pt，可用 858pt；均不折行、不出框。
页面上的行宽预检数字即该函数的实跑值（P4 页脚一行）。

**(e) 目视复核（人工开档；本轮额外手段，方案 GT 未要求）**

```bash
"/c/Program Files/LibreOffice/program/soffice.exe" --headless --convert-to pdf \
  --outdir /tmp/slidecheck workflow-out/slides/trustbridge-final-slides.pptx
python -c "import pymupdf; d=pymupdf.open('.../trustbridge-final-slides.pdf'); print('PDF_PAGES', d.page_count)"
```

实跑：`PDF_PAGES 12`（12 页全部落 PNG 逐页阅图）。逐页检查结论：中文渲染正常、
无缺字方块、表格与 console 块不出框、标题条与页脚对齐。**本轮据此修正的三处**：
① 正文误用 markdown 反引号（U+0060 会原样显示）→ 去除；② P5/P6 版面留白过大 →
加 T7 实录 console 块、表格字号 10→11.5/9.5→11；③ `⇒`（U+21D2）在 Microsoft YaHei 中
**无字形**（自检 `FONT_COVERAGE` 抓到 `MISSING='⇒'`）→ 改为「，即」。修正后
`FONT_COVERAGE=UNIQUE_CHARS=630 MISSING_IN_MSYH=0 OK`（修订前的首次构建为 628，差异来自新增的「R3 版…取回」限定语字符）。

**(f) 字体覆盖（方案 §2 冻结条款 6 的配套检查）**

全片 630 个去重字符（含 notes）逐一比对 `C:\Windows\Fonts\msyh.ttc` 的 cmap，
缺失 0 个 —— 即目标机装有 Microsoft YaHei 时不会出现缺字方块；Consolas 仅用于
ASCII 行（console 摘录），ASCII 亦在 MSYH cmap 内，即便等宽字体缺失也只是字宽变化、
内容不丢。

---

## 4. 降级路径登记（方案 §2 R1 风险 / GT-f）

**未触发。** python-pptx 1.0.2 主路径构建成功（§2），因此既未走「marp/beamer 源 +
未构建登记」的降级路径，也未出现「未真出 .pptx」的情形。

**差异登记（GT-f）**：

| # | 项 | 方案原文 | 实际 | 处置 |
|---|---|---|---|---|
| 1 | console 摘录行宽假设 | 「摘录行本身 ≤100 字符，选行时已核」（§3.1） | P4 的 `cert.signers RAW …` 行实为 **114 字符** | 保留原行不改写（实录逐字优先）；用 12.5pt Consolas + 程序化行宽预检保证不折行不出框（§3-(d)），并在此登记 |
| 2 | 目视复核 | 方案未列 | 本轮用 LibreOffice 转 PDF + PyMuPDF 落图逐页复核 | 额外手段，已登记结论（§3-(e)）；不改变任何交付判据 |
| 3 | 数字口径 | 与 KEY_HITS 一致 | 一致（23/23 命中）；未发现需要改数的项 | 无差异 |
| 4 | implementation.md 指针 | 方案 §0 把 `implementation.md` 列为只读素材（R3 版） | 本轮按工作流约定重写了该文件（实现说明 §5-D1），裸指针会指向新文件 | P9（含 notes）/P3 notes 的指针统一加「R3 版」限定，并给取回命令 `git show 8d093b5:workflow-out/implementation.md`；自检 grep 无残余裸指针（verify-raw §T9） |

---

## 5. KEY_HITS 一致性核对表（每页 → 出处）

> 数字唯一事实源 = `workflow-out/report/README.md` §3 KEY_HITS 与 §5 证据索引。
> 下表把**幻灯片页**映射到 KEY_HITS 行，便于逐条抽查（行号为该 README 的实际行号）。

| 页 | 关键数字 / 字面值 | KEY_HITS 出处（report/README.md） | 一手证据 |
|---|---|---|---|
| P1 | `8d093b5`、`2026-10-30` | §3(a) HEAD / 日期 | `git log --oneline -1` 实跑（§7） |
| P2 | `172.18.0.2`；heuristic `75 / ["heuristic-mode"] / 60000 / 40` | §5「R1 真实 LLM」「R1 assess_brief」 | `w1b2-r1-s3-assess.md:151、:161-163`；`:83` |
| P3 | `"state": "Funded"`→`"state": "Refunded"`；`avg_num=4`；四端口 10087/11087/12087/13087 | §5「R0 状态字面」「R3 判级」 | `w1b2-refunded-evidence.md:37、:43`；`_r3-t3-console-raw.txt:19、:24`；`agents/common/rpc.py:91` |
| P4 | `inputs=4`、`[0, 1, 2, 3]`；L2 口径 | §5「R3 判级 L2」「判级口径」 | `_r3-t3-console-raw.txt:24、:31`；`docs/b3-user-test/通过判据.md:27` |
| P5 | `0x87006e75a5B6bE9D1bbF61AC8Cd84f05D9140589`；`0x942ED2fa862887Dc698682cc6a86355324F0f01e`；`10000 → 9000 → 10000` | §5「R3 实例 / 合约」「R3 退款守恒」「R3 T7 复验」 | `w1b2-r3-e2-committee.md:42、:98、:164-179`；`_r3-t7-dt31-verify-raw.txt:22、:30、:31、:69` |
| P6 | `1,936,008` / `3,843,041` / `3,707,457`；`407` / `2083` / `1323` / `2933` / `2173`；`non-member signer`；`0xFD6F7A6a5c21A3f503EBaE7a473639974379c351`（notes） | §5「EVM 创建 gas」「EVM 代码量」「EVM 信任假设 / 负对照」 | `r3-t4-contrast-report.md:180-187、:60-83、:85-97、:104、:232`；`_r2-normal-assess-raw.txt:2` |
| P7 | `1,936,008` vs `3,843,041`（≈1.98×）；`47,908` / `226,658`；`32,713` / `36,014`；20 笔 vs 14 笔 | §5 同上（结论段） | `r3-t4-contrast-report.md:250、:251、:252、:193、:197、:219` |
| P8 | `0x85e4e39b…0838`；`999002` → `1000002`；deadline_slot 102 / claim@104；`9000` / `980` / `20`；`77000` / `3920` / `80`（sum `81000`）；`[0, 1, 2, 3]`；`inputs=4` | §3 全部相关行 | `w1b2-refunded-evidence.md:14、:20-25、:43、:46-47、:51-54`；`w1b2-r1-demo-normal.md:29、:79`；`w1b2-r2-adversarial.md:86-90、:77、:89、:147、:156-157`；`_r3-t3-console-raw.txt:24、:31` |
| P9 | `misconduct`；`lib.rs:222` TODO(W4)；`_r2-adversarial-raw.txt:6` | §5「局限清单」 | `r3-t4-contrast-report.md:107、:212-221`；`implementation.md:28、:511、:603`（R3 版，`git show 8d093b5:workflow-out/implementation.md` 取回） |
| P10 | 1.98×；propose 1 + aggregate 10 行 + 回调 1 笔 | §5 同（结论） | `r3-t4-contrast-report.md:199-208、:250` |
| P11 | `_r3-t7-dt31-verify-raw.txt:22、:31、:69` | §5「R3 T7 复验」 | 同上 |
| P12 | 27/27（KEY_HITS 实跑）、路径指引 | §3(b) 实跑 | `report/README.md` §3(b) |

**口径提醒（方案 §2 冻结条款 2）**：`9000 / 980 / 20` 三数同现只属 **R1 正常流分账**
（`w1b2-r1-demo-normal.md:29、:79`）；**R2 Fulfilled 结算**是 bob +980 / broker +20
（alice 49000→48000→48000，`w1b2-r2-adversarial.md:77-:78、:89`，R2 档内无三数三元组）；
`9000` 作为独立数值另有一处 = **R3 funding 中间态**（`w1b2-r3-e2-committee.md:98`，
P5 已按此标注）。

---

## 6. 字体不嵌入登记（方案 §2 冻结条款 6 / §7 R3）

- 构建期只写**字体名**（`Microsoft YaHei` 用于标题与正文，`Consolas` 用于 console 块），
  **不嵌入字体**；pptx 内每个 run 同时写 `a:latin` / `a:ea` / `a:cs` 三处 typeface，
  保证中文走指定字族而非回退到主题默认字体。
- 目标机缺字体时的替代表现：PowerPoint / WPS 会按系统字体替换表替代（中文通常落到
  宋体/思源黑体一类），**内容不丢、换行可能变化**；console 块若缺 Consolas，等宽效果
  消失但字符仍完整。
- 目标机字体要求（交付说明）：Microsoft YaHei（或等价 CJK 无衬线）；Consolas（可选）。
- 构建期实测覆盖：630 个去重字符在 msyh cmap 内 **0 缺失**（`FONT_COVERAGE=… OK`），
  即本机环境下不出现缺字方块。

---

## 7. 复现步骤（一键）与产物指纹

```bash
cd trustbridge
python -c "import pptx; print('pptx', pptx.__version__)"          # 期望 1.0.2
python workflow-out/slides/build_slides.py                        # 期望末行 BUILD_OK、PAGES=12、EXIT=0
python -c "from pptx import Presentation; p=Presentation('workflow-out/slides/trustbridge-final-slides.pptx'); print('PAGES', len(p.slides))"
```

产物指纹（本轮实跑 `md5sum`，写入 `workflow-out/_r4d2d3-verify-raw.txt` 尾段）：

| 文件 | 大小 | md5（最终值，见 verify-raw §T9-④） |
|---|---|---|
| `trustbridge-final-slides.pptx` | 81,155 B | `a2495e35786d6c17a91341a61235af9b`（每次重建都会变：pptx 内含构建时间戳） |
| `build_slides.py` | 50,445 B（1,013 行） | `25ccb29fdad6d5189c3edfcf7102fc59` |

> 说明：上表 md5 为**最终交付指纹**（与 `_r4d2d3-verify-raw.txt` §T9-④ 同值）。`.pptx` 为
> zip 容器，内含文档属性与 zip 时间戳，**任何重建都会改变其 md5**（重建后请以新实跑值为准）；
> `build_slides.py` 为纯文本源，md5 仅随源文件编辑变化。

---

## 8. 与方案 §3 逐页对照（自检用）

| 页 | 方案标题 | 实现标题（pptx 实际） | notes |
|---|---|---|---|
| P1 | 封面 | `TrustBridge：基于 Lyquid 平台的 A2A 交易信任桥` | 有 |
| P2 | 动机：A2A 信任桥问题 | 同 | 有 |
| P3 | 架构一页 | `架构一页：四件组件` | 有 |
| P4 | 演示实录摘录：R3-T3 E2 判级 L2 | 同 | 有 |
| P5 | 退款守恒与读回勾稽 | `退款守恒与读回勾稽（R3 实例 + T7 复验）` | 有 |
| P6 | 实验对照表：纯 EVM Escrow vs Lyquid（四维） | `实验对照：纯 EVM Escrow vs Lyquid（四维）` | 有 |
| P7 | 对照要点解读（诚实口径） | `对照要点解读：不做单向结论` | 有 |
| P8 | 里程碑时间线（R0→R3） | `里程碑时间线：R0 → R3` | 有 |
| P9 | 信任假设与局限（诚实清单） | `信任假设与局限（诚实清单，七条）` | 有 |
| P10 | 结论 | 同 | 有 |
| P11 | 后续工作 | 同 | 有 |
| P12 | 封底：证据索引与声明 | `证据索引与声明` | 有 |

标题在方案基础上仅作短语化（不改变内容口径）；每页 notes 承载完整口径与「文件:行」出处。
