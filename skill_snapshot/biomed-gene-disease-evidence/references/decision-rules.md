# 判定规则 R1–R16（1.3.0）

范围/字段在同一批次固定，用户例外记录manifest.scope_overrides。语义判断引用原文，不能以关键词、模型一致性或边数代替。规则优先于案例；发现歧义记录并版本化修订，不偷偷改预期。

## R1 主矩阵范围

|类别|主矩阵|条件|
|---|---|---|
|明确诊断、疾病家族/亚型、具名损伤|是|包括背景、鉴别/排除、个案、共病；宽泛家族只要作为疾病类别、定义上位类或关系对象出现也纳入，不能仅因“泛称”排除；出现不等于关联。|
|仅作表头/栏目/分组标签的疾病类别|否|无独立疾病类别用法或分析变量意义时记excluded_candidates，excluded_reason=table_grouping_label；若正文另作疾病类别，或确为诊断/分析变量，则按实体纳入。|
|具名临床事件/复合病症|是|原文定义含义或用作分析结局，类型仍clinical_event；泛指“出血”不因有名称就纳入。|
|症状、体征、一般表型、影像/实验室发现|否|保存辅助实体，不补成疾病诊断。|
|有诊断/基因指称依据、身份未定的候选|是|ambiguous加candidate_side；诊断栏/箭头只是线索，需结合上下文。|
|缺乏类型依据的未定名称|否|候选表保留原名/上下文/理由，不猜为疾病或基因。|
|明确出现的人类/非人类基因|是|包括仅背景出现；物种按R2。|
|仅作工具的报告基因/标签/抗体标记物|否|保存角色；若研究标记物本身，仍须确认对应基因，不能将抗体自动当基因。|
|基因集合/通路/复合物|非单基因端点|保存成员与角色，分配按R13。|

未知基因候选用candidate_side=gene，未知诊断用disease。分别统计疾病、事件及未定候选，不把矩阵目标数称为疾病数。

表头位置本身不是排除依据。先核对其作用：仅归类下级条目的标签（如“Non-cerebral CM”）不另增主节点，但保留表头与下级条目的连接；表头真正指向诊断/研究变量或其名称在表注独立定义时须正常提取。spinal CM、cutaneous CM及脚注定义的一般CM不因分组标签排除而被删除。上位类与部位限定子类不得合并（R7）。

## R2 物种、构建体和模型

不同明确来源物种分基因节点。原文明确动物模型或其他非人语境时，即使具体物种未写明，也与人类基因分开：gene_species=null、identity_status=provisional、identity_issues含species_unresolved，species_scope记录非人依据。“物种未知不自动新增节点”仅用于语境本身无法区分来源的情形。大小写不能单独指定物种。

上述默认用于非人模型基因指称；已明确为人类构建体/人类序列时，仍优先保留已知gene_species，不能因非人宿主或动物模型位置将它改成非人基因。

gene_species、host_species、gene_alteration、model_type分字段。人类构建体在非人细胞中表达时基因仍human；heterozygous loss是改变，不是model_type。序列比较与实验干预分开。

明确“基因改变诱导某疾病动物模型”可连到同名疾病概念，边标evidence_species=non-human及已知条件，用线型/颜色及图例区分；这是模型证据，不是人类因果。仅细胞/组织表型、未对应疾病模型时不推疾病边，无其他证据则not_found。混合证据逐条标物种；不能用宿主推断基因来源。

## R3 类型、多主张和主表

- causal：原文明确将疾病发生/改变归因于该基因/变异，或明确报告对应模型干预因果；仍须通过R4的假设/范围/依据检查，不能由措辞或细胞表型自动判定。
- correlation：统计两端为基因状态/表达/负荷与指定疾病变量。负相关也可支持相关，相关不是因果。
- association：明确对应当前疾病的联系，如病例—对照、该疾病的共分离/诊断、特异性变异归因或明确背景关系报告。本研究/个案仅检出或“致病”标签不够；背景群体变异发现且被当前论文作为疾病相关事实使用时按R4处理。
- none：未确认支持类型；explicit_negative/uncertain的原问题类型另列tested_relation_type及claims。

各claims保存status、relation_type、source_scope、evidence_ids、条件和理由；描述观察可单列observational_context，不强建association claim。

主表摘要顺序：

1. 先裁决各主张及适用条件；显著与不显著本身不证明两者互相矛盾，不同物种/亚型/变异/终点分别保留。
2. 有支持主张且无妨碍该主张的实质未解决冲突，主表supported。多种支持类型按causal、correlation、association的**展示优先级**摘要，不称证据强度排序。
3. source_scope只描述选中支持类型及其主张。背景因果+本研究仅检出时为causal/背景引用，观察另存；仅两方均支持该主张时用两者兼有。
4. 同一问题/条件有实质相反证据而无法解决时，主表uncertain并保留双方。另一个问题的不显著或新增弱假设不抹去既有支持。
5. 无支持主张：对应问题明确阴性且无实质冲突为explicit_negative；相关证据待解决为uncertain；其余not_found。仅目的不是待解决结果。

