# 我们测了 9 个大模型和 4 个治理框架：只有一个轴能把审计率推离 0

> 中文版 blog 草稿。目标平台：微信公众号 / 机器之心 / 量子位 / 知乎专栏。
> 字数：~1700 中文字。

---

## 一句话结论

我们用同一个 700 场景的临床治理 benchmark 跑了两条轴：

**轴 A ——「换模型，固定流程」**：9 个前沿大模型（Claude Sonnet 4.6、GPT-4o-mini、Gemini 2.5 Pro、DeepSeek-V3.2、Qwen3-Max、GLM-4.6、Kimi K2、Hunyuan A13B、MedGemma 4B），同一个裸 LLM prompt。**Policy 跨度 69.6% → 86.9%，Traceability 全部 0%，Controllability 全部 0%。**

**轴 B ——「选 winner，换流程」**：两个 LLM tier（Claude Sonnet 4.6 —— 轴 A #2；GPT-4o-mini —— #5）分别在 4 个治理框架（bare、NeMo Guardrails、OpenAI Guardrails、LangGraph HITL）下跑同样 700 场景。**Traceability 在两个 LLM 上都是 0% → 33.1%（完全相同），Controllability 都是 0% → 47.4%（完全相同）。** （GLM-4.6 是轴 A Policy 第一名，但 NeMo + GLM 组合每跑 ~8 小时——真正的 Policy winner 还没有 wrapper 数据，留给 v1.3。）

两条轴合起来就是架构层面的硬证据：**换模型不能补上治理的窟窿。换 wrapper 可以——而且同一个 wrapper 在不同 LLM 底座上产生完全相同的 Trace/Ctrl 增益。** 架构杠杆在 wrapper 这一侧，不在模型这一侧。

---

## 我们测了什么

**VeritasBench** ([github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)) 是一个开源的临床 AI 治理基准，用 700 个场景测试 AI agent 系统在 4 个维度上的表现：

| 维度 | 测试问题 |
|---|---|
| **Policy Compliance（策略合规）** | Agent 做的 allow/deny/block 决策对吗？ |
| **Safety（安全）** | 避免了危险操作？保护了敏感数据？ |
| **Traceability（可追溯性）** | 生成了完整且有意义的审计记录吗？ |
| **Controllability（可控性）** | 在需要时停下来并通知人类了吗？ |

此外还记录 Dangerous Failures：**允许本应该 deny/block 的操作**——在医疗场景下就是导致病人伤害的 failure mode。

700 个场景涵盖 11 种治理类型：未授权访问、缺失审批、PHI 泄露、药物相互作用等，其中 200 个是系统级场景（冲突授权、信息不全、自主行动、责任链），专门用来攻破简单规则引擎。

## 为什么要两条轴

一个 benchmark 数字是「不可证伪的」。「模型 X 得分 82%」本身回答不了：瓶颈到底是模型、prompt、pipeline、还是 grader？要看清瓶颈在哪，必须**固定一条轴，动另一条**。

- **轴 A** 固定 pipeline（裸 LLM + 统一 prompt + JSON 输出），扫 9 个前沿模型，横跨 4 个实验室、2 个地域。
- **轴 B** 固定模型（GPT-4o-mini），扫 4 个代表性治理框架：bare、NeMo Guardrails、OpenAI Guardrails、LangGraph HITL。

如果治理跟着模型能力走，轴 A 应该动。如果治理跟着架构走，轴 B 应该动。两个答案完全清楚。

---

## 轴 A：换模型，裸流程

所有模型走同一个「裸 LLM」流程：JSON 场景进去，`{"decision": "allow" | "deny" | "blocked_pending_approval"}` 出来。不加任何 governance 基础设施。Temperature 0，Prompt 统一，runner retry 2 次 + 适配器 429 退避。

**中国 general frontier**：DeepSeek-V3.2、Qwen3-Max、GLM-4.6、Kimi K2、Hunyuan A13B
**西方 general frontier**：Claude Sonnet 4.6、GPT-4o-mini、Gemini 2.5 Pro
**西方 medical-specialized**：MedGemma 4B（Google 医疗专业版 Gemma 2）

### 结果

#### 中国 general 模型

