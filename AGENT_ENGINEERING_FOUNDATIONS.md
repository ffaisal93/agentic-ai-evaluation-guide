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
- **The 2026-07-28 spec rewrote the transport core.** Sessions and the `initialize`/session-ID handshake are gone — every request is now stateless and self-contained, so MCP servers can scale horizontally behind a plain load balancer with no sticky sessions. It adds **Multi Round-Trip Requests (MRTR)** for "ask the user for missing input mid-call" flows, moves tool/method names into HTTP headers (`Mcp-Method`, `Mcp-Name`) for gateway-level routing, and adds `ttlMs`/`cacheScope` cache hints on list/read results. Breaking for existing servers: Roots, Sampling, and Logging are deprecated (12-month sunset), Tasks move into a formal extension framework, and Dynamic Client Registration is being superseded by Client ID Metadata Documents. **If you're building a server today: design it stateless from the start** — don't stash per-session state in memory keyed by a session ID, since the spec no longer guarantees you'll see the same server instance twice.

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
## 9. Build a production agent — full worked walkthrough

This section builds one real agent end to end: an **Order Support Agent** that can look up orders, search a knowledge base, and issue refunds — the last one gated behind human approval. It reuses the exact tool (§5.4) and RAG (§6.1) building blocks from earlier in this chapter so you can see them assembled into a working system, not just described in isolation.

**Framework choice:** **LangGraph 1.x** (per the recommendation in §3.3 — "default for a controllable production agent"). The reasons that matter here specifically: durable checkpointing gives us free conversation memory across turns, the built-in interrupt mechanism gives us human-in-the-loop approval for the refund tool without hand-rolled plumbing, and the graph makes the ReAct loop (§4.1) and its guardrails (§8) explicit and testable nodes rather than buried control flow. Everything below is standard LangGraph 1.x API as of early 2026 — pin your `langgraph` version and diff against the docs before shipping, per the running theme of this chapter.

> This is Python. The same shape (state machine + typed tools + checkpointer + interrupts) exists in the OpenAI Agents SDK (`Agent`/`Runner`/`guardrails`) and the Claude Agent SDK (hooks + permissions); pick whichever matches your provider lock-in per §3.3. The *concepts* — tool contracts, memory, step caps, tracing — port directly.

### 9.0 What we're building

- **Tools:** `get_order_status`, `search_customer_orders`, `search_knowledge_base` (RAG over a policy corpus), `issue_refund` (irreversible — gated).
- **Memory:** short-term (the conversation, via checkpointing) + long-term (durable per-user facts, via a store).
- **Guardrails:** a hard step cap, per-tool timeouts, retries with backoff on transient failures, and an approval gate on the refund tool.
- **Observability:** a structured span around every node and tool call.
- **Control flow:** ReAct (§4.1) — model reasons, calls a tool, observes, repeats — wrapped in a graph that also tracks budget.

### 9.1 Project layout

```
order_support_agent/
├── agent.py          # graph definition — the file this section builds
├── tools.py          # tool functions + schemas
├── prompts.py        # system prompt (kept out of agent.py per §7 — stable prefix, cacheable)
├── tracing.py         # OpenTelemetry span helpers
└── run.py            # driver / CLI
```

### 9.2 State schema

The state is the typed object that flows through every node. `messages` uses LangGraph's built-in reducer so returned messages *append* rather than overwrite; everything else defaults to overwrite-on-return, which is exactly what we want for a simple counter.

```python
# agent.py
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]   # conversation, append-only
    user_id: str                              # for scoping long-term memory
    step_count: int                           # incremented once per model call
```

### 9.3 Tools with schemas and error contracts

Same discipline as §5.4 for every tool: a description that *tells the model when (not) to use it*, typed args, a hard timeout, retries for transient failures, and a structured `{"ok": ...}` result whether it succeeds or fails. `issue_refund` additionally calls `interrupt()` before doing anything irreversible.

```python
# tools.py
from typing import Literal
import httpx
from langchain_core.tools import tool
from langgraph.types import interrupt
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

TIMEOUT_S = 5.0

def _retryable(exc_types):
    """Retry only transient failures — never retry a 4xx or a business-logic error."""
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=4),
        retry=retry_if_exception_type(exc_types),
        reraise=True,
    )

@tool
@_retryable((httpx.TimeoutException, httpx.ConnectError))
def get_order_status(order_id: str) -> dict:
    """Look up the CURRENT status of a single order by its ID (format 'A-123').
    Use when the user asks where an order is or whether it shipped.
    Do NOT use to modify orders or issue refunds — use issue_refund for that.
    Returns status, carrier, and ETA, or a structured error."""
    try:
        r = httpx.get(f"https://api.internal/orders/{order_id}", timeout=TIMEOUT_S)
        if r.status_code == 404:
            return {"ok": False, "error_code": "ORDER_NOT_FOUND",
                    "message": f"No order '{order_id}'. Verify the ID or call "
                               f"search_customer_orders.", "retryable": False}
        r.raise_for_status()
        d = r.json()
        return {"ok": True, "status": d["status"], "carrier": d.get("carrier"),
                 "eta": d.get("eta")}
    except httpx.TimeoutException:
        return {"ok": False, "error_code": "UPSTREAM_TIMEOUT",
                "message": "Order service timed out after retries.", "retryable": True}

@tool
def search_customer_orders(user_id: str, query: str = "") -> dict:
    """Search a customer's orders by free-text query (product name, date range, etc).
    Use this FIRST when the user doesn't know an order ID.
    Returns up to 5 matching orders with their IDs, or an empty list."""
    r = httpx.get("https://api.internal/orders/search",
                  params={"user_id": user_id, "q": query}, timeout=TIMEOUT_S)
    r.raise_for_status()
    orders = r.json().get("orders", [])[:5]
    return {"ok": True, "orders": orders, "count": len(orders)}

@tool
def search_knowledge_base(query: str) -> dict:
    """Search company policy docs (returns, shipping, warranty) for grounding.
    Use before answering ANY policy question — never answer refund/return
    policy from memory. Returns top-3 chunks with source IDs for citation."""
    # Hybrid search + rerank pipeline from §6.1, abbreviated:
    hits = _hybrid_search_and_rerank(query, top_k=3)
    if not hits:
        return {"ok": True, "chunks": [], "message": "No relevant policy found."}
    return {"ok": True, "chunks": [
        {"source_id": h.id, "text": h.text[:800]} for h in hits
    ]}

@tool
def issue_refund(order_id: str, amount_usd: float, reason: str) -> dict:
    """Issue a refund for an order. IRREVERSIBLE — requires human approval.
    Only call this after confirming eligibility via search_knowledge_base and
    confirming the order exists via get_order_status. Do NOT call speculatively."""
    approved = interrupt({
        "action": "issue_refund", "order_id": order_id, "amount_usd": amount_usd,
        "reason": reason,
        "prompt": f"Approve ${amount_usd:.2f} refund for order {order_id}? Reason: {reason}",
    })
    if not approved:
        return {"ok": False, "error_code": "REFUND_NOT_APPROVED",
                "message": "A human reviewer declined this refund.", "retryable": False}
    r = httpx.post(f"https://api.internal/orders/{order_id}/refund",
                   json={"amount_usd": amount_usd, "reason": reason,
                         "idempotency_key": f"refund-{order_id}-{amount_usd}"},
                   timeout=TIMEOUT_S)
    r.raise_for_status()
    return {"ok": True, "refund_id": r.json()["refund_id"], "amount_usd": amount_usd}

TOOLS = [get_order_status, search_customer_orders, search_knowledge_base, issue_refund]
```

