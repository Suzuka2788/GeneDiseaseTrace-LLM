# Manuscript (LaTeX)

Journal of Biomedical Informatics format (Elsevier `elsarticle`, 10pt preprint). Layout and section logic follow a recent JBI paper prepared the same way: Park et al., *Automated Identification of Incidentalomas Requiring Follow-Up* (arXiv:2512.05537; copy in `../jbi_examples/`). Text follows `../draft_jbi_v2.md`, regrouped into that paper's structure (Datasets → Relation Extraction → Evaluation; Results → Error Analysis; Discussion → Limitations).

Highlights and the Statement of significance are collected separately at submission, so they live in `submission_extras.tex`.

## Build

```bash
latexmk -pdf main.tex
```

Needs a TeX Live with `elsarticle`, `pgfplots` and `tikz` (TeX Live 2026 works). For the double-spaced submission version, change `preprint` to `review` in the first line of `main.tex`.

## Files

| File | Content |
|---|---|
| `main.tex` | Manuscript text, tables and figure captions |
| `refs.bib` | References (entries 12–20 were added by Gemini and still need checking against the publisher pages) |
| `figstyle.tex` | Shared colours and TikZ/pgfplots styles for all figures |
| `submission_extras.tex` | Highlights and Statement of significance (separate submission items) |
| `figures/fig2_pipeline.tex` | Figure 1: the single-request pipeline |
| `figures/fig1_example.tex` | Figure 2: worked example on PMC10014009 (source text, model output, pair records, per-paper graph) |
| `figures/fig3_pr.tex` | Figure 3: precision–recall operating points with 95% CIs on the three benchmarks |
| `figures/fig4_recall.tex` | Figure 4: where BioRED recall is lost, and reason-code rates for the operating point |

All figures are drawn in TikZ/pgfplots from numbers typed into the `.tex` files. Each file's header names the result files the numbers come from.

Open items are marked `[TODO: ...]` in red in the PDF.
