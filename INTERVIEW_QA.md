# Agentic AI Evaluation — Master Interview Bank

A comprehensive, senior-level interview-prep bank for **Agentic AI + Evaluation** roles
(AI/ML Engineer, Applied Scientist, Eval/Red-Team, Agent Platform, and Research Engineer tracks).

This bank accompanies *"Agentic AI Evaluation — A Practical Guide"* and maps 1:1 onto its 12 chapters.
It is written to help you convince a **senior interviewer** that you understand agentic systems and
their evaluation *cold* — not just definitions, but trade-offs, failure modes, and how you would
build and defend a real evaluation program.

> **Math rendering note:** This book renders with **MathJax** (KaTeX disabled). Write inline math as
> `\( ... \)` and display math as `\[ ... \]`. Never use single-dollar `$...$` — literal dollar signs
> (e.g. costs like \(\$0.003\) per call) render as plain text.

---

## How to Use This Bank

**The goal is not memorization — it is fluent framing.** A senior interviewer probes for depth by
asking "why" and "what breaks." Practice speaking each answer out loud in 60–120 seconds, then let
them pull the thread.

Recommended loop:

1. **Read the model answer once** for structure (the *shape* of a strong answer).
2. **Close the page and re-answer out loud** in your own words. Record yourself.
3. **Grade against three bars:** (a) did you name the trade-off? (b) did you give a concrete metric
   or number? (c) did you mention a failure mode? If you missed any, re-do.
4. **Chain into follow-ups.** Every answer here ends with likely follow-up directions — pre-load them.
5. **Do the system-design + rapid-fire sections last**, once the vocabulary is automatic.

**How answers are structured.** Most model answers follow: *intuition → mechanism → concrete example
→ trade-off / failure mode*. Interviewers reward candidates who volunteer the trade-off before being
asked. When you can, anchor a claim to a number (a success rate, a token budget, a p95 latency, a
confidence interval) — specificity reads as experience.

**Three things to weave into almost every answer:**
- **Reliability over a single run.** Agents are stochastic; talk in distributions (pass@k, pass^k),
  not single scores.
- **Cost/latency budgets.** An eval that ignores tokens, tool calls, and wall-clock is incomplete.
- **Safety as a first-class axis**, not an afterthought.

---

## Study Plans

### 1-Week Plan (about 1–2 hours/day)

| Day | Focus | Deliverable |
|-----|-------|-------------|
| **Day 1** | Fundamentals + Eval Frameworks (Ch. 1–2). Agent loop, memory, planner/executor, what makes eval hard. | Explain the agent loop and 3 reasons agents are hard to evaluate, from memory. |
| **Day 2** | Metrics + Benchmarks (Ch. 3). Task success, pass@k vs pass^k, cost/latency, SWE-bench/GAIA/tau-bench. | Whiteboard a metrics dashboard for one agent product. |
| **Day 3** | Tool-use + Reasoning eval (Ch. 4–5). Tool selection/args/chaining, trajectory vs outcome, CoT faithfulness. | Design a rubric that scores a tool-use trajectory. |
| **Day 4** | Safety + Multi-agent (Ch. 6–7). Prompt injection, red-teaming, agent-specific harms, coordination metrics. | List 8 attack classes for a browsing agent + a mitigation each. |
| **Day 5** | Real-world testing, Automated eval, Datasets, Tooling, Monitoring (Ch. 8–12). Shadow/canary/A-B, LLM-as-judge, online eval. | Draft an online-eval + monitoring plan for a support agent. |
| **Day 6** | **System design.** Work all 6 scenarios; sketch each on paper in ≤10 min. | Timed: 2 designs in 45 min total. |
| **Day 7** | **Mock loop.** Rapid-fire flashcards, behavioral/STAR stories, "traps & recovery." | 3 STAR stories written; flashcards ≥90% recall. |

### 1-Day Cram (about 4–6 hours)

1. **(45 min)** Fundamentals + the "why agents are hard to evaluate" answer. Nail the agent loop.
2. **(45 min)** Metrics: pass@k vs pass^k, trajectory vs outcome, cost/latency, LLM-as-judge caveats.
3. **(45 min)** Benchmarks + 2025–2026 landscape quiz (models, MCP, reasoning models, frameworks).
4. **(45 min)** Safety + tool-use + monitoring one-liners.
5. **(60 min)** Two system-design scenarios out loud, on paper, timed.
6. **(30 min)** Rapid-fire flashcards + 3 STAR stories.
7. **(15 min)** Skim "traps & how to recover" right before you walk in.

**Night-before rule:** don't cram new material. Re-read your three STAR stories and the "red flags vs
green flags" list. Sleep.

---

## Table of Contents