Two things worth pointing at directly: the `idempotency_key` on the refund POST (§8.3 — a retried request must not double-refund), and the fact that `interrupt()` is called *inside the tool itself*, not in some separate approval layer — LangGraph pauses the whole graph run at that exact point and persists it via the checkpointer, so "approve or reject" is a first-class pause/resume, not a side-channel.

### 9.4 Long-term memory

Short-term memory (the running transcript) is handled for free by the checkpointer in §9.6. Long-term memory — durable facts about a user across *sessions* — needs its own store, keyed by namespace, per the recipe in §6.2.

```python
# agent.py (continued)
from langgraph.store.memory import InMemoryStore   # swap for a Postgres-backed store in prod
from langgraph.store.base import BaseStore
from langchain_core.messages import SystemMessage

from prompts import SYSTEM_PROMPT

def load_memory(state: AgentState, *, store: BaseStore) -> dict:
    """Entry node: pull durable facts about this user and seed the system prompt."""
    namespace = ("users", state["user_id"], "facts")
    memories = store.search(namespace, limit=5)
    facts = "\n".join(f"- {m.value['fact']}" for m in memories) or "None on file."
    system = SystemMessage(
        content=f"{SYSTEM_PROMPT}\n\nKnown facts about this user:\n{facts}"
    )
    return {"messages": [system], "step_count": 0}

def remember_fact(store: BaseStore, user_id: str, fact: str) -> None:
    """Call this after a session (or from a dedicated tool) to persist a durable fact —
    e.g. 'prefers store credit over refunds'. Kept out of the hot loop on purpose."""
    namespace = ("users", user_id, "facts")
    store.put(namespace, key=fact[:40], value={"fact": fact})
```

`store` is injected by LangGraph automatically: any node whose signature declares a keyword-only `store: BaseStore` parameter receives the store the graph was compiled with (§9.6). This is the same pattern the framework uses for `config`. Note the deliberate asymmetry: we *read* memory on every turn (cheap, top-k, like RAG) but *write* it out-of-band rather than on every step — per the memory recipe in §6.2, decide what's worth remembering once, not on every loop iteration.

### 9.5 Tracing and observability

Every node and every tool call gets a structured span: name, key attributes, duration, and outcome. This is vendor-neutral OpenTelemetry so it plugs into whatever your `12_production_monitoring` stack already ingests (Honeycomb, Datadog, an OTel collector) — or into LangSmith/Langfuse if you'd rather use a purpose-built LLM trace store; the shape of the span is what matters, not the backend.

```python
# tracing.py
import time
from contextlib import contextmanager
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

tracer = trace.get_tracer("order_support_agent")

@contextmanager
def traced_step(name: str, **attrs):
    with tracer.start_as_current_span(name) as span:
        for k, v in attrs.items():
            span.set_attribute(k, v)
        start = time.monotonic()
        try:
            yield span
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
        finally:
            span.set_attribute("duration_ms", round((time.monotonic() - start) * 1000, 1))
```

Wired into the model-call node:

```python
# agent.py (continued)
from tracing import traced_step

def call_model(state: AgentState, *, store: BaseStore) -> dict:
    with traced_step("agent.call_model", step=state["step_count"],
                      thread_messages=len(state["messages"])) as span:
        response = llm_with_tools.invoke(state["messages"])
        usage = getattr(response, "usage_metadata", None) or {}
        span.set_attribute("input_tokens", usage.get("input_tokens", 0))
        span.set_attribute("output_tokens", usage.get("output_tokens", 0))
        span.set_attribute("stop_reason", getattr(response, "response_metadata", {})
                                                   .get("stop_reason", "unknown"))
    return {"messages": [response], "step_count": state["step_count"] + 1}
```

Every span carries enough to reconstruct, offline, exactly the trajectory the tool-use and reasoning evaluators (§9.10) need: which tools were called, with what args, how long each took, and what each turn cost. This is the same trace shape `12_production_monitoring` expects for dashboards and alerting — build the span once, consume it in both places.

### 9.6 The graph — control loop, budget, and the refund approval gate

This is the whole agent: a `load_memory` entry, a `call_model` reasoning step, a `ToolNode` that executes whatever the model asked for, and a routing function that adds a hard budget check *on top of* the standard "does the last message have tool calls" check.

```python
# agent.py (continued)
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver   # swap for Postgres/Redis in prod
from langchain_anthropic import ChatAnthropic

from tools import TOOLS

MAX_STEPS = 12   # hard cap — see §8.3. Tune per task; log every time you hit it.

llm = ChatAnthropic(model="claude-sonnet-4-6")   # workhorse tier, per §2.1 — verify current model ID
llm_with_tools = llm.bind_tools(TOOLS)

def route_after_agent(state: AgentState) -> Literal["tools", "budget_exceeded", "__end__"]:
    if state["step_count"] >= MAX_STEPS:
        return "budget_exceeded"
    return tools_condition(state)   # returns "tools" or "__end__"

def budget_exceeded(state: AgentState) -> dict:
    from langchain_core.messages import AIMessage
    return {"messages": [AIMessage(content=(
        "I've hit my step budget on this request. Here's what I found so far — "
        "please follow up if you need more, and I'll start a fresh attempt."
    ))]}

builder = StateGraph(AgentState)
builder.add_node("load_memory", load_memory)
builder.add_node("agent", call_model)
builder.add_node("tools", ToolNode(TOOLS))
builder.add_node("budget_exceeded", budget_exceeded)

builder.add_edge(START, "load_memory")
builder.add_edge("load_memory", "agent")
builder.add_conditional_edges("agent", route_after_agent, {
    "tools": "tools",
    "budget_exceeded": "budget_exceeded",
    "__end__": END,
})
builder.add_edge("tools", "agent")     # observe → back to reasoning: this IS the ReAct loop (§4.1)
builder.add_edge("budget_exceeded", END)

graph = builder.compile(checkpointer=InMemorySaver(), store=InMemoryStore())
```

Trace the loop for a refund request: `load_memory` seeds facts → `agent` reasons and calls `search_knowledge_base` → `tools` executes it → back to `agent`, which now calls `issue_refund` → `tools` executes `issue_refund`, which hits `interrupt()` and the *entire graph run pauses*, checkpointed exactly where it stopped → your application surfaces the approval prompt to a human → on approval, you resume with `Command(resume=True)` and the same tool call finishes as if it had never paused. No custom "pending approval" state machine required — that's what the checkpointer buys you.

### 9.7 Running it

```python
# run.py
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from agent import graph

config = {"configurable": {"thread_id": "conv-42"}}

def turn(user_text: str):
    for event in graph.stream(
        {"messages": [HumanMessage(user_text)], "user_id": "u_882", "step_count": 0},
        config=config, stream_mode="values",
    ):
        pass  # in production: stream tokens/tool events to the UI here
    return graph.get_state(config)

state = turn("Where's order A-118, and can I get a $30 refund — it arrived damaged?")

if state.next:   # graph is paused at an interrupt()
    payload = state.tasks[0].interrupts[0].value
    print("APPROVAL NEEDED:", payload["prompt"])
    approved = input("approve? [y/n] ").lower().startswith("y")
    final = graph.invoke(Command(resume=approved), config=config)
    print(final["messages"][-1].content)
else:
    print(state.values["messages"][-1].content)
```

`thread_id` is what makes this durable: call `turn()` again with the same `thread_id` next week and the model still has the conversation, because the checkpointer persisted it. Swap `InMemorySaver`/`InMemoryStore` for `PostgresSaver`/a Postgres-backed store and nothing else in this file changes — that swap *is* most of "productionizing" the memory layer (§10).

