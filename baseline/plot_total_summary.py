"""Presentation overview from all 100 recorded article results; no simulated data."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from biomed.io import read_json, write_csv, write_json
from biomed.results import load_results

INK = "#183543"
MUTED = "#637984"
TEAL = "#16879A"
PURPLE = "#7F719E"
AMBER = "#BE853C"
LINE = "#DCE5E9"
PALE = "#F4F8F9"


def summary_data(output):
    output = Path(output)
    papers = [r["summary"] for r in load_results(output)]
    if not papers:
        raise ValueError("No completed current-run results to summarize")
    quality = read_json(output / "quality_report.json")
    audit = read_json(output / "delivery_audit.json")
    manifest = read_json(output / "run_manifest.json")
    if quality["run_id"] != manifest["run_id"] or audit["run_id"] != manifest["run_id"]:
        raise ValueError("Quality/audit records belong to a different run")
    if not audit["passed"]:
        raise ValueError("Current-run delivery audit must pass before plotting")
    if len(papers) != quality["papers"] or len(papers) != audit["counts"]["papers"]:
        raise ValueError("Input sources disagree on article counts")
    totals = {key: sum(int(p[key]) for p in papers) for key in ("genes", "diseases", "pairs", "predicted_edges")}
    types = quality["article_types"]
    with_prediction = sum(int(p["predicted_edges"]) > 0 for p in papers)
    without_prediction = len(papers) - with_prediction
    groups = [("Research articles", types.get("research-article", 0)),
              ("Case reports", types.get("case-report", 0)),
              ("Review articles", types.get("review-article", 0)),
              ("Other article types", sum(v for k, v in types.items()
                                          if k not in ("research-article", "case-report", "review-article")))]
    data = {"run_id": manifest["run_id"], "n_papers": len(papers), **totals, "article_types_grouped": dict(groups),
            "papers_with_prediction": with_prediction, "papers_without_prediction": without_prediction,
            "structural_checks_passed": quality["all_structural_checks_passed"],
            "semantic_verification": quality["semantic_verification"],
            "counting_rule": "Gene/disease nodes and pairs are summed per paper; not pooled unique entities.",
            "exclusions": "No current-run result excluded. All non-research/case-report/review-article types are grouped as Other.",
            "statistics": "Descriptive counts for the complete supplied collection; no inferential tests."}
    return data, papers, groups


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    config = read_json(ROOT / "baseline" / "config.json")
    output = ROOT / config["output_dir"]
    destination = output / "figures"
    destination.mkdir(exist_ok=True)
    data, papers, groups = summary_data(output)
    totals = data
    with_prediction = data["papers_with_prediction"]
    without_prediction = data["papers_without_prediction"]
    write_json(destination / "total_summary_data.json", data)
    write_csv(destination / "total_summary_source.csv", papers, list(papers[0]))

    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "font.size": 15, "svg.fonttype": "none", "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.linewidth": 0.7, "text.color": INK, "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": INK})
    fig = plt.figure(figsize=(16, 9), facecolor="white")
    canvas = fig.add_axes([0, 0, 1, 1])
    canvas.set_axis_off()

    def text(x, y, value, size=15, color=INK, weight="normal", **kwargs):
        return canvas.text(x, y, value, transform=canvas.transAxes, fontsize=size,
                           color=color, weight=weight, va="top", **kwargs)

    def box(x, y, w, h, color=PALE, border=LINE):
        patch = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.006,rounding_size=0.009",
                               facecolor=color, edgecolor=border, linewidth=0.8,
                               transform=canvas.transAxes)
        canvas.add_patch(patch)

    text(.045, .958, "BIOMEDICAL LITERATURE MINING  /  AUTOMATED BASELINE", 12, TEAL, "bold")
    text(.045, .912, f"Gene–disease extraction across {len(papers)} papers", 29, weight="bold")
    text(.045, .85, "Structured XML → local entity alignment → candidate-pair ledger → predicted bipartite graphs", 15, MUTED)

    metrics = [(len(papers), "XML articles processed", TEAL),
               (totals["genes"], "Gene nodes", TEAL),
               (totals["diseases"], "Disease nodes", PURPLE),
               (totals["pairs"], "Candidate pairs", INK),
               (totals["predicted_edges"], "Model-predicted edges", AMBER)]
    width = .172
    for i, (number, label, color) in enumerate(metrics):
        x = .045 + i * .184
        box(x, .659, width, .139)
        text(x + .014, .778, f"{number:,}", 31, color, "bold")
        text(x + .014, .705, label, 13, MUTED)
    text(.045, .635, "Node and pair counts are summed per paper; they are not unique counts across the collection.", 11.5, MUTED)

    box(.045, .22, .439, .364, "white")
    box(.516, .22, .439, .364, "white")
    text(.061, .568, "a", 15, weight="bold")
    text(.084, .568, "Input collection", 18, weight="bold")
    text(.061, .526, f"All {len(papers)} current-run articles retained", 12, MUTED)
    ax = fig.add_axes([.205, .274, .237, .225])
    values = [v for _, v in groups]
    ax.barh(range(4), values, height=.51, color=[TEAL, "#6BABB4", "#A0C5CB", "#CADADF"])
    ax.set_yticks(range(4), labels=[name for name, _ in groups], fontsize=13)
    ax.invert_yaxis()
    ax.set_xlim(0, 80)
    ax.set_xticks([0, 20, 40, 60, 80], labels=["0", "20", "40", "60", "80"], fontsize=10)
    ax.tick_params(axis="both", length=0, pad=7)
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    for i, v in enumerate(values):
        ax.text(v + 1.6, i, str(v), va="center", fontsize=13, color=INK, weight="bold")
    ax.set_xlabel("Number of articles", fontsize=11, labelpad=8)

    text(.532, .568, "b", 15, weight="bold")
    text(.555, .568, "Prediction coverage", 18, weight="bold")
    text(.532, .526, "Articles with ≥1 gene–disease prediction", 12, MUTED)
    text(.532, .48, f"{with_prediction} / {len(papers)}", 31, AMBER, "bold")
    y, x, w = .373, .532, .405
    ratio = with_prediction / len(papers)
    canvas.add_patch(Rectangle((x, y), w * ratio, .036, facecolor=AMBER, transform=canvas.transAxes))
    canvas.add_patch(Rectangle((x + w * ratio, y), w * (1 - ratio), .036, facecolor="#E5EBEE", transform=canvas.transAxes))
    text(.532, .354, f"{with_prediction} with predictions", 12, AMBER)
    text(.937, .354, f"{without_prediction} without predictions", 12, MUTED, ha="right")
    text(.532, .294, "A missing prediction is not a negative finding.", 13, MUTED)
    text(.532, .258, f"Structural integrity checks: {len(papers)} / {len(papers)} passed", 12, TEAL)

    box(.045, .083, .91, .095, "#FFF6E8", "#E9D5B5")
    text(.061, .159, "CURRENT STATUS", 11, AMBER, "bold")
    text(.061, .132, "Full-text semantic verification and accuracy evaluation are pending.", 17, INK, "bold")
    text(.045, .047, "Source: supplied XML articles, cached PubTator3 annotations and local output audit. Descriptive counts; no accuracy claim.", 10.5, MUTED)

    stem = destination / "total_summary"
    fig.savefig(stem.with_suffix(".svg"), facecolor="white")
    fig.savefig(stem.with_suffix(".pdf"), facecolor="white")
    fig.savefig(stem.with_suffix(".png"), dpi=300, facecolor="white")
    plt.close(fig)
    write_json(destination / "total_summary_qa.json", {
        "run_id": data["run_id"], "backend": "python", "archetype": "quantitative grid",
        "dimensions": "16 x 9 inches", "source_papers": data["n_papers"],
        "claim": "Current-run descriptive baseline counts; semantic verification remains pending.",
        "exclusions": data["exclusions"], "visual_review": "Required after rendering",
        "accepted_preflight_warnings": ["Presentation dimensions rather than journal-column width",
                                          "300 dpi PNG plus editable vector exports; TIFF not required"]})
    print(stem.with_suffix(".png"))


if __name__ == "__main__":
    main()
