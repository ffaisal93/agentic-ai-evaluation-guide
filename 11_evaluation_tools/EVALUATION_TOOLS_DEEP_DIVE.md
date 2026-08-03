# Evaluation Tools & Platforms — Choosing and Building Your Eval Stack

> Rendering note: this book uses MathJax, not KaTeX. Inline math is written
> with `\( ... \)` and display math with `\[ ... \]`. Plain dollar signs are
> literal currency.

## Why this matters

You can design the world's best rubric and still ship a broken agent, because
the rubric lives in your head and nowhere in your infrastructure. The gap
between "I have an evaluation idea" and "my team runs that evaluation on every
commit, sees the results on a dashboard, and gets paged when a metric drops" is
filled entirely by **tooling**. This chapter is a map of that tooling.

The landscape is noisy. Every vendor claims to do "LLM evals" and "observability
and "agent monitoring," and the words mean subtly different things to each. If
you pick a tool by reading its landing page you will end up with three
overlapping products, a five-figure annual bill, and no clear answer to "did the
new prompt make the agent better?" The goal here is to give you a mental model
sharp enough that you can look at any tool and say, in one sentence, what job it
does and whether you need it.

A second reason this matters: **tooling choices are sticky**. The place you send
your traces, the format you store eval results in, and the API your graders call
are decisions you will live with for years. Migrating a year of production
traces from one vendor to another is a project, not an afternoon. Choosing well
early — or choosing standards-based components that keep you portable — is one of
the highest-leverage decisions in an eval program.

A third reason, specific to **agents**: the thing you are evaluating is no longer
a single prompt/response pair. An agent emits a *trajectory* — a nested tree of
model calls, tool calls, retries, sub-agents, and state mutations — and most of
the interesting failures live in that tree, not in the final answer. A "correct
final answer reached through a broken plan" is still a bug (it will not
generalize), and you can only see it if your tooling captures and lets you
inspect the trajectory. This is why, for agents, **evaluation and observability
have fused**: you cannot grade what you cannot trace, and you cannot debug a
regression you cannot replay. Half of this chapter is about that fusion and the
tools that either respect it or fight it.

---

## Core intuition: eval tooling is five jobs, not one

Strip away the branding and every evaluation-and-observability tool is some
subset of **five distinct jobs**:

1. **Harness** — the thing that runs your agent or model against a set of
   inputs. Loops over a dataset, calls the system under test, handles
   concurrency, retries, and timeouts. ("Run these 500 cases.")
2. **Graders / scorers** — the code (or LLM judge, or human) that turns a raw
   output into a score. ("Was case 37 correct? How faithful? How toxic?")
3. **Storage** — where inputs, outputs, scores, and metadata are persisted so
   you can compare run A to run B next month. ("Keep every result forever, keyed
   by dataset version and code version.")
4. **Tracing / observability** — the instrumentation that captures what happened
   *inside* one run: every LLM call, tool call, token count, latency, and
   nesting. ("Show me the full call tree for the case that failed.")
5. **Visualization / reporting** — dashboards, diff views, tables, and alerts
   that turn stored numbers into human decisions. ("Show me which cases
   regressed between the two runs, side by side.")

The single most useful fact about the tooling market is this: **most tools cover
a subset of these five jobs, not all of them.** promptfoo is mostly harness +
graders + a local report. Langfuse is mostly tracing + storage + dashboards.
Ragas is mostly graders. LangSmith and Braintrust try to do all five and charge
for it. When you evaluate a tool, do not ask "is it good?" — ask "which of the
five jobs does it do, and how well, and what do I still need to bolt on?"

A related intuition: **the two big families rarely merge cleanly.** "Eval
frameworks" grew up in the offline, batch, CI world (run a dataset, get a
number). "Observability platforms" grew up in the online, streaming, production
world (watch live traffic, alert on drift). Many products now claim both, but
almost all of them started on one side and the other side feels bolted on.
Knowing a tool's *origin* tells you where it will be strong.

One more lens, because it decides more procurement fights than any feature:
**the five jobs have very different half-lives of value.** A grader encodes your
definition of quality and is worth writing carefully and owning forever. A
dashboard is worth exactly as much as the decisions it changes this quarter. A
tracing backend is plumbing that should be boring, cheap, and swappable. When
someone proposes spending money, ask *which job* the money buys and *how long*
that job's value lasts — you will find you want to own the durable jobs (graders,
data) and rent the perishable ones (dashboards, managed storage).

---

## The capability map

Four functional categories, mapped to the five jobs above.

### Category 1 — Eval frameworks (harness + graders, offline/CI)

These run a dataset through your system and score it. They live in your test
suite and your CI pipeline. Origin: batch/offline.

- **OpenAI Evals** — a framework for evaluating LLMs and an open-source registry
  of benchmarks. YAML-and-Python, template-based (match, includes,
  model-graded). The original reference implementation; more a benchmark
  registry than a product. Open source (MIT).
  <https://github.com/openai/evals>
- **Inspect (UK AISI)** — a rigorous evaluation framework from the UK AI
  Security Institute. Structured around **datasets → solvers → scorers**, with
  first-class support for tool use, multi-turn agents, model-graded scoring, and
  **sandboxed** agent execution. Ships a companion library, `inspect_evals`,
  with 200+ community benchmarks, plus a rich log viewer. MIT-licensed. The most
  credible choice for serious capability/safety evals.
  <https://github.com/UKGovernmentBEIS/inspect_ai> · <https://inspect.aisi.org.uk/>
- **DeepEval** — an open-source, "Pytest-for-LLMs" framework by Confident AI.
  Assertion-style tests with a large metric library: **G-Eval** (LLM-judge from
  a rubric), faithfulness, answer relevancy, hallucination, task completion, and
  more. Pairs with the hosted Confident AI platform for storage/dashboards.
  <https://deepeval.com> · <https://github.com/confident-ai/deepeval>
- **Ragas** — an open-source framework specialized for **RAG** evaluation:
  faithfulness, answer relevancy, context precision, context recall, plus
  synthetic test-set generation. Not a full harness — you bring the runner; Ragas
  brings the metrics. <https://www.ragas.io> · <https://github.com/explodinggradients/ragas>
- **promptfoo** — an open-source (MIT) CLI + library for evaluating and
  **red-teaming** LLM apps. Declarative YAML config, side-by-side model
  comparison, `promptfoo eval` / `promptfoo view`, CI integration, and a
  vulnerability scanner. Local-first: "LLM evals run 100% locally."
  <https://github.com/promptfoo/promptfoo>
- **MLflow LLM/GenAI evaluation** — `mlflow.evaluate()` and the newer GenAI eval
  harness bring LLM-judge scorers, dataset management, and tracing into the
  MLflow ecosystem. Open source (Apache-2.0), self-hostable, and attractive if
  you already run MLflow for classical ML.
  <https://mlflow.org/docs/latest/genai/eval-monitor/>

### Category 2 — Tracing / observability (tracing + storage, online/production)

These capture what your agent actually did in production and let you search,
replay, and monitor it. Origin: streaming/online.

- **Langfuse** — open-source LLM observability and tracing you can **self-host**
  or use as cloud. Traces, sessions, prompt management, evals, and dashboards.
  Core is open source (MIT); some enterprise features are gated. The default
  answer when someone wants "open-source LangSmith." As of January 2026 the
  company was **acquired by ClickHouse**, which had long been Langfuse's storage
  engine; the project stays MIT and Langfuse Cloud continues standalone.
  <https://langfuse.com> · <https://langfuse.com/self-hosting>
- **Arize Phoenix** — open-source AI observability **and** evaluation, built
  natively on **OpenTelemetry + OpenInference**. Tracing, LLM-based evals,
  datasets, experiments, and a prompt playground; runs locally, in a notebook,
  in Docker/K8s, or as Arize cloud. The most standards-forward OSS option.
  <https://github.com/Arize-ai/phoenix> · <https://arize.com/phoenix/>
- **Helicone** — open-source LLM observability with a **proxy/gateway-first**
  design: route calls through Helicone and get logging, caching, and cost
  tracking with one line of code (YC W23). Self-host or hosted. Cheapest way to
  get "see every call" with near-zero code change; the proxy model is also its
  main tradeoff (a hop in your request path).
  <https://github.com/helicone/helicone>
- **OpenLLMetry (Traceloop)** — not a platform but an **open-source
  instrumentation** layer: OpenTelemetry-based SDKs that emit standard
  `gen_ai.*` spans for LLM and vector-DB calls, exportable to any OTel backend.
  Use it when you want vendor-neutral traces. <https://github.com/traceloop/openllmetry>

### Category 3 — Judge / scoring libraries (graders only)

Reusable graders you drop into any harness. Ragas and DeepEval's metric modules
belong here too. Also worth knowing:

- **Autoevals** (from Braintrust) — a standalone open-source library of common
  scorers (factuality, similarity, JSON validity, LLM-as-judge templates) usable
  outside Braintrust. <https://github.com/braintrustdata/autoevals>
