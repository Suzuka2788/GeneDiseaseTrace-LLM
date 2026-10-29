"""Manage blind run folders: set them up, see their state, hand out prompts and collect results.

Usage:
  python archive/scripts/blind_runs.py status                     # table of every run folder and its state
  python archive/scripts/blind_runs.py next                       # first folder not started: prints path, copies prompt to clipboard
  python archive/scripts/blind_runs.py prompt PMC10487392_GPT-6_Astra   # copy that folder's prompt to the clipboard
  python archive/scripts/blind_runs.py smoke --model GPT-6_Astra    # tiny test run in a throwaway copy (login, permissions, Python)
  python archive/scripts/blind_runs.py launch --model GPT-6_Astra --papers PMC10487392 PMC9111839 PMC8626062 PMC10014009
  python archive/scripts/blind_runs.py collect                    # copy finished runs into archive/outputs_blind/ and re-validate them
  python archive/scripts/blind_runs.py setup --papers PMC1 PMC2 --models GPT-6_Astra Claude_Opus_5.5

Each folder is C:\\Users\\tongz\\blind_runs\\<paper>_<model>\\ and contains only input/, biomed/, skill/
(rules without boundary cases), toolkit/ and PROMPT.md. Only `launch` starts a model (non-interactive CLI).
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from toolkit.validate import validate

BLIND_ROOT = Path.home() / "blind_runs"
SKILL_SOURCE = Path.home() / ".codex" / "skills" / "biomed-gene-disease-evidence"
COLLECTED = ROOT / "archive" / "outputs_blind"
LOG_ROOT = BLIND_ROOT / "_launch_logs"
PYTHON = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe"
HIDDEN_FROM_RUNS = ("references/boundary-cases.json", "references/boundary-cases.md",
                    "references/model-comparison.md", "CHANGELOG.md", "scripts")
RULE_FILES = ("SKILL.md", "references/decision-rules.md", "references/data-contract.md")
MODELS = ("GPT-6_Astra", "GPT-6.1_sol", "Claude_Opus_5.5")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_folders():
    return sorted(f for f in BLIND_ROOT.iterdir() if f.is_dir() and not f.name.startswith("_"))


def split_name(folder):
    paper, model = folder.name.split("_", 1)
    return paper, model


def paper_info(paper):
    article = json.loads((ROOT / "cache" / "articles" / f"{paper}.json").read_text(encoding="utf-8"))
    chars = sum(len(b["text"]) for b in article["blocks"])
    multi = any("multi-study" in w for w in article["warnings"])
    return article["article_type"], chars, len(article["blocks"]), multi


def article_language(xml_path):
    root = ET.parse(xml_path).getroot()
    return (root.get("{http://www.w3.org/XML/1998/namespace}lang") or "").lower()[:2]


def prompt_text(folder):
    paper, _ = split_name(folder)
    skill = folder / "skill" / "biomed-gene-disease-evidence"
    version = re.search(r'^\s*version:\s*"([^"]+)"', (skill / "SKILL.md").read_text(encoding="utf-8"), re.M).group(1)
    hashes = {Path(f).name: sha256(skill / f) for f in RULE_FILES}
    article_type, chars, blocks, multi = paper_info(paper)
    extra = ""
    if article_type == "abstract" or multi:
        extra += ("- 这个文件可能包含多个独立研究（如会议摘要合集）。先按 skill 的 R9 划定研究单元，写进 judgments.json 的 units；"
                  "配对只在单元内生成。\n- 全文很长，可以分单元、分多轮完成，在 work/progress.md 记录已完成和未完成的单元。不能截断、抽样或跳过；"
                  "没有全部完成时把 completion 写成 partial，并在 unresolved 里列出未完成的单元。\n")
    if article_language(folder / "input" / f"{paper}.xml") not in ("en", ""):
        extra += "- 这篇论文不是英文。引文必须保留原文；需要翻译时写在 evidence 的 translation 字段，不能用译文代替原文，也不能因翻译新增名称。\n"
    return f"""你将独立完成一项生物医学文献证据抽取任务。这是一次盲测运行：结果会与其他模型的结果比较，独立性和可追溯性比速度重要。

## 第 0 步：确认工作目录
当前工作目录应当只有 input/、biomed/、skill/、toolkit/ 和 PROMPT.md（可以有你本次运行新建的文件）。如果有别人的输出，或者 input/ 里的论文不是 {paper}.xml，停止并报告。

