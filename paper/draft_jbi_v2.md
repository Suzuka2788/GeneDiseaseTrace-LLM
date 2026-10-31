# Evidence-traceable, status-aware gene–disease relation extraction with a large language model: a multi-benchmark evaluation

Oct 30, 2026 · @zeqian tong

Draft for discussion with Dr. Zhi Wei. All numbers come from the project's evaluation files; items marked \[TODO\] still need experiments.

## Abstract

**Objective.** We developed and evaluated a zero-shot method that extracts gene–disease relations from biomedical papers. Each prediction includes sentence-level evidence, a four-way status (supported, uncertain, explicit negative, not found), and a source label (this study or background).

**Methods.** A large language model (Claude Opus 5.5) reads each paper in a single request and follows a frozen one-page decision card. A deterministic validator checks every cited span against the source text. Without benchmark-specific tuning, we evaluated the method on BioRED (419 abstracts), EU-ADR (100 abstracts), and a 40-article full-text sample of RENET2. Pairs were matched per document, confidence intervals were bootstrapped, and PubTator3 served as the comparator.

**Results.** On BioRED, precision was 0.894 (95% CI 0.855–0.931) and recall was 0.430. An operating point chosen on Train+Dev raised held-out Test F1 from 0.542 to 0.627 with precision unchanged. PubTator3, which is trained on BioRED, scored higher on a 50-abstract test sample (F1 0.726 vs 0.551). Together, the two systems recovered 73% of gold relations. On EU-ADR, F1 was comparable (0.506 vs 0.529), and all three negative gold pairs were labelled explicit negative. On RENET2 full text, our recall exceeded PubTator3's (0.370 vs 0.254), and only 2 of 223 supported pairs contradicted a gold label. Re-querying 97 unjudged pairs whose gene and disease share a sentence yielded no new supported relation. Replacing the model with GPT-6.1 Sol gave the same F1 (0.555). Cost was USD 0.056 per abstract and USD 0.44 per full text.

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

Gene–disease associations underpin variant interpretation, target discovery, and knowledge bases such as DisGeNET [9] and CTD [10]. Most of this knowledge is still published as free text, and manual curation does not scale with the literature.

Automatic relation extraction has improved steadily on benchmarks such as BioRED [1]. Its output, however, is a set of positive pairs. Three elements that a curator needs are usually missing:

- **Evidence.** Curators need the supporting sentences so that each claim can be checked in seconds.
- **Status.** A paper can support a relation, hedge it, or state that no association was found. Collapsing these cases into "related / not related" discards negative and speculative findings.
- **Source.** Curators must distinguish a paper's own result from a citation of prior work. These two sources carry different weight in curation.

Most tools also work only on abstracts. In our 100-paper full-text corpus, 90% of the supported relations had evidence only outside the abstract.

Large language models (LLMs) can read full papers and follow written instructions. Free-form prompting, however, produces outputs that are hard to verify and vary between runs [8,12]. We therefore wrote the annotation guideline as a compact decision card and required a fixed line-based output format. A deterministic validator rejects any answer that cites text not present in the paper (Figure 1, Figure 2).

We ask five research questions, which are answered in order in Section 4:

- **RQ1.** Is the output precise, and do its statuses agree with graded gold labels?
- **RQ2.** How does it compare with a supervised tool (PubTator3 [2]) on abstracts and full text?
- **RQ3.** Where is recall lost?
- **RQ4.** Can recall be recovered without losing precision?
- **RQ5.** Do the results depend on the model, and what does the method cost?

Our contributions are fourfold:

1. **A traceable, status-aware extraction method.** A single request per paper produces four-way statuses, evidence spans, and source labels. These outputs are checked by script at USD 0.44 per full-text paper.
2. **A frozen evaluation on three benchmarks with different annotation standards.** We evaluate on BioRED [1], EU-ADR [3], and RENET2 [4] with bootstrap confidence intervals and compare against PubTator3 [2].
3. **An analysis of the recall gap.** Two interventions that forced the model to judge more pairs did not raise recall. The gap stems from a stricter evidence standard than the annotators used, and an operating point chosen on development data recovers most of it (Figure 3).
4. **Evidence that the method is not tied to one model.** GPT-6.1 Sol with the same card performed within the confidence interval of Claude.

## 2. Related work

**Supervised biomedical relation extraction.** Domain-pretrained encoders such as BioBERT [6] and PubMedBERT [7], fine-tuned on annotated corpora, remain the standard approach. BioREx [5] improved BioRED results by pooling heterogeneous corpora during training, and subsequent work added relation directionality [16]. These models predict a relation label for each entity pair and are trained mostly on abstracts.

**Literature-scale systems.** PubTator3 [2] combines entity recognition, normalization, and relation extraction over PubMed and PMC. Its relation model is trained on BioRED [1] and deployed with BioREx [5]. It is the most widely used public resource for this task and serves as our main comparator.

**Gene–disease benchmarks.** BioRED [1] annotates eight relation types between concept pairs in 600 abstracts and marks whether each relation is a new finding (`Novel`) or background knowledge. EU-ADR [3] provides gene–disease abstracts labelled by multiple annotators as positive, speculative, or negative. RENET2 [4] provides document-level gene–disease labels on full texts, with negative labels assigned automatically by tools. These three corpora apply different criteria for what counts as a relation, which we examine in Section 5.

