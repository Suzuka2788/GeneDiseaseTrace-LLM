# 数据约定（1.3.0）

CSV的列表/对象单元格用有效JSON，JSON保留原生类型。ID在本次交付稳定；缺失值留空/null并说明，不编造。源语言保留，译文另列。以下定义字段语义，不强制数据必须装入一个文件。

## 运行、位置和单元

manifest：run_id、rule_version、rule_hashes、paper_id、题名、article_type、language、输入路径/source_sha256、使用的annotation_hash（没有则null）、已知模型标识、覆盖/OCR/规范化方式、unread_attachments、scope_overrides、输出清单/统计及检查限制。未知模型身份明示；接触旧答案的重做不称盲法。

unread_attachments每项含名称、原始链接/文件名、引用位置、未读原因。已确认依赖写depends_on_unread/dependency_detail；附近引用但对应未确定写possible_attachment_reference，不能猜表内统计量。

source_blocks：paper_id、block_id、原文、章节、内容类型、原XML ID或真实PDF页码。保留标题、表头/列/行/脚注、图注与位置；规范化文本可逐字检索，并记录规范化方法，不改变否定、数字或基因拼写。表格解释须可追溯表头/行组。

多研究文件每记录加unit_id；主键为paper_id+unit_id+端点。矩阵是各单元笛卡尔积之和；跨单元不生成的组合在scope_exclusions说明，不混入not_found分母。总图可合并同一已核实实体，但边保留单元和全部claims，不伪造跨单元证据。

## 实体、原名与身份

entities字段：

|字段|含义|
|---|---|
|paper_id / unit_id / entity_id|论文、单元、统一实体|
|entity_type|gene / disease / symptom / phenotype / clinical_event / ambiguous|
|candidate_side|未定候选的gene / disease；无法确定不猜，保留候选表|
|canonical_name / original_names|保守统一名及实际出现名称，不暗示数据库确认；局部回指另记|
|identity_status|resolved / provisional / unresolved|
|identity_issues|列表：undefined_abbreviation / suspected_typo / species_unresolved / ambiguous_mapping / other|
|gene_species / host_species|基因来源物种与实验宿主；未知null，范围和依据另列|
|species_scope|人类患者/动物模型/构建体等原文范围与依据，不代替前两字段|
|location / ambiguity / merge_basis|提及位置、残余歧义、同义/同指依据|
|parent_id / hierarchy_basis / qualifiers|原文层级依据、部位/侧别/分级等限定；层级不传播关系|
|in_primary_matrix|按R1；疾病、事件、未定候选分别计数|
|database_id / reference_sequences_from_text|未核实实体ID留空；原文参考序列不当实体ID|

resolved仅表示本次映射已清楚，不要求已查数据库。provisional可用于强上下文笔误归一或物种未定但模型指称清楚；identity_issues可并存。不能仅按identity_status决定配对状态（R15）。

mentions：mention_id、entity_id（可未解决）、surface、entity_type、mention_role、location、上下文、start/end偏移、contextual_referent、coreference_path及限定。角色区分基因、蛋白、工具标记物/构建体、携带者组、gene_set_modifier、疾病词修饰基因集合、表头补足、局部回指。错误拼写和限定原文不丢失。

辅助实体可放entities并标in_primary_matrix=false，或另存auxiliary_entities，保持相同身份字段。excluded_candidates保存非实体/类型未定名称及上下文、原因；纯表头疾病分组标签写excluded_reason=table_grouping_label，并保留其与下级条目的语境连接。表注/图注/缩写表中独立定义的名称仍须正常记录。基因集合另存set_id、原文名称、成员ID/成员依据和作用范围，不作伪单基因。

## 配对、主张和证据

pairs：paper_id、unit_id、pair_id、gene_id、disease_id、status、relation_type、tested_relation_type、source_scope、claims、evidence_ids、location、reason、conditions、unresolved_reason、context_checked、observational_context、data_conflict_ids。

status仅supported / explicit_negative / uncertain / not_found。relation_type仅association / correlation / causal / none；supported选已获支持的类型，其余主表用none，被检验/否定/待审类型另保留。source_scope继续使用中文固定值背景引用/本研究结果/两者兼有/不确定；1.3.0不迁移为英文代码。没有可归属关系依据可为不确定，不自动改变not_found。

unresolved_reason用列表，允许identity / coreference / hedged_claim / support_basis_unresolved / presupposed_only / scope / conflict / missing_material / other；uncertain须解释具体阻碍。presupposed_only表示仅预设关系、没有其他支持断言/结果，不是普通共现或未知机制一律适用。not_found的实体仍可identity_status=unresolved。

claims每项：claim_id、端点/适用范围、status、relation_type或tested_relation_type、source_scope、evidence_ids、conditions、reason。多条支持主张按R3选主表摘要，展示优先级不代表可信度。仅检测变异的观察放observational_context，不强建association claim。主表选中来源要能追到对应claim，不能把背景因果改为本研究因果。

