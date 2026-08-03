# Agentic AI Fundamentals — A Deep Dive

> **Why this matters for evaluation.** You cannot evaluate what you cannot describe. An agent is not a single function that maps a prompt to an answer — it is a *process* that unfolds over many steps, branches on its own decisions, calls out to the world, and remembers (or forgets) as it goes. Every one of those degrees of freedom is a place where the system can succeed, fail, or half-succeed. Before you can build a benchmark, write a judge, or read a trace, you need a precise mental model of what an agent *is*, what it is *made of*, and *how it moves*. This chapter builds that model, and at every step names the failure modes that your evaluation will have to catch.

---

## 1. Core intuition: what an agent actually is

Start with the plainest possible definition, the one Anthropic uses in [*Building Effective Agents*](https://www.anthropic.com/engineering/building-effective-agents):

> An **agent** is an LLM that **dynamically directs its own process and tool usage**, running in a **loop**, using **feedback from the environment** to decide what to do next — and deciding *for itself* when it is done.

Contrast that with a plain LLM call, which is a single forward pass: text in, text out, no memory of what came before, no way to act on the world, no second chance. And contrast it with a **workflow**, where an LLM is embedded in *predefined code paths* — the control flow is fixed by a human programmer, and the model only fills in blanks.

The one word that separates an agent from everything else is **control**. In a workflow, the *code* decides the order of steps. In an agent, the *model* decides — at run time, based on what it just saw. The model chooses which tool to call, with what arguments, whether the result was good enough, and whether to stop. That transfer of control from code to model is exactly what makes agents powerful *and* exactly what makes them hard to evaluate.

A useful one-liner: **an agent is a policy in a loop over an environment.** In reinforcement-learning terms, the LLM is the policy \( \pi \) that maps a state (the accumulated context) to an action (a tool call or a final answer); the environment returns an observation; the loop repeats until the policy emits "done" or a budget runs out.

### Why evaluating an agent is harder than grading one LLM output

| A single LLM call | An agent |
|---|---|
| One input, one output. Grade the output. | A *trajectory*: many inputs, tool calls, observations, and a final output. |
| Deterministic-ish given fixed sampling. | Branches on its own choices → wildly different paths on reruns. |
| No side effects. | Sends emails, writes files, spends money, mutates databases. |
| Correctness ≈ "is the text right?" | Correctness = right answer **and** right *process* (didn't delete the prod table on the way). |
| Errors are visible in the output. | Errors compound silently across steps and only surface at the end. |
| Cost is one call. | Cost = sum over an unknown number of calls; can blow up on a loop. |

The core evaluation problem: **the final answer can be right for the wrong reasons, or wrong for reasons that have nothing to do with the model's intelligence** (a flaky tool, a stale memory, a truncated context). If you only grade the last message, you are blind to most of what actually happened.

---

## 2. Anatomy of an agent

An agent is an assembly of parts. Below, each component is defined precisely, given its role, and — critically for us — paired with the ways it fails. Keep the failure column; it is the seed list for your test suite.

### 2.1 The LLM core (the "reasoner" / policy)

**What it is.** The language model that, given the current context, produces the next thought and the next action. This is the decision-maker — the policy.

**Role.** Interpret the goal, decompose it, choose tools, read observations, judge progress, decide when to stop, and write the final answer.

**Failure modes to evaluate.**
- *Hallucinated tool calls* — invents a tool that does not exist, or arguments in the wrong schema.
- *Reasoning errors* — sound-looking chain of thought that reaches a wrong conclusion.
- *Refusal / over-caution* — stops or asks for confirmation when it should just act (and vice versa).
- *Instruction drift* — forgets the original goal after many steps ("goal decay").
- *Sycophancy* — accepts a bad tool result as truth because it "looks authoritative."

### 2.2 Tools (the hands)

**What it is.** Functions the agent can invoke to sense or change the world: web search, a code interpreter, a SQL query, an HTTP call, a file write. Each tool has a **name**, a **description**, and a **typed schema** for its arguments. The model chooses tools purely from those descriptions.

**Role.** Bridge the gap between "the model knows things" and "the model can *do* things." Tools are how an agent gets *ground truth* — real feedback from a real environment — instead of guessing.

**Failure modes to evaluate.**
- *Wrong tool selection* — uses search when it should calculate.
- *Malformed arguments* — right tool, wrong/invalid parameters.
- *Tool errors handled poorly* — a 500 or a timeout that the agent ignores or loops on.
- *Bad tool descriptions* — the model can only be as good as the schema it reads; ambiguous descriptions cause silent misuse. (This is an *engineering* failure that looks like a *model* failure — evaluation must distinguish them.)
- *Unsafe execution* — the classic `eval()` calculator that runs arbitrary code (see §7).

### 2.3 Memory & state

**What it is.** Everything the agent carries forward. In practice this splits into several kinds (detailed in §6): the **context window** (working memory), a **scratchpad** (the running trace of thoughts/actions/observations), and **long-term memory** (a store — often a vector database — the agent reads from and writes to across steps or sessions).

**Role.** Provide continuity. Without memory an agent cannot do multi-step work: it would forget the goal, repeat tool calls, and lose intermediate results.

**Failure modes to evaluate.** Context overflow / truncation, retrieval of stale or irrelevant memories, memory poisoning (a bad fact written once and re-read forever), and cross-session leakage. Memory bugs are insidious because they surface *later*, far from their cause (§6).

### 2.4 Planner

**What it is.** The mechanism that turns a goal into a sequence (or tree) of sub-steps. Planning can be *implicit* (the LLM plans one step at a time inside a ReAct loop) or *explicit* (a separate "plan first, then execute" phase, sometimes a distinct model call that emits a task list).

**Role.** Impose structure on open-ended problems so the agent does not wander.

**Failure modes to evaluate.**
- *Under-planning* — dives into actions with no decomposition, gets lost.
- *Over-planning* — produces an elaborate plan and never adapts when reality diverges.
- *No replanning* — the plan is wrong after step 2 but the agent marches on ("plan rigidity").
- *Infinite loops* — re-plans the same failing step forever.

### 2.5 Controller / orchestrator (the loop driver)

**What it is.** The code that actually *runs* the loop: it calls the model, parses the model's chosen action, executes the tool, appends the observation, checks stopping conditions (max iterations, budget, a "done" signal), and — in multi-agent systems — routes work between sub-agents. In frameworks this is the graph/runtime (LangGraph's state machine, the OpenAI Agents SDK runner, CrewAI's crew).

**Role.** Turn a stateless model into a stateful process. The controller owns the guardrails: iteration caps, timeouts, retries, human-in-the-loop checkpoints.

**Failure modes to evaluate.**
- *Missing or too-high iteration cap* → runaway cost.
- *Bad stop condition* → stops too early (incomplete) or never (looping).
- *Silent error swallowing* → tool fails, controller feeds an empty observation, agent hallucinates around it.
- *Bad routing* (multi-agent) → sends the sub-task to the wrong specialist.

> **Mental model.** LLM core = the brain. Tools = the hands. Memory = the notebook. Planner = the intent. Controller = the nervous system that wires them together and keeps the loop honest. Evaluation must probe each *and* their interactions.

---

## 3. The agent loop: perceive → plan → act → observe

Every agent, under all the framework branding, runs some version of this cycle:

```
        ┌─────────────────────────────────────────────┐
        │                                             │
        ▼                                             │
   ┌─────────┐   ┌────────┐   ┌───────┐   ┌──────────┐│
   │ PERCEIVE│──▶│  PLAN  │──▶│  ACT  │──▶│ OBSERVE  ││
   │ (read   │   │(reason │   │(call  │   │(read tool││
   │  state) │   │ /decide│   │ tool) │   │  result) ││
   └─────────┘   └────────┘   └───────┘   └────┬─────┘│
                                               │      │
                              done? ───no──────┘──────┘
                                │
                               yes
                                ▼
                          ┌───────────┐
                          │ FINAL ANS │
                          └───────────┘
```

- **Perceive** — assemble the current state: the goal, the scratchpad so far, any retrieved memories, the tool catalog.
- **Plan / reason** — the LLM produces a *thought* and decides the next *action* (which tool, which arguments) or that it is finished.
- **Act** — the controller executes the chosen tool.
- **Observe** — the tool's result (or error) is appended to the scratchpad, becoming part of the next perception.

### ReAct: interleaving reasoning and acting

The dominant realization of this loop is **ReAct** ([Yao et al., 2022, *Synergizing Reasoning and Acting in Language Models*](https://arxiv.org/abs/2210.03629)). ReAct's insight: don't separate "think" from "do." Interleave them as a repeating triple — **Thought → Action → Observation** — so that reasoning guides the next action *and* fresh observations correct the reasoning. This grounds the chain of thought in real feedback (reducing hallucination) and lets the model form plans that survive contact with reality.

### Beyond ReAct

- **Reflexion** ([Shinn et al., 2023](https://arxiv.org/abs/2303.11366)) — after a failed attempt, the agent writes a natural-language *self-reflection* ("I failed because I searched the wrong term") into memory and retries. It is "verbal reinforcement learning": no weight updates, just a linguistic critique that improves the next trajectory.
- **Plan-and-Execute / ReWOO** — plan the whole task up front, then execute, reducing per-step LLM calls (cheaper, but weaker at adapting mid-task).
- **Tree-of-Thoughts** — explore *multiple* reasoning branches and search over them, rather than committing to one linear chain.

### A concrete trace

**Task:** *"What is the total 2025 revenue of the top-2 US airlines by passengers, and is that more than Apple's Q1 2025 revenue?"*

```
Thought:  I need passenger rankings, two revenue figures, and Apple's Q1.
Action:   web_search("top US airlines by passengers 2025")
Observation: "1) American Airlines  2) Delta Air Lines ..."

Thought:  Get American's 2025 revenue.
Action:   web_search("American Airlines 2025 annual revenue")
Observation: "American Airlines 2025 revenue: $54.2B"

Thought:  Now Delta's.
Action:   web_search("Delta Air Lines 2025 annual revenue")
Observation: "Delta 2025 revenue: $61.6B"

Thought:  Sum them.
Action:   calculator("54.2 + 61.6")
Observation: 115.8

Thought:  Get Apple's Q1 2025 revenue to compare.
Action:   web_search("Apple Q1 2025 revenue")
Observation: "Apple fiscal Q1 2025 revenue: $124.3B"

Thought:  115.8B < 124.3B. I can answer.
Action:   finish("Top-2 US airlines' combined 2025 revenue ≈ $115.8B,
          which is LESS than Apple's Q1 2025 revenue of $124.3B.")
```

**What you would evaluate in this single trace:** Did it pick the right airlines (perception/grounding)? Are the three retrieved numbers correct (tool-result faithfulness)? Is the arithmetic right (tool use)? Did it compare the *right* quantities — full-year airline vs. *one quarter* of Apple (a subtle reasoning trap)? Did it stop at the right moment? Notice the last answer can be *stated confidently and still be wrong* if any one observation was stale — which is why per-step grading beats final-answer grading.

---

## 4. Agent vs. workflow vs. single LLM call

This is the distinction that most interview questions and most architecture reviews hinge on. Anthropic frames it as **workflows** (LLMs orchestrated through *predefined code paths*) vs. **agents** (LLMs that *dynamically direct their own* process).

| Dimension | Single LLM call | Workflow | Agent |
|---|---|---|---|
| Who controls the flow | The prompt | **The code** (fixed paths) | **The model** (dynamic) |
| Number of steps | 1 | Fixed, known in advance | Unknown, decided at run time |
| Tools | None | Called at fixed points | Chosen by the model, when it wants |
| Adapts mid-task | No | No | Yes |
| Determinism | Highest | High | Lowest |
| Cost predictability | Exact | Bounded | **Unbounded** (needs caps) |
| Ease of evaluation | Easy | Moderate | **Hard** |
| Failure blast radius | Small | Medium | Large (side effects) |

**Named workflow patterns** (from *Building Effective Agents*) — worth knowing because reviewers ask "could this be a workflow instead?":

1. **Prompt chaining** — decompose into fixed sequential LLM steps.
2. **Routing** — classify the input, dispatch to a specialized path.
3. **Parallelization** — run steps concurrently (sectioning or voting), then aggregate.
4. **Orchestrator-workers** — a lead LLM dynamically splits work among worker LLMs.
5. **Evaluator-optimizer** — one LLM generates, another critiques, loop until good.

**When to use each:**
- **Single call** — the task fits in one shot: classify, summarize, rewrite. Add nothing more.
- **Workflow** — the task decomposes into *known, stable* steps. You want predictability, testability, and bounded cost. Most production "AI features" should be workflows.
- **Agent** — the task is *open-ended*, the number of steps *cannot be known in advance*, and flexibility is worth the loss of control. Think open-ended research, debugging, "do X however it takes."

> Anthropic's guiding rule: **"Find the simplest solution possible, and only increase complexity when needed."** An agent you can't evaluate or afford is worse than a workflow you can. Much of good agent engineering is *resisting* the agent.

---

## 5. Memory & state

Memory is where agents accumulate — and corrupt — their understanding of a task. Evaluators must know the types and their characteristic bugs.

| Type | Mechanism | Lifetime | Typical bug that shows up in eval |
|---|---|---|---|
| **Working / context** | The LLM's context window itself | This step | Truncation drops the goal or an early key fact → later steps go off-course |
| **Scratchpad** | Appended Thought/Action/Observation trace | This task/run | Grows unbounded → context overflow; or old failed attempts pollute reasoning |
| **Episodic** | Stored records of past events/trajectories | Across sessions | Retrieves a *similar-but-wrong* past episode and over-applies it |
| **Long-term / semantic** | Vector DB + embeddings, retrieved by similarity | Persistent | Retrieves stale/irrelevant chunks; embeddings miss the actually-relevant fact |
| **Procedural** | Learned/stored skills, tool recipes, reflections | Persistent | A once-wrong "lesson" (bad reflection) is re-applied forever |

**Mechanisms in practice.**
- *Short-term* is usually just "keep the last N turns in context," possibly with **summarization/compaction** when it gets long (which itself can drop a crucial detail — a bug source).
- *Long-term* is typically **retrieval-augmented**: write facts as embeddings, retrieve top-\( k \) by cosine similarity at each step. Quality is bounded by retrieval quality, so retrieval must be evaluated *separately*.

**How memory bugs surface in evaluation — the key point:** memory failures are **non-local**. A fact poisoned or dropped at step 2 causes a wrong action at step 9. If your evaluation only inspects the final answer, you will misattribute the failure to "bad reasoning" when the real cause was retrieval or truncation. Good agent evals therefore log the *full state at each step* (what was in context, what was retrieved) so failures can be traced to their origin. Concretely, test for: *repeated identical tool calls* (agent forgot it already did that), *contradiction with an earlier established fact* (context loss), and *acting on an outdated value* (stale memory).

---

## 6. A fully worked example

A small but *correct* and *safe* ReAct-style agent. It is deliberately close to the repository's skeleton so you can see the difference between "looks like an agent" and "actually loops on feedback." Two fixes matter for evaluation: the calculator uses a **safe** evaluator (no `eval`), and the loop **actually re-plans using observations** rather than declaring victory on the first non-null result.

```python
"""A minimal, safe, ReAct-style agent with a real perceive-plan-act-observe loop.

The LLM is stubbed by `decide()` so the example runs deterministically and the
loop logic is inspectable. In production, `decide()` is one LLM call that reads
the scratchpad and returns the next action as structured output (tool + args)
or a final answer.
"""
from __future__ import annotations
import ast, operator, math
from dataclasses import dataclass, field
from typing import Any, Callable


# ---- Tools -------------------------------------------------------------------

_ALLOWED_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg,
}

def safe_calculator(expression: str) -> float:
    """Evaluate arithmetic WITHOUT eval(). Rejects anything but numbers + math."""
    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPS:
            return _ALLOWED_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPS:
            return _ALLOWED_OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported expression element: {ast.dump(node)}")
    return _eval(ast.parse(expression, mode="eval").body)


def fake_search(query: str) -> str:
    """Stubbed knowledge tool. In production: a real search/RAG call."""
    facts = {
        "speed of light m/s": "299792458",
        "seconds in a day": "86400",
    }
    for key, val in facts.items():
        if all(w in query.lower() for w in key.split()):
            return val
    return "NO_RESULT"


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[..., Any]


# ---- Agent -------------------------------------------------------------------

@dataclass
class Step:
    thought: str
    action: str
    args: dict
    observation: Any = None

@dataclass
class Agent:
    tools: dict[str, Tool]
    max_steps: int = 6
    trace: list[Step] = field(default_factory=list)

    def decide(self, goal: str) -> Step:
        """Stand-in for the LLM policy. Reads the scratchpad, returns next step.
        Real agents return this from a single structured LLM call."""
        seen = {s.action: s.observation for s in self.trace}
        if "light travels in one day" in goal:
            if "search_c" not in seen:
                return Step("Need c in m/s.", "search_c",
                            {"query": "speed of light m/s"})
            if "search_day" not in seen:
                return Step("Need seconds per day.", "search_day",
                            {"query": "seconds in a day"})
            if "calc" not in seen:
                c, day = seen["search_c"], seen["search_day"]
                return Step("Distance = c * seconds.", "calc",
                            {"expression": f"{c} * {day}"})
            return Step("Have the product; finish.", "finish",
                        {"answer": f"{seen['calc']} meters"})
        return Step("Unknown goal.", "finish", {"answer": "cannot solve"})

    def run(self, goal: str) -> dict:
        for _ in range(self.max_steps):
            step = self.decide(goal)                      # PERCEIVE + PLAN
            if step.action == "finish":                   # stop condition
                self.trace.append(step)
                return {"answer": step.args["answer"], "steps": len(self.trace),
                        "trace": self.trace}
            tool_map = {"search_c": "search", "search_day": "search",
                        "calc": "calculator"}
            tool = self.tools[tool_map[step.action]]
            try:
                step.observation = tool.run(**step.args)  # ACT
            except Exception as e:                          # OBSERVE (errors too)
                step.observation = f"ERROR: {e}"
            self.trace.append(step)                        # write to scratchpad
        return {"answer": "MAX_STEPS_EXCEEDED", "steps": len(self.trace),
                "trace": self.trace}


if __name__ == "__main__":
    agent = Agent(tools={
        "search": Tool("search", "look up a fact", fake_search),
        "calculator": Tool("calculator", "safe arithmetic", safe_calculator),
    })
    result = agent.run("how far does light travels in one day in meters")
    for i, s in enumerate(result["trace"]):
        print(f"[{i}] {s.action:9} args={s.args} -> {s.observation}")
    print("ANSWER:", result["answer"])
```

**Its execution trace:**

```
[0] search_c   args={'query': 'speed of light m/s'} -> 299792458
[1] search_day args={'query': 'seconds in a day'}   -> 86400
[2] calc       args={'expression': '299792458 * 86400'} -> 2.590263...e+13
[3] finish     args={'answer': '25902068371200.0 meters'}
ANSWER: 25902068371200.0 meters
```

**What you would evaluate, mapped to components:**

| Trace element | Component under test | The evaluation question |
|---|---|---|
| Step 0–1 chose `search` | Planner + LLM core | Did it identify *both* facts it needed before calculating? |
| Observations `299792458`, `86400` | Tools / faithfulness | Are the retrieved facts correct? (retrieval eval) |
| Step 2 expression | Tool-argument correctness | Did it multiply the *right* two numbers? |
| Result magnitude | Reasoning / sanity | Is ~\(2.6\times10^{13}\) m physically plausible? |
| Step 3 `finish` | Controller / stop logic | Did it stop at the right time — not too early, not looping? |
| No `eval` in calculator | Safety | Would a malicious `expression` execute code? (No — it can't.) |
| `steps ≤ max_steps` | Controller / budget | Did it stay within its iteration cap? |

That mapping *is* the shape of an agent test plan: one assertion per component, plus one on the end-to-end outcome.

---

## 7. Why agents are hard to evaluate

The properties that make agents useful are the same ones that break naive evaluation.

- **Nondeterminism.** Sampling temperature, tool latency ordering, and the model's own branching mean the *same task* yields *different trajectories* on reruns. A single pass tells you almost nothing; you need multiple runs and a notion of *pass rate* (e.g., pass\@k), not a single pass/fail.

- **Trajectory vs. outcome.** The final answer can be right by luck (two errors canceling) or the *process* can be unacceptable even when the answer is right (it deleted a table, spent $40, leaked a secret). You must decide, per use case, whether you are grading **outcome** (did the DB end in the correct state?), **trajectory** (were the steps valid and efficient?), or both. Most serious evals grade both, with separate metrics.

- **Compounding errors.** If each step is 95% reliable, a 10-step task is \( 0.95^{10} \approx 0.60 \) reliable end-to-end. Small per-step error rates become large task-failure rates. This is why per-step metrics matter and why "the model is great" does not imply "the agent is great."

- **Partial credit.** Real tasks are rarely all-or-nothing. An agent that completes 4 of 5 subgoals, or gets a correct answer via an inefficient 12-step path, deserves a score *between* 0 and 1. Designing partial-credit rubrics (subgoal completion, checkpoint milestones) is a core eval skill.

- **Attribution / credit assignment.** When a 15-step run fails, *which step* caused it — the model, a flaky tool, a stale memory, a bad tool description? Without step-level logging you cannot tell, and you will "fix" the wrong thing.

- **Side effects and non-repeatability.** Agents act on stateful environments. Re-running a test after the agent already sent the email, or against a mutated sandbox, gives meaningless results. Evals need *hermetic, resettable* environments (sandboxes, mock tools, transactional rollbacks).

- **Cost and latency are first-class.** An agent that is correct but takes 60 steps and $2 per task may be a failure in production. Token cost, wall-clock, and tool-call count are metrics, not footnotes.

The through-line: **grade the process, not just the product; run many times, not once; and log enough state to assign blame.**

---

## 8. Tools & frameworks (real, current — 2025–2026)

One line each; verify against the linked docs, as APIs move fast.

| Framework | What it is | Distinguishing trait |
|---|---|---|
| [**LangGraph**](https://langchain-ai.github.io/langgraph/) | Graph/state-machine runtime for agents (LangChain) | Explicit nodes+edges+shared state; durable, controllable loops and checkpoints |
| [**OpenAI Agents SDK**](https://openai.github.io/openai-agents-python/) | OpenAI's lightweight agent framework (successor to Swarm) | Minimal primitives: agents, handoffs, guardrails, tracing |
| [**Claude Agent SDK**](https://docs.anthropic.com/en/api/agent-sdk/overview) | Anthropic's SDK for building agents (formerly Claude Code SDK) | Tool use, subagents, and long-horizon context/compaction built in |
| [**AutoGen**](https://microsoft.github.io/autogen/) | Microsoft's multi-agent conversation framework | Agents that talk to each other + humans; strong for multi-agent chat |
| [**CrewAI**](https://docs.crewai.com/) | Role-based multi-agent orchestration | "Crews" of role-playing agents with tasks; fast to prototype |
| [**LlamaIndex**](https://docs.llamaindex.ai/) | Data/RAG framework with agent workflows | Strong retrieval + event-driven `Workflow` abstraction |
| [**Pydantic AI**](https://ai.pydantic.dev/) | Type-safe agent framework | Structured, validated tool I/O via Pydantic models |
| [**LangSmith**](https://docs.smith.langchain.com/) | Tracing + evaluation platform | Records full agent traces; runs dataset-based agent evals |

Multi-agent (AutoGen, CrewAI) adds *another* control layer — routing between agents — and therefore *another* class of failures (bad handoffs, agents talking past each other) to evaluate.

---

## 9. What an interviewer or reviewer will probe

**Q1. "What actually makes something an agent rather than a workflow?"**
Control location. In a workflow the *code* fixes the sequence of steps; in an agent the *model* decides the next action at run time from feedback, and decides when it is done. If you can draw the full control-flow graph ahead of time, it's a workflow.

**Q2. "Walk me through the ReAct loop and why interleaving reasoning and acting helps."**
Thought → Action → Observation, repeated. Reasoning picks the next action; the observation (real environment feedback) corrects the reasoning. Interleaving grounds the chain of thought in reality, cutting hallucination versus reason-only (CoT) and giving structure versus act-only.

**Q3. "If the final answer is correct, is the agent correct?"**
Not necessarily. The answer can be right by luck or reached via an unacceptable trajectory (side effects, cost, unsafe actions). You must grade trajectory *and* outcome, and run multiple times because of nondeterminism.

**Q4. "Each step is 95% reliable. What's your end-to-end reliability on a 10-step task, and what does that imply for evaluation?"**
\( 0.95^{10}\approx 0.60 \). Small per-step errors compound. Implication: measure per-step reliability and shorten the critical path; a high single-call score does not predict agent success.

**Q5. "A 15-step run failed. How do you find the cause?"**
Step-level logging. Inspect the trace: which action first diverged, what was in context/memory at that point, whether a tool errored or returned stale data. Distinguish model failures from tool/description/memory failures — they need different fixes.

**Q6. "How do memory bugs typically show up in evaluation, and why are they tricky?"**
Non-locally: a fact dropped by truncation or a stale retrieval at step 2 causes a wrong action at step 9. Symptoms: repeated identical tool calls, contradictions with earlier established facts, acting on outdated values. Tricky because the failure is far from its cause — final-answer grading misattributes it to reasoning.

**Q7. "When would you deliberately *not* build an agent?"**
When the task decomposes into known, stable steps — use a workflow or a single call. Agents cost predictability, determinism, testability, and money, and add side-effect risk. Follow "simplest thing that works; add complexity only when it demonstrably helps."

**Q8. "What metrics beyond task success would you report for an agent?"**
Pass\@k / success rate over multiple runs, subgoal/partial-credit score, step count and efficiency, token cost and dollar cost, latency, tool-call error rate, and safety/side-effect violations.

---

## 10. Further reading

- Anthropic — [*Building Effective Agents*](https://www.anthropic.com/engineering/building-effective-agents) — the workflow-vs-agent framing used throughout this chapter.
- Yao et al., 2022 — [*ReAct: Synergizing Reasoning and Acting in Language Models*](https://arxiv.org/abs/2210.03629) ([project page](https://react-lm.github.io/)).
- Shinn et al., 2023 — [*Reflexion: Language Agents with Verbal Reinforcement Learning*](https://arxiv.org/abs/2303.11366) (NeurIPS 2023).
- Wei et al., 2022 — [*Chain-of-Thought Prompting*](https://arxiv.org/abs/2201.11903) — the reasoning half that ReAct grounds.
- Yao et al., 2023 — [*Tree of Thoughts*](https://arxiv.org/abs/2305.10601) — search over reasoning branches.
- OpenAI — [*A Practical Guide to Building Agents*](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) (PDF).
- LangGraph docs — [langchain-ai.github.io/langgraph](https://langchain-ai.github.io/langgraph/).
- OpenAI Agents SDK — [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/).
- Anthropic Agent SDK — [docs.anthropic.com/en/api/agent-sdk/overview](https://docs.anthropic.com/en/api/agent-sdk/overview).
- Lilian Weng, 2023 — [*LLM Powered Autonomous Agents*](https://lilianweng.github.io/posts/2023-06-23-agent/) — the canonical component breakdown (planning, memory, tools).

---

> **Carry this into every later chapter:** an agent is *the LLM's decisions, in a loop, over tools and memory, driven by a controller.* To evaluate it you must observe the whole trajectory, run it many times, log the state at each step so you can assign blame, and score process and outcome separately. Everything else in this guide is built on that.