**LLMs for biomedical relation extraction.** Recent benchmarks show that zero- and few-shot LLMs lag behind fine-tuned encoders on biomedical relation extraction [8,13,14,15]. In the BioCreative VIII BioRED track, community systems relied primarily on fine-tuned encoders, while direct LLM prompting struggled with recall and schema adherence [13]. End-to-end zero-shot evaluations on BioRED [14] and across 61 biomedical triplet datasets [15] found that general-purpose LLMs often miss implicit relations or output unaligned entity spans. Most prior studies use short prompts and score only binary or typed positive predictions. Our work differs in three ways: a written decision procedure instead of a brief prompt, machine-checked evidence spans, and explicit scoring of uncertain and negative statuses.

**LLM-assisted biocuration.** To make LLM outputs usable for database curation, recent tools combine prompting with ontologies or external APIs. SPIRES (OntoGPT) [17] uses zero-shot schema templates to populate structured knowledge bases and ground terms to ontologies. DRAGON-AI [18] combines retrieval-augmented generation with ontology curation workflows. Similarly, PubTator3 [2] pairs precomputed entity and relation index tables with LLM queries to reduce hallucinated citations. Unlike retrieval wrappers that depend on abstract-level indices, our method reads the full text directly and enforces verbatim span verification through a deterministic post-processor.

**Evaluation with incomplete gold standards.** Evaluating generative extractors against fixed corpora is difficult because valid relations are often unannotated in the gold standard [12,19]. Wadhwa et al. [12] showed through manual review that many apparent LLM false positives on standard relation extraction datasets are valid relations missed by annotators. Fan et al. [19] formalized this issue by separating unannotated valid extractions from factual errors. In biomedical corpora, incomplete consensus is also common. For example, crowdsourced re-annotation of the EU-ADR corpus showed that single-annotator relations and guideline ambiguities account for many disagreements [20]. Similarly, semi-automated full-text corpora such as RENET2 [4] only label candidate pairs proposed by baseline tools. We address this issue by auditing contradictions against explicit negative labels separately from unlabelled extra predictions.

## 3. Materials and methods

### 3.1 Task definition

The input is one paper formatted as text. The output has two parts. The first part is a set of gene and disease entities, each linked to the surface forms that occur verbatim in the text. The second part assigns one of four statuses to every gene × disease pair:

| Status | Definition |
| --- | --- |
| supported | The text reports a finding or an explicit attribution linking the pair (not an aim or a hypothesis), and the link is readable in the text. |
| uncertain | There is potential evidence, but hedging, scope, identity, co-reference, presupposition or a conflict prevents a decision. A reason code is required. |
| explicit\_negative | The text explicitly reports no association, or an opposite result, for this pair on a stated question. |
| not\_found | Everything else, including co-occurrence only. It does not mean the pair is medically unrelated. |

Supported pairs also carry a relation type (causal, correlation, or association) and a source label (this study, background, both, or unclear). Symptoms and general phenotypes are recorded as auxiliary entities rather than primary disease endpoints. This design choice affects benchmark evaluation (Section 3.7).

### 3.2 Decision card

The decision rules began as a detailed annotation guideline refined on development papers before any benchmark run. We condensed this guideline into a one-page decision card of about 1,000 words, paired with an output format specification of about 600 words. The card defines entity typing and merging, the four pair statuses, relation types, source labels, and key boundary judgments. For example, co-occurrence alone is never a relation, and the authors' own speculation is marked `uncertain` (`hedged_claim`). A genetic variant detected without disease attribution is not a relation. Statistical tests apply to a pair only when they test that specific gene against that disease outcome.

The decision card was frozen as variant V1 before the benchmark experiments. It was not edited for any benchmark.

### 3.3 Single-request pipeline

The extraction pipeline runs in four steps (Figure 2):

1. **Packing.** The paper is split into blocks and sentences with stable IDs (e.g. `b0012.s3`), and the reference list is removed. The decision card and format instructions are placed in a cached system prompt, while the paper text forms the user message.
2. **Generation.** We send one request per paper to Claude Opus 5.5 with medium reasoning effort and all tools disabled. The model returns pipe-separated lines for entities (`E`), evidence (`EV`), pairs (`P`), study findings (`F`), conflicts (`C`), and rule gaps (`R`). Evidence is cited by sentence ID only, never as copied text.
3. **Expansion.** A deterministic script locates every entity surface form in the source text and builds the mention table and full gene × disease matrix. Pairs that the model does not list default to `not_found`.
4. **Validation.** The validator checks that every surface form occurs verbatim, every sentence ID exists, pair endpoints are primary entities, and uncertain pairs carry valid reason codes. If any check fails, one repair request is sent with the error list.

On the 100-paper corpus, 69 papers passed on the first request and 31 needed one repair. All 100 papers passed validation, and all repairs fixed formatting rather than semantic content.

### 3.4 Design checks before freezing

We evaluated three variants on a fixed, stratified set of 12 full-text papers that were never used to edit the rules:

- **V1 versus V2 (the full guideline).** Condensing the guideline into the card did not reduce quality. Pair-status agreement was 0.976, and the first request was about 12% cheaper.
- **V1 versus V3 (low reasoning effort).** Low effort reduced cost by 24%, but lost about 10% of genes, diseases, and supported relations. We therefore kept medium reasoning effort.