evidence每项：

- evidence_id、原文quote、location、可用的字符偏移；非英文translation另列。
- source_scope与assertion_kind：reported_result / background_relation_statement / hypothesis / aim / interpretation / negative_result / descriptive_cooccurrence。
- relation_asserted：affirmed / negated / hypothetical / questioned / not_asserted / presupposed。presupposed表示关系被当作背景前提、句子断言的是别的内容；它不是明确的关系断言，不单独支持连边。
- support_basis：列表，可含explicit_background_report / reported_result / explicit_disease_attribution / co_segregation / comparative_result / model_intervention / descriptive_only / hypothesis_only / unclear / none；supports说明具体支持/不能支持什么。
- conditions：原文提供的物种、基因改变、模型、构建体、疾病亚型、变异类别、样本/对照、变量、终点、时点和附件依赖。无引用编号但明确为既有知识时记citation_absent=true；不编造引文来源。背景群体变异报告记真实范围，不补造样本量、病例—对照或因果证据。
- evidence_link_path、distribution_basis：跨片段连接及集合分配依据；不用距离或成员列举代替语义判断。

这些枚举帮助记录，不能通过填入“reported_result”就使状态自动成立。原文明确背景归因可以支持而不要求当前论文重述实验；仍要解释为什么不是目的/推测/共现。

not_found可没有支持引语，但须写检查范围和理由；容易误读的共病/组阴性附context_checked，并解释不足。不能编造“未发现”的原句。evidence可被多个成员/claims引用，复用不等于多份独立实验。

## study_findings：类型、显著性、方向分开

每项含finding_id、variables、population_or_group、source_scope、evidence_ids、conditions、limits，另含：

|字段|取值/说明|
|---|---|
|finding_type|association / correlation / group_comparison / descriptive / mechanism / hypothesis / other|
|reported_significance|significant / not_significant / mixed / unknown / not_applicable；保留原文依据，不能从“风险增加”猜p值|
|effect_direction|positive / negative / mixed / null / unknown / not_applicable；仅原文明确无效应/等效时可null，不因p不显著填null|
|statistics_availability|available / partial / unread / not_reported / not_applicable|
|statistics|原文实际可读效应量、r、HR、CI、p及阈值/检验，不可读null|
|depends_on_unread / dependency_detail|确有依赖的附件及依赖内容；可能对应时用possible_attachment_reference|

作者正文明确不显著而统计量在未读表，可记not_significant+unread；正文只叙述趋势且无检验可记unknown+not_reported/partial。负相关可以significant+negative。总体检验无单一方向用not_applicable。不要用旧单一status混合这些维度。

## data_conflicts

conflict_id、subject、statements（各quote/location/value/问题/条件）、same_question_assessment、impact（noncritical / status_critical / undetermined）、affected_claim_ids/pair_ids、resolution（resolved / unresolved）、action、reason。

冲突影响的规范字段统一为impact，案例expected也用impact；不再用conflict_impact。旧版交付原样保留，转换时记录字段映射；两字段同时出现且不同须报告，不能默默挑一个值。

先核对队列/分母/终点等；不得默认表格胜正文。非关键数值不一致可保留关系但不确定精确值。关键身份/方向/依据冲突才阻碍配对；不能从“显著对不显著”自动推出矛盾。

## 比较与未解决项

entity_alignment保存双方名称/别名、原ID、类型、物种、身份状态及统一ID和same/split/merge/scope/unresolved依据。

adjudications：issue_id、双方主张、统一端点、原文证据、四类裁决（支持A/支持B/两者均需修正/暂无法裁决）、修订动作与限制。aligned_pair_comparison保留全部可比/不可比组合及原/修订状态和裁决ID；实体拆分时不伪造原模型已有子实体判断。

unresolved保存身份/关系/覆盖问题、状态、原因及所需材料。区分规则版本差异、执行错误与原文含糊，不用模型一致性作准确性证据。

## 图与机械检查

保留全部主端点，含孤立候选；bipartite=gene/target分侧。仅supported连边，边含端点、relation_type、source_scope、evidence_ids、unit_id、conditions，以及evidence_species（human / non-human / mixed / unknown）。gene_species、host_species、gene_alteration、model_type按证据保存，未知不补造。GraphML合法key定义；混合条件不能只用一条人类因果标签覆盖。

检查引用/偏移、ID、每单元完整唯一笛卡尔积、supported/explicit_negative依据、uncertain理由、claims/证据链接、图节点全集和恰为supported的边集合、各格式与文件清单计数一致。检查各维度合法不能代替语义解释。校验报告明确结构/引文检查与未执行的行为/跨模型试点，不编造性能分数。
