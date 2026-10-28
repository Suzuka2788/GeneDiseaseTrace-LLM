import copy
import unittest
from pathlib import Path

from biomed.evaluation import assess
from biomed.io import read_json


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.reference = read_json(Path(__file__).parent / "fixtures" / "PMC6240673_reference.json")
        self.result = {"article": {"source_sha256": self.reference["source_sha256"]},
            "entities": [{"entity_id": item["key"], "entity_type": item["entity_type"],
                "canonical_name": item["aliases"][0], "aliases": list(item["aliases"])} for item in self.reference["entities"]],
            "pairs": [{"gene_id": item["gene"], "disease_id": item["disease"],
                "status": "predicted" if item["expectation"] == "positive" else "unreviewed"}
                for item in self.reference["relation_checks"]]}

    def test_false_positive_edge_fails_despite_real_entity_names(self):
        report = assess(self.result, self.reference)
        self.assertTrue(all(p["passed"] for p in report["relation_checks"]))
        wrong = copy.deepcopy(self.result)
        wrong["pairs"][2]["status"] = "predicted"
        self.assertFalse(assess(wrong, self.reference)["relation_checks"][2]["passed"])

    def test_missing_entity_cannot_pass_no_positive_check(self):
        self.result["entities"] = [e for e in self.result["entities"] if e["entity_id"] != "LAMP1"]
        self.assertIsNone(assess(self.result, self.reference)["relation_checks"][3]["passed"])

    def test_conflicting_alias_identity_exposed(self):
        entity = next(e for e in self.result["entities"] if e["entity_id"] == "PMD_HLD1")
        entity["aliases"].append("HLD11")
        report = assess(self.result, self.reference)
        self.assertEqual(report["conflicting_numbered_aliases"], ["PMD_HLD1"])
        self.assertEqual(len(report["cross_identity_alias_conflicts"]), 1)


if __name__ == "__main__":
    unittest.main()
