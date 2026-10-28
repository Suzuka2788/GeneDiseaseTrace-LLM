# biomed-gene-disease-evidence：未定规则补全建议

对象：`C:\Users\tongz\.codex\skills\biomed-gene-disease-evidence\`（v1.0.0）
本文件只是建议，skill 本身未修改。每条包含：问题、建议条文（可直接粘贴）、放置位置、对 PMC10014009 的影响。

目标：同一规则跑 100 篇时，不同论文、不同模型、不同轮次在同类情形下得到相同处理。凡原 skill 写"本次声明""视上下文"的地方，都改成固定默认值，确有例外时必须记录。

---

## 1. 主矩阵纳入范围（固定默认值）

**问题**：原文写"具名临床事件/复合病症可纳入，但须在本次范围声明中列明"。每篇论文都可以有不同选择，结果无法横向比较。动物基因、报告基因、排除标准里的疾病、个案共病是否进入主矩阵，也没有写明。

**建议条文**（替换 SKILL.md "主疾病范围默认包含…" 一段）：

> 主矩阵纳入策略对所有论文固定，不逐篇声明：
>
> | 候选类别 | in_primary_matrix | 说明 |
> |---|---|---|
> | 明确诊断、疾病亚型、疾病家族 | 是 | 包括只在排除标准、鉴别诊断、共病或个案中出现的疾病 |
> | 具名临床事件（原文有固定名称或缩写的并发症/事件，如出血、卒中、梗死） | 是 | entity_type 仍为 clinical_event |
> | 症状、体征、一般表型、影像/实验室发现 | 否 | 进入辅助表；需要时另生成辅助矩阵 |
> | 未定义缩写或身份未定的名称，出现在诊断位置（诊断栏、"→ X"、"diagnosed with X"） | 是，entity_type=ambiguous | 不展开、不猜全称 |
> | 身份未定且不在诊断位置 | 否 | 进入 excluded_candidates |
> | 人类基因（含仅在背景中出现的） | 是 | |
> | 非人类基因（动物模型、细胞系物种、病原体） | 是，独立节点 | species_scope 必填，见第 2 条 |
> | 报告基因、标签蛋白、抗体标记物（只作工具用途） | 否 | 记录 mention_role；若原文把该标记物本身当研究对象，按基因处理 |
> | 基因集合、通路名、蛋白复合物 | 否 | 记为 mention_role=gene_set_modifier |
>
> 例外只能在用户明确要求时发生，并写入 manifest.scope_overrides。

**放置**：SKILL.md 第 1 节末尾；data-contract.md 的 `in_primary_matrix` 字段说明引用此表。

**对第一篇的影响**：疾病侧从 39 个降到约 20 个（D21–D39 的症状和 D10 cerebral microbleeds 移入辅助表）；CASH 保留在主矩阵；PLE 保留为 ambiguous。主矩阵约 8 × 20 = 160 对。

---

## 2. 非人类基因与跨物种证据

**问题**：原文只要求"动物证据明确区分"，没有规定动物基因节点能不能连到人类疾病节点，也没有说边该怎么标。

**建议条文**：

> - 非人类基因建立独立节点，命名为 `符号 (物种或 "animal model, species not stated")`，不与人类同源基因合并。
> - 疾病侧不为动物模型另建疾病节点。原文明确写出"X 疾病的动物模型由该基因改变诱导/产生"时，可连到同名疾病节点，status=supported，并在边上标 `evidence_species=non-human`、`model_type`。图中用不同线型表示。
> - 只描述动物细胞/组织表型、没有指明疾病模型时，不连到疾病节点，status=not_found，表型写入 study_findings 或辅助表。
> - 人类基因构建体在非人类细胞中表达：基因节点为人类，species_scope 记录宿主细胞物种，不改变基因物种。

**放置**：SKILL.md 第 1 节物种段之后；data-contract.md 的 edges 增加 `evidence_species`、`model_type`。

**对第一篇的影响**：Krit1、Ccm2、Pdcd10 到 CCM 的 3 条边保留，加上 `evidence_species=non-human` 和 `model_type=heterozygous loss`；做法与现在基本一致。

---

## 3. relation_type 的定义与单对取值

**问题**：每对只能有一个 relation_type，但原文没有说明多条主张并存时取哪个。association、correlation、causal 的界线也没有定义。

**建议条文**：

> relation_type 定义：
> - `causal`：原文用明确因果措辞把该基因（或其变异/功能丧失）与该疾病联系起来，如 cause、induce、lead to、responsible for、underlie；或报告了实验性干预改变疾病结局（敲除/挽救/转基因模型）。ACMG 致病/可能致病分级本身不算因果措辞。
> - `correlation`：报告了以该基因状态（或表达量、变异负荷）和该疾病变量为两端的统计相关或剂量关系。
> - `association`：其他明确的联系，如在患者中检出该基因的致病变异、病例—对照富集、"is associated with"、家系共分离、遗传诊断。
> - `none`：status 不是 supported 时使用。
>
> 一对有多条 supported 主张时：
> 1. 主表 relation_type 取有证据支持的最高级别，排序 causal > correlation > association。
> 2. 主表 source_scope 只描述**支持该最高级别主张**的证据来源。例如因果来自背景、本研究只有检出变异时，写 `causal / background`，不写 both。
> 3. 其余主张逐条写入 `claims`（relation_type、source_scope、evidence_id）。
> 4. 只有本研究自身也提供该级别证据时，source_scope 才能写 both。

**放置**：SKILL.md 第 2 节状态表之后。

**对第一篇的影响**：KRIT1、CCM2、PDCD10 到 FCCM 由 `causal / both` 改为 `causal / background`，并在 claims 中增加 `association / this_study`（检出变异、家系共分离）。

---

## 4. 措辞与主张类型判定表

**问题**：原文写"proposed、suggested、may 不单独决定状态，须读上下文"。方向对，但不同模型会读出不同结论。

**建议条文**（加到"证据与主张的边界"小节）：

> | 原文形式 | assertion_kind | 该对 status |
> |---|---|---|
> | 陈述既有发现，带或不带引用："X mutations have been identified/confirmed in Y [ref]" | background_relation_statement | supported / background |
> | 报道动词加被引研究的结论："A et al. reported/proposed/suggested/showed that X is associated with Y [ref]" | background_relation_statement | supported / background，conditions 记录原措辞 |
> | 作者自己的推测："X may/could/might contribute to Y"、"possibly"、"we speculate" | hypothesis | uncertain |
> | 作者对机制的推断："likely critical for…"、"suggesting that…"，没有直接结果支撑 | interpretation | uncertain |
> | 研究目的或假设："we aimed to examine whether X…" | aim | 不作为证据，状态由结果决定 |
> | 本研究检验后报告显著结果 | reported_result | supported / this_study |
> | 本研究检验后报告不显著或无差异 | negative_result | 见第 5 条 |
> | 未来研究建议："further studies are needed to determine whether X…" | aim | 不作为证据 |
>
> 同一句同时包含引用事实和作者推测时，拆成两条 evidence 分别标注。

**放置**：SKILL.md 第 2 节"证据与主张的边界"。

**对第一篇的影响**：ZPLD1 到 FCCM（"proposed…15"）维持 supported / background；MAP3K3 到 FCCM（"could be a novel cause"）维持 uncertain；KRIT1 到 vascular malformation（"likely critical"）维持 uncertain。结论不变，但有了明确依据。

---

## 5. 组水平统计如何落到单对

**问题**：原文禁止把组水平不显著拆成每个基因的阴性，但没有说清哪些检验可以算作单个基因的证据、单对应该落在哪个状态。

**建议条文**：

> 按检验的比较单元决定：
>
> | 检验设计 | 落到单对 | 其余 |
> |---|---|---|
> | 指定基因组 vs 明确对照（非携带者、其他基因组、健康人），结局为指定疾病或事件 | 显著：supported（association 或 correlation）/ this_study；不显著：explicit_negative，conditions 写清对照、结局、样本量、时点 | — |
> | 多个基因型的总体检验（omnibus），没有逐基因对比 | 不落单对；该对按其他证据判断，没有其他证据则为 not_found，并附 context_checked | 写入 study_findings |
> | 合并组（如"任一致病基因突变检出" vs 未检出） | 不落单对 | 写入 study_findings，population 记录合并组构成 |
> | 仅分组描述性频数，未检验 | not_found，附 context_checked | 可选写入 study_findings（status=descriptive） |
> | 疾病内部的严重度、病灶数、发病年龄与年龄等变量相关 | 不是基因—疾病相关；不落单对 | 写入 study_findings |
>
> 在已确诊患者中比较某基因组的并发症/事件（如出血）时，若满足第一行条件，可以落到"基因—该事件"这一对，conditions 必须写明"在 [疾病] 患者中"。

**放置**：SKILL.md 第 2 节；data-contract.md 的 study_findings 段落引用本表。

**对第一篇的影响**：KRIT1、CCM2、PDCD10 到 CASH 的 3 条 explicit_negative 改为 not_found，并附 context_checked（b0021、b0094 的基因型总体检验）。新增 study_findings：
1. 合并突变检出组与脑干、外侧颞叶、顶叶病灶相关（AUC）；
2. 基因型与首次 CASH 风险，总体不显著；
3. 各基因组内年龄与大病灶数的相关；
4. 突变检出组与未检出组临床特征无显著差异。

---

## 6. 回指与跨句连接

**问题**：原文写"局部省略或回指可解读，但不提升为全局别名"，没有说回指能延伸多远。

**建议条文**：

> 回指（"these genes""the three genes""this mutation"）只在以下情况解析：先行词出现在同一句或紧邻的前一句，并且是明确列举。超出这个范围，或者有多个可能的先行词时，记为 `contextual_referent=unresolved`，相关配对为 uncertain，unresolved_reason=coreference。

**对第一篇的影响**：KRIT1/CCM2/PDCD10 到 CCM 依赖的 b0011 "these genes" 指紧邻前一句列出的三基因，可以解析，维持 supported。MAP3K3 到 FCCM 的 "these genes" 有多个可能先行词，维持 uncertain。

---

## 7. 疾病层级（parent_id）

**问题**：原文要求保留层级，但没有说层级依据从哪里来。

**建议条文**：

> parent_id 只依据原文明确的层级陈述（"X is a type/subtype of Y""Y is divided into A and B""Y, including X"），或疾病名本身含有上位名加限定词（familial Y、spinal Y）。不引用外部本体。层级只用于展示，不传播关系；对上位疾病的关系必须有直接针对上位疾病的证据。

**对第一篇的影响**：FCCM、散发性 CCM 的 parent 为 CCM（b0011）；spinal CM、cutaneous CM 的 parent 为 CM。关系判断不变。

---

## 8. 拼写错误与未定义缩写

**建议条文**：

> - 疑似拼写错误合并必须同时满足：(a) 与另一个已出现名称编辑距离 ≤ 2；(b) 处在相同的列举或相同用途的语境中；(c) 原文没有其他对它的定义。三条全部满足才合并，否则建为 ambiguous。
> - 原文没有展开的缩写，不用领域知识补全称；canonical_name 写"<缩写>（原文未定义）"。

**对第一篇的影响**：KRTI1 合并到 KRIT1（满足三条）；CMM 合并到 CCM 也需要同样记录依据；PLE 维持 ambiguous。

---

## 9. 按文章类型的处理

**问题**：100 篇里有 69 篇 research-article、13 篇 case-report、11 篇 review-article、2 篇 letter，以及 editorial、abstract、systematic-review、brief-report、discussion 各 1 篇。原 skill 没有区分文章类型。

**建议条文**（新增小节"文章类型"）：

> manifest 记录 XML 的 article-type，并按下表处理：
>
> | 类型 | 规则 |
> |---|---|
> | research-article、brief-report | 按通用流程 |
> | case-report | 作者明确把患者的疾病归因于检出的变异时，记为 supported association / this_study；患者的其他共病为 not_found，附 context_checked |
> | review-article、discussion、editorial、letter | 默认 source_scope=background；只有作者自己的新数据或新分析才能标 this_study |
> | systematic-review、meta-analysis | 汇总分析结果视为 this_study；单篇被纳入研究的结论视为 background |
> | 会议摘要合集（一个文件包含多个独立摘要） | 先切成子单元 `paper_id#unitN`，在各子单元内配对；跨子单元的配对自动为 not_found，reason=different_study_unit；每个文件仍交付一张图，边标注子单元 |
> | 勘误、撤稿声明、无实质正文 | 报告可读范围；没有实体时交付空矩阵和说明，不报错 |

