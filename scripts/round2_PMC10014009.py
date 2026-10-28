"""Second-round paper-specific review from original XML under skill v1.0.0.

No previous model-result file is loaded. Curated decisions below refer only to
source blocks; mechanical checks do not establish semantic correctness.
"""
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from biomed.io import write_csv, write_json
from biomed.jats import element_text, parse_article
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
RUN='round2_skill_v1.0.0'
OUT=ROOT/'outputs_GPT_6.1_sol'/RUN/'PMC10014009'
SOURCE=ROOT/'.Input/100papers/PMC10014009.xml'
SKILL=ROOT/'skills/biomed-gene-disease-evidence'

def run():
    if OUT.exists():
        raise FileExistsError(f'Choose a new run directory; existing review is preserved: {OUT}')
    a=parse_article(SOURCE)
    bs={b['block_id']:b for b in a['blocks']}
    raw=ET.parse(SOURCE).getroot()
    entities=[]

    def ent(eid,typ,name,forms,species,merge,ambiguity='',parent=None,qualifiers=None,primary=True,refs=None):
        entities.append(dict(paper_id=a['paper_id'],entity_id=eid,entity_type=typ,canonical_name=name,
            original_names=[],recognition_forms=forms,species=species,location=[],ambiguity=ambiguity,
            merge_basis=merge,parent_id=parent,qualifiers=qualifiers or {},in_primary_matrix=primary,
            database_id='',reference_sequences_from_text=refs or []))

    human='Homo sapiens；本研究为患者血样测序'
    ent('G01','gene','KRIT1',['KRIT1','KRTI1'],human,
        'b0003/b0014/b0019均列KRIT1、CCM2、PDCD10；b0005同一面板的KRTI1据此作疑似笔误合并。',
        '疑似排字错误尚无作者勘误确认；KRIT1 protein为产物提及。',refs=['NG_012964.1','NC_000007.14'])
    ent('G02','gene','CCM2',['CCM2'],human,'人类患者测序语境；不与动物Ccm2合并。',refs=['NG_016295.1','NC_000007.14'])
    ent('G03','gene','PDCD10',['PDCD10'],human,'人类患者测序语境；不与动物Pdcd10合并。',refs=['NG_008158.1','NC_000003.12'])
    ent('G04','gene','ZPLD1',['ZPLD1'],'人类FCCM背景语境，原句未显式标注物种','原文单一符号。','未纳入本研究面板；proposed关联的证据性质未解决。')
    ent('G05','gene','MAP3K3',['MAP3K3','MEKK3'],'人类散发CCM患者背景语境',
        'b0098明确MAP3K3, encoding MEKK3；后者作为同一基因的蛋白产物记录。','MEKK3不是第二个独立基因节点。')
    for eid,name in [('G06','Krit1'),('G07','Ccm2'),('G08','Pdcd10')]:
        ent(eid,'gene',name,[name],'非人动物模型；具体物种未注明',
            'b0099明确CCM animal model，按实验范围与人类测序节点分开。',
            '不根据大小写猜测小鼠；具体物种与跨物种映射未确认。')
    ent('D01','disease','cerebral cavernous malformation',
        ['Cerebral cavernous malformation','cerebral cavernous malformation','CCM','CCMs','CMM'],
        '人类；b0099另用于动物模型',
        'b0011、图注与表脚注明确CCM；CCMs为复数；CMM仅在b0099紧接CCM治疗句，据上下文作疑似笔误。',
        'CMM合并未经作者勘误；疾病作基因集合修饰语的提及不算病例证据。',parent='D21')
    ent('D02','disease','familial cerebral cavernous malformation',
        ['Familial cerebral cavernous malformation','familial cerebral cavernous malformation','Familial CCM','familial CCM','FCCM'],
        '人类','b0003/b0011展开FCCM；临床疑似和基因确诊分组以qualifier区分。',parent='D01')
    ent('D03','disease','sporadic cerebral cavernous malformation',['sporadic CCM','sporadic CCMs'],
        '人类','b0011明确区分sporadic/familial类别；不是FCCM别名。',parent='D01')
    ent('D04','disease','spinal cavernous malformation',['spinal cavernous malformation','spinal CM','Spinal CM'],
        '人类','b0016与表格部位语境；Spinal单元格需联合Non-cerebral CM表头。',parent='D19')
    ent('D05','disease','cutaneous cavernous malformation',['cutaneous CM','Cutaneous CM'],
        '人类','b0016与表格部位语境；Cutaneous单元格需联合Non-cerebral CM表头。',parent='D19')
    ent('D06','clinical_event','cavernous angioma with symptomatic hemorrhage',
        ['cavernous angioma with symptomatic hemorrhage','cavernous angiomas with a symptomatic hemorrhage',
         'cavernous angiomas with the occurrence of symptomatic hemorrhage','CASH'],
        '人类','b0016/b0021及表下注释展开CASH。',
        '本轮明确纳入主矩阵的病变伴症状性出血复合事件；不与所有CCM或一般出血合并。',
        qualifiers={'scope_policy':'named_clinical_event_in_primary_matrix'})
    ent('D07','disease','small vessel disease',['small vessel disease'],'人类','原文诊断名称，排除病例也提取。')
    ent('D08','disease','diffuse axonal injury',['diffuse axonal injury'],'人类','原文具名损伤，排除病例也提取。')
    ent('D09','disease','intracerebral hemorrhage',['intracerebral hemorrhages'],'人类',
        '原文具名脑内出血病症，保留多发复发且无CCM的条件。',qualifiers={'multiple':True,'recurrent':True,'without_CCM_lesions':True})
    ent('D10','disease','developmental venous anomaly',['developmental venous anomaly'],'人类',
        'b0026名称明确；否定存在仍提取实体。','队列无人患病，不代表基因关联阴性。')
    ent('D11','disease','tumor',['tumor','tumors','Tumor','tumorous condition'],'人类',
        '宽泛肿瘤类，不把各具体肿瘤归为其别名。','tumorous condition为当时影像疑诊，不能改成病理确诊。')
    for eid,name,surface in [('D12','breast cancer','Breast cancer'),('D13','thyroid cancer','Thyroid cancer'),
                             ('D15','adrenal adenoma','Adrenal adenoma')]:
        ent(eid,'disease',name,[surface],'人类','表2具名共病；不与肿瘤总类合并。',parent='D11')
    ent('D14','disease','diffuse midline glioma',['diffuse midline glioma','Diffuse midline glioma'],'人类',
        'b0070活检与表2同一K3病例对应；WHO grade IV为分级。',parent='D11',qualifiers={'WHO_grade':'IV'})
    ent('D16','disease','left anterior cerebral artery infarction',['Left ACA infarction'],'人类',
        'b0093展开ACA=anterior cerebral artery；保留Left限定，不推断病因。',qualifiers={'laterality':'left'})
    ent('D17','disease','occipital lobe epilepsy',['OLE','occipital lobe epilepsy'],'人类','b0093明确展开OLE。')
    ent('D18','ambiguous','PLE',['PLE'],'人类','原文诊断缩写未定义，独立保留。',
        '不能补成某种癫痫，不能与OLE合并；本轮纳入候选矩阵，identity未解决。')
    ent('D19','disease','cavernous malformation',['cavernous malformation','CM'],'人类',
        '表1/表2脚注定义CM；一般类别与脑、脊髓、皮肤类型分开。','部位可由上下文补足的CM提及另作回指，不一律作部位未明。')
    ent('D20','disease','vascular malformation',['vascular malformation'],'人类/一般机制描述',
        '宽泛血管畸形类；不与部位限定的intracranial类别合并。','b0011抑制机制未知；b0100为蛋白功能推测。')
    ent('D21','disease','intracranial vascular malformation',['intracranial vascular malformation'],'人类疾病定义',
        'b0011直接用于定义CCM；与更广泛vascular malformation是层级关系。',parent='D20')
    symptom_specs=[
        ('S01','seizure',['Seizure','seizure','seizures']),
        ('S02','focal impaired awareness seizure',['FIAS','focal impaired awareness seizure']),
        ('S03','focal to bilateral tonic-clonic seizure',['FBTCS','focal to bilateral tonic-clonic seizure']),
        ('S04','emotional seizure',['Emotional seizure']),('S05','headache',['Headache','headache','Nonspecific headache']),
        ('S06','neck pain',['neck pain']),('S07','dizziness',['Dizziness','dizziness']),
        ('S08','weakness',['Weakness','weakness','sided weakness']),('S09','dysarthria',['Dysarthria']),
        ('S10','facial palsy',['Facial palsy']),('S11','diplopia',['Diplopia','diplopia','binocular diplopia']),
        ('S12','visual symptoms',['Visual symptoms']),('S13','visual disturbance',['Visual disturbance']),
        ('S14','central vertigo',['Central vertigo']),('S15','drowsy mentality',['drowsy mentality']),
        ('S16','decreased mentality',['Decreased mentality']),
        ('S19','transient positive visual symptom',['Transient positive visual symptom'])]
    for eid,name,forms in symptom_specs:
        ent(eid,'symptom',name,forms,'人类',
            '按原文症状/发作类型记录；全称缩写仅按表2脚注；词内限定保留在提及表，不当成疾病诊断。',
            '不进入主疾病矩阵；不根据发作补入癫痫诊断。',primary=False)
    ent('S17','phenotype','cerebral microbleeds',['cerebral microbleeds'],'人类','b0026作为small vessel disease的影像表现。',primary=False)
    ent('S18','phenotype','neurological sequelae',['severe neurological sequelae'],'人类','b0070为出血后的非特异后遗症。',primary=False)
    entities.sort(key=lambda e:(e['entity_id'][0],e['entity_id']))
    E={e['entity_id']:e for e in entities}

    # Extract exact names with full paragraph/row context. Longer phrases take
    # precedence over embedded umbrella names; local anaphora is handled explicitly.
    mentions=[]
    for bid,b in bs.items():
        hits=[]
        for e in entities:
            for form in e['recognition_forms']:
                for m in re.finditer(r'(?<![A-Za-z0-9])'+re.escape(form)+r'(?![A-Za-z0-9])',b['text']):
                    hits.append((m.start(),m.end(),e['entity_id']))
        chosen=[]
        for s,t,eid in sorted(hits,key=lambda h:(-(h[1]-h[0]),h[0])):
            if any(s<yy and t>xx for xx,yy,_ in chosen):continue
            chosen.append((s,t,eid))
        for s,t,eid in sorted(chosen):
            form=b['text'][s:t];role=E[eid]['entity_type'];tail=b['text'][t:]
            qualifier={};ref=''
            if form=='MEKK3' or (form=='KRIT1' and tail.startswith(' protein')):role='protein_product'
            if eid[0]=='G' and re.match(r' (?:group|variants?|patients?)\b',tail):role='gene_carrier_group_or_variant'
            if eid in ['D01','D02'] and re.match(r'[- ](?:associated genes|genes?\b|complexes\b|genotype\b|mutation genotypes\b)',tail):
                role='disease_name_in_gene_group_modifier'
            if eid=='D19' and bid in ['b0016','b0070']:
                eid='D04';role='contextual_anaphora';ref='D04'
                qualifier={'basis':'同句/段spinal cavernous malformation或thoracic spinal cord语境；不是全局CM别名。'}
            if form=='Nonspecific headache':qualifier['nonspecific']=True
            if form=='sided weakness':qualifier['sided']=True
            if form=='binocular diplopia':qualifier['binocular']=True
            if eid=='S19':qualifier.update(transient=True,positive=True)
            mentions.append(dict(paper_id=a['paper_id'],entity_id=eid,surface=form,entity_type=E[eid]['entity_type'],
                mention_role=role,location=bid,section=b['section'],start=s,end=t,context=b['text'],
                contextual_referent=ref,qualifiers=qualifier))
    def extra(eid,bid,surface,role,why):
        s=bs[bid]['text'].index(surface);t=s+len(surface)
        if any(m['entity_id']==eid and m['location']==bid and m['start']==s for m in mentions):return
        mentions.append(dict(paper_id=a['paper_id'],entity_id=eid,surface=surface,entity_type=E[eid]['entity_type'],
            mention_role=role,location=bid,section=bs[bid]['section'],start=s,end=t,context=bs[bid]['text'],
            contextual_referent=eid,qualifiers={'basis':why}))
    for eid,bid,form in [('D04','b0076','Spinal'),('D04','b0090','Spinal'),('D05','b0085','Cutaneous')]:
        extra(eid,bid,form,'table_cell_with_header','需联合b0072的Non-cerebral CM列，不将孤立解剖词当疾病。')
    extra('D03','b0011','sporadic','elliptical_subtype','CCM divided into sporadic and familial categories。')
    extra('D02','b0011','familial','elliptical_subtype','同句CCM类别省略；不是全局别名。')
    extra('D03','b0099','sporadic','elliptical_subtype','sporadic and familial CCM共享后置CCM。')
    extra('D06','b0070','recurrent symptomatic hemorrhage','contextual_anaphora','紧接six experienced CASH；仅作此段事件回指，不作所有出血的别名。')
    mentions.sort(key=lambda m:(m['location'],m['start'],m['entity_id']))
    for n,m in enumerate(mentions,1):m['mention_id']=f'M{n:04d}'
    for e in entities:
        ms=[m for m in mentions if m['entity_id']==e['entity_id']]
        e['original_names']=sorted({m['surface'] for m in ms})
        e['location']=sorted({m['location'] for m in ms})
        e['mention_ids']=[m['mention_id'] for m in ms]
        del e['recognition_forms']
        assert ms,e['entity_id']
    raw_names=[]
    for eid,surface in sorted({(m['entity_id'],m['surface']) for m in mentions}):
        ms=[m for m in mentions if m['entity_id']==eid and m['surface']==surface]
        raw_names.append(dict(paper_id=a['paper_id'],surface=surface,entity_id=eid,entity_type=E[eid]['entity_type'],
            locations=sorted({m['location'] for m in ms}),mention_ids=[m['mention_id'] for m in ms],
            context_examples=[{'location':m['location'],'context':m['context']} for m in ms[:2]]))

    excluded=[]
    exclusion_specs={
        'gene_group':['CCM genes','FCCM gene','CCM-associated genes','CCM complexes'],
        'database_or_guideline':['HGMD','The Genome Aggregation Database','Korean Reference Genome database','KRGDB','ACMG'],
        'software':['FSPLICE','NNSplice','NetGene2','SPSS','RStudio'],
        'classification_or_variant_code':['PVS1','PM2','PP1','PP4','IVS8','WHO grade IV','Zabramski type IV'],
        'general_event_or_state':['recent hemorrhage','hemorrhage','symptomatic','asymptomatic','disease burden'],
        'imaging_or_general_phenotype':['blooming artifacts','lesion counts','large CCMs','multiple lesions'],
        'anatomy':['brainstem','Brainstem','Cerebellum','Cortex/Subcortex','Frontal','Temporal','Lateral temporal',
                   'Medial temporal','Parietal','Occipital','Basal ganglia','Thalamus','pons','medulla oblongata',
                   'motor cortex','occipital cortex','frontal cortex','hindbrain','thoracic spinal cord'],
    }
    for kind,names in exclusion_specs.items():
        for name in names:
            occurrences=[]
            for bid,b in bs.items():
                for m in re.finditer(r'(?<![A-Za-z0-9])'+re.escape(name)+r'(?![A-Za-z0-9])',b['text']):
                    occurrences.append({'location':bid,'surface':m.group(),'start':m.start(),'end':m.end(),'context':b['text']})
            if occurrences:
                excluded.append(dict(surface=name,kind=kind,occurrences=occurrences,
                    reason='不作为独立基因或疾病。具名临床事件CASH、具名症状与表型已另行记录；一般词、解剖位置和工具/编号不补成实体。'))

    # Preserve the source table structure as well as the textual block index.
    tables=[]
    for t in raw.findall('.//table-wrap'):
        rows=[]
        for row in t.findall('.//tr'):
            rows.append([{'text':element_text(c),'rowspan':c.get('rowspan','1'),'colspan':c.get('colspan','1'),'cell_tag':c.tag}
                         for c in row if c.tag in ['th','td']])
        tables.append({'xml_id':t.get('id'),'label':element_text(t.find('label')),
            'caption':element_text(t.find('caption')),'rows':rows,'footnotes':element_text(t.find('table-wrap-foot'))})
    table1_columns=['characteristic','All (n=21)','KRIT1 (n=9)','CCM2 (n=2)','PDCD10 (n=2)',
                    'Mutation detected total (n=13)','Mutation not detected (n=8)']
    table2_columns=bs['b0072']['text'].split(' | ')
    table_cells=[]
    group=None
    for bid,b in bs.items():
        if b['content_type']!='table_row':continue
        cells=b['text'].split(' | ')
        if 'Table 1' in b['section'] and len(cells)==7 and bid not in ['b0052']:
            for col,value in zip(table1_columns,cells):table_cells.append({'location':bid,'table':'Table 1','column':col,'row_label':cells[0],'value':value,'gene_scope':None})
        if bid in ['b0073','b0084','b0087']:group={'b0073':'G01','b0084':'G02','b0087':'G03'}[bid]
        if 'Table 2' in b['section'] and len(cells)==14 and bid not in ['b0072','b0073','b0084','b0087']:
            for col,value in zip(table2_columns,cells):table_cells.append({'location':bid,'table':'Table 2','column':col,'row_label':cells[0],'value':value,'gene_scope':group})

    # Each evidence record has its own assertion kind and source, independent of
    # the row-level relationship classification.
    evidences=[]
    def evidence(bid,quote,scope,kind,supports,conditions=None):
        assert quote in bs[bid]['text'],(bid,quote)
        key=(bid,quote,scope,kind,supports,json.dumps(conditions,sort_keys=True))
        for x in evidences:
            if x['_key']==key:return x['evidence_id']
        start=bs[bid]['text'].index(quote)
        record=dict(evidence_id=f'EV{len(evidences)+1:03d}',paper_id=a['paper_id'],quote=quote,location=bid,
            section=bs[bid]['section'],start=start,end=start+len(quote),source_scope=scope,
            assertion_kind=kind,supports=supports,conditions=conditions or {},_key=key)
        evidences.append(record)
        return record['evidence_id']
    def whole(bid,scope,kind,supports,conditions=None):return evidence(bid,bs[bid]['text'],scope,kind,supports,conditions)
    bg='背景引用';own='本研究结果'
    ev_ccm=evidence('b0011','These prior studies demonstrated that the products of the three genes (KRIT1, CCM2, and PDCD10) are associated with CCM form complexes. Loss of function (LOF) of these genes leads to the formation of CCM.',
        bg,'background_relation_statement','三个人类基因的LOF导致CCM；these genes由前句逐一指定。',{'species':'human context','variant_class':'LOF'})
    ev_fccm=evidence('b0011','Familial CCM (FCCM) is an autosomal dominant disorder caused by mutations in three genes, KRIT1, CCM2, and PDCD10.',
        bg,'background_relation_statement','三个人类基因与FCCM的明确背景因果陈述。')
    ev_cases=evidence('b0028','Cohort 1 consisted of nine patients with KRIT1 variants, two with CCM2 variants, two with PDCD10 variants, and eight with the mutation not detected (Table 1).',
        own,'reported_result','病例中各基因变异检出及未检出分组；不是本研究新做的因果验证。',{'cohort':1,'n':21})
    ev_family=evidence('b0070','The family members of one patient with a KRIT1 variant (K7), and two patients with PDCD10 variants (P1 and P2), received genetic testing, and four family members with the same variant as the proband were detected. Furthermore, these family members had CCM lesions confirmed by brain MRI.',
        own,'reported_result','同变异亲属检出CCM病灶的家系观察；不替代背景因果来源。')
    ev_map=evidence('b0098','Moreover, gain-of-function (GOF) mutations in MAP3K3, encoding MEKK3, have been confirmed in sporadic CCM patients.',
        bg,'background_relation_statement','明确散发CCM患者中的MAP3K3功能获得变异报告。',{'variant_class':'GOF','disease_subtype':'sporadic CCM'})
    ev_exclusive=evidence('b0098','LOF in CCM genes and GOF in MAP3K3 are mutually exclusive, and the researchers suggested that CCM complexes suppress the activity of MEKK3.',
        bg,'interpretation','互斥模式及机制解释与前句联合支持保守association；不独立证明因果。')
    ev_animal=evidence('b0099','Some preclinical studies have demonstrated that the CCM animal model induced by Krit1, Ccm2, or Pdcd10 heterozygous loss in the immediate postnatal period, tended to harbor lesions in the hindbrain.',
        bg,'background_relation_statement','三个动物模型基因的杂合缺失诱导CCM模型。',{'species':'animal, unspecified','timing':'immediate postnatal period','intervention':'heterozygous loss'})
    ev_zpld=evidence('b0098','Second, other gene mutations could induce FCCM despite the rarity of the disease. F. Gianfrancesco et al. proposed that ZPLD1 mutation is associated with FCCM. 15',
        bg,'interpretation','当前论文提出的背景关联；could/proposed语境未提供结果细节，实证性质尚待审核。')
    ev_hypothesis=evidence('b0098','Therefore, the mutation of these genes could be a novel cause of FCCM.',
        bg,'hypothesis','FCCM病因推测，these genes指代未完全明确，不从散发CCM传播。')
    ev_twohit=evidence('b0098','In the 2-hit model, biallelic LOF in CCM genes, achieved by one somatic mutation in heterozygous germline mutation or two somatic mutations in wild-type gene, is required to initiate CCM formation.',
        bg,'background_relation_statement','一般CCM双打击机制；未逐一指定散发CCM基因关系。')
    ev_sporadic=evidence('b0026','Of the remaining 27 patients, six sporadic CCM patients with a wild-type FCCM gene, a single CCM lesion, and no family history of CCM were excluded.',
        own,'reported_result','排除病例的检测/临床条件；不等同于对体细胞机制的阴性检验。')
    ev_suppression=evidence('b0011','Despite the tremendous progress in understanding CCM, the explicit mechanisms underlying the vascular-specific manifestation and vascular malformation suppression of the three CCM genes remain unknown.',
        bg,'interpretation','宽泛血管畸形抑制功能的背景描述；机制未知、具体疾病范围未清。')
    ev_likely=evidence('b0100','Exon 12 is responsible for a particular portion of the KRIT1 protein ankyrin component. 19 This component is likely critical for preventing vascular malformation.',
        bg,'interpretation','KRIT1蛋白组分功能推测；不能证明对所有血管畸形的因果。')
    ev_ple=whole('b0076',own,'descriptive_cooccurrence','K3行包含未展开PLE；身份不确定，不推断其扩写。')
    ev_cox_aim=evidence('b0021','Moreover, we determined whether CCM genotype was associated with the earlier occurrence of the first CASH, adjusting for gender and first CCM diagnosis age using Cox proportional hazards models.',
        own,'aim','首次CASH时间的基因型比较问题及调整变量；目的不是结果。')
    ev_cox_null=evidence('b0094','The difference among the CCM mutation genotypes was not statistically significant (Table S3).',
        own,'negative_result','基因型组间首次CASH时点未见显著差异；不能拆成单基因阴性。',
        {'cohort':2,'n':25,'endpoint':'earlier first CASH','adjustment':['gender','first CCM diagnosis age'],'per_gene_contrasts':'S3 unavailable'})

    genes=[e for e in entities if e['entity_type']=='gene']
    targets=[e for e in entities if e['in_primary_matrix'] and e['entity_type']!='gene']
    pair_lookup={}
    for g in genes:
        for d in targets:
            pair_lookup[g['entity_id'],d['entity_id']]=dict(paper_id=a['paper_id'],pair_id=g['entity_id']+'__'+d['entity_id'],
                gene_id=g['entity_id'],disease_id=d['entity_id'],status='not_found',relation_type='none',source_scope='不确定',
                evidence_ids=[],evidence=[],location=[],observational_context_ids=[],context_checked_ids=[],
                reason='在已检查的全部XML标题、摘要、正文、表格、脚注、图注和补充说明中，没有找到足够的指定实体对关系证据。',
                conditions='只限已读范围；没有检查缺失图片像素与补充DOCX，不代表医学上无关联。',unresolved_reason='')
    def judge(g,d,status,rel,scope,ids,reason,conditions='',unresolved='',observed=None,checked=None):
        pair_lookup[g,d].update(status=status,relation_type=rel,source_scope=scope,evidence_ids=ids,
            reason=reason,conditions=conditions,unresolved_reason=unresolved,
            observational_context_ids=observed or [],context_checked_ids=checked or [])
    for gid in ['G01','G02','G03']:
        judge(gid,'D01','supported','causal',bg,[ev_ccm],
            '原文在一般CCM层面明确将三基因LOF与形成CCM相连，不是由FCCM关系自动向上推广。',
            '背景机制陈述；不指任意变异或所有散发病例；未独立阅读被引研究。')
        judge(gid,'D02','supported','causal',bg,[ev_fccm],
            '背景直接陈述FCCM由指定基因突变导致；本研究病例结果另存观察，不误写成本研究新验证因果。',
            '限原文致病变异语境；未检出变异病例不排除关系。',observed=[ev_cases]+([ev_family] if gid in ['G01','G03'] else []))
        judge(gid,'D03','uncertain','none',bg,[ev_twohit],
            '双打击背景包含野生型中的两次体细胞突变，但原文未明确逐一指定该基因与散发亚型；关联映射未解决。',
            '不由一般CCM自动传播到散发亚型；排除病例的野生型面板结果不能当反证。',
            unresolved='subtype_specificity_and_gene_group_reference',checked=[ev_sporadic])
        judge(gid,'D20','uncertain','none',bg,[ev_suppression]+([ev_likely] if gid=='G01' else []),
            '存在三基因抑制血管畸形的背景语句，但类别过宽、机制未知；KRIT1另有likely功能解释，均不足确定全类关系。',
            unresolved='broad_disease_scope_and_mechanistic_interpretation')
        judge(gid,'D06','not_found','none',own,[],
            '现有阴性结果针对基因型分组的首次CASH时点，未提供指定单基因对比；没有足够证据把单基因关系标阳性或阴性。',
            'cohort2 n=25；调整性别与首次CCM诊断年龄；S3缺失。',checked=[ev_cox_aim,ev_cox_null])
    judge('G04','D02','uncertain','none',bg,[ev_zpld],
        '结合前句could与背景proposed关联，当前论文不足以区分实证结果转述与提出假设；不单凭一个词判阴性或支持。',
        '本研究未测ZPLD1；没有引入被引文献作为新证据。',unresolved='background_assertion_empirical_basis_unresolved')
    judge('G05','D03','supported','association',bg,[ev_map,ev_exclusive],
        '联合确认的功能获得变异、特定散发患者范围及与CCM基因LOF的互斥模式，超过一般共现；保守作背景关联。',
        '没有升级为本研究因果；不传播到家族性或整个上位疾病。')
    judge('G05','D02','uncertain','none',bg,[ev_hypothesis],
        'could为FCCM病因假设，these genes指代含糊；明确的MAP3K3变异结果仅对应散发亚型。',
        unresolved='hypothesis_and_ambiguous_gene_reference',checked=[ev_map])
    for gid in ['G06','G07','G08']:
        judge(gid,'D01','supported','causal',bg,[ev_animal],
            '原文明确用指定动物基因杂合缺失诱导CCM动物模型；支持严格限定的模型因果。',
            '动物具体物种未知；出生后早期杂合缺失；不等同人类致病。')
    for gid in [e['entity_id'] for e in genes]:
        judge(gid,'D18','uncertain','none','不确定',[ev_ple],
            '诊断候选PLE在全文未定义，实体身份尚未解决；uncertain来自身份，不暗示已有弱关联。',
            unresolved='disease_identity')

    # Potential false positives: retain exact records, but no edge from co-occurrence.
    for did,bid in [('D11','b0070'),('D12','b0074'),('D13','b0075'),('D14','b0076'),
                    ('D15','b0077'),('D16','b0077'),('D17','b0082')]:
        x=whole(bid,own,'descriptive_cooccurrence','KRIT1携带者的共病记录，不证明基因与该共病关系。')
        p=pair_lookup['G01',did];p['context_checked_ids']=[x]
        p['reason']='KRIT1变异携带者存在该诊断/肿瘤的病例记录，没有指定基因与该疾病的关联检验或明确关系主张。'
    for gid,did,bid in [('G01','D04','b0076'),('G03','D04','b0090'),('G02','D05','b0085')]:
        x=whole(bid,own,'descriptive_cooccurrence','按表2基因分组和Non-cerebral CM列连接的个案共存。')
        p=pair_lookup[gid,did];p['context_checked_ids']=[x]
        p['reason']='表2对应基因携带者有此部位CM，仅个体共存；未把一般FCCM因果传播到该部位亚型。'

    findings=[]
    def finding(fid,variables,groups,status,ids,limits):
        findings.append(dict(finding_id=fid,variables=variables,population_or_group=groups,status=status,
            source_scope=own,evidence_ids=ids,conditions={},limits=limits))
    finding('F01',['CCM genotype group','earlier first CASH'],'cohort2 n=25','explicit_negative',
        [ev_cox_aim,ev_cox_null],'组间结论；不拆成每基因阴性。S3具体参照组、HR、CI和p值缺失。')
    ev_age=evidence('b0094','The correlation coefficients of the KRIT1, Mutation not detected, and CCM2 groups were 0.75 (P < 0.001), 0.53 (P = 0.004), and - 0.84 (p = 0.019), respectively.',
        own,'reported_result','三个分组内的年龄—大病灶数量相关。')
    ev_pd_age=evidence('b0094','However, the correlation between age and the number of large CCMs was not statistically significant in the PDCD10 group.',
        own,'negative_result','仅PDCD10组内年龄—病灶数无显著相关，不否定PDCD10—FCCM/CCM。')
    ev_fig3=whole('b0095',own,'reported_result','图3图注的分组趋势及不显著描述。')
    finding('F02',['age','number of large CCM lesions'],'KRIT1 / Mutation not detected / CCM2 groups','reported_correlation',
        [ev_age,ev_fig3],'相关系数不等于基因—疾病相关；不能仅凭两组r或斜率不同宣称组间差异经过正式检验。')
    finding('F03',['age','number of large CCM lesions'],'PDCD10 group','explicit_negative',
        [ev_pd_age,ev_fig3],'限本队列该统计问题；图注趋势不是显著相关。')
    ev_table_p=evidence('b0064','P-values were obtained from the comparison between Mutation detected group and Mutation not detected group.',
        own,'reported_result','表1p值比较的是合并检出/未检出组，不是各单基因。')
    ev_clinical=whole('b0066',own,'negative_result','临床特征合并分组无显著差异及描述性趋势。')
    finding('F04',['panel mutation detected vs not detected','clinical characteristics'],'cohort1 n=21','explicit_negative',
        [ev_table_p,ev_clinical],'表1频数与合并组结论不能分配为逐基因—逐症状的阴性。')
    ev_marker=whole('b0068',own,'reported_result','解剖位置预测面板变异检出的ROC模型。')
    finding('F05',['lesion location','mutation detection'],'pooled panel','reported_association',[ev_marker],
        'brainstem是病灶位置，不额外建脑干疾病；不能作每单基因的位置关联。')
    ev_seizure=evidence('b0102','However, Christine K. Fox et al. revealed that large CCM lesion (a least 5 mm) counts are more associated with early-onset seizure than total lesion counts. 11',
        bg,'background_relation_statement','大病灶计数—早发发作关系；没有指定基因。')
    finding('F06',['large CCM lesion counts','early-onset seizure'],'cited prior study','background_association',[ev_seizure],
        '不是本研究结果，也不能借此连基因—癫痫边。')
    findings[-1]['source_scope']=bg
    ev_cohort=whole('b0070',own,'descriptive_cooccurrence','病例与变异类型、共病及病理诊断描述。')
    finding('F07',['variant carriers','spinal/cutaneous CM and tumors'],'individual cases','descriptive_cooccurrence',[ev_cohort],
        '病理诊断确认胶质瘤，不证明KRIT1导致胶质瘤。')

    EV={x['evidence_id']:x for x in evidences}
    for x in evidences:del x['_key']
    pairs=list(pair_lookup.values())
    for p in pairs:
        p['evidence']=[copy_evidence(EV[x]) for x in p['evidence_ids']]
        p['location']=sorted({EV[x]['location'] for x in p['evidence_ids']})
        p['context_checked']=[copy_evidence(EV[x]) for x in p['context_checked_ids']]
        p['observational_context']=[copy_evidence(EV[x]) for x in p['observational_context_ids']]
    for f in findings:f['evidence']=[copy_evidence(EV[x]) for x in f['evidence_ids']]

    unresolved=[
        {'subject':'PLE','state':'identity','location':['b0076'],'reason':'诊断缩写未定义；8对候选保留uncertain。'},
        {'subject':'ZPLD1—FCCM','state':'assertion_basis','location':['b0098'],'reason':'当前论文未提供proposed关联的结果细节，保留待审核。'},
        {'subject':'MAP3K3—FCCM','state':'hypothesis','location':['b0098'],'reason':'could及these genes指代；散发亚型结果不能补足。'},
        {'subject':'人类三基因—散发CCM','state':'subtype_specificity','location':['b0098','b0026'],'reason':'间接双打击背景，缺乏明确逐基因亚型对应。'},
        {'subject':'人类三基因—广义血管畸形','state':'broad_scope','location':['b0011','b0100'],'reason':'范围宽泛且为机制/功能解释。'},
        {'subject':'动物Krit1/Ccm2/Pdcd10','state':'species','location':['b0099'],'reason':'具体动物物种未指明；支持边仅限模型。'},
        {'subject':'CASH首次时点逐基因对比','state':'missing_supplement','location':['b0094','b0116'],'reason':'缺S3，未将组阴性拆成单基因阴性。'},
        {'subject':'图片与S1—S3实际数据','state':'coverage','location':['b0027','b0068','b0095','b0114','b0115','b0116'],'reason':'仅链接JPG与DOCX，无法检查附件新增实体。'},
        {'subject':'KRTI1/CMM疑似笔误','state':'contextual_normalization','location':['b0005','b0099'],'reason':'上下文支持合并，但没有作者勘误确认。'},
    ]
    nodes=[{'id':e['entity_id'],'label':e['canonical_name'],'entity_type':e['entity_type'],
            'bipartite':0 if e['entity_type']=='gene' else 1,'species':e['species'],
            'ambiguity':e['ambiguity']} for e in entities if e['in_primary_matrix']]
    edges=[dict(edge_id=f'ED{n:02d}',**p) for n,p in enumerate([p for p in pairs if p['status']=='supported'],1)]
    graph={'paper_id':a['paper_id'],'nodes':nodes,'edges':edges,
           'policy':'supported only; all primary endpoints retained; no human/animal edge propagation'}

    # Verify sets and evidence before exporting a graph or declaring completion.
    all_pair_set={(g['entity_id'],d['entity_id']) for g in genes for d in targets}
    assert {(p['gene_id'],p['disease_id']) for p in pairs}==all_pair_set
    assert len(pairs)==len(all_pair_set)
    assert all(bs[x['location']]['text'][x['start']:x['end']]==x['quote'] for x in evidences)
    assert all(bs[m['location']]['text'][m['start']:m['end']]==m['surface'] for m in mentions)
    assert all(p['evidence_ids'] for p in pairs if p['status'] in ['supported','explicit_negative'])
    assert all(p['unresolved_reason'] for p in pairs if p['status']=='uncertain')
    assert all(E[e['gene_id']]['entity_type']=='gene' and E[e['disease_id']]['in_primary_matrix'] for e in edges)
    OUT.mkdir(parents=True)
    datasets={'entities':entities,'mentions':mentions,'raw_names':raw_names,'candidate_pairs':pairs,
              'evidence':evidences,'excluded_candidates':excluded,'table_cells':table_cells,
              'study_findings':findings,'unresolved':unresolved,'nodes':nodes,'edges':edges}
    for name,rows in datasets.items():
        write_json(OUT/(name+'.json'),rows)
        write_csv(OUT/(name+'.csv'),rows,list(rows[0]))
    write_json(OUT/'source_blocks.json',a)
    (OUT/'source_blocks.txt').write_text('\n\n'.join(b['block_id']+' ['+b['section']+']\n'+b['text'] for b in a['blocks']),encoding='utf-8')
    write_json(OUT/'source_tables.json',tables)
    write_json(OUT/'graph.json',graph)
    graphml(graph,OUT/'network.graphml')
    render(graph,OUT)

    ns={'g':'http://graphml.graphdrawing.org/xmlns'}
    gr=ET.parse(OUT/'network.graphml')
    assert {n.get('id') for n in gr.findall('.//g:node',ns)}=={n['id'] for n in nodes}
    assert {(n.get('source'),n.get('target')) for n in gr.findall('.//g:edge',ns)}=={(p['gene_id'],p['disease_id']) for p in pairs if p['status']=='supported'}
    counts=Counter(p['status'] for p in pairs)
    audit={'paper_id':a['paper_id'],'run_id':RUN,'rule_version':'1.0.0',
        'entity_type_counts':dict(Counter(e['entity_type'] for e in entities)),
        'primary_gene_count':len(genes),'primary_target_count':len(targets),'primary_pair_count':len(pairs),
        'status_counts':dict(counts),'graph_nodes':len(nodes),'graph_edges':len(edges),
        'raw_name_count':len(raw_names),'mention_count':len(mentions),'evidence_count':len(evidences),
        'source_table_rows':sum(len(t['rows']) for t in tables),'source_block_count':len(bs),
        'checks':{'complete_unique_pair_set':True,'quotes_and_offsets_exact':True,'mentions_and_offsets_exact':True,
                  'positive_negative_evidence_present':True,'uncertainty_reason_present':True,
                  'graph_node_set_complete':True,'graph_edge_set_equals_supported':True},
        'limitations':'模型自查和机械校验；不是独立人工验证，不能证明语义完整或无遗漏。'}
    write_json(OUT/'audit.json',audit)
    report(a,entities,pairs,edges,findings,unresolved,audit,OUT)
    # Add an output index after every promised artifact has actually been produced.
    manifest={'run_id':RUN,'rule_version':'1.0.0','paper_id':a['paper_id'],'title':a['title'],
        'source_path':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'result_label':'GPT_6.1_sol','reviewer':'current assistant session; not a blind independent reviewer',
        'source_of_decisions':'direct re-reading of supplied XML under skill; no previous model-result files loaded',
        'skill_hashes':{str(p.relative_to(SKILL)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SKILL.rglob('*') if p.is_file()},
        'script_path':str(Path(__file__).resolve()),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'scope':{'abstract':True,'body':True,'table_rows':55,'table_footnotes':True,'figure_captions':3,
                 'image_pixels':False,'supplement_contents':False,'supplement_descriptions':True,'references':False},
        'missing_attachments':[e.get('{http://www.w3.org/1999/xlink}href') for tag in ['graphic','media'] for e in raw.findall('.//'+tag)],
        'normalization':'biomed.jats.parse_article Unicode NFKC, whitespace and typography normalization; source unchanged',
        'primary_scope_policy':'genes x diseases plus explicitly included CASH clinical_event and unresolved PLE diagnostic candidate; symptoms/phenotypes auxiliary only',
        'counts':audit,'files':sorted(p.name for p in OUT.iterdir() if p.is_file())+['manifest.json']}
    write_json(OUT/'manifest.json',manifest)
    print(json.dumps(audit,ensure_ascii=False,indent=2))

def copy_evidence(x):
    return {k:v for k,v in x.items() if k!='_key'}

def graphml(graph,path):
    ns='http://graphml.graphdrawing.org/xmlns';ET.register_namespace('',ns)
    def tag(t):return '{'+ns+'}'+t
    root=ET.Element(tag('graphml'))
    nk=['label','entity_type','bipartite','species','ambiguity']
    ek=['status','relation_type','source_scope','evidence_ids','evidence','conditions','reason']
    for kind,keys in [('node',nk),('edge',ek)]:
        for k in keys:ET.SubElement(root,tag('key'),{'id':k,'for':kind,'attr.name':k,'attr.type':'int' if k=='bipartite' else 'string'})
    gr=ET.SubElement(root,tag('graph'),id=graph['paper_id'],edgedefault='undirected')
    for n in graph['nodes']:
        node=ET.SubElement(gr,tag('node'),id=n['id'])
        for k in nk:ET.SubElement(node,tag('data'),key=k).text=str(n[k])
    for e in graph['edges']:
        edge=ET.SubElement(gr,tag('edge'),id=e['edge_id'],source=e['gene_id'],target=e['disease_id'])
        for k in ek:
            v=e[k];ET.SubElement(edge,tag('data'),key=k).text=json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else str(v)
    ET.ElementTree(root).write(path,encoding='utf-8',xml_declaration=True)

def render(graph,out):
    genes=[n for n in graph['nodes'] if n['bipartite']==0]
    targets=[n for n in graph['nodes'] if n['bipartite']==1]
    width=1260;height=1340
    positions={n['id']:(250,125+i*143) for i,n in enumerate(genes)}
    positions.update({n['id']:(690,118+i*54) for i,n in enumerate(targets)})
    edges=graph['edges'];label_y={};last=-100
    for e in sorted(edges,key=lambda e:positions[e['gene_id']][1]*.4+positions[e['disease_id']][1]*.6):
        last=max(last+19,positions[e['gene_id']][1]*.4+positions[e['disease_id']][1]*.6)
        label_y[e['edge_id']]=last
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
         '<rect width="100%" height="100%" fill="#fcfcfe"/>',
         '<style>text{font-family:Arial,sans-serif;fill:#14283f;font-size:14px}.small{font-size:12px}.title{font-size:23px;font-weight:bold}</style>',
         '<text x="28" y="34" class="title">PMC10014009 | Round 2 | Skill v1.0.0</text>',
         '<text x="28" y="62">Only supported pairs are edges. All primary nodes retained. Auxiliary symptoms are in separate tables.</text>',
         '<text x="28" y="83" class="small">Teal: human-context background evidence. Purple: animal-model background evidence.</text>']
    for e in edges:
        x,y=positions[e['gene_id']];xx,yy=positions[e['disease_id']]
        color='#7954a0' if e['gene_id'] in ['G06','G07','G08'] else '#207f89'
        title=html.escape(json.dumps(e,ensure_ascii=False))
        svg.append(f'<path d="M{x},{y} C430,{y} 510,{yy} {xx},{yy}" fill="none" stroke="{color}" stroke-width="1.7"><title>{title}</title></path>')
        svg.append(f'<text x="470" y="{label_y[e["edge_id"]]}" class="small">{e["edge_id"]}</text>')
    for n in graph['nodes']:
        x,y=positions[n['id']];left=n['bipartite']==0
        fill='#e0f1f2' if left else '#fff0d3'
        if n['entity_type']=='ambiguous':fill='#f3d8df'
        if n['entity_type']=='clinical_event':fill='#dce9f9'
        anchor='end' if left else 'start';tx=x-13 if left else x+13
        svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{fill}" stroke="#334155"><title>{html.escape(json.dumps(n,ensure_ascii=False))}</title></circle>')
        svg.append(f'<text x="{tx}" y="{y+5}" text-anchor="{anchor}">{html.escape(n["id"]+" "+n["label"])}</text>')
        if n['id'] in ['G06','G07','G08']:svg.append(f'<text x="{tx}" y="{y+23}" text-anchor="end" class="small">animal; species unresolved</text>')
    svg+=['<text x="28" y="1295" class="small">ED labels map to edges.csv; EV identifiers map to evidence.csv. Causal claims here are cited background.</text>',
          '<text x="28" y="1318" class="small">CASH: included clinical event. PLE: unresolved candidate. No external evidence or automatic subtype propagation.</text>','</svg>']
    (out/'network.svg').write_text('\n'.join(svg),encoding='utf-8')
    s=2;im=Image.new('RGB',(width*s,height*s),'#fcfcfe');dr=ImageDraw.Draw(im)
    def txt(x,y,text,size=14,anchor=None,bold=False):
        f=ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),size*s)
        dr.text((x*s,y*s),text,font=f,fill='#14283f',anchor=anchor)
    txt(28,12,'PMC10014009 | Round 2 | Skill v1.0.0',23,bold=True)
    txt(28,45,'Only supported pairs are edges. All primary nodes retained. Auxiliary symptoms are in separate tables.')
    txt(28,69,'Teal: human-context background evidence. Purple: animal-model background evidence.',12)
    for e in edges:
        x,y=positions[e['gene_id']];xx,yy=positions[e['disease_id']]
        color='#7954a0' if e['gene_id'] in ['G06','G07','G08'] else '#207f89';points=[]
        for j in range(101):
            t=j/100;u=1-t
            points.append(((u**3*x+3*u*u*t*430+3*u*t*t*510+t**3*xx)*s,
                           (u**3*y+3*u*u*t*y+3*u*t*t*yy+t**3*yy)*s))
        dr.line(points,fill=color,width=2*s)
        txt(470,label_y[e['edge_id']]-12,e['edge_id'],12)
    for n in graph['nodes']:
        x,y=positions[n['id']];left=n['bipartite']==0;fill='#e0f1f2' if left else '#fff0d3'
        if n['entity_type']=='ambiguous':fill='#f3d8df'
        if n['entity_type']=='clinical_event':fill='#dce9f9'
        dr.ellipse(((x-7)*s,(y-7)*s,(x+7)*s,(y+7)*s),fill=fill,outline='#334155',width=s)
        txt(x-13 if left else x+13,y,n['id']+' '+n['label'],anchor='rm' if left else 'lm')
        if n['id'] in ['G06','G07','G08']:txt(x-13,y+18,'animal; species unresolved',12,anchor='rm')
    txt(28,1280,'ED labels map to edges.csv; EV identifiers map to evidence.csv. Causal claims here are cited background.',12)
    txt(28,1303,'CASH: included clinical event. PLE: unresolved candidate. No external evidence or automatic subtype propagation.',12)
    im.resize((width,height),Image.Resampling.LANCZOS).save(out/'network.png')

