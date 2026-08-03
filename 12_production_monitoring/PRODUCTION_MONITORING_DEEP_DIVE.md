# Production Monitoring — Observing, Measuring, and Improving Live Agents

> "You do not deploy an agent and finish evaluating it. You deploy an agent and *start* evaluating it — on real inputs, forever."

## Why This Matters

Every previous chapter was about evaluation *before* deployment: build a dataset, run the agent, score it, gate the release. That work ends at a single moment — the deploy — and it is measured against inputs *you* chose. Production is different in three ways that break offline eval:

1. **The inputs are not yours.** Real users ask things your dataset never imagined. The distribution shifts weekly.
2. **The world moves.** Model providers silently update weights, tools change their APIs, a downstream retrieval index goes stale. Your code did not change but your agent's behavior did.
3. **There is no ground truth.** Offline you had labels. In production you have a stream of traces and, if you are lucky, some noisy user signals. You have to *manufacture* judgment.

Production monitoring is therefore not "ops for the agent." It is **continuous evaluation**: the same measurement discipline from the rest of this book, applied to a live, unlabeled, drifting stream. Offline eval answers "is this version good enough to ship?" Monitoring answers "is it *still* good, right now, on what people are actually doing?" — and feeds what it learns back into the offline datasets so the next release is better.

This chapter covers the full loop: tracing runs, the metrics catalog, online evaluation on sampled traffic, feedback capture, drift and regression detection, alerting, and closing the loop back into your eval sets.

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

---

## What to Monitor — A Metrics Catalog

Group production metrics into five families. For each, track the aggregate *and* the tail — averages hide the failures that matter.

### 1. Quality proxies
You rarely have per-request ground truth, so you approximate quality:

- **Online judge score** — an LLM-as-judge verdict on a *sample* of traffic (see the online-eval section). Report mean and the fraction below a pass threshold.
- **Self-consistency / refusal rate** — how often the agent bails, says "I don't know," or emits an error message to the user.
- **Task-completion rate** — fraction of runs that reached a terminal success state. For an agent this means the *final goal* was met, not that the last LLM call returned. Requires you to define machine-checkable success signals (e.g., "a ticket was created," "code compiled," "the tool returned 200 and the loop exited cleanly").

### 2. Latency
Always percentiles, never just the mean — LLM latency is heavy-tailed.

- **p50 / p95 / p99 end-to-end** — wall-clock from request to final answer.
- **Time-to-first-token (TTFT)** — perceived responsiveness for streaming UIs.
- **Per-step latency** — because an agent run is a *loop*, total latency = (steps) × (per-call latency). A regression can come from more steps *or* slower calls; you need both broken out.

\[
\text{latency}_{\text{run}} \;=\; \sum_{i=1}^{N_{\text{steps}}} \big(\text{llm}_i + \text{tool}_i\big)
\]

### 3. Cost
- **Cost per request** — derived from token usage × per-model price. Track input and output tokens separately (output is usually 3–5× the price).
- **Cost per completed task** — the honest denominator. An agent that retries five times is cheap per call and expensive per outcome.
- **Token usage** — `gen_ai.usage.input_tokens` / `output_tokens` are the OpenTelemetry-standard names; sum them per run and per model.

### 4. Reliability
- **Tool-error rate** — fraction of tool calls that raise, time out, or return a malformed/unparseable payload. Break down by tool name; one flaky API poisons the whole agent.
- **Loop / step-count distribution** — runaway agents that hit the max-iteration cap are a strong failure signal.
- **Parse/format-failure rate** — how often the model emits JSON/tool-args the runtime cannot parse.

### 5. Safety & guardrails
- **Guardrail hit rate** — how often an input or output guardrail fires (PII filter, jailbreak classifier, moderation, schema validator). A *spike* is either an attack or a regression that made the model misbehave.
- **Block vs. flag ratio** — of the hits, how many were hard-blocked vs. logged for review.
- **Drift signals** — input-distribution and output-quality drift (own section below), surfaced as a monitored metric, not just an offline analysis.

> Rule of thumb: for every metric, decide up front whether you alert on it (needs a threshold and an owner) or merely dashboard it. Un-alerted metrics are documentation; alerted metrics are commitments.

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

At a glance you see *where* the 8 seconds went and *which* tool failed. That is impossible with unstructured logs.

### The GenAI semantic conventions

OpenTelemetry now ships **GenAI semantic conventions** — a standard vocabulary so traces are portable across Langfuse, Phoenix, LangSmith, Datadog, etc. instead of every vendor inventing its own field names. The three canonical span types map directly onto how agents work:

| Span type | Represents | Key attributes |
|---|---|---|
| `invoke_agent` | one agent invocation (the root) | `gen_ai.agent.name`, overall status |
| `chat` | one LLM call | `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons` |
| `execute_tool` | one tool invocation | `gen_ai.tool.name`, span `status` |

Companion metrics are standardized too: `gen_ai.client.operation.duration` (latency histogram) and `gen_ai.client.token.usage` (token histogram, filterable by `gen_ai.token.type` = input/output). Adopting these names means an off-the-shelf collector can compute your latency and cost dashboards with zero custom parsing. (Sources at the end.)

### Practical instrumentation

You have three options, roughly in order of effort:

1. **Auto-instrumentation** — libraries like OpenLLMetry (Traceloop) or the Phoenix/OpenInference SDKs monkey-patch the OpenAI/Anthropic/LangChain SDKs and emit spans for free.
2. **A managed SDK** — Langfuse/LangSmith decorators (`@observe`) wrap functions into spans.
3. **Hand-rolled** — emit OpenTelemetry spans yourself (the worked example below does a minimal version so the mechanics are visible).

Whatever you choose, **sample thoughtfully**: keep 100% of traces that errored or got a thumbs-down, and down-sample the boring successes to control storage cost.

---

## Online Evaluation on Live Traffic

Offline you scored every example against labels. Online you have no labels and can't afford to hand-review everything. The pattern is **sample → judge → aggregate**.

### Sampling
Judging is not free (an LLM judge is another model call; a human reviewer is expensive). So you evaluate a *slice*:

- **Uniform random sample** (e.g., 5% of traffic) for an unbiased quality estimate.
- **Stratified / targeted sampling** — oversample high-risk segments (new user cohort, a specific tool, long runs) so rare failures show up.
- **Signal-triggered** — always evaluate runs that erred, hit a guardrail, or got negative feedback. These are your highest-information samples.

### LLM-as-judge in production
Run the same rubric-based judge from Chapter 9, but on live outputs instead of a fixed dataset. In production the judge has extra constraints:

- **It is a cost and latency line-item.** Judge asynchronously, off the user's critical path — read from the trace log, score, write the score back onto the trace. Never make the user wait for the judge.
- **It must be cheap enough to run at your sample rate.** A common pattern: a small/fast model does a coarse pass on a large sample, and an expensive judge only re-scores the ones the cheap judge flags as borderline.
- **The judge itself drifts and can be gamed.** Calibrate it periodically against a human-labeled gold set (see closing-the-loop). A judge you never re-validate is a metric you should not trust.

Langfuse, Phoenix, and LangSmith all support attaching evaluator scores to sampled production traces and charting them over time; this is the mainstream "online eval" workflow. (Sources at the end.)

### Human review queues
LLM judges cannot ground-truth everything, especially subjective quality and safety edge cases. Route a trickle of traces — the judge's borderline cases, sampled thumbs-downs, a random audit slice — into a **human annotation queue**. Humans produce the gold labels that (a) calibrate the judge and (b) become new eval-set rows. Keep the queue small and prioritized or reviewers burn out.

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

### Output-quality drift — the *answers* get worse
Same inputs, worse outputs. This is the dangerous one because it is silent — latency and cost look fine. Causes: a provider model update, a stale retrieval index, prompt/template rot, a dependency change.

**Methods:**

- **Rolling online-judge score** — the single most direct signal. A statistically significant drop in the mean judge score over a rolling window *is* an output-quality regression. Use a control-chart or two-window comparison rather than a fixed threshold.
- **Proxy drift** — refusal rate, answer length, tool-error rate, guardrail-hit rate. A sudden jump in refusals or a collapse in answer length often precedes a measurable quality drop and is far cheaper to compute.
- **Champion/challenger & canary** — route a small % of traffic to a new model/prompt and compare judge scores and feedback head-to-head before full rollout. This turns "did the provider break us?" from a guess into an experiment.

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
| Tool failure | any tool error rate > 20% | ticket | circuit-break that tool |

**Incident response for agents** adds one step over normal SRE: because the failure may be *behavioral*, your runbook must include "pull the traces." The span tree tells you whether the regression is a slow tool, a changed model, more loop iterations, or worse reasoning — each has a different owner and fix. Keep the last-known-good prompt/model pinned so rollback is one config change.

---

## Worked Example — Instrument, Aggregate, Alert

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

## Closing the Loop

The payoff of all this instrumentation is not the dashboard — it is the **flywheel** that makes the next release better. Production is the richest source of eval data you will ever have, because it is real.

The loop:

1. **Mine traces for interesting cases.** Every thumbs-down, guardrail hit, tool error, low judge score, and human-flagged run is a candidate.
2. **Curate them into eval datasets.** Cluster the failures, dedupe, and turn representative ones into new offline test cases — ideally with a human-written expected output or a checkable success condition. This is exactly the dataset-construction discipline from Chapter 10, but sourced from reality instead of imagination.
3. **Label a gold set to calibrate the judge.** Periodically have humans score a sample the LLM-judge also scored; measure judge–human agreement. If it drifts, fix the rubric before trusting the online score again.
4. **Reproduce and fix.** The new cases become regression tests. The fix (prompt change, tool patch, model swap) is validated offline against them *before* redeploy.
5. **Canary the fix**, watch the same production metrics, and confirm the regression is gone.

Every trip around the loop transfers knowledge from production back into your offline suite, so the class of failure you saw once can never silently return. Offline eval and production monitoring are not two phases — they are one loop that never stops turning.

---

## Failure Modes & Pitfalls

- **Proxy-metric gaming (Goodhart's law).** When "thumbs-up rate" becomes the target, teams optimize for flattery, not correctness. Any single proxy can be gamed; triangulate quality from several independent signals (judge, explicit, implicit, task-completion) and periodically re-anchor to human gold labels.
- **Alert fatigue.** Too many noisy pages train the on-call to ignore them — including the real one. Alert on sustained, windowed conditions; route non-urgent signals to tickets/dashboards; tune thresholds against historical data so a firing alert almost always means action.
- **PII in traces.** Traces capture real user prompts and outputs — a compliance liability. Scrub or redact PII at ingestion, control access, set retention limits, and be deliberate about whether you store message *content* (`gen_ai.input.messages` is optional in the OTel conventions precisely for this reason).
- **The cost of judging everything.** An LLM judge on 100% of traffic can rival the cost of serving the traffic. Sample; use a cheap judge to triage and an expensive one only on borderline/flagged cases.
- **Trusting an un-validated judge.** A judge is a model; it drifts, is biased toward verbosity, and can be gamed. If you never compare it to human labels, your "quality metric" is a fiction.
- **Averages hiding tails.** Mean latency and mean quality look fine while p99 users suffer. Always report percentiles and segment by cohort/tool/model.
- **Survivorship bias in feedback.** The users who churned after a bad experience never left a thumbs-down. Pair sparse explicit feedback with implicit-abandonment signals so silent failures are visible.
- **Instrumentation drift.** If spans are added ad hoc, half your runs lack the attributes your dashboards need. Standardize on the OTel GenAI conventions so every trace is uniformly queryable.

---

## Tools Landscape

| Tool | Type | Strengths | Notes |
|---|---|---|---|
| **OpenTelemetry GenAI SemConv** | Open standard | Vendor-neutral span/metric vocabulary for LLM & agent traces | The naming layer most tools now emit/ingest |
| **OpenLLMetry (Traceloop)** | Open source | Auto-instruments popular LLM/agent SDKs into OTel spans | Low-effort instrumentation path |
| **Langfuse** | Open source / cloud | Tracing, online eval (LLM-as-judge), datasets, prompt mgmt; OTel-compatible | Self-hostable; strong closing-the-loop story |
| **Arize Phoenix** | Open source | Tracing + evals; OpenInference conventions; drift/embedding analysis heritage | Pairs with Arize's ML-observability lineage |
| **LangSmith** | Commercial (LangChain) | Tracing, online & offline eval, feedback capture, annotation queues | Tight LangChain/LangGraph integration |
| **Helicone** | Open source / cloud | Proxy-first: one-line integration for cost/latency/usage monitoring | Sits in front of the provider API |
| **Evidently** | Open source | Data/embedding drift detection methods and reports | Strong for input-drift monitoring |
| **Datadog / cloud APM** | Commercial | Now ingest OTel GenAI conventions natively; alerting & SRE tooling | Good when you already live in an APM |

(Placement reflects each tool's emphasis, not an endorsement; verify current features against the linked docs.)

---

## Interview Q&A

**Q1. Why isn't offline evaluation enough once you deploy?**
Offline eval scores the agent on inputs you chose, at one moment, against labels. Production inputs are out-of-distribution and shifting, the world (models, tools, indices) changes underneath you, and there is no ground truth. Monitoring is continuous evaluation on the real, unlabeled, drifting stream — plus it feeds new failure cases back into the offline suite.

**Q2. How do you measure quality in production with no labels?**
Layered proxies: LLM-as-judge on a sampled slice (async, off the critical path), machine-checkable task-completion signals, cheap behavioral proxies (refusal rate, answer length, tool-error rate), and user feedback. Triangulate across them and periodically calibrate the judge against a small human-labeled gold set — never trust a single un-validated proxy.

**Q3. Why are structured traces essential for agents specifically?**
An agent run is a loop of LLM calls, tool calls, and sub-agents, not a single call. A nested span tree preserves timing and causality, so you can see *where* latency/cost went and *which* step failed. Flat logs throw that structure away, making completion-rate, cost-attribution, and per-step debugging impossible. OTel GenAI conventions (`invoke_agent`/`chat`/`execute_tool`) standardize it.

**Q4. Distinguish input drift from output-quality drift and how you detect each.**
Input drift = the incoming questions change (your agent is unchanged); detect via embedding-distribution comparison (domain-classifier AUC is a robust default) or cheap proxies like prompt-length/topic-share PSI. Output-quality drift = same inputs, worse answers (silent — latency/cost look fine); detect via a rolling online-judge score compared window-to-window, plus proxy jumps in refusal rate or format failures. Fixes differ: input drift → expand coverage/retrain; output drift → find the changed model/prompt/tool.

**Q5. Compare explicit and implicit feedback and their biases.**
Explicit (thumbs, edits, reports) is direct but sparse (<1% respond) and polarized toward extremes — silence isn't approval. Implicit (regenerate, copy, continuation, downstream success) is plentiful but ambiguous — abandonment could mean "perfect" or "gave up." Use implicit for volume/trend, explicit for ground-truth spot-checks, validate each implicit proxy against explicit labels, and join both onto the trace.

**Q6. How do you design alerts for agents without causing alert fatigue?**
Alert on sustained, windowed breaches rather than instantaneous spikes (LLM metrics are heavy-tailed); compare against a baseline instead of a raw threshold; tolerate delayed async quality metrics; add cost-per-request and step-count alerts because runaway loops burn money while returning 200s; and route non-urgent signals to tickets/dashboards so pages almost always mean action. Runbooks must include "pull the traces" since failures can be behavioral.

**Q7. Judging every request with an LLM is expensive — what do you do?**
Sample. Keep 100% of high-signal traces (errors, guardrail hits, negative feedback) and down-sample boring successes. Use a two-tier judge: a cheap/fast model triages a large sample and only borderline cases go to an expensive judge. Judge asynchronously off the user's path, and pick a sample rate that gives a statistically useful estimate at acceptable cost.

**Q8. How does production monitoring close the loop back into evaluation?**
Mine traces for failures (thumbs-downs, guardrail hits, low judge scores, tool errors), curate representative ones into offline eval datasets with expected outputs/checkable conditions, label a gold set to calibrate the judge, turn the cases into regression tests, validate fixes offline, then canary in production. Each loop moves real-world knowledge into the offline suite so a seen failure can't silently recur.

---

## Further Reading

- OpenTelemetry — *Inside the LLM Call: GenAI Observability with OpenTelemetry* — https://opentelemetry.io/blog/2026/genai-observability/
- Traceloop — *GenAI Semantic Conventions (OpenLLMetry)* — https://www.traceloop.com/docs/openllmetry/contributing/semantic-conventions
- Datadog — *Agent Observability natively supports OpenTelemetry GenAI Semantic Conventions* — https://www.datadoghq.com/blog/llm-otel-semantic-convention/
- Langfuse — *What is LLM Observability & Monitoring?* — https://langfuse.com/faq/all/llm-observability
- Langfuse — *LLM-as-a-Judge* — https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge
- Langfuse — *LLM Observability & Application Tracing (Open Source)* — https://langfuse.com/docs/observability/overview
- Arize Phoenix — *Evaluation / LLM Evals* — https://arize.com/docs/phoenix/evaluation/llm-evals
- Arize Phoenix — *GitHub repository* — https://github.com/arize-ai/phoenix
- LangSmith — *Evaluation concepts* — https://docs.langchain.com/langsmith/evaluation-concepts
- LangSmith cookbook — *Collect User Feedback* — https://github.com/langchain-ai/langsmith-cookbook/blob/main/feedback-examples/streamlit/README.md
- Helicone — *Open-source LLM observability platform (GitHub)* — https://github.com/Helicone/helicone
- Evidently AI — *5 methods to detect drift in ML embeddings* — https://www.evidentlyai.com/blog/embedding-drift-detection
- Braintrust — *What is LLM monitoring? (quality, cost, latency, drift)* — https://www.braintrust.dev/articles/what-is-llm-monitoring
- AWS Prescriptive Guidance — *Detecting drift in production applications* — https://docs.aws.amazon.com/prescriptive-guidance/latest/gen-ai-lifecycle-operational-excellence/prod-monitoring-drift.html
