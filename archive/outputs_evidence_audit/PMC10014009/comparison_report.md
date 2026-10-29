# PMC10014009：两模型结果的原文证据裁决

**A = outputs_GPT_6.1_sol；B = outputs_claude_Opus_5.5。两份结果均是待核查主张，原始XML是证据来源。**

## 输入和覆盖

题目：Clinicoradiologic data of familial cerebral cavernous malformation with age-related disease burden。

直接重解析输入 `.Input/100papers/PMC10014009.xml`。输入哈希与B manifest及A原始记录一致；同一套b0001–b0117位置为可核查定位。检查标题、摘要、正文、两张表全部55行及脚注、三幅图注、补充说明。参考文献列表不抽实体；正文转述可作背景。仅链接的3张JPG及补充DOCX未提供，未读取其像素/实际表格，因此附件中的共同遗漏暂无法排除。所有引用是空白、Unicode规范化后的精确原文片段，原始文件不改。

## 先对齐实体

基因身份共8个对齐，无一方独有的单基因。人类KRIT1/CCM2/PDCD10与动物Krit1/Ccm2/Pdcd10分别保留；具体动物物种未知。MAP3K3编码MEKK3，后者按蛋白提及记录；KRTI1与KRIT1的上下文笔误合并均可保留但有标记。没有按数据库编号前缀、解剖名称或变异编号补入基因。

B的39个疾病/候选表项不等于39个疾病。18项为症状或表型，A已保留在排除记录，并非A完全漏提。修订统一实体表保留全部这些名称，但分为symptom/phenotype辅助表项，不混入主疾病矩阵。B中Visual symptoms与Transient positive visual symptom缺少严格同义依据，进一步拆开，辅助实体共19个。

A把vascular malformation与intracranial vascular malformation合并，需支持B的分层处理；修订为D20与D21。CCM、FCCM、散发CCM、一般CM、脊髓CM、皮肤CM仍分开，PLE不与OLE合并。

**修订计数：8个基因，20个疾病/复合病症，1个未解决诊断候选PLE，19个辅助症状/表型，共48个实体。主候选矩阵为8×21=168对；辅助矩阵另存8×19=152对，不算疾病关系。**

完整身份对照见 entity_alignment.csv；它包含每个统一ID的A/B映射、分拆、原文依据和主表纳入标记。数字相同的A/B疾病ID不视为同一实体。例如A D04（spinal CM）对应B D05；A D19（CM）对应B D04。

## 逐项差异与裁决

完整45项裁决见 adjudications.csv/json，每项含双方主张、原文位置、原句、裁决、修订和限制。下列按议题合并显示，文件中逐实体/逐关系分行保留：

|议题|裁决|原文依据与修订|
|---|---|---|
|颅内血管畸形 vs 广义血管畸形|支持结果 B|b0011 “an intracranial vascular malformation”；b0100 “preventing vascular malformation”。上下位关系不是同义，拆开。|
|B主疾病表中的16项症状、2项表型|支持结果 A|b0026、表1、表2及b0070；名称保留为辅助表，不当疾病。每个名称有单独裁决。|
|Visual symptoms与Transient positive visual symptom|支持结果 A|b0040 与 b0082；保留宽泛症状类和具体表现的区别。|
|ZPLD1—FCCM|暂无法裁决|b0098 “F. Gianfrancesco et al. proposed that ZPLD1 mutation is associated with FCCM.” 当前论文未提供结果细节；保持uncertain，不强迫赞同某模型的实证解释。|
|KRIT1/CCM2/PDCD10—CASH|支持结果 A|b0021研究基因型与首次CASH时点；b0094 “The difference among the CCM mutation genotypes was not statistically significant (Table S3).” 仅组间整体结果，不能对每基因赋explicit_negative。单基因对not_found；组阴性另存F01。|
|三个基因—散发CCM|支持结果 B|b0098双打击模型含two somatic mutations in wild-type gene；b0026散发病例胚系检测阴性是排除条件。存在间接但非特异证据，改uncertain，不画边。|
|CCM2/PDCD10—广义vascular malformation|支持结果 B|b0011提到三基因的vascular malformation suppression而机制未知。A的空证据not_found遗漏此语句；改uncertain。|
|8个基因—未定义PLE|支持结果 A|b0076 “FIAS and FBTCS, 51YO → PLE”；全文未展开。疾病身份不明，保持uncertain。|
|MEKK3提及角色|支持结果 A|b0098 “MAP3K3, encoding MEKK3”。B文字说明正确，但mentions没有保存protein角色；修订提及类型。|
|因果背景与本研究观察的字段混合|两者均需修正|b0011为背景caused by；b0028为患者变异检测。原解释均有限定，但source_scope字段需拆清。因果边来源标背景，本研究记录留在observational_context。|
|疾病缩写的基因集合修饰语、部位回指|两者均需修正|“CCM genes”“FCCM gene”不能算独立疾病病例证据；b0070的“CM in the thoracic spinal cord”须记录脊髓回指。完善提及角色，不增加边。|
|年龄—病灶数和合并组阴性结果|两者均需修正|b0094/b0095、b0064/b0066，原有说明不足以结构化追踪每个统计问题。另存F01–F07，不能压成单基因关系。|
|缺失图片/补充材料中的共同遗漏|暂无法裁决|b0114–b0116只有说明，外部文件未提供。保留覆盖限制。|

