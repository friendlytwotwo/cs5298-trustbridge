# R4-D4 方案：提交清单与全量交叉复核（规划师，2026-10-30）

六阶段拆分⑥：**纯文档收尾任务**——产出 `workflow-out/_submission-plan.md` 一份
（ZIP 内容清单 + 全量交叉复核 + 人工待办清单）。
铁律：**零 git 写操作**（不 commit/add/push/branch/tag/restore/stash；仓库定格
`HEAD=8d093b5`，本任务全程只读引用 git）；**产物只写新文件**；不碰
`lyquid/`、`scripts/`、`docs/`、`experiments/`、`agents/`（只读引用允许，零写入）；
**诚实红线**：复核结果如实登记，发现不一致**只登记不修改**他阶段产物。

## 0. 受影响文件清单（3 项，供审查员核对）

| # | 路径 | 动作 | 说明 |
|---|---|---|---|
| 1 | `workflow-out/plan.md` | 覆盖写 | 本方案；覆盖前旧 R4-D2+D3 方案已备份（#2） |
| 2 | `workflow-out/_plan-prev-r4d2d3-backup.md` | 新建（备份） | 规划期已执行：`cp` 复制旧 plan.md，md5 `529920260968386051db3eb75078e122` 两侧一致（实跑输出在案） |
| 3 | `workflow-out/_submission-plan.md` | 新建 | **本任务唯一交付产物**（§1 ZIP 清单 + §2 交叉复核 + §3 人工待办） |

只读素材（不改，编码期引用）：`report/README.md`（KEY_HITS 唯一事实源）、
`slides/README.md`、`demo-script.md`、`_commit-plan.md`、`implementation.md`（盘上 208 行
R4-D1 版）、`w1b2-*` 13 份、`_r1/_r2/_r3/_r4d2d3-*` 原始日志、`_r3-t3-deploy-raw.txt` 等
抽查目标日志、`_plan-prev-r2/r3/r3t4/r3t5t6/r4d1-final-backup.md`（终裁记录定位）、
`docs/b3-user-test/` 三份（**只读**引用其文件名与行数，零写入）、
`report/trustbridge-final-report.pdf`、`slides/trustbridge-final-slides.pptx`。

## 1. 规划期实跑核实的前置事实（编码员直接采信，标 ✅ 者编码期须复跑）

1. ✅ `git log --oneline -1` = `8d093b5 R3 evidence: D-T3-1 fix E2E re-verification on
   fresh instance (T7)`（仓库定格确认）。
2. **已入库面**（2026-10-30 规划期实跑）：`git log --oneline dc78d2f..HEAD` = **15 个提交**
   （acb7315/f36d24e/e43d8d2/c31d701 = R1-C1..C4；6f8f82a/785a944/efc256c = R2-C5..C7；
   c150d31/5634880/d1e6f5f/944a5a1/826fa50/3af0460 = R3-C1..C6；d292012 = 归档；
   8d093b5 = T7 复验）——与 `_commit-plan.md` C1–C7+R3 分组一一对应，任务书"已全部
   落库"属实。**注意**：`_commit-plan.md` 头部仍写"未执行任何 git commit"——这是其
   撰写时点（基线 dc78d2f）的时点语义 + 原文快照不改的勘误惯例，**如实登记、不修改**，
   入库判定一律以 git 实跑为准。
3. **在盘未入库清单**（规划期 `git status --short` 实跑，trustbridge 范围）：
   ` M workflow-out/{implementation.md,plan.md,_probe_cold_a0.md,_probe_gate_a0.md,
   _probe_impl_a0.md,_probe_plan_r1_a0.md}`；`?? workflow-out/{report/,slides/,
   demo-script.md,_r4d2d3-verify-raw.txt,_plan-prev-r4d1-backup.md,
   _plan-prev-r4d1-final-backup.md,_implementation-prev-*(3),_pre-task-snapshot-*.patch(3)}`。
   **即 R4-D1/D2/D3 全部交付物尚未入库**（8d093b5 之后无提交）——这是 §3 提交前检查单
   的关键项，入库决策属人工待办，本任务不 commit。
