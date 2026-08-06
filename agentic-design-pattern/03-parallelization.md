# Pattern 3: Parallelization — stop waiting in line when the tasks don't need each other

## The interview scenario

Parallelization hides inside questions like these:

"Design a due-diligence agent: given a company name, it should pull recent news, financials, leadership info, and competitor landscape, and produce one briefing."

"Build a travel-planning assistant that, for a given trip, checks flights, hotels, local events, and restaurant options, and assembles an itinerary. Users are waiting live — it has to feel fast."

"We receive product feedback at scale. Design a system that runs sentiment analysis, topic extraction, and urgent-issue detection on each piece, and how would you make it fast enough?"

The tell is a task that fans out into several *independent* lookups or analyses — pieces that don't need each other's answers — followed by an assembly step.
The moment a design has you doing A, then B, then C, and you notice B never looks at A's output, the interviewer is waiting for you to say: those can run at the same time.

The skill under test is dependency analysis — can you look at a workflow and see which arrows are real — plus operational judgment about concurrency's sharp edges.
A candidate who parallelizes the independent parts earns the speed points; the candidate who *also* volunteers the straggler problem, the partial-results policy, and the rate-limit governor earns the hire, because those three are the difference between having read about concurrency and having been paged by it.
It's also quietly a judgment test in reverse: parallelizing things that are dependent, or reaching for concurrency when the sequential version was already fast enough, loses more points than never mentioning parallelism at all.

## What this pattern is, in plain words

Parallelization means running multiple components — LLM calls, tool calls, even whole sub-agents — at the same time instead of one after another, whenever they don't depend on each other's outputs, then gathering the results and combining them.
One sentence: find the steps that don't need to wait for each other, fire them all simultaneously, and only go sequential again at the step that combines them.

The everyday analogy is cooking Thanksgiving dinner.
A rookie cooks the turkey, *then* starts the potatoes, *then* the green beans, and dinner is at midnight.
An experienced cook has the turkey in the oven, potatoes boiling, and beans steaming all at once — because none of those dishes needs another dish to be finished first — and only the final plating waits for everything.
Same total work; a fraction of the wall-clock time.

The problem it solves is that sequential execution makes total time the *sum* of every step, and this hurts most where agentic systems spend most of their lives: waiting on the outside world.
The book underlines this — the big wins come when steps involve external calls with latency, like APIs, searches, and database queries, because during a three-second API wait your system is doing *nothing*; it may as well have five other requests in flight.
Two bits of vocabulary to drop naturally: the moment where one step splits into many concurrent ones is the **fan-out**, and the moment where you collect all their results back together is the **fan-in** — the gather step.
And one precision point worth having ready, straight from the book's LangChain example: in Python this is usually *concurrency* rather than true parallelism — one worker juggling many waiting tasks, switching to another whenever one is idle on the network — which is exactly what you want for I/O-heavy agent work, since the bottleneck is waiting, not computing.

The breadth here is worth a quick tour too, because parallelization is more versatile than "make research faster."
The book's catalog: multi-source information gathering — news, stock data, social mentions, database queries about one company, all at once; multi-analysis processing — sentiment, keywords, categories, and urgency extracted from the same feedback simultaneously; multi-tool assembly — the travel agent hitting flights, hotels, events, and restaurants concurrently; multi-part content generation — subject line, body, image selection, and call-to-action drafted in parallel and assembled; concurrent validation — email format, phone number, address, and profanity checks running side by side for instant feedback; multimodal splits — the text and the image of a social post analyzed simultaneously by different branches; and best-of-N generation — three headline candidates from three slightly different prompts, with a judge picking the winner.
Notice that last pair: parallelization isn't only a speed tool — splitting by *modality* is a structure tool, and racing candidates is a *quality* tool, and mentioning either unprompted signals real fluency.

## How the design actually works

The shape has four parts, and it's worth drawing them in this order: a **fan-out point** where the orchestrator launches N independent branches simultaneously; the **branches** themselves, each a self-contained unit — a prompt, a chain, a tool call, or a sub-agent — that neither reads nor writes another branch's data; a **gather point** (the fan-in) that waits for the branches and collects their outputs; and an **aggregator**, typically one final LLM call that synthesizes the collected pieces into the deliverable.
Notice the rhythm: parallel in the middle, sequential at the ends.
The book's research-agent example has exactly this shape — searches and per-source summaries run concurrently, but collation, synthesis, and final review are inherently one-after-another — and most real systems are this hybrid: chains where one link has been widened into a parallel block.

