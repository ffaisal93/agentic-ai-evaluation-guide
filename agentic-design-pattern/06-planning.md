# Pattern 6: Planning — deciding the steps before (and while) taking them

## The interview scenario

Planning questions usually sound like one of these:

- "Design a deep-research agent: the user asks a broad question and gets back a structured, cited report
  an hour later."
- "Design an agent that automates employee onboarding — accounts, training assignments, equipment,
  coordination across three departments."
- "Our agent handles simple requests fine but falls apart on anything multi-step. It does the first thing
  it thinks of and quits. How would you fix that?"

The tell is a goal that cannot be satisfied by any single action — something with stages, dependencies,
and an outcome that has to be assembled rather than fetched.

## What this pattern is, in plain words

Planning is the ability to look at a big goal and work out a sequence of steps that gets you from here to
there — before, or while, actually doing them.

The analogy the book leans on, and the one I'd use in an interview, is delegating to a capable specialist.
When you tell an event planner "organize a team offsite," you're specifying the *what* — the goal and its
constraints: budget, headcount, rough dates. You are absolutely not specifying the *how*. The planner's
whole job is to discover the how: understand the starting conditions, understand what "done" looks like,
and chart the sequence of actions connecting them.

Crucially, the plan doesn't exist before the request arrives. It's synthesized in response to it. That's
what separates a planning agent from a workflow — a workflow is a route someone already mapped; a plan is
a route being drawn for the first time.

And a real plan is a living thing. If the preferred venue is booked, a good planner doesn't declare
failure — they absorb the new constraint, re-evaluate, and propose an alternative. That adaptability is
the hallmark of the pattern: the initial plan is a starting hypothesis, not a rigid script.

For a language model, planning means taking a high-level objective and generating an explicit, ordered
list of sub-goals — "first gather sources, then extract claims, then reconcile disagreements, then draft,
then cite" — and then executing against that list, revising it when reality pushes back.

The problem it solves is exactly the one in the third interview prompt above: a reactive agent, given a
big goal, does one plausible-looking thing and stops, because nothing forced it to think about the whole
arc. Planning is the forcing function.

## How the design actually works

There are two ways to run the pattern, and interviewers expect you to know both and to pick one
deliberately.

**Decompose-then-execute.** The agent's first act is to produce the complete plan as an artifact — a
numbered list of steps, written down before any step runs. Then an executor works through the steps in
order, feeding each step's output into the next.

This is what the CrewAI example in the source chapter does in miniature: a single agent is instructed to
first write a bulleted plan for a summary, then write the summary following its own plan. The plan
literally appears in the output before the prose does.

The huge advantage of this mode is that *the plan is a checkable artifact*. Because it exists as text
before execution, you can inspect it, lint it with rules ("does any step call a tool we don't have?"),
estimate its cost, and — most valuably — show it to a human for approval. Google's Gemini Deep Research
does exactly this: it deconstructs your prompt into a multi-point research plan and presents it to you for
review and editing *before* running it, so you and the agent agree on the trajectory before any budget is
spent.

A plan artifact for a research task might look like this — deliberately boring, deliberately inspectable:

```
GOAL: Assess the economic impact of semaglutide
      on global healthcare systems.

PLAN:
 1. [pending] Identify major healthcare markets and
              current spending baselines.        -> web_search
 2. [pending] Gather cost/outcome studies on
              semaglutide adoption.              -> web_search
 3. [pending] Extract and reconcile claims;
              flag contradictions.               -> extract_claims
 4. [pending] Project system-level impact;
              note uncertainty.                  -> synthesize
 5. [pending] Draft cited report per outline.    -> synthesize

BUDGET: max 40 searches, 3 replans, 30 min
```

Notice what's checkable at a glance: every step names a capability that exists, step 3 consumes what steps
1–2 produce, the length is sane, and there's a budget line. None of that is verifiable when the "plan"
lives only in the model's head.

**Plan-as-you-go.** The agent decides the next step, executes it, looks at the result, and only then
decides the following step. The plan never fully exists; it's discovered incrementally.

This mode shines when the environment is unknowable up front. Deep-research systems run their search phase
this way: each round of results reveals knowledge gaps, contradictions to resolve, and leads to chase, so
the next queries are formulated from what just came back — you couldn't have listed them in advance.

