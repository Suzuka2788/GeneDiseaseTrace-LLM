"""Evidence adjudication for two saved model outputs; supplied XML is the source."""
import copy
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

from biomed.jats import parse_article

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT / 'archive' / 'outputs_evidence_audit'/'PMC10014009'
OUT.mkdir(parents=True,exist_ok=True)
A_DIR=ROOT / 'archive' / 'outputs_GPT_6.1_sol'/'PMC10014009'
B_DIR=ROOT / 'archive' / 'outputs_claude_Opus_5.5'/'PMC10014009'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def csvout(name,rows,fields=None):
    fields=fields or list(rows[0])
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for row in rows:
            w.writerow({k:json.dumps(row.get(k),ensure_ascii=False) if isinstance(row.get(k),(list,dict)) else row.get(k,'') for k in fields})

article=parse_article(ROOT/'.Input/100papers/PMC10014009.xml')
blocks={b['block_id']:b for b in article['blocks']}
A_entities=read(A_DIR/'entities.json'); A_pairs=read(A_DIR/'candidate_pairs.json')
A_mentions=read(A_DIR/'mentions.json'); A_excluded=read(A_DIR/'excluded_candidates.json')
B=read(B_DIR/'result.json'); B_entities=B['entities'];B_pairs=B['pairs']
B_mentions=list(csv.DictReader((B_DIR/'mentions.csv').open(encoding='utf-8-sig')))
AA={(p['gene_id'],p['disease_id']):p for p in A_pairs}
BB={(p['gene_id'],p['disease_id']):p for p in B_pairs}
BE={e['id']:e for e in B_entities}
def ev(bid,quote=None):
    text=blocks[bid]['text'];quote=quote or text
    assert quote in text,(bid,quote)
    return {'location':bid,'section':blocks[bid]['section'],'quote':quote,'start':text.index(quote),'end':text.index(quote)+len(quote)}

# Maps are decisions about identity and granularity, not based on equal ID numbers.
BMAP={'D01':'D01','D02':'D02','D03':'D03','D04':'D19','D05':'D04','D06':'D05',
      'D07':'D06','D08':'D21','D09':'D20','D11':'D07','D12':'D08','D13':'D09',
      'D14':'D10','D15':'D11','D16':'D12','D17':'D13','D18':'D14','D19':'D15',
      'D20':'D16','D25':'D17','D26':'D18','D21':'S01','D22':'S02','D23':'S03',
      'D24':'S04','D27':'S05','D28':'S06','D29':'S07','D30':'S08','D31':'S09',
      'D32':'S10','D33':'S11','D34':'S12','D35':'S13','D36':'S14','D37':'S15',
      'D38':'S16','D10':'S17','D39':'S18'}
BMAP.update({f'G{i:02d}':f'G{i:02d}' for i in range(1,9)})
REV_B={v:k for k,v in BMAP.items()}
REV_B['S19']='D34'

entities=copy.deepcopy(A_entities)
for e in entities:
    e['in_primary_matrix']=True
    e['reference_sequences_from_text']=[]
    e['review_state']='reviewed_with_limitations'
    if e['entity_type']=='gene':
        e['entity_subtype']='gene_with_product_mentions' if e['entity_id'] in ['G01','G05'] else 'gene'
    if e['entity_id']=='G01':e['reference_sequences_from_text']=['NG_012964.1','NC_000007.14']
    if e['entity_id']=='G02':e['reference_sequences_from_text']=['NG_016295.1','NC_000007.14']
    if e['entity_id']=='G03':e['reference_sequences_from_text']=['NG_008158.1','NC_000003.12']
    if e['entity_id']=='D20':
        e['original_names']=['vascular malformation']
        e['merge_basis']='宽泛类别；不把 intracranial vascular malformation 当作同义词。b0011 的抑制机制语句与 b0100 属此范围。'
        e['location']=['b0011','b0100']
        e['ambiguity']='机制背景指代尚需审慎；与颅内子类D21分开。'
entities.append(dict(paper_id=article['paper_id'],entity_id='D21',entity_type='disease',
    canonical_name='intracranial vascular malformation',original_names=['intracranial vascular malformation'],
    species='人类疾病定义语境',location=['b0011'],ambiguity='CCM的上位类别，但不是所有 vascular malformation 的同义词。',
    merge_basis='b0011 的原文定义；独立于 D20，不自动继承基因边。',entity_subtype='疾病家族/部位限定子类',
    database_id='',in_primary_matrix=True,reference_sequences_from_text=[],review_state='reviewed_with_limitations'))
for bid,rid in BMAP.items():
    if not rid.startswith('S'):continue
    b=BE[bid]
    aliases=list(b['surface_forms'])
    if rid=='S12':aliases=['Visual symptoms']
    entities.append(dict(paper_id=article['paper_id'],entity_id=rid,
        entity_type='phenotype' if b['category']=='phenotype' else 'symptom',
        canonical_name=b['name'],original_names=aliases,species='人类',location=list(b['locations']),
        ambiguity='辅助实体，不标为疾病，不进入主基因×疾病表。',
        merge_basis=b['merge_basis'] if rid!='S12' else '表1的概括症状类目；不与表2特定阳性视觉症状作严格同义合并。',
        entity_subtype=b['category'],database_id='',in_primary_matrix=False,
        reference_sequences_from_text=[],review_state='auxiliary_only'))
entities.append(dict(paper_id=article['paper_id'],entity_id='S19',entity_type='symptom',
    canonical_name='transient positive visual symptom',original_names=['Transient positive visual symptom'],
    species='人类',location=['b0082'],ambiguity='特定症状；保留Transient/positive限定，不与表1Visual symptoms作同义合并。',
    merge_basis='表2 K8 原文，最多属于广泛视觉症状类，不等同同义实体。',entity_subtype='symptom',database_id='',
    in_primary_matrix=False,reference_sequences_from_text=[],review_state='auxiliary_only'))
