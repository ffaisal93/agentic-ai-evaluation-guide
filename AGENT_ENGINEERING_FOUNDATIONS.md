# Agent Engineering Foundations — How to Actually Build Agents Today

> **Capstone / build companion.** The rest of this guide teaches you how to *evaluate* agents. This chapter is the other half of the loop: how to *build* them. You cannot meaningfully evaluate a system whose moving parts you have never assembled yourself. Read this to understand — concretely, at the level of code and architecture — what a modern (2025–2026) AI agent is made of, how to choose a model and a framework, which architecture patterns actually ship, and how to take an agent from a notebook to production. Every eval concept elsewhere in this book has a corresponding *design decision* here.

---

## 0. Why this chapter exists

There is a failure mode common to people who study evaluation before they study engineering: they measure the wrong things because they do not know what the moving parts *are*. They test "tool-use accuracy" without knowing that the model, not the harness, decides when to call a tool. They design a "memory benchmark" without knowing whether the agent even has episodic memory or is just re-reading a growing transcript. They flag "hallucinated citations" as a retrieval bug when it is a context-assembly bug.

**You cannot evaluate what you cannot build.** This chapter closes that gap. By the end you should be able to:

- Name every component of an agent and say what each one is responsible for.
- Pick a model for a given job and justify it on capability, latency, and cost.
- Pick a framework and defend the choice against three alternatives.
- Recognize the standard architecture patterns on sight and know their failure modes.
- Design a tool the model can actually use, and expose it over MCP.
- Wire up RAG and memory without drowning the context window.
- Ship an agent with guardrails, budgets, retries, and tracing — then hand it to the eval harness in the rest of this book.

Intuition first, then mechanism. Short paragraphs. Honest tradeoffs. Runnable code.

---

## 1. The anatomy of a modern agent

If you remember one sentence from the fundamentals chapter (`01_agentic_ai_fundamentals`), remember this: **an agent is an LLM running in a loop with access to tools, where the model decides what to do next.** Everything else is plumbing that makes that loop reliable, cheap, and safe.

Anthropic's widely-cited framing calls the core unit the **augmented LLM**: a model enriched with *retrieval*, *tools*, and *memory*. An agent is that augmented LLM placed inside a control loop. Let us name the parts.

```
                       ┌───────────────────────────────────────────┐
   user goal  ───────► │              ORCHESTRATOR                  │
                       │  (owns the loop, budget, state, routing)   │
                       └───────────────┬───────────────────────────┘
                                       │  assembles context
                                       ▼
        ┌───────────────────────────────────────────────────────┐
        │                    CONTEXT WINDOW                       │
        │  system prompt · tools schema · memory · retrieved docs │
        │  running transcript · current observation               │
        └───────────────┬─────────────────────────────┬──────────┘
                        │                              ▲
                        ▼                              │ observation
                 ┌──────────────┐               ┌──────┴───────┐
                 │    MODEL     │──tool call───►│    TOOLS      │
                 │ (the "brain")│               │ APIs, code,   │
                 │  reasons +   │◄──result──────│ retrieval,    │
                 │  decides     │               │ MCP servers   │
                 └──────┬───────┘               └───────────────┘
                        │ final answer
                        ▼
                    user / caller
                        │
                        ▼
                 ┌──────────────┐
                 │    MEMORY    │  (writes summaries, facts, episodes back)
                 └──────────────┘
```

**The five parts, and who owns what:**

| Component | Responsibility | Failure if missing |
|---|---|---|
| **Model** | Reasons, plans, decides which tool to call and when to stop. | No autonomy — you just have a workflow. |
| **Tools** | Give the model *actions*: read/write the world, fetch facts, run code. | The model can only talk, not act. |
| **Memory** | Persist state beyond the context window: facts, summaries, episodes. | Amnesia between (and within long) sessions. |
| **Control loop** | Repeatedly call model → execute tool → feed result back, until done. | One-shot Q&A, no multi-step behavior. |
| **Orchestrator** | Owns budget, retries, routing, state, guardrails, tracing. | Runs forever, blows the budget, no observability. |

