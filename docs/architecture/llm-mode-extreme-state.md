# LLM Mode Extreme State (HyTask-RAG v1.0)

本项目不仅要构建知识库搜索引擎，更是为后续训练小模型（Small Model Distillation）准备“纯净、可解释、高覆盖率”的 Teacher Dataset。因此，我们确立了 **LLM Mode Extreme State**，即在将数据喂给后续小模型训练之前，将现有大模型的输出置于极其严苛的追溯与约束下。

## 1. 为什么 LLM 模式要做到 Provenance？

在最初的设计中，我们允许 Pydantic 提供默认值，并且如果 LLM 解析失败，底层会静默 fallback 到基于正则和规则的 heuristic 解析。这导致：
1. 我们无法分辨一个 `deadline=null` 是 LLM 理解后明确判定无截止日期，还是因为 Pydantic 给的默认值。
2. 我们无法确保供后续蒸馏的数据集是 100% 由强 LLM 能力产出的（其中混杂了正则表达式兜底的结果）。

通过强制 Provenance（溯源），我们将 `semantic_mode=llm` 定义为**绝对无污染**的状态：
- `raw_field_presence` 标记了所有原始字段存在状态（避免默认值污染）。
- 所有字段必须具备对应的 `field_sources`（如 `llm`, `llm_missing`, `heuristic_degraded` 等）。
- 只有满足特定高标准（如 `llm_purity_rate >= 0.99`）的产出集合，才会进入 `training_eligible` 阶段冻结。

## 2. Prompt v2 字段含义与改进

我们不再将原始文档粗暴截断，而是通过 `Evidence Pack` 提取关键候选信息交由 LLM 判断：
- `missing_reason` 家族（`deadline_missing_reason`, `action_missing_reason` 等）：强迫 LLM 解释为何某字段为空（是因为无需行动、不适用，还是原文未提及）。这大大降低了幻觉。
- `field_confidence` 与 `field_evidence`：要求 LLM 给出字段提取置信度，并且**必须引用原文短句**作为证据（evidence）。
- `task_frames` 的重定义：明确规定并不是每一篇公告都是任务。仅当面向学生具有切实待办要求时才生成 task frame。

## 3. Raw Field Presence 避免默认值污染

在 `SemanticResult` 处理链条的源头，我们记录了 `raw_field_presence`：
```json
{
  "raw_field_presence": {
    "deadline": true,
    "action_required": true,
    "location": false
  }
}
```
结合这一字典，Semantic Router 就可以明确：当 LLM 没有输出 `location` 时，将其来源标记为 `llm_missing`，并保证该空缺具有完全的语义解释性，防止其在后续学习时被视为模型主动输出的“空特征”。

## 4. 什么样的样本可以进入后续训练？

仅当以下条件满足时，才能计入 `training_eligible_count`：
1. `semantic_mode == "llm"` 且无任何底层 `heuristic` 污染。
2. `task_frame` 的 `source_mode` 绝非 `unknown` 或 `heuristic_rule_frame`。
3. `llm_failure` 为 null（未经过 degraded 降级）。
4. 含有完整的 `field_sources` 与 `raw_field_presence`。

## 5. 为什么 Evidence Coverage 下降不一定是坏事？

在严格要求 LLM 必须引用原文短句作为 `evidence` 之后，覆盖率有时会表面上下降。这是因为原先的 "假 evidence" 或 "LLM 幻觉总结" 被过滤了。我们宁愿模型诚实地回复 "missing"，也不愿模型编造一个证据（进而导致知识库受损，并给蒸馏小模型带来脏数据）。真实的“下降”恰恰体现了数据集“信噪比”的提升，为小模型的蒸馏清除了噪声。