entities.sort(key=lambda e:(0 if e['entity_id'].startswith('G') else 1 if e['entity_id'].startswith('D') else 2,e['entity_id']))
EE={e['entity_id']:e for e in entities}

# Re-extract all supplied-text name spans; retain explicit role rather than treating
# gene-panel modifiers as disease occurrence evidence.
mentions=[]
for bid,b in blocks.items():
    hits=[]
    for e in entities:
        for alias in e['original_names']:
            for m in re.finditer(r'(?<![A-Za-z0-9])'+re.escape(alias)+r'(?![A-Za-z0-9])',b['text']):
                hits.append((m.start(),m.end(),e,alias))
    selected=[]
    for s,t,e,alias in sorted(hits,key=lambda x:(-(x[1]-x[0]),x[0])):
        if any(s<yy and t>xx for xx,yy,_,_ in selected):continue
        selected.append((s,t,e,alias))
    for s,t,e,alias in sorted(selected,key=lambda x:x[0]):
        role=e['entity_type'];tail=b['text'][t:]
        if alias=='MEKK3' or (alias=='KRIT1' and tail.startswith(' protein')):role='protein_product'
        if e['entity_id'] in ['D01','D02'] and re.match(r'[- ](?:associated genes|genes?\b|complexes\b|genotype\b|mutation genotypes\b)',tail):
            role='disease_name_used_in_gene_group_modifier'
        if e['entity_type']=='gene' and re.match(r' (?:group|variants?|patients?)\b',tail):role='gene_carrier_group_or_variant'
        mentions.append(dict(paper_id=article['paper_id'],entity_id=e['entity_id'],surface=b['text'][s:t],
            entity_type=e['entity_type'],role=role,location=bid,section=b['section'],start=s,end=t,
            context=b['text'],qualification=''))
def extra_mention(eid,bid,surface,role,qualification):
    text=blocks[bid]['text'];start=text.index(surface)
    if any(m['entity_id']==eid and m['location']==bid and m['start']==start for m in mentions):return
    mentions.append(dict(paper_id=article['paper_id'],entity_id=eid,surface=surface,entity_type=EE[eid]['entity_type'],
        role=role,location=bid,section=blocks[bid]['section'],start=start,end=start+len(surface),context=text,qualification=qualification))
for eid,bid,surface in [('D04','b0076','Spinal'),('D04','b0090','Spinal'),('D05','b0085','Cutaneous')]:
    extra_mention(eid,bid,surface,'table_cell_with_header','由 b0072 Non-cerebral CM 表头补足含义，不把解剖词单独当疾病。')
for bid in ['b0011','b0099']:
    extra_mention('D03',bid,'sporadic','elliptical_subtype','需要联合所在句 CCM 语境。')
extra_mention('D02','b0011','familial','elliptical_subtype','CCM is broadly divided into sporadic and familial categories.')
extra_mention('D06','b0070','recurrent symptomatic hemorrhage','contextual_event_reference','前句 Among the probands with mutations detected, six experienced CASH；只在此段回指，不把一般出血当全局别名。')
for e in entities:
    e['location']=sorted({m['location'] for m in mentions if m['entity_id']==e['entity_id']})

issues=[]
def issue(iid,kind,subject,a,b,verdict,decision,evidence,revision,limits=''):
    issues.append(dict(issue_id=iid,category=kind,subject=subject,result_A=a,result_B=b,
        verdict=verdict,decision=decision,evidence=evidence,location=sorted({x['location'] for x in evidence}),
        revision=revision,remaining_limits=limits))

issue('I01','identity','D20与D21：血管畸形层级','A D20合并 vascular malformation 与 intracranial vascular malformation',
    'B D08与D09分开','支持结果 B','部位限定子类不是同义名，应拆开。',
    [ev('b0011','Cerebral cavernous malformation (CCM) is an intracranial vascular malformation causing a collection of abnormally distended capillaries.'),
     ev('b0100','This component is likely critical for preventing vascular malformation.')],
    'A D20拆为修订D20与D21；新增8个主候选对，不自动继承边。')

# All 18 B-table-only items are tracked individually; A had already kept them outside
# the disease table, so these are not 18 newly discovered disease names.
for index,e in enumerate([x for x in entities if x['entity_id'].startswith('S') and x['entity_id']!='S19'],start=2):
    b_id=REV_B[e['entity_id']];category=BE[b_id]['category']
    found=[ev(loc) for loc in e['location'][:2]]
    issue(f'I{index:02d}','entity_scope',e['entity_id']+' '+e['canonical_name'],
        'A 在 excluded_candidates 中保留，未纳入疾病主表',
        f'B {b_id} 的 type=disease，category={category}，进入疾病笛卡尔积',
        '支持结果 A','按原任务区分疾病、症状与一般表型；保留辅助实体，不把这些名称当新疾病。',
        found,'修订实体类型为 '+e['entity_type']+'；辅助配对另存，不进入主基因×疾病表。')

issue('I20','alias','S12与S19：视觉症状粒度','A 排除记录中分别保留 Visual symptoms 与 Transient positive visual symptom',
    'B D34将二者合并','支持结果 A','原文没有把表1泛化症状类与K8的特定阳性症状定义为同义。',
    [ev('b0040'),ev('b0082')],'拆为辅助S12和S19；只保留类别/特定表现联系，不作严格同义合并。')
issue('I21','relation','G04 ZPLD1—D02 FCCM','uncertain','supported association background',
    '暂无法裁决','当前论文可确认“提出过该关联”，不能从这一个句子确认是有结果支持的关联还是假设。',
    [ev('b0098','F. Gianfrancesco et al. proposed that ZPLD1 mutation is associated with FCCM. 15')],
    '保留 uncertain/none，不画支持边；状态与A一致，但不据此否定B所指的潜在背景结果。',
    '严格限制当前论文，未调入被引研究15；需要该研究的结果细节才能进一步裁决。')