## 输入与规则
- 论文：input/{paper}.xml（{article_type}，约 {chars} 字符，{blocks} 个解析块）。开始前核对 SHA-256，应为
  {sha256(folder / "input" / f"{paper}.xml")}
  不一致就停止并报告。
- 规则：skill/biomed-gene-disease-evidence/（版本 {version}）。先读 SKILL.md，再按其要求读 references/decision-rules.md 和 references/data-contract.md。核对 SHA-256：
  SKILL.md           {hashes['SKILL.md']}
  decision-rules.md  {hashes['decision-rules.md']}
  data-contract.md   {hashes['data-contract.md']}
  不一致就停止并报告。
- SKILL.md 链接的 boundary-cases.md、model-comparison.md 和 CHANGELOG.md 是有意不提供的，本任务不需要它们，不要去其他位置寻找。
- 工具：先读 toolkit/README.md。必须用工具包完成解析、名称定位、文件生成和校验：你只写 judgments.json，其余交给 toolkit。不要另写解析、输出或校验脚本。
- Python：优先使用 PATH 中的 python；没有时使用 {PYTHON}。两者都不可用时停止并报告，不要自行下载或安装。
{extra}
## 独立性要求
- 除了调用上面的 Python 解释器，只读取当前工作目录内的文件。不访问网络，不查询 PubTator 或任何数据库。
- 不搜索、不打开、不引用这篇论文的任何既往结果、比较报告、边界案例、修订建议或其他模型输出，即使你在磁盘其他位置发现它们。
- 开始前如实声明：你此前是否在任何会话或记忆中接触过这篇论文的分析结果，或这个 skill 的边界案例。写进 judgments.json 的 exposure；接触过就不能称为盲测。
- 不用你已有的医学知识补全关系，只依据本文可读内容。

## 任务
1. 运行 `python -m toolkit.blocks`，通读 work/blocks.txt 的全部内容（正文、表格、图注）。
2. 按 skill 流程完成判断，写成 judgments.json：A 输入范围（input_scope）、B 实体（含辅助实体、排除候选、基因集合）、C 你判断过的配对（未列出的配对由工具记为 not_found）、study_findings、data_conflicts、unread_attachments、unresolved、rule_feedback。字段见 toolkit/README.md 与 data-contract。
3. 用 `python -m toolkit.find` 确认每个名称写法和每段引文都逐字存在。
4. 反复运行 `python -m toolkit.build judgments.json --check`，直到没有问题。
5. 最后运行一次 `python -m toolkit.build judgments.json`，生成 outputs/{paper}/rules-{version}/<run_id>/，并确认校验 PASSED。

- 遇到规则冲突或规则没覆盖的情况：按有依据的最保守方式处理，写进 rule_feedback。不要修改 skill 或 toolkit。
- 不预设边数或状态分布。只做这一篇，不提交 git。