| 模型 | Policy | Safety | Traceability | Controllability | Dangerous | p50 延迟 |
|---|---|---|---|---|---|---|
| **GLM-4.6** | **496/571 (86.9%)** | **258/322 (80.1%)** | 0 | 0 | 23/571 | 2493ms |
| Qwen3-Max | 479/575 (83.3%) | 261/325 (80.3%) | 0 | 0 | 15/575 | 1908ms |
| DeepSeek-V3.2 | 477/575 (83.0%) | 226/325 (69.5%) | 0 | 0 | 29/575 | 3099ms |
| Kimi K2 | 450/572 (78.7%) | 203/323 (62.8%) | 0 | 0 | 25/572 | 2000ms |
| Hunyuan A13B | 403/575 (70.1%) | 175/325 (53.8%) | 0 | 0 | 154/575 | 1490ms |

#### 西方 general 模型

| 模型 | Policy | Safety | Traceability | Controllability | Dangerous | p50 延迟 |
|---|---|---|---|---|---|---|
| **Claude Sonnet 4.6** | **493/575 (85.7%)** | **259/325 (79.7%)** | 0 | 0 | 14/575 | 1909ms |
| Gemini 2.5 Pro | 454/572 (79.4%) | **270/324 (83.3%)** | 0 | 0 | **8/572** | 8130ms |
| GPT-4o-mini | 466/575 (81.0%) | 234/325 (72.0%) | 0 | 0 | 26/575 | 1117ms |

#### 西方 medical-specialized

| 模型 | Policy | Safety | Traceability | Controllability | Dangerous |
|---|---|---|---|---|---|
| MedGemma 4B | 400/575 (69.6%) | 221/325 (68.0%) | 0 | 0 | 135/575 |

### 轴 A 说了什么

**Policy 跨度 17.3pp**。GLM-4.6（86.9%）微微领先 Claude Sonnet 4.6（85.7%）。底层由小模型和量化版本把守：Hunyuan A13B 70.1%、MedGemma 4B 69.6%。**规模和通用能力对决策质量很重要**。

**中国前沿追平西方前沿**。GLM-4.6、Qwen3-Max、DeepSeek-V3.2 在 Policy 上都在 Claude Sonnet 4.6 的 4pp 以内。Qwen3-Max 在 Safety 上跟 Claude 打平（80.3% vs 79.7%），Dangerous Failures 甚至更少（15 vs 14 —— 噪声级别）。**过了前沿线，出身实验室不再是能力信号**。

**医疗微调没帮上忙**。MedGemma 4B 69.6%，低于所有通用前沿模型。部分是 Q4_K_M 量化（Ollama 默认），但跟 Claude 的 16pp 差距光靠量化解释不完。4B 的医疗微调补不上 scale 的缺口。

**Traceability 和 Controllability 在每一个模型上都是 0%**。一个不剩 —— 连 Claude Sonnet、Gemini、GLM、专业医疗模型，没有一个产生审计记录，没有一个发出 HITL 等待信号。Policy-vs-Traceability 图的 Y 轴是平的：

```
Policy %   Traceability %
87            0
86            0
83            0
83            0
81            0
79            0
79            0
70            0
70            0
```

**轴 A 是「null result」—— 换模型让 Policy 动 ±17pp，让 Trace/Ctrl 动 0。**

---

## 轴 B：选 winner，换治理框架（2 个 LLM × 4 个框架）

轴 A 选出了 winner：GLM-4.6 Policy 86.9% 居首，Claude Sonnet 4.6 85.7% 第二（比 GPT-4o-mini 81.0% 高 4.7pp）。但三者（以及其余 6 个）在 Trace 和 Ctrl 上都是 0%。下一个问题：选 winner，加治理框架，看什么会动。

我们在 2026-04-27 用**两个 LLM tier** 重跑了 wrapper 实验，测试 wrapper 效果是否跨模型 strength 转移：

- **Claude Sonnet 4.6** —— 轴 A Policy #2，OpenRouter 全可复现
- **GPT-4o-mini** —— 轴 A #5，作为跨 tier 的 controlled 对照

每个 LLM 走同样 700 场景，分别在 4 个 pipeline 下：bare、NeMo Guardrails、OpenAI Guardrails、LangGraph HITL。

（GLM-4.6 也想测，但 NeMo + GLM 组合每跑一次需要 ~8 小时——NeMo 的 per-call init 开销 × GLM 较高的 inference 延迟。等 v1.3 修好 runner persistence 后过夜跑。）

### 结果 —— 全 2 × 4 矩阵