- **G-Eval** — a *technique* (chain-of-thought LLM judge scored against a rubric)
  implemented in several frameworks (notably DeepEval), not a product.

The point of this category: **graders are the most portable component of your
stack.** A well-written scorer is ~30 lines of Python that calls a model with a
rubric and parses a number. Do not let a platform convince you that its
proprietary scorer is the reason to lock in — you can carry graders anywhere.

### Category 4 — All-in-one platforms + dashboards (all five jobs, hosted)

- **LangSmith** — LangChain's commercial platform: tracing/observability,
  datasets, evaluators (heuristic, LLM-judge, human annotation queues), prompt
  hub, and experiment comparison. Framework-agnostic but integrates most tightly
  with LangChain/LangGraph. Primarily **hosted SaaS**, with enterprise
  self-hosted/hybrid deployment. Proprietary. Strong end-to-end UX; the cost of
  that is lock-in and price. <https://www.langchain.com/langsmith>
- **Braintrust** — an **eval-first** commercial platform: experiments,
  scoring/autoevals, a prompt playground, dataset management, human review, and
  production logging, with CI-oriented workflows and enterprise self-host/on-prem
  options. Popular where the primary job is systematic offline eval rather than
  production monitoring. <https://www.braintrust.dev>
- **W&B Weave** — Weights & Biases' tracing + evaluation toolkit. The SDK is
  open source (Apache-2.0); tracing is a `@weave.op` decorator, and the
  `Evaluation` API runs datasets against scorers. Backend is the hosted W&B
  platform (free tier). Natural fit if you already use W&B for experiment
  tracking. <https://github.com/wandb/weave> · <https://docs.wandb.ai/weave>

### Comparison table

| Tool | Category | OSS / Hosted | Standout strength |
|---|---|---|---|
| OpenAI Evals | Eval framework | OSS (MIT) | Reference framework + benchmark registry |
| Inspect (UK AISI) | Eval framework | OSS (MIT) | Rigorous agentic/safety evals; sandboxing; 200+ evals; log viewer |
| DeepEval | Eval framework / judges | OSS + hosted (Confident AI) | Pytest-style DX; rich metric library incl. G-Eval |
| Ragas | Judge library (RAG) | OSS | Best-known RAG metrics + synthetic test-set gen |
| promptfoo | Eval framework | OSS (MIT) | Local-first YAML evals + red-teaming + model diff |
| MLflow GenAI eval | Eval framework + tracing | OSS (Apache-2.0) | Fits existing MLflow; self-hostable judges + tracing |
| Langfuse | Tracing / observability | OSS (MIT core) + hosted | Self-hostable observability + prompt mgmt |
| Arize Phoenix | Tracing + eval | OSS + hosted (Arize) | OpenTelemetry/OpenInference-native tracing + evals |
| Helicone | Tracing / observability | OSS + hosted | One-line proxy logging, caching, cost tracking |
| OpenLLMetry | Instrumentation | OSS | Vendor-neutral OTel `gen_ai.*` spans |
| LangSmith | All-in-one platform | Hosted (enterprise self-host) | End-to-end tracing + datasets + eval UX |
| Braintrust | All-in-one platform | Hosted (enterprise self-host) | Eval-first experiments + scoring + playground |
| W&B Weave | Tracing + eval | OSS SDK + hosted backend | Tight W&B integration; simple decorator tracing |

> Honesty note: this is a fast-moving market and every product ships features
> monthly. Treat the "category" column as *center of gravity*, not a fence —
> Phoenix does evals, DeepEval does some tracing, LangSmith does everything.
> Verify current specifics against each project's own docs before you commit.

---

## The 2025–2026 landscape — what actually changed

The taxonomy above is stable; the *market* under it moved fast in 2025 and into
2026. If you walk into an interview or a build-vs-buy meeting, these are the
developments you are expected to know are real, not just the product names.

### The macro shifts (why the whole map moved)

1. **Agents replaced chatbots as the thing being evaluated.** Every serious
   vendor spent 2025 retooling from "log a prompt and a completion" to "capture a
   nested agent trajectory with tool calls and sub-agents." This is why tracing
   and eval fused: a flat request/response logger is not enough to debug an agent.
2. **OpenTelemetry won the tracing-format war.** The GenAI **semantic
   conventions** matured to the point that instrumentation, not backend, became
   the portable layer. In 2025 the GenAI conventions were split out into their
   own repository, **`open-telemetry/semantic-conventions-genai`**, and gained
   dedicated **agent spans** — `create_agent`, `invoke_agent`, `invoke_workflow`,
   `plan`, and `execute_tool` — alongside the existing `chat`/`embeddings`
   operations. They remain at **Development** stability (expect churn), but even
   moving, they are the thing every backend now agrees to speak. Datadog,
   Grafana, and the OSS platforms all advertise native ingestion of `gen_ai.*`
   spans. <https://github.com/open-telemetry/semantic-conventions-genai>
3. **LLM-as-judge went from novelty to default — and then got audited.** By 2026
   "we use an LLM judge" is table stakes; the sophistication is in *validating*
   the judge against human labels, controlling for its biases, and pinning its
   version. Tools now ship judge-calibration and human-review workflows as
   first-class features, because unvalidated judges burned enough teams.
4. **Consolidation and capital arrived.** Observability startups raised real
   money and got acquired; the space is no longer a dozen indie repos. Langfuse
   raised a Series B and was then **acquired by ClickHouse (announced January 16,
   2026)** — a signal that "LLM observability is a database problem" is now the
   consensus. Expect more of the category to be absorbed into data-platform and
   APM vendors.

### The tooling map, tool by tool (eval-vs-tracing · OSS-vs-hosted · what changed)

- **LangSmith** — *center of gravity: tracing + all-in-one; hosted SaaS with
  enterprise self-host.* Rebranded around "agent engineering," deepened
  LangGraph integration, and pushed annotation queues and online evaluators
  (judges that run on live production traces, not just offline datasets). It is
  the smoothest end-to-end UX and the easiest to over-buy. Watch the pricing on
  trace volume. <https://www.langchain.com/langsmith>
- **Braintrust** — *center of gravity: offline eval/experiments; hosted with
  self-host.* Stayed eval-first and leaned into CI-native workflows, the `Eval()`
  loop, and a strong playground for prompt iteration with side-by-side scoring.
  The natural pick when the primary job is "systematically compare candidate
  prompts/models on a dataset," not "watch production." Its Autoevals library is
  usable standalone. <https://www.braintrust.dev>
- **W&B Weave** — *center of gravity: tracing + eval; OSS SDK, hosted backend.*
  Rode the W&B install base: if your ML org already lives in Weights & Biases,
  `@weave.op` tracing and the `Evaluation` API are the path of least resistance.
  The SDK is Apache-2.0; the durable data lives in the hosted platform.
  <https://docs.wandb.ai/weave>
- **Arize Phoenix** — *center of gravity: OTel-native tracing + eval; OSS with
  Arize cloud.* The standards-forward OSS choice. Built on OpenTelemetry +
  **OpenInference**, so its traces are portable by construction; ships LLM
  evaluators, datasets, and experiments. If "no lock-in" is a hard requirement
  and you still want a real UI, this is usually the answer.
  <https://arize.com/phoenix/>
- **Langfuse** — *center of gravity: tracing/observability + prompt mgmt; OSS
  (MIT) + hosted.* The default "open-source LangSmith": self-host the whole thing,
  get traces, sessions, prompt management, datasets, and evals. The v3 SDK is
  OpenTelemetry-based, so instrumentation is now standards-aligned. The ClickHouse
  acquisition (Jan 2026) reinforces its data-at-scale story while keeping the core
  MIT-licensed. <https://langfuse.com>
- **Inspect (UK AISI)** — *center of gravity: rigorous offline eval; OSS (MIT).*
  Became the credible standard for capability and safety evals. Its
  dataset→solver→scorer model, sandboxed tool execution, and the `inspect_evals`
  library (200+ benchmarks) make it the tool you reach for when a *number has to
  survive scrutiny*. Not an observability product; pair it with a tracer.
  <https://inspect.aisi.org.uk/>
- **DeepEval** — *center of gravity: offline eval/judges; OSS + Confident AI
  hosted.* The "Pytest for LLMs" experience matured with a broad metric library
  (G-Eval, faithfulness, task completion, conversational metrics) and tighter
  agent/component-level testing. Great DX for teams that want evals to feel like
  unit tests. <https://deepeval.com>
- **Ragas** — *center of gravity: RAG grader library; OSS.* Still the reference
  for RAG-specific metrics (faithfulness, context precision/recall) and synthetic
  test-set generation, and increasingly used as a metric provider *inside* other
  harnesses rather than as a standalone runner. <https://www.ragas.io>
- **promptfoo** — *center of gravity: local-first offline eval + red-team; OSS
  (MIT).* Doubled down on being the fastest path from zero to a comparison table,
  and on **security/red-teaming** — its vulnerability scanner and adversarial
  probes made it a common pick for the "is this safe to ship?" gate.
  <https://www.promptfoo.dev>
