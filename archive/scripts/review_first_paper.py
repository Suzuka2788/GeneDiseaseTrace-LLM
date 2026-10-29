"""Paper-specific evidence ledger, curated from the supplied XML; no external knowledge."""
import csv
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

from biomed.jats import parse_article

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'archive' / 'outputs_GPT_6.1_sol' / 'PMC10014009'
OUT.mkdir(parents=True, exist_ok=True)
article = parse_article(ROOT / '.Input/100papers/PMC10014009.xml')
blocks = {b['block_id']: b for b in article['blocks']}
paper = article['paper_id']

def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def write_csv(name, rows, fields):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: json.dumps(row.get(k), ensure_ascii=False) if isinstance(row.get(k), (list, dict)) else row.get(k, '') for k in fields})

entities = []
def entity(eid, typ, canonical, aliases, species, loc, ambiguity='', merge='原文名称；未进行数据库映射。', subtype=''):
    entities.append(dict(paper_id=paper, entity_id=eid, entity_type=typ,
        canonical_name=canonical, original_names=aliases, species=species,
        location=loc, ambiguity=ambiguity, merge_basis=merge, entity_subtype=subtype,
        database_id=''))

entity('G01','gene','KRIT1',['KRIT1','KRTI1'],'Homo sapiens',['b0003','b0005','b0019','b0073','b0100'],
       'KRTI1 是原文拼写，按同一三基因检测面板上下文判为 KRIT1 的疑似排字错误，不作独立基因。',
       'b0003、b0014、b0019 的检测面板均为 KRIT1/CCM2/PDCD10；仅 b0005 写 KRTI1。b0100 的 KRIT1 protein 是同一基因产物，角色另记。')
entity('G02','gene','CCM2',['CCM2'],'Homo sapiens',['b0003','b0019','b0084'])
entity('G03','gene','PDCD10',['PDCD10'],'Homo sapiens',['b0003','b0019','b0087'])
entity('G04','gene','ZPLD1',['ZPLD1'],'人类患者语境；原句未另标物种',['b0098'],
       '只有讨论中转述他人提出的关联，本研究未测定此基因。')
entity('G05','gene','MAP3K3',['MAP3K3','MEKK3'],'人类散发 CCM 患者语境',['b0098'],
       'MEKK3 为蛋白产物名称，不是另一个已明确出现的基因。',
       'b0098 明写 MAP3K3, encoding MEKK3；并入同一基因产物节点，mentions.csv 保留 gene/protein 角色。')
for eid, name in [('G06','Krit1'),('G07','Ccm2'),('G08','Pdcd10')]:
    entity(eid,'gene',name,[name],'动物模型；所给原文未指明具体物种',['b0099'],
       '与对应人类基因分开保留；动物物种未解决。不能仅凭大小写推断为小鼠。',
       'b0099 明确为 CCM animal model；不同于本研究人类血样基因检测语境。')

entity('D01','disease','cerebral cavernous malformation',['Cerebral cavernous malformation','cerebral cavernous malformation','CCM','CCMs','cerebral cavernous malformations','CMM'],'人类；动物模型另有语境',['b0011','b0099'],
       'CMM 仅 b0099 出现一次，按相邻治疗 CCM 语境视为疑似笔误；保留原文。',
       'b0011 和图注明确定义 CCM；CCMs 为复数。CMM 的合并为上下文判断。','疾病家族/上位疾病')
