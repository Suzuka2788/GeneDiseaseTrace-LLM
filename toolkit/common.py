import hashlib
import re
from pathlib import Path

from biomed.jats import parse_article

SKILL_DIR = Path("skill/biomed-gene-disease-evidence")
RULE_FILES = ("SKILL.md", "references/decision-rules.md", "references/data-contract.md")

ENTITY_TYPES = {"gene", "disease", "symptom", "phenotype", "clinical_event", "ambiguous"}
AUXILIARY_TYPES = {"symptom", "phenotype"}
IDENTITY_STATUS = {"resolved", "provisional", "unresolved"}
IDENTITY_ISSUES = {"undefined_abbreviation", "suspected_typo", "species_unresolved", "ambiguous_mapping", "other"}
STATUSES = ("supported", "explicit_negative", "uncertain", "not_found")
RELATION_TYPES = {"association", "correlation", "causal", "none"}
DISPLAY_PRIORITY = {"causal": 3, "correlation": 2, "association": 1}
SOURCE_SCOPES = {"背景引用", "本研究结果", "两者兼有", "不确定"}
ASSERTION_KINDS = {"reported_result", "background_relation_statement", "hypothesis", "aim", "interpretation",
                   "negative_result", "descriptive_cooccurrence"}
RELATION_ASSERTED = {"affirmed", "negated", "hypothetical", "questioned", "not_asserted", "presupposed"}
SUPPORT_BASIS = {"explicit_background_report", "reported_result", "explicit_disease_attribution", "co_segregation",
                 "comparative_result", "model_intervention", "descriptive_only", "hypothesis_only", "unclear", "none"}
UNRESOLVED_REASONS = {"identity", "coreference", "hedged_claim", "support_basis_unresolved", "presupposed_only",
                      "scope", "conflict", "missing_material", "other"}
EVIDENCE_SPECIES = {"human", "non-human", "mixed", "unknown"}
FINDING_TYPES = {"association", "correlation", "group_comparison", "descriptive", "mechanism", "hypothesis", "other"}
SIGNIFICANCE = {"significant", "not_significant", "mixed", "unknown", "not_applicable"}
DIRECTION = {"positive", "negative", "mixed", "null", "unknown", "not_applicable"}
STAT_AVAILABILITY = {"available", "partial", "unread", "not_reported", "not_applicable"}
IMPACT = {"noncritical", "status_critical", "undetermined"}
RESOLUTION = {"resolved", "unresolved"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def find_input():
    papers = sorted(Path("input").glob("*.xml"))
    if len(papers) != 1:
        raise SystemExit(f"Expected exactly one XML in input/, found {len(papers)}")
    return papers[0]


def load_article():
    path = find_input()
    article = parse_article(path)
    return path, article, {b["block_id"]: b for b in article["blocks"]}


def rule_info():
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    version = re.search(r'^\s*version:\s*"([^"]+)"', skill, re.M)
    return (version.group(1) if version else "unknown"), {Path(f).name: sha256(SKILL_DIR / f) for f in RULE_FILES}


def block_range(spec, block_ids):
    """Expand 'all', 'b0001-b0050' or a list of such strings into an ordered list of block IDs."""
    if spec in (None, "all"):
        return list(block_ids)
    specs = [spec] if isinstance(spec, str) else spec
    chosen = []
    for item in specs:
        if "-" in item:
            start, end = item.split("-", 1)
            if start not in block_ids or end not in block_ids:
                raise ValueError(f"Unknown block range {item}")
            chosen += block_ids[block_ids.index(start):block_ids.index(end) + 1]
        elif item in block_ids:
            chosen.append(item)
        else:
            raise ValueError(f"Unknown block {item}")
    return chosen