for n,g in enumerate(['G01','G02','G03'],start=22):
    issue(f'I{n:02d}','relation',g+'—D06 CASH','not_found，保留组间阴性片段','explicit_negative，限定首次CASH时点',
        '支持结果 A','B 的条件限定有价值，但正文只给基因型组间整体结论，不能确定每个单基因对比均为阴性。',
        [ev('b0021','Moreover, we determined whether CCM genotype was associated with the earlier occurrence of the first CASH, adjusting for gender and first CCM diagnosis age using Cox proportional hazards models.'),
         ev('b0094','The difference among the CCM mutation genotypes was not statistically significant (Table S3).')],
        '单基因对维持 not_found；另在study_findings保存组水平 explicit_negative，不丢失阴性结果。',
        'Table S3未提供，参照组、每基因HR、置信区间及各对比p值未知。')
for n,g in enumerate(['G01','G02','G03'],start=25):
    issue(f'I{n:02d}','relation',g+'—D03 散发CCM','not_found','uncertain',
        '支持结果 B','双打击背景和体细胞变异提供间接联系，但缺少指定基因—散发亚型的明确对应；属于未解决证据而非支持边。',
        [ev('b0098','In the 2-hit model, biallelic LOF in CCM genes, achieved by one somatic mutation in heterozygous germline mutation or two somatic mutations in wild-type gene, is required to initiate CCM formation.'),
         ev('b0026','Of the remaining 27 patients, six sporadic CCM patients with a wild-type FCCM gene, a single CCM lesion, and no family history of CCM were excluded.')],
        '改为uncertain/none；不把未检出胚系变异解释为反对体细胞变异，也不自动传播一般CCM关系。')
for n,g in enumerate(['G02','G03'],start=28):
    issue(f'I{n:02d}','relation',g+'—D20 广义血管畸形','not_found','uncertain',
        '支持结果 B','A漏记了三基因抑制血管畸形的机制语句；该句并非阴性，但也不够证明整个宽泛疾病类别的关系。',
        [ev('b0011','Despite the tremendous progress in understanding CCM, the explicit mechanisms underlying the vascular-specific manifestation and vascular malformation suppression of the three CCM genes remain unknown.')],
        '改为uncertain/none，保留宽泛疾病范围与机制证据不足的限制。')
for n,g in enumerate([f'G{i:02d}' for i in range(1,9)],start=30):
    issue(f'I{n:02d}','relation',g+'—D18 PLE','uncertain','not_found',
        '支持结果 A','实体含义未解决；在完整候选矩阵中保留身份不确定性，不能假装已知是哪一种疾病。',
        [ev('b0076')],'保留uncertain，不扩写PLE、不与OLE合并。')

issue('I38','provenance','G01/G02/G03—D02 causal 的证据归属','causal + source_scope=两者兼有，说明中限定因果来自背景',
    'causal + source_scope=both，说明中限定因果来自背景','两者均需修正',
    '文字解释均有重要限定；但单一字段把因果陈述与观察病例混在一起，易被下游读成作者新验证因果。',
    [ev('b0011','Familial CCM (FCCM) is an autosomal dominant disorder caused by mutations in three genes, KRIT1, CCM2, and PDCD10.'),
     ev('b0028','Cohort 1 consisted of nine patients with KRIT1 variants, two with CCM2 variants, two with PDCD10 variants, and eight with the mutation not detected (Table 1).')],
    'causal关系来源单列为背景引用；observational_context另外保留本研究变异病例及家系观察。不是撤销原关系。')
issue('I39','mention_role','疾病缩写作基因集合/复合物修饰语','mentions中部分CCM/FCCM默认疾病角色',
    'modifier已标记，但仍计入疾病提及数','两者均需修正',
    '可保留字符串，但“CCM genes/FCCM gene/CCM complexes”不是一次独立疾病病例描述，不能作关系支持。',
    [ev('b0005'),ev('b0098','LOF in CCM genes and GOF in MAP3K3 are mutually exclusive, and the researchers suggested that CCM complexes suppress the activity of MEKK3.')],
    '修订mentions增加 disease_name_used_in_gene_group_modifier；实体计数不等于病例或关系证据数。')
issue('I40','mention_role','MEKK3蛋白角色','A mentions明确标protein_product','B实体说明正确，但mentions中MEKK3为name且归gene实体',
    '支持结果 A','b0098的encoding关系能确定基因产物；不另建基因，但提及类型必须保存。',
    [ev('b0098','Moreover, gain-of-function (GOF) mutations in MAP3K3, encoding MEKK3, have been confirmed in sporadic CCM patients.')],
    '两次MEKK3提及明确标protein_product。')
issue('I41','shared_coverage','省略式疾病亚型与一般CM的部位回指','部分只按词面收集一般CM、sporadic等','部分记录sporadic省略，但一般CM回指未逐处消歧',
    '两者均需修正','不能把代词式CM每次均看成部位未指定的新疾病证据；也不能漏掉明显省略式的亚型。',
    [ev('b0011','CCM is broadly divided into sporadic and familial categories.'),
     ev('b0070','At the age of 52 years, a follow-up spine MRI revealed an increased size and prominent heterogeneous enhancement of T2 high signal intensity around the CM in the thoracic spinal cord.')],
    '补足省略式亚型提及；b0070的CM脊髓回指另记，不增加支持关系。')
