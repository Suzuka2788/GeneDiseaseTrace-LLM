import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from biomed.jats import normalize, parse_article
from biomed.pubtator import extract_entities, pair_records, relation_predictions
from biomed.report import graphml, safe_json
from biomed.validate import validate


JATS = '''<article><front><article-meta><article-id pub-id-type="pmcid">PMC1</article-id>
<article-id pub-id-type="pmid">1</article-id><title-group><article-title>Gene study</article-title></title-group>
<abstract><p>No association was found between <italic>ABC1</italic> and disease X.</p></abstract></article-meta></front>
<body><sec id="results"><title>Results</title><p>ABC1 and disease X were measured.</p>
<table-wrap id="t1"><label>Table 1</label><caption><p>Measurements</p></caption><table><tbody><tr><th>Gene</th><th>Disease</th></tr><tr><td>ABC1</td><td>disease X</td></tr></tbody></table></table-wrap>
<fig><label>Figure 1</label><caption><p>ABC1 expression</p></caption><graphic href="fig.png"/></fig></sec></body>
<back><ref-list><ref id="r1"><mixed-citation>REFONLY and disease Y.</mixed-citation></ref></ref-list></back></article>'''


def annotation(kind, identifier, text, name=None):
    return {"text": text, "infons": {"type": kind, "identifier": identifier, "name": name or text}}


