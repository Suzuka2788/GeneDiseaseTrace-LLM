# Manuscript (LaTeX)

Journal of Biomedical Informatics format (Elsevier `elsarticle`). Text follows `../draft_jbi_v2.md`.

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
| `figures/fig1_example.tex` | Worked example on PMC10014009: source text, model output, pair records, per-paper graph |
| `figures/fig2_pipeline.tex` | The single-request pipeline |
| `figures/fig3_pr.tex` | Precision–recall operating points with 95% CIs on the three benchmarks |
| `figures/fig4_recall.tex` | Where BioRED recall is lost, and reason-code rates for the operating point |

All figures are drawn in TikZ/pgfplots from numbers typed into the `.tex` files. Each file's header names the result files the numbers come from.

Open items are marked `[TODO: ...]` in red in the PDF.