State deserves a careful sentence here, because it's where parallel designs quietly rot.
Each branch receives a *copy* of what it needs from the shared state at fan-out — in the ADK example from the book, each researcher sub-agent writes its result to its own dedicated key in the session state, like labeled cubbyholes, and the merger agent reads all the cubbyholes afterward.
What branches must *not* do is write to the same piece of state while running, because two concurrent writers produce a mess whose polite name is a **race condition** — an outcome that depends on which branch happened to finish first, which makes bugs that appear and vanish randomly.
The discipline is: read-only shared input, each branch owns its output slot, and only the gather step assembles.

The non-negotiable precondition — say this explicitly in every interview — is **independence**.
The pattern's rule of thumb, per the book, is to use it for multiple independent operations: several API fetches, different chunks of data, multiple content pieces for later synthesis.
If step B genuinely needs step A's output, they cannot run together, full stop; a dependency is a wall.
So the design skill is dependency analysis: sketch the steps, draw an arrow for every "needs the output of," and everything not connected by arrows is fair game to parallelize.

Where it breaks — four failure modes, with names.
**The straggler problem**: your fan-in waits for *all* branches, so the parallel block is only as fast as its slowest member — you traded "sum of all steps" for "the worst step," which is a huge improvement that can still be ruined by one slow API.
Mitigations: per-branch timeouts, and a policy decision made in advance — is a partial result acceptable?
For a research briefing, absolutely: four of five sources with a note about the missing one beats an error page.
For something like a payment-verification fan-out, no — all checks must pass.
**Partial failure**: one branch errors while four succeed.
Same policy question, plus mechanics: retry the failed branch alone — this is where per-branch idempotency pays off, since redoing one branch must not redo its side effects — and degrade gracefully if it stays dead.
**Rate-limit collisions**: fan out fifty model calls at once and your provider's rate limit — the per-minute cap on requests — slams the door, failing calls that would have succeeded politely spaced out.
The cure is a concurrency cap: a governor that keeps at most, say, eight calls in flight, with the rest queued.
This is also the honest answer to "why not parallelize *everything*": beyond the caps, the book flatly warns that concurrent architectures cost real complexity in design, debugging, and logging — so you buy speed only where users actually feel it.
**Debugging fog**: five interleaved branches produce five interleaved log streams, and reconstructing what happened requires discipline you must design in — a shared request ID plus a branch label on every log line, so traces can be untangled per branch.

On a card:

| Failure mode | What it looks like | The defense |
|---|---|---|
| Straggler | One slow branch holds the whole gather hostage | Per-branch timeouts; decide the partial-results policy in advance |
| Partial failure | Four branches succeed, one errors | Retry the failed branch alone; degrade to a labeled gap or fail per policy |
| Rate-limit collision | Big fan-out slams the provider's per-minute cap | Concurrency cap with a queue; backoff on throttle errors |
| Debugging fog | Interleaved logs from concurrent branches | Request ID + branch label on every line; per-branch traces |

One more shape worth naming, because interviews love it: the same fan-out idea applied to *many items* instead of many aspects.
Everything above fanned out different tasks about one company; the batch variant fans out the *same* task over a thousand items — summarize each of last night's support tickets, analyze each feedback entry.
Old-school data engineers will recognize this as the map step of map-reduce, and the mechanics are identical: independent items, concurrent workers, a gather at the end — plus one new concern, which is that at a thousand items the concurrency cap and the queue stop being nice-to-haves and become the design.
If an interviewer says "and now do this for our whole backlog," they're asking you to make exactly this jump, and the answer is: same pattern, plus a governor, plus progress tracking so a crash at item 700 resumes at 701 instead of at zero.

When to use it: multiple independent lookups, batch processing of many items with the same treatment, multi-tool assembly jobs, validation checks that can run side by side, or generating several candidate outputs to pick the best from — that last one, several tries at the *same* task in parallel and choose the winner, is a quality technique, not just a speed technique, and mentioning it earns points.
When not: when steps are dependent (impossible), when the sequential version is already fast enough (complexity without payoff), or when a shared bottleneck like one rate-limited API means parallel requests just queue up anyway.
Versus neighbors: chaining is steps in a row because they depend on each other; parallelization is steps side by side because they don't; routing picks *one* path among several, parallelization takes *all* of them; and reflection spends extra time to gain quality, while parallelization spends nothing extra to reclaim time — which is why they stack so well: a parallel fan-out feeding a synthesis, followed by a reflection pass, is a very common trio.

