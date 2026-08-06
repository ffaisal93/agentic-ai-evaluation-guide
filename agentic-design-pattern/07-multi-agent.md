# Pattern 7: Multi-Agent Collaboration — a team of specialists instead of one overworked generalist

## The interview scenario

Multi-agent questions come in two flavors — the build flavor and the judgment flavor:

- "Design a content-production system: a product brief goes in, and a researched, written, edited,
  fact-checked article comes out."
- "Design an automated code-review system where different concerns — correctness, security, style — each
  get real attention."
- "Your team wants to split our single assistant into six specialized agents. Is that a good idea? How
  would you decide, and how would the agents coordinate?"

That third phrasing is the trap version, and it's increasingly common. The interviewer is checking whether
you reach for a swarm of agents reflexively or whether you can argue for the simplest architecture that
works.

## What this pattern is, in plain words

One agent with a pile of tools is a talented generalist. For a lot of tasks that's exactly right. But as
the task sprawls across domains — research *and* writing *and* editing *and* compliance — the generalist
starts to buckle.

Its instructions grow into a novel trying to describe every duty at once. Its tool list grows past the
point of reliable selection. And its context — the model's working memory, the finite window of text it
can consider at once — fills with material from one sub-task while it's trying to do another.

Multi-Agent Collaboration is the organizational fix: break the objective into sub-problems, and give each
sub-problem to a separate agent with its own focused instructions, its own small tool set, and its own
slice of context. Then wire the agents together so work flows between them.

The analogy is a small newsroom. A researcher digs up facts. A writer turns them into a draft. An editor
sharpens it. A fact-checker challenges it. Nobody does everybody's job, and the value isn't just the
division of labor — it's that each role can be *good* at its narrow thing, and the roles check each other.

Each "agent" here is the same underlying machinery you already know — a model, instructions, tools, the
tool-use loop — just scoped narrowly. The new engineering is everything *between* the agents: who talks to
whom, in what format, and who decides what happens next.

One framing worth saying aloud in an interview: a multi-agent system is Tool Use turned inward. To an
orchestrating agent, a specialist agent looks exactly like a tool — Google's ADK makes this literal with
an AgentTool wrapper that presents an entire agent to its parent as a callable function. Once you see
that, the pattern loses its mystique: it's tools all the way down, where some tools happen to think.

## How the design actually works

Designing a multi-agent system means answering three questions: what are the roles, how do they
communicate, and what's the flow of control. The book gives you a vocabulary for each.

**Roles.** Each agent gets a role, a goal, and its capabilities. In CrewAI this is explicit and almost
theatrical — you define an agent with a role ("Senior Research Analyst"), a goal ("find and summarize the
latest trends"), and a backstory that shapes its voice. The theater has a purpose: a tightly scoped
identity keeps the model's behavior inside its lane.

**Interaction shapes.** The book catalogs the recurring collaboration forms, and they're worth having on
the tip of your tongue:

*Sequential handoff* — an assembly line: agent A finishes, its output becomes agent B's input. The CrewAI
blog-crew example is exactly this: a research task feeds a writing task through an explicit context
dependency.

*Parallel workstreams* — independent sub-tasks run simultaneously and a later step merges the results.
ADK's ParallelAgent runs a weather-fetcher and a news-fetcher at once, each writing to its own key in
shared state.

*Debate and consensus* — several agents with different perspectives argue toward a better answer than any
would give alone.

*Hierarchy* — a manager delegates to workers and synthesizes their results; each worker can own a coherent
group of tools rather than one agent juggling all of them.

*Critic–reviewer* — one set of agents produces (a plan, a draft, code), another set critiques against
correctness, policy, or quality, and the producer revises. The book flags this as especially effective for
code generation and research writing, and for cutting hallucinations — the critic's fresh context is
exactly what the producer, marinating in its own output, has lost.

**Topologies.** Zooming out from interactions to system shape, the book's spectrum runs: single agent (no
coordination at all — always your baseline); network (peers talking directly, decentralized — resilient,
since no one node's death kills the system, but communication overhead grows fast and keeping a large
unstructured web coherent is genuinely hard); supervisor (one coordinator routes work among subordinates —
clean control and one place to look when things go wrong, but a single point of failure and a bottleneck
when it's overwhelmed); supervisor-as-tool (the coordinator demoted to a resource the workers consult —
guidance without command); hierarchical (supervisors of supervisors, for problems that decompose in
layers); and custom (any hybrid the problem demands).