\[TODO: add a minimal-prompt baseline without the card to quantify the card's contribution.\]

### 3.5 Benchmarks

| Benchmark | Text | Documents used | Gold gene–disease relations | Labels beyond "related" |
| --- | --- | --- | --- | --- |
| BioRED [1] | PubMed abstracts | All 419 abstracts with ≥1 gene–disease relation (Train 275 / Dev 71 / Test 73); 50-abstract Test sample for the PubTator3 comparison | 1,633 | Novel / not novel |
| EU-ADR [3] | PubMed abstracts | Target–Disorder subset, 100 abstracts | 134 consensus pairs: 122 positive (PA), 9 speculative (SA), 3 negative (NA) | Positive / speculative / negative |
| RENET2 [4] | PMC full text (title, abstract and early body, as released) | Random sample of 40 articles (seed 20261028) | 181 associated; 83 non-associated; 1 ambiguous | Non-associated labels are tool-assigned (silver) |

In BioRED, a relation counts when one endpoint is a gene or gene product and the other is a disease or phenotypic feature, regardless of the specific relation subtype. In RENET2, three associated gold pairs involve an entity that does not occur in the released truncated text; we retain these three pairs in the recall denominator.

### 3.6 Matching and metrics

The evaluation unit is one (gene concept, disease concept) pair per document. A predicted entity aligns with a gold concept when any of its mentions overlaps a gold mention by character span within the same text block. This span-overlap rule has two consequences: spelling variants align without database normalization, and a predicted entity that overlaps no gold mention cannot match.

We report precision, recall, and F1. Precision and F1 use predicted pairs as the unit, whereas recall uses gold pairs. We compute 95% confidence intervals by bootstrapping over documents (2,000 resamples, seed 20261028) [11], because pairs within a document are not independent.

The same evaluation script scores all three benchmarks and all compared systems.

### 3.7 Operating points and views

The four-way status output supports multiple operating points from a single model run:

- **Strict.** Only `supported` pairs count as positive predictions. This is the default setting.
- **Supported + uncertain.** All `uncertain` pairs are also counted as positive predictions.
- **Supported + hedged/scope.** Uncertain pairs count as positive only when their reason codes are restricted to `hedged_claim` and/or `scope`. This rule was selected on BioRED Train+Dev (Section 4.4) and evaluated once on the held-out Test split.

Separately, the **scope-adjusted view** removes from the recall denominator gold pairs whose disease endpoint our rules classify as a symptom or phenotype. This view separates task-definition differences from missed relations. We report it alongside the strict view, never as a replacement.

### 3.8 Comparators

- **PubTator3 [2].** We retrieve relation predictions from the public API. Its relations come from abstracts only, even when queried on the RENET2 full texts. Because PubTator3's relation extractor is trained on BioRED, BioRED represents an in-domain evaluation for it.
- **GPT-6.1 Sol.** We run the same frozen card, output format, input text, and validator using GPT-6.1 Sol via the Codex CLI. This comparison tests whether performance depends on a single model family.

\[TODO: add an open-weight LLM (e.g. Llama or Qwen) with the same card; quote published supervised BioRED results (e.g. BioREx) as reference rows.\]

## 4. Results

Across the three benchmarks, the frozen method matched or exceeded PubTator3's precision on abstracts and recovered more gold relations on full text (Table 1). PubTator3 achieved higher recall and F1 on its in-domain benchmark, BioRED.

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

On all 419 BioRED abstracts, 89% of `supported` pairs matched gold relations. Performance was consistent across data splits: F1 was 0.584 on Train, 0.608 on Dev, and 0.542 on Test. Under the scope-adjusted view, recall rose to 0.468 and F1 reached 0.614.

Among the 703 matched gold relations, our source label (`this study` vs `background`) agreed with BioRED's `Novel` label in 526 cases (75%).

EU-ADR provides graded relation labels that test the non-positive statuses not present in BioRED:

- **Negative pairs (NA).** All 3 gold negative pairs were labelled `explicit_negative` by our method. PubTator3 predicted one of these three negative pairs as a positive relation.
- **Positive pairs (PA, 122).** Our method labelled 67 as `supported`, 16 as `uncertain`, 10 as `not_found`, and 4 as `explicit_negative`; for the remaining 25 pairs, one endpoint was not recorded as a primary entity.
- **Counting uncertain pairs.** Including `uncertain` pairs raised EU-ADR PA recall to 0.680 at a precision of 0.414.

On RENET2, measured precision was 0.318 (Table 1), which reflects the incomplete coverage of the benchmark's candidate-based labels. Among our 152 `supported` pairs outside the gold positive set:

- 105 involved two gold entities that were never labelled in RENET2 because no baseline tool had proposed the pair;
- 45 involved an entity that was not annotated as a RENET2 concept;
- 2 carried RENET2's silver `non-associated` label.

Of these 152 extra pairs, 136 were relations that our method labelled as `background`. Measured precision was 0.53 for pairs we labelled `this study` (or `both`), compared with 0.28 for pairs we labelled `background`. Because RENET2 was constructed around main study findings, its annotations omit most background knowledge stated in introductions.

### 4.2 RQ2: Comparison with PubTator3

On the 50-abstract BioRED Test sample, PubTator3 achieved similar precision (0.827 vs 0.835) and higher recall (0.647 vs 0.412). However, the two systems were complementary. Across the 238 gold relations, both systems found 78, only PubTator3 found 76, only our method found 20, and both missed 64. Combining the two systems recovered 174 relations (73%).

On EU-ADR, overall F1 was similar between our method and PubTator3 (0.506 vs 0.529, with overlapping confidence intervals). The two systems operated at different precision–recall trade-offs: our method had higher precision (0.469 vs 0.408), whereas PubTator3 had higher recall (0.754 vs 0.549).

On the 40 RENET2 full-text articles, our method achieved higher recall than PubTator3 (0.370 vs 0.254; 0.464 when counting `uncertain` pairs). PubTator3 extracts relations only from abstracts and therefore missed relations stated only in the article body.

### 4.3 RQ3: Where recall is lost

Most missed BioRED relations were pairs that the model identified and evaluated, rather than pairs it overlooked (Table 2). Consequently, recall could be increased by adjusting which `uncertain` pairs count as positive, but not by forcing the model to inspect additional pairs.

**Table 2.** The 930 gold relations missed on all 419 abstracts (strict view).

| Category | Pairs | Share |
| --- | --- | --- |
| Pair judged, but not supported: not\_found 295, uncertain 240, explicit\_negative 12 | 547 | 59% |
| Disease end recorded as a symptom or phenotype | 131 | 14% |
| Disease not recorded as an entity | 159 | 17% |
| Gene not recorded as an entity | 93 | 10% |

The 87 `supported` pairs counted as false positives on BioRED fell into three categories:

- **60 pairs:** BioRED annotated both concepts in the abstract but did not annotate a relation between them;
- **23 pairs:** our disease endpoint (such as a clinical outcome) was not annotated as a BioRED disease concept;
- **4 pairs:** our gene endpoint did not match a BioRED gene concept.

Among the unrecorded entities on Train+Dev, two systematic exclusions accounted for most misses:

- **Gene families and protein complexes,** such as NF-κB, MAPK, Wnt, and NMDA receptors, which the decision card excludes as single-gene endpoints.
- **Generic disease terms,** such as "cancer", "tumor", and "inflammation".

Even if every such entity were added and every resulting pair were judged `supported`, recall on Train+Dev would increase by at most 4.0 and 6.6 percentage points, respectively.

### 4.4 RQ4: Recovering recall

**What worked: selecting an operating point from reason codes.**

On BioRED Train+Dev, the proportion of `uncertain` pairs that matched gold relations varied sharply by reason code:

| Reason code | Uncertain pairs that are gold relations |
| --- | --- |
| hedged\_claim only | 82% (of 99) |
| hedged\_claim + scope | 75% (of 32) |
| scope only | 62% (of 113) |
| presupposed\_only | 38% |
| identity | 6% |

Based on this Train+Dev distribution, we defined an operating point that includes `supported` pairs plus `uncertain` pairs carrying only `hedged_claim` and/or `scope` reasons. On the held-out Test split (73 abstracts), this rule raised F1 from 0.542 to 0.627: recall increased from 0.397 to 0.498 while precision went from 0.853 to 0.846 (Figure 3). This gain requires no additional model calls. Conversely, the 6% gold rate for `identity` confirms that the model's entity-identity flags effectively filter out false matches.

**What did not help: forcing more pairs to be judged.**

On Train+Dev, we examined the 155 gold relations whose gene and disease were both extracted as entities but left unjudged (`not_found` by default). In 117 of these 155 pairs (75%), the gene and disease co-occurred in the same sentence. To test whether the model simply overlooked these co-mentions, we ran two experiments on the Dev split (71 abstracts):

- **Variant V4 (coverage rule).** We modified the output format to require an explicit `P` line for every gene–disease pair co-mentioned in a sentence. On Dev, recall fell from 0.454 to 0.403 and precision rose from 0.922 to 0.947. The number of `supported` pairs dropped from 153 to 133, and API cost increased by 16%.
- **Second pass (`second_pass.py`).** Starting from the frozen V1 outputs, a script identified all 97 unjudged same-sentence pairs across 18 Dev abstracts and sent a second request asking the model to judge each pair. Of the 97 pairs, 92 remained `not_found`, 4 became `uncertain`, 1 became `explicit_negative`, and 0 became `supported`. Precision, recall, and F1 were completely unchanged at an additional cost of USD 0.64.

Both experiments support the same conclusion. Even when prompted to evaluate each co-occurring pair directly, the model judged that the text did not meet the decision card's criteria for a `supported` relation. The remaining recall gap therefore reflects a stricter evidence threshold than BioRED annotators used, rather than an attention failure. Lowering that threshold would require changing the decision rules, which should wait for manual adjudication of the disputed pairs.

### 4.5 RQ5: Model independence, full text and cost

Replacing Claude Opus 5.5 with GPT-6.1 Sol under the same frozen card yielded an F1 of 0.555 (vs 0.551 for Claude) on the 50-abstract BioRED sample. On the 11 full-text benchmark papers that passed validation on both models, pair-status agreement between GPT-6.1 Sol and Claude Opus 5.5 was 0.986.

At list API prices (including repair requests), the mean cost was:

- USD 0.056 per BioRED abstract;
- USD 4.75 total for the 100 EU-ADR abstracts;
- USD 6.36 total for the 40 RENET2 full-text articles;
- USD 0.44 per full-text paper across the 100-paper PMC corpus, with a mean model runtime of 78 s.

Across the 100 heterogeneous PMC full-text papers, our method extracted 972 `supported` relations, 451 `uncertain` pairs, and 47 `explicit_negative` pairs, whereas PubTator3 reported 198 relations. Of our 972 `supported` relations, 875 (90%) were supported only by sentences outside the abstract. Twenty-five papers yielded zero `supported` relations: 8 contained no gene mentions, 8 contained no disease mentions, and 9 contained only co-occurrences, diagnostic panel listings, or speculative statements.

\[TODO: annotate 15–20 of these papers to measure full-text precision and recall.\]

## 5. Discussion

**One method, three different scores.** Running the same frozen pipeline produced strict F1 scores of 0.58 on BioRED, 0.51 on EU-ADR, and 0.34 on RENET2. Because no rule or prompt was changed across benchmarks, these differences reflect how each benchmark defines and annotates a relation:

- **BioRED [1]** annotates relations stated in abstracts, including hedged associations, and groups symptoms, phenotypes, and broad terms such as "cancer" under its disease category.
- **EU-ADR [3]** retains only consensus relations endorsed by at least two annotators. Ten of our 37 extra predictions involving EU-ADR gold concepts had in fact been marked by a single annotator.
- **RENET2 [4]** labels only candidate pairs proposed by its baseline text-mining tools, and its negative labels are assigned automatically without manual review.

A precision-oriented extractor is penalized differently by each annotation protocol. On EU-ADR and RENET2, measured precision is therefore a lower bound [12,19]. Reporting a single F1 score without error stratification obscures these benchmark properties.

**Precision and contradiction.** Across the corpora that include negative labels, our method rarely contradicted an explicit negative annotation:

- EU-ADR: 0 of 3 gold negative (`NA`) pairs were predicted as `supported`;
- RENET2: 2 of 223 predicted `supported` pairs carried the silver `non-associated` label.

Most apparent false positives are unlabelled pairs rather than direct contradictions. In curation workflows where a human biocurator verifies the highlighted sentence, low contradiction rates and high precision are the primary requirements.

**Statuses as an operating-point control.** Four-way statuses allow one extraction run to serve different curation workflows (Figure 3). A database pipeline can import `supported` pairs automatically while routing `uncertain` pairs tagged with `hedged_claim` or `scope` to human review. On BioRED Test, including these two uncertainty categories recovered 10 recall percentage points at almost no precision cost (0.853 to 0.846). Binary classifiers cannot separate hedged claims from entity-identity errors without retraining.

**Complementarity with supervised tools.** PubTator3 [2] achieves higher recall within its training domain, whereas our method captures full-text body evidence, distinguishes study findings from background citations, and identifies explicit negatives. On the BioRED test sample, the union of both systems recovered 73% of gold relations, compared with 65% for PubTator3 alone. A practical curation pipeline could combine both approaches by using PubTator3 to propose candidate pairs and applying the decision card to verify evidence spans and statuses.

**A frozen decision card instead of task-specific training.** The decision card is human-readable, version-controlled, and independent of any single benchmark. Adapting the pipeline to a new relation type, such as chemical–disease associations, requires editing one page of rules rather than annotating a new training set. Moreover, running the same card on GPT-6.1 Sol produced nearly identical performance, showing that the extraction behaviour is governed by the written rules rather than model-specific prompting quirks.

### 5.1 Limitations

- **No manual adjudication yet.** Our observation that many extra predictions represent valid unannotated relations relies on benchmark structure and spot checks rather than formal dual-annotator review.
- **Modest sample sizes on two benchmarks.** The RENET2 evaluation used 40 articles and the head-to-head PubTator3 comparison on BioRED used 50 abstracts, resulting in wide confidence intervals for several comparisons.
- **No ontology normalization.** Extracted entities are aligned by character span and are not yet mapped to NCBI Gene or MeSH identifiers, which prevents cross-document aggregation and direct comparison with DisGeNET [9] or CTD [10].
- **Proprietary models.** Claude Opus 5.5 and GPT-6.1 Sol are closed commercial models whose weights may change over time. To support reproducibility, we archive all prompts, raw model responses, and evaluation scripts.
- **Potential pretraining contamination.** The benchmark abstracts are publicly available and may have been present in the models' pretraining corpora. Similarly, PubTator3 was trained directly on BioRED.
- **Single-run evaluation.** Each benchmark configuration was run once. Although V1/V2/V3 pair-status agreement was 0.976–0.985 on the 12-paper full-text set, we did not measure multi-run variance on the full benchmarks.
- **Unmeasured full-text precision.** The 100-paper PMC corpus lacks gold annotations, and RENET2's released full texts are truncated mid-article.

## 6. Conclusions

A frozen, one-page decision card enabled a general-purpose LLM to extract gene–disease relations from full-text papers with machine-checked sentence evidence, four-way statuses, and source labels at USD 0.44 per paper.

Across three benchmarks with distinct annotation protocols, the method achieved high precision on BioRED (0.894) and rarely contradicted explicit negative labels on EU-ADR or RENET2. Directly re-querying unjudged same-sentence pairs yielded zero additional `supported` relations, demonstrating that the recall gap reflects a stricter evidence standard rather than missed text. Selecting an operating point on development data recovered 10 recall points on held-out test data.

The method complements supervised systems such as PubTator3, particularly on full text. Future work will incorporate dual-annotator adjudication of disputed pairs, entity normalization to NCBI Gene and MeSH, and hybrid pipelines that pair supervised candidate generation with rule-guided LLM verification.

## Figure specifications

### Graphical abstract
- **Data source files:** `experiments/single_shot/variants/v1_card_lean_medium/card.md`, `experiments/single_shot/runs/biored_all/v1_card_lean_medium/biored_eval.json`, `experiments/single_shot/runs/euadr/v1_card_lean_medium/euadr_eval.json`, `experiments/single_shot/runs/renet2/v1_card_lean_medium/renet2_eval.json`, and `experiments/single_shot/runs/full100/v1_card_lean_medium/vs_pubtator_relations.csv`.
- **Visual specification:** A three-panel horizontal layout (left-to-right workflow and results summary, sized 1328 × 531 px minimum for Elsevier JBI):
  - *Left panel (Input & Single-Request Neuro-Symbolic Pipeline):* Icon of a full-text JATS XML paper segmented into numbered sentences (`b0098.s3`) combined with a frozen 1-page Decision Card (`card.md`). An arrow points to a single LLM call (Claude Opus 5.5 / GPT-6.1 Sol, tools disabled), followed by a deterministic validator (`expand.py` + `validate.py`) that verifies verbatim surface forms and character spans.
  - *Middle panel (Traceable, Status-Aware Output):* A compact example output card showing a gene–disease pair linked to its exact evidence sentence ID, a 4-way status badge (`supported`, `uncertain` with reason code `hedged_claim`/`scope`, `explicit_negative`, `not_found`), and a source badge (`this study` vs `background`).
  - *Right panel (Multi-Benchmark & Full-Text Findings):* Three mini summary bars/callouts: (1) **BioRED (419 abstracts):** 0.894 precision; operating-point calibration raises Test F1 from 0.542 to 0.627 with zero extra model calls. (2) **Full Text (100 PMC papers):** 972 supported relations ($0.44/paper, 78 s), with 90% of evidence located outside the abstract. (3) **Epistemic Calibration:** Re-querying 97 unjudged same-sentence pairs yields 0 new `supported` pairs, proving the recall gap reflects a stricter evidence standard.
- **Short caption:** Graphical abstract: Single-request, status-aware gene–disease relation extraction using a frozen decision card and deterministic span validation across three benchmarks and full-text articles.

### Figure 1: Example paper output with evidence highlighting
- **Data source files:** `experiments/single_shot/runs/full100/v1_card_lean_medium/PMC10014009/response.txt` and expanded contract tables in `experiments/single_shot/runs/full100/v1_card_lean_medium/PMC10014009/outputs/{entities.csv,mentions.csv,evidence.csv,pairs.csv,graph.graphml}` (or `PMC10487392/outputs/` for a compact case-report view).
- **Visual specification:** A two-part composite figure illustrating how numbered sentences in a full-text article map to structured, auditable outputs:
  - *Panel A (Source text with sentence IDs and highlighted spans):* Excerpts from the abstract and body of `PMC10014009` showing sentence IDs (e.g. background sentence vs results sentence), with gene mentions (e.g. *KRIT1* including merged typo *KRTI1*, *MAP3K3*, *ZPLD1*) highlighted in blue and disease targets (e.g. cerebral cavernous malformation [CCM], familial CCM [FCCM], sporadic CCM) highlighted in coral.
  - *Panel B (Compact model response and expanded pair table):* Top box shows the raw pipe-delimited lines (`E|...`, `EV|...`, `P|...`) from `response.txt` citing only sentence IDs. Bottom table shows the deterministically expanded records from `pairs.csv` and `evidence.csv` contrasting three statuses in the same paper: (i) `supported` (`MAP3K3`–sporadic CCM, `this study`, with verbatim sentence quote and character offsets), (ii) `supported` (`KRIT1`–FCCM, `background`), and (iii) `uncertain` (`MAP3K3`–FCCM, reason code `hedged_claim`, and `KRIT1`–vascular malformation, reason code `presupposed_only`).
  - *Panel C (Mini bipartite graph):* The per-paper gene–disease bipartite graph rendered from `PMC10014009/outputs/graph.graphml`, with solid edges for `this study`, dashed edges for `background`, and dotted grey edges for `uncertain`.
- **Short caption:** Figure 1. Traceable extraction on a full-text article (`PMC10014009`), showing sentence-indexed text spans (A), compact model output and deterministically reconstructed evidence records across statuses and sources (B), and the resulting gene–disease bipartite graph (C).

### Figure 2: The single-request extraction and validation pipeline
- **Data source files:** Pipeline scripts `experiments/single_shot/{pack.py,run.py,expand.py}`, `toolkit/validate.py`, `experiments/single_shot/variants/v1_card_lean_medium/{card.md,format.md}`, and run statistics from `experiments/single_shot/runs/full100/v1_card_lean_medium/summary.csv`.
- **Visual specification:** A four-stage horizontal process diagram separating neural judgment from deterministic symbolic post-processing:
  - *Stage 1 — Deterministic Packing (`pack.py`):* JATS XML input is stripped of reference/acknowledgement sections and segmented into numbered blocks and sentences (`b0012.s3`). Fixed instructions (`card.md`, 1,044 words + `format.md`, 594 words) enter the cached system prompt; the numbered paper enters the user prompt.
  - *Stage 2 — Single-Shot LLM Inference (`run.py`):* A single tool-free request to Claude Opus 5.5 (or GPT-6.1 Sol) outputs compact pipe-delimited records (`E`, `X`, `EV`, `P`, `F`, `C`, `U`, `R`) referencing sentence IDs without copying text.
  - *Stage 3 — Deterministic Expansion (`expand.py`):* Script resolves sentence IDs back to exact text quotes, locates verbatim character offsets for every surface form, and populates the complete gene × disease Cartesian matrix (defaulting unlisted pairs to `not_found`).
  - *Stage 4 — Contract Validation & One-Shot Repair (`toolkit/validate.py`):* Checks verbatim span existence, sentence ID validity, primary endpoint membership, and legal reason codes. A green arrow ("Pass: 69/100 on first request; 381/419 on BioRED") leads to final CSV/GraphML outputs; a red feedback loop ("Format error: 31/100") sends the error list back to Stage 2 for at most one repair request (100/100 final pass rate).
- **Short caption:** Figure 2. Architecture of the single-request neuro-symbolic pipeline, separating LLM status judgment (`run.py`) from deterministic span reconstruction (`expand.py`) and contract validation (`validate.py`).

### Figure 3: Precision–recall plot of operating points across benchmarks
- **Data source files:**
  - BioRED (419 abstracts & Test 73): `experiments/single_shot/runs/biored_all/v1_card_lean_medium/biored_eval.json` and `experiments/single_shot/README.md` (Section "优化第一轮", lines 234–249 & 281–287).
  - BioRED Test sample (50 abstracts): `experiments/single_shot/runs/biored50/{v1_card_lean_medium,pubtator3}/biored_eval.json` and `experiments/single_shot/runs/biored50_gpt/v1_card_lean_medium/biored_eval.json`.
  - EU-ADR (100 abstracts, PA): `experiments/single_shot/runs/euadr/{v1_card_lean_medium,pubtator3}/euadr_eval.json`.
  - RENET2 (40 full texts): `experiments/single_shot/runs/renet2/{v1_card_lean_medium,pubtator3}/renet2_eval.json`.
- **Visual specification:** A four-panel precision–recall scatter/trajectory plot (Recall on x-axis from 0.0 to 1.0, Precision on y-axis from 0.0 to 1.0, with dashed iso-F1 contours at F1 = 0.3, 0.4, 0.5, 0.6, 0.7, 0.8 and 95% bootstrap CI error bars):
  - *Panel A (BioRED 419 abstracts & Held-out Test 73):* Plots connected trajectories across operating points from a single run: `Strict (supported only)` (419: P=0.894, R=0.430, F1=0.581; Test 73: P=0.853, R=0.397, F1=0.542) $\rightarrow$ `Supported + hedged/scope` (Test 73: P=0.846, R=0.498, F1=0.627) $\rightarrow$ `Supported + all uncertain` (419: P=0.814, R=0.577, F1=0.676; Test 73: P=0.833, R=0.536, F1=0.652), plus an open marker for `Scope-adjusted strict` (419: P=0.894, R=0.468, F1=0.614).
  - *Panel B (BioRED 50-abstract Test sample — Model & Comparator comparison):* Compares Claude Opus 5.5 (`Strict` P=0.835, R=0.412; `Supported + uncertain` P=0.833, R=0.542), GPT-6.1 Sol (`Strict` P=0.853, R=0.412; `Supported + uncertain` P=0.853, R=0.496), and in-domain PubTator3 (P=0.827, R=0.647, F1=0.726).
  - *Panel C (EU-ADR 100 abstracts, PA):* Shows our trajectory from `Strict` (P=0.469, R=0.549, F1=0.506) and `Scope-adjusted` (P=0.469, R=0.583, F1=0.520) to `Supported + uncertain` (P=0.414, R=0.680, F1=0.514; scope-adjusted R=0.722, F1=0.526) alongside PubTator3 (P=0.408, R=0.754, F1=0.529), illustrating the precision–recall trade-off along the same F1 contour.
  - *Panel D (RENET2 40 full texts):* Shows our trajectory from `Strict` (P=0.318, R=0.370, F1=0.342) to `Supported + uncertain` (P=0.312, R=0.464, F1=0.373; scope-adjusted R=0.488, F1=0.381) versus abstract-only PubTator3 (P=0.623, R=0.254, F1=0.361).
- **Short caption:** Figure 3. Precision–recall operating points and 95% bootstrap confidence intervals across BioRED (A, B), EU-ADR (C), and RENET2 full texts (D), showing how status reason codes shift recall without retraining and how the method compares with GPT-6.1 Sol and PubTator3.

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

[1] Luo L, Lai PT, Wei CH, Arighi CN, Lu Z. BioRED: a rich biomedical relation extraction dataset. *Briefings in Bioinformatics* 2022;23(5):bbac282. https://doi.org/10.1093/bib/bbac282 (PMID: 35849818).

[2] Wei CH, Allot A, Lai PT, Leaman R, Tian S, Luo L, et al. PubTator 3.0: an AI-powered literature resource for unlocking biomedical knowledge. *Nucleic Acids Research* 2024;52(W1):W540–6. https://doi.org/10.1093/nar/gkae235 (PMID: 38572754).

[3] van Mulligen EM, Fourrier-Reglat A, Gurwitz D, Molokhia M, Nieto A, Trifirò G, et al. The EU-ADR corpus: annotated drugs, diseases, targets, and their relationships. *Journal of Biomedical Informatics* 2012;45(5):879–84. https://doi.org/10.1016/j.jbi.2012.04.004 (PMID: 22554700).

[4] Su J, Wu Y, Ting HF, Lam TW, Luo R. RENET2: high-performance full-text gene–disease relation extraction with iterative training data expansion. *NAR Genomics and Bioinformatics* 2021;3(3):lqab062. https://doi.org/10.1093/nargab/lqab062 (PMID: 34278295).

[5] Lai PT, Wei CH, Luo L, Chen Q, Lu Z. BioREx: improving biomedical relation extraction by leveraging heterogeneous datasets. *Journal of Biomedical Informatics* 2023;146:104487. https://doi.org/10.1016/j.jbi.2023.104487 (PMID: 37696452).

[6] Lee J, Yoon W, Kim S, Kim D, Kim S, So CH, et al. BioBERT: a pre-trained biomedical language representation model for biomedical text mining. *Bioinformatics* 2020;36(4):1234–40. https://doi.org/10.1093/bioinformatics/btz682 (PMID: 31501885).

[7] Gu Y, Tinn R, Cheng H, Lucas M, Usuyama N, Liu X, et al. Domain-specific language model pretraining for biomedical natural language processing. *ACM Transactions on Computing for Healthcare* 2021;3(1):2. https://doi.org/10.1145/3458754.

[8] Chen Q, Hu Y, Peng X, Xie Q, Jin Q, Gilson A, et al. Benchmarking large language models for biomedical natural language processing applications and recommendations. *Nature Communications* 2025;16:1580. https://doi.org/10.1038/s41467-025-56989-2 (PMID: 39948109).

[9] Piñero J, Ramírez-Anguita JM, Saüch-Pitarch J, Ronzano F, Centeno E, Sanz F, et al. The DisGeNET knowledge platform for disease genomics: 2019 update. *Nucleic Acids Research* 2020;48(D1):D845–55. https://doi.org/10.1093/nar/gkz1021 (PMID: 31680165).

[10] Davis AP, Wiegers TC, Johnson RJ, Sciaky D, Wiegers J, Mattingly CJ. Comparative Toxicogenomics Database (CTD): update 2023. *Nucleic Acids Research* 2023;51(D1):D1257–62. https://doi.org/10.1093/nar/gkac833 (PMID: 36169237).

[11] Efron B, Tibshirani RJ. *An introduction to the bootstrap*. New York: Chapman & Hall/CRC; 1993. https://doi.org/10.1201/9780429246593.

[12] Wadhwa S, Amir S, Wallace BC. Revisiting relation extraction in the era of large language models. In: *Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers)*. Toronto: Association for Computational Linguistics; 2023, p. 15566–89. https://doi.org/10.18653/v1/2023.acl-long.868 (arXiv:2305.05003).

