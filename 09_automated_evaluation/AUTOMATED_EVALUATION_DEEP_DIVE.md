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

There is a fourth thing, quieter but decisive over a year: **automated eval changes the unit of debate on the team.** Without it, "is the new prompt better?" is a taste argument won by whoever is most senior or most stubborn in the room. With it, the argument is a number attached to a diff, reproducible by anyone, and the review culture shifts from opinion to evidence. That cultural shift is the real payoff, and it is why the strongest applied-AI teams treat their eval harness as a first-class product surface with an owner, an on-call, and a roadmap — not a script in someone's home directory.

If you take one idea from this chapter: **evaluation is not a phase, it is a control loop.** The rest is engineering it correctly.

> **Saying it out loud.** So the honest answer to "why automate evals" is that a manual eval rots — not because anyone's lazy, but because a one-time measurement expires the moment the thing you measured changes, and an agent changes every day. Prompts get tweaked, tools get added, the provider silently rolls the model forward, and nobody re-runs the notebook. Automating it buys three things a notebook can't: regression protection before users feel it, a ratchet so quality only moves one way, and institutional memory, because the thresholds live in version control instead of a Slack scroll. The one I'd actually lead with is the cultural payoff — once there's a number attached to the diff, "is the new prompt better?" stops being an argument won by whoever is most senior in the room. The sentence to land on: evaluation isn't a phase, it's a control loop.

### The cost of not doing it (a concrete failure timeline)

To make the stakes vivid, here is the shape of the incident that this chapter exists to prevent — a composite drawn from how these actually unfold:

```
 Day 0   Prompt tweak to "be more concise" merges. Manual spot-check looks fine.
 Day 2   Provider silently rolls the base model forward a minor version.
 Day 5   A dependency bump changes the JSON parser's coercion of "true"/"false".
 Day 9   Someone "improves" a tool description; tool-selection drifts on 8% of cases.
 Day 14  A customer opens a ticket: "the agent stopped citing sources."
 Day 15  Eng cannot reproduce. No baseline. No dataset. No idea which change did it.
 Day 18  Bisecting 40 merged PRs by hand. Groundedness was never measured after Day 0.
 Day 21  Root cause: three independent 1–2 point drops that compounded. Ship a fix on faith.
```

Every one of those days is a place an automated gate would have failed a build and named the culprit in a diff. The manual team paid for it with a three-week fire drill and a customer who no longer trusts the product. The automated team paid for it with a red check on a PR and a five-minute revert. Same bugs, wildly different blast radius.

---

## Core Intuition: Treat Prompts and Agents Like Code

Software engineering already solved "how do we keep a fast-changing artifact from silently breaking." The answer was the test suite plus CI: every change is proposed as a diff, the diff runs the tests, and the merge is blocked if they fail. Nobody merges to `main` on vibes.

The whole of automated evaluation is applying that discipline to the parts of an agent that are *not* traditional code — the prompt, the tool definitions, the retrieval config, the model choice — and to a metric that is *not* boolean — a success rate, a groundedness score, a judge rating.

Two adjustments make the analogy work in practice, and both are the source of every hard problem in this chapter:

1. **The unit under test is behavioral, not structural.** A unit test asserts `add(2, 2) == 4`. An eval asserts "the agent books the flight correctly on ≥ 90% of the 200 booking scenarios." The assertion is statistical, over a dataset, against a threshold — not a single equality.

2. **The system under test is nondeterministic.** Run the same prompt twice and you may get two different outputs. Temperature, sampling, batch-dependent floating point, and model-side changes all mean the *same input* can pass one run and fail the next. A unit test that flips randomly is a bug; an eval that flips randomly is Tuesday. Managing that noise rigorously — rather than pretending it away — is the difference between a gate people trust and a gate people disable.

Hold those two facts and the rest of the design follows: you need a dataset (not one example), a grader (to turn text into a number), a statistical gate (to turn a noisy number into a trustworthy pass/fail), and a place to run it automatically (CI).

There is a third, subtler adjustment that trips up teams coming from classical testing: **the oracle is expensive and imperfect.** In unit testing the correct answer is known and cheap to check — you wrote `== 4`. In agent eval, deciding whether an open-ended answer is "correct" often requires a second model (an LLM judge), a human, or a carefully engineered deterministic checker, and each of those is either slow, costly, or itself noisy. A huge fraction of the craft in this chapter is **pushing as much of the oracle as possible down the cost/variance ladder** — turning a fuzzy "is this a good answer?" into a crisp deterministic assertion wherever the task allows, and reserving the expensive judge for the residue that genuinely needs it.

> **Saying it out loud.** The framing is that CI already solved this for code — propose a diff, run the tests, block the merge if they fail — and you're applying it to the parts of an agent that aren't code: the prompt, the tools, the retrieval config. Two things break the analogy, and every hard problem in the chapter falls out of them. First, the assertion is statistical, not boolean: it's not `add(2,2) == 4`, it's "books the flight correctly on at least 90% of 200 scenarios." Second, the system under test is nondeterministic, so the same input passes Monday and fails Tuesday — a unit test that flips randomly is a bug, an eval that flips randomly is just Tuesday. And the third one people forget: the oracle is expensive and imperfect, because deciding whether an open-ended answer is right costs a judge call or a human, so most of the craft is pushing that judgment down into cheap deterministic checks wherever the task lets you.

---

## Anatomy of an Automated Eval Pipeline

Every automated eval — whether built on promptfoo, DeepEval, LangSmith, Braintrust, Inspect, or hand-rolled — is the same seven components wired in a line. Learn the parts once and every tool is just a different spelling of them.

```
 TRIGGER ──▶ DATASET ──▶ HARNESS ──▶ GRADERS ──▶ GATE ──▶ REPORT ──▶ ALERT
 (PR /       (golden,     (run the    (score      (pass/   (HTML,     (Slack,
  merge /     versioned,   agent on    each        fail vs  JUnit,     PagerDuty
  cron /      sliced)      each row,   output:     baseline dashboard  on
  deploy)                  capture     exact,      +          link)    regression)
                           traces)     judge,      threshold)
                                       rubric)
```

**1. Trigger.** The event that starts a run. In CI this is a GitHub Actions `on:` clause: `pull_request` for PR gates, `schedule` (cron) for nightly runs, `workflow_dispatch` for manual, and `deployment` / post-merge for canary comparison. The trigger determines how much you can afford to run (see the CI/CD section). A subtle but important property: the trigger also sets the *comparison semantics*. A PR trigger compares the branch against `main`; a nightly compares today against a rolling baseline; a canary compares the new deployment against the previous one on live traffic. Same seven boxes, three different meanings of "regression."

**2. Dataset.** The set of inputs plus expected outputs (or grading criteria). This is your *golden dataset* — versioned, reviewed, and sliced by category. It is the single most valuable and most neglected asset in the pipeline. A gate is only as good as the examples it runs. Datasets have a lifecycle that people forget: they are *seeded* (from design docs and hand-written cases), *grown* (from real production failures promoted back in), *sliced* (by intent, language, difficulty, tool-required), and *versioned* (so a comparison is against a fixed ruler). A dataset with no lifecycle is a dataset that silently drifts — see the pitfalls section.

**3. Harness.** The code that actually invokes the agent on each dataset row and captures the output *and the trace* (tool calls, retrieved chunks, intermediate steps). For agents you almost always want the trace, because you grade tool-use and process, not just the final string. The harness is also where you enforce *isolation* — each row runs against a hermetic environment (mocked tools, a frozen retrieval index, a fixed clock) so that a failure means "the agent did the wrong thing," not "a downstream API was flaky today." An agent eval that hits live third-party APIs is measuring the internet's uptime as much as the agent's quality.

