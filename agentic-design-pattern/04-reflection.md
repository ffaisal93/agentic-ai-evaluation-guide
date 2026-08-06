# Pattern 4: Reflection — the system that checks its own work before you see it

## The interview scenario

Reflection questions sound like these:

"Design an assistant that writes SQL queries — or Python functions — for analysts. The catch: the code it ships has to actually be correct, not just plausible."

"Our marketing team wants AI-drafted copy, but everything published must meet brand and legal guidelines. Design a system where the output quality is trustworthy enough to need only a light human skim."

"Design a contract-summarization tool for a legal team. Missing a clause in the summary is unacceptable. How do you get the error rate down?"

The tell is a *quality bar*: the question stresses correctness, polish, compliance, or completeness, and there's an implied tolerance for taking a bit longer and spending a bit more to get there.
When you hear "it has to be right," "it must meet the guidelines," or "a mistake is unacceptable," the interviewer is inviting you to say: then the first draft can't be the final answer — the system needs to critique and revise its own work.

What's being tested is subtler than the previous three patterns: it's whether you understand that LLM output quality is a *distribution*, not a constant, and that you can engineer the distribution — and whether you'll reach for objective verification before subjective opinion.
The candidates who stand out ground the critique in something un-foolable — run the code, execute the query, validate the schema — and treat the LLM critic as the layer for what can't be checked mechanically.
The candidates who struggle say "the model double-checks itself" and stop there, which is the pattern's cardinal sin: a self-graded exam with the same blind spots on both sides of the desk.

## What this pattern is, in plain words

Reflection means the system doesn't ship its first attempt: it generates an output, then evaluates that output against criteria — using another LLM call, a set of rules, or a real tool like a test runner — and uses the critique to produce an improved version, looping until the work passes or a budget runs out.
One sentence: it's a feedback loop bolted onto generation — draft, critique, revise, repeat.

The everyday analogy is a writer and an editor.
Nobody publishes their first draft; you write it, then you — or better, someone else — reads it with a red pen, and the marked-up copy drives the rewrite.
The "someone else" part matters, and it's the heart of the book's treatment: the most effective form of this pattern splits the work into two roles, a **producer** that only generates and a **critic** that only evaluates — the generator-critic model.
They can literally be the same underlying LLM wearing two different system prompts, but the separation still works, because a critic prompted as "you are a meticulous senior reviewer; your job is to find flaws" reads the draft with fresh eyes and no attachment.
The book's phrase for why is lovely: it avoids the cognitive bias of an agent grading its own homework.
A producer asked "check your own work" tends to conclude its work is fine; a dedicated critic is *rewarded* for finding problems, so it finds them.

The problem reflection solves: every pattern so far — chain, router, parallel block — is single-pass; whatever comes out, ships.
But first-pass LLM output is routinely 80%-good: right shape, wrong detail; working code, missed edge case; fine summary, one omitted clause.
Reflection is the pattern that converts 80%-good into actually-good by spending more compute — and it's the only pattern in this part whose purpose is *quality* rather than structure or speed.

Its natural habitats, per the book's catalog: creative and long-form writing, where drafts get critiqued for flow, tone, and clarity and rewritten until they pass; code generation and debugging, where the critique is tests and static analysis and the loop is write-test-fix; complex reasoning, where the system evaluates whether an intermediate step actually moves toward the solution and backtracks when it doesn't; summarization, where the summary is checked against the source's key points and patched for what it missed; planning, where a proposed plan gets stress-tested against constraints before anyone executes it; and conversational agents, where reviewing recent turns keeps the thread coherent and catches misunderstandings before they compound.
Two through-lines in that list: the critique is always against *explicit criteria*, and the payoff is always largest where a subtle miss is expensive — which is your targeting guide for where to spend reflection budget.

## How the design actually works

The loop has four beats, straight from the book: **execute** — the producer generates the initial output from the task prompt; **evaluate** — the critic examines that output against explicit criteria: factual accuracy, completeness, style, adherence to instructions; **refine** — the critique goes back to the producer, which generates a new version *guided by* the specific feedback rather than just re-rolling the dice; **iterate** — repeat until a stopping condition fires.
The orchestrator around this loop is doing real work: it carries the state, and the state here is richer than in any previous pattern — the original task, every draft so far, every critique so far — because the producer revises best when it can see what it wrote *and* what was wrong with it.
That accumulating history is also the pattern's hidden tax, which we'll get to.

Two design decisions define any reflection system, and interviewers probe both.