[13] Islamaj R, Lai PT, Wei CH, Luo L, Almeida T, Jonker RAA, et al. The overview of the BioRED (Biomedical Relation Extraction Dataset) track at BioCreative VIII. *Database (Oxford)* 2024;2024:baae069. https://doi.org/10.1093/database/baae069 (PMID: 39096045).

[14] Brokman A, Ai X, Jiang Y, Gupta S, Kavuluru R. A benchmark for end-to-end zero-shot biomedical relation extraction with LLMs: experiments with OpenAI models. In: *Proceedings of the Third Workshop for Artificial Intelligence for Scientific Publications (WASP)*. Association for Computational Linguistics; 2025, p. 44–55. https://doi.org/10.18653/v1/2025.wasp-main.6 (arXiv:2504.04083).

[15] Gade FS, Lund O, Zepeda Mendoza ML. Benchmarking zero-shot biomedical relation triplet extraction across language model architectures. In: *Proceedings of the 24th Workshop on Biomedical Language Processing (BioNLP 2025)*. Association for Computational Linguistics; 2025, p. 102–18. https://doi.org/10.18653/v1/2025.bionlp-1.9.

[16] Lai PT, Wei CH, Tian S, Leaman R, Lu Z. Enhancing biomedical relation extraction with directionality. *Bioinformatics* 2025;41(Suppl 1):i226–34. https://doi.org/10.1093/bioinformatics/btaf226.

