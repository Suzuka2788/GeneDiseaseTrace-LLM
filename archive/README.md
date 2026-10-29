# Archive: development history

Material from the rounds before the final single-request method. It is kept for traceability and is not needed to
run or reproduce the current results.

| Folder | What it holds |
|---|---|
| `manual/`, `outputs_claude_Opus_5.5/` | Hand-curated annotation of the first paper (PMC10014009) under rules 1.1.0, and the earlier version under `rules-pre-1.1.0/` |
| `outputs_GPT_6.1_sol/`, `outputs_evidence_audit/` | First- and second-round model outputs for the same paper and the audit comparing them |
| `outputs_blind/`, `outputs_blind_comparison/` | Blind re-runs in fresh sessions (Claude Opus 5.5, GPT-6.1 Sol, GPT-6 Astra) and their pair-by-pair comparison |
| `outputs_rule_tests/` | Rule-card vs full-rule boundary-case checks from the agent-mode stage |
| `proposals/` | Blind-run prompts and the skill 1.3.0 revision proposal |
| `notes/` | `SKILL_REVISION_PROPOSAL.md` (rules 1.1.0 proposal) and `LLM_WORKFLOW.md` (the early LLM route) |
| `scripts/` | One-off scripts of those rounds: blind-run management, manual-analysis builder, comparisons, agent-mode single-request runner (`oneshot.py`), `validate_contract.py` (same as `python -m toolkit.validate`) |

Paths inside these scripts were updated when they moved here (root = two folders up; outputs under `archive/`).
Two are known not to run as-is, independent of the move: `review_first_paper.py` and `round2_PMC10014009.py` need
Pillow, and `audit_model_results_PMC10014009.py` expects a `result.json` that was later moved into `rules-pre-1.1.0/`.