issue('I42','shared_scope','年龄—病灶负担与PDCD10不显著','均在说明/部分关系中保留，非结构化独立结果','均未作单独结构化finding',
    '两者均需修正','年龄与病灶数是统计变量；不应压成基因是否导致疾病，但应保留以供证据复核。',
    [ev('b0094','The correlation coefficients of the KRIT1, Mutation not detected, and CCM2 groups were 0.75 (P < 0.001), 0.53 (P = 0.004), and - 0.84 (p = 0.019), respectively.'),
     ev('b0094','However, the correlation between age and the number of large CCMs was not statistically significant in the PDCD10 group.')],
    '另存带变量、分组和限定的study_findings；不新增基因—疾病correlation边。')
issue('I43','shared_coverage','无法检查图片和补充材料','均承认未读取','均承认未读取',
    '暂无法裁决','两模型的一致性不能排除附件中的共同遗漏。',
    [ev('b0114'),ev('b0115'),ev('b0116')],
    '明确覆盖盲区；不宣称完整含附件全文无遗漏。','原始XML仅有外部JPG/DOCX文件名。')
issue('I44','qualifier','左侧ACA梗死的侧别','A标准名保留left','B标准名不含left，但ambiguity中保留侧别',
    '支持结果 A','不是不同疾病身份；修订应在可导出的标准名或结构化限定字段中保留原文侧别，避免下游丢失。',
    [ev('b0077'),ev('b0093','ACA, anterior cerebral artery;')],
    'D16标准名保留left；不根据部位补入梗死病因。')
issue('I45','contextual_alias','recurrent symptomatic hemorrhage的局部回指','A作为一般事件排除，未在CASH提及中记此局部回指',
    'B列为CASH表面形式','两者均需修正','b0070紧接six experienced CASH之后可作局部回指；但不能当作对整篇所有症状性出血通用的严格别名。',
    [ev('b0070','Among the probands with mutations detected, six experienced CASH. Two patients experienced recurrent symptomatic hemorrhage and severe neurological sequelae.')],
    '按contextual_event_reference记录，附局部连接依据；不新增基因关系。')

# Contextual anaphora is separate from aliases, because CM is not globally spinal.
for m in mentions:
    if m['entity_id']=='D19' and m['location']=='b0070':
        m['qualification']='此段多处CM回指脊髓病灶；保留词面D19并另记referent，不当成所有CM部位未明。'
        m['contextual_referent']='D04'
    else:m['contextual_referent']=''

align=[]
for e in entities:
    rid=e['entity_id'];bid=REV_B.get(rid,'')
    aid=rid if rid.startswith('G') or (rid.startswith('D') and rid!='D21') else ('D20' if rid=='D21' else '')
    a_scope='主表' if aid else '排除/症状表型记录'
    alignment='same_identity'
    if rid in ['D20','D21']:alignment='A_one_to_many_split'
    if rid.startswith('S'):alignment='scope_difference_not_missing_name'
    if rid in ['S12','S19']:alignment='B_one_to_many_symptom_split'
    align.append(dict(revised_id=rid,canonical_name=e['canonical_name'],revised_type=e['entity_type'],
        A_id=aid,A_storage_scope=a_scope,B_id=bid,B_type=BE[bid]['type'] if bid else '',
        A_name=next((x['canonical_name'] for x in A_entities if x['entity_id']==aid),''),
        B_name=BE[bid]['name'] if bid else '',
        A_aliases=next((x['original_names'] for x in A_entities if x['entity_id']==aid),[]),
        B_aliases=BE[bid]['surface_forms'] if bid else [],
        A_species=next((x['species'] for x in A_entities if x['entity_id']==aid),''),
        B_species=BE[bid]['species'] if bid else '',
        alignment=alignment,in_primary_matrix=e['in_primary_matrix'],basis=e['merge_basis'],
        evidence=[ev(e['location'][0])] if e['location'] else [],ambiguity=e['ambiguity']))

source_normalize={'background':'背景引用','this_study':'本研究结果','both':'两者兼有','uncertain':'不确定'}
main_pairs=[]
for g in [e for e in entities if e['entity_type']=='gene']:
    for d in [e for e in entities if e['entity_id'].startswith('D')]:
        gid=g['entity_id'];did=d['entity_id']
        a=AA.get((gid,did)) if did!='D21' else None
        b=BB.get((gid,REV_B[did]))
        p=copy.deepcopy(a) if a else dict(paper_id=article['paper_id'],gene_id=gid,disease_id=did,
            status='not_found',relation_type='none',source_scope='不确定',evidence=[],location=[],
            reason='当前论文未将指定基因与颅内血管畸形这一上位疾病类别直接建立关系；不自动从CCM子类传播。',conditions='无足够关系证据，不是医学上无关联。')
        p['gene_name']=g['canonical_name'];p['disease_name']=d['canonical_name']
        p['evidence']=[ev(x['location'],x['quote']) for x in p['evidence']]
        p['A_status']=a['status'] if a else 'unresolved_due_to_entity_merge'
        p['B_status']=b['status']
        p['observational_context']=[]
        p['review_issues']=[]
        if did=='D02' and gid in ['G01','G02','G03']:
            p['evidence']=[ev('b0011','Familial CCM (FCCM) is an autosomal dominant disorder caused by mutations in three genes, KRIT1, CCM2, and PDCD10.')]
            p['source_scope']='背景引用'
            p['observational_context']=[ev('b0028')]
            if gid in ['G01','G03']:p['observational_context'].append(ev('b0070'))
            p['reason']='因果主张直接来自背景；本研究只提供检测到变异及家系病灶等观察，不作新的因果验证。'
        if did=='D03' and gid in ['G01','G02','G03']:
            p.update(status='uncertain',relation_type='none',source_scope='背景引用',
                evidence=[ev('b0098','In the 2-hit model, biallelic LOF in CCM genes, achieved by one somatic mutation in heterozygous germline mutation or two somatic mutations in wild-type gene, is required to initiate CCM formation.'),ev('b0026')],
                reason='体细胞双打击提供间接机制背景，但未明确指定基因与散发亚型对应；需要核实，不升级为支持。')
        if did=='D20' and gid in ['G01','G02','G03']:
            evidence=[ev('b0011','Despite the tremendous progress in understanding CCM, the explicit mechanisms underlying the vascular-specific manifestation and vascular malformation suppression of the three CCM genes remain unknown.')]
            if gid=='G01':evidence.append(ev('b0100','This component is likely critical for preventing vascular malformation.'))
            p.update(status='uncertain',relation_type='none',source_scope='背景引用',evidence=evidence,
                reason='有三基因抑制血管畸形的背景语句，但机制未知且疾病类别宽泛；不能作确定关联或因果。')
        if gid=='G04' and did=='D02':
            p['reason']='当前论文仅用 proposed 转述他人关联，没有叙述支持结果；暂无法裁决实证强度，保留待审核。'
        if gid=='G05' and did=='D02':p['source_scope']='背景引用'
        if did=='D06' and gid in ['G01','G02','G03']:
            p['evidence']=[ev('b0021','Moreover, we determined whether CCM genotype was associated with the earlier occurrence of the first CASH, adjusting for gender and first CCM diagnosis age using Cox proportional hazards models.'),ev('b0094','The difference among the CCM mutation genotypes was not statistically significant (Table S3).')]
            p['reason']='正文仅报告基因型组水平不显著，未给每基因对比；单基因—CASH状态维持not_found，组水平阴性单独保存。'
            p['conditions']='cohort 2, n=25；首次CASH发生时点；调整性别与首次CCM诊断年龄；S3缺失。'
        p['location']=sorted({x['location'] for x in p['evidence']})
        p['review_issues']=[i['issue_id'] for i in issues if (gid+'—'+did) in i['subject']]
        if did=='D02' and gid in ['G01','G02','G03']:p['review_issues'].append('I38')
        if did in ['D20','D21']:p['review_issues'].append('I01')
        main_pairs.append(p)

