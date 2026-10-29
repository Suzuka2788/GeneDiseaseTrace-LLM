# 工具包使用说明（toolkit 0.1.0）

分工：**你（模型）负责判断，工具负责其余所有事情。** 你只写一个 `judgments.json`，工具会定位全部名称提及、计算引文偏移、把没列出的配对补成 not_found、按 data-contract 检查格式，并生成全部交付文件（CSV、JSON、GraphML、SVG、预览页和校验报告）。不要自己另写解析、输出或校验脚本。

所有命令都在运行目录（含 `input/`、`biomed/`、`skill/`、`toolkit/` 的目录）下执行：

```
python -m toolkit.blocks                         # 解析原文，写 work/blocks.txt（带块编号，供通读）
python -m toolkit.find "KRIT1" [--ignore-case] [--whole-word] [--regex]   # 查某个名称或引文在哪些块、什么位置
python -m toolkit.build judgments.json --check   # 只检查，不写文件；有问题会逐条列出
python -m toolkit.build judgments.json           # 生成 outputs/<paper>/rules-<版本>/<run_id>/ 并自动校验
```

建议流程：先 `blocks` 通读全文 → 边读边写 `judgments.json` → 反复 `--check` 直到没有问题 → 最后正式 `build` 一次。每次正式 build 都会生成新的 run_id 目录，不覆盖旧的。

## judgments.json 结构

字段含义以 skill 的 `references/data-contract.md` 为准；这里只说明工具怎么读。枚举值必须与 data-contract 完全一致（例如 source_scope 用中文固定值）。

```json
{
  "paper_id": "必须与输入论文一致",
  "model_identifier": "实际模型名；不确定写 unknown_model",
  "exposure": {"statement": "是否接触过本文既往结果或 skill 边界案例"},
  "language": "en / es / ...",
  "completion": "complete 或 partial（没做完全部单元时）",
  "input_scope": "A 部分：实际读取的范围与限制",
  "units": [{"unit_id": "u1", "title": "...", "blocks": "all"}],
  "entities": [...],
  "gene_sets": [...],
  "excluded_candidates": [...],
  "evidence": [...],
  "pairs": [...],
  "default_not_found_reason": "可选；未列出的配对使用的理由",
  "study_findings": [...],
  "data_conflicts": [...],
  "unread_attachments": [...],
  "scope_exclusions": [...],
  "unresolved": [...],
  "rule_feedback": [{"rule": "R4", "location": "b0098", "problem": "...", "handling": "..."}]
}
```

**units**：单研究论文可以省略（默认一个单元 `u1` 覆盖全文）。多研究文件（如会议摘要合集）按 R9 划分，`blocks` 可写 `"b0010-b0042"` 或其列表。每个实体属于一个单元；配对只在同一单元内生成，跨单元组合不生成。

**entities**：每个实体一项，字段同 data-contract（entity_id、entity_type、candidate_side、canonical_name、identity_status、identity_issues、gene_species、host_species、species_scope、ambiguity、merge_basis、parent_id、hierarchy_basis、qualifiers、in_primary_matrix、database_id、reference_sequences_from_text），另加：
- `surface_forms`（必填）：原文中实际出现的写法列表。工具会在该单元的全部文本中按完整词边界查找每一处出现（区分大小写）；多个实体的写法重叠时，较长的匹配优先。可写成对象以设置选项：`{"surface": "MEKK3", "role": "protein_product"}`、`{"surface": "headache", "ignore_case": true}`。
- `extra_mentions`（可选）：回指等无法用写法自动定位的提及，`{"block_id": "b0011", "surface": "these genes", "occurrence": 1, "mention_role": "local_coreference", "contextual_referent": "...", "coreference_path": "..."}`。
- `in_primary_matrix` 省略时：symptom、phenotype 为 false（进入辅助表），其余为 true。
- 每个实体至少要有一处能在原文中找到的写法，否则 build 报错。

**evidence**：`{"evidence_id", "block_id", "quote", "translation", "source_scope", "assertion_kind", "relation_asserted", "support_basis": [...], "supports", "conditions": {...}, "evidence_link_path", "distribution_basis"}`。`quote` 必须是该块中逐字存在的片段（先用 `toolkit.find` 确认）；省略 `quote` 表示引用整块（适合表格行）。偏移由工具计算。

**pairs**：只需列出你实际判断过、且不是默认 not_found 的配对；也可以列出带 context_checked 的 not_found。未列出的组合自动记为 not_found。每项字段：`gene_id, disease_id, status, relation_type, tested_relation_type, source_scope, claims: [...], reason, conditions, unresolved_reason: [...], context_checked: [...], observational_context: [...], data_conflict_ids: [...]`。
- claims 每项：`claim_id, status, relation_type 或 tested_relation_type, source_scope, evidence_ids, conditions, reason`。
- 工具会检查：supported 必须有带证据的 supported claim，主表 relation_type 和 source_scope 要符合 R3 的展示优先级与来源规则；explicit_negative 要有带证据的 explicit_negative claim；uncertain 要有 unresolved_reason；非 supported 的 relation_type 为 none；所有证据 ID 和冲突 ID 都要存在。
- 非人类证据在 `conditions` 里写 `evidence_species`、`gene_alteration`、`model_type`、`host_species`。

**study_findings / data_conflicts**：字段同 data-contract；工具检查枚举值和证据 ID。

## 工具不能替你做的

工具只检查结构、引文和一致性，不判断语义是否正确。名称有没有漏、关系判得对不对、规则怎么适用，仍然由你按 skill 判断。

## 单次请求模式（archive/scripts/oneshot.py）

不让模型使用工具，而是由程序把规则、输出格式和原文打包成一个请求（`python -m toolkit.pack [--rules full|card]` 生成 `work/request.md`），模型一次返回精简 JSON（格式写在 `toolkit/pack.py` 的 OUTPUT_FORMAT 里），`python -m toolkit.expand` 把它展开成 `judgments.json`，再由 `toolkit.build` 检查和生成全部文件。检查不通过时，问题清单会发回给模型修正，最多两次。

`--rules card` 使用 `toolkit/rules_card.md`：这是 skill 1.3.0 三份规则文件的压缩版（约三分之一长度），只供单次请求使用，语义以 skill 原文为准。用 `scripts/rule_cases.py` 可以拿 skill 的冻结边界案例比较压缩版和原文的判断是否一致。
