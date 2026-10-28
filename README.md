# GeneDiseaseTrace-LLM

Evidence-traceable extraction of gene–disease relations from biomedical papers with an LLM. Every reported relation
points to the sentence(s) that support it and says whether it is the paper's own finding or background knowledge.
Pairs the paper only hints at are flagged *uncertain* instead of being reported as relations.

Built for a PhD interview task: read 100 PMC full-text papers (JATS XML), extract genes, diseases and the
evidence-supported relations between them, and build a bipartite graph per paper.

## Method in one paragraph
A rule set (`skill_snapshot/`: rules R1–R16 and 35 boundary cases) is compressed into a short decision card.
Each paper goes to Claude Opus 5.5 in **one tool-less request**: the card, a compact line format and the paper's
numbered sentences. A deterministic expander turns the reply into entity, mention, evidence and pair tables plus
GraphML, and a contract validator checks every quote and offset against the source. One repair request is sent only
if the checker finds format problems. Cost: about $0.44 and 78 s per full-text paper, $0.06 per abstract.

## Results
| Evaluation | What it shows | Where |
|---|---|---|
| A/B test, 12 frozen papers | Card ≈ full rules (97.6% pair agreement, 11% cheaper); medium vs low reasoning | `experiments/single_shot/runs/ab/ab_summary.html` |
| 100 papers vs PubTator3 | 972 supported relations vs 198; 90% rest on text beyond the abstract | `experiments/single_shot/runs/full100/v1_card_lean_medium/vs_pubtator.html` |
| BioRED, all 419 abstracts with a gene–disease relation | Precision 0.89, recall 0.43 (0.58 counting *uncertain*), F1 0.58–0.68; stable across Train/Dev/Test; same precision as PubTator3 on 50 test abstracts | `experiments/single_shot/runs/biored_all/v1_card_lean_medium/biored_results.html` |

Details, including the error analyses and caveats, are in `experiments/single_shot/README.md` and
`experiments/biored/README.md` (in Chinese).

## Layout
| Path | Contents |
|---|---|
| `experiments/single_shot/` | Single-request pipeline: card, format, packer, runner, expander, batch runner, A/B variants, comparison and page renderers, run outputs |
| `experiments/biored/` | BioRED adapter (`prepare.py`), PubTator3 baseline, scorer (`evaluate.py`), results page renderer, frozen sample and gold files |
| `skill_snapshot/` | Exported copy of the gene–disease evidence skill 1.3.0 (rules, data contract, boundary cases) |
| `toolkit/`, `biomed/`, `scripts/`, `tests/` | Shared JATS parser, PubTator3 client, contract validator, earlier agent-mode toolkit and tests |
| `outputs_*`, `manual/`, `proposals/` | Earlier rounds: manual annotation of paper 1, blind runs, rule revision proposals |

## Reproducing
- Input papers are not included because PMC licences vary. Put the 100 JATS XML files in `.Input/100papers/`.
- BioRED: download `BIORED.zip` from https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/ into `experiments/biored/data/`,
  unzip it, then run `python experiments/biored/prepare.py --all`.
- Runs need the Claude CLI signed in, e.g.
  `python experiments/single_shot/batch.py --variant v1_card_lean_medium --run-set biored_all --papers <ids>`.

---

# 早期基线（PubTator3 对齐，v0.2）

这是博士面试任务的**无需 API 密钥的自动化基线**。系统已经能够读取给定的 JATS XML 全文，获取公开 PubTator3 模型标注，与本地原文对齐，记录全部基因×疾病候选配对，生成可交互报告及二部图。

**当前不是完成语义验证的最终答案。** 图中的虚线表示模型预测，`supported_edges = 0` 表示尚未运行语义核查，并不表示论文没有支持关系。

## 本次基线结果

| 项目 | 数量 |
|---|---:|
| 成功处理的 XML | 100 / 100 |
| 逐篇累计基因节点 | 1,700 |
| 逐篇累计疾病节点 | 2,639 |
| 有记录的候选配对 | 58,844 |
| 模型预测边 | 198 |
| 已定位实体提及 | 26,958 |
| 运行失败 | 0 |

节点数量不是跨论文去重后的生物实体总数。35 项程序测试覆盖解析、配对集合、失败重跑、批次隔离、网络重试与导出行为。逐篇交付检查位于 `outputs/delivery_audit.json`，汇总图与整合图的数据一致性检查位于 `outputs/figures_integrity.json`。

## v0.2 修复内容

- 每次推理运行分配独立 `run_id`，逐篇结果记录配置哈希和输入哈希。集合报告和绘图只读取该运行明确成功的论文，失败重跑不会混入旧结果。
- 旧文件保留以便检查，但不再通过扫描文件夹自动纳入新批次。`fetch` 只更新原始标注缓存及 `fetch_manifest.json`，不会覆盖推理运行记录。
- 审计对照输入清单与本批次预期论文，空目录、缺失论文、解析/处理失败均不能通过。
- 配对校验比较完整的端点集合，能发现“条数正确但配对重复”的错误；图导出也检查实际节点和边端点。
- XML 段落中的图表被移出时，保留其后的正文；多张相邻图也有回归测试。
- 总览图及整合图读取同一批次，统计说明由实际数据生成。绘图依赖已固定在独立清单，CSV 和 JSON 转义复用已有 helper。