entity('D02','disease','familial cerebral cavernous malformation',['familial cerebral cavernous malformation','Familial cerebral cavernous malformation','Familial CCM','familial CCM','FCCM'],'人类',['b0001','b0003','b0011'],merge='b0003、b0011 显式定义 FCCM；保留为 CCM 的家族性亚型节点，不与上位 CCM 合并。',subtype='疾病亚型')
entity('D03','disease','sporadic cerebral cavernous malformation',['sporadic CCM','sporadic CCMs'],'人类',['b0011','b0026','b0098'],merge='b0011 明确区分 sporadic 与 familial；不向另一个亚型传播证据。',subtype='疾病亚型')
entity('D04','disease','spinal cavernous malformation',['spinal cavernous malformation','spinal CM','Spinal CM'],'人类',['b0016','b0047','b0070','b0076','b0090'],merge='b0016 定义 CM；spinal 明确限定脊髓部位。表2 Spinal 为同列的简写。')
entity('D05','disease','cutaneous cavernous malformation',['cutaneous CM','Cutaneous CM'],'人类',['b0016','b0048','b0070','b0085'],merge='b0016 的 CM 定义及表1、表2 的 non-cerebral CM 语境。')
entity('D06','disease','cavernous angioma with symptomatic hemorrhage',['cavernous angioma with symptomatic hemorrhage','cavernous angioma with a symptomatic hemorrhage','cavernous angiomas with the occurrence of symptomatic hemorrhage','cavernous angiomas with a symptomatic hemorrhage','CASH'],'人类',['b0016','b0021','b0043','b0064','b0093','b0094'],ambiguity='病变伴症状性出血的复合临床事件，作为条件节点保留；不与所有 CCM 合并。',merge='b0016、b0064、b0093 明确 CASH 的展开。',subtype='疾病伴并发事件')
entity('D07','disease','small vessel disease',['small vessel disease'],'人类',['b0026'])
entity('D08','disease','diffuse axonal injury',['diffuse axonal injury'],'人类',['b0026'],subtype='损伤')
entity('D09','disease','intracerebral hemorrhage',['intracerebral hemorrhages'],'人类',['b0026'],ambiguity='原文指无 CCM 病灶的多发复发脑内出血，不与 CASH 合并。',subtype='出血性病症')
entity('D10','disease','developmental venous anomaly',['developmental venous anomaly'],'人类',['b0026'],ambiguity='本队列明确无人患此畸形；这不是基因—疾病关联阴性试验。')
entity('D11','disease','tumor',['tumor','tumors','Tumor','tumorous condition'],'人类',['b0016','b0050','b0070','b0072'],ambiguity='宽泛疾病家族；表2的具体肿瘤不并入此节点。',subtype='疾病家族')
entity('D12','disease','breast cancer',['Breast cancer'],'人类',['b0074'])
entity('D13','disease','thyroid cancer',['Thyroid cancer'],'人类',['b0075'])
entity('D14','disease','diffuse midline glioma',['diffuse midline glioma','Diffuse midline glioma'],'人类',['b0070','b0076'],merge='正文活检与表2均指 K3，WHO grade IV 为分级，不是另一肿瘤节点。')
entity('D15','disease','adrenal adenoma',['Adrenal adenoma'],'人类',['b0077'])
entity('D16','disease','left anterior cerebral artery infarction',['Left ACA infarction'],'人类',['b0077','b0093'],merge='b0093 明确 ACA 为 anterior cerebral artery；不推断具体梗死病因。')
entity('D17','disease','occipital lobe epilepsy',['occipital lobe epilepsy','OLE'],'人类',['b0082','b0093'],merge='表2脚注明确定义 OLE。')
entity('D18','ambiguous','PLE',['PLE'],'人类',['b0076'],ambiguity='表2 K3 临床表现出现 PLE，正文及脚注未定义，不能按常识补为某种癫痫。',subtype='未解决的疾病/诊断缩写候选')
entity('D19','disease','cavernous malformation',['cavernous malformation','CM'],'人类',['b0016','b0064','b0093'],ambiguity='一般 CM 上位名称；不自动合并为脑 CCM 或脊髓/皮肤亚型。',merge='b0064、b0093 定义 CM；限定部位的名称分别入 D01/D04/D05。',subtype='疾病家族')
entity('D20','disease','vascular malformation',['vascular malformation','intracranial vascular malformation'],'人类；机制描述',['b0011','b0100'],ambiguity='宽泛畸形表述；b0100 是 KRIT1 蛋白组分功能推测，不足以支持对该宽泛家族的基因因果关系。',subtype='疾病家族')

# Exact surface occurrences, with full original block for independently checkable context.
mentions = []
patterns = []
for e in entities:
    for alias in e['original_names']:
        patterns.append((e, alias, re.compile(r'(?<![A-Za-z0-9])'+re.escape(alias)+r'(?![A-Za-z0-9])')))
for bid,b in blocks.items():
    hits=[]
    for e,alias,pat in patterns:
        for m in pat.finditer(b['text']):
            hits.append((m.start(),m.end(),e,alias))
    # Prefer full specific names over embedded abbreviations / broader disease names.
    selected=[]
    for start,end,e,alias in sorted(hits,key=lambda x: (-(x[1]-x[0]),x[0])):
        if any(start < y and end > x for x,y,_,_ in selected):
            continue
        selected.append((start,end,e,alias))
    for start,end,e,alias in sorted(selected,key=lambda x:x[0]):
        role='gene' if e['entity_type']=='gene' else e['entity_subtype'] or e['entity_type']
        if alias=='MEKK3' or (alias=='KRIT1' and b['text'][end:].startswith(' protein')):
            role='protein_product'
        mentions.append(dict(paper_id=paper,entity_id=e['entity_id'],original_name=b['text'][start:end],
            entity_type=e['entity_type'],mention_role=role,location=bid,section=b['section'],
            start=start,end=end,context=b['text'],ambiguity=e['ambiguity']))