## The complete interview answer, spoken

Here's the full spoken answer for: *"Design a due-diligence agent: company name in, briefing out — news, financials, leadership, competitors."*

"Questions first.
Who's the user and how long will they wait?
I'll assume an analyst at a firm, kicked off from a dashboard, and that under a minute feels great while five minutes feels broken — so latency matters, but it's not a chat where seconds count.
Depth versus freshness: I'll assume this is a current-snapshot briefing built from live sources — news APIs, a financial-data API, web search — not a deep archival crawl.
Volume: dozens of briefings a day, not thousands, so my cost pressure is moderate and my quality bar is high, since analysts act on this.
And accuracy stakes: getting a revenue figure wrong in a due-diligence doc is genuinely bad, so I'll want the numbers to come from the data API, not from model memory, and I'll want sources cited.

The simplest thing: one LLM call — 'tell me about Acme Corp.'
Fails immediately on two counts: the model's knowledge is stale and it will confidently fill gaps with plausible fiction, which in due diligence is disqualifying.
Next-simplest: a sequential chain — fetch news, then financials, then leadership, then competitors, then synthesize.
That version is *correct*, and it's how I'd think about the logic — but look at the dependency structure: the news fetch doesn't need the financials; the leadership lookup doesn't read the competitor scan.
Four independent gathering tasks, each dominated by waiting on external APIs, each taking maybe five to ten seconds — run in a row that's up to forty seconds of pure queueing before synthesis even starts.
They're independent, so this is a parallelization problem: fan out the gathering, fan in for synthesis.

Here's the whiteboard:

```
    company name
        |
        v
   +---------+          FAN-OUT (all four at once)
   | Orchestr|---> [News agent]------- news items -----.
   |  -ator  |---> [Financials agent]-- key figures ----+--> GATHER --> [Synthesis] --> briefing
   |         |---> [Leadership agent]-- execs/changes --+   (wait w/     (one strong    (with
   |         |---> [Competitor agent]-- landscape -----'    timeout)      LLM call)     sources)
   +---------+
     each branch: own tools, own output slot, no shared writes
```

Walking it through: the request hits the orchestrator, which immediately launches all four branches concurrently.
Each branch is a small self-contained chain: the news branch queries a news API and has a small model summarize the hits with dates and sources; the financials branch calls the financial-data API and normalizes key figures — revenue, margins, headcount if we have it — as structured JSON, deliberately *not* asking the model to recall numbers, only to arrange fetched ones; leadership pulls executive data and recent changes; competitors runs a couple of searches and produces a labeled landscape summary.
Each branch writes to its own slot in the request's state — its own cubbyhole — and no branch reads another's, which is what keeps concurrency safe: shared read-only input, exclusive output slots, so there's no possibility of two writers colliding.

The gather step waits on all four with a per-branch timeout of, say, fifteen seconds.
And here's a policy I'd state explicitly rather than leave implicit: partial results are acceptable and labeled.
If the news API is having a bad day, the analyst gets a briefing with three sections and a visible note — 'news retrieval failed; rerun or check manually' — because for this product an honest partial beats both an error and a silently incomplete document.
The one refinement: if the *financials* branch fails I'd flag it loudly at the top of the briefing, since that's the section analysts trust most.

Then the sequential tail: one synthesis call on my strongest model, taking the four structured outputs and composing the briefing — and I'd borrow a discipline straight from how the ADK merger agent is prompted in the literature: the synthesis prompt says, in effect, *use only the material provided in these inputs; add nothing from your own knowledge*.
That grounding instruction is what keeps the final document anchored to what we actually fetched, with each claim attributable to a branch, which becomes my citation trail.
End-to-end: the parallel block costs roughly the slowest branch — call it ten seconds — plus a few seconds of synthesis.
Fifteen-ish seconds instead of forty-five: same work, a third of the wait, and that's the whole argument for the pattern.

