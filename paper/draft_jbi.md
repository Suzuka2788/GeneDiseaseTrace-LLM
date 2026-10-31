# Evidence-traceable, status-aware gene–disease relation extraction with a large language model: a multi-benchmark evaluation

Oct 30, 2026 · @zeqian tong

Draft for discussion with Dr. Zhi Wei. All numbers come from the project's evaluation files; items marked \[TODO\] still need experiments.

## Abstract

**Objective.** To develop and evaluate a zero-shot method that extracts gene–disease relations from biomedical papers with three additions: sentence-level evidence, a four-way status (supported, uncertain, explicit negative, not found) and a source label (this study or background).

**Methods.** A large language model (Claude Opus 5.5) reads each paper in a single request and follows a frozen one-page decision card. A deterministic validator checks every cited span against the text. Without benchmark-specific tuning, we evaluated the method on three benchmarks: BioRED (419 abstracts), EU-ADR (100 abstracts) and a 40-article full-text sample of RENET2. Pairs were matched per document, confidence intervals were bootstrapped, and PubTator3 served as the comparator.

**Results.** On BioRED, precision was 0.894 (95% CI 0.855–0.931) and recall 0.430. An operating point chosen on Train+Dev raised held-out Test F1 from 0.542 to 0.627 with precision unchanged. PubTator3, which is trained on BioRED, scored higher on a 50-abstract test sample (F1 0.726 vs 0.551). Together, the two systems recovered 73% of gold relations. On EU-ADR, F1 was comparable (0.506 vs 0.529), and all three negative gold pairs were labelled explicit negative. On RENET2 full text, our recall exceeded PubTator3's (0.370 vs 0.254), and only 2 of 223 supported pairs contradicted a gold label. Re-querying 97 unjudged pairs whose gene and disease share a sentence yielded no new supported relation. Replacing the model with GPT-6.1 Sol gave the same F1 (0.555). Cost was USD 0.056 per abstract and USD 0.44 per full text.

**Conclusion.** A written decision card turns a general-purpose LLM into a precise, auditable gene–disease extractor that complements supervised tools. Its recall gap mainly reflects a stricter evidence standard than benchmark annotators apply. The status labels let users adjust this trade-off.

**Keywords:** relation extraction; gene–disease association; large language models; biocuration; evidence traceability; benchmark evaluation

## Statement of significance

|  |  |
| --- | --- |
| **Problem** | Curators need gene–disease relations with evidence, status and source. Extraction tools return only positive pairs, mostly from abstracts. |
| **What is already known** | Supervised extractors reach high F1 on in-domain benchmarks such as BioRED. Zero-shot LLMs have been reported to lag in recall and consistency. |
| **What this paper adds** | A frozen decision card that gives an LLM high precision, checkable evidence and four-way statuses on three benchmarks and on full text. Evidence that much of the measured gap reflects differing annotation standards. An operating point that recovers recall on held-out data. |

