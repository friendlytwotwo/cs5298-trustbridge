# R4-D4 实现说明（编码员，2026-10-30）

> 方案：`workflow-out/plan.md`（R4-D4，2026-10-30，审查通过版；下文「§x」均指该文件）。
> 本轮任务 = **纯文档收尾**：产出 `workflow-out/_submission-plan.md` 一份
> （ZIP 内容清单 + 全量交叉复核 a/b/c/d + 人工待办清单），**不产生任何链上证据、不改代码目录**。
> 纪律：**零 git 写**（全程只读 `git log/status/diff/ls-files/show/rev-list/check-ignore`）；
> **只登记不修改**（复核发现的不一致全部落 `_submission-plan.md` §2.e，未改动 R0–R3/R4-D1/D2/D3 产物）。
> 复核与清单的每条结论均为**本轮实跑**，命令与输出逐字入档于 `_submission-plan.md` §2/§4。
>
> **本文件按工作流约定重写（先例：R4-D2+D3 的 D1，见 `git show 8d093b5:workflow-out/implementation.md`
> §5-D1）**。上一版为 **R4-D2+D3 实现说明**（208 行，md5 `b421a1997fdfd160219a4789cf934278`），
> 该版本**未入库**（`git status` 为 ` M`、不在 HEAD），**无法由 git 取回**，故本轮改写前先 `cp` 到
> `%TEMP%` 并**逐字保留于本文件附录 A**（md5 复核见 §4-T1）。该改写不在方案 §0 清单内，作为偏离项
> 登记于 §5-D1。

---

## 0. 基线与环境（本轮实跑）

| 项 | 值 | 取得方式 |
|---|---|---|
| HEAD（开工） | `8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)` | `git log --oneline -1` |
| 工作树（开工） | **19 条**（6 `M` + 13 `??`；逐条见 `_submission-plan.md` §5） | `git status --short` / `git status --porcelain \| wc -l` |
| Python | 3.14.5 | `python --version` |
| pypdf / python-pptx | **6.19.0 / 1.0.2** | `python -c "import pypdf,pptx; print(pypdf.__version__, pptx.__version__)"` |
| 本机 grep | ugrep 7.8.4（`-F` 固定串语义；Windows 上输出 CRLF） | `grep --version` |
| PowerShell | 5.1.26100.9711（`Compress-Archive`/`Expand-Archive`/`Get-FileHash` 可用） | `powershell -NoProfile -Command '$PSVersionTable.PSVersion.ToString()'` |
| tar | GNU tar 1.35（`F:\Git\usr\bin\tar.exe`） | `tar --version`（PowerShell 内同源） |
| 不可用工具 | **无 `7z` / 无 `zip` / 无 `pwsh`**（`command -v` 均 rc=1） | `command -v 7z \| zip \| pwsh` |
| 仓库体积提示 | `lyquid/` = **1.3G**（含 `lyquid/target`，已 gitignore） | `du -sh lyquid`；ZIP 命令据此改用 `git archive`（§3.1.2） |

未触发任何降级路径：方案 §6 的风险 3（pypdf/pptx 环境异常）未发生（§2.d 两条命令均实跑通过）。

---

## 1. 逐文件改动（方案 §0 清单对照）

| # | 路径 | 动作 | 改动摘要 | 规模 |
|---|---|---|---|---|
| 1 | `workflow-out/_submission-plan.md` | **新建**（方案 §0-#3，唯一交付产物） | 五章：§1 ZIP 内容清单（1.1 三件 + 1.2 已入库代码面 103 文件逐文件 + 1.3 w1b2-* 13 份逐份 + 1.4 其余证据归组 + 1.5 在盘未入库 19 条）；§2 交叉复核（2.a 27×3 矩阵、2.b b1/b2/b3、2.c 15 条抽查、2.d 页数、2.e 不一致 8 条）；§3 人工待办五项（ZIP 命令 2 版 / 11-19 检查单 8 项 / B3 / demo 实拍 / 终裁记录五份）；§4 命令附录 C1–C10；§5 红线自查 | **779 行**（T7 `wc -l` 实跑，md5 `b24acb49e22ff9281ce9a3688daad0e3`；其后若仅有登记性追改，以复跑为准） |
| 2 | `workflow-out/implementation.md` | **改写**（工作流约定；偏离项 D1） | 本文件；R4-D2+D3 原版 208 行**逐字保留于附录 A** | 本文件 |

**只读引用（一字未改）**：`workflow-out/plan.md`（R4-D4 方案，规划期覆盖，非本轮写入）、
`workflow-out/_plan-prev-r4d2d3-backup.md`（规划期备份）、`report/{README.md,build_report.py,
trustbridge-final-report.pdf}`、`slides/{README.md,build_slides.py,trustbridge-final-slides.pptx}`、
`demo-script.md`、`r3-t4-contrast-report.md`、`_r4d2d3-verify-raw.txt`、`w1b2-*` 13 份、
`_r1-*`/`_r2-*`/`_r3-*` 原始日志、`docs/b3-user-test/` 三份、`_plan-prev-r2/r3/r3t4/r3t5t6/
r4d1-final-backup.md`、`_commit-plan.md`。**零写入**：`lyquid/`、`scripts/`、`agents/`、
`docs/`、`experiments/`、`README.md`（T7 `git status` 与 T0 逐条比对可证）。

---

## 2. `_submission-plan.md` 实现要点（方案 §5 章节规格逐节对照）

