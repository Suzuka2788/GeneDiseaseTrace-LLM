import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from biomed.io import read_json, write_json
from biomed.pipeline import prepare, run
from biomed.results import load_results
from baseline.plot_integrated_network import pool, write_tables, write_html
from baseline.plot_total_summary import summary_data
from baseline.audit_outputs import audit_outputs
from test_pipeline import JATS, source_document


class RunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.input = self.root / "input"
        self.input.mkdir()
        self.output = self.root / "output"
        self.config = {"input_dir": str(self.input), "output_dir": str(self.output),
                       "cache_dir": str(self.root / "cache"), "include_references": False}
        (self.input / "paper.xml").write_text(JATS, encoding="utf-8")
        document = source_document()
        document.update({"pmid": "1", "pmcid": "PMC1"})
        write_json(self.root / "cache/pubtator/1.json", {"PubTator3": [document]})

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            articles = prepare(self.config)
            return run(self.config, articles, offline=True, **kwargs)

    def test_successful_run_has_complete_auditable_outputs(self):
        self.assertEqual(self.execute(), [])
        audit = audit_outputs(self.output)
        self.assertTrue(audit["passed"], audit["errors"])
        self.assertEqual(audit["counts"]["papers"], 1)

    def test_failed_rerun_does_not_count_previous_result(self):
        self.execute()
        old_run = read_json(self.output / "papers/PMC1/result.json")
        self.config["include_references"] = True
        self.config["cache_dir"] = str(self.root / "missing_cache")
        self.assertEqual(len(self.execute()), 1)
        manifest = read_json(self.output / "run_manifest.json")
        self.assertEqual(manifest["available_results"], 0)
        self.assertEqual(manifest["successful_paper_ids"], [])
        with (self.output / "summary.csv").open(encoding="utf-8-sig", newline="") as stream:
            self.assertEqual(list(csv.DictReader(stream)), [])
        self.assertEqual(read_json(self.output / "papers/PMC1/result.json"), old_run)
        self.assertFalse(audit_outputs(self.output)["passed"])

    def test_fetch_does_not_replace_inference_manifest(self):
        self.execute()
        before = (self.output / "run_manifest.json").read_bytes()
        self.execute(fetch_only=True)
        self.assertEqual((self.output / "run_manifest.json").read_bytes(), before)
        self.assertEqual(read_json(self.output / "fetch_manifest.json")["cached_paper_ids"], ["PMC1"])

    def test_audit_rejects_empty_output(self):
        report = audit_outputs(self.output)
        self.assertFalse(report["passed"])

    def test_audit_rejects_missing_expected_paper(self):
        self.execute()
        (self.output / "papers/PMC1/result.json").unlink()
        report = audit_outputs(self.output)
        self.assertFalse(report["passed"])

    def test_audit_rejects_same_count_wrong_graph_endpoints(self):
        self.execute()
        path = self.output / "papers/PMC1/graph.graphml"
        text = path.read_text(encoding="utf-8")
        import xml.etree.ElementTree as ET
        tree = ET.fromstring(text)
        edge = tree.find(".//{*}edge")
        self.assertIsNotNone(edge)
        edge.set("source", edge.get("target"))
        path.write_text(ET.tostring(tree, encoding="unicode"), encoding="utf-8")
        self.assertFalse(audit_outputs(self.output)["passed"])

    def test_stale_result_run_id_is_rejected(self):
        self.execute()
        path = self.output / "papers/PMC1/result.json"
        data = read_json(path)
        data["run_id"] = "old-run"
        write_json(path, data)
        with self.assertRaisesRegex(ValueError, "Stale run"):
            load_results(self.output)
        self.assertFalse(audit_outputs(self.output)["passed"])

    def test_stale_result_config_is_rejected(self):
        self.execute()
        path = self.output / "papers/PMC1/result.json"
        data = read_json(path)
        data["config_sha256"] = "old-config"
        write_json(path, data)
        with self.assertRaisesRegex(ValueError, "configuration"):
            load_results(self.output)

    def test_failed_integrity_does_not_publish_result(self):
        with patch("biomed.pipeline.validate", return_value={"passed": False, "errors": ["corrupt_pair"]}):
            failures = self.execute()
        self.assertEqual(len(failures), 1)
        self.assertFalse((self.output / "papers/PMC1/result.json").exists())
        self.assertEqual(read_json(self.output / "run_manifest.json")["successful_paper_ids"], [])

    def test_parse_failure_prevents_successful_audit(self):
        (self.input / "invalid.xml").write_text("<article>broken", encoding="utf-8")
        self.execute()
        self.assertFalse(audit_outputs(self.output)["passed"])

    def test_figures_use_only_current_manifest_and_dynamic_counts(self):
        self.execute()
        # An old, unrelated JSON must not become an extra graph input.
        write_json(self.output / "papers/OLD/result.json", {"unrelated": True})
        write_json(self.output / "delivery_audit.json", audit_outputs(self.output))
        data, _, _ = summary_data(self.output)
        self.assertEqual(data["n_papers"], 1)
        self.assertEqual(data["predicted_edges"], 1)
        nodes, edges, _, _, summary = pool(self.output)
        self.assertEqual(len(nodes), 2)
        self.assertEqual(len(edges), 1)
        self.assertEqual(summary["input_papers"], 1)

    def test_overview_rejects_stale_audit(self):
        self.execute()
        audit = audit_outputs(self.output)
        audit["run_id"] = "old-run"
        write_json(self.output / "delivery_audit.json", audit)
        with self.assertRaisesRegex(ValueError, "different run"):
            summary_data(self.output)

    def test_integrated_exports_preserve_identifiers_and_provenance(self):
        self.execute()
        nodes, edges, _, _, summary = pool(self.output)
        directory = self.output / "integrated"
        directory.mkdir()
        data = write_tables(nodes, edges, summary, directory)
        self.assertEqual(read_json(directory / "network_data.json"), data)
        with (directory / "edges.csv").open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["gene_id"], next(iter(edges.values()))["gene_id"])
        import json
        self.assertEqual(json.loads(rows[0]["source_pairs"]), data["edges"][0]["source_pairs"])

    def test_integrated_html_escapes_source_labels_and_uses_actual_counts(self):
        self.execute()
        nodes, edges, _, _, summary = pool(self.output)
        directory = self.output / "integrated"
        directory.mkdir()
        data = write_tables(nodes, edges, summary, directory)
        data["nodes"][0]["label"] = "</script><script>unexpected()</script>"
        (directory / "gene_disease_network.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
        write_html(data, directory)
        page = (directory / "network.html").read_text(encoding="utf-8")
        self.assertNotIn(data["nodes"][0]["label"], page)
        self.assertIn("1 genes · 1 diseases · 1 predicted pairs", page)