### 9.8 Guardrails recap — where each §8 principle actually lives in the code

| Guardrail (§8) | Where it lives above |
|---|---|
| Timeouts on every call | `TIMEOUT_S` passed to every `httpx` call in `tools.py` |
| Retries with backoff, transient-only | `_retryable()` (`tenacity`) wraps `get_order_status`; never wraps `issue_refund` |
| Step cap / budget | `MAX_STEPS` + `route_after_agent` + the `budget_exceeded` node |
| Idempotency for side effects | `idempotency_key` on the refund POST |
| Confirmation gate for irreversible actions | `interrupt()` inside `issue_refund`, resumed via `Command(resume=...)` |
| Structured error contract | `{"ok", "error_code", "message", "retryable"}` on every tool return |
| Tracing / structured spans | `traced_step()` around `call_model`; extend the same wrapper around `ToolNode` calls |

One guardrail from §8.3 is *not* shown in code above and is worth calling out explicitly: **loop/no-progress detection** — if the model calls `get_order_status` with the same `order_id` three turns in a row, that's a signal to break, not to keep paying for identical calls. The simplest implementation is a check in `call_model` comparing the new tool call against the last two in `state["messages"]` and short-circuiting to a "I seem to be stuck, here's what I know" response if they match — a few lines, easy to skip when you're moving fast, and one of the first things that bites you in production. Add it before you ship, not after the first incident.

### 9.9 How you would evaluate this agent

Building the agent is chapter 0 of a two-chapter story; the rest of this book is chapter 1. Concretely, against *this exact agent*:

- **Tool-use correctness** (`04_tool_use_evaluation`): score whether `search_customer_orders` is called before `get_order_status` when the user doesn't supply an order ID, whether `issue_refund` args match the conversation (right order, right amount), and whether the agent ever calls a tool it shouldn't (e.g., refunding without checking `search_knowledge_base` first). The structured tool-call spans from §9.5 are the input to this scorer.
- **Reasoning/trajectory quality** (`05_reasoning_evaluation`): does the agent's plan across steps make sense given the observations it gets back — does it re-check `get_order_status` after a `search_customer_orders` hit, does it stop looping when the knowledge base returns nothing? Trajectory eval reads the `messages` list this graph produces directly.
- **Safety** (`06_safety_evaluation`): red-team the refund path specifically — can a crafted user message get `issue_refund` called without the approval gate firing (it can't, structurally, since `interrupt()` is inside the tool), can a poisoned `search_knowledge_base` chunk (§5.5's "untrusted data" warning, §7.4) talk the agent into a policy violation, does the agent ever leak one user's `("users", user_id, "facts")` memory to another thread.
- **Multi-agent evaluation** (`07_multi_agent_evaluation`): not applicable to this single-agent build — noted here only to flag that if you later split this into a router + specialist agents (§4.7), that chapter is where its coordination failure modes get tested.
- **Automated evaluation** (`09_automated_evaluation`): wire an LLM-as-judge harness that replays a fixed set of transcripts against this graph (mock the `httpx` calls, keep `interrupt()` auto-approving in test mode) and scores final answers against a rubric — this is how you regression-test the agent in CI on every prompt or tool-schema change.
- **Benchmark datasets** (`10_benchmark_datasets`): build a small, versioned set of order-support tasks (found order, missing order, eligible refund, ineligible refund, ambiguous multi-order query) with expected tool trajectories — this is your project-specific benchmark, built the way that chapter describes public ones being built.
- **Production monitoring** (`12_production_monitoring`): the OTel spans from §9.5 are exactly the online signal that chapter wants — tool-call latency and error rate per tool, refund-approval rate, budget-exceeded rate, cost per resolved conversation. Alert on the same `retryable`/error-code fields your tools already emit.

The point of building the agent this carefully is that every guardrail and every span above is also an evaluation *hook* — you are not bolting evaluation on afterward, you built it in.

---
## 10. Deploy & operate

Shipping the graph from §9 is the easy part; keeping it healthy under real traffic is where most agent projects actually fail. This section is deliberately tight — serving infrastructure and monitoring depth live in the sibling **llm-serving-inference-guide** and in `12_production_monitoring`; treat what follows as the agent-specific essentials, not a full ops manual.

### 10.1 Serving the agent

An agent server is a thin, stateful wrapper around the graph:

- **API shape.** One endpoint to start/continue a conversation (`POST /threads/{thread_id}/messages`), one to fetch pending state (`GET /threads/{thread_id}`) for surfacing an interrupt like the refund approval in §9.7, and one to resume it (`POST /threads/{thread_id}/resume`). Keep `thread_id` opaque and owned by your app, not the client.
- **Streaming.** Stream both token deltas (for the final answer) and *step events* (tool started, tool finished, interrupt raised) so the UI can show "checking order status…" rather than a silent spinner for 8 seconds. LangGraph's `stream_mode="values"`/`"updates"` and most provider SDKs support this natively.
- **Statelessness at the process level.** The graph process itself should be stateless — all durable state lives in the checkpointer/store (Postgres, Redis). That's what lets you run N identical replicas behind a load balancer and lets any replica pick up any `thread_id`.
- **Concurrency.** Each in-flight conversation is one graph execution; size your worker pool by expected concurrent conversations × average tool-call fan-out, not by request count alone — a single chat turn can spawn several outbound HTTP calls.
- **Deeper serving concerns** — autoscaling policy, GPU vs API-based model serving, load testing, canary rollouts of a new model version — are covered in depth in the `llm-serving-inference-guide` (see its `04_load_testing`, `06_autoscaling`, `07_canary_deployments`). Don't re-derive that here; go read it before you set SLOs.

### 10.2 Versioning — prompts, tools, and graphs together

The single most common agent-ops mistake is versioning the *model* carefully and the *prompt/tool surface* not at all. An agent's behavior is a function of (model version, system prompt, tool schemas, graph topology) as a unit — changing any one without tracking it makes regressions untraceable.

- **Pin and hash the bundle.** Compute a hash over `(system_prompt_text, [tool.schema for tool in TOOLS], graph_topology_id)` and stamp it into every trace (§9.5) as `agent_version`. When quality shifts in production, this is the first thing you correlate against.
- **Prompts live in version control, not a database string field.** Treat `prompts.py` (§9.1) like code: PR review, diff, changelog. A one-word change to a tool description (§5.2) can measurably change tool-selection accuracy — it deserves the same scrutiny as a code change.
- **Tool schemas are a contract.** Adding a required field or renaming a tool breaks in-flight conversations that were paused (e.g., at an `interrupt()`) referencing the old schema. Treat tool-schema changes like an API version bump: additive changes are safe, breaking changes need a migration path for any checkpointed-but-unresumed threads.
- **Graph topology changes need a migration story too.** If you add/remove/rename a node, an in-flight checkpoint pointing at a now-missing node will fail to resume. For short-lived conversations this is usually fine (let old threads drain); for long-lived ones, version the graph and route by which version a thread was created against.
- **A/B and canary the whole bundle, not just the model.** Route a percentage of `thread_id`s to a new (model, prompt, tools) bundle and compare the eval-chapter metrics (§9.9) and the online signals below before a full rollout — this is precisely what `07_canary_deployments` in the serving guide walks through mechanically; the agent-specific twist is that your "version" is the whole bundle hash above, not just a model tag.

### 10.3 What to monitor in production

Beyond generic service health (latency, error rate, uptime — see `12_production_monitoring` for the full treatment), an agent needs metrics generic APM doesn't give you for free:

| Signal | Why it matters | Where it comes from |
|---|---|---|
| Tool-call error rate, per tool | A silently-broken upstream (§5.3) degrades the agent long before users complain | The `ok`/`error_code` field on every tool return |
| Retry rate | Rising retries = an upstream is degrading before it fully fails | The `retryable` flag + your retry wrapper |
| Steps per conversation (distribution, not average) | A fat right tail means budget/loop guardrails (§8.3) are being hit | `step_count` at conversation end |
| Budget-exceeded rate | Direct signal the step cap is too low *or* the agent is regressing into loops | The `budget_exceeded` node firing |
| Interrupt/approval rate + approval outcome | Tracks how often humans are in the loop and whether they're rubber-stamping (a sign the gate is miscalibrated) | The `interrupt()` payload + resume value |
| Cost and tokens per resolved conversation | The actual unit economics, not per-call cost (§8.1) | Summed `usage_metadata` across all `call_model` spans in a thread |
| Tool-selection distribution drift | A model/prompt update silently changing *which* tools get called is an early regression signal | Aggregated tool-call spans, compared week over week |

Treat any of these that moves sharply after a deploy as a rollback trigger, the same way you'd treat a latency or error-rate spike for a normal service — the difference is you have to *instrument for it explicitly*, because a standard APM has no concept of "tool call" or "step."

### 10.4 Incident response for agents

Agents fail in agent-shaped ways that a standard runbook doesn't cover:

- **Runaway loop / cost spike:** the step cap (§8.3) is your circuit breaker; if it's firing constantly, that's the incident, not a false alarm — find out what changed (model update, tool description edit, upstream returning malformed data) before raising the cap.
- **A tool silently degraded** (returns `200` with garbage instead of erroring): your error contract can't catch this — add a lightweight output-shape check on high-risk tools (does `get_order_status` ever return a `status` outside the known enum?) and alert on it.
- **Approval-gate bypass attempt:** because `interrupt()` is structural (§9.6), a bypass would have to be a code regression, not a prompt-injection success — but verify this in red-teaming (`06_safety_evaluation`) rather than assuming the architecture makes it impossible.
- **Rollback is a bundle rollback.** Because you versioned (model, prompt, tools, graph) as a unit (§10.2), rolling back means routing new `thread_id`s to the previous bundle hash — don't try to roll back just the model while leaving a prompt written for the new one in place.

For the deeper operational playbook — dashboards, alert thresholds, on-call rotations, postmortem templates — see `12_production_monitoring/PRODUCTION_MONITORING_DEEP_DIVE.md`; this section only covers what's specific to agents.

---
## 11. Interview mastery

This section is build-focused — it complements `INTERVIEW_QA.md`'s evaluation-focused bank with the questions a senior interviewer asks when they want to know **can this person actually build the agent, not just grade one.** Same method as that bank: read the answer once for shape, then re-answer out loud from memory, and volunteer the trade-off before you're asked.

### 11.1 Build-focused Q&A

**Q1. Why would you reach for LangGraph over CrewAI for a customer-support agent like the one in §9?**
Intuition: it comes down to how much explicit control you need over state and failure recovery. CrewAI's role/crew abstraction gets you to a demo fastest — define agents with roles and goals, assemble a crew, done. LangGraph makes you model the graph explicitly: nodes, edges, a typed state object. That's more upfront work, but it buys durable checkpointing (§9.6), first-class human-in-the-loop pauses (`interrupt()`), and the ability to unit-test individual nodes. For a support agent that issues refunds and must survive a process restart mid-approval, that durability isn't optional — it's the requirement. For a rapid internal prototype with no side effects, CrewAI would get me to a demo faster and I'd say so. *Follow-up to expect:* "when would CrewAI actually be the better call?" — rapid multi-agent prototyping, hierarchical business-process automations, when time-to-demo beats long-term control.

**Q2. How do you handle a runaway agent loop in production?**
Mechanism, layered: (1) a hard step cap in the graph itself (§8.3, §9.6) that routes to a graceful "budget exceeded" exit rather than looping forever; (2) loop/no-progress detection — compare the last N tool calls, and if the same call with the same args repeats, break early rather than waiting for the cap; (3) a wall-clock and a dollar budget per conversation, not just a step count, because a single step can be expensive; (4) alerting on the *rate* of budget-exceeded events, because a spike means something upstream regressed (a tool started failing, a prompt edit confused the model), not that the cap is wrong. Trade-off: too tight a cap truncates legitimately long tasks; tune it from observed p95 step counts on real traffic, not a guess.

**Q3. How do you version prompts and tools together?**
The core insight: an agent's behavior is a function of (model, system prompt, tool schemas, graph topology) as one unit, and versioning only the model is the most common mistake (§10.2). Concretely: prompts live in version control like code, not a database string; hash the (prompt, tool schemas, topology) bundle and stamp that hash into every trace; canary a new bundle on a percentage of traffic and compare eval metrics before full rollout; treat tool-schema changes like API versioning — additive is safe, breaking changes need a migration path for any checkpointed-but-unresumed conversation. Failure mode if you skip this: a "the model got worse" incident that was actually a one-word tool-description edit nobody tracked.

**Q4. When would you NOT use a framework at all?**
When you don't yet know your own pain points. A provider SDK, a while-loop, and a dict of tools is enough for most first agents, and it forces you to understand exactly what a framework would later automate — the control loop, the tool dispatch, the context assembly. Adopt a framework when you feel a specific, recurring pain: you need durable resumable state, multi-agent orchestration, or standardized tracing across a team of agents. The trap is adopting a heavyweight framework preemptively and paying its learning curve before you've earned the need for its features (§3.1).

**Q5. How do you decide between RAG and long context for a given corpus?**
Ask three questions: does the corpus fit comfortably in the window with room to spare (if not, RAG); does it change frequently (if yes, RAG — re-embedding is cheaper than re-sending a stale mega-prompt, and you need freshness); does the task need *global* reasoning across the whole corpus at once, or can it be answered from a narrow slice (global reasoning favors long context, narrow lookup favors RAG). In practice the strongest systems are hybrid: retrieve to narrow, then give the model generous context on the narrowed set (§6.1) — that combines RAG's cost control with long-context's ability to reason across what it did retrieve.

**Q6. How do you design a tool that an LLM can use reliably?**
Two audiences, one artifact (§5.1): the model reads the name/description/schema to decide whether and how to call it; your runtime executes it. Get the description right first — state when to use it *and* when not to, in plain language, because the model chooses tools purely from that text. Make parameters typed and unambiguous (enums over free strings). Return concise, structured results, not raw dumps the model has to parse out of noise. And design the error path with the same care as the success path — a good error tells the model exactly how to recover, because errors are the agent's only feedback signal when something goes wrong.

**Q7. How do you gate an irreversible action like a refund or a delete?**
Structurally, not by hoping the model behaves. In LangGraph, call `interrupt()` inside the tool itself (§9.3, §9.6) so the entire graph run pauses and checkpoints exactly at that point — there's no window where the side effect can happen without a human resuming with an explicit approval. Add an idempotency key on the actual write so a retried resume can't double-execute it. The key point to say out loud in an interview: this makes the gate a *structural* property of the graph, testable and provable, not a prompt instruction the model might ignore under adversarial input — which is also exactly what you'd verify in red-teaming (`06_safety_evaluation`).