- **Helicone** — *center of gravity: proxy-based tracing/cost; OSS + hosted.*
  Still the one-line way to get logging, caching, rate-limit handling, and cost
  attribution by routing calls through a gateway. The gateway is the feature and
  the caveat: it is a hop in your request path. <https://www.helicone.ai>
- **MLflow GenAI eval** — *center of gravity: eval + tracing inside MLflow; OSS
  (Apache-2.0).* Became the sane default for shops already running MLflow for
  classical ML: `mlflow.evaluate()`, GenAI judge scorers, dataset management, and
  tracing all in one self-hostable stack, no new vendor.
  <https://mlflow.org/docs/latest/genai/eval-monitor/>
- **OpenLLMetry / OpenTelemetry GenAI** — *center of gravity: instrumentation
  standard, not a platform.* The connective tissue of the whole map. Emit
  `gen_ai.*` spans once; send them anywhere. This is the single most important
  thing to adopt early, because it makes every other choice reversible.
  <https://github.com/traceloop/openllmetry>

### What changed table (2025 → 2026)

| Area | 2024 posture | 2025–2026 posture |
|---|---|---|
| Unit of evaluation | prompt/response pair | agent trajectory (nested tool calls, sub-agents) |
| Tracing format | per-vendor proprietary schema | OpenTelemetry `gen_ai.*` + OpenInference, portable |
| OTel GenAI spec | a few `gen_ai.*` attributes in main semconv | dedicated **semantic-conventions-genai** repo with agent spans (Development) |
| LLM-as-judge | "we tried a judge" | default grader, now *validated* against human labels + version-pinned |
| Online vs offline eval | separate worlds | online evaluators run judges on live prod traces |
| Market structure | indie OSS repos | funded startups + acquisitions (ClickHouse → Langfuse, Jan 2026) |
| Red-teaming | manual, ad hoc | built-in scanners (promptfoo) as a ship gate |

The practical takeaway: **standardize on OTel now, keep your graders and data in
open formats, and treat every hosted UI as rentable.** The market will keep
consolidating; the only durable protection is portability you built in yourself.

---

## How to choose — a decision guide

Do not start from tools. Start from **which of the five jobs is your bottleneck
today**, then pick the smallest thing that unblocks it.

### By primary need

- **"I can't see what my agent is doing in production."** Your bottleneck is
  tracing. Start with Langfuse (self-host) or Phoenix (OTel-native), or Helicone
  if you want the fastest possible integration via a proxy.
- **"I can't tell if a change made the agent better."** Your bottleneck is
  offline evals. Start with promptfoo (fastest to a first result), DeepEval (if
  you like Pytest), or Inspect (if the stakes are high).
- **"My RAG answers are wrong and I don't know why."** Add Ragas metrics for
  faithfulness/context recall on top of whatever harness you have.
- **"I need to prove capability/safety claims rigorously."** Inspect, full stop.
- **"I want one place for everything and I have budget."** LangSmith or
  Braintrust — pick Braintrust if evals are the center of gravity, LangSmith if
  production tracing is.

### By team size / maturity

| Situation | Recommended posture |
|---|---|
| Solo / prototype | One OSS tool. promptfoo for evals **or** Langfuse for tracing. Don't buy anything. |
| Small team, first eval program | OSS eval framework (DeepEval/promptfoo) + OSS tracing (Langfuse/Phoenix). Keep them separate; wire together later. |
| Growing team, evals in CI | Standardize on OTel-based tracing (Phoenix/OpenLLMetry) early. Add a hosted platform (Braintrust/LangSmith) if dashboard/collaboration pain is real. |
| Enterprise / regulated | Self-hostable stack; standards-based (OTel) so you stay portable; hosted platform with on-prem option only if procurement and data-residency allow. |
| Safety / high-stakes evals | Inspect + sandboxing, with results stored in your own store. |

### Decision heuristics

- **Buy tracing, build graders.** Tracing is undifferentiated plumbing you don't
  want to maintain; graders encode *your* definition of quality and should live
  in your repo.
- **Prefer tools that read/write open formats** (OTel spans, JSON/JSONL results)
  over ones that trap data in a proprietary schema.
- **Don't buy a platform to solve a problem you haven't hit yet.** Dashboards and
  collaboration features are worth money only once multiple humans argue about
  results weekly.
- **Match the tool's origin to your problem.** Batch-origin tools (promptfoo,
  Inspect) for CI; stream-origin tools (Langfuse, Helicone) for production.
- **Count the integration surface, not the feature list.** The real cost of a
  tool is the code you write to feed it and the code you write to get data out.
  A tool with 200 features and a proprietary ingest is more expensive than a
  tool with 20 features that speaks OTel, every time.

### A scoring rubric for tool selection

When two tools look equivalent on the landing page, score them on these axes and
the tie breaks itself. Rate each 1–5.

| Axis | Question | Why it matters |
|---|---|---|
| Portability | Can I export *all* data in an open format? Does it speak OTel? | Determines your cost to leave; the single biggest long-term risk. |
| Job coverage | How many of the five jobs does it actually do well (not "checkbox")? | Fewer tools = less sprawl, but beware the all-in-one that does none deeply. |
| Self-host | Can I run it in my VPC with no data egress? | Gates regulated/enterprise use entirely. |
| Integration cost | Lines of code + concepts to instrument and to read results out. | The hidden recurring tax. |
| Trace fidelity | Does it capture nested agent trajectories, not just flat calls? | For agents, a flat logger is nearly useless. |
| Judge tooling | Judge caching, version pinning, human-label calibration? | Decides whether your eval numbers are trustworthy. |
| Cost model | Priced on traces? seats? spans? What happens at 10x volume? | Trace-volume pricing is where hosted bills explode. |

---

## Building a custom framework — when it's justified

Most teams should **not** build. The gravitational pull toward "we'll just write
our own" is strong and usually wrong: you underestimate storage, concurrency,
retries, versioning, and the dashboard, and you end up maintaining a worse
Langfuse. Build only when at least one of these is true:

- **Weird system under test.** Your agent isn't a simple request/response — it's
  a long-running multi-agent workflow, a simulator, or a hardware-in-the-loop
  system that no off-the-shelf harness models cleanly.
- **Proprietary / regulated data** that legally cannot touch a third-party
  service, and self-hosting an existing OSS tool is somehow insufficient.
- **A grading notion no library expresses** — e.g. multi-step trajectory scoring
  against a ground-truth plan, or domain metrics (clinical, legal) that need
  custom logic and audit trails.
- **You're a platform team** whose product *is* evaluation, so the harness is
  core IP.

Even then, **build the thin layer, buy/borrow the thick ones.** Reuse OTel for
tracing, an existing store (Postgres, or Phoenix/Langfuse) for storage, and an
off-the-shelf dashboard. The part worth writing yourself is the harness glue and
your domain-specific graders.

### Minimal architecture

A custom eval framework has the same five parts. A clean, minimal design:

```
             ┌───────────────┐
   dataset → │    Harness     │ → runs system-under-test, with concurrency
             │  (the runner)  │    + retries + timeouts, emits a Result per case
             └──────┬────────┘
                    │ each Result carries: input, output, trace_id, metadata
                    ▼
             ┌───────────────┐
             │    Graders     │  pure functions: (case, output) → Score(s)
             │ (composable)   │  heuristic | LLM-judge | human
             └──────┬────────┘
                    ▼
             ┌───────────────┐      ┌──────────────────────┐
             │    Storage     │◀────▶│  Tracing (OTel/OSS)  │  joined on trace_id
             │ (JSONL/Postgres)│     └──────────────────────┘
             └──────┬────────┘
                    ▼
             ┌───────────────┐
             │  Report / UI   │  summary table, run-vs-run diff, alert
             └───────────────┘
```

Design rules that keep it maintainable:

- **Graders are pure functions**, independent of the harness. This makes them
  testable and portable.
- **Everything is versioned**: dataset version, code/prompt version, model
  version. A score without those three is meaningless for comparison.
- **Results are append-only** and keyed so you can diff any two runs.
- **Trace and result share an ID** so a bad score links straight to its call
  tree.

---

## Worked example — a small, real, reusable eval runner

Below is a compact but genuinely reusable eval runner. It runs a dataset through
any callable system-under-test, applies a list of graders (heuristic or
LLM-judge), persists every result as JSONL, and prints a summary report. It is
deliberately dependency-light so you can read the whole thing, and it mirrors the
API shape of tools like DeepEval/promptfoo (dataset + graders + report) so
migrating later is trivial.