For interviews, the supervisor topology is your default recommendation for small systems: it's the easiest
to reason about, debug, and control. Reach for peer networks only when resilience or decentralization is a
stated requirement, and for hierarchy only at a scale most interview problems never reach.

**Handoffs and shared state.** The mechanics of "work flows between agents" deserve precision, because
this is where real systems fail.

A handoff is two things at once: a transfer of control (whose turn is it?) and a transfer of context (what
does the next agent need to know?). The second is the dangerous one. Hand over too little and the next
agent works blind; hand over everything and you've re-created the bloated context you were escaping.

The clean solution is a shared state store — a structured scratchpad all agents can read and write, rather
than agents forwarding their entire histories to each other. ADK models this directly: an agent declares
an output_key, its result lands in session.state under that key, and the next agent's instructions tell it
to read state["data"]. The state becomes the team's whiteboard, and each handoff is just "your inputs are
under these keys; write yours under that one."

That convention — agreed keys, agreed formats — is a small version of what the book calls a shared
ontology: a common vocabulary so agents mean the same thing by the same words. It sounds academic until
the researcher writes findings as free prose and the writer expected a structured list, and the pipeline
produces confident nonsense.

**Flow control.** Someone has to decide what runs when. Frameworks give you deterministic composers —
ADK's SequentialAgent (fixed order), ParallelAgent (concurrent), and LoopAgent (repeat until a
condition-checking agent escalates a stop signal, with a hard max-iterations cap) — plus the LLM-driven
option, where a coordinator agent reads the situation and delegates dynamically to its sub-agents. The
engineering wisdom: make flow control deterministic wherever you can, and spend the model's judgment only
where routing genuinely requires it.

**Where it breaks.** Multi-agent failure modes are organizational failures, which makes them fun to name:

*Cascading errors.* The researcher hallucinates one statistic; the writer builds a paragraph on it; the
editor polishes the paragraph's grammar. Each downstream agent adds confidence to the original mistake.
Defense: validation at handoff boundaries — schema checks on structured outputs, a critic stage for
content — so errors stop at the seam where they're cheapest to catch.

*Agents talking past each other.* No shared ontology: mismatched formats, mismatched assumptions, two
agents solving subtly different problems. Defense: contract-first design — define each handoff's format
before writing any prompts, and validate it mechanically.

*Delegation ping-pong.* Agent A decides this is B's job; B decides it's A's. Or a supervisor loops
delegating-and-rejecting forever. Defense: hard iteration caps (the LoopAgent's max_iterations exists for
exactly this) and an escalation path to a human when the cap hits.

*Cost and latency multiplication.* Every inter-agent message is a model call carrying context. A
five-agent pipeline can easily cost five to ten times the single-agent version and take proportionally
longer. This is the quiet reason "fewer agents" usually wins.

*Supervisor bottleneck.* In hub topologies, everything funnels through one coordinator — one overwhelmed
agent, or one bad routing prompt, degrades the whole system.

*Blurred accountability.* When the final output is wrong, which agent failed? Without per-agent traces —
logged inputs and outputs at every handoff — debugging a multi-agent system is archaeology.

**Why fewer agents is usually better — and when to split anyway.** Every agent boundary is a lossy, costly
handoff. The honest default is one agent with good tools, and you add agents only when you can point at a
concrete forcing function:

| Forcing function | Why it forces a split |
|---|---|
| Instructions have grown contradictory | One prompt can't be a rigorous critic and a fast producer at once |
| Tool list too large for reliable selection | Partition tools across agents, each with a coherent group |
| Different permissions or data access | Least privilege per agent — the writer never holds refund credentials |
| Genuine parallelism available | Independent sub-tasks can run concurrently |
| Adversarial roles needed | A critic sharing the producer's context inherits its blind spots |
| Different models per role | Cheap model for extraction, strong model for judgment |

If you can't name one of these, you don't need another agent — you need a better prompt.

**Neighboring patterns.** Versus one agent with tools: same building blocks; multi-agent adds separate
instruction sets, separate contexts, and inter-agent protocol — pay that complexity only for the forcing
functions above. Versus planning: planning produces the step list; multi-agent is one way of *staffing*
the steps — a plan can be executed entirely by its author. Versus chaining: a sequential multi-agent
pipeline *is* a chain whose stages are full agents rather than single prompts — the difference is autonomy
at each stage.

