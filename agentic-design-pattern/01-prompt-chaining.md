# Pattern 1: Prompt Chaining — one big scary task, broken into small boring steps

## The interview scenario

This pattern hides inside questions like these:

"Design a system that takes a messy customer email and turns it into a structured refund request our order system can process."

"We get long market-research reports. Build something that summarizes each one, pulls out the key trends with supporting numbers, and drafts an email to the marketing team."

"Design a pipeline that reads scanned invoices and outputs clean, validated data — vendor, line items, totals — into our accounting system."

Notice the common shape: one input goes in, one output comes out, and in between there are clearly *distinct kinds of work* — understand, then extract, then transform, then compose.
Nobody says the words "prompt chaining" in the question.
Your job is to hear the stages hiding inside the task.

And know what's actually being tested when this question is asked, because it's rarely "do you know what a pipeline is."
The interviewer is testing decomposition — can you carve a fuzzy task at its natural joints — and, even more, whether you know what *reliability engineering* looks like when the workers are probabilistic: do you validate between steps, do you think about what happens when step three returns nonsense, do you know where deterministic code belongs in an AI system.
Chaining questions are also the classic *opening* question of an agentic interview, the one the later questions build on — so a crisp, failure-aware answer here sets the temperature for the whole hour.

## What this pattern is, in plain words

Prompt chaining — Gulli also calls it the Pipeline pattern — is the divide-and-conquer move: instead of asking the model to do a big complicated task in one giant prompt, you break the task into a sequence of small, focused prompts, where the output of each step becomes the input to the next.
One sentence: it's an assembly line for language tasks, one specialist per station.

The everyday analogy is exactly that — an assembly line, or if you prefer, a restaurant kitchen.
You don't hire one cook and shout "make the entire wedding banquet" at them; you have one station prep vegetables, another grill, another plate, and each station receives the previous station's output in a known form.
Each cook does one thing, does it well, and — crucially — you can *taste the food between stations*.

The problem it solves is that big monolithic prompts fail in predictable, ugly ways.
Gulli's book names them, and they're worth knowing by name because they're great interview vocabulary.
**Instruction neglect**: give a model six instructions in one prompt and it will quietly drop one or two — it summarizes beautifully and simply forgets you asked for an email.
**Contextual drift**: over a long generation the model loses the thread of what it was originally asked.
**Error propagation**: a small mistake made early poisons everything built on top of it.
And plain old **hallucination** — making things up — which gets *more* likely as the cognitive load of a prompt goes up.
Chaining attacks all of these at once: each prompt carries one instruction, so nothing gets neglected; each step is short, so there's no thread to lose; and because there are seams between steps, you can *check the work* at each seam and catch errors before they propagate.

It helps to know how widely this shape shows up, because breadth is ammunition for interviews.
The book catalogs the recurring families: information-processing pipelines (extract, summarize, entity-tag, look up, report); complex question answering, where a hard question gets split into sub-questions researched separately and then synthesized; unstructured-to-structured data extraction, with conditional re-prompting when fields come back missing; content generation staged as ideas, outline, drafted sections, revision; code generation staged as pseudocode, draft, review, refine, document; and even multi-turn conversation itself, where each turn is a link that carries forward the accumulated conversation state.
That last one is worth a beat: every chatbot that "remembers" what you said three turns ago is quietly running a chain, with the conversation history as the state flowing down the line.
Once you see the shape, you see it everywhere — which is exactly what you want to convey in the room.

## How the design actually works

Let me walk the machine end to end.
A request lands at the orchestrator — the plain, non-AI program that owns the sequence.
The orchestrator sends the input to step one, which is a single focused LLM call with its own carefully written prompt and, ideally, its own persona: Gulli suggests giving each stage a distinct role, like "you are a market analyst" for the extraction step and "you are a technical writer" for the drafting step, because a narrow role sharpens a step's output.
Step one's output comes back to the orchestrator, which may check it, may transform it, and then feeds it into step two's prompt.
This repeats down the line until the final step emits the answer.

The single most important engineering decision in the whole pattern is *what format the data takes as it moves between steps* — and the book is emphatic about this: make it **structured output**, meaning you force each step to answer in a machine-readable format like JSON (a simple text format of named fields and values, like `{"vendor": "Acme", "total": 1050}`) instead of free-flowing prose.
Why?
Because a chain is only as reliable as its hand-offs.
If step one hands step two a chatty paragraph, step two has to *interpret* it, and interpretation is where ambiguity — and therefore error — creeps in.
If step one hands over a JSON object with known fields, the orchestrator can *parse* it — read it with ordinary code, no AI involved — and verify it deterministically: are all required fields present, is the total a number, is the date a date.
That's the state being passed between steps: not vibes, but a growing, validated bundle of structured data.

