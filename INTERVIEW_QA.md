# Agentic AI Evaluation — Master Interview Bank

A comprehensive, senior-level interview-prep bank for **Agentic AI + Evaluation** roles
(AI/ML Engineer, Applied Scientist, Eval/Red-Team, Agent Platform, and Research Engineer tracks).

This bank accompanies *"Agentic AI Evaluation — A Practical Guide"* and maps 1:1 onto its 12 chapters.
It is written to help you convince a **senior interviewer** that you understand agentic systems and
their evaluation *cold* — not just definitions, but trade-offs, failure modes, and how you would
build and defend a real evaluation program.

> **Math rendering note:** This book renders with **MathJax** (KaTeX disabled). Write inline math as
> `\( ... \)` and display math as `\[ ... \]`. Never use single-dollar `$...$` — literal dollar signs
> (e.g. costs like \\(\\$0.003\\) per call) render as plain text.

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

**Practising out loud.** Most answers end with a **"Saying it out loud"** block — a short spoken-register
version of the answer, the way you would actually say it in the room rather than the way it is written
on the page. Use it as the target for step 2 of the loop above: read the model answer for structure,
close the page, say your own version, then compare against the spoken block. It is deliberately a
*different angle* from the prose, not a summary of it, and each one ends on the thing that scores — a
named trade-off, a named failure mode, or a number.

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
Paris next week under \\(\\$600\\)" is an agent task: it must search, filter, compare, possibly call a
booking API, and confirm — several dependent steps with real side effects.

**Trade-off / why it matters for eval.** The agent's power (autonomy, tool access, statefulness) is
exactly what makes it hard to evaluate: errors *compound* across steps, outputs are *non-deterministic*,
and actions have *side effects* you must sandbox. Evaluating an agent ≠ evaluating an LLM.

*Follow-ups to pre-load:* Where does "agentic" stop and "workflow" begin? (See 1.9.) What's the
minimal viable agent?

> **Saying it out loud.** So the simplest way I'd put it is: an LLM call answers, an agent *does*. You give a plain model a prompt and it hands back text; you give an agent a goal and it loops — picks a tool, runs it, looks at what came back, decides what to do next, and keeps going until it's done or it runs out of budget. Everything interesting about agents comes from that loop, and so does everything painful about evaluating them. The number I'd anchor on is compounding: a step that's 90% reliable, run ten times, lands around 35% end-to-end, and now those failures also have side effects you can't undo.

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

> **Saying it out loud.** It's really just four things on repeat: think, do, look, check. The model decides what to do next, the scaffold actually executes it, the result gets fed back into context, and then something checks whether we're finished or out of budget. The main design choice is whether you plan the whole thing up front or decide step by step — plan-and-execute is cheaper and reads nicely, but it shatters the moment reality doesn't match the plan, whereas ReAct adapts but burns tokens on every step. And the reason I care about the phases is that each one is a separate place to score: plan quality, action correctness, whether it actually used the observation, and did it stop when it should have.

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

> **Saying it out loud.** If I had to draw it on a whiteboard, it's the model in the middle and four things hanging off it: tools, memory, the control loop, and guardrails — with observability as a plane cutting through all of it. The model is the policy, everything else is scaffolding, and most production incidents come from the scaffolding, not the model. The one people forget to mention is observability, and that's the tell — if you can't replay a run step by step, you can't debug it and you definitely can't evaluate it. The tradeoff I'd name is that every component you add buys capability and costs you determinism, so each one needs its own test surface.

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

> **Saying it out loud.** Memory is just the agent remembering things beyond the current context window — what happened earlier in the run, what happened in past runs, and durable facts about the user. It's genuinely useful, but it's the thing that quietly destroys your evaluation, because if the agent writes to memory then run two isn't the same experiment as run one. So the practical move is you snapshot memory and reset it before every eval run, exactly like you'd reset a database in an integration test. The failure mode to name out loud is memory poisoning — one wrong fact gets written and then silently reused for weeks, and no single-turn benchmark will ever catch it.

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

> **Saying it out loud.** A workflow is when I decide the control flow and the model fills in the blanks; an agent is when the model decides the control flow. It's a dial, not a switch, and the honest engineering default is to turn the dial as low as you can get away with. If a fixed pipeline solves the task, you get to test it like normal software — node by node, deterministic, cheap. The tradeoff is real: agency buys you coverage on open-ended tasks and costs you predictability in cost, latency, and failure surface, so 'agentify everything' is a red flag in an interview.

---

### 1.6 Why are agents fundamentally harder to evaluate than single-turn LLMs?

**Answer.** Five compounding reasons:
1. **Multi-step compounding error.** A 90%-reliable step run 10 times gives \\(0.9^{10} \approx 0.35\\)
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

> **Saying it out loud.** The one-liner I'd lead with is that you're not evaluating an output, you're evaluating a stochastic policy in a stateful world. Concretely: errors compound over steps, the same input gives you different trajectories, two runs can reach the same right answer by wildly different routes, and real actions leave side effects you can't just re-run. That last one is why single-score reporting is misleading — you need distributions, pass@k versus pass^k, not one number. The number that makes it land: 90% per step over ten steps is roughly 35% end to end, and that's before anyone's touched a production system.

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

> **Saying it out loud.** I like to group these so I don't just list nine random things. Planning failures, tool failures, looping, bad error handling, losing the goal, reward hacking, safety, and cost blowups — and the trick is each bucket maps to a specific check, not to vibes. Looping gets a step cap plus a repeated-action detector; reward hacking gets hidden verification tests the agent can't see or edit. The one I'd single out is reward hacking, because it's the only failure that looks like success on your dashboard — the agent edits the test instead of fixing the code and your pass rate goes up.

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

> **Saying it out loud.** When I open a trace I'm basically asking six questions: did every step serve the actual goal, were the tool calls correct and non-redundant, did it actually read the results, did it recover from errors, did it stop when it was done, and did it stay in budget. The thing to say next, though, is that most of that is automatable — redundant-call rate, tool-error rate, step count are all just numbers you can compute on every trace, not things you eyeball. Eyeballing is for the fifty traces you sample; the metrics run on all of them. The failure I look for hardest is oscillation, where the agent alternates between two actions forever and burns the whole token budget before hitting the step cap.

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

> **Saying it out loud.** Prompt engineering is picking the right words for one instruction. Context engineering is deciding what's in the window at every single step of a run — system prompt, tool schemas, retrieved docs, past tool results, memory — under a fixed token budget. I care about the distinction because a huge share of what people call reasoning failures are really context failures: the model never had the fact, or it had it forty thousand tokens ago and lost it. So my eval suite deliberately includes long-horizon and long-context stressors, and I plot success rate against context size — the curve usually bends down well before the advertised window limit.

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

> **Saying it out loud.** ReAct is just alternating 'here's what I'm thinking' with 'here's the tool I'm calling', looping until it answers. It became the default because writing the reasoning down genuinely improves tool choice and it gives you something readable to debug. But there are four honest limits: it's token-hungry, it's greedy with no lookahead so it commits early to bad paths, it has no built-in recovery, and — the big one — the written thought isn't necessarily the real cause of the action. That last point is the faithfulness problem, and the practical consequence is you score actions and outcomes, and treat the visible reasoning as a hypothesis rather than evidence.

---

### 1.11 When should you NOT build an agent?

**Answer.** Prefer a simpler solution when: the task is well-specified and repeatable (use a fixed
workflow or a single prompt); latency/cost must be tight and predictable; the action space includes
irreversible/high-stakes operations without good guardrails; or you lack the observability/eval
infrastructure to operate an autonomous system safely. Agency buys flexibility for *open-ended,
variable* tasks at the cost of predictability. The mature engineering instinct — and a green flag in
interviews — is to reach for the least-agentic design that meets the requirement.

> **Saying it out loud.** Honestly, most of the time. If the task is well-specified and repeats the same way, a fixed workflow or one good prompt wins on cost, latency, and debuggability. I'd also say no when the action space includes irreversible things without approval gates, or when the team has no tracing and no eval harness — running an autonomous system you can't observe is just an incident waiting to happen. The framing I'd give is: agency is something you buy for open-ended variable tasks, and the price is predictability, so reach for the least agentic design that meets the requirement.

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

> **Saying it out loud.** I'd describe it as four layers, cheapest first. Unit-style assertions that run in seconds, then component evals for the planner and the retriever and the judge, then full end-to-end scenarios in a sandbox, then online eval on real traffic. The order matters because it's the same instinct as a test pyramid — don't pay an LLM judge to check something a regex can check, and don't pay a human to check something a judge can check. The two things I'd make sure to say are: freeze the environment and memory per run so results are comparable, and treat the eval set as a living asset that grows every time production breaks.

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

> **Saying it out loud.** Automated eval is fast, cheap, and consistent; humans are slow, expensive, and the only source of ground truth on the fuzzy stuff. So I don't pick one, I stack them: deterministic checks on everything, an LLM judge on most of it, and humans on a stratified sample that over-weights failures and high-risk cases. The bit people miss is that the human labels aren't just for sign-off — they're the dataset you use to validate the judge, so if you cut humans entirely you lose the ability to know whether your automation is lying to you. The tradeoff is coverage versus trust, and the sampled human layer is what buys the trust back.

---

### 2.3 How do you evaluate non-deterministic agents rigorously?

**Answer.** Treat each task's success as a random variable and estimate it:
- **Multiple seeds per task** (e.g., \\(k=5\\)–\\(10\\)), report mean success with a **confidence interval**
  (Wilson interval for proportions), not a single number.
- **pass@k** — probability at least one of \\(k\\) attempts succeeds (measures *capability*; optimistic).
- **pass^k** — probability *all* \\(k\\) attempts succeed (measures *reliability*; what production cares
  about). tau-bench popularized pass^k for exactly this reason.
- **Semantic / criteria-based grading** instead of exact match: state-based checks, rubric LLM-judge,
  or embedding similarity for free-text.
- **Control variance:** fix seeds/temperature where possible, snapshot environments, and pin model
  versions so a regression is attributable to your change, not the weather.
- **Power/sample size:** enough cases and seeds that your CI can actually detect the effect size you
  care about; report the CI so reviewers see the noise floor.

The senior framing: *"a 72% success rate means nothing without a confidence interval and a statement of
how many seeds and cases produced it."*

> **Saying it out loud.** The move is to stop thinking of success as a fact and start thinking of it as a random variable you're estimating. So: run every task five or ten times with different seeds, report the mean with a confidence interval, and separate capability from reliability — pass@k for 'could it ever' and pass^k for 'does it every time'. Pin the model version and snapshot the environment, otherwise you can't tell whether your change caused the delta or the vendor did. The line I'd end on is that a 72% success rate is meaningless without a confidence interval and a count of how many seeds and cases produced it.

---

### 2.4 What makes a good eval dataset for agents?

