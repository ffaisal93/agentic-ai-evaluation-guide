# Automated Evaluation — A Practical Guide

> Making evaluation continuous and part of the engineering workflow, so quality is defended on every change instead of audited once a quarter.

---

## Why It Matters: Evals Rot Without Automation

Everyone who ships an agent runs an eval at least once. They open a notebook, run 50 examples, eyeball a spreadsheet, feel good, and merge. Three weeks later the notebook is stale, the prompt has been edited eleven times, a model version rolled forward underneath them, and nobody can say whether the agent is better or worse than the day it launched.

This is the default fate of a manual eval: **it rots.** Not because the team is lazy, but because a one-time measurement decays the instant the system under test changes — and an agent changes constantly. Prompts get tweaked, tools get added, retrieval corpora get re-indexed, the underlying model gets silently upgraded by the provider, a dependency bumps a tokenizer. Every one of those is a chance to regress, and a manual eval catches none of them because nobody re-ran it.

The fix is not "run the eval more often" through discipline. Discipline does not scale and does not survive on-call weeks. The fix is to make the eval **a machine that runs itself** — triggered by the same events that already gate your code (a pull request, a merge, a nightly cron), producing a pass/fail signal that blocks a bad change the same way a failing unit test does.

Concretely, automated evaluation buys you three things a manual eval cannot:

- **Regression protection.** A quality bar that a change must clear *before* it reaches users, not after they complain.
- **A ratchet.** Because the bar is enforced continuously, quality only moves in one direction: improvements stick, and backsliding is rejected at the door.
- **Institutional memory.** The eval config, the golden dataset, and the thresholds live in version control. When someone asks "why is groundedness 0.85 and not 0.90?", the answer is a reviewed commit, not a Slack scroll.

If you take one idea from this chapter: **evaluation is not a phase, it is a control loop.** The rest is engineering it correctly.

---

## Core Intuition: Treat Prompts and Agents Like Code

Software engineering already solved "how do we keep a fast-changing artifact from silently breaking." The answer was the test suite plus CI: every change is proposed as a diff, the diff runs the tests, and the merge is blocked if they fail. Nobody merges to `main` on vibes.

The whole of automated evaluation is applying that discipline to the parts of an agent that are *not* traditional code — the prompt, the tool definitions, the retrieval config, the model choice — and to a metric that is *not* boolean — a success rate, a groundedness score, a judge rating.

Two adjustments make the analogy work in practice, and both are the source of every hard problem in this chapter:

1. **The unit under test is behavioral, not structural.** A unit test asserts `add(2, 2) == 4`. An eval asserts "the agent books the flight correctly on ≥ 90% of the 200 booking scenarios." The assertion is statistical, over a dataset, against a threshold — not a single equality.

2. **The system under test is nondeterministic.** Run the same prompt twice and you may get two different outputs. Temperature, sampling, batch-dependent floating point, and model-side changes all mean the *same input* can pass one run and fail the next. A unit test that flips randomly is a bug; an eval that flips randomly is Tuesday. Managing that noise rigorously — rather than pretending it away — is the difference between a gate people trust and a gate people disable.

Hold those two facts and the rest of the design follows: you need a dataset (not one example), a grader (to turn text into a number), a statistical gate (to turn a noisy number into a trustworthy pass/fail), and a place to run it automatically (CI).

---

## Anatomy of an Automated Eval Pipeline

Every automated eval — whether built on promptfoo, DeepEval, LangSmith, Braintrust, or hand-rolled — is the same seven components wired in a line. Learn the parts once and every tool is just a different spelling of them.

```
 TRIGGER ──▶ DATASET ──▶ HARNESS ──▶ GRADERS ──▶ GATE ──▶ REPORT ──▶ ALERT
 (PR /       (golden,     (run the    (score      (pass/   (HTML,     (Slack,
  merge /     versioned,   agent on    each        fail vs  JUnit,     PagerDuty
  cron /      sliced)      each row,   output:     baseline dashboard  on
  deploy)                  capture     exact,      +          link)    regression)
                           traces)     judge,      threshold)
                                       rubric)
```