**放置**：SKILL.md "选择模式与确定范围"之后。

**对第一篇的影响**：无（research-article）。会影响 PMC10994491 等文章。

---

## 10. 缺失附件与覆盖说明

**建议条文**：

> 正文明确引用、但未能读取的补充表或补充图（如"(Table S3)"），在受影响配对的 conditions 中写 `depends_on_unread=Table S3`。状态不因附件缺失而改变：不能因为"可能在附件里"改成 uncertain，也不能因为没读到就当作阴性。manifest 列出所有未读附件和引用它们的位置。

**对第一篇的影响**：CASH 相关配对和 study_findings 2 加上 `depends_on_unread=Table S3`。

---

## 11. 论文顺序、输出目录与版本

**建议条文**：

> - "第一篇"的确定：用户给出顺序时按用户顺序；否则按项目清单文件（若有）顺序；再否则按文件名字典序，并在 A 部分说明采用了哪种顺序。
> - 输出目录：`outputs_<模型标识>/<paper_id>/`，模型标识使用实际执行的模型名。
> - manifest 必填：`run_id`、`rule_version`（即本 skill 的 version）、`annotation_hash`、`source_sha256`。规则变化时 rule_version 递增；旧版本输出保留，不覆盖。
> - 规则修订记录写在 skill 的 `CHANGELOG`，每条注明影响到的已交付论文。