def report(a,entities,pairs,edges,findings,unresolved,audit,out):
    E={e['entity_id']:e for e in entities}
    text=f'''# 第二轮：{a['paper_id']}（Skill v1.0.0）

论文：{a['title']}。DOI：{a['doi']}。

## A. 输入范围与限制

本轮仍分析第一篇论文，使用biomed-gene-disease-evidence 1.0.0直接重读原始JATS XML；未载入上一轮、Claude或比较裁决结果文件作为证据。当前会话已接触之前结论，因此这是重做，不是盲法独立验证。原始文件及既有结果不覆盖。

检查标题、摘要、正文、两张表全部55行与脚注、三幅图注及补充说明，共117个文本块。引用使用source_blocks.txt中的b编号；原文空白、Unicode和标点经规范化，原始XML不改。表格原结构另存source_tables.json，table_cells保留列和患者/基因分组。

未提取参考文献列表实体。XML只链接3张JPG和补充DOCX，本地输入未附这些文件；图片内文字和S1–S3实际内容没有读取。图注可读不等于图片已读；不宣称完整含附件全文已检查。本文没有明确出现需要另建节点的抗体标记物、报告构建体或跨物种序列比较；这不是附件中不存在的保证。

## B. 实体表与身份核对

主矩阵：8个基因范围节点 × 21个目标（19个疾病/疾病家族、1个临床事件CASH、1个未解决诊断候选PLE）。症状17项、一般表型2项保存在辅助范围，不计作疾病，不画主图。全部48项在entities.csv/json，原文名称raw_names，逐次上下文/角色mentions。

别名仅有原文展开或上下文依据时合并；D20 vascular malformation和D21 intracranial vascular malformation分开。CM、CCM、FCCM、散发CCM及脊髓/皮肤亚型分开。PLE不展开、不与OLE合并。人类与动物基因节点分开，具体动物物种未知；MAP3K3的MEKK3提及标为protein_product。KRTI1/CMM疑似笔误保留原名与合并依据。侧别、分级、症状限定及局部回指另存；局部CM回指不当全局别名。

|ID|类型|统一名称|物种或范围|主矩阵|
|---|---|---|---|---|
'''
    for e in entities:
        text+='|'+ '|'.join([e['entity_id'],e['entity_type'],e['canonical_name'],e['species'],'是' if e['in_primary_matrix'] else '辅助'])+'|\n'
    text+='''
数据库实体编号未验证，留空；b0019测序参考序列另列。数据库/软件/指南代码、解剖位置、一般事件及基因集合在excluded_candidates中保存，不推断新基因或疾病。

## C. 全部候选关系

'''+f"完整168对，状态为 {audit['status_counts']}。not_found不是无关联证明；uncertain必须注明identity、亚型特异性、指代或解释等具体原因。\n\n"
    text+='''每个关系有主状态和原文证据；证据单独带source_scope、assertion_kind、supports及条件。背景因果与本研究变异病例观察分开，后者在observational_context，不能冒充本研究验证因果。not_found可以没有支持引语，但易误读的共病/组阴性放context_checked，保留原文。

|边|基因|目标|类型|来源|证据|
|---|---|---|---|---|---|
'''
    for e in edges:
        text+='|'+ '|'.join([e['edge_id'],E[e['gene_id']]['canonical_name'],E[e['disease_id']]['canonical_name'],e['relation_type'],e['source_scope'],', '.join(e['evidence_ids'])])+'|\n'
    text+='''
关键未解决判断：ZPLD1–FCCM结合could/proposed及整段语境仍无结果细节，保留uncertain，并非一见proposed就排除。MAP3K3–散发CCM由confirmed GOF与互斥模式联合支持association；向FCCM的could为假设，不连边。三个人类基因–散发CCM有间接双打击背景但亚型映射未明，保留uncertain。三基因–广义血管畸形的机制/范围未清，保留uncertain。PLE身份未明的8对uncertain不表示存在弱关联。

首次CASH基因型组间不显著结果另存F01；S3未提供，不能逐基因标explicit_negative。PDCD10组年龄–病灶数不显著另存F03，不否定PDCD10–CCM/FCCM。临床特征的检出/未检出合并组阴性另存F04，不拆给每个基因和症状。7项study_findings保留实际统计变量与条件；各临床共病只有个案记录，未据此建立基因边。

## D. 二部图及编辑数据

graph.json、nodes.csv、edges.csv、network.graphml保存29个主节点及10条supported边；network.svg可编辑，network.png为预览。孤立节点全部保留；CASH显示为临床事件，PLE显示为未解决候选。紫色边限动物模型；每条ED边连接EV证据及原文位置。症状/表型辅助表项不伪装为疾病图节点。

## E. 质量说明

已复核全部可读文本、两张表、脚注、三幅图注及讨论次要名称；检查否定、条件、别名、物种、基因集合修饰语、蛋白角色和非支持候选。大写名称候选扫查用于辅助找漏，不作为提取完整性的保证。

引用/提及偏移存在性、全部笛卡尔积集合与唯一性、证据ID、uncertain原因、图节点和supported边集合通过程序检查，详见audit.json。这不证明语义准确、没有遗漏，也不是独立人工验证；无准确率、召回率或置信度分数。

'''
    for u in unresolved:text+='- '+u['subject']+'：'+u['reason']+'（'+', '.join(u['location'])+'）\n'
    text+='''

文件索引：entities、raw_names、mentions、candidate_pairs、evidence、excluded_candidates、table_cells、study_findings、unresolved、nodes、edges均提供CSV/JSON；另有原文文本/表格结构、GraphML、SVG/PNG预览及manifest。manifest记录规则/脚本/输入哈希和实际覆盖。当前会话的重复核查不构成独立模型复现实验。
'''
    (out/'report.md').write_text(text,encoding='utf-8')

if __name__=='__main__':run()