```python
"""
mini_eval.py — a minimal, reusable eval runner.

Five jobs, visibly separated:
  Harness   -> EvalRunner.run
  Graders   -> Grader protocol + example graders
  Storage   -> JSONL append in EvalRunner.run
  Tracing   -> trace_id per case (join key to your OTel backend)
  Reporting -> summarize()
"""
from __future__ import annotations

import json
import time
import uuid
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Protocol


# ---------- data model ----------

@dataclass
class Case:
    """One evaluation input, plus optional ground truth + metadata."""
    id: str
    input: Any
    expected: Any = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Score:
    """A single grader's verdict for one case."""
    name: str
    value: float          # normalized to [0, 1]
    passed: bool
    detail: str = ""


@dataclass
class Result:
    case_id: str
    output: Any
    scores: list[Score]
    trace_id: str
    latency_s: float
    error: str | None = None


# ---------- graders ----------

class Grader(Protocol):
    name: str
    def __call__(self, case: Case, output: Any) -> Score: ...


class ExactMatch:
    """Heuristic grader: output must equal expected (case-insensitive)."""
    name = "exact_match"

    def __call__(self, case: Case, output: Any) -> Score:
        ok = str(output).strip().lower() == str(case.expected).strip().lower()
        return Score(self.name, 1.0 if ok else 0.0, ok,
                     detail="" if ok else f"expected={case.expected!r}")


class Contains:
    """Heuristic grader: output must contain a required substring."""
    name = "contains"

    def __init__(self, needle_key: str = "needle"):
        self.needle_key = needle_key

    def __call__(self, case: Case, output: Any) -> Score:
        needle = case.metadata.get(self.needle_key, case.expected)
        ok = str(needle).lower() in str(output).lower()
        return Score(self.name, 1.0 if ok else 0.0, ok,
                     detail="" if ok else f"missing {needle!r}")


class LLMJudge:
    """
    LLM-as-judge grader. `judge_fn(prompt) -> str` is any function that calls a
    model and returns text; injecting it keeps the grader vendor-neutral and
    unit-testable (pass a fake in tests). We ask for a strict JSON verdict.
    """
    name = "llm_judge"

    def __init__(self, judge_fn: Callable[[str], str], rubric: str,
                 threshold: float = 0.7):
        self.judge_fn = judge_fn
        self.rubric = rubric
        self.threshold = threshold

    def __call__(self, case: Case, output: Any) -> Score:
        prompt = (
            "You are a strict evaluator. Score the RESPONSE against the RUBRIC "
            'on a 0.0-1.0 scale. Reply ONLY as JSON: {"score": <float>, '
            '"reason": "<short>"}.\n\n'
            f"RUBRIC:\n{self.rubric}\n\nINPUT:\n{case.input}\n\n"
            f"RESPONSE:\n{output}\n"
        )
        raw = self.judge_fn(prompt)
        try:
            verdict = json.loads(raw)
            value = float(verdict["score"])
            reason = str(verdict.get("reason", ""))
        except (ValueError, KeyError, TypeError):
            # Fail closed on unparseable judge output — never silently pass.
            return Score(self.name, 0.0, False, detail=f"unparseable: {raw[:80]!r}")
        value = max(0.0, min(1.0, value))
        return Score(self.name, value, value >= self.threshold, detail=reason)


# ---------- harness + storage ----------

class EvalRunner:
    def __init__(self, system_under_test: Callable[[Any], Any],
                 graders: list[Grader], out_dir: str = "eval_runs",
                 max_workers: int = 8):
        self.sut = system_under_test
        self.graders = graders
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers

    def _run_one(self, case: Case) -> Result:
        trace_id = uuid.uuid4().hex  # join key to your tracing backend
        t0 = time.perf_counter()
        try:
            output = self.sut(case.input)
            scores = [g(case, output) for g in self.graders]
            err = None
        except Exception as exc:  # a crash is a failing case, not a lost case
            output, scores, err = None, [], f"{type(exc).__name__}: {exc}"
        return Result(case.id, output, scores, trace_id,
                      round(time.perf_counter() - t0, 4), err)

    def run(self, dataset: list[Case], run_id: str | None = None) -> list[Result]:
        run_id = run_id or f"run-{int(time.time())}"
        path = self.out_dir / f"{run_id}.jsonl"
        results: list[Result] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool, \
                path.open("w") as fh:
            futs = {pool.submit(self._run_one, c): c for c in dataset}
            for fut in as_completed(futs):
                r = fut.result()
                results.append(r)
                fh.write(json.dumps(asdict(r)) + "\n")  # append-only storage
        return results


# ---------- reporting ----------

def summarize(results: list[Result]) -> dict:
    """Aggregate per-grader pass rate + mean score, and print a table."""
    by_grader: dict[str, list[Score]] = {}
    errors = sum(1 for r in results if r.error)
    for r in results:
        for s in r.scores:
            by_grader.setdefault(s.name, []).append(s)

    rows = []
    for name, scores in sorted(by_grader.items()):
        pass_rate = statistics.mean(1.0 if s.passed else 0.0 for s in scores)
        mean_val = statistics.mean(s.value for s in scores)
        rows.append((name, len(scores), pass_rate, mean_val))

    lat = [r.latency_s for r in results]
    print(f"\n=== Eval summary: {len(results)} cases, {errors} errors ===")
    print(f"{'grader':<16}{'n':>5}{'pass_rate':>12}{'mean_score':>12}")
    print("-" * 45)
    for name, n, pr, mv in rows:
        print(f"{name:<16}{n:>5}{pr:>12.1%}{mv:>12.3f}")
    if lat:
        print(f"\nlatency  p50={statistics.median(lat):.3f}s  "
              f"max={max(lat):.3f}s")

    return {
        "n_cases": len(results),
        "n_errors": errors,
        "graders": {name: {"n": n, "pass_rate": pr, "mean_score": mv}
                    for name, n, pr, mv in rows},
    }


# ---------- usage ----------

if __name__ == "__main__":
    # System under test: any callable. Here, a toy "agent".
    def my_agent(question: str) -> str:
        table = {"capital of france": "Paris", "2+2": "4"}
        return table.get(question.lower().strip(), "I don't know")

    # A fake judge so the example runs offline; swap for a real model call.
    def fake_judge(prompt: str) -> str:
        return '{"score": 0.9, "reason": "looks correct"}'

    dataset = [
        Case(id="q1", input="Capital of France", expected="Paris"),
        Case(id="q2", input="2+2", expected="4"),
        Case(id="q3", input="Capital of Mars", expected="Unknown"),
    ]

    runner = EvalRunner(
        system_under_test=my_agent,
        graders=[
            ExactMatch(),
            LLMJudge(fake_judge, rubric="Response must correctly answer the question."),
        ],
    )
    results = runner.run(dataset, run_id="demo")
    report = summarize(results)
    print("\nmachine-readable:", json.dumps(report, indent=2))
```

What to notice, because these are the design decisions that separate a real
runner from a toy:

- **The judge model is injected**, not hard-coded. That single choice makes the
  grader testable (pass a fake), vendor-neutral, and safe to run offline.
- **A crashing case is a failing result, not a lost one.** Silently dropping
  errors is the most common way eval numbers lie.
- **The judge fails closed.** Unparseable judge output scores 0, never a silent
  pass — LLM judges *will* occasionally return prose instead of JSON.
- **Every result carries a `trace_id`**, the join key to your tracing backend.
  This is the whole trick behind "click a bad score, see the call tree."
- **Storage is append-only JSONL** — trivially diffable, greppable, and
  loadable into pandas or any dashboard. No lock-in.

### Wiring to an OSS tool's API pattern

To send the same runs to an OSS platform instead of local JSONL, you swap the
storage step. The shape most tools expect is nearly identical — a dataset, a
task function, and scorers — which is exactly why keeping graders separate pays
off. For example, DeepEval's pattern is `LLMTestCase` + `metric.measure(...)` +
`assert_test`; promptfoo's is a YAML `providers`/`tests`/`assert` file; Weave's
is `weave.Evaluation(dataset=..., scorers=[...]).evaluate(model)`. In each,
your `ExactMatch`/`LLMJudge` graders map onto the tool's "metric"/"scorer"
concept with a thin adapter — you do not rewrite your definition of quality.

---

## Build it in practice — wiring the runner to real OSS tools

The section above is intentionally self-contained. Now let us make it *real*:
take the exact `Result`/`Score` objects the runner already produces and push
them into an actual OSS backend, so a bad score becomes a clickable trace. We
show two genuinely different API shapes — **Langfuse** (tracing/observability,
you push traces + scores to it) and **Inspect** (an eval framework, you declare
a task and it runs the loop for you) — because seeing both teaches you what
"integration cost" really means.

### Adapter 1 — log every run and score to Langfuse

Langfuse's model is: create a **trace** per unit of work, optionally nest
**spans/generations** inside it, and attach **scores** (numeric or categorical)
to the trace. Our `EvalRunner` already produces exactly the right objects; we
just add a reporter. The snippet below uses the low-level Langfuse Python SDK
(v2 style, which is stable and explicit); a note after it shows the v3
OpenTelemetry-decorator equivalent.