---

## 12. 批量运行（100 篇）

**建议条文**：

> - 每篇独立判断，禁止跨论文补证据或合并节点；跨论文汇总另做，只读取各篇已完成的结果。
> - 每篇完成后先跑程序校验，再处理下一篇；校验失败的论文在汇总中标为失败，不用旧结果替代。
> - 汇总表按篇列出：主实体数、辅助实体数、主矩阵对数、各状态计数、study_findings 数、未读附件数、ambiguous 数。

---

## 修订后第一篇的预期变化汇总

| 项目 | 现在 | 按建议修订后 |
|---|---|---|
| 主矩阵疾病节点 | 39 | 约 20（症状移入辅助表） |
| 主矩阵对数 | 312 | 约 160 |
| explicit_negative | 3（基因到 CASH） | 0，改为 not_found 并附 context_checked |
| 基因到 FCCM 的 source_scope | both | background（causal），另记 this_study 的 association 主张 |
| study_findings | 无 | 4 条 |
| supported 边 | 11 | 11（不变） |
| 新增字段 | — | evidence_id、assertion_kind、conditions、claims、parent_id、in_primary_matrix、run_id、rule_version |

## 需要你拍板的选择

以下几处我选了一个默认值，也可以反过来定：

1. **具名临床事件进主矩阵**（第 1 条）。另一种做法是像症状一样放到辅助表，第一篇的 CASH 就不会出现在图上。
2. **被引研究结论用报道动词（proposed/suggested）时判 supported**（第 4 条）。更保守的做法是一律判 uncertain。
3. **非人类基因可以连到同名人类疾病节点，用虚线区分**（第 2 条）。另一种做法是动物证据不连边，只写入 study_findings。
4. **source_scope 只描述最高级别主张的来源**（第 3 条）。另一种做法是保留 both，表示两类证据都有。
