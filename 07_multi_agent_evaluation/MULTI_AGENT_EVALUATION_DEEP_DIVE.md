# Multi-Agent Evaluation — A Deep Dive

> "A multi-agent system can produce the right answer while every step of its process was wrong — and it can produce a wrong answer while every individual agent behaved correctly. Evaluating only the answer misses both."

## Why This Matters

Single-agent evaluation asks a comparatively simple question: given an input, did the agent produce a good output? Multi-agent evaluation asks a harder one: given a *society* of agents that talk to each other, hand off work, criticize one another, and share state, did the **system** behave well — and if it did not, *which agent, at which step, caused the failure*?

This distinction is not academic. As soon as you move from one agent to several, three new classes of things can go wrong that simply do not exist in the single-agent world:

1. **The communication channel** — agents misread, ignore, or corrupt each other's messages.
2. **The coordination structure** — the wrong agent does the work, two agents do the same work, or everyone waits for everyone else.
3. **Emergent dynamics** — errors amplify as they propagate, agents converge on a confidently wrong consensus (groupthink), or the system stalls (deadlock).

The economics also change. Anthropic reports that agents use roughly **4x more tokens than chat**, and multi-agent systems roughly **15x more tokens than chat** ([Anthropic, "How we built our multi-agent research system"](https://www.anthropic.com/engineering/multi-agent-research-system)). At 15x the cost, a multi-agent architecture has to *earn* its overhead — and the only way to know whether it does is to evaluate it properly against a single-agent baseline. Evaluation is therefore not just a quality gate; it is the instrument that tells you whether you should be running a multi-agent system at all.

This chapter gives you the intuition, the metrics, a taxonomy of failures grounded in real research, working code, and an honest account of when multi-agent is worth it.

---

## Core Intuition

Hold three ideas in your head before anything else.

**1. Outcome and process are separable.** A pipeline of a planner, a coder, and a reviewer can ship correct code because the coder happened to be right and the reviewer rubber-stamped it without reading — the outcome passed, the process failed. Next time the coder is wrong, the same broken process ships a bug. If your eval only checks the final artifact, you have no early warning. **Evaluate the process, not just the product.**

**2. Failures are systemic, not local.** In the largest empirical study of this to date, Cemri et al. found that most multi-agent failures are *not* "the LLM is dumb" — they are failures of **system design, inter-agent alignment, and verification** ([Cemri et al., "Why Do Multi-Agent LLM Systems Fail?", 2025](https://arxiv.org/abs/2503.13657)). Swapping in a stronger base model often does not fix them, because the fault lives in the *interaction*, not in any single agent's head.

**3. Attribution is the whole game.** In a single-agent trace, blame is trivial — there is one agent. In a multi-agent trace, a wrong final answer might trace back to a planner that under-specified the task 12 steps ago, which no downstream agent could have recovered from. The core new skill of multi-agent evaluation is **credit assignment**: mapping a system-level outcome back to the agent and step responsible for it.

Everything below is in service of those three ideas.

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

A useful mental model: **task outcome is the *what*; the middle five are the *how*; cost is the *whether it was worth it*.** A mature eval scores all three.

### End-state vs step-by-step evaluation

Two philosophies for scoring outcome and process:

- **End-state evaluation** checks only whether the system reached a correct final state, tolerating many valid paths to get there. Anthropic uses this for its research system precisely because "there are often multiple valid paths" to a good research answer ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). It is cheap and path-agnostic but blind to lucky-right processes.
- **Trajectory / step evaluation** scores the sequence of actions and messages. It catches process failures and enables credit assignment but is expensive and requires reference trajectories or a strong judge.

Use end-state for headline pass/fail and trajectory scoring for diagnosis. They answer different questions; you generally want both.

---

## The Credit-Assignment Problem in Depth

Credit assignment is the problem of attributing a system-level outcome to the individual agents and steps that produced it. It is borrowed from reinforcement learning (the "temporal credit assignment problem": which of the many actions in an episode deserves credit for the eventual reward?) and it is *the* hard problem of multi-agent evaluation.

### Why it is hard

- **Delayed effect.** The decision that doomed the run often happened long before the visible failure. A planner that omitted a constraint on step 2 causes a spec violation on step 20; the coder who "produced" the wrong output is not the culprit.
- **Diffuse responsibility.** When five agents each contribute 20% of a flawed argument, no single message is "the bug." Groupthink failures have no localizable owner.
- **Counterfactual ambiguity.** "Agent B caused the failure" really means "had B acted differently, the outcome would have been better." Establishing that requires a counterfactual you usually cannot run.
- **Interaction effects.** Two agents can each be individually correct yet jointly wrong (e.g., both assume the other will handle error-checking).

### Four practical attribution methods

**1. Trace-based localization (annotate the decisive step).** Have a human or LLM judge read the full transcript and mark the *first* step where the trajectory became unrecoverable — the "decisive error." This is exactly the methodology behind MAST: expert annotators labeled traces for failure modes and the step at which each occurred, reaching Cohen's kappa = 0.88 inter-annotator agreement ([Cemri et al., 2025](https://arxiv.org/abs/2503.13657)). Cheap-ish, interpretable, but subjective and hard to scale without an LLM judge.

**2. Ablation / leave-one-out.** Re-run the task with agent \( i \) removed (or replaced by a no-op / a stronger model / a weaker model). The change in system performance estimates that agent's marginal contribution:

\[ \Delta_i = V(\text{system}) - V(\text{system} \setminus i) \]

where \( V \) is your outcome score. Large positive \( \Delta_i \) means agent \( i \) is load-bearing; \( \Delta_i \approx 0 \) means it is dead weight (a candidate for deletion — cost savings!). Requires re-running, which multiplies cost.

**3. Shapley-value attribution.** Leave-one-out ignores interactions. The Shapley value fairly distributes the total system value across agents by averaging each agent's marginal contribution over *all* orderings of agent inclusion:

\[ \phi_i = \sum_{S \subseteq N \setminus \{i\}} \frac{|S|!\,(|N|-|S|-1)!}{|N|!} \big[ V(S \cup \{i\}) - V(S) \big] \]

Here \( N \) is the set of agents, \( S \) a coalition not containing \( i \), and \( V(S) \) the score achieved by only the agents in \( S \). Shapley values are the principled answer to "how much did each agent contribute," but they cost \( O(2^{|N|}) \) re-runs — feasible for 3–4 agents, not for 30.

**4. Milestone / process rewards.** Decompose the task into intermediate milestones and check which agent achieved which. MultiAgentBench uses exactly this: **milestone-based KPIs** that score whether key sub-goals were reached, separating collaboration quality from raw task score ([Zhu et al., "MultiAgentBench", ACL 2025](https://arxiv.org/abs/2503.01935)). This gives per-agent, per-milestone credit without combinatorial re-runs, at the cost of needing hand-authored milestones.

**Rule of thumb:** use trace-based localization for debugging a specific failure, milestone KPIs for routine per-agent scoring, leave-one-out for pruning agents, and Shapley only when you have ≤4 agents and need defensible attribution.

---

## A Taxonomy of Multi-Agent Failure Modes

The most useful empirical map here is **MAST (Multi-Agent System failure Taxonomy)** from Cemri et al., built by annotating 200+ execution traces across seven frameworks (MetaGPT, ChatDev, HyperAgent, AppWorld, AG2, Magentic-One, OpenManus) and clustering into **14 failure modes under 3 categories** ([arXiv:2503.13657](https://arxiv.org/abs/2503.13657)). The percentages below are the share of failures each category accounted for in their study.

### FC1 — Specification & System-Design Issues (~42% of failures)

The system is poorly specified or structured before any conversation goes wrong.

| Mode | What it looks like |
|---|---|
| Fail to follow task requirements | System ignores an explicit constraint from the prompt |
| Disobey role specification | Reviewer starts writing code; planner starts executing |
| Step repetition | Agents redo work already completed |
| Loss of conversation history | Context is dropped; an agent "forgets" an earlier decision |
| Unaware of stopping conditions | No agent knows when the task is done |

### FC2 — Inter-Agent Misalignment (~37% of failures)

The agents are individually capable but fail to align with each other.

| Mode | What it looks like |
|---|---|
| Conversation reset | Dialogue unexpectedly restarts, discarding progress |
| Proceeding on wrong assumptions | An agent guesses instead of asking a clarifying question |
| Task derailment | Conversation drifts off the original objective |
| Withholding crucial information | An agent knows something relevant but never shares it |
| Ignoring other agents' input | A message is received and simply not acted on |
| Reasoning–action mismatch | Agent says one thing, does another |

### FC3 — Task Verification & Termination (~21% of failures)

The system fails to check its own work.

| Mode | What it looks like |
|---|---|
| Premature termination | System stops before the goal is met |
| No / incomplete verification | Output is never checked against requirements |
| Incorrect verification | The checker approves a wrong answer |

### Cross-cutting emergent failures

Some failures are not single modes but *dynamics* over the interaction graph. These are the ones single-agent evaluation has no vocabulary for:

- **Cascading errors / error propagation.** Agent A's small mistake becomes agent B's premise, which B builds on confidently, and so on. The error is *amplified* rather than *contained*. A robust system has a verification agent that breaks the chain (FC3 is where this defense lives or dies).
- **Groupthink / sycophantic convergence.** In debate or committee setups, agents converge on a confident consensus that is wrong, because each defers to the apparent majority instead of reasoning independently. Multi-agent debate can *improve* factuality when agents genuinely critique ([Du et al., "Improving Factuality and Reasoning through Multiagent Debate", 2023](https://arxiv.org/abs/2305.14325)) — but the same setup degrades into mutual agreement when critique collapses.
- **Deadlock / livelock.** A waits for B, B waits for A (deadlock); or agents keep politely handing the task back and forth without progress (livelock). Both surface as "unaware of stopping conditions" plus "step repetition."
- **Redundant work / cost blowup.** Two subagents independently research the same subtopic. The outcome may still be correct, but you paid twice — a *coordination* failure visible only in the cost dimension.

**Worked micro-example of error propagation.** A planner instructs: "compute revenue for Q3." The data agent silently uses Q2 data (wrong assumption, FC2). The analyst computes a beautiful, correct-looking growth rate on the wrong numbers. The reviewer checks the *arithmetic* (correct) but not the *data source* (incomplete verification, FC3). Final answer: confidently wrong. No single agent was "broken"; the *system* had no data-provenance check. This is why MAST's authors stress that better *base models alone do not fix* these failures — the fix is structural.

---

## Worked Example: Scoring a Multi-Agent Transcript

Below is a self-contained Python script that scores a multi-agent transcript on three axes: **task success**, **per-agent contribution** (a simple milestone-based credit assignment), and a **coordination metric** (how cleanly work was routed and handed off). It uses only the standard library so it runs anywhere. The judging here is rule-based for reproducibility; in practice you would swap the milestone checks for an LLM-as-judge call.

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

Two things worth noticing. First, the **planner contributed 0 milestones** — leave-one-out or a cost review should ask whether it earns its tokens. Second, this transcript is clean; to see the metrics bite, imagine the reviewer message were `Message(4, "reviewer", "analyst", "def recheck(): ...")` — the role-violation term would fire, dragging the coordination score below 1.0 and flagging an FC1 "disobey role specification" failure.

---

## Metrics, Formally

Precise definitions with micro-examples. All use MathJax delimiters.

### Task Success Rate (TSR)

Fraction of tasks the *system* fully completed:

\[ \text{TSR} = \frac{1}{|D|} \sum_{t \in D} \mathbb{1}[\text{system solved } t] \]

*Micro-example.* Over \( |D| = 50 \) tasks the system fully solves 34, so \( \text{TSR} = 34/50 = 0.68 \).

### Milestone Coverage

Fraction of predefined sub-goals achieved, averaged over tasks — a partial-credit signal that survives when TSR is 0:

\[ \text{MC} = \frac{1}{|D|}\sum_{t \in D} \frac{|\text{milestones hit}_t|}{|\text{milestones}_t|} \]

*Micro-example.* A task with 4 milestones where 3 are hit contributes \( 3/4 = 0.75 \). A system can have low TSR but high MC — it gets *most* of the way and fails at the last step (often FC3 premature termination).

### Per-Agent Credit (Shapley)

Defined earlier; the key property is **efficiency**: credits sum to the total system value,

\[ \sum_{i \in N} \phi_i = V(N) \]

*Micro-example.* Two agents, \( V(\varnothing)=0,\ V(\{A\})=0.4,\ V(\{B\})=0.2,\ V(\{A,B\})=1.0 \). Then \( \phi_A = \tfrac12(0.4-0) + \tfrac12(1.0-0.2) = 0.6 \) and \( \phi_B = 0.4 \), summing to \( V(\{A,B\}) = 1.0 \). Note both exceed their solo scores — the *interaction* created value, which leave-one-out alone would misattribute.

### Communication Efficiency

Useful information moved per token spent. One simple operationalization: milestones achieved per thousand tokens of inter-agent messages,

\[ \text{CE} = \frac{\text{milestones hit}}{(\text{message tokens})/1000} \]

*Micro-example.* 4 milestones over 8,000 message tokens gives \( \text{CE} = 4/8 = 0.5 \) milestones per 1k tokens. Falling CE across runs is an early sign of chatter/redundancy.

### Coordination Score

The composite used in the code, generalized to a weighted penalty average with weights \( w_k \) summing to 1:

\[ \text{Coord} = 1 - \sum_{k} w_k \, p_k, \qquad p_k \in [0,1] \]

where each \( p_k \) is a penalty rate (redundancy, role violations, ignored messages). *Micro-example.* Equal weights with \( p = (0.1, 0.0, 0.2) \) give \( \text{Coord} = 1 - \tfrac13(0.3) = 0.9 \).

### Cost-Adjusted Utility (the honest metric)

The one that decides whether multi-agent was worth it — quality per unit cost, compared to a baseline:

\[ \text{CAU} = \frac{V_{\text{multi}} - V_{\text{single}}}{C_{\text{multi}} - C_{\text{single}}} \]

*Micro-example.* Multi-agent scores 0.90 vs single-agent 0.75 (\( \Delta V = 0.15 \)) but costs 15x the tokens (say \( \Delta C = 14 \) baseline-units). \( \text{CAU} = 0.15/14 \approx 0.011 \) quality points per baseline-unit of extra cost. Whether that clears your bar depends entirely on how much a quality point is worth in your product.

---

## Single-Agent vs Multi-Agent: When Is It Worth It?

The uncomfortable truth: **most tasks do not need multiple agents.** Multi-agent architectures buy you parallel breadth and specialization at a steep cost in tokens, latency, coordination complexity, and new failure modes. Anthropic's own guidance is that multi-agent shines for *breadth-first, parallelizable* problems and is a poor fit for tightly coupled tasks where agents must share evolving context ([Anthropic, "When to use multi-agent systems"](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)).

| Factor | Single-agent | Multi-agent |
|---|---|---|
| Token cost | ~1x (baseline) | ~15x chat / several x single-agent ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)) |
| Latency | Lower, sequential | Higher per-agent, but parallelizable across subagents |
| Best for | Tightly coupled, sequential reasoning; shared evolving context | Breadth-first search; independent parallel subtasks; many specialized tools |
| Failure surface | One agent's mistakes | + communication, coordination, emergent (cascade, groupthink, deadlock) |
| Debuggability | Straightforward trace | Hard: non-deterministic, cross-agent, needs full tracing |
| Credit assignment | Trivial | Genuinely hard (this chapter) |
| When it *earns* its cost | Default choice | Task value is high AND work truly parallelizes AND context exceeds one window |

Anthropic reports a **90.2%** improvement of a multi-agent (Opus 4 lead + subagents) system over single-agent Opus 4 on an internal research eval — a large gain, but on a task that is *inherently breadth-first* (explore many sources in parallel) and *high-value* enough to justify 15x tokens ([Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)). That is the profile where multi-agent wins.

**Diminishing returns are real.** Adding a fourth or fifth agent to a coordination-heavy task frequently *lowers* quality: more agents means more messages, more opportunities for FC2 misalignment, and more chances for one bad hand-off to cascade. MultiAgentBench found that *coordination topology matters more than agent count* — graph-structured coordination beat other topologies on research tasks, and cognitive planning added only ~3% to milestone achievement ([Zhu et al., 2025](https://arxiv.org/abs/2503.01935)). The lesson: **structure your agents well before you add more of them, and always keep a single-agent baseline in your eval to prove the overhead pays.**

---

## Pitfalls in Evaluating Multi-Agent Systems

The evaluation itself has failure modes. Watch for these.

- **Grading only the final answer.** The lucky-right process (correct output, broken process) passes and reappears as a regression later. Always score trajectory *and* end-state.
- **No single-agent baseline.** Without it you cannot compute cost-adjusted utility, and you will keep an expensive multi-agent system that a single agent matches.
- **Ignoring cost.** A quality win at 15x tokens may be a net loss. Report cost alongside every quality number.
- **Judge contamination / self-preference.** Using one of the system's own agents (or same-family model) as the LLM judge inflates scores. Use an independent judge and spot-check with humans, as Anthropic does to catch hallucinated answers automated judges miss.
- **Non-determinism mistaken for signal.** Multi-agent runs vary run-to-run. A single run is noise; report means and variance over multiple seeds.
- **Attribution by vibes.** Declaring "the coder was at fault" without trace localization, ablation, or milestone evidence. Credit assignment needs a method, not an intuition.
- **Over-fitting to one topology.** Evaluating only your favorite orchestration structure hides whether a chain would have beaten your graph (or vice versa). Vary the topology.
- **Milestone leakage.** If milestones are too granular they become a checklist the agents game; too coarse and they give no per-agent signal. Calibrate against human judgments.

---

## Tools & Benchmarks

| Name | Type | What it gives you | Link |
|---|---|---|---|
| MAST | Taxonomy + dataset | 14 failure modes / 3 categories; 200+ annotated traces; an LLM-judge annotator | [arXiv:2503.13657](https://arxiv.org/abs/2503.13657) |
| MultiAgentBench (MARBLE) | Benchmark | Milestone KPIs; collaboration & competition scenarios; star/chain/tree/graph topologies | [arXiv:2503.01935](https://arxiv.org/abs/2503.01935) |
| Multiagent Debate | Method + code | Debate protocol that improves factuality/reasoning; baseline for consensus dynamics | [arXiv:2305.14325](https://arxiv.org/abs/2305.14325) · [code](https://github.com/composable-models/llm_multiagent_debate) |
| AutoGen (AG2) | Framework | Conversable multi-agent orchestration; traces to evaluate | [microsoft.github.io/autogen](https://microsoft.github.io/autogen/) |
| CrewAI | Framework | Role/goal-based crews; role-adherence evaluation surface | [docs.crewai.com](https://docs.crewai.com/) |
| LangGraph | Framework | Graph-structured agent workflows; explicit state for tracing | [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/) |
| OpenAI Agents SDK (ex-Swarm) | Framework | Lightweight handoffs between agents; simple coordination to eval | [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/) |
| LangSmith / Langfuse | Observability | Full multi-agent tracing needed for credit assignment & debugging | [langfuse.com](https://langfuse.com/) |

---

## Interviewer Q&A

**Q1. Why can't you just evaluate a multi-agent system by checking its final output?**
Because outcome and process are separable. A system can produce the right answer through a broken process (the coder happened to be right; the reviewer never actually checked) — that passes your eval and then regresses the moment the lucky step goes wrong. And a system can fail while every individual agent behaved correctly, because the fault was in the *interaction*. You need trajectory scoring and credit assignment on top of end-state checking.

**Q2. What is the credit-assignment problem and how do you approach it?**
It is attributing a system-level outcome to the specific agent and step that caused it — hard because effects are delayed, responsibility is diffuse, and true attribution is counterfactual. Four practical methods: trace-based localization of the decisive error (the MAST approach), leave-one-out ablation for marginal contribution, Shapley values for principled attribution when you have ≤4 agents, and milestone-based KPIs for scalable per-agent credit.

**Q3. Name the main categories of multi-agent failure.**
Using MAST: (1) specification/system-design issues — bad roles, lost history, no stopping condition (~42% of failures); (2) inter-agent misalignment — wrong assumptions, ignored messages, withheld information (~37%); (3) task verification failures — premature termination, no or incorrect verification (~21%). Plus cross-cutting emergent dynamics: cascading errors, groupthink, and deadlock.

**Q4. When is a multi-agent system actually worth the cost?**
When the task is high-value, genuinely breadth-first / parallelizable, and its context exceeds a single window. Multi-agent uses roughly 15x the tokens of chat, so a small quality gain rarely pays. Anthropic saw a ~90% gain on a research task that is inherently parallel — but the same architecture hurts on tightly coupled sequential tasks. Always keep a single-agent baseline and report cost-adjusted utility.

**Q5. How would you detect error propagation / cascading failures in a transcript?**
Look for a low-confidence or wrong assertion early in the trace that later messages build on without re-checking, combined with weak or absent verification (FC3). Concretely: trace-localize the first decisive error, then confirm no downstream agent challenged it. A healthy system has a verification agent that breaks the chain; its absence is the structural bug, and stronger base models alone won't fix it.

**Q6. What's the difference between end-state and trajectory evaluation, and when do you use each?**
End-state checks only the final state, tolerating multiple valid paths — cheap, path-agnostic, good for headline pass/fail (Anthropic uses it for research). Trajectory evaluation scores the sequence of actions/messages — expensive but necessary for catching process failures and doing credit assignment. Use end-state for the top-line metric, trajectory for diagnosis; you usually want both.

**Q7. Does adding more agents reliably improve performance?**
No — diminishing and often negative returns. More agents mean more messages and more chances for misalignment and cascades. MultiAgentBench found coordination *topology* (graph beat chain/tree/star on research) mattered more than agent count, and elaborate planning added only ~3%. Structure the agents well before adding more, and prove each additional agent's marginal contribution with ablation.

**Q8. What are the traps in evaluating multi-agent systems themselves?**
Grading only the final answer; no single-agent baseline; ignoring token cost; using a same-family model as judge (self-preference); treating a single non-deterministic run as signal; and attributing blame by intuition instead of a method. Each of these makes a broken or overpriced system look good.

---

## Further Reading

- Cemri et al., "Why Do Multi-Agent LLM Systems Fail?" (MAST taxonomy, NeurIPS 2025) — https://arxiv.org/abs/2503.13657
- Zhu et al., "MultiAgentBench: Evaluating the Collaboration and Competition of LLM agents" (ACL 2025) — https://arxiv.org/abs/2503.01935
- Du et al., "Improving Factuality and Reasoning in Language Models through Multiagent Debate" (ICML 2024) — https://arxiv.org/abs/2305.14325
- Anthropic, "How we built our multi-agent research system" — https://www.anthropic.com/engineering/multi-agent-research-system
- Anthropic / Claude, "When to use multi-agent systems (and when not to)" — https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them
- AutoGen (AG2) documentation — https://microsoft.github.io/autogen/
- CrewAI documentation — https://docs.crewai.com/
- LangGraph documentation — https://langchain-ai.github.io/langgraph/
- OpenAI Agents SDK — https://openai.github.io/openai-agents-python/
- Multiagent Debate reference implementation — https://github.com/composable-models/llm_multiagent_debate
