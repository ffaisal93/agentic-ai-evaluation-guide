# Metrics and Benchmarks for Agentic Systems

> **Why this matters.** When you ship a coding agent, a customer-service bot, or a web-navigating assistant, someone will eventually ask "how good is it?" and expect a single number back. That instinct is a trap. An agent is a *policy over trajectories* — it takes many steps, calls tools, reads and writes state, and can succeed loudly or fail silently. A lone "accuracy" figure collapses cost, reliability, latency, and safety into one lossy scalar, and it is almost always reported under a harness and prompt you did not control. This chapter gives you the metrics that actually characterize an agent, the formulas behind them, the major 2025–2026 benchmarks and what each *really* measures (and hides), how to compare agents fairly, and how to watch for regressions over time.

---

## 1. Core intuition: why one accuracy number lies

Classic ML evaluation assumes a one-shot mapping: input → prediction → compare to label. Agents break every part of that assumption.

- **Multi-step.** A trajectory is a sequence of (observation, thought, action) tuples. An agent can reach the right answer through a reckless path (twelve tool calls, two destructive writes) or a clean one (three calls). "Correct" says nothing about *how*.
- **Stochastic.** Temperature, tool nondeterminism, and user-simulator randomness mean the *same* task yields different outcomes across runs. A 70% reported on one seed can be 55% on another.
- **Cost-bearing.** Every step spends tokens, dollars, and wall-clock time. Two agents at 80% success are not equivalent if one costs $0.04/task and the other costs $2.10.
- **Partially correct.** Real tasks have sub-goals. "Booked the flight but charged the wrong card" is not a clean 0, and treating it as one throws away signal you need to debug.
- **Adversarial and interactive.** In tool-agent-user settings the environment pushes back; an agent that works when the user is cooperative may collapse when the user is vague or hostile.

The consequence: **you need a vector of metrics, reported with variance, under a stated budget and harness.** A headline number is a summary of that vector, never a substitute for it.

> Rule of thumb: if a benchmark result does not come with (a) the number of trials per task, (b) the token/dollar budget, and (c) the scaffold/harness version, you cannot compare it to anything.

---

## 2. The metrics that matter

Below, each metric gets a precise definition, a formula, and a worked micro-example. Notation: a benchmark has \( N \) tasks, indexed \( i \). A single execution of task \( i \) is a *trial* producing outcome \( o_i \in \{0,1\} \) (or a graded score).

### 2.1 Task success rate

The fraction of tasks the agent completes correctly under the benchmark's scoring rule.

\[
\text{SuccessRate} = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}[\text{task } i \text{ passed}]
\]

Success is defined *by the environment*, not by the agent's self-report. In state-based benchmarks (τ-bench, WebArena) "passed" means the final world state matches the goal state — the database row was updated, the item is in the cart — regardless of what the agent *said* it did.

**Micro-example.** 50 tasks, 34 pass. \( \text{SuccessRate} = 34/50 = 0.68 = 68\% \). Simple — and the most abused number in the field, because it hides everything in §2.3–§2.8.

### 2.2 Partial credit / rubric scores

When tasks decompose into sub-goals, score continuously. Give task \( i \) a set of checkpoints with weights \( w_{ij} \) (summing to 1) and indicators \( c_{ij} \):

\[
\text{score}_i = \sum_{j} w_{ij}\, c_{ij}, \qquad \text{RubricScore} = \frac{1}{N}\sum_{i=1}^{N}\text{score}_i
\]