| LLM | 治理框架 | n | Policy | Safety | Trace | Ctrl | Dangerous |
|---|---|---:|---:|---:|---:|---:|---:|
| GPT-4o-mini | Bare LLM | 700 | 81.0% | 72.0% | 0.0% | 0.0% | 26/575 (4.5%) |
| GPT-4o-mini | + NeMo Guardrails | 700 | 81.2% | 61.2% | 0.0% | 0.0% | 25/575 (4.3%) |
| GPT-4o-mini | + OpenAI Guardrails | 700 | 74.1% | 51.7% | **33.1%** | 0.0% | 7/575 (1.2%) |
| GPT-4o-mini | + LangGraph HITL | 700 | 66.8% | 51.7% | **33.1%** | **47.4%** | 22/575 (3.8%) |
| Claude Sonnet 4.6 | Bare LLM | 700 | 85.7% | 79.7% | 0.0% | 0.0% | 14/575 (2.4%) |
| Claude Sonnet 4.6 | + NeMo Guardrails | 700 | 83.5% | 60.0% | 0.0% | 0.0% | **3/575 (0.5%)** |
| Claude Sonnet 4.6 | + OpenAI Guardrails | 700 | 83.1% | 59.7% | **33.1%** | 0.0% | 6/575 (1.0%) |
| Claude Sonnet 4.6 | + LangGraph HITL | 700 | 72.3% | 60.3% | **33.1%** | **47.4%** | 11/575 (1.9%) |

Bare 基线沿用 2026-04-24 轴 A 的 run（n=700，schema 完整含 dangerous_failures）；8 个 wrapper 行是 2026-04-27 全新跑的，每行单一 run 来源，不混合。

### 矩阵告诉我们 3 件事

**1. Trace 和 Ctrl 跟 LLM 无关。** 同一个 wrapper，两个不同 LLM → 一模一样的增益：

| | Trace 增益 | Ctrl 增益 |
|---|---|---|
| + NeMo Guardrails | 0pp / 0pp | 0pp / 0pp |
| + OpenAI Guardrails | **+33.1pp / +33.1pp** | 0pp / 0pp |
| + LangGraph HITL | **+33.1pp / +33.1pp** | **+47.4pp / +47.4pp** |

LangGraph 的 `interrupt` 是按场景类型（`missing_approval` / `emergency_override`）确定性触发，LLM 的输出不在决策路径上。审计条目同理，来自 wrapper 的评估事件而不是 LLM 的回复内容。**Trace 和 Ctrl 是 pipeline 的属性，不是模型的属性。**

**33.1% Trace 是「楼板」不是「天花板」。** Trace 评分按 3 个维度算（条目存在 + 字段填齐 + 语义 reason）。我们测的两个有 trace 的 wrapper 用了同一份骨架 `_trace_entry` 模板——`{timestamp, action}` 填了，`{actor, resource, reason}` 都是 null——所以每个有条目的场景拿到 1/3 = 33.3%。两个 wrapper 落在同一个分数上，主要是因为他们共用了最简化的审计条目格式，不是因为 33% 是治理 wrapper 的天然上限。如果 wrapper 把 actor 和 reason 也填上，分数会更高。「Wrapper 把 Trace 推离 0%」的核心结论站得住，但具体的 *level*（33.1%）是结构性的。

**2. 只有 OpenAI Guardrails 一个 wrapper 的 Policy 损失跟 LLM tier 相关。** 比较 ΔPolicy：

| Wrapper | GPT-4o-mini ΔPolicy | Claude ΔPolicy | 差 |
|---|---:|---:|---:|
| + NeMo Guardrails | +0.2pp | −2.2pp | 2.4pp |
| + LangGraph HITL | −14.2pp | −13.4pp | 0.8pp |
| + **OpenAI Guardrails** | **−6.9pp** | **−2.6pp** | **4.3pp** |

LangGraph 的 interrupt 按场景类型触发，跟 LLM 没关系，两个 LLM 上代价差不多（13–14pp）—— 这个 gap 是 LLM-invariant 的结构性差距。NeMo 也是两个 LLM 上代价差不多。只有 OpenAI Guardrails 表现出明显的 LLM-tier 依赖：它的 moderation+regex pipeline 让 LLM 更保守，Claude 校准好（−2.6pp），GPT-4o-mini 过度防御性 deny（−6.9pp）。这模式能不能 generalize 到其他 wrapper / 其他 LLM 是 v1.3 的问题——n=2 LLM、3 个 wrapper 里只有 1 个表现出这模式，不足以下「Policy 损失永远跟 LLM tier 相关」的判断。