# Additional table cells whose specificity is supplied by the column header.
for bid,alias,eid in [('b0076','Spinal','D04'),('b0090','Spinal','D04'),('b0085','Cutaneous','D05')]:
    text=blocks[bid]['text']; start=text.index(alias)
    mentions.append(dict(paper_id=paper,entity_id=eid,original_name=alias,entity_type='disease',
        mention_role='table_cell_with_header',location=bid,section=blocks[bid]['section'],
        start=start,end=start+len(alias),context=text,
        ambiguity='需联合 b0072 Non-cerebral CM 表头；此处不是孤立解剖名称。'))

excluded=[]
def exclude(names, category, bids, why):
    for name in names:
        found=[]
        for bid in bids:
            if name.lower() in blocks[bid]['text'].lower():
                found.append({'location':bid,'context':blocks[bid]['text']})
        excluded.append(dict(original_name=name,category=category,occurrences=found,reason=why))

exclude(['Headache','Dizziness','Weakness','Dysarthria','Facial palsy','Diplopia','Visual symptoms'],
        'symptom',['b0036','b0037','b0038','b0039','b0040'],'症状，单列保留，不作为已诊断疾病节点。')
exclude(['Seizure','FIAS','focal impaired awareness seizure','FBTCS','focal to bilateral tonic-clonic seizure','Emotional seizure','drowsy mentality','Decreased mentality','Central vertigo','neck pain','Visual disturbance','Transient positive visual symptom','binocular diplopia','Nonspecific headache'],
        'symptom_or_seizure_type',['b0041','b0042','b0074','b0075','b0076','b0078','b0079','b0080','b0081','b0082','b0083','b0085','b0086','b0088','b0093'],
        '临床症状/发作类型；不据此补入癫痫诊断。OLE 是明确定义诊断，另行纳入；PLE 保留歧义。')
exclude(['cerebral microbleeds','symptomatic hemorrhage','severe neurological sequelae'],
        'finding_or_event',['b0026','b0070'],'微出血是 small vessel disease 的影像表现；单独的症状性出血/神经后遗症为事件或表型。CASH 复合病症另外保留。')
exclude(['CCM genes','FCCM gene','CCM complexes','CCM-associated genes'],
        'gene_group',['b0003','b0011','b0098'],'集合称谓，不创建一个与具体基因重复的单基因节点。')
exclude(['HGMD','KRGDB','FSPLICE','NNSplice','NetGene2','ACMG','PVS1','PM2','PP1','PP4','ACA'],
        'not_gene_or_disease',['b0019','b0074','b0079','b0088','b0093'],
        '数据库/分析工具/指南分类代码/解剖缩写，不是基因或疾病。变异编号随各基因上下文保留，不另建基因。')

def ev(bid, quote=None):
    text=blocks[bid]['text']
    if quote is None: quote=text
    assert quote in text, (bid,quote)
    return dict(quote=quote,location=bid,section=blocks[bid]['section'])

genes=[e for e in entities if e['entity_type']=='gene']
diseases=[e for e in entities if e['entity_id'].startswith('D')]
pairs=[]
for g in genes:
    for d in diseases:
        pairs.append(dict(paper_id=paper,gene_id=g['entity_id'],disease_id=d['entity_id'],
            status='not_found',relation_type='none',source_scope='不确定',evidence=[],
            location=[],reason='已检查所给 XML 的全部标题、摘要、正文、表格、图注与补充说明；未找到将指定基因与指定疾病建立关系的足够证据。',
            conditions='不代表医学上不存在关系；未检查缺失的图片像素与补充 DOCX。'))
lookup={(p['gene_id'],p['disease_id']):p for p in pairs}
def judge(g,d,status,rel,scope,evidence,reason,conditions=''):
    lookup[g,d].update(status=status,relation_type=rel,source_scope=scope,evidence=evidence,
        location=[x['location'] for x in evidence],reason=reason,conditions=conditions)