| 方案 §5 要求的节 | 落点 | 实现摘要 |
|---|---|---|
| §0 头部 | 文件头引用块 | 方案出处（R4-D4 + 备份件）、生成日期 2026-10-30、基线 HEAD 存证（开工/收尾两次逐字 `8d093b5`）、纪律声明四条（零 git 写 / 只登记 / 全实跑 / 不生成 ZIP） |
| §1.1 主交付三件 | §1.1 | PDF（12 页，md5 `18c90f03…`）、PPTX（12 页 16:9，md5 `a2495e35…`）、demo-script（8 镜 305s，md5 `cd78c647…`），各标规模 + 来源路径 + 入库状态（三件均未入库）；另列 7 件配套源文件/说明件 |
| §1.2 已入库代码面 | §1.2 | 15 提交序列逐字 + 103 文件（95 A + 8 M）按 C1–C7/R3-C1–C6/归档/T7 **逐文件**分组 + `_commit-plan.md` 头部时点语义登记（E1） |
| §1.3 证据索引 | §1.3 | w1b2-* **13 份逐份一行**：说明（文件头 / `report/README.md` §5）、对应原始日志（文档内引用实取）、规模、入库提交号（dc78d2f×6 / c31d701×3 / efc256c×3 / 8d093b5×1）；`_w1b2_t3_replay.py` 与两份 `_plan-prev-w1b2*` 备份单列（非证据件） |
| §1.4 其余证据归组 | §1.4 | `_r1-*`(13) / `_r2-*`(15) / `_r3-*`(26) / `_r4d2d3-verify-raw.txt` / `w1a-*`(8) / `w1b1-*`(8) / `t0-*`(2) / `_w1b1-*`(3) 按组一行（计数 + 归属组号 + 入库状态，`ls`/`git ls-files` 实跑） |
| §1.5 在盘未入库 | §1.5 | 19 条按 6 类归组（R4 产物 / 本轮新建 / 改写件 / 探针 / 备份 / patch），指向 §3.2 |
| §2.a 命中矩阵 | §2.a | 报告 27/27（逐字复跑 `report/README.md:71`）、幻灯片 25/27（python-pptx 全文本，P6 六键全命中且命中页 = P6）、demo 19/27（`grep -cF`）；**27×3 三态矩阵** + 冲突扫描（地址/selector/大数字结构化抽取，结论 **0 冲突**）+ 未命中形态说明 + 可选修正建议 |
| §2.b 索引齐套 | §2.b | b1 索引→盘 10/10 OK；b2 盘→索引 `comm -3` **DIFF_LINES=0**（13/13）；b3 引用原始日志 34/34 OK |
| §2.c 抽查 15 条 | §2.c | 命令级 9（S2-①…④、S2 备路径、S3、S4、S5-①、S5-②）+ 输出级 6（S1 七行、deploy exit、S3 分账、S4 归因、S5-① 退款勾稽、S5-② 四签）；**15/15 命中**，另附可选 S1 命令源（HEAD `:443/:617`）实跑 |
| §2.d 页数复验 | §2.d | `PAGES=12`、`SLIDES=12`、`NOTES_EMPTY=[]`（逐字） |
| §2.e 不一致总表 | §2.e | E1–E8 逐条：位置 / 事实 / 与谁不一致 / 以 KEY_HITS 或 git 为准的建议 / 处置状态 =「仅登记，未修改」 |
| §3.1 ZIP 命令 | §3.1 | 两条可复制 PowerShell 命令（3.1.1 显式清单 / 3.1.2 `git archive 8d093b5` + 叠加），附工具可用性实测与「勿整目录压 `lyquid/`（1.3G）」提示 |
| §3.2 提交前检查单 | §3.2 | 8 项（R4 入库决策 / 冲突修正 / PDF-PPTX 终验 / demo 实拍 / B3 回收 / 终裁签认 / ZIP+md5 / git 动作），标「11/19 12:00 截止」与状态 |
| §3.3 B3 安排 | §3.3 | 三份 481/144/123 行（`wc -l` 实跑）+ 当前状态（空白表单、无反馈，HEAD `implementation.md` §9.1 #6 口径）+ ≥3 天回收窗口建议 |
| §3.4 demo 实拍 | §3.4 | S3 当轮新实例（`demo-script.md` §8-5/§3）、占位符、单次纪律、`MSYS_NO_PATHCONV=1`、截止/rc=124、预案 A/B、305s 与 180s 剪辑点 |
| §3.5 终裁记录 | §3.5 | 五份位置（R2 `:279`、R3 `:9`、T4 `:4/:14`、T5T6 `:48/:73`、D1 `:139-:144/:146-:148`）`grep -n '终裁'` 实跑 + HEAD 版 `:347-:361`/`:663-:696` 只读取回核对结论 |
| §4 命令附录 | §4 | C1–C10 逐字（KEY_HITS / 幻灯片提取 / demo 计数 / 两处结构化扫描 / b1-b3 / 15 条抽查 / 页数 / T1 采集 / 终裁定位） |
| §5 红线自查 | §5 | 零 git 写前后存证、新增/覆盖文件 4 项、未修改声明、未跑项 5 项、复现性 |

### 2.1 执行顺序（方案 §4 T0–T7 对照）

| 阶段 | 方案要求 | 本轮实跑 |
|---|---|---|
| T0 | HEAD + `status` + 环境探测 | `8d093b5`；19 条；pypdf 6.19.0 / pptx 1.0.2 / Python 3.14.5 ✅ |
| T1 | 已入库面采集 | 15 提交；103 文件（95 A + 8 M）；`ls-files workflow-out/` = 119；w1b2 16 命中（13 证据件 + 2 方案备份 + 1 脚本）✅ |
| T2 | 三文档 27 键 | 27/27、25/27、19/27；P6 六键命中页 = P6 ✅ |
| T3 | b1/b2/b3 | 10/10、13/13 DIFF=0、34/34 ✅ |
| T4 | 15 条抽查 | 命令级 9/9 + 输出级 6/6 = 15/15 ✅ |
| T5 | 可打开性 | `PAGES=12`、`SLIDES=12`、`NOTES_EMPTY=[]` ✅ |
| T6 | 撰写交付文件 | `workflow-out/_submission-plan.md` ✅ |
| T7 | 收尾存证 | HEAD 仍 `8d093b5`；见 §4-T7 / `_submission-plan.md` §5 ✅ |

---

## 3. 门禁总表（方案 §2 完成判据，逐项如实登记）

