# biomed-gene-disease-evidence 1.3.0 修订建议

来源：PMC10014009 的三模型盲测（GPT-6 Astra、GPT-6.1 sol、Claude Opus 5.5，规则 1.2.0），比较报告见 `outputs_blind_comparison/PMC10014009/comparison_report.md`。
起草：Claude Opus 5.5（看过 1.2.0 边界案例，不是中立方）。本文件只是建议，skill 由 Codex 在维护源修改和提交。

用户已经确定的两项：
- **MAP3K3 → 散发性 CCM 这类"被引研究在患者中确认变异"的情况判 supported**（第 1 条）；
- **"机制未知"句中预设的关系判 uncertain**（第 2 条）。

第 4 条（表头类别不进主矩阵）采用建议的默认值，用户没有提出异议。其余各条是澄清或执行提醒。

---

## 1. 被引研究在某病患者中确认变异 → supported（用户已定）

**盲测表现**：三方都没有判 supported（两个 GPT 判 not_found，Claude 判 uncertain）。原因是 R4 的 "confirmed 仅确认变异检出 → descriptive" 和 R3 的 "患者中检出不够"，这两条本来是针对**本研究里的个案检出**写的，结果也覆盖了背景文献中的群体性发现。

**建议条文**（加到 R4 判定表，放在 "confirmed 仅确认变异检出" 那一行之前）：

> |背景报告：被引研究在指定疾病患者（群体，而非单个病例）中发现或确认该基因的变异，且当前论文把这一发现作为与该疾病相关的事实陈述（用于解释病因、机制、遗传异质性等）|supported / association / 背景引用；support_basis=explicit_background_report。不升级为 causal，除非原文另有因果措辞。|

并把原行改为：

> |本研究或个案中，confirmed 仅确认变异检出，无疾病归因或检验|descriptive_cooccurrence，无其他依据则 not_found。|

R3 association 定义同步改为："本研究中仅在患者中检出不够；明确的背景群体发现按 R4 处理。"

**判别要点**（写进规则正文，避免和 BC03、BC08 冲突）：
- 来源是被引研究或背景陈述，不是本研究自己的一次检出；
- 对象是该病患者群体（patients、cases、cohort），不是单个病例；
- 当前论文把它当作与该病有关的事实，而不是顺带提及。

**新增边界案例 BC31**（原文片段）：
- text：`Moreover, gain-of-function (GOF) mutations in MAP3K3, encoding MEKK3, have been confirmed in sporadic CCM patients.`
- context：`LOF in CCM genes and GOF in MAP3K3 are mutually exclusive, and the researchers suggested that CCM complexes suppress the activity of MEKK3.`（b0098）
- expected：status=supported, relation_type=association, source_scope=背景引用, propagate_to_parent=false（不传到 CCM 或 FCCM）
- 与 BC03（本研究检出、无归因 → not_found）和 BC08（背景因果 + 本研究个案检出）并列，用来区分两种 "检出"。

**对第一篇的影响**：MAP3K3 → 散发性 CCM 变为 supported，supported 边从 9 条变为 10 条。

---

## 2. "机制未知" 句中预设的关系 → uncertain（用户已定）

**盲测表现**：b0011 "the explicit mechanisms underlying the … vascular malformation suppression of the three CCM genes remain unknown"。Astra 判 CCM2/PDCD10 → 血管畸形为 not_found，Claude 判 uncertain。R4 判定表没有这一类。

**建议条文**（加到 R4 判定表）：

> |句子断言的是别的内容（如"机制未知"），但其中预设了指定实体对的关系，且没有其他断言或结果支持|uncertain；relation_asserted=presupposed；unresolved_reason 含 presupposed_only。预设不是断言，不能单独支持连边，也不能当作没有线索。|

数据约定同步：relation_asserted 增加取值 `presupposed`，unresolved_reason 增加取值 `presupposed_only`。

理由：R15 的逻辑是"有关系线索但无法确认才判 uncertain"，预设正好是有线索而没有断言；判 not_found 等于按句式直接排除，和"不能只凭措辞判状态"的原则冲突。

预设涉及基因集合时（如本句的 "the three CCM genes"），仍按 R13 和 R6 先确认成员和指代路径；成员无法确定时，unresolved_reason 再加 coreference。

**新增边界案例 BC32**（原文片段）：
- text：`Despite the tremendous progress in understanding CCM, the explicit mechanisms underlying the vascular-specific manifestation and vascular malformation suppression of the three CCM genes remain unknown.`（b0011）
- question：只依据这一句，CCM2 → vascular malformation 应判什么？
- expected：status=uncertain, relation_type=none, relation_asserted=presupposed, unresolved_reason=["presupposed_only"]
- rationale：句子断言的是机制未知，基因抑制血管畸形只是预设；有线索、无断言，不能连边，也不判 not_found。

**对第一篇的影响**：CCM2、PDCD10 → 一般血管畸形判为 uncertain（KRIT1 另有 b0100 的 "likely" 推测，本来就是 uncertain）。