## R4 主张、措辞与依据

分别记录relation_asserted（affirmed/negated/hypothetical/questioned/not_asserted/presupposed）、assertion_kind和support_basis。词表只帮助定位。

supported须同时满足：(a)指定实体对与范围明确；(b)报告发现或明确归因而非仅目的/可能性；(c)可读内容足以解释连接依据；(d)无关键未解决问题阻碍该连接。

清楚、非假设的疾病特异性背景归因/发现可以作为explicit_background_report，不要求当前论文重现被引研究实验或p值，也不意味着被引研究已独立核实。引用或报道动词本身不是充分依据。

|实际内容|处理|
|---|---|
|明确背景关系/病因报告，无完整实验细节|满足上述标准可supported/背景引用。|
|背景报告被引研究在指定疾病患者群体中发现/确认该基因变异，且当前论文把发现作为该疾病相关事实使用（解释病因、机制或遗传异质性等）|supported / association / 背景引用，support_basis含explicit_background_report；不升级causal，除非另有符合R3/R4的明确因果主张。|
|proposed/suggested附具体、疾病对应的共分离/富集等支持结果|按结果判断，不凭动词降级。|
|提出可能关系，语境不能区分结果转述与假设|uncertain并记hedged_claim/support_basis_unresolved。|
|本研究或个案中confirmed仅确认变异检出，无疾病归因/检验|descriptive_cooccurrence，无其他依据则not_found。|
|句子断言别的事（如机制未知），但预设指定实体对关系，且没有其他断言/结果支持|uncertain，relation_asserted=presupposed，unresolved_reason含presupposed_only；不是支持边，也不是完全没有关系线索。|
|showed/reported的是未发现指定关联|按R5判阴性，不因动词变阳性。|
|仅研究目的、待检验问题、未来计划|不作支持/阴性；无其他依据则not_found。|
|确实提出指定实体对的假设但无结果|hypothesis claim及uncertain，不画支持边。|

同句事实/推测可拆分；联合片段列evidence_link_path。措辞“关联/风险增加”不自动说明统计显著（R16）。

背景群体发现须同时确认：来源是被引/既有研究而非本研究检出；对象确为该疾病患者群体而非单个共病病例；当前论文确实将该发现用于疾病关联的事实陈述而非顺带提及。patients/cases/cohort只是线索，不因复数单词或章节位置自动通过，也不补造群体规模、富集或p值。BC03/BC08的描述性检出处理不变。

预设必须可追溯到指定基因与指定疾病，不能从“机制未知”泛化出任意关系。若涉及“the three genes”等集合，先按R6/R13确认成员与路径；仍有竞争指代时再加coreference。只有预设是唯一关系线索时以presupposed_only阻碍支持；若另有独立充分证据，仍按R3汇总，不能由此抹去已有支持主张。

## R5 实际统计单元

|设计|单基因配对|
|---|---|
|指定基因状态对明确对照，结局为指定疾病/具名事件|对应主张明确显著可支持association/correlation；明确不显著可explicit_negative，保留问题和条件，不称证明无关系。|
|基因型总体检验，无逐基因对比|不拆给成员；保存findings，无其他证据则not_found并附context_checked。|
|任一面板变异检出等合并组|不拆给成员，保存组构成。|
|仅频数、未检验/归因|描述记录，无其他依据则not_found。|
|基因组内年龄与病灶数/发作年龄相关|统计两端不是基因与疾病，不改成基因correlation边。|

在疾病患者中检验基因—并发事件，可支持该事件，必须限定患者范围。直接比较基因状态与疾病严重度须保留该终点，不扩大为易感性。不显著不等于等效或无效。

## R6 回指和跨句连接

优先邻句，允许表头、行组、图注和明确段落主题提供更远连接。列先行词、连接片段、范围及排除竞争指代的依据。多个合理先行词影响裁决时记coreference未解决；距离远但路径明确不自动不确定。局部回指不成为全局别名。

## R7 疾病层级

仅依据原文明确层级或上位名加限定词（familial Y/spinal Y），保留hierarchy_basis，不外查本体补全。层级仅展示，不向上、横向或跨物种自动传播关系。

## R8 拼写和缩写

编辑距离只找候选。合并需同一指称的正面依据，如同一检测面板多处一致、某处疑似错拼；还须排除原文明示不同成员。相近数字、同列或同用途不够。保留原名、依据、identity_issues；不足不合并。未知缩写保留原名，不以知识补全称。