def source_document():
    return {"passages": [{"text": "No association was found between ABC1 and disease X.",
                           "annotations": [annotation("Gene", "123", "ABC1"), annotation("Disease", "MESH:D1", "disease X")]},
                          {"text": "REFONLY and disease Y.",
                           "annotations": [annotation("Gene", "999", "REFONLY"), annotation("Disease", "MESH:D2", "disease Y")]}],
            "relations": [{"id": "R1", "infons": {"type": "Association", "score": "0.99",
                            "role1": {"type": "Gene", "identifier": "123"},
                            "role2": {"type": "Disease", "identifier": "MESH:D1"}}}]}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "paper.xml"
        self.path.write_text(JATS, encoding="utf-8")
        self.article = parse_article(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def extraction(self):
        entities, rejected = extract_entities(self.article, source_document())
        pairs = pair_records(self.article, entities, relation_predictions(source_document(), entities))
        return entities, pairs, rejected

    def test_inline_markup_and_reference_scope(self):
        texts = [b["text"] for b in self.article["blocks"]]
        self.assertIn("No association was found between ABC1 and disease X.", texts)
        self.assertFalse(any("REFONLY" in t for t in texts))
        included = parse_article(self.path, include_references=True)
        self.assertTrue(any("REFONLY" in b["text"] for b in included["blocks"]))

    def test_table_cells_and_caption_preserved(self):
        self.assertTrue(any(b["text"] == "ABC1 | disease X" for b in self.article["blocks"]))
        self.assertTrue(any(b["text"] == "ABC1 expression" and b["content_type"] == "caption" for b in self.article["blocks"]))

    def test_only_source_aligned_entities_retained(self):
        entities, _, rejected = self.extraction()
        self.assertEqual(len(entities), 2)
        self.assertNotIn("REFONLY", str(entities))
        self.assertEqual(len(rejected), 2)

    def test_short_heading_does_not_shadow_paragraph_alignment(self):
        document = {"passages": [{"text": "Results ABC1 and disease X were measured.", "annotations":
                                  [annotation("Gene", "123", "ABC1"), annotation("Disease", "MESH:D1", "disease X")]}]}
        entities, _ = extract_entities(self.article, document)
        self.assertEqual(len(entities), 2)
        self.assertTrue(all(any("ABC1 and disease X" in next(b["text"] for b in self.article["blocks"] if b["block_id"] == m["block_id"])
                                for m in entity["mentions"]) for entity in entities))

    def test_prediction_with_negation_never_auto_accepted(self):
        entities, pairs, _ = self.extraction()
        self.assertEqual(pairs[0]["status"], "predicted")
        self.assertEqual(pairs[0]["semantic_verification"], "not_run")
        self.assertIn("No association", pairs[0]["evidence"][0]["quote"])
        self.assertTrue(validate(self.article, entities, pairs)["passed"])

    def test_cooccurrence_alone_never_creates_edge(self):
        entities, _, _ = self.extraction()
        pairs = pair_records(self.article, entities, {})
        self.assertEqual(pairs[0]["status"], "unreviewed")

    def test_fabricated_quote_fails_integrity(self):
        entities, pairs, _ = self.extraction()
        pairs[0]["evidence"][0]["quote"] = "Fabricated causal evidence"
        self.assertFalse(validate(self.article, entities, pairs)["passed"])

    def test_unverified_supported_edge_fails_integrity(self):
        entities, pairs, _ = self.extraction()
        pairs[0]["status"] = "supported"
        self.assertFalse(validate(self.article, entities, pairs)["passed"])

    def test_isolates_retained_in_graphml(self):
        entities, pairs, _ = self.extraction()
        result = {"article": self.article, "entities": entities, "pairs": pair_records(self.article, entities, {})}
        target = self.root / "graph.graphml"
        graphml(result, target)
        root = ET.parse(target).getroot()
        self.assertEqual(len(root.findall(".//{*}node")), 2)
        self.assertEqual(len(root.findall(".//{*}edge")), 0)

    def test_missing_pair_record_fails_coverage(self):
        entities, pairs, _ = self.extraction()
        self.assertFalse(validate(self.article, entities, [])["passed"])

    def test_duplicate_endpoints_with_distinct_ids_fail_coverage(self):
        entities = [{"entity_id": name, "entity_type": kind, "mentions": []}
                    for name, kind in [("G1", "gene"), ("G2", "gene"), ("D1", "disease"), ("D2", "disease")]]
        pairs = [{"pair_id": f"p{i}", "gene_id": "G1", "disease_id": "D1", "evidence": [],
                  "status": "unreviewed", "semantic_verification": "not_run"} for i in range(4)]
        result = validate({"blocks": []}, entities, pairs)
        self.assertFalse(result["passed"])
        self.assertTrue(any(e.startswith("duplicate_pair_endpoints:") for e in result["errors"]))

    def test_inline_figure_preserves_surrounding_text(self):
        self.path.write_text(JATS.replace("ABC1 and disease X were measured.",
                             "Before<fig><caption><p>Caption</p></caption></fig>AFTER_GENE causes disease."), encoding="utf-8")
        article = parse_article(self.path)
        self.assertTrue(any("BeforeAFTER_GENE causes disease." == b["text"] for b in article["blocks"]))

    def test_adjacent_inline_figures_preserve_both_tails(self):
        self.path.write_text(JATS.replace("ABC1 and disease X were measured.",
                             "A<fig><caption><p>One</p></caption></fig>B<fig><caption><p>Two</p></caption></fig>C"), encoding="utf-8")
        article = parse_article(self.path)
        self.assertTrue(any(b["text"] == "ABC" for b in article["blocks"]))

    def test_unresolved_identifiers_do_not_merge(self):
        document = {"passages": [{"text": "No association was found between ABC1 and disease X.", "annotations":
                                  [annotation("Gene", "-", "ABC1"), annotation("Disease", "-", "disease X")]}]}
        entities, _ = extract_entities(self.article, document)
        self.assertEqual(len(entities), 2)

    def test_entity_match_respects_case_and_word_boundaries(self):
        document = {"passages": [{"text": "No association was found between ABC1 and disease X.", "annotations":
                                  [annotation("Gene", "123", "ABC"), annotation("Gene", "456", "abc1")]}]}
        entities, _ = extract_entities(self.article, document)
        self.assertEqual(entities, [])

    def test_script_data_cannot_close_script_tag(self):
        data = {"title": "</script><script>alert(1)</script>"}
        escaped = safe_json(data)
        self.assertNotIn("</script>", escaped)
        self.assertEqual(json.loads(escaped), data)

    def test_typography_normalization(self):
        self.assertEqual(normalize("loss‐of‐function\u00a0  mutations"), "loss-of-function mutations")

    def test_article_id_cannot_escape_output_directory(self):
        self.path.write_text(JATS.replace("PMC1", "../../elsewhere"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "identifier"):
            parse_article(self.path)


if __name__ == "__main__":
    unittest.main()
