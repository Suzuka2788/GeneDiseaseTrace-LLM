import copy
import importlib.util
import json
from pathlib import Path
import unittest

PACKAGE = Path(__file__).parents[1] / 'biomed-gene-disease-evidence'
spec = importlib.util.spec_from_file_location('case_validation', PACKAGE / 'scripts/validate_cases.py')
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


class CaseValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((PACKAGE / 'references/boundary-cases.json').read_text(encoding='utf-8'))
        self.rules = {f'R{i}' for i in range(1, 17)}

    def test_prompt_export_omits_answers_and_reasons(self):
        prompts = validation.prompt_records(self.data)
        self.assertTrue(prompts)
        self.assertTrue(all('expected' not in p and 'rationale' not in p for p in prompts))
        self.assertEqual([p['text'] for p in prompts], [c['text'] for c in self.data['cases']])

    def test_missing_source_is_reported_as_unchecked(self):
        result = validation.validate_cases(self.data, self.rules, {})
        self.assertFalse(result['errors'])
        self.assertGreater(result['paper_fragments_unchecked'], 0)
        self.assertEqual(result['paper_fragments_checked'], 0)
        self.assertFalse(result['model_behavior_tested'])

    def test_wrong_source_hash_and_fabricated_quotes_are_rejected(self):
        result = validation.validate_cases(self.data, self.rules,
            {'PMC10014009': {'sha256': 'wrong', 'text': 'no biomedical excerpt'}})
        self.assertTrue(any('hash mismatch' in e for e in result['errors']))
        self.assertTrue(any('quote absent' in e for e in result['errors']))

    def test_unknown_rule_duplicate_id_and_invalid_status_are_rejected(self):
        bad = copy.deepcopy(self.data)
        bad['cases'][0]['rule_ids'] = ['R999']
        bad['cases'][0]['expected']['status'] = 'probably_true'
        bad['cases'].append(copy.deepcopy(bad['cases'][0]))
        result = validation.validate_cases(bad, self.rules, {})
        for text in ['unknown or missing rule', 'duplicate ID', 'invalid status']:
            self.assertTrue(any(text in e for e in result['errors']))

    def test_presupposed_fields_validate_and_bad_values_are_rejected(self):
        source = next(c for c in self.data['cases'] if c['case_id'] == 'BC32')
        valid = {'cases': [copy.deepcopy(source)]}
        self.assertFalse(validation.validate_cases(valid, self.rules, {})['errors'])
        for field, value in [('relation_asserted', 'presumed_true'),
                             ('relation_asserted', ['presupposed']),
                             ('unresolved_reason', ['unrecognized_reason']),
                             ('unresolved_reason', 'presupposed_only')]:
            bad = copy.deepcopy(valid)
            bad['cases'][0]['expected'][field] = value
            self.assertTrue(any(f'invalid {field}' in e for e in
                                validation.validate_cases(bad, self.rules, {})['errors']))

    def test_impact_is_canonical_and_obsolete_name_is_rejected(self):
        source = next(c for c in self.data['cases'] if c['case_id'] == 'BC22')
        valid = {'cases': [copy.deepcopy(source)]}
        self.assertFalse(validation.validate_cases(valid, self.rules, {})['errors'])
        for field, value in [('impact', 'unknown_impact'), ('conflict_impact', 'noncritical')]:
            bad = copy.deepcopy(valid)
            bad['cases'][0]['expected'][field] = value
            result = validation.validate_cases(bad, self.rules, {})
            self.assertTrue(any(field in e for e in result['errors']))


if __name__ == '__main__':
    unittest.main()