4. `w1b2-*` 13 份**全部已入库**（`git ls-files workflow-out/ | grep w1b2` 实跑 16 命中，
   其中 13 份为 w1b2-* 证据/基线文件；6 份早期件在 dc78d2f 已入库，7 份 R1–R3 件在
   dc78d2f..8d093b5 入库——编码期逐份 `git log --oneline -1 -- <file>` 实取落表）。
5. `implementation.md` HEAD 版 751 行（R3 版），盘上 208 行为 R4-D1 重写版（未入库）；
   `_plan-prev-r4d1-final-backup.md` 引用的仲裁段行号（:347-:361、:663-:696）指 HEAD 版，
   编码期用 `git show HEAD:workflow-out/implementation.md | sed -n '<行号>p'` 只读取回。
6. 终裁记录候选位置（规划期 grep 定位，编码期 `grep -n` 精确到行）：
   R2 → `_plan-prev-r2-backup.md:279`（§10 终裁采纳项对照）；R3 →
   `_plan-prev-r3-backup.md:9`（终裁定稿冻结条款六条）；T4 →
   `_plan-prev-r3t4-backup.md`（含对 R3 备份的引用声明 :4/:14）；T5T6 →
   `_plan-prev-r3t5t6-backup.md:48、:73`（终裁维持性指令 1–3）；D1 →
   `_plan-prev-r4d1-final-backup.md`（终裁官定稿；角色表 :139-:144、佐证材料段 :146-:148）。
7. KEY_HITS 事实源 = `report/README.md` §3(b)：**27 键**（tx hash 1、gas/金额数字 20、
   地址 3、selector 1、字面值 2、`8d093b5`、`2026-10-30` 等），命令逐字在
   `report/README.md:71`；slides 自验口径为 23 键 MIN=15（`slides/README.md` §2 输出
   `KEY_HITS=23/23`），与本任务 27 键口径不同属正常，登记说明即可。
8. 环境可用（先例登记）：pypdf 6.19.0、python-pptx 1.0.2、Python 3.14.5
   （`report/README.md` §1 / `slides/README.md` §1）；编码期先复跑版本探测再跑复核。

## 2. 目标与完成判据

**目标**：交付 `workflow-out/_submission-plan.md`，含三大块——
(1) ZIP 内容清单（主交付三件 + 已入库代码面 + w1b2-* 证据索引 + 其余证据归组，
每项标来源路径与入库状态）；
(2) 全量交叉复核 **a/b/c/d 四项全部实跑命令**（非目测），输出逐字入档，不一致只登记；
(3) 人工待办清单（ZIP 打包命令 / 11·19 12:00 截止检查单 / B3 安排 / demo 实拍提示 /
终裁记录五份位置索引）。

**完成判据**：
- GT-a：§2.a 27 键 × 3 文档命中矩阵完整（每键×每文档有 命中/未命中/冲突 三态之一），
  冲突项给出"以 KEY_HITS 为准"的修正建议且**未改动任何他阶段产物**；
- GT-b：§2.b 双向核对输出在档：索引所指文件 100% 在盘、在盘 w1b2-* 100% 被索引
  （`comm` 双向零差异）；
- GT-c：§2.c 抽查 15 条（其中命令级 ≥5，本方案定命令级 9 + 输出级 6），每条给出实跑
  `grep -nF` 命令与输出；
- GT-d：§2.d pypdf `PAGES=12`、python-pptx `SLIDES=12` 逐字输出在档；
- GT-e：§3 五项人工待办齐全，ZIP 命令可直接复制执行；
- GT-f：收尾 `git log --oneline -1` 仍为 `8d093b5`；相对 T0 基线新增文件仅
  `_submission-plan.md`（+规划期已产生的 `_plan-prev-r4d2d3-backup.md` 与本方案覆盖的
  `plan.md`），`git status` 差异逐条登记；全程零 `git add/commit/push`。