for g in ['G01','G02','G03']:
    judge(g,'D02','supported','causal','两者兼有',[
        ev('b0003','Familial cerebral cavernous malformation (FCCM) is an autosomal dominant disease induced by loss-of-function mutations in three CCM genes, KRIT1, CCM2, and PDCD10.'),
        ev('b0028','Cohort 1 consisted of nine patients with KRIT1 variants, two with CCM2 variants, two with PDCD10 variants, and eight with the mutation not detected (Table 1).')],
        '背景明确将三个基因的失功能变异归为 FCCM 病因；本研究检出对应患者变异。causal 来自背景陈述，本研究为观察性结果，不是新的因果验证。',
        '限原文所述致病变异，不指任意变异均致病；8例未检出不能解释为排除基因关联。')
    judge(g,'D01','supported','causal','背景引用',[
        ev('b0011','These prior studies demonstrated that the products of the three genes (KRIT1, CCM2, and PDCD10) are associated with CCM form complexes. Loss of function (LOF) of these genes leads to the formation of CCM.')],
        '正文直接针对 CCM 描述三个基因的失功能致病机制；不是把家族性亚型关系自动向上推广。',
        '背景机制陈述；不推及每一种散发病例或所有变异。')
judge('G04','D02','uncertain','none','背景引用',[
    ev('b0098','F. Gianfrancesco et al. proposed that ZPLD1 mutation is associated with FCCM.')],
    '论文只转述他人 proposed 的关联，未描述相应结果或证据；在当前论文范围无法区分已获支持的关联与研究提议，保守保留 uncertain。',
    'proposed，证据强度受限；本研究无 ZPLD1 测序结果。未读取被引论文，不能核实其原始证据。')
judge('G05','D03','supported','association','背景引用',[
    ev('b0098','Moreover, gain-of-function (GOF) mutations in MAP3K3, encoding MEKK3, have been confirmed in sporadic CCM patients.'),
    ev('b0098','LOF in CCM genes and GOF in MAP3K3 are mutually exclusive, and the researchers suggested that CCM complexes suppress the activity of MEKK3.')],
    '联合疾病患者中确认的功能获得突变、与CCM基因失功能的互斥模式及相关机制讨论，支持背景关联，超过单纯名称共现；保守不升级为因果。')
judge('G05','D02','uncertain','none','背景引用',[
    ev('b0098','Therefore, the mutation of these genes could be a novel cause of FCCM.')],
    '这些基因的指代及对 FCCM 的推广均为 could 的假设；散发 CCM 证据不足以支持家族性亚型。',
    '不将 could cause 编码为 causal。')
for g in ['G06','G07','G08']:
    judge(g,'D01','supported','causal','背景引用',[
        ev('b0099','Some preclinical studies have demonstrated that the CCM animal model induced by Krit1, Ccm2, or Pdcd10 heterozygous loss in the immediate postnatal period, tended to harbor lesions in the hindbrain.')],
        '正文将各基因的杂合缺失与诱导 CCM 动物模型直接相连；模型因果证据与人类节点分开保留。',
        '动物模型、出生后早期杂合缺失；具体物种未注明，不等同人类疾病因果。')

# Explicitly account for tempting co-occurrence, hypotheses, and conditional null findings.
for g in ['G01','G02','G03']:
    judge(g,'D06','not_found','none','本研究结果',[
        ev('b0094','The difference among the CCM mutation genotypes was not statistically significant (Table S3).'),
        ev('b0101')],
        '有 CASH 的基因分组观察与组间不显著结果，但不是指定单基因与 CASH 有无关联的检验；缺失 S3 无法还原每个对比，不能逐基因泛化 explicit_negative。',
        '记录的是不同 CCM 基因型间首次 CASH 风险比较；病例组内有事件不等于独立基因—CASH 关联。')
for g in ['G01','G03']:
    judge(g,'D04','not_found','none','本研究结果',[ev('b0070','Two patients (K3 and P2) had spinal CM, and one (C1) had cutaneous CM.')],
        '结合表2可知 K3 为 KRIT1、P2 为 PDCD10；只有个体共存记录，未提出或检验指定基因与脊髓 CM 的关联。')
judge('G02','D05','not_found','none','本研究结果',[ev('b0070','Two patients (K3 and P2) had spinal CM, and one (C1) had cutaneous CM.'),ev('b0085')],
      'C1 为 CCM2 变异病例且有皮肤 CM，仍仅为个案共存，未建立基因与此亚型的关系。')
