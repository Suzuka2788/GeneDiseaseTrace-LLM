# 输出格式

只输出下面这些行，不要输出任何其他文字、标题或代码块标记。每行一条记录，字段用 `|` 分隔，字段内容里不要出现 `|`。可选字段留空即可（保留分隔符）。引用证据只写句子编号（如 `b0012.s3`），不要抄原文。

```
META|你的实际模型名|是否接触过本文既往分析结果或该规则的边界案例（一句话）
SCOPE|实际读取范围与限制（一句话）
UNIT|单元ID|标题|块范围        （仅多研究文件需要，如 UNIT|u2|Abstract 2|b0040-b0071；单研究论文不写）
E|实体ID|类型|统一名|原文写法1;原文写法2|身份|身份问题|基因物种|上位实体ID|单元ID|候选侧
X|原文名称|块编号|排除原因
EV|证据ID|句子编号（同一块内连续句用+连接）|来源|主张类型|关系断言|支持依据
P|基因ID|目标ID|状态|关系类型|来源|主张|未决原因|仅作核对的证据ID|理由
F|发现ID|发现类型|变量|人群或组|显著性|方向|统计量可读性|证据ID|限制
C|冲突ID|主题|句子编号|影响|是否已解决|说明
U|附件名|引用位置|未读原因
R|规则编号|位置|问题|你的处理
```

取值代码：
- 类型：gene / disease / clinical_event / symptom / phenotype / ambiguous
- 身份：r（resolved）/ p（provisional）/ u（unresolved）
- 身份问题（逗号分隔）：undefined_abbreviation, suspected_typo, species_unresolved, ambiguous_mapping, other
- 基因物种：human / non-human / 留空（未知）
- 候选侧（仅 ambiguous）：gene / disease
- 来源：bg（背景引用）/ ts（本研究结果）/ both（两者兼有）/ unk（不确定）
- 主张类型：res（结果）/ bgr（背景关系陈述）/ hyp（假设）/ aim（目的）/ int（解释推断）/ neg（阴性结果）/ co（描述性共现）
- 关系断言：aff / neg / hyp / q / na / pre（预设）
- 支持依据（逗号分隔）：ebr（明确背景报告）, rr（报告结果）, eda（明确疾病归因）, cs（共分离）, cmp（对比结果）, mi（模型干预）, do（仅描述）, ho（仅假设）, unc（不清楚）, none
- 状态：sup / neg / unc / nf
- 关系类型：c（causal）/ r（correlation）/ a（association）/ -（none）
- 主张：分号分隔，每条写成 `状态:关系类型:来源:证据ID+证据ID`，如 `sup:c:bg:V1;sup:a:ts:V2+V3`
- 未决原因（逗号分隔）：identity, coreference, hedged_claim, support_basis_unresolved, presupposed_only, scope, conflict, missing_material, other
- 发现类型：association / correlation / group_comparison / descriptive / mechanism / hypothesis / other
- 显著性：significant / not_significant / mixed / unknown / not_applicable
- 方向：positive / negative / mixed / null / unknown / not_applicable
- 统计量可读性：available / partial / unread / not_reported / not_applicable
- 影响：noncritical / status_critical / undetermined；是否已解决：resolved / unresolved

规则：
- 只写需要说明的配对（sup、neg、unc，以及有容易误读证据、需要列出核对证据的 nf）。没写到的配对一律视为 nf。
- 理由一句话以内；能用规则编号说明的就用编号（如 `R5 总体检验，不拆给成员`）。
- 每个实体至少要有一个写法能在原文中逐字找到（区分大小写，完整词匹配）。
- 证据句子编号必须来自下面给出的论文；同一条证据只能在一个块内。
