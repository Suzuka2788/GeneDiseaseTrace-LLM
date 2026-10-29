# 盲测提示词：PMC10014009，skill 1.2.0

运行目录：`C:\Users\tongz\blind_PMC10014009_Claude_Opus_5.5\`（在这个目录里打开新的 Claude Code 会话，不要在原项目目录中打开）。

```text
你将独立完成一项生物医学文献证据抽取任务。这是一次盲测运行：结果会与其他模型的结果比较，独立性和可追溯性比速度重要。

## 输入与规则
- 论文：input/PMC10014009.xml。开始前核对 SHA-256，应为
  fafc0d2128bbaadc1e13b163c86781e531cb976f3dde11b233d7e8d13fa0958e
  不一致就停止并报告。
- 规则：skill/biomed-gene-disease-evidence/（版本 1.2.0）。先读 SKILL.md，再按其要求读 references/decision-rules.md 和 references/data-contract.md。核对 SHA-256：
  SKILL.md           8286c118fd11a24c69e6009493cb616b75d5630bf9b019755396b4bfc6803b9f
  decision-rules.md  0204643864c423ec066b9720a583c83443aff88dd87ceab8cb07fbe13f80d506
  data-contract.md   22c98879ce145de87ebe8e6dde6d2c38e2ac434541e2f2c0c3fcb5a9ca262455
  不一致就停止并报告。
- SKILL.md 链接的 boundary-cases.md、model-comparison.md 和 CHANGELOG.md 是有意不提供的，本任务不需要它们，不要去其他位置寻找。
- 解析：必须用 biomed/jats.py 的 parse_article() 解析 XML（只依赖 Python 标准库），以它给出的块编号（b0001 起）作为位置。不要另写解析器或换用其他工具；如果无法运行 Python，停止并报告，不要继续。

## 独立性要求
- 只读取当前工作目录内的文件。不访问网络，不查询 PubTator 或任何数据库。
- 不搜索、不打开、不引用这篇论文的任何既往结果、比较报告、边界案例、修订建议或其他模型输出，即使你在磁盘其他位置发现它们。
- 开始前如实声明：你此前是否在任何会话或记忆中接触过这篇论文的分析结果，或这个 skill 的边界案例。写入 manifest 的 exposure 字段；接触过就不能称为盲测。
- 不用你已有的医学知识补全关系，只依据本文可读内容。

## 任务
按 skill 流程完整分析这一篇论文，交付 A–E：
A 输入范围与限制；
B 实体表：主表、辅助表、候选/排除表，含原文名称映射、identity_status 与 identity_issues、物种相关字段和疾病层级；
C 主矩阵全部候选配对的判断：每对恰好一条，字段按 data-contract（claims、evidence、context_checked、observational_context、conditions、unresolved_reason 等）；
D 二部图；
E 未解决问题与质量说明。
另按规则交付 study_findings 和 data_conflicts；没有内容就交空表并说明原因。

- 遇到规则冲突或规则没覆盖的情况：按有依据的最保守方式处理，并写入 rule_feedback.md（规则编号、原文位置、问题、你的处理）。不要修改 skill。
- 不预设边数或状态分布。

## 输出
写到 outputs_Claude_Opus_5.5_blind/PMC10014009/rules-1.2.0/<run_id>/，run_id 用 UTC 时间戳加短哈希。至少包含：
manifest.json、entities.csv、auxiliary_entities.csv、excluded_candidates.csv、mentions.csv、pairs.csv、edges.csv、evidence.csv、study_findings.csv、data_conflicts.csv、result.json、graph.graphml、graph.svg 或 index.html、validation.json、rule_feedback.md。
manifest.json 记录：run_id、rule_version、三个规则文件哈希、输入哈希、实际模型标识、exposure 声明、读取范围、未读附件、文本规范化方式。

## 校验与收尾
- 用程序执行 data-contract 中的校验：引文能在对应原文块中逐字找到且字符偏移正确；配对集合恰为基因 × 主目标的笛卡尔积，每对一次；图节点 = 主实体（保留孤立节点），边 = supported 配对；各文件计数一致。结果写入 validation.json，并写明哪些内容没有检查。
- 只做这一篇；不修改 skill，不提交 git，不运行其他论文。
- 最后回复：输出目录；实体数和配对数；各状态数量；全部 supported 边及其证据位置；全部 uncertain 配对及原因；rule_feedback 摘要。不要声称准确率、召回率，也不要声称经过了独立验证。
```