## 3. 冻结条款（编码员必守）

1. **零 git 写**：仅允许 `git log` / `git status` / `git diff` / `git show` / `git ls-files`
   只读命令；开工与收尾各存证 `git log --oneline -1` + `git status --short`。
2. **只写 §0 清单 3 个文件**：除此之外零写入；**不得修改**任何 R0–R3/R4-D1/D2/D3 产物
   （含 README、demo-script、证据、日志、备份件、探针件）。
3. **数字唯一事实源 = `report/README.md` KEY_HITS 27 项**；三数口径铁律沿用
   （R1 分账 9000/980/20；R2 结算 bob +980/broker +20；R3 funding 中间态
   9000 = 10000→9000→10000）——发现文档冲突只登记 + 给修正建议，不擅改。
4. **不虚构**：所有复核结论必须附实跑命令与输出；跑不了的如实写"未跑+原因"。
5. 抽查与清单中的每一行"入库状态"必须来自实跑 `git ls-files` / `git log --oneline -1
   -- <file>` / `git status`，禁止凭记忆或凭 `_commit-plan.md` 文字直接采信。
6. ZIP 打包命令只写入待办清单供人工执行，**本任务不生成 ZIP**。

## 4. 子任务拆分与执行顺序（T0–T7）

### T0 基线存证（开工第一动作）
`git log --oneline -1`（期望逐字 `8d093b5 …(T7)`）；`git status --short` 全文存证
（作为收尾比对基线，即 §1-3 清单）；`python -c "import pypdf,pptx; print(pypdf.__version__,
pptx.__version__)"` 探测环境（期望 pypdf 6.19.0 / pptx 1.0.2 量级）。

### T1 已入库面数据采集（只读 git）
- `git log --oneline dc78d2f..HEAD`（15 提交序列，逐字入档）；
- `git diff --name-status dc78d2f..HEAD`（已入库代码+文档逐文件清单，A/M 状态）；
- `git ls-files workflow-out/`（tracked 面）；对 w1b2-* 13 份逐份
  `git log --oneline -1 -- workflow-out/<file>`（入库提交号）。

### T2 复核 a：三文档数字一致性（27 键命中矩阵）
- 报告：**逐字复跑** `report/README.md:71` 的 pypdf 命令 → 期望 `KEY_HITS=27/27`；
- 幻灯片：python-pptx 提取全部 12 页——递归遍历 shapes（GROUP 形状递归进入；当前版
  无组形状，属前瞻）；每 shape 取 `has_text_frame` 文本；`has_table` 的 GraphicFrame
  逐行逐格取 `cell.text`（仲裁实跑证实 P6、P8 各 1 张表）；notes 非空页纳入（沿用
  `_r4d2d3` 先例口径）。对 27 键逐键 `in` 判断后，对照 `slides/README.md:169-182`
  分页映射复核：P6 的 `3,707,457` / `407` / `2083` / `1323` / `2933` / `2173` 六键必须
  =「命中」且命中页 = P6；若仍报未命中即提取器漏了表格，**不得登记为文档未命中**。
  两处诚实未命中如实登记并注明形态原因：`0x85e4…`（P8 为 `0x85e4e39b…0838` 缩略
  展示形态，`slides/README.md:178`）、`第 5 节`（幻灯片无此字面，三文档侧重不同）；
  均不构成冲突（下条「未命中≠错误」口径不变）；
- demo 脚本：`demo-script.md` 全文对 27 键逐键 `grep -cF`；
- 输出 27×3 矩阵（命中/未命中/冲突）；**未命中≠错误**（三文档侧重不同），仅当
  "同一数据点在文档中出现且值与 KEY_HITS 不同"才登记冲突 + 以 KEY_HITS 为准的修正建议。

