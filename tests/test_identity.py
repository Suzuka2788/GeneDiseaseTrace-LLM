import copy
import unittest

from biomed.identity import (collect_mentions, identity_task, mention_tasks, reconcile_reviews,
                             resolve_identities, review_tasks)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.article = {"paper_id": "PMC1", "source_sha256": "test", "blocks": [
            {"block_id": "b0001", "section": "Body", "text": "PMD is also called HLD1. HLD11 is different. POLR1C variants are associated with HLD11."},
            {"block_id": "b0002", "section": "Caption", "text": "POLR1C was stained with anti-LAMP1 antibody."}]}
        self.tasks = mention_tasks(self.article)
        response = {self.tasks[0]["task_id"]: {"mentions": [
            {"surface": s, "entity_type": "disease", "ambiguity": "none", "block_id": "b0001"}
            for s in ("PMD", "HLD1", "HLD11")]}}
        self.mentions = collect_mentions(self.article, self.tasks, response)
        self.item = identity_task(self.article, self.mentions)
        self.payload = {"entities": [self.entity("PMD", ["PMD", "HLD1"]), self.entity("HLD11", ["HLD11"])], "excluded": []}

    def entity(self, name, aliases):
        return {"canonical_name": name, "entity_type": "disease", "species": "human",
                "species_context": "disease", "ambiguity": "none", "aliases": aliases,
                "identity_evidence": [{"block_id": "b0001", "quote": self.article["blocks"][0]["text"]}]}

    def test_alias_proof_and_all_occurrences(self):
        entities = resolve_identities(self.article, self.item, self.payload, self.mentions)
        self.assertEqual(entities[0]["aliases"], ["PMD", "HLD1"])
        hld1 = [m for m in self.mentions if m["surface"] == "HLD1"][0]
        self.assertEqual(len(hld1["mentions"]), 1)

    def test_numbered_subtypes_cannot_silently_merge(self):
        payload = {"entities": [self.entity("HLD1", ["PMD", "HLD1", "HLD11"])], "excluded": []}
        with self.assertRaisesRegex(ValueError, "numbered aliases"):
            resolve_identities(self.article, self.item, payload, self.mentions)

    def test_substring_not_valid_alias_evidence(self):
        payload = copy.deepcopy(self.payload)
        payload["entities"][0]["identity_evidence"][0]["quote"] = "HLD11 is different."
        with self.assertRaisesRegex(ValueError, "whole-token"):
            resolve_identities(self.article, self.item, payload, self.mentions)

    def test_silent_surface_omission_rejected(self):
        payload = copy.deepcopy(self.payload)
        payload["entities"].pop()
        with self.assertRaisesRegex(ValueError, "accounting"):
            resolve_identities(self.article, self.item, payload, self.mentions)

    def test_same_model_disagreement_blocks_edge(self):
        first = {"pair_id": "p1", "gene_id": "g1", "disease_id": "d1", "decision": "supported",
                 "relation_type": "association", "source_scope": "study", "reason": "initial", "evidence": []}
        second = {**first, "decision": "not_found", "relation_type": "none", "reason": "review"}
        final = reconcile_reviews([first], [second])[0]
        self.assertEqual(final["status"], "unreviewed")
        self.assertEqual(final["decision"], "uncertain")
        self.assertEqual(final["independent_semantic_review"], "not_run")
        final = reconcile_reviews([first], [first])[0]
        self.assertEqual(final["status"], "predicted")

    def test_review_blinded_to_first_answers(self):
        tasks = review_tasks(self.article, [], [{"pair_id": "p1", "gene_id": "g1", "disease_id": "d1"}])
        self.assertEqual(set(tasks[0]["context"]), {"blocks", "entities", "pairs"})
        self.assertNotIn("decision", tasks[0]["context"]["pairs"][0])


if __name__ == "__main__":
    unittest.main()