# Auxiliary symptom/phenotype table: preserve all extra names without inflating
# the disease inventory. No association is inferred from a carrier's symptom.
aux_pairs=[]
for g in [e for e in entities if e['entity_type']=='gene']:
    for s in [e for e in entities if e['entity_id'].startswith('S')]:
        b=BB[g['entity_id'],REV_B[s['entity_id']]]
        aux_pairs.append(dict(paper_id=article['paper_id'],gene_id=g['entity_id'],auxiliary_id=s['entity_id'],
            auxiliary_type=s['entity_type'],status='not_found',relation_type='none',source_scope='不确定',
            evidence=[],location=[],reason='全文未直接提出或检验指定单基因与该症状/表型的关系；个体共存、合并组不显著和病灶数—发作相关不等于单基因关系。',
            context_checked=[ev(x) for x in s['location']],B_status=b['status'],in_primary_matrix=False))

findings=[dict(finding_id='F01',status='explicit_negative',level='group_comparison',
    variables=['CCM genotype groups','earlier occurrence of first CASH'],
    gene_scope=['G01','G02','G03'],disease_scope=['D06'],source_scope='本研究结果',
    evidence=[ev('b0021','Moreover, we determined whether CCM genotype was associated with the earlier occurrence of the first CASH, adjusting for gender and first CCM diagnosis age using Cox proportional hazards models.'),ev('b0094','The difference among the CCM mutation genotypes was not statistically significant (Table S3).')],
    limits='总体基因型分组结果；不拆成每单基因阴性。n=25；S3未提供，具体比较和HR未解决。'),
 dict(finding_id='F02',status='reported_correlation',level='within_genotype_age_lesion_count',
    variables=['age','number of large CCM lesions'],gene_scope=['G01','G02'],disease_scope=['D01','D02'],source_scope='本研究结果',
    evidence=[ev('b0094','The correlation coefficients of the KRIT1, Mutation not detected, and CCM2 groups were 0.75 (P < 0.001), 0.53 (P = 0.004), and - 0.84 (p = 0.019), respectively.'),ev('b0101')],
    limits='KRIT1组r=.75，CCM2组r=-.84；是各组内年龄—病灶数关系，不是基因—疾病相关系数；不能由斜率大小推断正式的组间差异显著。'),
 dict(finding_id='F03',status='explicit_negative',level='within_genotype_age_lesion_count',
    variables=['age','number of large CCM lesions'],gene_scope=['G03'],disease_scope=['D01','D02'],source_scope='本研究结果',
    evidence=[ev('b0094','However, the correlation between age and the number of large CCMs was not statistically significant in the PDCD10 group.'),ev('b0095')],
    limits='仅为PDCD10组年龄—病灶数量无显著相关，不否定PDCD10—CCM/FCCM。'),
 dict(finding_id='F04',status='explicit_negative',level='pooled_genetic_test_group_comparison',
    variables=['Mutation detected vs Mutation not detected','clinical characteristics'],gene_scope=['pooled_panel'],disease_scope=[],source_scope='本研究结果',
    evidence=[ev('b0064','P-values were obtained from the comparison between Mutation detected group and Mutation not detected group.'),ev('b0066')],
    limits='表1多数临床特征比较按检出/未检出合并组；不能分配到每基因与每症状。'),
 dict(finding_id='F05',status='reported_association',level='pooled_marker_prediction',
    variables=['brainstem lesion location','mutation detection'],gene_scope=['pooled_panel'],disease_scope=['D02'],source_scope='本研究结果',
    evidence=[ev('b0068')],limits='位置预测面板检出，不是独立脑干疾病或各单基因关联。'),
 dict(finding_id='F06',status='descriptive_cooccurrence',level='individual_cases',
    variables=['variant carriers','comorbid diagnoses'],gene_scope=['G01','G02','G03'],disease_scope=['D04','D05','D11','D12','D13','D14','D15','D16','D17'],source_scope='本研究结果',
    evidence=[ev('b0070'),ev('b0074'),ev('b0075'),ev('b0076'),ev('b0077'),ev('b0082'),ev('b0085'),ev('b0090')],
    limits='病例记录不能作单基因对各共病的关联边。'),
 dict(finding_id='F07',status='background_association',level='lesion_burden_vs_seizure',
    variables=['large CCM lesion counts','early-onset seizure'],gene_scope=[],disease_scope=['D01'],source_scope='背景引用',
    evidence=[ev('b0102','However, Christine K. Fox et al. revealed that large CCM lesion (a least 5 mm) counts are more associated with early-onset seizure than total lesion counts. 11')],
    limits='病灶计数与发作的关系，不含指定基因，不能改成某基因—癫痫关系。')]

