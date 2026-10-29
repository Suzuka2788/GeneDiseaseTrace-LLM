# 第二轮：PMC10014009（Skill v1.0.0）

论文：Clinicoradiologic data of familial cerebral cavernous malformation with age-related disease burden。DOI：10.1002/acn3.51728。

## A. 输入范围与限制

本轮仍分析第一篇论文，使用biomed-gene-disease-evidence 1.0.0直接重读原始JATS XML；未载入上一轮、Claude或比较裁决结果文件作为证据。当前会话已接触之前结论，因此这是重做，不是盲法独立验证。原始文件及既有结果不覆盖。

检查标题、摘要、正文、两张表全部55行与脚注、三幅图注及补充说明，共117个文本块。引用使用source_blocks.txt中的b编号；原文空白、Unicode和标点经规范化，原始XML不改。表格原结构另存source_tables.json，table_cells保留列和患者/基因分组。

未提取参考文献列表实体。XML只链接3张JPG和补充DOCX，本地输入未附这些文件；图片内文字和S1–S3实际内容没有读取。图注可读不等于图片已读；不宣称完整含附件全文已检查。本文没有明确出现需要另建节点的抗体标记物、报告构建体或跨物种序列比较；这不是附件中不存在的保证。

## B. 实体表与身份核对

主矩阵：8个基因范围节点 × 21个目标（19个疾病/疾病家族、1个临床事件CASH、1个未解决诊断候选PLE）。症状17项、一般表型2项保存在辅助范围，不计作疾病，不画主图。全部48项在entities.csv/json，原文名称raw_names，逐次上下文/角色mentions。

别名仅有原文展开或上下文依据时合并；D20 vascular malformation和D21 intracranial vascular malformation分开。CM、CCM、FCCM、散发CCM及脊髓/皮肤亚型分开。PLE不展开、不与OLE合并。人类与动物基因节点分开，具体动物物种未知；MAP3K3的MEKK3提及标为protein_product。KRTI1/CMM疑似笔误保留原名与合并依据。侧别、分级、症状限定及局部回指另存；局部CM回指不当全局别名。

|ID|类型|统一名称|物种或范围|主矩阵|
|---|---|---|---|---|
|D01|disease|cerebral cavernous malformation|人类；b0099另用于动物模型|是|
|D02|disease|familial cerebral cavernous malformation|人类|是|
|D03|disease|sporadic cerebral cavernous malformation|人类|是|
|D04|disease|spinal cavernous malformation|人类|是|
|D05|disease|cutaneous cavernous malformation|人类|是|
|D06|clinical_event|cavernous angioma with symptomatic hemorrhage|人类|是|
|D07|disease|small vessel disease|人类|是|
|D08|disease|diffuse axonal injury|人类|是|
|D09|disease|intracerebral hemorrhage|人类|是|
|D10|disease|developmental venous anomaly|人类|是|
|D11|disease|tumor|人类|是|
|D12|disease|breast cancer|人类|是|
|D13|disease|thyroid cancer|人类|是|
|D14|disease|diffuse midline glioma|人类|是|
|D15|disease|adrenal adenoma|人类|是|
|D16|disease|left anterior cerebral artery infarction|人类|是|
|D17|disease|occipital lobe epilepsy|人类|是|
|D18|ambiguous|PLE|人类|是|
|D19|disease|cavernous malformation|人类|是|
|D20|disease|vascular malformation|人类/一般机制描述|是|
|D21|disease|intracranial vascular malformation|人类疾病定义|是|
|G01|gene|KRIT1|Homo sapiens；本研究为患者血样测序|是|
|G02|gene|CCM2|Homo sapiens；本研究为患者血样测序|是|
|G03|gene|PDCD10|Homo sapiens；本研究为患者血样测序|是|
|G04|gene|ZPLD1|人类FCCM背景语境，原句未显式标注物种|是|
|G05|gene|MAP3K3|人类散发CCM患者背景语境|是|
|G06|gene|Krit1|非人动物模型；具体物种未注明|是|
|G07|gene|Ccm2|非人动物模型；具体物种未注明|是|
|G08|gene|Pdcd10|非人动物模型；具体物种未注明|是|
|S01|symptom|seizure|人类|辅助|
|S02|symptom|focal impaired awareness seizure|人类|辅助|
|S03|symptom|focal to bilateral tonic-clonic seizure|人类|辅助|
|S04|symptom|emotional seizure|人类|辅助|
|S05|symptom|headache|人类|辅助|
|S06|symptom|neck pain|人类|辅助|
|S07|symptom|dizziness|人类|辅助|
|S08|symptom|weakness|人类|辅助|
|S09|symptom|dysarthria|人类|辅助|
|S10|symptom|facial palsy|人类|辅助|
|S11|symptom|diplopia|人类|辅助|
|S12|symptom|visual symptoms|人类|辅助|
|S13|symptom|visual disturbance|人类|辅助|
|S14|symptom|central vertigo|人类|辅助|
|S15|symptom|drowsy mentality|人类|辅助|
|S16|symptom|decreased mentality|人类|辅助|
|S17|phenotype|cerebral microbleeds|人类|辅助|
|S18|phenotype|neurological sequelae|人类|辅助|
|S19|symptom|transient positive visual symptom|人类|辅助|