The mature answer is usually a hybrid: a coarse upfront plan for structure and checkability, with adaptive
execution inside each step. That's precisely how the deep-research products are built — an approved
outline on the outside, an iterative search-evaluate-refine loop on the inside.

| | Decompose-then-execute | Plan-as-you-go |
|---|---|---|
| Plan exists as | Full artifact before execution | One step at a time |
| Best when | Steps are foreseeable | Each step's result shapes the next |
| Checkable / approvable | Yes — review before spending | Only step-by-step |
| Main risk | Plan goes stale mid-flight | Wandering, no global view, cost creep |

**The state being passed around.** Three things flow through a planning system. First, the plan itself —
the step list, with per-step status: pending, running, done, failed. Second, the accumulated results of
completed steps. Third, the original goal plus constraints, which must stay visible the whole time so
replanning has something to aim at.

Lose any of the three and the system degrades in a characteristic way. Lose the goal and replanning drifts
toward whatever the recent context suggests. Lose the results and steps get repeated, doubling cost. Lose
the plan status and you can't resume after a crash — every failure becomes a full restart.

**Replanning when a step fails.** This is the paragraph interviewers wait for. A step will fail — an API
dies, a search comes back empty, the caterer is booked. The naive designs either abort the whole run or
blindly barrel into the next step with a hole in the middle.

The right design treats failure as new information. The executor reports the failure into context, and the
planner is re-invoked with four things: the goal, the plan so far, the completed results, and the failure.
It emits a revised plan — maybe substituting a step, maybe reordering, maybe concluding the goal is
unreachable and saying so with reasons, which is itself a successful outcome, not a crash.

You bound this with a replan budget — a counter, say three replans per run — because the ugliest failure
mode here is the infinite replan loop, where the agent keeps rearranging steps around an obstacle it can
never pass.

**Where it breaks.** Name these plainly:

*Bad decomposition.* The plan misses a necessary step, orders steps so a later one needs data an earlier
one never produced, or includes steps no available tool can perform. Defense: validate the plan as an
artifact before executing — check tool references, check data dependencies — and keep a human review gate
for expensive runs.

*Stale plans.* In decompose-then-execute, the world can change between planning and step six. Defense:
cheap precondition checks before each step, escalating to a replan when one fails.

*Error cascades.* Step three quietly returns garbage, and steps four through eight faithfully build on it.
Defense: lightweight verification between steps — even a one-line "does this output look like what step
four needs?" check — so bad output stops at the boundary instead of propagating.

*Hallucinated completion.* The model marks a step done without the evidence existing — claims it gathered
sources it never fetched. Defense: step completion is judged by the orchestrator from actual tool outputs,
never by the model's say-so.

*Over-planning.* Twenty-step plans for three-step problems: slower, costlier, more failure surface, no
better output. Defense: cap plan length and push back in the planner prompt toward the fewest steps that
work.

*Cost blowups.* Open-ended loops — especially research loops — can run indefinitely. Defense: budgets on
every axis: steps, tool calls, tokens, wall-clock time.

**When to use it, and when not.** The book's rule of thumb is a single question, and it's a great
interview line: *does the "how" need to be discovered, or is it already known?* If every request follows
the same known route — password resets, standard document processing — a fixed workflow beats a planner on
every metric that matters: predictability, cost, debuggability. You deliberately constrain the agent's
autonomy to buy reliability. Reach for planning only when the route genuinely varies per request and
foresight across multiple interdependent steps is required.

**Neighboring patterns.** Versus chaining: a chain is a sequence the *developer* wrote at design time; a
plan is a sequence the *model* writes at run time — chaining is the known-how case, planning the
discovered-how case. Versus tool use: planning decides *which* tool calls and in *what order*; tool use is
the mechanics of any single call. Versus multi-agent: a plan's steps can all be executed by one agent;
hand different steps to different specialists and you've crossed into the next pattern.

## The complete interview answer, spoken

The prompt: "Design a deep-research agent — a user asks a broad question and gets a structured, cited
report." Here's the 15–20 minute version, spoken.

"Let me scope it first. How fresh does the information need to be — is this web research, internal
documents, or both? I'll design for web-first with optional user-provided documents, since that's the
common product shape. Is the user willing to wait? I'll assume yes — minutes to an hour, this is an
offline job, not chat. And is there a cost ceiling per report? I'll assume we want a knob for that, say a
few dollars of model and search spend per run.