Failure modes, preemptively.
Stragglers: my parallel block is only as fast as its slowest branch, hence the per-branch timeouts and the partial-results policy — I'd also watch per-branch p95 latency so a chronically slow source gets fixed or replaced rather than silently dragging every briefing.
Partial failure: a failed branch retries once on its own — safe because branches are read-only against the world, so a retry can't double any side effect — then degrades to the labeled-gap behavior.
Rate limits: four branches is gentle, but the same design at batch scale — say, screening two hundred companies overnight — would fan out eight hundred calls and get us throttled; so the orchestrator has a concurrency cap, keeping maybe ten calls in flight globally, everything else queued.
The nightly batch shares that governor with the live traffic, and live requests get priority in the queue.
Debugging: concurrent logs interleave into soup, so every log line carries the request ID plus its branch name, and my tracing view groups by branch — the book is blunt that parallel architectures tax design, debugging, and logging, and I'd budget for that tax rather than discover it.

Evaluation and monitoring.
Correctness first: for a golden set of companies, I'd check the financial figures in the output against the API's ground truth — that should be exact, since the model only formats fetched numbers, and any mismatch is a bug, not a judgment call.
For the prose sections, an LLM-as-judge — a separate model call grading outputs against a rubric — scores groundedness: is every claim in the briefing traceable to a branch's fetched material?
That directly measures whether my 'use only the provided inputs' instruction is holding.
A human analyst reviews a weekly sample for usefulness, which no automated metric captures.
Operationally: per-branch success rate, per-branch and end-to-end p95 latency, partial-briefing rate — if 20% of briefings are shipping with gaps, a source integration is rotting — and cost per briefing.
My SLO: 95% of briefings complete, in full, in under thirty seconds.

Cost: per briefing, roughly four small-model branch calls plus API fees plus one strong-model synthesis — the synthesis dominates; order of a few cents, maybe ten with generous retrieval.
For dozens a day, single-digit dollars daily — irrelevant next to analyst time.
Note that parallelization didn't change the cost at all — same calls, rearranged in time; it bought latency, not savings.
Under a one-week deadline: ship two branches — news and financials, the core value — sequentially first, since at two branches the parallel machinery isn't yet worth its complexity; add branches three and four, and *then* introduce the fan-out when the sequential latency actually hurts.
One economy note before I close: briefings repeat.
If three analysts pull Acme Corp this week, the second and third requests should hit a cache — I'd cache per-branch results with freshness windows matched to how fast each source moves: financial figures until the API's next update, news for an hour or two, leadership basically until it changes.
A cache hit skips the branch entirely, which improves latency *and* cost — the two things parallelization alone couldn't do together — and a 'refresh now' button covers the analyst who needs this minute's truth.

Parallelism is an optimization; I earn it after correctness."

## Follow-ups they will ask

**"What exactly makes two steps safe to run in parallel?"**
"Two conditions.
No data dependency: neither step consumes the other's output — if B reads what A produces, there's a wall between them and they're a chain, not a fan-out.
And no write conflict: they don't mutate the same state or the same external resource while running, or you get race conditions — results that depend on finish order, which are the worst bugs to chase because they don't reproduce.
My discipline: branches share read-only input, each owns an exclusive output slot, and only the gather step combines."

**"One of your five branches fails. Now what?"**
"Policy first, mechanics second.
The policy — decided at design time, per product — is whether partial results are acceptable: for a research briefing yes, labeled; for a compliance check, no, all branches are mandatory.
Mechanics: the failed branch retries alone with backoff — cheap and safe since branches are read-only — and if it stays dead we either ship the labeled partial or fail the request per the policy.
The anti-pattern is re-running the whole fan-out because one branch hiccuped."

**"You fan out 100 calls and the model provider throttles you. Fix it."**
"Concurrency cap plus a queue: a governor allows at most N calls in flight — N tuned to sit under the provider's rate limit with headroom — and the other work waits its turn.
Add backoff on 'too many requests' errors so retries don't pile on, and if there are multiple traffic classes, priority in the queue — live users ahead of batch jobs.
The insight to say out loud: beyond the cap, more concurrency adds zero speed, because the provider has become the bottleneck; you're just converting polite queueing into errors."

**"Does parallelization save money?"**
"No — and saying so crisply is worth points.
It's the same calls rearranged in time: latency drops, the bill doesn't.
It can even *raise* costs indirectly, because it makes it painless to do more — fanning out ten speculative lookups where a sequential design would have done three carefully.
If cost is the pressure, the levers are elsewhere: fewer or smaller calls, caching, or a router that skips work.
Parallelization buys exactly one thing — time."