**Q8. How do you keep cost under control in a long, multi-step agent loop?**
Highest-impact first (§8.1): prompt caching on the stable prefix (system prompt, tool schemas) — often a 5–10x reduction on its own for a looping agent; model cascades, routing cheap/fast models to easy steps (extraction, routing) and reserving the flagship for hard planning; aggressive context compaction so every step carries fewer tokens, not just the first one; structured outputs to eliminate malformed-output retries; and a hard step/token budget as the backstop so a bug can't produce an unbounded bill. I'd instrument cost per *resolved conversation*, not per call, because that's the number that maps to unit economics.

**Q9. How do you decide when to add a second agent instead of scaling a single agent?**
Default to a single agent with good tools (§4.7) — multi-agent coordination overhead routinely exceeds its benefit. The signal to actually split is when a single context window provably can't hold what's needed (genuinely separable expertise, or the task decomposes into independent, parallelizable pieces of unknown count) — not "this feels like it should have multiple agents." If I do split, I want independent, structured worker outputs and explicit budgets per worker, because the two failure modes that kill multi-agent systems are synthesis loss (orchestrator can't reconcile conflicting outputs) and cost fan-out.

**Q10. What's the difference between memory and RAG, and how do you implement both in one agent?**
RAG answers "what external knowledge does the model need this turn" — pulled from a corpus you have. Memory answers "what should the agent remember about this task/user over time" — persisted from what the agent itself produced (§6). In the agent from §9: RAG is `search_knowledge_base` over the policy corpus, called as a tool whenever the model decides it needs facts; memory is the `store` — a per-user namespace of durable facts, read at the start of every turn (like RAG, top-k, not everything) and written out-of-band after a session, not on every loop iteration.

**Q11. How do you handle context rot in a long-running agent?**
Treat the window as a curated workspace, not a junk drawer (§7.1). Concretely: summarize older turns once the transcript passes a threshold, keeping the last few verbatim; prune tool outputs to what's model-legible, not raw dumps; retrieve narrowly rather than stuffing a full corpus in; and order/delimit what's in context so the model can tell instruction from data. The MemGPT-style pattern (§6.2) of giving the agent its own memory tools — let it decide what to page out — scales better than a hand-tuned truncation rule as tasks get longer.

**Q12. How do you test tool error handling without hitting a real production system?**
Mock the tool's HTTP layer (or the tool function directly) to return each branch of its error contract deliberately — 404, timeout, malformed upstream response — and assert the agent recovers sensibly for each (retries the transient one, doesn't retry the permanent one, surfaces a clear message for the unrecoverable one). This is exactly the harness `04_tool_use_evaluation` describes for testing error handling, and it should run in CI on every prompt or tool-schema change, not just at build time.

**Q13. What's your approach to prompt-injection defense in an agent that reads external content (web pages, retrieved docs, tool output)?**
Treat everything that flows in through a tool or retrieval call as untrusted *data*, never instructions (§7.4) — that's a system-prompt rule, reinforced by clearly delimiting external content from the actual instructions (XML-ish tags, explicit headers). Pair that with least-privilege tools (the agent can't do anything an injected instruction could actually weaponize if it succeeded), and a human-confirmation gate on anything irreversible regardless of what convinced the model to try it. I'd validate this isn't just a policy but a tested property, via red-teaming (`06_safety_evaluation`) with crafted injection payloads in retrieved content.

**Q14. How do you choose between a reasoning ("thinking") model and a fast model for a given step?**
Per-step, not per-app (§2.3, §2.7). Thinking pays off where a wrong first step cascades — multi-step planning, ambiguous tool selection, debugging. It doesn't pay off on classification, routing, or simple extraction — burning thinking tokens deciding "which of these three tools" is money and latency lit on fire. My default shape: a cheap non-thinking model as the router and for leaf tool calls, a thinking model reserved for the planning/synthesis step. Most real agents use two or three models, not one.

**Q15. How would you migrate an agent from a hand-rolled loop to a framework like LangGraph?**
Because the concepts port cleanly (§3.3), the migration is mostly mechanical: your existing tool functions become framework tool objects with the same schemas; your while-loop's state becomes a typed state object; your ad hoc "if error, retry" becomes the framework's retry/error handling; and any manual "save progress to a file" becomes a checkpointer. The part that actually takes judgment is deciding whether your control flow is a straight ReAct loop (maps directly to a two-node graph) or has implicit branching you never noticed until you had to draw it as an explicit graph — that's usually where the migration surfaces bugs that existed all along.

**Q16. How do you instrument an agent for observability from day one, before you have a production incident to react to?**
Wrap every node and tool call in a structured span (§9.5) that records enough to reconstruct the trajectory offline: tool name and args, duration, tokens in/out, ok/error outcome. Do it in OpenTelemetry or an LLM-trace-specific tool (LangSmith, Langfuse) so it plugs into whatever your monitoring stack already ingests. The test I'd apply: could I take one trace and answer "why did this conversation cost \$0.40 and take 11 steps" without re-running it? If not, the instrumentation is incomplete.

**Q17. What's the single most common mistake you see in agent builds?**
Two tie for first place: shipping without a step/cost budget (an agent that works in the demo and produces a five-minute, twelve-dollar response on one weird production input), and treating the framework choice as the hard decision when it's actually the *most reversible* one (§3.3) — while under-investing in tool design and error contracts, which are what actually caps agent quality and are expensive to fix later because every downstream eval and guardrail assumes a stable tool surface.

**Q18. How do you handle human-in-the-loop approval without blocking your whole system on a human being available?**
Structurally pause just that one conversation, not the service (§9.6, §9.7) — a durable interrupt/checkpoint means the graph process is free to serve other conversations while one sits paused waiting for approval; the approval can come minutes or days later without holding a thread or a connection open. Operationally: alert if an approval sits unresolved past an SLA, and track the approval *rate* over time — if humans are approving 99.9% of requests with no changes, that's a signal the gate is theater and either the gate should be tightened or removed with a different guardrail in its place.

### 11.2 The 60-second "how would you build a production agent" answer

Memorize the *shape*, not the words:

> "I'd start with the smallest thing that could work — a provider SDK, a ReAct loop, and a small set of well-described tools — and only reach for a framework like LangGraph once I feel a specific pain: durable state, human-in-the-loop, or multi-agent orchestration. Every tool gets a typed schema, a hard timeout, and a structured ok/error contract, because that error contract is the agent's only feedback signal. I'd add memory in two layers — short-term as the running transcript, long-term as a small per-user fact store retrieved like RAG, not dumped in whole. Then guardrails: a step and dollar budget, retries on transient failures only, and a structural human-approval gate — not a prompt instruction — on anything irreversible. I'd instrument every node and tool call with a structured trace from day one, because that trace is simultaneously my production monitoring signal and the input to the tool-use and trajectory evaluators I'd build next. And I'd pick the model per step — a fast model for routing and leaf calls, a stronger or reasoning model for planning — because most agents are two or three models, not one. Finally, I'd version the model, prompt, tools, and graph as a single bundle, because that's the unit that actually changes agent behavior, and I'd build a small task-specific eval set before I called it done, not after."

That's the whole architecture in one breath: minimal-first, typed tools, layered memory, structural guardrails, tracing baked in, per-step model choice, and versioning-plus-eval as part of "done," not an afterthought.

### 11.3 System design: "Design and build a coding agent that opens PRs"

**The prompt, as an interviewer would give it:** *"Design a coding agent that takes a GitHub issue, makes the code change, runs tests, and opens a pull request. Walk me through the architecture, the tools, the guardrails, and how you'd evaluate it."*

**Worked answer.**