[17] Caufield JH, Hegde H, Emonet V, Harris NL, Joachimiak MP, Matentzoglu N, et al. Structured Prompt Interrogation and Recursive Extraction of Semantics (SPIRES): a method for populating knowledge bases using zero-shot learning. *Bioinformatics* 2024;40(3):btae104. https://doi.org/10.1093/bioinformatics/btae104 (PMID: 38381653).

[18] Toro S, Anagnostopoulos AV, Bello SM, Blumberg K, Cameron R, Carmody L, et al. Dynamic retrieval augmented generation of ontologies using artificial intelligence (DRAGON-AI). *Journal of Biomedical Semantics* 2024;15:19. https://doi.org/10.1186/s13326-024-00320-3 (PMID: 39420412).

[19] Fan Y, Liu Y, Yao Z, Yu J, Hou L, Li J. Evaluating generative language models in information extraction as subjective question correction. In: *Proceedings of the 2024 Joint International Conference on Computational Linguistics, Language Resources and Evaluation (LREC-COLING 2024)*. Torino: ELRA and ICCL; 2024, p. 6450–63. https://doi.org/10.48550/arXiv.2404.03532 (arXiv:2404.03532).

[20] Li TS, Good BM, Su AI. Reproducing an expert-curated relation extraction gold standard with crowdsourcing. *arXiv preprint* 2015. https://doi.org/10.48550/arXiv.1505.06256 (arXiv:1505.06256).
