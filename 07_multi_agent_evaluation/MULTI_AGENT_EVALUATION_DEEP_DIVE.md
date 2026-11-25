# Multi-Agent Evaluation — A Deep Dive

> "A multi-agent system can produce the right answer while every step of its process was wrong — and it can produce a wrong answer while every individual agent behaved correctly. Evaluating only the answer misses both."

> **What you will be able to do by the end.** (a) *Build* a real orchestrator-plus-workers multi-agent system and instrument it for evaluation; (b) *score* it on outcome, per-agent credit, coordination, and cost; (c) *diagnose* a failure down to the agent and step that caused it; (d) *decide* — with numbers — whether the multi-agent architecture is earning its 15x token bill or whether a single agent would do; and (e) *convince a senior interviewer* you understand the 2025–2026 landscape, the failure taxonomy, and the live architectural debate cold.

## Why This Matters

Single-agent evaluation asks a comparatively simple question: given an input, did the agent produce a good output? Multi-agent evaluation asks a harder one: given a *society* of agents that talk to each other, hand off work, criticize one another, and share state, did the **system** behave well — and if it did not, *which agent, at which step, caused the failure*?

This distinction is not academic. As soon as you move from one agent to several, three new classes of things can go wrong that simply do not exist in the single-agent world:

1. **The communication channel** — agents misread, ignore, or corrupt each other's messages.
2. **The coordination structure** — the wrong agent does the work, two agents do the same work, or everyone waits for everyone else.
3. **Emergent dynamics** — errors amplify as they propagate, agents converge on a confidently wrong consensus (groupthink), or the system stalls (deadlock).

