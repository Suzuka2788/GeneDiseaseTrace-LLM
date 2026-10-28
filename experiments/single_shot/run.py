"""Run one paper through one model in a single request (no tools), then expand and validate.

Usage: python experiments/single_shot/run.py PMC10487392 --model Claude_Opus_5.5 [--effort medium] [--no-repair]

The model runs in an empty folder under runs/ with every tool disabled, so it only sees the prompt.
If the response breaks the format, one repair request is sent with the problem list (unless --no-repair).
Time, tokens and list-price cost (when the CLI reports it) go to run.json.
"""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from common import RUNS
from expand import expand, main as expand_and_validate
from pack import fixed_part, paper_part

MODELS = {
    "Claude_Opus_5.5": ("claude", "claude-opus-5-5"),
    "GPT-6_Astra": ("codex", "gpt-6-astra"),
    "GPT-6.1_sol": ("codex", "gpt-6.1-sol"),
}
SYSTEM = ("You extract gene-disease evidence from biomedical papers. "
          "Follow the decision card and output format exactly; output only the specified lines.")


def find_cli(name):
    home = Path.home()
    base, pattern = {"codex": (home / "AppData/Local/OpenAI/Codex/bin", "*/codex.exe"),
                     "claude": (home / "AppData/Local/Claude-Data", "*/claude-code/*/*/claude.exe")}[name]
    found = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not found:
        raise SystemExit(f"{name} executable not found")
    return found[-1]


def call(model, effort, prompt, workdir, fixed=""):
    """fixed: text identical for every paper. Claude gets it in the system prompt, which is cached as its own
    prefix, so later papers in a batch read it from cache; Codex gets it at the start of the message.
    """
    cli, model_id = MODELS[model]
    exe = find_cli(cli)
    if cli == "claude" and len(fixed) > 30000:
        # Windows caps a command line at 32,767 characters; a long fixed part goes into the message instead.
        prompt, fixed = fixed + "\n\n" + prompt, ""
    if cli == "claude":
        system = SYSTEM + ("\n\n" + fixed if fixed else "")
        command = [str(exe), "-p", "--model", model_id, "--effort", effort, "--tools", "", "--system-prompt", system,
                   "--strict-mcp-config", "--no-session-persistence", "--output-format", "json"]
    else:
        command = [str(exe), "exec", "-m", model_id, "-c", f'model_reasoning_effort="{effort}"', "-s", "read-only",
                   "--ignore-user-config", "--skip-git-repo-check", "--ephemeral", "--color", "never", "--json",
                   "-o", str(workdir / "last_message.txt"), "-"]
        prompt = (fixed + "\n\n" + prompt) if fixed else prompt
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, cwd=workdir, input=prompt.encode("utf-8"), capture_output=True)
    seconds = (datetime.now(timezone.utc) - started).total_seconds()
    raw = result.stdout.decode("utf-8", errors="replace")
    if cli == "claude":
        data = json.loads(raw) if raw.strip().startswith("{") else {"result": raw, "is_error": True}
        usage = {"usage": data.get("usage"), "cost_usd": data.get("total_cost_usd"), "turns": data.get("num_turns"),
                 "model_usage": data.get("modelUsage")}
        text = data.get("result", "")
    else:
        events = [json.loads(l) for l in raw.splitlines() if l.strip().startswith("{")]
        usage = {"usage_events": [e for e in events if "usage" in json.dumps(e)][-3:], "cost_usd": None}
        last = workdir / "last_message.txt"
        text = last.read_text(encoding="utf-8") if last.exists() else ""
    return text, {"seconds": round(seconds, 1), "exit_code": result.returncode, **usage,
                  "stderr": result.stderr.decode("utf-8", errors="replace")[-2000:]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paper")
    parser.add_argument("--model", required=True, choices=sorted(MODELS))
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--no-repair", action="store_true")
    args = parser.parse_args()

    fixed = fixed_part()
    prompt, _ = paper_part(args.paper)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = RUNS / args.paper / f"{args.model}_{stamp}"
    workdir = run_dir / "empty_workdir"
    workdir.mkdir(parents=True)
    meta = {"paper_id": args.paper, "model": args.model, "cli_model": MODELS[args.model][1], "effort": args.effort,
            "fixed_characters": len(fixed), "paper_characters": len(prompt), "calls": []}

    text, usage = call(args.model, args.effort, prompt, workdir, fixed)
    meta["calls"].append(usage)
    (run_dir / "response.txt").write_text(text, encoding="utf-8")
    (run_dir / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    problems = expand(run_dir)
    if problems and not args.no_repair:
        repair = (prompt + "\n\n# Your previous output\n" + text + "\n\n# Problems found by the checker\n" +
                  "\n".join(problems) + "\n\nFix these problems and output the complete result again "
                  "(all lines, not only the changed ones).")
        text, usage = call(args.model, args.effort, repair, workdir, fixed)
        meta["calls"].append(usage)
        (run_dir / "response_first.txt").write_text((run_dir / "response.txt").read_text(encoding="utf-8"), encoding="utf-8")
        (run_dir / "response.txt").write_text(text, encoding="utf-8")
    meta["total_seconds"] = round(sum(c["seconds"] for c in meta["calls"]), 1)
    costs = [c.get("cost_usd") for c in meta["calls"]]
    meta["total_cost_usd"] = round(sum(costs), 4) if all(c is not None for c in costs) else None
    (run_dir / "run.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{run_dir}: {len(meta['calls'])} call(s), {meta['total_seconds']} s, cost {meta['total_cost_usd']}")
    expand_and_validate(run_dir)


if __name__ == "__main__":
    main()