## 双方一致项也回到原文复核

10条原有共同supported边都有独立原句复核，并非因模型一致而通过。人类三基因—CCM来自b0011的明确LOF致CCM陈述；人类三基因—FCCM来自b0003/b0011的明确背景病因陈述；MAP3K3—散发CCM来自b0098的确认GOF变异和互斥模式，保守作association；动物三基因—CCM来自b0099的模型诱导语句，只限动物条件。不把动物模型致病推广成人类证据，也不推断模型一定是小鼠。

双方对KRIT1携带者的乳腺癌、甲状腺癌、弥漫性中线胶质瘤、肾上腺腺瘤、ACA梗死、OLE，以及各基因携带者的脊髓/皮肤CM，均未画支持边。已回查表2和b0070，仍只有个案共存，没有指定基因与这些疾病的关联或因果证据。维持not_found，不以共同结论当证据。

共同遗漏/误判风险的处理：

1. 保留年龄与病灶数、首次CASH时点、检出/未检出合并组等实际变量和研究条件，避免把统计问题改写成基因是否致病。
2. b0102的大病灶数—早发发作关联是病灶与症状关系，不涉及指定基因，不能补成基因—癫痫边。
3. 一般CM在K3脊髓语境中的回指及sporadic/familial省略式名称已补充角色。命中名称不能自动当新增疾病或独立证据。
4. 只检查了已提供XML范围；无法声称图片及S1–S3中没有新实体。未发现可从该可读范围明确证明遗漏的第9个具体基因；这不是无遗漏保证。

## 修订交付与完整性

主关系表168对：{'supported': 10, 'uncertain': 16, 'not_found': 142}。10条supported边，16对uncertain，142对not_found，0条可确认的逐单基因explicit_negative。组水平阴性仍在study_findings中。


- revised_entities.csv/json：48个统一实体及类型、原文名、物种、位置、歧义、合并依据；in_primary_matrix区分主表与辅助名称。
- revised_mentions.csv/json：原文精确提及、完整上下文、蛋白/修饰语/省略/回指角色。
- revised_pairs.csv/json：完整168对，含A/B原状态、修订状态、关系类型、来源、证据、条件与裁决编号。
- auxiliary_pairs.csv/json：152个辅助症状/表型对，不静默删除B的额外候选。
- aligned_pair_comparison.csv/json：320个对齐后的主/辅助组合，包含一致和不一致的状态；不是320个疾病关系。
- adjudications.csv/json：45项逐项裁决；entity_alignment.csv/json：全实体身份映射。
- study_findings.csv/json：7项统计/观察结果，阴性与条件不会丢失。
- unresolved.csv/json：9类未解决问题；source_blocks.txt/json：本轮原文定位。
- revised_graph.json/revised_edges.csv：只含主实体与10条supported关系，29个主节点全部保留。

所有A/B非空关系引用均在当前规范化原文找到；修订引用与提及字符偏移、完整笛卡尔积和唯一性通过校验。45条B关系引用存在不意味着45条语义判断正确；这些存在性校验不能代替证据裁决。原模型输出未覆盖。本次复核是模型分析与程序检查，不是独立人工验证，没有准确率、召回率或置信度分数。