The defining property of this problem is that no single action solves it. 'Research the economic impact of
drug X on healthcare systems' decomposes into finding sources, extracting claims, noticing gaps,
reconciling contradictions, and synthesizing — with dependencies between those. So the backbone of my
design is the Planning pattern, and I'll use a hybrid: an explicit upfront plan for the skeleton, adaptive
execution inside the research phase.

Here's the architecture I'd draw.

```
 User query + optional docs
        |
        v
+---------------+     plan (text artifact)
|  Planner LLM  | ------------------------+
+---------------+                         v
        ^                        +-----------------+
        | approve / edit  <----- |  User review    |
        |                        +-----------------+
        v
+-------------------------------------------------+
|  Orchestrator (owns plan state + budgets)       |
|                                                 |
|   step: search --> read --> assess gaps --+     |
|            ^                              |     |
|            +----- refine queries <--------+     |
|                (loop until covered              |
|                 or budget hit)                  |
+-------------------------------------------------+
        |                         |
        v                         v
+---------------+        +----------------+
|  Search tool  |        |  Findings store|
+---------------+        |  (claims + src)|
                         +----------------+
                                  |
                                  v
                         +----------------+
                         | Synthesis LLM  |
                         | -> cited report|
                         +----------------+
```

Phase one, planning. The user's question goes to a planner — a model call whose only job is to emit a
research plan: the sub-questions to answer, roughly in order, with the angle each one covers. This plan is
a text artifact, and I'd surface it to the user for approval and editing before execution, which is
exactly what Google's Deep Research product does. That gate earns its keep three ways: the user catches
misunderstandings before we spend money, editing the plan is the cheapest possible steering mechanism, and
the approved plan becomes our contract for what 'done' means.

Even without a human in the loop, I'd still generate the plan as an artifact, because I can check it
mechanically — every step maps to a capability we have, no step consumes data no earlier step produces,
length is under my cap. A plan that fails lint gets regenerated with the lint errors in the prompt, which
usually fixes it in one round.

Phase two, execution — and this is where I switch modes. The outer plan is fixed, but inside the research
step I run plan-as-you-go, because search is fundamentally iterative: I can't know query number four until
I've read the results of query number two.

Concretely, the orchestrator — a plain program, not a model — owns the loop. For each sub-question:
formulate queries, run the search tool, pull the promising pages, and have a model extract claims with
their sources into a findings store — just a structured scratchpad accumulating claim, source URL, and
confidence.

Then a gap-assessment call: given the sub-question and the findings so far, what's missing, what's
contradicted, what needs corroboration? Its output drives the next round of queries. This is the
dynamic-refinement behavior the real deep-research systems describe — chasing gaps, corroborating data
points, resolving discrepancies — rather than firing a fixed list of searches.

The loop exits on either of two conditions: the gap assessor says coverage is sufficient, or the budget
for this sub-question — searches, tokens, minutes — runs out. Budget exhaustion isn't failure; the report
will note thinner sourcing for that section. Every open-ended loop in this system has a budget, because
the worst failure mode of research agents is the infinite rabbit hole, and the second worst is a surprise
five-hundred-dollar run.

Phase three, synthesis. With all sub-questions covered, a synthesis model gets the approved plan as the
outline and the findings store as the only permitted source material. Its instruction is strict: every
claim in the report must trace to a finding, and every finding carries its source, so citations fall out
naturally. Synthesizing from the curated store rather than from raw pages is my main hallucination defense
— the model's job narrows from 'know things' to 'organize these things.'

Now failure handling, because a run this long *will* hit failures. Search API down: retry with backoff —
meaning increasing pauses between attempts so we don't hammer a struggling service — then continue with
other sub-questions and circle back. A sub-question that comes up genuinely dry: that's a replanning
trigger. The orchestrator re-invokes the planner with the plan, the results so far, and the failure, and
the planner revises — splits the step, reframes it, or drops it with a note. I cap replans at three per
run; past that, finish what's finishable and flag the rest. And the whole run checkpoints its state — plan
status plus findings store — after every step, so a crash at minute forty resumes instead of restarting.
Since the job is minutes-to-hours, it runs asynchronously and notifies the user on completion, which also
means one flaky step never takes down the whole investigation.