for d,bid in [('D11','b0070'),('D12','b0074'),('D13','b0075'),('D14','b0076'),('D15','b0077'),('D16','b0077'),('D17','b0082')]:
    judge('G01',d,'not_found','none','本研究结果',[ev(bid)],
        'KRIT1 变异携带者的共病/诊断记录；没有指定基因与该疾病的关联检验、明确关联主张或机制证据。')
for g in [x['entity_id'] for x in genes]:
    judge(g,'D18','uncertain','none','不确定',[ev('b0076')],
        'PLE 未定义，疾病实体身份未解决；不能对未知诊断作确定关联判断。')
judge('G01','D20','uncertain','none','不确定',[
    ev('b0100','Exon 12 is responsible for a particular portion of the KRIT1 protein ankyrin component.'),
    ev('b0100','This component is likely critical for preventing vascular malformation.')],
    'likely 为蛋白组分功能推测；vascular malformation 是宽泛名称，不能推及整个疾病家族。')

for e in entities:
    e['location']=sorted(set(e['location']+[m['location'] for m in mentions if m['entity_id']==e['entity_id']]))
    assert any(m['entity_id']==e['entity_id'] for m in mentions),e['entity_id']

write_json('source_blocks.json',article)
(OUT/'source_blocks.txt').write_text('\n\n'.join(f"{b['block_id']} [{b['section']}]\n{b['text']}" for b in article['blocks']),encoding='utf-8')
write_json('entities.json',entities)
write_json('mentions.json',mentions)
write_json('excluded_candidates.json',excluded)
write_json('candidate_pairs.json',pairs)
write_csv('entities.csv',entities,list(entities[0]))
write_csv('mentions.csv',mentions,list(mentions[0]))
write_csv('candidate_pairs.csv',pairs,list(pairs[0]))
write_csv('excluded_candidates.csv',excluded,['original_name','category','occurrences','reason'])

edges=[]
for p in pairs:
    if p['status']=='supported':
        edges.append(dict(edge_id=f"E{len(edges)+1:02d}",**p))
nodes=[dict(id=e['entity_id'],label=e['canonical_name'],bipartite=0 if e['entity_type']=='gene' else 1,
            species=e['species'],entity_type=e['entity_type'],ambiguity=e['ambiguity']) for e in entities]
graph=dict(paper_id=paper,nodes=nodes,edges=edges,policy='Only supported pairs are edges. All entity nodes retained, including unresolved disease candidate PLE.')
write_json('graph.json',graph)
write_csv('edges.csv',edges,list(edges[0]))
write_csv('nodes.csv',nodes,list(nodes[0]))

ns='http://graphml.graphdrawing.org/xmlns'
ET.register_namespace('',ns)
r=ET.Element('{'+ns+'}graphml')
for key,scope,typ in [('label','node','string'),('bipartite','node','int'),('species','node','string'),('entity_type','node','string'),('ambiguity','node','string'),('status','edge','string'),('relation_type','edge','string'),('source_scope','edge','string'),('evidence','edge','string'),('reason','edge','string'),('conditions','edge','string')]:
    ET.SubElement(r,'{'+ns+'}key',{'id':key,'for':scope,'attr.name':key,'attr.type':typ})
gr=ET.SubElement(r,'{'+ns+'}graph',id=paper,edgedefault='undirected')
for n in nodes:
    ne=ET.SubElement(gr,'{'+ns+'}node',id=n['id'])
    for k,v in n.items():
        if k!='id': ET.SubElement(ne,'{'+ns+'}data',key=k).text=str(v)
for e in edges:
    ee=ET.SubElement(gr,'{'+ns+'}edge',id=e['edge_id'],source=e['gene_id'],target=e['disease_id'])
    for k in ['status','relation_type','source_scope','evidence','reason','conditions']:
        ET.SubElement(ee,'{'+ns+'}data',key=k).text=json.dumps(e[k],ensure_ascii=False) if k=='evidence' else e[k]
ET.ElementTree(r).write(OUT/'network.graphml',encoding='utf-8',xml_declaration=True)

