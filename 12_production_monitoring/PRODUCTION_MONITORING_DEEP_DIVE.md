# Production Monitoring — Observing, Measuring, and Improving Live Agents

> "You do not deploy an agent and finish evaluating it. You deploy an agent and *start* evaluating it — on real inputs, forever."

## Why This Matters

Every previous chapter was about evaluation *before* deployment: build a dataset, run the agent, score it, gate the release. That work ends at a single moment — the deploy — and it is measured against inputs *you* chose. Production is different in three ways that break offline eval:

1. **The inputs are not yours.** Real users ask things your dataset never imagined. The distribution shifts weekly.
2. **The world moves.** Model providers silently update weights, tools change their APIs, a downstream retrieval index goes stale. Your code did not change but your agent's behavior did.
3. **There is no ground truth.** Offline you had labels. In production you have a stream of traces and, if you are lucky, some noisy user signals. You have to *manufacture* judgment.

Production monitoring is therefore not "ops for the agent." It is **continuous evaluation**: the same measurement discipline from the rest of this book, applied to a live, unlabeled, drifting stream. Offline eval answers "is this version good enough to ship?" Monitoring answers "is it *still* good, right now, on what people are actually doing?" — and feeds what it learns back into the offline datasets so the next release is better.

This chapter covers the full loop: tracing runs, the metrics catalog, online evaluation on sampled traffic, feedback capture, drift and regression detection, alerting, and closing the loop back into your eval sets. It also grounds all of that in the concrete 2025–2026 tooling landscape — OpenTelemetry's GenAI semantic conventions, OpenLLMetry, and the tracing-plus-eval platforms (LangSmith, Langfuse, Arize Phoenix, Helicone, Braintrust) that most teams actually reach for — and in real incidents that teams have lived through.

### The mental shift interviewers listen for

A weak candidate treats production monitoring as "add Datadog and page on 5xx." A strong one articulates the shift explicitly: **the unit of observability is the agent *run*, not the HTTP request; the primary metric is *quality*, which you cannot measure directly and must approximate; and the deliverable is a *loop*, not a dashboard.** If you can say that sentence and then defend each clause, you are already ahead of most interviewees. The rest of this chapter is the defense.

---

## Core Intuition

Think of a live agent as a **factory line you cannot see inside of**. Requests go in, answers come out. Monitoring bolts sensors onto that line at four depths:

| Depth | Question it answers | Cost to collect | Latency of signal |
|---|---|---|---|
| **Operational** | Is it up, fast, cheap? | ~free (already emitted) | seconds |
| **Structural** | *What did it do* on each request? (spans) | cheap (instrumentation) | seconds |
| **Behavioral** | Was the output *good*? (online eval) | moderate (judge/human) | minutes–hours |
| **Outcome** | Did the *user* get what they wanted? (feedback) | slow, sparse, biased | hours–days |

The trap is to only measure the top row because it is free. Latency and cost tell you the factory is *running*; they say nothing about whether it is producing *scrap*. An agent can be 100% "up," p95 latency healthy, and quietly wrong on 30% of requests. The engineering job is to push measurement down the depth ladder as cheaply as you can — and the enabling technology for the bottom three rows is **structured tracing**.