## R9 类型、语言和独立单元

manifest记article_type/语言，但标签不独自决定来源。病例明确疾病特异性归因可支持association，不自动因果；共病不算。综述/社论/来信的引用为背景，作者自己新数据/分析为本研究。系统综述的被纳入研究和本次汇总分析分开。

摘要/引言等位置明确陈述既有知识、且不是本研究结果时，即使无引用编号也用source_scope=背景引用、assertion_kind=background_relation_statement，并在conditions中记citation_absent=true。此来源标签不表示存在真实引文编号；不编造参考文献，也不因所在章节自动把作者自己的结果改成背景。

会议合集先按标题/作者/摘要界限建立unit_id，各单元内生成完整矩阵；跨单元不生成、不标not_found，说明scope_exclusions。无法可靠划分时报告限制。总图保留单元证据，不制造跨单元边。勘误/撤稿声明记录纠正影响；无实体可交空矩阵而非抽取失败。

非英文引用原句及位置，译文另列，不能因翻译新增名称；语言限制明示。

## R10 未读附件

列附件名、引用位置、缺失原因；受影响记录写depends_on_unread和dependency_detail。缺失本身不改状态、不作阴性；“可能有”不制造uncertain。关键身份/对照/解释确实依赖未读项且妨碍裁决时可uncertain/missing_material。

正文明确不显著则reported_significance仍not_significant，未读的效应量/精度单独标不可读。只有附近引用而未确认对应某发现时用possible_attachment_reference，不能声称未读表一定含该统计量。

## R11 顺序、输出和版本

- 按用户顺序、项目清单、文件名字典序依次选择并说明。
- 新输出 `outputs_<模型标识>/<paper_id>/rules-<rule_version>/<run_id>/`；模型只填已知实际值，未知明示。旧结果不迁移/覆盖。
- manifest存run_id、规则版本/哈希、输入哈希、类型/语言、范围/附件、使用的标注哈希及输出清单。比较还记双方版本及接触历史。
- 通过维护源/安装副本流程发布，记录影响，不预设边数。旧结果不因发布规则重新标版本。

## R12 批次与试点

逐篇/单元独立判断和校验，失败不混旧结果；大表完整导出。汇总列主/辅助实体、候选数、状态、findings、矛盾和未读材料。

回归预期先于模型测试冻结，不是医学金标准。跨模型测试固定规则/输入/范围，各自完成后比较；一致性不等于准确性。已见预期/旧结论需披露，不称盲法。语义歧义修规则并改版本，执行错只修结果。未经请求不跑100篇或向其他模型发任务。

## R13 集合到成员

先确定集合成员、物种、疾病范围与谓词：

- “mutations in three genes X,Y,Z cause D”或“each of X,Y,Z …D”可分配，记共同引用及distribution_basis。
- “X/Y/Z产物形成复合物”不推出各基因—疾病关系。
- 联合敲除/联合评分/合并面板效应不分配为各成员独立效应，除非另有单成员对比/归因。
- “biallelic LOF in CCM genes”不是固定支持/不确定模板；依上下文核对成员、逐成员含义与亚型。一般CCM机制不自动支持散发/FCCM。相关但分配未明用uncertain/scope；仅未知是否属集合又无关系线索时，不制造关联。

## R14 内部矛盾

保留各原句、值、位置、问题/条件及data_conflicts，不擅改或默认表格优先。先排除不同队列、模型、时间、分母、定义的表观差异。

不影响身份、方向或关键推断的数值差异为noncritical，可保留关系并标精确值未解决。身份/方向/支持依据实质矛盾未解决为status_critical，相关对uncertain/conflict。支持与不显著本身、不同条件的不同结果，不自动冲突。

## R15 身份与配对状态

identity_status取resolved/provisional/unresolved；identity_issues可多选undefined_abbreviation/suspected_typo/species_unresolved/ambiguous_mapping/other。它不代表数据库确认。物种未知但模型范围明确可为provisional，模型关系仍可在限定条件下supported。

“G改变与QX诊断有关”但QX未知，关系解释依赖身份，可uncertain/identity。“携带G变异患者也有QX”只是共现，无其他线索则not_found；QX身份仍未解决并保留候选孤立节点。不能因未知实体机械增加整列uncertain。

## R16 研究发现与可读性

study_findings分别记finding_type、reported_significance、effect_direction、statistics_availability，不用配对四状态或旧单一status代替（字段见data-contract）。

显著负相关为correlation/significant/negative，不是explicit_negative。正文明确不显著，即使数值在未读附件，仍not_significant；只报告风险更高却未说明检验，显著性unknown。不可读数值不补造，依赖按R10记；总体检验无统一方向用not_applicable。