输入包括 69 篇研究论文、13 篇病例报告、11 篇综述，以及社论、来信、会议摘要合集等其他类型。50 篇没有现成的基因—疾病关系预测，不能据此解释为这些论文没有关系。

## 快速查收

- 双击 `outputs/index.html`，无需服务器即可打开整个结果集合。
- 选择一篇论文，查看预测图、实体别名、候选配对和对应原文。
- `outputs/summary.csv` 是逐篇统计。
- `outputs/review_queue.csv` 是自动生成的待核查项。
- `outputs/quality_report.json` 是流程诊断，不能当作准确率。
- `outputs/run_manifest.json` 记录本次运行版本、配置哈希及处理范围。

## 实际输入与方案调整

原始 Box 链接提供的是 `100papers.zip`，里面有 **100 篇 XML 论文**，不是 PDF。

因此第一版使用 Python 标准库的 XML 解析器，不需要 OCR、PDF 解析器或额外安装 Python 包。章节、表格行、图注分别保留，采用稳定的 XML block ID 定位，不编造 PDF 页码。

论文压缩包已经下载到 `.Input/100papers.zip`，并安全解压到 `.Input/100papers/`。原始文件保持不变；解析数据位于 `cache/articles/`，公开模型响应位于 `cache/pubtator/`。

## 运行

需要 Python 3.10+。本机也可使用脚本自动定位 Codex 自带的 Python。

```powershell
# 自动解析并处理所有论文。已有公开模型响应会使用缓存。
.\run.ps1 -Command run

# 只运行前 3 篇
.\run.ps1 -Command run -Limit 3

# 缓存齐全后断网重跑
.\run.ps1 -Command run -Offline

# 只解析输入，不访问外网
.\run.ps1 -Command prepare

# 程序测试，不访问外网
.\run.ps1 -Command test

# 逐篇审查输出文件完整性
.\run.ps1 -Command audit

# 已安装可选绘图环境后：重画总览图、整合图，并检查派生文件
.\run.ps1 -Command figures
```

也可直接使用 Python：

```powershell
python -m biomed.pipeline run --limit 3
python -m biomed.pipeline run --paper PMC10014009 --offline
python -m unittest discover -s tests -v
```

首次访问 PubTator 需要网络。下载和解析输入可重现：

```powershell
python scripts/download_inputs.py
```

该下载脚本验证原始压缩包 SHA-1，并拒绝目录穿越和超出预期大小的压缩包。无需密钥，不上传 XML，外部请求只使用论文 PMID 获取公开标注。查看 HTML 不访问模型服务，也不加载外部脚本。

### 独立绘图环境

基线提取和程序测试使用 Python 标准库。重新绘图需要可选的 matplotlib 环境；不再依赖 `.Resource` 中的私人安装路径。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-figures.txt
.\run.ps1 -Command run -Offline
.\run.ps1 -Command audit
.\run.ps1 -Command figures
```

依赖版本固定为本机已验证的版本，使用 Python 3.12 测试。`run.ps1` 优先使用项目 `.venv`。压缩包不包含虚拟环境或第三方库；它包含依赖清单、源码、原始输入、缓存和结果。首次安装绘图依赖需要网络或相应 wheel 缓存，查看既有图表无需安装。

移动项目或解压到新位置后，先执行离线重跑，刷新原文路径及运行记录。`--limit`/`--paper` 会形成一个新的、范围明确的子集运行，而不是把历史输出全部混合起来。

## 处理思路

1. **XML 解析**：记录标题、摘要、章节标题、正文、表格行、图注和非参考文献的后置内容。默认排除参考文献列表。
2. **模型标注**：按 PMID 获取 PubTator3 的预计算全文实体标注和现成关系预测，并缓存原始响应。
3. **本地对齐**：使用来源段落和词边界，将基因/疾病名称对齐到给定 XML。标注不能在本地内容中定位时，不直接加入节点。
4. **实体合并**：优先按实体类型和数据库 ID 合并；未解析的名称保持独立。不把标准 ID 缺失的所有实体合成一个节点。
5. **配对登记**：为每篇论文建立完整的基因×疾病笛卡尔积。存在模型关系的标记 `predicted`，其他标记 `unreviewed`。
6. **上下文检索**：提取双方共享的 XML 内容块，最多展示前 6 个，完整共享位置列表保留在配对记录中。没有共享块的预测进入跨段落检索待办。
7. **机械核查**：检查实体字符位置、证据文本、端点类型、配对数量、重复 ID，以及禁止未经语义核查的关系标成 `supported`。
8. **图与报告**：实体构成两类节点；模型预测形成虚线。所有孤立节点保留在 GraphML 和 SVG，交互图可切换显示。

目前没有用共同出现直接建立支持边；也没有把缺失预测解释成明确否定。

## 输出结构

```text
outputs/
  index.html                 # 集合报告
  inventory.csv              # 原始输入清单
  summary.csv                # 逐篇统计
  quality_report.json        # 自动诊断
  review_queue.csv           # 异常与待核查项
  run_manifest.json          # 运行记录
  run_failures.json           # 运行失败
  papers/PMC.../
    report.html              # 可交互图、实体与原文上下文
    result.json              # 完整结果与解析原文
    entities.json
    entities.csv
    relations.csv            # 只包含模型预测的配对
    pair_decisions.jsonl     # 包含所有候选配对
    graph.graphml            # 所有节点和带状态的预测边
    graph.svg                # 可直接放大查看的静态图
