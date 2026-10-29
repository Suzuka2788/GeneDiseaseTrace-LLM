<p align="right"><a href="README.md">English</a> | <b>简体中文</b></p>

# GeneDiseaseTrace-LLM

用 LLM 从生物医学全文论文中抽取基因–疾病关系，并且每条关系都可追溯。
每条报告的关系都指向支撑它的原文句子，并标明是论文自身的发现还是背景知识；原文只是暗示的配对标为 *uncertain*，不作为关系报告。

**项目主页（结果、方法和交互图）：** https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/?lang=zh

## 任务
对 100 篇 PMC 全文论文（JATS XML）逐篇处理：抽取所有基因和疾病；对每一个基因 × 疾病配对，判断论文是否提供了关联、相关或因果关系的证据；最后为每篇论文构建一张基因–疾病二部图。

## 方法
1. **先定规则。** 在试点论文上制定判定规则（R1–R16）和 35 个边界案例，作为一个有版本管理的 skill 保存（`skill_snapshot/`，1.3.0 版）。
2. **压缩成判定卡。** 把完整规则（约 20k tokens）压缩成一张简短的判定卡：在 112 次边界案例判定中有 110 次与完整规则一致，3 次运行结果稳定。
3. **每篇论文一次请求。** 脚本把判定卡、精简的输出格式和论文的编号句子打包成一次不调用任何工具的请求，发给 Claude Opus 5.5。模型用简短的行作答，引用句子编号而不复制原文。
4. **确定性的后处理。** 脚本从原文重建引文和字符位置，补全基因 × 疾病矩阵，并写出实体、提及、证据和配对表以及 GraphML。契约校验器核对每条引文和位置；只有发现问题时，才把错误清单发回模型修正一次。

## 结果
| 评测 | 结果 | 详情 |
|---|---|---|
| 12 篇冻结论文上的 A/B 测试 | 判定卡与完整规则在 97.6% 的配对上一致，成本低 11%；低推理强度快 2.4 倍，但找到的关系更少。最终选用 V1（判定卡 + 中等推理强度）。 | [A/B 汇总](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/results/ab/ab_summary.html) |
| 全部 100 篇论文 | 100/100 通过校验；972 条 supported 关系（另有 451 对 uncertain、47 对 explicit_negative）；每篇 $0.44、78 秒。PubTator3 报告 198 条关系；我们的关系 90% 依据摘要以外的文本。 | [与 PubTator3 对比](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/results/full100/vs_pubtator.html) |
| BioRED：全部 419 篇含基因–疾病关系的摘要 | 零样本：精确率 0.89、召回率 0.43、F1 0.58（把 *uncertain* 也算作预测时为 0.81 / 0.58 / 0.68）；在 Train / Dev / Test 三部分上结果一致。在 50 篇测试摘要上：精确率与 PubTator3 持平（0.84 对 0.83），召回率较低（0.41 对 0.65）。 | [BioRED 页面](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/results/biored/biored_results.html) |
| 二部图 | 每篇论文一张图；BioRED 的图叠加在标准答案上；以及把 100 篇合并成一个网络的大图 | [二部图](https://suzuka2788.github.io/GeneDiseaseTrace-LLM-site/graphs/?lang=zh) |

**局限性。** 全文结果的精确率没有经过人工核对（BioRED 只覆盖摘要）。在 BioRED 上召回率低于 PubTator3，主要因为保守表述被单独标为 *uncertain*，以及症状与疾病分开记录。实体没有映射到数据库 ID（NCBI Gene / MeSH）。与 BioRED 的"新发现/背景"标签一致率为 75%。无法排除模型在预训练时见过这些文本。

## 仓库结构
| 路径 | 内容 |
|---|---|
| `experiments/single_shot/` | **方法本体。** 判定卡、输出格式、打包、运行、展开脚本、批量运行、冻结的 A/B 变体、与 PubTator3 的对比和页面生成；`runs/` 保存每次运行的输出。说明见 `README.md` |
| `experiments/biored/` | **基准评测。** BioRED 适配（`prepare.py`）、冻结的样本和标准答案、评分脚本（`evaluate.py`）、PubTator3 基线、结果页。说明见 `README.md` |
| `skill_snapshot/` | 判定规则：skill 1.3.0，含数据契约和边界案例（从另一个独立仓库导出） |
| `toolkit/` | 契约校验器和共用工具（也是早期 agent 模式的工具包） |
| `biomed/` | 各部分共用的 JATS 解析器和 PubTator3 客户端 |
| `baseline/` | 最早不用 LLM 的基线：把 PubTator3 标注对齐到全文（`run.ps1`、配置、审计和画图脚本） |
| `site_builder/` | 生成公开项目主页（`build_site.py`、中英双语主页模板、二部图页面） |
| `tests/` | 解析器、流程和基线的单元测试 |
| `archive/` | 开发过程记录：第一篇论文的人工标注、盲测、规则修订提案、一次性脚本 |

## 复现
需要 Python 3.12；跑模型需要先安装并登录 Claude CLI。

```bash
# 输入论文不包含在仓库中（PMC 各篇许可证不同），放在 .Input/100papers/
python experiments/single_shot/batch.py --variant v1_card_lean_medium --all --run-set full100

# BioRED：从 https://ftp.ncbi.nlm.nih.gov/pub/lu/BioRED/ 下载 BIORED.zip，放到 experiments/biored/data/ 并解压
python experiments/biored/prepare.py --all
python experiments/single_shot/batch.py --variant v1_card_lean_medium --run-set biored_all --papers <sample_all.json 中的编号>
python experiments/biored/evaluate.py v1_card_lean_medium biored_all

# 单元测试和公开主页
python -m unittest discover -s tests
python site_builder/build_site.py
```

与 PubTator3 的对比读取基线在 `outputs/` 中对齐好的标注；用 `.\baseline\run.ps1 -Command run` 生成（见 `baseline/README.md`）。

## 数据与致谢
BioRED：Luo et al., *Briefings in Bioinformatics* 2022（公有领域，NCBI）。PubTator3：NCBI。本仓库不转载 100 篇输入论文和含全文的提示词。