# Native editable SVG: evidence identifiers are visible; full evidence is in hover titles.
esc=html.escape
positions={}
for i,g in enumerate(genes):positions[g['entity_id']]=(245,120+i*125)
for i,d in enumerate(diseases):positions[d['entity_id']]=(690,95+i*52)
label_ys={}
previous=-100
for edge in sorted(edges,key=lambda e:positions[e['gene_id']][1]*0.48+positions[e['disease_id']][1]*0.52):
    baseline=positions[edge['gene_id']][1]*0.48+positions[edge['disease_id']][1]*0.52
    previous=max(previous+18,baseline)
    label_ys[edge['edge_id']]=previous
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1230" height="1180" viewBox="0 0 1230 1180">',
 '<rect width="1230" height="1180" fill="#fcfcfe"/>',
 '<style>text{font-family:Arial,sans-serif;font-size:14px}.title{font-size:22px;font-weight:bold}.small{font-size:12px}</style>',
 '<text x="30" y="32" class="title">PMC10014009: evidence-supported bipartite graph</text>',
 '<text x="30" y="57">Genes (left) | diseases / unresolved candidate (right) | isolated nodes retained</text>']
for e in edges:
    x,y=positions[e['gene_id']];xx,yy=positions[e['disease_id']]
    color='#7652a0' if e['gene_id'] in ['G06','G07','G08'] else '#237881'
    svg.append(f'<path d="M{x},{y} C430,{y} 500,{yy} {xx},{yy}" stroke="{color}" stroke-width="1.8" fill="none" opacity="0.65"><title>{esc(e["edge_id"]+" "+json.dumps(e,ensure_ascii=False))}</title></path>')
    # Near-source labels resolve crossings using the edge ledger.
    my=label_ys[e['edge_id']]
    svg.append(f'<text x="465" y="{my:.1f}" fill="{color}" class="small">{e["edge_id"]}</text>')
for n in nodes:
    x,y=positions[n['id']]; left=n['bipartite']==0
    color='#eee5fa' if n['id'] in ['G06','G07','G08'] else ('#dff2f4' if left else '#ffedcf')
    if n['entity_type']=='ambiguous':color='#f5d9dd'
    svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="#334155"><title>{esc(json.dumps(n,ensure_ascii=False))}</title></circle>')
    label=n['id']+' '+n['label']
    svg.append(f'<text x="{x-12 if left else x+14}" y="{y+5}" text-anchor="{"end" if left else "start"}">{esc(label)}</text>')
    if n['id'] in ['G06','G07','G08']:
        svg.append(f'<text x="{x-12}" y="{y+23}" text-anchor="end" class="small">animal; species unresolved</text>')
svg+=['<text x="30" y="1148" class="small">E01-E10: see edges.csv / graph.json for evidence, scope, and experimental conditions.</text>',
      '<text x="30" y="1168" class="small">Purple edges: animal model evidence. ZPLD1: uncertain, isolated. No external biomedical facts added.</text>','</svg>']
(OUT/'network.svg').write_text('\n'.join(svg),encoding='utf-8')

# Raster preview of the same native graph; no generated or edited biomedical images.
from PIL import Image, ImageDraw, ImageFont
scale=2
im=Image.new('RGB',(1230*scale,1180*scale),'#fcfcfe')
dr=ImageDraw.Draw(im)
fontdir=Path('C:/Windows/Fonts')
def font(size,bold=False):
    return ImageFont.truetype(str(fontdir/('arialbd.ttf' if bold else 'arial.ttf')),size*scale)
def text(x,y,s,size=14,color='#14283f',anchor=None,bold=False):
    dr.text((x*scale,y*scale),s,font=font(size,bold),fill=color,anchor=anchor)
text(30,12,'PMC10014009: evidence-supported bipartite graph',22,bold=True)
text(30,43,'Genes (left) | diseases / unresolved candidate (right) | isolated nodes retained')
for e in edges:
    x,y=positions[e['gene_id']];xx,yy=positions[e['disease_id']]
    color='#7652a0' if e['gene_id'] in ['G06','G07','G08'] else '#237881'
    points=[]
    for j in range(101):
        t=j/100;u=1-t
        points.append(((u*u*u*x+3*u*u*t*430+3*u*t*t*500+t*t*t*xx)*scale,
                       (u*u*u*y+3*u*u*t*y+3*u*t*t*yy+t*t*t*yy)*scale))
    dr.line(points,fill=color,width=2*scale)
    text(465,label_ys[e['edge_id']]-12,e['edge_id'],12,color)