```

HTML 可离线查看。页面搜索及筛选在本地运行。所有来自论文的字符串通过安全转义或 `textContent` 显示。

## 判断状态与接口约定

基线只产生 `predicted` 和 `unreviewed`。后续关系核查模块可读取 `result.json` 中的 `entities`、`pairs`、`article.blocks`，输出以下状态及证据：

| 状态 | 含义 | 最终支持图连边 |
|---|---|---|
| supported | 有文内支持证据且完成语义核查 | 是 |
| explicit_negative | 检查到明确否定结果，未发现支持证据 | 否 |
| insufficient_evidence | 检查过的内容不足以支持关系 | 否 |
| unresolved | 歧义、冲突或解析问题尚未解决 | 否 |

`biomed.validate.validate()` 会拒绝没有证据或没有 `semantic_verification = passed` 的 `supported` 配对。但字段合规本身仍然不能证明医学语义正确。

当前尚未实现独立的大模型 API 调用或语义核查执行器；没有暗中调用收费服务。结构化输出是后续模块的对接格式，不应理解为核查模块已经完成。

## 已知限制与科研解释

- 预计算标注可能对应不同的 XML 版本。当前采用保守的上下文对齐，可能漏掉未成功对齐的实体。
- 基因标注可能包含蛋白质名称；物种、基因/蛋白及疾病/表型的边界尚未做语义消歧。
- 标准化也可能出错。第一篇文章中，源模型把 `brainstem lesions` 映射为 `Brain Stem Neoplasms`，把 `WHO` 标为疾病；这类原文与标准名称的对应必须复核，不能把数据库 ID 当作正确性的保证。
- 论文类型并不一致。例如 `PMC10994491` 是会议摘要合集，单个 XML 包含多个独立研究。按任务的逐文件要求仍保留一张图，但不能把跨研究的实体共现解释为关系；该文件已自动标记。输入清单保留原始 `article-type`。
- `unresolved_entity_normalization` 表示标准 ID 未解析，不表示实体必然错误；相反，有标准 ID 也不保证映射正确。
- 未读取图像像素，也未下载外部补充材料。表格行文本保留，但复杂跨行/跨列语义尚未重建。
- 参考文献默认排除；正文中的背景引用仍会保留，尚未自动区分作者新发现与引用知识。
- **全文实体标注不等于全文关系覆盖。** PubTator3 的 2024 方法论文说明当时关系抽取限于摘要；当前 API 响应也不能作为每个全文配对都已检查的证明。因此本实现只能作为关系候选基线，不能替代题目要求的全文证据分析。
- 机械核查通过不是 Precision/Recall/F1。没有独立标注样本，不报告真实准确率或召回率。
- CSV 中的节点总数按论文累加，不是跨论文唯一基因/疾病数量。

## 下一阶段

基于当前自动化基线，下一步应补充全文关系判断：对未审查配对检索跨句/跨段落证据，区分否定、推测、相关与因果；再执行独立核查。实体补漏和标准化消歧也应在该阶段加入。

最后，用独立人工标注样本评估实体和关系的准确率、召回率，再把经过核查的边作为最终任务结果提交。

## 参考来源

- 原始任务材料：[Box archive](https://app.box.com/s/cf1gqx7eeug8rd5hajno2svt3q94snvv)
- [PubTator3 官方入口](https://www.ncbi.nlm.nih.gov/research/pubtator3/)
- [PubTator3 官方 API 页面](https://www.ncbi.nlm.nih.gov/research/pubtator3/api)
- [PubTator3 方法论文，Nucleic Acids Research, 2024](https://academic.oup.com/nar/article/52/W1/W540/7640526)

## 代码位置

独立 LLM 路线、Hermes 本机接口和单篇试跑命令见 [LLM_WORKFLOW.md](LLM_WORKFLOW.md)。
这条路线不使用 PubTator 答案，结果保存在 `outputs_llm/`，不覆盖原基线。

- `biomed/jats.py`：解析与位置保留。
- `biomed/pubtator.py`：公开模型访问、实体对齐、关系候选与全配对登记。
- `biomed/validate.py`：结构和证据文本完整性检查。
- `biomed/quality.py`：自动核查队列。
- `biomed/report.py`：交互 HTML、SVG 与 GraphML。
- `biomed/pipeline.py`：批量调度、缓存复用和运行记录。
- `biomed/results.py`：读取并核对指定运行批次的结果。
- `scripts/audit_outputs.py`：逐篇检查所有图、配对账本、原文哈希和本地链接。
- `scripts/audit_figures.py`：核对汇总图、整合图的批次、统计、SVG 节点/边与来源。
