# Output format

Output only the lines below; no other text, headings or code fences. One record per line, fields separated by `|`, never use `|` inside a field. Leave optional fields empty (keep the separators). Cite evidence by sentence ID only (e.g. `b0012.s3`); never copy text.

```
META|your actual model name|whether you have seen prior analyses of this paper or the rule boundary cases (one sentence)
SCOPE|what you read and its limits (one sentence)
UNIT|unit_id|title|block range        (multi-study files only, e.g. UNIT|u2|Abstract 2|b0040-b0071)
E|entity_id|type|canonical name|surface1;surface2|identity|identity issues|gene species|parent entity_id|unit_id|candidate side
X|name as written|block_id|reason
EV|evidence_id|sentence IDs (consecutive in one block joined by +)|source|assertion kind|relation asserted|support basis
P|gene_id|target_id|status|relation type|source|claims|unresolved reasons|context-only evidence IDs|reason
F|finding_id|finding type|variables|population or group|significance|direction|statistics availability|evidence IDs|limits
C|conflict_id|subject|sentence IDs|impact|resolution|note
U|attachment name|where cited|why unread
R|rule|location|problem|your handling
```

Codes:
- type: gene / disease / clinical_event / symptom / phenotype / ambiguous
- identity: r (resolved) / p (provisional) / u (unresolved)
- identity issues (comma-separated): undefined_abbreviation, suspected_typo, species_unresolved, ambiguous_mapping, other
- gene species: human / non-human / empty (unknown)
- candidate side (ambiguous only): gene / disease
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
- Reasons in one short sentence; use a rule name where it says enough (e.g. `overall genotype test, not split to members`).
- Every entity needs at least one surface form found verbatim in the text (case-sensitive, whole word).
- Sentence IDs must come from the paper below; one evidence item stays within one block.