```python
"""
langfuse_reporter.py — push mini_eval Results into Langfuse as traces + scores.

Run against Langfuse Cloud or a self-hosted instance. Configure via env:
  LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
Install:  pip install langfuse
"""
from __future__ import annotations

import statistics
from langfuse import Langfuse           # pip install langfuse
from mini_eval import Case, Result, EvalRunner, ExactMatch, LLMJudge


def report_to_langfuse(results: list[Result],
                       dataset: list[Case],
                       run_name: str) -> dict:
    """
    Create one Langfuse trace per case and attach every grader Score to it.
    The trace's `id` is our own trace_id, so a score in Langfuse links straight
    back to the JSONL row and (if you also instrument the agent) its call tree.
    """
    lf = Langfuse()  # reads keys/host from environment
    by_id = {c.id: c for c in dataset}

    for r in results:
        case = by_id[r.case_id]
        # One trace == one evaluated case. Reuse OUR trace_id as the join key.
        trace = lf.trace(
            id=r.trace_id,
            name=f"{run_name}:{r.case_id}",
            input=case.input,
            output=r.output,
            metadata={"run": run_name, "latency_s": r.latency_s,
                      "error": r.error, **case.metadata},
            tags=[run_name],
        )
        # Attach each grader's verdict as a Langfuse score on the trace.
        for s in r.scores:
            lf.score(
                trace_id=trace.id,
                name=s.name,
                value=s.value,          # numeric score in [0, 1]
                comment=s.detail or None,
            )
        # Record a hard failure as a distinct signal, not a silent gap.
        if r.error:
            lf.score(trace_id=trace.id, name="ran_ok", value=0.0,
                     comment=r.error)

    lf.flush()  # IMPORTANT: SDK batches; flush before the process exits.

    # Emit the same machine-readable summary the local runner does.
    by_grader: dict[str, list[float]] = {}
    for r in results:
        for s in r.scores:
            by_grader.setdefault(s.name, []).append(s.value)
    summary = {
        "run": run_name,
        "n_cases": len(results),
        "n_errors": sum(1 for r in results if r.error),
        "graders": {name: {"n": len(v), "mean_score": statistics.mean(v)}
                    for name, v in sorted(by_grader.items())},
    }
    print(f"[langfuse] logged {len(results)} traces for run {run_name!r}")
    return summary


if __name__ == "__main__":
    def my_agent(q: str) -> str:
        return {"capital of france": "Paris", "2+2": "4"}.get(q.lower().strip(),
                                                              "I don't know")

    def fake_judge(prompt: str) -> str:
        return '{"score": 0.9, "reason": "looks correct"}'

    dataset = [
        Case(id="q1", input="Capital of France", expected="Paris"),
        Case(id="q2", input="2+2", expected="4"),
    ]
    runner = EvalRunner(my_agent, graders=[
        ExactMatch(),
        LLMJudge(fake_judge, rubric="Correctly answers the question."),
    ])
    results = runner.run(dataset, run_id="langfuse-demo")
    print(report_to_langfuse(results, dataset, run_name="langfuse-demo"))
```

Three things this makes concrete:

- **The join key is yours.** Because we pass `id=r.trace_id` into `lf.trace(...)`,
  the very same ID keys your JSONL row, your Langfuse trace, and — if you also
  instrument `my_agent` with `@observe` or OTel spans — the nested call tree.
  One click from "score 0.0" to "here's the exact tool call that failed."
- **`lf.flush()` is not optional.** The SDK batches network writes for
  throughput; a script that exits without flushing silently drops its last
  batch. This is the single most common "why are my traces missing?" bug.
- **The graders never changed.** `ExactMatch` and `LLMJudge` are byte-for-byte
  the ones from `mini_eval.py`. That is the payoff of keeping graders as pure
  functions: the backend is a swappable reporter, not a rewrite.

> **v3 SDK note.** Langfuse's newer SDK is OpenTelemetry-based: instead of
> `lf.trace(...)` you wrap work in `with langfuse.start_as_current_span(...)` or
> decorate the agent with `@observe`, and attach scores with
> `langfuse.score_current_trace(name=..., value=...)`. The *mental model* — trace
> per unit of work, scores attached to it — is identical; only the surface API
> changed. Pin the SDK major version and read the current docs before wiring
> production. <https://langfuse.com/docs>

### Adapter 2 — the same eval as an Inspect task

Inspect inverts control: you do not write the loop, you *declare* a `Task`
(dataset + solver + scorer) and Inspect runs it, handling concurrency, retries,
logging, and a rich viewer for free. This is the "buy the harness" path, and for
high-stakes evals it is usually the right one.

```python
"""
capital_task.py — the same quiz as an Inspect eval.
Install:  pip install inspect-ai
Run:      inspect eval capital_task.py --model openai/gpt-4o
View:     inspect view
"""
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import match, model_graded_qa
from inspect_ai.solver import generate, system_message


@task
def capital_quiz() -> Task:
    return Task(
        dataset=[
            Sample(input="What is the capital of France?", target="Paris"),
            Sample(input="What is 2 + 2?", target="4"),
            Sample(input="What is the capital of Mars?", target="unknown"),
        ],
        solver=[
            system_message("Answer in as few words as possible."),
            generate(),
        ],
        # Two scorers: a cheap exact-ish match AND a model-graded judge.
        scorer=[
            match(location="any"),   # heuristic: target string appears in output
            model_graded_qa(),       # LLM judge: is the answer correct vs target?
        ],
    )
```

What the two adapters teach, side by side:

- **Langfuse = push model.** You own the loop and the graders; the tool stores
  and visualizes. Maximum control, minimum magic, and your existing runner drops
  in with a ~40-line reporter.
- **Inspect = declarative model.** You give it a dataset, a solver, and scorers;
  it owns concurrency, sandboxing, logging, and the viewer. Far less code, at the
  cost of expressing your eval in *its* vocabulary. The moment your grader is
  "trajectory matches a ground-truth plan," you either find an Inspect scorer
  that fits or write a custom one in its scorer API.
- **Both emit a report.** Langfuse via the returned summary dict + its dashboard;
  Inspect via `inspect view` and its `.eval` log files. Neither leaves you at a
  bare number.

The lesson is the recurring one: **own the graders, rent the harness or the
backend.** Whichever adapter you pick, the definition of quality stayed in your
code and stayed portable.

---

## OpenTelemetry & standardization

The most important recent development in this space is that **tracing is
becoming a standard**, not a per-vendor format. OpenTelemetry — the
industry-standard observability framework — now has **GenAI semantic
conventions**: an agreed vocabulary for how to record LLM and agent operations
as spans.

Concretely, the conventions define a span hierarchy — an `invoke_agent` span at
the top, `chat` spans for individual model calls, and `execute_tool` spans for
tool invocations — with standardized attributes such as:

- `gen_ai.request.model` — the model called (e.g. `gpt-4o`)
- `gen_ai.usage.input_tokens` / `gen_ai.usage.output_tokens` — token counts
- `gen_ai.response.finish_reasons` — why generation stopped (`stop`, `tool_calls`)
- `gen_ai.input.messages` / `gen_ai.output.messages` / `gen_ai.system_instructions`
  — the actual content, captured only when you opt in

As of 2025–2026, the GenAI conventions were **split out of the main
semantic-conventions repo into their own repository**,
`open-telemetry/semantic-conventions-genai`, and grew a dedicated set of **agent
spans** aimed squarely at the trajectory problem:

- `create_agent` — instantiating an agent (name, id, version, model)
- `invoke_agent` — a full agent invocation (the top of the trajectory tree)
- `invoke_workflow` — orchestrated multi-step workflows
- `plan` — an explicit planning/reasoning phase
- `execute_tool` — a single tool call, nested under the agent

with shared attributes like `gen_ai.operation.name`, `gen_ai.provider.name`,
and `error.type`. This is exactly the nested shape an agent produces, which is
why it matters more for agents than for chatbots.

Why you should care: if your agent emits **standard `gen_ai.*` spans**, you can
point them at Phoenix today, Langfuse tomorrow, and Datadog next year without
re-instrumenting your code. That is the single strongest antidote to lock-in in
the whole chapter. Tools like **OpenLLMetry** (Traceloop) exist precisely to
emit these standard spans from your app, and OTel-native platforms like
**Phoenix** consume them directly. By 2026, mainstream APM and data vendors
(Datadog among them) advertise native ingestion of the OTel GenAI conventions,
so "standard spans" is not an OSS-only story — it is how you keep the enterprise
backends portable too.

The honest caveat: the GenAI conventions are **still at Development stability** —
actively developed, already useful, but not frozen, and some attribute names have
already been renamed/deprecated between versions. Adopt them, but pin versions
and expect churn. Even a moving standard is more portable than a proprietary
schema. See the OpenTelemetry GenAI SIG for current status.
<https://opentelemetry.io/blog/2026/genai-observability/> ·
<https://github.com/open-telemetry/semantic-conventions-genai>

### A tiny OTel instrumentation sketch

You do not need OpenLLMetry to emit standard spans — you can set the attributes
yourself, which is worth doing once so you understand what the auto-instrumentors
are doing under the hood.

```python
from opentelemetry import trace
tracer = trace.get_tracer("my.agent")

def call_model(messages, model="gpt-4o"):
    with tracer.start_as_current_span("chat") as span:
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.request.model", model)
        resp = client.chat.completions.create(model=model, messages=messages)
        u = resp.usage
        span.set_attribute("gen_ai.usage.input_tokens", u.prompt_tokens)
        span.set_attribute("gen_ai.usage.output_tokens", u.completion_tokens)
        span.set_attribute("gen_ai.response.finish_reasons",
                           [resp.choices[0].finish_reason])
        return resp
```