**4. Graders (scorers).** The functions that turn an output into a number. Three families, roughly in order of cost and flexibility:
   - **Deterministic / programmatic** — exact match, regex, JSON-schema validity, `contains`, numeric tolerance, tool-call assertions, SQL execution equivalence. Free, instant, zero variance. Use them for everything you can. The single highest-leverage move in the whole pipeline is *converting a judged criterion into a deterministic one* — e.g. instead of asking a judge "did it use the right tool?", assert on the captured tool-call trace.
   - **Model-graded (LLM-as-judge)** — a second model scores groundedness, helpfulness, or rubric adherence. Flexible, but slow, costly, and *itself noisy*. Judges have their own failure modes: position bias (favoring the first answer shown), verbosity bias (favoring longer answers), self-preference (favoring their own family's outputs), and drift when the provider updates them.
   - **Reference / embedding** — semantic similarity to a gold answer, NLI-based entailment for faithfulness. Cheaper and lower-variance than a full judge, but blunt: high cosine similarity to the gold answer does not guarantee correctness, and a correct paraphrase can score low.

**5. Gate.** The decision logic that turns per-example scores into a single **pass or fail** for the run. This is where thresholds, baselines, and statistical tests live. The gate is what makes the pipeline a *gate* and not a dashboard. The distinction is everything: a dashboard informs, a gate *blocks*. Teams routinely build beautiful dashboards, look at them never, and ship regressions anyway. The gate is the part that consumes attention only when something is wrong — which is the only sustainable way to spend a team's attention.

**6. Report.** The human-readable artifact: an HTML diff of this run vs baseline, a JUnit XML the CI renders as test results, a link to a hosted experiment. When the gate fails, the report is how a human finds out *why* in under a minute. The design test for a report: when a gate fails at 4:55pm on a Friday, can the on-call engineer see *which slice*, *which examples*, and *by how much* without cloning the repo? If not, the report is decoration.

**7. Alert.** The push notification when a gate fails on a protected branch or a nightly run regresses — Slack webhook, PagerDuty, GitHub check annotation. Without this, nightly failures are discovered three days later. A PR gate is *self-alerting* (the author is staring at the red check); a nightly gate is *not* (everyone is asleep), which is exactly why the alert box matters most for the runs nobody is watching.

Everything in the rest of the chapter is a decision about one of these seven boxes.

> **Saying it out loud.** Every eval pipeline is the same seven boxes — trigger, dataset, harness, graders, gate, report, alert — and every tool you can name is just a different spelling of those seven. The box teams underinvest in is the dataset, and the box they confuse is the gate: a dashboard informs, a gate blocks, and plenty of teams build a beautiful dashboard, look at it never, and ship the regression anyway. The harness matters more than it sounds, because that's where you capture the trace and not just the final string — for an agent you're grading tool calls and process, not the last paragraph. It's also where you enforce hermeticity, and if your eval hits live third-party APIs you're measuring the internet's uptime as much as the agent's quality. The failure mode worth naming: a "flaky agent" is very often just a leaky harness.

---

## The 2025–2026 Landscape: Eval-in-CI as It Actually Exists Today

By 2026 "run your evals in CI" has gone from a novel idea to table stakes, and a clear tool ecosystem has settled out. You will be expected in an interview to name the players, know what shape each one is, and have an opinion about when to reach for which. This section maps the landscape as it stands, with primary sources you can cite.

> **Saying it out loud.** As of mid-2026 — and I'd date that claim, because this layer moves fast — eval-in-CI is table stakes and the tool list has settled into about five names. promptfoo if your unit of change is a prompt or a RAG config and you want YAML plus a PR comment; DeepEval if your team already lives in pytest; LangSmith or Braintrust if you want tracing and hosted experiment diffs sharing one data model; Inspect, from the UK AI Safety Institute, when you need benchmark-grade rigor. None of them is wrong — they're the same seven boxes with a different box made easy — so the real question is which box is your bottleneck. Most mature teams end up with two tools, and that's the tradeoff worth stating: buy the platform for tracing and triage UX, but own the gate math yourself, because that's the part you can't afford to have change under you.

### The tools, by shape

**promptfoo (declarative YAML + CLI + GitHub Action).** The most popular open-source "test your prompts like code" tool. You write a `promptfooconfig.yaml` describing providers, test cases, and `assert` blocks (deterministic checks, `llm-rubric` judges, similarity, latency/cost thresholds), and the CLI exits non-zero when assertions fail — which is all CI needs to block a merge. The official `promptfoo/promptfoo-action` posts a comment on the PR summarizing pass/fail and diffs against the base branch. It ships response caching out of the box (`PROMPTFOO_CACHE_PATH`), so re-runs on unchanged inputs are free. Docs: <https://www.promptfoo.dev/docs/integrations/ci-cd/> and <https://www.promptfoo.dev/docs/integrations/github-action/>; action source: <https://github.com/promptfoo/promptfoo-action>. Reach for it when your unit-of-change is a prompt or a RAG config and you want config-not-code plus red-teaming in the same tool.

**DeepEval (pytest-native).** Positions itself as "Pytest for LLMs." You write ordinary test functions, call `assert_test(test_case, metrics=[...])`, and run `deepeval test run test_file.py`; a metric scoring below its `threshold` raises and fails the build, exactly like a failing unit test. It ships 14+ research-backed metrics (answer relevancy, faithfulness, contextual precision/recall, hallucination, task completion, G-Eval custom rubrics) and drives from versioned `EvaluationDataset` goldens with `@pytest.mark.parametrize`. Docs: <https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd>; regression-testing guide: <https://deepeval.com/guides/guides-regression-testing-in-cicd>; 2025 changelog: <https://deepeval.com/changelog/changelog-2025>. Reach for it when your team already lives in pytest and wants eval-as-unit-test with batteries-included metrics.

**LangSmith + openevals (SDK + pytest/Vitest integration).** LangSmith gives you tracing, hosted datasets with versioning, and a `@pytest.mark.langsmith` decorator that syncs each test to a dataset example and records pass/fail as feedback; `--langsmith-output` renders a rich terminal table. In late 2024–2025 LangChain also open-sourced **openevals** (<https://github.com/langchain-ai/openevals>), a package of ready-made evaluators — LLM-as-judge correctness/conciseness/hallucination prompts, plus structured-output and trajectory evaluators for agents — that you can drop into any harness without buying the platform. Pytest integration: <https://docs.langchain.com/langsmith/pytest>; openevals overview: <https://www.langchain.com/blog/evaluating-llms-with-openevals>. Reach for this stack when you are already on LangChain/LangGraph and want tracing and eval to share one data model.

**Braintrust (`Eval()` SDK + hosted experiments).** A commercial platform built around the experiment-diff. You write `Eval("project", data=..., task=..., scorers=[...])`, and in CI it runs the experiment and auto-compares the candidate against a baseline experiment, surfacing per-example regressions in a side-by-side UI and failing the build via its GitHub integration. Its strength is the regression *review* experience — seeing exactly which rows moved and reading the two outputs next to each other. Docs: <https://www.braintrust.dev/docs/evaluate> and <https://www.braintrust.dev/docs/evaluate/compare-experiments>; their own 2025/2026 CI/CD tool survey is a useful landscape read: <https://www.braintrust.dev/articles/best-ai-evals-tools-cicd-2025>. Reach for it when regression triage across many experiments is your bottleneck and you will pay for UX.

**Inspect (UK AISI, Python framework).** `inspect_ai` from the UK AI Safety Institute is the framework the safety/evals research world standardized on. You define a `Task` (dataset + `solver` + `scorer`), run `inspect eval task.py --model ...`, and get a rich log viewer. It is less "gate my web-app PR" and more "run a rigorous, reproducible benchmark," but it runs cleanly in CI and its `inspect_evals` companion repo ships dozens of implemented benchmarks (GPQA, SWE-bench, agent tasks). Repo: <https://github.com/UKGovernmentBEIS/inspect_ai>; site: <https://inspect.aisi.org.uk/>; the `inspect_evals` benchmark suite: <https://ukgovernmentbeis.github.io/inspect_evals/> and the AISI announcement <https://www.aisi.gov.uk/blog/inspect-evals>. Reach for it when you need benchmark-grade rigor, capability/safety evals, or interoperability with the research community.

**OpenAI Evals (open-source registry + `oaieval`).** The original YAML-registered eval registry; more oriented toward model-vs-model benchmarking than app-level regression gating, but still a valid CI citizen via its CLI. Docs: <https://github.com/openai/evals/blob/main/docs/run-evals.md>.

### How they all agree (and where they differ)

Every one of these tools is the same seven boxes from the Anatomy section — they differ only in *which box they make easy*:

| Tool | Native shape | Makes easy | Weakest box | CI exit mechanism |
|---|---|---|---|---|
| promptfoo | YAML + CLI | Dataset + assertions + red-team, PR comment | Complex agent harnesses | CLI non-zero exit; PR-comment action |
| DeepEval | pytest | Graders (14+ metrics), eval-as-unit-test | Hosted reporting (needs Confident AI) | `assert_test` raises |
| LangSmith/openevals | SDK + pytest | Trace + dataset + graders in one model | Config-only (needs code) | pytest fail; feedback tracked |
| Braintrust | `Eval()` SDK | Report + regression diff review | Fully offline/air-gapped use | GitHub check via platform |
| Inspect | Python `Task` | Harness + scorer rigor, reproducibility | App-level "gate my PR" ergonomics | non-zero on scorer thresholds |
| Custom pytest | Hand-rolled | The gate math (you own it) | Everything you don't build | plain `assert` |

The interview-ready summary: **promptfoo for config-first prompt/RAG gates, DeepEval for pytest-native metric gates, LangSmith/Braintrust when you want the hosted trace+experiment platform, Inspect for benchmark-grade rigor, and hand-rolled pytest when you need to own the statistical gate exactly.** Nobody is wrong; they are optimizing different boxes.

### Nondeterminism in 2025–2026: the story got sharper

The most important *conceptual* development of 2025 for anyone gating on LLM output is a crisp answer to "why is inference nondeterministic even at temperature 0?" The folk explanation — "floating-point addition is non-associative and GPU concurrency reorders it" — turns out to be only half right. In September 2025, Horace He and colleagues at **Thinking Machines Lab** published *Defeating Nondeterminism in LLM Inference* (<https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/>, 2025-09-10), arguing the *primary* cause is **lack of batch invariance**: server-side batch size varies with concurrent load, and common kernels (RMSNorm, matmul, attention) produce subtly different reductions at different batch sizes. Because you do not control how many other requests are batched with yours, your "identical" request is silently computed differently run to run. With batch-invariant kernels they drove 1000 completions to be bit-identical where stock vLLM produced 80 distinct outputs. Simon Willison's write-up is a good short summary (<https://simonwillison.net/2025/Sep/11/defeating-nondeterminism/>), and LMSYS shipped deterministic-inference support in SGLang shortly after (<https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/>). There is also a solid arXiv treatment of the numerical sources (<https://arxiv.org/html/2506.09501v2>).

Why this matters for *your* gate: it explains, with a citation, why pinning `temperature=0` and a `seed` is necessary but **not sufficient** to make a hosted endpoint reproducible — you are a tenant on shared, load-dependent batching you do not control. That is the empirical justification for the whole statistical apparatus later in this chapter: you cannot pin your way to determinism against a multi-tenant endpoint, so you must *quantify and gate on the residual noise* instead of pretending it away. In an interview, being able to name the batch-invariance result and draw the correct conclusion ("so I gate on a confidence bound, not a point estimate") is a strong signal.

> **Saying it out loud.** The interesting update is *why* inference is nondeterministic even at temperature zero. The folk answer — floating-point addition isn't associative and GPUs reorder things — turns out to be only half right; the Thinking Machines Lab result from September 2025 argues the dominant cause is lack of batch invariance. Server-side batch size varies with how many other people are hitting the endpoint, and kernels like RMSNorm, matmul and attention reduce slightly differently at different batch sizes, so your "identical" request is genuinely computed differently run to run and you don't control the batch. With batch-invariant kernels they got a thousand completions to come out bit-identical, where stock vLLM had produced eighty distinct outputs. The conclusion that scores in an interview: pinning temperature and seed is necessary but not sufficient on a multi-tenant endpoint, so you gate on a confidence bound instead of pretending you pinned your way to determinism.

### Cost control in 2025–2026: the norms that settled

The community converged on a small set of cost patterns that are now considered baseline competence:

- **Deterministic-first, judge-last (the cascade).** Run free programmatic checks on every row; only escalate the ambiguous residue to an LLM judge. Widely reported as roughly an order-of-magnitude cost reduction on the hot (PR) tier.
- **Response caching keyed on (prompt, input, model version).** Standard in promptfoo, easy to add anywhere; turns most CI re-runs into $0 runs. The subtlety everyone learns once: your cache key **must** include the model version, or a provider rollout serves you stale cached outputs and hides a regression.
- **Small-model judges, validated against a frontier judge before trust.** Using a cheap model to judge is fine *if* you have measured its agreement with the expensive judge and with humans on your task; blind substitution is how judge drift sneaks in.
- **Tiering (PR-smoke vs nightly-full).** The dollars live in nightly, not on every commit. This is now the default architecture, not a clever optimization.
- **Per-run token/cost ceilings.** A hard abort-and-alert if a single run exceeds a dollar budget, as insurance against an agent stuck in a tool-call loop burning tokens.

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

There is a fourth tier worth naming because interviewers probe for it: the **pre-merge / merge-queue full eval**. Some teams run the small suite on every push but gate the *actual merge* (via a merge queue like GitHub's) on a medium suite, so the expensive-ish run happens once per merge rather than once per commit. This is the sweet spot for teams whose PRs get many commits: you get fast per-commit feedback and a more rigorous check exactly at the moment of merge, without paying for the big suite on every `git push`.

> **Saying it out loud.** There's a triangle here — cheap, fast, statistically significant — and you get two. Thirty examples in forty seconds for twelve cents is cheap and fast and has so much variance it can't detect a real regression; two thousand judged examples is significant and costs dollars and tens of minutes. You don't resolve that on one run, you resolve it by tiering: a small, mostly-deterministic, path-scoped smoke suite on every PR in under three minutes, a five-hundred-to-two-thousand-example judge sweep nightly while everyone's asleep, and a canary on one to five percent of live traffic for the distribution you can't simulate offline. The design rule is that the PR gate has to be fast enough that engineers never learn to hate it, because the moment they do, they start skipping CI. And the tradeoff to name out loud: path-scoping is a cost optimization, not a safety guarantee — scope the PR tier for speed, never scope nightly, or a cross-cutting change walks right past the filter.

### Why the PR gate must stay deterministic-heavy

An LLM judge on every PR is a trap: it is slow, it costs money on every commit (and engineers commit dozens of times a day), and it *adds its own noise* to a signal you are trying to keep clean. The high-leverage move is a **classifier cascade** — run cheap deterministic and small-classifier rubrics on all PR examples first, and only escalate the handful of low-confidence cases to an expensive frontier judge. Reported effect is roughly a 10x cost reduction on the PR tier without losing signal. Reserve the full judge sweep for nightly.

A second reason to keep the PR gate deterministic-heavy is *psychological*, and it matters more than the cost: a deterministic check that fails means "you broke something," full stop, and the author fixes it. A judge-based check that fails means "a model thinks you might have made something slightly worse," which invites argument, re-runs, and eventually cynicism. The PR gate's entire value is that engineers *believe its red*. Every noisy judge you add to the hot path spends down that belief.

> **Saying it out loud.** Putting an LLM judge on every PR is a trap, and the reason is psychological before it's financial. A deterministic check going red means "you broke something," full stop, and the author just fixes it. A judge going red means "a model thinks you might have made this slightly worse," which invites argument, re-runs, and eventually cynicism — and the PR gate's entire value is that people believe its red. The money argument is real too: a classifier cascade, where free programmatic checks run on every row and only the low-confidence residue escalates to a frontier judge, is reported at roughly a 10x cost cut on the PR tier. So judges live in nightly and the hot path stays deterministic, which keeps it both cheap and trusted.

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

A caution that has bitten many teams: **path filters are a cost optimization, not a safety guarantee.** If your prompt lives in `prompts/**` but a change to `src/util/formatting.py` alters how outputs get post-processed, a path-scoped gate will happily skip the eval and let a regression through. The rule of thumb: path-scope the *PR* tier for speed, but never path-scope the *nightly* tier — nightly runs the whole suite regardless of what changed, precisely to catch the cross-cutting change the path filter missed.

---

## Handling Nondeterminism and Flakiness Rigorously

This is the section that separates a gate people trust from a gate people route around. LLM outputs vary run to run for reasons that are mostly *not* your bug: sampling temperature, provider-side model updates, and — as the 2025 Thinking Machines work made precise — **batch-size-dependent kernel non-invariance** on shared inference endpoints (a genuine, documented source of nondeterminism even at temperature 0; see the landscape section). If you gate on a single sample against a hard threshold, your gate will flip red on noise, engineers will hit "re-run" until it passes, and the gate is now theater.

The mental model to internalize: **your suite-level score is a random variable, not a number.** Every time you run it you draw one sample from a distribution. The whole job of rigorous gating is to reason about that distribution — its mean, its spread, and whether the mean plausibly sits below your bar — rather than treating a single draw as ground truth. Everything below is that idea, operationalized.

Handle it with four (really five) layers, in order:

> **Saying it out loud.** The one sentence to internalize is that your suite-level score is a random variable, not a number — every run is a single draw from a distribution, and the job is to reason about that distribution instead of treating one draw as ground truth. You attack it in layers: cut variance at the source by pinning the exact dated model version and temperature and freezing the retrieval index and tools; sample each case three to five times and aggregate; gate on a confidence bound rather than the point estimate; require regressions to be both significant and meaningful; and quarantine what's irreducibly flaky. Pick the aggregation to match the product question, because pass@k and pass^k encode opposite risk attitudes — "can it ever" is right when a human can retry, "does it succeed every single time" is right for autonomous actions nobody reviews. The failure mode this whole section exists to prevent is the gate that cries wolf: once red means nothing, people re-run until green and a real regression strolls through.

### 1. Reduce variance at the source

- **Pin what you can.** Set `temperature=0` (or a fixed `seed` where the provider honors it) for gradeable tasks; pin the exact model version string (`gpt-4o-2024-08-06`, not `gpt-4o`) so a provider rollout is a *reviewed* change, not a surprise.
- **Understand the ceiling.** Per the batch-invariance result, pinning temperature and seed reduces but does **not eliminate** variance on a multi-tenant hosted endpoint, because you do not control the server-side batch your request lands in. If you truly need bit-reproducibility (e.g. for RL training or a legal-grade audit), you need a deterministic-inference stack (SGLang's deterministic mode, batch-invariant kernels) — not just `temperature=0`. For ordinary app eval, accept the residual and quantify it with the next layers.
- **Freeze the environment around the model.** Fixed retrieval index snapshot, mocked tool responses, a pinned clock/seed for any randomness in your own code. A surprising amount of "LLM flakiness" is actually your harness leaking real-world entropy into the test.

### 2. Sample multiple times, gate on the aggregate

Run each example \(k\) times (typically \(k = 3\) to \(5\)) and aggregate. For a per-example pass/fail, use **majority vote** or **pass@k / pass^k** depending on whether you care about "can it ever" or "does it reliably." The suite-level metric becomes the mean of a many-Bernoulli process, whose noise you can *quantify* — which unlocks layer 3.

Choose the aggregation to match the product question, because they encode opposite risk attitudes:
- **pass@k** ("succeeds at least once in k tries") is optimistic — right for "can a human retry?" surfaces like code generation with a test the user can re-run.
- **pass^k / all-of-k** ("succeeds every one of k tries") is pessimistic — right for autonomous, no-human-in-the-loop actions where one failure ships to a customer.
- **majority-vote@k** is the balanced default for a quality gate: it smooths a single unlucky sample without hiding a genuinely 50/50 case.
Reporting the wrong one flatters or maligns the agent unfairly, and a sharp interviewer will ask which you used and why.

### 3. Gate on a statistical bound, not a point estimate

> **In plain terms.** Instead of asking "did we score above 85%?", ask "given how few examples we ran, could the true rate actually be below 85%?" The formula below turns an observed pass rate into a range the true rate plausibly lives in, and you compare the bottom of that range to your bar. A small sample gives a wide range, so an unlucky run doesn't flip the gate — it honestly reports that you don't have enough examples to conclude anything.

Do not compare a raw mean to a threshold. Compare a **confidence bound** to the threshold. If your suite of \(n\) examples has \(s\) successes, the point estimate is \(\hat{p} = s/n\), but the honest question is "given noise, could the *true* success rate be below my bar?" Use the lower bound of a binomial confidence interval. The **Wilson score interval** is the right default (it behaves near 0 and 1 where the naive normal interval breaks):

\[
\hat{p}_{\pm} = \frac{\hat{p} + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}
\]

with \(z = 1.96\) for 95% confidence. **Gate on the lower bound** \(\hat{p}_{-} \ge \text{threshold}\): you only fail the build when you are statistically confident the true rate is below the bar. This directly kills "small sample, unlucky run" flakiness — and it tells you when your dataset is simply *too small* to conclude anything (the interval is wide).

Worth building intuition for the numbers, because interviewers love a concrete feel: at \(\hat{p} = 0.90\), the Wilson lower bound is roughly **0.74 at n=30**, **0.82 at n=100**, **0.87 at n=500**, and **0.88 at n=1000**. Read that as: to *prove* you cleared a 0.85 bar with 95% confidence, you need on the order of hundreds of trials, not thirty. This is the mathematical reason the PR tier (small n) cannot gate on tight quality deltas and the nightly tier (large n) can — it is not a matter of taste, it is the width of the interval.

> **Saying it out loud.** The punchline is that you never compare a raw mean to a threshold; you compare a confidence bound to the threshold. The observed pass rate is just a point estimate with sampling noise in it, so you compute the Wilson lower bound and fail the build only when that bound is below the bar — meaning you're statistically confident the true rate is genuinely under it, not that you had a bad night. Wilson rather than the naive normal interval because it behaves properly near zero and one, which is exactly where good agents live. The numbers give you the intuition: at an observed 90%, the lower bound is about 0.74 at thirty examples, 0.82 at a hundred, and 0.87 at five hundred. So proving you cleared an 0.85 bar with 95% confidence takes hundreds of trials, not thirty — that's the mathematical reason the PR tier can't gate tight quality deltas and the nightly tier can.

### 4. For regressions, require a significant *and* meaningful drop

> **In plain terms.** This is one rule with three parts: the score has to have gone down, the drop has to be unlikely to be noise, and it has to be big enough that anyone would care. All three have to be true before the build fails.

When comparing a candidate to a baseline, a naive "mean went down → fail" fires constantly on judge noise. The rigorous gate is a conjunction of three conditions:

\[
\text{FAIL} \iff (\text{mean dropped}) \;\wedge\; (\underbrace{p < 0.05}_{\text{Welch's t-test}}) \;\wedge\; (\underbrace{\Delta > \delta_{\min}}_{\text{effect floor}})
\]

That is: the mean must drop, the drop must be statistically significant (Welch's t-test on the per-example score arrays — not just the means), **and** the drop must exceed a minimum effect size you actually care about. Requiring all three prevents the two failure modes at once: significant-but-trivial drops (a 0.3% dip with a huge sample) and large-but-noisy drops (a 5% dip on 12 examples).

Why **Welch's** t-test specifically and not Student's: Welch does not assume the two runs have equal variance, and eval runs frequently *don't* — a prompt change can make the agent both worse on average and more erratic. Welch is the safe default; using Student's here is a subtle correctness bug that inflates false positives when variances differ. For paired designs (same examples, same seeds, before and after) a **paired** test or bootstrap over per-example deltas is even more powerful, because it removes the example-difficulty variance that dominates the unpaired comparison. If you can pin seeds so the same rows are comparable across runs, pair them — it can shrink the number of examples you need by a large factor.

> **Saying it out loud.** "The mean went down, so fail" is the naive gate, and it fires constantly on judge noise. The rigorous version is a conjunction: the mean dropped, the drop is significant under a Welch's t-test on the per-example score arrays, and the drop exceeds a minimum effect size you actually care about. Requiring all three kills both failure modes at once — the significant-but-trivial 0.3-point dip on a huge sample, and the big-but-noisy 5-point dip on twelve examples. Welch specifically, not Student's, because eval runs frequently have unequal variance: a prompt change can make an agent both worse on average and more erratic, and using Student's there quietly inflates false positives. And if you can pin seeds so the same rows are comparable across runs, pair the test or bootstrap the per-example deltas — that removes example-difficulty variance and can cut the sample size you need by a large factor.

### 5. Quarantine, don't ignore

Some examples are irreducibly flaky (ambiguous ground truth, judge disagreement). Tag them `@flaky` and move them to a **quarantine suite** that runs and reports but does *not* block the merge. This keeps the main gate green and trustworthy while preserving the signal. The discipline: a test in quarantine is a bug ticket, not a graveyard — review the quarantine list every sprint or it becomes a place tests go to die.

A concrete quarantine policy that works: an example auto-enters quarantine when its *flip rate* (fraction of recent runs where it changed pass/fail with no code change) exceeds a threshold, say 10% over the last 20 nightly runs. It auto-exits when either the underlying ambiguity is fixed (someone tightens the grader or the ground truth) or it stabilizes on its own. Crucially, **the size of the quarantine is itself a monitored metric** — a growing quarantine means your graders or dataset are decaying, and if half your suite is quarantined your gate is mostly decorative. Alert when quarantine exceeds, say, 5% of the suite.

> **Saying it out loud.** Some examples are irreducibly flaky — ambiguous ground truth, a judge that disagrees with itself — and the right move is to quarantine them rather than delete them or tolerate them. Tag them, run them, report them, but never let them block a merge, so the main gate stays green and trustworthy while you keep the signal. Make the policy mechanical: auto-quarantine anything whose flip rate exceeds about 10% over the last twenty nightly runs, and auto-exit when it stabilizes or someone tightens the grader. The trap is that quarantine becomes a graveyard, so treat its size as a monitored metric and alert past roughly 5% of the suite — a bloated quarantine means your graders or your dataset are decaying and the gate is going hollow.

---

## Regression Detection: Baselines, Thresholds, Slices

A gate needs something to compare against. Two philosophies, usually combined:

**Absolute floors.** Fixed thresholds that encode a non-negotiable quality bar: groundedness ≥ 0.85, JSON-validity = 1.0, tool-selection accuracy ≥ 0.90. These catch *catastrophic* failures — a prompt edit that breaks structured output entirely. They live in version control and change only via reviewed PR.

**Relative / delta gates.** Compare the candidate to a **rolling baseline** — typically the score of `main` over the last N days, stored as a checked-in JSON so a threshold change shows up as a reviewed diff. These catch *slow drift*: a series of individually-innocent prompt tweaks that each drop quality 0.5% until you have lost ten points and nobody noticed. The delta gate uses the significant-and-meaningful conjunction from the previous section.

**Per-slice regression is the one people miss.** Your aggregate success rate can be flat while a subpopulation collapses. Overall 92% → 91% looks fine; hidden inside it, the `refund` intent went 95% → 70% and the `spanish_language` slice went 88% → 60%, masked by the `faq` slice getting easier. **Always gate per slice, not just on the mean.** Break the dataset into categories (intent, language, difficulty, tool-required-vs-not) and apply the regression test to each. A per-slice gate is the difference between "we shipped a small overall dip" and "we shipped a total outage for Spanish-speaking refund requests."

The tension per-slice gating creates — and how to resolve it — is a favorite interview follow-up: **more slices means more independent tests, which means more chances for one to fail on noise** (the multiple-comparisons problem). Naively gating on "any slice regressed at p<0.05" with 20 slices gives you roughly a 64% chance of at least one false alarm per run even when nothing changed. Resolve it by (a) requiring a *meaningful* effect floor per slice, not just significance; (b) applying a multiple-comparison correction (Benjamini–Hochberg to control false-discovery rate is more appropriate here than the overly conservative Bonferroni); and (c) keeping slices coarse enough that each has enough examples to say anything — a slice with 6 examples cannot regress "significantly" and only adds noise. A slice needs a minimum n (say 30) to be gate-eligible; below that it reports but does not block.

Practical baseline hygiene:
- Store baselines as a **reviewed artifact** (JSON in the repo, or a named experiment in Braintrust/LangSmith), never as "whatever `main` happened to score today."
- **Promote** a candidate's scores to the new baseline only after it merges — so the ratchet moves forward.
- Keep the baseline **dataset version** pinned alongside the scores; comparing scores across two different dataset versions is meaningless (see silent dataset drift, below).
- Use a **rolling window** (median of the last N nightly runs) rather than a single previous run as the baseline, so one lucky or unlucky night does not become the ruler everything else is measured against. The median of the last 7 nights is robust to a single outlier in a way that "yesterday's score" is not.

> **Saying it out loud.** You need two kinds of comparison and you use both. Absolute floors encode the non-negotiable bar — JSON validity is 1.0, tool selection at least 0.9 — and they catch the catastrophic break. Relative delta gates against a rolling baseline catch slow drift: ten individually-innocent half-point prompt tweaks that add up to ten lost points nobody noticed. The thing most people miss is per-slice gating — overall 92% to 91% looks fine while the refund intent went 95 to 70 and the Spanish slice went 88 to 60, masked by the FAQ slice getting easier. But slicing has a price: twenty slices tested at p below 0.05 gives you roughly a 64% chance of at least one false alarm per run even when nothing changed, so you add a per-slice effect floor, use Benjamini–Hochberg rather than the overly conservative Bonferroni, and require a minimum slice size — around thirty — before a slice is allowed to block anything. And baseline against the median of the last seven nights, not yesterday, so one unlucky run doesn't become the ruler.

---

## Build It in Practice: A Complete, Runnable CI Eval Setup

Theory is cheap. This section is a realistic, correct, copy-adaptable setup: a pytest eval that gates a build on a success-rate threshold with a Wilson lower bound; a Welch's-test regression gate against a baseline; a per-slice floor; flaky-test quarantine; and the GitHub Actions workflows that wire PR-smoke and nightly-full triggers. Every code block here is written to actually run, not to gesture.

### The statistical core: `evals/stats.py`

Isolate the gate math in one reviewed, unit-tested module. This is the single most important file to get *provably* right — everything else trusts it.

```python
"""Statistical primitives for eval gating. Pure functions, unit-tested,
no I/O. Keeping the gate math here means it can be reviewed and tested in
isolation from the (noisy, slow) agent-running code."""
from __future__ import annotations
import math
from dataclasses import dataclass


def wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> float:
    """Lower bound of the Wilson score interval for a binomial proportion.

    Stable near p=0 and p=1 where the normal approximation fails. Gate on
    THIS, not the raw rate, so a small/unlucky sample cannot flake the build.
    z=1.96 -> 95% two-sided, i.e. a one-sided 97.5% lower bound.
    """
    if n == 0:
        return 0.0
    p = successes / n
    denom = 1.0 + z * z / n
    center = p + z * z / (2 * n)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)
    return (center - margin) / denom


@dataclass
class WelchResult:
    mean_a: float
    mean_b: float
    delta: float          # mean_b - mean_a  (candidate minus baseline)
    t: float
    df: float
    p_two_sided: float
    significant: bool


def _t_sf(t: float, df: float) -> float:
    """Survival function (1 - CDF) of Student's t via a regularized incomplete
    beta. Avoids a scipy dependency in CI; accurate enough for gating."""
    x = df / (df + t * t)
    # Regularized incomplete beta I_x(df/2, 1/2) via continued fraction.
    a, b = df / 2.0, 0.5
    return 0.5 * _betai(a, b, x)


def _betai(a: float, b: float, x: float) -> float:
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a
    # Lentz's algorithm for the continued fraction.
    f, c, d = 1.0, 1.0, 0.0
    for i in range(0, 300):
        m = i // 2
        if i == 0:
            num = 1.0
        elif i % 2 == 0:
            num = (m * (b - m) * x) / ((a + 2 * m - 1) * (a + 2 * m))
        else:
            num = -((a + m) * (a + b + m) * x) / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1e-30 if abs(d) < 1e-30 else d
        d = 1.0 / d
        c = 1.0 + num / c
        c = 1e-30 if abs(c) < 1e-30 else c
        f *= d * c
        if abs(1.0 - d * c) < 1e-10:
            break
    return front * (f - 1.0)


def welch_t_test(a: list[float], b: list[float]) -> WelchResult:
    """Two-sample Welch's t-test (unequal variances). `a` = baseline scores,
    `b` = candidate scores (per-example, aligned or not). We use Welch, not
    Student's, because a change can alter the variance, not just the mean."""
    na, nb = len(a), len(b)
    ma, mb = sum(a) / na, sum(b) / nb
    va = sum((x - ma) ** 2 for x in a) / (na - 1)
    vb = sum((x - mb) ** 2 for x in b) / (nb - 1)
    se = math.sqrt(va / na + vb / nb)
    if se == 0.0:
        t, df, p = 0.0, float(na + nb - 2), 1.0
    else:
        t = (mb - ma) / se
        df = (va / na + vb / nb) ** 2 / (
            (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
        p = 2.0 * _t_sf(abs(t), df)
    return WelchResult(ma, mb, mb - ma, t, df, p, p < 0.05)


def regression_fails(baseline: list[float], candidate: list[float],
                     min_effect: float = 0.02) -> tuple[bool, str]:
    """The three-condition regression gate: FAIL iff the mean dropped AND the
    drop is significant (Welch p<0.05) AND the drop exceeds the effect floor.
    Returns (fail, human_readable_reason)."""
    r = welch_t_test(baseline, candidate)
    dropped = r.delta < 0
    meaningful = abs(r.delta) >= min_effect
    fail = dropped and r.significant and meaningful
    reason = (f"delta={r.delta:+.3f} (cand {r.mean_b:.3f} vs base {r.mean_a:.3f}), "
              f"p={r.p_two_sided:.3f}, min_effect={min_effect}: "
              f"{'FAIL' if fail else 'pass'} "
              f"[dropped={dropped}, sig={r.significant}, meaningful={meaningful}]")
    return fail, reason
```

Note the deliberate choice to implement the t-distribution tail *without scipy*. In CI you want the gate to have the fewest possible dependencies, because a gate that fails to install is a gate that gets bypassed "just this once." If you already ship scipy, `scipy.stats.ttest_ind(a, b, equal_var=False)` is the one-liner equivalent — but ship the tests below either way.

### Unit-testing the gate math (yes, really)

The gate is code that can block a release; it deserves its own tests more than any prompt does. A gate with a sign error will either wave through every regression or block every green build — both catastrophic.

```python
"""evals/test_stats.py — unit tests for the GATE ITSELF. Fast, deterministic,
no model calls. Run in the same CI job before any agent eval."""
import math
from evals.stats import wilson_lower_bound, welch_t_test, regression_fails


def test_wilson_tightens_with_n():
    lb_small = wilson_lower_bound(27, 30)   # 0.90 on 30
    lb_big = wilson_lower_bound(900, 1000)  # 0.90 on 1000
    assert lb_small < lb_big                # more data -> tighter bound
    assert 0.70 < lb_small < 0.80
    assert 0.87 < lb_big < 0.89


def test_wilson_edge_cases():
    assert wilson_lower_bound(0, 0) == 0.0
    assert wilson_lower_bound(10, 10) < 1.0   # never claims certainty


def test_welch_detects_real_drop():
    base = [1.0] * 95 + [0.0] * 5     # 0.95
    cand = [1.0] * 70 + [0.0] * 30    # 0.70
    fail, reason = regression_fails(base, cand, min_effect=0.02)
    assert fail, reason


def test_welch_ignores_trivial_drop_on_huge_n():
    base = [1.0] * 5000 + [0.0] * 5000       # 0.500
    cand = [1.0] * 4990 + [0.0] * 5010       # 0.499  (significant, trivial)
    fail, _ = regression_fails(base, cand, min_effect=0.02)
    assert not fail                           # effect floor saves us


def test_welch_ignores_noisy_drop_on_tiny_n():
    base = [1, 1, 1, 1, 0, 1, 1, 1, 1, 1]     # 0.9 on 10
    cand = [1, 0, 1, 1, 0, 1, 1, 1, 1, 1]     # 0.8 on 10 (not significant)
    fail, _ = regression_fails(base, cand, min_effect=0.02)
    assert not fail                           # significance floor saves us
```

Those last two tests encode the entire philosophy of the regression gate: it must ignore both the trivial-but-significant drop and the large-but-noisy drop. If you only remember one thing about building these gates, remember that you can and should unit-test them with synthetic score arrays, no model required.

### The gating eval: `evals/test_booking_agent.py`

This is a complete, correct pattern: run an agent over a versioned golden dataset, sample each case k times to average out nondeterminism, enforce a per-slice floor, and gate the build on the Wilson lower bound clearing a threshold — plus an optional regression gate against a checked-in baseline. Flaky cases are read from a quarantine file and reported-but-not-blocked.

```python
"""Automated eval that gates CI on a statistically-sound success rate.

Run locally:      pytest evals/test_booking_agent.py -v -m eval
Run in CI:        same command; a failing assert fails the build.
Nightly (delta):  EVAL_MODE=nightly pytest evals/test_booking_agent.py -m eval
"""
import json
import os
from pathlib import Path

import pytest

from src.agent import booking_agent          # the system under test
from src.graders import grade_booking         # deterministic grader -> bool
from evals.stats import wilson_lower_bound, regression_fails

# ---- Config: absolute floor + statistical rigor knobs --------------------
SUCCESS_THRESHOLD = 0.90          # absolute quality bar (Wilson LB must clear)
SLICE_FLOOR = 0.75                # no subpopulation may collapse below this
SAMPLES_PER_CASE = 3              # repeat each case to average out noise
MODE = os.environ.get("EVAL_MODE", "pr")     # "pr" (fast) or "nightly" (delta)
BASELINE_PATH = "evals/baseline/booking_v3.json"
QUARANTINE_PATH = "evals/quarantine.txt"


def load_golden(path: str = "evals/data/booking_golden_v3.jsonl") -> list[dict]:
    """Load the versioned golden dataset. The version is IN THE FILENAME so a
    dataset change is an explicit, reviewable diff — never a silent swap."""
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    assert rows, "golden dataset is empty — refusing to run a meaningless gate"
    return rows


def load_quarantine() -> set[str]:
    """Case IDs that are irreducibly flaky: they run and report but never block.
    Quarantine is a tracked bug list, not a graveyard — reviewed every sprint."""
    p = Path(QUARANTINE_PATH)
    if not p.exists():
        return set()
    return {l.strip() for l in p.read_text().splitlines()
            if l.strip() and not l.startswith("#")}


GOLDEN = load_golden()
QUARANTINED = load_quarantine()


@pytest.mark.eval
def test_booking_success_rate():
    """Run every golden case SAMPLES_PER_CASE times, grade deterministically,
    enforce a per-slice floor, then gate on the Wilson lower bound. In nightly
    mode also run the three-condition regression gate vs the checked-in baseline."""
    successes, trials = 0, 0
    per_slice: dict[str, list[int]] = {}
    per_case_scores: dict[str, list[int]] = {}   # for baseline & regression
    quarantined_flips = 0

    for row in GOLDEN:
        cid = row["id"]
        for _ in range(SAMPLES_PER_CASE):
            output = booking_agent.run(row["input"])          # capture output
            ok = int(grade_booking(output, row["expected"]))  # deterministic
            per_case_scores.setdefault(cid, []).append(ok)
            if cid in QUARANTINED:
                quarantined_flips += (0 if ok else 1)         # report, don't block
                continue
            successes += ok
            trials += 1
            per_slice.setdefault(row["slice"], []).append(ok)

    rate = successes / trials if trials else 0.0
    lower = wilson_lower_bound(successes, trials)

    # ---- Report (prints to CI log; also emit JSON for the dashboard) ------
    report = {
        "mode": MODE, "success_rate": rate, "wilson_lower_bound": lower,
        "trials": trials, "threshold": SUCCESS_THRESHOLD,
        "quarantined_cases": len(QUARANTINED), "quarantined_flips": quarantined_flips,
        "slices": {s: sum(v) / len(v) for s, v in per_slice.items()},
        # flat per-example arrays let a future run diff against this as a baseline
        "scores": {c: v for c, v in per_case_scores.items()},
    }
    print(f"[{MODE}] success_rate={rate:.3f} wilson_lb={lower:.3f} "
          f"n={trials} threshold={SUCCESS_THRESHOLD} "
          f"quarantined={len(QUARANTINED)}")
    Path("eval_report.json").write_text(json.dumps(report, indent=2))

    # ---- Per-slice floor: aggregate can hide a collapsed subpopulation ----
    collapsed = []
    for slice_name, results in per_slice.items():
        if len(results) < 30:        # too small to gate on; report only
            continue
        s_rate = sum(results) / len(results)
        if s_rate < SLICE_FLOOR:
            collapsed.append(f"{slice_name}={s_rate:.2f}")
    assert not collapsed, (
        f"slice floor {SLICE_FLOOR} breached: {', '.join(collapsed)} "
        f"— a subpopulation collapsed even though overall looks fine")

    # ---- Nightly-only: three-condition regression gate vs baseline --------
    if MODE == "nightly" and Path(BASELINE_PATH).exists():
        base = json.loads(Path(BASELINE_PATH).read_text())
        # flatten to per-example score arrays, matched on case id
        base_arr, cand_arr = [], []
        for cid, cand_scores in per_case_scores.items():
            if cid in base["scores"]:
                base_arr.extend(base["scores"][cid])
                cand_arr.extend(cand_scores)
        if base_arr and cand_arr:
            fail, reason = regression_fails(base_arr, cand_arr, min_effect=0.02)
            print(f"[nightly] regression check: {reason}")
            assert not fail, f"regression vs baseline: {reason}"

    # ---- The absolute gate: fail ONLY when confident TRUE rate is low -----
    assert lower >= SUCCESS_THRESHOLD, (
        f"Wilson lower bound {lower:.3f} < threshold {SUCCESS_THRESHOLD}. "
        f"Point estimate was {rate:.3f} over {trials} trials. Either quality "
        f"regressed, or the dataset is too small to prove it met the bar.")
```

Four properties make this gate trustworthy rather than flaky:

- It gates on `wilson_lower_bound`, so an unlucky run on a small sample produces a wide interval and a *clear* failure message ("too small to prove it met the bar") instead of a random red X. Grow the dataset and the interval tightens.
- It enforces a **per-slice floor** (with a minimum-n guard) before the aggregate gate, so a collapsed subpopulation fails loudly even when the overall mean looks healthy — without letting a 6-example slice flake the build.
- **Quarantined cases run and report but never block**, so irreducible ambiguity does not hold the release hostage, yet you still see the signal (`quarantined_flips`).
- In nightly mode it adds the **three-condition regression gate**, matched per-case against a checked-in baseline, so slow drift gets caught where you can afford the statistical power.

### Promoting the baseline: `evals/promote_baseline.py`

The ratchet only moves if you promote the new scores *after* a merge to `main`. Do this in a post-merge job, never on a branch, so the baseline is always "what main actually scored," reviewed via the merge itself.

```python
"""Promote the latest eval_report.json to the checked-in baseline. Runs in a
post-merge (push to main) job only. Commits the baseline so a threshold/ruler
change is always a reviewable diff, never an in-place mutation."""
import json, shutil, sys
from pathlib import Path

REPORT = Path("eval_report.json")
BASELINE = Path("evals/baseline/booking_v3.json")

if not REPORT.exists():
    sys.exit("no eval_report.json to promote")

report = json.loads(REPORT.read_text())
# Refuse to promote a baseline that itself failed the bar — never ratchet down.
if report["wilson_lower_bound"] < report["threshold"]:
    sys.exit(f"refusing to promote: wilson_lb {report['wilson_lower_bound']:.3f} "
             f"< threshold {report['threshold']}")
BASELINE.parent.mkdir(parents=True, exist_ok=True)
shutil.copy(REPORT, BASELINE)
print(f"promoted baseline -> {BASELINE}")
```

### PR-smoke workflow: `.github/workflows/pr-eval.yml`

Fast, path-scoped, deterministic-heavy, cancels stale runs, always uploads the report.

```yaml
name: PR Smoke Eval
on:
  pull_request:
    paths: ["prompts/**", "src/**", "evals/**"]

concurrency:
  group: pr-eval-${{ github.ref }}
  cancel-in-progress: true          # a new push cancels the stale run

jobs:
  gate-math:                        # the gate's own unit tests, first & free
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: pytest evals/test_stats.py -v      # deterministic, no model calls

  eval:
    needs: gate-math                # never run the slow eval if the math is broken
    runs-on: ubuntu-latest
    timeout-minutes: 10             # a hung judge must not block merges forever
    env:
      EVAL_MODE: pr
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      PROMPTFOO_CACHE_PATH: ~/.cache/eval
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }

      - name: Restore eval response cache      # unchanged inputs -> $0 re-runs
        uses: actions/cache@v4
        with:
          path: ~/.cache/eval
          # cache key MUST include the model version, or a provider rollout
          # serves stale outputs and hides a regression.
          key: eval-${{ vars.MODEL_VERSION }}-${{ hashFiles('prompts/**', 'evals/data/**') }}

      - run: pip install -r requirements.txt
      - name: Run gating eval (PR tier)
        run: pytest evals/test_booking_agent.py -v -m eval

      - name: Publish eval report            # surface numbers even on failure
        if: always()
        uses: actions/upload-artifact@v4
        with: { name: eval-report-pr, path: eval_report.json }
```

The `if: always()` on the report upload is the detail people forget: when the gate fails, that is *exactly* when you most need the numbers, so the report must be produced on failure too. The `gate-math` job running first is a cheap insurance policy: if someone breaks `stats.py`, you find out in five seconds from a deterministic unit test, not from a mysteriously-always-green eval.

### Nightly-full workflow: `.github/workflows/nightly-eval.yml`

Big suite, full judge sweep, regression gate, and — critically — an **alert** on failure, because nobody is watching at 02:00.

```yaml
name: Nightly Full Eval
on:
  schedule:
    - cron: "0 2 * * *"            # 02:00 UTC daily
  workflow_dispatch: {}            # allow manual "run it now"

jobs:
  eval:
    runs-on: ubuntu-latest
    timeout-minutes: 60
    env:
      EVAL_MODE: nightly
      OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
      MAX_RUN_COST_USD: "25"       # abort-and-alert insurance vs runaway agents
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt

      - name: Run full eval + regression gate
        id: run
        run: pytest evals/test_booking_agent.py -v -m eval

      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with: { name: eval-report-nightly, path: eval_report.json }

      - name: Alert on failure          # the box people forget for cron runs
        if: failure()
        uses: slackapi/slack-github-action@v2
        with:
          webhook: ${{ secrets.SLACK_EVAL_WEBHOOK }}
          webhook-type: incoming-webhook
          payload: |
            {"text": ":rotating_light: Nightly eval FAILED on main — regression or floor breach. Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"}
```

### Post-merge baseline promotion: `.github/workflows/promote.yml`

```yaml
name: Promote Eval Baseline
on:
  push:
    branches: [main]
    paths: ["prompts/**", "src/**", "evals/**"]

jobs:
  promote:
    runs-on: ubuntu-latest
    env: { EVAL_MODE: nightly, OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }} }
    steps:
      - uses: actions/checkout@v4
        with: { token: ${{ secrets.EVAL_BOT_TOKEN }} }
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: pytest evals/test_booking_agent.py -m eval     # produce fresh scores
      - run: python evals/promote_baseline.py               # ratchet forward
      - name: Commit new baseline
        run: |
          git config user.name  "eval-bot"
          git config user.email "eval-bot@users.noreply.github.com"
          git add evals/baseline/booking_v3.json
          git commit -m "chore(eval): promote baseline [skip ci]" || echo "no change"
          git push
```

Together these four files are a complete, honest CI eval system: a fast per-PR gate, a rigorous nightly with alerting, a promoted ratcheting baseline, and unit-tested gate math. Adapt the thresholds and grader; the skeleton is production-shaped.

### The same pattern in the ecosystem tools

You rarely have to build all of this by hand. The identical seven-box pipeline is expressed by:

- **promptfoo** — declarative `promptfooconfig.yaml` with `assert` blocks and thresholds; the [promptfoo GitHub Action](https://github.com/promptfoo/promptfoo-action) runs it on PRs and comments a diff, and the CLI exits non-zero when assertions fail so the build blocks automatically.
- **DeepEval** — `deepeval test run test_file.py` wraps pytest; `assert_test(golden, metrics=[...])` raises when a metric falls below its `threshold`, and `@pytest.mark.parametrize("golden", dataset.goldens)` drives it from a versioned dataset.
- **LangSmith / openevals** — `@pytest.mark.langsmith` syncs each test to a dataset example, `log_outputs` / `log_reference_outputs` record results, and openevals' ready-made judge and trajectory evaluators slot in as the graders.
- **Braintrust** — `Eval(...)` with `scorers=[...]` runs experiments that auto-compare against a baseline in CI and surface per-example regressions.
- **Inspect** — a `Task(dataset, solver, scorer)` you run with `inspect eval`, ideal when you want benchmark-grade rigor and a shared format with the research community.

> **Saying it out loud.** If you build this by hand it's four files, and I'd walk through them in order: a stats module holding the Wilson bound and the Welch test, unit tests for that stats module, the eval test that runs the agent over a versioned golden set, and the workflow YAML that tiers PR versus nightly. The one everyone skips is unit-testing the gate math, and it's the highest-value test in the system — a sign error in the Welch test either waves through every regression or blocks every green build, and you can catch it with synthetic score arrays and no model calls at all. Four properties make the gate trustworthy: it gates on the Wilson lower bound so a small sample fails honestly rather than randomly, it enforces a per-slice floor with a minimum-n guard, quarantined cases report but never block, and the three-condition regression gate only runs nightly where you have the statistical power. Promote the baseline in a post-merge job, never on a branch, so the ruler moves only by review and the ratchet turns one way. And the ecosystem tools are the same pipeline in different syntax — promptfoo's `assert` blocks, DeepEval's `assert_test` raising below threshold, Braintrust auto-diffing against a baseline experiment — so you're choosing which box to outsource, not a different architecture.

---

## Cost and Runtime Management

Eval suites cost real money (every judged example is 1–3 model calls) and real wall-clock time, and both grow with your dataset. Left unmanaged, a full suite on every commit will either bankrupt the eval budget or get so slow that people disable it. Levers, cheapest-win first:

| Lever | What it does | Typical effect |
|---|---|---|
| **Deterministic-first / classifier cascade** | Run free programmatic + small-classifier graders on all rows; escalate only low-confidence rows to a frontier judge | ~10x cost cut on the PR tier |
| **Response caching** | Cache model outputs keyed by (prompt, input, model version); re-runs on unchanged inputs cost $0 | Most CI re-runs become free |
| **Tiering (PR vs nightly)** | Small suite on PRs, big suite nightly | Moves the dollars off the hot path |
| **Path scoping + sharding** | Only run routes the diff touches; parallelize with a CI matrix | Cuts both cost and latency |
| **Sampling the golden set** | PR runs a stratified sample; nightly runs the full corpus | Bounds PR cost at the price of some sensitivity |
| **Cheaper judge model** | Use a small model as judge where it correlates with the big one (validate first!) | Large per-call savings if correlation holds |
| **Fail-fast on catastrophe** | If JSON-validity or a deterministic floor fails, stop before running expensive judges | Avoids paying for a doomed run |
| **Batch / async concurrency** | Fire judge calls concurrently within a rate-limit budget | Cuts wall-clock, not cost |

Two guardrails worth wiring in: a **per-run cost ceiling** (abort and alert if a run exceeds \(N\) dollars — cheap insurance against an infinite-loop agent burning tokens) and a **cached-vs-live ratio** in the report so you notice when caching silently stopped working and costs quietly 10x'd.

> **Saying it out loud.** Cost and runtime both scale with the dataset, and if you ignore them one of two things happens: you blow the budget, or the gate gets slow enough that people turn it off. The levers in payoff order are deterministic-first grading with a cascade, response caching keyed on prompt plus input plus model version, tiering so the dollars sit in nightly instead of on every commit, then path scoping, sharding and stratified sampling. Two guardrails to wire on day one: a per-run dollar ceiling that aborts and alerts — cheap insurance against an agent stuck in a tool-call loop burning tokens — and a cached-versus-live ratio in the report so you notice when caching silently stopped working and the bill quietly 10x'd. The bug everyone hits exactly once: if the cache key omits the exact model version, a provider rollout serves you stale cached outputs and the regression is invisible because you never actually called the new model. And runtime is really a patience budget — a twelve-minute PR gate gets skipped within a month, so keep that tier under about three minutes.

### A back-of-envelope cost model

> **In plain terms.** The formula below is just: how many examples, times how many times you run each one, times the price of one agent call plus whatever fraction of rows get escalated to an expensive judge. Every cost lever in this chapter is one of those four terms — and only two of them are safe to shrink.

Interviewers like to see you reason quantitatively about this. A simple model:

\[
\text{cost per run} \approx n_{\text{examples}} \times k_{\text{samples}} \times \big(c_{\text{agent}} + f_{\text{judge}} \times c_{\text{judge}}\big)
\]

where \(f_{\text{judge}}\) is the fraction of rows that escalate to the frontier judge after the cascade. Plug in numbers: a nightly of \(n = 1000\), \(k = 3\), agent cost \(c_{\text{agent}}\) = 2 cents/call, judge cost \(c_{\text{judge}}\) = 3 cents/call, and *no* cascade (\(f = 1\)) costs \(1000 \times 3 \times (0.02 + 0.03)\) = 150 dollars/night, or ~4,500 dollars/month. Add a cascade that escalates only 15% of rows (\(f = 0.15\)) and it drops to \(1000 \times 3 \times (0.02 + 0.15 \times 0.03)\) ≈ 74 dollars/night — roughly half — and layering response caching on the unchanged majority of nightly rows takes the *marginal* cost of a night with no dataset change close to zero. The lesson the arithmetic teaches: the cascade fraction \(f\) and the cache hit rate are the two dials that actually move the bill; sampling \(k\) down hurts your statistics faster than it helps your budget.

> **Saying it out loud.** If they ask you to size it, do the arithmetic out loud, because that's the part that sounds like experience. Thousand-example nightly, three samples each, two cents per agent call and three cents per judge call with no cascade: a thousand times three times five cents is 150 dollars a night, about 4,500 a month. Put in a cascade that escalates only 15% of rows to the frontier judge and it drops to roughly 74 dollars a night, and caching the unchanged majority takes the marginal cost of a night with no dataset change close to zero. The lesson buried in the arithmetic is which dials matter: the cascade fraction and the cache hit rate move the bill, while cutting your sample count hurts your statistics faster than it helps your budget.

### The runtime side

Cost is dollars; runtime is patience, and patience is what determines whether the gate survives. A PR gate that takes 12 minutes will get `[skip ci]`'d within a month. Keep the PR tier under ~3 minutes by (a) shrinking \(n\) to a stratified sample, (b) sharding across a CI matrix so slices run in parallel, (c) caching aggressively, and (d) issuing judge calls concurrently up to your rate limit. The nightly tier can be slow because it runs while everyone sleeps — but even there, cap it with a `timeout-minutes` so a hung provider call cannot leave a job running (and billing) for six hours.

---

## Production Case Studies & War Stories

Patterns are easier to trust when you have seen them save (or sink) a real team. These are composites — drawn from how agent-eval-in-CI actually plays out across companies — chosen because each teaches a lesson you can carry into an interview or a design review.

### Case study 1: How a mature team actually runs it

A typical well-run applied-AI team in 2025–2026 converges on something like this, regardless of which vendor they buy:

- **Every PR** runs a 60-example, path-scoped, deterministic-heavy smoke suite in under two minutes. It gates on absolute floors only (JSON-validity = 1.0, tool-selection ≥ 0.9, no catastrophic groundedness collapse). It almost never fails — and when it does, it is nearly always a real, obvious break, which is exactly why engineers still trust its red after a year.
- **Every night** a 1,500-example suite runs the full judge sweep, computes per-slice deltas against the median of the last seven nights, and posts a summary to a `#eval` Slack channel — green or red. Posting on green too is deliberate: a channel that only speaks up on failure trains people to dread it; a daily "all clear, here are the numbers" keeps the eval visible and builds the habit of glancing at trends.
- **The golden dataset is a product.** It has an owner. Every production incident ends with "add the failing case to the golden set" as a checklist item, so the suite gets monotonically better at catching the things that actually hurt users. Over a year this "incident-to-golden" pipeline is what makes the suite representative — far more than any up-front dataset design.
- **The judge is calibrated quarterly** against a few hundred human labels, and the agreement number is tracked over time. When a provider updates the judge model, the calibration run is how they find out the ruler moved.

The meta-lesson: the tooling is interchangeable, but the *disciplines* — floors on PR, deltas at night, incident-to-golden, judge calibration, posting on green — are what separate a gate people trust from a dashboard people ignore.

> **Saying it out loud.** If someone asks what a mature setup actually looks like, describe the disciplines rather than the vendor, because the vendor is interchangeable. Every PR runs a sixty-example, path-scoped, deterministic-heavy suite in under two minutes gating on absolute floors, and it almost never fails — which is exactly why people still trust its red a year later. Every night a fifteen-hundred-example suite runs the full judge sweep, computes per-slice deltas against the median of the last seven nights, and posts to a Slack channel green or red; posting on green is deliberate, because a channel that only speaks up on failure trains people to dread it. The golden dataset has a named owner, and every production incident ends with "add the failing case to the golden set" — over a year that incident-to-golden pipeline does more for representativeness than any upfront dataset design. And the judge is calibrated against a few hundred human labels quarterly, because that calibration run is how you find out the provider moved your ruler.

### War story 2: The too-strict flaky gate that blocked every release

A team set a PR gate at "success rate ≥ 0.95, hard threshold, single sample, 40 examples." It looked rigorous. In practice, a 40-example single-sample estimate of a ~0.95-true-rate process has enormous run-to-run variance — the observed rate routinely swung between 0.90 and 1.00 on *identical code*. So the gate failed maybe one run in three at random. Engineers learned within a week that red meant nothing, and the culture became "just hit re-run until it's green." Then a *real* regression landed — tool-selection quietly dropped — and it sailed through, because the one red check it produced was indistinguishable from the dozens of noise-reds everyone had been re-running past all month.

**Root cause:** gating a noisy point estimate against a hard threshold on a tiny sample. The gate wasn't too strict in the sense of "bar too high" — it was too strict in the sense of "pretending a noisy measurement was exact." **Lesson:** the fix was not to lower the bar; it was to gate on the Wilson lower bound (which on n=40 is honest about its own uncertainty and stops flaking) and to move the tight quality delta to the nightly tier where n is large enough to actually measure it. A gate that cries wolf is worse than no gate, because it launders a real failure into the noise. The credibility of red is the entire asset; a flaky gate spends it to zero.

> **Saying it out loud.** Here's the cautionary number. A team gated at "success rate at least 0.95, hard threshold, single sample, forty examples," which looks rigorous and is actually close to a coin flip — at a true rate around 0.95, a forty-example single-sample estimate routinely swings between 0.90 and 1.00 on identical code, so the gate failed roughly one run in three at random. Within a week the culture was "hit re-run until it's green," and then a real tool-selection regression landed and sailed straight through, because its one red check was indistinguishable from a month of noise-reds. The root cause wasn't that the bar was too high; it was pretending a noisy measurement was exact. The fix was gating on the Wilson lower bound, which at n=40 is honest about its own uncertainty, and moving the tight quality delta to nightly where the sample size can actually support it. The line to remember: a gate that cries wolf is worse than no gate, because it launders a real failure into the noise.

### War story 3: Silent dataset drift and the phantom regression

Over a quarter, the nightly groundedness score drifted down from 0.91 to 0.83. Panic: which prompt change broke citations? Two engineers spent a week bisecting merges. The agent was fine. What had happened: a well-meaning teammate had been *editing the golden dataset's `expected` values* over the quarter to "improve" them — tightening the reference answers — and a separate re-export had reordered rows so the per-case baseline matching silently fell back to whole-suite comparison. This week's 0.83 and last quarter's 0.91 were measured against different rulers. The regression was 100% an artifact of the dataset, not the agent.

**Root cause:** an unversioned, in-place-mutated dataset compared against stored scores. **Lesson:** the dataset is part of the measuring apparatus and must be as immutable and version-controlled as the baseline. Concretely: put the version in the filename (`booking_golden_v3.jsonl`), require dataset changes to go through reviewed PRs, store a content hash of the dataset alongside every baseline score, and make the eval *refuse to compare across dataset versions* — a hash mismatch should hard-error with "you changed the ruler," not silently produce a phantom regression. After adding the hash check, the same class of incident became a loud, immediate error at the top of the run instead of a week-long ghost hunt.

### War story 4: Judge drift moved the bar under everyone's feet

A team's "helpfulness" score jumped 6 points overnight with no code change. Champagne, briefly. The real cause: the provider had rolled the judge model (`gpt-4o` pinned only to the floating alias) to a newer snapshot that happened to score more generously on their rubric. The agent had not improved at all; the ruler had gotten more lenient. Worse, it could just as easily have gone the other way and manufactured a "regression" that consumed a week.

**Root cause:** an unpinned judge model — the same silent-provider-rollout risk as the agent model, but on the measuring instrument. **Lesson:** pin the judge to an exact dated snapshot (`gpt-4o-2024-08-06`), treat a judge-version bump as a reviewed change that re-baselines the suite, and keep a standing set of human-labeled examples to re-validate the judge whenever it changes. The judge is an instrument; instruments need calibration certificates, and an uncalibrated instrument that silently recalibrates itself is worse than a slightly-biased one that holds still.

### War story 5: Overfitting the eval into meaninglessness

A team gated every merge on a fixed 50-example suite. Success rate climbed steadily from 0.82 to 0.99 over two months, and everyone felt great — until customer complaints kept rising in lockstep. Investigation found engineers had been (entirely rationally, given the incentive) pasting failing eval cases and their ideal answers straight into the system prompt. The agent had essentially memorized the test. The 0.99 measured the prompt's ability to recite 50 answers, not to serve users.

**Root cause:** a small, static, fully-visible eval set became the optimization target — textbook Goodhart. **Lesson:** keep a **held-out** slice that never informs prompt edits and is only ever *reported*, not optimized against; rotate and grow the golden set continuously (the incident-to-golden pipeline helps here); and treat a suddenly-perfect score as a smell to investigate, not a trophy. When the visible suite and the held-out suite diverge, you are overfitting — and the held-out number is the one that predicts production.

> **Saying it out loud.** This is Goodhart's law with a body count. A team gated every merge on a fixed fifty-example suite and watched success climb from 0.82 to 0.99 over two months — while customer complaints climbed right alongside it, because engineers had been pasting failing eval cases and their ideal answers into the system prompt. The 0.99 was measuring the prompt's ability to recite fifty answers, not to serve users. The defenses are a held-out slice that never informs prompt edits and is only ever reported, rotating and growing the golden set through the incident-to-golden pipeline, and treating a suddenly-perfect score as a smell to investigate rather than a trophy. When the visible number and the held-out number diverge, the held-out one is the one that predicts production.

---

## Failure Modes and Pitfalls

**The gate is too strict or flaky, so people route around it.** A gate that flips red on noise trains engineers to hit "re-run until green," which is worse than no gate — it produces false confidence and, as War Story 2 shows, launders real failures into the noise. Fix with the statistical machinery above (confidence bounds, multiple samples, significant-*and*-meaningful deltas) and quarantine irreducibly flaky cases. A gate's credibility is its entire value; spend it carefully.

**Overfitting to the CI eval (the eval becomes the target).** This is Goodhart's law: once a fixed 50-example set gates every merge, people optimize prompts *against those 50 examples* — sometimes literally pasting failing cases into the prompt (War Story 5). The suite goes green while real-world quality stalls. Defenses: keep a **held-out** slice that never informs prompt edits, **rotate/grow** the golden set over time, and treat a suddenly-perfect score as a smell to investigate, not a trophy.

**Silent dataset drift.** The golden dataset changes underneath the comparison — someone edits `expected` values, a re-export reorders rows, a labeler "fixes" answers — and now this week's 91% and last week's 93% are measured against different rulers (War Story 3). The regression is an artifact of the dataset, not the agent. Defenses: **version the dataset** (hash or version in the filename, like `booking_golden_v3.jsonl`), require dataset changes to go through **reviewed PRs**, pin the **dataset version alongside every baseline score**, and refuse to compare scores across versions (hard-error on hash mismatch).

**LLM-judge drift.** Your grader is itself a model, and the provider can change it (War Story 4). A groundedness score that "regressed" may be the judge getting stricter, not the agent getting worse — and it can move in either direction. Pin the judge model version to a dated snapshot, and periodically **re-validate the judge against human labels** — the judge is a measuring instrument and instruments need calibration.

**Nightly failures nobody sees.** A cron eval fails at 02:00, the report sits in an artifact, and the regression is discovered three days later by a user. If a run has no **alert** wired to a channel a human watches, it is not a gate — it is a log file. Wire the Slack/PagerDuty hook the day you create the nightly, and post on green too so the channel stays trusted.

**A green suite that tests the wrong thing.** The most dangerous failure is a passing gate on a dataset that does not reflect production. High coverage of easy cases and zero coverage of the failure modes users actually hit. The eval is only ever as good as the golden dataset; invest there (via the incident-to-golden pipeline) before you invest in fancier graders.

**Non-hermetic harness leaking real-world entropy.** An eval that calls live third-party APIs, a mutable retrieval index, or the wall clock measures the internet's uptime and today's index as much as the agent. A "flaky agent" is frequently a leaky harness. Freeze the environment: mock tools, snapshot the index, pin the clock and any seeds in your own code, so a failure unambiguously means the agent did the wrong thing.

**Gating the mean instead of the tails.** A great average can hide a catastrophic p99 — the agent is usually excellent but occasionally leaks PII or hallucinates a refund policy. For safety-critical behaviors, gate on the *worst case* (max hallucination rate, any policy violation = fail), not the average. Averages are for quality; floors and max-violation checks are for safety.

**Untested gate math.** The gate is code that can block a release. A sign error in the Welch test or an off-by-one in the Wilson bound will silently wave through every regression or block every green build. Unit-test the gate with synthetic score arrays (as in `test_stats.py`) — it is the cheapest, highest-value test in the whole system.

**Cache poisoning by an unpinned model.** If the response cache key omits the model version, a provider rollout serves you stale cached outputs and the regression is invisible because you never actually called the new model. Always include the exact model version in the cache key.

> **Saying it out loud.** Being able to name these cold is what makes you sound like you've operated one of these rather than read about it. The headline set: a flaky gate people route around, overfitting to a small fixed eval set, silent dataset drift where someone edits the golden answers so this week and last week are measured with different rulers, judge drift where the provider rolls your grader and the bar moves under everyone, and nightly failures nobody sees because there's no alert wired to a channel a human watches. Two less-discussed ones worth having ready: a non-hermetic harness leaking real-world entropy, so what looks like a flaky agent is really a leaky test, and gating the mean instead of the tails, where a healthy average hides an occasional PII leak. The rule for that last one is a clean soundbite — averages are for quality, zero-tolerance max-violation checks are for safety. And the meta-failure is untested gate math: a sign error in the Welch test silently waves through every regression, and it's the cheapest test in the whole system to write.

---

## Tools Table

| Tool | Shape | CI/CD hook | Best for | Notes |
|---|---|---|---|---|
| **promptfoo** | Declarative YAML + CLI | Official GitHub Action (PR comment + diff); CLI exits non-zero on assertion failure; JSON/HTML/JUnit output | Prompt & RAG regression gates, red-teaming | Response caching built in (`PROMPTFOO_CACHE_PATH`); `--share` for hosted reports |
| **DeepEval** | pytest-native (`deepeval test run`) | `assert_test` raises below `threshold`; drives from `dataset.goldens` | Python teams wanting eval-as-unit-test | 14+ research-backed metrics; pairs with Confident AI for hosting |
| **LangSmith** | SDK + `@pytest.mark.langsmith` / Vitest | Syncs tests to datasets; pass/fail as feedback; `--langsmith-output` | LangChain/LangGraph stacks, tracing + eval together | Online eval on production traces; dataset versioning in-platform |
| **openevals** | Library of ready-made evaluators | Drop into any pytest/harness as the grader functions | Not wanting to hand-write judge prompts / trajectory evals | Open-source; correctness/conciseness/hallucination + agent trajectory evaluators |
| **Braintrust** | `Eval()` SDK + hosted experiments | Auto-compares candidate vs baseline in CI; per-example regression view | Teams wanting rich experiment diffing | Strong side-by-side regression UX |
| **Inspect (UK AISI)** | Python `Task` (dataset + solver + scorer) | `inspect eval`; non-zero on scorer thresholds; log viewer | Benchmark-grade rigor, capability/safety evals | `inspect_evals` ships dozens of implemented benchmarks; research-standard |
| **OpenAI Evals** | Open-source registry + `oaieval` | Run in CI via CLI; YAML-registered evals over samples | Benchmark-style, model-vs-model | Community registry of benchmarks; more benchmark than app-eval |
| **Custom pytest + Wilson/Welch** | Hand-rolled (this chapter) | Plain `pytest` assert fails the build | Full control over statistical gating | Zero lock-in; you own the confidence math |

How to choose in one breath: **config-first prompt/RAG gate → promptfoo; pytest-native metric gate → DeepEval; hosted trace + experiment platform → LangSmith or Braintrust; ready-made evaluators without a platform → openevals; benchmark-grade rigor → Inspect; own the exact statistics → hand-rolled pytest.** Most teams end up with *two*: a platform for tracing/reporting and a thin hand-rolled layer for the gate math they refuse to outsource.

---

## Interview Mastery

This section is engineered to make you fluent enough to convince a senior interviewer that you have actually built this, not just read about it. It has four parts: a rapid-fire 60-second answer to the signature question, a full system-design walkthrough, tradeoff tables you can draw on a whiteboard, and a red-flags/green-flags rubric — followed by a deep Q&A bank.

### The 60-second answer: "How would you gate a build on a nondeterministic eval?"

Practice saying this out loud until it is 60 seconds flat:

> "The problem is that the eval score is a random variable, not a number, so if I compare a single run to a hard threshold the gate flips red on noise and engineers learn to ignore it. So I do four things. First, I cut variance at the source — pin the model version and temperature, freeze the retrieval index and tools — though on a shared endpoint that only reduces noise, it doesn't remove it, because batch size varies with load. Second, I run each case a few times and aggregate. Third — the key move — I gate on a *confidence bound*, the Wilson lower bound of the success rate, not the point estimate: I only fail the build when I'm statistically confident the true rate is below the bar, so an unlucky small sample gives a wide interval and an honest 'too small to conclude' instead of a random red. Fourth, for regressions I require the drop to be both statistically significant, via a Welch's t-test on the per-example scores, *and* larger than a minimum effect size I actually care about, so I don't fire on a trivial 0.3% dip or a noisy 5% dip on twelve examples. Anything irreducibly flaky goes into a quarantine that reports but doesn't block. And I keep the tight, statistically-hungry checks on the nightly tier where n is large, and only cheap deterministic floors on the per-PR tier where it has to be fast."

That answer hits: nondeterminism source (with the 2025 batch-invariance nuance), aggregation, confidence-bound gating, the three-condition regression test, quarantine, and tiering. It is the whole chapter compressed, and it signals hands-on experience.

### System design: "Design the CI/CD eval pipeline for an agent"

Treat this like any system-design interview: clarify, sketch, justify, then discuss failure modes and scaling. Here is a strong answer skeleton.

**1. Clarify requirements (30 seconds of questions).** What is the agent (tool-using? RAG? multi-turn?)? What is "correct" and who defines it? How bad is a false-block vs a missed regression (i.e. is this a payments agent or a brainstorming toy)? What is the deploy cadence and the eval budget? These answers set your thresholds and tiering.

**2. Draw the pipeline.**

```
                       ┌────────────────────── DATASETS (versioned, hashed) ──────────────────────┐
                       │  golden_vN.jsonl  ·  held-out slice  ·  quarantine.txt  ·  baseline.json  │
                       └──────────────────────────────────────────────────────────────────────────┘
                                    │                    │                      │
   PR push ──▶ [PR SMOKE]           │        merge ──▶ [MERGE-QUEUE MED]        │      cron ──▶ [NIGHTLY FULL]
   path-scoped, n≈60,   ───────────┘        n≈300, deterministic+cheap  ───────┘      n≈1500, full judge sweep
   deterministic floors,                    judge, blocks the merge               per-slice Welch delta vs
   Wilson LB, <3 min                                                              7-night median baseline
        │                                          │                                        │
        ▼                                          ▼                                        ▼
   PR check + report                        merge allowed / blocked            Slack #eval (green OR red) + alert
                                                                                        │
                                                                        promote baseline (post-merge, committed)
                                                                                        │
   deploy ──▶ [CANARY / ONLINE EVAL] 1–5% live traffic, same rubrics async ──▶ auto-rollback + feed failures back to golden
```

**3. Justify each box.** PR tier is deterministic-heavy and path-scoped so it is fast and its red is trustworthy; it gates on absolute floors and a Wilson lower bound only. The merge-queue tier (optional) runs a medium suite once per merge rather than per commit. Nightly is where the statistical power lives: full judge sweep, per-slice Welch deltas against a rolling-median baseline, with an alert because nobody is watching. Baseline promotion is a post-merge committed diff so the ruler only moves via review. The canary catches the live distribution offline can't, auto-rolls-back, and its failures become new golden cases — closing the loop.

**4. Address the cross-cutting concerns without being asked** (this is what separates a senior answer): nondeterminism → confidence-bound gating; cost → cascade + caching + tiering + per-run ceiling; dataset integrity → versioning + hashing + reviewed PRs; judge integrity → pinned snapshot + quarterly human calibration; observability → report on every run, alert on nightly, post-on-green. Name the failure mode for each box (flaky gate, silent drift, judge drift, unseen nightly failure) and the specific defense.

**5. Discuss scale.** As the org grows: shard the suite across runners; move from per-file datasets to a dataset service with versioning; introduce a held-out set to fight overfitting; add a merge queue; and eventually a dedicated eval platform (Braintrust/LangSmith) for the reporting/triage UX while keeping the gate math in-house.

> **Saying it out loud.** The skeleton is: clarify, draw the seven boxes, tier the triggers, then volunteer the cross-cutting concerns before they're asked. Clarify first, and the question that actually matters is whether a false block or a missed regression is worse — a payments agent and a brainstorming toy get completely different thresholds. Then draw it: a deterministic, path-scoped PR tier gating on floors plus a Wilson bound; an optional merge-queue tier running a medium suite once per merge instead of once per commit; a nightly with the full judge sweep, per-slice Welch deltas against a rolling-median baseline, and an alert because nobody's awake; post-merge baseline promotion so the ruler only moves through review; and a canary on live traffic whose failures feed back as new golden cases. The senior move is the next step — naming nondeterminism, cost, dataset integrity, judge integrity and observability with one specific defense each, unprompted. Then scale it: shard across runners, graduate from files to a versioned dataset service, add a held-out set, and buy a platform for triage UX while keeping the gate math in-house.

### Tradeoff table: PR-smoke vs nightly-full

| Dimension | PR smoke | Nightly full |
|---|---|---|
| Trigger | every `pull_request` (path-scoped) | `schedule` cron |
| Size (n) | 30–100 | 500–2,000 |
| Graders | deterministic + cheap classifiers | full LLM-judge sweep |
| Latency budget | < 3 min (patience-bound) | 20–60 min (invisible) |
| Cost budget | cents | dollars |
| Statistical power | low (wide intervals) | high (tight intervals) |
| Gate type | absolute floors + Wilson LB | per-slice significant-and-meaningful delta |
| Blocks | the PR | the release train / raises alert |
| Self-alerting? | yes (author watches) | no → must wire Slack/PagerDuty |
| Path-scoped? | yes (speed) | no (catch cross-cutting changes) |
| Failure meaning | "you broke something obvious" | "quality drifted; investigate" |

### Tradeoff table: strict vs lenient gates

| | Strict gate | Lenient gate |
|---|---|---|
| False block rate | high (flakes) | low |
| Missed-regression rate | low (if not routed around) | high |
| Engineer trust over time | erodes if flaky → routed around | stays, but may be ignored as toothless |
| Right for | payments, safety, irreversible actions | brainstorming, drafts, human-in-loop |
| Failure mode | cries wolf → real reg slips through | rubber-stamps → slow drift accumulates |
| The actual fix | not "less strict" — gate on *confidence bound* so strictness is honest about noise | add a delta gate so drift is still caught |

The senior insight both tables encode: **strict-vs-lenient is the wrong axis.** The right axis is *statistically honest vs statistically naive*. A confidence-bound gate can be strict on the true rate while never flaking on noise — you get rigor and trust at once, which the naive "raise/lower the threshold" framing can never deliver.

### Red flags vs green flags

What a strong candidate says (and a weak one doesn't):

| Red flag (weak answer) | Green flag (strong answer) |
|---|---|
| "Run the full suite on every commit." | "Tier it — deterministic floors on PR, judge sweep nightly." |
| "Compare the score to the threshold." | "Gate on the Wilson lower bound so noise doesn't flake it." |
| "If the mean drops, fail." | "Require significant *and* meaningful drop; Welch, not Student's." |
| "Temperature 0 makes it deterministic." | "Pinning helps but batch-size variance on shared endpoints remains." |
| "We track the average success rate." | "We gate per-slice and on tails for safety-critical behaviors." |
| "The eval set gates every merge." | "There's a held-out slice that never informs prompt edits." |
| "We edit the golden answers when they seem wrong." | "Dataset is versioned + hashed; changes go through review." |
| "The judge is GPT-4o." | "The judge is pinned to a dated snapshot and calibrated to humans quarterly." |
| "Nightly writes a report artifact." | "Nightly alerts Slack on failure and posts on green too." |
| "LLM judge on every PR for quality." | "Judge is nightly; PR is deterministic to keep red trustworthy and cheap." |
| "It flaked so we hit re-run." | "A flaky gate is a bug in the gate; fix the statistics or quarantine." |

### Q&A bank

**Q1. Why not just run your full eval suite on every pull request?**
Because of the cheap/fast/significant triangle: a statistically meaningful suite (hundreds of judged examples) is slow and expensive, and running it on every commit either blows the budget or gets so slow engineers disable it. The standard resolution is tiering — a small, mostly-deterministic, path-scoped smoke suite on PRs for fast feedback, and the heavy statistically-rigorous judge sweep nightly where a 40-minute run is invisible. Production canary catches what offline cannot.

**Q2. Your eval gate flips red randomly and engineers just re-run it. What's wrong and how do you fix it?**
The gate is comparing a single noisy sample to a hard threshold, so LLM nondeterminism flips it. Fix in layers: pin model version and temperature to cut variance at the source; sample each case k times and aggregate; and crucially, gate on a **confidence bound** (Wilson lower bound) rather than the point estimate, so you only fail when statistically confident the true rate is below the bar. For regressions, require the drop to be significant (Welch's t-test) *and* exceed a minimum effect size. Quarantine irreducibly flaky cases so they report but don't block.

**Q3. Why gate on a Wilson lower bound instead of the raw success rate?**
The raw rate is a point estimate with sampling noise; on a small suite it can land above or below the threshold by luck. The Wilson lower bound answers the honest question — "could the *true* rate be below my bar?" — and is stable near 0 and 1 where the normal approximation breaks. Gating on it means an unlucky small run yields a wide interval and a clear "too small to conclude" failure, not a random flake; growing the dataset tightens the interval. It simultaneously enforces quality *and* dataset adequacy.

**Q4. Your overall success rate is flat but users report the agent broke for a specific case type. How does automated eval catch that?**
Per-slice gating. An aggregate mean can stay flat while a subpopulation collapses, masked by another slice getting easier. You break the dataset into categories (intent, language, difficulty, tool-required) and run the regression/threshold test on *each slice*, not just the mean. A per-slice floor fails loudly when, say, the Spanish refund slice drops from 88% to 60% even though the overall number barely moved. Guard against the multiple-comparisons inflation by requiring a per-slice effect floor and a minimum slice size.

**Q5. What is "overfitting to the eval" and how do you prevent it?**
Goodhart's law: once a fixed small dataset gates every merge, people optimize prompts against those specific examples — sometimes pasting failing cases straight into the prompt — so the suite goes green while real quality stalls. Prevent it with a held-out slice that never informs prompt changes, by rotating and growing the golden set over time (incident-to-golden), and by treating a suddenly-perfect score as a smell to investigate rather than a win. When the visible and held-out numbers diverge, the held-out one predicts production.

**Q6. How do you keep eval costs from exploding as your suite grows?**
Deterministic-first grading with a classifier cascade (free programmatic checks on all rows, escalate only low-confidence cases to a frontier judge — roughly 10x cheaper); response caching keyed on (prompt, input, model version) so re-runs on unchanged inputs cost nothing; tiering so the dollars sit in nightly not on every commit; path-scoping and sharding; and a per-run cost ceiling that aborts and alerts on a runaway agent. Validate any cheaper judge model against the expensive one before trusting it. The cascade fraction and cache hit rate are the two dials that actually move the bill.

**Q7. What is silent dataset drift and why is it dangerous?**
It's when the golden dataset changes underneath your comparison — edited expected values, reordered rows, "corrected" labels — so this week's score and last week's score are measured against different rulers, and a phantom regression appears that has nothing to do with the agent. It's dangerous because it silently invalidates the whole gate and burns days of investigation. Defend by versioning the dataset (version in the filename), hashing it and storing the hash with every baseline, requiring reviewed PRs for dataset changes, and hard-erroring on a hash mismatch instead of comparing across versions.

**Q8. Where does online/continuous evaluation fit relative to CI evals?**
CI evals (PR + nightly) run offline against a curated golden set — they catch regressions before shipping but only for scenarios you thought to include. Online eval runs the same rubrics asynchronously on a sample of *live production traffic*, catching what offline cannot: real user distribution, model drift, and long-tail inputs. It typically drives alerts and auto-rollback rather than blocking a merge, and its surprising failures become new golden examples — closing the loop back into the offline suite.

**Q9. Even at temperature 0 your evals aren't reproducible. Why, and what do you do?**
Pinning temperature and seed removes *sampling* randomness but not all nondeterminism on a hosted endpoint. The 2025 Thinking Machines result showed the dominant cause is lack of **batch invariance**: server-side batch size varies with concurrent load, and common kernels produce slightly different reductions at different batch sizes, so your "identical" request is computed differently run to run. If you need true bit-reproducibility you need a deterministic-inference stack (batch-invariant kernels, e.g. SGLang's deterministic mode). For ordinary app eval you accept the residual and gate on confidence bounds instead of pretending it away — which is why the statistics matter.

**Q10. Why Welch's t-test and not Student's for regression detection?**
Welch's does not assume equal variances between the baseline and candidate runs, and eval runs frequently have unequal variance — a change can make the agent both worse on average and more erratic. Using Student's when variances differ inflates false positives. Welch is the safe default. If I can pin seeds so the same rows are comparable across runs, I'd go further and use a paired test or a bootstrap over per-example deltas, which removes example-difficulty variance and needs far fewer examples for the same power.

**Q11. How do you choose the threshold and the minimum effect size?**
Both are product decisions, not statistical ones. The absolute floor encodes the non-negotiable bar for the use case (JSON-validity 1.0 always; groundedness maybe 0.85 for a support agent, higher for medical). The minimum effect size is "how big a drop do we actually care about?" — small enough to catch real regressions, large enough to ignore judge noise; a couple of points is typical. I set them explicitly in version control so they're reviewable, and I calibrate the effect floor against the observed run-to-run noise of the suite: if the suite naturally wobbles ±1.5 points on identical code, a 1-point effect floor is guaranteed to flake.

**Q12. What do you do about irreducibly flaky examples — ambiguous ground truth, judge disagreement?**
Quarantine them: tag `@flaky`, move to a suite that runs and reports but never blocks the merge. That keeps the main gate green and trustworthy while preserving the signal. But quarantine is a tracked bug list, not a graveyard — I auto-quarantine on a measured flip rate, review the list every sprint, and alert if quarantine exceeds ~5% of the suite, because a bloated quarantine means my graders or dataset are decaying and the gate is going hollow.

**Q13. How do you gate a safety-critical behavior differently from a quality metric?**
Quality metrics gate on the average (or a confidence bound on it); safety-critical behaviors gate on the *worst case*. A great mean can hide a catastrophic tail — usually excellent, occasionally leaks PII or fabricates a refund policy. For those I gate on max-violation: any policy violation in the suite fails the build, no averaging. Averages are for "is it good"; floors and zero-tolerance max checks are for "is it safe."

**Q14. Your PR eval passed but the nightly caught a regression the next day. Is the PR gate broken?**
No — that's the tiers working as designed. The PR gate is deliberately small and deterministic-heavy for speed, so it has low statistical power and only catches obvious/catastrophic breaks. The nightly has the sample size and full judge sweep to detect a subtle few-point drift the PR tier mathematically cannot see. The right response is to add the caught case to the golden set so the *class* of regression becomes catchable earlier next time, and to check whether it should be promoted into the PR smoke sample.

**Q15. How do you prevent the judge model from silently changing your results?**
Pin it to an exact dated snapshot, never a floating alias — the same discipline as the agent model. Treat a judge-version bump as a reviewed change that re-baselines the suite. Keep a standing set of human-labeled examples and re-validate the judge's agreement with humans on a schedule (quarterly) and whenever it changes. Track that agreement number over time; a drop means the ruler moved. The judge is a measuring instrument and it needs a calibration certificate.

**Q16. How would you catch slow, cumulative drift where each individual change looks innocent?**
A single previous-run comparison can't — each 0.5-point drop is within noise. The delta gate against a *rolling baseline* (median of the last N nightly runs) plus a longer-horizon trend view catches the cumulative slope. And the ratchet discipline — promoting the baseline forward only on merge, and refusing to ratchet *down* — means quality can't quietly erode: every merge has to clear the accumulated bar, not just beat yesterday.

**Q17. What belongs in the golden dataset, and how does it stay representative?**
Seed it from design docs and hand-written cases covering intended behaviors and known-hard edge cases, sliced by the dimensions you care about (intent, language, difficulty, tool-required). Then the crucial part: an **incident-to-golden pipeline** — every production failure ends with "add the failing case to the golden set." Over a year that's what makes the suite match reality, far more than up-front design. Keep a held-out slice for overfitting defense, and monitor coverage so easy cases don't crowd out the failure modes users actually hit.

**Q18. When would you say a team does NOT need automated eval in CI?**
When the cost of a regression is trivially reversible and the change rate is low — a personal side project, a throwaway prototype, or a purely human-in-the-loop draft tool where every output is reviewed before it matters. The moment the agent takes an autonomous or hard-to-reverse action, changes more than occasionally, or has more than one person editing prompts, the manual eval starts rotting and CI pays for itself. It's a cost/benefit call, and being able to say "here's when it's *not* worth it" signals judgment, not dogma.

---

## Further Reading

Grouped by topic, with primary sources. URLs verified against the 2025–2026 ecosystem.

### Tools and CI/CD integration
- promptfoo — CI/CD Integration: <https://www.promptfoo.dev/docs/integrations/ci-cd/>
- promptfoo — Testing Prompts with GitHub Actions: <https://www.promptfoo.dev/docs/integrations/github-action/>
- promptfoo GitHub Action (source): <https://github.com/promptfoo/promptfoo-action>
- DeepEval — Unit Testing in CI/CD: <https://deepeval.com/docs/evaluation-unit-testing-in-ci-cd>
- DeepEval — Regression Testing LLM Systems in CI/CD: <https://deepeval.com/guides/guides-regression-testing-in-cicd>
- DeepEval — 2025 changelog (feature timeline): <https://deepeval.com/changelog/changelog-2025>
- LangSmith — Run evaluations with pytest: <https://docs.langchain.com/langsmith/pytest>
- LangSmith — Run evals with the openevals package: <https://docs.langchain.com/langsmith/openevals>
- LangChain — Evaluating LLMs with OpenEvals (blog): <https://www.langchain.com/blog/evaluating-llms-with-openevals>
- openevals (source): <https://github.com/langchain-ai/openevals>
- Braintrust — Evaluate systematically: <https://www.braintrust.dev/docs/evaluate>
- Braintrust — Compare experiments (regression diff): <https://www.braintrust.dev/docs/evaluate/compare-experiments>
- Braintrust — Best AI Eval Tools for CI/CD Pipelines (2025/2026 survey): <https://www.braintrust.dev/articles/best-ai-evals-tools-cicd-2025>
- Inspect (UK AISI) — framework: <https://inspect.aisi.org.uk/> and source <https://github.com/UKGovernmentBEIS/inspect_ai>
- Inspect Evals — implemented benchmark suite: <https://ukgovernmentbeis.github.io/inspect_evals/> · AISI announcement: <https://www.aisi.gov.uk/blog/inspect-evals>
- OpenAI Evals — Running evals: <https://github.com/openai/evals/blob/main/docs/run-evals.md>

### Nondeterminism (the 2025 story)
- Thinking Machines Lab — *Defeating Nondeterminism in LLM Inference* (Horace He et al., 2025-09-10): <https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/>
- Simon Willison — summary and commentary (2025-09-11): <https://simonwillison.net/2025/Sep/11/defeating-nondeterminism/>
- LMSYS — Deterministic inference in SGLang & reproducible RL training (2025-09-22): <https://www.lmsys.org/blog/2025-09-22-sglang-deterministic/>
- arXiv — Understanding and Mitigating Numerical Sources of Nondeterminism in LLM Inference: <https://arxiv.org/html/2506.09501v2>

### Statistics for gating
- Wilson score interval (binomial proportion confidence interval): <https://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval#Wilson_score_interval>
- Welch's t-test (unequal-variance two-sample test): <https://en.wikipedia.org/wiki/Welch%27s_t-test>
- Benjamini–Hochberg procedure (false discovery rate for multiple slices): <https://en.wikipedia.org/wiki/False_discovery_rate#Benjamini%E2%80%93Hochberg_procedure>

### Landscape and practice
- Future AGI — LLM Eval Gates in GitHub Actions (statistical gating, cascades, exit codes): <https://futureagi.com/blog/ci-cd-llm-eval-github-actions-2026/>
- Braintrust — Top 5 platforms for agent evals in 2025: <https://www.braintrust.dev/articles/top-5-platforms-agent-evals-2025>

---

## Key Takeaways

- **Evaluation is a control loop, not a phase.** A manual eval rots the moment the system under test changes — and an agent changes constantly. Automation is what keeps quality from eroding one innocent change at a time.
- **Every pipeline is seven boxes:** trigger, dataset, harness, graders, gate, report, alert. Every tool — promptfoo, DeepEval, LangSmith/openevals, Braintrust, Inspect — is a different spelling of the same seven.
- **The score is a random variable, not a number.** Gate on a **Wilson lower bound**, not a point estimate, so noise on a small sample can't flake the build; require a regression to be **significant (Welch) *and* meaningful (effect floor)** so you fire on neither trivial nor noisy drops.
- **Tier your triggers:** cheap deterministic floors on the PR (fast, trustworthy red), the statistically-hungry judge sweep nightly (large n, alerted), canary on live traffic for what offline can't see.
- **Pinning doesn't buy determinism on a shared endpoint** — the 2025 batch-invariance result explains why — so quantify the residual noise instead of pretending it away.
- **The dataset and the judge are measuring instruments.** Version and hash the dataset; pin and calibrate the judge. Silent dataset drift and judge drift both manufacture phantom regressions that burn days.
- **Gate per slice and on tails**, not just the mean: an aggregate can hide a collapsed subpopulation or a catastrophic safety tail.
- **A gate's credibility is its entire value.** A flaky gate is worse than no gate because it launders real failures into noise. Spend the credibility carefully: unit-test the gate math, quarantine irreducible flakiness, and keep the red trustworthy.

> **Saying it out loud.** If you had to compress the whole chapter into one answer: evaluation is a control loop, not a phase; every pipeline is the same seven boxes; and the score is a random variable, not a number. That third one drives everything else — you gate on a Wilson lower bound instead of a point estimate, and you require a regression to be both statistically significant under Welch and larger than an effect floor you actually care about. Tier the triggers so cheap deterministic floors run on the PR, where red has to stay trustworthy, and the statistically hungry judge sweep runs nightly, where the sample size can support it. Treat the dataset and the judge as measuring instruments — version and hash the dataset, pin and calibrate the judge — because silent drift in either one manufactures phantom regressions that burn days of investigation. And the closer: a gate's credibility is its entire value, which is why a flaky gate is worse than no gate at all.

---

*This chapter is part of "Agentic AI Evaluation — A Practical Guide." It treats evaluation as a control loop wired into CI, not a phase — the mechanisms here (statistical gates, tiered triggers, versioned goldens, per-slice regression, judge calibration) are what keep an agent's quality from rotting one innocent change at a time. Build the seven boxes, gate on a confidence bound, tier your triggers, and defend the dataset and the judge as the instruments they are.*