First: **what does the critic actually check, and with what?**
The strongest critics aren't LLMs at all — they're ground truth.
If the output is code, run the tests; if it's JSON, run the validator; if it's SQL, execute it against a sample database.
The book's code-generation example leans exactly this way: critique via tests and static analysis where possible.
Objective checks can't be sweet-talked.
When the criteria are fuzzy — tone, clarity, completeness of a summary — the critic is an LLM call with a sharply written rubric and a persona: "you are a senior software engineer performing a meticulous review; list concrete flaws as bullets."
The craft here is making the critique *actionable*: "issue: the function doesn't handle negative input; fix: raise a ValueError" drives a good revision, while "could be better" drives a coin flip.
Best practice is a structured critique — the book's ADK reviewer returns a status field, ACCURATE or INACCURATE, plus reasoning — so the orchestrator can branch on the verdict mechanically.

The menu of critics, in rough order of how much you should trust them:

| Critic type | Example | Objectivity | Cost | Can it be fooled? |
|---|---|---|---|---|
| Execution / tests | Run the code; run the SQL on a replica | Ground truth | Cheap | No — reality doesn't negotiate |
| Deterministic checks | Schema validation, length limits, banned-terms scan | Ground truth for what they cover | Nearly free | No, but they cover only what you wrote |
| LLM with a rubric | "Senior reviewer" persona grading against criteria | Good, not perfect | One model call per lap | Yes — calibrate it on planted defects |
| Human review | Expert skims flagged outputs | Best judgment available | Expensive, slow | Rarely — but doesn't scale |

The design instinct: stack them, cheapest and most objective first, and only let the expensive subjective layers see work that survived the mechanical ones.

Where the loop *sits* is a design choice too.
The obvious placement is at the end — reflect on the final output before shipping — and that's the default.
But reflection can also guard a single step inside a larger chain: only the extraction step gets a critique loop, because that's where errors are born, while the cheap formatting steps stay single-pass.
And the loop doesn't even have to block the user: a valid pattern is ship-then-refine, where the draft goes out immediately and a background reflection pass upgrades it — right for documents, wrong for anything with side effects, since you can't un-send a refund.
Saying "I'd put the reflection budget where the errors actually are, not around everything" is a sentence that marks you as someone who's paid these bills.

Second: **when does the loop stop?**
Three exits, and you should name all three.
The happy exit: the critic passes the work — the book's LangChain example literally has the critic emit a sentinel phrase, CODE_IS_PERFECT, that the orchestrator watches for.
The budget exit: a maximum iteration count — two or three, almost never more — because each lap costs a full generate-plus-critique cycle in latency and tokens, and returns diminish fast: the first revision captures most of the gain, the third is usually polishing marginalia.
The stall exit: if the critique isn't changing or the drafts aren't improving between laps, stop — the loop is orbiting, not converging, and more laps just burn money.
A loop with only the happy exit is a bug: a too-picky critic against a maxed-out producer will spin forever.

Where it breaks — the failure modes to volunteer.
**Cost and latency multiplication**: the book is explicit that this is the pattern's core trade-off — every lap is at least two more LLM calls, so a three-iteration loop can multiply a step's cost and latency several-fold, which is disqualifying for time-sensitive paths.
**Context bloat**: the history grows every lap — draft one, critique one, draft two, critique two — and can crowd the context window, degrading the model or hitting hard limits; the standard cure is compaction: carry the latest draft, the latest critique, and the original requirements, and drop the fossil record.
**The lenient critic**: a critic that waves everything through gives you the pattern's cost with none of its benefit — detectable when your pass rate is suspiciously near 100% while downstream users still find errors; the cure is tightening the rubric and calibrating the critic against known-flawed examples, where it must catch the planted bugs.
**The unappeasable critic**: the opposite disease — a nitpicker that never passes anything, caught by the iteration cap and by monitoring average laps per request.
**Oscillation**: the producer "fixes" issue A by reintroducing issue B, laps alternating forever between two flawed versions — caught by the stall detector.

When to use it — the book's rule of thumb, almost verbatim because it's so quotable: when the quality, accuracy, and detail of the output matter more than speed and cost.
Polished long-form content, working code, high-stakes summaries, plans that must survive contact with constraints.
And use a *separate* critic when the evaluation needs objectivity or expertise the producer's generalist framing won't supply.
When not: real-time chat, high-volume cheap paths, or tasks where "pretty good" genuinely is good enough — reflection on a casual chatbot reply is paying triple for a nicety nobody asked for.
Versus neighbors: a chain moves *forward* through different stages; reflection *cycles* over the same work — it's the one pattern here with a loop in the graph, which is why frameworks matter: a single draft-critique-revise pass fits a linear chain, but true iteration needs state and cycles, which is LangGraph territory or an explicit loop in code, per the book.
And one forward pointer worth dropping: reflection is how *goals* become enforceable — the critique criteria are the goal restated as a checklist, and with memory attached, critiques can accumulate so the system stops repeating last week's mistakes; the book connects reflection to goal-monitoring and memory chapters on exactly those lines.

