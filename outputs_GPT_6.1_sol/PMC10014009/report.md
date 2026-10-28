# PMC10014009：逐篇证据核查

## A. 输入范围与限制

论文：Clinicoradiologic data of familial cerebral cavernous malformation with age-related disease burden。DOI：10.1002/acn3.51728。按上传压缩包文件顺序选第一篇；不是按发表日期排序。

直接重解析所给 JATS XML，共 117 个文本块：标题1、段落32（含摘要及补充说明）、章节标题22、图表标题/图注5、表格行55、表下注释2。检查范围为标题、摘要、全部正文、表1和表2（含表头、所有行和脚注）、图1–3图注、补充表S1–S3说明及声明。参考文献列表不纳入实体提取；正文引用陈述可以作为背景。

XML 仅链接3张 JPG（ACN3-10-373-g001/g002/g003.jpg）与1个补充 DOCX（ACN3-10-373-s001.docx）；本地输入包未提供这些文件，故未读取图片内文字、曲线标注或补充表实际数据。不能声称检查了含这些附件的完整全文。所有位置为 source_blocks.txt 的块编号，不编造页码。文本进行空白、Unicode和标点规范化；引用与此规范化原文逐字校验，原始XML保持不变。

## B. 实体表

entities.csv/json 为统一实体表；mentions.csv/json 为原文名称、角色、位置、精确字符偏移与完整段落上下文。excluded_candidates.csv/json 明示症状、一般表型、数据库、工具、指南代码和基因集合称谓等排除项。未填入未经原文确认的数据库实体编号；原文的测序参考序列保留在 b0019，不误作实体ID。

共8个基因范围节点（5个人类语境、3个具体物种未明的动物模型节点）、19个疾病/临床病症节点及1个未解决诊断候选PLE。没有抗体标记物、报告基因或跨物种序列比较的明确记录；KRIT1 protein 和 MEKK3 均按基因产物角色记录。

|ID|类型|统一名称|物种/范围|关键说明|
|---|---|---|---|---|
|G01|gene|KRIT1|Homo sapiens|KRTI1 是原文拼写，按同一三基因检测面板上下文判为 KRIT1 的疑似排字错误，不作独立基因。|
|G02|gene|CCM2|Homo sapiens|原文名称；未进行数据库映射。|
|G03|gene|PDCD10|Homo sapiens|原文名称；未进行数据库映射。|
|G04|gene|ZPLD1|人类患者语境；原句未另标物种|只有讨论中转述他人提出的关联，本研究未测定此基因。|
|G05|gene|MAP3K3|人类散发 CCM 患者语境|MEKK3 为蛋白产物名称，不是另一个已明确出现的基因。|
|G06|gene|Krit1|动物模型；所给原文未指明具体物种|与对应人类基因分开保留；动物物种未解决。不能仅凭大小写推断为小鼠。|
|G07|gene|Ccm2|动物模型；所给原文未指明具体物种|与对应人类基因分开保留；动物物种未解决。不能仅凭大小写推断为小鼠。|
|G08|gene|Pdcd10|动物模型；所给原文未指明具体物种|与对应人类基因分开保留；动物物种未解决。不能仅凭大小写推断为小鼠。|
|D01|disease|cerebral cavernous malformation|人类；动物模型另有语境|CMM 仅 b0099 出现一次，按相邻治疗 CCM 语境视为疑似笔误；保留原文。|
|D02|disease|familial cerebral cavernous malformation|人类|b0003、b0011 显式定义 FCCM；保留为 CCM 的家族性亚型节点，不与上位 CCM 合并。|
|D03|disease|sporadic cerebral cavernous malformation|人类|b0011 明确区分 sporadic 与 familial；不向另一个亚型传播证据。|
|D04|disease|spinal cavernous malformation|人类|b0016 定义 CM；spinal 明确限定脊髓部位。表2 Spinal 为同列的简写。|
|D05|disease|cutaneous cavernous malformation|人类|b0016 的 CM 定义及表1、表2 的 non-cerebral CM 语境。|
|D06|disease|cavernous angioma with symptomatic hemorrhage|人类|病变伴症状性出血的复合临床事件，作为条件节点保留；不与所有 CCM 合并。|
|D07|disease|small vessel disease|人类|原文名称；未进行数据库映射。|
|D08|disease|diffuse axonal injury|人类|原文名称；未进行数据库映射。|
|D09|disease|intracerebral hemorrhage|人类|原文指无 CCM 病灶的多发复发脑内出血，不与 CASH 合并。|
|D10|disease|developmental venous anomaly|人类|本队列明确无人患此畸形；这不是基因—疾病关联阴性试验。|
|D11|disease|tumor|人类|宽泛疾病家族；表2的具体肿瘤不并入此节点。|
|D12|disease|breast cancer|人类|原文名称；未进行数据库映射。|
|D13|disease|thyroid cancer|人类|原文名称；未进行数据库映射。|
|D14|disease|diffuse midline glioma|人类|正文活检与表2均指 K3，WHO grade IV 为分级，不是另一肿瘤节点。|
|D15|disease|adrenal adenoma|人类|原文名称；未进行数据库映射。|
|D16|disease|left anterior cerebral artery infarction|人类|b0093 明确 ACA 为 anterior cerebral artery；不推断具体梗死病因。|
|D17|disease|occipital lobe epilepsy|人类|表2脚注明确定义 OLE。|
|D18|ambiguous|PLE|人类|表2 K3 临床表现出现 PLE，正文及脚注未定义，不能按常识补为某种癫痫。|
|D19|disease|cavernous malformation|人类|一般 CM 上位名称；不自动合并为脑 CCM 或脊髓/皮肤亚型。|
|D20|disease|vascular malformation|人类；机制描述|宽泛畸形表述；b0100 是 KRIT1 蛋白组分功能推测，不足以支持对该宽泛家族的基因因果关系。|

