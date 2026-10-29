"""Run papers in single-response mode: one tool-free model call per paper, then the toolkit does the rest.

Usage:
  python archive/scripts/oneshot.py --model Claude_Opus_5.5 --papers PMC10487392
  python archive/scripts/oneshot.py --model GPT-6_Astra --papers PMC10487392 PMC9111839 --parallel 2

Per paper: toolkit.pack builds one request (rules + output format + parsed paper); the model answers with one
JSON object and has no tools; toolkit.expand + toolkit.build --check verify it; problems are sent back for up to
--max-repairs corrections; then toolkit.build writes the outputs. Folders: C:\\Users\\tongz\\oneshot_runs\\<paper>_<model>\\.
Time, tokens and cost of every call are logged in work/oneshot_log.json.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blind_runs import LAUNCH, create_run_folder, find_cli

ONESHOT_ROOT = Path.home() / "oneshot_runs"
SYSTEM_PROMPT = "你是严谨的生物医学文献证据抽取助手。严格按用户消息中的规则和输出格式工作，只输出一个合法的 JSON 对象，不输出任何其他文字。"


def toolkit(folder, *args):
    result = subprocess.run([sys.executable, "-B", "-m", *args], cwd=folder, capture_output=True, text=True, encoding="utf-8")
    return result.returncode, (result.stdout + result.stderr).strip()


def call_claude(model, effort, message, session, logs):
    command = [str(find_cli("claude")), "-p", "--model", LAUNCH[model]["model"], "--effort", effort, "--tools", "",
               "--system-prompt", SYSTEM_PROMPT, "--strict-mcp-config", "--output-format", "json"]
    if session:
        command += ["--resume", session]
    started = datetime.now(timezone.utc)
    # The CLI's default output cap can be smaller than a long paper's JSON; a cut-off response is not valid JSON.
    env = {**os.environ, "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "64000"}
    result = subprocess.run(command, input=message.encode("utf-8"), capture_output=True, cwd=logs, timeout=60 * 60, env=env)
    seconds = (datetime.now(timezone.utc) - started).total_seconds()
    raw = result.stdout.decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {"text": "", "error": raw[-2000:] + result.stderr.decode("utf-8", errors="replace")[-2000:], "seconds": seconds}
    usage = data.get("usage", {})
    return {"text": data.get("result", ""), "session": data.get("session_id"), "seconds": seconds,
            "cost_usd": data.get("total_cost_usd"), "error": data.get("result") if data.get("is_error") else None,
            "tokens": {k: usage.get(k, 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")}}


def call_codex(model, effort, message, _session, logs):
    last = logs / f"codex_last_{datetime.now(timezone.utc).strftime('%H%M%S%f')}.txt"
    command = [str(find_cli("codex")), "exec", "-m", LAUNCH[model]["model"], "-c", f'model_reasoning_effort="{effort}"',
               "-c", 'windows.sandbox="elevated"', "-s", "read-only", "--ignore-user-config", "--skip-git-repo-check",
               "--ephemeral", "--color", "never", "--json", "-o", str(last), "-"]
    started = datetime.now(timezone.utc)
    result = subprocess.run(command, input=message.encode("utf-8"), capture_output=True, cwd=logs, timeout=60 * 60)
    seconds = (datetime.now(timezone.utc) - started).total_seconds()
    tokens = {}
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        usage = event.get("usage") or (event.get("msg") or {}).get("info", {}).get("total_token_usage") if isinstance(event, dict) else None
        if isinstance(usage, dict):
            tokens = usage
    text = last.read_text(encoding="utf-8") if last.exists() else ""
    return {"text": text, "session": None, "seconds": seconds, "cost_usd": None, "tokens": tokens,
            "error": None if text else result.stderr.decode("utf-8", errors="replace")[-2000:]}


def extract_json(text):
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the response")
    return json.loads(text[start:end + 1])


def run_paper(paper, model, effort, max_repairs, rules="full"):
    folder = ONESHOT_ROOT / (f"{paper}_{model}" + ("_card" if rules == "card" else ""))
    if list(folder.glob("outputs/*/rules-*/*/validation.json")):
        return paper, {"skipped": "already has outputs"}
    if not folder.exists():
        create_run_folder(folder, paper)
    work = folder / "work"
    work.mkdir(exist_ok=True)
    code, message = toolkit(folder, "toolkit.pack", "--rules", rules)
    if code:
        return paper, {"error": message}
    request = (work / "request.md").read_text(encoding="utf-8")
    call = call_claude if LAUNCH[model]["cli"] == "claude" else call_codex
    log = {"paper": paper, "model": model, "cli_model": LAUNCH[model]["model"], "effort": effort, "rules": rules,
           "request_chars": len(request), "started": datetime.now(timezone.utc).isoformat(), "calls": []}
    session, previous, message = None, "", request
    passed = False
    for attempt in range(max_repairs + 1):
        response = call(model, effort, message, session, work)
        session = response.get("session") or session
        log["calls"].append({k: v for k, v in response.items() if k != "text"})
        (work / f"response_{attempt}.txt").write_text(response["text"], encoding="utf-8")
        if response.get("error") and not response["text"]:
            log["error"] = response["error"]
            break
        try:
            compact = extract_json(response["text"])
            (work / "compact.json").write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
            code, report = toolkit(folder, "toolkit.expand", "work/compact.json", "judgments.json", "--model", LAUNCH[model]["model"])
            if code == 0:
                code, report = toolkit(folder, "toolkit.build", "judgments.json", "--check")
        except ValueError as error:  # includes JSONDecodeError
            code, report = 1, f"输出不是合法 JSON：{error}"
        log["calls"][-1]["check"] = report[-3000:]
        if code == 0:
            passed = True
            break
        previous = response["text"]
        problems = f"程序检查发现以下问题。请输出修正后的完整 JSON（同样格式、包含全部内容，不要其他文字）：\n{report}"
        # Claude keeps the conversation (cheap cached context); Codex runs are ephemeral, so resend everything.
        message = problems if session else f"{request}\n\n# 你上一次的输出\n{previous}\n\n# {problems}"
    if passed:
        code, report = toolkit(folder, "toolkit.build", "judgments.json")
        log["build"] = report[-2000:]
        passed = code == 0
    log.update(finished=datetime.now(timezone.utc).isoformat(), passed=passed, repairs=len(log["calls"]) - 1,
               seconds=round(sum(c.get("seconds", 0) for c in log["calls"]), 1),
               cost_usd=round(sum(c.get("cost_usd") or 0 for c in log["calls"]), 4) if LAUNCH[model]["cli"] == "claude" else None)
    (work / "oneshot_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return paper, log


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", required=True, choices=sorted(LAUNCH))
    parser.add_argument("--papers", nargs="+", required=True)
    parser.add_argument("--parallel", type=int, default=1)
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--max-repairs", type=int, default=2)
    parser.add_argument("--rules", choices=("full", "card"), default="full")
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        futures = [pool.submit(run_paper, p, args.model, args.effort, args.max_repairs, args.rules) for p in args.papers]
        for future in as_completed(futures):
            paper, log = future.result()
            if "skipped" in log or "error" in log and "calls" not in log:
                print(f"{paper}: {log}")
                continue
            print(f"{paper}: {'PASSED' if log['passed'] else 'FAILED'}  calls={len(log['calls'])}  "
                  f"{log['seconds'] / 60:.1f} min  cost={log['cost_usd']}  -> {ONESHOT_ROOT / (paper + '_' + args.model + ('_card' if args.rules == 'card' else ''))}")


if __name__ == "__main__":
    main()