**1. Trigger.** The event that starts a run. In CI this is a GitHub Actions `on:` clause: `pull_request` for PR gates, `schedule` (cron) for nightly runs, `workflow_dispatch` for manual, and `deployment` / post-merge for canary comparison. The trigger determines how much you can afford to run (see the CI/CD section).

**2. Dataset.** The set of inputs plus expected outputs (or grading criteria). This is your *golden dataset* — versioned, reviewed, and sliced by category. It is the single most valuable and most neglected asset in the pipeline. A gate is only as good as the examples it runs.

**3. Harness.** The code that actually invokes the agent on each dataset row and captures the output *and the trace* (tool calls, retrieved chunks, intermediate steps). For agents you almost always want the trace, because you grade tool-use and process, not just the final string.

**4. Graders (scorers).** The functions that turn an output into a number. Three families, roughly in order of cost and flexibility:
   - **Deterministic / programmatic** — exact match, regex, JSON-schema validity, `contains`, numeric tolerance. Free, instant, zero variance. Use them for everything you can.
   - **Model-graded (LLM-as-judge)** — a second model scores groundedness, helpfulness, or rubric adherence. Flexible, but slow, costly, and *itself noisy*.
   - **Reference / embedding** — semantic similarity to a gold answer, NLI-based entailment for faithfulness.

**5. Gate.** The decision logic that turns per-example scores into a single **pass or fail** for the run. This is where thresholds, baselines, and statistical tests live. The gate is what makes the pipeline a *gate* and not a dashboard.

**6. Report.** The human-readable artifact: an HTML diff of this run vs baseline, a JUnit XML the CI renders as test results, a link to a hosted experiment. When the gate fails, the report is how a human finds out *why* in under a minute.

**7. Alert.** The push notification when a gate fails on a protected branch or a nightly run regresses — Slack webhook, PagerDuty, GitHub check annotation. Without this, nightly failures are discovered three days later.

Everything in the rest of the chapter is a decision about one of these seven boxes.

---

## CI/CD Integration Patterns: PR Smoke vs Nightly Full

The central tension of automated eval is a triangle you cannot fully satisfy on every run:

\[
\text{cheap} \quad \wedge \quad \text{fast} \quad \wedge \quad \text{statistically significant}
\]

Pick any two. A 30-example suite that runs in 40 seconds for twelve cents is cheap and fast but has so much variance it cannot detect a real regression. A 2,000-example LLM-judge sweep is significant but costs dollars and minutes. You resolve the triangle not by finding a magic run but by running **different suites at different triggers** — spending your statistical-significance budget where you can afford the latency.

The standard, battle-tested layout is three tiers:

| Tier | Trigger | Size | Graders | Latency budget | Cost budget | Gate strictness |
|---|---|---|---|---|---|---|
| **PR smoke eval** | Every `pull_request`, scoped to changed routes | 30–100 curated + deterministic checks | Mostly programmatic + cheap classifier cascade; few/no frontier judges | < 3 min | Cents | Hard block, but only on catastrophic/absolute floors |
| **Nightly full eval** | `schedule` cron (e.g. 02:00 UTC) | 500–2,000 versioned corpus | Full LLM-judge sweep + all scorers | 20–60 min | Dollars | Statistical delta gate vs rolling baseline; blocks the release train, not the PR |
| **Online / canary eval** | Post-deploy, 1–5% live traffic | Sampled real traffic | Same rubrics, async | Continuous | Metered by sample rate | Auto-rollback / alert, not a merge gate |

The design rule behind the table: **the PR gate must be fast enough that engineers never learn to hate it**, so it runs a small, mostly-deterministic suite on only the code paths the diff touched. The heavy, statistically rigorous work moves to nightly, where a 40-minute run is invisible because everyone is asleep. Anything you cannot simulate offline — real user distribution, live model drift — gets caught by the canary in production.