# Full aligned pair comparison includes equal statuses and scope-only differences.
comparisons=[]
for p in main_pairs:
    did=p['disease_id'];gid=p['gene_id'];a=AA.get((gid,did)) if did!='D21' else None;b=BB[gid,REV_B[did]]
    comparisons.append(dict(paper_id=article['paper_id'],gene_id=gid,revised_target_id=did,
        target_name=EE[did]['canonical_name'],target_type=EE[did]['entity_type'],
        A_gene_id=gid,A_target_id=did if a else 'D20 (conflated)',A_status=p['A_status'],
        B_gene_id=gid,B_target_id=REV_B[did],B_status=b['status'],
        comparison='entity_split' if not a else 'status_difference' if a['status']!=b['status'] else 'same_status',
        revised_status=p['status'],revised_relation_type=p['relation_type'],
        adjudication='; '.join(p['review_issues']) or '原文复核后保留；不以一致票数作证据。',
        evidence=p['evidence'],reason=p['reason'],in_primary_matrix=True))
for p in aux_pairs:
    sid=p['auxiliary_id'];gid=p['gene_id']
    comparisons.append(dict(paper_id=article['paper_id'],gene_id=gid,revised_target_id=sid,
        target_name=EE[sid]['canonical_name'],target_type=EE[sid]['entity_type'],A_gene_id=gid,
        A_target_id='辅助/排除名称记录',A_status='outside_disease_matrix',B_gene_id=gid,B_target_id=REV_B[sid],
        B_status=p['B_status'],comparison='scope_difference',revised_status=p['status'],revised_relation_type='none',
        adjudication='辅助实体单列，不算疾病遗漏或新增疾病。',evidence=p['context_checked'],reason=p['reason'],in_primary_matrix=False))

# Inspect original quotes/spans as well as revised ones. Existence is not semantic validation.
original_quote_audit=[]
for model,ps in [('A',A_pairs),('B',B_pairs)]:
    for p in ps:
        if model=='A': qs=[(x['location'],x['quote']) for x in p['evidence']]
        else:qs=[(re.search(r'b\d{4}',loc).group(),q) for loc,q in zip(p['location'],p['evidence'])]
        for bid,q in qs:
            original_quote_audit.append(dict(model=model,gene_id=p['gene_id'],target_id=p['disease_id'],
                location=bid,quote=q,exact_match=q in blocks[bid]['text']))

unresolved=[
 dict(id='U01',subject='ZPLD1—FCCM',state='uncertain',reason='proposed句未附结果细节，无法判断背景实证强度。',needed='被引研究15结果细节；当前任务不调用外部知识。'),
 dict(id='U02',subject='MAP3K3—FCCM',state='uncertain',reason='could be a novel cause及these genes指代不清。',needed='当前论文没有足够结果，不能用散发亚型补足。'),
 dict(id='U03',subject='KRIT1/CCM2/PDCD10—散发CCM',state='uncertain',reason='体细胞双打击与亚型对应为间接证据。',needed='指定基因和散发亚型直接对应证据。'),
 dict(id='U04',subject='三基因—广义vascular malformation',state='uncertain',reason='宽泛类别、机制未知/likely；范围不足。',needed='明确疾病范围与对应关系结果。'),
 dict(id='U05',subject='PLE',state='unresolved_identity',reason='全文及脚注没有展开；8个候选对保留uncertain。',needed='作者提供缩写定义或完整病历上下文。'),
 dict(id='U06',subject='动物Krit1/Ccm2/Pdcd10',state='unresolved_species',reason='仅写animal model，具体物种未注明。',needed='模型物种说明；现有边严格限动物背景。'),
 dict(id='U07',subject='首次CASH Cox分析',state='unresolved_per_gene_contrasts',reason='S3缺失，无法确认每基因参照组/HR/CI/p。',needed='ACN3-10-373-s001.docx中的S3。'),
 dict(id='U08',subject='覆盖盲区',state='missing_attachments',reason='3张图片像素与补充DOCX未提供，无法核查其中共同遗漏。',needed='原始JPG与补充DOCX。'),
 dict(id='U09',subject='KRTI1/CMM',state='contextual_typo_normalization',reason='上下文支持疑似排字错误合并，非数据库确认。',needed='出版社勘误或作者确认方可彻底消除疑义。')]