Any OTel-compatible backend — Phoenix, Langfuse v3, Datadog — will render this
span correctly and join it into the agent's trajectory, because the attribute
names are the agreed vocabulary, not a vendor's.

---

## Production case studies & war stories

Patterns are easier to trust with concrete stacks and scars attached. The
following are composite but realistic — the kind of decisions and incidents that
recur across teams building agents in 2025–2026.

### Case study 1 — Solo builder / prototype (1 engineer)

**Context.** One engineer shipping a RAG assistant side project, no budget, needs
to know "did my last prompt change help?"

**Stack.** promptfoo for offline evals (a single YAML, `promptfoo eval`,
`promptfoo view`), local JSONL for results, no tracing tool at all — just print
statements and the promptfoo web view.

**Decision.** Build-vs-buy is moot at this size; the answer is "one OSS tool, zero
dollars." The trap here is the opposite: reaching for a hosted platform's free
tier and immediately coupling to its schema. Staying local kept everything
portable.

**Lesson.** At n=1, your bottleneck is *iteration speed*, not collaboration.
Anything with a login screen is overhead.

### Case study 2 — Seed startup shipping a customer-facing agent (5 engineers)

**Context.** A support agent with tool use (search, ticket API). Real users, real
incidents, a founding team that argues about quality weekly.

**Stack.** Self-hosted **Langfuse** for tracing (instrumented via OTel so spans
are portable), **promptfoo** in CI as the ship gate, **Ragas** metrics on the
retrieval step, graders written in-repo with an injected judge model. Results in
Postgres; a notebook for run-vs-run diffs.

**Build-vs-buy.** They deliberately *did not* buy an all-in-one. The reasoning:
at five people the collaboration features of LangSmith/Braintrust weren't worth
the trace-volume bill or the lock-in, and self-hosted Langfuse gave them 90% of
the tracing value for the cost of a small VM.

**Lesson.** The right first stack is "one OSS tracer + one OSS eval framework +
your own graders." Keep them decoupled; you can add a hosted UI later if pain is
real.

### Case study 3 — Scale-up with an eval team (40+ engineers, dedicated eval owners)

**Context.** Multiple agent products, a platform team, regulated-adjacent data,
weekly release train, and executives who ask for a "quality number."

**Stack.** OTel/OpenInference instrumentation everywhere (portability mandated by
architecture review), **Phoenix** self-hosted for tracing + online evals, a
**hosted platform (Braintrust)** bought specifically for the experiment/dataset
collaboration UX that a 40-person org actually fights over, **Inspect** for the
high-stakes capability/safety evals whose numbers go in front of leadership, and
a shared in-repo grader library owned by the platform team.

**Build-vs-buy.** Here buying *did* pay off — but narrowly, for the one job
(collaborative experiments) where the org had genuine multi-human pain. Tracing
stayed OSS and standards-based on purpose, so the bought platform is replaceable.

**Lesson.** Buy the perishable job (collaboration UI) once the pain is proven;
keep the durable jobs (instrumentation, graders, data) OSS and portable so the
purchase never becomes a hostage situation.

### Case study 4 — Enterprise / regulated (bank, health, gov)

**Context.** Data legally cannot leave the VPC; auditors want reproducible
evidence that the agent was evaluated before each release.

**Stack.** Fully self-hosted: **Langfuse or Phoenix** in-VPC for tracing,
**Inspect** with sandboxed execution for the audited capability evals, results
in the org's own warehouse, OTel spans so nothing is trapped in a vendor. Hosted
SaaS considered only where an on-prem/BYOC option and a signed DPA exist.

**Lesson.** In regulated settings, "self-hostable" and "open data format" are not
nice-to-haves; they are the gate. A tool that can only send data to someone
else's cloud is disqualified before you evaluate its features.

### Stacks-by-team-size summary

| Team size | Tracing | Offline eval | Platform bought? | Graders |
|---|---|---|---|---|
| Solo | none / prints | promptfoo | No | in-repo |
| Seed (≈5) | self-host Langfuse (OTel) | promptfoo + Ragas | No | in-repo, injected judge |
| Scale-up (40+) | Phoenix (OTel) | Inspect (high-stakes) | Yes — Braintrust for collab | shared in-repo library |
| Enterprise/regulated | self-host in-VPC (OTel) | Inspect + sandbox | Only with on-prem/BYOC + DPA | in-repo, audited |

### War story A — the tracing-overhead incident

**What happened.** A team turned on full prompt/response content capture on every
span, in production, at a few hundred QPS, sampling 100%. Within a day: p95
latency up double digits of milliseconds per request from serialization + egress,
a surprise storage bill, and a trace backend struggling to keep up. The content
capture — the *most useful* part in dev — was the killer in prod.

**Root cause.** Treating dev-grade observability settings as production settings.
Capturing every token of every message, unsampled, is a dev luxury.

**Fix and lesson.** Sample in production (100% in dev, a small fraction in prod),
make content capture **opt-in per span** (metadata always, payloads only when a
flag is set or a case is flagged interesting), and set retention. Observability
is not free; budget it like any other production dependency and *measure its
overhead* before it measures you.

### War story B — the lock-in trap

**What happened.** A team went all-in on a single hosted platform's proprietary
tracing + eval schema. Eighteen months later, price and data-residency pressure
made them want to leave — and discovered that "leaving" meant re-instrumenting
every service and abandoning a year and a half of trace history that only existed
in the vendor's schema. The migration was quoted in engineer-quarters.

**Root cause.** No portability layer. Instrumentation spoke the vendor's dialect,
not OTel, and results lived only in the vendor's store.

**Fix and lesson.** Had they emitted **OTel `gen_ai.*` spans** and mirrored
results to their own store from day one, switching backends would have been a
config change plus a backfill, not a re-write. Ask every vendor "how do I export
*all* my data, in what format?" *before* you sign — and build the export even if
you never plan to leave.

### War story C — the judge that drifted

**What happened.** A team's headline quality metric quietly jumped one week with
no code change. Celebration turned to suspicion: the LLM-judge model had been
transparently updated by the provider, and the *new* judge scored more leniently.
Weeks of "improvement" were an artifact of the grader moving, not the agent.

**Root cause.** An unpinned, unvalidated judge — a non-stationary measuring stick.

**Fix and lesson.** Pin the judge model version, cache judge verdicts on
`(rubric, input, output)` so identical cases are stable, and keep a small
human-labeled **gold set** you re-score on every judge change to detect drift.
Your grader is an instrument; calibrate it or your numbers are fiction.

---

## Failure modes & pitfalls

**Tool lock-in.** The trap: you send a year of production traces and eval
history into a proprietary schema, then discover migration means re-instrumenting
everything and abandoning your history. Antidote: standards-based tracing (OTel
`gen_ai.*`) and open result formats (JSONL/Parquet). Ask every vendor "how do I
get all my data out?" *before* you sign.

**Tracing overhead.** Instrumenting every LLM and tool call is not free —
capturing full prompt/response content on high-QPS traffic adds latency, cost,
and a lot of storage. Antidotes: sample (trace 100% in dev, a fraction in prod),
make content capture opt-in per span, and set retention. Proxy-based tools
(Helicone) add a network hop to the request path; decorator/SDK tools add CPU and
egress. Measure it.

**Judge cost and drift.** LLM-as-judge is the default grader now, and it is
expensive at scale (you are running a second model on every case) and
*non-stationary* (the judge model changes under you when the provider updates it).
Antidotes: cache judge calls on identical (rubric, input, output) triples; pin
the judge model version; periodically validate the judge against a human-labeled
gold set; use a cheaper heuristic grader as a pre-filter so the judge only runs
where it must.