## The complete interview answer, spoken

The prompt: "Design a content-production system — a product brief goes in, and a researched, written,
fact-checked article comes out." Spoken, 15–20 minutes.

"Quick scoping questions. What volume — a handful of articles a day, not thousands? Assume yes. Does a
human sign off before publishing? I'll assume yes, and I'll design so the system makes that reviewer fast
rather than pretending to replace them. And accuracy bar? I'll assume high — these are public claims about
products, so a wrong statistic is a real incident, not a typo.

Let me start with the argument for the architecture, because 'use lots of agents' should never be the
opening move. Could one agent with a search tool do this? For a short social post, absolutely, and I'd say
stop there. But this task has three properties that push me to a team.

First, the sub-tasks want different personas that don't coexist in one prompt — an exhaustive researcher,
an engaging writer, and a suspicious fact-checker have contradictory instincts, and one instruction set
trying to be all three does each badly.

Second, I want adversarial separation: a fact-checker that shares the writer's context inherits the
writer's assumptions. Fresh context is the whole value of the check.

Third, the stages want different models and different tools — cheap-and-fast for research extraction,
strong for prose, and the fact-checker needs search access the writer shouldn't use mid-draft, because I
want every claim traceable to the research packet, not to a writer's impromptu search.

So: a small crew, sequential handoffs, one revision loop, everything coordinated by a plain-code pipeline
— not an LLM supervisor — because the flow here is known in advance. Deterministic order, LLM judgment
only inside the stages. Here's the whiteboard.

```
 Product brief
      |
      v
+-------------+   findings    +-----------+   draft
|  Researcher | ------------> |  Writer   | ----------+
| (search,    |  (structured  | (strong   |           |
|  cheap LLM) |   claims+src) |  model)   |           v
+-------------+               +-----------+     +-------------+
      ^                             ^           | Fact-checker|
      |                             |           | (fresh ctx, |
      |                       revise w/ notes   |  search)    |
      |                             |           +------+------+
      |                             +--- fail ---------+
      |                                                | pass
 gap request                                           v
 (missing evidence)                             +-------------+
                                                | Human review|
                                                +-------------+

        Shared state store (the team whiteboard):
        brief | findings | draft_v1..vN | check_report
```

Let me narrate the flow. The brief lands in a shared state store — think of it as the team's whiteboard: a
structured document with named slots that every stage reads from and writes to, instead of agents
forwarding their whole conversation histories around. That one decision keeps context small and handoffs
auditable.

Stage one, the researcher. Role-scoped agent, search tools, cheap model. Its output contract — and I use
the word contract deliberately — is not an essay; it's a structured findings packet: claim, source URL,
confidence, quote. The pipeline validates that structure mechanically before anything moves on. If the
researcher returns prose, the handoff fails loudly right there, not three stages later. That contract is
our shared ontology in miniature — every stage agrees on what a 'finding' is.

Stage two, the writer. It reads the brief and the findings packet — nothing else — and its instructions
are strict: every factual claim in the draft must come from the packet, cited by finding ID. No search
tool. That constraint looks harsh, but it's my main defense against the worst multi-agent failure mode:
cascading errors, where an invented fact gets polished into confident copy by every downstream stage. The
writer can't inject new facts because it has no way to get any.

If the writer finds the packet thin — a claim it needs but doesn't have — it doesn't improvise. It writes
a gap request into state, and the pipeline routes that back to the researcher for a targeted second pass.
That's a controlled backward edge, and it's capped: two gap rounds, then we proceed with what we have and
flag the thinness.

Stage three, the fact-checker, and this is the critic–reviewer pattern doing its job. Fresh agent, fresh
context — it sees the draft and the sources, not the writer's reasoning — and its own search access to
verify quotes and dates against the live web. Its instructions make it adversarial: assume the draft is
wrong; find out where. It emits a structured report: verified, contradicted, unverifiable, per claim.

Contradicted or unverifiable claims send the draft back to the writer with the checker's notes — that's
the revision loop. And because any loop between two LLM agents can ping-pong forever, the pipeline
enforces a hard cap: two revision cycles, then the article goes to the human queue with the disagreement
attached. An article that arrives saying 'these two claims are disputed, here's the evidence on each side'
still saves the human most of their time — that's a graceful degradation, not a failure.

Then the human. They see the draft plus the check report plus linked sources — the system's job was to
make their approval a five-minute skim instead of an hour of verification.