### T3 复核 b：证据索引齐套性（双向）
- b1 索引→盘：提取 `report/README.md` §5 表"出处"列的全部文件名（grep -o 去 `:行号`），
  逐个 `test -f`；缺失者登记；
- b2 盘→索引（w1b2 范围）：`ls workflow-out/w1b2-* | sort` 与 `_submission-plan.md`
  §1.3 索引集合 `comm -3` 双向比对，要求零差异；
- b3 w1b2 索引行"对应原始日志"列的每个 `_r*` / `w1a*` 文件 `test -f`。

### T4 复核 c：demo-script.md 可复制性抽查（15 条 = 命令级 9 + 输出级 6；命令级 ≥5 达标）
分两级：**命令级** = 对实录 `# command: ` 前缀后的命令串 `grep -nF`（占位符按
`demo-script.md` §3 规则；口径沿用 `_r4d2d3-verify-raw.txt` §T7-1 :128-206）；
**输出级** = 对预期输出行 `grep -nF`。抽查表每行标「命令级/输出级」。

命令级 9 条：
1. S2-① `docker exec multi-tools rm -rf /tmp/tb-lyquid` → `_r3-t3-deploy-raw.txt:57`；
2. S2-② `MSYS_NO_PATHCONV=1 docker cp lyquid/. multi-tools:/tmp/tb-lyquid` → `:58`；
3. S2-③ 片段 `docker exec -w /tmp/tb-lyquid multi-tools cargo check --target
   wasm32-unknown-unknown` → `:125`（该 `# command:` 行前段另有 `touch`，按片段命中并登记）；
4. S2-④ deploy 参数序片段 `--endpoint ws://node1:10087/ws` → `:59`（三行注释形态，
   按片段命中并登记）；
5. S2 备路径片段 `docker exec multi-tools shaker to-hex` → `:581`；
6. S3 `python scripts/demo.py --node http://127.0.0.1:10087 --contract <addr> --flow normal`
   → `_r2-normal-assess-raw.txt:3`（`<addr>` 为实录内字面占位符，逐字 grep）；
7. S4 `python scripts/keeper.py --node http://127.0.0.1:10087 --contract <addr> --deals
   deal-3 --interval 5` → `_r2-keeper-loop-raw.txt:3`；
8. S5-① T7 主命令 → `_r3-t7-dt31-verify-raw.txt:3`；
9. S5-② console 命令 → `_r3-t3-console-raw.txt:2`。

输出级 6 条（补充项）：
10. S1 输出形态 `multi-tools` 容器行 → `_r3-t4-precheck-raw.txt:5-:12`；
11. S2 预期 `[deploy exit=0]` → `_r3-t3-deploy-raw.txt:86`；
12. S3 预期 `final state=Settled balances: alice=9000 bob=980 broker=20` →
    `_r1-demo-normal-raw.txt:6`；
13. S4 预期 `ATTRIBUTION VERDICT: PASS` → `_r2-keeper-loop-raw.txt:30`；
14. S5-① 预期 `refund check OK: alice 10000 -> 9000 (after fund) -> 10000` →
    `_r3-t7-dt31-verify-raw.txt:31`；
15. S5-② 预期 `cert.signers RAW = [0, 1, 2, 3]` → `_r3-t3-console-raw.txt:31`。

可选（不强制、不计入 ≥5）：S1 命令级——命令源**只认 HEAD**：`git show
8d093b5:workflow-out/implementation.md` 的 `:443`/`:617`（仲裁已实跑核实在案）；
**不得**对盘上 208 行版直接 grep：其仅有的命中 `:153`（T9 验证记录行，该行自身载明
当时交付树 grep rc=1）与 `:190`（脚注）均非命令源；不列入则 S1 维持输出级（#10）。
未命中者如实登记（对照 `_r4d2d3-verify-raw.txt` §T7 的 D2D3 期校验记录解释差异）。

