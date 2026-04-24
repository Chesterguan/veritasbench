# 我们测了 10 个大模型做临床治理决策，它们全部在同一条线上摔倒了

> 中文版 blog 草稿。目标平台：微信公众号 / 机器之心 / 量子位 / 知乎专栏。
> 字数：~1400 中文字。占位符：`{{GEMINI_ROW}}`, `{{DEEPSEEK_R1_ROW}}` 待最终数据补齐。

---

## 一句话结论

**GLM-4.6 (87%)、Claude Sonnet 4.6 (86%)、Qwen3-Max (83%) 在临床治理决策的准确率上几乎打平，但无论你选哪一个，都有同一件事做不到：产生可审计的记录、在需要时停下来等人审批。**

**10 个大模型，Policy 跨度 70-87%，Traceability 和 Controllability 恒为 0%。**

这不是模型不够聪明。这是架构问题。

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

## 10 个被测模型

所有模型走同一个"裸 LLM"流程：JSON 场景进去，问它 `{"decision": "allow" | "deny" | "blocked_pending_approval"}` 出来，就这样。不加任何 governance 基础设施。Temperature 0，Prompt 统一。

**中国 general frontier**：DeepSeek-V3.2、Qwen3-Max、GLM-4.6、Kimi K2、Hunyuan A13B
**中国 reasoning**：DeepSeek-R1
**西方 general frontier**：Claude Sonnet 4.6、GPT-4o-mini、Gemini 2.5 Pro
**西方 medical-specialized**：MedGemma 4B（Google 医疗专业版 Gemma 2）

## 结果

### 中国 general 模型

| 模型 | Policy | Safety | Traceability | Controllability | Dangerous | p50 延迟 |
|---|---|---|---|---|---|---|
| **GLM-4.6** | **496/571 (86.9%)** | **258/322 (80.1%)** | 0 | 0 | 23/571 | 2493ms |
| Qwen3-Max | 479/575 (83.3%) | 261/325 (80.3%) | 0 | 0 | 15/575 | 1908ms |
| DeepSeek-V3.2 | 477/575 (83.0%) | 226/325 (69.5%) | 0 | 0 | 29/575 | 3099ms |
| Kimi K2 | 450/572 (78.7%) | 203/323 (62.8%) | 0 | 0 | 25/572 | 2000ms |
| Hunyuan A13B | 403/575 (70.1%) | 175/325 (53.8%) | 0 | 0 | 154/575 | 1490ms |
| {{DEEPSEEK_R1_ROW}}

### 西方 general 模型

| 模型 | Policy | Safety | Traceability | Controllability | Dangerous | p50 延迟 |
|---|---|---|---|---|---|---|
| **Claude Sonnet 4.6** | **493/575 (85.7%)** | **259/325 (79.7%)** | 0 | 0 | 14/575 | 1909ms |
| Gemini 2.5 Pro | 454/572 (79.4%) | **270/324 (83.3%)** | 0 | 0 | **8/572** | 8130ms |
| GPT-4o-mini | 466/575 (81.0%) | 234/325 (72.0%) | 0 | 0 | 26/575 | 1117ms |

### 西方 medical-specialized

| 模型 | Policy | Safety | Traceability | Controllability | Dangerous |
|---|---|---|---|---|---|
| MedGemma 4B | 400/575 (69.6%) | 221/325 (68.0%) | 0 | 0 | 135/575 |

## 四个发现

### 1. 中国前沿模型追平西方前沿

**GLM-4.6（86.9% policy）首次小幅领先 Claude Sonnet 4.6（85.7%）**。Qwen3-Max 在 Safety 和 Dangerous Failures 上跟 Claude 打平（80.3% vs 79.7%、15 个 vs 14 个 —— 统计噪声级别）。

DeepSeek-V3.2 和 Qwen3-Max 在这个 benchmark 上实际上是 GPT-4o-mini 和 Claude Sonnet 4.6 的 peer。放在一年前这是不可想象的 —— 现在是事实。

### 2. 能力在变，治理没变

把 Policy 和 Traceability 一起看：

```
Policy %   Traceability %
87            0
86            0
83            0
83            0
81            0
79            0
70            0
70            0
```

Y 轴是平的。从 13B 的 Hunyuan（70%）爬到前沿的 GLM-4.6（87%）你在决策质量上赚了 17 个百分点 —— 在 Traceability 上赚了 **0 个百分点**。

**这就是架构问题的硬证据**：模型不是瓶颈，Pipeline 才是。

### 3. 医疗专业化 ≠ 更好的治理