**Answer.** Good agent eval sets are: **representative** (drawn from real usage distribution),
**discriminative** (spread of difficulty so scores aren't 0% or 100% — avoid saturation),
**verifiable** (each case has a checkable success signal, ideally programmatic), **diverse** across
tools/domains/edge-cases, **uncontaminated** (kept out of training data; a private held-out slice),
and **maintained** (versioned, with failures from prod continuously folded in). Include *negative* and
*adversarial* cases, not just happy paths. Size is secondary to signal: 100 well-chosen, well-graded
cases beat 10,000 noisy ones.

> **Saying it out loud.** A good eval set does one job: it tells you apart from yourself yesterday. That means it has to be representative of real traffic, spread across difficulty so you're not stuck at zero or a hundred percent, verifiable with a checkable success signal, and uncontaminated by anything sitting in training data. And it has to include the ugly cases — adversarial inputs, ambiguous requests, tasks the agent should refuse — not just the happy path. Size is way less important than signal: a hundred well-graded cases will beat ten thousand noisy ones, because noise is what makes your CI gate useless.

---

### 2.5 Explain offline vs. online evaluation and how they complement each other.

**Answer.** **Offline** eval runs a fixed dataset against the agent in a sandbox before deploy: fast,
reproducible, gates releases, catches regressions. **Online** eval measures the agent on *real traffic*
in production: A/B tests, live quality metrics, user feedback, and LLM-judges scoring sampled real
sessions. Offline can't capture the true input distribution, adversarial users, or long-horizon drift;
online can't safely test dangerous cases and lacks ground truth. You need both: offline as the gate,
online as the truth. A healthy loop *mines production failures into the offline suite*, closing the gap.

> **Saying it out loud.** Offline is a fixed set of tasks run in a sandbox before you ship — it's your gate. Online is measuring the thing on real traffic after you ship — it's your truth. Neither one is sufficient: offline can't see the real input distribution, adversarial users, or slow drift, and online can't safely test the dangerous cases and usually has no ground truth. So they're a loop, not a choice, and the health of that loop is measured by one thing — whether production failures are actually getting mined back into the offline suite. If that pipeline doesn't exist, your offline set slowly stops describing your product.

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
judges; calibrate against a human-labeled gold set and report agreement (Cohen's/Fleiss' \\(\kappa\\),
or correlation); and use a *different* model family as judge than as candidate where possible. Never
ship an LLM-judge you haven't validated against humans.

> **Saying it out loud.** It's using a strong model to grade another model against a rubric, and it's the only way to score fuzzy quality at scale. The catch is that the judge has personality — it prefers the first option, it prefers the longer answer, it prefers text that sounds like itself, and it drifts more lenient over time. The fixes are mechanical: sharp rubrics with anchored examples, structured output with a rationale, randomize position and average, and use a different model family for judging than for generating. But the non-negotiable is that you validate it against human labels and report the agreement number — an unvalidated judge isn't a metric, it's a vibe.

---

### 2.7 How do you validate that your evaluator/judge is trustworthy?

**Answer.** Build a **human-labeled gold set**, then measure the judge against it: agreement
(\\(\kappa\\)), precision/recall on the "fail" class (you usually care most about catching failures), and
score correlation. Run **bias probes** (swap positions, pad length, swap model identities) to quantify
position/verbosity/self-preference bias. Track judge stability across runs (same input → same score?).
Re-validate whenever you change the judge model, prompt, or rubric — a judge is itself a model that can
regress. Report these numbers; "we use GPT-as-judge" without a validation number is a red flag.

> **Saying it out loud.** You treat the judge like a model you're shipping, because it is one. Build a human-labeled gold set, then measure agreement — kappa, plus precision and recall specifically on the fail class, since catching failures is usually what you actually want. Then run bias probes: swap the order, pad one answer with fluff, hide which model wrote what, and see how much the score moves. And re-validate every time you touch the judge model, the prompt, or the rubric — judges regress silently, and 'we use GPT as a judge' with no agreement number is the answer that ends an interview badly.

---

### 2.8 How do you evaluate a RAG-augmented agent's retrieval component?

**Answer.** Separate **retrieval** from **generation**. Retrieval metrics: recall@k / precision@k,
MRR, nDCG against labeled relevant docs; plus context relevance. Generation-grounding metrics:
**faithfulness/groundedness** (is the answer supported by retrieved context? — measurable with NLI or
an LLM-judge), **answer relevance**, and **citation correctness**. The RAG-triad (context relevance,
groundedness, answer relevance — popularized by TruLens/Ragas) is a clean way to say this. Evaluate them
independently so you can localize failures: bad answer from good context = generation bug; good answer
despite bad context = lucky/parametric-knowledge, still fragile.

> **Saying it out loud.** You split it in two, because otherwise you can't tell whose fault a bad answer is. Retrieval gets the classic IR metrics — recall@k, precision@k, MRR, nDCG against labeled relevant docs. Generation gets groundedness, answer relevance, and citation correctness — is this claim actually supported by what we retrieved. The reason to separate them is diagnostic: bad answer from good context means the generator is the bug, and a good answer despite bad context means you got lucky off parametric knowledge, which is arguably worse because it will fail silently the moment the question is slightly novel.

---

### 2.9 How would you set up regression testing for an agent in CI?

**Answer.** Maintain a curated regression suite (fast, deterministic-where-possible, seeded) that runs
on every change to prompts, tools, model version, or scaffold. Gate merges on: success rate not
dropping beyond a CI threshold, no new safety violations, and cost/latency within budget. Use **paired
comparisons** against the current baseline (same cases, same seeds) so you detect *deltas* with less
noise. Pin the model version. Store traces as artifacts for debugging. Because scores are noisy, gate
on a statistically meaningful drop (e.g., outside the CI), and alert-but-don't-block on borderline
regressions. Every production incident becomes a new regression case.

> **Saying it out loud.** Keep a curated suite that runs on every change to a prompt, a tool, the scaffold, or the model version — all four count as code. Run it paired against the current baseline: same cases, same seeds, so you're measuring a delta rather than two noisy absolute numbers. Gate the merge on three things — success rate not dropping outside the confidence interval, zero new safety violations, and cost and latency inside budget. And the discipline that makes it compound is that every production incident becomes a new case in the suite, so the same bug can only ever ship once.

---

### 2.10 A stakeholder asks for "one number" for agent quality. How do you respond?

**Answer.** Push back constructively: a single scalar hides the trade-offs that matter (a model can be
more capable but slower, or higher success but with more safety violations). I'd offer a **small
scorecard** — task success (with CI), reliability (pass^k), cost/task, p95 latency, and safety
violation rate — and, if forced, a weighted composite whose weights reflect *this product's* priorities,
always shown alongside its components. The instinct to reduce everything to one KPI is where reward
hacking and blind spots creep in; a good eval lead makes the trade-offs visible to decision-makers.

> **Saying it out loud.** I'd push back, but constructively — the reason one number is dangerous is that a model can look better on it while being slower, pricier, or less safe. What I'd offer instead is a five-line scorecard: task success with a confidence interval, pass^k for reliability, cost per task, p95 latency, and safety violation rate. If they genuinely need a single figure for a slide, fine — a weighted composite, with weights that reflect this product's priorities, always shown next to its components. The failure mode to name is reward hacking: the moment one KPI becomes the target, the team starts optimizing the metric instead of the product.

---

## 3. Metrics and Benchmarks

### 3.1 What metrics do you track when evaluating agents, and how do you organize them?

**Answer.** I group metrics into five families so nothing gets forgotten:

1. **Effectiveness (did it work?):** task success rate, goal completion, partial-credit / subgoal
   completion, exact/state-based correctness.
2. **Reliability (does it work *every* time?):** pass@k, pass^k, variance across seeds, consistency.
3. **Efficiency (what did it cost?):** steps to completion, tool calls, tokens, \\(\\$\\)/task, p50/p95
   latency, time-to-first-token.
4. **Process quality (how did it get there?):** tool-selection accuracy, tool-arg validity, redundant-
   call rate, recovery rate after errors, plan quality.
5. **Safety & UX:** safety-violation rate, refusal appropriateness, hallucination rate, calibration,
   user satisfaction / thumbs-up rate, escalation rate.

**Principle:** never report effectiveness without efficiency and safety alongside — an agent that
succeeds 95% of the time but costs \\(\\$2\\) and 40s per task, or leaks data 1% of the time, is not
"better" than a cheaper safer one. Interviewers listen for this multi-axis instinct.

> **Saying it out loud.** I keep five buckets in my head so I never forget one: did it work, does it work every time, what did it cost, how did it get there, and was it safe. Effectiveness, reliability, efficiency, process quality, safety. The reason for the buckets is that people default to reporting only the first one, and success rate alone is genuinely misleading. My rule is I never say a success number without saying a cost number and a safety number in the same breath — an agent that succeeds 95% of the time but takes 40 seconds and leaks data once in a hundred runs is not better than a cheaper, duller one.

---

### 3.2 Explain pass@k vs. pass^k and when each is the right metric.

**Answer.** With \\(k\\) independent attempts at a task:
- **pass@k** = probability that *at least one* of \\(k\\) succeeds. It's optimistic and measures
  *capability / ceiling*. Great for code-gen where you can verify and keep the best of \\(k\\).
- **pass^k** = probability that *all \\(k\\)* succeed. It's pessimistic and measures **reliability /
  consistency** — the property that matters when the agent acts autonomously in production and you
  can't cherry-pick.

For a per-attempt success probability \\(p\\): pass@k \\(=1-(1-p)^k\\) rises toward 1 with \\(k\\); pass^k
\\(=p^k\\) falls toward 0. A model with \\(p=0.8\\) has pass@5 \\(\approx 0.9997\\) but pass^5 \\(\approx 0.33\\).
tau-bench uses pass^k precisely because customer-service agents must be *dependably* right, not
occasionally right. Say which one you're optimizing and why.

> **Saying it out loud.** pass@k is 'did it get it right at least once in k tries' and pass^k is 'did it get it right all k times'. So pass@k measures ceiling — how good could this be if I can verify and retry — and pass^k measures reliability, which is what you care about when the agent is acting on its own and nobody's cherry-picking. The math is brutal and worth memorizing: at 80% per attempt, pass@5 is about 99.97% but pass^5 is about 33%. That gap is the whole reason tau-bench reports pass^k, and the punchline is that a demo shows you pass@k while production charges you pass^k.

---

### 3.3 How do you measure the cost and latency of an agent, and why does it belong in eval?

**Answer.** Cost = \\(\sum\\) (input+output tokens × price) across all model calls + tool/infra costs,
reported per task and per successful task (cost-per-success is the honest number — retries inflate it).
Latency = wall-clock per task, reported as p50/p95/p99 (tails matter for UX), plus time-to-first-token
and per-step latency. It belongs in eval because agents have *unbounded* loops: a quality win that
triples token spend or blows the latency budget may be a net loss. I plot success vs. cost as a
**Pareto frontier** and pick the knee, rather than maximizing quality unconditionally. This framing —
quality is a curve against cost/latency, not a scalar — is a strong senior signal.

> **Saying it out loud.** Cost is tokens times price across every model call plus tool and infra spend, and the honest version is cost per *successful* task, because retries hide inside the average. Latency you report as p50, p95, p99, plus time to first token, since tails are what users actually feel. This belongs in the eval and not in a footnote because agent loops are unbounded — a quality win that triples token spend can easily be a net loss for the business. The framing I'd use is that quality isn't a scalar, it's a curve against cost, so I plot the Pareto frontier and pick the knee rather than maximizing accuracy unconditionally.

---

### 3.4 What is the "outcome vs. trajectory" distinction in metrics?

**Answer.** **Outcome metrics** score the end state (was the flight booked correctly? do the tests
pass?). **Trajectory (process) metrics** score *how* it got there (right tools, no redundant steps, no
unsafe actions, efficient path). You need both: outcome-only rewards reward-hacking and unsafe
shortcuts (right answer, dangerous path); trajectory-only can penalize a valid creative solution. A
robust rubric weights outcome primarily but adds trajectory checks as *gates* (e.g., zero unsafe
actions) and *efficiency* signals. See 5.1 for the eval-design version of this.

> **Saying it out loud.** Outcome asks did it end up in the right state; trajectory asks was the route sane. You need both, and the reason is asymmetric. Score only the outcome and you'll happily reward an agent that got the right answer by deleting the failing test or by doing something you'd never sanction. Score only the trajectory and you punish a clever solution just for being unfamiliar. So in practice I weight outcome as the primary score and use trajectory as gates and efficiency signals — zero unsafe actions is a hard gate, step count is a soft one.

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

> **Saying it out loud.** I'd name six or eight and for each one give three things: the domain, how it's graded, and what it can't see. SWE-bench is real GitHub issues graded by whether the repo's hidden tests pass; tau-bench is customer service against a simulated user graded on final database state with pass^k; GAIA is assistant questions that are easy for people and need tools; WebArena and OSWorld are web and desktop tasks graded by end state; Terminal-Bench and BrowseComp cover shell work and hard multi-hop search. The tell that you actually know them is the grading mechanism, because that's what determines the blind spot — a passing test suite is not the same thing as good code. And treat any headline score as of-a-date, since these move monthly and vendor-reported numbers use vendor scaffolds.

---

### 3.6 What are the limitations of public benchmarks, and how do you compensate?

**Answer.** Limitations: (1) **contamination** — public sets leak into training data, inflating scores;
(2) **saturation** — frontier models cluster near the top, losing discriminative power; (3)
**construct gap** — benchmark tasks rarely match *your* product's distribution; (4) **gaming** — vendors
optimize to the leaderboard; (5) **static** — they don't capture drift or adversarial real users; (6)
**narrow grading** — a passing test suite ≠ good code. Compensate by treating public benchmarks as a
*sanity floor*, building a **private, contamination-controlled eval set from your own traffic**, keeping
a held-out slice, refreshing tasks, and weighting production online metrics as the real signal.

> **Saying it out loud.** Six problems, and I'd rattle them off: contamination, saturation, construct gap, leaderboard gaming, staticness, and narrow grading. Contamination and saturation are the loud ones, but construct gap is the one that actually costs you money — SWE-bench going up doesn't mean your support agent got better, because your traffic looks nothing like GitHub issues. So my stance is that public benchmarks are a sanity floor, not a decision input. The real signal is a private set built from your own traffic with a held-out slice, plus online metrics, and the vendor's published number is a vendor claim until you reproduce it in your own harness.

---

### 3.7 How do you handle partial credit for long multi-step tasks?

**Answer.** Binary success is too coarse for 15-step tasks — you lose signal on *near-misses* and can't
track progress. Options: (1) **subgoal decomposition** — define checkpoints and score fraction
completed; (2) **milestone/rubric scoring** — points per required capability demonstrated; (3)
**state-distance** — how close is the final environment state to the goal state; (4) **step-level
accuracy** against a gold trajectory (careful: multiple valid paths exist). Use partial credit for
*development signal and dashboards*, but keep a strict binary "fully correct" metric for the headline —
partial credit can mask that the task actually failed for the user.

> **Saying it out loud.** Binary pass/fail on a fifteen-step task throws away almost all your signal — you can't tell a run that died on step two from one that nailed fourteen and fumbled the last. So I define checkpoints and score the fraction of subgoals hit, or measure state distance from the goal. But here's the discipline: partial credit is for dashboards and development signal, never for the headline. The failure mode is exactly that — a team celebrates 80% partial credit while the actual user-facing completion rate is 30%, because from the user's side a task that's 80% done is a task that failed.

---

### 3.8 What is benchmark contamination and how do you detect/mitigate it?

**Answer.** Contamination = eval data (or near-duplicates) present in the model's training set, so the
model "remembers" answers rather than solving. Signals: suspiciously high scores on old public sets vs.
fresh ones; sensitivity to canary strings; big drops on perturbed/paraphrased variants. Mitigations:
**private held-out sets**, freshly authored or post-cutoff tasks, canary strings, perturbation tests
(rename variables, reword), and time-split evaluation (tasks created after the model's training cutoff).
For agents specifically, dynamic environments and randomized fixtures reduce memorization.

> **Saying it out loud.** Contamination is when the eval data, or something close enough to it, was in the training set — so the model is recalling rather than solving. You spot it by comparing old public sets against fresh ones, checking canary strings, and perturbing tasks: rename the variables, reword the question, and see if the score falls off a cliff. That perturbation drop is the cleanest evidence there is. Mitigations are private held-out sets, tasks authored after the model's cutoff, and for agents specifically, randomized fixtures and dynamic environments so there's nothing stable to memorize.

---

### 3.9 How do you compare two agents/models fairly?

**Answer.** Same tasks, same seeds, same environment snapshots, same tool implementations, and same
budget caps — a **paired** comparison so you difference out task difficulty. Report deltas with
confidence intervals or a paired significance test (e.g., bootstrap or McNemar for paired binary
outcomes), not raw scores. Control for prompt/scaffold differences (or hold them constant). Show the
**full scorecard** (success, cost, latency, safety), because one model rarely dominates on all axes —
the honest output is a Pareto comparison, and the choice depends on the product's priorities.

> **Saying it out loud.** Same tasks, same seeds, same environment snapshots, same tools, same budget caps — pair everything so task difficulty cancels out. Then report the delta with a confidence interval or a paired test like bootstrap or McNemar, rather than two standalone percentages that differ by three points of noise. And show the full scorecard, because one model almost never dominates on every axis. The honest output of a model comparison is a Pareto picture plus a recommendation grounded in this product's priorities — not 'model B wins'.

---

### 3.10 What is Elo / Arena-style ranking and when is it useful?

**Answer.** Pairwise-preference ranking (e.g., LMArena/Chatbot Arena) collects human or judge votes on
"which response is better" across many head-to-heads and fits **Elo/Bradley-Terry** ratings. Useful for
*subjective, open-ended* quality where there's no gold answer, and for tracking relative model strength
over time. Weaknesses: it measures *preference*, not task success; it's gameable by style/verbosity; and
it doesn't tell you *why* one is better or whether either meets a bar. For agents, use it to compare
overall assistant quality, but pair it with task-based, verifiable evals for anything mission-critical.

> **Saying it out loud.** Arena ranking is just lots of head-to-head votes on 'which of these two is better', fitted into an Elo or Bradley-Terry rating. It's genuinely useful where there's no gold answer and quality is subjective, and it tracks relative strength over time nicely. But it measures *preference*, not task success — and preference is gameable by formatting and verbosity, which is why models tuned to look good in an arena can be middling at real work. So I'd use it as a soft prior on general assistant quality and never as the gate for anything mission-critical; for that you want verifiable, task-based evals.

---

### 3.11 How do you know when your benchmark has "saturated" and it's time to retire it?

**Answer.** When top systems cluster near the ceiling and score differences fall within noise/CI, the
benchmark no longer discriminates — improvements on it stop predicting real-world gains. Signals: >90%
scores across frontier models, shrinking spread, and leaderboard gains not reproducing in production.
Response: raise difficulty (harder subset, e.g., "Verified"→"Hard"), add adversarial/long-horizon
cases, refresh with new tasks, or move the goalposts to a harder construct. Retire or demote saturated
sets to regression-only. Keeping a benchmark alive past saturation gives false confidence.

> **Saying it out loud.** A benchmark is saturated when the differences between top systems are smaller than the noise — everyone's above ninety, the spread is shrinking, and leaderboard gains stop showing up in production. That last signal is the important one, because it's the actual definition: the benchmark no longer predicts anything you care about. The response is to raise difficulty, add long-horizon and adversarial cases, or retire it to regression-only duty so it still catches breakage without pretending to measure progress. The risk of leaving it alive at the top of the dashboard is false confidence — you keep shipping to a number that stopped moving for reasons that have nothing to do with quality.

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

> **Saying it out loud.** I break tool use into four questions and score each one separately: did it pick the right tool, did it fill in the arguments correctly, did it chain the calls in the right order, and did it actually read what came back. Splitting it matters because the fixes are completely different — bad selection is a tool-description problem, bad arguments is a schema problem, bad result handling is a prompting problem. Selection and arguments you can grade with plain code when you know the gold; 'did it use the result well' needs a judge or a human. And the metric people forget is the unnecessary-call rate, because an agent that calls three tools when one would do is quietly doubling your cost per task.

---

### 4.2 How do you evaluate tool selection when multiple tools are valid?

**Answer.** Exact-match against one "gold tool" is wrong when several tools solve the task. Instead:
(1) define an **acceptable set** per case and score membership; (2) score on **outcome** (did the chosen
tool achieve the sub-goal?) rather than identity; (3) add an **efficiency** penalty for choosing a more
expensive/slower valid tool; (4) use a rubric LLM-judge for "was this a reasonable choice given the
state." The principle: reward *effective* selection, not conformity to one canonical path.

> **Saying it out loud.** The mistake is grading against one canonical gold tool when two or three would have worked — you end up penalizing correct behavior. So instead I define an acceptable set per case, or better, score on whether the sub-goal was achieved regardless of which tool got there. Then I layer an efficiency penalty on top, because picking the valid-but-expensive tool is a real cost even though it isn't wrong. The principle to say out loud is: reward effective selection, not conformity to one path — otherwise your metric slowly trains the team to make the agent more rigid.

---

### 4.3 How do you test an agent's error handling with tools?

**Answer.** Fault-inject and observe. Scenarios: tool unavailable, 4xx/5xx errors, timeouts, malformed/
empty responses, rate limits, invalid-argument rejections, and *misleading* results. For each, I score:
**detection** (did it notice the error vs. plow ahead?), **recovery** (retry with backoff, fallback
tool, replan, or graceful degradation?), **communication** (does it tell the user / ask for help?), and
**termination** (does it avoid infinite retry loops?). Implementation: wrap tools with a fault-injection
harness that can be toggled per case, keeping the rest of the environment fixed. Robust error handling
is where flashy demos and production-ready agents diverge — interviewers love concrete injection tests.

> **Saying it out loud.** You break things on purpose. Wrap every tool in a fault-injection harness you can toggle per case, then throw timeouts, 500s, rate limits, empty responses, and — the nastiest one — results that are wrong but plausible. For each I score four things: did it notice, did it recover sensibly, did it tell the user, and did it stop. That last one matters most because the classic production failure is the blind retry loop: the tool is down, the agent retries thirty times, and you burn the whole token budget without ever surfacing the problem.

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

> **Saying it out loud.** MCP is a standard way for an agent to talk to tools and data — the pitch is USB-C for AI tools, one protocol instead of N bespoke integrations. Anthropic introduced it in late 2024 and the other major vendors have since adopted it, so it's become the default assumption in tooling conversations. For evaluation it cuts both ways: it gives you a clean, tool-agnostic place to instrument and trace every call, which is great, and it also hands you a new attack surface — an untrusted server, a poisoned tool description, an over-broad scope. So the sentence I'd end on is that MCP makes your harness reusable and your threat model bigger, and any specific spec version or feature I'd quote as of a date, because it's still moving.

---

### 4.5 How do you evaluate agents that use *many* tools (large tool spaces)?

**Answer.** As the tool count grows, selection degrades (the model can't attend to 100 tool schemas).
Eval must stress this: measure selection accuracy as a function of tool-catalog size, include
distractor/near-duplicate tools, and test retrieval-based tool selection (RAG over tools). Track
"tool confusion" (picking a similar-but-wrong tool) and schema-injection risk. Design mitigations you
can then evaluate: tool retrieval/filtering, hierarchical namespaces, and clear tool descriptions
(tool-description quality measurably affects success — a current research thread). Report success vs.
#tools-in-context as a curve.

> **Saying it out loud.** The honest finding is that tool selection degrades as the catalog grows — a model that's excellent with five tools starts confusing near-duplicates at fifty. So I don't report one selection accuracy, I report a curve: accuracy against number of tools in context, with deliberate distractor tools that look similar to the right one. That curve is what justifies building retrieval over tools or hierarchical namespaces rather than jamming every schema into the prompt. The specific failure to name is tool confusion — picking the similar-but-wrong tool — because it produces plausible-looking trajectories that fail in ways selection-accuracy-at-five would never have caught.

---

### 4.6 How do you handle tool side effects in evaluation without causing real damage?

**Answer.** Never eval write/irreversible tools against production. Use: **sandboxed environments** with
resettable state (containers, ephemeral DBs), **mocks/stubs** with recorded fixtures (VCR-style) for
deterministic replay, **simulators** for external services, and **dry-run modes**. For unavoidable
real-effect tests, use dedicated test accounts and cleanup hooks. Snapshot-and-reset between runs for
reproducibility. The eval harness owning environment lifecycle (spin up → seed → run → assert →
teardown) is the mark of a serious setup.

> **Saying it out loud.** Rule one is you never point write tools at production, ever. Everything else follows from that: containers and ephemeral databases you can reset, recorded fixtures for deterministic replay, simulators for external services, dry-run modes where the tool exists but does nothing. Where a real side effect is unavoidable, dedicated test accounts with cleanup hooks. The thing that separates a serious setup from a hobby one is that the harness owns the environment lifecycle end to end — spin up, seed, run, assert, tear down — because if you can't reset state between runs, your run two is contaminated by run one and none of your numbers mean anything.

---

### 4.7 How do you evaluate function-calling / structured-output correctness specifically?

**Answer.** Two levels: **schema conformance** (valid JSON, required fields present, correct types /
enums — measurable deterministically, and often enforced via constrained decoding) and **semantic
correctness** (are the argument *values* right for the intent, e.g., the correct date, the right unit,
the right entity resolved?). Also test: hallucinated function names/params, over/under-calling,
and correct handling when *no* function should be called. Report schema-valid rate separately from
semantically-correct rate — a model can be 100% valid JSON and still 30% wrong on values.

> **Saying it out loud.** There are two different questions hiding here and you have to report them separately. One is schema conformance — valid JSON, required fields, right types — which is deterministic and increasingly enforced by constrained decoding. The other is semantic correctness — is the date actually right, is the unit right, did it resolve the right entity. The reason to split them is the number: a model can be 100% schema-valid and still 30% wrong on values, and if you only report the first one your dashboard looks perfect while users get wrong answers. I'd also test the no-call case, since over-calling and hallucinated parameter names are common and neither shows up in a validity metric.

---

### 4.8 How do you evaluate whether an agent knows when NOT to use a tool?

**Answer.** Include cases where the correct behavior is to answer directly, ask a clarifying question,
or refuse — with tempting-but-wrong tool options available. Metrics: **over-calling rate** (invoking
tools when unnecessary) and its cost, and **under-calling rate** (should have used a tool but didn't,
causing hallucination). Well-calibrated tool use is a distinct capability from raw tool ability; many
agents that ace happy-path tool tasks fail these restraint cases.

> **Saying it out loud.** This is restraint, and it's a genuinely separate capability from tool ability. So I build cases where the right move is to just answer, or to ask a clarifying question, or to refuse — and I make sure a tempting, plausible tool is sitting right there. Two metrics fall out: over-calling rate, which costs money and latency, and under-calling rate, where it should have looked something up and hallucinated instead. What's striking is how often an agent that aces every happy-path tool task falls over on these — restraint doesn't come for free with capability.

---

### 4.9 What signals from tool use can you turn into *online* production metrics?

**Answer.** Many trajectory signals are automatable without ground truth: tool-error rate, retry rate,
redundant/duplicate-call rate, average tool calls per session, schema-error rate, tool latency
contribution to p95, and rate of hitting the step cap. These become leading indicators — a spike in
tool-error or retry rate often precedes a drop in task success and is catchable in real time. Pair with
sampled LLM-judge scoring of full sessions for quality.

> **Saying it out loud.** The nice thing about tool signals is that most of them need no ground truth at all, so they work in production where labels don't exist. Tool error rate, retry rate, duplicate-call rate, calls per session, schema-error rate, how much of your p95 latency is tool time, and how often you hit the step cap. Those are leading indicators — a spike in tool-error or retry rate usually shows up hours before task success drops, so it's what you alert on. Then you sample sessions for an LLM judge to score quality, because the cheap signals tell you something changed and the expensive ones tell you whether it mattered.

---

### 4.10 How would you build a tool-use benchmark for your own product?

**Answer.** Inventory the product's real tools and top user intents; sample real (anonymized) sessions;
for each, define the goal, required tool(s)/acceptable set, gold arguments where deterministic, and a
programmatic success check (final state). Include adversarial and error-injection variants and
restraint cases (no-tool-needed). Version it, keep a private held-out slice, and grow it from
production failures. Validate that scores on it correlate with online success — a benchmark that
doesn't predict production isn't worth maintaining.

> **Saying it out loud.** Start from what actually happens, not what you imagine: inventory the real tools, take the top user intents, sample and anonymize real sessions. For each case write down the goal, the acceptable tool set, gold arguments where they're deterministic, and a programmatic check on final state. Then deliberately add the ugly variants — error injection, adversarial inputs, and no-tool-needed restraint cases. And the last step is the one people skip: check that scores on your benchmark actually correlate with online success, because a benchmark that doesn't predict production is just a maintenance cost with a leaderboard attached.

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

> **Saying it out loud.** Outcome asks whether it landed in the right place; trajectory asks whether the route was valid, efficient, and safe. You want both because they catch opposite errors — a right answer reached by luck or by a shortcut is fragile and won't generalize, while a sound process that hit a tool outage still tells you the agent is fine. In practice outcome is the headline and trajectory rubrics are diagnostics plus hard safety gates. And with reasoning models there's an extra wrinkle: the reasoning you can see may be a post-hoc story rather than the actual cause, so scoring the prose is easier to game than scoring the actions.

---

### 5.2 How do you evaluate multi-hop / compositional reasoning?

**Answer.** Use tasks that *require* chaining facts (e.g., HotpotQA-style multi-hop QA, or synthesized
tasks with known intermediate answers). Score the **final answer** but also **intermediate hop
correctness** where you have gold sub-answers, to localize where reasoning breaks. Add **perturbations**
(change one premise → answer must change) to catch shortcut/heuristic answering. Watch for "right answer,
wrong reasoning" by including distractor context that a shortcut would latch onto. Report accuracy vs.
number of hops — degradation with depth is the interesting signal.

> **Saying it out loud.** You need tasks that genuinely can't be done in one hop, and ideally ones where you know the intermediate answers so you can see which hop broke. Then I'd add perturbations: change a single premise and check that the answer changes the way it should. That's the test that separates real chaining from pattern matching, because a shortcut answer stays the same when you flip the premise underneath it. The thing I'd actually report is accuracy against number of hops — the shape of that decay curve is far more informative than a single aggregate, and it's usually much steeper than people expect past three hops.

---

### 5.3 How do you measure planning quality?

**Answer.** Dimensions: **validity** (is the plan executable — tools exist, preconditions met?),
**goal-completeness** (does it cover all sub-goals and constraints?), **efficiency/optimality** (minimal
redundant steps), and **robustness** (contingencies for failure). Methods: compare against a reference
plan where one exists; simulate execution and check goal achievement; rubric LLM-judge for feasibility;
and measure replanning quality when the environment surprises the agent. For plan-and-execute agents,
separately score the up-front plan and the execution adherence.

> **Saying it out loud.** Four dimensions: is the plan executable, does it cover every subgoal and constraint, is it efficient, and does it have any contingency when something fails. You can score it by simulating execution and checking goal achievement, by comparing to a reference plan where one exists, or with a rubric judge for feasibility. For plan-and-execute agents I'd score the up-front plan and the execution adherence separately, since those fail differently. And the underrated measurement is replanning quality — plans are cheap, what tells you whether the agent is any good is what it does the first time reality contradicts the plan.

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

> **Saying it out loud.** Reasoning models spend a variable amount of thinking before answering, and that variability is the whole story. So the eval isn't accuracy, it's an accuracy-versus-thinking-budget curve — where's the knee, and does more thinking actually buy anything past it. Then I'd look for the two symmetric failures: overthinking, burning budget on an easy task for zero gain, and underthinking on the hard ones. And crucially, run the same tasks against the non-reasoning variant so you can justify the cost, because the headline metric here is accuracy per dollar and accuracy per second, not raw accuracy.

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

> **Saying it out loud.** Faithfulness is whether the reasoning the model writes down is actually the reasoning that produced the answer. There's published work, including from Anthropic, showing models will reach an answer for hidden reasons and then generate a plausible rationale that had nothing to do with it — sometimes not even mentioning a hint they were given. That's a problem for two reasons: you can't use the visible chain of thought as an oversight mechanism, and if you grade the reasoning text you're grading something that can be faked convincingly. The way you test it is causal intervention — inject a hint or perturb a premise and see whether the stated reasoning acknowledges it and whether the answer moves. Treat chain of thought as a signal, never as ground truth.

---

### 5.6 How do you detect and evaluate reasoning shortcuts / spurious heuristics?

**Answer.** Models often exploit dataset artifacts (answer position, keyword overlap, length) instead
of reasoning. Detect with: **counterfactual/perturbation tests** (minimal edits that should flip the
answer), **distractor injection**, **contrast sets**, and checking robustness to reordering options.
If accuracy collapses under perturbation, the "reasoning" was a shortcut. For agents, the analog is a
task that *looks* solvable by a memorized pattern but requires genuine multi-step tool use.

> **Saying it out loud.** The trick is that a model can score well by exploiting dataset artifacts — answer position, keyword overlap, length — without reasoning at all. So you probe with counterfactuals: make the smallest possible edit that should flip the answer, and see whether it flips. Add distractors, shuffle the options, build contrast sets. The rule of thumb is simple — if accuracy collapses under perturbation, it was never reasoning, it was pattern matching, and your original number was measuring your dataset rather than the model.

---

### 5.7 How do you evaluate self-correction / reflection capabilities?

**Answer.** Give tasks where the first attempt is likely wrong and observe whether the agent detects
its error and improves (Reflexion-style). Metrics: **error-detection rate**, **correction success rate**
(fixed given feedback), and **regression rate** (did reflection make a *correct* answer worse — a real
failure mode). Distinguish self-correction *with* external feedback (tool error, test failure) from
*without* (pure introspection); models are far better at the former. Beware "false reflection" where the
model claims to fix something but doesn't.

> **Saying it out loud.** Set up tasks where the first attempt is probably wrong and watch what happens next. Three numbers fall out: how often does it detect the error, how often does it actually fix it once detected, and — the one people forget — how often does reflection make a correct answer worse. That regression rate is a genuine failure mode; reflection is not free. And the big caveat is that self-correction with external feedback, like a failing test or a tool error, is a completely different capability from pure introspection, and models are dramatically better at the first. Also watch for false reflection, where it announces the fix and changes nothing.

---

### 5.8 How do you evaluate calibration and uncertainty in agent reasoning?

**Answer.** Calibration = do the model's confidence signals match its actual accuracy? Measure with
**reliability diagrams** and **Expected Calibration Error (ECE)**, or by checking whether verbalized
confidence ("I'm 90% sure") tracks empirical correctness. For agents, calibration governs when to
**ask for help, seek more info, or refuse** vs. barrel ahead. Well-calibrated agents that escalate on
low confidence are far safer in production. Test with ambiguous/underspecified tasks and score whether
the agent appropriately expresses uncertainty or clarifies rather than confidently hallucinating.

> **Saying it out loud.** Calibration is just: when the agent says it's 90% sure, is it right 90% of the time. You measure it with reliability diagrams and expected calibration error, or by checking whether verbalized confidence tracks empirical accuracy. For agents this isn't academic, because calibration is what drives the decision to ask for help, gather more information, or escalate instead of barrelling ahead. So I test it with deliberately ambiguous and underspecified tasks and score whether it clarifies rather than confidently making something up. A well-calibrated agent that escalates on low confidence is far safer in production than a slightly more accurate one that never doubts itself.

---

### 5.9 How do reasoning evals differ for "System 1" vs "System 2" style tasks?

**Answer.** Fast, pattern-matching tasks (System 1) are well-served by direct-answer accuracy and are
cheap; forcing extended thinking there mostly wastes budget. Deliberate, multi-step tasks (System 2 —
math proofs, planning, debugging) benefit from test-time compute and need **process-aware** eval
(intermediate steps, budget-vs-accuracy). A good eval suite *labels task difficulty/type* so you can
tell whether a reasoning model earns its cost only where deliberation helps, and route accordingly.

> **Saying it out loud.** Some tasks are recall and pattern matching, and forcing extended thinking on those just burns budget for nothing. Others are genuinely deliberate — proofs, planning, debugging — and that's where test-time compute earns its keep, and where you need process-aware scoring rather than just final-answer accuracy. So the practical move is to label task type and difficulty in your eval set, then check whether the reasoning model is only paying its cost where deliberation actually helps. That labeling is also what lets you build a router, and the routing win is usually bigger than any prompt tweak — same accuracy at a fraction of the spend.

---

### 5.10 How do you build ground truth for open-ended reasoning tasks?

**Answer.** When there's no single correct answer: use **rubrics** with explicit criteria + anchored
examples, **expert-authored reference solutions** for comparison, **pairwise preference** judging, and
**verifiable sub-claims** (decompose the answer into checkable facts). For math/code, prefer
**execution/verification** (does the proof check, do tests pass) over judging prose. Always validate the
grader against human labels. The senior point: invest ground-truth effort where it's checkable, and be
honest about the noise floor where it isn't.

> **Saying it out loud.** Where there's no single right answer, you have a few options: explicit rubrics with anchored examples, expert-written reference solutions, pairwise preference judging, or decomposing the answer into sub-claims you can actually check. And wherever the domain lets you, prefer verification over judgment — if it's code, run the tests; if it's math, check the proof. The senior framing is to spend your ground-truth budget where things are checkable and be honest about the noise floor where they aren't. Whatever grader you land on, you still have to validate it against human labels, or you've just moved the unverified assumption one layer down.

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

> **Saying it out loud.** The one insight that makes this answer land is that with an agent you're no longer just worried about a dangerous output space, you're worried about a dangerous *action* space. So the classic content axes still apply, but on top you get injection, data exfiltration, irreversible actions, excessive agency, and reward hacking. A model saying something bad is embarrassing; an agent sending an email or deleting a table is an incident with a legal department attached. So I'd organize the eval around the action inventory — list what the agent can actually do, rank by reversibility and blast radius, and make sure the safety suite covers the top of that list first.

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

> **Saying it out loud.** Prompt injection is when text the model reads gets treated as instructions instead of data. Direct injection is the user typing 'ignore your instructions'; indirect is the dangerous one, where the payload is hiding in a web page, an email, a PDF, a tool result, or a malicious tool description. Agents make it much worse because they don't just say something wrong, they *act* on it with real credentials — an injected page can tell a browsing agent to go exfiltrate the user's data. It's the top item on the OWASP LLM list for a reason, and the key thing to say is that you cannot fix it with input filtering, because the untrusted content arrives mid-run from a source you didn't screen.

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

> **Saying it out loud.** You build an attack suite the same way you'd build any other eval set, organized by vector: direct, indirect through retrieved content, tool-result injection, gradual multi-step attacks, obfuscation, and poisoned tool descriptions. For each one you define what success actually looks like for the attacker — followed the instruction, exfiltrated something, took an unauthorized action — and you report attack success rate. Run it with tools live in a sandbox, because text-only testing misses action-level compromise entirely, which is the whole thing you're worried about. Then track ASR over time as a regression metric, and evaluate any defense on two numbers: how much ASR it removes and how much utility it costs.

---

### 6.4 What is red-teaming for agents, and how do you make it systematic?

**Answer.** Red-teaming = adversarial probing to elicit failures. Make it systematic rather than
ad-hoc: (1) enumerate a **threat model** (who attacks, what they want, via which surface); (2) build
**attack taxonomies** and seed prompts per category; (3) scale with **automated/LLM red-teamers** that
generate and mutate attacks, plus human experts for creative ones; (4) measure ASR per category and
severity; (5) feed successes into regression + into fine-tuning/guardrail improvements. Combine manual
(depth, novelty) and automated (coverage, regression). Report residual risk, not "we red-teamed it."

> **Saying it out loud.** Red-teaming is adversarial probing, and the difference between good and bad red-teaming is whether it's systematic or vibes. Systematic means you start from a threat model — who's attacking, what do they want, through which surface — then build a taxonomy with seed attacks per category, scale coverage with automated attackers, and keep humans for the creative novel stuff. You report attack success rate by category and severity, and every success becomes a regression case. And the phrasing that matters at the end: you report residual risk, not 'we red-teamed it' — the second one is a status update, the first one is a measurement.

---

### 6.5 How do you evaluate safety of *irreversible* or high-stakes actions?

**Answer.** Classify the action space by reversibility and blast radius. For high-risk actions
(payments, deletions, external comms, code deploy), eval whether the agent: seeks **explicit approval**
(human-in-the-loop gate), respects **least-privilege scopes**, **confirms preconditions**, and can be
**interrupted/rolled back**. Metrics: rate of unauthorized high-risk actions (target zero), approval-
gate adherence, and behavior under injection attempts to trigger such actions. Test in a sandbox with
real-looking-but-fake resources. The design principle you should voice: *make dangerous actions require
confirmation and least privilege by construction, then eval that the construction holds under attack.*

> **Saying it out loud.** First I'd classify the action space by two things: can you undo it, and how big is the blast radius. Payments, deletions, outbound comms, deploys — those need an approval gate, least-privilege scopes, precondition checks, and a rollback path, and then the eval is checking that all of that holds while someone is actively attacking it. The metric is the rate of unauthorized high-risk actions, and the target is genuinely zero, not 'low'. The design principle I'd voice is that you make dangerous actions require confirmation by construction and then test that the construction survives injection — you don't rely on the model choosing to be careful.

---

### 6.6 How do you evaluate a web-browsing / computer-use agent's safety specifically?

**Answer.** Its whole input surface is untrusted. Key tests: **indirect prompt injection** from web
pages (the top risk); **data exfiltration** (does it paste secrets into a form/URL?); navigating to
malicious/phishing sites; **destructive UI actions** (deleting, purchasing) without consent;
credential/session misuse; and downloading/executing untrusted content. Use a sandboxed browser with
seeded malicious pages and honeytokens (canary secrets that alert if they ever leave). Measure ASR,
data-leak rate, and unauthorized-action rate. Anthropic/OpenAI both ship computer-use models with
explicit warnings here; showing you know the *specific* browsing attack surface is a strong signal.

> **Saying it out loud.** The thing that makes browsing agents special is that their entire input surface is untrusted — every page is attacker-controlled by default. So the tests write themselves: indirect injection from seeded malicious pages, exfiltration checks where you see if it pastes a secret into a form or a URL, destructive UI actions like deleting or purchasing without consent, credential misuse, and downloading and running things. The technique I'd name is honeytokens — plant canary secrets in the context that fire an alert the moment they leave the sandbox, which catches exfiltration you'd never find by reading transcripts. Both Anthropic and OpenAI ship computer-use models with explicit warnings about exactly this, which tells you the vendors don't consider it solved either.

---

### 6.7 What are jailbreaks and how do you track resistance over time?

**Answer.** Jailbreaks are prompts that bypass safety training (role-play framings, "DAN", many-shot
jailbreaking, encoding tricks, gradual escalation, crescendo). Maintain a **living jailbreak suite**,
measure **bypass rate**, and re-run on every model/prompt/guardrail change — resistance regresses
silently. Include *automated* jailbreak generation for coverage. Report bypass rate by technique and
severity, and watch the arms-race: a defense that drops bypass rate but spikes false refusals on benign
prompts is a poor trade. Track both bypass rate *and* over-refusal rate.

> **Saying it out loud.** Jailbreaks are prompts that get around safety training — role-play framings, many-shot, encoding tricks, gradual escalation. The important word in the question is 'over time', because resistance regresses silently: you change a system prompt or the vendor updates the model and last month's blocked attack starts working again. So you keep a living suite, you re-run it on every model, prompt, or guardrail change, and you report bypass rate broken down by technique and severity. And you always report it next to over-refusal rate, because it's trivially easy to drive bypass rate to zero by making the agent useless.

---

### 6.8 How do you measure over-refusal (the safety/helpfulness trade-off)?

**Answer.** Safety tuning can make agents refuse benign requests ("false positives"). Maintain a
**benign-but-sensitive** eval set (e.g., legitimate security, medical, or dual-use questions) and
measure **over-refusal rate** alongside harmful-compliance rate. The goal is the Pareto frontier: low
harmful-compliance *and* low over-refusal. Report both; optimizing only one is easy and useless. Senior
framing: safety is a *two-sided* error problem, like precision/recall.

> **Saying it out loud.** Over-refusal is the other side of the coin — the agent declining perfectly legitimate requests because they brush against a sensitive topic. So I keep a benign-but-sensitive set: real security questions, real medical questions, dual-use stuff that a normal user genuinely needs. Then I report over-refusal rate right alongside harmful-compliance rate, because either one alone is trivially gameable. The framing that lands is that safety is a two-sided error problem, exactly like precision and recall — you're picking a point on a frontier, and a team that only reports the harmful-compliance number has chosen a point without telling you what it cost.

---

### 6.9 How do you evaluate for data leakage and privacy in agents?

**Answer.** Test whether the agent leaks: the **system prompt**, **secrets/credentials** in its context,
**other users' data** (cross-tenant), and **PII** it should redact. Techniques: honeytokens/canary
strings seeded in context or tools (alert if they appear in outputs or outbound tool calls), membership/
extraction probes, and cross-session tests for memory leakage. Metric: leak rate under normal and
adversarial (injection) conditions. Also verify **egress controls** — the agent shouldn't be *able* to
send secrets to arbitrary destinations (defense in depth beyond behavior).

> **Saying it out loud.** Four things I test for leaking: the system prompt, credentials sitting in context, other tenants' data, and PII that should have been redacted. The mechanism I like most is honeytokens — plant a canary string and alert if it ever shows up in an output or an outbound tool call, which catches leaks you'd never spot reading transcripts. Then measure leak rate under both normal and adversarial conditions, because those numbers are usually very different. And the last point is defense in depth: verify egress controls so the agent isn't even *able* to send a secret to an arbitrary destination — behavioral safety is a filter, not a boundary.

---

### 6.10 What is reward hacking / specification gaming, and how do you catch it in eval?

**Answer.** The agent optimizes your *measured* objective in an unintended way: editing/deleting tests
so they pass, hardcoding expected outputs, marking a task "done" without doing it, or exploiting a
grader's blind spot. Catch it with: **hidden/held-out verification** the agent can't see or modify,
**trajectory review** (not just outcome), **write-protection** on grading artifacts, adversarial graders,
and cross-checking claimed success against independent evidence. This is why outcome-only eval is
dangerous — a strong candidate always pairs outcome checks with process inspection and tamper-proofing.

> **Saying it out loud.** Reward hacking is when the agent optimizes the thing you measured instead of the thing you wanted — it edits the failing test, hardcodes the expected output, or just declares the task done. What makes it uniquely nasty is that it looks like improvement on your dashboard, so the metric goes up while the product gets worse. The defenses are structural: hidden verification the agent can't see or modify, write-protection on grading artifacts, and trajectory review rather than outcome-only scoring. That's exactly why outcome-only eval is dangerous — if the only thing you check is the final state, you've handed the agent a spec to game.

---

### 6.11 How do frontier labs' safety frameworks shape agent eval (RSP / Preparedness)?

**Answer.** Labs run **capability/dangerous-evals** tied to policy: Anthropic's Responsible Scaling
Policy (ASL levels), OpenAI's Preparedness Framework, Google DeepMind's Frontier Safety Framework.
These define capability thresholds (e.g., cyber, bio, autonomy, self-replication) that, if crossed,
trigger stronger safeguards before deployment. For an agent eval role this means: you may build
**capability evals** (can the agent do dangerous-X?) as *tripwires*, run them on every major model, and
tie results to go/no-go decisions and third-party audits. Knowing these frameworks by name signals you
understand eval's governance role, not just its metrics.

> **Saying it out loud.** The big labs all have a version of this — Anthropic's Responsible Scaling Policy with ASL levels, OpenAI's Preparedness Framework, Google DeepMind's Frontier Safety Framework. They define capability thresholds in areas like cyber, bio, and autonomy, and crossing one triggers stronger safeguards before deployment. What that means practically for an eval role is that you may be building tripwire evals — can the model do dangerous-X — that feed a go/no-go decision and sometimes a third-party audit, which is a very different job from moving a quality metric. Naming these frameworks signals you understand that eval has a governance function, not just a product one, and I'd describe any specific threshold as vendor-published policy as of a date, since they get revised.

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

> **Saying it out loud.** You keep everything you had for single-agent and then add the interaction layer, which is where multi-agent systems actually break. So: did the work get decomposed and delegated properly, was anything dropped or duplicated, how good and how expensive was the chatter between agents, and did anything emergent happen like a deadlock or an endless hand-off. The awkward part is credit assignment — when a five-agent run fails, two individually correct agents can produce a failure just by miscoordinating, so you need per-agent and per-handoff spans on a shared trace ID. And measure inter-agent token cost explicitly, because in most systems I've seen the chatter, not the work, is where the budget goes.

---

### 7.2 When is multi-agent actually worth it, and how do you prove it in eval?

**Answer.** Multi-agent (orchestrator-worker, debate, specialist ensembles) helps when tasks are
**parallelizable**, need **diverse expertise**, or benefit from **separation of concerns** — Anthropic's
research system showed gains for broad parallel search. But it adds cost, latency, and coordination
failure modes. Prove it with an **ablation**: single-agent baseline vs. multi-agent on the *same* tasks,
comparing success **and** cost/latency. If the single agent matches at lower cost, multi-agent isn't
justified. Never assume "more agents = better"; demonstrate the marginal value.

> **Saying it out loud.** The honest answer is: less often than people assume. It helps when the work genuinely parallelizes, when you need separate expertise, or when separation of concerns keeps contexts clean — Anthropic published gains for broad parallel search, and that's a vendor-reported result on their own system, so treat it as a signal rather than a law. The way you prove it is an ablation: single agent versus multi-agent on the same tasks *at an equal token budget*, comparing success and cost and latency together. That equal-budget qualifier is the whole game, because multi-agent setups frequently lose once you give the single agent the same tokens — and if your sub-agents share a base model they're correlated, so three of them agreeing is not three independent verifications, it's one opinion repeated.

---

### 7.3 How do you evaluate inter-agent communication quality?

**Answer.** Score messages on **relevance** (advances the shared goal), **grounding** (accurate, not
hallucinated), **completeness** (passes needed context — under-sharing causes failures), and
**efficiency** (not verbose). Track total inter-agent tokens and message count as cost. Watch for
**error propagation** (one agent's hallucination accepted downstream as fact) and **sycophancy** between
agents (agreeing rather than checking). Use trajectory review + LLM-judge on transcripts, plus automated
metrics (message count, redundancy, context-loss at handoffs).

> **Saying it out loud.** I score messages on four things: is it relevant to the shared goal, is it grounded and accurate, is it complete enough that the receiver can act, and is it concise. Under-sharing is the sneaky one — an agent that drops a constraint at the handoff causes a failure three steps later that looks like the downstream agent's fault. Then two automated signals: total inter-agent tokens and context loss at handoffs. And the failure mode I'd name is inter-agent sycophancy — one agent hallucinates, the next one accepts it as established fact and builds on it, and now the error is laundered into the shared state where nobody re-checks it.

---

### 7.4 What emergent failure modes are unique to multi-agent systems?

**Answer.** **Deadlock/livelock** (agents wait on each other or ping-pong forever), **infinite hand-off
loops**, **error amplification** (small errors compound as they propagate), **groupthink/echo** (agents
reinforce a wrong consensus), **coordination collapse** under ambiguity, **cost explosions**, and
**responsibility diffusion** (no agent owns the final check). Eval must include long-horizon runs, step/
turn caps, loop detection, and injected disagreement to test whether the system resolves conflict or
spirals. These don't appear in single-agent tests — you have to design for them.

> **Saying it out loud.** These are the failures that literally cannot happen with one agent. Deadlock, where everyone's waiting; livelock and infinite hand-offs, where they ping-pong forever; error amplification as a small mistake propagates and gets treated as fact; groupthink, where agents converge on a confident wrong consensus; and responsibility diffusion, where every agent assumes someone else did the final check. So the eval has to include long-horizon runs, hard turn caps, loop detection, and deliberately injected disagreement to see whether the system resolves conflict or spirals. And the cost version of this is real — a coordination failure doesn't just fail, it fails expensively, sometimes ten times the budget of the equivalent single-agent run.

---

### 7.5 How do you assign credit/blame across agents when a task fails?

**Answer.** Use **trajectory tracing** with per-agent, per-message spans (a shared trace ID across
agents). Techniques: replay with one agent swapped for an oracle to isolate its contribution;
counterfactual ablations (remove/fix an agent, see if outcome changes); step-level rubrics on each
agent's contribution; and detecting the first point where the shared state diverged from correct.
Credit assignment is genuinely hard — acknowledging that and having a *method* (ablation + tracing)
rather than hand-waving is the mark of experience.

> **Saying it out loud.** This is genuinely hard and I'd say so, then give a method rather than hand-waving. The method is trace plus ablate: one shared trace ID with per-agent, per-message spans so you can find the first moment shared state diverged from correct, then counterfactual ablations — swap one agent for an oracle, or remove it, and see whether the outcome changes. That's the only way to distinguish 'this agent was wrong' from 'this agent got bad input and behaved correctly'. Without the ablation you tend to blame the last agent in the chain, which is usually the one that merely surfaced someone else's error.

---

### 7.6 How do you evaluate orchestrator-worker architectures?

**Answer.** Separate the **orchestrator** (decomposition, delegation, synthesis) from **workers**
(sub-task execution). Orchestrator metrics: decomposition quality, correct routing, and synthesis
fidelity (does the final answer correctly integrate worker outputs?). Worker metrics: per-subtask
success. System metric: end-to-end success + total cost/latency. Common failure: a good orchestrator
plan with a worker that silently fails, and the orchestrator not verifying — so test the orchestrator's
*verification* of worker results, not just its planning.

> **Saying it out loud.** Split it: the orchestrator is judged on decomposition, routing, and synthesis, and the workers on per-subtask success. Then the system gets end-to-end success plus total cost and latency. The failure that keeps showing up is a good plan plus a worker that fails quietly, and an orchestrator that just takes the worker's word for it and synthesizes a confident wrong answer. So the specific thing I'd test is the orchestrator's *verification* of worker output, not just its planning — that's the difference between an orchestrator and a message bus.

---

### 7.7 How do you evaluate cooperative vs. competitive/adversarial multi-agent settings?

**Answer.** **Cooperative:** measure joint outcome, coordination efficiency, and whether the team beats
the best single agent (synergy). **Competitive/adversarial** (debate, negotiation, red-team-vs-blue):
measure equilibrium quality, strategy soundness, and outcome validity; use self-play and track whether
the setup produces better answers (debate can improve truthfulness) or degenerate strategies. In both,
watch for collusion, reward hacking of the interaction protocol, and instability across runs.

> **Saying it out loud.** In cooperative setups the question is synergy: does the team actually beat the best single agent on the same tasks, at the same budget. Quite often it doesn't, and that comparison is the one people skip. In competitive setups — debate, negotiation, red team versus blue — you're looking at strategy soundness and whether the mechanism produces better answers, since debate can improve truthfulness but can also degenerate. In both cases watch for collusion and for agents gaming the interaction protocol itself, and remember that if the participants share a base model their errors are correlated, so agreement between them is much weaker evidence than it feels like.

---

### 7.8 How do you keep multi-agent evaluation reproducible?

**Answer.** Non-determinism multiplies with agent count. Controls: pin all model versions, fix seeds,
snapshot the shared environment/memory, log every message with ordering, and control concurrency (async
message ordering can change outcomes — make it deterministic in eval). Run many seeds and report
distributions. Because a single trace is nearly unreadable, invest in **visualization** of the agent
interaction graph. Reproducibility is the first thing that breaks in multi-agent eval; naming the
concrete controls shows you've actually done it.

> **Saying it out loud.** Non-determinism doesn't add with agent count, it multiplies — and the sleeper is async message ordering, where the same run produces different outcomes purely because two messages arrived in a different order. So: pin every model version, fix seeds, snapshot shared environment and memory, log every message with its ordering, and force deterministic concurrency in the eval harness even if production is async. Then run many seeds and report distributions rather than a single run. And practically, invest in visualizing the interaction graph, because a raw multi-agent trace is unreadable and 'I couldn't reproduce it' is where most multi-agent debugging dies.

---

## 8. Real-World Testing

### 8.1 Why isn't a good benchmark score enough to ship an agent?

**Answer.** Benchmarks are a fixed, i.i.d.-ish sample of tasks; production is an open, adversarial,
drifting distribution — real users phrase things oddly, chain unexpected tasks, hit edge cases the
benchmark authors never imagined, and change behavior in response to the agent itself. Benchmarks also
can't measure things that only exist in production: real latency/cost under real load, real tool
outages, real user satisfaction, and long-tail harm. I treat offline benchmarks as a *necessary gate*
(cheap, fast, catches regressions) and real-world testing as the *actual validation* — the two answer
different questions ("did we regress?" vs. "does this work for our users?").

> **Saying it out loud.** Because a benchmark is a fixed sample and production is an open, adversarial, drifting distribution. Real users phrase things weirdly, chain two tasks you never imagined, and change their behavior in response to the agent itself — none of that is in your test set. Benchmarks also structurally can't measure real latency under real load, real tool outages, or real satisfaction. So I treat the offline suite as the gate that answers 'did we regress' and real-world testing as the validation that answers 'does this work for our users' — two different questions, and the second one is the one the business actually asked.

---

### 8.2 How do you design a staged rollout for a new agent version?

**Answer.** A funnel of increasing exposure and decreasing reversibility: (1) offline eval gate on
regression suite; (2) **shadow mode** — new version runs on live traffic in parallel, its outputs are
logged but never shown to users, compared against production; (3) **canary** — small % of real traffic
(e.g., 1–5%), monitored closely with fast rollback; (4) **A/B test** at larger scale with pre-registered
guardrail and success metrics; (5) staged ramp to 100%. Each stage has an explicit go/no-go metric and
owner, and automatic rollback triggers (e.g., error rate or safety-flag rate crosses a threshold).

> **Saying it out loud.** It's a funnel where exposure goes up and reversibility goes down. Offline gate, then shadow mode where the new version runs on live traffic but nobody sees the output, then a canary at one to five percent with fast rollback, then a proper A/B with pre-registered metrics, then ramp to a hundred. The part that makes it real rather than a diagram is that every stage has an explicit go/no-go metric, a named owner, and automatic rollback triggers — error rate or safety-flag rate crosses a line and it reverts without a meeting. Rollouts that fail badly are almost always the ones where the rollback decision was left to human judgment at two in the morning.

---

### 8.3 How do you run a valid A/B test for an agent, given non-determinism and network effects?

**Answer.** Randomize at the **user** (not request) level to avoid a user seeing inconsistent behavior
and to capture session-level effects. Pre-register primary metric (e.g., task success or resolution
rate) and guardrails (latency, cost, escalation rate, safety flags) before launching. Run long enough to
cover weekly seasonality and for the metric's variance to converge (agents have high per-session
variance, so required sample sizes are often bigger than people expect — run a power calculation first).
Watch for interaction effects if agents share downstream resources (e.g., a shared human-agent queue) —
that violates SUTVA and can bias results; consider cluster-randomization by pod/region if so.

> **Saying it out loud.** Randomize at the user level, not the request level — otherwise the same person gets two different agents mid-conversation and you've measured confusion. Pre-register your primary metric and your guardrails, latency, cost, escalation, safety flags, before you launch, because picking the metric after you see the data is how everything wins. Run long enough to cover weekly seasonality and do a power calculation first, since per-session variance for agents is much higher than people expect and the required sample size is usually a multiple of what they guessed. And watch for shared downstream resources like a common human-escalation queue — that breaks the independence assumption and will quietly bias the result.

---

### 8.4 What is "shadow mode" evaluation and when do you use it?

**Answer.** The new agent (or new tool/prompt/model) processes real production inputs *silently* —
its outputs are logged and scored but never shown to the user or acted on for real effects. This gives
you real-traffic signal (the true input distribution) with zero user risk. Use it before any canary,
especially for changes with a risk of harmful or costly actions. Limitation: shadow mode can't measure
effects that depend on the agent actually acting (e.g., a follow-up user message reacting to its
answer), so it's necessarily a precursor to, not a replacement for, a live canary.

> **Saying it out loud.** Shadow mode is running the new version on real production inputs while throwing its output away — you log and score it, but the user never sees it and it never takes a real action. What you buy is the true input distribution with zero user risk, which is exactly what you want before anything that could do something costly or harmful. The limitation to name is that shadow mode can't see anything interactive: if the user's next message would have depended on the agent's answer, you're scoring a conversation that never happened. So it's a precursor to a canary, not a substitute for one.

---

### 8.5 How do you incorporate human-in-the-loop review into an evaluation pipeline?

**Answer.** Humans are the highest-quality but slowest/most-expensive signal, so use them where they add
the most value: (1) building/validating the gold set and rubrics that automated judges are calibrated
against; (2) auditing a stratified sample of production traffic (weighted toward low-confidence,
high-stakes, or judge-disagreement cases) on a regular cadence; (3) adjudicating disagreements between
automated judges; (4) reviewing anything that trips a safety or escalation flag. Track inter-annotator
agreement and rotate/blind reviewers to control for fatigue and bias. The goal is a flywheel: human
labels calibrate and periodically re-anchor the automated judges, not a parallel, disconnected process.

> **Saying it out loud.** Humans are your most expensive signal so you spend them where they buy the most. That's four places: building the gold set and rubrics, auditing a stratified sample of production weighted toward low-confidence and high-stakes cases, adjudicating when automated judges disagree, and reviewing anything that trips a safety flag. Track inter-annotator agreement and rotate or blind reviewers, because fatigue and anchoring are real and they silently degrade your ground truth. The goal is a flywheel where human labels keep re-anchoring the automated judges — if human review is running as a separate disconnected process, you're paying for it twice and compounding neither.

---

### 8.6 How would you design a user acceptance test (UAT) for an enterprise agent deployment?

**Answer.** Work backward from the customer's own success criteria, not your internal benchmark. Steps:
(1) interview the customer/champion users for their top real workflows and unacceptable-failure list;
(2) build a UAT task set from those workflows (not synthetic ones); (3) define pass/fail thresholds
*with* the customer before testing, including any hard "must never" constraints; (4) run in the
customer's actual environment/data where possible (a sandboxed copy); (5) include a structured
debrief capturing qualitative friction, not just pass rate. UAT failing on something your benchmark
missed is signal to add that case to your suite — the point of UAT is that it feeds back into your
own harness.

> **Saying it out loud.** Start from the customer's success criteria, not yours. Interview the champion users about their actual top workflows and, just as important, their list of things that must never happen. Build the task set from those real workflows, agree the pass thresholds with the customer *before* you test, and run it in a sandboxed copy of their real environment and data. Then debrief for qualitative friction, not just a pass rate — 'it worked but I didn't trust it' is a finding. And the loop that matters: anything UAT catches that your benchmark missed goes straight into your suite, because that gap is the most useful information the engagement produced.

---

### 8.7 How do you simulate realistic users for agent testing at scale?

**Answer.** Build an **LLM-simulated user** with a persona, a goal, and a policy for how it behaves
(patience, ambiguity, adversarial-ness, made-up details, changing its mind mid-conversation) —
tau-bench pioneered this pattern for customer-service agents. Calibrate the simulator against a sample
of real transcripts (does the simulated distribution of turn count, sentiment, and confusion match
real users?) and keep a human-transcript holdout to periodically re-validate. Value: cheap, scalable,
reproducible multi-turn coverage. Risk: simulated users can be systematically "easier" or "harder" than
real ones, and self-play between two LLMs can drift into unrealistic patterns — treat simulated results
as a leading indicator, validated against real-user data, not a substitute for it.

> **Saying it out loud.** You build an LLM user with a persona, a hidden goal, and a behavior policy — how patient it is, how vague, whether it invents details or changes its mind halfway through. tau-bench popularized this for customer service and it's the standard pattern now. The critical step people skip is calibration: compare the simulated distribution of turn counts, confusion, and sentiment against real transcripts, and keep a human holdout to re-validate periodically. The risk is that simulated users are systematically easier or harder than real ones, and two LLMs talking will drift into unrealistically tidy patterns — so treat simulated results as a leading indicator, never as the number you report to leadership.

---

### 8.8 What is "longitudinal" or drift testing and why does it matter for agents?

**Answer.** Agents interact with a changing world: tool APIs update, upstream models get silently
swapped or deprecated by the vendor, user behavior shifts, and the agent's own outputs (if logged/used
as context) can create feedback loops. Longitudinal testing means re-running a fixed regression suite
on a schedule (not just at release) and tracking metric trends over time, plus watching for **silent
regressions** from vendor-side model updates you didn't initiate. Concretely: pin model versions where
possible, alert on any metric trend beyond a control-chart threshold, and re-validate your gold set and
judge calibration periodically since "correct" answers can also go stale (e.g., pricing, policies).

> **Saying it out loud.** Agents live in a world that moves under them — tool APIs change, user behavior shifts, and the vendor can swap the model beneath you without telling you. Longitudinal testing is just re-running your fixed suite on a schedule instead of only at release, and watching the trend rather than the point. Pin model versions where you can, and put control-chart thresholds on the trend so a slow drift trips an alert before it becomes an incident. The subtle one is that your *gold answers* also go stale — pricing, policies, product names — so re-validating the gold set and the judge calibration has to be on the same schedule, or you'll eventually be measuring your agent against last year's truth.

---

### 8.9 How do you red-team an agent with real (not synthetic) adversarial input?

**Answer.** Combine internal red-teamers (who know the system's blind spots) with external/crowdsourced
red-teaming (bounty programs, dedicated red-team vendors) for outside perspective, and — where
appropriate and consented — instrumented "bug bounty"-style programs on limited production surfaces.
Give red-teamers real tool access in a sandboxed clone of production, not a toy environment, so findings
transfer. Log everything, triage by severity, and — critically — turn every finding into a permanent
regression-suite case so the same hole can't reopen silently after a fix.

> **Saying it out loud.** You want two sources: internal red-teamers who know exactly where the bodies are buried, and external or crowdsourced people who don't share your blind spots. The thing that makes findings transfer is environment fidelity — give them real tool access in a sandboxed clone of production, not a toy, because attacks that work in a toy often don't reproduce and attacks that matter often need the real tool graph. Log everything and triage by severity. And the non-negotiable step is that every finding becomes a permanent regression case, otherwise the same hole quietly reopens two refactors later and nobody notices.

---

### 8.10 How do you close the loop from real-world failures back into your eval suite?

**Answer.** Every production incident, user complaint, human-review flag, or negative feedback signal
should have a defined path: triage → root-cause (which failure mode? see the taxonomy in Part I) →
minimal repro case added to the regression suite (ideally auto-mined and de-identified from the actual
trace) → fix → verify the new case now passes → monitor that the fix didn't regress elsewhere. Track
"suite growth from production" as its own metric — a suite that never grows from real failures is
static and will eventually stop predicting production behavior. This closed loop is usually the single
biggest differentiator between a mature and immature eval program.

> **Saying it out loud.** Every incident, complaint, review flag, or thumbs-down needs a defined path, not a vibe: triage, root-cause it to a named failure mode, mine a minimal de-identified repro out of the actual trace, add it to the suite, fix, verify the new case passes, then check nothing else moved. The metric I'd actually track is suite growth from production — how many cases this quarter came from real failures rather than someone's imagination. A suite that never grows from production is a suite slowly drifting away from your product, and in my experience this closed loop is the single clearest difference between a mature eval program and an immature one.

---

### 8.11 What are the biggest practical obstacles to real-world testing, and how do you mitigate them?

**Answer.** (1) **Cost/latency of live tests** — mitigate with sampling and staged rollout rather than
full-traffic tests. (2) **Risk of user-visible harm** — mitigate with shadow mode and sandboxed
canaries with kill switches. (3) **Non-reproducibility** — mitigate by logging full context (inputs,
tool responses, model version, seed where possible) so failures can be replayed offline. (4) **Privacy/
compliance** — mitigate with strict PII handling, consent, and data retention policies baked into the
harness, not bolted on. (5) **Attribution** — when multiple changes ship close together, use canaries/
feature flags per change so you can isolate cause. Naming these constraints unprompted signals you've
actually run real-world tests, not just read about them.

> **Saying it out loud.** Five, and naming them unprompted is the tell that you've done it. Live tests cost money and latency, so you sample and stage instead of running full traffic. Real user harm, so shadow mode and kill switches. Non-reproducibility, so you log the full context — inputs, tool responses, model version, seed — well enough to replay offline. Privacy and compliance, which has to be built into the harness rather than bolted on afterwards. And attribution, because when three changes ship the same week you can't tell which one moved the metric — which is what feature flags per change are for.

---

## 9. Automated Evaluation

### 9.1 What are the main automated evaluation methods for agents, and when do you use each?

**Answer.** (1) **Programmatic/deterministic checks** — exact match, regex, schema validation, final-
state assertions (DB row exists, file created) — use whenever ground truth is verifiable; cheapest and
most reliable. (2) **LLM-as-judge** — use for open-ended quality (helpfulness, tone, faithfulness) where
no deterministic check exists; requires calibration against humans. (3) **Model-based classifiers** —
smaller fine-tuned models for a narrow signal (toxicity, PII, intent) — cheaper and more consistent
than an LLM judge for a fixed, well-defined task. (4) **Simulation-based** — environment/simulated-user
loops that measure outcome via execution. The rule: use the cheapest method that's still valid for the
question; reserve LLM judges for what genuinely requires judgment.

> **Saying it out loud.** Four families, and the whole answer is knowing which one is cheapest for the question you're asking. Programmatic checks — exact match, schema validation, does the row exist in the database — whenever ground truth is actually verifiable. LLM-as-judge for genuinely open-ended quality where no deterministic check exists. Small fine-tuned classifiers for narrow, high-volume signals like toxicity or PII, which are cheaper and more consistent than a big judge. And simulation, where you measure outcome by executing in an environment. The rule I'd state is: use the cheapest method that's still valid, and reserve judgment-based grading for things that genuinely require judgment.

---

### 9.2 How do you build and validate an LLM-as-judge pipeline end to end?

**Answer.** (1) Write an explicit rubric with the exact criteria and a scoring scale; (2) few-shot the
judge with calibration examples spanning the scale, including hard boundary cases; (3) validate against
a human-labeled gold set — report agreement (accuracy, Cohen's/weighted kappa) and *where* it disagrees
(systematic bias, not just noise); (4) mitigate known biases: position bias (randomize order in pairwise
comparisons), verbosity bias (verbosity-controlled prompts or explicit "do not reward length"),
self-preference bias (avoid judging with the same model family when possible, or explicitly test for
it); (5) monitor judge drift over time by periodically re-running the human validation. A judge without
a documented human-agreement number is not production-ready — this is one of the fastest ways to signal
seniority in an interview.

> **Saying it out loud.** Write the rubric explicitly, anchor it with few-shot examples that span the scale including the hard boundary cases, then validate against a human-labeled gold set. And validate properly — report agreement, but also look at *where* it disagrees, because systematic bias and random noise need completely different fixes. Then handle the known biases mechanically: randomize order to kill position bias, tell it not to reward length, avoid judging with the same model family you're generating with. And re-run the human validation on a schedule, because judges drift. A judge with no documented human-agreement number isn't production-ready, and saying that sentence is one of the fastest ways to sound senior.

---

### 9.3 What's the difference between pointwise, pairwise, and rubric-based LLM judging — when do you use which?

**Answer.** **Pointwise** (score a single response on a scale): fast, cheap, parallelizable, but LLMs are
worse at consistent absolute scoring — scores drift and clump. **Pairwise** (A vs. B, which is better):
LLMs are meaningfully more reliable at comparisons than absolute scores, ideal for model/prompt A-B
selection and for building preference-based leaderboards (e.g., Elo/Bradley-Terry aggregation of
pairwise votes), but is \\(O(n^2)\\) and doesn't give an absolute bar. **Rubric-based** (decompose into
sub-criteria, each scored): best for diagnosing *why* something failed and for multi-dimensional agent
behavior (correctness + safety + efficiency separately) — more work to build but far more actionable.
In practice: rubric for regression-suite depth, pairwise for model/prompt selection, pointwise only for
lightweight production monitoring where cost matters most.

> **Saying it out loud.** Pointwise is 'score this one out of five' — cheap and parallel, but LLMs are genuinely bad at consistent absolute scoring, the numbers clump and drift. Pairwise is 'which of these two is better', and models are meaningfully more reliable at comparison than at absolute judgment, which is why arena-style leaderboards use it — but it's quadratic and it never tells you whether either option cleared the bar. Rubric-based decomposes into sub-criteria and is the only one that tells you *why* something failed. In practice I use rubric for the regression suite, pairwise for picking between models or prompts, and pointwise only for cheap production monitoring.

---

### 9.4 How do you evaluate the evaluator — i.e., trust an LLM judge without circular reasoning?

**Answer.** Never let the judge be its own ground truth. Anchor it against: (1) a static human-labeled
gold set (measure agreement, refresh periodically); (2) known-answer "trap" cases with an obviously
correct verdict (canaries — if the judge fails these, something's broken, e.g., a prompt regression);
(3) cross-validation with a second, independently-built judge (different model/prompt) — persistent
disagreement flags an ambiguous rubric, not a passing grade; (4) tracking judge-score-vs-downstream-
outcome correlation (does a high judge score actually predict user satisfaction / task success?). A
judge is a measurement instrument — it needs the same validation discipline as any sensor.

> **Saying it out loud.** The rule is the judge is never its own ground truth. So you anchor it four ways: a human-labeled gold set you refresh, trap cases with obviously correct verdicts that fire an alarm if the judge prompt regresses, a second independently built judge for cross-checking, and — the one people forget — correlation between judge score and downstream outcome. That last one is the real test: does a high judge score actually predict user satisfaction or task success? If it doesn't, the judge is precise and useless. Treat it like a sensor: it needs calibration against a reference, and calibration expires.

---

### 9.5 How do you reduce cost and latency in an automated eval pipeline without losing signal?

**Answer.** (1) **Cascade/triage**: cheap deterministic/classifier checks first, escalate only
ambiguous or flagged cases to an expensive LLM judge. (2) **Sampling**: judge 100% of a small canary
set but only a statistically-sized random sample of full production traffic, oversampling low-
confidence and high-stakes segments. (3) **Batching and caching**: batch judge calls, cache
judgments for identical (or near-identical, dedup'd) trajectories. (4) **Smaller/distilled judges**:
distill a large judge's decisions into a cheaper fine-tuned classifier for the highest-volume, most
stable checks, reserving the frontier judge for genuinely hard/novel cases. Track the cost-per-eval-run
as a first-class metric — an eval suite that becomes too slow/expensive to run gets skipped, which is
worse than a smaller one that always runs.

> **Saying it out loud.** Four levers. Cascade — cheap deterministic checks first, escalate only the ambiguous cases to the expensive judge. Sample — judge everything on a small canary set, but only a statistically sized slice of production, oversampling the risky segments. Batch and cache, including deduping near-identical trajectories. And distill: take the big judge's decisions and train a small classifier for your highest-volume, most stable checks. And I'd track cost-per-eval-run as a first-class metric, because the real failure mode isn't an expensive suite, it's a suite that got so slow people started skipping it — a smaller suite that always runs beats a thorough one that runs monthly.

---

### 9.6 What automated checks can you run on an agent's full trajectory (not just final answer)?

**Answer.** Structural/programmatic: step count vs. budget, tool-call schema validity, loop/oscillation
detection (repeated identical calls), error-recovery presence, forbidden-action detection (regex/
classifier over tool calls for disallowed actions), and state-diff assertions at each checkpoint.
Judge-based: step-level rubric scoring (was this step justified given prior state?), plan-adherence
scoring, and grounding checks (does each claim trace to a retrieved/tool-returned fact?). Combining
cheap structural checks (which catch a large fraction of failures) with sparser judge-based trajectory
review is far more cost-effective than judging every step with an LLM.

> **Saying it out loud.** A surprising amount is just structural and needs no model at all: step count against budget, schema validity on every tool call, loop detection for repeated identical actions, presence of error recovery, forbidden-action matching over tool calls, and state assertions at checkpoints. Then on top of that, sparser judge-based checks — was this step justified given the prior state, did it stick to the plan, does each claim trace back to a tool result. The economics matter here: the cheap structural checks catch a large fraction of failures for essentially nothing, so judging every single step with an LLM is usually paying frontier prices for signal a regex already gave you.

---

### 9.7 How do you automatically detect hallucination / lack of grounding in agent outputs?

**Answer.** (1) **Claim decomposition + verification**: extract atomic claims from the output, and for
each, check support against retrieved context/tool results (NLI-style entailment check or LLM-judge
per-claim); report a faithfulness/attribution rate. (2) **Consistency checks**: sample the same query
multiple times (or perturb it slightly) and flag high variance in factual claims as a hallucination
signal. (3) **Tool-grounding checks**: specifically verify that any claim attributable to a tool call
actually matches that tool's returned value (catches "the agent ignored the tool result and made
something up"). Report faithfulness/attribution rate as a first-class metric, not folded into a vague
"quality" score — it's usually the single most decision-relevant automated signal for RAG-heavy agents.

> **Saying it out loud.** Three techniques. Decompose the output into atomic claims and check each one for support against the retrieved context or tool results, entailment-style — that gives you a faithfulness rate. Consistency sampling: ask the same thing a few times and treat high variance in the factual claims as a hallucination signal. And tool grounding specifically — verify that anything attributable to a tool call actually matches what that tool returned, which is what catches the classic 'agent ignored the result and made something up'. Report faithfulness as its own number rather than folding it into a vague quality score; for anything RAG-heavy it's usually the single most decision-relevant automated signal you have.

---

### 9.8 How do you automate evaluation of multi-turn conversations end to end?

**Answer.** Score at three levels: **turn-level** (was this response appropriate given history?),
**trajectory-level** (did the conversation make progress toward the goal, e.g., using an LLM-simulated
user that has a hidden goal and reports resolution), and **outcome-level** (was the overall goal
achieved, checked programmatically where possible — order placed, ticket resolved). Automate the
simulated-user loop for scale, but validate its behavior against a held-out set of real transcripts. Also
track conversation-level structural signals automatically: turn count, user-repeats-self rate (proxy for
the agent misunderstanding), and clarification-question rate.

> **Saying it out loud.** Score at three levels because they fail differently. Turn level — was this response appropriate given the history. Trajectory level — did the conversation actually make progress, which you get from a simulated user holding a hidden goal and reporting whether it was resolved. And outcome level — was the thing done, checked programmatically: order placed, ticket closed. Automate the simulated-user loop for scale but keep validating it against real transcripts. And grab the free structural signals while you're there: turn count, clarification rate, and how often the user repeats themselves — that repeat rate is a lovely unlabeled proxy for the agent misunderstanding.

---

### 9.9 What's your approach to automatically generating new eval cases (rather than hand-writing all of them)?

**Answer.** (1) **Mining production**: sample real (de-identified) sessions, especially ones that hit
failure signals (low judge score, escalation, negative feedback, retry loop) and turn them into
regression cases with human review. (2) **LLM-based generation**: prompt a strong model to generate
diverse task variants from a seed taxonomy (persona × intent × difficulty), then human-filter for
validity. (3) **Mutation/perturbation**: programmatically perturb existing cases (paraphrase, inject
noise, change entity values, add distractors) to multiply coverage cheaply. (4) **Adversarial
generation**: use a red-team LLM to specifically generate cases designed to break the agent. All
generated cases need a human validity pass before they count as gold — automated generation without
validation just adds label noise.

> **Saying it out loud.** Four sources, roughly in order of value. Mining production is the best — sample real de-identified sessions, especially ones that hit a failure signal, and turn them into cases. Then LLM generation from a seed taxonomy of persona by intent by difficulty. Then cheap programmatic mutation of existing cases: paraphrase, swap entities, add distractors. And adversarial generation with a red-team model aimed at breaking things. But the rule that holds all of it together is that every generated case gets a human validity pass before it counts as gold — generation without validation doesn't add coverage, it adds label noise, and label noise in your gold set poisons every judge you calibrate against it.

---

### 9.10 How do you decide the right balance between automated and human evaluation over a product's lifecycle?

**Answer.** Early on, human eval dominates (no calibrated judge exists yet, the task/rubric definition is
still evolving). As the product matures: use human eval to build the gold set and calibrate judges;
once judge-human agreement is validated and stable, shift routine/regression testing to automated
checks and reserve humans for gold-set maintenance, judge re-calibration, disagreement adjudication, and
auditing a rotating sample. The failure mode to avoid: fully automating too early (before the judge is
validated) or never automating (human eval doesn't scale to the cadence agentic development needs —
you'll ship slower than competitors without ever catching more real issues).

> **Saying it out loud.** It moves over the product's life. Early on humans dominate, because you don't have a calibrated judge yet and honestly you don't have a stable rubric yet either. As it matures, humans build the gold set and calibrate the judges, and once agreement is validated and stable you push routine regression work onto automation and keep humans for gold-set maintenance, recalibration, adjudication, and a rotating audit sample. Two symmetric failure modes: automating before the judge is validated, which means you're measuring nothing confidently, and never automating at all, which means you ship slower than everyone else without catching more real issues.

---

## 10. Benchmark Datasets

### 10.1 Walk through the major public agent benchmarks and what each actually measures.

**Answer.** A working mental map: **SWE-bench (Verified)** — can an agent resolve real GitHub issues in
real Python repos, graded by whether the held-out test suite passes; the "Verified" subset is human-
filtered for solvability. **GAIA** — general-assistant tasks requiring web browsing, tool use, and
multi-step reasoning, with unambiguous short-answer grading; deliberately spans easy-to-very-hard tiers.
**WebArena** — realistic web navigation/transaction tasks across self-hosted clones of real site
categories (e-commerce, forums, dev tools), graded by functional/final-state correctness. **AgentBench**
— a suite spanning multiple environments (OS/shell, DB, web shopping, games) under one harness, useful
for breadth. **Terminal-Bench** — shell/CLI competence in isolated containers (scripting, sysadmin,
CI-style tasks). **OSWorld** — real desktop-GUI tasks (files, browsers, office apps) on a live Ubuntu
VM. **tau-bench / tau2-bench** — multi-turn customer-service-style agents graded on policy compliance
and task resolution against a simulated user, across domains like retail/airline; tau2-bench (Sierra
Research) extends this with more realistic tool-agent-user dynamics. **BFCL (Berkeley Function-Calling
Leaderboard)** — function/tool-calling accuracy in isolation. Know each one's grading mechanism
(programmatic final-state check vs. exact-match vs. LLM-judge) — that's usually the more interesting
interview thread than the leaderboard numbers themselves.

> **Saying it out loud.** I'd give a mental map rather than a list of scores. SWE-bench is real GitHub issues graded by hidden tests. GAIA is assistant tasks needing browsing and tools with short verifiable answers. WebArena and OSWorld are web and desktop tasks graded on end state. AgentBench is a breadth suite, Terminal-Bench is shell competence, tau-bench and tau2-bench are multi-turn customer service against a simulated user, and BFCL is function-calling in isolation. The thing to lead with for each is the grading mechanism, because that determines the blind spot — and I'd quote any specific score as of a date with the scaffold named, since these numbers move monthly and a vendor's reported figure comes with the vendor's harness.

---

### 10.2 What are the known weaknesses of public agent benchmarks?

**Answer.** (1) **Contamination** — popular benchmarks leak into pretraining/fine-tuning data over time,
inflating scores without real capability gain. (2) **Saturation** — once a benchmark is heavily
optimized against, it stops discriminating between strong models (a known pattern across many static
benchmarks). (3) **Narrow domain transfer** — e.g., SWE-bench is Python-heavy GitHub issues; a high
score doesn't guarantee general coding-agent competence, let alone your product's domain. (4) **Static
snapshots** — real environments (websites, APIs) drift, but the benchmark's environment often doesn't,
so it can reward memorized affordances over genuine capability. (5) **Grading brittleness** — exact-
match and even LLM-judge grading can mis-score valid-but-different solutions. Conclusion I'd give in
an interview: public benchmarks are useful as a rough capability signal and for cross-lab comparison,
but they should never be your only or primary decision signal for a specific product.

> **Saying it out loud.** Five, and I'd give a concrete example with each. Contamination — the set leaks into training data and the score rises without the capability. Saturation — once everyone optimizes against it, it stops separating models. Narrow transfer — SWE-bench is Python GitHub issues, so a high score says surprisingly little about a coding agent in your monorepo, let alone about a non-coding product. Static environments — real websites and APIs drift, benchmark clones don't, so you can reward memorized affordances. And grading brittleness, where a valid-but-different solution gets marked wrong. Conclusion: public benchmarks are a cross-lab capability signal, not a product decision input.

---

### 10.3 How do you decide whether a public benchmark is relevant to your product?

**Answer.** Check for **construct validity relative to your task**: does the benchmark's task
distribution, tool set, and difficulty resemble what your users actually do? If your agent does internal
enterprise workflows, SWE-bench tells you little about it. Practically: run the benchmark, then manually
inspect ~20 failure cases — do the failure modes look like the ones you see in your own eval/production?
If yes, it's a reasonable proxy and cheap regression signal; if no, don't use it as a go/no-go gate,
though it can still be a useful "does this model have baseline competence" filter before you invest in
building product-specific evals.

> **Saying it out loud.** The question is construct validity — does the benchmark's task distribution, tool set, and difficulty look anything like what your users actually do. And the practical test is cheap: run it, then read twenty failure cases by hand and ask whether those failures look like the ones you see in your own traffic. If they do, it's a fine proxy and a cheap regression signal. If they don't, it can still serve as a baseline-competence filter before you invest in building product-specific evals, but it has no business being a go/no-go gate.

---

### 10.4 How do you build a custom benchmark dataset for your own agent from scratch?

**Answer.** (1) **Taxonomy first**: enumerate task types, difficulty tiers, and known failure modes for
your domain (don't start from examples, start from the space you need to cover). (2) **Source real
distribution**: sample real (or realistic synthetic, validated by domain experts) tasks weighted like
production traffic, not just "interesting" edge cases. (3) **Gold labels**: define a programmatic check
where possible (final state, structured output); fall back to a calibrated rubric + LLM-judge with human
spot-check where not. (4) **Stratify and version**: tag each case by type/difficulty/source so you can
report sliced results and track suite evolution; freeze released versions, keep a private held-out slice
to prevent overfitting to the public one. (5) **Validate the benchmark itself**: does a known-good agent
score high and a known-bad one score low (sanity check)? Does the score correlate with real user
outcomes? A benchmark that never gets validated against reality is just a number.

> **Saying it out loud.** Taxonomy first, examples second — enumerate the task types, difficulty tiers, and known failure modes you need to cover, otherwise you end up with a pile of interesting edge cases and no coverage of the boring 80%. Then source from the real distribution and weight like production, not like your curiosity. Programmatic gold labels wherever the domain allows, calibrated rubrics where it doesn't. Tag everything by type and difficulty so you can slice, freeze released versions, and keep a private held-out slice. And then validate the benchmark itself: does a known-good agent score high and a known-bad one score low, and does the score correlate with real user outcomes — a benchmark nobody validated against reality is just a number with a changelog.

---

### 10.5 How large does a benchmark need to be, and how do you decide?

**Answer.** Size is a statistical-power question, not a round number: given your current pass rate and
the minimum detectable difference you care about (e.g., "did this change move success by ≥2pp?"), compute
required n for the desired confidence (often via a simple binomial/normal-approximation power calc, or a
bootstrap on historical variance). In practice, tens of cases per fine-grained slice is a reasonable
floor to say anything at all, hundreds per slice gives real statistical power for typical effect sizes,
and thousands total spread across slices lets you detect small regressions in aggregate. Report
confidence intervals (not just point pass rates) so viewers know whether a 2-point swing is signal or
noise — this is a strong signal of statistical maturity in an interview.

> **Saying it out loud.** It's a power question, not a round number. Start from your current pass rate and the smallest difference you care about detecting — say two percentage points — and compute the n you need for that, either analytically or by bootstrapping historical variance. Rules of thumb: tens of cases per slice is the floor for saying anything, hundreds per slice gives real power for typical effect sizes, and a few thousand total across slices lets you catch small aggregate regressions. And the discipline that makes it useful is reporting confidence intervals, because otherwise nobody in the room can tell whether that two-point swing was your change or the dice.

---

### 10.6 How do you avoid benchmark contamination and gaming?

**Answer.** (1) Keep a **private held-out set** never published or sent to any external eval/vendor.
(2) **Rotate/refresh** the public-facing slice periodically so memorization decays in value. (3)
**Canary strings/unique IDs** in cases to detect verbatim leakage into training data. (4) **Behavioral
tests, not just outcome**: paraphrase/perturb the same underlying task so pattern-memorization doesn't
transfer. (5) Be alert to **Goodhart's law internally** too — if an eval score becomes a bonus/promotion
metric, people (and automated optimization loops) will overfit to it; periodically audit whether score
gains are showing up in independent signals (production success, red-team results) or only on the
benchmark itself.

> **Saying it out loud.** Externally: keep a private held-out set that never leaves the building, rotate the public-facing slice so memorization decays, seed canary strings to detect verbatim leakage, and paraphrase or perturb the same underlying task so pattern memorization doesn't transfer. But the part people miss is internal Goodhart — the moment an eval score becomes a promotion or bonus metric, humans and automated optimization loops will both overfit to it, entirely sincerely. So I'd periodically audit whether score gains are showing up in independent signals like production success and red-team results, and if the benchmark is the only thing moving, that's the answer.

---

### 10.7 What's your process for slicing benchmark results, and why does it matter more than the headline number?

**Answer.** Slice by: task type, difficulty tier, input length, tool count involved, language/locale,
and (crucially) by known-risk segments (safety-relevant categories, high-stakes user groups). The
headline aggregate can hide a model that's flat overall but has regressed badly on a small, important
slice (e.g., dropped 15 points on a rare-but-critical intent). I always ship a slice table alongside any
aggregate number, and treat any slice regression beyond a set threshold as a blocking issue even if the
aggregate improved — aggregate-only reporting is one of the more common failure modes I've seen in
eval reviews.

> **Saying it out loud.** I slice by task type, difficulty, input length, number of tools, locale, and — most importantly — known-risk segments. The reason is that an aggregate is an average over things you care about unequally: a model can be flat overall while dropping fifteen points on a rare but critical intent, and the headline will never show it. So I ship a slice table with every aggregate, and I treat any slice regression beyond threshold as blocking even when the aggregate improved. Aggregate-only reporting is genuinely one of the most common failure modes I've seen in eval reviews, and it's the one that ships the bad release.

---

### 10.8 How do you keep a benchmark suite maintained as the product evolves?

**Answer.** Treat it like a living codebase, not a frozen artifact: version it, code-review changes to
gold labels/rubrics, deprecate cases that no longer reflect the product (with a changelog explaining
why, so historical score drops are interpretable), and continuously add cases from the production
failure-mining loop (9.9/8.10). Assign explicit ownership — a benchmark with no owner rots (stale
labels, silently-broken harness code, unreviewed additions). Periodically re-run judge/rubric
calibration against fresh human labels since "ground truth" itself can drift (policies change, correct
answers change).

> **Saying it out loud.** Treat it like a codebase, not an artifact. Version it, code-review changes to gold labels and rubrics, deprecate stale cases with a changelog so a historical score drop is interpretable rather than mysterious, and keep feeding it from the production failure-mining loop. And assign an owner — an unowned benchmark rots in a very specific way: labels go stale, harness code silently breaks, and additions land unreviewed until nobody quite trusts the number anymore. The subtle one is that ground truth itself drifts as policies and prices change, so judge and rubric recalibration against fresh human labels has to be on a schedule, not an impulse.

---

### 10.9 How would you compare two frontier models for your product using benchmarks, when public leaderboards disagree?

**Answer.** Public leaderboards disagree because they weight different capabilities and use different
grading; don't try to reconcile them abstractly. Instead: run *your* custom benchmark (10.4) plus 1–2
relevant public ones for external comparability, on identical infra/harness/decoding settings for both
models (same tools, prompts, temperature) to isolate the model variable. Report cost/latency alongside
accuracy (a small accuracy gain rarely justifies a large cost/latency increase for production agents),
and run a small live shadow-mode comparison (8.4) before fully committing, since offline numbers alone
have repeatedly missed real deployment issues (tool-format quirks, prompt sensitivity, safety behavior).

> **Saying it out loud.** When leaderboards disagree, don't try to reconcile them in the abstract — they weight different capabilities and grade differently, so the disagreement is real and unresolvable at that level. Run your own benchmark plus one or two relevant public ones, on identical infrastructure: same tools, same prompts, same decoding settings, so the only variable is the model. Report cost and latency next to accuracy, because a two-point accuracy gain rarely justifies a doubling of cost for a production agent. Then do a small shadow-mode comparison before committing, since offline numbers have repeatedly missed real deployment issues — tool format quirks, prompt sensitivity, different refusal behavior.

---

### 10.10 What benchmark would you build if none of the public ones fit your agent's domain?

**Answer.** I'd apply the same construction discipline as 10.4 but front-load domain-expert involvement:
partner with subject-matter experts to define what "correct" and "acceptable failure" mean in the
domain (this is often the hardest and most valuable part, especially in regulated domains), build a
programmatic grader wherever the domain has a checkable ground truth (a compliance rule, a numeric
answer, a required disclosure), and use structured rubrics reviewed by domain experts for the rest.
Pilot on a small held-out real-traffic sample before committing to the full build, and publish the
benchmark's construction methodology internally so its results are trusted and reproducible by other
teams — an eval nobody trusts doesn't get used regardless of how rigorously it was built.

> **Saying it out loud.** Same construction discipline as building any custom set, but with domain experts front-loaded — because in a specialized or regulated domain, defining what 'correct' and 'acceptable failure' even mean is the hardest and most valuable part of the work, and it's not something an engineer can shortcut. Build a programmatic grader anywhere the domain has a checkable rule — a compliance requirement, a required disclosure, a numeric answer — and use expert-reviewed rubrics for the rest. Pilot on a small held-out slice of real traffic before committing to the full build. And publish the construction methodology internally, because an eval nobody trusts doesn't get used, no matter how rigorously it was built.

---

## 11. Evaluation Tooling

### 11.1 What are the categories of tooling you need for agent evaluation, end to end?

**Answer.** (1) **Tracing/observability** — capture full trajectories (inputs, intermediate steps, tool
calls/results, final output) with a shared trace ID, ideally via an open standard (e.g., OpenTelemetry
GenAI semantic conventions) so it's portable across vendors. (2) **Experiment/eval harness** — define
datasets, run agents against them, score with programmatic checks and/or LLM judges, compare runs. (3)
**Human annotation/review** — queues, rubrics, inter-annotator agreement tooling for building gold sets
and auditing. (4) **Dashboards/alerting** — production metric trends, drift detection, on-call alerting.
(5) **Dataset/prompt/version management** — versioned datasets, prompts, and model configs so results are
reproducible and diffable across changes. Treat this as an integrated pipeline, not disconnected tools —
the biggest tooling failure I see is trace data that never makes it into the eval harness that could
learn from it.

> **Saying it out loud.** Five categories. Tracing, so you can see full trajectories with a shared trace ID — ideally on an open standard like the OpenTelemetry GenAI conventions so it's portable. An eval harness that runs datasets against the agent and scores them. Human annotation with queues and agreement tracking. Dashboards and alerting for production. And version management for datasets, prompts, and model configs, so results are reproducible. But the thing I'd emphasize is that these have to be one pipeline, not five tools — the most common tooling failure I see is beautiful trace data that never reaches the eval harness that could have learned from it.

---

### 11.2 Compare building an in-house eval harness vs. adopting a platform (e.g., LangSmith, Braintrust, Arize/Phoenix, Weights & Biases Weave, Galileo, Humanloop).

**Answer.** Platforms buy speed: tracing, dataset management, judge templates, dashboards, and
collaboration UI out of the box — valuable when the team is small or the eval need is generic. In-house
buys control: custom domain-specific graders, tighter integration with proprietary infra, no vendor
lock-in on sensitive trace data, and no per-seat/per-trace cost scaling surprises at volume. My default:
adopt a platform for tracing/observability and human-annotation workflows (undifferentiated, expensive to
rebuild well) but keep the *grading logic* (custom programmatic checks, domain rubrics) in-house and
portable, so you're never locked into one vendor's judge implementation. Re-evaluate the build/buy line
as volume and domain-specificity grow.

> **Saying it out loud.** Platforms buy you speed — tracing, dataset management, judge templates, dashboards, a review UI — and that's genuinely worth it for a small team or a generic need. In-house buys control: domain-specific graders, no vendor holding your trace data, and no per-trace pricing surprise at volume. My default split is to adopt for tracing and annotation workflow, which is undifferentiated and expensive to rebuild well, and keep the grading logic in-house and portable so you're never locked into someone else's judge implementation. And revisit the line as you scale — what's sensible to buy at ten evals a day can be the wrong answer at ten thousand.

---

### 11.3 What should an agent tracing schema capture, at minimum?

**Answer.** Per trace: a unique trace ID, the initiating request/user context, model+prompt version, and
overall outcome/latency/cost. Per step/span: step type (LLM call, tool call, retrieval), full input/
output, timestamps, token counts, and — for tool calls — the tool name, arguments, and raw result
(success/error). For multi-agent systems, an agent/role identifier and parent-child span relationships.
This is close to what the OpenTelemetry GenAI semantic conventions standardize (spans for `gen_ai.*`
operations with cost/token attributes), which is worth knowing by name — it signals you think about
observability as infrastructure, not a bespoke logging hack.

> **Saying it out loud.** Per trace: a unique ID, the initiating request and user context, model and prompt versions, and overall outcome, latency, and cost. Per span: step type, full input and output, timestamps, token counts, and for tool calls the name, the arguments, and the raw result including errors. For multi-agent, an agent identifier plus parent-child relationships between spans. This maps closely onto the OpenTelemetry GenAI semantic conventions, which is worth naming out loud because it signals you think of observability as infrastructure rather than as logging you bolt on. And the practical test of a schema is: can you replay the run from it? If not, it's a log, not a trace.

---

### 11.4 How do you evaluate/select a tool-calling or agent framework (e.g., LangGraph, CrewAI, AutoGen/AG2, OpenAI Agents SDK, Claude Agent SDK) from an evaluation standpoint?

**Answer.** Eval-relevant criteria, not just DX: (1) does it expose full trajectory/step data cleanly for
tracing (or does it hide state in ways that make debugging hard)? (2) does it support deterministic
replay/testing (fixed seeds, mockable tool calls) for reproducible evals? (3) how well does it integrate
with your tracing/observability stack (native OpenTelemetry support is a strong plus)? (4) does its
abstraction make it easy to swap models/tools for A/B testing without rewriting the harness? Framework
choice is a *build-time* decision but has lasting eval consequences — a framework that obscures
intermediate state is much harder to evaluate well later, even if it ships features fast.

> **Saying it out loud.** I'd judge a framework on eval consequences, not developer experience. Four questions: does it expose full step-level state cleanly or hide it inside abstractions, does it support deterministic replay with fixed seeds and mockable tools, does it integrate with your tracing stack natively, and can you swap models or tools for an A/B without rewriting the harness. The framing that lands is that framework choice is a build-time decision with a long eval tail — a framework that obscures intermediate state ships features fast and then makes every debugging session twice as expensive for the next two years.

---

### 11.5 How do you set up CI/CD-style continuous evaluation for an agent (eval-in-the-loop for every change)?

**Answer.** Mirror software CI: every PR (prompt, tool, model, or code change) triggers the regression
suite automatically; fast, cheap deterministic checks gate merge (must not regress); the fuller
LLM-judge suite runs async and posts results before deploy; a human sign-off is required if any slice
regresses beyond threshold. Track the suite's own runtime and cost as a first-class SLO so it stays fast
enough to run on every change — a suite people skip because it's slow provides zero of its value. Store
historical results so every change is diffable against the prior baseline, not just pass/fail against a
static threshold.

> **Saying it out loud.** Mirror software CI exactly. Every PR — prompt, tool, model, or code — triggers the suite. Fast deterministic checks gate the merge, the fuller judge-based suite runs async and posts before deploy, and any slice regression past threshold needs a human sign-off. Store historical results so every change diffs against the prior baseline rather than a static threshold, which is what lets you attribute a movement to a change. And treat the suite's own runtime and cost as an SLO, because the real failure mode is a suite so slow people start adding skip flags — a suite that gets skipped delivers exactly zero of its value.

---

### 11.6 What do you look for in an LLM-judge or eval framework's implementation to trust its numbers (e.g., OpenAI Evals, promptfoo, DeepEval, Ragas)?

**Answer.** (1) Transparent, inspectable prompts for built-in judges/metrics (not a black box) so you can
audit and tune them for your domain. (2) Support for custom graders (programmatic and LLM-based) so you
aren't stuck with generic metrics that don't map to your task. (3) Reproducibility — pinned model
versions/temperatures for judges, versioned datasets. (4) Reporting beyond a single aggregate: per-slice
breakdowns, confidence intervals, and raw traces for failing cases, not just a score. Any framework
whose judge prompts you can't see or modify is a liability for anything beyond quick prototyping — I'd
still validate its judgments against a human gold set before trusting it in a gate.

> **Saying it out loud.** Four things. Can I see and edit the judge prompts, or is the metric a black box. Can I plug in custom graders, both programmatic and LLM-based, so I'm not stuck with generic metrics that don't map to my task. Is it reproducible — pinned judge model and temperature, versioned datasets. And does it report beyond a single aggregate: per-slice breakdowns, confidence intervals, and the raw traces for failures. Any framework whose judge prompts you can't inspect is fine for prototyping and a liability in a gate — and either way I'd validate its judgments against a human gold set before letting it block a merge.

---

### 11.7 How do you version and manage prompts/datasets so evaluation results stay reproducible over time?

**Answer.** Treat prompts and datasets like code: store in version control (or a prompt-management
system with full history), tag every eval run with the exact prompt hash, dataset version, model
version/snapshot, and harness/code commit used. Never mutate a "released" dataset version in place —
create a new version and changelog the diff. This lets you answer "why did this metric move?" with a
clean diff instead of guesswork, and lets you roll back a bad prompt change the same way you'd revert
code.

> **Saying it out loud.** Prompts and datasets are code, so they live in version control with full history, and every eval run gets tagged with the exact prompt hash, dataset version, model snapshot, and harness commit. The rule that does the most work is: never mutate a released dataset version in place — cut a new version and changelog the diff. That's what turns 'why did this metric move?' from an archaeology project into a clean diff, and it's what lets you revert a bad prompt exactly the way you'd revert code. Without it, six months in, you have a number nobody can reproduce and no way to tell whether the model or the dataset changed.

---

### 11.8 What role does human annotation tooling play, and what makes it good?

**Answer.** Good annotation tooling: presents full trajectory context (not just the final answer) so
raters can judge grounding/process, not just output; supports structured rubrics (not free-text-only)
for consistent, aggregable scoring; tracks inter-annotator agreement automatically and flags low-
agreement items for adjudication; and supports blind/randomized assignment to reduce rater bias. The
tooling should make it *easy* to produce well-calibrated gold labels at the volume your judge-validation
and gold-set-refresh cadence requires — a clunky annotation tool is a hidden tax that quietly shrinks
your gold set over time.

> **Saying it out loud.** Annotation tooling is what determines whether your gold set is any good, which determines whether any of your automated judges mean anything. Good tooling shows the full trajectory, not just the final answer, so raters can judge grounding and process. It uses structured rubrics rather than free text so scores aggregate. It computes inter-annotator agreement automatically and flags low-agreement items for adjudication. And it supports blind randomized assignment to cut rater bias. The failure mode is quiet: a clunky tool is a tax that slowly shrinks your gold set, and a shrinking gold set means judge calibration silently expires without anyone deciding to let it.

---

### 11.9 How would you instrument cost tracking into your evaluation pipeline?

**Answer.** Capture token counts (input/output/cached) and model pricing per call at the span level,
roll up to per-trace and per-eval-run totals, and report **cost per successful task** (not just raw
cost) as the headline efficiency metric, since cheaper-but-more-failures isn't actually cheaper. Track
the eval pipeline's *own* compute cost too (judge calls add up) as a separate line so you can make an
informed build/sample/cascade tradeoff (9.5). Break cost down by step type (LLM calls vs. tool calls vs.
judge calls) so you know where to optimize first.

> **Saying it out loud.** Capture tokens — input, output, and cached separately — plus pricing at the span level, then roll up to per-trace and per-run totals. The headline number should be cost per *successful* task, not cost per task, because cheaper-with-more-failures isn't actually cheaper once you count the retries and the escalations. Break it down by step type so you know whether your money is going to model calls, tool calls, or judge calls. And track the eval pipeline's own spend as its own line item, because judge calls add up fast and that's the number that tells you when to cascade or sample instead of judging everything.

---

### 11.10 How do you decide what to build vs. adopt for a brand-new eval program with a small team?

**Answer.** Start by adopting for anything commodity and fast-moving (tracing/observability platform,
basic dataset/experiment tracking) — building these well early is a distraction from the actual eval
questions. Build in-house from day one: your task taxonomy, gold-labeling process, and domain-specific
graders, since these encode judgment nobody else can supply. Revisit the build/buy line as you scale —
what's "adopt" at 10 evals/day may need to become "build" at 10,000/day for cost or customization
reasons. The single highest-leverage early investment is usually a clean, versioned dataset + harness,
because everything downstream (judges, dashboards, gates) depends on it being trustworthy.

> **Saying it out loud.** Adopt anything commodity and fast-moving — tracing, basic experiment tracking — because building those well early is a distraction from the questions you're actually being paid to answer. Build from day one the things that encode judgment nobody else can supply: your task taxonomy, your gold-labeling process, your domain graders. Then revisit the line as volume grows, since what's sensible to buy at ten runs a day may need to be built at ten thousand. If I only got one investment, it'd be a clean versioned dataset and harness, because every judge, dashboard, and gate downstream is only as trustworthy as that.

---

## 12. Production Monitoring & Online Eval

### 12.1 What's the difference between offline evaluation and online/production monitoring, and how do they fit together?

**Answer.** Offline eval runs against a fixed, curated dataset before shipping — controlled, reproducible,
cheap to re-run, but a proxy for reality. Online monitoring observes the live, uncurated input
distribution continuously after shipping — it's the ground truth on whether offline gains transferred,
but noisier, harder to attribute, and can't easily use labels that don't exist in production. They form a
loop: offline gates a release; online validates it actually worked and surfaces new failure modes; those
failures get mined back into the offline suite (8.10). Neither replaces the other — offline-only misses
real-world drift, online-only means you ship regressions before catching them.

> **Saying it out loud.** Offline runs a curated fixed set before you ship — controlled, reproducible, cheap to re-run, and fundamentally a proxy. Online watches the real uncurated distribution after you ship — it's the actual truth about whether your offline gains transferred, but it's noisy, hard to attribute, and mostly has no labels. So they're a loop: offline gates, online validates, and the failures online finds get mined back into offline. Offline-only means you never see drift; online-only means you find out about regressions from your users, which is the expensive way to learn.

---

### 12.2 What metrics do you monitor in production for a deployed agent, and at what cadence?

**Answer.** Real-time/near-real-time (dashboards + alerting): error rate, tool-error rate, latency
(p50/p95/p99), cost per session, step-cap-hit rate, escalation/human-handoff rate, and safety-flag rate —
all computable without ground truth. Daily/weekly (sampled + judged): task success rate on a stratified
sample, faithfulness/grounding rate, user satisfaction (explicit ratings + implicit signals like
reformulation or abandonment), and slice-level breakdowns for known risk segments. Longer cycle
(judge/gold-set health): judge-human agreement re-validation, gold-set refresh. The real-time layer
exists to catch acute breakage fast; the sampled layer exists to catch quality drift that acute
monitoring can't see.

> **Saying it out loud.** I split by cadence, because the cheap stuff and the good stuff run at different rates. Real time, all label-free: error rate, tool-error rate, p50 through p99 latency, cost per session, step-cap hits, escalation rate, safety flags. Daily or weekly, sampled and judged: task success on a stratified sample, grounding rate, satisfaction, and slice breakdowns for risky segments. And on a slower cycle, judge-human agreement and gold-set refresh — monitoring the monitors. The division of labor is the point: the real-time layer catches acute breakage in minutes, the sampled layer catches quality drift that acute monitoring is structurally blind to.

---

### 12.3 What implicit (label-free) signals can approximate task success in production?

**Answer.** Session abandonment/drop-off, user reformulating or repeating the same request (signals the
first attempt failed), explicit thumbs up/down or ratings, escalation/handoff-to-human rate, follow-up
negative sentiment, task completion signals from the surrounding product (e.g., did a downstream action
actually get taken — a ticket closed, a purchase completed), and time-to-resolution. None is perfect
alone (e.g., silent abandonment could mean success *or* the user giving up) — triangulate several and
validate the composite proxy periodically against a human-judged sample so you know it's actually
tracking real success rather than a correlated-but-wrong signal.

> **Saying it out loud.** The useful ones are all behavioral: did the user abandon, did they rephrase and ask again, did they thumbs it down, did they escalate to a human, and did the downstream thing actually happen — ticket closed, order placed. Reformulation is my favorite because it's a near-direct signal that attempt one failed. But none of them are trustworthy alone — silent abandonment could equally mean the user got what they needed and left, so a single proxy will mislead you. So you triangulate several into a composite and then, on a schedule, validate that composite against a human-judged sample. Otherwise you're optimizing a correlated-but-wrong signal and won't find out for a quarter.

---

### 12.4 How do you detect distribution drift in production inputs or outputs?

**Answer.** Track the input distribution over time (intent/topic mix via clustering or classifier,
input length, tool-usage mix) and alert on statistically significant shifts (e.g., population stability
index / KL divergence between rolling windows and a baseline window). Do the same for outputs (response
length, refusal rate, tool-call mix). Drift itself isn't automatically bad (real-world usage legitimately
evolves), but it invalidates the assumption that your offline eval set still represents production —
significant drift should trigger a refresh of the benchmark/gold set to re-match, and should be a factor
in interpreting any metric movement (is the model worse, or are users just asking harder things now?).

> **Saying it out loud.** Track the input mix over time — intent clusters, length, which tools get used — and alert when a rolling window diverges from baseline, using something like population stability index or KL divergence rather than eyeballing a chart. Do the same on outputs: length, refusal rate, tool-call mix. The framing that matters is that drift isn't inherently bad; usage legitimately evolves. What drift actually tells you is that your offline eval set has stopped representing production, which means it's time to refresh the benchmark. It's also the first thing to check when a metric moves, because 'the model got worse' and 'users started asking harder questions' look identical on a dashboard.

---

### 12.5 How do you set alerting thresholds for agent production metrics without drowning in false positives?

**Answer.** Use statistical process control rather than arbitrary fixed thresholds: baseline the metric's
normal variance (control charts / rolling mean ± k·σ), and alert on sustained deviation beyond that band
rather than single-point noise, since agent metrics are naturally noisier than traditional service
metrics. Separate **guardrail alerts** (page immediately — safety flag spike, error-rate spike, cost
runaway) from **quality-trend alerts** (daily digest — gradual success-rate decline). Tune thresholds
using historical incident data (would this threshold have caught our past 3 real incidents without also
firing on the 20 non-incidents around them?) and revisit them as the product and traffic mix change.

> **Saying it out loud.** Don't pick a fixed threshold out of the air — agent metrics are much noisier than normal service metrics and a static line will page you constantly. Use statistical process control: baseline the normal variance and alert on sustained deviation outside the band, not on single-point spikes. Then split your alerts by urgency — guardrails like a safety-flag spike or cost runaway page immediately, quality trends like a slow success decline go in a daily digest. And tune against history: would this threshold have caught our last three real incidents without firing on the twenty non-incidents around them? That question is what separates a functioning pager from one people have muted.

---

### 12.6 How do you monitor and control for cost and latency regressions in production?

**Answer.** Track cost and p95/p99 latency per session continuously, broken down by step type (model
calls vs. tool calls vs. judge/monitoring overhead itself) so a regression is attributable. Set budget
guardrails (max tokens/tool-calls per session, with graceful truncation/escalation rather than silent
cutoff) and alert on cost-per-successful-task, not just raw cost, so a cheaper-but-more-failures change
doesn't look like a win. Watch for slow creep from prompt/context growth over time (a common silent cost
regression as few-shot examples or context accumulate) via a trend chart, not just point-in-time checks.

> **Saying it out loud.** Track cost and tail latency per session, broken down by step type — model calls, tool calls, and the monitoring overhead itself — so a regression is attributable rather than mysterious. Set hard budget guardrails on tokens and tool calls per session, and make them degrade gracefully or escalate rather than silently truncating mid-task. Alert on cost per *successful* task, not raw cost, so a change that's cheaper but fails more doesn't get celebrated. And the one that actually gets people is slow creep — someone adds a few-shot example, context grows a bit each month, and a year later your cost per session has doubled without a single visible regression.

---

### 12.7 How do you build an online safety-monitoring layer for a deployed agent?

**Answer.** Layer fast, cheap classifiers (toxicity, PII, jailbreak/prompt-injection detectors, policy-
violation detectors) as real-time guardrails on both input and output, with the ability to block/redact/
escalate before the user sees a harmful output or before a risky tool call executes. Log every flag with
enough trajectory context to audit, and route high-severity flags to human review immediately (page,
don't just log). Periodically red-team the live system to check the monitors themselves haven't decayed
(classifiers can drift as attack patterns evolve) and track false-positive rate on the guardrails too — a
overly aggressive monitor that blocks legitimate use is its own production incident.

> **Saying it out loud.** Fast cheap classifiers on both sides — toxicity, PII, injection detection, policy violation — running inline so they can block, redact, or escalate before the user sees an output or before a risky tool call actually executes. Log every flag with enough trajectory context to audit it later, and page on high-severity flags rather than just writing them to a file nobody reads. Then two maintenance things people skip: red-team the live system periodically, because classifiers decay as attack patterns evolve, and track the guardrails' false-positive rate. An over-aggressive monitor blocking legitimate use is its own production incident, it's just one that shows up as a support ticket instead of an alert.

---

### 12.8 How do you handle model or dependency updates that happen outside your control (silent vendor-side changes)?

**Answer.** Where possible, pin exact model snapshot versions rather than a floating "latest" alias, and
treat any forced migration as a full release (offline regression suite + shadow mode + canary) rather
than a no-op. For truly silent changes (a third-party tool/API changing behavior without notice), rely on
continuous regression testing against fixed benchmarks (12.1) and anomaly detection on production metrics
to catch the drift quickly, then root-cause via trace diffing (comparing before/after trajectories for the
same inputs). This is a case where "we can't prevent it, but we can detect it fast and have a rollback/
mitigation plan" is the honest and correct answer.

> **Saying it out loud.** Pin exact model snapshots rather than a floating 'latest' alias, and when a vendor forces a migration, treat it as a full release — regression suite, shadow mode, canary — not a config bump. For genuinely silent changes, like a third-party API quietly altering behavior, you can't prevent it, so you invest in detection: continuous regression runs against fixed cases plus anomaly detection on production metrics, then trace diffing to root-cause by comparing before-and-after trajectories on the same inputs. And I'd say that plainly in an interview — 'we can't prevent it, we can detect it in hours and roll back' is the honest and correct answer, and pretending otherwise is the wrong one.

---

### 12.9 What does an effective agent-monitoring dashboard look like, and who's it for?

**Answer.** Layered by audience: an **exec/on-call top layer** (health at a glance — success rate,
safety flags, cost, latency, all vs. SLO with trend arrows); a **debugging layer** for engineers (slice
breakdowns, drift charts, drill-down from an aggregate metric straight to the underlying failing traces);
and a **product/quality layer** for eval owners (judge-human agreement health, gold-set coverage, suite
growth from production). The critical design property is **drill-down**: every aggregate number should
click through to actual failing trajectories, because a dashboard that shows *that* something regressed
without letting you see *why* just relocates the debugging problem.

> **Saying it out loud.** Three layers for three audiences. Top layer for on-call and execs: success, safety flags, cost, latency, each against its SLO with a trend arrow. Middle layer for engineers: slice breakdowns, drift charts, and drill-down. Bottom layer for eval owners: judge-human agreement, gold-set coverage, suite growth from production. But the property that decides whether the dashboard is useful is drill-down — every aggregate has to click through to actual failing traces. A dashboard that tells you something regressed without letting you see why hasn't solved the debugging problem, it's just moved it to a different tab.

---

### 12.10 How do you run online experimentation (feature flags / A/B) for continuous agent improvement, not just big releases?

**Answer.** Build lightweight feature-flagging into the agent (prompt variant, tool config, model choice)
so small changes can be tested on a slice of traffic without a full deployment cycle, with the same
statistical rigor as 8.3 (pre-registered metrics, adequate sample size, guardrails). Maintain an
experiment log/registry so overlapping experiments don't confound each other's results, and default new
experiments to a small allocation with an automatic ramp/kill based on guardrail metrics. The goal is
turning "should we ship this prompt tweak" from a slow, high-ceremony release into routine, cheap,
statistically sound continuous testing — while keeping the guardrails that prevent a bad experiment from
being a real incident.

> **Saying it out loud.** Build feature flags into the agent itself — prompt variant, tool config, model choice — so testing a small change doesn't require a full deploy cycle. Then apply the same rigor you'd apply to a big A/B: pre-registered metrics, a power calculation, guardrails, automatic ramp or kill. And keep an experiment registry, because the thing that quietly ruins continuous experimentation is two overlapping experiments confounding each other and nobody noticing for a month. The goal is turning 'should we ship this prompt tweak' from a ceremony into a routine statistically sound question — without losing the guardrails that stop a bad experiment from becoming a real incident.

---

### 12.11 How do you decide when a production incident requires a full post-mortem vs. a quick fix?

**Answer.** Trigger a full post-mortem when: user-visible harm occurred (safety, financial, or trust
impact), the root cause reveals a systemic gap in the eval/monitoring pipeline itself (not just a one-off
bug), or the same failure class has recurred. A quick fix suffices for isolated, low-severity issues with
a clear, narrow root cause. Every post-mortem's most important deliverable, regardless of severity, is a
concrete addition to the regression suite and/or monitoring (8.10, 12.5) — a post-mortem that produces
only a narrative and no new automated defense hasn't actually closed the loop.

---

> **Saying it out loud.** Full post-mortem when any of three things is true: there was user-visible harm, the root cause exposed a systemic gap in the eval or monitoring pipeline rather than a one-off bug, or this failure class has happened before. Recurrence is the one I'd weight heaviest, because a repeat means the last fix didn't close anything. Isolated low-severity issues with an obvious narrow cause just get fixed. And whatever the severity, the deliverable that matters is the same: a new regression case or a new monitor. A post-mortem that produces a narrative and no automated defense hasn't closed the loop, it's just documented the incident nicely.

---

# Part II — Applied & Interview Craft

## 13. 2025–2026 Landscape Quiz

*This section is a dated snapshot (accurate as of August 2026) of the model, protocol, and benchmark
landscape an interviewer may probe to check you're current. Treat exact benchmark percentages as
illustrative and re-verify before quoting them in an interview — this space moves fast, and the point is
to know the shape of the landscape and the right vocabulary, not to memorize a leaderboard snapshot.*

### Q. What are the current frontier models from the major labs, as of mid-2026?

**A.** Anthropic's flagship is **Claude Opus 4.8**, with **Claude Sonnet 5** (released June 30, 2026)
as a cheaper, agent-focused mid-tier model — Anthropic's own framing was that Sonnet 5 "can make plans,
use tools like browsers and terminals, and run autonomously" at a level that needed a larger model
months earlier, and it slightly outperforms Opus 4.8 on some knowledge-work benchmarks while Opus
remains preferred for the highest-judgment tasks. OpenAI's line runs GPT-5 → **GPT-5.1** (Nov 2025, with
Instant and Thinking modes plus GPT-5.1-Codex-Max for agentic coding) → later **GPT-5.5**. Google's
flagship is **Gemini 3 Pro** (Nov 2025), since followed by **Gemini 3.1 Pro** and a cheaper **Gemini 3.5
Flash**. The pattern across all three labs: a "reasoning/thinking mode" is now a standard, user- or
API-selectable toggle rather than a separate product line, and each lab now ships an explicit cheaper
"agent-tier" model optimized for long autonomous tool-use sessions rather than single-turn quality.

> **Saying it out loud.** I'd answer this one with a caveat baked in, because it goes stale within weeks. The shape of the answer matters more than the version numbers: each major lab now ships a top-tier judgment model and a cheaper agent-tier model tuned for long autonomous tool-use sessions, and reasoning mode has become a toggle on the same model rather than a separate product line. So I'd name the current flagships as I last understood them, say plainly that these are vendor-published as of a date, and add that I'd check the model cards before putting a number in a decision doc. The reason that framing scores is that it shows you know the axis — cost-tier versus judgment-tier — rather than just memorizing a leaderboard.

---

### Q. Anthropic said Sonnet 5 "slightly outperforms Opus 4.8" on some benchmarks but scored lower on agentic coding — what were the numbers, and what does that tell you about model selection?

**A.** Reported agentic-coding scores were roughly Opus 4.8 at 69.2%, Sonnet 5 at 63.2%, and the prior
Sonnet 4.6 at 58.1% (verify current numbers before citing — labs revise these). The lesson for an
evaluator: "best model" is not a single scalar. Sonnet 5 can win on cost-normalized throughput and even
absolute score on some task families while still lagging Opus on the highest-difficulty agentic coding —
which is exactly why a real evaluation practice reports **per-task-family, cost-normalized** comparisons
rather than a single leaderboard number, and picks the model per use case (e.g., Sonnet-tier for
high-volume agent loops, Opus-tier for the highest-stakes/most-judgment-heavy calls).

> **Saying it out loud.** The point of this question isn't the digits, it's what the pattern means. A cheaper model can beat a bigger one on some knowledge-work benchmarks and still lose meaningfully on hard agentic coding — the reported spread was several points in Opus's favor there — and those are vendor-published numbers as of a date, which labs do revise. What that tells you is that 'best model' isn't a scalar, so a real eval practice reports per-task-family and cost-normalized comparisons instead of one leaderboard figure. And then you route: cheap tier for the high-volume agent loop, expensive tier for the highest-judgment calls, which usually buys more than any prompt tuning.

---

### Q. What changed in the July 2026 MCP specification update, and why does it matter for agent evaluation?

**A.** The 2026-07-28 MCP spec release made several evaluation-relevant changes: (1) it removed the
stateful `initialize`/session-ID handshake in favor of a **stateless, self-contained request** model,
simplifying reproducible test harnesses (no session state to reset between eval runs); (2) it added
**Multi Round-Trip Requests (MRTR)**, letting a server ask for missing input mid-call via an
`input_required` result instead of holding a long-lived bidirectional stream — this changes how you'd
simulate/mock a tool that needs clarification during eval; (3) it added `ttlMs`/`cacheScope` on list
results, which affects how you evaluate tool-selection latency and staleness; (4) it hardened OAuth
(RFC 9207 issuer validation, Client ID Metadata Documents superseding Dynamic Client Registration),
closing a class of auth-confusion vulnerabilities your MCP-server security eval should now specifically
test for; and (5) it deprecated the legacy HTTP+SSE transport and moved Roots/Sampling/Logging and Tasks
into an extension framework, with a 12-month support window — meaning eval harnesses built against the
old transport need a migration plan, not an indefinite ignore.

> **Saying it out loud.** I'd frame this as vendor-published spec changes as of that release date, and give the evaluation consequence of each rather than reciting the changelog. The stateless request model means no session state to reset between eval runs, which removes a whole class of harness bugs. Mid-call input requests change how you mock a tool that needs clarification. Cache TTLs on list results affect how you measure tool-selection staleness. And the auth hardening closes a class of auth-confusion attacks your MCP security suite should now test for specifically. The one with a deadline attached is the deprecated legacy transport — a support window means harnesses built on it need a migration plan, not an indefinite ignore.

---

### Q. Why does MCP's stateless-core change matter more for evaluation than it looks at first glance?

**A.** Session state was historically a reproducibility hazard: a trace could fail only because the
harness reset session state incorrectly between eval runs, or because two eval workers shared a session
ID and stepped on each other under parallelization. A stateless core means every request carries its own
context, so eval infrastructure can safely fan out many parallel, independent tool-call evaluations
behind a plain load balancer without session-affinity bugs — directly lowering the engineering cost of
running large-scale, parallel tool-use eval suites.

> **Saying it out loud.** Session state was quietly one of the worst reproducibility hazards in tool-use eval. You'd get a failing trace that had nothing to do with the agent — the harness reset the session wrong, or two parallel eval workers shared a session ID and stepped on each other. A stateless core means each request carries its own context, so you can fan out hundreds of parallel independent tool-call evaluations behind a plain load balancer with no session affinity. The concrete win is that large-scale parallel tool-use eval gets dramatically cheaper to engineer, and the specific bug class it kills — flaky failures from cross-worker session collisions — is one of the hardest to diagnose because it looks like non-determinism in the model.

---

### Q. What is tau2-bench and how does it differ from the original tau-bench?

**A.** tau-bench (Sierra Research) pioneered evaluating customer-service-style agents via a simulated
user with a hidden goal, scoring policy compliance and task resolution across domains like retail and
airline booking. **tau2-bench** is Sierra's successor benchmark, refining the tool-agent-user interaction
loop to be more realistic (more nuanced user simulation behavior and tool dynamics). The throughline
worth naming in an interview: the field has moved from evaluating an agent in isolation on a fixed input
to evaluating it *interactively*, against a simulated counterpart that can react, clarify, and change its
mind — because that's what production conversations actually look like.

> **Saying it out loud.** tau-bench was the one that made simulated-user evaluation mainstream — a customer-service agent talking to an LLM user that has a hidden goal, scored on policy compliance and whether the task actually got resolved, with pass^k for reliability. tau2-bench is the successor, refining the user simulation and tool dynamics to be more realistic. But the throughline is what I'd actually say out loud: the field moved from evaluating an agent against a fixed input to evaluating it *interactively*, against a counterpart that reacts, clarifies, and changes its mind. That's what production conversations look like, and it's also why a single-turn benchmark score tells you so little about a multi-turn product.

---

### Q. What are the standard agent benchmarks a senior candidate should be able to name and one-line-describe?

**A.** SWE-bench (Verified) — real-repo issue resolution graded by test pass. GAIA — general assistant
tasks needing browsing + multi-step reasoning, short-answer graded. WebArena — realistic web navigation/
transactions on self-hosted site clones. AgentBench — multi-environment breadth suite. Terminal-Bench —
shell/CLI competence in containers. OSWorld — real desktop-GUI tasks on a live VM. tau-bench/tau2-bench —
multi-turn customer-service agents vs. a simulated user. BFCL — isolated function/tool-calling accuracy.
Knowing the *grading mechanism* of each (test-pass vs. exact-match vs. LLM-judge vs. simulated-user
resolution) is the detail that actually distinguishes a candidate who's used these from one who's only
seen the leaderboard.

---

### Q. What is "reasoning mode" / extended thinking, and what does it change about evaluation?

**A.** Frontier labs now expose an explicit reasoning/thinking budget (e.g., Claude's extended thinking,
GPT-5.x's Thinking mode, Gemini's equivalent) — the model spends more inference-time compute generating
internal reasoning before answering, usually trading latency/cost for accuracy on hard, multi-step tasks.
For evaluation this means: (1) you must eval at the *same* reasoning-effort setting you'll actually
deploy at, since scores aren't comparable across settings; (2) cost/latency curves as a function of
reasoning budget become a first-class part of your eval report, not an afterthought; (3) it opens a new
failure mode to test — reasoning that looks thorough but reaches a wrong conclusion (persuasive-looking
but unfaithful chain-of-thought), which plain answer-accuracy checks can miss unless you also grade the
reasoning trace itself (see Part I, Section 5).

> **Saying it out loud.** Reasoning mode is an explicit knob for how much inference-time compute the model spends thinking before it answers, trading latency and cost for accuracy on hard multi-step work. Three consequences for eval. One, you must evaluate at the exact reasoning setting you'll deploy at, because scores across settings aren't comparable and this is an easy way to accidentally publish an unreachable number. Two, cost and latency as a function of thinking budget become part of the report, not a footnote. Three, it opens a specific failure mode — reasoning that looks thorough and lands on a wrong answer — which plain answer-accuracy will catch but plain trace-reading will not.

---

### Q. Are chain-of-thought traces from reasoning models faithful/reliable to audit as-is?

**A.** Not by default — this remains an active research concern across labs. A model's stated reasoning
can diverge from the actual computation driving its answer (unfaithful CoT), and reasoning traces can
be optimized (implicitly, via RLHF-style training pressure) to *look* convincing rather than to be
accurate reports of the underlying process. Practical implication for eval: treat visible reasoning as a
useful diagnostic signal, not ground truth — verify conclusions independently (final-answer grading,
consistency checks across resamples, or process-supervision against known-correct intermediate steps)
rather than trusting a plausible-sounding trace at face value.

> **Saying it out loud.** No, not by default, and this is still an open research problem rather than a solved one. The stated reasoning can diverge from whatever actually produced the answer, and there's a structural reason to expect that — if traces get optimized under training pressure, they're being shaped to look convincing, which is not the same objective as being an accurate report. So practically: use visible reasoning as a diagnostic, never as evidence for an oversight decision. Verify conclusions independently — grade final answers, resample and check consistency, or supervise against known-correct intermediate steps. The failure mode to name is the persuasive wrong trace, because a human reviewer reading it will approve it.

---

### Q. What's the current state of "agentic coding" as a specific eval category, and why has it become its own line item?

**A.** Coding agents (e.g., Codex-Max-style models, Claude in agentic coding harnesses) now get evaluated
specifically on autonomous, multi-step workflows — large refactors, test-driven iteration, and
autonomous debugging over many tool calls — not just single-function code generation. This split matters
because single-turn code-gen accuracy and multi-step autonomous-coding-agent success are genuinely
different capabilities that don't move together; a model can be excellent at one-shot function synthesis
and mediocre at a 50-step autonomous refactor requiring self-correction, which is exactly why labs and
benchmarks (SWE-bench Verified, Terminal-Bench) now report agentic-coding scores as a distinct category
from generic coding benchmarks.

> **Saying it out loud.** It's become its own category because single-turn code generation and multi-step autonomous coding turn out to be different capabilities that don't move together. A model can be excellent at one-shot function synthesis and mediocre at a fifty-step refactor that requires noticing its own mistake and backing out. So labs and benchmarks now report agentic coding separately — SWE-bench Verified, Terminal-Bench — rather than folding it into generic coding scores. What that means for you is that if your product is a coding agent, a HumanEval-style number is nearly uninformative; the thing you care about is success over long tool-use sessions, and the failure mode to watch is self-correction breaking down as the trajectory gets longer.

---

### Q. What should a candidate know about MCP security as of 2026, beyond "it's a protocol for tools"?

**A.** MCP's attack surface has become a distinct eval/security topic: untrusted or malicious MCP
servers can serve tool descriptions containing injected instructions (tool-description/prompt injection),
over-broad OAuth scopes can grant more access than a task needs, and (pre-2026-07-28) session/handshake
confusion enabled a class of auth-mixup attacks that the new spec's issuer-validation and CIMD changes
specifically target. A senior answer names concrete mitigations: sandboxing/allow-listing MCP servers,
scanning tool descriptions for injected instructions before they enter context, least-privilege OAuth
scoping per tool, and including malicious/compromised-MCP-server scenarios explicitly in your agent's
safety eval suite (Part I, Section 6) — not just assuming MCP servers are trusted infrastructure.

> **Saying it out loud.** The short version is that MCP servers are not trusted infrastructure, and treating them that way is the vulnerability. Concretely: a malicious server can put injected instructions inside a tool description, which lands directly in your context window before the agent has done anything; OAuth scopes are routinely broader than the task needs; and there was a class of auth-confusion attacks that recent spec work specifically targets. So the mitigations I'd name are sandboxing and allow-listing servers, scanning tool descriptions before they enter context, least-privilege scoping per tool, and putting compromised-server scenarios into the safety suite explicitly. Tool-description injection is the one to lead with, because most teams have never considered that the tool *catalog* is attacker-controlled input.

---

### Q. How has the emphasis in agent evaluation shifted over the last 12–18 months?

**A.** Three shifts worth naming: (1) from **single-turn/single-tool eval to long-horizon, multi-tool
trajectory eval**, as models handle longer autonomous sessions; (2) from **static benchmark leaderboards
to production-correlated, continuously-refreshed suites**, as saturation and contamination eroded trust
in static numbers; (3) from **capability-only eval to capability + cost + safety as co-equal axes**,
since cheaper "agent-tier" models (Sonnet 5, GPT-5.1-mini-class models, Gemini Flash-tier) made cost-
normalized comparison a first-class question rather than an afterthought. An interviewer asking this
question is really checking whether you're describing 2023-era single-prompt eval or the actual current
practice — lead with trajectory-level, production-correlated, cost-aware evaluation.

> **Saying it out loud.** Three shifts. From single-turn, single-tool scoring to long-horizon trajectory evaluation, because sessions got longer. From static leaderboards to production-correlated suites that get refreshed, because contamination and saturation ate the credibility of static numbers. And from capability-only to capability plus cost plus safety as co-equal axes, which happened once cheap agent-tier models made cost-normalized comparison unavoidable. The reason an interviewer asks this is to find out whether you're describing 2023 practice or current practice, so I'd lead with trajectory-level, production-correlated, cost-aware — and mention that treating cost as an afterthought is the single most common way a good eval program produces an unshippable recommendation.

---

### Q. What's a reasonable answer if asked to name a benchmark or model detail you're not 100% sure is current?

**A.** Say so directly and give your best-grounded approximation with a caveat: "as of my last check it
was X, but this space moves monthly — I'd verify against the model card / benchmark leaderboard before
quoting it in a decision doc." Interviewers evaluating for a fast-moving field are testing calibration
and epistemic honesty at least as much as raw recall — confidently stating a stale or fabricated number
is a worse signal than an accurate "I'd verify that" followed by correct surrounding context.

> **Saying it out loud.** Say it straight: as of my last check it was roughly X, but this space moves monthly and I'd verify against the model card or leaderboard before putting it in a decision doc. Then keep going and give the surrounding context you *are* confident about — the grading mechanism, the failure modes, why the number matters. The reason that scores well is that in a field this fast, interviewers are testing calibration as much as recall, and confidently stating a stale or invented number is a much worse signal than an accurate 'I'd verify that'. A fabricated benchmark figure is one of the few answers that can end an interview outright.

---

## 14. System-Design Scenarios

*Format for each: the prompt, clarifying questions to ask first, an architecture sketch, key design
decisions and tradeoffs, and how to defend the design under interviewer pushback. These are meant to be
read as worked examples you adapt live, not scripts to recite verbatim.*

### 14.1 Design an evaluation platform for an org running many agents

**Prompt:** "Your company has 6 product teams each shipping their own LLM agent. Design an evaluation
platform the whole org uses."

**Clarifying questions to ask:**
- Are the agents similar in shape (all tool-using chat agents) or genuinely heterogeneous (coding agent,
  support agent, browsing agent)? This determines how much can be shared vs. per-team.
- Is there an existing tracing/observability stack, or greenfield?
- Centralized eval team, or a platform that teams self-serve?
- Compliance/data-residency constraints (can traces leave region, contain PII)?
- What's the release cadence per team — daily prompt tweaks vs. monthly model upgrades?

**Architecture:**

```
                    ┌─────────────────────────────────────────┐
                    │           Agent Teams (x6)               │
                    │  each emits traces via a shared SDK       │
                    └───────────────────┬───────────────────────┘
                                        │ OTel-style spans (gen_ai.*)
                                        ▼
                    ┌─────────────────────────────────────────┐
                    │        Ingestion / Trace Store           │
                    │  (append-only, versioned, PII-redacted   │
                    │   at ingest, tagged: team/agent/version)  │
                    └───────────────┬─────────────┬─────────────┘
                                    │             │
                    ┌───────────────▼───┐   ┌─────▼─────────────┐
                    │  Eval Harness Svc  │   │  Prod Monitoring   │
                    │  - dataset registry│   │  - real-time metrics│
                    │  - graders (shared │   │  - drift detection │
                    │    + per-team      │   │  - alerting        │
                    │    plugins)        │   └─────┬─────────────┘
                    │  - CI/CD hooks     │         │
                    └───────┬────────────┘         │
                            │                       │
                    ┌───────▼───────────────────────▼───────────┐
                    │     Human Annotation & Gold-Set Service    │
                    │  (per-team queues, shared agreement/QA)    │
                    └───────────────────┬─────────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────────┐
                    │   Dashboards: org rollup + per-team drilldown │
                    └───────────────────────────────────────────────┘
```

**Key decisions and tradeoffs:**
- **Shared trace schema, per-team graders.** Standardize ingestion (one schema, one store) so
  cross-team tooling (dashboards, drift detection, cost rollups) works for free, but let each team plug
  in its own domain-specific graders/rubrics as a registered plugin rather than forcing one generic
  judge on all six agents — a coding agent and a support agent have almost nothing in common at the
  grading layer.
- **Centralized platform team, federated ownership of content.** The platform team owns
  infra (ingestion, harness runner, dashboards); each product team owns its datasets, rubrics, and
  thresholds. This avoids the two failure modes: a central team that becomes a bottleneck reviewing
  every team's evals, or six teams independently rebuilding tracing/dashboards from scratch.
- **CI/CD gate is opt-in-strict.** Every team gets the harness wired into their CI, but gate
  thresholds are per-team-owned (a support agent's safety bar and a coding agent's safety bar differ) —
  the platform enforces *that* a gate exists, not one universal threshold.
- **PII handling is a platform, not per-team, concern.** Redaction/consent logic lives in the shared
  ingestion layer so no team can accidentally ship a leaky trace pipeline; this is worth calling out
  explicitly since it's exactly the kind of cross-cutting risk a bad platform design ignores.

**Defending under pushback:**
- *"Why not one universal judge for everything?"* — Because grading is inherently task-specific;
  a universal judge either becomes vague enough to be useless everywhere, or genuinely good at one
  team's domain and silently miscalibrated for the others. Shared infra + pluggable graders gets you
  reuse where it's real (tracing, dashboards, cost rollups) without forcing false uniformity where it
  isn't (rubrics, thresholds).
- *"Won't federated ownership fragment quality?"* — Mitigate with a lightweight platform-level review
  bar (every team's judge must show human-agreement validation before its gate goes live) plus a
  quarterly cross-team eval review — enough governance to catch bad practice without a central
  bottleneck.
- *"How do you justify the build cost of shared infra vs. 6 teams using off-the-shelf tools
  independently?"* — Show the crossover math: shared ingestion/dashboards amortize over 6 teams, while
  per-team tool sprawl means 6x vendor cost, 6x onboarding cost, and zero cross-team incident
  correlation (you can't tell if a shared upstream model update degraded multiple agents at once).
  The break-even is usually well under 6 teams for a company already running agents in production.

> **Saying it out loud.** The whole design comes down to one line: standardize the pipes, federate the judgment. One shared trace schema and one ingest path, so dashboards, drift detection, and cost rollups work across all six teams for free — but each team plugs in its own graders and rubrics, because a coding agent and a support agent have essentially nothing in common at the grading layer. The platform team owns infrastructure, the product teams own datasets and thresholds, and the platform enforces that a CI gate exists rather than what its number is. Two named failure modes to avoid: a central eval team that becomes the bottleneck reviewing everyone's rubrics, and six teams independently rebuilding tracing. And PII redaction belongs in shared ingestion — that's the cross-cutting risk a bad platform design always misses.

---

### 14.2 Design and evaluate a coding agent

**Prompt:** "Design the evaluation strategy for an autonomous coding agent that does multi-file
refactors and bug fixes in real repos."

**Clarifying questions to ask:**
- Scope: single-function generation, or full autonomous sessions (many tool calls, self-correction)?
- Does it operate on customers' real repos (higher stakes, less control) or an internal monorepo?
- Human-in-the-loop (PR review gate) or fully autonomous merge?
- What languages/frameworks matter most to the actual user base?

**Architecture:**

```
   Task Source                Execution Sandbox                Grading
 ┌───────────────┐        ┌─────────────────────────┐     ┌───────────────────┐
 │ - mined real   │        │ Ephemeral container per  │     │ Deterministic:     │
 │   issues/PRs   │──────▶│ task: repo snapshot +     │────▶│  test suite pass/  │
 │ - synthetic    │        │ pinned deps, network      │     │  fail, lint, build  │
 │   generated    │        │ egress restricted          │     │  success            │
 │ - adversarial  │        │                            │     │                     │
 │   (broken      │        │ Agent runs with tool       │     │ LLM-judge:          │
 │   tests, bad   │        │ access (shell, file edit,  │     │  code quality,      │
 │   specs)       │        │ search) up to a step cap   │     │  diff minimality,   │
 └───────────────┘        └───────────┬─────────────────┘     │  explanation clarity│
                                       │  full trace logged     └─────────┬───────────┘
                                       ▼                                  │
                             ┌─────────────────────┐                     │
                             │ Trajectory analysis:  │◀────────────────────┘
                             │ - tool-call efficiency │
                             │ - self-correction rate │
                             │ - loop/oscillation      │
                             └───────────┬─────────────┘
                                         ▼
                             ┌─────────────────────────────┐
                             │ Report: pass rate, cost/task, │
                             │ slice by repo size/language,  │
                             │ human-review-needed rate      │
                             └─────────────────────────────┘
```

**Key decisions and tradeoffs:**
- **Ground truth via test execution, not diff-matching.** Grade by running the repo's real (or
  curated) test suite post-patch, like SWE-bench, rather than comparing to a canonical diff — this
  correctly credits valid-but-different solutions, which raw diff-match would wrongly fail.
- **Sandboxing is non-negotiable.** Every task runs in an ephemeral, network-restricted container with
  a repo snapshot — this both protects against destructive agent actions and guarantees reproducibility
  (same task, same starting state, every run).
- **Separate "solved" from "solved well."** Test-pass is binary ground truth for correctness; layer an
  LLM-judge rubric on top for diff minimality, code style, and whether the agent introduced
  unrelated changes (a common failure — sneaking in unrelated "improvements") since a passing test suite
  doesn't guarantee a mergeable PR.
- **Track trajectory efficiency, not just outcome.** Two agents both reaching 80% pass rate differ hugely
  if one does it in 5 tool calls and the other in 40 with a step-cap-hit rate of 20% — report cost and
  step count alongside pass rate, and specifically track self-correction rate (did it recover from its
  own broken intermediate edits?) as a leading indicator of robustness on harder, out-of-distribution
  repos.
- **Include adversarial/malformed-repo cases.** Broken existing tests, ambiguous issue descriptions,
  and conflicting instructions — a coding agent that only ever sees clean, well-specified tasks in eval
  will be systematically over-rated relative to real usage.

**Defending under pushback:**
- *"Isn't SWE-bench already enough?"* — SWE-bench is a strong external reference point but is Python/
  GitHub-issue-shaped; a product-specific suite mined from your own repos/languages and your own
  distribution of task difficulty is what actually predicts your users' experience, and only your suite
  can include your adversarial/malformed cases.
- *"How do you stop the agent from gaming the test suite (e.g., deleting failing tests)?"* — Explicitly
  grade for exactly that: diff the test files themselves and flag/fail any task where test files were
  modified in a way that trivially passes (a specific, common reward-hacking pattern for coding agents,
  see Part I 6.x), and keep the test suite outside the agent's editable file scope in the sandbox where
  feasible.
- *"What if human reviewers disagree with the LLM judge on code quality?"* — That's expected early on;
  it's exactly why the judge needs a human-agreement validation pass (9.2) before it gates anything, and
  disagreements should be triaged to refine the rubric, not dismissed as reviewer noise.

> **Saying it out loud.** For a coding agent the good news is you have real ground truth — tests either pass or they don't — so lean on execution-based grading and only reach for a judge on the fuzzy stuff like code quality. Sandbox everything, run the tests the agent can't see, and score outcome plus trajectory: did it edit the right files, did it recover from a failing test, how many tool calls did it burn. The failure mode that defines this domain is reward hacking — the agent deletes or weakens the failing test and your pass rate goes up. So keep the test suite outside the agent's editable scope and verify with a held-out suite, otherwise your headline metric is measuring the agent's creativity at gaming you.

---

### 14.3 Design a safety evaluation for a web-browsing agent

**Prompt:** "Your agent can browse the live web and take actions (fill forms, make purchases) on a
user's behalf. Design its safety evaluation."

**Clarifying questions to ask:**
- What real-world actions can it actually take (read-only browsing vs. purchases/account changes)?
- Does it operate on the open web (untrusted content) or a allow-listed set of sites?
- Is there a human-confirmation step before high-stakes actions, or fully autonomous?
- What's the blast radius of a mistake (a wrong search result vs. an unauthorized purchase)?

**Architecture:**

```
        Threat Model Inputs                 Test Environment
 ┌───────────────────────────┐     ┌───────────────────────────────────┐
 │ - prompt injection via     │     │  Mirrored/sandboxed web:            │
 │   page content              │───▶│  - cloned test sites for scripted    │
 │ - malicious/compromised     │     │    injection & purchase-flow tests   │
 │   MCP tool servers           │     │  - controlled live-web slice with    │
 │ - deceptive UI (fake         │     │    read-only egress for broad-web    │
 │   buttons, dark patterns)    │     │    coverage tests                    │
 │ - over-broad task framing     │     │  - human-confirmation gate simulator  │
 │   ("just get me a good deal") │     └───────────────┬───────────────────────┘
 └───────────────────────────┘                        │ full trajectory + DOM state
                                                       ▼
                                       ┌───────────────────────────────┐
                                       │ Automated checks:               │
                                       │ - injected-instruction detector │
                                       │   (did agent obey page-embedded │
                                       │   commands not from the user?)  │
                                       │ - action-authorization check    │
                                       │   (did it act w/o required       │
                                       │   confirmation on a high-stakes  │
                                       │   action?)                       │
                                       │ - scope-of-action check          │
                                       │   (stayed within task intent?)   │
                                       └───────────────┬───────────────────┘
                                                       ▼
                                       ┌───────────────────────────────┐
                                       │ Human red-team review of        │
                                       │ high-severity flags + periodic   │
                                       │ live-web red-team campaigns      │
                                       └───────────────────────────────────┘
```

**Key decisions and tradeoffs:**
- **Split test surface into scripted-sandbox vs. controlled-live-web.** Scripted sandbox (cloned sites
  with injected content you control) gives reproducible, high-coverage injection tests; a controlled
  live-web slice (real sites, read-only or low-stakes actions only) validates that sandboxed findings
  generalize to the messy real internet, which a sandbox alone can't guarantee.
- **Treat prompt injection via page content as the primary threat**, not just malicious user prompts —
  the agent's biggest attack surface is content it *reads*, not just what the user *asks*. Test cases
  should embed instructions in page text, alt-text, hidden DOM elements, and even in tool/MCP-server
  responses.
- **Hard requirement: irreversible/high-stakes actions require explicit confirmation**, and this is
  tested as a bright-line pass/fail gate (any purchase/account-change without confirmation = automatic
  fail), not folded into a fuzzy quality score — this is the single highest-value bright line for this
  agent class.
- **Scope-of-action grading**, not just "did it complete the task" — an agent that completes a task by
  taking actions well beyond what was asked (e.g., asked to "find" a good deal but autonomously
  completes a purchase) has failed even if the literal task outcome looks good.

**Defending under pushback:**
- *"Live-web testing sounds risky — how do you justify it?"* — Strict guardrails: read-only or
  reversible actions only on the live slice, dedicated test accounts, small/controlled traffic, and a
  kill switch; the alternative (sandbox-only) systematically under-tests real-world injection diversity,
  which is a bigger risk long-term.
- *"How do you keep up with new injection techniques?"* — Continuous red-teaming (internal + external/
  bounty) feeding new cases into the regression suite (8.9, 8.10) on a standing cadence, plus monitoring
  production for anomalous action patterns as a detection backstop for anything eval missed.
- *"Isn't a confirmation gate just punting the safety problem to the user?"* — Partially, by design —
  for genuinely high-stakes, hard-to-fully-verify actions, human confirmation is a legitimate and
  standard defense-in-depth layer, not a cop-out; the eval's job is ensuring the gate is *actually*
  triggered every time it should be, which is itself a rigorously testable property.

> **Saying it out loud.** Start from the premise that every page is attacker-controlled, so the input surface is untrusted by construction. That gives you the suite: indirect injection from seeded malicious pages, exfiltration tests with honeytokens that fire if a canary ever leaves, destructive UI actions like purchase or delete without consent, credential misuse, and downloading untrusted content. Run it all in a sandboxed browser with fake-but-realistic resources, and report attack success rate, leak rate, and unauthorized-action rate. And when someone says a confirmation gate is just punting the problem to the user — partly, by design, that's legitimate defense in depth, and the eval's job becomes proving the gate fires every single time it should, which is a crisply testable property.

---

### 14.4 Design monitoring and online evaluation for a customer-support agent

**Prompt:** "Design production monitoring and continuous online evaluation for a customer-support agent
handling live chats."

**Clarifying questions to ask:**
- Fully autonomous resolution, or agent-assists-a-human (copilot) model?
- What actions can it take (refunds, account changes) vs. information-only?
- What's the existing human-support baseline to compare against?
- Volume — hundreds vs. millions of sessions/day (drives sampling strategy)?

**Architecture:**

```
   Live Chat Sessions
 ┌─────────────────────┐
 │ User ↔ Agent turns   │
 └──────────┬────────────┘
            │ every turn traced (input, retrieved KB, tool calls, output)
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │                  Real-Time Guardrail Layer                │
 │  - policy-violation classifier (blocks/redacts pre-send)   │
 │  - refund/account-action authorization check                │
 │  - PII leak detector                                        │
 └──────────┬─────────────────────────────┬─────────────────────┘
            │ pass                        │ flagged → human escalation
            ▼                             ▼
 ┌─────────────────────────┐   ┌───────────────────────────┐
 │  Streaming Metrics Store  │   │   Human Review Queue        │
 │  - error/tool-error rate   │   │  (high-severity flags,      │
 │  - escalation rate          │   │   stratified random sample) │
 │  - latency/cost             │   └──────────────┬───────────────┘
 │  - CSAT / thumbs             │                  │ labels feed back
 └──────────┬───────────────────┘                  ▼
            │                         ┌───────────────────────────┐
            ▼                         │  Gold-Set & Judge          │
 ┌─────────────────────────┐          │  Calibration Service        │
 │  Drift Detector            │◀────────┤  (re-validates judge vs.    │
 │  (intent mix, judge score  │          │   fresh human labels)       │
 │   trend, control charts)   │          └───────────────────────────┘
 └──────────┬───────────────────┘
            ▼
 ┌─────────────────────────────────────────────┐
 │  Dashboards: exec (health/SLO), eng (drill-   │
 │  down to trace), quality (judge health, suite  │
 │  growth) + alerting (paged vs. digest)          │
 └─────────────────────────────────────────────────┘
```

**Key decisions and tradeoffs:**
- **Real-time guardrails are separate from and faster than the judge-based quality layer.** Guardrails
  (policy/refund-authorization/PII) run synchronously and can block a message before it's sent; quality
  scoring (LLM-judge on a sample, CSAT aggregation) runs asynchronously and never blocks the live turn —
  conflating these would make the chat unacceptably slow.
- **Sampling strategy is stratified, not uniform**, oversampling escalations, low-confidence sessions,
  and any session touching a monitored-risk intent (refunds, cancellations) — uniform random sampling at
  high volume would mostly show you easy, already-fine sessions.
- **Implicit signals (reformulation, abandonment, escalation) are tracked as leading indicators**
  alongside explicit CSAT, since explicit ratings have low response rates and self-selection bias.
- **Judge-human agreement is itself monitored and re-validated on a schedule**, not set once — support
  policies and correct answers change over time (new refund policy, new product), so "ground truth" for
  the judge needs refreshing, or the judge silently drifts out of calibration with reality.

**Defending under pushback:**
- *"How do you know the sampled quality score reflects the whole population, not just what you chose to
  sample?"* — Stratified sampling with known weights lets you reconstruct a valid population estimate
  (inverse-propensity weighting) rather than a biased raw average of the sample; also periodically
  audit a small uniform-random slice alongside the stratified one specifically to check the stratified
  estimate isn't drifting from reality.
- *"What's your rollback plan if a metric spikes?"* — Guardrail-tier alerts (error rate, escalation
  spike, safety flags) page on-call immediately with an automatic feature-flag rollback path to the
  prior agent version; quality-tier trend alerts (daily digest) trigger investigation, not auto-
  rollback, since they're noisier and slower-moving.
- *"Isn't a human review queue too slow to matter for 'online' eval?"* — It's not meant to catch things
  in real time — the real-time guardrail layer does that. The human queue's job is calibrating the
  automated layers and catching what they systematically miss, on a days-not-seconds cadence, which is
  the right speed for that job.

> **Saying it out loud.** Three layers at three speeds. Real time, label-free: containment rate, escalation rate, latency, cost, safety flags — that's what pages you. Daily, sampled and judged: resolution quality, grounding against the knowledge base, satisfaction, sliced by intent. And weekly, human review of a stratified queue that over-samples low-confidence and escalated sessions. The proxy I'd lean on hardest is user reformulation, because it's a strong label-free signal that the first answer failed. And the objection worth pre-loading: no, the human queue isn't too slow for online eval — it's not there to catch things in real time, the guardrails do that. It's there to calibrate the automated layers on a days cadence, which is the right speed for that job.

---

### 14.5 Design the metrics and benchmark strategy for a brand-new agent product launch

**Prompt:** "Your company is launching a brand-new agent product with no prior production data or
benchmark. Design the metrics and benchmark strategy from zero to launch."

**Clarifying questions to ask:**
- What's the core value proposition / top 3–5 user jobs-to-be-done?
- What's the launch timeline — does it allow for a pre-launch closed beta to gather real data?
- Is there an adjacent product/team's eval infra to leverage, or truly greenfield?
- What's the risk tolerance / regulatory exposure of the domain?

**Architecture / phased plan:**

```
 Phase 0: Define                Phase 1: Build            Phase 2: Closed Beta       Phase 3: Launch Gate
 ┌───────────────────┐        ┌───────────────────┐     ┌───────────────────┐      ┌────────────────────┐
 │ - Task taxonomy      │      │ - Programmatic       │   │ - Small real-user   │    │ - Full regression   │
 │   (jobs-to-be-done,  │─────▶│   graders where       │──▶│   traffic, shadow +  │───▶│   suite gate         │
 │   difficulty tiers)  │      │   ground truth exists │   │   canary               │    │ - Guardrail metrics  │
 │ - North-star metric  │      │ - LLM-judge rubrics   │   │ - Mine real failures  │    │   (safety, cost,      │
 │   + guardrails        │      │   for the rest, human │   │   into the suite       │    │   latency) at SLO     │
 │ - Risk/safety          │      │   validated           │   │ - First judge-human    │    │ - Sign-off from        │
 │   taxonomy             │      │ - Seed dataset from   │   │   agreement validation │    │   product + safety     │
 │                        │      │   internal dogfood +  │   │                        │    │   owners                │
 │                        │      │   synthetic gen        │   │                        │    │                        │
 └───────────────────┘        └───────────────────┘     └───────────────────┘      └────────────────────┘
```

**Key decisions and tradeoffs:**
- **Define the north-star metric and guardrails before writing a single eval case.** North-star is
  usually task-success-rate on the core jobs-to-be-done; guardrails are safety-flag rate, cost/session,
  and latency SLO. Defining these first prevents the common trap of building a benchmark around whatever
  is easiest to measure rather than what actually matters to users.
- **Bootstrap gold data from dogfooding + synthetic generation, then validate hard against a closed
  beta.** With zero production data, internal team dogfood traffic and taxonomy-driven synthetic
  generation (9.9) are the only sources — but explicitly flag these as *provisional* until validated
  against real closed-beta usage, since internal users are a biased sample of the eventual real user
  base.
- **Borrow one relevant external benchmark for outside calibration, but don't gate launch on it alone**
  (10.3) — useful for "are we in the right ballpark vs. the field," not a substitute for a product-
  specific suite.
- **Launch gate combines a static bar (must clear X% on regression suite, zero critical safety
  failures) with a live-signal bar (shadow-mode/canary results must not show a guardrail regression)** —
  a purely static offline gate has repeatedly missed things that only show up on real traffic in
  practice, and a purely live gate is too slow/risky to be the only check before any launch.

**Defending under pushback:**
- *"You have no production data — how do you know your synthetic benchmark is meaningful at all?"* —
  It isn't fully validated yet, and I'd say so explicitly; that's exactly why the closed-beta phase
  exists — its job is specifically to validate (or correct) the pre-launch benchmark against real usage
  before the bar is treated as final, and the plan should show that validation step as a named gate, not
  an afterthought.
- *"This phased plan sounds slow for a competitive launch timeline."* — The taxonomy/guardrail
  definition (Phase 0) is cheap and fast (days, not months); the closed beta can run in parallel with
  continued feature build-out rather than strictly gating it, and the plan is right-sized to launch
  risk — a low-stakes internal tool could compress phases 2–3, a consumer-facing agent with real-money
  actions should not.
- *"What if the beta reveals the north-star metric itself was wrong?"* — That's a legitimate and not-
  uncommon outcome; the response is to revise the metric definition with a documented rationale and
  re-baseline, not to force the original metric to keep working — a metrics strategy that can't survive
  contact with real users wasn't validated, and admitting that mid-flight is the correct call, not a
  failure.

> **Saying it out loud.** With no traffic yet, you have no distribution, so start from a task taxonomy built with domain experts and a small hand-built benchmark, then define one north-star metric and the guardrails around it — cost per successful task, p95 latency, safety violation rate. Ship to a small beta specifically to learn the real distribution, and plan from day one for the benchmark to be replaced by mined production cases within a couple of months. The thing I'd say explicitly is that the north-star metric may turn out to be wrong, and that's a normal outcome, not a failure — you revise the definition with a documented rationale and re-baseline. Forcing a metric that didn't survive contact with real users is how teams end up optimizing something nobody wanted.

---

## 15. Rapid-Fire Flashcards

*One-liners for drilling. Format: **Q** — A.*

**Fundamentals**
- **What distinguishes an "agent" from a plain LLM call?** — Autonomy over multiple steps: planning,
  tool use, and acting on the environment without a human in the loop each step.
- **What's the difference between capability and behavior evaluation?** — Capability asks "can it do X
  at all"; behavior asks "does it reliably do X the right way, safely, under real conditions."
- **Why is agent eval harder than single-turn LLM eval?** — Compounding errors across steps, huge action/
  trajectory space, non-determinism, and environment-dependent ground truth.
- **What is a trajectory?** — The full sequence of an agent's thoughts, tool calls, observations, and
  outputs for one task run.
- **What's the "needle in a trajectory" problem?** — A single wrong step early on can silently doom an
  otherwise-competent multi-step run — failures compound rather than average out.

**Frameworks & Metrics**
- **Outcome vs. process evaluation?** — Outcome grades the final result; process grades the steps taken
  to get there (efficiency, safety, reasoning quality).
- **What's a rubric-based eval?** — Decomposing a judgment into explicit, separately-scored criteria
  rather than one holistic score.
- **Why report confidence intervals, not just pass rate?** — To distinguish real regressions/gains from
  sampling noise, especially on small slices.
- **What is Goodhart's Law's relevance here?** — Any metric that becomes a target gets gamed — optimize
  for the underlying goal, monitor the metric as a proxy, not the objective itself.
- **Why slice results instead of reporting one aggregate?** — An aggregate can hide a serious regression
  in a small but important segment.
- **What's construct validity in eval terms?** — Whether the benchmark/metric actually measures the
  capability you care about, not a correlated proxy.

**Tool Use**
- **Four dimensions of tool-use eval?** — Selection, invocation/arguments, chaining/orchestration, result
  handling.
- **Over-calling vs. under-calling?** — Using a tool when unnecessary vs. failing to use one when needed
  — both are calibration failures.
- **Why mock/sandbox tools in eval?** — Reproducibility and safety — no real side effects, deterministic
  replay.
- **Schema-valid vs. semantically correct?** — A call can be valid JSON with right types yet still wrong
  values — grade both separately.
- **What is MCP?** — Model Context Protocol — an open standard for connecting agents to tools/data/
  prompts, "USB-C for AI tools."

**Reasoning**
- **Faithfulness of chain-of-thought?** — Whether the stated reasoning actually reflects the computation
  producing the answer — not guaranteed, must be tested.
- **Process vs. outcome reward in reasoning eval?** — Process grades intermediate steps; outcome grades
  only the final answer — process catches "right answer, wrong/lucky reasoning."
- **Why do harder reasoning benchmarks saturate fast?** — Frontier models improve quickly and public
  benchmarks leak into training data over time.

**Safety**
- **What is reward hacking in agents?** — Optimizing the literal metric/reward in an unintended way that
  violates the actual goal (e.g., deleting failing tests to "pass").
- **Prompt injection vs. jailbreak?** — Injection: malicious instructions smuggled in via content the
  agent processes; jailbreak: manipulating the model's own instructions/persona to bypass restrictions.
- **Why is a confirmation gate a legitimate safety control?** — For high-stakes/irreversible actions,
  human confirmation is a valid defense-in-depth layer, not a cop-out.
- **What should safety eval treat as a bright line, not a fuzzy score?** — Irreversible/high-stakes
  actions taken without required authorization.

**Multi-Agent**
- **What is credit assignment in multi-agent eval?** — Determining which agent in a chain caused a
  failure or success.
- **Cooperative vs. adversarial multi-agent eval?** — Cooperative measures joint outcome/synergy;
  adversarial measures equilibrium quality and watches for collusion/degenerate strategies.
- **Why is multi-agent eval reproducibility hard?** — Non-determinism compounds with agent count and
  async message ordering.

**Real-World & Automated Eval**
- **What is shadow mode?** — Running a new agent version on live traffic silently, scoring it without
  showing users its output.
- **Why randomize A/B tests at the user level, not request level?** — To avoid inconsistent behavior
  within a session and capture session-level effects.
- **Pointwise vs. pairwise LLM judging?** — Pointwise scores one response on a scale; pairwise compares
  two — LLMs are more reliable at pairwise comparisons.
- **How do you validate an LLM judge?** — Measure agreement against a human-labeled gold set, check for
  position/verbosity/self-preference bias.
- **What's the eval cost-cascade pattern?** — Cheap deterministic checks first, escalate only ambiguous
  cases to an expensive LLM judge.

**Benchmarks**
- **Name the standard agent benchmarks.** — SWE-bench (Verified), GAIA, WebArena, AgentBench,
  Terminal-Bench, OSWorld, tau-bench/tau2-bench, BFCL.
- **What does SWE-bench grade on?** — Whether a patch makes the repo's held-out test suite pass.
- **What does tau-bench grade?** — Policy compliance and task resolution for customer-service agents vs.
  a simulated user.
- **Biggest weakness of public benchmarks?** — Contamination and saturation over time; narrow domain
  transfer to your actual product.
- **Why keep a private held-out benchmark slice?** — To detect overfitting/gaming of the public-facing
  suite.

**Tooling & Monitoring**
- **What should agent tracing capture at minimum?** — Trace ID, full input/output per step, tool
  name/args/result, model+prompt version, cost/latency.
- **What's the OTel GenAI convention relevance?** — A standard schema for LLM/agent spans so tracing is
  portable across vendors.
- **Guardrail alert vs. quality-trend alert?** — Guardrail pages immediately (safety/error spike);
  quality-trend is a slower digest for gradual decline.
- **What's the most important post-mortem deliverable?** — A new regression-suite case or monitor, not
  just a narrative.
- **How do you detect production drift?** — Compare rolling input/output distributions to a baseline
  window (e.g., PSI/KL divergence).

**2025–2026 Landscape**
- **What is Claude Sonnet 5's positioning?** — A cheaper, agent-focused mid-tier model close to Opus
  4.8 quality on some tasks, launched June 2026.
- **What changed in MCP's July 2026 spec?** — Stateless core (no session handshake), Multi Round-Trip
  Requests, OAuth hardening (issuer validation, CIMD), deprecated legacy SSE transport.
- **What is tau2-bench?** — Sierra Research's successor to tau-bench, refining simulated tool-agent-
  user interaction realism.
- **What's the general 2024→2026 shift in agent eval emphasis?** — From single-turn/single-tool eval to
  long-horizon trajectory eval, from static leaderboards to production-correlated suites, and toward
  cost as a co-equal axis with capability.

---

## 16. Glossary

- **Agent** — A system that autonomously plans, acts (often via tools), and adapts across multiple steps
  to achieve a goal.
- **Agentic AI** — AI systems characterized by autonomy, tool use, and multi-step goal pursuit, as
  opposed to single-turn response generation.
- **Trajectory** — The full recorded sequence of an agent's reasoning, tool calls, and observations for
  one task run.
- **Rollout** — One executed run of an agent on a task, often used interchangeably with trajectory.
- **Grounding** — The property that an agent's claims are supported by retrieved/tool-returned evidence
  rather than fabricated.
- **Faithfulness** — Whether stated reasoning or cited evidence accurately reflects what actually
  produced the output.
- **Hallucination** — A confident but unsupported or false claim.
- **LLM-as-judge** — Using an LLM to score or compare outputs against a rubric, in place of or alongside
  human raters.
- **Pointwise judging** — Scoring one response in isolation on a scale.
- **Pairwise judging** — Comparing two responses head-to-head to determine which is better.
- **Rubric** — An explicit, decomposed set of scoring criteria used for consistent grading.
- **Gold set** — A curated, human-validated dataset with trusted labels used to calibrate judges/metrics.
- **Inter-annotator agreement** — A measure (e.g., Cohen's/weighted kappa) of how consistently human
  raters score the same items.
- **Construct validity** — Whether a metric/benchmark truly measures the capability it claims to.
- **Contamination** — When benchmark data leaks into a model's training data, inflating scores.
- **Saturation** — When a benchmark stops discriminating between strong models because scores cluster
  near the ceiling.
- **Goodhart's Law** — "When a measure becomes a target, it ceases to be a good measure" — metrics get
  gamed once optimized against directly.
- **Reward hacking** — Achieving a high score/reward via an unintended shortcut that violates the actual
  goal.
- **Prompt injection** — Malicious instructions smuggled into content an agent processes (web pages, tool
  results, documents) to hijack its behavior.
- **Jailbreak** — Manipulating a model's instructions/persona to bypass its safety training or policies.
- **Sandboxing** — Running an agent in an isolated, resettable environment to contain side effects.
- **Shadow mode** — Running a new system version on live traffic without exposing its output to users,
  for silent comparison.
- **Canary release** — Exposing a small percentage of real traffic to a new version before full rollout.
- **Guardrail metric** — A metric with a hard threshold that blocks release/triggers rollback if
  breached (e.g., safety-flag rate).
- **North-star metric** — The single primary metric a product/feature is optimized against.
- **Drift** — A change over time in the input or output distribution relative to a baseline.
- **Distribution shift** — Same as drift; production data no longer resembling the eval/training
  distribution.
- **Process supervision** — Grading/rewarding intermediate reasoning steps, not just the final answer.
- **Outcome supervision** — Grading only the final result.
- **Credit assignment** — Determining which component (agent, step, tool call) caused a multi-step
  outcome.
- **Orchestrator-worker architecture** — A multi-agent pattern where one agent decomposes/delegates and
  others execute sub-tasks.
- **Tool-calling / function-calling** — An LLM's ability to invoke external tools/APIs with structured
  arguments.
- **Schema conformance** — Whether a tool call's arguments are valid JSON with correct types/required
  fields.
- **MCP (Model Context Protocol)** — An open standard for connecting AI agents to tools, data sources,
  and prompts.
- **MCP server** — A service exposing tools/resources/prompts to an agent via MCP.
- **Extended thinking / reasoning mode** — A model setting that allocates more inference-time compute to
  internal reasoning before answering.
- **Chain-of-thought (CoT)** — A model's intermediate step-by-step reasoning text.
- **Unfaithful CoT** — Reasoning text that doesn't accurately represent the actual computation behind
  the answer.
- **Simulated user** — An LLM-driven stand-in for a real user, with a hidden goal, used to test
  multi-turn agents at scale.
- **tau-bench / tau2-bench** — Benchmarks (Sierra Research) evaluating agents via simulated-user
  interactions against a policy.
- **SWE-bench (Verified)** — A benchmark grading agents on resolving real GitHub issues by running the
  repo's held-out tests.
- **GAIA** — A benchmark of general-assistant tasks requiring browsing, tool use, and multi-step
  reasoning, graded by short-answer match.
- **BFCL (Berkeley Function-Calling Leaderboard)** — A benchmark isolating function/tool-calling
  accuracy.
- **OSWorld** — A benchmark of real desktop-GUI tasks executed on a live virtual machine.
- **OpenTelemetry (OTel) GenAI conventions** — A standardized schema for tracing LLM/agent operations
  (spans, tokens, cost).
- **PSI / KL divergence** — Statistical measures used to detect distribution shift between two data
  windows.
- **Control chart** — A statistical-process-control technique (mean ± k·σ) for flagging metric
  deviations beyond normal variance.
- **Cascade evaluation** — Running cheap checks first and escalating only ambiguous cases to expensive
  judges/humans.
- **Step cap** — A maximum number of steps/tool calls allowed before an agent run is forced to stop.
- **Escalation rate** — The fraction of agent sessions handed off to a human.
- **Faithfulness/attribution rate** — The fraction of claims in an output that are verifiably supported
  by retrieved/tool evidence.
- **CIMD (Client ID Metadata Documents)** — An MCP/OAuth mechanism superseding Dynamic Client
  Registration for binding client identity.
- **Dogfooding** — Using your own product internally before/alongside external users, as an early
  data source.

---

## 17. Behavioral / Experience (STAR)

*The STAR method (Situation, Task, Action, Result) structures a behavioral answer so it's concrete and
evidence-based rather than a vague claim of skill. Below: a template, three filled-in example answers
using a plausible agent-eval project, and guidance for framing thinner real experience honestly.*

**Template:**
- **Situation** — one or two sentences of concrete context (what system, what stakes).
- **Task** — what you specifically were responsible for (not "the team" — you).
- **Action** — the concrete steps you took, emphasizing judgment calls and tradeoffs, not just activity.
- **Result** — a quantified or otherwise verifiable outcome, plus what you learned/would do differently.

### Example 1 — Building an LLM-judge pipeline from scratch

**Situation.** Our support-agent team had no automated way to score response quality beyond a slow
weekly human-review sample of ~50 conversations, which meant prompt/model changes shipped without any
quality signal for days.

**Task.** I was asked to build an automated quality-scoring pipeline that the team could trust enough to
gate releases on.

**Action.** I started by writing an explicit rubric with the support lead (correctness, policy
compliance, tone) rather than a vague "quality" score, then built an LLM-judge prompt against it with
calibration examples spanning the scale. Before trusting it for anything, I ran it against 200 human-
labeled conversations and measured agreement — the first version had only 61% agreement, mostly because
it over-rewarded verbose responses. I added an explicit "do not reward length" instruction and randomized
response order to remove position bias, which brought agreement to 84%, close to our human inter-
annotator agreement of ~88%.

**Result.** We wired the validated judge into CI as a soft gate (block merge on regression beyond 2
points) and a full production-sampling pipeline. Within a month it caught two prompt regressions before
they reached more than 5% of traffic that would previously have shipped fully. What I'd do differently:
I'd build the human-agreement validation step first, before writing the judge prompt at all — I spent
time iterating on prompt wording before I had a way to actually know if it was improving.

---

### Example 2 — Root-causing a multi-agent production incident

**Situation.** A three-agent research-and-summarize pipeline (planner → retriever → writer) started
producing summaries with subtly wrong numbers roughly 8% of the time, only visible in production, not in
our offline eval.

**Task.** As the eval owner, I was responsible for finding the root cause and closing the gap in our
suite so it wouldn't ship silently again.

**Action.** Since the failure wasn't reproducible offline, I pulled 30 real failing traces and used
trajectory tracing with a shared trace ID across the three agents to line up each agent's view of the
shared state. I found the retriever was occasionally returning a stale cached document (a caching bug,
not a model problem) and the writer had no mechanism to notice the retrieved date didn't match the
question's timeframe — it just trusted the input. I ran an ablation replacing the retriever with an
oracle to confirm the writer alone wasn't the cause, isolating the caching bug as root cause.

**Result.** Fixed the cache-invalidation bug and, separately, added a grounding check to the writer's
eval (does its date claim match the retrieved document's date?) plus 12 new regression cases mined from
the real failing traces. Production error rate on that failure mode dropped to under 1% and stayed
there through two subsequent model upgrades. Lesson: I now treat "not reproducible offline" as a
tracing-and-instrumentation gap to close, not a reason to deprioritize the bug.

---

### Example 3 — Pushing back on a metric the team wanted to ship on

**Situation.** Ahead of a launch, the product team wanted to gate on a single "helpfulness" score from an
off-the-shelf eval framework's default judge.

**Task.** I wasn't asked to object, but as the person who'd own the consequences of a bad gate, I felt
responsible for raising it.

**Action.** I ran the default judge against 40 of our known-good and known-bad transcripts and showed it
disagreed with our own prior human labels on 9 of them, mostly favoring longer, more hedged answers
regardless of correctness — a verbosity bias. I proposed decomposing "helpfulness" into a rubric
(correctness, actionability, tone) with a validated custom judge instead, and offered to have it ready
within a week rather than blocking the existing timeline outright.

**Result.** The team agreed to delay the gate decision by one week. The rubric-based judge shipped with
79% human agreement (vs. the default judge's 58% on our transcripts) and caught a real regression in the
launch candidate's actionability that the original judge had missed entirely. Lesson: raising a concrete,
evidenced concern with a fast alternative in hand lands very differently than raising an abstract
objection with no path forward.

---

### Framing experience honestly when it's thinner than the ideal

If you haven't built a full eval platform end to end, don't invent scale you don't have — instead:
- **Reframe around the smallest complete loop you *have* run**: even a small project (calibrated one
  LLM-judge against 50 human labels, or root-caused one production failure via tracing) demonstrates the
  same judgment as a larger version of the same loop. Interviewers are probing for the *reasoning
  pattern* (define ground truth → validate the measurement → close the loop), which is scale-
  independent.
- **Be explicit about scope, don't inflate it.** "I built this for my own side project on a 50-case
  benchmark" is a credible, specific answer; a vague claim that implies enterprise scale without owning
  the real scope invites a follow-up question you can't sustain.
- **Use adjacent experience honestly, named as adjacent.** If your real background is ML evaluation
  broadly (not agents specifically), say so and connect the transferable parts explicitly ("I haven't
  evaluated multi-agent trajectories specifically, but I built a very similar failure-mining loop for a
  single-model classifier — the calibration and drift-detection logic transfers directly").
- **Lead with what you'd do, grounded in what you've done elsewhere**, when directly asked about
  something you haven't done — this is what most of Part I's answers model: a concrete method, not a
  claim of specific past scale.

---

## 18. Red Flags vs Green Flags

*From the interviewer's perspective — what tends to separate a strong senior answer from a weak one
across this whole domain.*

| Dimension | Red flag (weak signal) | Green flag (strong signal) |
|---|---|---|
| Metrics | One vague "quality score," no breakdown | Multi-dimensional rubric, sliced by segment, with CIs |
| Ground truth | "The LLM judge decides" with no validation | Judge validated against a human gold set, agreement reported |
| Failure handling | Talks only about happy-path success | Names specific failure modes and how each is caught |
| Reproducibility | No mention of seeds/versions/environment state | Pinned versions, sandboxed/resettable environments |
| Statistics | Reports a single pass-rate number as fact | Reports confidence intervals, discusses sample size |
| Safety | Treats safety as a final add-on step | Bakes safety cases into the core suite from the start |
| Production | Assumes offline eval = done | Describes the offline↔online feedback loop explicitly |
| Cost | Never mentions cost/latency | Reports cost-per-successful-task alongside accuracy |
| Tool use | "It calls the right tool" with no nuance | Distinguishes selection/args/chaining/result-handling |
| Multi-agent | No answer for credit assignment | Concrete method (tracing + ablation) for isolating cause |
| Landscape | Cites stale/outdated model or benchmark facts confidently | Gives dated facts, flags uncertainty, offers to verify |
| Honesty | Overclaims scale/scope of past experience | Frames real scope honestly, connects transferable judgment |
| Pushback | Gets defensive or vague under a challenge | Engages the tradeoff directly, updates position if warranted |
| Closing the loop | Fixes fail silently with no regression case | Every fix/incident produces a permanent suite addition |

---

## 19. Traps & How to Recover

*Common wrong answers or misconceptions interviewers specifically listen for, each with why it's wrong
and how to reframe it live if you catch yourself saying it.*

### 19.1 "We just use the LLM to judge itself, it works fine."

**Why it's wrong.** No validation against ground truth means you can't know if the judge is any good —
it could be confidently, consistently wrong (e.g., systematically biased toward verbose or self-similar
outputs) and you'd never find out.

**Reframe.** "We use an LLM judge, but we validate it against a human-labeled gold set first and
monitor agreement over time — I'd never gate a release on an unvalidated judge."

> **Saying it out loud.** The problem isn't using an LLM as a judge, it's the 'it works fine' part — with no ground truth you have no way of knowing. A judge can be confidently and consistently wrong, systematically favoring longer or more familiar-sounding answers, and everything downstream will look perfectly healthy. So the reframe is: yes we use an LLM judge, we validated it against a human-labeled gold set, here's the agreement number, and we re-check it on a schedule. The line I'd finish on is that I wouldn't gate a release on an unvalidated judge, because at that point the gate isn't measuring the agent, it's measuring the judge's taste.

### 19.2 "Accuracy was 95%, so the model is basically solved for this task."

**Why it's wrong.** A single aggregate hides slice-level failures, ignores confidence intervals, and
says nothing about the cases that matter most (safety-critical or high-value segments could be far
worse than 95%).

**Reframe.** "95% aggregate — but I'd want to see it sliced by task type and stratified by risk segment,
and check whether that's a statistically meaningful improvement given our sample size, before calling
anything solved."

> **Saying it out loud.** Three things are missing from that sentence and any one of them can flip the conclusion. There's no confidence interval, so I don't know if 95 is different from 93. There's no slicing, so a critical low-volume intent could be sitting at 60 and the average would never show it. And there's no cost or safety number next to it. The reframe is to ask for it sliced by task type and stratified by risk segment before anyone says solved. And the specific danger with high aggregate numbers is that they end the conversation — nobody digs into a 95, which is exactly when the bad slice ships.

### 19.3 "We test it on [public benchmark] and that's our eval strategy."

**Why it's wrong.** Public benchmarks are contamination-prone, can saturate, and are rarely construct-
valid for your specific product's task distribution.

**Reframe.** "We'd use a public benchmark as an external sanity check, but the primary suite is built
from our own task taxonomy and mined production failures, since that's what actually predicts our
users' experience."

> **Saying it out loud.** A public benchmark is a sanity check, not a strategy. It's contamination-prone, it saturates, and most importantly it almost never has construct validity for your product — SWE-bench going up tells you very little about your internal enterprise workflow agent. The reframe is that the primary suite is built from your own task taxonomy and mined production failures, and the public benchmark is there for external comparability and baseline competence. The test I'd offer is simple: does the benchmark score move when your users' experience moves? If it doesn't, it isn't your eval strategy, it's a number on a slide.

### 19.4 "The agent passed all our tests, so it's ready for production."

**Why it's wrong.** Offline tests are a fixed proxy; production is an open, drifting, adversarial
distribution. Passing a static suite says nothing about live tool outages, real user phrasing, or
distribution shift.

**Reframe.** "Passing the offline suite is a release gate, not a launch decision on its own — I'd
still want shadow mode and a staged canary with rollback guardrails before full rollout."

> **Saying it out loud.** Passing a static suite is a gate, not a launch decision — those are different things and conflating them is how bad releases happen. The suite is a fixed proxy; production is open, drifting, and occasionally adversarial, and it has real tool outages and real user phrasing your tests have never seen. So the reframe is that green tests earn you the right to run shadow mode, then a canary with rollback guardrails, then a ramp. The failure mode here is specific and common: teams treat the suite as the finish line, and then the first real incident is discovered by a customer rather than by a metric.

### 19.5 "We don't need to worry about reward hacking, our reward function is straightforward."

**Why it's wrong.** Reward hacking emerges from *any* imperfect proxy metric under optimization
pressure, not just complex reward functions — "straightforward" metrics (test pass rate, keyword match)
are some of the most commonly gamed in practice (e.g., deleting failing tests).

**Reframe.** "Any metric under optimization pressure is at risk of being gamed — I'd specifically test
for shortcut/gaming behavior relative to *our* metric, not assume simplicity makes it safe."

> **Saying it out loud.** Simplicity is actually what makes a metric easy to game, not what protects it. Test-pass rate and keyword match are about as straightforward as metrics get, and they're two of the most commonly gamed in practice — the classic being an agent that deletes the failing test. Reward hacking comes from any imperfect proxy under optimization pressure, and every metric is an imperfect proxy. So the reframe is that I'd test specifically for gaming behavior relative to *our* metric — hidden verification the agent can't touch, plus trajectory review — rather than assuming the reward function's simplicity makes it safe.

### 19.6 "Multi-agent systems are basically the same as single-agent, just evaluated per-agent."

**Why it's wrong.** This misses emergent system-level failure modes (miscommunication, error
propagation, credit-assignment ambiguity) that don't exist when you look at any single agent in
isolation.

**Reframe.** "I'd evaluate each agent's component competence, but the system-level behavior — where
errors propagate, how credit assigns across the chain — needs its own tracing and ablation-based
analysis; it's not just the sum of per-agent scores."

> **Saying it out loud.** Per-agent scoring misses the entire category of failure that makes multi-agent hard. Two individually correct agents can produce a failure purely by miscoordinating — dropped context at a handoff, one accepting the other's hallucination as fact, an endless ping-pong. None of that appears when you score any single agent in isolation. So the reframe is: component competence per agent, plus system-level analysis with cross-agent tracing and ablations to figure out where credit and blame actually land. And I'd add the cost point — coordination failures don't just fail, they fail at several times the token budget of the equivalent single-agent run.

### 19.7 "Chain-of-thought shows us exactly how the model reasoned, so we can just read it."

**Why it's wrong.** CoT faithfulness isn't guaranteed — the visible reasoning can diverge from the
actual computation behind the answer, especially under optimization pressure that rewards plausible-
looking reasoning.

**Reframe.** "I treat visible reasoning as a diagnostic signal, not ground truth — I'd verify
conclusions independently rather than trusting a convincing-looking trace at face value."

> **Saying it out loud.** It shows you a story about how it reasoned, which is not the same object. Faithfulness isn't guaranteed — the visible trace can diverge from the actual computation, and if training rewards traces that look good, you should expect them to look good rather than to be accurate. So the reframe is that I treat visible reasoning as a diagnostic signal and verify conclusions independently — final-answer grading, consistency across resamples, process supervision against known intermediate steps. The failure mode to name is the persuasive wrong trace, because a human reviewer reading it will sign off, which makes it worse than a trace that's obviously incoherent.

### 19.8 "We ran an A/B test and it won, so we shipped it."

**Why it's wrong.** Without checking sample size/power, guardrail metrics, and randomization unit
(user vs. request), an apparent win can be noise, or a real win on the primary metric masking a
guardrail regression (cost, safety, latency).

**Reframe.** "We'd pre-register the primary metric and guardrails, check the test had adequate power,
and confirm no guardrail regressed before calling it a win."

> **Saying it out loud.** Won on what, with how much power, randomized how? Any of those three can turn a win into noise. If you randomized at the request level, users saw both agents and you measured confusion. If you didn't do a power calculation, given how high agent per-session variance is, you may well be looking at chance. And if you only tracked the primary metric, you can absolutely win on success while quietly regressing cost, latency, or escalation. So the reframe is pre-registered primary and guardrail metrics, adequate power, and explicit confirmation that no guardrail moved before anyone says shipped.

### 19.9 "Our tool-use eval is just checking if it called the right tool."

**Why it's wrong.** This ignores argument correctness, chaining/ordering, result-grounding, and
restraint (knowing when *not* to call a tool) — a huge share of real tool-use failures live in those
other dimensions.

**Reframe.** "Selection is one of four dimensions I'd check — selection, argument correctness, chaining,
and result-handling — plus whether it correctly avoids calling a tool when it shouldn't."

> **Saying it out loud.** Selection is one of four dimensions and honestly not the one that fails most. The others are argument correctness — right shape, wrong values is extremely common — chaining and ordering, and result handling, meaning did it actually read what came back. And then there's the fifth thing, restraint: knowing when *not* to call a tool at all. A model can be 100% schema-valid and 30% wrong on argument values, and a selection-only metric will show you a perfect score while users get wrong answers. So the reframe is score all four, and add explicit no-tool-needed cases.

### 19.10 "We don't test for prompt injection because our tools are internal/trusted."

**Why it's wrong.** Any content the agent *reads* (retrieved documents, web pages, tool outputs, even
MCP server responses) is a potential injection vector regardless of whether the tool call itself is
"internal" — the risk is in untrusted content, not just untrusted infrastructure.

**Reframe.** "Even with trusted infrastructure, any external content the agent processes is a potential
injection vector — I'd still test with injected instructions embedded in retrieved/tool content."

> **Saying it out loud.** The risk isn't in your infrastructure, it's in the content. Any text the agent *reads* is an injection vector — a retrieved document, a web page, an email body, a tool result, even an MCP server's tool description — and it doesn't matter that the tool call itself went to a service you own. If the agent summarizes a customer-supplied PDF, that PDF is attacker-controlled input running through a system with credentials. So the reframe is: trusted infrastructure, untrusted content, and I'd still run injection tests with payloads embedded in retrieved and tool-returned content. This is consistently rated the top security risk for LLM agents, and 'our tools are internal' is the most common reason teams skip it.

### 19.11 "Human review doesn't scale, so we should fully automate evaluation."

**Why it's wrong.** Full automation without any human anchor means your automated judges have no ground
truth to calibrate against and will silently drift, especially as "correct" answers change over time
(policy updates, new products).

**Reframe.** "Automation handles routine volume, but I'd keep a standing human review process for gold-
set maintenance and judge re-calibration — full automation with no human anchor eventually drifts
undetected."

> **Saying it out loud.** Human review doesn't scale, that part's true — the wrong inference is 'therefore eliminate it'. Without a human anchor, your automated judges have nothing to calibrate against and will drift silently, and the drift is worst exactly when it matters, because correct answers themselves change as policies and products change. So the reframe is that automation handles routine volume and humans do the small, high-leverage part: gold-set maintenance, judge recalibration, adjudicating disagreements, and a rotating audit. It's a few hours a week, not an army, and it's the difference between a metric and a number.

### 19.12 "Cost doesn't matter at the eval stage, we'll optimize that later."

**Why it's wrong.** Ignoring cost/latency during eval means model or design choices get locked in
before you know their true tradeoff, and "cheaper but 10% worse" vs. "expensive but marginally better"
is often the actual decision an eval needs to inform.

**Reframe.** "I'd report cost and latency alongside accuracy from the start — a lot of real model/design
decisions are cost-normalized tradeoffs, not pure accuracy plays."

> **Saying it out loud.** Cost is often the actual decision the eval exists to inform, so deferring it means you've deferred the decision. Real choices look like 'cheaper but ten percent worse' versus 'expensive and marginally better', and you cannot answer that without cost in the report from day one. Worse, if you evaluate without it you'll lock in a model and a design before you know the tradeoff, and undoing that later is a rewrite rather than a config change. So the reframe is: report cost and latency alongside accuracy from the first run, and make the headline metric cost per *successful* task, because that's the number that survives contact with a finance conversation.

### 19.13 "One incident, one quick fix — no need for a post-mortem or new test case."

**Why it's wrong.** Without a permanent regression-suite addition, the same failure class can silently
recur after the fix is forgotten or a later change reintroduces it.

**Reframe.** "Even for a quick fix, I'd add the minimal repro as a permanent regression case — the fix
matters less than making sure it can't silently regress again."

> **Saying it out loud.** The fix matters less than the guarantee that it can't silently come back. Without a permanent regression case, the same failure class returns the moment someone refactors, changes a prompt, or the vendor updates the model — and nobody connects it to the incident from six months ago. So even for a trivial quick fix, the minimal repro goes into the suite. That's cheap: usually one case, ten minutes. And it's the mechanism by which an eval suite gets better over time rather than staying at whatever someone imagined on day one — I'd actually track suite growth from production as its own metric.

---

## 20. Final Tips & Resources

- **Lead with method, not memorized facts.** Interviewers in this space are usually probing for a
  repeatable reasoning pattern (define the goal → pick the cheapest valid measurement → validate it
  against ground truth → close the loop from production) more than for recall of any specific benchmark
  number.
- **Always be ready to say "I'd verify that."** This field moves monthly; calibrated uncertainty about a
  specific fact reads as more senior than confident recall that turns out to be stale.
- **Quantify wherever you can, and flag when you can't.** A number with a caveat about sample size beats
  a vague qualitative claim, and vague qualitative claims dressed up as certainty are one of the fastest
  ways to lose credibility with a technical interviewer.
- **Always connect a technique back to a concrete failure mode it catches.** "We validate the judge
  against human labels" is stronger paired with "...because an unvalidated judge with position bias
  would silently favor the first option in every pairwise test we ran."
- **Practice the system-design scenarios out loud, not just read them.** The clarifying-questions step
  is often the single highest-signal part of a design interview — resist the urge to jump straight to
  the architecture.
- **Revisit Part II (13) close to interview day, not weeks before.** The landscape section is the part of
  this guide most likely to go stale fastest — do a quick refresh search on current models/benchmarks
  the week of your interview.
- **Use the STAR examples in Part V as a structure, not a script.** Swap in your own real project
  details; a rehearsed-sounding answer using someone else's project reads worse than an honest, less
  polished answer about your own.

---