## 最后回复
输出目录；实体数和配对数；各状态数量；全部 supported 边及其证据位置；全部 uncertain 配对及原因；rule_feedback 摘要。不要声称准确率、召回率，也不要声称经过了独立验证。
"""


def state(folder):
    runs = sorted(folder.glob("outputs/*/rules-*/*/validation.json"))
    if runs:
        report = json.loads(runs[-1].read_text(encoding="utf-8"))
        manifest = json.loads((runs[-1].parent / "manifest.json").read_text(encoding="utf-8"))
        counts = manifest.get("status_counts", {})
        label = "done" if report.get("passed") else "done, validation FAILED"
        if manifest.get("completion") == "partial":
            label += " (partial)"
        return label, runs[-1].parent, counts
    if (folder / "judgments.json").exists() or (folder / "work").exists():
        return "in progress", None, {}
    return "not started", None, {}


def create_run_folder(folder, paper):
    """input/, biomed/ parser, skill/ without boundary cases, toolkit/ — the same contents for every run mode."""
    (folder / "input").mkdir(parents=True)
    shutil.copy2(ROOT / ".Input" / "100papers" / f"{paper}.xml", folder / "input")
    (folder / "biomed").mkdir()
    for name in ("__init__.py", "io.py", "jats.py"):
        shutil.copy2(ROOT / "biomed" / name, folder / "biomed")
    shutil.copytree(SKILL_SOURCE, folder / "skill" / SKILL_SOURCE.name, ignore=shutil.ignore_patterns("__pycache__"))
    for hidden in HIDDEN_FROM_RUNS:
        target = folder / "skill" / SKILL_SOURCE.name / hidden
        shutil.rmtree(target) if target.is_dir() else target.unlink(missing_ok=True)
    shutil.copytree(ROOT / "toolkit", folder / "toolkit", ignore=shutil.ignore_patterns("__pycache__"))


def cmd_setup(args):
    for paper in args.papers:
        for model in args.models:
            folder = BLIND_ROOT / f"{paper}_{model}"
            if folder.exists():
                print(f"exists, left alone: {folder}")
                continue
            create_run_folder(folder, paper)
            (folder / "PROMPT.md").write_text(prompt_text(folder), encoding="utf-8")
            print(f"created {folder}")


def cmd_refresh_prompts(_):
    for folder in run_folders():
        if state(folder)[0] == "not started":
            (folder / "PROMPT.md").write_text(prompt_text(folder), encoding="utf-8")
            print(f"prompt written: {folder.name}")


def cmd_status(_):
    rows = []
    for folder in run_folders():
        paper, model = split_name(folder)
        label, run, counts = state(folder)
        summary = " ".join(f"{k[:3]}={v}" for k, v in counts.items()) if counts else ""
        rows.append((paper, model, label, summary))
    width = max(len(r[2]) for r in rows) if rows else 10
    for paper, model, label, summary in rows:
        print(f"{paper:12} {model:16} {label:{width}} {summary}")
    done = sum(r[2].startswith("done") for r in rows)
    print(f"\n{done}/{len(rows)} done")


def copy_prompt(folder):
    text = (folder / "PROMPT.md").read_text(encoding="utf-8")
    try:
        subprocess.run(["clip"], input=text.encode("utf-16-le"), check=True)
        copied = "copied to clipboard"
    except (OSError, subprocess.CalledProcessError):
        copied = "clipboard unavailable; open PROMPT.md and copy it"
    print(f"Open a NEW session in:\n  {folder}\nPrompt {copied} ({folder / 'PROMPT.md'}).")


def run_order(folder):
    """Short single-study papers first, multi-study collections last."""
    paper, model = split_name(folder)
    article_type, chars, _, multi = paper_info(paper)
    return (article_type == "abstract" or multi, chars, paper, model)


def cmd_next(_):
    for folder in sorted(run_folders(), key=run_order):
        if state(folder)[0] == "not started":
            copy_prompt(folder)
            return
    print("Every folder has been started.")


def cmd_prompt(args):
    copy_prompt(BLIND_ROOT / args.folder)


def cmd_collect(_):
    for folder in run_folders():
        paper, model = split_name(folder)
        label, run, _ = state(folder)
        if run is None:
            continue
        target = COLLECTED / paper / model / run.name
        if not target.exists():
            shutil.copytree(run, target)
        report = validate(target, folder / "input" / f"{paper}.xml")
        (target / "validation_shared.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{paper} {model}: {'PASSED' if report['passed'] else 'FAILED'} -> {target.relative_to(ROOT).as_posix()}")


LAUNCH = {
    "GPT-6_Astra": {"cli": "codex", "model": "gpt-6-astra"},
    "GPT-6.1_sol": {"cli": "codex", "model": "gpt-6.1-sol"},
    "Claude_Opus_5.5": {"cli": "claude", "model": "claude-opus-5-5"},
}
CLI_GLOBS = {
    "codex": (Path.home() / "AppData/Local/OpenAI/Codex/bin", "*/codex.exe"),
    "claude": (Path.home() / "AppData/Local/Claude-Data", "*/claude-code/*/*/claude.exe"),
}


def find_cli(name):
    base, pattern = CLI_GLOBS[name]
    found = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not found:
        raise SystemExit(f"{name} executable not found under {base}")
    return found[-1]


def launch_command(model, effort, last_message):
    spec = LAUNCH[model]
    exe = find_cli(spec["cli"])
    if spec["cli"] == "codex":
        # User config is ignored so global instructions and memories cannot leak in; the Windows sandbox setting
        # it carried is restored explicitly. workspace-write keeps network off and writes inside the folder.
        return [str(exe), "exec", "-m", spec["model"], "-c", f'model_reasoning_effort="{effort}"',
                "-c", 'windows.sandbox="elevated"', "-s", "workspace-write", "--ignore-user-config",
                "--skip-git-repo-check", "--ephemeral", "--color", "never", "--json", "-o", str(last_message), "-"]
    # New folder = empty project memory; no MCP servers; only file tools and the shell.
    return [str(exe), "-p", "--model", spec["model"], "--effort", effort, "--permission-mode", "dontAsk",
            "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", "Bash", "PowerShell",
            "--strict-mcp-config", "--no-session-persistence", "--output-format", "json"]


def run_one(folder, model, effort, timeout_minutes, prompt=None):
    # Logs live outside the run folder so the model never sees them as someone else's output.
    logs = LOG_ROOT / folder.name
    logs.mkdir(parents=True, exist_ok=True)
    command = launch_command(model, effort, logs / "last_message.md")
    started = datetime.now(timezone.utc)
    record = {"model": model, "cli_model": LAUNCH[model]["model"], "effort": effort, "command": command,
              "started": started.isoformat()}
    try:
        with (logs / "output.txt").open("wb") as out:
            result = subprocess.run(command, cwd=folder, input=prompt or (folder / "PROMPT.md").read_bytes(), stdout=out,
                                    stderr=subprocess.STDOUT, timeout=timeout_minutes * 60)
        record["exit_code"] = result.returncode
    except subprocess.TimeoutExpired:
        record["exit_code"] = "timeout"
    finished = datetime.now(timezone.utc)
    record.update(finished=finished.isoformat(), minutes=round((finished - started).total_seconds() / 60, 1),
                  final_state=state(folder)[0])
    (logs / "launch.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return folder, record


SMOKE_PROMPT = ("这是一次环境测试。在当前目录运行 python -m toolkit.blocks（PATH 中没有 python 时用 {python}），"
                "然后只回复 work/blocks.txt 的第一行，以及你实际用的 python 路径。不要做其他事。")


def cmd_smoke(args):
    """Run a tiny task in a throwaway copy to check login, permissions and Python before a real launch."""
    source = run_folders()[0]
    target = Path.home() / f"blind_smoke_{args.model}"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("outputs", "work", "judgments.json"))
    _, record = run_one(target, args.model, "low", 10, SMOKE_PROMPT.format(python=PYTHON).encode("utf-8"))
    blocks = target / "work" / "blocks.txt"
    ok = blocks.exists()
    print(f"{args.model}: exit={record['exit_code']}, {record['minutes']} min, toolkit ran: {'yes' if ok else 'NO'}")
    print(f"log: {LOG_ROOT / target.name / 'output.txt'}")
    if ok:
        shutil.rmtree(target, ignore_errors=True)
    else:
        print(f"Left {target} in place for inspection.")


def cmd_launch(args):
    folders = [BLIND_ROOT / f"{paper}_{args.model}" for paper in args.papers] if args.papers else \
        sorted((f for f in run_folders() if split_name(f)[1] == args.model), key=run_order)
    todo = [f for f in folders if f.is_dir() and state(f)[0] == "not started"]
    skipped = [f.name for f in folders if f not in todo]
    if skipped:
        print("Skipping (missing or already started): " + ", ".join(skipped))
    if not todo:
        print("Nothing to launch.")
        return
    print(f"{args.model}: {len(todo)} run(s), {args.parallel} at a time, effort={args.effort}, timeout={args.timeout} min")
    for f in todo:
        print(f"  {f}")
    print("  command: " + " ".join(launch_command(args.model, args.effort, LOG_ROOT / "<folder>" / "last_message.md")) + "  < PROMPT.md")
    if args.dry_run:
        return
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        for future in as_completed(pool.submit(run_one, f, args.model, args.effort, args.timeout) for f in todo):
            folder, record = future.result()
            print(f"{folder.name}: exit={record['exit_code']} {record['minutes']} min -> {record['final_state']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup")
    setup.add_argument("--papers", nargs="+", required=True)
    setup.add_argument("--models", nargs="+", default=list(MODELS))
    sub.add_parser("refresh-prompts")
    sub.add_parser("status")
    sub.add_parser("next")
    prompt = sub.add_parser("prompt")
    prompt.add_argument("folder")
    sub.add_parser("collect")
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--model", required=True, choices=sorted(LAUNCH))
    launch = sub.add_parser("launch")
    launch.add_argument("--model", required=True, choices=sorted(LAUNCH))
    launch.add_argument("--papers", nargs="+", help="default: every not-started folder of this model")
    launch.add_argument("--parallel", type=int, default=1)
    launch.add_argument("--effort", default="medium", help="reasoning effort passed to the CLI (use the same for every model)")
    launch.add_argument("--timeout", type=int, default=120, help="minutes per run")
    launch.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    {"setup": cmd_setup, "refresh-prompts": cmd_refresh_prompts, "status": cmd_status, "next": cmd_next,
     "prompt": cmd_prompt, "collect": cmd_collect, "launch": cmd_launch, "smoke": cmd_smoke}[args.command](args)


if __name__ == "__main__":
    main()