A word on the user's own documents, since I scoped those in: they enter the findings store through the
same extraction path as web pages, just tagged with their origin. That gives us the blend the real
products offer — private sources and public research in one report — without a separate pipeline, and the
tagging means citations still say exactly where each claim came from.

I'd also log every intermediate step — the plan, each query, each extraction, each replan — the way the
OpenAI Deep Research API exposes its reasoning steps and executed searches. That transparency is how you
debug a bad report: was it a bad plan, bad retrieval, or bad synthesis? Without the trace you're guessing.

For live monitoring, I'd watch four numbers per run and in aggregate: replans per run (rising means plans
are getting worse or the world is getting harder), budget-exhaustion rate per sub-question (rising means
budgets are mis-set or retrieval is degrading), average searches per finding (efficiency of the loop), and
citation-check pass rate on the sampled audits. Each of those points at a different component when it
moves, which is the whole point of a metric.

Evaluation is honestly the hard part, and I'd say so out loud. Three layers. Citation faithfulness is
checkable automatically: sample claims from the report and verify the cited source actually supports them
— a model can grade this, humans audit the grader. Coverage: did the report address every step of the
approved plan — mechanically checkable against the artifact. Overall quality needs humans: a rubric —
accuracy, organization, source quality — scored on a sampled set of reports, tracked over time so I notice
regressions when we change prompts or models.

Cost per report is dominated by the research loop — dozens of model calls plus search fees. The knobs:
sub-question count, search rounds per sub-question, and which models run where. Extraction is high-volume
and simple, so a small cheap model; planning and synthesis are low-volume and judgment-heavy, so the big
model. I'd expose a quick-versus-thorough setting to the user, which just scales those budgets.

The tradeoff to volunteer: this design front-loads structure — plan artifact, approval gate, budgets — at
the price of some autonomy and speed. For a research product, I'll take that trade every time: the plan
gate is what keeps a thirty-minute, multi-dollar run pointed at what the user actually asked."

## Follow-ups they will ask

**"Why generate a full plan upfront if you're going to deviate anyway?"** Because the artifact pays for
itself even when it changes: it's the thing I can lint, cost-estimate, and get approved before spending,
it defines "done," and deviations from it are logged, reviewable events rather than silent drift. Cheap
insurance, high leverage.

**"What if the model's plan is just bad?"** Layers: a planner prompt with good examples of plan shape,
mechanical lint (unknown tools, broken dependencies, over-length), regeneration with lint feedback, and
the human gate for expensive runs. Plus an eval set of goal → known-reasonable-plan pairs so plan quality
is a measured number, not vibes.

**"How is this different from just chaining prompts together?"** A chain is a fixed sequence I wrote at
design time — the how is known, and honestly, when the how is known a chain is the *better* tool: cheaper,
predictable, debuggable. Planning earns its complexity only when the sequence must be discovered per
request. The book's one-line test: does the how need to be discovered? No — chain it. Yes — plan it.

**"When a mid-plan step fails, restart or patch?"** Patch, almost always: keep completed results,
re-invoke the planner with goal, plan state, and the failure, and get a revised remainder. Restarting
throws away paid-for work and re-rolls the dice on steps that already succeeded. But cap replans, and make
"this goal is unreachable, here's why" a legitimate planner output — an agent that can conclude
impossibility is more trustworthy than one that thrashes.

**"How do you keep an autonomous research loop from running forever or costing a fortune?"** Budgets on
every axis — steps, tool calls, tokens, wall-clock — enforced by the orchestrator, not requested of the
model. And diminishing-returns detection: when a search round adds almost nothing new to the findings
store, that sub-question is done regardless of remaining budget.

**"Could you do all this with one giant prompt instead — 'research X and write a cited report'?"** For a
narrow question with a strong model, sometimes, and it's a fair baseline. But it fails exactly where
planning shines: no intermediate artifacts to check, no place to resume after a crash, no per-phase
budgets, citations you can't trace to a retrieval step, and one context window holding an hour's worth of
material. Decomposition is what makes the job inspectable, resumable, and billable.

## Say it in one breath

Planning is the agent writing its own route: decompose a big goal into ordered steps, execute them, and
revise the route when a step fails or the world changes. Generate the plan as a text artifact whenever you
can, because an artifact can be linted, cost-estimated, approved by a human, and used as the definition of
done. And apply the one-line test before reaching for it: if the how is already known, use a fixed
workflow — planning is only for when the how must be discovered.
