"""Check whether the condensed card leads to the same answers as the full skill rules on the 35 boundary cases.

Usage: python experiments/single_shot/card_check.py --model Claude_Opus_5.5 [--effort medium] [--conditions card full]

For each condition the model gets the rules plus all cases in one request, without the expected answers,
rationales or rule numbers (the card has no rule numbers). Answers are scored field by field against the
frozen expectations, and the two conditions are compared case by case. Results go to runs/card_check/<stamp>/.
"""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from common import HERE, RUNS
from run import call

SKILL = Path.home() / ".codex/skills/biomed-gene-disease-evidence"
ENUMS = {
    "status": "supported / explicit_negative / uncertain / not_found",
    "relation_type": "causal / correlation / association / none",
    "tested_relation_type": "causal / correlation / association",
    "source_scope": "背景引用 / 本研究结果 / 两者兼有 / 不确定",
    "unresolved_reason": "list of: identity, coreference, hedged_claim, support_basis_unresolved, presupposed_only, scope, conflict, missing_material, other",
    "identity_status": "resolved / provisional / unresolved",
    "identity_issues": "list of: undefined_abbreviation, suspected_typo, species_unresolved, ambiguous_mapping, other",
    "impact": "noncritical / status_critical / undetermined",
    "reported_significance": "significant / not_significant / mixed / unknown / not_applicable",
    "statistics_availability": "available / partial / unread / not_reported / not_applicable",
    "effect_direction": "positive / negative / mixed / null / unknown / not_applicable",
    "finding_type": "association / correlation / group_comparison / descriptive / mechanism / hypothesis / other",
    "relation_asserted": "affirmed / negated / hypothetical / questioned / not_asserted / presupposed",
    "assertion_kind": "reported_result / background_relation_statement / hypothesis / aim / interpretation / negative_result / descriptive_cooccurrence",
    "support_basis": "list of: explicit_background_report, reported_result, explicit_disease_attribution, co_segregation, comparative_result, model_intervention, descriptive_only, hypothesis_only, unclear, none",
    "entity_type": "gene / disease / clinical_event / symptom / phenotype / ambiguous",
    "depends_on_unread": "list of attachment names, or []",
    "conditions": "object, e.g. {\"citation_absent\": true} or {}",
}


def rules_text(condition):
    if condition == "card":
        return (HERE / "card.md").read_text(encoding="utf-8")
    parts = ["SKILL.md", "references/decision-rules.md", "references/data-contract.md"]
    return "\n\n".join((SKILL / p).read_text(encoding="utf-8") for p in parts)


def case_block(case):
    hints = {f: ENUMS.get(f, "true / false" if isinstance(v, bool) else "short string") for f, v in case["expected"].items()}
    source = case.get("source") or {}
    lines = [f"## {case['case_id']}（{'论文原文片段 ' + source.get('location', '') if case['origin'] == 'paper_excerpt' else '人为构造的示例，G/H/D/QX 只是符号'}）",
             f"片段：{case['text']}"]
    lines += [f"上下文（{c.get('location', '')}）：{c['quote']}" for c in case.get("context", [])]
    lines += [f"问题：{case['question']}", "需要回答的字段：" + json.dumps(hints, ensure_ascii=False)]
    return "\n".join(lines)


def build_prompt(rules, cases):
    head = ("下面是判定规则，之后是若干个独立的判定案例。每个案例只依据它自己的片段和上下文判断，"
            "按规则回答指定字段。只输出一个 JSON 对象，键为案例编号，值为该案例字段的对象，"
            "不要输出任何其他文字或代码块标记。")
    return "\n\n".join([rules, "# 任务说明\n" + head, "# 案例\n" + "\n\n".join(case_block(c) for c in cases)])


def parse_answers(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def same(expected, answer, lenient):
    if isinstance(expected, list):
        if not isinstance(answer, list):
            answer = [answer] if answer not in (None, "") else []
        exp, ans = {str(x).lower() for x in expected}, {str(x).lower() for x in answer}
        return exp <= ans if lenient else exp == ans
    if isinstance(expected, dict):
        return isinstance(answer, dict) and all(answer.get(k) == v for k, v in expected.items())
    if isinstance(expected, bool):
        return answer is expected or str(answer).lower() == str(expected).lower()
    return str(answer).strip().lower() == str(expected).strip().lower()


def score(cases, answers):
    rows = []
    for case in cases:
        got = answers.get(case["case_id"], {})
        for field, expected in case["expected"].items():
            answer = got.get(field)
            rows.append({"case_id": case["case_id"], "field": field, "expected": expected, "answer": answer,
                         "strict": same(expected, answer, False), "lenient": same(expected, answer, True)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="Claude_Opus_5.5")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--conditions", nargs="+", default=["card", "full"])
    parser.add_argument("--repeat", type=int, default=1, help="independent runs per condition, to see run-to-run variation")
    args = parser.parse_args()
    data = json.loads((SKILL / "references/boundary-cases.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    out = RUNS / "card_check" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    (out / "empty_workdir").mkdir(parents=True)
    (out / "card_used.md").write_text((HERE / "card.md").read_text(encoding="utf-8"), encoding="utf-8")
    results = {}
    for condition in args.conditions:
        prompt = build_prompt(rules_text(condition), cases)
        (out / f"prompt_{condition}.txt").write_text(prompt, encoding="utf-8")
        for n in range(1, args.repeat + 1):
            text, usage = call(args.model, args.effort, prompt, out / "empty_workdir")
            (out / f"response_{condition}_{n}.txt").write_text(text, encoding="utf-8")
            rows = score(cases, parse_answers(text))
            results.setdefault(condition, []).append({"usage": usage, "rows": rows})
            strict = sum(r["strict"] for r in rows)
            lenient = sum(r["lenient"] for r in rows)
            full_cases = sum(all(r["strict"] for r in rows if r["case_id"] == c["case_id"]) for c in cases)
            print(f"{condition} run {n}: fields strict {strict}/{len(rows)}, lenient {lenient}/{len(rows)}, "
                  f"cases fully right {full_cases}/{len(cases)}, {usage['seconds']} s, cost {usage.get('cost_usd')}")
    print("\nFields missed in any run (strict), as misses per condition:")
    keys = [(r["case_id"], r["field"], r["expected"]) for r in next(iter(results.values()))[0]["rows"]]
    for i, (case_id, field, expected) in enumerate(keys):
        misses = {c: [run["rows"][i]["answer"] for run in runs if not run["rows"][i]["strict"]] for c, runs in results.items()}
        if any(misses.values()):
            detail = "; ".join(f"{c} {len(m)}/{len(results[c])} {json.dumps(m[:1], ensure_ascii=False)[:90]}" for c, m in misses.items())
            print(f"  {case_id} {field} expected={json.dumps(expected, ensure_ascii=False)}: {detail}")
    (out / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n{out}")


if __name__ == "__main__":
    main()