### T5 复核 d：可打开性复验
- `python -c "import pypdf; r=pypdf.PdfReader('workflow-out/report/trustbridge-final-report.pdf'); print('PAGES=%d'%len(r.pages))"` → 期望 `PAGES=12`；
- `python -c "from pptx import Presentation; p=Presentation('workflow-out/slides/trustbridge-final-slides.pptx'); print('SLIDES=%d'%len(p.slides)); print('NOTES_EMPTY=%s'%[i for i,s in enumerate(p.slides,1) if not (s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip())])"` → 期望 `SLIDES=12`、`NOTES_EMPTY=[]`。

### T6 撰写 `workflow-out/_submission-plan.md`（唯一交付产物，章节规格见 §5）

### T7 收尾自查与存证
复跑 `git log --oneline -1`（仍 `8d093b5`）+ `git status --short`，与 T0 基线逐条比对；
确认新增文件仅 `_submission-plan.md`；`md5sum` 交付三件（PDF/PPTX/demo-script）登记；
差异登记表收尾。

## 5. `_submission-plan.md` 章节规格（逐节内容要求）

- **§0 头部**：方案出处（本文件）、生成日期 2026-10-30、基线 HEAD 存证、纪律执行声明
  （零 git 写 / 只登记不修改 / 抽查与状态全来自实跑）。
- **§1 ZIP 内容清单**：
  - 1.1 主交付三件：`report/trustbridge-final-report.pdf`（12 页，md5 复算）、
    `slides/trustbridge-final-slides.pptx`（12 页 16:9）、`demo-script.md`（8 镜 305s），
    各标来源路径 + 入库状态（三件均在盘**未入库**，见方案 §1-3）；
  - 1.2 已入库代码文件清单：T1 实取的 `git diff --name-status dc78d2f..8d093b5` 逐文件 +
    归组（C1–C7+R3 对照 `_commit-plan.md` §2/§5/§6）+ 15 提交序列 + `_commit-plan.md`
    头部时点语义的登记说明；
  - 1.3 证据索引：w1b2-* 13 份逐份一行（文件名 / 一行说明取自各文件头部或
    `report/README.md` §5 对应行 / 对应原始日志（各 w1b2 文档内引用的 `_r*` 档）/
    入库提交号）；`w1b2_t3_replay.py` 与两份 `_plan-prev-w1b2*` 备份单列说明（非证据件）；
  - 1.4 其余证据/日志归组总表：`_r1-*`(13)/`_r2-*`(15)/`_r3-*`(26)/
    `_r4d2d3-verify-raw.txt`/`w1a-*`/`w1b1-*`/`t0-*` 按组一行（组内计数 + 归属
    `_commit-plan.md` §6.1 组号 + 已入库状态），不逐份展开散文；
  - 1.5 在盘未入库清单（R4 产物 + 备份 + patch 三类）→ 指向 §3.2 提交决策待办。
- **§2 全量交叉复核**：2.a 命中矩阵 + 冲突登记与修正建议；2.b b1/b2/b3 逐字输出；
  2.c 15 条抽查表（镜号/内容/出处/级别/实跑命令/结果）；2.d 两条页数命令输出；
  2.e 不一致登记总表（编号/位置/事实/建议/处置状态=「仅登记，未修改」）。