CCM、FCCM、sporadic CCM、一般 CM、spinal CM、cutaneous CM 分开保留。原文因果句直接提及 CCM 时才建立 CCM 关系，不把亚型关系自动向上或横向传播。CASH 是病变伴症状性出血复合条件；发作类型、头痛、复视等单列为症状，不补入疾病诊断。PLE 未展开，不能与 OLE 或任何推测名称合并。

## C. 全候选组合

8 × 20 = **160** 对，全部写入 candidate_pairs.csv/json，包括 PLE 候选；状态统计：{'supported': 10, 'not_found': 139, 'uncertain': 11}。

relation_type 的 none 表示没有可确认的关系类型，并不是无关系证明。not_found 行的 source_scope 不确定表示没有正面关系来源可归属；如果有已排查的共存或阴性片段，则标其实际来源。not_found 的空 evidence 表示未找到支持片段，检查范围已在 reason/conditions 与 source_blocks 文件中列明，绝不编造“未发现”的原文引语。

|边ID|基因|疾病|关系|来源|证据位置|判断|
|---|---|---|---|---|---|---|
|E01|G01|D01|causal|背景引用|b0011|正文直接针对 CCM 描述三个基因的失功能致病机制；不是把家族性亚型关系自动向上推广。|
|E02|G01|D02|causal|两者兼有|b0003, b0028|背景明确将三个基因的失功能变异归为 FCCM 病因；本研究检出对应患者变异。causal 来自背景陈述，本研究为观察性结果，不是新的因果验证。|
|E03|G02|D01|causal|背景引用|b0011|正文直接针对 CCM 描述三个基因的失功能致病机制；不是把家族性亚型关系自动向上推广。|
|E04|G02|D02|causal|两者兼有|b0003, b0028|背景明确将三个基因的失功能变异归为 FCCM 病因；本研究检出对应患者变异。causal 来自背景陈述，本研究为观察性结果，不是新的因果验证。|
|E05|G03|D01|causal|背景引用|b0011|正文直接针对 CCM 描述三个基因的失功能致病机制；不是把家族性亚型关系自动向上推广。|
|E06|G03|D02|causal|两者兼有|b0003, b0028|背景明确将三个基因的失功能变异归为 FCCM 病因；本研究检出对应患者变异。causal 来自背景陈述，本研究为观察性结果，不是新的因果验证。|
|E07|G05|D03|association|背景引用|b0098, b0098|联合疾病患者中确认的功能获得突变、与CCM基因失功能的互斥模式及相关机制讨论，支持背景关联，超过单纯名称共现；保守不升级为因果。|
|E08|G06|D01|causal|背景引用|b0099|正文将各基因的杂合缺失与诱导 CCM 动物模型直接相连；模型因果证据与人类节点分开保留。|
|E09|G07|D01|causal|背景引用|b0099|正文将各基因的杂合缺失与诱导 CCM 动物模型直接相连；模型因果证据与人类节点分开保留。|
|E10|G08|D01|causal|背景引用|b0099|正文将各基因的杂合缺失与诱导 CCM 动物模型直接相连；模型因果证据与人类节点分开保留。|

KRIT1/CCM2/PDCD10–FCCM 的 causal 类型来自背景明确的致病陈述；本研究仅增加人类变异病例观察。不是作者新做的因果实验。ZPLD1–FCCM 仅为论文转述“proposed”关联，未叙述证据结果，保守保留 uncertain，图中 ZPLD1 为孤立节点。MAP3K3–sporadic CCM 有背景GOF变异确认与突变互斥模式的联合证据，但 MAP3K3–FCCM 仅为 could 的推测，保留 uncertain。

表1/表2的肿瘤、脊髓/皮肤CM、OLE等个案共存记录没有直接升级为基因关系。b0094 的首次CASH基因型组间差异不显著，并不等于分别否定三个基因与CASH的关系。b0094/b0095 中 PDCD10 组年龄—大病灶数量无显著相关，比较变量是年龄与病灶数，也不等于 PDCD10–CCM/FCCM explicit_negative。因此本篇在当前基因—疾病粒度没有可严谨赋值的 explicit_negative 对；这些条件性阴性结果仍保留在证据和本说明中。

## D. 二部图

network.svg 为可编辑预览；network.graphml 为带属性的可编辑图；graph.json、nodes.csv、edges.csv 包括全部节点和 supported 边。每条边有独立 E 编号、原文证据、位置、来源及条件。保留所有孤立节点（包括 PLE），不将 uncertain、not_found 或 explicit_negative 画作边。动物模型边以紫色区分；物种缺失不据大小写猜测。

## E. 质量说明与自查

已重新通读正文、2张表及脚注和3幅图注，并核对全文大写缩写列表；特别检查讨论中的ZPLD1、MAP3K3/MEKK3、动物模型名称及表2非主要诊断。核对 KRTI1 与 KRIT1、CMM 与 CCM、PLE 与 OLE；人类/动物范围分开。所有实体提及与关系引用的字符串存在性、完整笛卡尔积、重复配对、图节点/边一致性通过程序检查，详见 audit.json。该检查不能证明生物学解释完全正确，不是独立人工验证。

未解决：图片像素和补充DOCX覆盖；PLE含义；动物模型具体物种；ZPLD1所提关联的证据强度；MAP3K3对FCCM的假设；宽泛vascular malformation的关系范围；两处疑似排字错误。没有读取被引论文来独立验证背景研究，也未借外部知识补全实体或边。原文样本小、单中心、回顾性与检出偏倚限制均适用。未计算或编造准确率、召回率或置信度分数。