And this points at the pattern's superpower, which candidates constantly under-sell: **the seams between steps are where you get to insert ordinary, deterministic code**.
Between two LLM calls you can validate the JSON, look something up in a database, branch on a condition, or call a tool.
The book's invoice example is perfect: the model extracts text, a second step normalizes it — turning "one thousand and fifty" into 1050 — and then, because LLMs are famously unreliable at arithmetic, the *math* gets delegated to an actual calculator tool, with the model just deciding what to compute.
The chain isn't just LLM-LLM-LLM; it's LLM, *check*, code, LLM, *tool*, *check*, LLM.
The checks are the point.

Where does it break?
Four failure modes to name in an interview.
First, **error compounding** — the chain's signature disease: each step is, say, 95% accurate, but errors multiply down the line, so five chained steps land you around 77% end-to-end (0.95 multiplied by itself five times).
The cure is validation at the seams, so errors get caught where they're born instead of compounding.
Second, **malformed output**: a step returns broken JSON or prose where JSON was expected, and a naive pipeline crashes.
The cure is parse-and-retry — if parsing fails, re-call that one step, including the error message in the retry prompt so the model can fix itself.
Third, **latency stacking**: five sequential model calls at two-ish seconds each is a ten-second-plus response, and the user feels every second.
The cures are streaming progress to the user, caching repeat inputs, and keeping the chain as short as honesty allows.
Fourth, **mid-chain crashes**: the process dies at step four — do you redo the whole thing?
The cure is checkpointing — saving each step's validated output as you go — so you can resume from where you fell, and making any step with side effects idempotent so a resume can't, say, double-file a refund.

Here are those four on a card, because they come up in every chaining conversation:

| Failure mode | What it looks like | The defense |
|---|---|---|
| Error compounding | Each step slightly wrong; the end wildly wrong | Validate at every seam; escalate ambiguity instead of guessing |
| Malformed output | A step returns prose or broken JSON where JSON was expected | Parse everything; retry that one step with the error message included |
| Latency stacking | Five polite two-second calls become one rude twelve-second wait | Shorten the chain, cache repeats, stream progress, parallelize what's independent |
| Mid-chain crash | Process dies at step four; work at risk of rerun or loss | Checkpoint each validated step; make side-effect steps idempotent |

A quick word on how this looks in the frameworks, since interviewers sometimes ask for grounding.
In LangChain, a chain is literally written with a pipe operator — prompt, then model, then output parser, composed like `prompt | llm | parser` — and the expression language (LCEL) handles passing each stage's output into the next, so the code reads like the diagram.
LangGraph is the step up for when a "chain" stops being a straight line: it models the workflow as a graph of nodes with explicit shared state, which is what you want once you need conditional branches, retries with memory, or resumable checkpoints — the stateful, cyclic stuff plain pipelines can't express.
CrewAI frames the same idea as a sequence of tasks handed between role-named agents, and Google's ADK gives you a SequentialAgent that runs sub-agents in order, each reading and writing named keys in a shared session state — which is precisely the "validated bundle of state flowing down the line" picture, just with framework nouns attached.
You don't need to know any of these deeply for an interview; you need one sentence — "this is a linear LCEL-style chain, and I'd graduate to LangGraph the moment I need branching or resumability" — to show your design maps onto real tooling.

When should you use chaining?
The book's rule of thumb: when a task is too complex for one prompt, has multiple *distinct* processing stages, needs tool calls between steps, or is a multi-step process that must carry state forward.
When should you *not*?
When one good prompt honestly does the job — every added link costs latency, money, and a new place to break, so a chain you didn't need is pure downside.
And how does it differ from its neighbors?
Chaining is a *fixed, linear* path — you, the designer, chose the steps.
If the path needs to *fork* based on the input, that's Routing (next chapter).
If steps don't depend on each other and could run simultaneously, that's Parallelization.
If the output loops back for critique and improvement, that's Reflection.
Chains are the straight roads; the other patterns are the intersections, the extra lanes, and the U-turns.

## The complete interview answer, spoken

Here's how I'd actually say it, start to finish, for: *"Design a system that turns a messy customer email into a structured refund request."*

"Before I design anything, let me pin down the problem with a few questions.
First — volume and speed: how many emails a day, and does anyone wait on the answer in real time?
I'll assume a few thousand a day and that nobody's watching a spinner — the email just needs to become a refund ticket within a few minutes, which takes latency pressure off and lets me favor reliability.
Second — what exactly must come out the other end?
I'll assume the order system wants a structured record: order ID, customer, items, refund amount, reason code, plus a confidence signal.
Third — and this shapes everything — what happens when we get it wrong?
Refunds are money, so I'll assume wrong-but-confident is much worse than 'flagged for a human.'
That tells me the design should prefer escalating to people over guessing.
Fourth, are emails text or do attachments and images matter?
I'll assume mostly text for the core design and mention attachments as an extension.