**"Aggregation: does the final merge have to be an LLM call?"**
"Only when synthesis is actually needed.
If branches return structured data going into a report template, plain code assembles it — cheaper and deterministic, so prefer it.
Use an LLM aggregator when the value is weaving prose from heterogeneous pieces, and then constrain it hard: 'ground every statement in the provided inputs, add nothing' — the aggregator is a fresh model call with all the usual hallucination risk, and the fan-out's careful sourcing can be undone by one sloppy merge prompt.
Special case: if the fan-out generated N candidates for the *same* task, the aggregator is a judge picking the best — that's parallelization as a quality tool, best-of-N, not just a speed tool."

**"How would this look in a framework — say LangChain or Google's ADK?"**
"LangChain's expression language has a parallel construct — RunnableParallel — where you hand it a map of named chains and it runs them concurrently, feeding the combined results onward; under the hood it's async I/O, one worker juggling waiting tasks, which is the right model since our branches are network-bound.
In ADK you'd compose it structurally: a ParallelAgent runs specialist sub-agents concurrently, each writing to its own state key, then a SequentialAgent chains that block with a merger agent that reads those keys and synthesizes.
Same shape either way — fan out, cubbyholes, gather, synthesize — the frameworks just differ in whether you express it as a data-flow expression or as an agent hierarchy."

**"How do you test a parallel workflow? It sounds like a nightmare."**
"Layer it, so most of the testing never touches concurrency at all.
Each branch is a self-contained unit — same input, own output slot — so branches get tested individually, sequentially, like any chain; that's where correctness lives.
The concurrent machinery gets its own targeted tests: inject a slow branch and verify the timeout and partial-results policy fire; inject a failing branch and verify solo retry; hammer the governor and verify nothing exceeds the in-flight cap.
And the aggregator gets tested with fixed, hand-built branch outputs — including partial ones with gaps — so its behavior is checked deterministically.
The trap to name: race conditions don't show up reliably in tests, which is why I prevent them by construction — exclusive output slots, no shared writes — rather than trying to catch them after the fact."

**"A user is watching a spinner. How do you combine the fan-out with streaming?"**
"Show branches as they land instead of gating everything on the gather.
The UI renders a section per branch — news, financials, leadership, competitors — each filling in the moment its branch completes, so the perceived wait is the *fastest* branch, not the slowest.
The synthesis, which genuinely needs all inputs, streams in last as the executive summary on top, or gets skipped in the live view and delivered on demand.
Two details make it work: branch outputs must be independently presentable — another reason each branch owns a clean structured slot — and the UI needs an honest per-branch state, pending, done, or failed-with-note, so a straggler shows as 'still checking' rather than freezing the page.
This is the cheapest large improvement in perceived speed available, because it changes no computation at all — only when the user gets to see it."

## How the other scenarios morph

The travel-planner question is the due-diligence answer with the latency dial turned all the way up: users wait live, so the fan-out — flights, hotels, events, restaurants — is not an optimization but the entire viability of the product, and the follow-through is streaming partial results into the UI as branches land, flights first because they anchor everything else.
It also sneaks in a soft dependency worth catching aloud: restaurant and event suggestions are *better* with the hotel's neighborhood known, so you either accept city-level results to keep full parallelism or run a fast second wave once the hotel branch lands — naming that tradeoff is the senior move.
The feedback-at-scale question is the batch variant: fan out across thousands of items rather than four aspects, which shifts the emphasis to the concurrency governor, checkpointed progress so item 700's crash doesn't restart the night, and cost — because at batch scale, model choice per item, not latency, is what the CFO sees.
One skeleton, three dials: aspect fan-out, latency-critical fan-out, item fan-out.

## Say it in one breath

Parallelization finds the steps in a workflow that don't depend on each other — independent lookups, tool calls, or sub-agents — and runs them simultaneously, fanning out at the start and gathering at the end for a final synthesis, so total time collapses from the sum of all steps to roughly the slowest one.
Independence is the entry ticket: no branch may read another's output or write shared state, and you still need per-branch timeouts, a partial-results policy, and a concurrency cap to survive stragglers, failures, and rate limits.
It buys latency, not money — same calls, rearranged — and it costs debugging complexity, so deploy it where users feel the wait and keep the tail of the workflow sequential where dependencies demand it.