for n in nodes:
    x,y=positions[n['id']];left=n['bipartite']==0
    fill='#eee5fa' if n['id'] in ['G06','G07','G08'] else ('#dff2f4' if left else '#ffedcf')
    if n['entity_type']=='ambiguous':fill='#f5d9dd'
    dr.ellipse(((x-7)*scale,(y-7)*scale,(x+7)*scale,(y+7)*scale),fill=fill,outline='#334155',width=scale)
    text(x-12 if left else x+14,y,n['id']+' '+n['label'],anchor='rm' if left else 'lm')
    if n['id'] in ['G06','G07','G08']:text(x-12,y+18,'animal; species unresolved',12,anchor='rm')
text(30,1136,'E01-E10: see edges.csv / graph.json for evidence, scope, and experimental conditions.',12)
text(30,1156,'Purple: animal model evidence. ZPLD1: uncertain, isolated. No external biomedical facts added.',12)
im.resize((1230,1180),Image.Resampling.LANCZOS).save(OUT/'network.png')

status_counts=Counter(p['status'] for p in pairs)
audit={
 'paper_id':paper,'input_sha256':hashlib.sha256(Path(article['source_file']).read_bytes()).hexdigest(),
 'block_counts':dict(Counter(b['content_type'] for b in article['blocks'])),
 'gene_count':len(genes),'disease_count':sum(e['entity_type']=='disease' for e in diseases),
 'ambiguous_disease_candidate_count':1,'pair_count':len(pairs),'status_counts':dict(status_counts),
 'supported_edges':len(edges),'mentions':len(mentions),
 'pair_set_complete':{(g['entity_id'],d['entity_id']) for g in genes for d in diseases}==set(lookup),
 'pair_unique':len(pairs)==len(lookup),
 'quotes_exact':all(ev['quote'] in blocks[ev['location']]['text'] for p in pairs for ev in p['evidence']),
 'mentions_exact':all(blocks[m['location']]['text'][m['start']:m['end']]==m['original_name'] for m in mentions),
 'graph_includes_all_nodes':set(n['id'] for n in nodes)==set(e['entity_id'] for e in entities),
 'graph_only_supported':all(e['status']=='supported' for e in edges),
 'xml_graph_counts':{'nodes':len(gr.findall('{'+ns+'}node')),'edges':len(gr.findall('{'+ns+'}edge'))},
 'validation_scope':'本次分析自查与字符串/集合校验；不是独立人工验证，也不是准确率或召回率评估。',
 'unresolved':['图片像素未提供','补充 DOCX 未提供','PLE 未定义','动物模型具体物种未注明','ZPLD1 仅提出的背景关联','MAP3K3 与 FCCM 仅推测','KRTI1/CMM 疑似排字错误的上下文合并','宽泛 vascular malformation 的范围与推测性证据','未读取被引文献原始研究']}
assert audit['pair_set_complete'] and audit['pair_unique'] and audit['quotes_exact'] and audit['mentions_exact']
assert audit['graph_includes_all_nodes'] and audit['graph_only_supported']
write_json('audit.json',audit)

report=f'''# PMC10014009：逐篇证据核查

## A. 输入范围与限制

论文：{article['title']}。DOI：{article['doi']}。按上传压缩包文件顺序选第一篇；不是按发表日期排序。

直接重解析所给 JATS XML，共 {len(blocks)} 个文本块：标题1、段落32（含摘要及补充说明）、章节标题22、图表标题/图注5、表格行55、表下注释2。检查范围为标题、摘要、全部正文、表1和表2（含表头、所有行和脚注）、图1–3图注、补充表S1–S3说明及声明。参考文献列表不纳入实体提取；正文引用陈述可以作为背景。

XML 仅链接3张 JPG（ACN3-10-373-g001/g002/g003.jpg）与1个补充 DOCX（ACN3-10-373-s001.docx）；本地输入包未提供这些文件，故未读取图片内文字、曲线标注或补充表实际数据。不能声称检查了含这些附件的完整全文。所有位置为 source_blocks.txt 的块编号，不编造页码。文本进行空白、Unicode和标点规范化；引用与此规范化原文逐字校验，原始XML保持不变。

## B. 实体表

entities.csv/json 为统一实体表；mentions.csv/json 为原文名称、角色、位置、精确字符偏移与完整段落上下文。excluded_candidates.csv/json 明示症状、一般表型、数据库、工具、指南代码和基因集合称谓等排除项。未填入未经原文确认的数据库实体编号；原文的测序参考序列保留在 b0019，不误作实体ID。

共8个基因范围节点（5个人类语境、3个具体物种未明的动物模型节点）、19个疾病/临床病症节点及1个未解决诊断候选PLE。没有抗体标记物、报告基因或跨物种序列比较的明确记录；KRIT1 protein 和 MEKK3 均按基因产物角色记录。

|ID|类型|统一名称|物种/范围|关键说明|
|---|---|---|---|---|
'''
for e in entities:
    report+='|'+ '|'.join([e['entity_id'],e['entity_type'],e['canonical_name'],e['species'],e['ambiguity'] or e['merge_basis']])+'|\n'