primary_ids={e['entity_id'] for e in entities if e['entity_id'].startswith('D')}
gene_ids={e['entity_id'] for e in entities if e['entity_id'].startswith('G')}
assert {(p['gene_id'],p['disease_id']) for p in main_pairs}=={(g,d) for g in gene_ids for d in primary_ids}
assert len(main_pairs)==len(gene_ids)*len(primary_ids)
assert all(x['exact_match'] for x in original_quote_audit)
assert all(blocks[m['location']]['text'][m['start']:m['end']]==m['surface'] for m in mentions)
assert all(blocks[m['block_id']]['text'][int(m['start']):int(m['end'])]==m['surface'] for m in B_mentions)
assert all(any(m['entity_id']==e['entity_id'] for m in mentions) for e in entities)
audit=dict(source_sha256=article['source_sha256'],A='outputs_GPT_6.1_sol',B='outputs_claude_Opus_5.5',
    input_hash_matches_B_manifest=article['source_sha256']==read(B_DIR/'manifest.json')['source_sha256'],
    original_A_pair_count=len(A_pairs),original_B_pair_count=len(B_pairs),
    revised_genes=len(gene_ids),revised_disease_and_candidate_count=len(primary_ids),
    revised_entity_types=dict(Counter(e['entity_type'] for e in entities)),
    revised_primary_pair_count=len(main_pairs),revised_status_counts=dict(Counter(p['status'] for p in main_pairs)),
    auxiliary_pair_count=len(aux_pairs),full_aligned_comparison_count=len(comparisons),
    compared_main_statuses=dict(Counter(p['comparison'] for p in comparisons if p['in_primary_matrix'])),
    original_quote_checks=dict(Counter(x['model'] for x in original_quote_audit)),all_original_quotes_found=True,
    revised_mentions=len(mentions),all_revised_mentions_exact=True,original_B_mentions=len(B_mentions),
    issues=len(issues),study_findings=len(findings),primary_cartesian_product_complete=True,
    limitations='这是对原始论文的模型证据复核和程序一致性校验，不是独立人工验证，不提供准确率/召回率。')
for name,obj in [('source_blocks.json',article),('revised_entities.json',entities),('revised_mentions.json',mentions),
                 ('entity_alignment.json',align),('adjudications.json',issues),('revised_pairs.json',main_pairs),
                 ('auxiliary_pairs.json',aux_pairs),('aligned_pair_comparison.json',comparisons),
                 ('study_findings.json',findings),('original_quote_audit.json',original_quote_audit),
                 ('unresolved.json',unresolved),('audit.json',audit)]:dump(name,obj)
(OUT/'source_blocks.txt').write_text('\n\n'.join(b['block_id']+' ['+b['section']+']\n'+b['text'] for b in article['blocks']),encoding='utf-8')
for name,rows in [('revised_entities.csv',entities),('revised_mentions.csv',mentions),('entity_alignment.csv',align),
                  ('adjudications.csv',issues),('revised_pairs.csv',main_pairs),('auxiliary_pairs.csv',aux_pairs),
                  ('aligned_pair_comparison.csv',comparisons),('study_findings.csv',findings),('unresolved.csv',unresolved)]:csvout(name,rows)

# A new graph uses the corrected primary identities only; model outputs stay intact.
edges=[dict(edge_id=f'R{n:02d}',**p) for n,p in enumerate([p for p in main_pairs if p['status']=='supported'],start=1)]
graph=dict(paper_id=article['paper_id'],nodes=[e for e in entities if e['in_primary_matrix']],edges=edges)
dump('revised_graph.json',graph)
csvout('revised_edges.csv',edges)