On failure handling beyond the loops: every handoff writes to the state store before control transfers, so
the pipeline checkpoints itself — if the fact-checker's search API dies, we retry that stage alone, not
the whole run. Per-stage timeouts and budgets, because a runaway researcher is the most expensive kind.
And every stage's input and output is logged against the run ID, which is what makes the system
debuggable: when an article is bad, I can point at the exact seam — bad findings, bad prose, or bad
checking — instead of shrugging at the ensemble.

Evaluation, two levels. Per-stage: the researcher gets scored on findings quality against briefs with
known-good source sets; the writer on citation discipline — does every claim trace to a finding, checkable
automatically; the fact-checker is the fun one — I seed drafts with known planted errors and measure catch
rate. That per-stage decomposition is the hidden gift of multi-agent design: each seam is a place to
measure. End-to-end: human reviewers already rate every article as part of approval, so I harvest that —
approval rate, edit distance between submitted and published, revision cycles per article — as my
system-level health metrics, all trending on a dashboard.

Cost: this pipeline is maybe four to eight model calls per article versus one — but the calls are
right-sized. Research and checking on the cheap model, only the writing on the premium one. At editorial
volumes — dozens a day, latency in minutes — cost is dominated by quality anyway: one published wrong
claim costs more than a month of inference.

And the tradeoff I'd close on: I chose plain-code orchestration over an LLM supervisor deliberately. The
flow is known, so a supervisor agent would add a routing failure mode, a bottleneck, and cost, for zero
benefit — the book's supervisor topology earns its keep when routing is genuinely dynamic, which this
isn't. If tomorrow the system needs to handle wildly different content types with different flows, that's
when I'd promote the pipeline to a supervisor agent — and I'd know exactly what I was paying for."

## Follow-ups they will ask

**"Why not one strong agent with search, write, and check as tools?"** For simple content, do that — it's
my baseline and I'd say so. The team earns its cost through three things one agent can't give me:
adversarial fresh context for checking, contradictory personas separated into stages, and permission
boundaries like the writer having no search. If none of those mattered — low stakes, short content — the
single agent wins on cost, latency, and simplicity.

**"How do agents actually talk to each other — do they chat?"** In my design they never converse in free
text; they read and write structured entries in shared state, and plain code moves control. Free-form
agent chatter is where ontology mismatches and ping-pong live. I reserve unstructured exchange for the one
place it pays — the critic's notes to the writer — and even that travels inside a structured report.

**"What happens when the fact-checker and writer disagree forever?"** They don't get the chance: a hard
cap of two revision cycles, enforced by the pipeline, then escalation to the human with both positions
attached. Deadlock between agents is a certainty at scale, so the design question isn't preventing
disagreement — it's making the tie-breaker (a human, or a policy rule) explicit and cheap.

**"How does this scale to fifty agents?"** Mostly: don't. Scale stages horizontally — many parallel
instances of this same small pipeline — rather than deepening one pipeline to fifty roles, because errors
and costs compound per handoff. If the org genuinely needs many specialist teams, that's when hierarchy
appears: a coordinator routes work to team-level pipelines, each internally simple — supervisors of
supervisors, exactly the layered topology the book describes, adopted at the last responsible moment.

**"How do you attribute a bad output to the right agent?"** Handoff logging is the answer: every stage's
inputs and outputs are recorded against the run, so I replay the run and find the first seam where good
input produced bad output. This is also why structured handoffs beat free text — diffing a structured
findings packet against reality is tractable; diffing two agents' chat transcript is not.

**"Could two copies of the same model really catch each other's errors?"** Yes, and it's less mysterious
than it sounds: the value isn't a different brain, it's different context and different incentives. The
writer's context is full of its own draft and the pressure to be fluent; the checker's context contains
the draft as a hostile document and instructions to attack it. Same weights, different role, materially
different behavior — that's the critic–reviewer pattern's whole trick.

## Say it in one breath

Multi-agent collaboration is task decomposition made organizational: each sub-problem gets an agent with
narrow instructions, its own tools, and its own context, wired together through structured handoffs and a
shared state store. Default to one agent — every extra agent multiplies cost, latency, and failure seams —
and split only for a concrete forcing function: contradictory personas, tool overload, permission
boundaries, parallelism, or an adversarial critic that needs fresh context. Keep flow control in plain
code when the flow is known, cap every loop, and log every handoff, because when the ensemble fails you
need to find the seam.