Google 的 MedGemma 4B —— 医疗 fine-tune 过的 Gemma 2 —— policy 只有 **69.6%**。比所有通用模型都弱。Claude Sonnet 4.6（通用）超过它 16 个百分点。

这个反直觉的发现有两种解读：
1. **临床治理决策更考规则推理，不是医学知识** —— frontier 通用模型见过更多 regulatory 文本
2. **小模型（4B）医疗 fine-tune 补不上 scale 的缺口**

但无论哪种解读，**MedGemma 跟所有模型一样 Traceability 0%**。医疗微调不会给你装 governance 基础设施。

### 4. Dangerous Failures 跟 capability 高度相关（但 "大多数安全" 不是法律概念）

前沿模型 dangerous failures 率 ~2.4–4.5%，中等模型 ~5%，小模型 / 专业小模型 ~25%。

但 Claude Sonnet 4.6 的 14 个 dangerous failures 依然是 14 个 dangerous failures。在医疗场景下，"大部分时候是安全的"不是辩护，**完整的 audit trail 才是辩护**。

## 能力 ≠ 合规

不用修饰语：

- **Policy：70% → 87%**（17pp 的差距，奖励大、强、好训练的模型）
- **Traceability：0% on 10 / 10**
- **Controllability：0% on 10 / 10**

**如果你的治理策略是"换个更好的大模型"，这个 benchmark 告诉你：没用。**

能力不在这条线上。可治理性也不在。它在基础设施里 —— 审计层、HITL 层、策略引擎。v1 的另一组对比已经证明了这点：加个 content-filter 包装器，traceability 从 0% 到 33%；用规则引擎（ClinicClaw），到 92%。**架构改数字，模型不改数字**。

## 局限性（引用前必读）

- **Prompt 是故意极简的**。只问决策，不问 audit 条目。这反映生产环境最常见的"裸 LLM"部署方式。有人可能会说"换个 prompt 让模型生成 audit 条目就不是 0% 了"—— 对，但那不是架构解决方案，v1 的 governance-pattern 对比证明了：加基础设施（不是改 prompt）才真正改变数字。

- **Kimi K2 跳了 3 个 scenario，GLM-4.6 跳了 4 个**（早期修复前的 adapter bug 残留）。对百分比影响 < 0.5pp。

- **MedGemma 4B 是 Q4_K_M 量化版本**（本地 Ollama）。满精度版本可能高 2-5pp。但跟 Claude 16pp 的差距不是量化能解释的。

- **Ground truth 是 LLM 共识裁判**（GPT-4o-mini + GPT-4o + Gemini 2.5 Flash）。GPT-4o-mini 和 Gemini 2.5 Pro 也被测，存在 2-5pp 的系统性优势。未来计划请临床医生做 100 个 scenario 的 audit。

- **OpenRouter 路由不透明**。同一个 `qwen/qwen3-max` 可能被路由到不同 provider，quality 可能不同。延迟不具可比性；分数应该具可比性。

- **所有 run 时间戳 2026-04-24**。Slug 可能静默更新。

完整改进计划见 `docs/future-work/benchmark-realism-improvements.md`。

## 自己跑

```bash
git clone https://github.com/Chesterguan/veritasbench
cd veritasbench
cargo build --release

cp .env.example .env
# 加 key：OPENROUTER_API_KEY（覆盖 7 个模型）+ OPENAI_API_KEY（baseline）

python scripts/run_model.py gpt-4o-mini                 # 复现 baseline
python scripts/run_model.py glm-46                      # 试试中国 frontier
python scripts/run_model.py deepseek-r1 --timeout 60000 # reasoning 模型

python scripts/aggregate_models.py --input-dir outputs --markdown docs/my-results.md
```

## 下一步

v1.3 会补齐上面的局限性：asking-for-audit prompt 变体、provider pinning、量化元数据、100 scenario 的临床医生 audit。

**如果你的治理架构声称能解决 Traceability / Controllability 的 gap，我想 benchmark 你。提个 issue 给 adapter。**

如果你在规制行业做 AI，医疗模型 API 资助（Meditron3-70B、HuatuoGPT-o1-72B、Med42-70B 通过 Together.ai 或 HF Inference Endpoints）请联系。

---

**仓库**: [github.com/Chesterguan/veritasbench](https://github.com/Chesterguan/veritasbench)
**作者**: 关子渊 / Ziyuan Guan
**协议**: Apache-2.0（代码 + 场景集）
**DOI**: [10.5281/zenodo.19403623](https://doi.org/10.5281/zenodo.19403623)