\[Format to verify on the JBI guide for authors: the significance statement's exact form, Highlights, and the graphical abstract file.\]

## 1. Introduction

Gene–disease associations underpin variant interpretation, target discovery and knowledge bases such as DisGeNET and CTD. Most of this knowledge is still published as free text, and manual curation does not scale with the literature.

Automatic relation extraction has improved steadily on benchmarks such as BioRED. Its output, however, is a set of positive pairs. Three things a curator needs are usually missing:

- **Evidence.** Which sentences support the pair, so the claim can be checked in seconds.
- **Status.** A paper can support a relation, hedge it, or state that no association was found. Collapsing these into "related / not related" discards negative and speculative findings.
- **Source.** Whether the relation is the paper's own result or a citation of prior work. These carry different weight in curation.

Most tools also work on abstracts. In our 100-paper full-text corpus, 90% of the supported relations had evidence only outside the abstract.

Large language models (LLMs) can read full papers and follow written instructions. Free-form prompting, though, produces outputs that are hard to verify and vary between runs. We therefore wrote the annotation guideline as a compact decision card, asked for a fixed line-based output, and let a deterministic validator reject any answer that cites text not in the paper.

We ask five research questions, answered in order in Section 4:

- **RQ1.** Is the output precise, and do its statuses agree with graded gold labels?
- **RQ2.** How does it compare with a supervised tool (PubTator3) on abstracts and full text?
- **RQ3.** Where is recall lost?
- **RQ4.** Can recall be recovered without losing precision?
- **RQ5.** Do the results depend on the model, and what does the method cost?

Our contributions are:

1. **A traceable, status-aware extraction method.** A single request per paper produces four-way statuses, evidence spans and source labels. These are checked by script, at USD 0.44 per full-text paper.
2. **A frozen evaluation on three benchmarks with different annotation standards** (BioRED, EU-ADR, RENET2), with bootstrap confidence intervals and a comparison with PubTator3.
3. **An analysis of the recall gap.** Two interventions that forced the model to judge more pairs did not raise recall. The gap comes from a stricter evidence standard than the annotators', and choosing an operating point on development data recovers most of it.
4. **Evidence that the method is not tied to one model.** GPT-6.1 Sol with the same card performed within the confidence interval of Claude.

## 2. Related work

**Supervised biomedical relation extraction.** Domain-pretrained encoders such as BioBERT and PubMedBERT, fine-tuned on annotated corpora, are the standard approach. BioREx improved BioRED results by pooling heterogeneous corpora. These models predict a relation type for each entity pair and are trained mostly on abstracts.

**Literature-scale systems.** PubTator3 combines entity recognition, normalization and relation extraction over PubMed and PMC. Its relation model is trained on BioRED. It is the most widely used public resource for this task and our main comparator.

**Gene–disease benchmarks.** BioRED annotates eight relation types between concept pairs in 600 abstracts and marks each relation as novel or not. EU-ADR has gene–disease abstracts labelled by several annotators as positive, speculative or negative. RENET2 provides document-level gene–disease labels on full texts, with negatives assigned automatically. The three corpora use different notions of what counts as a relation, which we examine in Section 5.

**LLMs for biomedical relation extraction.** Several benchmark studies found that zero- and few-shot LLMs lag behind fine-tuned models on relation extraction, mostly in recall and output consistency \[cite: Chen et al. 2025; others to add\]. Most of these studies use short free-form prompts and score only positive predictions. Our work differs in three ways: a written decision procedure instead of a free prompt; machine-checked evidence; and evaluation of the uncertain and negative statuses that existing work does not score.

\[TODO: complete with a literature search, focusing on 2024–2026 LLM relation-extraction and curation-assistant papers.\]

## 3. Materials and methods

### 3.1 Task definition

The input is one paper as text. The output has two parts. The first is a set of gene and disease entities, each with the surface forms that occur verbatim in the text. The second is a status for every gene × disease pair:

| Status | Definition |
| --- | --- |
| supported | The text reports a finding or an explicit attribution linking the pair (not an aim or a hypothesis), and the link is readable in the text. |
| uncertain | There is potential evidence, but hedging, scope, identity, co-reference, presupposition or a conflict prevents a decision. A reason code is required. |
| explicit\_negative | The text explicitly reports no association, or an opposite result, for this pair on a stated question. |
| not\_found | Everything else, including co-occurrence only. It does not mean the pair is medically unrelated. |

Supported pairs also carry a relation type (causal, correlation or association) and a source label: this study, background, both, or unclear. Symptoms and general phenotypes are recorded as auxiliary entities, not as disease endpoints. This choice affects evaluation (Section 3.7).

### 3.2 Decision card

The decision rules began as a long annotation guideline that we wrote and refined on development papers before any benchmark run. We condensed it into a one-page decision card of about 1,000 words, plus an output format of about 600 words. The card covers entity typing and merging, the four statuses, relation types and sources, and a list of key judgments. Examples: co-occurrence is never a relation; the authors' own speculation is uncertain (hedged\_claim); a variant detected without an attribution is not a relation; statistics apply to a pair only when they test that gene against that disease outcome.

The card was frozen (variant V1) before the benchmark experiments. It was not edited for any benchmark.

### 3.3 Single-request pipeline

1. **Packing.** The paper is split into blocks and sentences with stable IDs (e.g. `b0012.s3`), and the reference list is removed. The card and format go into a cached system prompt; the paper is the user message.
2. **Generation.** One request to Claude Opus 5.5 (reasoning effort: medium). The model returns pipe-separated lines for entities (E), evidence (EV), pairs (P), study findings (F), conflicts (C) and rule gaps (R). Evidence is cited by sentence ID only, never as copied text.
3. **Expansion.** A deterministic script locates every surface form in the text, builds the mention table and the full gene × disease matrix. Pairs the model did not list default to not\_found.
4. **Validation.** The script checks that every surface form occurs verbatim, every sentence ID exists, pair endpoints are primary entities, and uncertain pairs carry legal reason codes. If a check fails, one repair request is sent with the list of problems.

On the 100-paper corpus, 69 papers passed on the first request and 31 needed one repair. All 100 passed validation, and all repairs concerned format, not content.

### 3.4 Design checks before freezing

On a fixed, stratified set of 12 full-text papers that was never used to edit rules, we compared three variants:

- **V1 versus V2 (the full guideline).** The card did not lose quality: pair-status agreement was 0.976, and the first request was about 12% cheaper.
- **V1 versus V3 (low reasoning effort).** Cost fell by 24%, but about 10% of genes, diseases and supported relations were lost. We kept medium effort.

\[TODO: add a minimal-prompt baseline without the card to quantify the card's contribution.\]

### 3.5 Benchmarks

| Benchmark | Text | Documents used | Gold gene–disease relations | Labels beyond "related" |
| --- | --- | --- | --- | --- |
| BioRED | PubMed abstracts | All 419 abstracts with ≥1 gene–disease relation (Train 275 / Dev 71 / Test 73); 50-abstract Test sample for the PubTator3 comparison | 1,633 | Novel / not novel |
| EU-ADR | PubMed abstracts | Target–Disorder subset, 100 abstracts | 134 consensus pairs: 122 positive (PA), 9 speculative (SA), 3 negative (NA) | Positive / speculative / negative |
| RENET2 | PMC full text (title, abstract and early body, as released) | Random sample of 40 articles (seed 20261028) | 181 associated; 83 non-associated; 1 ambiguous | Non-associated labels are tool-assigned (silver) |

A BioRED relation counts when one end is a gene or gene product and the other a disease or phenotypic feature, whatever the relation type. Three RENET2 associated pairs have an entity that does not occur in the released text; they stay in the denominator.

### 3.6 Matching and metrics

The evaluation unit is one (gene concept, disease concept) pair per document. A predicted entity is aligned with a gold concept when any of its mentions overlaps a gold mention, by character span, within the same text block. Two consequences follow. Spelling variants align without normalization. A predicted entity that overlaps no gold mention cannot match.

We report precision, recall and F1. Precision and F1 count predicted pairs; recall counts gold pairs. 95% confidence intervals come from a bootstrap over documents (2,000 resamples, seed 20261028), because pairs in one document are not independent.

The same code scores all three benchmarks and both systems.

### 3.7 Operating points and views

The method's statuses allow several operating points from one run:

- **Strict.** Only supported pairs count as predicted relations. This is the default.
- **Supported + uncertain.** All uncertain pairs count too.
- **Supported + hedged/scope.** Uncertain pairs count only when their reason codes are hedged\_claim and/or scope. This rule was chosen on BioRED Train+Dev only (Section 4.4) and tested on Test.

Separately, the **scope-adjusted view** removes from the recall denominator the gold pairs whose disease our rules record as a symptom or phenotype rather than a disease. It separates differences in task definition from actual misses. We report it next to the strict view, never instead of it.

### 3.8 Comparators

- **PubTator3.** Relations from the public API. Its relations come from abstracts only, including for the RENET2 full texts. It is trained on BioRED, so BioRED is in-domain for it.
- **GPT-6.1 Sol.** The same frozen card, format, text and validator, run via the Codex CLI. This tests whether the results depend on the model.

\[TODO: add an open-weight LLM (e.g. Llama or Qwen) with the same card; quote published supervised BioRED results (e.g. BioREx) as reference rows.\]

## 4. Results

Across three benchmarks, the frozen method matched or exceeded PubTator3's precision on abstracts and found more gold relations on full text. PubTator3 led on its in-domain benchmark, BioRED.

**Table 1.** Main results, strict view unless stated. 95% bootstrap CIs are shown for F1, and for P where discussed.

| Benchmark (documents) | System | Precision | Recall | F1 \[95% CI\] |
| --- | --- | --- | --- | --- |
| BioRED, all (419) | Ours | 0.894 \[0.855, 0.931\] | 0.430 | 0.581 \[0.538, 0.625\] |
| BioRED, all (419) | Ours, supported + uncertain | 0.814 | 0.577 | 0.676 \[0.636, 0.714\] |
| BioRED Test (73) | Ours | 0.853 | 0.397 | 0.542 \[0.444, 0.644\] |
| BioRED Test (73) | Ours, supported + hedged/scope | 0.846 | 0.498 | 0.627 |
| BioRED Test sample (50) | Ours | 0.835 | 0.412 | 0.551 \[0.440, 0.665\] |
| BioRED Test sample (50) | Ours with GPT-6.1 Sol | 0.853 | 0.412 | 0.555 \[0.47, 0.64\] |
| BioRED Test sample (50) | PubTator3 | 0.827 | 0.647 | 0.726 \[0.609, 0.825\] |
| EU-ADR, PA (100) | Ours | 0.469 \[0.350, 0.600\] | 0.549 | 0.506 \[0.403, 0.602\] |
| EU-ADR, PA (100) | PubTator3 | 0.408 \[0.326, 0.498\] | 0.754 | 0.529 \[0.447, 0.612\] |
| RENET2 full text (40) | Ours | 0.318 \[0.206, 0.470\] | 0.370 | 0.342 \[0.258, 0.421\] |
| RENET2 full text (40) | Ours, supported + uncertain | 0.312 | 0.464 | 0.373 |
| RENET2 full text (40) | PubTator3 | 0.623 \[0.511, 0.750\] | 0.254 | 0.361 \[0.243, 0.475\] |

### 4.1 RQ1: Precision and agreement with graded labels

On all 419 BioRED abstracts, 89% of supported pairs were gold relations. Results were stable across splits: F1 was 0.584 on Train, 0.608 on Dev and 0.542 on Test. The scope-adjusted view raised recall to 0.468 (F1 0.614).

For matched relations, our source label agreed with BioRED's novelty label in 526 of 703 cases (75%).

EU-ADR's graded labels test the statuses that BioRED cannot:

- **Negative pairs (NA).** All 3 were labelled explicit\_negative by our method. PubTator3 predicted one of them as a relation.
- **Positive pairs (PA, 122).** We labelled 67 supported, 16 uncertain, 10 not\_found and 4 explicit\_negative; for 25, an entity was not recorded.
- **Counting uncertain pairs.** Recall rose to 0.680 at precision 0.414.

On RENET2, measured precision was low (Table 1), but the benchmark's labels explain most of it. Of our 152 supported pairs outside the gold set:

- 105 had never been labelled, because no tool had proposed them;
- 45 involved an entity that is not a RENET2 concept;
- 2 carried RENET2's non-associated label.

Of the 152, 136 were pairs we labelled as background. Precision was 0.53 for relations we labelled this study and 0.28 for background relations. RENET2 annotates the article's main findings, so its gold set omits most cited knowledge.

### 4.2 RQ2: Comparison with PubTator3

On the 50-abstract BioRED Test sample, PubTator3 had similar precision and much higher recall. The two systems were complementary. Of 238 gold relations, both found 78, only PubTator3 found 76, only ours found 20, and 64 were missed by both. Together they covered 73%.

On EU-ADR, F1 was comparable (0.506 vs 0.529, overlapping intervals). The systems sat at different points of the trade-off: ours was higher on precision, PubTator3 on recall.

On RENET2 full text, our method found more gold relations than PubTator3 (recall 0.370 vs 0.254). PubTator3 extracts relations from abstracts only.

### 4.3 RQ3: Where recall is lost

Most missed BioRED relations were pairs the model read and judged, not pairs it overlooked. Raising recall worked only by choosing which uncertain pairs to count, not by asking the model to judge more pairs.

**Table 2.** The 930 gold relations missed on all 419 abstracts (strict view).

| Category | Pairs | Share |
| --- | --- | --- |
| Pair judged, but not supported: not\_found 295, uncertain 240, explicit\_negative 12 | 547 | 59% |
| Disease end recorded as a symptom or phenotype | 131 | 14% |
| Disease not recorded as an entity | 159 | 17% |
| Gene not recorded as an entity | 93 | 10% |

The 87 supported pairs counted as false positives fell into three groups:

- **60:** BioRED annotates both concepts but no relation;
- **23:** our disease end is not a BioRED disease concept;
- **4:** our gene is not a BioRED gene concept.

Among the unrecorded entities on Train+Dev, two patterns dominate:

- **Gene families and complexes,** such as NF-κB, MAPK, Wnt and NMDA receptors. The card excludes them as single-gene endpoints by design.
- **Generic disease terms,** such as cancer, tumor and inflammation.

If every such pair had been recorded and judged supported, recall would rise by at most 4.0 and 6.6 points respectively.

### 4.4 RQ4: Recovering recall

**What worked: an operating point from reason codes.**

On Train+Dev, the share of uncertain pairs that were gold relations depended strongly on the reason code:

| Reason code | Uncertain pairs that are gold relations |
| --- | --- |
| hedged\_claim only | 82% (of 99) |
| hedged\_claim + scope | 75% (of 32) |
| scope only | 62% (of 113) |
| presupposed\_only | 38% |
| identity | 6% |

We therefore also count uncertain pairs whose reasons are only hedged\_claim and/or scope. On the held-out Test split, F1 rose from 0.542 to 0.627: recall went from 0.397 to 0.498 and precision from 0.853 to 0.846. This needs no extra model call. The low rate for identity shows that the model's doubts about entity identity were well founded.

**What did not help: forcing more pairs to be judged.**

Before the second pass, we checked the gold relations the model never judged on Train+Dev. Of 155, 117 (75%) had the gene and disease in the same sentence. This suggested an attention failure, so we tested two fixes on Dev (71 abstracts).

**V4: a coverage rule.** The format required a judgment for every gene–disease pair co-mentioned in a sentence. Recall fell from 0.454 to 0.403 and precision rose from 0.922 to 0.947. Supported pairs fell from 153 to 133, and cost rose by 16%.

**Second pass.** A script listed the unjudged co-mentioned pairs (97 in 18 abstracts) and a second request asked the model to judge each one. The result: 92 stayed not\_found, 4 became uncertain, 1 became explicit\_negative, and none became supported. Metrics were unchanged, at an extra cost of USD 0.64.

Both results point the same way. When asked directly, the model still judged that the text does not support these relations. The remaining recall gap is a difference in evidence standard between the decision card and the BioRED annotators. Closing it would mean changing the standard itself, which we do not do without a manual adjudication of the disputed pairs.

### 4.5 RQ5: Model independence, full text and cost

With GPT-6.1 Sol and the same card, F1 on the BioRED sample was 0.555 vs 0.551. On 11 full-text papers, pair-status agreement with Claude was 0.986.

The mean cost (list price, repairs included) was:

- USD 0.056 per BioRED abstract;
- USD 4.75 for the 100 EU-ADR abstracts;
- USD 6.36 for the 40 RENET2 articles;
- USD 0.44 per full-text paper in the 100-paper corpus, with a mean model time of 78 s.

On 100 heterogeneous PMC papers, the method produced 972 supported relations, 451 uncertain pairs and 47 explicit negatives. PubTator3 produced 198 relations. Of our supported relations, 875 (90%) had evidence only outside the abstract. Twenty-five papers had no supported relation: 8 named no gene, 8 named no disease, and 9 contained only co-occurrence or hedged statements.

\[TODO: annotate 15–20 of these papers to measure full-text precision and recall.\]

## 5. Discussion

**One method, three different scores.** The same frozen output scored F1 0.58 on BioRED, 0.51 on EU-ADR and 0.34 on RENET2. The method did not change between benchmarks, so the spread mostly reflects what each benchmark counts as a relation:

- **BioRED** annotates every relation stated in an abstract, including loosely phrased ones. It treats phenotypes and generic terms such as "cancer" as diseases.
- **EU-ADR** keeps only relations on which at least two annotators agreed. Ten of our 37 EU-ADR extras on gold concepts had been marked by a single annotator.
- **RENET2** labels only pairs that its tools proposed, and its negatives were never checked by hand.

A precise extractor is therefore penalized differently by each benchmark. On EU-ADR and RENET2 the measured precision is a lower bound. Reporting a single F1 hides this.

**Precision and contradiction.** Across benchmarks, our method rarely contradicted an explicit gold label:

- EU-ADR: 0 of 3 negative pairs predicted as relations;
- RENET2: 2 of 223 supported pairs carried the non-associated label.

Most disagreements are unlabelled pairs, not contradictions. For curation, where a reviewer checks the cited sentence, this is the property that matters.

**Statuses as a control.** Statuses make one run usable at several operating points. A curation pipeline can take supported pairs for automatic import and route hedged or scope-limited pairs to review. On BioRED Test, this second group added 10 recall points at almost no precision cost. Binary extractors cannot offer this without retraining.

**Complementarity with supervised tools.** PubTator3 is stronger on recall within its training domain; our method is stronger on full text, sources and negatives. Their union covered 73% of BioRED sample relations, against 65% for PubTator3 alone. A practical system would combine them: PubTator3 to propose pairs, and the decision card to judge each pair with evidence.

**A frozen card instead of training.** The card is human-readable and versioned, and it was not tuned on any benchmark. Moving to another relation type (e.g. chemical–disease) means editing a page of rules, not annotating a training corpus. The same card produced near-identical results on a second model, so the behaviour is carried by the rules rather than by one model's quirks.

### 5.1 Limitations

- **No adjudication yet.** The claim that many "false positives" are true relations is based on the structure of each benchmark's labels, not on a manual review.
- **Small samples.** RENET2 used 40 articles and the PubTator3 comparison on BioRED used 50 abstracts. Several differences are inside the confidence intervals.
- **No normalization.** Entities are not mapped to NCBI Gene or MeSH identifiers, so outputs cannot yet be merged across papers by identifier. This also limits comparison with knowledge bases.
- **Closed models.** Claude Opus 5.5 and GPT-6.1 Sol are proprietary and versioned by their providers, so exact reproduction may not be possible later. We release all prompts, raw outputs and scoring code.
- **Possible contamination.** The benchmark abstracts were public before the models were trained. We cannot rule out that the models saw them. PubTator3 was trained on BioRED itself.
- **Single runs.** Each configuration was run once. The V1/V2/V3 agreement of 0.976–0.985 suggests low run-to-run variation, but this was not measured directly.
- **Full-text quality is unmeasured.** The 100-paper corpus has no gold labels, and RENET2's released texts are truncated.

## 6. Conclusions

A frozen, one-page decision card enabled a general-purpose LLM to extract gene–disease relations from full papers with checkable evidence, four statuses and source labels. The cost was USD 0.44 per paper.

Across three benchmarks with different annotation standards, the method was consistently precise and rarely contradicted an explicit gold label. Its recall gap persisted when the model was asked directly about missed pairs, so it reflects a stricter evidence standard rather than missed text. An operating point chosen on development data recovered 10 recall points on held-out data.

The method complements supervised tools such as PubTator3. Future work will add manual adjudication of disputed pairs, entity normalization, and a hybrid in which a supervised tool proposes pairs and the decision card judges them.

## Declarations

- **CRediT authorship contribution statement:** \[to be agreed with co-authors\]
- **Declaration of competing interest:** \[to complete\]
- **Data and code availability:** Code, decision card, prompts, raw model outputs and scoring scripts will be released at \[repository URL\]. EU-ADR and RENET2 texts are not redistributed; download scripts are provided.
- **Declaration of generative AI use:** \[Required by the publisher. Describe the use of AI tools in drafting this manuscript; check the current Elsevier wording.\]
- **Funding and acknowledgements:** \[to complete\]

## Author notes (remove before submission)

The draft follows the JBI structure: structured abstract, significance statement, research questions, Materials and methods, Results by question, Discussion with limitations, Conclusions, Declarations. Items 1–3 are needed for the central claims; the rest strengthen the paper. Target journals: *Journal of Biomedical Informatics* or *Database* (Oxford); fallback *BMC Bioinformatics*.

- [ ] **1. Manual adjudication.** Two annotators independently review the disputed pairs (BioRED 87, EU-ADR 67, RENET2 152) against the cited sentences. Report Cohen's κ and adjusted precision. Also review a sample of missed BioRED pairs judged not\_found or uncertain. This turns the "evidence standard" argument from inference into measurement.
- [ ] **2. Baselines and ablation.**
  - A minimal prompt without the card, to show what the card adds.
  - An open-weight model with the card.
  - Published supervised BioRED results as reference rows.
- [ ] **3. Full-text gold.** Annotate 15–20 papers from the 100-paper corpus. Run the full RENET2 test set (about USD 80 at current cost).
- [ ] **4. Statistics.** Paired bootstrap tests for system differences, and repeated runs on a subset to measure run-to-run variance.
- [ ] **5. Normalization.** Map entities to NCBI Gene and MeSH, and check supported relations against DisGeNET and CTD as an external plausibility check.
- [ ] **6. Figures.**
  - Graphical abstract (required by JBI, separate file) and a pipeline diagram.
  - Precision–recall plot of the operating points on all benchmarks.
  - Figure 1: one paper's output with evidence highlighting, as BioREx opens with an example.
  - Bipartite graph of the 100-paper corpus.
- [ ] **7. Release.** Code, card, prompts and raw outputs. EU-ADR and RENET2 texts are not redistributed; provide download scripts.
- [ ] **8. Authorship and affiliations** with Dr. Wei's group; use of the 100-paper task set.

## References

Written from memory and not yet checked: confirm authors, years and venues before submission.

1. Luo L, Lai PT, Wei CH, Arighi CN, Lu Z. BioRED: a rich biomedical relation extraction dataset. *Briefings in Bioinformatics*, 2022.
2. Wei CH, Allot A, Lai PT, et al. PubTator 3.0: an AI-powered literature resource for unlocking biomedical knowledge. *Nucleic Acids Research*, 2024.
3. van Mulligen EM, Fourrier-Reglat A, Gurwitz D, et al. The EU-ADR corpus: annotated drugs, diseases, targets, and their relationships. *Journal of Biomedical Informatics*, 2012.
4. Su J, Wu Y, Ting HF, Lam TW, Luo R. RENET2: high-performance full-text gene–disease relation extraction with iterative training data expansion. *NAR Genomics and Bioinformatics*, 2021.
5. Lai PT, Wei CH, Luo L, Chen Q, Lu Z. BioREx: improving biomedical relation extraction by leveraging heterogeneous datasets. *Journal of Biomedical Informatics*, 2023.
6. Lee J, Yoon W, Kim S, et al. BioBERT: a pre-trained biomedical language representation model for biomedical text mining. *Bioinformatics*, 2020.
7. Gu Y, Tinn R, Cheng H, et al. Domain-specific language model pretraining for biomedical natural language processing. *ACM Transactions on Computing for Healthcare*, 2021.
8. Chen Q, et al. Benchmarking large language models for biomedical natural language processing applications and recommendations. *Nature Communications*, 2025.
9. Piñero J, et al. The DisGeNET knowledge platform for disease genomics. *Nucleic Acids Research*, 2020.
10. Davis AP, et al. Comparative Toxicogenomics Database (CTD): update. *Nucleic Acids Research* (latest update to be chosen).
11. Efron B, Tibshirani RJ. *An Introduction to the Bootstrap*. Chapman & Hall, 1993.
