"""Run the skill's frozen boundary cases against a model, with either the full rules or the compressed rules card.

Usage:
  python scripts/rule_cases.py --model Claude_Opus_5.5 --rules full
  python scripts/rule_cases.py --model Claude_Opus_5.5 --rules card
  python scripts/rule_cases.py --compare outputs_rule_tests/A.json outputs_rule_tests/B.json

All cases go into one request. The model sees each case's text, context, question and the names of the fields
to answer, never the expected values or rationale. Each answered field is scored against the frozen expectation.
This measures whether a rules text leads to the same rule behaviour; it is not a measure of biomedical accuracy.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oneshot import call_claude, call_codex, extract_json
from blind_runs import LAUNCH

ROOT = Path(__file__).resolve().parents[1]
SKILL = Path.home() / ".codex" / "skills" / "biomed-gene-disease-evidence"
RULE_FILES = ("SKILL.md", "references/decision-rules.md", "references/data-contract.md")
OUT = ROOT / "outputs_rule_tests"


def rules_text(kind):
    if kind == "card":
        return (ROOT / "toolkit" / "rules_card.md").read_text(encoding="utf-8")
    return "\n\n".join(f"===== {Path(f).name} =====\n{(SKILL / f).read_text(encoding='utf-8')}" for f in RULE_FILES)


def build_request(kind, cases):
    blocks = []
    for c in cases:
        context = "\n".join(f"  [{x.get('location', '')}] {x['quote']}" for x in c.get("context", []))
        origin = "论文原文片段" if c["origin"] == "paper_excerpt" else "人为构造的示例（G/H/D/QX 只是符号）"
        blocks.append(f"### {c['case_id']}（{origin}）\n文本：{c['text']}\n" + (f"上下文：\n{context}\n" if context else "")
                      + f"问题：{c['question']}\n需要回答的字段：{', '.join(c['expected'])}")
    return f"""# 任务
下面是一组规则测试案例。请严格依据给出的规则判断每个案例，只依据案例中给出的文本，不用外部知识。

# 规则
{rules_text(kind)}

# 回答格式
只输出一个 JSON 对象，不要其他文字：键是案例编号，值是一个对象，只包含该案例"需要回答的字段"。
- 枚举字段使用规则中的取值（如 status 用 supported / explicit_negative / uncertain / not_found；source_scope 用 背景引用 / 本研究结果 / 两者兼有 / 不确定）。
- 列表字段（如 unresolved_reason、identity_issues、depends_on_unread、support_basis）用 JSON 数组。
- 是否类字段用 true / false；名称类字段用字符串；不适用时用 null。

# 案例
""" + "\n\n".join(blocks)


def normalise(value):
    if isinstance(value, list):
        return sorted(str(v).strip().lower() for v in value)
    if isinstance(value, str):
        return value.strip().lower()
    return value


def score(cases, answers):
    rows = []
    for c in cases:
        got = answers.get(c["case_id"], {}) or {}
        for field, expected in c["expected"].items():
            value = got.get(field, "<missing>")
            exact = normalise(value) == normalise(expected)
            # Lists also count as matching when every expected item is present (extra items are reported separately).
            covered = exact or (isinstance(expected, list) and isinstance(value, list)
                                and set(normalise(expected)) <= set(normalise(value)))
            rows.append({"case_id": c["case_id"], "field": field, "expected": expected, "answer": value,
                         "exact": exact, "covered": covered})
    return rows


def run(args):
    data = json.loads((SKILL / "references" / "boundary-cases.json").read_text(encoding="utf-8"))
    cases = data["cases"]
    request = build_request(args.rules, cases)
    work = OUT / "work"
    work.mkdir(parents=True, exist_ok=True)
    call = call_claude if LAUNCH[args.model]["cli"] == "claude" else call_codex
    response = call(args.model, args.effort, request, None, work)
    answers = extract_json(response["text"])
    rows = score(cases, answers)
    exact = sum(r["exact"] for r in rows)
    covered = sum(r["covered"] for r in rows)
    cases_all_exact = sum(all(r["exact"] for r in rows if r["case_id"] == c["case_id"]) for c in cases)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {"model": args.model, "rules": args.rules, "case_set_version": data["case_set_version"],
              "request_chars": len(request), "seconds": round(response["seconds"], 1), "cost_usd": response.get("cost_usd"),
              "tokens": response.get("tokens"), "fields": len(rows), "fields_exact": exact, "fields_covered": covered,
              "cases": len(cases), "cases_all_exact": cases_all_exact, "rows": rows, "answers": answers}
    path = OUT / f"{args.rules}_{args.model}_{stamp}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{args.rules} / {args.model}: fields exact {exact}/{len(rows)}, covered {covered}/{len(rows)}, "
          f"cases fully exact {cases_all_exact}/{len(cases)}; {report['seconds']} s, cost {report['cost_usd']}, "
          f"request {len(request)} chars -> {path.relative_to(ROOT).as_posix()}")
    for r in rows:
        if not r["exact"]:
            print(f"  {r['case_id']} {r['field']}: expected {r['expected']!r}, got {r['answer']!r}"
                  + (" (covered)" if r["covered"] else ""))


def compare(paths):
    a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in paths)
    rb = {(r["case_id"], r["field"]): r for r in b["rows"]}
    print(f"A = {a['rules']}/{a['model']}: exact {a['fields_exact']}/{a['fields']}   "
          f"B = {b['rules']}/{b['model']}: exact {b['fields_exact']}/{b['fields']}")
    for r in a["rows"]:
        other = rb.get((r["case_id"], r["field"]))
        if other and r["exact"] != other["exact"]:
            print(f"  {r['case_id']} {r['field']}: expected {r['expected']!r}; A={r['answer']!r}; B={other['answer']!r}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", choices=sorted(LAUNCH))
    parser.add_argument("--rules", choices=("full", "card"))
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--compare", nargs=2)
    args = parser.parse_args()
    if args.compare:
        compare(args.compare)
    else:
        run(args)


if __name__ == "__main__":
    main()