| 门 | 判据 | 状态 | 依据 |
|---|---|---|---|
| GT-a | 27 键 × 3 文档矩阵完整（每格 命中/未命中/冲突），冲突项给「以 KEY_HITS 为准」建议且未改他阶段产物 | **满足** | `_submission-plan.md` §2.a 27 行矩阵；报告 27/27、幻灯片 25/27、demo 19/27、**冲突 0**；未命中 10 处均判「非冲突、无需改数」 |
| GT-b | b1 索引所指文件 100% 在盘；b2 在盘 w1b2-* 100% 被索引（`comm` 双向零差异） | **满足** | §2.b：b1 10/10 OK、b2 `IDX=13 DISK=13 DIFF_LINES=0`、b3 34/34 OK |
| GT-c | 抽查 15 条（命令级 ≥5，本方案定命令级 9 + 输出级 6），每条给实跑 `grep -nF` 命令与输出 | **满足** | §2.c：15/15 命中（命令级 9/9、输出级 6/6），逐条附命令与命中行号 |
| GT-d | pypdf `PAGES=12`、python-pptx `SLIDES=12` 逐字输出在档 | **满足** | §2.d 两条命令逐字输出（另 `NOTES_EMPTY=[]`） |
| GT-e | §3 五项人工待办齐全，ZIP 命令可直接复制执行 | **满足** | §3.1–§3.5 五项齐全；ZIP 命令两版可复制的 PowerShell 片段 + 工具可用性实测（3.1 未执行，见 §7） |
| GT-f | 收尾 HEAD 仍 `8d093b5`；相对 T0 新增文件仅 `_submission-plan.md`（+规划期 2 项）；`git status` 差异逐条登记；零 `git add/commit/push` | **满足（1 项登记）** | HEAD 不变（§4-T7）；新增 `_submission-plan.md`；`plan.md`/`_plan-prev-r4d2d3-backup.md` 为规划期产物；另有 `implementation.md` 改写（D1，属既有 ` M` 条目、不新增 status 行），差异全部登记 |

---

## 4. 命令与输出摘要（全部本轮实跑；完整原文见 `_submission-plan.md` §2/§4）

| 步 | 命令（逐字） | 关键输出 |
|---|---|---|
| T0 | `git log --oneline -1`；`git status --short`；`python -c "import pypdf,pptx; …"` | `8d093b5 …`；19 条；`6.19.0 1.0.2`；`Python 3.14.5` |
| T1 | `git log --oneline dc78d2f..HEAD`；`git rev-list --count`；`git diff --name-status dc78d2f..HEAD`；`git ls-files workflow-out/`；逐 w1b2 `git log -1 -- <f>`；逐提交 `git show --name-status` | 15 提交；103 文件（95 A + 8 M）；119 tracked；w1b2 13 份提交号 dc78d2f/c31d701/efc256c/8d093b5 |
| T2-a1 | 报告 KEY_HITS 一行 `python -c`（`report/README.md:71` 逐字） | `KEY_HITS=27/27` / `MISSING=[]` / `RC=0` |
| T2-a2 | 幻灯片 12 页递归提取（正文 + 表格 + notes）27 键判定 | `SLIDES=12` / `NOTES_EMPTY=[]` / `KEY_HITS=25/27` / `MISSING=[完整 tx hash, 第 5 节]` / `P6_HAS_TABLE=True` / `P8_HAS_TABLE=True` |
| T2-a3 | `grep -cF -- "<key>" demo-script.md` × 27 | 19 命中 / 8 未命中（键序计数逐字见 §2.a） |
| T2-冲突 | 幻灯片 + demo 结构化抽取（地址/selector/大数字） | 幻灯片地址 3（全落 KEY_HITS）、selector 3、大数字均属对比报告/R2 语境；demo `980` 6 处全为 R1 分账 → **0 冲突** |
| T3-b1 | `sed -n '109,136p' report/README.md \| grep -oE … \| sed … \| sort -u` + `test -f` 循环 | 10 文件，10/10 OK |
| T3-b2 | 从 `_submission-plan.md` §1.3 抽 w1b2 文件名集合 → `tr -d '\r'` → `sort -u`，与 `ls workflow-out/w1b2-*` 的 basename 排序集做 `comm -3`（逐字命令见 `_submission-plan.md` §2.b） | `IDX=13 DISK=13` / `DIFF_LINES=0` |
| T3-b3 | `cat w1b2-* \| grep -ohE '_[A-Za-z0-9_-]*\.(txt\|md)' \| tr -d '\r' \| sort -u` + `test -f` | 34 文件，34/34 OK |
| T4 | 15 条 `grep -nF -- '<literal>' <raw>` + 同 literal 对 `demo-script.md` | 15/15 命中（raw 行号 57/58/125/59/581/3/3/3/2/6/86/6/30/31/31） |
| T4-可选 | `git show 8d093b5:workflow-out/implementation.md \| grep -nF 'docker ps --format "{{.Names}} {{.Status}}"'` | 命中 `:443`、`:617`，rc=0（T4 执行时盘上 D2+D3 版仅 `:153`/`:190` 提及，非命令源；改写后的盘上 D4 版见 `_submission-plan.md` §2.c 时点说明） |
| T5 | `python -c "import pypdf; …PAGES…"`；`python -c "from pptx import Presentation; …SLIDES/NOTES_EMPTY…"` | `PAGES=12`；`SLIDES=12`；`NOTES_EMPTY=[]` |
| T6 | 撰写 `workflow-out/_submission-plan.md` | 五章落盘；b2 在文档落盘后对最终 `§1.3` 复跑得 `DIFF_LINES=0` |
| T1（附录 A 自保） | `cp workflow-out/implementation.md /tmp/impl-d2d3-backup.md` + `md5sum` | 两侧 `b421a1997fdfd160219a4789cf934278`，208 行（逐字一致） |
| T7 | `git log --oneline -1`；`git status --short`；`git status --porcelain \| wc -l`；`won't-run` 项见 §7 | 见下 |

**T7 收尾实跑（逐字）**