---

## 3. 宽泛疾病家族是否进主矩阵（澄清 R1）

**盲测表现**：一般 "vascular malformation" 在 sol 那里被放进排除表（理由：泛称类别），Astra 把它建成节点，Claude 把它并入了 "intracranial vascular malformation"（违反 R7，属于执行错误）。

**建议条文**（R1 第一行条件后补充）：

> 宽泛疾病家族只要在原文中作为疾病类别出现（定义某病所属类别、或作为关系陈述的对象），就进主矩阵；不能以 "泛称" 为由排除。层级仍只用于展示，关系不传播。上位类别与部位限定子类不得合并（R7、BC27）。

**新增边界案例 BC33**：b0100 "This component is likely critical for preventing vascular malformation." → in_primary_matrix=true，不与 intracranial vascular malformation 合并。

---

## 4. 表头或栏目名中的疾病类别（采用建议默认值）

**盲测表现**：表 2 列名 "Non-cerebral CM" 只有 Astra 建了节点。

**建议默认值**：表头、栏目名或分组标签中的疾病类别，记入 excluded_candidates（原因：table_grouping_label），**不进主矩阵**；除非正文另把它当作疾病类别使用，或作为分析变量。理由：表头只是对行内容的分组，进主矩阵只会增加没有证据的配对。

**新增边界案例 BC35**（原文片段）：b0072 表 2 表头中的 "Non-cerebral CM" → in_primary_matrix=false，excluded_reason=table_grouping_label；其下的 spinal CM、cutaneous CM 照常作为疾病节点。

---

## 5. 表注和缩写表中定义的名称（执行提醒）

**盲测表现**：Claude 漏掉了一般 CM，理由是 "通用名从未单独出现"，但表注 b0064、b0093 写明了 "CM, cavernous malformation"。

**建议条文**（SKILL.md 第 1 节 "收集原名" 处）：

> 表注、图注和缩写表中定义的疾病或基因缩写，属于原文名称来源，必须核对并记录；不能只依据正文段落判断某个名称 "没有单独出现"。

不是规则歧义，只是把容易漏的地方写明。

---

## 6. 物种未写明的动物模型基因（澄清 R2）

**盲测表现**：三方都单独建了节点，但都在反馈里指出 R2 两句话之间的张力（"物种未知不产生新节点" 和 "模型与患者语境明确不同时可分开"）。

**建议条文**：

> 原文明确是动物模型或其他非人实验语境时，即使未写明物种，也与人类基因分开建节点：gene_species=null，identity_status=provisional，identity_issues 含 species_unresolved。"物种未知不产生新节点" 只适用于语境本身无法区分人类与非人的情况。

---

## 7. 没有引用文献的作者一般性陈述（澄清 R3/R9）

**盲测表现**：Claude 的反馈第 4 条；之前给 Codex 的意见里也提过。

**建议条文**：

> 摘要、引言中作者陈述的既有知识（没有引用编号，也不是本研究结果），source_scope=背景引用，assertion_kind=background_relation_statement，conditions 记 citation_absent=true。

**新增边界案例 BC34**：b0003 "Familial cerebral cavernous malformation (FCCM) is an autosomal dominant disease induced by loss-of-function mutations in three CCM genes, KRIT1, CCM2, and PDCD10." → source_scope=背景引用, citation_absent=true（与 BC01 同一句，只补这一字段）。

---

## 8. 数据约定的两处遗留

- **conflict_impact**：边界案例和校验脚本都在用（noncritical / status_critical / undetermined），但 data-contract 没有定义这个字段。建议在 data_conflicts 的字段说明里补上，三份盲测输出实际用的字段名是 `impact`，也要统一。
- **source_scope 的取值语言**：现在是中文（背景引用 / 本研究结果 / 两者兼有 / 不确定）。三个模型都照做了，没有出错。如果交付物要英文，建议在 1.3.0 改为英文代码加中文展示标签；不改也可以，但要在 CHANGELOG 里说明这是格式约定。

---

## 版本与后续

- 以上属于规则语义变更（第 1、2、4 条会改变判断结果），建议版本号 1.3.0，更新 CHANGELOG 并写明影响范围。第一篇预计：MAP3K3 → 散发性 CCM 变为 supported（supported 边 9 → 10）；CCM2、PDCD10 → 一般血管畸形为 uncertain；一般血管畸形进主矩阵、"Non-cerebral CM" 不进，三个模型的矩阵大小应趋于一致。这些只是按新规则的推算，不是预设目标，以重新运行的结果为准。
- 新增边界案例 BC31–BC35，预期值已全部填写，要在任何模型运行前冻结。
- 1.3.0 冻结后，用同样的盲测方式跑其余 4 篇试点（病例报告、综述、西班牙语、会议摘要合集）。第一篇不必重跑全部，只需要在汇总时注明 1.2.0 和 1.3.0 的差异。