### Why the PR gate must stay deterministic-heavy

An LLM judge on every PR is a trap: it is slow, it costs money on every commit (and engineers commit dozens of times a day), and it *adds its own noise* to a signal you are trying to keep clean. The high-leverage move is a **classifier cascade** — run cheap deterministic and small-classifier rubrics on all PR examples first, and only escalate the handful of low-confidence cases to an expensive frontier judge. Reported effect is roughly a 10x cost reduction on the PR tier without losing signal. Reserve the full judge sweep for nightly.

### Scoping to changed paths

Use your CI's path filters so a docs-only PR does not run the retrieval eval. In GitHub Actions:

```yaml
on:
  pull_request:
    paths:
      - "prompts/**"
      - "src/agent/**"
      - "evals/**"
```

Combine with a job `matrix` to shard routes across runners so one slow slice does not serialize the whole suite, and set `concurrency: { group: eval-${{ github.ref }}, cancel-in-progress: true }` so a new push cancels the stale run instead of queueing behind it.

---

## Handling Nondeterminism and Flakiness Rigorously

This is the section that separates a gate people trust from a gate people route around. LLM outputs vary run to run for reasons that are mostly *not* your bug: sampling temperature, provider-side model updates, and even batch-size-dependent floating-point non-associativity in the inference kernels (a genuine, documented source of nondeterminism even at temperature 0). If you gate on a single sample against a hard threshold, your gate will flip red on noise, engineers will hit "re-run" until it passes, and the gate is now theater.

Handle it with four layers, in order:

### 1. Reduce variance at the source

- **Pin what you can.** Set `temperature=0` (or a fixed `seed` where the provider honors it) for gradeable tasks; pin the exact model version string (`gpt-4o-2024-08-06`, not `gpt-4o`) so a provider rollout is a *reviewed* change, not a surprise.
- Accept that pinning reduces but does **not eliminate** variance — hence the next layers.

### 2. Sample multiple times, gate on the aggregate

Run each example \(k\) times (typically \(k = 3\) to \(5\)) and aggregate. For a per-example pass/fail, use **majority vote** or **pass@k / pass^k** depending on whether you care about "can it ever" or "does it reliably." The suite-level metric becomes the mean of a many-Bernoulli process, whose noise you can *quantify* — which unlocks layer 3.

### 3. Gate on a statistical bound, not a point estimate

Do not compare a raw mean to a threshold. Compare a **confidence bound** to the threshold. If your suite of \(n\) examples has \(s\) successes, the point estimate is \(\hat{p} = s/n\), but the honest question is "given noise, could the *true* success rate be below my bar?" Use the lower bound of a binomial confidence interval. The **Wilson score interval** is the right default (it behaves near 0 and 1 where the naive normal interval breaks):

\[
\hat{p}_{\pm} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
\]

with \(z = 1.96\) for 95% confidence. **Gate on the lower bound** \(\hat{p}_{-} \ge \text{threshold}\): you only fail the build when you are statistically confident the true rate is below the bar. This directly kills "small sample, unlucky run" flakiness — and it tells you when your dataset is simply *too small* to conclude anything (the interval is wide).

### 4. For regressions, require a significant *and* meaningful drop

When comparing a candidate to a baseline, a naive "mean went down → fail" fires constantly on judge noise. The rigorous gate is a conjunction of three conditions:

\[
\text{FAIL} \iff (\text{mean dropped}) \;\wedge\; (\underbrace{p < 0.05}_{\text{Welch's t-test}}) \;\wedge\; (\underbrace{\Delta > \delta_{\min}}_{\text{effect floor}})
\]

That is: the mean must drop, the drop must be statistically significant (Welch's t-test on the per-example score arrays — not just the means), **and** the drop must exceed a minimum effect size you actually care about. Requiring all three prevents the two failure modes at once: significant-but-trivial drops (a 0.3% dip with a huge sample) and large-but-noisy drops (a 5% dip on 12 examples).

### 5. Quarantine, don't ignore

Some examples are irreducibly flaky (ambiguous ground truth, judge disagreement). Tag them `@flaky` and move them to a **quarantine suite** that runs and reports but does *not* block the merge. This keeps the main gate green and trustworthy while preserving the signal. The discipline: a test in quarantine is a bug ticket, not a graveyard — review the quarantine list every sprint or it becomes a place tests go to die.

---

## Regression Detection: Baselines, Thresholds, Slices

A gate needs something to compare against. Two philosophies, usually combined:

**Absolute floors.** Fixed thresholds that encode a non-negotiable quality bar: groundedness ≥ 0.85, JSON-validity = 1.0, tool-selection accuracy ≥ 0.90. These catch *catastrophic* failures — a prompt edit that breaks structured output entirely. They live in version control and change only via reviewed PR.

**Relative / delta gates.** Compare the candidate to a **rolling baseline** — typically the score of `main` over the last N days, stored as a checked-in JSON so a threshold change shows up as a reviewed diff. These catch *slow drift*: a series of individually-innocent prompt tweaks that each drop quality 0.5% until you have lost ten points and nobody noticed. The delta gate uses the significant-and-meaningful conjunction from the previous section.

**Per-slice regression is the one people miss.** Your aggregate success rate can be flat while a subpopulation collapses. Overall 92% → 91% looks fine; hidden inside it, the `refund` intent went 95% → 70% and the `spanish_language` slice went 88% → 60%, masked by the `faq` slice getting easier. **Always gate per slice, not just on the mean.** Break the dataset into categories (intent, language, difficulty, tool-required-vs-not) and apply the regression test to each. A per-slice gate is the difference between "we shipped a small overall dip" and "we shipped a total outage for Spanish-speaking refund requests."

Practical baseline hygiene:
- Store baselines as a **reviewed artifact** (JSON in the repo, or a named experiment in Braintrust/LangSmith), never as "whatever `main` happened to score today."
- **Promote** a candidate's scores to the new baseline only after it merges — so the ratchet moves forward.
- Keep the baseline **dataset version** pinned alongside the scores; comparing scores across two different dataset versions is meaningless (see silent dataset drift, below).

---

## Fully Worked Example: A Success-Rate Gate With a Confidence Check

This is a complete, correct, runnable pattern: a pytest-style eval that runs an agent over a golden dataset, computes a success rate, and **gates the build on the Wilson lower bound clearing a threshold** — so the build only fails when we are statistically confident the true success rate is below the bar. Below it is the GitHub Actions workflow that runs it as a PR gate.

### The eval: `evals/test_booking_agent.py`

```python
"""Automated eval that gates CI on a statistically-sound success rate.

Run locally:      pytest evals/test_booking_agent.py -v
Run in CI:        same command; a failing assert fails the build.
"""
import json
import math
import os
from pathlib import Path

import pytest

from src.agent import booking_agent          # the system under test
from src.graders import grade_booking         # deterministic grader -> bool

# ---- Config: absolute floor + statistical rigor knobs --------------------
SUCCESS_THRESHOLD = 0.90     # the quality bar (absolute floor)
CONFIDENCE_Z = 1.96          # 95% two-sided -> one-sided lower bound
SAMPLES_PER_CASE = 3         # repeat each case to average out nondeterminism


def wilson_lower_bound(successes: int, n: int, z: float = CONFIDENCE_Z) -> float:
    """Lower bound of the Wilson score interval for a binomial proportion.

    Stable near p=0 and p=1 where the normal approximation fails. We gate on
    THIS, not on the raw rate, so a small/unlucky sample cannot flake the build.
    """
    if n == 0:
        return 0.0
    p_hat = successes / n
    denom = 1.0 + z * z / n
    center = p_hat + z * z / (2 * n)
    margin = z * math.sqrt((p_hat * (1 - p_hat) + z * z / (4 * n)) / n)
    return (center - margin) / denom


def load_golden(path: str = "evals/data/booking_golden_v3.jsonl") -> list[dict]:
    """Load the versioned golden dataset. The version is IN THE FILENAME so a
    dataset change is an explicit, reviewable diff — never a silent swap."""
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    assert rows, "golden dataset is empty — refusing to run a meaningless gate"
    return rows


GOLDEN = load_golden()


@pytest.mark.eval
def test_booking_success_rate():
    """Run every golden case SAMPLES_PER_CASE times, grade deterministically,
    and gate the build on the Wilson lower bound clearing the threshold."""
    successes, trials = 0, 0
    per_slice: dict[str, list[int]] = {}

    for row in GOLDEN:
        for _ in range(SAMPLES_PER_CASE):
            output = booking_agent.run(row["input"])          # capture output
            ok = grade_booking(output, row["expected"])       # -> bool
            successes += int(ok)
            trials += 1
            per_slice.setdefault(row["slice"], []).append(int(ok))

    rate = successes / trials
    lower = wilson_lower_bound(successes, trials)

    # ---- Report (prints to CI log; also emit JSON for the dashboard) ------
    print(f"success_rate={rate:.3f}  wilson_lb={lower:.3f}  "
          f"n={trials}  threshold={SUCCESS_THRESHOLD}")
    Path("eval_report.json").write_text(json.dumps({
        "success_rate": rate, "wilson_lower_bound": lower,
        "trials": trials, "threshold": SUCCESS_THRESHOLD,
        "slices": {s: sum(v) / len(v) for s, v in per_slice.items()},
    }, indent=2))

    # ---- Per-slice floor: aggregate can hide a collapsed subpopulation ----
    for slice_name, results in per_slice.items():
        s_rate = sum(results) / len(results)
        assert s_rate >= 0.75, (
            f"slice '{slice_name}' collapsed to {s_rate:.2f} "
            f"(< 0.75 floor) even though overall looks fine"
        )

    # ---- The gate: fail ONLY when we are confident the TRUE rate is low ---
    assert lower >= SUCCESS_THRESHOLD, (
        f"Wilson lower bound {lower:.3f} < threshold {SUCCESS_THRESHOLD}. "
        f"Point estimate was {rate:.3f} over {trials} trials. Either quality "
        f"regressed, or the dataset is too small to prove it met the bar."
    )
```

Two properties make this gate trustworthy rather than flaky:

- It gates on `wilson_lower_bound`, so an unlucky run on a small sample produces a wide interval and a *clear* failure message ("too small to prove it met the bar") instead of a random red X. Grow the dataset and the interval tightens.
- It enforces a **per-slice floor** before the aggregate gate, so a collapsed subpopulation fails loudly even when the overall mean looks healthy.

### The CI: `.github/workflows/pr-eval.yml`

```yaml
name: PR Smoke Eval
on:
  pull_request:
    paths: ["prompts/**", "src/**", "evals/**"]

concurrency:
  group: pr-eval-${{ github.ref }}
  cancel-in-progress: true          # a new push cancels the stale run

jobs:
  eval:
    runs-on: ubuntu-latest
    timeout-minutes: 10             # a hung judge must not block merges forever
    env:
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      # Cache model responses so re-runs on unchanged inputs cost $0.
      PROMPTFOO_CACHE_PATH: ~/.cache/eval
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }

      - name: Restore eval response cache
        uses: actions/cache@v4
        with:
          path: ~/.cache/eval
          key: eval-${{ hashFiles('prompts/**', 'evals/data/**') }}

      - run: pip install -r requirements.txt

      - name: Run gating eval
        run: pytest evals/test_booking_agent.py -v -m eval

      # Always surface the numbers, even when the gate fails.
      - name: Publish eval report
        if: always()
        uses: actions/upload-artifact@v4
        with: { name: eval-report, path: eval_report.json }
```

The `if: always()` on the report upload is the detail people forget: when the gate fails, that is *exactly* when you most need the numbers, so the report must be produced on failure too. The response cache means a re-run on an unchanged prompt is free — cost is paid once per real change, not once per CI trigger.

### The same pattern in the ecosystem tools

You rarely have to build all of this by hand. The identical seven-box pipeline is expressed by:

- **promptfoo** — declarative `promptfooconfig.yaml` with `assert` blocks and thresholds; the [promptfoo GitHub Action](https://github.com/promptfoo/promptfoo-action) runs it on PRs, and the CLI exits non-zero when assertions fail so the build blocks automatically.
- **DeepEval** — `deepeval test run test_file.py` wraps pytest; `assert_test(golden, metrics=[...])` raises when a metric falls below its `threshold`, and `@pytest.mark.parametrize("golden", dataset.goldens)` drives it from a versioned dataset.
- **LangSmith** — `@pytest.mark.langsmith` syncs each test to a dataset example, `log_outputs` / `log_reference_outputs` record results, and pass/fail is tracked as feedback with a rich `--langsmith-output` display.
- **Braintrust** — `Eval(...)` with `scorers=[...]` runs experiments that auto-compare against a baseline in CI and surface per-example regressions.

---

## Cost and Runtime Management

Eval suites cost real money (every judged example is 1–3 model calls) and real wall-clock time, and both grow with your dataset. Left unmanaged, a full suite on every commit will either bankrupt the eval budget or get so slow that people disable it. Levers, cheapest-win first:

| Lever | What it does | Typical effect |
|---|---|---|
| **Deterministic-first / classifier cascade** | Run free programmatic + small-classifier graders on all rows; escalate only low-confidence rows to a frontier judge | ~10x cost cut on the PR tier |
| **Response caching** | Cache model outputs keyed by (prompt, input); re-runs on unchanged inputs cost $0 | Most CI re-runs become free |
| **Tiering (PR vs nightly)** | Small suite on PRs, big suite nightly | Moves the dollars off the hot path |
| **Path scoping + sharding** | Only run routes the diff touches; parallelize with a CI matrix | Cuts both cost and latency |
| **Sampling the golden set** | PR runs a stratified sample; nightly runs the full corpus | Bounds PR cost at the price of some sensitivity |
| **Cheaper judge model** | Use a small model as judge where it correlates with the big one (validate first!) | Large per-call savings if correlation holds |
| **Fail-fast on catastrophe** | If JSON-validity or a deterministic floor fails, stop before running expensive judges | Avoids paying for a doomed run |

Two guardrails worth wiring in: a **per-run cost ceiling** (abort and alert if a run exceeds \(N\) dollars — cheap insurance against an infinite-loop agent burning tokens) and a **cached-vs-live ratio** in the report so you notice when caching silently stopped working and costs quietly 10x'd.

---

## Failure Modes and Pitfalls

**The gate is too strict or flaky, so people route around it.** A gate that flips red on noise trains engineers to hit "re-run until green," which is worse than no gate — it produces false confidence. Fix with the statistical machinery above (confidence bounds, multiple samples, significant-*and*-meaningful deltas) and quarantine irreducibly flaky cases. A gate's credibility is its entire value; spend it carefully.

**Overfitting to the CI eval (the eval becomes the target).** This is Goodhart's law: once a fixed 50-example set gates every merge, people optimize prompts *against those 50 examples* — sometimes literally pasting failing cases into the prompt. The suite goes green while real-world quality stalls. Defenses: keep a **held-out** slice that never informs prompt edits, **rotate/grow** the golden set over time, and treat a suddenly-perfect score as a smell to investigate, not a trophy.

**Silent dataset drift.** The golden dataset changes underneath the comparison — someone edits `expected` values, a re-export reorders rows, a labeler "fixes" answers — and now this week's 91% and last week's 93% are measured against different rulers. The regression is an artifact of the dataset, not the agent. Defenses: **version the dataset** (hash or version in the filename, like `booking_golden_v3.jsonl`), require dataset changes to go through **reviewed PRs**, pin the **dataset version alongside every baseline score**, and refuse to compare scores across versions.

**LLM-judge drift.** Your grader is itself a model, and the provider can change it. A groundedness score that "regressed" may be the judge getting stricter, not the agent getting worse. Pin the judge model version, and periodically **re-validate the judge against human labels** — the judge is a measuring instrument and instruments need calibration.

**Nightly failures nobody sees.** A cron eval fails at 02:00, the report sits in an artifact, and the regression is discovered three days later by a user. If a run has no **alert** wired to a channel a human watches, it is not a gate — it is a log file. Wire the Slack/PagerDuty hook the day you create the nightly.

**A green suite that tests the wrong thing.** The most dangerous failure is a passing gate on a dataset that does not reflect production. High coverage of easy cases and zero coverage of the failure modes users actually hit. The eval is only ever as good as the golden dataset; invest there before you invest in fancier graders.

---

## Tools Table

| Tool | Shape | CI/CD hook | Best for | Notes |
|---|---|---|---|---|
| **promptfoo** | Declarative YAML + CLI | Official GitHub Action; CLI exits non-zero on assertion failure; JSON/HTML/JUnit output | Prompt & RAG regression gates, red-teaming | Response caching built in (`PROMPTFOO_CACHE_PATH`); `--share` for hosted reports |
| **DeepEval** | pytest-native (`deepeval test run`) | `assert_test` raises below `threshold`; drives from `dataset.goldens` | Python teams wanting eval-as-unit-test | 14+ research-backed metrics; pairs with Confident AI for hosting |
| **LangSmith** | SDK + `@pytest.mark.langsmith` / Vitest | Syncs tests to datasets; pass/fail as feedback; `--langsmith-output` | LangChain/LangGraph stacks, tracing + eval together | Online eval on production traces; dataset versioning in-platform |
| **Braintrust** | `Eval()` SDK + hosted experiments | Auto-compares candidate vs baseline in CI; per-example regression view | Teams wanting rich experiment diffing | Strong side-by-side regression UX |
| **OpenAI Evals** | Open-source registry + `oaieval` | Run in CI via CLI; YAML-registered evals over samples | Benchmark-style, model-vs-model | Community registry of benchmarks; more benchmark than app-eval |
| **Custom pytest + Wilson/Welch** | Hand-rolled (this chapter) | Plain `pytest` assert fails the build | Full control over statistical gating | Zero lock-in; you own the confidence math |

---

## Interviewer Q&A

**Q1. Why not just run your full eval suite on every pull request?**
Because of the cheap/fast/significant triangle: a statistically meaningful suite (hundreds of judged examples) is slow and expensive, and running it on every commit either blows the budget or gets so slow engineers disable it. The standard resolution is tiering — a small, mostly-deterministic, path-scoped smoke suite on PRs for fast feedback, and the heavy statistically-rigorous judge sweep nightly where a 40-minute run is invisible. Production canary catches what offline cannot.

**Q2. Your eval gate flips red randomly and engineers just re-run it. What's wrong and how do you fix it?**
The gate is comparing a single noisy sample to a hard threshold, so LLM nondeterminism flips it. Fix in layers: pin model version and temperature to cut variance at the source; sample each case k times and aggregate; and crucially, gate on a **confidence bound** (Wilson lower bound) rather than the point estimate, so you only fail when statistically confident the true rate is below the bar. For regressions, require the drop to be significant (Welch's t-test) *and* exceed a minimum effect size. Quarantine irreducibly flaky cases so they report but don't block.

**Q3. Why gate on a Wilson lower bound instead of the raw success rate?**
The raw rate is a point estimate with sampling noise; on a small suite it can land above or below the threshold by luck. The Wilson lower bound answers the honest question — "could the *true* rate be below my bar?" — and is stable near 0 and 1 where the normal approximation breaks. Gating on it means an unlucky small run yields a wide interval and a clear "too small to conclude" failure, not a random flake; growing the dataset tightens the interval. It simultaneously enforces quality *and* dataset adequacy.

**Q4. Your overall success rate is flat but users report the agent broke for a specific case type. How does automated eval catch that?**
Per-slice gating. An aggregate mean can stay flat while a subpopulation collapses, masked by another slice getting easier. You break the dataset into categories (intent, language, difficulty, tool-required) and run the regression/threshold test on *each slice*, not just the mean. A per-slice floor fails loudly when, say, the Spanish refund slice drops from 88% to 60% even though the overall number barely moved.

**Q5. What is "overfitting to the eval" and how do you prevent it?**
Goodhart's law: once a fixed small dataset gates every merge, people optimize prompts against those specific examples — sometimes pasting failing cases straight into the prompt — so the suite goes green while real quality stalls. Prevent it with a held-out slice that never informs prompt changes, by rotating and growing the golden set over time, and by treating a suddenly-perfect score as a smell to investigate rather than a win.

**Q6. How do you keep eval costs from exploding as your suite grows?**
Deterministic-first grading with a classifier cascade (free programmatic checks on all rows, escalate only low-confidence cases to a frontier judge — roughly 10x cheaper); response caching so re-runs on unchanged inputs cost nothing; tiering so the dollars sit in nightly not on every commit; path-scoping and sharding; and a per-run cost ceiling that aborts and alerts on a runaway agent. Validate any cheaper judge model against the expensive one before trusting it.

**Q7. What is silent dataset drift and why is it dangerous?**
It's when the golden dataset changes underneath your comparison — edited expected values, reordered rows, "corrected" labels — so this week's score and last week's score are measured against different rulers, and a phantom regression appears that has nothing to do with the agent. It's dangerous because it silently invalidates the whole gate. Defend by versioning the dataset (version in the filename), requiring reviewed PRs for dataset changes, pinning the dataset version alongside every baseline score, and refusing cross-version comparisons.

**Q8. Where does online/continuous evaluation fit relative to CI evals?**
CI evals (PR + nightly) run offline against a curated golden set — they catch regressions before shipping but only for scenarios you thought to include. Online eval runs the same rubrics asynchronously on a sample of *live production traffic*, catching what offline cannot: real user distribution, model drift, and long-tail inputs. It typically drives alerts and auto-rollback rather than blocking a merge, and its surprising failures become new golden examples — closing the loop back into the offline suite.

---

## Further Reading

- promptfoo — CI/CD Integration: <https://www.promptfoo.dev/docs/integrations/ci-cd/>
- promptfoo GitHub Action: <https://github.com/promptfoo/promptfoo-action>
- DeepEval — Unit Testing in CI/CD: <https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd>
- DeepEval — Regression Testing in CI/CD (guide): <https://deepeval.com/guides/guides-regression-testing-in-cicd>
- LangSmith — Run evaluations with pytest: <https://docs.langchain.com/langsmith/pytest>
- LangChain blog — Pytest and Vitest integrations for LangSmith evals: <https://blog.langchain.com/pytest-and-vitest-for-langsmith-evals/>
- Braintrust — Evaluate systematically: <https://www.braintrust.dev/docs/evaluate>
- OpenAI Evals — Running evals: <https://github.com/openai/evals/blob/main/docs/run-evals.md>
- Future AGI — LLM Eval Gates in GitHub Actions (statistical gating, cascades, exit codes): <https://futureagi.com/blog/ci-cd-llm-eval-github-actions-2026/>
- Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference (arXiv): <https://arxiv.org/html/2506.09501v2>
- Wilson score interval (binomial proportion confidence interval): <https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval>

---

*This chapter is part of "Agentic AI Evaluation — A Practical Guide." It treats evaluation as a control loop wired into CI, not a phase — the mechanisms here (statistical gates, tiered triggers, versioned goldens, per-slice regression) are what keep an agent's quality from rotting one innocent change at a time.*