```
$ git log --oneline -1
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)

$ git status --porcelain | wc -l
20

$ git status --short   （6 M + 14 ??；与 T0 19 条相比唯一新增 = ?? workflow-out/_submission-plan.md）
 M workflow-out/_probe_cold_a0.md
 M workflow-out/_probe_gate_a0.md
 M workflow-out/_probe_impl_a0.md
 M workflow-out/_probe_plan_r1_a0.md
 M workflow-out/implementation.md
 M workflow-out/plan.md
?? workflow-out/_implementation-prev-r1-backup.md
?? workflow-out/_implementation-prev-r2-backup.md
?? workflow-out/_implementation-prev-w1a-backup.md
?? workflow-out/_plan-prev-r4d1-backup.md
?? workflow-out/_plan-prev-r4d1-final-backup.md
?? workflow-out/_plan-prev-r4d2d3-backup.md
?? workflow-out/_pre-task-snapshot-r1.patch
?? workflow-out/_pre-task-snapshot-r2.patch
?? workflow-out/_pre-task-snapshot-r3.patch
?? workflow-out/_r4d2d3-verify-raw.txt
?? workflow-out/_submission-plan.md
?? workflow-out/demo-script.md
?? workflow-out/report/
?? workflow-out/slides/

$ git diff --name-only -- lyquid scripts agents experiments docs README.md
（空输出）

$ wc -l workflow-out/_submission-plan.md
779 workflow-out/_submission-plan.md

$ md5sum workflow-out/_submission-plan.md
b24acb49e22ff9281ce9a3688daad0e3 *workflow-out/_submission-plan.md

$ git log --oneline -1
8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)
```

**未运行（如实登记）**：`docker` / `scripts/demo.py` / `scripts/keeper.py` / `shaker deploy` /
`cargo` 全部未跑（纯文档任务，不产生新证据）；ZIP 未生成（方案冻结条款 6）；demo 未实拍；
B3 未开展；PDF/PPTX 目视复核未重跑（沿用 D1/D2+D3 轮记录）。

---

## 5. 偏离与差异登记

| # | 项 | 说明 | 处置 |
|---|---|---|---|
| **D1** | 重写 `workflow-out/implementation.md` | 工作流约定「实现说明写入 `workflow-out/implementation.md`」，但方案 §0 只列 3 件、§3-2 要求「清单之外零写入」；上一版（R4-D2+D3，208 行）**未入库、git 无法取回** | 按工作流约定重写（本文件）；改写前 `cp` + `md5sum`（`b421a199…`），**原版逐字保留于附录 A**；`git status` 该文件本就在 T0 基线（` M`），不新增条目；影响面仅内容 |
| D2 | T0 `git status` 19 条 vs 方案 §1-3 预列 18 条 | 差 1 = 规划期新建 `_plan-prev-r4d2d3-backup.md` | 以 T0 实跑为基线；`_submission-plan.md` §2.e-E7 登记 |
| D3 | ugrep 在 Windows 输出 CRLF | 直接 `grep -o` 入 `comm`/`test -f` 会把 13/34 份全部误报 MISS（`DIFF_LINES=26`） | b2/b3 命令统一 `tr -d '\r'` 并写明原因（§2.b）；误报已实测复现后修正 |
| D4 | HEAD 版 `implementation.md` §9.1 行数 477/143 | 现盘实取 481/144（8d093b5 改过两文档） | 属时点差异，`_submission-plan.md` §2.e-E2 仅登记，未改 |
| D5 | `report/README.md:133`（及 PDF 封面）裸指针 `implementation.md:28/:407/:511/:603` | 该文件只读冻结；指针只对 HEAD/R3 版（751 行）有效 | §2.e-E5 登记 + 给出 `git show 8d093b5:…` 取回命令；未改冻结文件 |
| D6 | `_commit-plan.md:1` 头部「未执行任何 git commit」 | 与 15 提交事实并存（时点语义） | §2.e-E1 登记；入库判定以 git 实跑为准 |
| D7 | `_pre-task-snapshot.patch`（无后缀）不在 `??` 面 | 已于 `dc78d2f` 入库（`git log -1 -- <f>` 实跑） | 已在 §1.5/§2.e 备注，非漏项 |
| D8 | demo 脚本 8 键未命中 / 幻灯片 2 键未命中 | 三文档侧重不同；形态差异（缩略哈希） | 判「未命中≠错误」，§2.a 登记 + 可选口播补充建议（**本任务未执行**） |
| D9 | ZIP 命令未执行 | 方案冻结条款 6 | §3.1 给两条可复制命令；工具可用性已实测 |

---

## 6. 红线自查

1. **零 git 写**：全程仅 `git log/status/diff/ls-files/show/rev-list/check-ignore`；开工与收尾 `git log --oneline -1` 均 `8d093b5`（§4-T7）。
2. **写入面**：`workflow-out/_submission-plan.md`（新建）+ `workflow-out/implementation.md`（工作流约定，附录 A 保留原版）；`plan.md` / `_plan-prev-r4d2d3-backup.md` 为规划期产物。
3. **未修改他阶段产物**：T7 `git status` 与 T0 基线逐条比对，状态行集合**只新增本文件**
   `?? workflow-out/_submission-plan.md`（19 → 20 条），其余 19 条逐字相同（其中 `implementation.md`
   内容被本轮改写，状态行不变，见 D1）；代码面 `git diff --name-only -- lyquid scripts agents
   experiments docs README.md` **空输出**。
4. **未跑项**见 §4 末（docker/demo/keeper/deploy/cargo/ZIP/实拍/B3/目视复核）。

---

## 7. 未尽清单（如实）

1. **ZIP 未生成**（D9）：两条命令已按本机工具链（PowerShell 5.1 + GNU tar 1.35，无 7z/zip）写死路径与步骤，但**未执行**，ZIP 内条目结构最终以人工运行为准。
2. **demo 未实拍**：305s 为设计值；S3 预期输出只静态命中 R1 档（`_r1-demo-normal-raw.txt:5/:6/:9`），录制当轮须以新实例实录为准。
3. **B3 未开展**：反馈收集表为空白表单，无已收集反馈（`_submission-plan.md` §3.3）。
4. **目视复核未重跑**：本轮只做程序化页数/notes 复验（§2.d），未重开 PDF/PPTX 逐页阅图。
5. **`report/README.md:133` 与 PDF 封面的裸指针**未修（只读冻结）：以 `git show 8d093b5:workflow-out/implementation.md` 取回为准（§2.e-E5）。
6. **`implementation.md` 改写**：见 D1，如不接受可用附录 A 逐字还原（md5 应与 `b421a1997fdfd160219a4789cf934278` 一致）。

---

## 附录 A：R4-D2+D3 实现说明原版（逐字保留）

