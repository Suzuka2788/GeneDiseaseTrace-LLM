# Output format

Output only the lines below; no other text, headings or code fences. One record per line, fields separated by `|`, never use `|` inside a field. Leave optional fields empty (keep the separators). Cite evidence by sentence ID only (e.g. `b0012.s3`); never copy text.

```
META|your actual model name|seen prior analyses of this paper or the rule boundary cases?
SCOPE|what you read and its limits
UNIT|unit_id|title|block range        (multi-study files only, e.g. UNIT|u2|Abstract 2|b0040-b0071)
E|entity_id|type|canonical name|surface1;surface2|identity|identity issues|gene species|parent entity_id|unit_id
X|name as written|block_id|reason
EV|evidence_id|sentence IDs joined by +|source|assertion kind|relation asserted|support basis
P|gene_id|target_id|status|relation type|source|claims|unresolved reasons|context-only evidence IDs|reason
F|finding_id|finding type|variables|population or group|significance|direction|statistics availability|evidence IDs|limits
C|conflict_id|subject|sentence IDs|impact|resolution|note
U|attachment name|where cited|why unread
R|rule|location|problem|your handling
```

Codes:
- type: gene / disease / clinical_event / symptom / phenotype / ambiguous_gene / ambiguous_disease (unresolved identity, with the side it is a candidate for)
- identity: r (resolved) / p (provisional) / u (unresolved)
- identity issues (comma-separated): undefined_abbreviation, suspected_typo, species_unresolved, ambiguous_mapping, other
- gene species: human / non-human / empty (unknown)
- source: bg (背景引用) / ts (本研究结果) / both (两者兼有) / unk (不确定)
- assertion kind: res (reported result) / bgr (background relation statement) / hyp (hypothesis) / aim / int (interpretation) / neg (negative result) / co (descriptive co-occurrence)
- relation asserted: aff / neg / hyp / q / na / pre (presupposed)
- support basis (comma-separated): ebr (explicit background report), rr (reported result), eda (explicit disease attribution), cs (co-segregation), cmp (comparative result), mi (model intervention), do (descriptive only), ho (hypothesis only), unc (unclear), none
- status: sup / neg / unc / nf
- relation type: c (causal) / r (correlation) / a (association) / - (none)
- claims: semicolon-separated, each `status:type:source:EV+EV`, e.g. `sup:c:bg:V1;sup:a:ts:V2+V3`
- unresolved reasons (comma-separated): identity, coreference, hedged_claim, support_basis_unresolved, presupposed_only, scope, conflict, missing_material, other
- finding type: association / correlation / group_comparison / descriptive / mechanism / hypothesis / other
- significance: significant / not_significant / mixed / unknown / not_applicable
- direction: positive / negative / mixed / null / unknown / not_applicable
- statistics availability: available / partial / unread / not_reported / not_applicable
- impact: noncritical / status_critical / undetermined; resolution: resolved / unresolved

Rules:
- List only pairs that need it (sup, neg, unc, and nf pairs with easily misread evidence to list as context). Every unlisted pair is nf.
- Sentence IDs must come from the paper below.
- Every entity needs at least one surface form found verbatim in the text (case-sensitive, whole word). Gene and disease entities list every distinct written form; symptom/phenotype entities list one form only.

Keep the output short; every free-text field has a word limit:
- META: model name and `seen: no` or `seen: yes, <what>` (max 8 words). SCOPE: max 12 words.
- P reason: max 10 words. F variables/group: max 8 words each; F limits: max 8 words or empty. C subject and note: max 8 words each. R problem and handling: max 15 words each.
- X: only names that could be mistaken for a gene or disease (e.g., table grouping labels, gene-like identifiers, disease-like terms). Skip obvious databases, tools, statistics and anatomy.
- F: only findings that involve a gene, a gene group or a primary disease (e.g., group-level genotype tests, within-disease correlations by gene group). Skip general clinical descriptives.
- C: only conflicts that involve a gene, a disease, a variant or a statistic used in F or P. Skip other numeric discrepancies.
- R: only when a rule genuinely does not cover the case; at most 3 lines.
- Do not repeat information across records.