The economics also change, and they change hard. Anthropic reports that agents use roughly **4x more tokens than chat**, and multi-agent systems roughly **15x more tokens than chat** ([Anthropic, "How we built our multi-agent research system," June 2025](https://www.anthropic.com/engineering/multi-agent-research-system)). In their analysis, **token usage alone explained about 80% of the variance** in how well their research system performed — meaning most of the "intelligence" you are buying is really *permission to spend more tokens searching in parallel*. At 15x the cost, a multi-agent architecture has to *earn* its overhead, and the only way to know whether it does is to evaluate it properly against a single-agent baseline. Evaluation is therefore not just a quality gate; it is the instrument that tells you whether you should be running a multi-agent system at all.

There is also a live, public disagreement among the teams who build these systems for a living about whether you should build them at all. In June 2025 Cognition (the Devin team) published ["Don't Build Multi-Agents"](https://cognition.com/blog/dont-build-multi-agents), arguing that parallel subagents make conflicting implicit decisions and that a single, linear, context-engineered agent is more reliable. The same month Anthropic published the opposite lesson from its research product. Both cannot be unconditionally right — and the reconciliation (below) is one of the most useful things you can carry into an interview.

This chapter gives you the intuition, the current landscape, the metrics, a taxonomy of failures grounded in real research, working code you can run, production war stories, and an honest account of when multi-agent is worth it.

> **Saying it out loud.** Single-agent evaluation asks "did it produce a good output." Multi-agent evaluation asks something much harder: given a whole society of agents that hand work to each other and share state, did the *system* behave well — and if not, which agent, at which step, caused it. Three things go wrong that simply don't exist with one agent: communication breakdowns, coordination failures, and emergent dynamics like cascades and groupthink. And the economics change hard — Anthropic reports agents use about four times the tokens of chat and multi-agent about fifteen times, with token budget alone explaining roughly 80% of their performance variance. That last number is the punchline: at 15x cost, a lot of what you're buying isn't cleverness, it's permission to spend more tokens, and evaluation is the only instrument that tells you whether you should be running multi-agent at all.

---

## Core Intuition

Hold three ideas in your head before anything else.

**1. Outcome and process are separable.** A pipeline of a planner, a coder, and a reviewer can ship correct code because the coder happened to be right and the reviewer rubber-stamped it without reading — the outcome passed, the process failed. Next time the coder is wrong, the same broken process ships a bug. If your eval only checks the final artifact, you have no early warning. **Evaluate the process, not just the product.**

**2. Failures are systemic, not local.** In the largest empirical study of this to date, Cemri et al. found that most multi-agent failures are *not* "the LLM is dumb" — they are failures of **system design, inter-agent alignment, and verification** ([Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", 2025](https://arxiv.org/abs/2503.13657)). Swapping in a stronger base model often does not fix them, because the fault lives in the *interaction*, not in any single agent's head. This is the single most counterintuitive fact in the field: you can upgrade every agent to a frontier model and watch the same failure recur, because no agent was ever the problem.

**3. Attribution is the whole game.** In a single-agent trace, blame is trivial — there is one agent. In a multi-agent trace, a wrong final answer might trace back to a planner that under-specified the task 12 steps ago, which no downstream agent could have recovered from. The core new skill of multi-agent evaluation is **credit assignment**: mapping a system-level outcome back to the agent and step responsible for it. Everything hard about this chapter is a consequence of this one problem being genuinely unsolved in general.

Everything below is in service of those three ideas.

A fourth idea worth holding loosely, because it frames the whole architectural debate: **agents are stateful, and in a stateful system errors compound.** A single wrong assumption early in a trajectory is not a one-time cost — it is a premise that every later step inherits and builds on. Anthropic put it bluntly: agents are stateful and errors compound, so minor issues that traditional software shrugs off can derail an agent run. That is why verification and containment (not just capability) dominate multi-agent reliability.

> **Saying it out loud.** Three ideas carry the whole chapter. First, the system is the unit of analysis, not the agent — you can have every agent behave correctly by its own contract and still ship a wrong answer. Second, and this is the counterintuitive one, failures are systemic rather than local: Cemri et al.'s study of 200-plus real traces found most multi-agent failures come from specification, inter-agent alignment, and verification, not from any agent being dumb — so you can upgrade every agent to a frontier model and watch the exact same failure recur. Third, attribution is the whole game: a wrong final answer might trace back to a planner that under-specified the task twelve steps earlier, and mapping outcomes back to the responsible agent and step is the genuinely new skill here — and it's unsolved in general.

---
## The 2025–2026 Landscape

You will be asked, in some form, "what does the field actually look like right now?" Here is the map: the frameworks people build on, the research that named the failure modes, the production writeup everyone cites, and the architectural debate that is still unresolved. Dates and links are real; verify them yourself before quoting them in an interview.

### The frameworks people actually build on

Five stacks dominate multi-agent construction in 2025–2026. You do not need to master all of them, but you must be able to say what each one *is* and what evaluation surface it exposes.

| Framework | Origin / status | Coordination model | What it hands your evaluator |
|---|---|---|---|
| **AutoGen / AG2** | Microsoft Research (2023); rewritten as **AutoGen v0.4** (Jan 2025, async actor-model core); the original creators maintain the community fork **AG2** | Conversable agents exchanging messages; `GroupChat` with a manager; event-driven | Full message transcripts between named agents — ideal for role-adherence and communication scoring |
| **CrewAI** | Independent company; popular since 2024 | Role/goal/backstory "crews"; sequential or hierarchical process; **Flows** add deterministic, event-driven orchestration | Explicit roles and a manager agent — a clean surface for role-violation and delegation metrics |
| **LangGraph** | LangChain (2024) | Directed graph of nodes/edges over an **explicit shared state**; checkpointing, human-in-the-loop, `supervisor` and `swarm` prebuilts | The state object and graph edges are first-class — the best surface for trajectory tracing and credit assignment |
| **OpenAI Agents SDK** | Successor to the experimental **Swarm** (Oct 2024); Agents SDK shipped as OpenAI's production framework in **March 2025** | Lightweight `Agent`s that **hand off** to one another; built-in guardrails, sessions, and tracing | Handoff events and a built-in trace viewer — coordination and handoff-correctness fall out for free |
| **Google ADK + A2A** | **Agent Development Kit** and the **Agent2Agent (A2A)** protocol both announced at Google Cloud Next, **April 2025**; A2A donated to the **Linux Foundation in June 2025** | Code-first, model-agnostic agents; A2A lets agents from *different vendors and frameworks* discover and call each other via **Agent Cards** | Cross-framework, cross-vendor call logs — the surface for evaluating *interoperable* agent ecosystems |

Two structural points an interviewer will reward you for making. First, **AutoGen/AG2, CrewAI, and LangGraph are orchestration frameworks** — they run agents *inside one process/organization*. **A2A is an interoperability protocol** — it standardizes how agents *across* organizations talk, the way HTTP standardized how servers talk, and it is complementary to MCP (which standardizes how an agent talks to *tools*, not to other agents). Second, **the framework you choose changes what you can evaluate.** LangGraph's explicit state object makes trajectory replay and per-node credit assignment natural; a framework that hides the transcript forces you to reconstruct it from logs before you can score coordination at all. **Choose the framework partly for its observability.**

- AutoGen — [microsoft.github.io/autogen](https://microsoft.github.io/autogen/); AG2 — [docs.ag2.ai](https://docs.ag2.ai/). Microsoft's generalist multi-agent reference, **Magentic-One** (Nov 2024), pairs an Orchestrator with WebSurfer, FileSurfer, Coder, and Terminal agents and is a good concrete example to name ([Magentic-One](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/)).
- CrewAI — [docs.crewai.com](https://docs.crewai.com/).
- LangGraph — [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/).
- OpenAI Agents SDK — [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/); the archived Swarm — [github.com/openai/swarm](https://github.com/openai/swarm).
- Google ADK — [google.github.io/adk-docs](https://google.github.io/adk-docs/); A2A — [a2a-protocol.org](https://a2a-protocol.org/) and the [Linux Foundation A2A project](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents).

> **Saying it out loud.** The frameworks matter to evaluation mostly because of what they expose. LangGraph gives you explicit shared state and a graph, which is the cleanest surface for tracing and for adding a verifier node with reject authority. CrewAI gives you named roles and a manager, which makes role-violation and delegation metrics almost free. AutoGen gives you full conversational transcripts. OpenAI's Agents SDK gives you handoffs with built-in tracing. The thing I'd say in an interview is that framework choice is largely an *observability* decision — if your framework doesn't emit a structured transcript with sender, recipient, and tool calls, you cannot do credit assignment at all, and no metric downstream will save you.

### The research that named the failure modes: MAST

Before 2025 there was no shared vocabulary for *how* multi-agent systems fail. Cemri et al.'s **MAST — Multi-Agent System failure Taxonomy** — supplied one, and it is now the standard reference. The authors hand-annotated 200+ execution traces across seven frameworks (MetaGPT, ChatDev, HyperAgent, AppWorld, AG2, Magentic-One, OpenManus), clustered the failures into **14 modes under 3 categories**, and — crucially — validated the taxonomy by training an LLM judge to apply it, reaching strong inter-annotator agreement (Cohen's kappa around 0.88) ([arXiv:2503.13657](https://arxiv.org/abs/2503.13657)). The headline finding is the one from Core Intuition #2: the failures are dominated by *specification, coordination, and verification* problems, not by any single agent's raw capability. We use MAST as the spine of the taxonomy section below.

> **Saying it out loud.** Before 2025 there was no shared vocabulary for how multi-agent systems fail, and MAST supplied one. The method matters as much as the result: they hand-annotated over 200 real execution traces across seven frameworks, clustered the failures into fourteen modes under three categories, and then validated the taxonomy by training an LLM judge to apply it, hitting a Cohen's kappa around 0.88. That's the template for any serious trajectory eval — validate on humans first, then scale with the judge. And the headline finding is the one to memorize: the failures are dominated by specification, coordination, and verification problems, not by raw model capability.

### The production writeup everyone cites: Anthropic's research system

Anthropic's ["How we built our multi-agent research system"](https://www.anthropic.com/engineering/multi-agent-research-system) (June 2025) is the most-cited real-world account and worth reading end to end. The load-bearing facts to memorize:

- **Architecture:** an **orchestrator-worker** pattern. A lead agent (Claude Opus 4) plans and spawns specialized subagents (Claude Sonnet 4) that search in parallel, each with its own context window, then synthesizes their findings.
- **The win:** the multi-agent system outperformed a single-agent Claude Opus 4 by **90.2%** on their internal research eval.
- **The cost:** ~**15x** the tokens of a chat interaction; **token budget explained ~80% of performance variance**. Multi-agent "wins" largely by spending more tokens searching more places at once.
- **How they evaluate it:** **end-state / outcome** evaluation with an **LLM judge** grading against a rubric (factual accuracy, citation quality, completeness, source quality), because "there are often multiple valid paths" to a good research answer. They started small — on the order of ~20 representative test cases — rather than waiting for a big benchmark, and they kept **humans in the loop** to catch failure modes (e.g., subtle source-quality problems) the automated judge missed.
- **The operational lessons:** agents are stateful and errors compound; they used **rainbow deployments** to update agents without disrupting in-flight runs; and prompt-engineering the *orchestrator's delegation* (clear task boundaries per subagent) mattered more than tuning the subagents.

> **Saying it out loud.** This is the reference production writeup, and I'd flag up front that the numbers are vendor-published on an internal eval, not an independent benchmark. The claimed win is that the multi-agent system beat single-agent Claude Opus 4 by 90.2% on their internal research eval. The cost is roughly 15x chat tokens, and — this is the part people skip — token budget alone explained about 80% of the performance variance. So the honest reading is that the comparison isn't token-matched: a large part of the win is that the multi-agent system was allowed to spend far more. Which is exactly why your own eval needs a single-agent baseline given a comparable budget before you conclude the architecture is what helped.

### The debate: does multi-agent actually beat single-agent?

This is the part interviewers use to separate people who have read a blog post from people who have built systems. There is a genuine, unresolved disagreement.

**The skeptic case — Cognition, ["Don't Build Multi-Agents"](https://cognition.com/blog/dont-build-multi-agents) (Walden Yan, June 2025).** Building Devin (an autonomous coding agent), Cognition found parallel subagents unreliable for *write-heavy* work. Their argument distills to two principles of context engineering: **(1) share full context** — every agent should see the whole trajectory, not a compressed summary — and **(2) actions carry implicit decisions**, so when two subagents act in parallel they make *conflicting* implicit decisions that cannot be reconciled after the fact. Their now-famous example: ask parallel subagents to build a Flappy Bird clone and one renders a bird in one visual style while another builds pipes in a clashing style — each subagent silently assumed a different aesthetic, and there is no clean merge. Their prescription: a **single-threaded, linear agent** with aggressive context management, and if the context grows too large, a dedicated model to *compress* the trajectory rather than *fork* it. The slogan people took away is the **"single writer"** principle — one agent owns the mutable state.

**The advocate case — Anthropic, above.** For *read-heavy, breadth-first* work (research: explore many independent sources, no shared mutable artifact), parallel subagents with separate context windows are exactly right — they multiply the effective context and search bandwidth, and the lack of a shared artifact means there is nothing to merge and therefore no conflicting-decisions problem.

**The reconciliation (say this).** They are not actually contradicting each other; they are describing different *task shapes*. The deciding variable is whether the subtasks **share a mutable artifact / evolving decision state**:

- **Read-heavy, decomposable, no shared writes** (research, breadth-first search, gathering evidence): multi-agent wins — parallelism buys real coverage and the subagents' outputs *concatenate* rather than *conflict*.
- **Write-heavy, tightly coupled, shared evolving state** (coding a single artifact, editing one document): single-agent (or a strictly serialized single-writer) wins — parallel writers make irreconcilable implicit decisions, exactly Cognition's failure.

Both camps agree on the deeper point: **context engineering is the real work.** Multi-agent is one tool for managing context (give each subagent a clean window); linear-agent-plus-compression is another. The architecture is downstream of the task's read/write structure, and your evaluation must *measure* which one is actually winning on your task — which is why a single-agent baseline is non-negotiable (see "When Is It Worth It?").

> **Saying it out loud.** There's a live public disagreement here and the reconciliation is the answer. Cognition's "Don't Build Multi-Agents" says parallel subagents make conflicting implicit decisions — their example is subagents building a Flappy Bird clone where one renders the bird in one style and another builds pipes in a clashing one, and there's no clean merge — so prefer a single linear agent with aggressive context management, one writer owning the mutable state. Anthropic says the opposite for research. Both are right in their regime, and the deciding variable is whether the subtasks share a mutable artifact: read-heavy breadth-first work with nothing to merge favors multi-agent, write-heavy tightly-coupled work favors a single agent. The caveat I'd add is that the headline multi-agent wins usually aren't token-matched — when you equalize the budget, multi-agent frequently *underperforms* a single agent — and agents sharing a base model aren't independent verifiers, they're correlated ones, so a committee of them agreeing is much weaker evidence than it looks.

---
## What to Evaluate

A complete multi-agent evaluation covers seven dimensions. Outcome alone is table stakes; the other six are what distinguish a multi-agent eval from a single-agent one.

| Dimension | Question it answers | Example signal |
|---|---|---|
| **Task outcome** | Did the system achieve the goal? | Final answer correct; end-state matches spec |
| **Communication effectiveness** | Do messages carry the right information, understood correctly? | Key facts propagate; no ignored/misread messages |
| **Coordination / orchestration** | Is work routed to the right agent, in the right order, without redundancy? | No duplicated work; no idle agents; correct handoffs |
| **Role adherence** | Does each agent stay within its assigned role? | Reviewer reviews (doesn't rewrite); planner plans (doesn't code) |
| **Credit assignment** | Which agent/step caused success or failure? | Blame localized to a specific message |
| **Robustness** | Does the system contain errors or amplify them? | One agent's mistake gets caught, not propagated |
| **Cost / efficiency** | Is the outcome worth the tokens, latency, and dollars? | Quality gain per extra token vs single-agent baseline |

A useful mental model: **task outcome is the *what*; the middle five are the *how*; cost is the *whether it was worth it*.** A mature eval scores all three. A common mistake is to build an elaborate rubric for the *what*, nothing for the *how*, and to leave cost off the dashboard entirely — which is precisely how teams end up shipping an expensive system whose overhead they cannot justify when a director asks.

**Map each dimension to a MAST category.** The seven dimensions are not arbitrary — each one is the *detector* for a family of failures in the taxonomy below. Communication effectiveness catches "ignored other agents' input" and "withholding crucial information" (FC2). Role adherence catches "disobey role specification" (FC1). Robustness catches cascading errors and "incorrect verification" (FC3). If you cannot say which failure mode a metric is supposed to catch, that metric is decoration.

> **Saying it out loud.** A complete multi-agent eval covers seven dimensions, and outcome is only the first one. Task outcome is the *what*. Then five process dimensions are the *how* — communication effectiveness, coordination, role adherence, credit assignment, and robustness. And cost is the *whether it was worth it*. The rule that keeps this from being a laundry list: every metric has to name the failure mode it's supposed to catch, or it's decoration. Communication effectiveness catches withheld information and ignored messages; role adherence catches the reviewer who starts rewriting code; robustness catches cascades. And the classic mistake is an elaborate rubric for the *what*, nothing for the *how*, and cost left off the dashboard entirely — which is exactly how you end up unable to justify a 15x bill when a director asks.

### End-state vs step-by-step evaluation

Two philosophies for scoring outcome and process:

- **End-state evaluation** checks only whether the system reached a correct final state, tolerating many valid paths to get there. Anthropic uses this for its research system precisely because "there are often multiple valid paths" to a good research answer ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). It is cheap and path-agnostic but blind to lucky-right processes.
- **Trajectory / step evaluation** scores the sequence of actions and messages. It catches process failures and enables credit assignment but is expensive and requires reference trajectories or a strong judge.

Use end-state for headline pass/fail and trajectory scoring for diagnosis. They answer different questions; you generally want both. A practical division of labor: run **end-state on every case, every run** (cheap enough for CI), and run **trajectory scoring only on the failures** end-state flags (expensive, so spend it where the signal is). This "cheap filter, expensive diagnosis" split is how you keep a trajectory eval affordable at scale.

A subtle trap lives in end-state evaluation for multi-agent systems specifically: **a correct end state can be reached by a process so wasteful or so lucky that it will not reproduce.** Two subagents duplicating the same research still produce a correct report — end-state passes, and you have quietly paid double and learned nothing. This is why cost must ride alongside the end-state score, not in a separate report nobody opens.

> **Saying it out loud.** Two philosophies, and you want both for different jobs. End-state evaluation checks only whether the system reached a correct final state, tolerating many valid paths — Anthropic uses it for research precisely because there are lots of good ways to answer a research question. Trajectory evaluation scores the actual sequence of messages and actions, which is what enables credit assignment, but it's expensive. The practical split is: run end-state on every case every run because it's cheap enough for CI, and spend trajectory scoring only on the cases end-state flagged as failures. And the trap specific to multi-agent: a correct end state can come from a process so wasteful it doesn't reproduce — two subagents duplicating the same research still produce a correct report, end-state passes, and you quietly paid twice.

---

## The Credit-Assignment Problem in Depth

Credit assignment is the problem of attributing a system-level outcome to the individual agents and steps that produced it. It is borrowed from reinforcement learning (the "temporal credit assignment problem": which of the many actions in an episode deserves credit for the eventual reward?) and it is *the* hard problem of multi-agent evaluation.

**The 60-second version (memorize this).** In a system of many agents that pass work to each other, a single system-level score — "the report was wrong" — has to be distributed back over dozens of messages from several agents. That is credit assignment. It is hard for four reasons: the decisive mistake often happened *long before* the visible failure (delayed effect); when several agents each contribute a slice of a bad answer *no single message is the bug* (diffuse responsibility); "agent B caused it" is really a *counterfactual* — "had B acted differently the outcome would improve" — which you usually cannot run; and agents that are each individually correct can be *jointly* wrong (interaction effects). The practical toolkit is four methods trading off cost against rigor: trace localization, leave-one-out ablation, Shapley values, and milestone KPIs.

> **Saying it out loud.** Credit assignment is pushing one system-level score — "the report was wrong" — back onto the dozens of messages from several agents that produced it. It's borrowed from reinforcement learning's temporal credit assignment problem, and it's the hard problem of this whole field. Four things make it hard: the decisive mistake usually happened long before the visible failure, responsibility is often diffuse so no single message is *the* bug, "agent B caused it" is really a counterfactual you can't run, and agents that are each individually correct can be jointly wrong. The toolkit is four methods trading cost against rigor — trace localization, leave-one-out ablation, Shapley values, and milestone KPIs — and the discipline that matters most is blaming the *first unrecoverable* error rather than the last visible symptom.

### Why it is hard

- **Delayed effect.** The decision that doomed the run often happened long before the visible failure. A planner that omitted a constraint on step 2 causes a spec violation on step 20; the coder who "produced" the wrong output is not the culprit.
- **Diffuse responsibility.** When five agents each contribute 20% of a flawed argument, no single message is "the bug." Groupthink failures have no localizable owner.
- **Counterfactual ambiguity.** "Agent B caused the failure" really means "had B acted differently, the outcome would have been better." Establishing that requires a counterfactual you usually cannot run.
- **Interaction effects.** Two agents can each be individually correct yet jointly wrong (e.g., both assume the other will handle error-checking).

> **Saying it out loud.** Four reasons, and they're worth being able to list cold. Delayed effect — the planner that omitted a constraint at step two causes the spec violation at step twenty, and the coder who "produced" the wrong output isn't the culprit. Diffuse responsibility — when five agents each contribute twenty percent of a flawed argument, there's no single bug to point at, which is exactly why groupthink failures have no localizable owner. Counterfactual ambiguity — "B caused it" means "had B acted differently the outcome would improve," and you usually can't run that experiment. And interaction effects — two agents can each be individually correct and jointly wrong, like both assuming the other handles error checking.

### Four practical attribution methods

Four ways to answer "which agent gets the blame," from cheapest to most rigorous: read the trace and mark the decisive step; remove an agent and see if the score moves; compute Shapley values over every subset of agents; or check which agent hit which predefined milestone.

**1. Trace-based localization (annotate the decisive step).** Have a human or LLM judge read the full transcript and mark the *first* step where the trajectory became unrecoverable — the "decisive error." This is exactly the methodology behind MAST: expert annotators labeled traces for failure modes and the step at which each occurred, reaching Cohen's kappa = 0.88 inter-annotator agreement ([Cemri et al., 2025](https://arxiv.org/abs/2503.13657)). Cheap-ish, interpretable, but subjective and hard to scale without an LLM judge. The key discipline is finding the *first* unrecoverable error, not the last visible symptom — those are usually different messages authored by different agents, and blaming the symptom is how teams "fix" the wrong agent.

**2. Ablation / leave-one-out.** Re-run the task with agent \\( i \\) removed (or replaced by a no-op / a stronger model / a weaker model). The change in system performance estimates that agent's marginal contribution:

\\[ \Delta_i = V(\text{system}) - V(\text{system} \setminus i) \\]

where \\( V \\) is your outcome score. Large positive \\( \Delta_i \\) means agent \\( i \\) is load-bearing; \\( \Delta_i \approx 0 \\) means it is dead weight (a candidate for deletion — cost savings!); and, importantly, a **negative** \\( \Delta_i \\) means the agent is *actively harmful* — the system scores *better* without it, which is more common than teams expect for redundant reviewers and over-eager planners. Requires re-running, which multiplies cost, and — because these systems are non-deterministic — you must average \\( \Delta_i \\) over several seeds or you are measuring noise.

**3. Shapley-value attribution.** Leave-one-out ignores interactions. The Shapley value fairly distributes the total system value across agents by averaging each agent's marginal contribution over *all* orderings of agent inclusion:

\\[ \phi_i = \sum_{S \subseteq N \setminus \\{i\\}} \frac{|S|!\\,(|N|-|S|-1)!}{|N|!} \big[ V(S \cup \\{i\\}) - V(S) \big] \\]

Here \\( N \\) is the set of agents, \\( S \\) a coalition not containing \\( i \\), and \\( V(S) \\) the score achieved by only the agents in \\( S \\). Shapley values are the principled answer to "how much did each agent contribute" — they uniquely satisfy efficiency, symmetry, null-player, and additivity — but they cost \\( O(2^{|N|}) \\) coalition evaluations, so feasible for 3–4 agents, not for 30. For larger systems you approximate with **Monte-Carlo Shapley** (sample random agent orderings and average marginal contributions), trading exactness for a tractable number of re-runs.

**4. Milestone / process rewards.** Decompose the task into intermediate milestones and check which agent achieved which. MultiAgentBench uses exactly this: **milestone-based KPIs** that score whether key sub-goals were reached, separating collaboration quality from raw task score ([Zhu et al., "MultiAgentBench", 2025](https://arxiv.org/abs/2503.01935)). This gives per-agent, per-milestone credit without combinatorial re-runs, at the cost of needing hand-authored milestones. It is the only one of the four that scales to production volume, which is why it is the workhorse for routine per-agent scoring.

**Rule of thumb:** use trace-based localization for debugging a specific failure, milestone KPIs for routine per-agent scoring, leave-one-out for pruning agents, and Shapley only when you have ≤4 agents and need defensible attribution. In practice these compose: milestone KPIs run continuously and flag *which* agent is under-contributing; trace localization then explains *why* on a sampled failure; leave-one-out confirms the fix by showing the score moves when you change that agent.

> **Saying it out loud.** Rule of thumb for which method when. Trace localization — a human or judge marks the first step where the run became unrecoverable — is what you use to debug one specific failure; it's the MAST methodology and it's interpretable but subjective. Leave-one-out ablation, rerunning with an agent removed, is what you use to prune agents — and watch for a *negative* delta, meaning the system scores better without that agent, which is more common than teams expect for redundant reviewers. Shapley values are the principled answer because they handle interactions leave-one-out misses, but they cost two-to-the-N coalition evaluations, so realistically four agents or fewer. And milestone KPIs are the only one that scales to production volume, which is why they're the workhorse for routine scoring. The catch across all of them: these systems are non-deterministic, so a delta measured on a single seed is noise, not attribution.

---
## A Taxonomy of Multi-Agent Failure Modes

The most useful empirical map here is **MAST (Multi-Agent System failure Taxonomy)** from Cemri et al., built by annotating 200+ execution traces across seven frameworks (MetaGPT, ChatDev, HyperAgent, AppWorld, AG2, Magentic-One, OpenManus) and clustering into **14 failure modes under 3 categories** ([arXiv:2503.13657](https://arxiv.org/abs/2503.13657)). The percentages below are the approximate share of failures each category accounted for in their study. Treat them as an order-of-magnitude map of where to spend your defenses, not as universal constants — your distribution will differ by task, but the striking result that *specification and coordination dominate raw capability* holds broadly.

> **Saying it out loud.** MAST breaks fourteen failure modes into three buckets, and the split is roughly 42% specification and system design, 37% inter-agent misalignment, 21% verification and termination. Treat those percentages as an order-of-magnitude map of where to spend your defenses rather than universal constants — your distribution will differ by task. But the striking result holds broadly: specification and coordination dominate raw capability. That means the highest-leverage fix is usually structural — clearer roles, tighter handoffs, a mandatory verification step — and *not* waiting for a smarter base model, because the fault lives in the interaction, not in any agent's head.

### FC1 — Specification & System-Design Issues (~42% of failures)

The system is poorly specified or structured before any conversation goes wrong. These are the "you built it wrong," not "it ran wrong," failures — and because they are baked into the prompts, roles, and topology, they are the ones a stronger base model is *least* able to rescue.

| Mode | What it looks like | Where your eval catches it |
|---|---|---|
| Fail to follow task requirements | System ignores an explicit constraint from the prompt | Outcome check against the spec's constraints, not just the goal |
| Disobey role specification | Reviewer starts writing code; planner starts executing | Role-adherence metric (forbidden-action detector) |
| Step repetition | Agents redo work already completed | Redundancy rate over (sender, content) |
| Loss of conversation history | Context is dropped; an agent "forgets" an earlier decision | Fact-propagation check across the transcript |
| Unaware of stopping conditions | No agent knows when the task is done | Termination check: did it stop at goal, or run out / loop? |

> **Saying it out loud.** This is the biggest bucket and it's the "you built it wrong" category, not the "it ran wrong" one. The system ignores an explicit constraint, or the reviewer starts writing code instead of reviewing, or agents redo work that's already done, or context gets dropped so an agent forgets an earlier decision, or nobody knows when the task is finished. These are baked into the prompts, the roles, and the topology before any conversation happens — which is precisely why a stronger base model is *least* able to rescue them. Forty-two percent of failures being design errors is the single strongest argument for spending your time on the spec rather than on the model.

### FC2 — Inter-Agent Misalignment (~37% of failures)

The agents are individually capable but fail to align with each other. This is the category with no single-agent analogue at all — it exists *only* because there is more than one agent.

| Mode | What it looks like | Where your eval catches it |
|---|---|---|
| Conversation reset | Dialogue unexpectedly restarts, discarding progress | Progress-monotonicity check on milestone coverage |
| Proceeding on wrong assumptions | An agent guesses instead of asking a clarifying question | Assumption audit; provenance check on inputs |
| Task derailment | Conversation drifts off the original objective | Goal-drift score (semantic distance from original goal) |
| Withholding crucial information | An agent knows something relevant but never shares it | Information-flow / communication-effectiveness metric |
| Ignoring other agents' input | A message is received and simply not acted on | Ignored-message rate (directed message, no downstream use) |
| Reasoning–action mismatch | Agent says one thing, does another | Consistency check between stated intent and tool call |

> **Saying it out loud.** This is the category with no single-agent analogue at all — it exists only because there's more than one agent. The agents are individually capable and still fail to align: one proceeds on a guess instead of asking a clarifying question, one knows something relevant and never shares it, one receives a message and simply doesn't act on it, the conversation drifts off the original objective, or an agent says one thing and does another. Each of these maps to a specific detector — an assumption audit, an information-flow metric, an ignored-message rate, a goal-drift score, a stated-intent-versus-tool-call consistency check. If your eval has no metric in this family, you are blind to more than a third of your failures.

### FC3 — Task Verification & Termination (~21% of failures)

The system fails to check its own work. Small as a percentage, this category is disproportionately dangerous because it is the *last line of defense* — an FC3 failure is what lets an FC1 or FC2 error reach the user unchallenged.

| Mode | What it looks like | Where your eval catches it |
|---|---|---|
| Premature termination | System stops before the goal is met | Milestone coverage < 1.0 at termination |
| No / incomplete verification | Output is never checked against requirements | Presence + coverage of a verification step |
| Incorrect verification | The checker approves a wrong answer | Verifier accuracy (does "approved" correlate with actually correct?) |

> **Saying it out loud.** Smallest bucket, disproportionately dangerous, because this is the last line of defense — an FC3 failure is what lets an FC1 or FC2 error reach the user unchallenged. Three shapes: stopping before the goal is met, never checking the output against the requirements at all, and the nastiest one, a checker that approves a wrong answer. That last one is worse than having no verifier, because it manufactures false confidence. So the metric that matters isn't "is there a verification step," it's *verifier accuracy* — does "approved" actually correlate with correct? A reviewer that rubber-stamps has coverage of 100% and discrimination of zero.

### Cross-cutting emergent failures

Some failures are not single modes but *dynamics* over the interaction graph. These are the ones single-agent evaluation has no vocabulary for:

- **Cascading errors / error propagation.** Agent A's small mistake becomes agent B's premise, which B builds on confidently, and so on. The error is *amplified* rather than *contained*. A robust system has a verification agent that breaks the chain (FC3 is where this defense lives or dies). The diagnostic signature is a low-confidence or wrong assertion early in the trace that later messages cite *without re-deriving*.
- **Groupthink / sycophantic convergence.** In debate or committee setups, agents converge on a confident consensus that is wrong, because each defers to the apparent majority instead of reasoning independently. Multi-agent debate can *improve* factuality when agents genuinely critique ([Du et al., "Improving Factuality and Reasoning through Multiagent Debate", 2023](https://arxiv.org/abs/2305.14325)) — but the same setup degrades into mutual agreement when critique collapses. The tell is *falling* disagreement across rounds coupled with *rising* confidence — unanimity reached too early is a red flag, not a green one.
- **Deadlock / livelock.** A waits for B, B waits for A (deadlock); or agents keep politely handing the task back and forth without progress (livelock). Both surface as "unaware of stopping conditions" plus "step repetition," and both are caught by a turn/step budget with a progress check.
- **Redundant work / cost blowup.** Two subagents independently research the same subtopic. The outcome may still be correct, but you paid twice — a *coordination* failure visible only in the cost dimension, which is exactly why cost is one of the seven evaluation dimensions and not an afterthought.

**Worked micro-example of error propagation.** A planner instructs: "compute revenue for Q3." The data agent silently uses Q2 data (wrong assumption, FC2). The analyst computes a beautiful, correct-looking growth rate on the wrong numbers. The reviewer checks the *arithmetic* (correct) but not the *data source* (incomplete verification, FC3). Final answer: confidently wrong. No single agent was "broken"; the *system* had no data-provenance check. This is why MAST's authors stress that better *base models alone do not fix* these failures — the fix is structural: add a provenance assertion to the data agent's contract and make source-checking an explicit item on the reviewer's checklist. Notice the failure required **two** modes to line up (FC2 wrong assumption + FC3 incomplete verification) — robust systems fail only when a defense *and* its backstop both miss, which is the whole argument for a dedicated verifier.

> **Saying it out loud.** Some failures aren't single modes, they're dynamics over the interaction graph, and single-agent evaluation has no vocabulary for them. Cascading errors, where A's small mistake becomes B's premise and gets amplified rather than contained — the diagnostic signature is an early shaky assertion that later messages cite without ever re-deriving. Groupthink, where a debate setup collapses into mutual agreement; debate genuinely improves factuality when the critique is real, but the tell that it's degraded is falling disagreement across rounds coupled with rising confidence, so early unanimity is a red flag, not a green one. Deadlock and livelock, caught by a step budget plus a progress check. And redundant work, where two subagents research the same subtopic — the answer is still correct, you just paid twice, which is a coordination failure visible only in the cost dimension.

### How to use the taxonomy in an eval

Turn MAST into a **checklist judge**. For each transcript, an LLM judge (or human) answers a yes/no question per failure mode ("Did any agent proceed on an unstated assumption? cite the message"), and you aggregate the rate of each mode across your eval set. Now your dashboard shows not just "68% pass" but "of the 32% that failed, 40% were incomplete-verification and 25% were wrong-assumption" — which tells you *what to build next* (a verifier, a clarify-first policy). This is the difference between an eval that scores and an eval that *directs engineering*.

> **Saying it out loud.** Turn the taxonomy into a checklist judge. For each transcript, a judge answers one yes-or-no question per failure mode — "did any agent proceed on an unstated assumption? cite the message" — and you aggregate the rate of each mode across the eval set. Now your dashboard doesn't say "68% pass," it says "of the 32% that failed, 40% were incomplete verification and 25% were wrong assumption." That second version tells you what to build next: a verifier, and a clarify-before-acting policy. That's the difference between an eval that scores and an eval that directs engineering.

---
## Build It in Practice

Reading about orchestrator-worker systems is not the same as building one. This section builds a realistic research system — a lead orchestrator that decomposes a query and spawns parallel workers, plus a synthesizer — first in **LangGraph** (how you would ship it), then as a **self-contained runnable harness** (stdlib only, no API keys) that generates an instrumented transcript and computes task success, per-agent credit via *empirical leave-one-out*, and a coordination metric. Together with the scorer in the next section, this is a complete evaluation loop you can lift into a real codebase.

### B.1 — The architecture, in LangGraph

The canonical multi-agent shape — and the one Anthropic's research system uses — is **orchestrator-worker**: a lead agent plans, dynamically fans out to specialized workers (each with its own context window), then a synthesizer merges their findings. LangGraph expresses the dynamic fan-out with its `Send` API, which lets the orchestrator emit one worker invocation per subtask at run time (the number of workers is not known until the orchestrator plans). This is real, current LangGraph; it requires `pip install langgraph langchain` and a chat model.

```python
"""Orchestrator-worker research system in LangGraph (fan-out with Send)."""
import operator
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langchain.chat_models import init_chat_model

llm = init_chat_model("anthropic:claude-sonnet-4-20250514")  # any chat model


# ---- Shared graph state. `findings` uses operator.add so parallel workers
#      APPEND rather than overwrite each other (a map-reduce reducer). ----
class State(TypedDict):
    topic: str
    subtasks: list[str]
    findings: Annotated[list, operator.add]   # reducer: concatenate
    report: str


class WorkerState(TypedDict):
    subtask: str
    findings: Annotated[list, operator.add]


def orchestrator(state: State) -> dict:
    """Lead agent: decompose the topic into independent, parallelizable subtasks."""
    prompt = (
        f"Break this research topic into 3-5 INDEPENDENT subtopics that can be "
        f"researched in parallel without shared decisions. Topic: {state['topic']}. "
        f"Return one subtopic per line."
    )
    resp = llm.invoke(prompt).content
    subtasks = [ln.strip("-* ").strip() for ln in resp.splitlines() if ln.strip()]
    return {"subtasks": subtasks}


def assign_workers(state: State):
    """Conditional edge: fan out one worker per subtask via the Send API."""
    return [Send("worker", {"subtask": s}) for s in state["subtasks"]]


def worker(state: WorkerState) -> dict:
    """Specialized subagent: researches ONE subtask in its own context window."""
    resp = llm.invoke(f"Research this and report key findings concisely: {state['subtask']}")
    return {"findings": [{"subtask": state["subtask"], "text": resp.content}]}


def synthesizer(state: State) -> dict:
    """Lead agent: merge worker findings into a single cited report."""
    bundle = "\n\n".join(f"## {f['subtask']}\n{f['text']}" for f in state["findings"])
    resp = llm.invoke(f"Synthesize these findings into a report:\n\n{bundle}")
    return {"report": resp.content}


builder = StateGraph(State)
builder.add_node("orchestrator", orchestrator)
builder.add_node("worker", worker)
builder.add_node("synthesizer", synthesizer)
builder.add_edge(START, "orchestrator")
builder.add_conditional_edges("orchestrator", assign_workers, ["worker"])
builder.add_edge("worker", "synthesizer")
builder.add_edge("synthesizer", END)
graph = builder.compile()

# result = graph.invoke({"topic": "Impact of A2A protocol on enterprise agent adoption"})
# print(result["report"])
```

Three design choices in that code are exactly the things your evaluation will later scrutinize. **(1) The orchestrator's decomposition prompt demands *independent* subtasks** — this is the read-heavy / no-shared-writes regime where multi-agent wins; if the subtasks secretly share a decision (Cognition's Flappy Bird trap) the `operator.add` merge will concatenate *conflicting* findings and the synthesizer will have to paper over them. **(2) Each worker gets its own context window** — that is the entire point of the pattern (multiply effective context), and it is why per-agent credit is even meaningful. **(3) The synthesizer is a single writer** — there is exactly one agent that produces the final artifact, honoring the single-writer principle even inside a multi-agent system.

> **Saying it out loud.** Three design choices in that code are exactly what your eval will later scrutinize. The orchestrator's prompt demands *independent* subtasks, because that's the read-heavy regime where multi-agent actually wins — if the subtasks secretly share a decision, you fall straight into the Flappy Bird trap and the merge just concatenates conflicting findings for the synthesizer to paper over. Each worker gets its own context window, which is the entire point of the pattern and the reason per-agent credit is even meaningful. And the synthesizer is a single writer — exactly one agent produces the final artifact, honoring the single-writer principle even inside a multi-agent system. If you can only remember one, remember the last: parallel readers are fine, parallel writers are where it breaks.

### B.2 — Instrument first, or you cannot evaluate

You cannot score coordination from a final report. You need the **transcript**: an ordered, structured log of who did what, when, with what inputs and outputs, and how many tokens it cost. Add a thin event recorder to every node before you do anything else — this is the highest-leverage thing on this page.

```python
import time, json

class Recorder:
    """Append-only event log; one row per agent action. This IS your eval surface."""
    def __init__(self):
        self.events = []
    def log(self, agent, role, action, recipient, content, tokens, milestone=None):
        self.events.append({
            "step": len(self.events) + 1, "t": time.time(),
            "agent": agent, "role": role, "action": action,
            "recipient": recipient, "content": content,
            "tokens": tokens, "milestone": milestone,
        })
    def dump(self, path):
        with open(path, "w") as f:
            json.dump(self.events, f, indent=2)
```

Wrap each node so it calls `rec.log(...)` on entry and exit. In production you get this for free from a tracer — **LangSmith** (LangGraph), the OpenAI Agents SDK's built-in tracing, or **Langfuse** — which record the same structured spans. The rule: *if it did not get logged, it did not happen as far as your evaluation is concerned.*

> **Saying it out loud.** This is the unglamorous prerequisite: no structured transcript, no evaluation. Every message needs a sender, a recipient, a timestamp, the tool calls it made, the tokens it burned, and ideally the milestone it claims to complete. Without that, coordination metrics, credit assignment, and reproducing a failure are all impossible — you're left with vibes. And because these systems are non-deterministic, you also need the trace to be replayable, or a failure you saw once is a failure you can never study. Instrumentation is the cheapest thing in this chapter and the one whose absence blocks everything else.

### B.3 — A runnable end-to-end harness (stdlib only)

Below is a complete, dependency-free program that *simulates* the orchestrator-worker system with pluggable "agent" functions, records a transcript, scores the end state, and computes **empirical per-agent contribution by leave-one-out re-runs** — the ablation method from the credit-assignment section, actually executed. It runs as-is with `python3`. Swap the stubbed agent bodies for real `llm.invoke` calls and it becomes a real evaluator.

```python
"""Runnable orchestrator-worker simulation + leave-one-out credit assignment.
Pure standard library. Replace the stubbed agent functions with real LLM calls."""
from __future__ import annotations
from dataclasses import dataclass, field

# ---- Ground truth for a toy research task: the facts a good report must contain. ----
GOLD_FACTS = {
    "a2a_origin": "A2A was announced by Google in April 2025.",
    "a2a_lf": "A2A was donated to the Linux Foundation in June 2025.",
    "a2a_vs_mcp": "A2A connects agents to agents; MCP connects agents to tools.",
    "adk": "Google's ADK is a code-first framework that speaks A2A.",
}

# Which worker is responsible for which fact (its 'beat'). The orchestrator assigns these.
BEATS = {
    "history":   ["a2a_origin", "a2a_lf"],
    "protocols": ["a2a_vs_mcp"],
    "tooling":   ["adk"],
}


@dataclass
class Transcript:
    events: list = field(default_factory=list)
    def add(self, agent, action, facts=None, tokens=0):
        self.events.append({"step": len(self.events) + 1, "agent": agent,
                            "action": action, "facts": facts or [], "tokens": tokens})


def orchestrator(topic: str, active_workers: list[str], t: Transcript) -> list[str]:
    """Plans: assigns each active worker its beat. ~200 planning tokens."""
    plan = [w for w in active_workers if w in BEATS]
    t.add("orchestrator", f"plan:{topic}", tokens=200)
    return plan


def worker(name: str, t: Transcript) -> list[str]:
    """A subagent researches its beat and reports the facts it found. ~600 tokens."""
    found = list(BEATS.get(name, []))
    t.add(name, "research", facts=found, tokens=600)
    return found


def synthesizer(all_facts: list[str], t: Transcript) -> set[str]:
    """Single writer: merges worker findings into the report. ~400 tokens."""
    report_facts = set(all_facts)
    t.add("synthesizer", "write_report", facts=sorted(report_facts), tokens=400)
    return report_facts


def run_system(topic: str, active_workers: list[str]) -> tuple[set[str], Transcript]:
    """One full run of the orchestrator-worker system with a given worker set."""
    t = Transcript()
    plan = orchestrator(topic, active_workers, t)
    gathered: list[str] = []
    for w in plan:                       # (parallel in reality; sequential here)
        gathered += worker(w, t)
    report = synthesizer(gathered, t)
    return report, t


def end_state_score(report_facts: set[str]) -> float:
    """Outcome metric: fraction of gold facts present in the report."""
    return len(report_facts & set(GOLD_FACTS)) / len(GOLD_FACTS)


def leave_one_out_credit(topic: str, workers: list[str]) -> dict[str, float]:
    """Empirical marginal contribution: score with all workers minus score without w."""
    full_report, _ = run_system(topic, workers)
    full = end_state_score(full_report)
    credit = {}
    for w in workers:
        ablated = [x for x in workers if x != w]
        rep, _ = run_system(topic, ablated)
        credit[w] = round(full - end_state_score(rep), 3)   # Delta_i
    return full, credit


if __name__ == "__main__":
    workers = ["history", "protocols", "tooling"]
    report, tr = run_system("A2A protocol landscape", workers)
    print("END-STATE SCORE :", round(end_state_score(report), 3))
    total_tokens = sum(e["tokens"] for e in tr.events)
    print("TOKENS SPENT    :", total_tokens)
    full, credit = leave_one_out_credit("A2A protocol landscape", workers)
    print("LEAVE-ONE-OUT   :", credit)
```

Running it prints:

```
END-STATE SCORE : 1.0
TOKENS SPENT    : 1800
LEAVE-ONE-OUT   : {'history': 0.5, 'protocols': 0.25, 'tooling': 0.25}
```

Read the output like an evaluator. The **end-state score is 1.0** — all four gold facts made it into the report. The **leave-one-out credits are the empirical \\( \Delta_i \\)**: removing the `history` worker drops the score by 0.5 (it owned two of four facts), each of the others by 0.25 — so `history` is the most load-bearing worker, and none is dead weight. Now inject a failure to watch the metric bite: give the `history` worker a wrong assumption (have it research Q2 instead of Q3, i.e. `BEATS["history"] = []`) and its leave-one-out credit collapses to 0.0 while the end-state score falls to 0.5 — the ablation *localizes the damage to the agent that caused it* without any human reading the transcript. That is credit assignment, executed, in forty lines.

**What is deliberately missing, and why it matters.** This harness scores *outcome* and *contribution* but not *coordination* — it cannot see redundant work, role violations, or ignored messages, because those live in the transcript's structure, not in the fact set. That is exactly the job of the scorer in the next section, which consumes a transcript of the same shape and produces the coordination metrics. The two halves — this generator/ablator and that scorer — compose into a full evaluation harness.

> **Saying it out loud.** The harness does the one thing that makes a multi-agent claim credible: it runs the same task through the multi-agent system *and* a single-agent baseline, over multiple seeds, and reports both quality and cost. Multiple seeds is not optional — run-to-run variance in these systems is often larger than the effect you're trying to measure, so a single-run comparison is noise dressed as a result. Then leave-one-out on each agent tells you who's actually load-bearing. The number that usually surprises people the first time they run it is how often removing an agent leaves the score flat, which means you've been paying for a participant, not a contributor.

---
## Worked Example: Scoring a Multi-Agent Transcript

This is the second half of the harness. Where §B generated a transcript and did leave-one-out on *outcome*, this scorer reads a transcript and scores the **process** — task success (with milestone coverage), per-agent contribution (a milestone-based credit assignment complementary to §B's ablation), and a **coordination metric** (how cleanly work was routed and handed off). It uses only the standard library so it runs anywhere. The judging here is rule-based for reproducibility; in practice you would swap the milestone checks and role rules for an LLM-as-judge call driven by the MAST checklist from the taxonomy section.

```python
"""Score a multi-agent transcript: task success, per-agent contribution, coordination.

Transcript model: an ordered list of messages. Each message has a sender (agent id),
a recipient, textual content, and an optional 'milestone' it completes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class Message:
    step: int
    sender: str
    recipient: str            # "all" for broadcast
    content: str
    milestone: str | None = None   # id of a milestone this message completes, if any


@dataclass
class Task:
    goal: str
    milestones: list[str]                 # ordered sub-goals that define success
    roles: dict[str, str]                 # agent_id -> role name
    final_answer_correct: bool            # from an outcome checker / gold comparison


def task_success(task: Task, transcript: list[Message]) -> dict:
    """End-state success plus milestone coverage."""
    hit = {m.milestone for m in transcript if m.milestone is not None}
    covered = [m for m in task.milestones if m in hit]
    coverage = len(covered) / len(task.milestones) if task.milestones else 0.0
    # System 'passes' only if the final answer is correct AND all milestones were hit.
    passed = task.final_answer_correct and coverage == 1.0
    return {
        "final_answer_correct": task.final_answer_correct,
        "milestone_coverage": round(coverage, 3),
        "milestones_missed": [m for m in task.milestones if m not in hit],
        "passed": passed,
    }


def per_agent_contribution(task: Task, transcript: list[Message]) -> dict:
    """Milestone-based credit assignment: share of milestones each agent completed,
    weighted so that credit sums to 1.0 across all completed milestones."""
    completed = [m for m in transcript if m.milestone in task.milestones]
    total = len(completed)
    credit: dict[str, float] = defaultdict(float)
    counts: dict[str, int] = defaultdict(int)
    for m in completed:
        credit[m.sender] += 1.0 / total if total else 0.0
        counts[m.sender] += 1
    # Every agent that ever spoke should appear, even with zero credit (dead weight).
    for m in transcript:
        credit.setdefault(m.sender, 0.0)
    return {
        agent: {"credit_share": round(credit[agent], 3),
                "milestones_completed": counts.get(agent, 0)}
        for agent in sorted(credit)
    }


def coordination_score(task: Task, transcript: list[Message]) -> dict:
    """A composite coordination metric in [0, 1] combining three penalties:
       - redundancy: repeated identical (sender, content) work
       - role violations: an agent producing content outside its role's allowed verbs
       - ignored messages: a directed message that never gets a reply from its recipient
    Higher is better."""
    n = len(transcript)

    # 1) Redundancy: fraction of messages that duplicate earlier (sender, content).
    seen = set()
    redundant = 0
    for m in transcript:
        key = (m.sender, m.content.strip().lower())
        if key in seen:
            redundant += 1
        seen.add(key)
    redundancy_rate = redundant / n if n else 0.0

    # 2) Role adherence: a 'reviewer' must not author code; a 'planner' must not execute.
    forbidden = {"reviewer": "def ", "planner": "EXECUTE"}
    role_violations = 0
    for m in transcript:
        role = task.roles.get(m.sender, "")
        needle = forbidden.get(role)
        if needle and needle in m.content:
            role_violations += 1
    role_violation_rate = role_violations / n if n else 0.0

    # 3) Ignored messages: directed (non-broadcast) message whose recipient never
    #    sends anything afterward is treated as ignored.
    ignored = 0
    directed = 0
    for i, m in enumerate(transcript):
        if m.recipient == "all":
            continue
        directed += 1
        if not any(later.sender == m.recipient for later in transcript[i + 1:]):
            ignored += 1
    ignored_rate = ignored / directed if directed else 0.0

    # Combine: equal-weight average of (1 - each penalty).
    score = (
        (1 - redundancy_rate) + (1 - role_violation_rate) + (1 - ignored_rate)
    ) / 3
    return {
        "coordination_score": round(score, 3),
        "redundancy_rate": round(redundancy_rate, 3),
        "role_violation_rate": round(role_violation_rate, 3),
        "ignored_rate": round(ignored_rate, 3),
    }


if __name__ == "__main__":
    task = Task(
        goal="Compute Q3 revenue growth and write a summary.",
        milestones=["fetch_data", "compute_growth", "verify", "write_summary"],
        roles={"planner": "planner", "data": "worker",
               "analyst": "worker", "reviewer": "reviewer"},
        final_answer_correct=True,
    )
    transcript = [
        Message(1, "planner", "data", "Fetch Q3 revenue.", milestone=None),
        Message(2, "data", "analyst", "Q3 revenue = 120M.", milestone="fetch_data"),
        Message(3, "analyst", "reviewer", "Growth = 12% QoQ.", milestone="compute_growth"),
        Message(4, "reviewer", "analyst", "Checked numbers, ok.", milestone="verify"),
        Message(5, "analyst", "all", "Summary: revenue up 12%.", milestone="write_summary"),
    ]

    print("TASK SUCCESS   :", task_success(task, transcript))
    print("CONTRIBUTION   :", per_agent_contribution(task, transcript))
    print("COORDINATION   :", coordination_score(task, transcript))
```

Running it produces (values match the transcript above):

```
TASK SUCCESS   : {'final_answer_correct': True, 'milestone_coverage': 1.0,
                 'milestones_missed': [], 'passed': True}
CONTRIBUTION   : {'analyst': {'credit_share': 0.5, 'milestones_completed': 2},
                 'data': {'credit_share': 0.25, 'milestones_completed': 1},
                 'planner': {'credit_share': 0.0, 'milestones_completed': 0},
                 'reviewer': {'credit_share': 0.25, 'milestones_completed': 1}}
COORDINATION   : {'coordination_score': 1.0, 'redundancy_rate': 0.0,
                 'role_violation_rate': 0.0, 'ignored_rate': 0.0}
```

Two things worth noticing. First, the **planner contributed 0 milestones** — leave-one-out or a cost review should ask whether it earns its tokens. (Note the two contribution methods answer *different* questions: this milestone method says the planner completed no milestone; the §B ablation would ask whether *removing* the planner hurts the outcome. A planner can score zero on the first and still be load-bearing on the second, because good delegation enables the workers without itself "completing" a milestone — which is exactly why you keep both methods and do not prune on either one alone.) Second, this transcript is clean; to see the metrics bite, imagine the reviewer message were `Message(4, "reviewer", "analyst", "def recheck(): ...")` — the role-violation term would fire, dragging the coordination score below 1.0 and flagging an FC1 "disobey role specification" failure. Or swap the reviewer's content to duplicate the analyst's and watch `redundancy_rate` rise. These one-line perturbations are how you write *unit tests for your evaluator* — a metric that never moves when you inject the failure it claims to detect is a broken metric.

**Hardening notes for production.** The three coordination checks here are deliberately simple; in a real system you would (1) replace substring role-rules with an LLM judge that reads intent, because `"def "` is a brittle proxy for "wrote code"; (2) make "ignored message" smarter than "recipient never spoke again" — a message can be acknowledged by action rather than reply; and (3) weight the three penalties by how much each failure mode actually costs you (a role violation that ships bad code is worse than one redundant search), using the weighted form \\( \text{Coord} = 1 - \sum_k w_k p_k \\) from the metrics section.

> **Saying it out loud.** This scorer reads a transcript and grades the *process* rather than the answer: task success with milestone coverage, per-agent contribution, and a coordination score built from penalty rates for redundancy, role violations, and ignored messages. It's rule-based here for reproducibility, but in production you'd swap the rules for a checklist judge, because no substring match can tell you whether an agent proceeded on an unstated assumption. The thing to notice is that the coordination penalties are weighted, and you should choose those weights by the *dollar cost* of each failure in your product — otherwise the coordination score is a vanity number rather than a decision input.

---
## Metrics, Formally

Each metric below is one formula plus a tiny worked example. Underneath the notation they're all simple fractions: how many tasks solved, how many milestones hit, how many milestones per thousand tokens, and how much quality you bought per extra dollar.

Precise definitions with micro-examples. Math uses MathJax delimiters (this book renders `\( \)` and `\[ \]`, not dollar signs).

### Task Success Rate (TSR)

Fraction of tasks the *system* fully completed:

\\[ \text{TSR} = \frac{1}{|D|} \sum_{t \in D} \mathbb{1}[\text{system solved } t] \\]

*Micro-example.* Over \\( |D| = 50 \\) tasks the system fully solves 34, so \\( \text{TSR} = 34/50 = 0.68 \\). Because runs are non-deterministic, report TSR as a mean over \\( k \\) seeds with a confidence interval; a single-run TSR is a point estimate of a random variable, not a fact.

### Milestone Coverage

Fraction of predefined sub-goals achieved, averaged over tasks — a partial-credit signal that survives when TSR is 0:

\\[ \text{MC} = \frac{1}{|D|}\sum_{t \in D} \frac{|\text{milestones hit}_t|}{|\text{milestones}_t|} \\]

*Micro-example.* A task with 4 milestones where 3 are hit contributes \\( 3/4 = 0.75 \\). A system can have low TSR but high MC — it gets *most* of the way and fails at the last step (often FC3 premature termination). Watching MC and TSR together localizes failures in *time*: high MC with low TSR means "fails at the end" (fix verification/termination); low MC means "fails early" (fix the orchestrator's plan).

### Per-Agent Credit (Shapley)

A Shapley value asks: across every possible order in which you could add the agents to the team, how much did this agent add on average? The key property is that the credits sum exactly to the team's total score.

Defined earlier; the key property is **efficiency**: credits sum to the total system value,

\\[ \sum_{i \in N} \phi_i = V(N) \\]

*Micro-example.* Two agents, \\( V(\varnothing)=0,\ V(\\{A\\})=0.4,\ V(\\{B\\})=0.2,\ V(\\{A,B\\})=1.0 \\). Then \\( \phi_A = \tfrac12(0.4-0) + \tfrac12(1.0-0.2) = 0.6 \\) and \\( \phi_B = 0.4 \\), summing to \\( V(\\{A,B\\}) = 1.0 \\). Note both exceed their solo scores — the *interaction* created value, which leave-one-out alone would misattribute. This is the concrete reason to reach for Shapley over ablation when agents are synergistic rather than independent.

> **Saying it out loud.** Shapley is the principled answer to "how much did each agent contribute," and the reason to reach for it over simple ablation is interaction. Take two agents: A alone scores 0.4, B alone scores 0.2, together they score 1.0. Shapley gives A 0.6 and B 0.4, summing exactly to the team score. Notice both *exceed* their solo numbers — the interaction created value, and leave-one-out would have misattributed that entirely. The tradeoff is cost: it's exponential in the number of agents, so it's realistic at three or four and you need Monte-Carlo sampling above that. Use it when you need defensible attribution, not for routine scoring.

### Communication Efficiency

Useful information moved per token spent. One simple operationalization: milestones achieved per thousand tokens of inter-agent messages,

\\[ \text{CE} = \frac{\text{milestones hit}}{(\text{message tokens})/1000} \\]

*Micro-example.* 4 milestones over 8,000 message tokens gives \\( \text{CE} = 4/8 = 0.5 \\) milestones per 1k tokens. Falling CE across runs is an early sign of chatter/redundancy — agents talking more to accomplish the same thing, the quantitative signature of FC2 misalignment creeping in.

### Coordination Score

The composite used in the code, generalized to a weighted penalty average with weights \\( w_k \\) summing to 1:

\\[ \text{Coord} = 1 - \sum_{k} w_k \\, p_k, \qquad p_k \in [0,1] \\]

where each \\( p_k \\) is a penalty rate (redundancy, role violations, ignored messages). *Micro-example.* Equal weights with \\( p = (0.1, 0.0, 0.2) \\) give \\( \text{Coord} = 1 - \tfrac13(0.3) = 0.9 \\). Choose the weights \\( w_k \\) by the *dollar cost* of each failure in your product, not by intuition — that is what turns a vanity number into a decision input.

### Goal-Drift Score

A dynamics metric with no single-agent analogue: how far the conversation wanders from the original objective. With \\( g \\) the goal embedding and \\( m_t \\) the embedding of the message at step \\( t \\),

\\[ \text{Drift} = \frac{1}{T}\sum_{t=1}^{T}\big(1 - \cos(g, m_t)\big) \\]

*Micro-example.* If cosine similarity to the goal stays near 0.9 early then decays to 0.4 over a long trace, rising Drift flags FC2 "task derailment" *while it is happening*, letting a supervisor intervene before termination.

> **Saying it out loud.** Goal drift measures how far the conversation wanders from the original objective — you embed the goal, embed each message, and track one minus the cosine similarity over time. It's a dynamics metric with no single-agent analogue, and its real value is that it's a *leading* indicator rather than a postmortem one: if similarity sits near 0.9 early and decays toward 0.4 over a long trace, you can see derailment happening and have a supervisor intervene before the run terminates. That's the difference between a metric that explains a failure and one that prevents it.

### Cost-Adjusted Utility (the honest metric)

The one that decides whether multi-agent was worth it — quality per unit cost, compared to a baseline:

\\[ \text{CAU} = \frac{V_{\text{multi}} - V_{\text{single}}}{C_{\text{multi}} - C_{\text{single}}} \\]

*Micro-example.* Multi-agent scores 0.90 vs single-agent 0.75 (\\( \Delta V = 0.15 \\)) but costs 15x the tokens (say \\( \Delta C = 14 \\) baseline-units). \\( \text{CAU} = 0.15/14 \approx 0.011 \\) quality points per baseline-unit of extra cost. Whether that clears your bar depends entirely on how much a quality point is worth in your product. The discipline: never report \\( \Delta V \\) (the quality win) without \\( \Delta C \\) (the cost) in the same sentence — a 90% quality improvement at 15x cost is a *business decision*, not an automatic yes, and CAU is the number that forces that conversation.

> **Saying it out loud.** This is the metric that decides whether multi-agent was worth building: quality gained divided by cost added, against a single-agent baseline. Concretely — multi-agent scores 0.90 against single-agent's 0.75, so you gained 0.15, but it cost fourteen extra baseline-units of tokens. That's about 0.011 quality points per unit of extra spend, and whether that clears your bar depends entirely on what a quality point is worth in your product. The discipline is simple and people violate it constantly: never say the quality win without saying the cost in the same sentence. A 90% improvement at 15x cost is a business decision, not an automatic yes.

---
## Production Case Studies & War Stories

Theory tells you what *could* go wrong; production tells you what *does*. Here are how real teams evaluate multi-agent systems, and a dissection of a cascading failure with the lesson that generalizes.

### Case study 1 — Anthropic's research system: outcome-first, human-in-the-loop

Anthropic's public account ([June 2025](https://www.anthropic.com/engineering/multi-agent-research-system)) is the reference implementation for *how to evaluate a multi-agent system in production*, and its choices are worth studying as choices:

- **They evaluate the end state, not the path**, using an **LLM judge** against a rubric (factual accuracy, citation quality, completeness, source quality, tool efficiency) — because a research question has many valid trajectories, so scoring the trajectory against a reference would penalize good-but-different paths. This is the "end-state for headline pass/fail" philosophy applied at scale.
- **They started with ~20 test cases, not thousands.** The lesson every senior engineer will nod at: a small set of *representative* queries caught the large effects immediately, and waiting for a big benchmark would have delayed learning by months. Start evaluating on day one with the cases you have.
- **They kept humans in the loop** precisely because the automated judge missed subtle failures — e.g., a report that looked well-cited but leaned on low-quality sources, or that quietly preferred SEO-optimized content farms over primary sources. Automated judges catch the gross errors; humans catch the ones that matter most and are hardest to specify.
- **They treated the *orchestrator's delegation* as the highest-leverage thing to tune.** Vague subagent instructions ("research the semiconductor shortage") caused duplicated work and gaps; precise, bounded task descriptions per subagent fixed more than any subagent-level change. In evaluation terms: the coordination dimension dominated the outcome dimension.
- **They deployed with "rainbow deployments"** — updating agents gradually while runs are in flight — because agents are long-running and stateful, so a naive redeploy kills work in progress. An operational lesson that only shows up once your agents run for minutes, not milliseconds.

The transferable takeaway: **outcome-first LLM-judge evaluation, seeded with a tiny human-curated set, with humans retained for the failures the judge cannot see, and with coordination treated as the primary lever.**

> **Saying it out loud.** Four choices from this writeup are worth stealing. They evaluate the *end state* with an LLM judge against a rubric, not the path, because a research question has many valid trajectories and scoring against a reference would punish good-but-different ones. They started with about twenty test cases, not thousands — a small representative set caught the big effects immediately, and waiting for a proper benchmark would have cost months of learning. They kept humans in the loop because the judge missed the subtle failures, like a report that looked well-cited but leaned on SEO content farms instead of primary sources. And they found the *orchestrator's delegation quality* was the highest-leverage thing to tune — vague subagent instructions caused duplicated work and gaps, so coordination dominated outcome. Worth noting these are their published accounts of their own system, not independent replication.

### Case study 2 — MAST's empirical trace study: how researchers evaluate at the population level

Where Anthropic evaluated *their* system, Cemri et al. evaluated *the field* ([arXiv:2503.13657](https://arxiv.org/abs/2503.13657)). Their method is itself a case study in multi-agent evaluation:

- **Collect real traces** across seven frameworks, not synthetic ones — the failures had to be ecologically valid.
- **Hand-annotate with a codebook**, iterating the taxonomy until inter-annotator agreement was high (kappa ≈ 0.88). This is the gold-standard move: the humans *and the rubric* are validated before any automation.
- **Then automate**: train an LLM judge to apply the validated taxonomy, so the annotation scales. This "validate on humans, then scale with a judge" pipeline is the template for any serious trajectory eval.
- **The finding that reframed the field**: failures cluster in specification, coordination, and verification — so the fix is *structural* (better roles, clearer handoffs, mandatory verification), not "wait for a smarter model."

> **Saying it out loud.** This one is a case study in *method*. They collected real traces across seven frameworks rather than synthetic ones, so the failures were ecologically valid. They hand-annotated with a codebook, iterating the taxonomy until inter-annotator agreement was high — kappa around 0.88 — which validates both the humans and the rubric before any automation touches it. Then they trained an LLM judge to apply the validated taxonomy so the annotation scales. That "validate on humans, then scale with a judge" pipeline is the template for any serious trajectory eval, and skipping the first half is how teams end up with a judge nobody can defend.

### War story — the cascading-failure incident

Here is a composite incident, assembled from the failure modes above, of the kind that recurs in production analytics agents. It is illustrative rather than a specific company's postmortem, but every step maps to a documented MAST mode.

**The setup.** A four-agent financial-reporting system: `planner` → `data-fetcher` → `analyst` → `reviewer`, orchestrated as a chain. Task: "Produce the Q3 revenue-growth summary for the board deck."

**The trajectory.**
1. The **planner** writes: "Compute revenue growth for the latest quarter." It does *not* pin the fiscal quarter or the data source — an FC1 *fail-to-follow-requirements* seed (the prompt said Q3; the plan said "latest").
2. The **data-fetcher**, seeing "latest quarter," queries a warehouse view that had not yet loaded Q3, so "latest" resolved to **Q2**. It never states which quarter it pulled — FC2 *proceeding on wrong assumptions* + *withholding crucial information* (the provenance).
3. The **analyst** computes a clean, correct 8% QoQ growth *on the Q2 numbers*. Its reasoning is flawless; its inputs are wrong. The error is now laundered into a confident, well-formatted result — this is the **cascade**: a silent assumption became a load-bearing premise.
4. The **reviewer** checks the arithmetic (correct), checks the formatting (correct), and approves. It does not check *which quarter the data came from*, because provenance was never in its checklist — FC3 *incorrect/incomplete verification*. The defense that should have broken the chain instead rubber-stamped it.
5. The board deck ships a confidently wrong Q3 number that is actually Q2. Every agent behaved "correctly" by its own contract. The **system** had no data-provenance check anywhere along the chain.

**How evaluation would have caught it.** (a) A **trajectory/MAST-checklist judge** asking "did any agent proceed on an unstated assumption about the time period?" fires on step 2. (b) A **fact-propagation check** comparing the requested period (Q3) against the period actually used (Q2) fails immediately — this is a *provenance* metric, not a *quality* metric, which is why an arithmetic-only reviewer missed it. (c) **Credit assignment via trace localization** marks step 1/2 as the decisive error, *not* step 4 where the symptom surfaced — so the fix targets the planner's specification and the fetcher's provenance reporting, not the reviewer. (d) A **cost/redundancy** metric would not have caught this one — a reminder that no single metric is sufficient.

**The lessons, generalized.**
- **Provenance is a first-class output.** Every agent that produces data must state where it came from, and every verifier must check provenance, not just internal consistency. Correct math on wrong data is the most dangerous multi-agent failure because it *looks* right.
- **Verification must target the failure mode, not the surface.** A reviewer that checks the wrong thing is worse than no reviewer — it manufactures false confidence (FC3 *incorrect verification*).
- **Blame the decisive error, not the symptom.** The reviewer "shipped" the number, but the planner and fetcher caused the failure. Firing the reviewer (or upgrading its model) fixes nothing; adding a provenance contract does.
- **Stronger models would not have saved this.** Every agent could be a frontier model and still cascade, because the missing thing was a *structural* provenance check — the central MAST finding, in one incident.
- **Chains propagate; graphs with a verifier contain.** Had the topology included a provenance-verification node with the *authority to reject and re-dispatch*, the chain breaks at step 2. Topology is a safety property, not just a performance one.

> **Saying it out loud.** Four agents in a chain: planner, data-fetcher, analyst, reviewer. The task said Q3; the planner wrote "latest quarter." The fetcher hit a warehouse view where Q3 hadn't loaded, so "latest" resolved to Q2, and it never said which quarter it used. The analyst computed a flawless 8% growth rate on the wrong data. The reviewer checked the arithmetic and the formatting, both correct, and approved — because provenance was never on its checklist. A confidently wrong number shipped to a board deck, and every single agent behaved correctly by its own contract. The generalizable lessons: provenance is a first-class output, a verifier that checks the wrong thing is worse than no verifier because it manufactures confidence, blame the decisive error at step one or two rather than the reviewer where the symptom surfaced, and stronger models would not have saved this because the missing piece was structural. Chains propagate; a graph with a verifier that has authority to reject and re-dispatch contains.

---
## Single-Agent vs Multi-Agent: When Is It Worth It?

The uncomfortable truth: **most tasks do not need multiple agents.** Multi-agent architectures buy you parallel breadth and specialization at a steep cost in tokens, latency, coordination complexity, and new failure modes. Anthropic's own guidance is that multi-agent shines for *breadth-first, parallelizable* problems and is a poor fit for tightly coupled tasks where agents must share evolving context ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)); Cognition's guidance is that for *write-heavy* tasks you should prefer a single linear agent entirely ([Cognition](https://cognition.com/blog/dont-build-multi-agents)). Both reduce to one question: **do the subtasks share a mutable artifact or evolving decision state?**

| Factor | Single-agent | Multi-agent |
|---|---|---|
| Token cost | ~1x (baseline) | ~15x chat / several x single-agent ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)) |
| Latency | Lower, sequential | Higher per-agent, but parallelizable across subagents |
| Best for | Tightly coupled, sequential reasoning; shared evolving context | Breadth-first search; independent parallel subtasks; many specialized tools |
| Failure surface | One agent's mistakes | + communication, coordination, emergent (cascade, groupthink, deadlock) |
| Debuggability | Straightforward trace | Hard: non-deterministic, cross-agent, needs full tracing |
| Credit assignment | Trivial | Genuinely hard (this chapter) |
| Context handling | One window; compaction as it fills | Each subagent gets a fresh window — multiplies effective context |
| When it *earns* its cost | Default choice | Task value is high AND work truly parallelizes AND context exceeds one window |

**A decision table for "does the overhead pay?"** Multi-agent earns its 15x only when several conditions hold at once. If any of the "single-agent" answers apply, start there and prove multi-agent beats it before adopting it.

| Question | Points to single-agent | Points to multi-agent |
|---|---|---|
| Do subtasks share a mutable artifact / evolving decisions? | Yes (coding one file, editing one doc) | No (independent research beats) |
| Is the work read-heavy or write-heavy? | Write-heavy | Read-heavy / gather-and-synthesize |
| Does the full context fit one window with room to reason? | Yes | No — need parallel windows |
| Is the task decomposable into independent chunks? | No, tightly coupled | Yes, cleanly separable |
| Is the per-task value high enough to justify 15x tokens? | No | Yes |
| Do you need many specialized tools/personas that conflict in one prompt? | No | Yes |
| Is low, predictable latency a hard requirement? | Yes | No (parallelism helps throughput, not tail latency) |

Anthropic reports a **90.2%** improvement of a multi-agent (Opus 4 lead + Sonnet 4 subagents) system over single-agent Opus 4 on an internal research eval — a large gain, but on a task that is *inherently breadth-first* (explore many sources in parallel), *read-heavy* (no shared artifact to merge), and *high-value* enough to justify 15x tokens ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). That is the profile where multi-agent wins. Change any one of those — make it write-heavy, or coupled, or low-value — and the calculus flips, which is exactly Cognition's coding regime.

**Diminishing returns are real.** Adding a fourth or fifth agent to a coordination-heavy task frequently *lowers* quality: more agents means more messages, more opportunities for FC2 misalignment, and more chances for one bad hand-off to cascade. MultiAgentBench found that *coordination topology matters more than agent count* — graph-structured coordination beat other topologies on research tasks, and elaborate cognitive planning added only a few percent to milestone achievement ([Zhu et al., 2025](https://arxiv.org/abs/2503.01935)). The lesson: **structure your agents well before you add more of them, and always keep a single-agent baseline in your eval to prove the overhead pays.** The failure pattern to avoid is "agent sprawl" — adding a specialist for every sub-concern until the coordination cost swamps the specialization benefit; leave-one-out ablation is how you find and delete the agents that are no longer paying for themselves.

**The topology cheat-sheet.** Beyond count, the *shape* of the interaction graph is a design decision with evaluation consequences:

| Topology | Shape | Strength | Watch for |
|---|---|---|---|
| Single agent | one loop | simplest, cheapest, trivially debuggable | capability/context ceiling |
| Chain / pipeline | A→B→C | clear stages, easy to reason about | cascades: no backstop if a stage errs |
| Orchestrator-worker (star) | lead fans out to workers | parallel breadth; fresh context per worker | orchestrator's delegation quality is the bottleneck |
| Debate / committee | agents critique each other | improves factuality *if* critique is real | groupthink / sycophantic convergence |
| Graph (arbitrary) | nodes + conditional edges | most expressive; can add verifier nodes with reject authority | complexity; hardest to trace |

> **Saying it out loud.** The uncomfortable answer is that most tasks don't need multiple agents, and the deciding question is one line: do the subtasks share a mutable artifact or evolving decision state? If yes — coding one file, editing one document — a single agent or a strictly serialized single writer wins, because parallel writers make irreconcilable implicit decisions. If no — independent research beats with nothing to merge — multi-agent can genuinely win, and Anthropic's +90% is on exactly that profile. But three cautions. That win is vendor-published, on an internal eval, and *not* token-matched at 15x spend; recent evidence is that at an equal token budget multi-agent often underperforms a single agent. Adding a fourth or fifth agent frequently *lowers* quality, and MultiAgentBench found coordination topology matters more than agent count. And agents sharing one base model aren't independent verifiers — their errors are correlated, so a committee agreeing is much weaker evidence than three independent checks. So: single agent is the default, and multi-agent has to prove itself against a baseline with cost-adjusted utility.

---

## Pitfalls in Evaluating Multi-Agent Systems

The evaluation itself has failure modes. Watch for these.

- **Grading only the final answer.** The lucky-right process (correct output, broken process) passes and reappears as a regression later. Always score trajectory *and* end-state.
- **No single-agent baseline.** Without it you cannot compute cost-adjusted utility, and you will keep an expensive multi-agent system that a single agent matches. This is the single most common and most expensive mistake; the baseline is not optional.
- **Ignoring cost.** A quality win at 15x tokens may be a net loss. Report cost alongside every quality number, in the same view.
- **Judge contamination / self-preference.** Using one of the system's own agents (or same-family model) as the LLM judge inflates scores. Use an independent judge and spot-check with humans, as Anthropic does to catch hallucinated or low-source-quality answers automated judges miss.
- **Non-determinism mistaken for signal.** Multi-agent runs vary run-to-run. A single run is noise; report means and variance over multiple seeds, and be suspicious of any A/B where the effect size is smaller than the run-to-run spread.
- **Attribution by vibes.** Declaring "the coder was at fault" without trace localization, ablation, or milestone evidence. Credit assignment needs a method, not an intuition — and it usually indicts a *different* agent than the one where the symptom appeared.
- **Over-fitting to one topology.** Evaluating only your favorite orchestration structure hides whether a chain would have beaten your graph (or vice versa). Vary the topology; MultiAgentBench found topology mattered more than agent count.
- **Milestone leakage.** If milestones are too granular they become a checklist the agents game; too coarse and they give no per-agent signal. Calibrate against human judgments.
- **Evaluating on the happy path only.** Multi-agent failures are combinatorial; your eval set must include adversarial inputs, tool failures, and ambiguous prompts, because that is where coordination and verification break.
- **Confusing "reached consensus" with "correct."** Unanimity is a *process* observation, not an *outcome* one; early, confident agreement is a groupthink red flag, not a success signal.

> **Saying it out loud.** If I had to name the one mistake that costs the most money, it's shipping without a single-agent baseline — without it you can't compute cost-adjusted utility, and you'll keep paying 15x for something one agent matches. Close behind: grading only the final answer, so the lucky-right process passes and regresses later; leaving cost off the dashboard; and treating a single run as a result when run-to-run variance in these systems routinely exceeds the effect size you're claiming. Then two subtler ones — using a model from the same family as your agents as the judge, which inflates scores through self-preference, and attribution by vibes, declaring "the coder was at fault" with no trace localization or ablation behind it. That last one usually indicts a different agent than the one where the symptom appeared.

---

## Tools & Benchmarks

| Name | Type | What it gives you | Link |
|---|---|---|---|
| MAST | Taxonomy + dataset | 14 failure modes / 3 categories; 200+ annotated traces; an LLM-judge annotator | [arXiv:2503.13657](https://arxiv.org/abs/2503.13657) |
| MultiAgentBench (MARBLE) | Benchmark | Milestone KPIs; collaboration & competition scenarios; star/chain/tree/graph topologies | [arXiv:2503.01935](https://arxiv.org/abs/2503.01935) |
| Multiagent Debate | Method + code | Debate protocol that improves factuality/reasoning; baseline for consensus dynamics | [arXiv:2305.14325](https://arxiv.org/abs/2305.14325) · [code](https://github.com/composable-models/llm_multiagent_debate) |
| AutoGen / AG2 | Framework | Conversable multi-agent orchestration; GroupChat; full transcripts to evaluate | [autogen](https://microsoft.github.io/autogen/) · [AG2](https://docs.ag2.ai/) |
| Magentic-One | Reference system | Generalist orchestrator + web/file/coder/terminal agents; a concrete architecture to cite | [Microsoft Research](https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/) |
| CrewAI | Framework | Role/goal-based crews; Flows for deterministic orchestration; role-adherence surface | [docs.crewai.com](https://docs.crewai.com/) |
| LangGraph | Framework | Graph-structured agent workflows; explicit shared state for tracing; supervisor/swarm prebuilts | [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/) |
| OpenAI Agents SDK (ex-Swarm) | Framework | Lightweight handoffs between agents; built-in tracing and guardrails | [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/) |
| Google ADK + A2A | Framework + protocol | Code-first agents; A2A cross-vendor/cross-framework interop via Agent Cards | [ADK](https://google.github.io/adk-docs/) · [A2A](https://a2a-protocol.org/) |
| LangSmith / Langfuse | Observability | Full multi-agent tracing needed for credit assignment & debugging | [langsmith](https://docs.smith.langchain.com/) · [langfuse.com](https://langfuse.com/) |
| tau-bench (τ-bench) | Benchmark | Agent-user + tool interaction; reliability across repeated trials (pass^k) | [arXiv:2406.12045](https://arxiv.org/abs/2406.12045) |

> **Saying it out loud.** The short list I'd name: MAST for the failure taxonomy and its annotated traces, MultiAgentBench for milestone KPIs and topology comparisons, the multi-agent debate paper as the baseline for consensus dynamics, and tau-bench when reliability across repeated trials is what you care about — its pass-to-the-k metric is the honest way to ask "does it work every time" rather than "did it work once." On the tooling side, the one that's genuinely non-negotiable is tracing: LangSmith, Langfuse, whatever you like, but without full structured traces credit assignment is impossible and every other metric on this list degrades into a number you can't act on.

---
## Interview Mastery

This section is engineered to make you sound like someone who has *built and evaluated* these systems, not just read about them. It has four parts: the rapid-fire Q&A, a memorized 60-second answer to the hardest single question, a full system-design walkthrough with a sketch, and a red-flags/green-flags cheat sheet.

### Rapid-fire Q&A

**Q1. Why can't you just evaluate a multi-agent system by checking its final output?**
Because outcome and process are separable. A system can produce the right answer through a broken process (the coder happened to be right; the reviewer never actually checked) — that passes your eval and then regresses the moment the lucky step goes wrong. And a system can fail while every individual agent behaved correctly, because the fault was in the *interaction*. You need trajectory scoring and credit assignment on top of end-state checking.

**Q2. What is the credit-assignment problem and how do you approach it?**
It is attributing a system-level outcome to the specific agent and step that caused it — hard because effects are delayed, responsibility is diffuse, and true attribution is counterfactual. Four practical methods: trace-based localization of the decisive error (the MAST approach), leave-one-out ablation for marginal contribution, Shapley values for principled attribution when you have ≤4 agents, and milestone-based KPIs for scalable per-agent credit. In practice I run milestone KPIs continuously, use trace localization to explain sampled failures, and confirm fixes with ablation.

**Q3. Name the main categories of multi-agent failure.**
Using MAST: (1) specification/system-design issues — bad roles, lost history, no stopping condition (~42% of failures); (2) inter-agent misalignment — wrong assumptions, ignored messages, withheld information (~37%); (3) task verification failures — premature termination, no or incorrect verification (~21%). Plus cross-cutting emergent dynamics: cascading errors, groupthink, and deadlock. The headline is that these are *structural*, so a stronger base model often does not fix them.

**Q4. When is a multi-agent system actually worth the cost?**
When the subtasks *don't* share a mutable artifact — read-heavy, breadth-first, decomposable work whose context exceeds one window — and the per-task value justifies ~15x the tokens of chat. Anthropic saw ~90% gain on research (parallel, read-heavy); Cognition argues *against* multi-agent for coding (write-heavy, shared state). The deciding variable is the read/write structure of the task. Always keep a single-agent baseline and report cost-adjusted utility.

**Q5. How would you detect error propagation / cascading failures in a transcript?**
Look for a low-confidence or wrong assertion early in the trace that later messages build on without re-checking, combined with weak or absent verification (FC3). Concretely: trace-localize the first decisive error, then confirm no downstream agent challenged it. A healthy system has a verification agent that breaks the chain; its absence is the structural bug, and stronger base models alone won't fix it. Add a provenance check so "correct math on wrong data" cannot pass.

**Q6. What's the difference between end-state and trajectory evaluation, and when do you use each?**
End-state checks only the final state, tolerating multiple valid paths — cheap, path-agnostic, good for headline pass/fail (Anthropic uses it for research). Trajectory evaluation scores the sequence of actions/messages — expensive but necessary for catching process failures and doing credit assignment. Use end-state on every run for the top-line metric, and spend trajectory scoring only on the failures end-state flags.

**Q7. Does adding more agents reliably improve performance?**
No — diminishing and often negative returns. More agents mean more messages and more chances for misalignment and cascades. MultiAgentBench found coordination *topology* (graph beat chain/tree/star on research) mattered more than agent count, and elaborate planning added only a few percent. Structure the agents well before adding more, and prove each additional agent's marginal contribution with ablation — a negative \\( \Delta_i \\) means delete it.

**Q8. What are the traps in evaluating multi-agent systems themselves?**
Grading only the final answer; no single-agent baseline; ignoring token cost; using a same-family model as judge (self-preference); treating a single non-deterministic run as signal; and attributing blame by intuition instead of a method. Each of these makes a broken or overpriced system look good.

**Q9. Anthropic and Cognition published opposite advice the same month. Reconcile them.**
They describe different task shapes, not a real contradiction. Anthropic's research task is read-heavy with no shared mutable artifact, so parallel subagents' outputs concatenate — multi-agent wins. Cognition's coding task is write-heavy with shared evolving state, so parallel agents make conflicting implicit decisions that can't be merged — single-agent wins. Both agree the real work is context engineering; the architecture is downstream of whether subtasks share writes. Cognition's "single-writer" principle even lives *inside* Anthropic's design — one synthesizer owns the final artifact.

**Q10. What is the "single-writer" principle and why does it matter?**
Exactly one agent should own any given piece of mutable state or artifact. When two agents write the same artifact in parallel, each embeds implicit decisions (Cognition's Flappy Bird example: clashing visual styles) that cannot be reconciled after the fact. It matters for evaluation because a role-adherence/coordination metric should flag multiple writers to the same artifact as a design smell before it produces an incoherent output.

**Q11. Explain the MAST taxonomy and how you'd turn it into an eval.**
MAST is 14 empirically-derived failure modes in three buckets — specification/design, inter-agent misalignment, verification/termination — from 200+ annotated traces. I turn it into a *checklist judge*: for each transcript an LLM (validated against human labels) answers one yes/no question per mode with a citing message. Aggregating gives a failure-mode distribution, so the dashboard says not just "68% pass" but "of failures, 40% are incomplete-verification" — which tells engineering to build a verifier next.

**Q12. What's the difference between MCP and A2A, and why does it matter for evaluation?**
MCP standardizes how an agent talks to *tools*; A2A standardizes how an agent talks to *other agents* (cross-vendor, via Agent Cards; donated to the Linux Foundation in June 2025). For evaluation it matters because A2A gives you a standardized *inter-agent call log* even across frameworks and organizations — a portable transcript surface — whereas without it you're reconstructing coordination from heterogeneous logs.

**Q13. How do you handle non-determinism when comparing two multi-agent designs?**
Run each design over \\( k \\) seeds, report mean and variance of every metric, and only believe an A/B difference that exceeds the run-to-run spread. For reliability specifically, use a pass^k style metric (does it succeed on *all* k trials, not just one) — a system that's right 1-in-3 times is not "66% good," it's unreliable.

**Q14. A multi-agent run gave the right answer but you're unhappy. Why might that be?**
Right answer, broken process: it may have reached the answer by luck (a wrong assumption that happened to cancel out), by wasteful duplication (two agents did the same search — cost failure), or without any verification (so it won't reproduce). End-state passed; trajectory and cost scoring would show the process is fragile, and it will regress.

**Q15. Where do you put verification in a multi-agent system, and how do you evaluate the verifier?**
Give verification its own node with the *authority to reject and re-dispatch*, positioned to break cascades before they reach the output. Evaluate the verifier by its *discrimination*: does "approved" actually correlate with "correct"? A verifier that approves everything (or checks the wrong property, like arithmetic instead of provenance) manufactures false confidence — FC3 incorrect verification — and is worse than none.

**Q16. How would you detect and prevent groupthink in a debate/committee setup?**
Detect it by tracking disagreement and confidence across rounds: falling disagreement with rising confidence, especially early unanimity, is the signature. Prevent it by assigning genuine adversarial roles, hiding others' answers until each agent commits independently, and using an independent judge rather than majority vote. Multiagent debate helps factuality only when the critique is real.

**Q17. Your multi-agent system costs 15x a single agent for a 10% quality gain. Ship it?**
Not automatically — that's a business decision, captured by cost-adjusted utility \\( \text{CAU} = \Delta V / \Delta C \\). I'd quantify what a quality point is worth in the product, check whether a cheaper design (better single-agent prompt, fewer agents, better delegation) captures most of the 10%, and only ship multi-agent if the value per marginal token clears our bar. Often the honest answer is "improve the single agent first."

**Q18. What observability do you need before you can evaluate a multi-agent system at all?**
A structured, append-only transcript: per-action rows with agent id, role, action, inputs, outputs, tokens, and timestamps — from a tracer like LangSmith, the Agents SDK tracer, or Langfuse. Without it you can't score coordination, do credit assignment, or reproduce a failure. If it wasn't logged, it didn't happen. Instrumentation is a prerequisite, not a nice-to-have.

### Explain the credit-assignment problem in 60 seconds

> "In a multi-agent system, several agents pass work to each other, and at the end you get one system-level signal — the report was right, or it was wrong. Credit assignment is the problem of pushing that single signal back onto the individual agents and steps that actually caused it. It's hard for four reasons. First, delay: the mistake that doomed the run often happened many steps before the visible failure — a planner under-specified the task and the coder twelve steps later just inherited it. Second, diffusion: when five agents each contribute a slice of a bad answer, no single message *is* the bug. Third, it's counterfactual: 'agent B caused it' really means 'if B had acted differently the outcome would improve,' and you usually can't run that world. Fourth, interaction: two agents can each be individually correct and jointly wrong. In practice I use four tools that trade cost for rigor: read the trace and mark the first unrecoverable error; leave-one-out ablation to measure each agent's marginal contribution; Shapley values when there are only three or four agents and I need a defensible split; and milestone KPIs for cheap per-agent credit at scale. The one discipline that matters most: blame the *decisive* error, not the *symptom* — they're almost always different agents."

### System-design prompt: "Design and evaluate a multi-agent research system"

This is the canonical multi-agent system-design interview question. Here is a structured answer you can adapt.

**1. Clarify the task and the win condition.** "Research system" = given an open-ended question, produce a cited, accurate, complete report. It's *read-heavy* and *breadth-first* with *no shared mutable artifact until synthesis* — the profile where multi-agent genuinely wins. Success = factual accuracy + citation quality + completeness + source quality, judged on the end state (many valid paths).

**2. Architecture — orchestrator-worker.** A lead agent decomposes the query into independent subtopics and fans out one worker per subtopic (each with its own context window, searching in parallel), then a single synthesizer merges findings into the report. One writer owns the final artifact (single-writer principle). Add a dedicated **verifier** node between synthesis and output, with authority to reject and re-dispatch, so cascades and low-source-quality claims get caught.

```
                         (query)
                            |
                     +------------+
                     | ORCHESTRATOR |  plan: split into independent subtopics
                     +------------+
                        /   |   \        fan-out (Send / handoff), parallel
                       v    v    v
                   [worker][worker][worker]   each: own context window, tools, cites sources
                       \    |    /
                        v   v   v
                     +------------+
                     | SYNTHESIZER |  single writer -> draft report (with citations)
                     +------------+
                            |
                     +------------+
                     |  VERIFIER   |  check facts, citations, provenance, completeness
                     +------------+
                       reject|approve
                       (re-dispatch)  \-> (final report)
```

**3. Instrumentation.** Trace every node: agent id, subtopic assigned, tools called, sources cited, tokens, latency. This transcript is the eval surface; without it nothing below is possible.

**4. Evaluation plan.**
- *Outcome (end-state):* LLM judge against a rubric (accuracy, citations, completeness, source quality), validated against ~20 human-curated cases to start, humans retained for the failures the judge misses (e.g., authoritative-looking but low-quality sources).
- *Process (trajectory):* MAST checklist judge on sampled/failed runs — did any worker proceed on a wrong assumption? did the synthesizer drop a worker's finding? did the verifier actually check provenance?
- *Coordination:* redundancy rate (two workers on the same subtopic), ignored-finding rate (a worker's result absent from the report), goal-drift.
- *Credit assignment:* milestone KPIs per subtopic for routine per-worker credit; leave-one-out to prune workers that don't move the outcome.
- *Cost:* tokens and dollars per report, and cost-adjusted utility vs a **single-agent baseline** — non-negotiable, or you can't prove the architecture pays.
- *Reliability:* run each eval query over k seeds; report mean/variance; watch pass^k for consistency.

**5. The failure modes I'd specifically guard against.** Duplicated subtopics (orchestrator delegation quality — tune the plan prompt); a worker's finding silently dropped in synthesis (withholding/ignored input, FC2); the verifier rubber-stamping (FC3 — evaluate the verifier's discrimination); and cost blowup from over-broad decomposition. I'd start with ~20 test cases, ship, and let the failure-mode distribution direct what to build next.

**6. When I'd walk it back to a single agent.** If the eval shows CAU below our bar — i.e., the 15x tokens don't buy enough quality over a well-prompted single agent — or if the task turns out write-heavy (drafting one long artifact where sections must stay consistent), I'd collapse to a single agent with retrieval and context compaction, keeping only the verifier.

### Red flags vs green flags

Use this to read a candidate system (or to audit your own) fast.

| Red flags (worry) | Green flags (healthy) |
|---|---|
| Eval checks only the final answer | Scores end-state *and* trajectory *and* cost |
| No single-agent baseline in the eval | Every multi-agent number sits next to a single-agent one |
| Quality reported without cost | Cost-adjusted utility reported alongside quality |
| "The X agent is at fault" with no method | Blame localized by trace/ablation/milestones to a decisive step |
| Same-family model judges its own system | Independent judge, human spot-checks |
| A single run cited as a result | Means and variance over multiple seeds; pass^k for reliability |
| No verifier, or a verifier that checks the surface | Verifier with reject authority, evaluated for discrimination |
| Adds agents to fix quality problems | Structures/topology first; prunes agents with negative \\( \Delta_i \\) |
| Multiple agents writing the same artifact | Single writer owns each mutable artifact |
| Early, confident consensus treated as success | Consensus dynamics monitored for groupthink |
| No transcript / can't reproduce a failure | Full structured tracing; failures replayable |
| "We use multi-agent because it's powerful" | "We use multi-agent because this task is read-heavy and parallelizable, and here's the CAU proving it" |

---
## Further Reading

**Research — failure analysis & benchmarks**
- Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST taxonomy; 14 modes, 3 categories; 200+ traces; 2025) — https://arxiv.org/abs/2503.13657
- Zhu et al., "MultiAgentBench: Evaluating the Collaboration and Competition of LLM Agents" (MARBLE; milestone KPIs; topology study; 2025) — https://arxiv.org/abs/2503.01935
- Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (2023) — https://arxiv.org/abs/2305.14325 · code: https://github.com/composable-models/llm_multiagent_debate
- Yao et al., "tau-bench: A Benchmark for Tool-Agent-User Interaction" (reliability across trials; pass^k) — https://arxiv.org/abs/2406.12045

**Production writeups & the architecture debate**
- Anthropic, "How we built our multi-agent research system" (June 2025) — https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic, "Building Effective Agents" (patterns; workflow vs agent) — https://www.anthropic.com/engineering/building-effective-agents
- Cognition (Walden Yan), "Don't Build Multi-Agents" (context engineering; single-writer) — https://cognition.com/blog/dont-build-multi-agents
- Microsoft Research, "Magentic-One: A Generalist Multi-Agent System" (Nov 2024) — https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks/

**Frameworks**
- AutoGen (Microsoft) — https://microsoft.github.io/autogen/ · AG2 (community fork) — https://docs.ag2.ai/
- CrewAI — https://docs.crewai.com/
- LangGraph (multi-agent patterns; supervisor/swarm) — https://langchain-ai.github.io/langgraph/
- OpenAI Agents SDK — https://openai.github.io/openai-agents-python/ · archived Swarm — https://github.com/openai/swarm
- Google Agent Development Kit (ADK) — https://google.github.io/adk-docs/

**Protocols & interoperability**
- Agent2Agent (A2A) protocol — https://a2a-protocol.org/
- Google, "Announcing the Agent2Agent Protocol (A2A)" (April 2025) — https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/
- Linux Foundation, "Launches the Agent2Agent Protocol Project" (June 2025) — https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents
- Model Context Protocol (MCP; agent-to-tool, complements A2A) — https://modelcontextprotocol.io/

**Observability**
- LangSmith — https://docs.smith.langchain.com/
- Langfuse — https://langfuse.com/

---

## Key Takeaways

1. **Evaluate the process, not just the product.** Outcome and process are separable; a right answer from a broken process will regress. Score end-state, trajectory, and cost.
2. **Failures are structural.** MAST shows most multi-agent failures come from specification, coordination, and verification — not raw model capability. A stronger base model rarely fixes them; better roles, handoffs, provenance, and verification do.
3. **Credit assignment is the core new skill.** Push a single system-level signal back onto the agent and step that caused it, using trace localization, leave-one-out, Shapley, and milestone KPIs — and always blame the decisive error, not the symptom.
4. **Multi-agent is not free and not always better.** It costs ~15x chat tokens. It wins on read-heavy, breadth-first, decomposable, high-value work (Anthropic's research: +90%); it loses on write-heavy, tightly-coupled work with shared state (Cognition's coding). The deciding variable is whether subtasks share mutable state.
5. **Prove it with a baseline and cost-adjusted utility.** Never adopt multi-agent without a single-agent baseline and a CAU that shows the overhead pays.
6. **Instrument first.** No structured transcript, no evaluation. Coordination, credit assignment, and reproducibility all depend on tracing every action.

---

## Appendix A — A MAST checklist judge (LLM-as-judge for trajectories)

The rule-based scorer earlier is reproducible but brittle: `"def "` is a poor proxy for "wrote code," and no substring rule can tell whether an agent *proceeded on an unstated assumption*. For process scoring at production quality you promote the MAST checklist to an **LLM-as-judge** that reads the transcript and answers one structured question per failure mode, each with a citing step so the verdict is auditable. Below is the scaffolding; the `call_llm` body is where your provider's structured-output call goes. Use an **independent** model family from the ones under test to avoid self-preference.

```python
"""MAST checklist judge: turn a transcript into a per-failure-mode verdict with citations.
The judge model should be from a DIFFERENT family than the agents under test."""
import json
from dataclasses import dataclass

# One question per MAST mode. Keep them yes/no and demand a citing step.
MAST_CHECKS = {
    "FC1_role_violation":   "Did any agent act outside its assigned role (e.g., a reviewer writing code)?",
    "FC1_lost_history":     "Did any agent forget or contradict a decision made earlier in the transcript?",
    "FC1_no_stop_cond":     "Did the system fail to recognize when the task was complete?",
    "FC2_wrong_assumption": "Did any agent proceed on an unstated assumption instead of asking or verifying?",
    "FC2_ignored_input":    "Was any agent's message received and then not acted upon by its recipient?",
    "FC2_withheld_info":    "Did any agent hold back information (e.g., data provenance) that others needed?",
    "FC2_derailment":       "Did the conversation drift away from the original objective?",
    "FC3_no_verification":  "Was the final output never checked against the task requirements?",
    "FC3_bad_verification": "Did a verifier approve an output that was actually wrong or unchecked on a key property?",
}

JUDGE_SYSTEM = (
    "You are an impartial evaluator of multi-agent transcripts. For each question, "
    "answer strictly in JSON: {\"present\": true|false, \"step\": <int or null>, "
    "\"evidence\": \"<short quote>\"}. Cite the earliest step where the issue first occurs. "
    "Do not reward fluent writing; judge only the behavior asked about."
)

@dataclass
class Verdict:
    mode: str
    present: bool
    step: int | None
    evidence: str

def call_llm(system: str, user: str) -> dict:
    """Replace with your provider's JSON/structured-output call (temperature 0)."""
    raise NotImplementedError

def judge_transcript(transcript_json: str) -> list[Verdict]:
    verdicts = []
    for mode, question in MAST_CHECKS.items():
        user = f"TRANSCRIPT:\n{transcript_json}\n\nQUESTION: {question}"
        out = call_llm(JUDGE_SYSTEM, user)     # {"present":..., "step":..., "evidence":...}
        verdicts.append(Verdict(mode, out["present"], out.get("step"), out.get("evidence", "")))
    return verdicts

def failure_mode_rates(all_verdicts: list[list[Verdict]]) -> dict:
    """Aggregate across an eval set: share of transcripts exhibiting each mode."""
    n = len(all_verdicts) or 1
    rates = {mode: 0 for mode in MAST_CHECKS}
    for vs in all_verdicts:
        for v in vs:
            if v.present:
                rates[v.mode] += 1
    return {m: round(c / n, 3) for m, c in rates.items()}
```

Two disciplines make this trustworthy. **Validate the judge before you trust it:** hand-label 30–50 transcripts, run the judge, and require high agreement (Cohen's kappa) per mode — exactly the "validate on humans, then scale with the judge" pipeline MAST's authors used. And **decompose the prompt into one narrow question per call** rather than asking for all fourteen at once; narrow questions are far more reliable and each verdict carries its own citing step, so a disputed call is auditable. The payoff is the failure-mode *distribution* across your eval set — the dashboard line that turns "68% pass" into "of the failures, incomplete-verification is 40% and wrong-assumption 25%," which is a directive for what to build next.

> **Saying it out loud.** Two disciplines make a checklist judge trustworthy. First, validate before you trust: hand-label thirty to fifty transcripts, run the judge against them, and require high agreement per mode — that's the same validate-then-scale pipeline the MAST authors used, and skipping it means your failure-mode dashboard is unfalsifiable. Second, decompose into one narrow yes-or-no question per call rather than asking for all fourteen modes at once, and demand a citing step with each verdict, so a disputed call is auditable. Also use a judge from a different model family than the agents under test, or self-preference bias quietly inflates everything. The payoff is the failure-mode distribution, which turns "68% pass" into a directive about what to build next.

---

## Appendix B — A reproducible multi-agent eval-run checklist

A concrete, copy-pastable protocol for evaluating a multi-agent system so results are comparable across runs and defensible in review.

1. **Freeze the eval set.** Curate ~20–50 representative tasks with gold outcomes and, where possible, milestone lists. Include adversarial and ambiguous cases and at least a few with injected tool failures. Version it.
2. **Stand up the single-agent baseline.** The *same* task solved by a well-prompted single agent. Without it, no cost-adjusted utility, no adoption decision.
3. **Instrument.** Confirm every action emits a structured trace row (agent, role, action, inputs, outputs, tokens, latency). Spot-check that a known failure is reproducible from the trace alone.
4. **Run k seeds.** For each task, run the system and the baseline over k≥3 seeds. Record every metric per seed; you will report mean and variance, never a single run.
5. **Score outcome (end-state).** LLM judge (independent family) against a rubric, plus milestone coverage. This is the cheap filter that runs on every case.
6. **Score process (trajectory) on failures.** Run the MAST checklist judge on the cases end-state flagged, plus a random sample of passes (to catch lucky-right processes). Produce the failure-mode distribution.
7. **Score coordination and cost.** Redundancy, ignored-input, role-violation rates; tokens and dollars per task; communication efficiency; goal-drift on long traces.
8. **Assign credit.** Milestone KPIs per agent for routine credit; leave-one-out ablation to find dead-weight or actively-harmful agents (negative \\( \Delta_i \\)); trace localization on the most important failures to name the decisive step.
9. **Compute the decision number.** Cost-adjusted utility vs the baseline. State plainly whether the overhead pays and what a quality point is worth in the product.
10. **Write the directive, not just the score.** The output of an eval run is not "68% pass" — it is "ship/hold, here is the dominant failure mode, and here is the one structural change (verifier / provenance contract / better delegation prompt) that addresses it." Re-run after the change and confirm the mode's rate dropped.

Follow this and your evaluation does the two things a senior interviewer is listening for: it *localizes* failure to a cause, and it *decides* whether the architecture earns its cost.