> 本节为**上一版 `workflow-out/implementation.md`**（R4-D2+D3 实现说明，2026-10-30，208 行，
> md5 `b421a1997fdfd160219a4789cf934278`）的**逐字副本**。该版本未入库（`git status` 为 ` M`，不在 HEAD），
> 无法由 git 取回，为避免改写造成信息丢失原样保留；节内「方案」「§x」「verify-raw」等指代均指
> R4-D2+D3 方案及其证据，备份件为 `workflow-out/_plan-prev-r4d2d3-backup.md`。**本节不得回改**。

# R4-D2+D3 实现说明（编码员，2026-10-30）

> 方案：`workflow-out/plan.md`（R4-D2+D3，审查通过版；以下「§x」均指该文件）。
> 本轮任务 = **纯文档交付**：D2 幻灯片（≥10 页 `.pptx`，本方案定 12 页，每页 notes）+
> D3 预录 demo 分镜脚本（8 镜，305s）。**零 git 写操作**（全程只有 `git log` / `status` /
> `diff` 只读）；**不改代码目录**（`lyquid/`、`scripts/`、`docs/`、`experiments/`、
> `agents/` 零改动，`git diff --name-only` 空输出为证）。
> 构建/自检/逐条核对均为**本轮实跑**，原始输出全部入档
> `workflow-out/_r4d2d3-verify-raw.txt`（约 690 行）。
>
> **本轮按工作流约定重写了本文件（implementation.md）**：上一版为 R3 实现说明
> （md5 `f7033445e29ef8436fae8d4dc7cb170f`，751 行）。重写前实测
> `md5sum workflow-out/implementation.md` 与 `git show 8d093b5:workflow-out/implementation.md | md5sum`
> **两侧同值**，即 R3 版与 HEAD 跟踪版本逐字一致 → 可由
> `git show 8d093b5:workflow-out/implementation.md` 原样取回。
>
> **受影响引用（扩围说明，仲裁修订第 4 条）**：凡指向 R3 版 `implementation.md` 的「文件:行」
> 均不受本次重写影响，但必须**按 R3 版取回后核对**——① 期末报告 PDF 封面引用的
> `implementation.md:28-:31`（devnet / 工具版本行）与 `report/README.md:133` 的 §5 索引行
> （`:28、:407、:511、:603`）；② 幻灯片 P9 正文与 notes 的 `:603 / :511 / :28`、P3 notes 的
> 「§2 同源」；③ demo-script 的 S1 出处 `implementation.md:443`（同节 `:617`）与 §6 纪律里的
> `workflow-out/implementation.md §7.3`（D-T6-1 教训）。上述引用在本轮交付物中**一律加「R3 版」限定语**
> 并给出取回命令；`report/README.md` 与报告 PDF 按 `plan.md:27` **只读冻结、不回改**（其 :133 与
> 封面 :28-:31 引用由本段说明覆盖）。限定语落实后的裸指针自查与 S1 出处复核见 verify-raw §T9
> （`MENTIONS_TOTAL=19 / BARE_POINTERS=0`；交付树 grep rc=1、限定形 grep 命中 :443/:617）。
>
> 该重写不在方案 §0 的 7 件清单内，作为**偏离项**登记于 §5-D1。

---

## 0. 基线与环境（本轮实跑）

| 项 | 值 | 证据（verify-raw 段） |
|---|---|---|
| HEAD（开工） | `8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on fresh instance (T7)` | T1 |
| 工作树（开工） | 5 条 M（4 份评审探针档 + `plan.md`）+ 9 条历史未跟踪条目（含 `report/`），共 14 条；§0 的 7 件均不存在 | T1 |
| HEAD（收尾） | `8d093b5`（逐字不变） | T8 / T8.2 |
| Python | 3.14.5 | T2 |
| python-pptx | 1.0.2 | T2 |
| fontTools | 4.66.1（字覆盖检查） | T2 |
| PyMuPDF | 1.28.2（仅目视复核用） | T2 |
| 本机 grep | ugrep 7.8.4（Git for Windows；`-F` 固定串语义） | T2 |
| 目视复核工具 | LibreOffice 26.8.1.1（`soffice --headless --convert-to pdf`；版本取自 `soffice.exe` VersionInfo） | T4.2 |

工具链与方案 §8 规划期基线一致，**未触发**方案 §7-R1 的降级路径（marp/beamer）。

---

## 1. 逐文件改动（方案 §0 清单对照）

| # | 路径 | 动作 | 摘要 | 规模 |
|---|---|---|---|---|
| 1 | `workflow-out/slides/build_slides.py` | **新建** | 幻灯片唯一源文件：12 页全文 + speaker notes 内嵌为 Python 数据结构；python-pptx 构建；尾段同进程**重开产物**自检（页数 / 16:9 / notes / KEY_HITS / 三数口径护栏 / P5 退款链 / console 行宽 / 字体覆盖）。md5 `25ccb29fdad6d5189c3edfcf7102fc59` | 1,013 行 / 50,445 B |
| 2 | `workflow-out/slides/trustbridge-final-slides.pptx` | **新建（构建产物）** | 13.333×7.5 in（16:9）、12 页、每页 notes 非空；中文字体 Microsoft YaHei、console 块 Consolas；**不嵌入字体**。md5 `a2495e35786d6c17a91341a61235af9b`（含时间戳，重建即变） | 81,155 B |
| 3 | `workflow-out/slides/README.md` | **新建** | 构建/验证/复现命令与实跑输出、KEY_HITS 一致性核对表（12 页 → 出处）、字体不嵌入登记、降级路径登记（未触发）、差异登记 4 条（含 implementation.md 指针限定）+ D4 措辞登记。md5 `3f742722007c03ccff7f38126ddb3b69`（最终值，见 verify-raw §T9-④） | 242 行 / 14,741 B |
| 4 | `workflow-out/demo-script.md` | **新建** | D3 分镜脚本：8 镜（S0–S7）五列表 + 逐镜口播 + 占位符替换规则 + 录制技巧 + 预案 A/B + 纪律 + 时长判据 + 差异登记 7 条；S1 出处与 §6 纪律的 implementation.md 指针均加「R3 版…取回」限定。md5 `cd78c6471b4bfe55e5d92b5a97b34bb7`（最终值，见 verify-raw §T9-④） | 285 行 / 25,555 B |
| 5 | `workflow-out/_r4d2d3-verify-raw.txt` | **新建** | 验证实录：T1 开工基线 / T2 工具链 / T4 构建+自检+目视 / T5-T6 指纹 / T7 逐条 grep（65 项全 PASS）/ T7-b′ 三数口径 token 扫描 / T8+T8.2 收尾。**追加型实录，md5 与行数随追加变化，不写死** | 约 690 行 / 约 49 KB |
| 6 | `workflow-out/implementation.md` | **重写**（工作流约定；见 §5-D1） | 本文件 | — |