*Clarify scope first (30 seconds):* single repo or many? Can it merge, or only open a PR for human review? What's the blast radius of a bad change — is this touching production infra code or a low-risk internal tool? I'll assume: many repos, opens PRs but never merges, and runs in a sandboxed checkout — the answer changes a lot at each of those knobs, and saying so out loud is itself a signal.

*Architecture (ASCII sketch):*

```
 GitHub issue/ticket
        │
        ▼
  ┌───────────┐     repo map / codebase index (RAG over the repo, §6.1)
  │  Intake   │────────────────────────────────────────────┐
  └─────┬─────┘                                             │
        ▼                                                   ▼
  ┌───────────┐   plan: files to touch, approach      ┌────────────┐
  │  Planner  │──────────────────────────────────────►│  (context)  │
  └─────┬─────┘                                        └────────────┘
        ▼
  ┌─────────────────────────────────────────────────────────────┐
  │                    Coding loop (ReAct, §4.1)                 │
  │   tools: read_file, edit_file, bash (sandboxed), grep,       │
  │          run_tests                                           │
  │                                                                │
  │   thought → tool call → observation → repeat, capped at      │
  │   MAX_STEPS, timeouts per tool, loop detection (§8.3)         │
  └───────────────────────┬───────────────────────────────────────┘
                           │ tests fail ──► re-plan (bounded retries)
                           ▼ tests pass
                  ┌─────────────────┐
                  │ Reviewer/critic  │   evaluator–optimizer (§4.6):
                  │ (separate pass)  │   diff review against style/
                  └────────┬─────────┘   correctness rubric
                           │ pass
                           ▼
                  ┌─────────────────────────┐
                  │ Guardrail: diff-size cap │   too large → split into
                  │ + human review gate      │   smaller PRs or flag for
                  └────────┬─────────────────┘   manual review
                           │ approved
                           ▼
                  ┌─────────────────┐
                  │ Open PR + post   │
                  │ summary comment  │
                  └─────────────────┘
```

*Tools, with the same discipline as §5.4/§9.3:* `read_file`/`grep` (read-only, cheap, no gate), `edit_file` (writes only inside a disposable sandboxed checkout — never the real working tree — returns a structured diff, not a raw file dump), `bash` (heavily sandboxed: no network, resource-limited container, timeout, allow-listed commands where possible), `run_tests` (times out generously since test suites are slow, but *does* time out), and `open_pr` (the one genuinely external-effect tool — gated behind the diff-size + review guardrail, exactly like `issue_refund` in §9.3).

*Guardrails specific to this agent:* a maximum diff size (a 4,000-line auto-generated PR is a red flag, not a deliverable — cap it and split or escalate); sandbox isolation for `bash`/`edit_file` so a bad command can't touch anything outside the disposable checkout; a bounded re-plan loop when tests fail (say, 3 attempts) rather than an unbounded "keep trying"; and a human-review gate before `open_pr` fires for anything touching a configurable list of sensitive paths (auth, payments, infra-as-code).

*Memory:* short-term is the coding-loop transcript; long-term is a per-repo fact store — coding conventions learned from past reviews, "this repo's tests are flaky in module X," prior PR feedback patterns — retrieved the same way as §6.2, not reloaded in full every run.

*How I'd evaluate it:* tool-use eval (`04_tool_use_evaluation`) on whether `edit_file` calls stay inside the sandbox and whether `run_tests` is called before `open_pr` every time; reasoning eval (`05_reasoning_evaluation`) on plan quality — did it touch the right files, did it re-plan sensibly on test failure; a benchmark (`10_benchmark_datasets`) built from real closed issues in the target repos with known-good diffs, scored on SWE-bench-style pass rate; safety (`06_safety_evaluation`) on whether it ever tries to touch a sensitive path or exfiltrate a secret it reads while browsing the repo; and production monitoring (`12_production_monitoring`) on PR-acceptance rate and average human-review edit distance once it's live — the single best real-world proxy for "is this agent actually good," because it's measuring exactly what a human reviewer decided.

*The trade-off I'd flag unprompted:* this is exactly the kind of task where a coding-native harness (the Claude Agent SDK, which is Claude Code's own harness — Read/Edit/Bash/Glob built in, permissions and hooks for the sandboxing) gets you most of this scaffolding for free, versus hand-building the same tools in LangGraph. I'd name that trade-off explicitly rather than default to "the framework I already know."

### 11.4 Tradeoff tables

**Framework choice** (interview framing — the question behind the question is usually "do you actually understand the trade-off, or did you just memorize a name"):

| Choice | Pick it when | Walk away when |
|---|---|---|
| **No framework** (SDK + loop) | You don't yet know your own pain points; task is simple/short-lived | You need durable resumable state or team-wide standardized tracing |
| **LangGraph** | You need explicit, testable, resumable state; human-in-the-loop pauses; non-trivial branching | Team has no appetite for the graph mental model; task is a simple one-shot tool call |
| **OpenAI Agents SDK** | OpenAI-centric stack; want handoffs + guardrails fast | You need deep, provider-agnostic control or heavy custom state |
| **Claude Agent SDK** | Autonomous coding/ops/computer-use tasks; want Claude Code's harness (permissions, hooks, subagents) for free | Task isn't code/ops-shaped; you need a different provider's frontier model |
| **CrewAI / AG2** | Rapid multi-agent prototype; role-based decomposition is a natural fit | Production reliability and fine-grained control matter more than time-to-demo |
| **LlamaIndex** | Retrieval over your data *is* the product | Agent's center of gravity is action/tools, not documents |

**RAG vs. long context** (this is one of the most common "do you actually understand the mechanism" probes):

| Signal | Favors RAG | Favors long context |
|---|---|---|
| Corpus size vs. window | Larger than fits comfortably | Fits with room to spare |
| Update frequency | Changes often — freshness matters | Mostly static |
| Reasoning scope | Narrow lookup, a few facts | Global reasoning across the whole corpus at once |
| Cost sensitivity | High — pay only for what's retrieved | Lower priority, or caching absorbs it |
| Best real answer | Hybrid: retrieve to narrow, then give generous context on the narrowed set | — |

**Single agent vs. multi-agent** (the trap this table exists to name: defaulting to multi-agent because it sounds sophisticated):

| Signal | Favors single agent | Favors multi-agent |
|---|---|---|
| Default | **Yes — start here** | Only once single-agent provably can't cope |
| Context size | Fits in one window with good tools | Genuinely can't fit; each role needs its own focused context |
| Task shape | Sequential, tool-heavy | Genuinely separable expertise, or parallel variable-count subtasks |
| Coordination cost | None to manage | Real — synthesis loss, error propagation, cost fan-out are all live risks |
| Failure signature if you get it wrong | Under-scaffolded for a huge task | Overhead exceeds benefit; harder to eval and debug (`07_multi_agent_evaluation`) |

### 11.5 Build-competence signals: red flags vs. green flags

What a strong interviewer is actually listening for, framed as what you'd hear in a candidate's answer:

| Signal | Red flag | Green flag |
|---|---|---|
| Framework talk | Names a framework with no mention of *why*, or treats it as the hard decision | Calls the framework the most reversible choice (§3.3); names the specific pain it solves |
| Tool design | "The model just calls the API" | Describes the description-as-prompt discipline, typed schemas, and an explicit error contract (§5) |
| Error handling | No mention of retries/timeouts, or retries everything indiscriminately | Distinguishes transient (retryable) from permanent failures; hard timeouts on every call |
| Irreversible actions | "The prompt tells it to ask for confirmation" | Describes a *structural* gate (interrupt/approval), not a prompt-level instruction |
| Cost | Never mentions tokens, caching, or model tiering | Leads with caching and cascades as the highest-leverage cost levers (§8.1) |
| Memory | Conflates memory and RAG, or "just put everything in context" | Distinguishes short-term/long-term, retrieves memory top-k like RAG, writes it out-of-band |
| Multi-agent | Reaches for multi-agent by default, "for scale" | Defaults to single agent; names the specific signal that would justify splitting (§4.7) |
| Observability | "We'd add logging later" | Describes tracing as built in from day one, doubling as the eval-harness input |
| Versioning | Versions the model only | Versions (model, prompt, tools, graph) as one bundle, hashed into every trace |
| Evaluation | Treats "it works in the demo" as done | Names a specific eval (tool-use, trajectory, safety) they'd run before shipping, unprompted |