**Dashboard theater.** The most insidious failure: a beautiful dashboard full of
green numbers that nobody has connected to a real quality question. Vanity
metrics (average score of 0.87 — of what? against what baseline?) create false
confidence. Antidotes: every dashboard tile must answer a decision ("ship or
not?", "did case X regress?"); always show a baseline and a diff, never a lone
number; and periodically ask "if this metric moved, would we actually do
anything?" If not, delete it.

**Overlapping tools / stack sprawl.** Teams routinely end up paying for
LangSmith *and* Braintrust *and* Langfuse because each was adopted for one
feature. Antidote: maintain an explicit map of which of the five jobs each tool
does, and retire duplicates.

**Grading the wrong thing well.** No tool saves you from a bad rubric. A polished
harness that scores fluency when you needed factuality just makes a wrong answer
arrive faster and prettier. Tooling is downstream of a correct eval design.

**Flushing and sampling bugs.** Two silent data-loss classes worth their own
line: SDKs that batch writes and drop the last batch if you never call `flush()`,
and sampling configs that quietly discard the exact rare trace you needed. If
traces are "sometimes missing," suspect these before you suspect the backend.

---

## Starter stack recommendation

If you want a concrete, opinionated default that is cheap, portable, and scales:

- **Tracing:** self-hosted **Langfuse** *or* **Arize Phoenix** (pick Phoenix if
  you want OTel-native from day one). Instrument via **OpenLLMetry** so your
  spans are standard `gen_ai.*`.
- **Offline evals / CI:** **promptfoo** for the first week (fastest to a result),
  graduating to **DeepEval** or **Inspect** as your rubrics get serious.
- **RAG-specific metrics:** add **Ragas** where you have retrieval.
- **Graders:** write your own, in your repo, injected model — like the worked
  example above. This is your quality IP; own it.
- **Storage/reporting to start:** append-only JSONL + a notebook, exactly as
  shown. Add the tracing tool's dashboard once multiple humans need to look
  together.
- **Buy a platform (LangSmith / Braintrust / Weave)** only when
  collaboration/dashboard pain is real and recurring — not before.

The through-line: **buy the plumbing (tracing), keep it standards-based (OTel),
and own the graders.** That combination gives you most of the value of the
expensive platforms while keeping you free to leave any of them.

---

## Interview mastery

This section is engineered for the interview room and the design review. It has
five parts: a 60-second framework answer, a system-design prompt with a sketch,
tradeoff tables you can reproduce on a whiteboard, red/green flags, and a bank of
Q&A.

### Explain how you'd choose an eval/observability stack in 60 seconds

> "I don't start from tools, I start from which of five jobs is my bottleneck:
> harness, graders, storage, tracing, or reporting. For most agent teams the
> answer is 'I can't see what the agent did and I can't tell if a change helped,'
> so I stand up one OSS tracer — Langfuse or Phoenix — instrumented with
> OpenTelemetry `gen_ai.*` spans so I'm never locked to a backend, and one OSS
> eval framework — promptfoo to start, Inspect when the numbers have to survive
> scrutiny. I write the graders myself, in the repo, with the judge model
> injected, because graders *are* my definition of quality and the one thing I
> refuse to outsource. Storage is append-only JSONL until multiple humans are
> arguing about results weekly; only then do I buy a hosted platform, and only
> for that collaboration job. The whole philosophy is: buy the perishable
> plumbing, keep it standards-based, own the durable parts — graders and data."

That answer hits: the five-jobs model, OTel portability, buy-vs-build split,
maturity-gating the purchase, and a stated philosophy. It is complete in a
minute.

### System-design prompt: "Design the eval + observability platform for an agent org"

**Prompt.** A 100-engineer org ships several agent products. Design their
evaluation + observability platform: offline evals in CI, production tracing,
online quality monitoring, and a way for PMs and engineers to collaborate on
quality. Cover data flow, portability, cost control, and governance.

**A strong answer sketches this:**

```
  Dev / CI                              Production
  ────────                              ──────────
  code push                             live agent traffic
      │                                     │
      ▼                                     ▼  OTel gen_ai.* spans (sampled)
  ┌──────────────┐                    ┌───────────────────┐
  │ Eval harness │  dataset+graders   │ OTel Collector    │  central pipeline:
  │ (Inspect /   │───────────────┐    │ (sample, redact,  │  routing, PII redaction,
  │  promptfoo)  │               │    │  fan-out)         │  sampling policy
  └──────┬───────┘               │    └─────────┬─────────┘
         │ scores + trace_ids    │              │
         ▼                       ▼              ▼
  ┌──────────────────────────────────────────────────────┐
  │  Trace + result store (Phoenix/Langfuse self-host)    │  ← single source of truth,
  │  joined on trace_id; also mirrored to the warehouse   │    open format, in-VPC
  └───────┬───────────────────────────────┬──────────────┘
          │ online evaluators (judges)     │ offline experiment history
          ▼                                ▼
  ┌───────────────┐                 ┌────────────────────┐
  │ Alerting      │  metric drop →  │ Collaboration UI   │  ← the ONE bought SaaS:
  │ (drift, cost) │  page on-call   │ (Braintrust/       │    datasets, experiment
  └───────────────┘                 │  LangSmith)        │    diffs, human review
                                    └────────────────────┘
  Governance layer (cross-cutting): grader library in a shared repo (owned,
  versioned, code-reviewed) · judge model registry (pinned versions + gold-set
  calibration) · dataset versioning · retention & PII policy in the Collector.
```

**Talking points that score:**

- **One instrumentation standard (OTel `gen_ai.*`) everywhere**, so every backend
  is swappable — the platform survives a vendor change.
- **A central OTel Collector** as the choke point for sampling, PII redaction, and
  routing: cost and governance controls live in one place, not scattered per app.
- **trace_id as the universal join key** linking a CI eval score, a production
  trace, and an online-judge verdict to the same unit of work.
- **Buy exactly one job** (collaboration UI) where a 100-person org has real
  multi-human pain; keep tracing, graders, and data OSS/open so the purchase is
  never load-bearing.
- **Governance is a first-class layer**: a shared, versioned grader library; a
  judge registry with pinned versions and gold-set calibration; dataset
  versioning; retention/PII policy enforced at the Collector.
- **Online + offline share the store**, so a production regression can be turned
  into a CI regression test by promoting the failing trace into a dataset.

### Tradeoff tables

**OSS vs hosted:**

| | OSS (self-host) | Hosted SaaS |
|---|---|---|
| Cost shape | infra + your ops time | subscription, often per-trace/seat |
| Data residency | in your VPC | vendor cloud (unless BYOC/on-prem) |
| Time to value | slower (you run it) | fast (sign up) |
| Lock-in | low (you hold the data) | higher (proprietary schema risk) |
| Best when | regulated, cost-sensitive, portability-first | small team, want UX now, budget exists |

**Build vs buy:**

| | Build | Buy |
|---|---|---|
| What you build | thin harness glue + domain graders | integration + configuration |
| Cost | eng time, ongoing maintenance | license + integration + lock-in risk |
| Justified when | weird SUT, un-shippable data, novel grading, eval-is-the-product | common case; you want the five jobs solved |
| Danger | reinventing a worse Langfuse | over-buying; sprawl; lock-in |
| Rule of thumb | build the thin layer, buy/borrow the thick ones | buy the perishable job once pain is proven |

**Eval (offline) vs tracing (online):**

| | Eval framework | Observability platform |
|---|---|---|
| Origin | batch / offline / CI | streaming / online / prod |
| Question answered | "did this change make it better?" | "what did the agent do, and is it healthy?" |
| Data | curated dataset + ground truth | live traffic, no labels |
| Examples | promptfoo, Inspect, DeepEval | Langfuse, Phoenix, Helicone |
| Failure if missing | you ship regressions blind | you can't debug or monitor prod |
| For agents | both are mandatory, joined on trace_id | |

### Red flags vs green flags

**Red flags (in a tool, a vendor, or a team's answer):**

- "How do I export everything?" has no clean answer, or the export is a lossy CSV.
- Instrumentation speaks only the vendor's schema, not OTel.
- The team's quality metric is a single number with no baseline and no diff.
- The LLM judge is unpinned and unvalidated against human labels.
- Content capture is on, 100%, unsampled, in production.
- Paying for three overlapping platforms because each was adopted for one feature.
- "We built our own" and it turns out to be a worse, unmaintained Langfuse.
- A regression does not block any deploy — evals exist but change nothing.

**Green flags:**

- Traces are OTel `gen_ai.*`; the backend is admittedly swappable.
- Graders live in the repo, are code-reviewed, and the judge model is version-pinned.
- Results are append-only in an open format and mirrored to the org's own store.
- Every dashboard tile maps to a decision and shows a baseline + diff.
- There is a small human-labeled gold set used to calibrate the judge.
- The team can state, per tool, which of the five jobs it does — and has retired
  duplicates.
- A production failure can be promoted into a CI regression test.

### Q&A bank

**Q1. A team says "we have LangSmith, so we're covered on evals." What's your
follow-up?**
LangSmith is strong on tracing/observability and provides an eval harness, but
"having the tool" is not "having an eval program." I'd ask: what's the dataset,
who defined the graders, what's the baseline, and does a regression block a
deploy? A platform provides the harness and storage; the team still has to supply
the rubric and the discipline. Coverage is a process question, not a license
question.

**Q2. When would you build a custom eval framework instead of buying?**
Rarely, and only for a thin layer. Justified when the system under test is
unusual (long-running multi-agent, simulator, hardware-in-loop), when data is
legally un-shippable and self-hosting an OSS tool is insufficient, or when the
grading logic is domain-specific with no library equivalent. Even then I reuse
OTel for tracing and an existing store, and only hand-write the harness glue and
domain graders. Building your own Langfuse is almost always a mistake.

**Q3. What's the difference between an eval framework and an observability
platform, and why does origin matter?**
Eval frameworks are batch/offline: run a dataset, get a score, fit into CI
(promptfoo, Inspect, DeepEval). Observability platforms are streaming/online:
capture live production traffic, search traces, alert on drift (Langfuse,
Helicone, Phoenix). Many tools now claim both, but almost all started on one side
and the other feels bolted on. Knowing the origin predicts where a tool is
genuinely strong versus checkbox-strong.

**Q4. How do you avoid tool lock-in?**
Two levers. One: standards-based tracing — emit OpenTelemetry `gen_ai.*` spans
(via OpenLLMetry) so any OTel backend can consume them and you can switch vendors
without re-instrumenting. Two: keep results in open formats (JSONL/Parquet) and
keep graders in your own repo. Before signing with any vendor I ask, "how do I
export *all* my data, and in what format?" If the answer is bad, that's a red
flag regardless of features.

**Q5. LLM-as-judge is convenient but has failure modes. Name them and your
mitigations.**
Cost (a second model on every case) — mitigate with caching on
(rubric, input, output) and a cheap heuristic pre-filter. Drift/non-stationarity
(the judge changes when the provider updates it) — pin the judge model version and
periodically validate against a human gold set. Unreliable output format —
require strict JSON and fail closed on parse errors, never silently pass.
Position/verbosity bias — randomize order and control for length in the rubric.

**Q6. What is "dashboard theater" and how do you prevent it?**
A dashboard of green numbers nobody has tied to a real decision — a mean score of
0.87 with no baseline, no diff, and no consequence. Prevent it by requiring every
tile to answer a decision ("ship?", "did case X regress?"), always showing a
baseline and a run-vs-run diff instead of a lone number, and periodically asking
"if this moved, would we do anything?" If not, delete the tile.

**Q7. Why does OpenTelemetry matter for agent evaluation specifically?**
Because agents produce deeply nested execution (agent → model calls → tool calls),
and OTel's GenAI conventions standardize exactly that hierarchy —
`invoke_agent`/`chat`/`execute_tool` spans with `gen_ai.*` attributes for model,
tokens, finish reasons, and content. Standard spans mean portable traces: same
instrumentation feeds Phoenix, Langfuse, or Datadog. The caveat is that the
conventions are still at Development stability, so pin versions — but even a
moving standard beats a proprietary schema.

**Q8. Design a minimal eval stack for a five-person startup shipping a RAG
agent.**
Self-host one tracing tool (Langfuse or Phoenix), instrument with OpenLLMetry for
portable spans. Use promptfoo for CI evals and add Ragas metrics for retrieval
faithfulness and context recall. Write graders in-repo with an injected judge
model, store results as JSONL, and read them in a notebook. Buy nothing until
multiple people are arguing about results weekly. Total cost: near zero, fully
portable, and every piece is replaceable.

**Q9. Walk me through the five jobs of an eval tool.**
Harness (runs the system over a dataset, with concurrency/retries/timeouts),
graders (turn an output into a score — heuristic, LLM-judge, or human), storage
(persist inputs/outputs/scores/metadata, versioned, so you can diff runs),
tracing (capture the nested execution inside one run), and reporting (dashboards,
diffs, alerts that drive decisions). Every product on the market is some subset;
the skill is naming which subset a tool does and what you still need to bolt on.

**Q10. Buy tracing but build graders — defend that split.**
Tracing is undifferentiated plumbing: capturing spans, storing them, drawing call
trees. Nobody's competitive advantage is a nicer span store, and it's expensive
to maintain, so rent it — but rent it standards-based (OTel) so it's swappable.
Graders are the opposite: they encode *your* definition of quality, they're small
(~30 lines each), and they must evolve with your product. Outsourcing them means
outsourcing your standard of correctness. So: rent the commodity, own the IP.

**Q11. Your headline quality metric jumped 5 points with no code change. What do
you check first?**
The grader before the agent. First suspect a non-stationary LLM judge — did the
provider update the judge model, or did someone change the rubric or threshold?
Re-score a fixed human-labeled gold set with the pinned judge to see if the
instrument moved. Also check dataset drift (did the test set change?) and
sampling. Only after ruling out measurement changes do I believe the agent
actually improved.

**Q12. How do you evaluate an agent trajectory, not just its final answer?**
Capture the full trajectory as nested spans (OTel `invoke_agent` → `plan` →
`execute_tool` → `chat`) so it's inspectable, then grade at multiple levels: final
answer correctness, plus trajectory-level graders like "did it call the right
tools in a sensible order," "did it avoid unnecessary/looping calls," and "did it
recover from a tool error." A correct answer via a broken plan is still a bug
because it won't generalize; only trajectory-aware grading catches it.

**Q13. What's your sampling and retention strategy for production tracing?**
Sample 100% in dev and a small, tunable fraction in production, with the ability
to force-capture flagged cases (errors, low scores, specific users). Capture
metadata always but full prompt/response payloads only opt-in, because content
capture is the expensive part. Set retention by tier — short for raw high-volume
traces, longer for sampled + flagged ones promoted into datasets. All of this
lives in a central OTel Collector so the policy is one place, not per service.

**Q14. When is a proxy-based tracer (Helicone) the right call, and what's the
cost?**
It's the right call when you want "see every LLM call" with essentially zero code
change and you value speed of integration over control — route calls through the
gateway and get logging, caching, and cost tracking immediately. The cost is that
the gateway sits in your request path: a hop that adds latency and a dependency on
its availability. For high-QPS or latency-sensitive paths, an in-process SDK/OTel
approach avoids the extra hop.

**Q15. How would you turn a production incident into a permanent regression test?**
Because the failing production trace and my eval results share a `trace_id` and
live in the same store, I promote the failing case's input (and the correct
expected output, once known) into a versioned eval dataset, add or reuse a grader
that would have caught it, and wire that dataset into CI so a future deploy that
regresses it is blocked. Production failures should ratchet the offline suite
upward; that loop is how eval coverage compounds.

**Q16. Two tools look identical on the landing page. How do you break the tie?**
I score them on a rubric: portability (can I export everything; does it speak
OTel?), how many of the five jobs it does deeply vs checkbox, self-host/data
residency, integration cost (lines of code in and out), trace fidelity for nested
agents, judge tooling (caching, version pinning, calibration), and cost model at
10x volume. Portability and integration cost usually break the tie, because
they're the durable, recurring costs the landing page hides.

**Q17. What changed in the eval-tooling landscape in 2025–2026 that you'd want a
team to know?**
Four things: agents (not chatbots) became the unit of evaluation, fusing tracing
and eval; OpenTelemetry's GenAI conventions matured — split into their own repo
with dedicated agent spans — and became the portable layer; LLM-as-judge went from
novelty to default *and* got audited (validation, pinning, calibration are now
expected); and the market consolidated with real capital, e.g. ClickHouse
acquiring Langfuse in January 2026. The strategic response to all of it is the
same: standardize on OTel, own your graders and data, rent the UI.

**Q18. A stakeholder wants "one tool for everything." How do you respond?**
I explain that all-in-one platforms do all five jobs but rarely all deeply, and
buying one to solve a problem you haven't hit yet trades money and lock-in for
features you won't use. I'd rather adopt the minimum that unblocks today's
bottleneck, keep tracing standards-based so consolidation is possible later, and
buy the all-in-one only for the specific job — usually multi-human collaboration —
where the pain is proven and recurring. One tool for everything is fine as an
outcome, dangerous as a starting assumption.

---

## Further reading

- LangSmith — <https://www.langchain.com/langsmith> · docs <https://docs.langchain.com/langsmith/>
- Braintrust — <https://www.braintrust.dev> · Autoevals <https://github.com/braintrustdata/autoevals>
- W&B Weave — <https://docs.wandb.ai/weave> · <https://github.com/wandb/weave>
- Arize Phoenix — <https://arize.com/phoenix/> · <https://github.com/Arize-ai/phoenix> · OpenInference <https://github.com/Arize-ai/openinference>
- Langfuse — <https://langfuse.com> · self-hosting <https://langfuse.com/self-hosting> · docs <https://langfuse.com/docs> · ClickHouse acquisition (Jan 16 2026) <https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability>
- Inspect (UK AISI) — <https://inspect.aisi.org.uk/> · <https://github.com/UKGovernmentBEIS/inspect_ai> · Inspect Evals <https://www.aisi.gov.uk/blog/inspect-evals>
- DeepEval — <https://deepeval.com> · <https://github.com/confident-ai/deepeval>
- Ragas — <https://www.ragas.io> · <https://github.com/explodinggradients/ragas>
- promptfoo — <https://www.promptfoo.dev> · <https://github.com/promptfoo/promptfoo>
- OpenAI Evals — <https://github.com/openai/evals>
- Helicone — <https://www.helicone.ai> · <https://github.com/helicone/helicone>
- MLflow GenAI evaluation — <https://mlflow.org/docs/latest/genai/eval-monitor/>
- OpenLLMetry (Traceloop) — <https://github.com/traceloop/openllmetry>
- OpenTelemetry GenAI semantic conventions — <https://opentelemetry.io/blog/2026/genai-observability/> · main spec <https://opentelemetry.io/docs/specs/semconv/gen-ai/> · dedicated repo <https://github.com/open-telemetry/semantic-conventions-genai>
- Datadog native OTel GenAI support — <https://www.datadoghq.com/blog/llm-otel-semantic-convention/>