report+='''
CCM、FCCM、sporadic CCM、一般 CM、spinal CM、cutaneous CM 分开保留。原文因果句直接提及 CCM 时才建立 CCM 关系，不把亚型关系自动向上或横向传播。CASH 是病变伴症状性出血复合条件；发作类型、头痛、复视等单列为症状，不补入疾病诊断。PLE 未展开，不能与 OLE 或任何推测名称合并。

## C. 全候选组合

'''+f'8 × 20 = **{len(pairs)}** 对，全部写入 candidate_pairs.csv/json，包括 PLE 候选；状态统计：{dict(status_counts)}。\n\n'
report+='''relation_type 的 none 表示没有可确认的关系类型，并不是无关系证明。not_found 行的 source_scope 不确定表示没有正面关系来源可归属；如果有已排查的共存或阴性片段，则标其实际来源。not_found 的空 evidence 表示未找到支持片段，检查范围已在 reason/conditions 与 source_blocks 文件中列明，绝不编造“未发现”的原文引语。

|边ID|基因|疾病|关系|来源|证据位置|判断|
|---|---|---|---|---|---|---|
'''
for e in edges:
    report+='|'+ '|'.join([e['edge_id'],e['gene_id'],e['disease_id'],e['relation_type'],e['source_scope'],', '.join(e['location']),e['reason']])+'|\n'
report+='''
KRIT1/CCM2/PDCD10–FCCM 的 causal 类型来自背景明确的致病陈述；本研究仅增加人类变异病例观察。不是作者新做的因果实验。ZPLD1–FCCM 仅为论文转述“proposed”关联，未叙述证据结果，保守保留 uncertain，图中 ZPLD1 为孤立节点。MAP3K3–sporadic CCM 有背景GOF变异确认与突变互斥模式的联合证据，但 MAP3K3–FCCM 仅为 could 的推测，保留 uncertain。

表1/表2的肿瘤、脊髓/皮肤CM、OLE等个案共存记录没有直接升级为基因关系。b0094 的首次CASH基因型组间差异不显著，并不等于分别否定三个基因与CASH的关系。b0094/b0095 中 PDCD10 组年龄—大病灶数量无显著相关，比较变量是年龄与病灶数，也不等于 PDCD10–CCM/FCCM explicit_negative。因此本篇在当前基因—疾病粒度没有可严谨赋值的 explicit_negative 对；这些条件性阴性结果仍保留在证据和本说明中。

## D. 二部图

network.svg 为可编辑预览；network.graphml 为带属性的可编辑图；graph.json、nodes.csv、edges.csv 包括全部节点和 supported 边。每条边有独立 E 编号、原文证据、位置、来源及条件。保留所有孤立节点（包括 PLE），不将 uncertain、not_found 或 explicit_negative 画作边。动物模型边以紫色区分；物种缺失不据大小写猜测。

## E. 质量说明与自查

已重新通读正文、2张表及脚注和3幅图注，并核对全文大写缩写列表；特别检查讨论中的ZPLD1、MAP3K3/MEKK3、动物模型名称及表2非主要诊断。核对 KRTI1 与 KRIT1、CMM 与 CCM、PLE 与 OLE；人类/动物范围分开。所有实体提及与关系引用的字符串存在性、完整笛卡尔积、重复配对、图节点/边一致性通过程序检查，详见 audit.json。该检查不能证明生物学解释完全正确，不是独立人工验证。

未解决：图片像素和补充DOCX覆盖；PLE含义；动物模型具体物种；ZPLD1所提关联的证据强度；MAP3K3对FCCM的假设；宽泛vascular malformation的关系范围；两处疑似排字错误。没有读取被引论文来独立验证背景研究，也未借外部知识补全实体或边。原文样本小、单中心、回顾性与检出偏倚限制均适用。未计算或编造准确率、召回率或置信度分数。
'''
(OUT/'report.md').write_text(report,encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