- **§3 人工待办清单**：
  - 3.1 ZIP 打包命令建议：给两条可复制路径（PowerShell `Compress-Archive` 显式清单 /
    `git archive 8d093b5` 导出已入库代码面再叠加 workflow-out 交付件），含建议纳入
    文件全集（1.1 三件 + implementation.md 现版 + r3-t4-contrast-report.md +
    docs/b3-user-test/ 三件 + 已入库代码面），并提示 ZIP 内路径结构；
  - 3.2 提交前检查单（**11/19 12:00 截止**）：R4 产物入库决策（1.5 清单）、2.a 冲突项
    人工修正执行、PDF/PPTX 终验、demo 实拍完成、B3 反馈回收、终裁记录复核签认；
  - 3.3 B3 线下测试安排：三份文件（操作手册 481 行/通过判据 144 行/反馈收集表 123 行，
    规划期 `wc -l` 实测）+ 当前状态（反馈表为空白表单、无已收集反馈——
    `implementation.md` §9.1 #6 口径）+ 建议安排（11/19 前留出回收与整理窗口）；
  - 3.4 demo 实拍提示：**S3 当轮新实例实录需录制时产生**（demo-script.md §8-5：静态
    预期命中 R1 档，录制当轮以新实例实录为准；§3 占位符替换规则）；S1/S2 同理以当轮
    输出为准；单次纪律（§6-1）与 `MSYS_NO_PATHCONV=1`（§6-2）；预案 A/B 指引；
  - 3.5 终裁记录复核清单（五份位置索引）：R2/R3/T4/T5T6/D1 → 方案 §1-6 候选位置，
    编码期 `grep -n "终裁"` 各备份件精确定行成表；附 implementation.md HEAD 版
    仲裁修订登记段（`git show HEAD:workflow-out/implementation.md` 的 :347-:361、
    :663-:696 只读取回核对）。
- **§4 命令附录**：§2 全部命令逐字集中列出，供人工一键重跑。
- **§5 红线自查**：零 git 写前后存证对比、新增/覆盖文件清单（3 项）、未修改他阶段
  产物声明、未能执行的检查及原因（如有）。

## 6. 风险与回退

| # | 风险 | 缓解 | 回退 |
|---|---|---|---|
| 1 | 交叉复核发现文档间数字冲突（KEY_HITS vs 幻灯片/demo） | 只登记 + 以 KEY_HITS 为准的修正建议，留 §3.2 人工执行；不擅改 | 无需回退（零修改） |
| 2 | `_commit-plan.md` 头部"未执行任何 git commit"与实际入库矛盾引发误读 | §1.2 登记时点语义说明（撰写于 dc78d2f 基线 + 快照不改惯例），入库以 git 实跑为准 | 同上 |
| 3 | pypdf/python-pptx 环境异常导致 2.a/2.d 跑不了 | T0 先探测版本；异常则如实登记"未跑+原因+先例记录（README §1 曾成功）"，不得伪造输出 | 人工环境修复后按 §4 附录重跑 |
| 4 | 覆盖 plan.md 造成信息丢失 | 规划期已完成 cp 备份 + md5 双侧一致（§0-#2） | `cp _plan-prev-r4d2d3-backup.md plan.md` 即可逐字节还原 |
| 5 | 抽查 grep 未命中（日志行号漂移/形态差异） | 如实登记未命中 + 对照 `_r4d2d3-verify-raw.txt` §T7 解释；必要时同型片段命中并注明口径 | 无需回退 |
| 6 | 证据文件面大（~130 份）误判入库状态 | 全部机械命令实取（ls-files/log -1），逐份落表，不逐份人读 | 单份重跑 `git log -1 -- <file>` 纠正 |
| 7 | 误写他阶段产物（README/证据/备份） | 冻结条款 2 + T7 收尾 `git status` 与 T0 基线逐条比对，任何计划外 M/?? 触发回查 | `git diff` 确认后手工还原（内容均已在 HEAD 或备份中） |
| 8 | 误执行 git 写命令 | 冻结条款 1 白名单；T7 存证 HEAD 不变 | 本任务无 git 写需求，若误执行立即报告人工（不自行 reset 掩盖） |

## 7. 验收口径（审查员对 GT-a…GT-f 逐条核）

以 §2 完成判据为准：矩阵完整、双向零差异、15 条抽查（命令级 ≥5）有实跑输出、两条页数
命令逐字输出、五项待办齐全、收尾 HEAD=8d093b5 且新增文件仅 §0 清单 3 项、全程可由
§4 附录命令复现。