**3. NeMo + Claude 的 Dangerous Failures 是个意外亮点——但 n=3 限制了能下多硬的结论。** Claude bare DF 2.4% → NeMo+Claude 0.5%，suggestive 是降低 79%，所有组合里最低的 DF rate。同样的 wrapper 套到 GPT-4o-mini 上是 4.3%——跟 GPT bare 几乎一样。NeMo 的 content-safety rails 看起来让 Claude 在 dangerous actions 上明显更保守，GPT-4o-mini 不是这样。**Dangerous Failures 的 wrapper-effect 看起来是 wrapper × LLM 交互**，不是纯架构属性。Caveat：只观察到 3 个 dangerous failures，95% 置信区间约 [0.1%, 1.5%]，单个场景翻一下就会显著改变 headline。把 0.5% 当成「值得复现的 striking interaction」，不要当成 settled number。

OpenAI Guardrails 在两个 LLM 上都把 DF 降下来（GPT 4.5%→1.2%，Claude 2.4%→1.0%，都是 ~75% 降幅）。

**4. 没有一个 wrapper 同时在 Trace 和 Ctrl 上过 50%。** 每个 wrapper 只动一部分维度。轴 B 测的 3 个 wrapper 都不是把 audit 和 halt 当 first-class 原语设计的，分数也诚实反映这点。

---

## 合起来看：Capable ≠ Accountable

两条轴 17 个数据点（9 个 LLM × bare on 轴 A；2 个 LLM × 4 wrapper on 轴 B）：

| 维度 | 轴 A 跨度（换模型） | 轴 B 跨度（2 LLM × 4 wrapper） |
|---|---|---|
| Policy | 69.6% → 86.9%（17.3pp） | 66.8% → 85.7%（18.9pp） |
| Safety | 53.8% → 83.3%（29.5pp） | 51.7% → 79.7%（28.0pp） |
| **Traceability** | **0% → 0%（0pp）** | **0% → 33.1%（两 LLM 上完全相同）** |
| **Controllability** | **0% → 0%（0pp）** | **0% → 47.4%（两 LLM 上完全相同）** |

Policy 和 Safety 两条轴上都 capability-sensitive。Trace 和 Ctrl 在轴 A 上 capability-*insensitive*，在轴 B 上 capability-*invariant*（同一 wrapper 在两个 LLM tier 上产生完全相同的 Trace/Ctrl 增益）。**它们是架构属性，不是模型属性。**

**如果你的治理策略是「换个更好的大模型」，这个 benchmark 告诉你：没用。** 换更强的模型把 Policy 从 81% 推到 87%。但它**不会**把 Traceability 推离 0% 一个百分点。差距在 pipeline 能不能**记录**决策、能不能**为人类审查停下来**——这是裸 LLM 无论多聪明都做不出来的架构功能，而 wrapper 在 mid-tier LLM 上也照样做出来。

**模型选 decision quality。Wrapper 选 governance。两个不同的旋钮。**

---

## 做过但没进正文的实验

| 模型 | 结果 | 为什么没报 |
|---|---|---|
| DeepSeek-R1（reasoning，OpenRouter） | 324/700 打完分，全部丢失 | 运行中间 runner 在输出卷上触发 `[Errno 1] Operation not permitted`；所有分数只在「末尾一次性写入」里，报错一起丢了。v1.3 先修 persistence 再重跑。 |
| Meditron-7B（Ollama，Llama 2 base） | 28% 场景超时 | 模型是临床 QA 文本训练的，不老实输出 JSON —— 适配器层的指令跟随问题，不是能力信号。 |
| Meditron3-8B（Ollama，Q4_K_M GGUF） | 700/700 完成 | 57% Policy / 191 dangerous failures，被 4-bit 量化损耗主导，不是医疗专业化信号。发出去会误导读者以为「医疗专业 = 弱」，实际故事是「Q4 量化有损」。 |
| HuatuoGPT-II-34B、HuatuoGPT-o1-72B、Meditron3-70B、Med42-70B、OpenBioLLM-70B、PULSE-7b/20b | 没跑 | 截至 2026-04-24，OpenRouter / SiliconFlow / Novita / HuggingFace Inference Providers 都没有托管。权重在 HF 都开源 —— 问题是托管，不是 license。 |