> **指纹口径**：`slides/build_slides.py`、`slides/trustbridge-final-slides.pptx`、
> `slides/README.md`、`demo-script.md` 的 md5 为**交付指纹**——以 verify-raw **§T9-④**（仲裁修订后的
> 重建/重写实跑值）为最终值；T5/T6、T8.2、T8.3 记的是各时点的历史值（指针限定语改动后已变）。
> 其中 `.pptx` 含时间戳、**重建即变**；`_r4d2d3-verify-raw.txt` 与 `implementation.md` 属
> 追加/修订型文档，不写死 md5。

只读引用（未改一字）：`workflow-out/report/README.md`（KEY_HITS 唯一事实源）、
`workflow-out/report/build_report.py`（构建模式参考）、R3 版 `implementation.md`、
`w1b2-*.md` 六件、`_r1-demo-normal-raw.txt`、`_r2-{normal-assess,keeper-loop,adversarial}-raw.txt`、
`_r3-t3-{console,committee,deploy}-raw.txt`、`_r3-t7-dt31-verify-raw.txt`、
`_r3-t4-{precheck,flows,gas,code-size,evidence-recheck,lyquid-scan}-raw.txt`、
`r3-t4-contrast-report.md`、`docs/b3-user-test/通过判据.md`、`scripts/demo.py:346-:357`、
`agents/common/rpc.py:91、:97`。

---

## 2. `build_slides.py` 实现要点（方案 §3 / §3.1）

### 2.1 结构
- 单文件、无外部数据依赖：12 个 `slide_NN(prs)` 函数各自内嵌标题 / 正文 / 表格行 /
  console 行 / notes；`SLIDE_BUILDERS` 顺序表 + `main()` 构建落盘 + `self_check()`。
- 版式：`blank` 版式（`slide_layouts[6]`）+ 自绘文本框；标题条（25pt 粗体 NAVY + 细横线）、
  页脚「TrustBridge · CS5298 · 2026-10-30 · 第 X / 12 页」。
- 表格：`shapes.add_table`，列宽按比例（P6 `[1.45, 4.3, 5.2]`，P8 `[1.55, 7.0, 3.7]`），
  表头 NAVY 底白字、正文行 `#F2F4F7` / 白交替。
- console 摘录：圆角浅底框 + `Consolas` 文本框，`word_wrap = False`（**长行不折断**）。
- notes：`slide.notes_slide.notes_text_frame.text = …`，写入后再统一设字体。

### 2.2 字体写法（冻结条款 6）
每个 run 同时写 `a:latin` / `a:ea` / `a:cs` 三处 `typeface`（`_set_run_font`）——只设
`font.name` 只管西文，中文会回退主题字体；三处同设才保证中文走 Microsoft YaHei。
**不嵌入**任何字体（无 `embedTrueTypeFonts`、无 fontdata part）。

### 2.3 尾段自检（重开产物；全过才 `BUILD_OK` + exit 0）
| 项 | 判据 | 本轮实跑 |
|---|---|---|
| (a) 页数 / 尺寸 | `len(slides)==12` 且 ≥10；13.333×7.5 | `PAGES=12`、`SLIDE_SIZE_IN=13.333 x 7.500 (16:9=True)` |
| (b) notes | 每页 notes 非空 | `NOTES_OK=True (empty=[])` |
| (c) KEY_HITS | 方案 §6 GT-b 候选 23 项在「全文本（含 notes）」命中 ≥15 | `KEY_HITS=23/23 (MIN=15)`、`MISSING=[]` |
| (d) 三数口径 | `9000`+`980`+`20`「独立数值」同现页 ⊆ {P8}；P5 含 `10000 → 9000 → 10000` | `TRIPLE_PAGES=[8] (allowed=[8])`、`P5_CHAIN=True` |
| (e) console 行宽 | 最长行 × 0.55em × 字号 ≤ 块内可用宽（不折行不出框） | P4：114 字符/784pt/858pt；P5：112 字符/739pt/858pt（页脚可见） |
| (f) 字体覆盖 | 全片去重字符 ⊆ msyh cmap（fontTools；缺字形方块预警） | `FONT_COVERAGE=UNIQUE_CHARS=628 MISSING_IN_MSYH=0 OK` |

「独立数值」正则用 `(?<![\d,])…(?![\d,])` 边界，避免 `19000` / `2026-10-30` / `2083` /
`3,707,457` 误判（这也是 GT-b′ 护栏能在 P5 与 P8 之外不误报的原因）。

### 2.4 与方案的差异（细节见 `slides/README.md` §4）
- §3.1 假设「摘录行 ≤100 字符」；P4 的 `cert.signers RAW …` 实录行实为 **114 字符**。
  处置：**不改写实录行**，改用 12.5pt Consolas + 程序化行宽预检（§2.3-e）保证不折行。
- 目视复核为本轮**额外**手段（方案 GT 未要求），结论见 verify-raw T4.2。

---

## 3. `demo-script.md` 实现要点（方案 §4）

- **8 镜 / 305 秒**：S0 20 + S1 20 + S2 40 + S3 60 + S4 45 + S5 60 + S6 40 + S7 20 = 305s
  （5 分 05 秒，落在 240–360；表后附合计行与判据说明）。
- **五列表**：镜号 / 画面 / 命令（逐字 + 「文件:行」）/ 预期输出（对齐实录 + 行号）/ 时长；
  表后每镜一小节写口播 2–3 句；S3 口播点 R1 三数（9000/980/20），S5 口播点 funding 中间态
  （`10000 → 9000 → 10000`，全额退款）。
