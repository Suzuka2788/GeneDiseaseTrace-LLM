"""Check regression-case structure and optional source quotes; never run a model."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import xml.etree.ElementTree as ET

PACKAGE = Path(__file__).resolve().parents[1]


def normalize(text):
    text = unicodedata.normalize('NFKC', text)
    text = text.translate(str.maketrans({'‐': '-', '‑': '-', '–': '-', '−': '-', '’': "'"}))
    return re.sub(r'\s+', ' ', text).strip()


def load_source(path):
    raw = Path(path).read_bytes()
    root = ET.fromstring(raw)
    return dict(sha256=hashlib.sha256(raw).hexdigest(), text=normalize(''.join(root.itertext())))


def prompt_records(data):
    return [{key: value for key, value in case.items() if key not in ['expected', 'rationale']}
            for case in data['cases']]


def validate_cases(data, rule_ids, sources):
    errors = []
    ids = set()
    checked = unchecked = 0
    expected_enums = {
        'status': {'supported', 'explicit_negative', 'uncertain', 'not_found'},
        'relation_type': {'causal', 'correlation', 'association', 'none'},
        'tested_relation_type': {'causal', 'correlation', 'association'},
        'source_scope': {'背景引用', '本研究结果', '两者兼有', '不确定'},
        'identity_status': {'resolved', 'provisional', 'unresolved'},
        'reported_significance': {'significant', 'not_significant', 'mixed', 'unknown', 'not_applicable'},
        'effect_direction': {'positive', 'negative', 'mixed', 'null', 'unknown', 'not_applicable'},
        'statistics_availability': {'available', 'partial', 'unread', 'not_reported', 'not_applicable'},
        'impact': {'noncritical', 'status_critical', 'undetermined'},
        'relation_asserted': {'affirmed', 'negated', 'hypothetical', 'questioned', 'not_asserted', 'presupposed'},
        'entity_type': {'gene', 'disease', 'symptom', 'phenotype', 'clinical_event', 'ambiguous'},
        'finding_type': {'association', 'correlation', 'group_comparison', 'descriptive', 'mechanism', 'hypothesis', 'other'},
    }
    expected_list_enums = {
        'unresolved_reason': {'identity', 'coreference', 'hedged_claim', 'support_basis_unresolved',
                              'presupposed_only', 'scope', 'conflict', 'missing_material', 'other'},
        'identity_issues': {'undefined_abbreviation', 'suspected_typo', 'species_unresolved', 'ambiguous_mapping', 'other'},
        'support_basis': {'explicit_background_report', 'reported_result', 'explicit_disease_attribution',
                          'co_segregation', 'comparative_result', 'model_intervention', 'descriptive_only',
                          'hypothesis_only', 'unclear', 'none'},
    }
    for c in data['cases']:
        cid = c['case_id']
        if cid in ids:
            errors.append(f'{cid}: duplicate ID')
        ids.add(cid)
        if not c['text'] or not c['question'] or not c['rationale'] or not c['expected']:
            errors.append(f'{cid}: incomplete case')
        if not c['rule_ids'] or set(c['rule_ids']) - rule_ids:
            errors.append(f'{cid}: unknown or missing rule reference')
        for field, allowed in expected_enums.items():
            if field in c['expected'] and (not isinstance(c['expected'][field], str)
                                            or c['expected'][field] not in allowed):
                errors.append(f'{cid}: invalid {field}')
        for field, allowed in expected_list_enums.items():
            if field in c['expected']:
                values = c['expected'][field]
                if not isinstance(values, list) or any(not isinstance(v, str) or v not in allowed for v in values):
                    errors.append(f'{cid}: invalid {field}')
        if 'conflict_impact' in c['expected']:
            errors.append(f'{cid}: obsolete conflict_impact; use impact')
        if c['origin'] == 'synthetic':
            if c['source'] is not None:
                errors.append(f'{cid}: synthetic case must not claim a paper source')
        elif c['origin'] == 'paper_excerpt':
            s = c['source']
            if not isinstance(s, dict) or not all(s.get(k) for k in ['paper_id', 'source_sha256', 'location']):
                errors.append(f'{cid}: missing source provenance')
                continue
            source = sources.get(s['paper_id'])
            fragments = [c['text']] + [x['quote'] for x in c['context']]
            if source is None:
                unchecked += len(fragments)
            else:
                if s['source_sha256'] != source['sha256']:
                    errors.append(f'{cid}: source hash mismatch')
                for fragment in fragments:
                    checked += 1
                    if normalize(fragment) not in source['text']:
                        errors.append(f'{cid}: quote absent from supplied XML')
        else:
            errors.append(f'{cid}: unrecognized origin')
    return dict(case_count=len(ids), paper_fragments_checked=checked,
                paper_fragments_unchecked=unchecked, errors=errors,
                model_behavior_tested=False, block_locations_checked_by_this_script=False)


def check_links(package):
    errors = []
    for path in package.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            resolved = (path.parent / target.split('#')[0]).resolve()
            if not resolved.is_relative_to(package.resolve()) or not resolved.is_file():
                errors.append(f'{path.name}: broken or external package link {target}')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-xml', action='append', default=[], help='Original XML path; filename stem is paper_id.')
    parser.add_argument('--export-prompts', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    data = json.loads((PACKAGE / 'references/boundary-cases.json').read_text(encoding='utf-8'))
    rules = set(re.findall(r'^## (R\d+)\b', (PACKAGE / 'references/decision-rules.md').read_text(encoding='utf-8'), re.M))
    sources = {Path(p).stem: load_source(p) for p in args.source_xml}
    result = validate_cases(data, rules, sources)
    result['errors'].extend(check_links(PACKAGE))
    version = re.search(r'^  version: "([^"]+)"', (PACKAGE / 'SKILL.md').read_text(encoding='utf-8'), re.M).group(1)
    if data['case_set_version'] != version:
        result['errors'].append('Case version differs from skill version')
    if args.export_prompts and not result['errors']:
        args.export_prompts.parent.mkdir(parents=True, exist_ok=True)
        args.export_prompts.write_text(json.dumps(prompt_records(data), ensure_ascii=False, indent=2), encoding='utf-8')
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    print(payload)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload + '\n', encoding='utf-8')
    raise SystemExit(bool(result['errors']))


if __name__ == '__main__':
    main()