## The complete interview answer, spoken

Here's the full spoken answer for: *"Design an assistant that writes SQL for analysts — and the queries have to be right."*

"Clarifying questions first.
Who uses this and can they read SQL?
I'll assume analysts who can mostly read it but don't want to write it — which means they'll skim, not audit, so the system carries the correctness burden.
What does 'wrong' cost?
A syntactically broken query is annoying; a query that *runs* and returns subtly wrong numbers is dangerous, because wrong numbers travel into decisions.
So my enemy is the plausible-but-wrong query, and I'll design against that specifically.
Latency tolerance: I'll assume this is an ask-and-wait tool where ten to twenty seconds for a trustworthy answer beats two seconds for a coin flip — worth confirming, because it licenses everything that follows.
Scale: a few hundred queries a day across the org.
And I'll assume we have the database schema available and a safe, read-only replica — a copy of the database that can't modify anything — where candidate queries can be executed harmlessly.

Simplest thing that could work: one call — schema in the prompt, question in, SQL out.
Modern models are genuinely decent at this, and honestly, that's the right design for throwaway exploration.
But our bar is 'analysts trust it,' and single-pass SQL fails in exactly the way we fear most: it usually *runs* — joins that silently duplicate rows, filters that quietly drop the rows you meant to keep, aggregates over the wrong grain.
The failure is invisible at generation time; it only shows up when someone checks the work.
So the design conclusion writes itself: the system has to check the work — this is a reflection problem, and better, one where much of the critique can be *objective*, because SQL can be executed.

Here's the loop I'd draw:

```
   question + schema
        |
        v
  +----------+   draft SQL   +-----------------+
  | PRODUCER | ------------> |  CRITIC          |
  | (writes  |               |  1. run on       |
  |  SQL)    |               |     replica      |
  +----------+               |  2. sanity checks|
        ^                    |  3. LLM review   |
        |   critique:        +-----------------+
        |   errors, row        |            |
        |   counts, flaws      | PASS       | FAIL (max 3 laps)
        +----------------------+            |
             (revise)          v            v
                        ship w/ explan.   escalate w/ trace
```

Walking it through.
The producer is an LLM call with the question, the relevant slice of the schema — not all four hundred tables; I'd retrieve just the tables that match the question, which is context engineering keeping the prompt sharp — plus a few example query patterns for this warehouse.
It drafts a query with a one-line explanation of its approach.

Then the critic — and here's the core of my design: the critic is layered, cheapest and most objective checks first.
Layer one is execution: run the draft against the read-only replica with a row limit and a timeout.
Syntax errors and missing columns are caught instantly, by ground truth, for free — no LLM opinion involved, and no risk, because the replica can't be harmed and the query can't mutate anything.
Layer two is mechanical sanity checks in plain code: did it return zero rows for a question that plainly expects data; did a join explode the row count; are there obvious grain mismatches.
Layer three is the LLM critic — a separate call, distinct persona: 'you are a meticulous senior data engineer reviewing this query against this question and this schema; list concrete flaws' — and critically, it gets to see the *execution results*, not just the SQL: a sample of returned rows and the row count.
A reviewer who can see what the query actually did catches semantic wrongness — right syntax, wrong meaning — far better than one reading code cold.
It returns a structured verdict: pass or fail, plus bulleted, actionable issues.

Why a separate critic call rather than telling the producer 'double-check your work'?
Because models grading their own homework grade generously — the book calls it the cognitive bias of self-review.
A dedicated critic, prompted to hunt flaws, with the execution evidence in hand, is adversarial by construction, and that separation of concerns is what makes the loop actually catch things.
Same underlying model is fine; different instructions are the point.

If the critic fails the draft, the loop closes: producer gets its own SQL back plus the full critique — 'the join on orders duplicates customers with multiple orders; aggregate before joining' — and revises against the specific complaints.
Stopping conditions, three of them: pass, obviously; a hard cap of three laps, because lap one captures most of the improvement and lap four is usually the loop orbiting; and a stall check — if the same critique repeats twice, we stop early, because we're oscillating, not converging.
On exhaustion the query is *not* shipped as if fine: the analyst gets the best draft explicitly flagged 'unverified — review before trusting,' with the critic's outstanding concerns attached.
Honest failure preserves the trust that silent failure would spend.
And to control context bloat as laps accumulate, each revision carries only the original question, the latest draft, and the latest critique — the loop's fossil record gets dropped, keeping every call small.