- **S4 = 实录回放**（方案仲裁修订 1）：无执行命令，画面即 `_r2-keeper-loop-raw.txt`；keeper.py
  命令降为「讲解行，不执行」并给 `:3` 形态与 `:2`/`:7` 实例地址；预期输出 :6/:8/:10/:30/:31-32。
- **S5 = T7 主命令**（方案仲裁修订 2）：主命令取 `_r3-t7-dt31-verify-raw.txt:3`（去
  `# command: ` 前缀）；预期 :22/:28/:30/:31/:69/:72-73。T3 档降为可选回放（不执行），
  若展示**必须补** `:41` RuntimeError 与 `:43` exit=1 并加字幕「D-T3-1 修复前档案」。
  console 命令取 `_r3-t3-console-raw.txt:2`，预期 :24/:31/:36/:38。
- **S3 单一口径**（方案冷读修订 7）：`<addr>` = S2 当轮新部署实例地址；
  **禁填** `0xFD6F…c351`；**禁引** `_r2-normal-assess-raw.txt:12-:13`（已用实例 deal-9）；
  条件分支写明「复用已 Up 实例时余额不得引 R1 三数」。
- **占位符**：`<addr>` / `<实例名>` / `<新名>` / `<新地址>` / `<ANVIL0_KEY>` 逐条给替换规则；
  全钥来源 `agents/common/rpc.py:97`（`:90` 注明 devnet 公开确定性密钥、非生产凭据），
  但脚本正文只写 `<ANVIL0_KEY>`，实录行按 R2 先例脱敏（`_r3-t3-deploy-raw.txt:59`）。
- **技巧 / 预案 / 纪律**：字号 ≥18pt、每镜独立起止、S5 双终端、console 流式回放与
  `rc=124` 正常收尾、预案 A（devnet 不可用 → 全实录回放）、预案 B（逐镜重录点，S4 无重录点）、
  单次纪律（禁重复 `e2_arm` / `e2_run_verdict_round`）、`MSYS_NO_PATHCONV=1`、实例不混称。
- **差异登记 7 条**（含 S1 命令实际行号 `implementation.md:443`、容器名带 compose 后缀、
  S2 命令三行注释形态拼回单行、密钥脱敏、S3 预期来源只能静态命中 R1 档、**3 分钟版剪辑点**
  与课程原文（方向总结:24「3 分钟预录 demo」）的口径差、时长为设计值未经实拍）。

---

## 4. 命令与输出摘要（全部本轮实跑；完整原文见 `_r4d2d3-verify-raw.txt`）

| 步骤 | 命令（逐字） | 关键输出 | 段 |
|---|---|---|---|
| T1 基线 | `git log --oneline -1` + `git status --short` | `8d093b5 …`；14 条既有条目（5 M + 9 ??）；§0 七件不存在 | T1 |
| T2 工具链 | `python -c "import pptx; print(pptx.__version__)"` 等 | `1.0.2` / `Python 3.14.5` / `fontTools 4.66.1` / `pymupdf 1.28.2` | T2 |
| T4 构建 | `python workflow-out/slides/build_slides.py` | `BUILD_OK`、`EXIT=0`、`PAGES=12`、`KEY_HITS=23/23`、`TRIPLE_PAGES=[8]`、`P5_CHAIN=True`、`FONT_COVERAGE … MISSING_IN_MSYH=0 OK` | T4 |
| T4.1 复核 | `python -c "from pptx import Presentation; …"` | `PAGES 12` / `NOTES_ALL True` / `SIZE_IN 13.333 7.5` | T4.1 |
| T4.2 目视 | `soffice --headless --convert-to pdf …` + PyMuPDF 落图 | `PDF_PAGES 12`；12 页 PNG 逐页阅图（修正 3 处视觉问题） | T4.2 |
| T7 逐条核对 | `grep -nF -- <literal> <raw-file>` × 65 | `CHECKS_TOTAL=65 FAILS=0`（13 命令 + 5 关键输出 + 6 代码块逐行 + 禁引反向 + KEY_HITS 三方） | T7 |
| T7-b′ 口径 | token 扫描（`9000/980/20` 独立数值） | 同现页 = {P8}；P5 的 9000 全为 funding 中间态/退款链语境；非 P5/P8 只命中「20」（行号/工作量表述） | T7-b′ |
| T8 收尾 | `git log --oneline -1` + `git status --short` + `git diff --name-only` | HEAD 仍 `8d093b5`；新增仅 `?? workflow-out/slides/`、`?? workflow-out/demo-script.md`（+ 本文件与 verify-raw）；代码目录 `git diff` 空 | T8 / T8.2 |
| T9 仲裁修订（指针限定 + 重建） | ① `python workflow-out/slides/build_slides.py`（重建）② `grep -nF -- 'docker ps --format "{{.Names}} {{.Status}}"' workflow-out/implementation.md` ③ `git show 8d093b5:workflow-out/implementation.md \| grep -nF 'docker ps --format "{{.Names}} {{.Status}}"'` ④ 裸指针自查脚本 | ① `BUILD_OK`/`EXIT=0`、`PAGES=12`、`KEY_HITS=23/23`、`TRIPLE_PAGES=[8]`、`P5_CHAIN=True`、`SIZE_BYTES=81155`；② **rc=1（无输出）**——交付树已无该行（T8.2 重写所致，见 D1）；③ 命中 `:443`、`:617`，`rc=0`；④ `MENTIONS_TOTAL=19 / BARE_POINTERS=0` | T9（T9-0/①②③④） |

未运行（如实登记）：任何 `docker` / `python scripts/demo.py` / `scripts/keeper.py` /
`shaker deploy` / `cargo` 命令 —— 本轮为纯文档任务，**不产生新的链上证据**，
所有预期输出一律引用既有档案。

---

## 5. 偏离与差异登记