A crisp mental distinction you will use constantly (also from Anthropic's *Building Effective Agents*):

- A **workflow** is a system where LLMs and tools are orchestrated through **predefined code paths**. *You* decide the steps.
- An **agent** is a system where the **model dynamically directs its own process** — it chooses the steps at runtime.

Most production "agents" are actually mostly-workflow with a small agentic core. That is a feature, not a failure: predefined paths are easier to test, cheaper, and more predictable. Reach for autonomy only where the branching is genuinely open-ended.

Everything below is a zoom-in on one of these five parts, plus the engineering that makes them production-grade.

---

## 2. The 2025–2026 model landscape for builders

The model is the single biggest determinant of what your agent can do. Frameworks are swappable; a weak model cannot be prompt-engineered into a strong agent. Here is what a builder needs to know about the current landscape, organized by the capabilities that actually change your architecture.

### 2.1 The frontier lineup (as of mid-2026)

Model families move fast; verify exact versions and prices against the provider's pricing page before you ship. As of this writing:

| Model | Provider | Context | Input / Output (per 1M tok) | Notable for agents |
|---|---|---|---|---|
| **Claude Opus 4.8** (rel. 2026-05-28) | Anthropic | 1M | \$5 / \$25 | Adaptive "thinking," effort controls, strong tool use & coding |
| **Claude Sonnet 4.6** | Anthropic | 1M | \$3 / \$15 | Production workhorse — best cost/capability balance |
| **Claude Haiku 4.5** | Anthropic | 200K | \$1 / \$5 | Latency-optimized; routers, classifiers, cheap sub-agents |
| **GPT-5.5** (rel. 2026-04-23) | OpenAI | 1M (API) | \$5 / \$30 | Strong browse/computer-use (BrowseComp 84.4%, OSWorld 78.7%) |
| **GPT-5.5 Thinking / Pro** | OpenAI | 1M | \$30 / \$180 (Pro) | Hard reasoning, autonomous multi-tool tasks |
| **Gemini 3.x Pro** | Google | 1M+ | tiered | Long-context, multimodal, native Google-tool integration |

Prices and versions change monthly — treat the table as a *snapshot of the shape of the market*, not a spec sheet. The durable facts are: flagship context windows have converged on **~1M tokens**; there is a clear **capability tier** (Opus/GPT-5.5-Pro), a **workhorse tier** (Sonnet/GPT-5.5), and a **cheap-fast tier** (Haiku); and **prompt caching (~90% savings) and batch (~50% savings)** are universal.

> Sources: Anthropic and OpenAI pricing/announcement pages (see Further Reading). The point is the *structure*, which is stable even as digits change.

### 2.2 Function / tool calling — the feature that makes agents possible

Every frontier model exposes **structured tool calling**: you pass a list of tool definitions (name, description, JSON-Schema parameters); the model, instead of replying in prose, emits a structured request like `{"tool":"get_weather","arguments":{"city":"Paris"}}`. Your harness executes it and feeds the result back.

This is the primitive the entire agent stack is built on. Two things a builder must internalize:

1. **The model does not run your tool.** It only *asks* to. Your loop runs it. Everything about safety, retries, and timeouts lives in *your* code, not the model's.
2. **Tool descriptions are prompt.** The model chooses tools purely from their names, descriptions, and schemas. A badly-described tool is a badly-behaved agent. (See §6.)

Modern APIs support **parallel tool calls** (the model requests several at once) and **forced tool choice** (`tool_choice: "required"` / a specific tool) — both are levers for latency and control.

### 2.3 Reasoning / "thinking" models — and when to use them

The biggest shift of 2025 was **reasoning models**: models trained to spend extra tokens on an internal chain of thought before answering (OpenAI's o-series lineage, now folded into GPT-5.x "Thinking"; Anthropic's **extended/adaptive thinking**; Gemini "thinking"). You typically get a **thinking budget** or **effort** knob (low/medium/high) that trades latency and cost for accuracy on hard problems.

**When thinking pays off:** multi-step math, complex planning, code debugging, ambiguous tool-selection, anything where a wrong first step cascades. **When it does not:** classification, routing, extraction, simple lookups, latency-critical hops. Burning thinking tokens on "which of these 3 tools" is money lit on fire.

**Builder rule of thumb:** use a *cheap non-thinking* model for the router and the leaf tools, and a *thinking* model only for the planning/synthesis steps. This is the single highest-leverage cost decision in most agents (see §9 cascades).

### 2.4 Context windows and caching

1M-token windows are real, but **a big window is not free memory** — it is a resource you spend on every turn, and quality degrades as it fills (§8, "context rot"). Two mechanics matter:

- **Prompt caching.** Providers let you mark a long, stable prefix (system prompt + tool schemas + reference docs) as cacheable. Subsequent calls that reuse that prefix pay a fraction (~10%) for the cached portion. For an agent that loops 20 times over the same system prompt, this is often a **5–10× cost reduction**. Structure your prompt so the stable part comes *first*.
- **The window is a budget, not a bucket.** Just because you *can* stuff 1M tokens does not mean you *should*. Retrieval + summarization (§7, §8) usually beats dumping everything in.

### 2.5 Structured outputs

Beyond tool calling, models offer **structured output / JSON mode**: constrain the *final answer* to a JSON Schema so you get parseable data instead of prose. OpenAI's "Structured Outputs" and Anthropic's tool-based JSON both effectively guarantee schema-valid output. Use this for any step whose result another program consumes — extraction, classification, form-filling, agent-to-agent handoffs. It removes an entire class of "the model wrapped the JSON in prose" bugs.

### 2.6 Multimodal and computer/browser use

Frontier models are **natively multimodal** (image, and increasingly audio/video, in; text out). For agents this unlocks screenshots, PDFs, charts, and UI understanding.

**Computer use / browser use** is the frontier: the model is given screenshots and can emit mouse/keyboard actions (Anthropic's Computer Use; OpenAI's computer-use tool; browser agents). Benchmarks like **OSWorld** and **BrowseComp** track it. It is powerful and *unreliable* — treat it as a last resort when no API exists, sandbox it aggressively, and put a human in the loop for anything consequential.

### 2.7 How model choice shapes the agent

| If your model… | Then your architecture… |
|---|---|
| Has strong native tool use | Can lean on a simple ReAct loop; less scaffolding. |
| Is a reasoning model | Needs *less* explicit planning prompt; give it room to think, don't over-orchestrate. |
| Has a 1M window + caching | Can favor long-context over aggressive RAG for medium corpora. |
| Is cheap/fast (Haiku-class) | Is ideal as a router or a swarm of parallel workers. |
| Supports structured outputs | Lets you make agent-to-agent handoffs typed and testable. |

Pick the model **per step**, not per app. A well-built agent frequently uses two or three models.

---
## 3. Frameworks compared, in depth

A framework does three things for you: (1) it owns the **control loop** so you don't hand-roll the while-loop; (2) it standardizes **tool definitions, memory, and state**; (3) it gives you **observability, streaming, and human-in-the-loop** hooks. What differs is the *mental model* each imposes and how much control it hands back to you.

> **First, the honest meta-point:** you can build a solid production agent with **no framework** — just the provider SDK, a `while` loop, and a dict of tools. Frameworks earn their keep when you need durable state, multi-agent orchestration, or standardized observability. Start minimal; adopt a framework when you feel a specific pain, not preemptively.

### 3.1 The contenders (mental model + what it's best at)

**LangGraph** — *the graph/state-machine framework* (LangChain). You model your agent as a **graph**: nodes are functions (call model, run tool, decide), edges are transitions, and a typed **state object** flows through. Its superpower is **durable execution**: checkpoints, resumability, human-in-the-loop pauses, and time-travel. Reached **1.0 GA in October 2025** and is the default choice when you need explicit, testable, stateful control over a non-trivial workflow. Steeper learning curve; you think in graphs.

**OpenAI Agents SDK** — *the lightweight, batteries-included loop* (OpenAI). A small, opinionated SDK built around `Agent`, `Runner`, `handoffs`, and `guardrails`, with built-in web-search and computer-use tools. Best when your stack is OpenAI-centric and you want to ship a tool-using or multi-agent handoff system in an afternoon. Released March 2025 (the successor to the experimental "Swarm"). Less machinery than LangGraph — which is the point.

**Claude Agent SDK** — *Claude Code as a library* (Anthropic). Renamed from the *Claude Code SDK*. It exposes the exact agent harness that powers Claude Code — the same agent loop, context management, built-in tools (**Read, Edit, Bash, Glob, WebFetch, WebSearch**), **subagents**, **MCP** support, **hooks**, **permissions**, and filesystem-based **skills/CLAUDE.md** memory. Python and TypeScript. Best when you want a strong, autonomous, code-and-computer-capable agent out of the box with minimal loop code, especially for coding/ops/research tasks.

**AutoGen / AG2** — *conversational multi-agent research* (community; AG2 is the community fork of Microsoft's AutoGen). Agents are **conversational participants** that message each other; you compose group chats, nested chats, and human proxies. Best for research and experimentation with emergent multi-agent dynamics. (Microsoft's own lineage has largely converged into the **Microsoft Agent Framework** / Semantic Kernel; AG2 carries the open-source torch.)

**CrewAI** — *role-based crews, fast to stand up* (CrewAI Inc.). You define **agents with roles/goals/backstories** and assemble them into a **crew** with sequential or hierarchical process. Very fast time-to-first-demo, a visual editor, and a commercial platform. Best for rapid multi-agent prototypes and business-process automations; less low-level control than LangGraph.

**LlamaIndex** — *the data/RAG-first framework*. Started as the premier RAG toolkit (indexing, retrieval, query engines) and grew an agent/**Workflows** layer on top. Best when your agent's center of gravity is **retrieval over your data** — document QA, knowledge assistants — and you want first-class ingestion and indexing.

**Pydantic AI** — *type-safe agents for Python engineers* (Pydantic team). Brings Pydantic's validation ergonomics to agents: typed dependencies, typed structured outputs, and a clean testing story. Best when you value **type safety, testability, and production discipline** over multi-agent bells and whistles.

**Smolagents** — *minimalist, code-writing agents* (Hugging Face). Tiny library whose signature idea is the **CodeAgent**: instead of emitting JSON tool calls, the agent writes **Python code** that calls your tools, which often reduces steps for complex tasks. Best for lightweight, hackable agents and when you want the model to *compose* tool calls in code. Model-agnostic (Hub, OpenAI, Anthropic, local).

### 3.2 Comparison table

Versions/dates are snapshots as of early 2026 — check the repo before relying on a number.

| Framework | Maintainer | Mental model | Best at | Multi-agent | State/durability | Maturity (early 2026) |
|---|---|---|---|---|---|---|
| **LangGraph** | LangChain | Graph / state machine | Stateful, controllable production workflows | Yes (as subgraphs) | First-class (checkpoints, resume) | 1.0 GA Oct 2025; v1.1.x |
| **OpenAI Agents SDK** | OpenAI | Agent + Runner + handoffs | Quick OpenAI-native agents | Yes (handoffs) | Sessions; lighter | v0.x, rel. Mar 2025 |
| **Claude Agent SDK** | Anthropic | Claude Code harness as library | Autonomous coding/ops/research agents | Yes (subagents) | Context mgmt + filesystem memory | GA (renamed 2025) |
| **AutoGen / AG2** | Community (ex-MS) | Conversational agents | Multi-agent research/experiments | Core strength | Conversation state | AG2 active fork |
| **CrewAI** | CrewAI Inc. | Roles → crew | Fast multi-agent prototypes | Core strength | Crew/process state | v1.x, mature |
| **LlamaIndex** | LlamaIndex | Data → index → query → workflow | RAG-centric agents | Yes (Workflows) | Workflow state | Mature |
| **Pydantic AI** | Pydantic | Typed agent + deps | Type-safe production agents | Yes | Typed deps; testable | v1.x |
| **Smolagents** | Hugging Face | Code-writing agent | Minimal, hackable, code-first | Managed agents | Light | Active |

Reference URLs (Further Reading, §13): LangGraph docs & 1.0 announcement, OpenAI Agents SDK docs, Claude Agent SDK docs, AG2 docs, CrewAI docs, LlamaIndex docs, Pydantic AI docs, smolagents docs.

### 3.3 How to actually choose

- **Default for a controllable production agent:** LangGraph. You will want the durability and the explicit state.
- **All-in on OpenAI, want speed:** OpenAI Agents SDK.
- **Autonomous coding / computer / ops agent on Claude:** Claude Agent SDK.
- **RAG is the whole point:** LlamaIndex.
- **You are a typed-Python shop that hates magic:** Pydantic AI.
- **Multi-agent brainstorm / research:** AG2 or CrewAI.
- **You want the model to write code that orchestrates tools:** smolagents.
- **You're not sure yet:** no framework — provider SDK + a loop. Migrate later; the concepts port cleanly.

The framework is the *most reversible* decision in your stack. The model, the tool contracts, and the eval harness are the ones that lock you in. Do not over-agonize here.

---
## 4. Core architecture patterns

These are the reusable shapes agents come in. You will combine them. Each entry: a diagram-in-words, when to use it, and how it breaks. (These map directly onto the eval chapters — every failure mode here is something you must *test for* later.)

### 4.1 ReAct (Reason + Act)

**Diagram-in-words:** loop — the model produces a *thought* ("I should look up the order status"), an *action* (tool call), receives an *observation* (tool result), and repeats until it emits a final answer. Reason, act, observe, reason, act, observe…

**When to use:** the default, general-purpose agentic loop. Great when the path is unknown and depends on intermediate results (research, troubleshooting, tool-heavy tasks).

**Failure modes:** *looping* (calls the same tool forever), *thrashing* (oscillating between two approaches), *premature stop* (answers before gathering enough), *tool-selection errors*. Mitigate with step caps, loop detection, and forced-final-answer prompts. From Yao et al., 2022.

### 4.2 Plan-and-execute

**Diagram-in-words:** a *planner* step first writes an explicit multi-step plan; an *executor* then carries out each step (often with its own ReAct loop), optionally re-planning when reality diverges.

**When to use:** long-horizon tasks with many steps where letting the model improvise every step wastes tokens and drifts. The upfront plan anchors it.

**Failure modes:** *stale plans* (plan made on bad assumptions, executor follows it off a cliff), *no re-planning* (rigidity), *over-planning* (spends the budget planning). Mitigate by allowing re-plan on failure and validating each step's precondition.

### 4.3 Reflection / self-critique

**Diagram-in-words:** the agent produces a draft, then a *critic* pass (same or different model) evaluates it against criteria, and the agent revises. Repeat until the critic is satisfied or a cap is hit. **Reflexion** adds *verbal self-feedback stored in memory* so the agent learns across attempts.

**When to use:** quality-sensitive generation — code that must pass tests, writing with a rubric, math with a checker. Especially powerful when you have an *objective* signal (tests, a compiler, a validator) to reflect against.

**Failure modes:** *sycophantic self-review* (the critic rubber-stamps), *infinite polishing* (never satisfied), *cost blowup*. Use an *external* signal where possible; cap iterations. From Shinn et al., 2023 (Reflexion); Madaan et al., 2023 (Self-Refine).

### 4.4 Router

**Diagram-in-words:** a cheap classifier model inspects the input and *routes* it to one of several specialized handlers (a model, a prompt, a sub-agent, or a workflow).

**When to use:** heterogeneous traffic — a support bot where billing, technical, and sales queries need different tools and prompts. Routing lets each branch stay simple and cheap.

**Failure modes:** *misroute* (sends billing to the tech agent), *no fallback* (unmatched inputs dead-end), *route drift* as categories evolve. Mitigate with a confidence threshold + a default branch, and log routes for eval.

### 4.5 Orchestrator–worker

**Diagram-in-words:** a central **orchestrator** decomposes a task and dynamically spawns **worker** sub-agents (often in parallel), each handling a piece, then synthesizes their outputs. Unlike static parallelization, the orchestrator decides *at runtime* how many workers and what each does.

**When to use:** tasks that decompose into independent subtasks whose number/shape isn't known in advance — "research these N aspects," multi-file code changes, map-reduce over documents.

**Failure modes:** *synthesis loss* (orchestrator can't reconcile conflicting worker outputs), *cost fan-out* (spawns too many), *context duplication* (every worker re-reads everything). Mitigate with worker budgets and structured worker outputs. (This is roughly how Anthropic's multi-agent research system is built.)

### 4.6 Evaluator–optimizer

**Diagram-in-words:** two roles in a loop — an *optimizer* generates a candidate, an *evaluator* scores it and returns concrete feedback, the optimizer improves. Distinct from reflection in that the evaluator is a *separate, purpose-built* judge with explicit criteria.

**When to use:** when you have clear evaluation criteria and iteration measurably helps — literary translation, complex search, code meeting a spec.

**Failure modes:** *weak evaluator* (garbage feedback → garbage optimization), *reward hacking* (optimizer games the judge), *non-convergence*. Mitigate with a strong, well-prompted evaluator and a hard iteration cap. This pattern is the *build-time twin* of the LLM-as-judge evaluation you'll read about later.

### 4.7 Multi-agent (general)

**Diagram-in-words:** multiple agents with distinct roles/tools collaborate — via a shared orchestrator, a message bus, or handoffs — each specialized (planner, coder, tester, reviewer).

**When to use:** genuinely separable expertise, or when a single context window can't hold everything (each agent keeps its own focused context). Also for *parallelism*.

**Failure modes:** the big one — **coordination overhead often exceeds the benefit.** Also: error propagation between agents, exploding token cost, and emergent deadlock/loops. **Default to a single agent with good tools.** Reach for multi-agent only when a single agent provably can't cope. (The multi-agent evaluation chapter exists precisely because these failure modes are hard to catch.)

### 4.8 Choosing and combining

| Signal | Reach for |
|---|---|
| Unknown path, tool-heavy | ReAct |
| Long horizon, many steps | Plan-and-execute |
| Quality bar + a checker | Reflection / evaluator–optimizer |
| Heterogeneous inputs | Router |
| Parallel, variable-count subtasks | Orchestrator–worker |
| Separable expertise, context too big | Multi-agent |

Real systems nest these: a router at the front, plan-and-execute in the middle, ReAct inside each executor step, reflection on the final artifact. **Start with the simplest thing that could work (usually a single ReAct agent) and add structure only where evals show a gap.**

---
## 5. Tools & the Model Context Protocol (MCP)

Tools are where an agent stops being a chatbot and starts *doing things*. The quality of your tools caps the quality of your agent more than almost any other factor. This is also the most under-appreciated skill in agent engineering.

### 5.1 A tool is a prompt-plus-a-function

A tool has two audiences:

1. **The model**, which reads the *name*, *description*, and *parameter schema* to decide whether and how to call it.
2. **Your runtime**, which executes the function and returns a result.

Design for both. The description is not documentation for you — it is *instruction for the model.* Treat it like prompt engineering.

### 5.2 Principles for tools the model can actually use

- **Name for intent, not implementation.** `search_customer_orders`, not `pg_query_v2`.
- **Descriptions state *when* to use it and *when not to*.** "Use to look up an order's current status by order ID. Do NOT use for refunds — use `issue_refund`."
- **Make parameters unambiguous and typed.** Enums over free strings. Required vs optional explicit. Describe every field. Give examples in the description.
- **Return *model-legible* results.** Return structured, concise data — not a 50KB HTML dump. Summarize/paginate large results. The model has to *read* what you return, and it costs tokens.
- **Fail loudly and usefully.** Errors are the agent's feedback signal. A good error tells the model how to recover.
- **Prefer few powerful tools over many overlapping ones.** Overlapping tools cause selection errors. If two tools are easily confused, merge or rename them.
- **Make tools idempotent / safe where possible**, and gate irreversible ones behind confirmation (see guardrails, §8).
- **Right-size granularity.** One `manage_calendar(action=...)` can beat five micro-tools — fewer choices, fewer mistakes — but don't overload one tool with unrelated modes.

### 5.3 Error contracts

The single biggest reliability win in tool design is a **consistent error contract**. Decide the shape and return it *as data the model can act on*, never as an exception that crashes the loop:

```json
{
  "ok": false,
  "error_code": "ORDER_NOT_FOUND",
  "message": "No order with id 'A-123'. Verify the ID or call search_customer_orders.",
  "retryable": false
}
```

The model reads `message`, adjusts, and retries a *different* action instead of hammering the same failing call. `retryable` lets your harness decide whether to auto-retry (transient 5xx) or surface to the model (bad input). Distinguishing these two is most of reliability engineering for tools.

### 5.4 A worked tool

Here is a well-formed tool, written provider-agnostically. Note the description quality, the enum, the structured success/error return, and the timeout.

```python
from pydantic import BaseModel, Field
from typing import Literal
import httpx

# 1) Schema the MODEL sees — description is instruction, not docs.
class GetOrderStatusArgs(BaseModel):
    order_id: str = Field(
        description="Customer order ID, format 'A-123'. Get it from the user "
                    "or from search_customer_orders — never invent one."
    )

TOOL_SPEC = {
    "name": "get_order_status",
    "description": (
        "Look up the CURRENT status of a single order by its ID. "
        "Use when the user asks where an order is or whether it shipped. "
        "Do NOT use to modify orders or issue refunds. "
        "Returns status, carrier, and ETA, or a structured error."
    ),
    "input_schema": GetOrderStatusArgs.model_json_schema(),
}

# 2) The function YOUR runtime executes — consistent contract, hard timeout.
def get_order_status(order_id: str) -> dict:
    try:
        r = httpx.get(f"https://api.internal/orders/{order_id}",
                      timeout=5.0)              # never hang the agent loop
        if r.status_code == 404:
            return {"ok": False, "error_code": "ORDER_NOT_FOUND",
                    "message": f"No order '{order_id}'. Verify it or call "
                               f"search_customer_orders.",
                    "retryable": False}
        r.raise_for_status()
        d = r.json()
        return {"ok": True,                     # concise, model-legible result
                "status": d["status"], "carrier": d.get("carrier"),
                "eta": d.get("eta")}
    except httpx.TimeoutException:
        return {"ok": False, "error_code": "UPSTREAM_TIMEOUT",
                "message": "Order service timed out. Safe to retry once.",
                "retryable": True}
```

That is the whole discipline: a description the model can reason over, typed args, a hard timeout, and a structured result whether it succeeds or fails.

### 5.5 MCP — the emerging standard for tools

Historically every framework had its own tool format, so a tool you wrote for one agent didn't work in another. The **Model Context Protocol (MCP)**, open-sourced by Anthropic in **November 2024**, fixes this by standardizing how agents connect to tools and data. Think **"USB-C for AI tools"**: write an MCP **server** once (exposing tools, resources, and prompts), and any MCP-capable **client** (Claude Code, Cursor, VS Code, ChatGPT, and many more) can use it.

**Where MCP stands in 2026 (verify against the spec before building):**

- **It won.** Adopters span model providers (Anthropic, OpenAI, Google DeepMind) and tools/platforms (Microsoft/GitHub Copilot, Cursor, VS Code, Zed, Slack, Salesforce, Stripe, Notion, Linear, Figma).
- **Governance is now neutral.** In **December 2025** Anthropic donated MCP to the **Agentic AI Foundation under the Linux Foundation** — it is no longer a single vendor's protocol.
- **The spec matured.** The **2025-03** revision added **Streamable HTTP** transport and **OAuth 2.1**; the **2025-11-25** revision added **async tasks** (long-running operations), refined auth (OAuth Resource Server, Client ID Metadata Documents), **elicitation**, an **extensions** system, and **MCP Apps** (interactive UI in chat).
- **Transports:** **stdio** (local subprocess, great for desktop/CLI) and **Streamable HTTP + SSE** (remote, production-grade).
- **A public **registry** indexes ~2,000 servers.

**Core MCP primitives a server exposes:** **Tools** (model-callable functions), **Resources** (readable data/context, like files or DB rows), and **Prompts** (reusable templated interactions).

**A minimal MCP server (Python, FastMCP style):**

```python
# pip install "mcp[cli]"
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("orders")

@mcp.tool()
def get_order_status(order_id: str) -> dict:
    """Look up current status of an order by ID (format 'A-123').
    Use when the user asks where an order is. Returns status/carrier/eta."""
    # ... same logic as §5.4 ...
    return {"ok": True, "status": "shipped", "carrier": "UPS", "eta": "2026-08-05"}

if __name__ == "__main__":
    mcp.run()          # stdio transport by default; add transport="streamable-http" for remote
```

**Builder guidance:** expose *your own* internal capabilities as MCP servers so they're reusable across every agent and IDE you build; *consume* third-party MCP servers to avoid re-writing integrations. But **MCP is a distribution standard, not a safety boundary** — a malicious or buggy MCP server is code you're trusting. Pin versions, scope credentials narrowly, and review servers before granting them tools. (The tool-use evaluation chapter, `04_tool_use_evaluation`, covers testing MCP tools specifically.)

---
## 6. RAG for agents, and memory systems

Two different problems that people constantly conflate:

- **RAG (retrieval-augmented generation)** answers *"what external knowledge does the model need for this turn?"* — it pulls facts from a corpus into the context window on demand.
- **Memory** answers *"what should this agent remember about the task / user / itself over time?"* — it persists state the agent itself produced.

RAG is about *knowledge you have*; memory is about *experience the agent accumulates*. An agent often needs both.

### 6.1 RAG for agents

The classic pipeline: **chunk** documents → **embed** them → store vectors in a **vector store** → at query time, **embed the query, retrieve top-k similar chunks, assemble them into the prompt**, and generate. In an *agent*, RAG usually isn't a fixed pre-step — it's a **tool** the model calls (`search_knowledge_base(query)`) when it decides it needs facts. That is *agentic RAG*, and it's strictly more flexible: the agent can search multiple times, reformulate, and decide when it has enough.

**What actually moves quality (in rough order of impact):**

1. **Chunking.** Too big → noisy, dilutes the signal; too small → loses context. Semantic/structure-aware chunking (by heading/section) beats fixed-size. Keep a bit of overlap.
2. **Retrieval quality.** **Hybrid search** (dense embeddings + keyword/BM25) beats either alone. Add a **reranker** (a cross-encoder that re-scores the top ~50 down to top ~5) — often the single biggest jump in relevance.
3. **Context assembly.** What you *put in the prompt* from the retrieved set: dedupe, order by relevance, include source metadata for citation, and *cut ruthlessly* — more chunks is not better (see context rot, §7).
4. **Query transformation.** Let the agent rewrite the user's question into a good search query, or generate several (multi-query) and merge.
5. **Grounding + citation.** Ask the model to answer *only* from retrieved context and cite chunk IDs; this is what your faithfulness/groundedness evals will check.

**RAG vs long-context — the real tradeoff:** with 1M-token windows, "just stuff the docs in" is tempting. Use long-context when the corpus is small and fits, the task needs *global* reasoning across it, and latency/cost are acceptable. Use RAG when the corpus is large or changes often, you need freshness, or you want cost control. In practice, **hybrid wins**: retrieve to narrow, then give the model generous context on the narrowed set.

```
question ─► [rewrite query] ─► [hybrid search: dense + BM25] ─► top-50
        └─► [rerank cross-encoder] ─► top-5 ─► [assemble + dedupe + cite]
        └─► LLM answers grounded in the 5 chunks, cites sources
```

**Vector stores (2026):** managed — Pinecone, Weaviate, Qdrant Cloud, MongoDB Atlas / Postgres `pgvector`, Turbopuffer; embedded/local — Chroma, LanceDB, FAISS, Qdrant. Choose on scale, filtering needs, and whether you want a separate service or an embedded library. For most apps, `pgvector` or Qdrant is plenty; reach for a specialized service at large scale.

### 6.2 Memory systems

Human-inspired taxonomy, mapped to what you build:

| Memory type | What it holds | Typical implementation |
|---|---|---|
| **Short-term / working** | The current task's running context | The transcript in the context window |
| **Long-term semantic** | Durable facts ("user prefers metric units") | Key–value store / vector store, retrieved as needed |
| **Episodic** | Records of past interactions/attempts | Log of prior sessions; retrieved by similarity |
| **Procedural** | How to do recurring tasks; learned skills | Prompts, skills files, learned tool sequences |

**The core problem: the context window is finite, tasks are not.** A long agent run will overflow any window. The solution is **paging/summarization**, popularized by **MemGPT (Packer et al., 2023)**, which treats the LLM like an OS managing tiers of memory: a small fast "main context" and a large "external context," with the agent *itself* deciding what to page in and out via memory tools (`save_fact`, `search_memory`, `summarize_and_evict`).

**Practical memory recipe for a production agent:**

1. **Summarize as you go.** When the transcript exceeds a threshold, replace older turns with a running summary. Keep the last few turns verbatim.
2. **Extract durable facts to a store.** After each session, write stable facts (preferences, entities, decisions) to long-term memory keyed by user/task.
3. **Retrieve memory like RAG.** At the start of a turn, pull the top-k relevant memories into context — don't load *all* memory.
4. **Give the agent memory *tools*** so it can decide what to remember/recall, rather than hard-coding it.
5. **Expire and update.** Memories go stale. Store timestamps; prefer recent; let new facts overwrite old.

**Off-the-shelf:** frameworks ship memory (LangGraph checkpoint/store, LlamaIndex memory, CrewAI memory), and dedicated libraries like **Mem0**, **Letta** (the MemGPT team's platform), and **Zep** offer managed long-term memory with automatic fact extraction. Use one rather than hand-rolling — but understand the recipe above, because *what to remember* is a product/eval decision, not a library default.

> Eval tie-in: memory introduces its own failure modes — stale facts, false memories, retrieval misses, privacy leakage across users. These are exactly what the memory/state portions of the evaluation chapters probe. Build the memory *knowing* you'll have to test each of those.

---
## 7. Context engineering and prompting for agents

Prompt engineering asks "what words do I put in the message?" **Context engineering** asks the bigger question: **"what is the complete set of tokens in the window at each step, and how did they get there?"** For agents, this is the discipline that most determines behavior, because the window is assembled dynamically every turn from many sources: system prompt, tool schemas, memory, retrieved docs, and a growing transcript.

### 7.1 The context window is a curated workspace, not a junk drawer

Every token in the window either helps or hurts. The job is to keep the window **relevant, ordered, and lean**. The failure you are fighting is **context rot**: as the window fills — especially with irrelevant or redundant content — models get *worse*, not better. They lose track of instructions, over-weight recent tokens, miss facts buried in the middle ("lost in the middle"), and latency/cost climb. A 1M window that is 80% full of stale tool output is a liability.

**Levers to manage it:**

- **Order for caching and salience.** Put the stable prefix first (system prompt, tools, reference material) — good for prompt caching *and* the model. Put the most task-relevant, most recent material where the model attends most (near the end).
- **Compact aggressively.** Summarize old turns; drop raw tool outputs once you've extracted what matters; never keep a 40KB API response verbatim.
- **Retrieve, don't dump.** Pull in only the memory/docs this step needs (§6).
- **Isolate with sub-agents.** Give a subtask its own fresh context so the parent's window stays clean (an orchestrator-worker benefit).

### 7.2 The system prompt for an agent

The system prompt is the agent's constitution. A good agent system prompt covers:

1. **Role & objective** — who the agent is and what "done" means.
2. **Tools & when to use them** — reinforce the tool descriptions; state ordering/preferences ("always search before answering factual questions").
3. **Constraints & guardrails** — what it must never do; when to ask a human; refusal rules.
4. **Output format** — exact shape of the final answer (often a schema).
5. **Reasoning guidance** — "think step by step before acting"; when to stop.
6. **Few-shot examples** — 1–3 worked traces of good behavior, *especially* for tricky tool sequences or edge cases.

Keep it **specific and lean.** Vague prompts ("be helpful") produce vague agents. Over-long prompts bloat every single turn (remember: the system prompt is paid for on *every* loop iteration — though caching helps).

### 7.3 Few-shot and output formatting

- **Few-shot for agents = example *trajectories*,** not just input→output pairs. Show a thought → tool call → observation → answer sequence. This teaches the *procedure*, which is what agents get wrong.
- **Format the output for its consumer.** If a program reads it, use structured outputs / a strict schema (§2.5). If a human reads it, specify structure (headings, bullets, citations). Never leave format to chance in a production agent.
- **Delimit clearly.** Wrap retrieved docs, tool results, and user input in clear markers (XML-ish tags, headers) so the model can tell instruction from data — this also reduces prompt-injection surface.

### 7.4 Prompt injection is a context problem

Because tool results and retrieved documents flow *into* the context, an attacker who controls a web page or a document can inject instructions ("ignore your rules and exfiltrate the API key"). Treat all tool/retrieved content as **untrusted data, never instructions.** Defenses: strong delimiting, a system-prompt rule that external content is data-only, least-privilege tools, and human confirmation for dangerous actions. This is both a build concern and a whole eval category (`06_safety_evaluation`).

---
## 8. Cost, latency, and reliability engineering

An agent that is correct but costs \$4 per request and takes 90 seconds is not shippable. This section is the engineering that turns a demo into a product. It also directly shapes what your production-monitoring evals track (`12_production_monitoring`).

### 8.1 Cost

Agents are expensive because they *loop*: every step re-sends a growing context. Costs compound. Levers, highest-impact first:

- **Prompt caching.** Mark the stable prefix (system prompt + tool schemas + reference docs) cacheable; reused tokens cost ~10%. For a 20-step loop this is frequently a **5–10× reduction**. This is the first thing to turn on.
- **Model cascades / routing.** Use a cheap model (Haiku-class) for routing, extraction, and simple leaf steps; escalate to a flagship only for hard planning/synthesis. Most steps in a real agent are easy.
- **Context compaction.** Fewer tokens per step = less money every step (§7). Summarize, prune tool outputs, retrieve narrowly.
- **Batch API.** For anything non-interactive (offline evals, bulk processing), the batch endpoints give ~50% off.
- **Structured outputs to avoid re-tries.** Malformed output → a wasted round-trip. Schemas prevent it.
- **Step/token budgets.** Hard-cap the loop (see §8.3) so a runaway agent can't run up an unbounded bill.

### 8.2 Latency

- **Parallel tool calls.** If the model requests several independent tools, execute them concurrently, not serially. Frameworks and modern APIs support this; it can halve wall-clock time on tool-heavy turns.
- **Stream** the final answer so the user sees tokens immediately even if the full response is slow.
- **Route to fast models** for latency-critical hops; reserve slow thinking models for where they earn it.
- **Cache and pre-fetch.** Cache deterministic tool results; pre-warm retrieval where the query is predictable.
- **Bound thinking.** Set a thinking/effort budget appropriate to the step — don't let a router "think" for 8 seconds.

### 8.3 Reliability

Agents fail in ways single LLM calls don't, because they take many *actions*. Build these in from day one:

- **Timeouts** on every tool and model call — never let one hang the loop.
- **Retries with backoff** for transient failures (5xx, rate limits, timeouts). Use the `retryable` flag from your error contract (§5.3) to decide what to auto-retry vs. surface to the model.
- **Step caps / budgets.** Max iterations, max tokens, max wall-clock, max dollars. When hit, stop gracefully with a partial result — don't loop forever.
- **Loop / no-progress detection.** If the agent repeats the same tool call with the same args, or N steps pass with no state change, break and escalate.
- **Idempotency & confirmation for side effects.** Irreversible actions (send email, charge card, delete) go behind a confirmation gate or a human-in-the-loop approval, and use idempotency keys so a retry doesn't double-charge.
- **Graceful degradation & fallbacks.** If the primary model/tool is down, fall back to a secondary; if retrieval fails, say so rather than hallucinate.

### 8.4 Guardrails

Guardrails are checks that run *around* the agent, independent of the model's own judgment:

- **Input guardrails:** validate/sanitize user input; detect prompt injection; block out-of-scope requests early (cheap classifier).
- **Output guardrails:** validate the final output against a schema; run a safety/PII/policy check; verify citations exist before returning.
- **Action guardrails:** allow-lists for tools per context; spend limits; the confirmation gates above; a "human approval required" tier for high-risk actions.
- **The pattern:** a fast, cheap model or rule engine sits in front of and behind the expensive agent. Guardrails should *fail closed* for dangerous actions and *fail open* only where safe.

The general principle across all of §8: **the model is nondeterministic; your harness must be deterministic where it matters.** Budgets, timeouts, retries, schemas, and guardrails are how you wrap a probabilistic core in a predictable shell.

---