数据库实体编号未验证，留空；b0019测序参考序列另列。数据库/软件/指南代码、解剖位置、一般事件及基因集合在excluded_candidates中保存，不推断新基因或疾病。

## C. 全部候选关系

完整168对，状态为 {'supported': 10, 'uncertain': 16, 'not_found': 142}。not_found不是无关联证明；uncertain必须注明identity、亚型特异性、指代或解释等具体原因。

每个关系有主状态和原文证据；证据单独带source_scope、assertion_kind、supports及条件。背景因果与本研究变异病例观察分开，后者在observational_context，不能冒充本研究验证因果。not_found可以没有支持引语，但易误读的共病/组阴性放context_checked，保留原文。

|边|基因|目标|类型|来源|证据|
|---|---|---|---|---|---|
|ED01|KRIT1|cerebral cavernous malformation|causal|背景引用|EV001|
|ED02|KRIT1|familial cerebral cavernous malformation|causal|背景引用|EV002|
|ED03|CCM2|cerebral cavernous malformation|causal|背景引用|EV001|
|ED04|CCM2|familial cerebral cavernous malformation|causal|背景引用|EV002|
|ED05|PDCD10|cerebral cavernous malformation|causal|背景引用|EV001|
|ED06|PDCD10|familial cerebral cavernous malformation|causal|背景引用|EV002|
|ED07|MAP3K3|sporadic cerebral cavernous malformation|association|背景引用|EV005, EV006|
|ED08|Krit1|cerebral cavernous malformation|causal|背景引用|EV007|
|ED09|Ccm2|cerebral cavernous malformation|causal|背景引用|EV007|
|ED10|Pdcd10|cerebral cavernous malformation|causal|背景引用|EV007|

关键未解决判断：ZPLD1–FCCM结合could/proposed及整段语境仍无结果细节，保留uncertain，并非一见proposed就排除。MAP3K3–散发CCM由confirmed GOF与互斥模式联合支持association；向FCCM的could为假设，不连边。三个人类基因–散发CCM有间接双打击背景但亚型映射未明，保留uncertain。三基因–广义血管畸形的机制/范围未清，保留uncertain。PLE身份未明的8对uncertain不表示存在弱关联。

首次CASH基因型组间不显著结果另存F01；S3未提供，不能逐基因标explicit_negative。PDCD10组年龄–病灶数不显著另存F03，不否定PDCD10–CCM/FCCM。临床特征的检出/未检出合并组阴性另存F04，不拆给每个基因和症状。7项study_findings保留实际统计变量与条件；各临床共病只有个案记录，未据此建立基因边。

## D. 二部图及编辑数据

graph.json、nodes.csv、edges.csv、network.graphml保存29个主节点及10条supported边；network.svg可编辑，network.png为预览。孤立节点全部保留；CASH显示为临床事件，PLE显示为未解决候选。紫色边限动物模型；每条ED边连接EV证据及原文位置。症状/表型辅助表项不伪装为疾病图节点。

## E. 质量说明

已复核全部可读文本、两张表、脚注、三幅图注及讨论次要名称；检查否定、条件、别名、物种、基因集合修饰语、蛋白角色和非支持候选。大写名称候选扫查用于辅助找漏，不作为提取完整性的保证。

引用/提及偏移存在性、全部笛卡尔积集合与唯一性、证据ID、uncertain原因、图节点和supported边集合通过程序检查，详见audit.json。这不证明语义准确、没有遗漏，也不是独立人工验证；无准确率、召回率或置信度分数。

- PLE：诊断缩写未定义；8对候选保留uncertain。（b0076）
- ZPLD1—FCCM：当前论文未提供proposed关联的结果细节，保留待审核。（b0098）
- MAP3K3—FCCM：could及these genes指代；散发亚型结果不能补足。（b0098）
- 人类三基因—散发CCM：间接双打击背景，缺乏明确逐基因亚型对应。（b0098, b0026）
- 人类三基因—广义血管畸形：范围宽泛且为机制/功能解释。（b0011, b0100）
- 动物Krit1/Ccm2/Pdcd10：具体动物物种未指明；支持边仅限模型。（b0099）
- CASH首次时点逐基因对比：缺S3，未将组阴性拆成单基因阴性。（b0094, b0116）
- 图片与S1—S3实际数据：仅链接JPG与DOCX，无法检查附件新增实体。（b0027, b0068, b0095, b0114, b0115, b0116）
- KRTI1/CMM疑似笔误：上下文支持合并，但没有作者勘误确认。（b0005, b0099）


文件索引：entities、raw_names、mentions、candidate_pairs、evidence、excluded_candidates、table_cells、study_findings、unresolved、nodes、edges均提供CSV/JSON；另有原文文本/表格结构、GraphML、SVG/PNG预览及manifest。manifest记录规则/脚本/输入哈希和实际覆盖。当前会话的重复核查不构成独立模型复现实验。