| # | 项 | 说明 | 处置 |
|---|---|---|---|
| **D1** | 重写 `workflow-out/implementation.md` | 工作流约定「实现说明写入 workflow-out/implementation.md」，但方案 §0 只列 7 件、冻结条款 3 要求「清单之外零写入」，且 R3 版 implementation.md 是报告与 P9 的只读取证源 | 按工作流约定重写（本文件）；重写前实测 R3 版 md5 与 `git show 8d093b5:workflow-out/implementation.md` 一致（`f7033445…`），**可原样取回**；影响面：`git status` 新增 ` M workflow-out/implementation.md`（方案 GT-e 未列此项） |
| D2 | console 摘录行宽 | 方案 §3.1 假设 ≤100 字符；实录行 114 字符 | 不改写实录；12.5pt + 行宽预检（`slides/README.md` §4-1） |
| D3 | 目视复核 | 方案 GT 未要求 | 额外用 LibreOffice 转 PDF + 落图复核；据其修正 3 处视觉问题（反引号 / 留白 / `⇒` 缺字形） |
| D4 | P8 notes 反例句措辞 | 原句「R2 对抗流档内没有 9000/980/20 这组三元组」在同一句堆了三数与 R2 | 改为「没有这组三数」，消除机械误读（GT-b′ 人工复核要求） |
| D5 | 3 分钟版 | 课程原文 demo 上限 3 分钟（方向总结:24），方案判据 5±1 分钟 | 主设计按方案 305s；`demo-script.md` §7 附 180 秒剪辑点，供课程硬性上限时使用 |
| D6 | 时长未经实拍 | 8 镜时长为设计值 | `demo-script.md` §8-7 登记；实拍超 360s 的压法已给 |
| **D7** | implementation.md 指针限定语（仲裁修订） | D1 重写后，交付物里指向 R3 版的裸指针（`implementation.md:443/:617/§7.3/§2/:28/:511/:603`）会落到新文件上 | 全部改为「R3 版…`git show 8d093b5:workflow-out/implementation.md` 取回」限定形；`report/README.md` 与报告 PDF 按 `plan.md:27` 只读冻结不回改（其 :133 与封面 :28-:31 由本文件 §0 扩围说明覆盖）；自查 `BARE_POINTERS=0`（verify-raw §T9-③），并按修订要求重建 + 复跑自检（§T9-0） |

无「与 KEY_HITS 不一致」的数字：幻灯片 23 项 KEY_HITS 全部命中（`MISSING=[]`），
demo-script 的数字与 KEY_HITS/README 逐条三方核对通过（T7-5 `KEY_HITS_MISMATCH=[]`）。

---

## 6. 门禁总表（方案 §6，逐项如实登记）

| 门 | 判据 | 状态 | 依据（verify-raw） |
|---|---|---|---|
| GT-a | `.pptx` 存在、≥10 页（方案值 12）、每页 notes 非空 | **满足** | T4 `PAGES=12`、`NOTES_OK=True`；T4.1 独立复核 `PAGES 12 / NOTES_ALL True` |
| GT-b | KEY_HITS 字面值抽查 ≥15 项命中 pptx 全文本（含 notes） | **满足** | T4 `KEY_HITS=23/23 (MIN=15)`、`MISSING=[]` |
| GT-b′ | 三数口径：三数同现页 ⊆ {P8}；P5 含 `10000 → 9000 → 10000`；全片无「R2 且三数」表述 | **满足** | T4 `TRIPLE_PAGES=[8]`、`P5_CHAIN=True`；T7-b′ token 扫描 + 人工复核 (a)–(d) |
| GT-c | 分镜表时长合计 240–360s | **满足**（设计值 305s） | `demo-script.md` §7 合计行；**未经实拍计时**（D6） |
| GT-d | 每条命令带「文件:行」且 `grep -nF` 逐字命中；S4/S5/S3 预期输出行逐一命中 | **满足**（S1 出处为限定形，见脚注 †） | T7 `CHECKS_TOTAL=65 FAILS=0`（13 命令 + 5 关键输出 + 6 代码块逐行 + 禁引反向 + 三方对表）；† 见 verify-raw §T9-①② |
| GT-e | 收尾 HEAD 仍 `8d093b5`；`git status` 新增仅 §0 清单件 | **基本满足（1 项登记）** | T8/T8.2：HEAD 不变、代码目录 diff 空、新增仅 slides/ + demo-script.md（+ verify-raw、+ implementation.md=M，见 D1）；T9 修订只涉及 workflow-out/ 内文件，未新增 status 条目 |
| GT-f | 差异登记段：与 KEY_HITS 不一致处、降级如实列表 | **满足** | `slides/README.md` §4（4 条，含 D7 指针限定 + D4 措辞）；`demo-script.md` §8（7 条）；本文件 §5（7 条 D1–D7）；降级路径**未触发** |

† **GT-d 脚注（S1 出处）**：S1 的 `docker ps --format "{{.Names}} {{.Status}}"` 出处指向 R3 版
`implementation.md:443`（同节 `:617`）。T7 段执行时该行在交付树中可直接命中（当时 implementation.md
尚为 R3 版）；T8.2 重写（D1）后交付树 grep 已 rc=1，故 T9 段按修订要求复跑：交付树 `grep -nF` →
**rc=1**（无输出，预期），限定形 `git show 8d093b5:workflow-out/implementation.md | grep -nF '…'` →
命中 `:443`/`:617`、`rc=0`（PASS）。详见 verify-raw §T9-①②。

---

## 7. 未尽清单（如实）

1. **未实拍**：本脚本的 8 镜时长为设计值；实拍计时、口播磨合、字幕排版均未做（D6）。
2. **3 分钟版未剪**：仅给剪辑点，未产出第二版分镜。
3. **S3 的当轮实录未产生**：S3 预期输出只能静态命中 R1 档（`_r1-demo-normal-raw.txt:5/:6/:9`）；
   录制当轮须再以新实例实录为准（方案 GT-d 明示）。
4. **未跑 devnet / demo / keeper / deploy**：本轮无链写授权，不产生新证据（§4 末行）。
5. **字体只在构建机实测**：`FONT_COVERAGE` 只证明本机 msyh 覆盖 630 字符；目标机缺
   Microsoft YaHei 时的替代表现已登记（`slides/README.md` §6），未在多机验证。
6. **`implementation.md` 重写**：见 D1，若不接受可用 `git show 8d093b5:workflow-out/implementation.md`
   恢复 R3 版（与重写前逐字一致）。

