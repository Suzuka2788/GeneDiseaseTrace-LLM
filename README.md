# GeneDiseaseTrace-LLM

Evidence-traceable extraction of gene–disease relations from full-text biomedical papers with an LLM.
Every reported relation points to the sentence(s) that support it and is labeled as the paper's own finding or as
background knowledge; pairs the text only hints at are flagged *uncertain* instead of being reported.

**Project page (results, method and interactive graphs):** https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/

## The task
For each of 100 PMC full-text papers (JATS XML): extract all genes and diseases, decide for every gene × disease
pair whether the paper gives evidence of an association, correlation or causal relationship, and build one
gene–disease bipartite graph per paper.

## Method
1. **Rules first.** Decision rules (R1–R16) and 35 boundary cases were developed on pilot papers and kept as a
   versioned skill (`skill_snapshot/`, version 1.3.0).
2. **Compressed into a decision card.** The full rules (about 20k tokens) were condensed into a short card that
   makes the same decisions on 110 of 112 boundary-case checks, stable over 3 runs.
3. **One request per paper.** A script packs the card, a compact output format and the paper's numbered sentences
   into a single tool-less request to Claude Opus 5.5. The model answers with short lines that cite sentence IDs
   instead of copying text.
4. **Deterministic post-processing.** A script rebuilds quotes and character offsets from the source, completes
   the gene × disease matrix and writes entity, mention, evidence and pair tables plus GraphML. A contract validator
   checks every quote and offset; only if it finds problems is the error list sent back once for repair.

## Results
| Evaluation | Result | Details |
|---|---|---|
| A/B test on 12 frozen papers | The card agrees with the full rules on 97.6% of pairs and is 11% cheaper; low reasoning effort is 2.4× faster but finds fewer relations. V1 (card, medium effort) was chosen. | [A/B summary](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/results/ab/ab_summary.html) |
| All 100 papers | 100/100 valid; 972 supported relations (plus 451 uncertain, 47 explicitly negative); $0.44 and 78 s per paper. PubTator3 reports 198 relations; 90% of ours rest on text beyond the abstract. | [vs PubTator3](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/results/full100/vs_pubtator.html) |
| BioRED, all 419 abstracts with a gene–disease relation | Zero-shot: precision 0.89, recall 0.43, F1 0.58 (0.81 / 0.58 / 0.68 counting *uncertain*); stable across Train / Dev / Test. On 50 test abstracts: precision on par with PubTator3 (0.84 vs 0.83), recall lower (0.41 vs 0.65). | [BioRED page](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/results/biored/biored_results.html) |
| Bipartite graphs | One graph per paper, BioRED graphs overlaid on the gold relations, and all 100 papers merged into one network | [Graphs](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/graphs/) |

**Limitations.** Full-text precision has not been checked by hand (BioRED measures abstracts). Recall on BioRED is
lower than PubTator3's, mostly because hedged statements are kept as *uncertain* and symptoms are kept apart from
diseases. Entities are not mapped to database IDs (NCBI Gene / MeSH). Agreement with BioRED's novel/background
label is 75%. Pretraining exposure of the model to these texts cannot be ruled out.

## Repository layout
| Path | Contents |
|---|---|
| `experiments/single_shot/` | **The method.** Card, output format, packer, runner, expander, batch runner, frozen A/B variants, PubTator3 comparison and page renderers; `runs/` holds every run's outputs. Notes (Chinese): `README.md` |
| `experiments/biored/` | **The benchmark.** BioRED adapter (`prepare.py`), frozen samples and gold, scorer (`evaluate.py`), PubTator3 baseline, results page. Notes (Chinese): `README.md` |
| `skill_snapshot/` | The decision rules: skill 1.3.0 with data contract and boundary cases (exported from a separate repository) |
| `toolkit/` | Contract validator and shared helpers (also the earlier agent-mode toolkit) |
| `biomed/` | JATS parser and PubTator3 client shared by everything |
| `baseline/` | The first, LLM-free baseline: PubTator3 annotations aligned to the full text (`run.ps1`, config, audit and figure scripts) |
| `site_builder/` | Builds the public project page (`build_site.py`; bilingual main page template, graph viewers) |
| `tests/` | Unit tests for the parser, pipeline and baseline |
| `archive/` | Development history: manual annotation of paper 1, blind tests, rule proposals, one-off scripts |

## Reproducing
Python 3.12; the Claude CLI must be installed and signed in for model runs.

```bash
# Inputs (not included: PMC licences vary) go in .Input/100papers/
python experiments/single_shot/batch.py --variant v1_card_lean_medium --all --run-set full100

# BioRED: put BIORED.zip from https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/ in experiments/biored/data/ and unzip it
python experiments/biored/prepare.py --all
python experiments/single_shot/batch.py --variant v1_card_lean_medium --run-set biored_all --papers <ids from sample_all.json>
python experiments/biored/evaluate.py v1_card_lean_medium biored_all

# Tests and the public page
python -m unittest discover -s tests
python site_builder/build_site.py
```

The PubTator3 comparison reads the baseline's aligned annotations in `outputs/`; build them with
`.\baseline\run.ps1 -Command run` (see `baseline/README.md`).

## Data and credits
BioRED: Luo et al., *Briefings in Bioinformatics* 2022 (public domain, NCBI). PubTator3: NCBI. The 100 input
papers and full-text prompts are not redistributed here.