What ships on success: the SQL, the plain-English explanation of what it does, and a peek at the result — which doubles as the analyst's own last-mile check.

Failure modes of the loop itself, before you raise them.
Cost and latency multiplication is intrinsic — each lap is two-plus LLM calls plus an execution; that's the pattern's fundamental trade and it's exactly what our requirements said we'd pay.
Typical case: one lap, maybe eight seconds; worst case three laps, around twenty-five — within tolerance, and I'd stream status so the wait feels attended.
A lenient critic gives me cost without benefit — I'd calibrate it against a planted-bugs suite, queries with known subtle errors it *must* catch, and if its pass rate drifts toward 100% while analysts still report issues, the rubric tightens.
An unappeasable critic burns laps on nitpicks — visible as average-laps-per-request creeping up, tuned by telling the critic to distinguish blocking flaws from style notes and fail only on blockers.
And the replica execution needs its own timeout so a pathological draft query can't hang the whole loop.

Evaluation.
Offline: a golden set of a couple hundred question-to-verified-SQL pairs, scored on execution results matching — not SQL text matching, since different queries can be equally right.
I'd track first-draft pass rate versus post-reflection pass rate; that *delta is the reflection loop's entire reason to exist*, and if it's small, the loop isn't earning its cost and I should ship single-pass with execution-check only.
Online: laps per request, pass rate per lap, unverified-output rate, p95 latency, cost per query — and the metric that actually matters, analyst corrections: when a user edits or disputes a shipped query, that's a missed defect, logged against the critic, and it feeds the planted-bugs suite so the critic learns the org's real failure patterns.
SLO: 90% of queries ship verified in under fifteen seconds.

Cost: typical request is producer plus critic plus one revision — three to four LLM calls, a few cents on a strong model; a few hundred queries a day is maybe ten dollars.
Set against analysts hand-writing SQL or, worse, acting on wrong numbers, it's nothing.
Under a one-week deadline, here's what I'd cut and keep: keep the execution check — that's the highest-value component and it's just code, no ML — keep single-pass generation, and defer the LLM critic and the loop.
And one security note, since we're executing model-written queries: the replica connection runs under a read-only account with row limits and statement timeouts enforced by the *database*, not by the prompt — because a prompt is a request and a permission is a guarantee.
That also blunts prompt injection through the data: even if something in a table name or a question tricks the model into generating something hostile, the blast radius is a failed read on a replica, not a write to production.

Execution-checked single-pass is already a big step up from raw generation; the reflection loop is the second week's work, and the delta metric from my eval set will prove whether it pays."

## Follow-ups they will ask

**"Same model as producer and critic — does that actually help? It's grading itself."**
"It helps, and the evidence is the asymmetry of the two jobs: generation is open-ended, review against a rubric is constrained, and models are better reviewers than generators of the same content.
The separate call with an adversarial persona breaks the self-serving framing — the critic's instructions reward finding flaws, and it reads the draft without the generation context that would bias it.
That said, I'd strengthen it where it matters: ground the critique in objective signals — test runs, execution results — which no model can sweet-talk, and optionally use a different model family as critic for genuinely independent eyes."

**"How many iterations, and how did you pick that number?"**
"Cap at two or three, and empirically, not by taste: my eval set gives me quality-per-lap curves, and they're always steeply diminishing — lap one captures most of the gain, lap three is polishing.
Each lap costs a full generate-critique cycle in money and seconds, so the cap is where marginal quality drops below marginal cost.
Plus a stall exit: repeated identical critiques or oscillating drafts end the loop early regardless of budget, because more laps on a stalled loop is pure spend."

**"The critic passes something that's actually wrong. What's your defense?"**
"Defense in depth, because the critic is a probabilistic component like everything else.
Objective layers first — execution, tests, validators — catch the whole class of mechanically detectable wrongness before opinion enters.
The critic itself is calibrated on a planted-defects suite: known-bad outputs it must flag, tracked over time so leniency drift is visible.
Downstream, user corrections are logged as missed defects and fed back into that suite.
And the product is honest about residual risk — verified means 'passed these checks,' shown to the user, not 'guaranteed correct.'"

**"This tripled your latency. When is reflection simply the wrong call?"**
"Whenever speed or cost outranks polish: real-time conversation, high-volume low-stakes paths, drafts a human will heavily edit anyway.
The rule of thumb I use is the book's: reflection is for when quality, accuracy, and detail matter more than speed and cost.
The design answer isn't all-or-nothing, though — it's placement: reflect on the 5% of traffic that's high-stakes, single-pass the rest, and let a router make that call.
Or run reflection asynchronously — ship the draft, refine in the background, update if the revision materially improves."

