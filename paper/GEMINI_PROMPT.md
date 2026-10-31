# Role
You are a co-author helping finish a research paper for the Journal of Biomedical Informatics (JBI). The full draft is in paper/draft_jbi.md. It was exported from a shared doc; keep its section structure.

# Project background (read before editing)
- Project: GeneDiseaseTrace-LLM, a zero-shot gene–disease relation extraction method. Claude Opus 5.5 reads each paper in one request and follows a frozen decision card (experiments/single_shot/variants/v1_card_lean_medium/card.md). Each gene–disease pair gets one of four statuses (supported / uncertain / explicit_negative / not_found), plus evidence sentence IDs and a source label (this study / background).
- Evaluated on BioRED (419 abstracts), EU-ADR (100 abstracts) and RENET2 (a 40-article full-text sample). PubTator3 is the comparator.
- Where the numbers come from:
  - Evaluation results (JSON):
    - experiments/single_shot/runs/biored_all/v1_card_lean_medium/biored_eval.json
    - experiments/single_shot/runs/biored50/{v1_card_lean_medium,pubtator3}/biored_eval.json
    - experiments/single_shot/runs/biored50_gpt/v1_card_lean_medium/biored_eval.json
    - experiments/single_shot/runs/euadr/{v1_card_lean_medium,pubtator3}/euadr_eval.json
    - experiments/single_shot/runs/renet2/{v1_card_lean_medium,pubtator3}/renet2_eval.json
  - Experiment notes (written in Chinese; the numbers are the same):
    - experiments/single_shot/README.md: A/B tests, the 100-paper run, the cross-model run, the optimization round
    - experiments/biored/README.md: error breakdown, novelty agreement, comparison with PubTator3, cost
    - experiments/euadr/README.md: label scopes, status table, extra pairs, cost
    - experiments/renet2/README.md: extra-pair breakdown, this-study vs background precision, cost

# Tasks, in this order
1. Number check: verify every number in the draft against the files above. List each mismatch in a table (location | draft value | file value | file path). Do not fix numbers silently. If you cannot find a number in any file, list it as "not found" rather than guessing.
2. Language polish: edit for a JBI methods/evaluation paper. Use plain academic English, keep sentences under about 25 words, and avoid hype words (novel, groundbreaking, significantly, unless a statistical test is reported). Keep the abstract at 300 words or fewer, in the Objective / Methods / Results / Conclusion structure.
3. Related work: extend Section 2 with 2023–2026 work on (a) LLMs for biomedical relation extraction, (b) LLM-assisted biocuration, and (c) evaluation with incomplete gold standards.
   - Cite only papers you can verify, giving a DOI or PubMed/arXiv ID for each.
   - If you cannot verify a paper, write [CITATION NEEDED: description] instead of inventing one.
4. References: check the 11 existing references (authors, year, journal, DOI) and fix any errors. Put the list in the Elsevier numbered style.
5. Figures: write a detailed spec, but do not draw, for:
   - the graphical abstract;
   - Figure 1, one paper's output with evidence highlighting;
   - Figure 2, the pipeline;
   - Figure 3, a precision–recall plot of the operating points across benchmarks.
   For each, give the data source file and a short caption.

# Hard rules
- Never change, round differently or invent any number, confidence interval, count or cost. Wrong numbers go only in the task 1 table.
- Do not make claims stronger than the results. Keep these points as they are:
  - PubTator3 beats our method on BioRED, its own training domain;
  - precision on EU-ADR and RENET2 is a lower bound;
  - manual adjudication has not been done yet.
- Keep every [TODO], [to complete] and [to verify] marker unless you complete that item with verified sources.
- Do not touch the "Author notes" section except to tick items you completed.
- Do not edit any file except creating paper/draft_jbi_v2.md. Do not change paper/draft_jbi.md, the experiment code or the result files.
- Do not commit or push.

# Output
- Save the revised draft as paper/draft_jbi_v2.md. Leave the original file unchanged.
- At the end of your reply, give a change log table: section | what changed | why. Add a separate list of any claim you think is weak or unsupported, so a human can decide.