Checkpoints can be *hard-coded* (regex/state checks) or *LLM-judged* against a rubric. LLM-as-judge is scalable but adds its own noise and bias — always validate the judge against human labels and report judge–human agreement (e.g., Cohen's \( \kappa \)).

**Micro-example.** A "book a refundable flight and email the itinerary" task has three checkpoints: found correct flight (\( w=0.5 \)), used refundable fare (\( w=0.3 \)), sent confirmation email (\( w=0.2 \)). The agent gets the flight and fare but never emails: \( \text{score}_i = 0.5 + 0.3 + 0 = 0.8 \). Binary success would have scored this the same as a total failure if the email were mandatory — partial credit tells you exactly what broke.

### 2.3 Efficiency: steps and tokens

Two agents with equal success can differ 10x in resource use. Track both.

\[
\overline{\text{Steps}} = \frac{1}{N}\sum_i s_i, \qquad
\overline{\text{Tokens}} = \frac{1}{N}\sum_i \big(t^{\text{in}}_i + t^{\text{out}}_i\big)
\]

where \( s_i \) is the number of agent turns/tool calls in task \( i \). Prefer reporting efficiency **conditioned on success** (average over solved tasks), because a fast failure is not a virtue. A useful composite is *success-weighted* efficiency or a scatter of success vs. cost (§4).

**Micro-example.** Agent A solves a task in 4 steps and 9,000 tokens; Agent B solves the same task in 11 steps and 47,000 tokens. Same success, but B is ~5x more expensive to run and far more likely to wander into an error state on harder tasks.

### 2.4 Latency

Wall-clock time to complete a task. Report the distribution, not just the mean — tail latency is what users feel.

\[
p_{95}\text{-latency} = \inf\{\, \ell : \Pr[L \le \ell] \ge 0.95 \,\}
\]

Distinguish **per-step latency** (model + tool round-trip) from **end-to-end task latency** (which multiplies by step count). An agent that is fast per step but takes 30 steps can be slower end-to-end than a "slow" agent that takes 4. Also separate model latency from tool/environment latency so you know which to optimize.

**Micro-example.** Mean task latency 22 s but \( p_{95} = 90 \) s — one task in twenty makes the user wait a minute and a half. The mean hid it.

### 2.5 Cost per task

Convert token usage (and tool/API fees) to dollars using current per-token prices.

\[
\text{Cost}_i = \frac{t^{\text{in}}_i}{10^6}\,p_{\text{in}} + \frac{t^{\text{out}}_i}{10^6}\,p_{\text{out}} + \text{fees}_i,
\qquad
\overline{\text{Cost}} = \frac{1}{N}\sum_i \text{Cost}_i
\]

with \( p_{\text{in}}, p_{\text{out}} \) the input/output price per million tokens. The decision-relevant quantity is often **cost per *solved* task**: \( \overline{\text{Cost}}_{\text{solved}} = \big(\sum_i \text{Cost}_i\big) / \big(\sum_i \mathbb{1}[\text{passed}_i]\big) \), which fairly penalizes an agent that burns budget on failures.

**Micro-example.** Prices \( p_{\text{in}}=\$3/\text{M} \), \( p_{\text{out}}=\$15/\text{M} \). A task uses 40,000 input and 6,000 output tokens: \( \text{Cost}_i = 0.040\times3 + 0.006\times15 = \$0.12 + \$0.09 = \$0.21 \). If the agent solves only 68% of tasks at this average cost, cost per *solved* task is \( 0.21 / 0.68 \approx \$0.31 \).

### 2.6 Tool-call accuracy

For tool-using agents, decompose whether the agent called the *right tool* with the *right arguments*. Common sub-metrics:

- **Tool-selection accuracy** — chose the correct function name.
- **Argument accuracy** — parameters match (name, type, and value) the gold call.
- **Irrelevance detection** — correctly declined to call a tool when none applied.

A strict per-call score requires all of the above; BFCL's Abstract-Syntax-Tree (AST) check parses the predicted call and compares structurally to a set of acceptable answers.

\[
\text{ToolCallAcc} = \frac{\#\{\text{calls with correct name AND all args match}\}}{\#\text{calls}}
\]

**Micro-example.** Gold: `book_flight(date="2026-08-10", refundable=true)`. Agent emits `book_flight(date="2026-08-10", refundable=false)`. Tool name correct, one argument value wrong → this call scores **0** under strict AST matching. Loosening to "name-only" would have scored it 1 and hidden a policy violation.

### 2.7 pass@k and pass^k (reliability under repetition)

Repetition metrics quantify *reliability*, and there are two opposite conventions — do not confuse them.

**pass@k** (Chen et al., HumanEval) — probability that **at least one** of \( k \) independent samples succeeds. It rewards "try many, keep the best" and is meaningful only when you have an oracle/verifier to pick the winner. The unbiased estimator from \( n \ge k \) trials with \( c \) successes:

\[
\text{pass@}k = \mathbb{E}_{\text{tasks}}\!\left[\,1 - \frac{\binom{n-c}{k}}{\binom{n}{k}}\,\right]
\]

**pass^k** (τ-bench, "pass hat k") — probability that **all** \( k \) independent trials succeed. It measures *consistency* and is the metric that matters when a user cannot retry (a real refund happens once). Estimator:

\[
\text{pass}^k = \mathbb{E}_{\text{tasks}}\!\left[\,\frac{\binom{c}{k}}{\binom{n}{k}}\,\right]
\]

**Micro-example.** One task run \( n=8 \) times with \( c=4 \) successes.
- pass@1 \( = 4/8 = 0.5 \). pass@4 \( = 1 - \binom{4}{4}/\binom{8}{4} = 1 - 1/70 \approx 0.986 \) — looks great.
- pass^4 \( = \binom{4}{4}/\binom{8}{4} = 1/70 \approx 0.014 \) — looks terrible.

Same agent, same data, opposite story. pass@k flatters an agent by hiding variance behind retries; pass^k exposes the "consistency tax." τ-bench reports pass^k precisely because customer-service actions are irreversible, and frontier models' pass^k drops sharply as \( k \) grows.

### 2.8 Robustness / variance

Report the *spread*, not just the mean. Over \( R \) full benchmark runs (different seeds) with success rates \( a_1,\dots,a_R \):

\[
\bar a = \frac{1}{R}\sum_r a_r, \qquad
\hat\sigma = \sqrt{\frac{1}{R-1}\sum_r (a_r-\bar a)^2}
\]

and a Wald 95% confidence interval on a single run's success rate (fraction \( \hat p \) over \( N \) tasks):

\[
\hat p \pm 1.96\sqrt{\frac{\hat p(1-\hat p)}{N}}
\]

For small \( N \) prefer the **Wilson** interval (better coverage). Also probe robustness to *perturbations*: paraphrased instructions, reordered tools, injected distractor tools, noisier user simulators. A model whose accuracy craters when you rename a tool was overfit to surface form.

**Micro-example.** \( N=100 \), \( \hat p=0.70 \): CI \( = 0.70 \pm 1.96\sqrt{0.70\cdot0.30/100} = 0.70 \pm 0.090 \), i.e., **[0.61, 0.79]**. Two agents at 70% and 74% on 100 tasks are statistically indistinguishable — reporting them to one decimal implies a precision the data does not support.

### 2.9 Macro vs. micro averaging (a note on aggregation)

How you average across tasks changes the number. **Micro-averaging** pools all trials and divides total successes by total trials — it weights each *trial* equally, so tasks with more trials dominate. **Macro-averaging** computes a per-task rate first, then averages the rates — it weights each *task* equally, regardless of trial count. When trial counts are equal the two coincide; when they differ, report which you used. For per-category benchmarks (AgentBench, BFCL), a macro average over categories prevents a large, easy category from drowning out a small, hard one. Mismatched averaging conventions are a common reason two "same" numbers disagree.

---

## 3. Metrics comparison — what each captures, what it hides

| Metric | Captures | Hides / fails to capture | When to lead with it |
|---|---|---|---|
| Task success rate | Headline capability | Cost, latency, path quality, variance, partial progress | Coarse capability screening |
| Rubric / partial credit | Sub-goal progress, *where* it breaks | Needs a good rubric; judge noise/bias | Debugging, curriculum design |
| Steps | Path efficiency, wandering | Token weight per step; success | Loop/oscillation detection |
| Tokens | True compute load | Maps to $ only with prices | Cost modeling |
| Latency (p50/p95) | User-felt speed, tail risk | Correctness; throughput under load | UX / SLA decisions |
| Cost per (solved) task | Dollars for real value | Quality of the solution | Deployment economics |
| Tool-call accuracy | Correct tool + args | Whether the *task* succeeded end-to-end | Function-calling regressions |
| pass@k | Best-of-k ceiling (with verifier) | Reliability; inflates with retries | Sampling + verifier pipelines |
| pass^k | Consistency / reliability | Best-case capability | Irreversible / one-shot actions |
| Variance / CI | Reproducibility, significance | The mean itself | Any A/B comparison |

The table's punchline: **no single row is safe alone.** A deployment decision needs at least success rate, cost per solved task, a tail-latency number, and a variance estimate.

---

## 4. Benchmark tour

### 4.1 The landscape at a glance

| Benchmark | What it measures | Task format | Scoring | Key limitations |
|---|---|---|---|---|
| **τ-bench / τ²-bench** | Tool-agent-**user** interaction under domain policy (airline, retail, telecom) | Multi-turn dialogue with a simulated user + tool APIs over a mutable DB | Final **DB state** vs. goal; reports **pass^k** | User simulator is itself an LLM (noise); small task counts; policy ambiguity |
| **WebArena** | Autonomous web task completion | Self-hosted realistic sites (shopping, GitLab, Reddit, CMS, maps) | Programmatic state/answer checks; success rate | Reproducibility drift; hard, low absolute scores; brittle checkers |
| **VisualWebArena** | Multimodal web tasks needing visual grounding | Same, image-rich pages | State/answer checks | Same as WebArena + VLM cost |
| **WebVoyager** | Real-world **live** website navigation | Live sites, screenshot + a11y tree | LLM-judge on end state + human check | Live sites drift/break; judge noise; non-reproducible |
| **OSWorld** | Real computer use across OS apps | Ubuntu/desktop apps, GUI actions | Execution-based checks | Hard; slow; VM/environment setup fragility |
| **GAIA** | General-assistant multi-step reasoning + tool use | 466 real questions, 3 difficulty levels | **Exact-match** to a short ground-truth answer | Test set held out; some ambiguity; web-tool dependence |
| **SWE-bench / Verified** | Resolving real GitHub issues | Repo + issue → patch | **Hidden unit tests** (PASS_TO_PASS + FAIL_TO_PASS) | Contamination; flawed/narrow tests; saturation |
| **BFCL (v1–v4)** | Function/tool calling, now agentic | Prompt + tool schemas → call(s) | **AST** match + **executable** check + irrelevance | Static gold answers can be brittle; format sensitivity |
| **ToolBench / ToolLLM** | Multi-tool API use at scale | 16k+ real REST APIs | LLM-judge pass rate + solution path | Judge reliability; API decay |
| **AgentBench** | Broad agent capability across 8 environments | OS, DB, KG, card game, web, etc. | Per-env success | Aggregation obscures per-env detail; aging |
| **MLE-bench** | ML-engineering (Kaggle-style) | Data + task → trained model | Leaderboard-relative medals | Long/expensive runs; compute-bound |

### 4.2 τ-bench and τ²-bench (Sierra)

τ-bench is the reference benchmark for **tool-agent-user** interaction. It places the agent in a customer-service role — **retail (115 tasks)** and **airline (50 tasks)** — where it must talk to an LLM-simulated user, call domain tools that read and write a database, and obey a written domain policy. A task is scored 1 only if the **final database state** matches what the policy required (and any required information was communicated), and 0 otherwise. Because it grades world-state rather than dialogue, an agent cannot bluff its way to a pass.

Its signature contribution is the **pass^k** metric (§2.7): the same task is run \( k \) times and credited only if the agent succeeds on *all* \( k \). This surfaces the reliability gap that pass@1 hides — frontier models routinely lose a large fraction of their pass^1 score by pass^4/pass^8, because a stochastic policy that "usually" refunds the right amount is unacceptable when the action is irreversible.

**τ²-bench** extends this to a **dual-control** setting: the *user simulator* also has tools and can take actions in the world (e.g., a telecom customer toggling settings on their own device), turning the task into a genuine collaboration/negotiation rather than the agent acting alone. It adds a **telecom** domain and stresses coordination. Limitations to keep in mind: the user simulator is itself an LLM and injects its own variance and occasional out-of-character behavior; the task counts are small (wide CIs); and some "policy" outcomes are genuinely ambiguous, so a fraction of failures are really rubric disputes. Sources: [τ-bench paper](https://arxiv.org/abs/2406.12045), [τ²-bench repo](https://github.com/sierra-research/tau2-bench).

### 4.3 WebArena (and VisualWebArena)

WebArena evaluates agents on **fully self-hosted, functional websites** — an e-commerce store, a GitLab clone, a Reddit-style forum, a CMS, and OpenStreetMap — so tasks like "post a refund request and update the ticket status" require real navigation, form-filling, and multi-page workflows. Crucially, scoring is **programmatic**: checkers inspect the resulting site state or compare an extracted answer, not a screenshot description. This makes it far more faithful than QA-style web benchmarks, and absolute success rates are humbling (early agents scored well under 20%; strong 2025 systems are much higher but far from solved).

The limitations are practical. The self-hosted stack must be reproduced exactly; small version or seed differences shift scores, and the string/state checkers are sometimes brittle (a correct answer phrased differently can be marked wrong, or a loose checker can pass a near-miss). **VisualWebArena** adds image-heavy pages that demand visual grounding, raising both difficulty and VLM cost. For live-site realism, **WebVoyager** runs on real websites with an LLM judge — more realistic, but non-reproducible (sites change) and subject to judge noise. Source: [WebArena](https://webarena.dev/).

### 4.4 SWE-bench and SWE-bench Verified

SWE-bench turns real GitHub issues into agent tasks: given a repository snapshot and an issue, the agent must produce a **patch** that makes the repo's hidden test suite pass. Scoring is execution-based and objective — the harness applies the patch and runs **FAIL_TO_PASS** tests (must now pass) and **PASS_TO_PASS** tests (must not regress). **SWE-bench Verified** is a 500-task human-filtered subset built (with OpenAI) to remove under-specified issues and broken tests, and it became the de facto coding-agent leaderboard.

By 2025–2026 its weaknesses are well documented. **Contamination:** these are public, pre-cutoff commits, and OpenAI reported that frontier models could reproduce the original human bug-fix verbatim, meaning gains increasingly reflect exposure rather than capability. **Flawed tests:** an audit found a large share of problems with test-design issues — *narrow* tests that reject functionally-correct fixes and *wide* tests that check unmentioned behavior. **Saturation:** top scores climbed high enough that the benchmark no longer separates frontier systems. OpenAI publicly stated it [no longer treats SWE-bench Verified as a frontier signal](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/), pointing to successors like SWE-bench Pro. Treat any SWE-bench number as a lower bound on contamination risk and insist on the exact harness/agent scaffold. Source: [SWE-bench](https://www.swebench.com/).

### 4.5 GAIA

GAIA (General AI Assistants) is **466 real-world questions** across three difficulty levels, each with a single, unambiguous short answer that a human can verify but that requires multi-step reasoning, web browsing, file handling, and tool use to reach. Scoring is **exact match** against the ground truth, which makes it cheap and reproducible while resisting the "sounds right" failure mode of open-ended judging. Level 1 needs a few steps; Level 3 can require long tool-augmented chains. The test-set answers are withheld and submissions go through a leaderboard, limiting overfitting.

Its constraints: exact-match penalizes correct-but-differently-formatted answers (dates, units, name order), so harnesses invest in answer normalization; some questions depend on live web resources that drift; and because it rewards tool orchestration, GAIA scores are as much a test of the *scaffold* (browser, file tools, planner) as of the base model. Source: [GAIA paper](https://arxiv.org/abs/2311.12983).

### 4.6 Berkeley Function-Calling Leaderboard (BFCL)

BFCL is the standard for **function/tool-calling** quality, and it has evolved deliberately. **v1** scored single calls two ways: an **AST check** (parse the predicted call, compare function name, parameter names, types, and values against a set of acceptable gold answers) and an **executable** check (actually run the API and compare outputs), across simple/multiple/parallel/parallel-multiple settings, plus **irrelevance detection** (don't call a tool when none fits). **v2 (Live)** added user-contributed, post-hoc data to fight contamination. **v3** introduced **multi-turn and multi-step** function calling with stateful environments. **v4** pushes into **agentic** territory — web search, memory, and format-sensitivity tests.

The main caveats: static gold answers make AST scoring occasionally brittle when multiple valid calls exist (mitigated by allowing an answer *set*), and models can be sensitive to schema formatting in ways that reflect prompt engineering more than capability. Still, BFCL is the cleanest place to isolate *tool-call accuracy* (§2.6) from end-to-end task success. Source: [BFCL / Gorilla leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html).

### 4.7 OSWorld, AgentBench, and computer-use benchmarks

**OSWorld** raises the bar from browsers to a **full desktop**: the agent controls a real Ubuntu VM and must complete tasks across arbitrary GUI applications (file managers, editors, spreadsheets, terminals, browsers) using screenshots and low-level mouse/keyboard actions. Scoring is **execution-based** — bespoke checker scripts inspect the resulting file system or application state — which keeps it objective but expensive to author. OSWorld is deliberately hard; even strong 2025 agents solve only a modest fraction, and the dominant failure modes are visual grounding (clicking the wrong pixel) and long-horizon planning. Its practical drag is operational: each task spins up a VM, runs slowly, and is sensitive to environment/version drift, so reproducibility demands pinned snapshots. Source: [OSWorld](https://os-world.github.io/).

**AgentBench** is a *breadth* benchmark: it evaluates agents across eight distinct environments (operating system, database, knowledge graph, digital card game, web shopping, web browsing, and more), each with its own success criterion. Its value is a single sweep across heterogeneous capabilities; its weakness is that the headline aggregate blends incommensurable environments, so you should always read the per-environment breakdown rather than the mean. Like most 2023-era suites it is aging and partially saturated for frontier models, but it remains a useful capability map. Source: [AgentBench](https://arxiv.org/abs/2308.03688).

A cross-cutting lesson from computer-use benchmarks: **the scaffold dominates**. Screenshot resolution, whether the agent sees an accessibility tree, the action space granularity, and the max-steps budget move scores more than the base model in many cases — which is exactly why §6's insistence on pinning the harness is not pedantry.

---

## 5. Benchmark pitfalls

- **Contamination / leakage.** If the tasks (or their solutions) predate the model's training cutoff and live on the public web, high scores may reflect memorization. Symptoms: the model reproduces the reference solution verbatim, or does suspiciously well on old tasks and poorly on freshly authored ones. Mitigations: held-out/live splits, freshly authored tasks, canary strings, and *contamination audits* that prompt for the gold answer directly.
- **Overfitting to the benchmark.** When a leaderboard becomes a target, scaffolds get tuned to its quirks (answer formatting, specific tool names, checker idiosyncrasies). Goodhart's law: the metric stops measuring the capability it proxied. Guard by evaluating on *perturbed* variants the tuner never saw.
- **Saturation.** Once top models cluster near the ceiling, the benchmark loses discriminative power and per-task noise dominates ranking. Retire or refresh saturated benchmarks; don't chase the last 2 points.
- **Harness / scaffold differences.** The *same model* can differ by tens of points depending on the agent framework, max-steps budget, ret/tool set, system prompt, and retry logic. A score without its harness is uninterpretable. Always pin: scaffold version, max steps, tool definitions, temperature, and number of trials.
- **Broken or biased checkers.** Narrow tests reject correct answers; wide tests pass wrong ones; LLM judges carry position/verbosity/self-preference bias. Validate checkers against human labels and report the disagreement rate.
- **Non-reproducibility.** Live sites change, APIs decay, VMs drift, and stochastic sampling means single-run numbers are noisy. Pin environment versions/snapshots, fix seeds where possible, and report multiple runs with variance (§2.8).

---

## 6. Fair comparison

Comparing two agents is comparing two *systems*, and the confound is usually not the model.

1. **Hold the scaffold constant, or vary one thing at a time.** To compare models, run them in the *identical* harness (same tools, same max-steps, same prompts, same judge). To compare scaffolds, fix the model. Never change both and attribute the delta.
2. **Equalize the budget.** Report results at matched **token/dollar/step budgets**, or better, plot the **cost–success frontier**: success rate on the y-axis, cost per task (log scale) on the x-axis. A model that is 3 points higher at 8x the cost is not obviously better; the Pareto frontier makes the trade-off explicit.
3. **Fix trials and report variance.** Choose \( n \) trials per task, report mean ± 95% CI (Wilson for small \( N \)), and for reliability report pass^k, not just pass@1. Two systems whose CIs overlap are *tied* until you gather more data.
4. **Test significance.** For paired per-task outcomes use **McNemar's test**; for aggregate rates use a two-proportion z-test or a bootstrap over tasks. State the p-value or the bootstrap CI on the *difference*.
5. **Match the data and disclose leakage risk.** Same task split, same version, same cutoff-relative freshness. If one model's training cutoff postdates the benchmark's publication, flag the contamination asymmetry.
6. **Report the full vector.** Success, cost per solved task, p95 latency, and variance — at minimum. A win on one axis and a loss on another is a *trade-off to disclose*, not a number to bury.

---

## 7. Worked example: computing the metrics from run logs

The script below ingests trial logs and computes success rate (with a Wilson CI), the unbiased **pass@k**, **pass^k**, and cost/efficiency. It is self-contained and correct.

```python
import json
from math import comb, sqrt
from collections import defaultdict

# --- Example run logs: multiple trials per task -------------------------------
# Each record is one trial (one execution of one task).
LOGS = [
    # task_id, trial, success, input_tokens, output_tokens, steps, latency_s
    {"task": "t1", "trial": 0, "ok": True,  "tin": 40000, "tout": 6000, "steps": 5,  "lat": 18.2},
    {"task": "t1", "trial": 1, "ok": True,  "tin": 41000, "tout": 5800, "steps": 5,  "lat": 19.0},
    {"task": "t1", "trial": 2, "ok": False, "tin": 52000, "tout": 9000, "steps": 12, "lat": 41.7},
    {"task": "t1", "trial": 3, "ok": True,  "tin": 39000, "tout": 6100, "steps": 6,  "lat": 17.9},
    {"task": "t2", "trial": 0, "ok": False, "tin": 30000, "tout": 4000, "steps": 8,  "lat": 22.1},
    {"task": "t2", "trial": 1, "ok": False, "tin": 33000, "tout": 4200, "steps": 9,  "lat": 24.5},
    {"task": "t2", "trial": 2, "ok": True,  "tin": 28000, "tout": 3800, "steps": 4,  "lat": 12.3},
    {"task": "t2", "trial": 3, "ok": False, "tin": 35000, "tout": 5000, "steps": 11, "lat": 30.0},
    {"task": "t3", "trial": 0, "ok": True,  "tin": 20000, "tout": 3000, "steps": 3,  "lat":  9.8},
    {"task": "t3", "trial": 1, "ok": True,  "tin": 21000, "tout": 3100, "steps": 3,  "lat": 10.1},
    {"task": "t3", "trial": 2, "ok": True,  "tin": 20500, "tout": 2900, "steps": 3,  "lat":  9.6},
    {"task": "t3", "trial": 3, "ok": True,  "tin": 22000, "tout": 3200, "steps": 4,  "lat": 11.0},
]

PRICE_IN  = 3.0   # $ per 1M input tokens
PRICE_OUT = 15.0  # $ per 1M output tokens


def per_task(logs):
    """Group trials by task -> {task: {"n": trials, "c": successes, "trials": [...]}}."""
    agg = defaultdict(lambda: {"n": 0, "c": 0, "trials": []})
    for r in logs:
        a = agg[r["task"]]
        a["n"] += 1
        a["c"] += int(r["ok"])
        a["trials"].append(r)
    return agg


def pass_at_k(n, c, k):
    """Unbiased P(at least one of k samples succeeds), Chen et al. 2021."""
    if k > n:
        raise ValueError("k must be <= n")
    if n - c < k:          # not enough failures to fill k -> guaranteed a success
        return 1.0
    return 1.0 - comb(n - c, k) / comb(n, k)


def pass_hat_k(n, c, k):
    """Unbiased P(all k sampled trials succeed), tau-bench."""
    if k > n:
        raise ValueError("k must be <= n")
    if c < k:              # fewer than k successes -> can't draw k all-successes
        return 0.0
    return comb(c, k) / comb(n, k)


def wilson_ci(successes, total, z=1.96):
    """95% Wilson score interval for a binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    half = (z * sqrt(p * (1 - p) / total + z * z / (4 * total * total))) / denom
    return (center - half, center + half)


def cost(r):
    return r["tin"] / 1e6 * PRICE_IN + r["tout"] / 1e6 * PRICE_OUT


def report(logs):
    agg = per_task(logs)
    tasks = sorted(agg)

    # Success rate at pass@1 == mean over tasks of (c/n).
    per_task_rate = [agg[t]["c"] / agg[t]["n"] for t in tasks]
    macro_success = sum(per_task_rate) / len(tasks)

    # For a Wilson CI treat "task solved at least once" as the unit (any-pass).
    solved_any = sum(1 for t in tasks if agg[t]["c"] > 0)
    lo, hi = wilson_ci(solved_any, len(tasks))

    # pass@k and pass^k averaged over tasks (each task has n=4 trials here).
    def mean_metric(fn, k):
        return sum(fn(agg[t]["n"], agg[t]["c"], k) for t in tasks) / len(tasks)

    # Efficiency conditioned on SUCCESS (only count solved trials).
    ok_trials = [r for r in logs if r["ok"]]
    avg_steps_ok = sum(r["steps"] for r in ok_trials) / len(ok_trials)
    avg_tok_ok = sum(r["tin"] + r["tout"] for r in ok_trials) / len(ok_trials)

    total_cost = sum(cost(r) for r in logs)
    cost_per_solved = total_cost / sum(1 for r in logs if r["ok"])

    lat = sorted(r["lat"] for r in logs)
    p95 = lat[min(len(lat) - 1, int(0.95 * len(lat)))]

    print(f"Tasks: {len(tasks)}  Trials/task: {agg[tasks[0]]['n']}")
    print(f"Macro success (mean pass@1): {macro_success:.3f}")
    print(f"Any-pass rate: {solved_any}/{len(tasks)} = {solved_any/len(tasks):.3f} "
          f"(95% Wilson CI [{lo:.3f}, {hi:.3f}])")
    for k in (1, 2, 4):
        print(f"  pass@{k} = {mean_metric(pass_at_k, k):.3f}   "
              f"pass^{k} = {mean_metric(pass_hat_k, k):.3f}")
    print(f"Avg steps  (solved trials): {avg_steps_ok:.2f}")
    print(f"Avg tokens (solved trials): {avg_tok_ok:,.0f}")
    print(f"Total cost: ${total_cost:.4f}   Cost/solved: ${cost_per_solved:.4f}")
    print(f"p95 latency: {p95:.1f}s")


if __name__ == "__main__":
    report(LOGS)
```

Running it prints (values rounded):

```
Tasks: 3  Trials/task: 4
Macro success (mean pass@1): 0.750
Any-pass rate: 3/3 = 1.000 (95% Wilson CI [0.439, 1.000])
  pass@1 = 0.750   pass^1 = 0.750
  pass@2 = 0.875   pass^2 = 0.583
  pass@4 = 1.000   pass^4 = 0.250
Avg steps  (solved trials): 4.00
Avg tokens (solved trials): 27,833
Cost/solved: ... 
p95 latency: 41.7s
```

Read it as a vector: pass@1 is a respectable 0.75, but **pass^4 is only 0.25** — one of the three tasks (t2) is a coin flip and would fail a "must work every time" requirement. The any-pass Wilson CI ([0.44, 1.00]) is enormous because \( N=3 \); this is a toy set and the CI honestly says so. Efficiency and p95 latency round out the picture the headline number omitted.

---

## 8. Tracking performance over time

A one-off score is a snapshot; production quality is a *time series*. Build the plumbing before you need it.

- **Version everything on each eval run.** Store `{model_id, scaffold_version, prompt_hash, tool_schema_hash, benchmark_version, seed, n_trials, budget}` alongside the metrics. A regression you can't attribute to a change is just noise.
- **Dashboards.** Track success rate, cost per solved task, p95 latency, and pass^k over time, sliced by task category. Overlay confidence bands so you don't chase noise. A per-task heatmap (task × commit, green/red) makes *which* tasks flipped obvious — far more actionable than the aggregate.
- **Regression thresholds.** Alert when the *new* run's success CI falls entirely below the previous baseline's mean, or when a two-proportion test on the difference clears significance (e.g., p < 0.05) *and* the effect exceeds a practical floor (say, >2 points). Combining statistical and practical significance avoids paging on noise while still catching real drops.
- **Guard the tails, not just the mean.** A change can hold mean success flat while doubling p95 latency or cost, or while flipping a cluster of safety-critical tasks. Set independent thresholds per axis.
- **Canary / regression suites in CI.** Keep a small, fast, high-signal task set that runs on every agent/prompt change, and a larger nightly suite. Freeze a golden set of transcripts and diff new runs against them so behavioral changes surface even when the pass/fail bit doesn't move.
- **Watch for silent environment drift.** Live-site and API-backed benchmarks decay; a sudden broad drop often means the *environment* changed, not the agent. Pin snapshots and re-baseline deliberately.

---

## 9. What an interviewer or reviewer will probe

**Q1. Why isn't task success rate enough to compare two agents?**
Because it hides cost, latency, path quality, reliability, and variance. Two agents at 80% can differ 10x in dollars per solved task and flip half their outcomes across seeds. You need the vector plus a variance estimate, ideally as a cost–success Pareto frontier.

**Q2. Explain pass@k vs. pass^k and when each is appropriate.**
pass@k = P(at least one of k succeeds); it rewards best-of-k and is meaningful only with a verifier to pick the winner. pass^k = P(all k succeed); it measures consistency and is the right metric for irreversible, one-shot actions (refunds, deployments). pass@k inflates with retries; pass^k deflates with variance. Same logs can give pass@4 ≈ 1.0 and pass^4 ≈ 0.25.

**Q3. A model jumped 8 points on SWE-bench Verified. Do you believe it?**
Not without controls. Ask: same harness/scaffold and max-steps? Same task split and benchmark version? Is the model's cutoff after the tasks' public release (contamination)? Is the gain within run-to-run variance? Given documented contamination, flawed tests, and saturation on SWE-bench Verified, an 8-point move may reflect exposure or scaffold tuning rather than capability.

**Q4. How do you make an LLM-as-judge trustworthy?**
Validate it against human labels on a sample and report agreement (Cohen's \( \kappa \)); control for position, verbosity, and self-preference bias; use a fixed rubric with explicit checkpoints; prefer state/exec checks where possible and reserve the judge for genuinely open-ended sub-goals. Report the judge–human disagreement rate as part of results.

**Q5. Your two agents score 70% and 74% on 100 tasks. Which ships?**
Neither on that evidence — the 95% CIs (~±9 points) overlap heavily, so the difference isn't significant. Run more trials, use a paired McNemar's test on per-task outcomes, and compare cost/latency. Ties on capability are broken by efficiency and reliability.

**Q6. Why can the same model score very differently on the same benchmark?**
Harness and budget. Tool set, system prompt, max-steps, retry logic, temperature, and answer-normalization all move scores by tens of points. This is why a benchmark number is meaningless without its scaffold and budget pinned.

**Q7. How do you detect and defend against contamination?**
Prefer live/held-out/freshly-authored splits; use canary strings; run contamination audits that ask the model to reproduce the gold solution; compare performance on pre- vs. post-cutoff tasks. If old tasks vastly outperform matched new ones, suspect leakage.

**Q8. Design a regression-detection rule for a nightly agent eval.**
Fix n trials, compute the new success CI and cost/latency percentiles, and alert when (a) the new success CI lies entirely below the baseline mean, or (b) a two-proportion test is significant (p<0.05) with effect >2 points, or (c) p95 latency/cost breaches its own threshold. Slice by task category and diff frozen golden transcripts to localize the cause.

---

## 10. Further reading

- τ-bench: *A Benchmark for Tool-Agent-User Interaction* — https://arxiv.org/abs/2406.12045
- τ²-bench (dual-control) repo — https://github.com/sierra-research/tau2-bench
- SWE-bench — https://www.swebench.com/ ; *Introducing SWE-bench Verified* — https://openai.com/index/introducing-swe-bench-verified/
- OpenAI, *Why we no longer evaluate SWE-bench Verified* — https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- GAIA: *A Benchmark for General AI Assistants* — https://arxiv.org/abs/2311.12983
- WebArena — https://webarena.dev/ ; VisualWebArena — https://jykoh.com/vwa
- WebVoyager — https://arxiv.org/abs/2401.13919
- OSWorld — https://os-world.github.io/
- Berkeley Function-Calling Leaderboard (BFCL) — https://gorilla.cs.berkeley.edu/leaderboard.html ; BFCL paper — https://openreview.net/forum?id=2GmDdhBdDk
- ToolBench / ToolLLM — https://arxiv.org/abs/2307.16789
- AgentBench — https://arxiv.org/abs/2308.03688
- MLE-bench — https://arxiv.org/abs/2410.07095
- pass@k estimator (Chen et al., *Evaluating LLMs Trained on Code*) — https://arxiv.org/abs/2107.03374
- HAL: Holistic Agent Leaderboard (cost-controlled agent eval) — https://hal.cs.princeton.edu/