report='''# PMC10014009：两模型结果的原文证据裁决

**A = outputs_GPT_6.1_sol；B = outputs_claude_Opus_5.5。两份结果均是待核查主张，原始XML是证据来源。**

## 输入和覆盖

题目：Clinicoradiologic data of familial cerebral cavernous malformation with age-related disease burden。

直接重解析输入 `.Input/100papers/PMC10014009.xml`。输入哈希与B manifest及A原始记录一致；同一套b0001–b0117位置为可核查定位。检查标题、摘要、正文、两张表全部55行及脚注、三幅图注、补充说明。参考文献列表不抽实体；正文转述可作背景。仅链接的3张JPG及补充DOCX未提供，未读取其像素/实际表格，因此附件中的共同遗漏暂无法排除。所有引用是空白、Unicode规范化后的精确原文片段，原始文件不改。

## 先对齐实体

基因身份共8个对齐，无一方独有的单基因。人类KRIT1/CCM2/PDCD10与动物Krit1/Ccm2/Pdcd10分别保留；具体动物物种未知。MAP3K3编码MEKK3，后者按蛋白提及记录；KRTI1与KRIT1的上下文笔误合并均可保留但有标记。没有按数据库编号前缀、解剖名称或变异编号补入基因。

B的39个疾病/候选表项不等于39个疾病。18项为症状或表型，A已保留在排除记录，并非A完全漏提。修订统一实体表保留全部这些名称，但分为symptom/phenotype辅助表项，不混入主疾病矩阵。B中Visual symptoms与Transient positive visual symptom缺少严格同义依据，进一步拆开，辅助实体共19个。

A把vascular malformation与intracranial vascular malformation合并，需支持B的分层处理；修订为D20与D21。CCM、FCCM、散发CCM、一般CM、脊髓CM、皮肤CM仍分开，PLE不与OLE合并。

**修订计数：8个基因，20个疾病/复合病症，1个未解决诊断候选PLE，19个辅助症状/表型，共48个实体。主候选矩阵为8×21=168对；辅助矩阵另存8×19=152对，不算疾病关系。**

完整身份对照见 entity_alignment.csv；它包含每个统一ID的A/B映射、分拆、原文依据和主表纳入标记。数字相同的A/B疾病ID不视为同一实体。例如A D04（spinal CM）对应B D05；A D19（CM）对应B D04。

## 逐项差异与裁决

完整45项裁决见 adjudications.csv/json，每项含双方主张、原文位置、原句、裁决、修订和限制。下列按议题合并显示，文件中逐实体/逐关系分行保留：

|议题|裁决|原文依据与修订|
|---|---|---|
|颅内血管畸形 vs 广义血管畸形|支持结果 B|b0011 “an intracranial vascular malformation”；b0100 “preventing vascular malformation”。上下位关系不是同义，拆开。|
|B主疾病表中的16项症状、2项表型|支持结果 A|b0026、表1、表2及b0070；名称保留为辅助表，不当疾病。每个名称有单独裁决。|
|Visual symptoms与Transient positive visual symptom|支持结果 A|b0040 与 b0082；保留宽泛症状类和具体表现的区别。|
|ZPLD1—FCCM|暂无法裁决|b0098 “F. Gianfrancesco et al. proposed that ZPLD1 mutation is associated with FCCM.” 当前论文未提供结果细节；保持uncertain，不强迫赞同某模型的实证解释。|
|KRIT1/CCM2/PDCD10—CASH|支持结果 A|b0021研究基因型与首次CASH时点；b0094 “The difference among the CCM mutation genotypes was not statistically significant (Table S3).” 仅组间整体结果，不能对每基因赋explicit_negative。单基因对not_found；组阴性另存F01。|
|三个基因—散发CCM|支持结果 B|b0098双打击模型含two somatic mutations in wild-type gene；b0026散发病例胚系检测阴性是排除条件。存在间接但非特异证据，改uncertain，不画边。|
|CCM2/PDCD10—广义vascular malformation|支持结果 B|b0011提到三基因的vascular malformation suppression而机制未知。A的空证据not_found遗漏此语句；改uncertain。|
|8个基因—未定义PLE|支持结果 A|b0076 “FIAS and FBTCS, 51YO → PLE”；全文未展开。疾病身份不明，保持uncertain。|
|MEKK3提及角色|支持结果 A|b0098 “MAP3K3, encoding MEKK3”。B文字说明正确，但mentions没有保存protein角色；修订提及类型。|
|因果背景与本研究观察的字段混合|两者均需修正|b0011为背景caused by；b0028为患者变异检测。原解释均有限定，但source_scope字段需拆清。因果边来源标背景，本研究记录留在observational_context。|
|疾病缩写的基因集合修饰语、部位回指|两者均需修正|“CCM genes”“FCCM gene”不能算独立疾病病例证据；b0070的“CM in the thoracic spinal cord”须记录脊髓回指。完善提及角色，不增加边。|
|年龄—病灶数和合并组阴性结果|两者均需修正|b0094/b0095、b0064/b0066，原有说明不足以结构化追踪每个统计问题。另存F01–F07，不能压成单基因关系。|
|缺失图片/补充材料中的共同遗漏|暂无法裁决|b0114–b0116只有说明，外部文件未提供。保留覆盖限制。|

## 双方一致项也回到原文复核

10条原有共同supported边都有独立原句复核，并非因模型一致而通过。人类三基因—CCM来自b0011的明确LOF致CCM陈述；人类三基因—FCCM来自b0003/b0011的明确背景病因陈述；MAP3K3—散发CCM来自b0098的确认GOF变异和互斥模式，保守作association；动物三基因—CCM来自b0099的模型诱导语句，只限动物条件。不把动物模型致病推广成人类证据，也不推断模型一定是小鼠。

双方对KRIT1携带者的乳腺癌、甲状腺癌、弥漫性中线胶质瘤、肾上腺腺瘤、ACA梗死、OLE，以及各基因携带者的脊髓/皮肤CM，均未画支持边。已回查表2和b0070，仍只有个案共存，没有指定基因与这些疾病的关联或因果证据。维持not_found，不以共同结论当证据。

共同遗漏/误判风险的处理：

1. 保留年龄与病灶数、首次CASH时点、检出/未检出合并组等实际变量和研究条件，避免把统计问题改写成基因是否致病。
2. b0102的大病灶数—早发发作关联是病灶与症状关系，不涉及指定基因，不能补成基因—癫痫边。
3. 一般CM在K3脊髓语境中的回指及sporadic/familial省略式名称已补充角色。命中名称不能自动当新增疾病或独立证据。
4. 只检查了已提供XML范围；无法声称图片及S1–S3中没有新实体。未发现可从该可读范围明确证明遗漏的第9个具体基因；这不是无遗漏保证。

## 修订交付与完整性

'''
report+=f'主关系表168对：{dict(Counter(p["status"] for p in main_pairs))}。10条supported边，16对uncertain，142对not_found，0条可确认的逐单基因explicit_negative。组水平阴性仍在study_findings中。\n\n'
report+='''
- revised_entities.csv/json：48个统一实体及类型、原文名、物种、位置、歧义、合并依据；in_primary_matrix区分主表与辅助名称。
- revised_mentions.csv/json：原文精确提及、完整上下文、蛋白/修饰语/省略/回指角色。
- revised_pairs.csv/json：完整168对，含A/B原状态、修订状态、关系类型、来源、证据、条件与裁决编号。
- auxiliary_pairs.csv/json：152个辅助症状/表型对，不静默删除B的额外候选。
- aligned_pair_comparison.csv/json：320个对齐后的主/辅助组合，包含一致和不一致的状态；不是320个疾病关系。
- adjudications.csv/json：45项逐项裁决；entity_alignment.csv/json：全实体身份映射。
- study_findings.csv/json：7项统计/观察结果，阴性与条件不会丢失。
- unresolved.csv/json：9类未解决问题；source_blocks.txt/json：本轮原文定位。
- revised_graph.json/revised_edges.csv：只含主实体与10条supported关系，29个主节点全部保留。

所有A/B非空关系引用均在当前规范化原文找到；修订引用与提及字符偏移、完整笛卡尔积和唯一性通过校验。45条B关系引用存在不意味着45条语义判断正确；这些存在性校验不能代替证据裁决。原模型输出未覆盖。本次复核是模型分析与程序检查，不是独立人工验证，没有准确率、召回率或置信度分数。
'''
(OUT/'comparison_report.md').write_text(report,encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