Simplest thing that could work: one LLM call — 'here's an email, return this JSON.'
Honestly, for clean, polite emails that mention an order number, that works a lot of the time.
But messy is the operative word: emails ramble across three topics, reference orders by date instead of number — 'the blender from before Christmas' — and mix a refund request with a complaint and a question.
One giant prompt doing understand-plus-look-up-plus-calculate-plus-compose runs into the classic single-prompt failures — it'll neglect instructions, or hallucinate an order ID, and I can't verify any intermediate reasoning.
Refunds deserve better.

So this is a prompt-chaining problem — the task has natural sequential stages, each stage's output feeds the next, and I want to validate between stages.
Here's the pipeline I'd sketch:

```
 email
   |
   v
+-----------+     +------------+     +-----------+     +------------+
| 1.Extract | --> | 2. Order   | --> | 3.Compute | --> | 4. Compose |
|  intent + |     |  lookup    |     |  refund   |     |  ticket +  |
|  entities |     | (DB tool)  |     | (calc     |     |  customer  |
|  -> JSON  |     |            |     |  tool)    |     |  reply     |
+-----------+     +------------+     +-----------+     +------------+
   |  [validate]     |  [validate]      |  [validate]      |
   +--> escalate     +--> escalate      +--> escalate      v
        to human          to human          to human    order system
```

Let me walk one email through it.
Step one is an extraction call with a narrow job and a narrow persona — 'you are a customer-service intake analyst' — and it returns *only* structured JSON: intent, order references, items, reason, sentiment, and its own confidence per field.
I force JSON because the chain's reliability lives in its hand-offs — structured output means the next stage parses data instead of interpreting prose.
Right after it, my first seam: ordinary code validates the JSON — does it parse, are required fields present?
If parsing fails, I retry that one step with the parser's error message included so the model can correct itself; if intent isn't 'refund,' the email exits this pipeline entirely.

Step two isn't an LLM being clever — it's a database lookup, a tool call.
Whatever the extraction gave us — order number, customer email, fuzzy date — we query the order system with real code.
This seam is exactly why I chained: I get to insert deterministic logic between model calls.
If the lookup finds one match, great; zero or several matches, we don't guess — we escalate to a human, or send the customer a clarifying email, because a refund against the wrong order is the expensive failure we agreed to avoid.

Step three computes the refund amount, and here's a detail I'd flag: LLMs are bad at arithmetic, so the model doesn't do math.
An LLM call decides *what* to compute — which items, whether shipping's included, which policy applies — and hands the numbers to a calculator function.
Then a hard guardrail in plain code: amount must not exceed the order total, and anything above a policy threshold routes to human approval no matter how confident the model is.

Step four composes: the refund ticket for the order system, in its exact schema, and a friendly reply email to the customer.
I'd use my strongest model here since it's customer-facing prose, while steps one and three run on a small cheap model — matching model size to step difficulty is one of chaining's quiet economic wins.

Failure modes — let me name them before you do.
Error compounding: four stages at 95% each is only about 81% end-to-end if errors flow freely, which is exactly why every seam validates and why ambiguity escalates instead of proceeding.
Malformed output: handled by parse-and-retry at each seam.
Latency stacking: four sequential calls is maybe ten seconds — fine here because this is asynchronous, but if a support agent were watching live I'd stream progress and consider merging steps.
Mid-pipeline crashes: I checkpoint each validated step's output, so a crash at step three resumes from step two's saved state rather than re-running everything — and ticket creation is idempotent, keyed by a unique request ID, so a retry can never file the same refund twice.

Evaluation and monitoring.
Pre-launch, I'd build a test set of a couple hundred real emails with hand-labeled expected outputs, and score each stage *separately* — extraction accuracy, lookup precision, computation correctness — because per-stage scoring tells me where the pipeline is weak; end-to-end scoring alone just tells me *that* it's weak.
That's the debugging superpower chaining buys and monoliths lack.
In production: trace every request — every prompt, response, and tool result — dashboards for per-stage failure rate, escalation rate, p95 latency, and cost, and a weekly human review of a random sample plus every case where a customer disputed the outcome.
My north-star metric is the fraction of refunds fully handled correctly with no human touch; my safety metric is wrong-refund rate, which I want at effectively zero.

Cost: roughly three small-model calls plus one strong-model call per email — call it a cent or two each, so a few thousand emails a day is tens of dollars.
Against the cost of the support time it replaces, that's a rounding error.
Two extensions I'd flag without designing in full.
Attachments: receipts and photos make step one multimodal — same chain shape, with an extra extraction branch for images feeding the same validated state, so the architecture absorbs it without surgery.
And prompt changes: each step's prompt is versioned like code, tested against that stage's golden set before rollout, and canaried — because in a chain, an 'improvement' to step one can silently degrade step three, and per-stage eval is what catches the ripple.

