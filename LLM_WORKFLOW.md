# 独立 LLM 试跑

这条路线直接读取原始 JATS XML，不读取 PubTator 标注。原有 outputs/ 不变，
LLM 结果写入单独目录。当前实现的调用通道是本机 OpenAI-compatible Chat Completions，
已经发现 Hermes 管理的 llama.cpp 服务；不需要再安装 Ollama。

## 运行

在项目目录的 PowerShell 中运行（端口及模型名以 Hermes 实际配置为准）：

```powershell
.\.venv\Scripts\python.exe -m biomed.llm .Input/100papers/PMC6240673.xml --output outputs_llm/qwen-pilot-PMC6240673 --base-url http://127.0.0.1:18434/v1 --model Qwen3.8-27B-UD-Q4_K_M --key-file "$env:LOCALAPPDATA/hermes/runtimes/llamacpp/.api_key"
```

`--key-file` 只在内存中使用本机凭据，不复制进项目；也可使用环境变量
`BIOMED_LOCAL_API_KEY`。不要将凭据发到聊天中。当前实现只接受 loopback HTTP，
尚未实现 GPT/Claude 的云端调用，不能声称三个模型都已完成实验。

加 `--prepare-only` 可只导出论文与实体任务 JSON，不调用模型。
独立比较不同模型必须使用不同输出目录。完成的结果禁止覆盖。
中断后相同任务哈希和模型的已完成响应可复用；输入或实现变化应使用新目录。

## 执行顺序

1. 每批最多 6000 字符，长段落切分保留 block ID 和源偏移；不丢字符。
2. 模型提取基因/疾病、物种、歧义说明和精确引用。
3. 校验引用位于当前任务中的真实文本；按类型、标准名称文本和物种保守合并。
   这不是数据库标准化；跨分块别名仍可能重复，蛋白/基因歧义被保留。
4. 生成完整的基因×疾病笛卡尔积，每批 8 对，提供整篇已解析全文。
   试跑暂限 65000 字符，超限会停止，不截断后冒充全文分析。
5. 模型给出 supported/negated/uncertain/not_found、关系类型、背景或本研究、解释及引用。
6. 每对必须有且仅有一条判断，positive/negative 判断须有精确原文证据。
7. 输出全部配对账本与图。supported 判断只画为 predicted 边，因为原文字符串
   校验不能证明模型的生物学解释正确；独立语义审核仍然 pending。

原文包括下载 XML 中解析器支持的章节、表格行、图注等；不包括参考文献列表、
外部补充材料或图片像素。分段提取可能损失跨段别名上下文，需要后续参考集评估。
无边不等于已证明无关联，not_found 也不代表医学上的负关系。

## 文件

- `tasks/`：完整提示词、输入上下文、任务哈希。
- `responses/`：原始回答文本、结构化输出、实际模型名、调用耗时、token 使用量。
- `article.json`：论文文本和稳定位置。
- `entities.json` / `entities.csv`：保守合并后的实体。
- `pairs.csv`：所有候选对及判断、证据、来源类型。
- `graph.svg` / `graph.graphml`：含孤立节点的二部图。
- `index.html`：结果与证据表。
- `manifest.json` / `run_state.json`：运行身份和完成状态。
- `result.json`：成功完成标记，失败时不发布。

`failure.json` 表示 CLI 失败；检查已保留的任务和响应，不将部分结果当成完成。
接口返回截断内容、非 JSON 或不符合证据规则时直接停止，不静默修补或换模型。

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

合成测试验证数据流和拒绝错误的能力；真实论文试跑验证接口和流程可执行性。
两者都不能替代独立人工参考集，也不能用来声称抽取准确率或召回率。

本机接口协议参考：https://github.com/ggml-org/llama.cpp/tree/master/tools/server

## 文档核对与关系复核流程

命令追加 `--workflow reviewed`，并使用新的输出目录。
原来的 `direct` 路线保留用于重现旧试验；旧结果不会被覆盖。

1. 收集原文名称表面形式，不在分段阶段合并别名或指定物种。
   试跑每批 9000 字符，程序随后按完整单词边界枚举这些名称的所有原文出现位置。
2. 文档级实体核对收到整篇论文和名称列表，可补漏、合并显式别名或排除不适用名称。
   输入的每个名称必须进入一个实体或带理由的排除账本；别名须附原文依据。
   同一字母前缀但不同数字后缀的别名组会被拒绝，转为需人工复核；这是保守保护，
   不是证明其他别名组一定正确。物种和正交基因身份仍为暂定，未做数据库归一化。
3. 对核对后的所有候选组合执行第一遍关系判断。
4. 同一个模型用新的上下文再次判断，不查看第一遍回答。两遍不同意就降为 uncertain。
   两遍都支持且关系类型一致才画预测边。相同模型会有共同偏差，不能称作独立专家验证。
5. 实体缺失、没有候选组合的名称也必须在外部参考检查中暴露，不能把没有边计作正确拒绝。

新增文件 `mentions.json`、`identity_decisions.json`、`initial_pairs.json` 和
`review_pairs.json` 保留四步中间结果。所有提示词与实际回答照常保存。
文档级核对和关系核对都使用全部已解析正文/图注，仍受试跑全文长度限制。
这条流程并不保证完整提取；第一篇试跑已显示两遍实体处理仍可能漏掉蛋白标记物。

开发参考位于 `tests/fixtures/PMC6240673_reference.json`，由助手根据原文整理，
包含范围约定和引用，不是专家金标准。它不输入模型，只在运行后检查已知问题。
因为该论文参与了流程修改，它属于开发样本，不是独立测试集。

对比命令：

```powershell
.\.venv\Scripts\python.exe -m biomed.evaluation --reference tests/fixtures/PMC6240673_reference.json --baseline outputs/papers/PMC6240673/result.json --old outputs_llm/qwen-PMC6240673/result.json --new outputs_llm/qwen-reviewed-final-PMC6240673/result.json --output outputs_llm/comparison-PMC6240673
```

对比报告是逐项问题检查，不输出总体 precision/recall/F1。缺少实体时，相关关系检查
显示无法评估，不把它当作正确的无关系判断。宽泛疾病家族的关系传播未纳入评分。

本次交付目录 `outputs_llm/qwen-reviewed-final-PMC6240673/` 从真实响应缓存重建，
重新执行全部当前代码校验，未再次推理。`qwen-reviewed-PMC6240673/` 是开发运行快照。
最终目录包含当前代码身份；两个目录的提示词任务哈希和真实模型回答可逐项对照。