There is a second axis worth internalizing: **the signal you can afford is inversely correlated with the signal you actually want.** Operational metrics are free and nearly useless for judging quality; true outcome data (did the customer's problem get solved?) is what you want and is the slowest, sparsest, most biased thing you have. Every technique in this chapter is a way to buy signal further down that ladder at a price you can pay at scale: LLM-as-judge buys behavioral signal for pennies per sampled trace; implicit feedback buys a noisy outcome proxy for free. Naming that tradeoff out loud is a green flag in interviews.

---

## The 2025–2026 Landscape

Before the techniques, orient yourself in the tooling world as it actually stands in 2025–2026, because interviewers increasingly expect you to know the *names* and how the pieces fit — not just the abstractions. The landscape has consolidated around one open standard for *how traces are shaped* and a handful of platforms for *storing, evaluating, and alerting on them*.

### The standard layer: OpenTelemetry GenAI semantic conventions

The single most important development is that **OpenTelemetry now defines GenAI semantic conventions** — a shared vocabulary for LLM and agent telemetry so a trace emitted by your app is intelligible to any backend that speaks OTel, instead of every vendor inventing its own field names. OpenTelemetry's own write-up, *Inside the LLM Call: GenAI Observability with OpenTelemetry* (opentelemetry.io, dated **May 14, 2026**), lays out the model most tools now converge on:

- **Span hierarchy.** A top-level `invoke_agent` span parents `chat` spans (LLM calls) and `execute_tool` spans (tool invocations). This is exactly the agent-run tree.
- **Core attributes**, always captured: `gen_ai.request.model` (e.g. `gpt-4o`), `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons` (`stop`, `tool_calls`, …).
- **Optional content attributes**, off by default for privacy: `gen_ai.input.messages`, `gen_ai.output.messages`, `gen_ai.system_instructions`, plus tool schemas/arguments/results. That these are *optional* is a deliberate compliance affordance — see the PII war story below.
- **Standardized metrics**: `gen_ai.client.operation.duration` (a latency histogram, filterable by model) and `gen_ai.client.token.usage` (a token histogram, filterable by `gen_ai.token.type` = input/output). An off-the-shelf collector can compute your latency and cost dashboards from these with zero custom parsing.

Status as of this writing: the conventions are **published and in active use but still evolving** (they were incubating/experimental through 2025 and stabilizing piecemeal into 2026), so pin the convention version you target and expect field additions. Greptime's *How OpenTelemetry Traces LLM Calls, Agent Reasoning, and MCP Tools* (greptime.com, **May 9, 2026**) is a good deep read on how reasoning steps and MCP tool calls map onto spans; **Datadog** shipped native ingestion of these conventions and documents the mapping in *Agent Observability natively supports OpenTelemetry GenAI Semantic Conventions* (datadoghq.com).

### The instrumentation layer: OpenLLMetry and friends

You rarely hand-write spans. **OpenLLMetry** (by Traceloop) is an open-source set of OpenTelemetry-based instrumentations that monkey-patch the OpenAI/Anthropic/LangChain/LlamaIndex SDKs and emit GenAI-convention spans automatically; because the output is plain OTel, it exports to any OTel backend. **OpenInference** (Arize) plays the same role in the Phoenix ecosystem. The practical upshot: one or two lines of setup gets you a populated span tree, and you only hand-roll spans for custom orchestration the auto-instrumentors don't see.

### The platform layer: tracing + eval, side by side

Four or five platforms dominate mindshare in 2025–2026. What unifies them is that **tracing and evaluation now live in the same product** — you capture the run *and* score it in one place, which is what makes online eval and closing-the-loop practical.

| Platform | Shape | What it is known for (2025–2026) |
|---|---|---|
| **LangSmith** (LangChain) | Commercial SaaS | Deep LangChain/LangGraph tracing, online + offline eval, feedback capture, human annotation queues. Default choice if you already build on LangChain. |
| **Langfuse** | Open-source + cloud | Self-hostable tracing, LLM-as-judge online eval, datasets, prompt management; OTel-compatible ingestion. Strong "closing-the-loop" story (traces → datasets). |
| **Arize Phoenix** | Open-source (+ Arize AX cloud) | OpenInference tracing plus a rich built-in **evals** library; inherits Arize's ML-observability lineage for drift/embedding analysis. |
| **Helicone** | Open-source + cloud | **Proxy-first**: a one-line base-URL change puts it in front of the provider API to capture cost/latency/usage and caching. Lowest-friction start. |
| **Braintrust** | Commercial SaaS | Eval-centric workflow — experiments, scorers, and production monitoring of quality/cost/latency/drift as a first-class loop. |

Comparisons worth citing rather than inventing: Helicone's *Complete Guide to LLM Observability Platforms* (helicone.ai), Braintrust's *7 best AI observability platforms* (braintrust.dev), and Digital Applied's *AI Agent Observability 2026: Tracing & Monitoring Stack* (digitalapplied.com) all survey this field with current feature matrices. Treat any single vendor's comparison as motivated; triangulate.

### The workflow layer: online LLM-judge on sampled traffic

The pattern that all of these now support first-class is **online evaluation**: attach an LLM-as-judge (or a code/heuristic scorer) to a *sample* of live traces, asynchronously and off the user's critical path, then chart the score over time and alert on regressions. Langfuse documents this as *LLM-as-a-Judge*; Phoenix ships evaluators you point at spans; LangSmith and Braintrust expose "online evaluators" / "automations" that run scorers on a configurable fraction of production traffic. This is the mainstream mechanism by which teams get a continuous quality number without labels — covered in depth in the Online Evaluation section.

### The analysis layer: production drift detection for LLM apps

Finally, **drift detection** for LLM apps has matured from a research topic into a shipped feature. Two lineages meet here: classic ML data-drift tooling (**Evidently**'s embedding-drift methods, AWS's prescriptive guidance on *Detecting drift in production applications*) and LLM-native quality-drift monitoring (rolling judge scores, refusal-rate and answer-length control charts) built into the platforms above. Braintrust's *What is LLM monitoring?* frames quality/cost/latency/drift as the four things to watch. The key 2025–2026 realization the field has converged on: **the dangerous drift is silent output-quality drift from an upstream model or index change, not input drift** — detect it by comparing a rolling quality signal to a baseline window, not by thresholding a raw number.

> How to use this section in an interview: name the three layers (standard = OTel GenAI conventions; instrumentation = OpenLLMetry/OpenInference; platform = LangSmith/Langfuse/Phoenix/Helicone/Braintrust), say online-judge-on-sampled-traffic is the online-eval mechanism, and note that OTel portability means you are not locked to one backend. That is a 30-second answer that signals you have actually shipped this.

---
## What to Monitor — A Metrics Catalog

Group production metrics into five families. For each, track the aggregate *and* the tail — averages hide the failures that matter.

### 1. Quality proxies
You rarely have per-request ground truth, so you approximate quality:

- **Online judge score** — an LLM-as-judge verdict on a *sample* of traffic (see the online-eval section). Report mean and the fraction below a pass threshold.
- **Self-consistency / refusal rate** — how often the agent bails, says "I don't know," or emits an error message to the user.
- **Task-completion rate** — fraction of runs that reached a terminal success state. For an agent this means the *final goal* was met, not that the last LLM call returned. Requires you to define machine-checkable success signals (e.g., "a ticket was created," "code compiled," "the tool returned 200 and the loop exited cleanly").

The subtle failure here is conflating *proxy* with *truth*. A judge score is a **measurement of a measurement**: the judge is itself a model with its own error bars, and every quality number you report inherits them. Discipline: for each proxy, know (a) its correlation with human judgment on your task (measure it once, re-measure quarterly), and (b) its failure direction — LLM judges are famously biased toward *longer, more confident* answers, so an answer-length collapse can *hide* behind a stable judge score if the judge rewards brevity oddly. Report proxies as a **vector**, never a scalar; a single "quality: 0.82" invites Goodharting.

### 2. Latency
Always percentiles, never just the mean — LLM latency is heavy-tailed.

- **p50 / p95 / p99 end-to-end** — wall-clock from request to final answer.
- **Time-to-first-token (TTFT)** — perceived responsiveness for streaming UIs.
- **Per-step latency** — because an agent run is a *loop*, total latency = (steps) × (per-call latency). A regression can come from more steps *or* slower calls; you need both broken out.

\[
\text{latency}_{\text{run}} \;=\; \sum_{i=1}^{N_{\text{steps}}} \big(\text{llm}_i + \text{tool}_i\big)
\]

Two agent-specific latency traps. First, **queueing/rate-limit latency** hides outside the spans you instrument: if the provider throttles you, the wall-clock gap between "request sent" and "first token" balloons while the `chat` span's own timer may not capture the wait. Instrument the *client-side* send-to-first-token gap explicitly. Second, **tail latency compounds multiplicatively across steps**: a 5-step agent where each step has a p95 of 2s does not have a run p95 of 2s — the run tail is dominated by the probability that *any* step lands in its own tail. This is why an agent that looks fine per-call can have a brutal end-to-end p99. Always chart end-to-end tail separately from per-step tail.

### 3. Cost
- **Cost per request** — derived from token usage × per-model price. Track input and output tokens separately (output is usually 3–5× the price).
- **Cost per completed task** — the honest denominator. An agent that retries five times is cheap per call and expensive per outcome.
- **Token usage** — `gen_ai.usage.input_tokens` / `output_tokens` are the OpenTelemetry-standard names; sum them per run and per model.

Add two dimensions the naive version misses. **Cached vs. uncached input tokens**: with prompt caching now standard across providers, a large system prompt can be 90% cheaper on a cache hit, so your cost model must read the cache-hit token counts from the response, not assume list price on every input token. And **cost concentration**: cost per request is heavy-tailed like latency, so a p99 cost-per-request chart catches the runaway-loop / prompt-injection-spiral requests that a mean hides. Alert on the tail, not the average.

### 4. Reliability
- **Tool-error rate** — fraction of tool calls that raise, time out, or return a malformed/unparseable payload. Break down by tool name; one flaky API poisons the whole agent.
- **Loop / step-count distribution** — runaway agents that hit the max-iteration cap are a strong failure signal.
- **Parse/format-failure rate** — how often the model emits JSON/tool-args the runtime cannot parse.

Distinguish **hard errors** (tool raised / timed out — visible, easy to alert) from **soft errors** (tool returned 200 with a wrong or empty payload the agent then reasons over — invisible in status codes, corrosive to quality). Soft errors are the reliability equivalent of silent quality drift: the only way to catch them is to score the *agent's use* of the tool result, which pushes you back to online eval. Track the **max-iteration-cap hit rate** as a leading indicator: a rising fraction of runs bumping the loop ceiling almost always precedes a cost blowout and a quality drop, because it means the agent is flailing.

### 5. Safety & guardrails
- **Guardrail hit rate** — how often an input or output guardrail fires (PII filter, jailbreak classifier, moderation, schema validator). A *spike* is either an attack or a regression that made the model misbehave.
- **Block vs. flag ratio** — of the hits, how many were hard-blocked vs. logged for review.
- **Drift signals** — input-distribution and output-quality drift (own section below), surfaced as a monitored metric, not just an offline analysis.

Guardrail metrics are double-edged: a *drop* to zero is as alarming as a spike, because it usually means a guardrail silently broke (a classifier endpoint 500ing and failing open) rather than that the world got safe. Alert on **deviation in either direction** from baseline, and separately monitor guardrail *availability* — a failed-open safety filter is an incident even when no bad content slips through, because you have lost the sensor.

> Rule of thumb: for every metric, decide up front whether you alert on it (needs a threshold and an owner) or merely dashboard it. Un-alerted metrics are documentation; alerted metrics are commitments. A useful forcing question in design review: "Who gets paged, and what do they do in the first five minutes?" If there is no answer, it is a dashboard, not an alert.

### Segmentation: the dimension that makes metrics actionable

A global metric tells you *something* changed; a *segmented* metric tells you *what*. Every metric above should be sliceable by at least: **model/prompt version**, **tool name**, **user cohort** (new vs. returning, plan tier, geo/language), **request type/intent**, and **entry surface** (API vs. UI). The reason is causal isolation: when the rolling judge score drops, the first question is "everywhere, or in one slice?" A drop confined to `model=gpt-4o` after a provider update, or to `language=de` after a launch in Germany, or to `tool=db_query` after an API change, points straight at the owner. Aggregate metrics detect; segmented metrics diagnose. Build the segmentation in from day one — retrofitting cardinality onto a metrics pipeline is painful.

---

## Tracing an Agent Run

A **trace** is the complete record of one agent run, decomposed into a tree of **spans**. A span is a single timed operation with a start, end, status, and attributes. Structured traces are the substrate everything else in this chapter is built on — you cannot compute completion rate, attribute cost, or judge quality without them.

### Why an agent needs *nested* spans, not flat logs

A single agent request is not one LLM call. It is: think → call tool A → observe → think → call tool B → observe → … → answer, possibly delegating to sub-agents. A flat log line ("request took 8s, cost $0.04") throws away exactly the structure you need to debug a failure. The span tree preserves *causality and timing*:

```
invoke_agent  (root span, 8.2s, $0.041, status=OK)
├── chat            gpt-4o           1.1s   1,240 tok
├── execute_tool    web_search       0.4s   status=OK
├── chat            gpt-4o           0.9s     980 tok
├── execute_tool    db_query         3.0s   status=ERROR (timeout)   <-- the culprit
├── chat            gpt-4o           1.0s   1,050 tok   (retry after error)
└── chat            gpt-4o           0.8s     900 tok   (final answer)
```

At a glance you see *where* the 8 seconds went and *which* tool failed. That is impossible with unstructured logs. For a *multi-agent* system the tree gets one level deeper — a planner's `invoke_agent` parents a researcher's `invoke_agent`, which parents its own `chat`/`execute_tool` children — and the same span-context propagation that carries `trace_id` across process boundaries is what stitches a sub-agent running in a different service back into the parent run. Getting context propagation right across your queue/RPC boundaries is the single most common thing teams botch; when a sub-agent's spans show up as orphan roots, you have a propagation bug, not a missing instrument.

### The GenAI semantic conventions

OpenTelemetry now ships **GenAI semantic conventions** — a standard vocabulary so traces are portable across Langfuse, Phoenix, LangSmith, Datadog, etc. instead of every vendor inventing its own field names. The three canonical span types map directly onto how agents work:

| Span type | Represents | Key attributes |
|---|---|---|
| `invoke_agent` | one agent invocation (the root) | `gen_ai.agent.name`, overall status |
| `chat` | one LLM call | `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons` |
| `execute_tool` | one tool invocation | `gen_ai.tool.name`, span `status` |

Companion metrics are standardized too: `gen_ai.client.operation.duration` (latency histogram) and `gen_ai.client.token.usage` (token histogram, filterable by `gen_ai.token.type` = input/output). Adopting these names means an off-the-shelf collector can compute your latency and cost dashboards with zero custom parsing. (Sources at the end.)

Two operational points the conventions encode that matter in practice. First, **content capture is opt-in**: `gen_ai.input.messages` / `gen_ai.output.messages` are optional attributes precisely so you can run rich structural/metric telemetry *without* persisting raw prompts and completions — the privacy default is "metrics yes, content no," and you turn content on deliberately with scrubbing in place. Second, **`finish_reasons` is a cheap quality proxy hiding in plain sight**: a rising share of `length` finishes means truncation (answers getting cut off), and a shift in `tool_calls` vs `stop` ratios often signals the model's control flow changing under a version bump — both are free to compute from a field you already emit.

### Sampling that preserves signal: head vs. tail sampling

Storing 100% of traces at scale is expensive, but naive uniform sampling throws away exactly the rare failures you care about. The distinction:

- **Head sampling** decides *at the start* of a trace whether to keep it (e.g., keep 5%). Cheap and simple, but blind — it discards errors it hasn't seen yet.
- **Tail sampling** decides *after* the trace completes, when you know its outcome. This lets you **keep 100% of traces that errored, hit a guardrail, exceeded a latency/cost threshold, or got a thumbs-down, and down-sample only the boring successes.** For agents this is almost always the right policy: the OTel Collector's tail-sampling processor implements exactly this.

The rule: **sample for storage, but bias the sample toward high-information traces.** A monitoring system that keeps a representative 5% *plus* every failure gives you both an unbiased aggregate (weight the sampled successes back up) and a complete failure corpus for debugging and dataset-building.

### Practical instrumentation

You have three options, roughly in order of effort:

1. **Auto-instrumentation** — libraries like OpenLLMetry (Traceloop) or the Phoenix/OpenInference SDKs monkey-patch the OpenAI/Anthropic/LangChain SDKs and emit spans for free.
2. **A managed SDK** — Langfuse/LangSmith decorators (`@observe`) wrap functions into spans.
3. **Hand-rolled** — emit OpenTelemetry spans yourself (the worked example below does a minimal version so the mechanics are visible).

Whatever you choose, **sample thoughtfully**: keep 100% of traces that errored or got a thumbs-down, and down-sample the boring successes to control storage cost. And **standardize the attribute set** — if half your `chat` spans lack `gen_ai.usage.output_tokens` because someone instrumented a code path by hand, your cost dashboard silently under-counts. Instrumentation completeness is itself a metric worth monitoring (fraction of `chat` spans with token attributes present should be ~100%).

---

## Online Evaluation on Live Traffic

Offline you scored every example against labels. Online you have no labels and can't afford to hand-review everything. The pattern is **sample → judge → aggregate**.

### Sampling
Judging is not free (an LLM judge is another model call; a human reviewer is expensive). So you evaluate a *slice*:

- **Uniform random sample** (e.g., 5% of traffic) for an unbiased quality estimate.
- **Stratified / targeted sampling** — oversample high-risk segments (new user cohort, a specific tool, long runs) so rare failures show up.
- **Signal-triggered** — always evaluate runs that erred, hit a guardrail, or got negative feedback. These are your highest-information samples.

How large a sample? Enough that the *confidence interval on the pass rate* is tight enough to detect the regression you care about. For a proportion \(p\) the standard error is \(\sqrt{p(1-p)/n}\); to resolve a 5-point drop in pass rate you need the interval half-width well under 0.05, which around \(p\approx0.9\) means on the order of a few hundred judged traces per window — not tens of thousands. This is why sampling works: quality is a proportion, and proportions estimate cheaply. Spend the savings on judging the *tails* densely.

### LLM-as-judge in production
Run the same rubric-based judge from Chapter 9, but on live outputs instead of a fixed dataset. In production the judge has extra constraints:

- **It is a cost and latency line-item.** Judge asynchronously, off the user's critical path — read from the trace log, score, write the score back onto the trace. Never make the user wait for the judge.
- **It must be cheap enough to run at your sample rate.** A common pattern: a small/fast model does a coarse pass on a large sample, and an expensive judge only re-scores the ones the cheap judge flags as borderline.
- **The judge itself drifts and can be gamed.** Calibrate it periodically against a human-labeled gold set (see closing-the-loop). A judge you never re-validate is a metric you should not trust.

The **async writeback** pattern deserves a diagram because it is the crux of doing this without hurting users:

```
   user request                                     (critical path — fast)
        │
        ▼
   ┌──────────┐   emit spans    ┌──────────────┐
   │  agent   │────────────────▶│  trace store │───▶ user gets answer NOW
   └──────────┘                 └──────┬───────┘
                                       │ sampled async (off critical path)
                                       ▼
                                ┌──────────────┐   score
                                │ online judge │─────────┐
                                └──────────────┘         │
                                       ▲                 ▼
                                       │        writeback: attach
                                       └────────  judge_score to trace
                                                  → rolling dashboards & alerts
```

The user never waits for the judge; the score lands on the trace seconds-to-minutes later and flows into the rolling quality metric. This is precisely the workflow LangSmith "online evaluators," Langfuse "LLM-as-a-Judge," Braintrust "online scoring," and Phoenix evals implement out of the box.

### Human review queues
LLM judges cannot ground-truth everything, especially subjective quality and safety edge cases. Route a trickle of traces — the judge's borderline cases, sampled thumbs-downs, a random audit slice — into a **human annotation queue**. Humans produce the gold labels that (a) calibrate the judge and (b) become new eval-set rows. Keep the queue small and prioritized or reviewers burn out. A healthy queue is **judge-prioritized**: send humans the traces where the judge is *least confident* or where judge and a cheap heuristic *disagree*, because those carry the most information per minute of reviewer time. Random-only queues waste reviewers on obvious passes.

Langfuse, Phoenix, and LangSmith all support attaching evaluator scores to sampled production traces and charting them over time; this is the mainstream "online eval" workflow. (Sources at the end.)

---
## Feedback Capture

User feedback is the only signal that reflects whether the agent actually *helped*. It comes in two flavors with opposite trade-offs.

### Explicit feedback
The user deliberately rates the output.

- **Thumbs up/down**, star ratings, "was this helpful?"
- **Corrections / edits** — the user rewrites the agent's answer; the diff is a rich negative-plus-target signal.
- **Free-text reports** — "this is wrong because…"

*Bias:* explicit feedback is **sparse and skewed** — typically well under 1% of users click, and they cluster at the extremes (delighted or furious). Silence is not endorsement. A 90%-thumbs-up rate among the 0.5% who rated tells you little about the median user.

### Implicit feedback
Behavior that correlates with satisfaction, collected passively.

- **Accept vs. reject / regenerate** — did the user keep the answer or hit "try again"?
- **Copy, apply, run** — did they use the code/text?
- **Conversation continuation** — did they rephrase the same question three times (bad) or move on satisfied (good)?
- **Downstream task success** — did the ticket the agent drafted get sent? Did the PR merge?

*Bias:* implicit signals are **plentiful but ambiguous** — a user leaving might mean "perfect" or "gave up in disgust." A regenerate might mean "wrong" or "curious about alternatives." Each proxy needs validation against explicit labels before you trust it.

> Practical stance: implicit feedback for *volume and trend*, explicit feedback for *ground-truth spot-checks*, and always attach whichever you capture back onto the trace so it can be joined with the spans that produced it.

The join is the whole point. A thumbs-down that is *not* linked to its trace is a complaint; a thumbs-down *joined to the span tree that produced it* is a debuggable defect and a future eval row. Design the feedback widget to carry the `trace_id` so the link is automatic, and capture feedback *latency* too — feedback that arrives minutes after the answer (a downstream "PR merged" event) needs a trace store whose retention outlives the outcome you are waiting on.

---

## Drift & Regression Detection

Two distinct things degrade a live agent. Distinguish them because the fixes differ.

### Input drift — the *questions* change
The distribution of incoming requests moves away from what you evaluated against. Nothing about your agent changed; the world did. Symptoms: a new topic cluster, a new language, longer prompts, a product launch bringing novice users.

**Methods** (borrowed from ML monitoring, applied to prompts/embeddings):

- **Embedding drift.** Embed a reference window (e.g., last month) and a current window, then measure distance between the distributions. Evidently's survey of embedding-drift methods is a good map:
  - *Domain classifier* — train a binary classifier to tell "reference" from "current" embeddings; its ROC AUC is the drift score (0.5 = indistinguishable, →1.0 = strongly drifted). Recommended default: interpretable threshold, robust to dimensionality.
  - *Euclidean / cosine distance* between mean vectors — simple, but thresholds are hard to set.
  - *Share of drifted components* — treat each embedding dimension as a feature, count how many drifted.
  - *Maximum Mean Discrepancy (MMD)* — kernel two-sample test; powerful but non-interpretable and compute-heavy.
- **Cheap tabular proxies** — track prompt length, language ID, and topic-cluster shares over time. A population-stability-index (PSI) or KL divergence on these distributions catches gross shifts for almost no cost.

Why care about input drift if quality still looks fine? Because it is the **leading** indicator: your offline eval set no longer represents production, so your pre-deploy confidence is silently expiring. Input drift rarely pages anyone on its own — it files a *ticket* that says "go collect fresh cases from these new clusters and add them to the eval set before the next release." It is the input side of the flywheel.

### Output-quality drift — the *answers* get worse
Same inputs, worse outputs. This is the dangerous one because it is silent — latency and cost look fine. Causes: a provider model update, a stale retrieval index, prompt/template rot, a dependency change.

**Methods:**

- **Rolling online-judge score** — the single most direct signal. A statistically significant drop in the mean judge score over a rolling window *is* an output-quality regression. Use a control-chart or two-window comparison rather than a fixed threshold.
- **Proxy drift** — refusal rate, answer length, tool-error rate, guardrail-hit rate. A sudden jump in refusals or a collapse in answer length often precedes a measurable quality drop and is far cheaper to compute.
- **Champion/challenger & canary** — route a small % of traffic to a new model/prompt and compare judge scores and feedback head-to-head before full rollout. This turns "did the provider break us?" from a guess into an experiment.

**Statistical tooling that separates signal from noise.** "Judge score went down" is not an incident; "judge score went down *more than noise*" is. Two workhorses:

- **Two-window test.** Compare the current window's mean judge score to a frozen baseline window with a two-sample test (t-test or, more robustly for bounded scores, a Mann–Whitney U). Alert on a significant drop *sustained across consecutive windows*, not a single dip.
- **Control charts (EWMA / CUSUM).** An exponentially-weighted moving average smooths per-trace noise and flags when the smoothed score crosses a control limit set from the baseline's own variance (\(\mu - L\sigma\sqrt{\lambda/(2-\lambda)}\)). CUSUM accumulates small persistent drops and so detects *slow* decay — exactly the silent-degradation case — faster than a fixed threshold. The worked example below implements the EWMA chart.

The reason to prefer these over a hard threshold is **base-rate stability**: a fixed "alert if judge < 0.75" fires constantly when normal variance dips below 0.75 and never fires if your baseline is 0.74. A baseline-relative, variance-aware test adapts to *your* system's noise floor.

### Output-quality drift is not always your fault — and that changes the fix

The single most valuable diagnostic move is segmenting the drop by **model/prompt version and time of the provider's last silent update**. If the judge score for `model=gpt-4o` steps down at a timestamp that matches a provider model refresh, and your prompt/code did not change, the root cause is upstream — the fix is to pin the previous model snapshot (if the provider offers dated snapshots), open a canary against the new one, and re-tune the prompt against the new behavior. If instead the drop tracks *your* last deploy, it is prompt/template rot or a code change and the fix is a rollback. Same symptom, opposite owner. A monitoring system that cannot answer "did *we* change, or did *they*?" will send you chasing the wrong fix for hours.

> Detection principle: **compare two windows, don't threshold a raw value.** "Judge score is 0.72" is meaningless; "judge score dropped from a 0.81 baseline to 0.72, p < 0.01, sustained over 6 hours" is an incident.

---

## Alerting & Incident Response for Agents

Metrics without alerts are just wall art. But agents have properties that make naive alerting fail:

- **Everything is noisy and heavy-tailed.** A single 40-second run is normal; alerting on any p99 breach pages you nightly. Alert on *sustained* breaches over a window, not instantaneous spikes.
- **Quality signals lag.** The judge score for traffic in the last hour may not be computed for another 30 minutes. Your alerting has to tolerate delayed, asynchronous metrics.
- **Cost can spike without any error.** A prompt-injection loop or a runaway agent burns money while every request returns 200 OK. Alert on **cost-per-request and step-count**, not just error rates.

### A workable alert set

| Alert | Condition (illustrative) | Severity | First response |
|---|---|---|---|
| Availability | error rate > 5% for 5 min | page | roll back / failover |
| Latency | p95 > 2× baseline for 10 min | page | check provider status, tool health |
| Cost blowout | cost/req > 3× baseline for 15 min | page | inspect step-count; kill runaway loops |
| Quality drop | rolling judge score down >10% vs. 7-day baseline, sustained | ticket | diff traces, check for model/prompt change |
| Guardrail spike | safety-hit rate > 3σ above baseline | page | possible attack; enable stricter filtering |
| Guardrail blackout | guardrail hit rate drops to ~0 or classifier unavailable | page | filter failed open; restore the sensor |
| Tool failure | any tool error rate > 20% | ticket | circuit-break that tool |
| Loop ceiling | max-iteration-cap hit rate > 2× baseline | ticket | inspect flailing runs; check tool/retrieval health |

**Incident response for agents** adds one step over normal SRE: because the failure may be *behavioral*, your runbook must include "pull the traces." The span tree tells you whether the regression is a slow tool, a changed model, more loop iterations, or worse reasoning — each has a different owner and fix. Keep the last-known-good prompt/model pinned so rollback is one config change.

### A behavioral-incident runbook (the extra step SRE doesn't teach)

```
1. TRIAGE   Which alert, which segment? Slice the failing metric by
            model/prompt version, tool, cohort, surface. Global or local?
2. TRACES   Pull 10–20 failing traces from the affected segment. Read the
            span trees end to end. Where does the run go wrong — a slow/failed
            tool, more loop steps, or genuinely worse reasoning at a chat span?
3. CLASSIFY Assign to one of four owners:
              - slow/failed tool   → tool/infra owner (circuit-break, failover)
              - more loop steps    → orchestration owner (prompt/policy)
              - changed model      → provider issue (pin snapshot, canary)
              - worse reasoning     → prompt/model owner (rollback or re-tune)
4. MITIGATE Fastest safe action: roll back to pinned last-known-good
            prompt/model, or circuit-break the tool, or shed the bad segment.
5. LEARN    Turn the failing traces into eval rows; add a regression test so
            this class of failure can never silently return (close the loop).
```

The difference between a 20-minute incident and a 4-hour one is almost always step 2: teams that cannot pull traces fast argue about hypotheses; teams that can, read the answer off the span tree.

### Fighting alert fatigue on purpose

Every page that turns out to be noise trains the on-call to ignore the next one — including the real one. Concrete anti-fatigue practices: (1) alert on **sustained, windowed, baseline-relative** conditions, never instantaneous raw thresholds; (2) require **multi-signal confirmation** for quality pages (judge-score drop *and* a refusal-rate or feedback move) so a judge hiccup alone doesn't wake anyone; (3) route everything that isn't "act in the next 15 minutes" to **tickets and dashboards**, not pages; (4) track your **alert precision** (fraction of pages that led to action) as a first-class metric and tune any alert under ~50% precision. An alert nobody trusts is worse than no alert, because it consumes attention *and* provides false assurance.

---
## Worked Example — Instrument, Aggregate, Alert (in-process)

This self-contained example (1) instruments an agent run into structured spans, (2) computes rolling production metrics from a stream of finished traces, and (3) fires a simple drift/regression alert. No external services; standard library only. Copy-run.

```python
"""
Production monitoring in ~150 lines: spans -> rolling metrics -> drift alert.
Standard library only. Illustrative, not a framework.
"""
from __future__ import annotations
import time, uuid, random, statistics
from collections import deque
from dataclasses import dataclass, field, asdict
from contextlib import contextmanager
from typing import Optional

# ---------- 1. Minimal structured tracing (OTel-GenAI-flavored) ----------

# Per-1K-token prices (USD). Output priced higher than input, as in reality.
PRICES = {"gpt-4o": {"in": 0.0025, "out": 0.01}}

@dataclass
class Span:
    name: str                      # "invoke_agent" | "chat" | "execute_tool"
    start: float
    end: Optional[float] = None
    status: str = "OK"             # "OK" | "ERROR"
    attrs: dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return (self.end or time.perf_counter()) - self.start

@dataclass
class Trace:
    trace_id: str
    spans: list = field(default_factory=list)

    def cost_usd(self) -> float:
        total = 0.0
        for s in self.spans:
            if s.name == "chat":
                p = PRICES.get(s.attrs.get("model", ""), {"in": 0, "out": 0})
                total += (s.attrs.get("input_tokens", 0) / 1000) * p["in"]
                total += (s.attrs.get("output_tokens", 0) / 1000) * p["out"]
        return total

    def latency(self) -> float:
        root = next(s for s in self.spans if s.name == "invoke_agent")
        return root.duration

    def tool_error_rate(self) -> float:
        tools = [s for s in self.spans if s.name == "execute_tool"]
        if not tools:
            return 0.0
        return sum(s.status == "ERROR" for s in tools) / len(tools)

    def completed(self) -> bool:
        root = next(s for s in self.spans if s.name == "invoke_agent")
        return root.status == "OK" and root.attrs.get("final_answer") is not None

class Tracer:
    def __init__(self):
        self.trace = Trace(trace_id=str(uuid.uuid4()))

    @contextmanager
    def span(self, name: str, **attrs):
        s = Span(name=name, start=time.perf_counter(), attrs=attrs)
        self.trace.spans.append(s)
        try:
            yield s
        except Exception:
            s.status = "ERROR"
            raise
        finally:
            s.end = time.perf_counter()

# ---------- 2. A toy agent that emits spans ----------

def fake_llm_call(tracer, prompt_tokens, degraded=False):
    with tracer.span("chat", model="gpt-4o",
                     input_tokens=prompt_tokens,
                     output_tokens=random.randint(200, 400)) as s:
        time.sleep(0.001)
        # Under degradation the model rambles (proxy for quality drift).
        if degraded:
            s.attrs["output_tokens"] = random.randint(600, 900)
        s.attrs["finish_reason"] = "stop"

def fake_tool_call(tracer, name, fail_prob=0.05):
    with tracer.span("execute_tool", tool=name):
        time.sleep(0.001)
        if random.random() < fail_prob:
            raise TimeoutError(f"{name} timed out")

def run_agent(degraded=False, tool_fail=0.05) -> Trace:
    tracer = Tracer()
    with tracer.span("invoke_agent", agent="researcher") as root:
        try:
            fake_llm_call(tracer, 1200, degraded)
            try:
                fake_tool_call(tracer, "web_search", tool_fail)
            except TimeoutError:
                pass  # agent observes the error and retries once
            fake_llm_call(tracer, 1500, degraded)
            root.attrs["final_answer"] = "…answer…"
        except Exception:
            root.status = "ERROR"
    return tracer.trace

# ---------- 3. Rolling metrics + two-window drift/regression alert ----------

class RollingMonitor:
    """Maintains a sliding window of recent traces and compares it to a
    frozen baseline to detect regressions. Compare windows, don't threshold
    raw values."""
    def __init__(self, window=200):
        self.window = deque(maxlen=window)
        self.baseline: Optional[dict] = None

    def observe(self, tr: Trace):
        self.window.append({
            "latency": tr.latency(),
            "cost": tr.cost_usd(),
            "tool_err": tr.tool_error_rate(),
            "completed": tr.completed(),
            # Proxy for output quality: shorter, on-spec answers score higher.
            # In prod this field is an async LLM-judge score written back later.
            "quality": max(0.0, 1.0 - sum(
                s.attrs.get("output_tokens", 0) for s in tr.spans
                if s.name == "chat") / 2000),
        })

    def snapshot(self) -> dict:
        w = list(self.window)
        n = len(w)
        pick = lambda k: [x[k] for x in w]
        p95 = lambda xs: sorted(xs)[max(0, int(0.95 * len(xs)) - 1)]
        return {
            "n": n,
            "latency_p50": statistics.median(pick("latency")),
            "latency_p95": p95(pick("latency")),
            "cost_per_req": statistics.mean(pick("cost")),
            "tool_error_rate": statistics.mean(pick("tool_err")),
            "completion_rate": statistics.mean(pick("completed")),
            "quality_mean": statistics.mean(pick("quality")),
        }

    def freeze_baseline(self):
        self.baseline = self.snapshot()

    def check_regression(self, rel_drop=0.10) -> list[str]:
        """Alert when the current window's quality drops >rel_drop below the
        frozen baseline. Returns a list of alert strings (empty = healthy)."""
        alerts = []
        if not self.baseline or len(self.window) < self.window.maxlen // 2:
            return alerts
        cur = self.snapshot()
        base_q, cur_q = self.baseline["quality_mean"], cur["quality_mean"]
        if base_q > 0 and (base_q - cur_q) / base_q > rel_drop:
            alerts.append(
                f"QUALITY REGRESSION: {base_q:.3f} -> {cur_q:.3f} "
                f"({100*(base_q-cur_q)/base_q:.1f}% drop)")
        if cur["tool_error_rate"] > 0.20:
            alerts.append(f"TOOL ERROR SPIKE: {cur['tool_error_rate']:.1%}")
        if cur["cost_per_req"] > 1.5 * self.baseline["cost_per_req"]:
            alerts.append(
                f"COST BLOWOUT: ${cur['cost_per_req']:.4f}/req "
                f"vs ${self.baseline['cost_per_req']:.4f} baseline")
        return alerts

# ---------- 4. Simulate a healthy period, then an incident ----------

if __name__ == "__main__":
    random.seed(0)
    mon = RollingMonitor(window=200)

    # Healthy baseline traffic.
    for _ in range(200):
        mon.observe(run_agent(degraded=False, tool_fail=0.05))
    mon.freeze_baseline()
    print("BASELINE:", {k: round(v, 4) for k, v in mon.snapshot().items()})

    # A provider update degrades output quality; a tool starts flaking.
    for _ in range(200):
        mon.observe(run_agent(degraded=True, tool_fail=0.30))

    print("CURRENT :", {k: round(v, 4) for k, v in mon.snapshot().items()})
    for a in mon.check_regression():
        print("  ALERT:", a)
```

Running it prints a healthy baseline, then the degraded window trips the quality-regression and tool-error alerts — the two-window comparison catches a silent quality drop that a raw threshold on "quality > 0.5" would have missed. The `quality` field here is a stand-in for the async LLM-judge score you would write back onto the trace in a real system; everything else (spans, cost from token prices, tool-error rate, completion) is computed exactly as production code would.

**What is faithful to production:** structured spans with OTel-style attributes; cost derived from per-model input/output token prices; percentiles not means; window-vs-baseline regression detection. **What is simplified:** the judge is a heuristic on token count, there is no async pipeline or persistence, and real sampling/PII-scrubbing are omitted.

---

## Build It In Practice — From a Trace Log Stream

The in-process example above shows the mechanics. Real monitoring is **decoupled**: your agent emits spans to a durable stream (an OTLP exporter, a Kafka topic, or newline-delimited JSON on disk), and a *separate* consumer scrubs PII, runs a sampled async judge, maintains rolling metrics, and fires drift alerts. That decoupling is what keeps judging off the user's critical path and lets you reprocess history when you change a metric. This second example builds that consumer end-to-end — still standard-library only, still copy-runnable — and adds the three things the first example simplified away: **PII scrubbing at ingestion, an EWMA control chart for silent drift, and reading traces as a stream instead of in-process objects.**

```python
"""
Production monitoring from a TRACE LOG STREAM.
A producer emits one JSON object per finished trace (an OTLP-ish export).
A decoupled consumer: scrubs PII -> samples & 'judges' async -> maintains
rolling metrics per bucket -> fires an EWMA control-chart drift alert.
Standard library only. Copy-run:  python3 this_file.py
"""
from __future__ import annotations
import io, json, re, random, statistics
from collections import deque

# ============================================================ #
# 0.  PII SCRUBBING AT INGESTION                               #
#     Never persist raw user content unredacted. Scrub the     #
#     moment a trace enters the pipeline, before storage.      #
# ============================================================ #
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SSN   = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD  = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_PHONE = re.compile(r"\b\+?\d[\d ().-]{7,}\d\b")

def scrub(text):
    """Redact common PII classes. Order matters: SSN/card before phone,
    since a bare digit run could match multiple patterns."""
    if not isinstance(text, str):
        return text
    text = _EMAIL.sub("<email>", text)
    text = _SSN.sub("<ssn>", text)
    text = _CARD.sub("<card>", text)
    text = _PHONE.sub("<phone>", text)
    return text

# ============================================================ #
# 1.  PRODUCER — emit finished traces as a JSONL stream        #
# ============================================================ #
PRICES = {  # USD per 1K tokens
    "gpt-4o":      {"in": 0.0025,  "out": 0.010},
    "gpt-4o-mini": {"in": 0.00015, "out": 0.0006},
}

def make_trace(i, degraded=False, tool_fail=0.05, rng=random):
    """Build one agent-run trace: two chat spans + one tool span."""
    spans = []
    def add(name, dur, status="OK", **attrs):
        spans.append({"name": name, "duration_s": round(dur, 4),
                      "status": status, "attrs": attrs})

    out1 = rng.randint(600, 900) if degraded else rng.randint(200, 400)
    add("chat", rng.uniform(0.6, 1.3), model="gpt-4o",
        input_tokens=1200, output_tokens=out1, finish_reason="stop")

    if rng.random() < tool_fail:
        add("execute_tool", rng.uniform(2.0, 4.0), status="ERROR", tool="db_query")
    else:
        add("execute_tool", rng.uniform(0.2, 0.6), tool="db_query")

    out2 = rng.randint(600, 900) if degraded else rng.randint(200, 400)
    add("chat", rng.uniform(0.6, 1.3), model="gpt-4o",
        input_tokens=1500, output_tokens=out2, finish_reason="stop")

    # Raw user content contains PII on purpose, to exercise the scrubber.
    return {
        "trace_id": f"tr-{i:06d}",
        "ts": i,                                  # logical monotone time
        "agent": "support-bot",
        "root_status": "OK",
        "user_msg": "hi, email me at jane.doe@acme.com about order 55-12-3456",
        "final_answer": "Your order ships tomorrow.",
        "spans": spans,
    }

def stream(n, degraded=False, tool_fail=0.05, start=0, seed=0):
    """Yield JSONL lines — the on-the-wire format a consumer would read."""
    rng = random.Random(seed)
    for k in range(n):
        yield json.dumps(make_trace(start + k, degraded, tool_fail, rng))

# ============================================================ #
# 2.  DERIVED METRICS from a trace dict                        #
# ============================================================ #
def cost_usd(tr):
    total = 0.0
    for s in tr["spans"]:
        if s["name"] == "chat":
            p = PRICES.get(s["attrs"].get("model", ""), {"in": 0, "out": 0})
            total += s["attrs"].get("input_tokens", 0) / 1000 * p["in"]
            total += s["attrs"].get("output_tokens", 0) / 1000 * p["out"]
    return total

def latency_s(tr):
    return sum(s["duration_s"] for s in tr["spans"])

def tool_error_rate(tr):
    tools = [s for s in tr["spans"] if s["name"] == "execute_tool"]
    return sum(s["status"] == "ERROR" for s in tools) / len(tools) if tools else 0.0

def output_tokens(tr):
    return sum(s["attrs"].get("output_tokens", 0)
               for s in tr["spans"] if s["name"] == "chat")

# ============================================================ #
# 3.  ASYNC-ISH LLM JUDGE (sampled, off critical path)         #
#     Stand-in heuristic: rambly (long) answers score lower.   #
#     In prod this is a real judge call, run on a sample, its  #
#     score written back onto the trace seconds/minutes later. #
# ============================================================ #
def judge(tr):
    return max(0.0, min(1.0, 1.0 - output_tokens(tr) / 2000.0))

# ============================================================ #
# 4.  EWMA CONTROL CHART for silent quality drift              #
#     z_t = λ·x_t + (1-λ)·z_{t-1}; alert when z crosses a      #
#     lower control limit derived from the baseline variance.  #
# ============================================================ #
class EWMAChart:
    def __init__(self, lam=0.2, L=3.0):
        self.lam, self.L = lam, L
        self.mu = self.sigma = self.z = None

    def calibrate(self, xs):
        self.mu = statistics.mean(xs)
        self.sigma = (statistics.pvariance(xs) ** 0.5) or 1e-9
        self.z = self.mu

    def update(self, x):
        self.z = self.lam * x + (1 - self.lam) * self.z
        half = self.L * self.sigma * (self.lam / (2 - self.lam)) ** 0.5
        lcl = self.mu - half                      # lower control limit
        return self.z, lcl, self.z < lcl

# ============================================================ #
# 5.  ROLLING WINDOW of recent judged traces                   #
# ============================================================ #
class Window:
    def __init__(self, size=300):
        self.buf = deque(maxlen=size)

    def add(self, rec): self.buf.append(rec)

    def snapshot(self):
        w = list(self.buf)
        if not w:
            return {}
        pick = lambda k: [r[k] for r in w if r[k] is not None]
        lat = sorted(pick("latency"))
        p95 = lat[max(0, int(0.95 * len(lat)) - 1)]
        q = pick("quality")
        return {
            "n": len(w),
            "latency_p95": round(p95, 3),
            "cost_per_req": round(statistics.mean(pick("cost")), 5),
            "tool_error_rate": round(statistics.mean(pick("tool_err")), 3),
            "quality_mean": round(statistics.mean(q), 3) if q else None,
        }

# ============================================================ #
# 6.  THE CONSUMER — one pass over the stream                  #
# ============================================================ #
def consume(lines, chart, window, sample_rate=0.25, rng=random,
            alert_sink=None):
    fired = []
    for raw in lines:
        tr = json.loads(raw)

        # (a) SCRUB before anything is stored or logged.
        tr["user_msg"]     = scrub(tr["user_msg"])
        tr["final_answer"] = scrub(tr["final_answer"])

        # (b) Always-cheap structural/operational metrics.
        rec = {
            "latency": latency_s(tr),
            "cost": cost_usd(tr),
            "tool_err": tool_error_rate(tr),
            "quality": None,                      # filled only if sampled
        }

        # (c) Sampled async judge (+ always judge error/guardrail traces).
        if rng.random() < sample_rate:
            rec["quality"] = judge(tr)
            if chart.z is not None:
                z, lcl, breached = chart.update(rec["quality"])
                if breached:
                    msg = (f"[{tr['trace_id']}] QUALITY DRIFT: EWMA {z:.3f} "
                           f"< LCL {lcl:.3f} (baseline mean {chart.mu:.3f})")
                    fired.append((tr["ts"], msg))
                    if alert_sink:
                        alert_sink(msg)

        window.add(rec)
    return fired

# ============================================================ #
# 7.  RUN: calibrate on healthy traffic, then inject a decay   #
# ============================================================ #
if __name__ == "__main__":
    rng = random.Random(0)

    # --- Calibration: judge a batch of healthy traffic to set baseline. ---
    healthy = [json.loads(l) for l in stream(400, degraded=False,
                                             tool_fail=0.05, seed=1)]
    base_scores = [judge(t) for t in healthy]
    chart = EWMAChart(lam=0.2, L=3.0)
    chart.calibrate(base_scores)
    print(f"CALIBRATED EWMA: baseline mean={chart.mu:.3f} "
          f"sigma={chart.sigma:.3f}")

    win = Window(size=300)

    # Confirm PII scrubbing on the first trace.
    demo = json.loads(next(stream(1, seed=2)))
    print("SCRUBBED user_msg:", scrub(demo["user_msg"]))

    # --- Healthy period: no drift expected. ---
    consume(stream(300, degraded=False, tool_fail=0.05, start=1000, seed=3),
            chart, win, rng=rng)
    print("HEALTHY WINDOW  :", win.snapshot())

    # --- Incident: provider update degrades quality; a tool starts flaking. ---
    alerts = consume(stream(300, degraded=True, tool_fail=0.30, start=2000,
                            seed=4),
                     chart, win, rng=rng)
    print("DEGRADED WINDOW :", win.snapshot())
    if alerts:
        first_ts, first_msg = alerts[0]
        print(f"FIRST DRIFT ALERT at ts={first_ts}: {first_msg}")
        print(f"total drift alerts in incident window: {len(alerts)}")
    else:
        print("no drift detected (unexpected)")
```

What this version demonstrates that the first did not:

1. **Decoupling via a stream.** The producer emits JSONL; the consumer reads it line by line exactly as it would read from Kafka or an OTLP export. You can persist the stream and *re-run the consumer* with a new metric definition over historical traffic — impossible with in-process objects.
2. **PII scrubbing at ingestion.** `scrub()` redacts email/SSN/card/phone *before* the trace is stored, so raw user content never lands in the metrics store. The demo line prints the redacted message so you can see it working. (Real systems layer a named-entity model on top of regex for names/addresses.)
3. **EWMA control chart.** Instead of a fixed threshold, the chart calibrates on healthy traffic (mean and variance) and alerts when the smoothed quality score crosses a lower control limit scaled by the baseline's own noise. This catches **slow, silent decay** — the dangerous case — and adapts to your system's real noise floor. Run it: the healthy window stays quiet, and the degraded window fires a drift alert within the first handful of judged traces after the decay begins.
4. **Sampling on the judge, not on operational metrics.** Latency/cost/tool-error are computed on 100% of traces (they are cheap); the judge runs on a 25% sample (it is expensive). That is the real cost structure.

**Still simplified for runnability:** the judge is a token-count heuristic rather than a real model call; there is no persistence layer, no genuine async queue, no time-bucketing by wall clock, and the regex scrubber would be augmented with an NER model in production. The *shapes* — stream in, scrub, sample-and-judge, roll up, control-chart, alert — are exactly production's.

---
## Closing the Loop

The payoff of all this instrumentation is not the dashboard — it is the **flywheel** that makes the next release better. Production is the richest source of eval data you will ever have, because it is real.

The loop:

1. **Mine traces for interesting cases.** Every thumbs-down, guardrail hit, tool error, low judge score, and human-flagged run is a candidate.
2. **Curate them into eval datasets.** Cluster the failures, dedupe, and turn representative ones into new offline test cases — ideally with a human-written expected output or a checkable success condition. This is exactly the dataset-construction discipline from Chapter 10, but sourced from reality instead of imagination.
3. **Label a gold set to calibrate the judge.** Periodically have humans score a sample the LLM-judge also scored; measure judge–human agreement. If it drifts, fix the rubric before trusting the online score again.
4. **Reproduce and fix.** The new cases become regression tests. The fix (prompt change, tool patch, model swap) is validated offline against them *before* redeploy.
5. **Canary the fix**, watch the same production metrics, and confirm the regression is gone.

Every trip around the loop transfers knowledge from production back into your offline suite, so the class of failure you saw once can never silently return. Offline eval and production monitoring are not two phases — they are one loop that never stops turning.

```
        ┌─────────────────────── THE FLYWHEEL ───────────────────────┐
        │                                                             │
   ┌──────────┐   traces    ┌───────────┐   curate    ┌────────────┐ │
   │ PRODUCTION│──────────▶ │  mine     │──────────▶ │  offline   │ │
   │  agent    │  (fails,    │ failures  │ (cluster,   │  eval set  │ │
   └────▲──────┘  thumbs-dn) └───────────┘  dedupe)    └─────┬──────┘ │
        │                                                    │        │
        │ canary + watch same metrics                        │ becomes│
        │                                              regression tests
   ┌────┴──────┐   validate offline    ┌───────────┐         │        │
   │  deploy   │◀──────────────────────│    fix    │◀────────┘        │
   │  fix      │   against new cases    │ prompt/   │                  │
   └───────────┘                        │ tool/model│                  │
        └─────────────────────────────────────────────────────────────┘
```

The organizational tell of a team that has *actually* closed the loop: their offline eval set **grows every week**, and each row can be traced back to a real production incident. A static eval set that hasn't changed since launch is a team that is monitoring but not learning.

---

## Production Case Studies & War Stories

Abstract principles stick when attached to scars. These are composite but faithful accounts of how teams monitor agents in 2025–2026 and what goes wrong — drawn from the public write-ups cited in Further Reading and the recurring patterns they describe.

### Case study 1 — Closing the loop: traces → curated eval sets

**Setup.** A mid-size SaaS ships a customer-support agent (retrieval + a handful of account-action tools). At launch they had a 200-row offline eval set hand-written by the team. Within a month, production was throwing question shapes the set never imagined.

**What they built.** Tail-sampling kept 100% of thumbs-downs, guardrail hits, and tool errors, plus a 5% random slice. A nightly job clustered the kept failures by embedding, and a human spent 30 minutes triaging the top clusters into the offline eval set with checkable expected outcomes. An online LLM-judge scored a 10% sample; its score was calibrated weekly against a 50-row human-labeled gold set.

**The payoff.** The eval set grew from 200 to ~1,400 rows in a quarter, every new row sourced from a real failure. When they later swapped the underlying model, the *expanded* offline suite caught two regressions the original 200 rows missed — because those failure shapes only existed in the set *because production had surfaced them first*. This is the flywheel working: the class of failure seen once became a permanent regression test. Langfuse's and LangSmith's "add trace to dataset" flows exist precisely to make this one click; the discipline, not the tooling, is the hard part.

**Lesson.** The eval set is a living artifact. If yours hasn't grown since launch, you are flying on last quarter's map.

### Case study 2 — Silent quality decay after a provider model update

**The incident.** A coding-assistant agent's users started quietly complaining that "it feels dumber this week." Every operational dashboard was green: availability 99.9%, p95 latency normal, cost normal, zero error-rate change. Support tickets rose ~15% but nobody connected them to the agent.

**Why it was invisible.** The provider had silently rolled a new snapshot behind the same model alias. The agent's *code and prompts had not changed* — so every SRE instinct (check the last deploy, check error rates) pointed at nothing. The regression was purely behavioral: the new model was slightly worse at following the agent's tool-use format, so it more often produced plausible-but-wrong final answers. Latency and cost — the free metrics — cannot see this. This is exactly the failure class documented in industry write-ups on LLM degradation (e.g. the AI incident-response playbooks and "AI agents break without deploys" pieces in Further Reading).

**How it should have been caught.** A rolling online-judge score with a two-window / EWMA control chart would have stepped down at the snapshot timestamp — the very signal the worked example fires on. Segmenting the judge drop by `model` and correlating with the provider's release note pins the cause in minutes. The fix pattern: pin the previous dated snapshot if available, open a canary against the new one, and re-tune the prompt/format instructions to the new model's behavior before rolling forward.

**Lesson.** *"Our code didn't change" is not "our behavior didn't change."* The dangerous regressions are the silent, behavioral ones with no error and no deploy. If your only quality signal is user complaints, your detection latency is measured in weeks and paid in churn. Monitor a quality proxy, or you are not monitoring quality.

### Case study 3 — PII in traces: the observability data *is* the liability

**The incident.** A team turned on full message-content capture (`gen_ai.input.messages` / `gen_ai.output.messages`) to debug a nasty multi-turn failure. It worked — and it also meant every raw user prompt, including names, emails, and in a few cases payment details, was now sitting in the trace store and mirrored to a third-party observability SaaS, retained for 30 days, readable by the whole engineering org. A privacy review flagged it; it became a compliance incident.

**Why it happens.** Content capture is the single most useful debugging affordance and the single biggest privacy footgun, which is *exactly why the OTel GenAI conventions make message content optional and off by default*. The moment you flip it on, your observability pipeline becomes a system that processes personal data and inherits all the obligations that come with it.

**The fixes, layered.** Scrub PII at ingestion *before* storage (regex for structured PII like emails/SSNs/cards, augmented with an NER model for names/addresses) — as the log-stream example does in `scrub()`. Prefer metrics-and-structure by default and turn content capture on only for a sampled, short-retention, access-controlled debug slice. Set aggressive retention on anything containing content. Treat "which fields leave our trust boundary to a third-party SaaS" as a design decision, not a default.

**Lesson.** Your traces are a copy of everything your users said. Instrument as if a regulator will read the trace store — because one might.

### Case study 4 — Alert fatigue: the page that cried wolf

**The incident.** Eager to be "observable," a team wired up p99-latency alerts, per-tool error alerts, cost alerts, and a raw-threshold judge-score alert — all paging, all on instantaneous values. Within two weeks the on-call was getting 15–20 pages a night, essentially all noise from the heavy tail of normal LLM latency and the natural variance of a raw judge threshold. Predictably, when a *real* tool outage hit, the page was acknowledged-and-ignored like all the others; the incident ran for three hours before someone noticed the customer impact.

**Root cause.** Alerting on instantaneous, raw-threshold conditions in a domain where the metrics are inherently noisy and heavy-tailed. Every design choice that makes an LLM metric realistic (fat tails, judge variance, async lag) makes a naive threshold fire constantly.

**The fixes.** Move to **sustained, windowed, baseline-relative** conditions; require **multi-signal confirmation** for quality pages; demote everything non-urgent to tickets/dashboards; and track **alert precision** (share of pages that led to action), tuning any alert below ~50%. After the rework, nightly pages dropped to near zero and the next real incident was caught in minutes.

**Lesson.** An alert the on-call has learned to ignore is worse than no alert: it costs attention *and* gives false assurance. Alert precision is a first-class SLO for the monitoring system itself.

### Cross-cutting lesson

Notice the through-line across all four: **the free, operational signals (up/fast/cheap) were fine in every quality incident.** Decay, PII exposure, and behavioral regressions all live *below* the operational layer. The entire discipline of this chapter is buying signal down the depth ladder — structural, behavioral, outcome — because that is where the failures that actually hurt users live, and where naive monitoring is blind.

---

## Failure Modes & Pitfalls

- **Proxy-metric gaming (Goodhart's law).** When "thumbs-up rate" becomes the target, teams optimize for flattery, not correctness. Any single proxy can be gamed; triangulate quality from several independent signals (judge, explicit, implicit, task-completion) and periodically re-anchor to human gold labels.
- **Alert fatigue.** Too many noisy pages train the on-call to ignore them — including the real one. Alert on sustained, windowed conditions; route non-urgent signals to tickets/dashboards; tune thresholds against historical data so a firing alert almost always means action.
- **PII in traces.** Traces capture real user prompts and outputs — a compliance liability. Scrub or redact PII at ingestion, control access, set retention limits, and be deliberate about whether you store message *content* (`gen_ai.input.messages` is optional in the OTel conventions precisely for this reason).
- **The cost of judging everything.** An LLM judge on 100% of traffic can rival the cost of serving the traffic. Sample; use a cheap judge to triage and an expensive one only on borderline/flagged cases.
- **Trusting an un-validated judge.** A judge is a model; it drifts, is biased toward verbosity, and can be gamed. If you never compare it to human labels, your "quality metric" is a fiction.
- **Averages hiding tails.** Mean latency and mean quality look fine while p99 users suffer. Always report percentiles and segment by cohort/tool/model.
- **Survivorship bias in feedback.** The users who churned after a bad experience never left a thumbs-down. Pair sparse explicit feedback with implicit-abandonment signals so silent failures are visible.
- **Instrumentation drift.** If spans are added ad hoc, half your runs lack the attributes your dashboards need. Standardize on the OTel GenAI conventions so every trace is uniformly queryable, and monitor instrumentation completeness as its own metric.
- **Broken sensors read as good news.** A guardrail that failed open, a judge endpoint returning errors, or a metrics pipeline dropping spans all *look* like "everything is fine." Monitor the monitors: alert on a metric going suspiciously quiet, not just on it going bad.
- **No baseline, no incident.** Without a frozen baseline window you cannot tell drift from normal variance, so you either alert constantly or never. Freeze a baseline per model/prompt version and re-baseline deliberately after each intentional change.

---