**"How is reflection different from just chaining a 'review' step onto the pipeline?"**
"A single draft-critique-revise pass *is* expressible as a chain — three calls in a row — and for many products that one pass is all you need; the book makes exactly that point about single-cycle reflection fitting linear tools.
The pattern becomes distinct when it loops: the output cycles back, state accumulates across laps, and an exit condition — not position in a sequence — decides when you're done.
That cycle is architecturally different: chains are straight lines, reflection has a loop in the graph, which is why it wants stateful orchestration like LangGraph or an explicit loop with an iteration budget rather than a fixed pipeline."

**"Could the critic's feedback improve the system permanently, not just this one output?"**
"Yes — that's the bridge from reflection to memory and self-improvement.
Within a session, carrying critiques forward stops the producer repeating a mistake it just made.
Across sessions, mine the critique logs: recurring complaints — 'joins before aggregating,' 'missing the fiscal-calendar convention' — are systematic weaknesses, and the cheap fix is folding them into the producer's standing instructions, so next month's first drafts stop making this month's mistakes.
That turns the reflection loop from a per-request quality tax into a flywheel: the loop's byproduct is a map of your system's failure modes, and each one you fix reduces how often you need the loop at all."

**"Isn't your critic just evaluation? What's the difference between reflection and having a good eval set?"**
"Same muscle, different moment — and keeping them straight matters.
Reflection is *runtime*, per-request: the critic judges this one output, right now, and its verdict changes what this user receives.
Evaluation is *offline*, per-system: the golden set judges the whole design across hundreds of cases, and its verdict changes what I build next.
They feed each other beautifully — the runtime critic's rubric usually starts life as the offline eval's rubric, and every defect the runtime critic catches or misses becomes a new offline test case.
But they don't substitute: a great eval set can't save an individual bad output at 3 p.m. on a Tuesday, and a great runtime critic can't tell you whether last week's prompt change made the system better on average.
You want both, and in an interview I'd name them separately on purpose."

**"Why iterate at all? Why not generate five candidates in parallel and pick the best one?"**
"Best-of-N is a real alternative and sometimes the better one — it's parallelization applied to quality, so it's *fast*: five drafts arrive in one round-trip, a judge picks, done, no loop latency.
It shines when failures are random — flaky phrasing, occasional weak drafts — because five independent rolls of the dice probably include a good one.
Reflection shines when failures are *systematic*: if the model reliably misses the same edge case, all five candidates share the flaw, and no amount of picking fixes what only feedback can — the critique injects information the producer didn't have, which resampling never does.
They also compose: generate three candidates in parallel, have the critic pick the strongest *and* critique it, then one revision lap on the winner — roughly the quality of three reflection laps at the latency of one.
In the room, naming that hybrid — and the diagnosis that picks between them, random flaws versus systematic ones — is a genuinely senior answer."

## How the other scenarios morph

The marketing-copy question swaps the un-foolable execution critic for the next best thing: the brand and legal guidelines *are* the rubric, pasted into the critic's prompt verbatim, so the critique step becomes "audit this draft against these numbered rules and cite the rule for every violation" — which keeps the feedback concrete — plus a deterministic layer for the checkable subset, banned words and mandatory disclaimers, which is code, not opinion.
The promised "light human skim" is then a design input: the system surfaces the critic's audit trail alongside the draft, so the human reviews *the exceptions*, not the whole document — reflection as a labor-compression device.
The contract-summarization question stresses completeness, and the strong move is a critic that works *backward*: instead of asking "is this summary good," it walks the source contract clause by clause and checks each one is represented — a coverage audit, which is a much harder critic to charm than a general "review this" prompt.
Both keep the sacred structure: producer, independent critique against explicit criteria, revision driven by the specific complaints, capped laps, honest flagging of what never passed.

## Say it in one breath

Reflection refuses to ship the first draft: a producer generates, a critic — a separate LLM call with an adversarial rubric, or better, ground truth like tests and execution — evaluates it, and the specific critique drives a revision, looping with a hard iteration cap and a stall check.
The producer-critic split is the heart of it, because models grading their own homework grade generously, while a dedicated flaw-hunter with fresh eyes actually finds things.
It multiplies cost and latency by design, so reserve it for the paths where quality outranks speed — and measure the first-draft-versus-final delta, because that delta is the only proof the loop is earning its keep.