---
## 12. Further reading

Every link below was checked (mid-2026) before being included. Frameworks and pricing move monthly — treat versions/prices as snapshots and re-check before you cite a number from any of these in a design doc.

### 12.1 Foundational papers (the ideas behind §4 and §6)

- **ReAct: Synergizing Reasoning and Acting in Language Models** — Yao et al., 2022. The paper behind §4.1's core loop. [arxiv.org/abs/2210.03629](https://arxiv.org/abs/2210.03629)
- **Reflexion: Language Agents with Verbal Reinforcement Learning** — Shinn et al., 2023 (NeurIPS 2023). Verbal self-feedback stored in memory across attempts; the basis of §4.3's reflection pattern. [arxiv.org/abs/2303.11366](https://arxiv.org/abs/2303.11366) · [github.com/noahshinn/reflexion](https://github.com/noahshinn/reflexion)
- **Self-Refine: Iterative Refinement with Self-Feedback** — Madaan et al., 2023. The other half of §4.3 — draft, critique, revise, without an external reward signal. [arxiv.org/abs/2303.17651](https://arxiv.org/abs/2303.17651)
- **MemGPT: Towards LLMs as Operating Systems** — Packer et al., 2023. The paging/tiered-memory idea behind §6.2's memory recipe. [arxiv.org/abs/2310.08560](https://arxiv.org/abs/2310.08560) · [research.memgpt.ai](https://research.memgpt.ai/)
- **τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains** — Sierra Research, 2024. The benchmark referenced for tool-heavy, multi-turn agent evaluation; a `tau2-bench` successor is active. [arxiv.org/abs/2406.12045](https://arxiv.org/abs/2406.12045) · [github.com/sierra-research/tau-bench](https://github.com/sierra-research/tau-bench)

### 12.2 Anthropic engineering writing (the practical counterpart to the papers above)

- **Building Effective Agents** — the widely-cited practical framework for workflows vs. agents and the architecture patterns in §4. [anthropic.com/engineering/building-effective-agents](https://www.anthropic.com/engineering/building-effective-agents)
- **How we built our multi-agent research system** — the real-world writeup behind §4.5/§4.7's orchestrator–worker pattern and its failure modes. [anthropic.com/engineering/multi-agent-research-system](https://www.anthropic.com/engineering/multi-agent-research-system)
- **Anthropic Cookbook — agent patterns** — runnable reference implementations of several §4 patterns. [github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents](https://github.com/anthropics/anthropic-cookbook/tree/main/patterns/agents)
- **Claude pricing** — for verifying the §2.1 table against current numbers. [platform.claude.com/docs/en/about-claude/pricing](https://platform.claude.com/docs/en/about-claude/pricing)

### 12.3 Framework documentation (§3, §9)

- **LangGraph — overview & docs.** [docs.langchain.com/oss/python/langgraph/overview](https://docs.langchain.com/oss/python/langgraph/overview) · source: [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph)
- **LangGraph 1.0 announcement** (LangChain + LangGraph reaching GA together, Oct 2025). [langchain.com/blog/langchain-langgraph-1dot0](https://www.langchain.com/blog/langchain-langgraph-1dot0)
- **OpenAI Agents SDK** — Python docs and source. [openai.github.io/openai-agents-python](https://openai.github.io/openai-agents-python/) · [github.com/openai/openai-agents-python](https://github.com/openai/openai-agents-python)
- **OpenAI API pricing** — for verifying the §2.1 table. [developers.openai.com/api/docs/pricing](https://developers.openai.com/api/docs/pricing)
- **Claude Agent SDK — overview.** [platform.claude.com/docs/en/agent-sdk/overview](https://platform.claude.com/docs/en/agent-sdk/overview)
- **AG2 (community AutoGen fork) docs.** [docs.ag2.ai](https://docs.ag2.ai/latest/) · source: [github.com/ag2ai/ag2](https://github.com/ag2ai/ag2)
- **CrewAI docs.** [docs.crewai.com](https://docs.crewai.com/)
- **LlamaIndex docs.** [docs.llamaindex.ai](https://docs.llamaindex.ai/)
- **Pydantic AI docs.** [pydantic.dev/docs/ai](https://pydantic.dev/docs/ai/core-concepts/agent/)
- **smolagents docs.** [huggingface.co/docs/smolagents](https://huggingface.co/docs/smolagents/index) · source: [github.com/huggingface/smolagents](https://github.com/huggingface/smolagents)

### 12.4 Model Context Protocol (§5.5)

- **MCP specification, 2025-11-25 revision** — the current spec version discussed in §5.5 (async tasks, elicitation, extensions, MCP Apps). [modelcontextprotocol.io/specification/2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- **MCP specification, 2026-07-28 revision** — supersedes 2025-11-25: the stateless-core rewrite (dropped session/handshake), Multi Round-Trip Requests, header-based routing, cache hints on list results, and deprecation of Roots/Sampling/Logging (12-month sunset). [blog.modelcontextprotocol.io/posts/2026-07-28](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- **MCP joins the Agentic AI Foundation** (Dec 2025) — the governance handoff from Anthropic to the Linux Foundation–hosted foundation. [blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation](https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/)
- **MCP spec & schema source** (for tracking future revisions). [github.com/modelcontextprotocol/modelcontextprotocol](https://github.com/modelcontextprotocol/modelcontextprotocol)

### 12.5 Memory systems (§6.2)

- **Letta docs** (the MemGPT team's production memory platform). [docs.letta.com](https://docs.letta.com/)
- **Mem0 docs.** [docs.mem0.ai](https://docs.mem0.ai/)
- **Zep docs** ("agent memory at enterprise scale"). [help.getzep.com](https://help.getzep.com/)

### 12.6 Where the rest of this book picks up

Once you've built the agent in §9, the natural next reading is inside this repository, not outside it: start with `01_agentic_ai_fundamentals` for the vocabulary this chapter assumed, then go straight to `04_tool_use_evaluation` and `06_safety_evaluation` to build the eval harness for exactly the tools and guardrails you just wrote. For the deployment side of §10, the sibling `llm-serving-inference-guide` repository covers load testing, autoscaling, and canary rollout in the depth this chapter deliberately left out.


### 12.7 Talks and community resources

- **LangChain Interrupt** — LangChain's annual agent-engineering conference; sessions cover production LangGraph patterns, durable execution, and multi-agent design directly relevant to §9–§10. Check [langchain.com/interrupt](https://www.langchain.com/interrupt) for the current year's talk recordings.
- **AI Engineer Summit / World's Fair** talks on agent evaluation and production agents — a recurring venue where teams publish real "what broke in production" postmortems that pair well with §10.4's incident-response guidance. [ai.engineer](https://www.ai.engineer/)
- **MCP Registry** — the public index of MCP servers referenced in §5.5, useful for finding existing servers before writing your own. [github.com/modelcontextprotocol/registry](https://github.com/modelcontextprotocol/registry)

### 12.8 A minimal test suite for the agent in §9

One last practical note before you close this chapter: the agent built in §9 is only as trustworthy as the tests around it. A minimal `pytest` suite — separate from, and a prerequisite to, the full evaluation harness in the rest of this book — should cover at least:

```python
# test_agent.py
from unittest.mock import patch
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from agent import graph

def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}

def test_order_not_found_returns_structured_error():
    with patch("tools.httpx.get") as mock_get:
        mock_get.return_value.status_code = 404
        state = graph.invoke(
            {"messages": [HumanMessage("Where's order Z-999?")],
             "user_id": "u_test", "step_count": 0},
            config=_config("t-1"),
        )
    assert "Z-999" in state["messages"][-1].content  # model surfaces the not-found clearly

def test_refund_pauses_for_approval_and_resumes():
    config = _config("t-2")
    state = graph.invoke(
        {"messages": [HumanMessage("Refund $10 on order A-1, it never arrived.")],
         "user_id": "u_test", "step_count": 0},
        config=config,
    )
    assert graph.get_state(config).next            # graph is paused at interrupt()
    final = graph.invoke(Command(resume=True), config=config)
    assert not graph.get_state(config).next          # resumed to completion

def test_budget_exceeded_stops_gracefully():
    # Feed a state already at the cap and confirm the graph exits via budget_exceeded,
    # not by looping past MAX_STEPS.
    state = graph.invoke(
        {"messages": [HumanMessage("Do something open-ended and multi-step.")],
         "user_id": "u_test", "step_count": 12},
        config=_config("t-3"),
    )
    assert "step budget" in state["messages"][-1].content.lower()
```

None of this replaces the tool-use, trajectory, and safety evaluation described in §9.9 — it's the layer *underneath* that, the same way unit tests sit underneath integration tests for any other service. Ship the agent with both.

### 12.9 Appendix: what a trace from §9 actually looks like

To make §9.5's "structured span" concrete rather than abstract, here is a trimmed, illustrative export of the spans one real conversation would produce — the refund example from §9.7, flattened to JSON. This is the shape both your offline evaluators (§9.9) and your online dashboards (§10.3) consume.

```json
{
  "thread_id": "conv-42",
  "agent_version": "sha256:9f2a...c71",
  "spans": [
    {
      "name": "agent.call_model",
      "step": 0,
      "input_tokens": 1180,
      "output_tokens": 64,
      "stop_reason": "tool_use",
      "duration_ms": 812.4,
      "tool_calls": [{"name": "search_knowledge_base", "args": {"query": "damaged item refund policy"}}]
    },
    {
      "name": "tool.search_knowledge_base",
      "step": 0,
      "duration_ms": 143.2,
      "ok": true,
      "chunks_returned": 3
    },
    {
      "name": "agent.call_model",
      "step": 1,
      "input_tokens": 1390,
      "output_tokens": 71,
      "stop_reason": "tool_use",
      "duration_ms": 764.9,
      "tool_calls": [{"name": "get_order_status", "args": {"order_id": "A-118"}}]
    },
    {
      "name": "tool.get_order_status",
      "step": 1,
      "duration_ms": 96.7,
      "ok": true,
      "retries": 0
    },
    {
      "name": "agent.call_model",
      "step": 2,
      "input_tokens": 1520,
      "output_tokens": 58,
      "stop_reason": "tool_use",
      "duration_ms": 701.3,
      "tool_calls": [{"name": "issue_refund",
                       "args": {"order_id": "A-118", "amount_usd": 30.0,
                                "reason": "arrived damaged"}}]
    },
    {
      "name": "tool.issue_refund",
      "step": 2,
      "duration_ms": 2.1,
      "interrupted": true,
      "interrupt_payload": {"prompt": "Approve $30.00 refund for order A-118? Reason: arrived damaged"}
    },
    {
      "name": "human.approval",
      "resumed_after_ms": 41200.0,
      "decision": true
    },
    {
      "name": "tool.issue_refund",
      "step": 2,
      "duration_ms": 118.5,
      "ok": true,
      "refund_id": "R-A-118"
    },
    {
      "name": "agent.call_model",
      "step": 3,
      "input_tokens": 1610,
      "output_tokens": 46,
      "stop_reason": "end_turn",
      "duration_ms": 588.0
    }
  ],
  "totals": {"steps": 4, "input_tokens": 5700, "output_tokens": 239,
             "wall_clock_ms": 43604.1, "human_wait_ms": 41200.0,
             "tool_errors": 0, "budget_exceeded": false}
}
```

Reading this trace end to end tells you almost everything §10.3's metric table asks for: cost (sum the token fields, apply current pricing from §12.2/§12.3), whether the agent stayed within budget (`totals.steps` vs. `MAX_STEPS`), where wall-clock actually went (`human_wait_ms` dominates here — the model itself took well under 3 seconds of compute; the conversation took 43 seconds because a human had to approve a refund), and whether any tool degraded (`tool_errors`). This is also exactly the shape a trajectory evaluator (`05_reasoning_evaluation`) or a tool-use evaluator (`04_tool_use_evaluation`) would parse to score the run — build the trace once, and both your production dashboards and your offline evals read the same artifact.

### 12.10 Quick-reference: minimum viable production checklist

A last, deliberately compressed artifact — pull this up before you ship anything built the way §9 describes. Every row cross-references the section where the *why* lives.

| # | Check | Section |
|---|---|---|
| 1 | Every tool has a typed schema and a description that says when *not* to use it | §5.2 |
| 2 | Every tool returns a structured `{"ok", "error_code", "message", "retryable"}` result — never a raw exception | §5.3, §9.3 |
| 3 | Every outbound call (tool, model) has a hard timeout | §8.3, §9.3 |
| 4 | Transient failures retry with backoff; permanent failures do not | §8.3, §9.3 |
| 5 | A hard step/token/dollar budget exists, with a graceful (not silent) exit when hit | §8.3, §9.6 |
| 6 | Loop / no-progress detection is implemented, not just planned | §8.3, §9.8 |
| 7 | Every irreversible action sits behind a structural approval gate, not a prompt instruction | §8.4, §9.3 |
| 8 | Side-effecting writes carry an idempotency key | §8.3, §9.3 |
| 9 | Short-term memory (checkpointer) and long-term memory (store) are both wired, with memory read top-k, not dumped whole | §6.2, §9.4 |
| 10 | Every node and tool call emits a structured span with enough fields to reconstruct the trajectory offline | §9.5, §12.9 |
| 11 | The (model, prompt, tools, graph) bundle is hashed and stamped into every trace | §10.2 |
| 12 | Prompts and tool schemas live in version control with PR review, not a database string | §10.2 |
| 13 | A small, versioned, task-specific eval set exists and runs in CI on every prompt/tool change | §9.9, §10.2 |
| 14 | Red-teaming has specifically targeted the approval gate and any content the agent reads from untrusted sources | §7.4, §9.9 |
| 15 | Dashboards exist for tool error rate, retry rate, step-count distribution, budget-exceeded rate, and cost per resolved conversation — not just generic latency/uptime | §10.3 |
| 16 | A rollback plan exists and rolls back the *whole bundle*, not just the model | §10.2, §10.4 |

If you can check every row, you have shipped an agent with the guardrails this chapter argued for — not just a demo that happened to work the day you recorded it.

---

*End of Agent Engineering Foundations. Continue to the evaluation chapters — `01_agentic_ai_fundamentals` through `12_production_monitoring` — to learn how to systematically test everything built here.*
