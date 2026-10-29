# PMC10014009 三模型盲测比较（规则 1.2.0）

比较执行者：Claude Opus 5.5（本会话）。本会话看过边界案例的预期答案，也写过 1.1.0 的结果，不是中立方；下面的归类是初步意见，有争议的条目由用户裁决。

## 输入

| 模型 | 输出目录 | 备注 |
|---|---|---|
| GPT-6 Astra | `C:\Users\tongz\blind_PMC10014009_aborted_GPT-6_Astra\outputs_unknown_model_blind\…\20261027T224351018600Z_46a7b4ba` | 写在原来标为作废的目录里；用的是 jats.py，规则哈希一致 |
| GPT-6.1 sol | `C:\Users\tongz\blind_PMC10014009_GPT-6.1_sol\outputs_unknown_model_blind\…\20261027T223038Z-6b593930` | |
| Claude Opus 5.5 | `C:\Users\tongz\blind_PMC10014009_Claude_Opus_5.5\outputs_Claude_Opus_5.5_blind\…\20261027T223308Z_41176b9a` | |

三份都声明没有接触过既往结果或边界案例。

## 公共校验（scripts/validate_contract.py）

三份全部通过：原文和规则哈希、提及偏移、证据引文和偏移、完整矩阵、状态字段要求、证据 ID 引用、edges.csv 和 GraphML 与 supported 一致、manifest 计数。报告见 `validation_<模型>.json`。通过只说明结构合规、引文真实，不说明判断正确。

| | Astra | sol | Claude |
|---|---|---|---|
| 基因 × 主目标 | 8 × 22 = 176 | 8 × 19 = 152 | 8 × 19 = 152 |
| supported / uncertain / not_found | 9 / 3 / 164 | 9 / 2 / 141 | 9 / 6 / 137 |
| explicit_negative | 0 | 0 | 0 |

## 一致的部分

对齐后共 176 个基因 × 目标组合（`aligned_pairs.csv`，对照表 `entity_alignment.json`）：143 个三方完全一致，27 个在有该实体的模型之间一致，6 个不一致。

- 9 条 supported 边完全相同，关系类型都是 causal、来源都是背景引用：KRIT1/CCM2/PDCD10 各连 CCM 和 FCCM，三个动物模型基因各连 CCM。
- ZPLD1 → FCCM、MAP3K3 → FCCM 三方都判 uncertain。
- CASH、PLE 的所有配对三方都判 not_found；没有任何模型给出逐基因的 explicit_negative。
- 三方都把 KRTI1 归到 KRIT1、CMM 归到 CCM，并标注疑似笔误；都把动物模型基因单独建节点、物种留空。

## 不一致与初步归类

### 1. MAP3K3 → 散发性 CCM（规则歧义）
- Astra、sol：not_found；Claude：uncertain（support_basis_unresolved）。
- 原文 b0098："gain-of-function (GOF) mutations in MAP3K3 … have been confirmed in sporadic CCM patients"，下一句说它与 CCM 基因功能丧失互斥。
- 三方都没有判 supported，而 1.2.0 之前的几轮都判过 supported。原因是 R4 "confirmed 仅确认变异检出 → 描述性记录" 和 R3 "患者中检出不够"。分歧在于"互斥模式"算不算额外的支持依据：两个 GPT 认为不算，Claude 认为有线索但不足。
- 这条需要用户决定规则意图：被引研究"在某病患者中确认存在某基因的致病性变异"，是否应算明确的背景疾病关联。

### 2. 人类基因 → 血管畸形（实体处理差异 + 规则歧义）
- 实体层面三方各不相同：
  - Astra：一般"vascular malformation"和"intracranial vascular malformation"分成两个节点（符合 R7，边界案例 BC27 也明确不能合并）。
  - sol：两者都没进主矩阵，一般"vascular malformation"放进排除表，理由是泛称类别。与 R1"疾病家族进主矩阵"不一致，按执行偏差记。
  - Claude：把一般"vascular malformation"并入"intracranial vascular malformation"。这违反 R7 和 BC27，属于执行错误。
- 关系层面：KRIT1 依据 b0100 "likely critical for preventing vascular malformation"，Astra 和 Claude 都判 uncertain。CCM2/PDCD10 只有 b0011 "mechanisms underlying … vascular malformation suppression of the three CCM genes remain unknown" 这一句预设性陈述：Astra 判 not_found，Claude 判 uncertain。R4 判定表没有覆盖"预设在'机制未知'句中的关系"，属于规则歧义（Claude 的 rule_feedback 第 2 条也提出了）。

### 3. 只有部分模型记录的实体（执行差异）
- **一般 CM（cavernous malformation）**：Astra、sol 有，Claude 没有。Claude 的 rule_feedback 说"通用名 CM 从未单独出现"，但表 1/表 2 的注释（b0064、b0093）写明 "CM, cavernous malformation"，b0016 也有 "spinal cavernous malformation (CM)"。这是 Claude 的漏检。
- **non-cerebral CM**：只有 Astra 把表 2 的列名"Non-cerebral CM"建成部位限定的疾病类别。R1 没规定表头类别是否要建节点，属于轻微的规则歧义。
- 辅助实体（21 / 30 / 26）和 study_findings（28 / 25 / 18）数量差别较大，还没有逐项对齐。

### 4. 三方共同提出的规则反馈
- **R2**：物种未知但语境明确是动物模型时，可以单独建节点吗？R2 两句话之间有张力。三方都选择了分开，建议把这个做法写明。
- **R1/R15**：PLE 跟在箭头后，与 OLE 一行格式平行，三方都保留为 ambiguous 并判 not_found，结论一致。
- **R14**：三方都记录了论文内部的数值矛盾（AUC 0.928 / 0.982 等），都判为非关键。
- **R3/R4（Claude 第 4 条）**：摘要中没有引用文献的作者陈述被归为"背景引用"。与之前给 Codex 的意见相同，规则仍未写明。

## 小结

- 在决定 supported 边的那些关键判断上，三个模型按 1.2.0 执行得很稳定：9 条边一致，ZPLD1、CASH、PLE 的处理一致。
- 分歧集中在两类地方：一是规则没有覆盖的边界（MAP3K3 的"确认检出"、"机制未知"句中的预设关系、表头类别是否建节点）；二是实体粒度（一般 CM、一般和颅内血管畸形）。
- 实体粒度的差异不影响任何 supported 边，但会改变矩阵大小（152 和 176）和 uncertain 数量。

## 未做的部分
- 辅助实体、study_findings、data_conflicts 还没有逐项对齐。
- 对 not_found 判断的证据充分性没有抽查，只比较了状态。
