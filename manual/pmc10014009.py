"""Hand-curated annotation of PMC10014009 under biomed-gene-disease-evidence rules 1.1.0.

R-numbers refer to references/decision-rules.md of that skill. Every quote must occur verbatim in
its cited parsed block (quote None = the whole block, used for table rows); the builder rejects the
file otherwise. Patterns are matched longest-first so nested names go to the most specific entity.
"""

PAPER_ID = "PMC10014009"
RULE_VERSION = "1.1.0"
MODEL = "claude-opus-5-5"
OUTPUT_ROOT = "outputs_claude_Opus_5.5"
ORDER_BASIS = "outputs/inventory.csv order (first row); also first by file-name order"

HUMAN = "Homo sapiens (patient germline testing)"
HUMAN_CONTEXT = "human (only through human patient context; not explicitly stated)"
ANIMAL = "animal model, species not stated"

ENTITIES = [
    {"id": "G01", "type": "gene", "name": "KRIT1", "species": HUMAN,
     "patterns": [r"\bKRIT1\b", r"\bKRTI1\b"],
     "reference_sequences_from_text": "NG_012964.1/NC_000007.14 (b0019)",
     "merge_basis": "R8: KRTI1 (b0005) is edit distance 2 from KRIT1, appears in the same three-gene panel list that reads 'KRIT1, CCM2, and PDCD10' in b0003/b0014/b0019, and is not defined elsewhere.",
     "ambiguity": "'KRIT1 protein ankyrin component' (b0100) is a protein-product mention."},
    {"id": "G02", "type": "gene", "name": "CCM2", "species": HUMAN, "patterns": [r"\bCCM2\b"],
     "reference_sequences_from_text": "NG_016295.1/NC_000007.14 (b0019)",
     "merge_basis": "Single surface form; not merged with animal-model Ccm2 (R2).",
     "ambiguity": "Shares the 'CCM' prefix with the disease abbreviation; every occurrence denotes the gene or its carrier group."},
    {"id": "G03", "type": "gene", "name": "PDCD10", "species": HUMAN, "patterns": [r"\bPDCD10\b"],
     "reference_sequences_from_text": "NG_008158.1/NC_000003.12 (b0019)",
     "merge_basis": "Single surface form; not merged with animal-model Pdcd10 (R2).", "ambiguity": ""},
    {"id": "G04", "type": "gene", "name": "ZPLD1", "species": HUMAN_CONTEXT, "patterns": [r"\bZPLD1\b"],
     "merge_basis": "Single surface form.", "ambiguity": "Only in a cited finding (ref. 15)."},
    {"id": "G05", "type": "gene", "name": "MAP3K3", "species": HUMAN_CONTEXT,
     "patterns": [r"\bMAP3K3\b", r"\bMEKK3\b"], "protein_forms": ["MEKK3"],
     "merge_basis": "b0098 'MAP3K3, encoding MEKK3': MEKK3 kept as protein-product role of G05, not a separate gene.",
     "ambiguity": ""},
    {"id": "G06", "type": "gene", "name": "Krit1 (animal model, species not stated)", "species": ANIMAL,
     "patterns": [r"\bKrit1\b"], "merge_basis": "R2: separate from human KRIT1.", "ambiguity": "Model species not named."},
    {"id": "G07", "type": "gene", "name": "Ccm2 (animal model, species not stated)", "species": ANIMAL,
     "patterns": [r"\bCcm2\b"], "merge_basis": "R2: separate from human CCM2.", "ambiguity": "Model species not named."},
    {"id": "G08", "type": "gene", "name": "Pdcd10 (animal model, species not stated)", "species": ANIMAL,
     "patterns": [r"\bPdcd10\b"], "merge_basis": "R2: separate from human PDCD10.", "ambiguity": "Model species not named."},

    {"id": "D01", "type": "disease", "name": "cerebral cavernous malformation (CCM)", "species": "human",
     "patterns": [r"(?i)\bcerebral cavernous malformations?\b", r"\bCCMs?\b", r"\bCMM\b"],
     "parents": ["D08", "D04"],
     "parent_basis": "b0011 'Cerebral cavernous malformation (CCM) is an intracranial vascular malformation' (explicit 'X is a Y'); name = 'cerebral' + cavernous malformation (D04).",
     "merge_basis": "Abbreviation defined in b0011. R8: CMM (b0099) is edit distance 2 from CCM, used in the same sentence pair about therapeutics ('few therapeutic strategies for CCM … therapeutics for CMM'), and never defined.",
     "ambiguity": "'CCM' also prefixes gene-set terms (CCM genes, CCM complexes, CCM genotype) and lesion terms (CCM lesions); those mentions are role-tagged, not disease mentions."},
    {"id": "D02", "type": "disease", "name": "familial cerebral cavernous malformation (FCCM)", "species": "human",
     "patterns": [r"(?i)\bfamilial cerebral cavernous malformations?\b", r"\bFamilial CCM\b",
                  r"(?<=sporadic and )familial CCM\b", r"\bFCCM\b"],
     "parents": ["D01"], "parent_basis": "b0011 'CCM is broadly divided into sporadic and familial categories.'",
     "merge_basis": "Abbreviation defined in b0003 and b0011.",
     "ambiguity": "Includes 'clinical FCCM' (no mutation detected) and gene-confirmed FCCM, as the paper does."},
    {"id": "D03", "type": "disease", "name": "sporadic cerebral cavernous malformation", "species": "human",
     "patterns": [r"\bsporadic CCMs?\b", r"\bsporadic(?= and familial CCM)", r"\bsporadic(?= and familial categories)"],
     "parents": ["D01"], "parent_basis": "b0011 'CCM is broadly divided into sporadic and familial categories.'",
     "merge_basis": "Elliptical 'sporadic and familial CCM' (b0099) and 'sporadic … categories' (b0011) resolved within the same phrase (R6).",
     "ambiguity": ""},
    {"id": "D04", "type": "disease", "name": "cavernous malformation (CM, any site)", "species": "human",
     "patterns": [r"\bcavernous malformation\b", r"\bCM\b"],
     "merge_basis": "Defined in Table 1/2 notes ('CM, cavernous malformation').", "ambiguity": "Site-unspecified family term."},
    {"id": "D05", "type": "disease", "name": "spinal cavernous malformation", "species": "human",
     "patterns": [r"(?i)\bspinal (?:cavernous malformation|CM)\b", r"\bSpinal(?= \((?:neck pain|screen)\))"],
     "parents": ["D04"], "parent_basis": "Name = 'spinal' + cavernous malformation (R7).",
     "merge_basis": "b0016 'spinal cavernous malformation (CM)'; Table 2 'Non-cerebral CM' values 'Spinal (...)'.", "ambiguity": ""},
    {"id": "D06", "type": "disease", "name": "cutaneous cavernous malformation", "species": "human",
     "patterns": [r"(?i)\bcutaneous CM\b", r"(?<=\| )Cutaneous(?= \|)"],
     "parents": ["D04"], "parent_basis": "Name = 'cutaneous' + CM (R7).",
     "merge_basis": "b0016 'cutaneous CM'; Table 2 'Non-cerebral CM' value 'Cutaneous'.", "ambiguity": ""},
    {"id": "D07", "type": "clinical_event", "name": "cavernous angioma with symptomatic hemorrhage (CASH)", "species": "human",
     "patterns": [r"(?i)\bcavernous angiomas? with (?:a |the occurrence of )?symptomatic hemorrhage\b", r"\bCASH\b",
                  r"\brecurrent symptomatic hemorrhage\b"],
     "merge_basis": "Abbreviation defined in b0016/b0021 and table notes; 'recurrent symptomatic hemorrhage' uses the defining phrase.",
     "ambiguity": "Named haemorrhagic event of CCM (R1: named clinical event, in primary matrix)."},
    {"id": "D08", "type": "disease", "name": "intracranial vascular malformation", "species": "human",
     "patterns": [r"\bintracranial vascular malformation\b"], "parents": ["D09"],
     "parent_basis": "Name = 'intracranial' + vascular malformation (R7).",
     "merge_basis": "Single surface form.", "ambiguity": "Class term used to define CCM."},
    {"id": "D09", "type": "disease", "name": "vascular malformation", "species": "unspecified",
     "patterns": [r"\bvascular malformation\b"], "merge_basis": "Single surface form.", "ambiguity": "Broad class."},
    {"id": "D10", "type": "phenotype", "name": "cerebral microbleeds", "species": "human",
     "patterns": [r"\bcerebral microbleeds\b"], "merge_basis": "Single surface form.",
     "ambiguity": "Imaging finding in excluded patients (b0026); R1 auxiliary."},
    {"id": "D11", "type": "disease", "name": "small vessel disease", "species": "human",
     "patterns": [r"\bsmall vessel disease\b"], "merge_basis": "Single surface form.", "ambiguity": "Exclusion criterion (b0026)."},
    {"id": "D12", "type": "disease", "name": "diffuse axonal injury", "species": "human",
     "patterns": [r"\bdiffuse axonal injury\b"], "merge_basis": "Single surface form.", "ambiguity": "Exclusion criterion (b0026)."},
    {"id": "D13", "type": "disease", "name": "intracerebral hemorrhage", "species": "human",
     "patterns": [r"\bintracerebral hemorrhages?\b"], "merge_basis": "Single surface form.",
     "ambiguity": "Exclusion criterion (b0026); distinct from CASH."},
    {"id": "D14", "type": "disease", "name": "developmental venous anomaly", "species": "human",
     "patterns": [r"\bdevelopmental venous anomaly\b"], "merge_basis": "Single surface form.",
     "ambiguity": "Stated absent from the cohort (b0026)."},
    {"id": "D15", "type": "disease", "name": "tumor (unspecified)", "species": "human",
     "patterns": [r"(?i)\btumors?\b", r"\btumorous condition\b"],
     "merge_basis": "Generic term of Table 1/2 'Tumor' columns.", "ambiguity": "Family term; specific tumours are separate nodes."},
    {"id": "D16", "type": "disease", "name": "breast cancer", "species": "human",
     "patterns": [r"\bBreast cancer\b"], "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D17", "type": "disease", "name": "thyroid cancer", "species": "human",
     "patterns": [r"\bThyroid cancer\b"], "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D18", "type": "disease", "name": "diffuse midline glioma", "species": "human",
     "patterns": [r"(?i)\bdiffuse midline glioma\b"], "qualifiers": "WHO grade IV (b0070)",
     "merge_basis": "Same term in b0070 and Table 2 (K3).", "ambiguity": ""},
    {"id": "D19", "type": "disease", "name": "adrenal adenoma", "species": "human",
     "patterns": [r"\bAdrenal adenoma\b"], "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D20", "type": "disease", "name": "anterior cerebral artery (ACA) infarction", "species": "human",
     "patterns": [r"\bACA infarction\b"], "qualifiers": "left (b0077)",
     "merge_basis": "ACA expanded in Table 2 note.", "ambiguity": ""},
    {"id": "D21", "type": "symptom", "name": "seizure", "species": "human", "patterns": [r"(?i)\bseizures?\b"],
     "merge_basis": "Generic seizure mentions incl. 'early-onset seizure' (timing qualifier).", "ambiguity": ""},
    {"id": "D22", "type": "symptom", "name": "focal impaired awareness seizure (FIAS)", "species": "human",
     "patterns": [r"\bfocal impaired awareness seizure\b", r"\bFIAS\b"], "parents": ["D21"],
     "parent_basis": "Name contains 'seizure' (R7).", "merge_basis": "Abbreviation defined in Table 2 note.", "ambiguity": ""},
    {"id": "D23", "type": "symptom", "name": "focal to bilateral tonic-clonic seizure (FBTCS)", "species": "human",
     "patterns": [r"\bfocal to bilateral tonic.clonic seizure\b", r"\bFBTCS\b"], "parents": ["D21"],
     "parent_basis": "Name contains 'seizure' (R7).", "merge_basis": "Abbreviation defined in Table 2 note.", "ambiguity": ""},
    {"id": "D24", "type": "symptom", "name": "emotional seizure", "species": "human",
     "patterns": [r"\bEmotional seizure\b"], "parents": ["D21"], "parent_basis": "Name contains 'seizure' (R7).",
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D25", "type": "disease", "name": "occipital lobe epilepsy (OLE)", "species": "human",
     "patterns": [r"\boccipital lobe epilepsy\b", r"\bOLE\b"], "merge_basis": "Abbreviation defined in Table 2 note.", "ambiguity": ""},
    {"id": "D26", "type": "ambiguous", "name": "PLE (undefined in text)", "species": "human", "patterns": [r"\bPLE\b"],
     "merge_basis": "R8: not expanded anywhere; not merged with OLE.",
     "ambiguity": "In diagnosis position for K3 ('FIAS and FBTCS, 51YO → PLE'), parallel to '→ OLE' for K8; R1 keeps it in the primary matrix as ambiguous."},
    {"id": "D27", "type": "symptom", "name": "headache", "species": "human", "patterns": [r"(?i)\bheadache\b"],
     "merge_basis": "Includes 'Nonspecific headache'.", "ambiguity": ""},
    {"id": "D28", "type": "symptom", "name": "neck pain", "species": "human", "patterns": [r"\bneck pain\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D29", "type": "symptom", "name": "dizziness", "species": "human", "patterns": [r"(?i)\bdizziness\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D30", "type": "symptom", "name": "weakness", "species": "human", "patterns": [r"(?i)\bweakness\b"],
     "merge_basis": "Table 1 'Weakness' and Table 2 'sided weakness'.", "ambiguity": "Table 1 pools weakness, dysarthria and facial palsy."},
    {"id": "D31", "type": "symptom", "name": "dysarthria", "species": "human", "patterns": [r"\bDysarthria\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D32", "type": "symptom", "name": "facial palsy", "species": "human", "patterns": [r"\bFacial palsy\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D33", "type": "symptom", "name": "diplopia", "species": "human", "patterns": [r"(?i)\bdiplopia\b"],
     "merge_basis": "Includes 'binocular diplopia'.", "ambiguity": ""},
    {"id": "D34", "type": "symptom", "name": "visual symptoms", "species": "human",
     "patterns": [r"\bVisual symptoms\b", r"\bpositive visual symptom\b"],
     "merge_basis": "Table 1 category and K8 'Transient positive visual symptom'.", "ambiguity": "Not merged with 'visual disturbance'."},
    {"id": "D35", "type": "symptom", "name": "visual disturbance", "species": "human", "patterns": [r"\bVisual disturbance\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D36", "type": "symptom", "name": "central vertigo", "species": "human", "patterns": [r"\bCentral vertigo\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D37", "type": "symptom", "name": "drowsy mentality", "species": "human", "patterns": [r"\bdrowsy mentality\b"],
     "merge_basis": "Single surface form.", "ambiguity": "Not merged with 'decreased mentality'."},
    {"id": "D38", "type": "symptom", "name": "decreased mentality", "species": "human", "patterns": [r"\bDecreased mentality\b"],
     "merge_basis": "Single surface form.", "ambiguity": ""},
    {"id": "D39", "type": "phenotype", "name": "neurological sequelae", "species": "human",
     "patterns": [r"\bneurological sequelae\b"], "merge_basis": "Single surface form.", "ambiguity": "Non-specific outcome."},
]

EXCLUDED = [
    ("CCM genes / FCCM gene / the three CCM genes / CCM-associated genes", "gene set", "R1: gene-set term (defined in b0003 as KRIT1, CCM2, PDCD10); role-tagged gene_set_modifier."),
    ("CCM complexes", "protein complex", "R1: protein complex."),
    ("ankyrin component", "protein region", "Part of the KRIT1 protein (b0100)."),
    ("NG_012964.1, NC_000007.14, NG_016295.1, NG_008158.1, NC_000003.12", "reference sequence", "Stored as reference_sequences_from_text on G01-G03."),
    ("HGMD, gnomAD, KRGDB, ACMG", "database / guideline", "Not genes or diseases."),
    ("FSPLICE, NNSplice, NetGene2", "software", "Splice prediction tools."),
    ("WHO grade IV", "tumour grade", "Qualifier of D18."),
    ("brainstem lesions / brainstem / lateral temporal / parietal / cerebellum / cortex/subcortex / frontal / temporal / medial temporal / occipital / basal ganglia / thalamus / pons / medulla oblongata / motor cortex / occipital cortex / frontal cortex / hindbrain / thoracic spinal cord", "anatomical location", "Lesion sites; the location finding is study finding SF1."),
    ("Zabramski type IV", "lesion classification", "Radiological lesion type."),
    ("recent hemorrhage (b0070)", "ambiguous event", "Suspected haemorrhage in a spinal CM, not labelled CASH; not in a diagnosis position."),
    ("hemorrhage (b0011 'development and hemorrhage')", "generic event", "Unqualified mention in mechanism text."),
    ("symptoms / disease burden / symptomatic / asymptomatic", "generic term", "Not named conditions."),
    ("autosomal dominant disease/disorder", "inheritance descriptor", "Describes FCCM."),
    ("blooming artifacts", "imaging artefact", "MRI artefact."),
]

# Evidence: id -> (block, quote or None for whole block, source_scope, assertion_kind, conditions)
EVIDENCE = {
    "E01": ("b0011", "Familial CCM (FCCM) is an autosomal dominant disorder caused by mutations in three genes, KRIT1, CCM2, and PDCD10.",
            "background", "background_relation_statement", {}),
    "E02": ("b0003", "Familial cerebral cavernous malformation (FCCM) is an autosomal dominant disease induced by loss-of-function mutations in three CCM genes, KRIT1, CCM2, and PDCD10.",
            "background", "background_relation_statement", {"note": "Abstract restatement of E01 without citation"}),
    "E03": ("b0011", "These prior studies demonstrated that the products of the three genes (KRIT1, CCM2, and PDCD10) are associated with CCM form complexes. Loss of function (LOF) of these genes leads to the formation of CCM.",
            "background", "background_relation_statement",
            {"coreference": "'these genes' -> KRIT1, CCM2, PDCD10 listed in the immediately preceding sentence (R6)"}),
    "E04": ("b0028", "Cohort 1 consisted of nine patients with KRIT1 variants, two with CCM2 variants, two with PDCD10 variants, and eight with the mutation not detected (Table 1).",
            "this_study", "reported_result", {"population": "cohort 1, n = 21 FCCM patients", "variants": "heterozygous (Table 2 note)"}),
    "E06": ("b0070", "The family members of one patient with a KRIT1 variant (K7), and two patients with PDCD10 variants (P1 and P2), received genetic testing, and four family members with the same variant as the proband were detected. Furthermore, these family members had CCM lesions confirmed by brain MRI.",
            "this_study", "reported_result", {"design": "family co-segregation: K7 mother (KRIT1); P1 father, P2 two sons (PDCD10)"}),
    "E07": ("b0070", "Interestingly, five novel variants and one novel variant were confirmed in KRIT1 and PDCD10, respectively.",
            "this_study", "reported_result", {"classification": "novel variants classified LP by ACMG 2015 (Table 2)"}),
    "E08": ("b0070", "The CCM2 group comprised one patient with a nonsense mutation and one with a missense mutation.",
            "this_study", "reported_result", {"classification": "both 'Previously reported' (Table 2, b0085-b0086); no family testing"}),
    "E10": ("b0101", "CCM2 variant patients are usually asymptomatic and have milder symptoms. 9",
            "background", "background_relation_statement", {"scope": "severity of disease in CCM2 carriers"}),
    "E11": ("b0101", "PDCD10 variant patients usually have early onset and severe manifestations. 12",
            "background", "background_relation_statement", {"scope": "onset and severity in PDCD10 carriers"}),
    "E12": ("b0098", "In the 2-hit model, biallelic LOF in CCM genes, achieved by one somatic mutation in heterozygous germline mutation or two somatic mutations in wild-type gene, is required to initiate CCM formation.",
            "background", "background_relation_statement", {"note": "gene-set term 'CCM genes'; subtype not named"}),
    "E13": ("b0098", "Moreover, gain-of-function (GOF) mutations in MAP3K3, encoding MEKK3, have been confirmed in sporadic CCM patients. 16",
            "background", "background_relation_statement", {"variant_type": "gain-of-function"}),
    "E14": ("b0098", "LOF in CCM genes and GOF in MAP3K3 are mutually exclusive, and the researchers suggested that CCM complexes suppress the activity of MEKK3.",
            "background", "background_relation_statement", {"note": "disease not named in the sentence"}),
    "E15": ("b0098", "Therefore, the mutation of these genes could be a novel cause of FCCM.",
            "background", "hypothesis", {"coreference": "'these genes': preceding sentence names both 'CCM genes' and MAP3K3; unresolved (R6)"}),
    "E16": ("b0098", "F. Gianfrancesco et al. proposed that ZPLD1 mutation is associated with FCCM. 15",
            "background", "background_relation_statement", {"wording": "proposed (reporting verb, R4)"}),
    "E17": ("b0026", "Of the remaining 27 patients, six sporadic CCM patients with a wild-type FCCM gene, a single CCM lesion, and no family history of CCM were excluded.",
            "this_study", "descriptive_cooccurrence", {"note": "wild-type germline result is part of the exclusion definition"}),
    "E18": ("b0100", "Exon 12 is responsible for a particular portion of the KRIT1 protein ankyrin component. 19 This component is likely critical for preventing vascular malformation.",
            "background", "interpretation", {"wording": "likely"}),
    "E19": ("b0011", "Despite the tremendous progress in understanding CCM, the explicit mechanisms underlying the vascular-specific manifestation and vascular malformation suppression of the three CCM genes remain unknown.",
            "background", "interpretation", {"note": "presupposes a suppressive role; gene-set term, list two sentences earlier"}),
    "E20": ("b0099", "Some preclinical studies have demonstrated that the CCM animal model induced by Krit1, Ccm2, or Pdcd10 heterozygous loss in the immediate postnatal period, tended to harbor lesions in the hindbrain. 17 , 18",
            "background", "background_relation_statement",
            {"evidence_species": "non-human", "model_type": "heterozygous loss in the immediate postnatal period", "species": "not stated"}),
    "E21": ("b0021", "Moreover, we determined whether CCM genotype was associated with the earlier occurrence of the first CASH, adjusting for gender and first CCM diagnosis age using Cox proportional hazards models.",
            "this_study", "aim", {}),
    "E22": ("b0094", "The difference among the CCM mutation genotypes was not statistically significant (Table S3).",
            "this_study", "negative_result",
            {"population": "cohort 2, n = 25", "outcome": "time to first CASH", "design": "difference among genotypes; per-gene contrasts not visible", "depends_on_unread": "Table S3"}),
    "E23": ("b0043", None, "this_study", "descriptive_cooccurrence", {"table": "Table 1 row 'CASH, %' by gene group; no per-gene test"}),
    "E24": ("b0100", "Two probands had this mutation and showed different clinical manifestations, including age at diagnosis and the presence of CASH.",
            "this_study", "descriptive_cooccurrence", {"variant": "KRIT1 c.1147-2A>G (K6, K7)"}),
    "E25": ("b0101", "However, the CCM2 group exhibited an early diagnosis with a CASH event, albeit with a decreased lesion number over time.",
            "this_study", "descriptive_cooccurrence", {"n": "2"}),
    "E26": ("b0101", "Additionally, a patient with infancy onset had recurrent CASH with a short interval, resulting in a very poor prognosis.",
            "this_study", "descriptive_cooccurrence", {"coreference": "PDCD10 group, preceding sentence (R6); patient P1"}),
    "E27": ("b0074", None, "this_study", "descriptive_cooccurrence", {"patient": "K1, KRIT1 carrier, tumour column: breast cancer"}),
    "E28": ("b0075", None, "this_study", "descriptive_cooccurrence", {"patient": "K2, KRIT1 carrier, tumour column: thyroid cancer"}),
    "E29": ("b0076", None, "this_study", "descriptive_cooccurrence", {"patient": "K3, KRIT1 carrier: FIAS/FBTCS -> PLE, spinal CM, diffuse midline glioma"}),
    "E30": ("b0070", "The surgical biopsy exhibited diffuse midline glioma, classified as WHO grade IV.",
            "this_study", "descriptive_cooccurrence", {"patient": "K3"}),
    "E31": ("b0077", None, "this_study", "descriptive_cooccurrence", {"patient": "K4, KRIT1 carrier: left ACA infarction, adrenal adenoma"}),
    "E32": ("b0082", None, "this_study", "descriptive_cooccurrence", {"patient": "K8, KRIT1 carrier: OLE"}),
    "E33": ("b0050", None, "this_study", "descriptive_cooccurrence", {"table": "Table 1 row 'Tumor, %'; no significance mark"}),
    "E34": ("b0070", "Four patients with KRIT1 variants had a history of tumor or a current tumor.",
            "this_study", "descriptive_cooccurrence", {}),
    "E35": ("b0047", None, "this_study", "descriptive_cooccurrence", {"table": "Table 1 row 'Spinal CM, %'"}),
    "E36": ("b0048", None, "this_study", "descriptive_cooccurrence", {"table": "Table 1 row 'Cutaneous CM, %'"}),
    "E37": ("b0085", None, "this_study", "descriptive_cooccurrence", {"patient": "C1, CCM2 carrier: cutaneous CM"}),
    "E38": ("b0090", None, "this_study", "descriptive_cooccurrence", {"patient": "P2, PDCD10 carrier: spinal CM (screen)"}),
    "E39": ("b0070", "Two patients (K3 and P2) had spinal CM, and one (C1) had cutaneous CM.",
            "this_study", "descriptive_cooccurrence", {}),
    "E40": ("b0067", "Lesions of the brainstem, temporal lobe (especially lateral temporal), and parietal lobe were frequent in the patients with a mutation detected",
            "this_study", "reported_result", {}),
    "E41": ("b0067", "Nonetheless, the AUC significantly decreased after subtracting the brainstem (AUC 0.982 vs. 0.779, P = 0.0389), showing that brainstem lesions were mostly associated with mutation detection.",
            "this_study", "reported_result", {}),
    "E42": ("b0094", "To exhibit the age-related disease burden of FCCM, we investigated the number of large CCMs by age (Fig. 3A). The correlation coefficient was 0.27 (p = 0.017).",
            "this_study", "reported_result", {}),
    "E43": ("b0094", "The correlation coefficients of the KRIT1, Mutation not detected, and CCM2 groups were 0.75 (P < 0.001), 0.53 (P = 0.004), and - 0.84 (p = 0.019), respectively. However, the correlation between age and the number of large CCMs was not statistically significant in the PDCD10 group.",
            "this_study", "reported_result", {}),
    "E44": ("b0101", "These confusing findings might result from detection bias, in which many asymptomatic patients with the CCM2 variant did not visit the hospital and were not diagnosed or enrolled.",
            "this_study", "interpretation", {}),
    "E45": ("b0066", "Even though there was no statistical significance in the clinical characteristics, some conditions were relatively disproportionate.",
            "this_study", "negative_result", {}),
    "E46": ("b0094", "The patients diagnosed at a younger age were at increased risk of the earlier first CASH.",
            "this_study", "reported_result", {"depends_on_unread": "Table S3"}),
    "E47": ("b0094", "Besides, the cumulative incidence rate of the first CASH was 0.160 until nineteen years old (Table S2). The risk of first CASH did not show a plateau as the patients got older.",
            "this_study", "reported_result", {"depends_on_unread": "Table S2"}),
    "E48": ("b0101", "Even if the correlation was not statistically significant, the PDCD10 group trended toward early onset.",
            "this_study", "interpretation", {}),
    "E49": ("b0101", "the severity of brain imaging worsened faster in the KRIT1 group than in the Mutation not detected group",
            "this_study", "interpretation", {"note": "slope difference not formally tested in the text"}),
    "E50": ("b0007", "Cohort 1 demonstrated that brainstem lesions were mostly associated with the mutation detection in CCM genes (brainstem, lateral temporal, and parietal lesions vs. lateral temporal and parietal lesions, AUC 0.928 vs. 0.779, P = 0.0389).",
            "this_study", "reported_result", {}),
}

HUMAN_PANEL = ("G01", "G02", "G03")


def _claim(relation_type, source_scope, evidence_ids, statement):
    return {"relation_type": relation_type, "source_scope": source_scope, "evidence_ids": evidence_ids, "statement": statement}


def _not_found(context, reason, conditions=None):
    return {"status": "not_found", "relation_type": "none", "source_scope": "uncertain", "claims": [],
            "context_checked": context, "reason": reason, "conditions": conditions or {}, "unresolved_reason": ""}


JUDGMENTS = {}

_FCCM_THIS_STUDY = {
    "G01": (["E04", "E06", "E07"], "KRIT1 variants (5 novel LP, 2 previously reported, all null) detected in 9/21 FCCM patients; K7 variant co-segregated with MRI-confirmed CCM in the mother."),
    "G02": (["E04", "E08"], "CCM2 variants (nonsense, missense; both previously reported) detected in 2/21 FCCM patients; no family testing."),
    "G03": (["E04", "E06", "E07"], "PDCD10 variants (1 novel LP, 1 previously reported) detected in 2/21 FCCM patients; both co-segregated with MRI-confirmed CCM in tested relatives."),
}
_FCCM_SEVERITY = {"G02": ("E10", "Background: CCM2 carriers usually milder."), "G03": ("E11", "Background: PDCD10 carriers usually early onset and severe.")}

for gene in HUMAN_PANEL:
    ids, text = _FCCM_THIS_STUDY[gene]
    claims = [_claim("causal", "background", ["E01", "E02"], "Authors' background statement: FCCM is caused by mutations in KRIT1, CCM2 and PDCD10."),
              _claim("association", "this_study", ids, text)]
    if gene in _FCCM_SEVERITY:
        eid, statement = _FCCM_SEVERITY[gene]
        claims.append(_claim("association", "background", [eid], statement))
    JUDGMENTS[(gene, "D02")] = {
        "status": "supported", "relation_type": "causal", "source_scope": "background", "claims": claims, "context_checked": [],
        "conditions": {"population": "Korean single-centre retrospective cohort, n = 21 FCCM"},
        "unresolved_reason": "",
        "reason": "R3: highest-level claim is causal and comes from the authors' background statement, so source_scope = background. "
                  "This study adds an association claim (variant detection" + (", family co-segregation" if gene != "G02" else "") +
                  "), not causal evidence. Age-lesion correlations by gene group are study finding SF4, not this pair."}

    JUDGMENTS[(gene, "D01")] = {
        "status": "supported", "relation_type": "causal", "source_scope": "background",
        "claims": [_claim("causal", "background", ["E03"], "Prior studies: LOF of the three genes leads to the formation of CCM.")],
        "context_checked": ["E12"], "conditions": {"coreference": "resolved within adjacent sentence (R6)"}, "unresolved_reason": "",
        "reason": "Direct background statement about CCM (not propagated from FCCM). The 2-hit sentence (E12) uses the gene-set term 'CCM genes' and is kept as context only."}

    JUDGMENTS[(gene, "D03")] = {
        "status": "uncertain", "relation_type": "none", "source_scope": "background", "claims": [],
        "context_checked": ["E12", "E14", "E17"], "conditions": {}, "unresolved_reason": "scope",
        "reason": "The 2-hit model allows two somatic hits in a wild-type gene and LOF in 'CCM genes' is described as mutually exclusive with MAP3K3 GOF, "
                  "but no sentence names sporadic CCM together with this gene; the link needs an inference the text does not state. "
                  "The wild-type germline result in excluded sporadic patients (E17) is part of the exclusion definition, not evidence either way."}

    JUDGMENTS[(gene, "D07")] = _not_found(
        ["E21", "E22", "E23"] + {"G01": ["E24"], "G02": ["E25"], "G03": ["E26"]}[gene],
        "R5: the only test is the difference among genotypes in time to first CASH (cohort 2, n = 25), reported as not significant without per-gene contrasts; "
        "it is study finding SF2, not a per-gene negative. Remaining material is descriptive frequencies or single patients.",
        {"depends_on_unread": "Table S3"})

    JUDGMENTS[(gene, "D09")] = {
        "status": "uncertain", "relation_type": "none", "source_scope": "background", "claims": [],
        "context_checked": (["E18"] if gene == "G01" else []) + ["E19"], "conditions": {},
        "unresolved_reason": "hedged_claim, coreference",
        "reason": "R4: 'likely critical for preventing vascular malformation' is an interpretation (KRIT1 only), and the background sentence presupposes a "
                  "suppressive role of 'the three CCM genes' whose mechanism 'remain[s] unknown'; its gene-set referent is two sentences back (R6)."}

JUDGMENTS[("G01", "D05")] = _not_found(["E29", "E35", "E39"], "Single carrier (K3) with spinal CM; Table 1 frequencies by gene group untested.")
JUDGMENTS[("G03", "D05")] = _not_found(["E38", "E35", "E39"], "Single carrier (P2) with spinal CM; Table 1 frequencies by gene group untested.")
JUDGMENTS[("G02", "D06")] = _not_found(["E37", "E36", "E39"], "Single carrier (C1) with cutaneous CM; Table 1 frequencies by gene group untested.")
JUDGMENTS[("G01", "D15")] = _not_found(["E34", "E33"], "Four KRIT1 carriers had tumours, stated without analysis or attribution; Table 1 tumour row has no significance mark.")
JUDGMENTS[("G01", "D16")] = _not_found(["E27"], "Single carrier (K1) comorbidity.")
JUDGMENTS[("G01", "D17")] = _not_found(["E28"], "Single carrier (K2) comorbidity.")
JUDGMENTS[("G01", "D18")] = _not_found(["E29", "E30"], "Single carrier (K3) comorbidity; the authors do not attribute the glioma to the variant.")
JUDGMENTS[("G01", "D19")] = _not_found(["E31"], "Single carrier (K4) comorbidity.")
JUDGMENTS[("G01", "D20")] = _not_found(["E31"], "Single carrier (K4) presenting event.")
JUDGMENTS[("G01", "D25")] = _not_found(["E32"], "Single carrier (K8) diagnosis.")
JUDGMENTS[("G01", "D26")] = _not_found(["E29"], "Single carrier (K3); the abbreviation itself is unresolved.")

JUDGMENTS[("G04", "D02")] = {
    "status": "supported", "relation_type": "association", "source_scope": "background",
    "claims": [_claim("association", "background", ["E16"], "Cited study (ref. 15) proposed ZPLD1 mutation is associated with FCCM.")],
    "context_checked": [], "conditions": {"wording": "proposed", "tested_here": "no; ZPLD1 not on the panel"}, "unresolved_reason": "",
    "reason": "R4 row 2: reporting verb ('proposed') attributing a conclusion to a cited study -> supported / background."}
JUDGMENTS[("G04", "D01")] = _not_found(["E16"], "Evidence concerns FCCM only; not propagated to CCM (R7).")

JUDGMENTS[("G05", "D03")] = {
    "status": "supported", "relation_type": "association", "source_scope": "background",
    "claims": [_claim("association", "background", ["E13"], "GOF MAP3K3 mutations confirmed in sporadic CCM patients (ref. 16).")],
    "context_checked": ["E14"], "conditions": {"variant_type": "gain-of-function"}, "unresolved_reason": "",
    "reason": "R4 row 1: stated prior finding. Association (mutations found in patients), no causal wording."}
JUDGMENTS[("G05", "D02")] = {
    "status": "uncertain", "relation_type": "none", "source_scope": "background", "claims": [],
    "context_checked": ["E15"], "conditions": {}, "unresolved_reason": "hedged_claim, coreference",
    "reason": "R4: authors' speculation ('could be'); R6: 'these genes' has two candidate antecedents in the preceding sentence."}
JUDGMENTS[("G05", "D01")] = _not_found(["E13"], "Evidence concerns sporadic CCM only; not propagated to CCM (R7).")

for gene in ("G06", "G07", "G08"):
    JUDGMENTS[(gene, "D01")] = {
        "status": "supported", "relation_type": "causal", "source_scope": "background",
        "claims": [_claim("causal", "background", ["E20"], "Preclinical CCM model induced by heterozygous loss of the gene.")],
        "context_checked": [], "unresolved_reason": "",
        "conditions": {"evidence_species": "non-human", "model_type": "heterozygous loss in the immediate postnatal period",
                       "phenotype": "lesions tended to occur in the hindbrain"},
        "reason": "R2: the text explicitly names a CCM animal model induced by this gene's loss -> edge to the CCM node, marked non-human. R3: induced model counts as causal."}

STUDY_FINDINGS = [
    {"finding_id": "SF1", "variables": "lesion location (brainstem, lateral temporal, parietal) vs detection of a CCM-gene mutation",
     "population_or_group": "cohort 1, n = 21; pooled mutation-detected group (KRIT1 + CCM2 + PDCD10, n = 13) vs not detected (n = 8)",
     "status": "significant", "source_scope": "this_study", "evidence": ["E40", "E41", "E50"],
     "conditions": "ROC/logistic model; DeLong test for removing brainstem",
     "limits": "Pooled genes, so not attributable to a single gene (R5). Full-model AUC is 0.928 in the abstract (b0007) and 0.982 in the results (b0067) for the same comparison: internal inconsistency."},
    {"finding_id": "SF2", "variables": "CCM genotype vs time to first CASH",
     "population_or_group": "cohort 2, n = 25", "status": "not_significant", "source_scope": "this_study", "evidence": ["E21", "E22"],
     "conditions": "Cox model adjusted for gender and first diagnosis age; depends_on_unread = Table S3",
     "limits": "Per-gene contrasts not visible; small sample."},
    {"finding_id": "SF3", "variables": "age vs number of large (>= 5 mm) CCM lesions",
     "population_or_group": "cohort 2, n = 25 (80 MRIs)", "status": "significant", "source_scope": "this_study", "evidence": ["E42"],
     "conditions": "r = 0.27, p = 0.017", "limits": "Within-disease burden, not a gene-disease relation."},
    {"finding_id": "SF4", "variables": "age vs number of large CCM lesions, by gene group",
     "population_or_group": "KRIT1, CCM2, PDCD10 and mutation-not-detected groups of cohort 2", "status": "significant",
     "source_scope": "this_study", "evidence": ["E43", "E49", "E44"],
     "conditions": "KRIT1 r = 0.75 (P < 0.001); not detected r = 0.53 (P = 0.004); CCM2 r = -0.84 (p = 0.019); PDCD10 not significant",
     "limits": "Repeated MRIs per patient; CCM2 n = 2 and authors suggest detection bias; 'worsened faster' slope difference not formally tested in the text."},
    {"finding_id": "SF5", "variables": "clinical characteristics, mutation detected vs not detected",
     "population_or_group": "cohort 1, n = 21; pooled genes", "status": "not_significant", "source_scope": "this_study", "evidence": ["E45"],
     "conditions": "Table 1 comparisons", "limits": "Pooled genes; small sample."},
    {"finding_id": "SF6", "variables": "younger diagnosis age vs risk of earlier first CASH",
     "population_or_group": "cohort 2, n = 25", "status": "reported_without_statistics", "source_scope": "this_study", "evidence": ["E46"],
     "conditions": "depends_on_unread = Table S3", "limits": "Statistics not given in the readable text."},
    {"finding_id": "SF7", "variables": "cumulative incidence of first CASH by age",
     "population_or_group": "cohort 2, n = 25", "status": "descriptive", "source_scope": "this_study", "evidence": ["E47"],
     "conditions": "0.160 until 19 years; depends_on_unread = Table S2", "limits": ""},
    {"finding_id": "SF8", "variables": "PDCD10 group vs age at onset",
     "population_or_group": "PDCD10 group, n = 2 probands (3 patients with MRI)", "status": "trend", "source_scope": "this_study",
     "evidence": ["E48"], "conditions": "not statistically significant", "limits": "n = 2."},
]

UNREAD_ATTACHMENTS = [
    {"name": "Table S1", "referenced_in": ["b0070", "b0114"]},
    {"name": "Table S2", "referenced_in": ["b0094", "b0115"]},
    {"name": "Table S3", "referenced_in": ["b0094", "b0116"]},
    {"name": "Figure 1-3 image pixels", "referenced_in": ["b0027", "b0068", "b0095"]},
]
