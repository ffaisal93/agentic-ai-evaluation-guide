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
  answer when someone wants "open-source LangSmith."
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

Why you should care: if your agent emits **standard `gen_ai.*` spans**, you can
point them at Phoenix today, Langfuse tomorrow, and Datadog next year without
re-instrumenting your code. That is the single strongest antidote to lock-in in
the whole chapter. Tools like **OpenLLMetry** (Traceloop) exist precisely to
emit these standard spans from your app, and OTel-native platforms like
**Phoenix** consume them directly.

The honest caveat: the GenAI conventions are **still evolving** — actively
developed, already useful, but not fully frozen, and some attribute names have
already been renamed/deprecated between versions. Adopt them, but pin versions
and expect churn. Even a moving standard is more portable than a proprietary
schema. See the OpenTelemetry GenAI SIG for current status.
<https://opentelemetry.io/blog/2026/genai-observability/>

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

## Interviewer Q&A

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
conventions are still evolving, so pin versions — but even a moving standard beats
a proprietary schema.

**Q8. Design a minimal eval stack for a five-person startup shipping a RAG
agent.**
Self-host one tracing tool (Langfuse or Phoenix), instrument with OpenLLMetry for
portable spans. Use promptfoo for CI evals and add Ragas metrics for retrieval
faithfulness and context recall. Write graders in-repo with an injected judge
model, store results as JSONL, and read them in a notebook. Buy nothing until
multiple people are arguing about results weekly. Total cost: near zero, fully
portable, and every piece is replaceable.

---

## Further reading

- LangSmith — <https://www.langchain.com/langsmith> · docs <https://docs.langchain.com/langsmith/>
- Braintrust — <https://www.braintrust.dev> · Autoevals <https://github.com/braintrustdata/autoevals>
- W&B Weave — <https://docs.wandb.ai/weave> · <https://github.com/wandb/weave>
- Arize Phoenix — <https://arize.com/phoenix/> · <https://github.com/Arize-ai/phoenix>
- Langfuse — <https://langfuse.com> · self-hosting <https://langfuse.com/self-hosting>
- Inspect (UK AISI) — <https://inspect.aisi.org.uk/> · <https://github.com/UKGovernmentBEIS/inspect_ai> · Inspect Evals <https://www.aisi.gov.uk/blog/inspect-evals>
- DeepEval — <https://deepeval.com> · <https://github.com/confident-ai/deepeval>
- Ragas — <https://www.ragas.io> · <https://github.com/explodinggradients/ragas>
- promptfoo — <https://www.promptfoo.dev> · <https://github.com/promptfoo/promptfoo>
- OpenAI Evals — <https://github.com/openai/evals>
- Helicone — <https://www.helicone.ai> · <https://github.com/helicone/helicone>
- MLflow GenAI evaluation — <https://mlflow.org/docs/latest/genai/eval-monitor/>
- OpenLLMetry (Traceloop) — <https://github.com/traceloop/openllmetry>
- OpenTelemetry GenAI semantic conventions — <https://opentelemetry.io/blog/2026/genai-observability/> · <https://opentelemetry.io/docs/specs/semconv/gen-ai/>