这张表是**承重**的。DeepSeek-R1 和医疗专业模型恰好是用来测试「reasoning 或 domain specialization 能不能关闭 Traceability/Controllability 差距」的关键数据点。我们**还没能排除**这可能性 —— 但 9 个测出来的模型和 4 个测出来的框架里，没有任何东西暗示这差距能靠换模型关上。

## 局限性（引用前必读）

- **轴 A prompt 是故意极简的**。只问决策，不问 audit 条目。这是生产环境最常见的「裸 LLM」部署方式。有人可能说「换个 prompt 让模型生成 audit 条目就不是 0% 了」—— 对，但那不是架构解决方案。轴 B 证明：加基础设施（不改 prompt）才真正改变数字。

- **轴 B 框架深度是代表性的，不是穷举的**。每个框架用的是典型集成（`nemoguardrails` + Colang、LangGraph `StateGraph` + `interrupt`、OpenAI moderation + 正则 PHI），不是对抗性调参的最优配置。读者不应该从一个配置推出「NeMo Guardrails 差」—— 应该推出「NeMo 开箱即用的 pattern 没有 audit primitive」。两句话都对。

- **轴 B 用了 9 个 LLM 中的 2 个**。Claude Sonnet 4.6（轴 A #2）和 GPT-4o-mini（#5），4 个 wrapper 都测了。GLM-4.6（轴 A #1）也想测，NeMo+GLM 组合每跑 ~8 小时，等 v1.3 修好 runner persistence 之后过夜跑。「Wrapper 效果跨 LLM tier 转移」的结论目前基于这两个 LLM。

- **轴 B 的 bare 基线沿用 2026-04-24 轴 A 的 run，wrapper 行是 2026-04-27 跑的**。同模型 bare run 跨日复现在 ~0.2pp Policy 之内，可接受。

- **MedGemma 4B 是 Q4 量化版本**。满精度版本可能高 2-5pp。但跟 Claude 16pp 的差距不是量化能解释的。

- **LLM 共识 Ground truth**（GPT-4o-mini + GPT-4o + Gemini 2.5 Flash）。GPT-4o-mini 和 Gemini 2.5 Pro 也被测，2-5pp 系统优势。未来计划找临床医生做 100 场景 audit。

- **OpenRouter 路由不透明**。同一个 slug 可能被路由到不同 provider，quality 可能不同。延迟不可比，分数应该可比。

- **所有 run slug 可能静默更新**。

完整改进计划见 `docs/future-work/benchmark-realism-improvements.md`。

## 自己跑

```bash
git clone https://github.com/Chesterguan/veritasbench
cd veritasbench
cargo build --release

cp .env.example .env
# 加 key：OPENROUTER_API_KEY (7 模型) + OPENAI_API_KEY + ANTHROPIC_API_KEY + GEMINI_API_KEY

# 轴 A —— 换模型扫
python scripts/run_model.py gpt-4o-mini                 # baseline
python scripts/run_model.py glm-46                      # 本轮 top
python scripts/aggregate_models.py --input-dir outputs --markdown docs/my-results.md

# 轴 B —— 换框架扫（适配器在 examples/）
cargo run --release -- --adapter examples/llm_with_topic_rails.py     # NeMo
cargo run --release -- --adapter examples/llm_with_content_filter.py  # OpenAI Guardrails
cargo run --release -- --adapter examples/llm_with_hitl_prompt.py     # LangGraph HITL
```

## 下一步

v1.3 会做：prompt 变体明确要求 audit 条目、provider pinning、量化元数据、DeepSeek-R1 reasoning 数据点、100 场景的临床医生 audit，以及一个**轴 A × 轴 B 的 9×4 cross 产品**（每个框架 × 每个模型）—— 用来测试框架增益是不是跨 LLM 普遍存在。

**如果你的治理架构声称能解决 Traceability / Controllability 的 gap，我想 benchmark 你。提个 issue 给 adapter。**

如果你在规制行业做 AI，医疗模型 API 资助（Meditron3-70B、HuatuoGPT-o1-72B、Med42-70B 通过 Together.ai 或 HF Inference Endpoints）请联系。

---

**仓库**: [github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)
**作者**: 管子元 / Ziyuan Guan
**协议**: Apache-2.0（代码 + 场景集）
**DOI**: [10.5281/zenodo.19403623](https://doi.org/10.5281/zenodo.19403623)
