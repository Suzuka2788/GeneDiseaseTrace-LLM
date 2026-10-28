"""Pack rules, output format and the parsed paper into one request for a tool-free, single-response run.

Usage: python -m toolkit.pack [--rules full|card]   # writes work/request.md
The fixed part (task, rules, output format) comes first and the paper last, so runs share the same prefix.
"""
import argparse
from pathlib import Path

from .common import RULE_FILES, SKILL_DIR, load_article, rule_info, sha256

OUTPUT_FORMAT = """\
## 输出格式（只输出一个 JSON 对象，不要任何其他文字或代码块标记）

你看不到文件、也不能运行工具；原文已在下面按块给出。你只负责判断，名称定位、偏移计算、矩阵补全、文件生成和校验由程序完成。
"简洁"只针对文字：理由每条一句话，只写下面列出的字段，没有内容的字段可以省略。覆盖范围必须完整，不能为了省字而少列：
- 逐块检查全部原文（标题、摘要、正文、每一行表格、每条图注、表注），把出现的每个基因、疾病、症状和表型都列入 entities，辅助实体（symptom/phenotype）同样要列全；
- 名称看似是类别、工具、数据库或解剖部位时，列入 excluded 并给出理由；
- 核对正文、表格、图注之间的数值或描述是否互相矛盾，有就写入 conflicts；
- 本研究的统计、比较或机制结果写入 findings。

{
  "input_scope": "A 部分：实际可读范围与限制（一两句）",
  "exposure": "是否接触过本文既往结果或 skill 边界案例",
  "language": "en",
  "units": [{"id": "u1", "title": "...", "blocks": "b0001-b0120"}],      // 只有多研究文件（会议合集等，R9）才需要；单研究省略
  "entities": [
    {"id": "G01", "type": "gene|disease|symptom|phenotype|clinical_event|ambiguous",
     "name": "统一名", "forms": ["原文写法1", "原文写法2"],               // 必须是原文逐字出现的写法；程序按完整词、区分大小写在原文中查找全部出现
     "side": "gene|disease",          // 仅 ambiguous 需要
     "unit": "u1",                    // 仅多单元文件需要
     "status": "resolved|provisional|unresolved", "issues": ["suspected_typo", "..."],   // 省略 = resolved、无问题
     "species": "human", "host": null, "parent": "D01", "primary": false,   // primary 省略时：symptom/phenotype 为 false，其余为 true
     "note": "一句话：合并依据、层级依据或歧义"}
  ],
  "excluded": [{"surface": "...", "block": "b0019", "reason": "一句话", "label": "table_grouping_label"}],
  "evidence": [
    {"id": "E01", "block": "b0011", "quote": "从该块逐字复制的片段；省略表示引用整块（适合表格行）",
     "scope": "背景引用|本研究结果|两者兼有|不确定",
     "kind": "reported_result|background_relation_statement|hypothesis|aim|interpretation|negative_result|descriptive_cooccurrence",
     "asserted": "affirmed|negated|hypothetical|questioned|not_asserted|presupposed",
     "basis": ["explicit_background_report", "..."], "translation": "非英文原文才需要", "cond": {"citation_absent": true}}
  ],
  "pairs": [                         // 只列不是普通 not_found 的配对；未列出的组合由程序记为 not_found
    {"gene": "G01", "target": "D02", "status": "supported|explicit_negative|uncertain|not_found",
     "type": "causal|correlation|association",          // supported 时为主表类型；explicit_negative 时为被检验的类型
     "scope": "背景引用|本研究结果|两者兼有|不确定",
     "ev": ["E01"],                                      // 支持主表结论的证据
     "claims": [{"status": "supported", "type": "association", "scope": "本研究结果", "ev": ["E02"]}],   // 仅当有多条主张时才写；单条主张用上面的 type/scope/ev 即可
     "unresolved": ["hedged_claim"], "context": ["E05"], "obs": ["E03"], "conflicts": ["DC1"],
     "cond": {"evidence_species": "non-human", "gene_alteration": "...", "model_type": "..."},
     "reason": "一句话"}
  ],
  "findings": [{"id": "F1", "type": "association|correlation|group_comparison|descriptive|mechanism|hypothesis|other",
                "variables": "...", "group": "...", "scope": "本研究结果", "ev": ["E05"],
                "significance": "significant|not_significant|mixed|unknown|not_applicable",
                "direction": "positive|negative|mixed|null|unknown|not_applicable",
                "stats_available": "available|partial|unread|not_reported|not_applicable", "stats": "原文统计量或 null",
                "unread": "依赖的未读附件", "limits": "一句话"}],
  "conflicts": [{"id": "DC1", "subject": "...", "statements": [{"block": "b0007", "value": "..."}],
                 "impact": "noncritical|status_critical|undetermined", "resolution": "resolved|unresolved", "reason": "一句话"}],
  "unread": [{"name": "Table S1", "where": "b0114", "why": "外部附件未提供"}],
  "unresolved": [{"item": "...", "reason": "一句话"}],
  "feedback": [{"rule": "R4", "where": "b0098", "problem": "一句话", "handling": "一句话"}]
}

上面的 // 说明只为解释字段，你的输出必须是合法 JSON，不能带注释。

程序检查（不通过会把问题清单发回给你修正）：每个 forms 写法和 quote 必须在原文逐字存在；supported 需有证据，主表 type 取所有 supported 主张中展示优先级最高者（causal > correlation > association），scope 对应该主张的来源，背景与本研究都支持同一类型时为两者兼有；explicit_negative 需有证据；uncertain 需有 unresolved；非 supported 的配对不填 type（explicit_negative 的 type 表示被检验的类型）；配对两端必须是主矩阵中的基因和目标。
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rules", choices=("full", "card"), default="full",
                        help="full = the skill's three rule files; card = toolkit/rules_card.md (compressed)")
    args = parser.parse_args()
    xml_path, article, _ = load_article()
    version, hashes = rule_info()
    if args.rules == "card":
        rules = (Path(__file__).resolve().parent / "rules_card.md").read_text(encoding="utf-8")
    else:
        rules = "\n\n".join(f"===== {Path(name).name} =====\n{(SKILL_DIR / name).read_text(encoding='utf-8')}" for name in RULE_FILES)
    blocks = "\n".join(f"[{b['block_id']} | {b['content_type']} | {b['section']}] {b['text']}" for b in article["blocks"])
    request = f"""# 任务
按下面的 biomed-gene-disease-evidence 规则（版本 {version}），独立分析文末给出的这一篇论文：提取全部基因和疾病，判断所有基因×疾病候选组合的关系，按规定的 JSON 格式一次输出你的全部判断。只依据本文内容，不用已有医学知识补全关系。规则中提到的 boundary-cases.md、model-comparison.md、CHANGELOG.md 本任务不提供，也不需要。规则中关于读取文件、运行程序、生成 CSV/GraphML/图和校验的要求，由程序替你完成。

# 规则
{rules}

{OUTPUT_FORMAT}
# 论文
paper_id: {article['paper_id']}
标题: {article['title']}
类型: {article['article_type']}；解析警告: {'; '.join(article['warnings']) or '无'}
输入 SHA-256: {sha256(xml_path)}；参考文献列表已排除；图片像素与外部附件不可读。
原文共 {len(article['blocks'])} 块，格式为 [块编号 | 内容类型 | 章节] 文本：

{blocks}
"""
    work = Path("work")
    work.mkdir(exist_ok=True)
    (work / "request.md").write_text(request, encoding="utf-8")
    print(f"work/request.md: {len(request)} characters ({article['paper_id']}, rules {version})")


if __name__ == "__main__":
    main()