And if I had to ship in a week: collapse steps one and three into one call, keep the order-lookup seam and the amount guardrail — those are the load-bearing parts — skip the polished reply email, and route generously to humans while logging everything, so real traffic tells us where to invest next."

That's the whole arc — requirements, baseline, pattern with a reason, walked diagram, self-inflicted failure analysis, eval, money — in about fifteen spoken minutes.

## Follow-ups they will ask

**"Why not one big prompt? Models are pretty capable now."**
"Capability isn't the issue — verifiability is.
A monolith gives me one opaque blob: I can't check intermediate work, can't insert the database lookup or the amount guardrail mid-thought, and when quality drops I can't tell *which* skill failed.
The chain gives me seams, and the seams are where validation, tools, and debugging live.
That said, I'd keep the chain as short as the task honestly allows — every link is latency and cost."

**"A middle step returns garbage JSON. Walk me through what happens."**
"The parser fails, which my orchestrator catches immediately — the garbage never reaches the next step.
I retry that single step, appending the parse error to the prompt so the model can self-correct; that fixes the vast majority.
Two strikes and the request escalates to a human with the full trace attached.
The principle: fail loudly at the seam where the error was born, never let it compound downstream."

**"How do you stop errors from compounding even when every step 'succeeds'?"**
"Validation catches *format* errors; for *content* errors I use three tools: each step reports per-field confidence and low confidence escalates rather than proceeds; the seams cross-check against ground truth where it exists — the order database is my anchor of reality; and per-stage eval metrics tell me which stage drifts so I fix the source, not the symptom."

**"Latency is now unacceptable — say this must feel instant. What do you change?"**
"Three levers in order.
Shorten the chain — merge adjacent easy steps into one call.
Check which steps are actually independent and run those concurrently — that's the Parallelization pattern.
And stream: acknowledge instantly, show progress as stages complete.
If it truly must be sub-second, I'd cache aggressively and precompute what I can, and accept a simpler single-call design for the easy majority with the chain reserved for the hard cases."

**"How would you decide which model each step gets?"**
"Empirically.
Run my eval set per stage across model tiers: extraction and classification usually hit ceiling on small cheap models; nuanced synthesis or customer-facing prose earns the big model.
Chaining is what makes this possible at all — a monolith forces one model to be good at everything, so you pay big-model prices on trivial work."

**"Where does context engineering come into this?"**
"Each step should receive the *minimum* context that lets it succeed — not the whole conversation-so-far.
The book calls this context engineering: deliberately selecting and packaging what each call sees.
Practically, my orchestrator passes step three the validated order record and the extracted claim — not the raw email — which cuts tokens, cuts cost, and actually improves accuracy, because models get worse, not better, when you bury the signal in clutter."

**"Suppose one step needs a human sign-off — say, refunds over 200 dollars. Does that break the chain?"**
"Not at all — it just means the chain has to be able to *pause*.
The orchestrator checkpoints the full state at that seam, files an approval task for a human, and the pipeline for that request simply stops; when the approval lands — minutes or days later — the chain resumes from the saved state as if nothing happened.
Two things make this safe: the state was already structured and validated, so resuming is just reloading a JSON bundle, and the downstream steps are idempotent, so even a double-triggered resume can't file two refunds.
This is exactly why I'd pick a stateful orchestrator like LangGraph for anything involving approvals — a chain that lives entirely in one process's memory can't survive a three-day pause."

## How the other scenarios morph

Before the one-breath summary, a quick note on transferring this answer, because you'll never get the refund email verbatim.
The market-research question — summarize, find trends, draft the email — is the book's own worked example, and it's an even purer chain: summarizer persona, then trend-extractor emitting JSON with each trend's supporting data points, then a writer persona composing the email from that JSON; the seams validate that trends actually cite data, which is the guard against the model decorating its claims.
The invoice question adds the OCR wrinkle and rewards two specific moves from the book: a normalization step that converts "one thousand and fifty" into 1050 before anything downstream touches it, and delegating all arithmetic to a calculator tool because models flub precise math — plus a conditional loop where missing fields trigger a targeted re-extraction prompt rather than a full redo.
Different nouns, same skeleton: hear the stages, structure the hand-offs, validate the seams, put tools and humans where the model is weakest.

## Say it in one breath

Prompt chaining breaks one complex task into a fixed sequence of small focused LLM calls, each passing validated, structured output to the next — an assembly line with quality checks between stations.
It beats one giant prompt because single prompts neglect instructions and compound errors invisibly, while a chain gives you seams for validation, tool calls, and per-step debugging.
The cost is stacked latency and more moving parts, so use it when a task has genuinely distinct stages — and keep it as short as the task allows.
