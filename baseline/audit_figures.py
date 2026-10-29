"""Check derived overview/network exports against the current inference run."""
import csv
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biomed.io import read_json, write_json
from baseline.plot_integrated_network import pool
from baseline.plot_total_summary import summary_data


def audit_figures(output):
    output = Path(output)
    errors = []
    expected_summary, _, _ = summary_data(output)
    if read_json(output / "figures/total_summary_data.json") != expected_summary:
        errors.append("Overview data differs from the current run")
    nodes, edges, _, _, summary = pool(output)
    directory = output / "integrated"
    data = read_json(directory / "network_data.json")
    if data["summary"] != summary:
        errors.append("Integrated network summary differs from the current run")
    if len(data["nodes"]) != len(nodes) or {n["id"] for n in data["nodes"]} != set(nodes):
        errors.append("Integrated network node set mismatch")
    actual_edges = {(e["gene_id"], e["disease_id"]): e for e in data["edges"]}
    if len(actual_edges) != len(data["edges"]) or set(actual_edges) != set(edges):
        errors.append("Integrated network edge set mismatch")
    for key in set(actual_edges) & set(edges):
        if actual_edges[key]["papers"] != edges[key]["papers"]:
            errors.append("Integrated edge provenance mismatch: " + str(key))
    root = ET.parse(directory / "gene_disease_network.svg").getroot()
    ids = [n.get("id", "") for n in root.iter()]
    for prefix, expected in (("node_", {"node_" + n["gid"] for n in nodes.values()}),
                             ("label_", {"label_" + n["gid"] for n in nodes.values()}),
                             ("edge_", {"edge_" + e["id"] for e in edges.values()})):
        actual = [value for value in ids if value.startswith(prefix)]
        if len(actual) != len(expected) or set(actual) != expected:
            errors.append("SVG ID set mismatch: " + prefix)
    for filename, expected, key in (("nodes.csv", set(nodes), "id"),
                                     ("edges.csv", {e["id"] for e in edges.values()}, "id")):
        with (directory / filename).open(encoding="utf-8-sig", newline="") as stream:
            records = list(csv.DictReader(stream))
        if len(records) != len(expected) or {r[key] for r in records} != expected:
            errors.append("Integrated CSV ID set mismatch: " + filename)
    for edge in data["edges"]:
        for source in edge["source_pairs"]:
            if not (directory / source["report"]).resolve().is_file():
                errors.append("Missing source report: " + source["paper_id"])
    for folder, stem in ((output / "figures", "total_summary"), (directory, "gene_disease_network")):
        for suffix in (".svg", ".png", ".pdf"):
            path = folder / (stem + suffix)
            if not path.is_file() or not path.stat().st_size:
                errors.append("Missing/empty figure: " + path.name)
    return {"passed": not errors, "run_id": summary["run_id"], "errors": errors,
            "gene_nodes": summary["gene_nodes"], "disease_nodes": summary["disease_nodes"],
            "predicted_edges": summary["unique_predicted_pairs"],
            "note": "Derived-file integrity only; not semantic evidence verification."}


def main():
    config = read_json(ROOT / "baseline" / "config.json")
    output = ROOT / config["output_dir"]
    report = audit_figures(output)
    write_json(output / "figures_integrity.json", report)
    print(report)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