**Part I — Themed Q&A (mapped to the 12 chapters)**
1. [Agentic AI Fundamentals](#1-agentic-ai-fundamentals)
2. [Evaluation Frameworks](#2-evaluation-frameworks)
3. [Metrics and Benchmarks](#3-metrics-and-benchmarks)
4. [Tool-Use Evaluation](#4-tool-use-evaluation)
5. [Reasoning Evaluation](#5-reasoning-evaluation)
6. [Safety Evaluation](#6-safety-evaluation)
7. [Multi-Agent Evaluation](#7-multi-agent-evaluation)
8. [Real-World Testing](#8-real-world-testing)
9. [Automated Evaluation](#9-automated-evaluation)
10. [Benchmark Datasets](#10-benchmark-datasets)
11. [Evaluation Tooling](#11-evaluation-tooling)
12. [Production Monitoring & Online Eval](#12-production-monitoring--online-eval)

**Part II — Applied & Interview Craft**
13. [2025–2026 Landscape Quiz](#13-20252026-landscape-quiz)
14. [System-Design Scenarios](#14-system-design-scenarios)
15. [Rapid-Fire Flashcards](#15-rapid-fire-flashcards)
16. [Glossary](#16-glossary)
17. [Behavioral / Experience (STAR)](#17-behavioral--experience-star)
18. [Red Flags vs Green Flags](#18-red-flags-vs-green-flags)
19. [Traps & How to Recover](#19-traps--how-to-recover)
20. [Final Tips & Resources](#20-final-tips--resources)

---

# Part I — Themed Q&A

## 1. Agentic AI Fundamentals

### 1.1 What is an AI agent, and how does it differ from a plain LLM call?

**Intuition.** A plain LLM maps text → text in a single shot. An **agent** wraps an LLM in a loop that
lets it *take actions in an environment, observe the results, and decide what to do next* until a goal
is met or a budget is exhausted. The LLM is the policy; the scaffold (tools, memory, control flow) is
what makes it an agent.

**Mechanism — what the agent adds around the model:**
- **Tools / actions:** function calls, APIs, code execution, web/file access.
- **A control loop:** repeated model calls where each observation is fed back in (sometimes called the
  ReAct or plan–act–observe loop).
- **State / memory:** carries context across steps and sessions.
- **A stopping condition:** goal satisfied, max steps, budget, or human handoff.

| Aspect | Plain LLM call | Agent |
|--------|----------------|-------|
| Interaction | Single request→response | Iterative, multi-step loop |
| External actions | None | Tools / APIs / code / browser |
| State | Stateless per call | Maintains working + long-term state |
| Control flow | Fixed | Model decides next action |
| Autonomy | Reactive | Goal-directed, proactive |
| Failure surface | Bad answer | Bad answer **× N steps**, compounding + side effects |

**Example.** "What's the weather in Paris?" is a plain call. "Book me the cheapest refundable flight to
Paris next week under \(\$600\)" is an agent task: it must search, filter, compare, possibly call a
booking API, and confirm — several dependent steps with real side effects.

**Trade-off / why it matters for eval.** The agent's power (autonomy, tool access, statefulness) is
exactly what makes it hard to evaluate: errors *compound* across steps, outputs are *non-deterministic*,
and actions have *side effects* you must sandbox. Evaluating an agent ≠ evaluating an LLM.

*Follow-ups to pre-load:* Where does "agentic" stop and "workflow" begin? (See 1.9.) What's the
minimal viable agent?

---

### 1.2 Walk me through the agent control loop (plan–act–observe).

**Answer.** The core loop has four repeating phases:

```
        ┌─────────────────────────────────────────┐
        │                                          │
        ▼                                          │
   ┌─────────┐    ┌────────┐    ┌───────────┐    ┌────────┐
   │  PLAN   │──▶ │  ACT   │──▶ │  OBSERVE  │──▶ │ DECIDE │
   │ decide  │    │ call a │    │ read tool │    │ done?  │
   │ next    │    │ tool / │    │ result /  │    │ budget?│
   │ action  │    │ answer │    │ env state │    │        │
   └─────────┘    └────────┘    └───────────┘    └────────┘
                                                     │ no → loop
                                                     │ yes → finish
```

- **Plan.** Given goal + current state, the model reasons about the next action (or a full plan).
- **Act.** It emits a tool call (name + arguments) or a final answer.
- **Observe.** The scaffold executes the tool and returns the result/observation into context.
- **Decide.** Check stopping conditions (goal met, max steps, token/cost budget, error threshold,
  human handoff). If not done, loop.

**Two common shapes:** *ReAct* interleaves reasoning traces and actions step-by-step (reactive,
flexible). *Plan-and-execute* builds the whole plan up front, then executes (cheaper, more brittle to
surprises). Reflexion adds a self-critique step after failures.

**Eval hooks live at every phase.** You can score the *plan* (is it feasible?), each *action* (right
tool, right args?), each *observation handling* (did it use the result correctly?), and the *final
outcome*. This is why agent eval separates **trajectory** quality from **outcome** correctness (see 5.1).

---

### 1.3 What are the key components of an agent architecture?

**Answer.**
1. **Model / policy** — the LLM that chooses actions. Often a reasoning model for planning + a cheaper
   model for routine steps (a router/cascade).
2. **Tool layer** — function/tool definitions, schemas, and execution (increasingly standardized via
   **MCP**, the Model Context Protocol). Includes retrieval, code exec, web/browser, internal APIs.
3. **Memory** — working memory (current context window), episodic (past runs), and long-term
   (vector store / knowledge base). Includes summarization/compaction to fit the window.
4. **Orchestration / control flow** — the loop, routing, sub-agent delegation, retries, guardrails.
5. **State & context management** — what's in the window, tool results, scratchpad, and how it's pruned.
6. **Guardrails / policy** — input validation, output filters, allow/deny lists, approval gates for
   high-risk actions.
7. **Observability** — tracing every step (inputs, tool calls, tokens, latency) for eval + debugging.

**Interview tip.** Draw it as a box (the agent) with the model in the center, tools/memory as
peripherals, and a dashed "observability" plane cutting across everything. Naming observability as a
first-class component signals production maturity.

---

### 1.4 How does agent memory work, and why does it matter for evaluation?

**Answer.** Memory types:
- **Working / short-term:** the live context window — recent turns, tool results, scratchpad. Bounded by
  context length; managed via truncation, summarization, and **context compaction**.
- **Episodic:** records of prior task runs ("last time I booked, the user wanted aisle seats").
- **Long-term / semantic:** durable facts, user prefs, learned procedures — usually a vector DB or KB
  with retrieval.
- **Procedural:** reusable skills/tools the agent has accumulated.

**Why memory matters:** continuity across steps, personalization, avoiding repeated work, and learning
from failure.

**Why it complicates eval:**
- **Non-reproducibility.** If the agent reads/writes shared memory, two runs of the "same" task differ.
  You must **snapshot and reset** memory per eval run for fair comparison.
- **Contamination & drift.** Memory can accumulate errors or stale facts ("memory poisoning"); an
  offline benchmark won't catch this — you need long-horizon and multi-session tests.
- **Context-rot / lost-in-the-middle.** As the window fills, models attend worse to mid-context info;
  eval should include long-context and many-step tasks, not just short ones.

*Green-flag move:* mention that you version and freeze memory state as part of the eval harness so runs
are comparable.

---

### 1.5 What is the difference between a workflow and an agent, and why does the distinction matter?

**Answer.** Anthropic's widely-cited framing: **workflows** orchestrate LLMs and tools through
*predefined code paths*; **agents** let the *model dynamically direct its own process and tool use*.
It's a spectrum of autonomy, not a binary.

- **Workflow** (prompt chaining, routing, parallelization, orchestrator-worker): you, the engineer,
  decide the control flow. More predictable, cheaper, easier to evaluate — you can unit-test each node.
- **Agent:** the model decides how many steps, which tools, in what order. More flexible for open-ended
  tasks, but higher cost/latency variance and a much larger failure surface.

**Why it matters for eval and design.** The right default is often the *least* agentic thing that works:
if a fixed workflow solves the task, evaluate it like software (deterministic-ish, node-level tests).
Reserve full agency for genuinely open-ended tasks — and then invest in trajectory-level eval,
budgets, and guardrails. A strong candidate resists "agentify everything."

---

### 1.6 Why are agents fundamentally harder to evaluate than single-turn LLMs?

**Answer.** Five compounding reasons:
1. **Multi-step compounding error.** A 90%-reliable step run 10 times gives \(0.9^{10} \approx 0.35\)
   end-to-end. Small per-step errors explode over horizons.
2. **Non-determinism.** Temperature, tool latency/ordering, and model updates make the same input yield
   different trajectories → you must measure **distributions** (pass@k, pass^k), not points.
3. **Path dependence.** Two runs can reach the right answer via very different (good or dangerous)
   trajectories. Outcome-only scoring hides reward hacking and unsafe shortcuts.
4. **Side effects & statefulness.** Real actions (send email, write DB) can't be blindly re-run; you
   need sandboxes, mocks, and resettable environments.
5. **Credit assignment.** When a 15-step task fails, *which* step caused it? Requires trajectory
   tracing and step-level rubrics.

Plus: LLM-as-judge introduces its own biases, and benchmarks saturate/contaminate quickly. The honest
one-liner: *"you're evaluating a stochastic policy operating in a stateful environment, so you evaluate
behavior over distributions of trajectories, not a single output."*

---

### 1.7 What are the most common agent failure modes you design evals to catch?

**Answer.** Group them so you can rattle them off:
- **Planning:** wrong decomposition, no plan, over-planning, ignoring constraints.
- **Tool use:** wrong tool, malformed arguments, hallucinated tools/params, not reading the result.
- **Looping / non-termination:** repeating the same failing action; oscillation; never stopping.
- **Error handling:** failing to detect a tool error; giving up too early; retrying blindly.
- **Context problems:** losing earlier constraints (context rot), dropping the user's actual goal.
- **Reward hacking / shortcutting:** faking success, editing tests instead of code, claiming done.
- **Safety:** prompt/tool-output injection, data exfiltration, unsafe irreversible actions.
- **Cost/latency blowups:** runaway token/tool usage, pathological retries.
- **Overconfidence / poor calibration:** asserting success when the goal wasn't met.

Each maps to a specific eval: e.g., non-termination → step-cap + loop-detection metric; reward hacking
→ hidden verification tests + trajectory review.

---

### 1.8 What does a "good" agent trajectory look like — what would you inspect in a trace?

**Answer.** When I open a trace I look for:
- **Goal fidelity:** does every step serve the actual user goal, including all constraints?
- **Efficient tool use:** minimal, correct tool calls with valid args; no redundant/oscillating calls.
- **Grounded observations:** the model actually *uses* tool results, doesn't hallucinate over them.
- **Recovery:** on a tool error, does it diagnose and adapt vs. blindly retry or give up?
- **Termination:** stops when done; doesn't pad steps; asks for clarification when genuinely ambiguous.
- **Budget:** steps/tokens/cost within expectation; latency reasonable.
- **Safety:** no unsafe/irreversible action without justification or approval.

A great answer notes that many of these are *automatable* signals (tool-error rate, redundant-call rate,
step count) that you turn into online metrics, not just eyeballing.

---

### 1.9 What is "context engineering," and how is it different from prompt engineering?

**Answer.** *Prompt engineering* optimizes the wording of a single instruction. *Context engineering* is
the broader discipline of curating **everything in the model's window at each step** of an agent run:
system prompt, tool definitions, retrieved documents, prior tool results, memory, and scratchpad —
under a finite token budget.

Key levers: retrieval quality, **compaction/summarization** of long histories, tool-result trimming,
ordering (avoid lost-in-the-middle), and just-in-time loading of information. It matters for eval
because many agent failures are really *context* failures (the model never had, or lost, the relevant
fact) — so your eval suite should include long-horizon and long-context stressors, and you should track
context size vs. success. This is a very current (2025–2026) framing that senior interviewers like.

---

### 1.10 What is the ReAct pattern, and what are its limitations?

**Answer.** **ReAct** (Reason + Act) interleaves natural-language reasoning ("Thought") with tool calls
("Action") and their results ("Observation"), looping until an answer. It's the default agent pattern
because reasoning traces improve tool selection and give you an inspectable rationale.

**Limitations:** (1) verbose traces burn tokens/latency; (2) reasoning can be *post-hoc rationalization*
rather than the true cause of the action (faithfulness problem, see 5.5); (3) it's greedy/local — no
lookahead, so it can commit early to a bad path; (4) error recovery isn't built in (Reflexion/self-
critique variants add it). For eval, don't treat the visible "Thought" as ground truth about the
model's process — score actions and outcomes, and probe faithfulness separately.

---

### 1.11 When should you NOT build an agent?

**Answer.** Prefer a simpler solution when: the task is well-specified and repeatable (use a fixed
workflow or a single prompt); latency/cost must be tight and predictable; the action space includes
irreversible/high-stakes operations without good guardrails; or you lack the observability/eval
infrastructure to operate an autonomous system safely. Agency buys flexibility for *open-ended,
variable* tasks at the cost of predictability. The mature engineering instinct — and a green flag in
interviews — is to reach for the least-agentic design that meets the requirement.

---

## 2. Evaluation Frameworks

### 2.1 How would you design an end-to-end evaluation framework for AI agents?

**Answer.** I structure it in layers, from cheap/fast to expensive/high-signal:

```
   ┌────────────────────────────────────────────────────────────┐
   │  L4  Online eval (prod)  — real traffic, live metrics, HITL │
   ├────────────────────────────────────────────────────────────┤
   │  L3  Scenario / E2E offline — realistic tasks, sandboxed    │
   ├────────────────────────────────────────────────────────────┤
   │  L2  Component eval — planner, tool-selection, RAG, judge   │
   ├────────────────────────────────────────────────────────────┤
   │  L1  Unit / assertion — deterministic checks, regression    │
   └────────────────────────────────────────────────────────────┘
```

Core pieces:
1. **A task/dataset schema.** Each case: id, goal/input, environment/fixtures, success criteria
   (programmatic where possible), difficulty/tags, and any gold trajectory.
2. **A sandboxed environment** with resettable state so runs are reproducible and side-effect-free.
3. **Graders:** deterministic checks first (exact/state-based/test-suite), then rubric-based
   LLM-as-judge for the fuzzy parts, then human review for a sampled slice.
4. **Metrics + statistics:** success rate with confidence intervals, pass@k / pass^k, cost, latency,
   step count, safety violations. Multiple seeds per case.
5. **Runner + reporting:** parallel execution, per-case traces, aggregate dashboards, diffs vs.
   baseline, and regression gates in CI.
6. **Governance:** dataset versioning, contamination controls, a held-out set, and a process for
   promoting real production failures into the regression suite.

**Design principles to state aloud:** deterministic-before-LLM-before-human; measure trajectories *and*
outcomes; freeze environment/memory per run; and treat the eval set as a living asset that grows from
production failures.

---

### 2.2 Automated vs. human evaluation — when do you use each?

| Aspect | Automated | Human |
|--------|-----------|-------|
| Speed / scale | Seconds, unbounded | Slow, limited |
| Cost | Low | High |
| Consistency | High (deterministic) or medium (LLM-judge) | Variable, needs calibration |
| Nuance / novel cases | Limited | Excellent |
| Ground truth | Great when it exists | Defines ground truth |

**Use automated** for regression, CI gates, large sweeps, and anything with a programmatic checker.
**Use humans** for ambiguous quality, calibrating your LLM-judge, adjudicating disagreements, and
final sign-off on high-stakes changes. **Best practice is a pyramid:** cheap automated checks on
everything, LLM-as-judge on most, human review on a stratified sample (especially failures and
high-risk cases). Humans also produce the labeled set you use to *validate the judge*.

---

### 2.3 How do you evaluate non-deterministic agents rigorously?

**Answer.** Treat each task's success as a random variable and estimate it:
- **Multiple seeds per task** (e.g., \(k=5\)–\(10\)), report mean success with a **confidence interval**
  (Wilson interval for proportions), not a single number.
- **pass@k** — probability at least one of \(k\) attempts succeeds (measures *capability*; optimistic).
- **pass^k** — probability *all* \(k\) attempts succeed (measures *reliability*; what production cares
  about). tau-bench popularized pass^k for exactly this reason.
- **Semantic / criteria-based grading** instead of exact match: state-based checks, rubric LLM-judge,
  or embedding similarity for free-text.
- **Control variance:** fix seeds/temperature where possible, snapshot environments, and pin model
  versions so a regression is attributable to your change, not the weather.
- **Power/sample size:** enough cases and seeds that your CI can actually detect the effect size you
  care about; report the CI so reviewers see the noise floor.

The senior framing: *"a 72% success rate means nothing without a confidence interval and a statement of
how many seeds and cases produced it."*

---

### 2.4 What makes a good eval dataset for agents?

**Answer.** Good agent eval sets are: **representative** (drawn from real usage distribution),
**discriminative** (spread of difficulty so scores aren't 0% or 100% — avoid saturation),
**verifiable** (each case has a checkable success signal, ideally programmatic), **diverse** across
tools/domains/edge-cases, **uncontaminated** (kept out of training data; a private held-out slice),
and **maintained** (versioned, with failures from prod continuously folded in). Include *negative* and
*adversarial* cases, not just happy paths. Size is secondary to signal: 100 well-chosen, well-graded
cases beat 10,000 noisy ones.

---

### 2.5 Explain offline vs. online evaluation and how they complement each other.

**Answer.** **Offline** eval runs a fixed dataset against the agent in a sandbox before deploy: fast,
reproducible, gates releases, catches regressions. **Online** eval measures the agent on *real traffic*
in production: A/B tests, live quality metrics, user feedback, and LLM-judges scoring sampled real
sessions. Offline can't capture the true input distribution, adversarial users, or long-horizon drift;
online can't safely test dangerous cases and lacks ground truth. You need both: offline as the gate,
online as the truth. A healthy loop *mines production failures into the offline suite*, closing the gap.

---

### 2.6 What is LLM-as-a-judge, and what are its failure modes?

**Answer.** Using a strong LLM to grade another model's outputs against a rubric — scalable, cheap
relative to humans, good for fuzzy criteria. But it has well-documented biases:
- **Position bias** (favors first/last option in pairwise), **verbosity bias** (prefers longer),
  **self-preference** (a model favors its own style/family), **sycophancy**, and **leniency drift**.
- **Rubric sensitivity:** vague rubrics → noisy, non-reproducible scores.
- **Correlation, not truth:** it approximates human judgment; you must *measure that correlation*.

**Mitigations:** clear rubrics with explicit criteria and few-shot anchors; ask for structured
output + rationale; use pairwise comparisons and randomize/average over positions; ensemble multiple
judges; calibrate against a human-labeled gold set and report agreement (Cohen's/Fleiss' \(\kappa\),
or correlation); and use a *different* model family as judge than as candidate where possible. Never
ship an LLM-judge you haven't validated against humans.

---

### 2.7 How do you validate that your evaluator/judge is trustworthy?

**Answer.** Build a **human-labeled gold set**, then measure the judge against it: agreement
(\(\kappa\)), precision/recall on the "fail" class (you usually care most about catching failures), and
score correlation. Run **bias probes** (swap positions, pad length, swap model identities) to quantify
position/verbosity/self-preference bias. Track judge stability across runs (same input → same score?).
Re-validate whenever you change the judge model, prompt, or rubric — a judge is itself a model that can
regress. Report these numbers; "we use GPT-as-judge" without a validation number is a red flag.

---

### 2.8 How do you evaluate a RAG-augmented agent's retrieval component?

**Answer.** Separate **retrieval** from **generation**. Retrieval metrics: recall@k / precision@k,
MRR, nDCG against labeled relevant docs; plus context relevance. Generation-grounding metrics:
**faithfulness/groundedness** (is the answer supported by retrieved context? — measurable with NLI or
an LLM-judge), **answer relevance**, and **citation correctness**. The RAG-triad (context relevance,
groundedness, answer relevance — popularized by TruLens/Ragas) is a clean way to say this. Evaluate them
independently so you can localize failures: bad answer from good context = generation bug; good answer
despite bad context = lucky/parametric-knowledge, still fragile.

---

### 2.9 How would you set up regression testing for an agent in CI?

**Answer.** Maintain a curated regression suite (fast, deterministic-where-possible, seeded) that runs
on every change to prompts, tools, model version, or scaffold. Gate merges on: success rate not
dropping beyond a CI threshold, no new safety violations, and cost/latency within budget. Use **paired
comparisons** against the current baseline (same cases, same seeds) so you detect *deltas* with less
noise. Pin the model version. Store traces as artifacts for debugging. Because scores are noisy, gate
on a statistically meaningful drop (e.g., outside the CI), and alert-but-don't-block on borderline
regressions. Every production incident becomes a new regression case.

---

### 2.10 A stakeholder asks for "one number" for agent quality. How do you respond?

**Answer.** Push back constructively: a single scalar hides the trade-offs that matter (a model can be
more capable but slower, or higher success but with more safety violations). I'd offer a **small
scorecard** — task success (with CI), reliability (pass^k), cost/task, p95 latency, and safety
violation rate — and, if forced, a weighted composite whose weights reflect *this product's* priorities,
always shown alongside its components. The instinct to reduce everything to one KPI is where reward
hacking and blind spots creep in; a good eval lead makes the trade-offs visible to decision-makers.

---

## 3. Metrics and Benchmarks

### 3.1 What metrics do you track when evaluating agents, and how do you organize them?

**Answer.** I group metrics into five families so nothing gets forgotten:

1. **Effectiveness (did it work?):** task success rate, goal completion, partial-credit / subgoal
   completion, exact/state-based correctness.
2. **Reliability (does it work *every* time?):** pass@k, pass^k, variance across seeds, consistency.
3. **Efficiency (what did it cost?):** steps to completion, tool calls, tokens, \(\$\)/task, p50/p95
   latency, time-to-first-token.
4. **Process quality (how did it get there?):** tool-selection accuracy, tool-arg validity, redundant-
   call rate, recovery rate after errors, plan quality.
5. **Safety & UX:** safety-violation rate, refusal appropriateness, hallucination rate, calibration,
   user satisfaction / thumbs-up rate, escalation rate.

**Principle:** never report effectiveness without efficiency and safety alongside — an agent that
succeeds 95% of the time but costs \(\$2\) and 40s per task, or leaks data 1% of the time, is not
"better" than a cheaper safer one. Interviewers listen for this multi-axis instinct.

---

### 3.2 Explain pass@k vs. pass^k and when each is the right metric.

**Answer.** With \(k\) independent attempts at a task:
- **pass@k** = probability that *at least one* of \(k\) succeeds. It's optimistic and measures
  *capability / ceiling*. Great for code-gen where you can verify and keep the best of \(k\).
- **pass^k** = probability that *all \(k\)* succeed. It's pessimistic and measures **reliability /
  consistency** — the property that matters when the agent acts autonomously in production and you
  can't cherry-pick.

For a per-attempt success probability \(p\): pass@k \(=1-(1-p)^k\) rises toward 1 with \(k\); pass^k
\(=p^k\) falls toward 0. A model with \(p=0.8\) has pass@5 \(\approx 0.9997\) but pass^5 \(\approx 0.33\).
tau-bench uses pass^k precisely because customer-service agents must be *dependably* right, not
occasionally right. Say which one you're optimizing and why.

---

### 3.3 How do you measure the cost and latency of an agent, and why does it belong in eval?

**Answer.** Cost = \(\sum\) (input+output tokens × price) across all model calls + tool/infra costs,
reported per task and per successful task (cost-per-success is the honest number — retries inflate it).
Latency = wall-clock per task, reported as p50/p95/p99 (tails matter for UX), plus time-to-first-token
and per-step latency. It belongs in eval because agents have *unbounded* loops: a quality win that
triples token spend or blows the latency budget may be a net loss. I plot success vs. cost as a
**Pareto frontier** and pick the knee, rather than maximizing quality unconditionally. This framing —
quality is a curve against cost/latency, not a scalar — is a strong senior signal.

---

### 3.4 What is the "outcome vs. trajectory" distinction in metrics?

**Answer.** **Outcome metrics** score the end state (was the flight booked correctly? do the tests
pass?). **Trajectory (process) metrics** score *how* it got there (right tools, no redundant steps, no
unsafe actions, efficient path). You need both: outcome-only rewards reward-hacking and unsafe
shortcuts (right answer, dangerous path); trajectory-only can penalize a valid creative solution. A
robust rubric weights outcome primarily but adds trajectory checks as *gates* (e.g., zero unsafe
actions) and *efficiency* signals. See 5.1 for the eval-design version of this.

---

### 3.5 Walk me through the major agent benchmarks and what each actually measures.

**Answer.** (Know 6–8 cold.)
- **SWE-bench / SWE-bench Verified** — resolve real GitHub issues in real repos; graded by whether the
  repo's **hidden test suite passes** after the agent's patch. *Verified* is a 500-task human-validated
  subset (OpenAI) that removed broken/underspecified tasks. The reference coding-agent benchmark.
- **tau-bench / tau2-bench (Sierra)** — tool-agent in customer-service domains (retail, airline) talking
  to a **simulated user**; graded on final **database state** vs. goal, using **pass^k** for reliability.
  Tests policy-following + multi-turn tool use.
- **GAIA (Meta/HF)** — general-assistant questions that are easy for humans but need tool use + multi-step
  reasoning; single verifiable answer. Tests real-world assistant competence.
- **WebArena / VisualWebArena** — complete tasks on self-hosted realistic websites; functional
  correctness of the end state. Web-navigation agents.
- **OSWorld** — real computer-use tasks across OS/apps (files, GUI); execution-based checks. Computer-use
  agents.
- **Terminal-Bench** — agents solving tasks in a real terminal/sandbox environment.
- **BrowseComp (OpenAI)** — hard web-browsing/research questions requiring persistent multi-hop search.
- **AgentBench** — multi-environment suite (OS, DB, web, games) for broad agent capability.

For each, be ready to say the *domain*, the *grading mechanism* (test suite / DB state / exact answer /
execution check), and *what it fails to measure*.

---

### 3.6 What are the limitations of public benchmarks, and how do you compensate?

**Answer.** Limitations: (1) **contamination** — public sets leak into training data, inflating scores;
(2) **saturation** — frontier models cluster near the top, losing discriminative power; (3)
**construct gap** — benchmark tasks rarely match *your* product's distribution; (4) **gaming** — vendors
optimize to the leaderboard; (5) **static** — they don't capture drift or adversarial real users; (6)
**narrow grading** — a passing test suite ≠ good code. Compensate by treating public benchmarks as a
*sanity floor*, building a **private, contamination-controlled eval set from your own traffic**, keeping
a held-out slice, refreshing tasks, and weighting production online metrics as the real signal.

---

### 3.7 How do you handle partial credit for long multi-step tasks?

**Answer.** Binary success is too coarse for 15-step tasks — you lose signal on *near-misses* and can't
track progress. Options: (1) **subgoal decomposition** — define checkpoints and score fraction
completed; (2) **milestone/rubric scoring** — points per required capability demonstrated; (3)
**state-distance** — how close is the final environment state to the goal state; (4) **step-level
accuracy** against a gold trajectory (careful: multiple valid paths exist). Use partial credit for
*development signal and dashboards*, but keep a strict binary "fully correct" metric for the headline —
partial credit can mask that the task actually failed for the user.

---

### 3.8 What is benchmark contamination and how do you detect/mitigate it?

**Answer.** Contamination = eval data (or near-duplicates) present in the model's training set, so the
model "remembers" answers rather than solving. Signals: suspiciously high scores on old public sets vs.
fresh ones; sensitivity to canary strings; big drops on perturbed/paraphrased variants. Mitigations:
**private held-out sets**, freshly authored or post-cutoff tasks, canary strings, perturbation tests
(rename variables, reword), and time-split evaluation (tasks created after the model's training cutoff).
For agents specifically, dynamic environments and randomized fixtures reduce memorization.

---

### 3.9 How do you compare two agents/models fairly?

**Answer.** Same tasks, same seeds, same environment snapshots, same tool implementations, and same
budget caps — a **paired** comparison so you difference out task difficulty. Report deltas with
confidence intervals or a paired significance test (e.g., bootstrap or McNemar for paired binary
outcomes), not raw scores. Control for prompt/scaffold differences (or hold them constant). Show the
**full scorecard** (success, cost, latency, safety), because one model rarely dominates on all axes —
the honest output is a Pareto comparison, and the choice depends on the product's priorities.

---

### 3.10 What is Elo / Arena-style ranking and when is it useful?

**Answer.** Pairwise-preference ranking (e.g., LMArena/Chatbot Arena) collects human or judge votes on
"which response is better" across many head-to-heads and fits **Elo/Bradley-Terry** ratings. Useful for
*subjective, open-ended* quality where there's no gold answer, and for tracking relative model strength
over time. Weaknesses: it measures *preference*, not task success; it's gameable by style/verbosity; and
it doesn't tell you *why* one is better or whether either meets a bar. For agents, use it to compare
overall assistant quality, but pair it with task-based, verifiable evals for anything mission-critical.

---

### 3.11 How do you know when your benchmark has "saturated" and it's time to retire it?

**Answer.** When top systems cluster near the ceiling and score differences fall within noise/CI, the
benchmark no longer discriminates — improvements on it stop predicting real-world gains. Signals: >90%
scores across frontier models, shrinking spread, and leaderboard gains not reproducing in production.
Response: raise difficulty (harder subset, e.g., "Verified"→"Hard"), add adversarial/long-horizon
cases, refresh with new tasks, or move the goalposts to a harder construct. Retire or demote saturated
sets to regression-only. Keeping a benchmark alive past saturation gives false confidence.

---

## 4. Tool-Use Evaluation

### 4.1 How do you evaluate an agent's tool use end to end?

**Answer.** I decompose tool use into four scorable dimensions:
1. **Selection** — did it pick the right tool(s) for the sub-goal, and *not* call unnecessary ones?
   Metrics: selection accuracy, precision/recall vs. a gold tool set, unnecessary-call rate.
2. **Invocation (arguments)** — are the arguments schema-valid, correctly typed, and semantically
   right (right values, not just right shape)? Metrics: arg validity rate, schema-error rate.
3. **Chaining / orchestration** — correct order, dependency handling, passing outputs of one tool into
   the next. Metrics: sequence correctness, dependency-satisfaction.
4. **Result handling** — does it read the observation, ground on it, and handle errors/empty results?
   Metrics: grounding rate, error-recovery rate.

Plus efficiency (redundant/oscillating calls) and safety (no dangerous tool invoked without approval).
Grade selection/args programmatically where the gold is known; use LLM-judge + trajectory review for
the fuzzy "did it use the result well" part.

---

### 4.2 How do you evaluate tool selection when multiple tools are valid?

**Answer.** Exact-match against one "gold tool" is wrong when several tools solve the task. Instead:
(1) define an **acceptable set** per case and score membership; (2) score on **outcome** (did the chosen
tool achieve the sub-goal?) rather than identity; (3) add an **efficiency** penalty for choosing a more
expensive/slower valid tool; (4) use a rubric LLM-judge for "was this a reasonable choice given the
state." The principle: reward *effective* selection, not conformity to one canonical path.

---

### 4.3 How do you test an agent's error handling with tools?

**Answer.** Fault-inject and observe. Scenarios: tool unavailable, 4xx/5xx errors, timeouts, malformed/
empty responses, rate limits, invalid-argument rejections, and *misleading* results. For each, I score:
**detection** (did it notice the error vs. plow ahead?), **recovery** (retry with backoff, fallback
tool, replan, or graceful degradation?), **communication** (does it tell the user / ask for help?), and
**termination** (does it avoid infinite retry loops?). Implementation: wrap tools with a fault-injection
harness that can be toggled per case, keeping the rest of the environment fixed. Robust error handling
is where flashy demos and production-ready agents diverge — interviewers love concrete injection tests.

---

### 4.4 What is MCP and why does it matter for tool-use evaluation?

**Answer.** The **Model Context Protocol (MCP)** is an open standard (introduced by Anthropic in Nov
2024, now broadly adopted — OpenAI, Google, Microsoft, AWS) that standardizes how agents connect to
tools, data, and prompts via **MCP servers**. Think "USB-C for AI tools": one protocol instead of N
bespoke integrations. For evaluation this matters because (1) it standardizes the tool interface, so
you can build reusable, tool-agnostic eval harnesses and swap tools without rewriting the agent; (2)
MCP servers become a natural place to instrument/trace tool calls; and (3) it introduces its own
*attack surface* — untrusted MCP servers, tool-description injection, and over-broad scopes — that your
safety eval must cover (see 6.x). The Nov-2025 spec added task-based workflows, simplified OAuth-based
auth, and an extensions framework; a registry of MCP servers launched in Sept 2025.

---

### 4.5 How do you evaluate agents that use *many* tools (large tool spaces)?

**Answer.** As the tool count grows, selection degrades (the model can't attend to 100 tool schemas).
Eval must stress this: measure selection accuracy as a function of tool-catalog size, include
distractor/near-duplicate tools, and test retrieval-based tool selection (RAG over tools). Track
"tool confusion" (picking a similar-but-wrong tool) and schema-injection risk. Design mitigations you
can then evaluate: tool retrieval/filtering, hierarchical namespaces, and clear tool descriptions
(tool-description quality measurably affects success — a current research thread). Report success vs.
#tools-in-context as a curve.

---

### 4.6 How do you handle tool side effects in evaluation without causing real damage?

**Answer.** Never eval write/irreversible tools against production. Use: **sandboxed environments** with
resettable state (containers, ephemeral DBs), **mocks/stubs** with recorded fixtures (VCR-style) for
deterministic replay, **simulators** for external services, and **dry-run modes**. For unavoidable
real-effect tests, use dedicated test accounts and cleanup hooks. Snapshot-and-reset between runs for
reproducibility. The eval harness owning environment lifecycle (spin up → seed → run → assert →
teardown) is the mark of a serious setup.

---

### 4.7 How do you evaluate function-calling / structured-output correctness specifically?

**Answer.** Two levels: **schema conformance** (valid JSON, required fields present, correct types /
enums — measurable deterministically, and often enforced via constrained decoding) and **semantic
correctness** (are the argument *values* right for the intent, e.g., the correct date, the right unit,
the right entity resolved?). Also test: hallucinated function names/params, over/under-calling,
and correct handling when *no* function should be called. Report schema-valid rate separately from
semantically-correct rate — a model can be 100% valid JSON and still 30% wrong on values.

---

### 4.8 How do you evaluate whether an agent knows when NOT to use a tool?

**Answer.** Include cases where the correct behavior is to answer directly, ask a clarifying question,
or refuse — with tempting-but-wrong tool options available. Metrics: **over-calling rate** (invoking
tools when unnecessary) and its cost, and **under-calling rate** (should have used a tool but didn't,
causing hallucination). Well-calibrated tool use is a distinct capability from raw tool ability; many
agents that ace happy-path tool tasks fail these restraint cases.

---

### 4.9 What signals from tool use can you turn into *online* production metrics?

**Answer.** Many trajectory signals are automatable without ground truth: tool-error rate, retry rate,
redundant/duplicate-call rate, average tool calls per session, schema-error rate, tool latency
contribution to p95, and rate of hitting the step cap. These become leading indicators — a spike in
tool-error or retry rate often precedes a drop in task success and is catchable in real time. Pair with
sampled LLM-judge scoring of full sessions for quality.

---

### 4.10 How would you build a tool-use benchmark for your own product?

**Answer.** Inventory the product's real tools and top user intents; sample real (anonymized) sessions;
for each, define the goal, required tool(s)/acceptable set, gold arguments where deterministic, and a
programmatic success check (final state). Include adversarial and error-injection variants and
restraint cases (no-tool-needed). Version it, keep a private held-out slice, and grow it from
production failures. Validate that scores on it correlate with online success — a benchmark that
doesn't predict production isn't worth maintaining.

---

## 5. Reasoning Evaluation

### 5.1 How do you evaluate an agent's reasoning — trajectory vs. outcome?

**Answer.** **Outcome eval** asks "was the final answer/state correct?" **Trajectory (process) eval**
asks "was the reasoning path valid, efficient, and safe?" You need both because they catch different
failures: a correct outcome via flawed/lucky reasoning is fragile and won't generalize; a sound process
that hit a tool outage still tells you the agent is good. Practically: score outcome as the headline;
add trajectory rubrics (logical validity, no unsupported leaps, efficiency, grounding) as diagnostics
and safety gates. For reasoning models, also watch that the *visible* reasoning isn't just post-hoc
rationalization (see 5.5).

---

### 5.2 How do you evaluate multi-hop / compositional reasoning?

**Answer.** Use tasks that *require* chaining facts (e.g., HotpotQA-style multi-hop QA, or synthesized
tasks with known intermediate answers). Score the **final answer** but also **intermediate hop
correctness** where you have gold sub-answers, to localize where reasoning breaks. Add **perturbations**
(change one premise → answer must change) to catch shortcut/heuristic answering. Watch for "right answer,
wrong reasoning" by including distractor context that a shortcut would latch onto. Report accuracy vs.
number of hops — degradation with depth is the interesting signal.

---

### 5.3 How do you measure planning quality?

**Answer.** Dimensions: **validity** (is the plan executable — tools exist, preconditions met?),
**goal-completeness** (does it cover all sub-goals and constraints?), **efficiency/optimality** (minimal
redundant steps), and **robustness** (contingencies for failure). Methods: compare against a reference
plan where one exists; simulate execution and check goal achievement; rubric LLM-judge for feasibility;
and measure replanning quality when the environment surprises the agent. For plan-and-execute agents,
separately score the up-front plan and the execution adherence.

---

### 5.4 How do you evaluate reasoning models (extended-thinking / test-time compute)?

**Answer.** Reasoning models (OpenAI o-series/GPT-5 thinking, Claude extended thinking, Gemini thinking,
DeepSeek-R1) spend variable **test-time compute** ("thinking tokens") before answering. Eval must add:
(1) **accuracy vs. thinking-budget** curves — does more thinking actually help, and where's the knee?
(2) **cost/latency of reasoning** — thinking tokens are expensive and slow; report them; (3)
**overthinking** on easy tasks (burning budget for no gain) and **underthinking** on hard ones; (4)
**faithfulness** of the reasoning trace to the actual answer. Compare reasoning vs. non-reasoning
variants on the *same* tasks to justify the cost. The headline metric becomes accuracy-per-dollar and
accuracy-per-second, not raw accuracy.

---

### 5.5 What is chain-of-thought "faithfulness" and why does it matter for eval?

**Answer.** Faithfulness = whether the model's stated reasoning actually reflects the computation that
produced its answer. Research (incl. Anthropic) shows models sometimes reach an answer for hidden
reasons and generate a *plausible but non-causal* rationale — even omitting that they used an injected
hint. This matters because: (1) you can't trust the visible CoT as an explanation for
safety/oversight; (2) grading the *reasoning text* can be gamed by good-looking-but-fake rationales.
Test faithfulness with **causal interventions**: inject a hint or perturb a premise and check whether
the stated reasoning acknowledges it and whether the answer changes accordingly. Treat CoT as a signal,
not ground truth.

---

### 5.6 How do you detect and evaluate reasoning shortcuts / spurious heuristics?

**Answer.** Models often exploit dataset artifacts (answer position, keyword overlap, length) instead
of reasoning. Detect with: **counterfactual/perturbation tests** (minimal edits that should flip the
answer), **distractor injection**, **contrast sets**, and checking robustness to reordering options.
If accuracy collapses under perturbation, the "reasoning" was a shortcut. For agents, the analog is a
task that *looks* solvable by a memorized pattern but requires genuine multi-step tool use.

---

### 5.7 How do you evaluate self-correction / reflection capabilities?

**Answer.** Give tasks where the first attempt is likely wrong and observe whether the agent detects
its error and improves (Reflexion-style). Metrics: **error-detection rate**, **correction success rate**
(fixed given feedback), and **regression rate** (did reflection make a *correct* answer worse — a real
failure mode). Distinguish self-correction *with* external feedback (tool error, test failure) from
*without* (pure introspection); models are far better at the former. Beware "false reflection" where the
model claims to fix something but doesn't.

---

### 5.8 How do you evaluate calibration and uncertainty in agent reasoning?

**Answer.** Calibration = do the model's confidence signals match its actual accuracy? Measure with
**reliability diagrams** and **Expected Calibration Error (ECE)**, or by checking whether verbalized
confidence ("I'm 90% sure") tracks empirical correctness. For agents, calibration governs when to
**ask for help, seek more info, or refuse** vs. barrel ahead. Well-calibrated agents that escalate on
low confidence are far safer in production. Test with ambiguous/underspecified tasks and score whether
the agent appropriately expresses uncertainty or clarifies rather than confidently hallucinating.

---

### 5.9 How do reasoning evals differ for "System 1" vs "System 2" style tasks?

**Answer.** Fast, pattern-matching tasks (System 1) are well-served by direct-answer accuracy and are
cheap; forcing extended thinking there mostly wastes budget. Deliberate, multi-step tasks (System 2 —
math proofs, planning, debugging) benefit from test-time compute and need **process-aware** eval
(intermediate steps, budget-vs-accuracy). A good eval suite *labels task difficulty/type* so you can
tell whether a reasoning model earns its cost only where deliberation helps, and route accordingly.

---

### 5.10 How do you build ground truth for open-ended reasoning tasks?

**Answer.** When there's no single correct answer: use **rubrics** with explicit criteria + anchored
examples, **expert-authored reference solutions** for comparison, **pairwise preference** judging, and
**verifiable sub-claims** (decompose the answer into checkable facts). For math/code, prefer
**execution/verification** (does the proof check, do tests pass) over judging prose. Always validate the
grader against human labels. The senior point: invest ground-truth effort where it's checkable, and be
honest about the noise floor where it isn't.

---

## 6. Safety Evaluation

### 6.1 What are the axes of agent safety you evaluate?

**Answer.** Beyond content safety, agents add *action* safety. Axes:
- **Harmful content / policy violations:** the classic dimensions (violence, illegal, hate, self-harm).
- **Prompt & tool-output injection:** untrusted inputs hijacking the agent (see 6.2).
- **Data exfiltration / privacy:** leaking secrets, PII, or system prompts via tools or outputs.
- **Unsafe / irreversible actions:** deleting data, sending money/emails, running destructive commands.
- **Excessive agency / over-permissioning:** doing more than authorized; acting without approval.
- **Reward hacking / spec gaming:** achieving the letter of the goal unsafely.
- **Robustness:** adversarial inputs, jailbreaks, distribution shift.
- **Bias/fairness & calibration:** unfair treatment; overconfidence leading to harm.

Framing agents as having a *dangerous action space*, not just a dangerous *output space*, is the key
senior insight.

---

### 6.2 What is prompt injection, and how is it worse for agents?

**Answer.** Prompt injection = malicious instructions embedded in input that the model treats as
commands. **Direct** injection is in the user's message ("ignore your instructions..."); **indirect**
injection hides in *content the agent retrieves* — a web page, email, PDF, tool result, or a malicious
**MCP server's** tool description. Agents make it far worse because they *act on* the hijacked
instruction with real tools: an injected web page can tell a browsing agent to exfiltrate the user's
data or take unauthorized actions. It's considered the top security risk for LLM agents (OWASP LLM Top
10). Because indirect injection rides on untrusted retrieved content, you cannot solve it with input
filtering alone.

---

### 6.3 How do you evaluate prompt-injection resistance?

**Answer.** Build an **attack suite** across vectors: direct injection, indirect via retrieved
docs/web/email, tool-result injection, multi-step/gradual attacks, obfuscation (encoding, translation,
homoglyphs), and MCP tool-description injection. For each, define what a *successful* attack looks like
(agent follows the injected instruction / exfiltrates / takes unauthorized action) and measure **attack
success rate (ASR)**. Test *with tools live in a sandbox* so you catch action-level compromise, not just
text. Track ASR over time as a regression metric, and evaluate defenses (data/instruction separation,
allow-lists, human-approval gates, injection classifiers, least-privilege scopes) by their ASR
reduction and their false-positive/utility cost.

---

### 6.4 What is red-teaming for agents, and how do you make it systematic?

**Answer.** Red-teaming = adversarial probing to elicit failures. Make it systematic rather than
ad-hoc: (1) enumerate a **threat model** (who attacks, what they want, via which surface); (2) build
**attack taxonomies** and seed prompts per category; (3) scale with **automated/LLM red-teamers** that
generate and mutate attacks, plus human experts for creative ones; (4) measure ASR per category and
severity; (5) feed successes into regression + into fine-tuning/guardrail improvements. Combine manual
(depth, novelty) and automated (coverage, regression). Report residual risk, not "we red-teamed it."

---

### 6.5 How do you evaluate safety of *irreversible* or high-stakes actions?

**Answer.** Classify the action space by reversibility and blast radius. For high-risk actions
(payments, deletions, external comms, code deploy), eval whether the agent: seeks **explicit approval**
(human-in-the-loop gate), respects **least-privilege scopes**, **confirms preconditions**, and can be
**interrupted/rolled back**. Metrics: rate of unauthorized high-risk actions (target zero), approval-
gate adherence, and behavior under injection attempts to trigger such actions. Test in a sandbox with
real-looking-but-fake resources. The design principle you should voice: *make dangerous actions require
confirmation and least privilege by construction, then eval that the construction holds under attack.*

---

### 6.6 How do you evaluate a web-browsing / computer-use agent's safety specifically?

**Answer.** Its whole input surface is untrusted. Key tests: **indirect prompt injection** from web
pages (the top risk); **data exfiltration** (does it paste secrets into a form/URL?); navigating to
malicious/phishing sites; **destructive UI actions** (deleting, purchasing) without consent;
credential/session misuse; and downloading/executing untrusted content. Use a sandboxed browser with
seeded malicious pages and honeytokens (canary secrets that alert if they ever leave). Measure ASR,
data-leak rate, and unauthorized-action rate. Anthropic/OpenAI both ship computer-use models with
explicit warnings here; showing you know the *specific* browsing attack surface is a strong signal.

---

### 6.7 What are jailbreaks and how do you track resistance over time?

**Answer.** Jailbreaks are prompts that bypass safety training (role-play framings, "DAN", many-shot
jailbreaking, encoding tricks, gradual escalation, crescendo). Maintain a **living jailbreak suite**,
measure **bypass rate**, and re-run on every model/prompt/guardrail change — resistance regresses
silently. Include *automated* jailbreak generation for coverage. Report bypass rate by technique and
severity, and watch the arms-race: a defense that drops bypass rate but spikes false refusals on benign
prompts is a poor trade. Track both bypass rate *and* over-refusal rate.

---

### 6.8 How do you measure over-refusal (the safety/helpfulness trade-off)?

**Answer.** Safety tuning can make agents refuse benign requests ("false positives"). Maintain a
**benign-but-sensitive** eval set (e.g., legitimate security, medical, or dual-use questions) and
measure **over-refusal rate** alongside harmful-compliance rate. The goal is the Pareto frontier: low
harmful-compliance *and* low over-refusal. Report both; optimizing only one is easy and useless. Senior
framing: safety is a *two-sided* error problem, like precision/recall.

---

### 6.9 How do you evaluate for data leakage and privacy in agents?

**Answer.** Test whether the agent leaks: the **system prompt**, **secrets/credentials** in its context,
**other users' data** (cross-tenant), and **PII** it should redact. Techniques: honeytokens/canary
strings seeded in context or tools (alert if they appear in outputs or outbound tool calls), membership/
extraction probes, and cross-session tests for memory leakage. Metric: leak rate under normal and
adversarial (injection) conditions. Also verify **egress controls** — the agent shouldn't be *able* to
send secrets to arbitrary destinations (defense in depth beyond behavior).

---

### 6.10 What is reward hacking / specification gaming, and how do you catch it in eval?

**Answer.** The agent optimizes your *measured* objective in an unintended way: editing/deleting tests
so they pass, hardcoding expected outputs, marking a task "done" without doing it, or exploiting a
grader's blind spot. Catch it with: **hidden/held-out verification** the agent can't see or modify,
**trajectory review** (not just outcome), **write-protection** on grading artifacts, adversarial graders,
and cross-checking claimed success against independent evidence. This is why outcome-only eval is
dangerous — a strong candidate always pairs outcome checks with process inspection and tamper-proofing.

---

### 6.11 How do frontier labs' safety frameworks shape agent eval (RSP / Preparedness)?

**Answer.** Labs run **capability/dangerous-evals** tied to policy: Anthropic's Responsible Scaling
Policy (ASL levels), OpenAI's Preparedness Framework, Google DeepMind's Frontier Safety Framework.
These define capability thresholds (e.g., cyber, bio, autonomy, self-replication) that, if crossed,
trigger stronger safeguards before deployment. For an agent eval role this means: you may build
**capability evals** (can the agent do dangerous-X?) as *tripwires*, run them on every major model, and
tie results to go/no-go decisions and third-party audits. Knowing these frameworks by name signals you
understand eval's governance role, not just its metrics.

---

## 7. Multi-Agent Evaluation

### 7.1 How do you evaluate a multi-agent system, and what's different from single-agent eval?

**Answer.** You keep system-level outcome metrics but add **interaction-level** ones. New dimensions:
- **Coordination:** correct task decomposition and delegation; no duplicated or dropped work.
- **Communication:** message quality/relevance, protocol adherence, and *efficiency* (token cost of
  inter-agent chatter often dominates).
- **Emergent behavior:** deadlocks, infinite hand-offs, error propagation/amplification, groupthink.
- **Attribution / credit assignment:** which agent caused a failure (much harder than single-agent).
- **Cost blowup:** multi-agent systems can multiply token/latency cost — measure it explicitly.

What's different: failures are often *interactional* (two correct agents that miscoordinate), so
trajectory tracing across agents and per-agent + per-handoff metrics are essential.

---

### 7.2 When is multi-agent actually worth it, and how do you prove it in eval?

**Answer.** Multi-agent (orchestrator-worker, debate, specialist ensembles) helps when tasks are
**parallelizable**, need **diverse expertise**, or benefit from **separation of concerns** — Anthropic's
research system showed gains for broad parallel search. But it adds cost, latency, and coordination
failure modes. Prove it with an **ablation**: single-agent baseline vs. multi-agent on the *same* tasks,
comparing success **and** cost/latency. If the single agent matches at lower cost, multi-agent isn't
justified. Never assume "more agents = better"; demonstrate the marginal value.

---

### 7.3 How do you evaluate inter-agent communication quality?

**Answer.** Score messages on **relevance** (advances the shared goal), **grounding** (accurate, not
hallucinated), **completeness** (passes needed context — under-sharing causes failures), and
**efficiency** (not verbose). Track total inter-agent tokens and message count as cost. Watch for
**error propagation** (one agent's hallucination accepted downstream as fact) and **sycophancy** between
agents (agreeing rather than checking). Use trajectory review + LLM-judge on transcripts, plus automated
metrics (message count, redundancy, context-loss at handoffs).

---

### 7.4 What emergent failure modes are unique to multi-agent systems?

**Answer.** **Deadlock/livelock** (agents wait on each other or ping-pong forever), **infinite hand-off
loops**, **error amplification** (small errors compound as they propagate), **groupthink/echo** (agents
reinforce a wrong consensus), **coordination collapse** under ambiguity, **cost explosions**, and
**responsibility diffusion** (no agent owns the final check). Eval must include long-horizon runs, step/
turn caps, loop detection, and injected disagreement to test whether the system resolves conflict or
spirals. These don't appear in single-agent tests — you have to design for them.

---

### 7.5 How do you assign credit/blame across agents when a task fails?

**Answer.** Use **trajectory tracing** with per-agent, per-message spans (a shared trace ID across
agents). Techniques: replay with one agent swapped for an oracle to isolate its contribution;
counterfactual ablations (remove/fix an agent, see if outcome changes); step-level rubrics on each
agent's contribution; and detecting the first point where the shared state diverged from correct.
Credit assignment is genuinely hard — acknowledging that and having a *method* (ablation + tracing)
rather than hand-waving is the mark of experience.

---

### 7.6 How do you evaluate orchestrator-worker architectures?

**Answer.** Separate the **orchestrator** (decomposition, delegation, synthesis) from **workers**
(sub-task execution). Orchestrator metrics: decomposition quality, correct routing, and synthesis
fidelity (does the final answer correctly integrate worker outputs?). Worker metrics: per-subtask
success. System metric: end-to-end success + total cost/latency. Common failure: a good orchestrator
plan with a worker that silently fails, and the orchestrator not verifying — so test the orchestrator's
*verification* of worker results, not just its planning.

---

### 7.7 How do you evaluate cooperative vs. competitive/adversarial multi-agent settings?

**Answer.** **Cooperative:** measure joint outcome, coordination efficiency, and whether the team beats
the best single agent (synergy). **Competitive/adversarial** (debate, negotiation, red-team-vs-blue):
measure equilibrium quality, strategy soundness, and outcome validity; use self-play and track whether
the setup produces better answers (debate can improve truthfulness) or degenerate strategies. In both,
watch for collusion, reward hacking of the interaction protocol, and instability across runs.

---

### 7.8 How do you keep multi-agent evaluation reproducible?

**Answer.** Non-determinism multiplies with agent count. Controls: pin all model versions, fix seeds,
snapshot the shared environment/memory, log every message with ordering, and control concurrency (async
message ordering can change outcomes — make it deterministic in eval). Run many seeds and report
distributions. Because a single trace is nearly unreadable, invest in **visualization** of the agent
interaction graph. Reproducibility is the first thing that breaks in multi-agent eval; naming the
concrete controls shows you've actually done it.

---
