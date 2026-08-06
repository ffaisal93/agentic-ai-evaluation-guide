# Pattern 2: Routing — the front desk that sends each request to the right specialist

## The interview scenario

Routing questions sound like these:

"Design a customer-support assistant for an airline. Users ask about bookings, refunds, baggage rules, flight status — everything. How do you handle that variety?"

"We're building an internal AI helper for employees. It should answer HR questions, IT questions, and finance questions, each backed by different systems. Design it."

"Design an AI coding assistant that can debug code, explain code, or translate it between languages, depending on what the user pastes in."

The tell is *heterogeneous input*: requests arrive in one front door but belong to genuinely different categories, each needing different tools, different data, or different handling.
The moment you catch yourself thinking "well, it depends what kind of request it is" — that's the routing bell ringing.

What's being tested here is classification thinking plus honesty about uncertainty.
The interviewer wants to see whether you'll decompose the traffic before decomposing the task, whether you can compare decision mechanisms with real tradeoffs instead of defaulting to "the LLM decides," and — the discriminating detail — what you do when the classifier *isn't sure*, because candidates who have an `unclear` route and a confidence policy read as people who've watched a router be wrong in production, and candidates who don't, don't.

## What this pattern is, in plain words

Routing means putting a decision-maker at the front of your system that looks at each incoming request, figures out what *kind* of request it is, and sends it down the right specialized path.
One sentence: it's a classify-then-dispatch step that turns one rigid pipeline into a small family of specialist pipelines behind a single front door.

The everyday analogy is a hospital triage nurse.
Everyone walks into the same emergency room, but the nurse takes one look and directs you: broken arm to X-ray, chest pain straight to cardiology, sniffles to the waiting room.
The nurse doesn't treat anyone — the nurse's entire job is the *decision* — and the whole hospital works better because each patient reaches someone equipped for their specific problem.

The problem routing solves is that chaining alone is rigid.
A chain is one fixed road: great when every input needs the same treatment, hopeless when inputs genuinely differ.
You *could* build one mega-pipeline that handles bookings and refunds and baggage in a single flow, but you'd be back to the giant-prompt disease — a jack-of-all-trades that's mediocre at each, with a prompt that grows more contradictory with every category you bolt on.
Routing lets each downstream path stay small, focused, and independently testable, and it adds the thing chains lack: *conditional* behavior — the system reacts to what actually arrived instead of marching through a predetermined sequence.

And like chaining, this shape is everywhere once you have eyes for it.
The book's catalog: virtual assistants and AI tutors interpreting intent before choosing a response strategy — the tutor even routes on *performance*, picking the next lesson module based on how you did; document and data pipelines classifying incoming emails, tickets, and payloads into the right downstream workflow; multi-tool research systems dispatching each sub-task to the agent best suited for it; and coding assistants detecting language and intent before choosing the debug, explain, or translate path.
The common thread is a system that stops being a single script and starts being a *dispatcher* — which, incidentally, is why routing is the gateway to the multi-agent patterns later in the book: a coordinator delegating to specialist agents is routing wearing an organizational chart.

## How the design actually works

The anatomy has three parts: a **router** that makes the decision, a set of **handlers** — the specialist paths, each of which might be a single prompt, a whole chain, a tool, or even another agent — and a **default route** for everything the router can't confidently place.
The flow: a request lands at the router; the router emits a decision — essentially a label like `booking`, `refund`, `baggage`, or `unclear`; the orchestrator reads that label and forwards the *original request*, plus any useful context, to the matching handler; the handler produces the answer.
The state passed along is simple but worth naming in an interview: the raw request, the router's decision (with a confidence score if you have one), and any entities extracted along the way — keeping that bundle intact means the specialist never starts from zero and the trace tells you later why the request went where it went.

Now the design decision interviewers actually probe: *how does the router decide?*
The book lays out four options, and you should be able to rattle them off with tradeoffs.

**Rule-based routing**: plain code — if the text contains a booking reference pattern, go to bookings; if the subject line says "invoice," go to finance.
Instant, free, perfectly predictable — deterministic, meaning the same input always takes the same path.
But brittle: rules can't read nuance, and real users phrase things sideways.

**LLM-based routing**: ask a model directly — "classify this request as booking, refund, baggage, or other; answer with the single word only."
Maximally flexible, handles novel phrasing effortlessly, needs zero training data — but every routing decision now costs a model call's latency and money, and the model can occasionally get creative with its answer, so you must validate its output against the allowed labels and treat anything else as `unclear`.

**Embedding-based routing**: convert the request into an embedding — a list of numbers that captures the text's *meaning*, such that similar meanings produce nearby numbers — and compare it against reference embeddings for each route, picking the closest.
This is semantic matching without a full model call: faster and cheaper than LLM routing, smarter than rules, though it gives you a similarity score rather than reasoning, and borderline cases need a confidence threshold below which you fall back to something smarter.

**Trained-classifier routing**: collect a few thousand labeled examples — this request was a refund, that one was baggage — and train a small dedicated classification model.
At runtime it's fast, cheap, and consistent, with the decision baked into learned weights rather than a prompt; the price is the labeling effort and a retraining loop whenever categories shift.
A nice detail from the book worth quoting: you can use an LLM *offline* to generate synthetic training examples for this classifier, so the expensive model does the heavy lifting once, at training time, instead of on every request.

Side by side, since this comparison is the single most likely probe in a routing interview:

| Router type | Speed / cost | Handles messy phrasing | Needs training data | Best moment to use it |
|---|---|---|---|---|
| Rules (code) | Instant, free | Poorly | No | Dead-giveaway patterns; day-one short-circuits |
| Embedding similarity | Fast, cheap | Well | Just route descriptions | Many routes, semantic matching, moderate stakes |
| Trained classifier | Fast, cheap at runtime | Well, within its training | Yes — thousands of labels | High volume, stable categories, month two onward |
| LLM prompt | Slowest, priciest per call | Best | No | Day one, long-tail inputs, and as everyone's fallback |

One more structural idea before the failure modes: routing *nests*.
A big system rarely has one flat router with twenty labels — accuracy degrades as the label list grows, and the prompt becomes a wall of definitions.
Instead you route hierarchically, like a phone tree that actually works: a top-level router picks among three or four broad domains — support, sales, account — and each domain has its own small router picking among its handlers.
Each decision stays easy, each router's prompt stays short, and adding a new leaf route only retests one small router instead of the whole tree.
The cost is an extra decision hop on some paths, which is why the top level is the first candidate for graduating to a trained classifier.

The pragmatic senior-sounding synthesis: start with an LLM router because it ships in an hour with no data, log every routing decision, and once traffic reveals the true distribution, graduate the high-volume routes to a trained classifier or rules, keeping the LLM as the fallback for the weird stuff.
And note — the book makes this point — routing isn't only a front-door concern: it can sit mid-chain ("did extraction succeed? if not, branch to the recovery path") or inside a tool-selection step.
Anywhere your workflow needs an if-statement powered by understanding, that's routing.
Framework-wise: LangGraph models this naturally as a state graph — nodes with conditional edges, which is literally a routing diagram in code — while Google's ADK does it by *delegation*: you give a coordinator agent a set of described sub-agents, and the framework's Auto-Flow matches each request to the right one based on those descriptions.

Where it breaks — three failure modes to volunteer.
**Misrouting**: the router sends a refund request to the baggage handler; the specialist, prompted only for baggage, does something confidently useless.
Mitigations: a confidence threshold below which you ask a clarifying question instead of guessing; an explicit `unclear` route — never force the router to pick from only "real" categories; and letting a handler *bounce* a request back when it recognizes a stranger, rather than soldiering on.
**Ambiguous or multi-intent input**: "cancel my flight and also, where's my bag?" is legitimately two categories.
Decide the policy up front: split into two requests, handle the primary and acknowledge the secondary, or ask the user to pick — any is defensible; having no policy is not.
**Category drift**: the router's world was designed in January; by June users ask about things no route covers, and they're all being crammed into `other` or misrouted.
Mitigation: monitor the route distribution over time and review a sample of the `unclear` bucket weekly — the `unclear` pile is literally your product roadmap telling you which new route to build next.

When to use routing: the book's rule of thumb is whenever the agent must choose among multiple distinct workflows, tools, or sub-agents based on the input — triage is the canonical case.
When not: if 95% of traffic is one category, you don't need a router; you need one good pipeline and an escape hatch.
Versus its neighbors: chaining is a fixed sequence, routing is a fork — *choose one path of several*; parallelization is *take several paths at once*; and a router picks between different kinds of work, whereas reflection loops back over the same work to improve it.
Routing plus chaining is the bread-and-butter combo: a router at the front door, a specialist chain behind each door.

## The complete interview answer, spoken

Here's the full spoken answer for: *"Design a customer-support assistant for an airline — bookings, refunds, baggage, flight status, all of it."*

"Let me scope this first.
Channel and latency: is this a live chat where someone's waiting?
I'll assume yes — live chat, so responses within a few seconds, which will push me toward cheap fast routing.
Volume: I'll assume tens of thousands of chats a day — real scale, so cost per request matters.
Action surface: can the assistant actually *do* things — rebook, refund — or only answer questions?
I'll assume it can act on bookings and low-value refunds but anything above a threshold escalates to a human, because money plus autonomy is where these systems get dangerous.
And I'll assume we have existing systems to integrate: a booking API, a refund API, a policy knowledge base, and a human-agent queue.

Simplest thing that could work: one prompt — 'you are a helpful airline assistant' — with every tool attached and the whole policy manual stuffed into context.
For a demo, fine.
At scale it fails predictably: the prompt becomes a junk drawer of conflicting instructions, baggage-policy phrasing bleeds into refund handling, every request pays the token cost of every capability, and I can't test or improve one skill without risking the others.
The inputs are genuinely heterogeneous — that's the signal this is a routing problem.

So: a router at the front door, four specialist handlers behind it, and a human escalation lane.
Here's the whiteboard:

```
                      +-----------------+
   user message --->  |     ROUTER      |
                      | (small LLM      |
                      |  classifier)    |
                      +-----------------+
                        |    |    |    \__________
              booking   | refund  | baggage/policy \  unclear/
                        |    |    |                 \  low-conf
                        v    v    v                  v
                   +------+ +------+ +---------+  +-----------+
                   |Book- | |Refund| | Policy  |  | Clarify or|
                   |ing   | |chain | | Q&A     |  | human     |
                   |chain | |+human| | (RAG)   |  | handoff   |
                   |+tools| | gate | |         |  |           |
                   +------+ +------+ +---------+  +-----------+
                        \      |       /              |
                         v     v      v               v
                          reply to user          human agent
```

The flow: a message arrives, and the router — I'd start with a small fast LLM given a tightly constrained prompt: 'classify into booking, refund, baggage_policy, flight_status, or unclear; output only the label' — makes the call in a few hundred milliseconds.
My orchestrator validates that the output is actually one of the allowed labels — if the model returns anything creative, that's treated as `unclear`, never a crash.
Then the original message, the label, and the customer's context — their identity, their upcoming trips pulled from the booking system — get handed to the specialist.

Each specialist is its own small, boring, testable thing.
The booking handler is a short chain with the booking API as a tool.
The refund handler is a chain with a hard code-level gate: refunds above a threshold require human approval regardless of what the model thinks — that's a guardrail, not a suggestion.
The baggage-and-policy handler is retrieval-based: it looks up the actual policy documents and answers *from* them, so policy answers are grounded in the real text rather than the model's memory.
Flight status is barely AI at all — extract the flight number, call the status API, template the answer; cheap and instant.
And `unclear` is a first-class route, not an error: low router confidence or genuinely weird requests get one clarifying question, and if that doesn't resolve it, a warm handoff to a human with the full conversation attached.

Why LLM routing rather than rules or a trained classifier?
Sequencing, honestly.
Day one, I have no labeled data, so an LLM router ships immediately and handles messy phrasing well.
But I log every decision, and after a month I have tens of thousands of examples — at which point I'd train a small dedicated classifier for the head of the distribution, because at our volume, shaving a few hundred milliseconds and most of the routing cost off every single request is real money and real snappiness.
I'd keep the LLM router as the fallback tier for whatever the classifier isn't confident about, and cheap regex-style rules can pre-empt both for dead-giveaway cases like a message that's just a flight number.
Router as a funnel: rules, then classifier, then LLM — cheapest adequate decider wins.

Failure modes, before you ask.
Misrouting is the big one — a refund question sent to the booking handler.
Three defenses: the confidence threshold routes doubt to clarification instead of a guess; handlers are prompted to recognize out-of-scope requests and bounce them back to the router once — with a loop counter so a request can't ping-pong forever, two bounces and it goes to a human; and I track misroutes explicitly as a metric, measured on a labeled sample every week.
Multi-intent messages — 'cancel my flight and where's my bag' — get a policy: handle the primary intent, explicitly acknowledge the second, offer to do it next; users forgive sequencing, they don't forgive being half-ignored.
Category drift: six months in, users will ask about things my routes don't cover — new products, new policies.
The route distribution dashboard and a weekly review of the `unclear` bucket catch that; when a new cluster shows up in `unclear`, that's my signal to build route number six.
And the platform failures: the router itself times out — after two seconds I skip it and drop to keyword rules plus a generalist prompt, degraded but alive; a downstream API is down — the handler says so honestly and offers the human queue, rather than hallucinating a flight status.

Evaluation.
The lovely thing about routing is that the core decision is just classification, which is crisply measurable: I'd maintain a labeled test set of a thousand-odd real messages and track routing accuracy — overall and per class, because the confusion between specific pairs, like refund-versus-booking, is where the pain concentrates.
I want that north of, say, 97% before I trust automation with money.
Each handler then gets its own eval — resolution rate, grounding accuracy for the policy bot — which routing makes possible in the first place, because each skill is now an independently testable unit.
In production: route distribution over time, per-route escalation rate, end-to-end resolution rate — the fraction of chats resolved with no human — CSAT if we have it, p95 latency per route, and cost per conversation, all on one dashboard, with traces on every conversation so any complaint can be replayed step by step.

Cost.
The router is a few hundred tokens on a small model — a fraction of a cent — and most handlers similarly; the expensive routes are the retrieval-heavy policy answers.
Blended, well under a cent per message, a few cents per conversation — versus several dollars for a human-handled contact, so every percentage point of automated resolution pays for the whole system many times over.
Under a one-week deadline: ship the router plus the two highest-volume routes — flight status and baggage Q&A, which are also the safest — and route *everything else* to humans.
One wrinkle worth naming before I close: conversations have turns, and the router runs on every turn — but not statelessly.
Turn two of a refund conversation shouldn't be re-triaged from scratch; the router sees the active route as context and applies stickiness — stay with the refund handler unless the user has clearly changed subjects — because re-classifying 'yes, that one' with no context is how mid-conversation misroutes happen.
Topic switches are then an explicit, logged event: close out the old route's state, open the new one, and tell the user what's happening — 'I'll come back to the refund after we find your bag.'

That's the beauty of this pattern: the routes you haven't built yet just fall through to people, so you can launch a third of the system and it's still honest."

## Follow-ups they will ask

**"What exactly happens when the router is wrong?"**
"Depends where it's caught.
Best case, the handler notices — it's prompted to check scope — and bounces the request back with a 'not mine' signal; the router re-decides with that exclusion, capped at two bounces before a human takes it.
Worst case nobody notices and the user gets a useless answer — which is why I measure misroute rate on labeled samples rather than assuming silence means success, and why the confusion between specific route pairs drives my prompt and threshold tuning."

**"LLM router, embeddings, rules, or a trained classifier — pick one and defend it."**
"I refuse the premise slightly: it's a lifecycle, not a pick.
LLM router first — zero data needed, ships today, great with messy language.
Its logs become training data; a small trained classifier then takes the high-volume head for speed and cost; trivial rules pre-empt both for unambiguous patterns.
Cheapest adequate decider at each tier, LLM as the safety net.
If forced to run exactly one forever at high volume, I'd take the trained classifier and pay the labeling cost."

**"A message contains two different requests. What does your system do?"**
"Policy, decided in advance: the router flags multi-intent, the system handles the primary — the one with urgency or money attached — and explicitly says 'I see you also asked about X; want me to do that next?'
Splitting into two parallel handler runs is also viable and I'd consider it once the basics are solid, but acknowledged sequencing is simpler and users respond well to it.
The unacceptable option is silently answering half the message."

**"How do you add a new category without breaking the existing ones?"**
"This is routing's best feature.
The new handler gets built and tested in isolation against its own eval set.
Adding it to the router is one new label — I re-run the full routing test set to check the newcomer didn't steal traffic from existing routes, since classification boundaries shift when a class is added.
Then a canary rollout: the new route live for a small slice of traffic, watched, then ramped.
The old handlers' code never changed."

**"Doesn't the router add latency to every single request?"**
"Yes — it's a tax, and I'd size it honestly: a small-model call is a few hundred milliseconds.
I'd claw it back three ways: rules short-circuit the obvious cases for free; a trained classifier eventually makes the common case near-instant; and the router's decision can overlap with fetching the customer's context, since those are independent — a small dose of parallelization inside the routing step itself.
The tax buys specialist quality everywhere downstream; that trade is almost always worth it."

**"Where else besides the front door would you put routing?"**
"Anywhere the workflow needs a decision.
Mid-chain: after extraction, route on whether it succeeded — clean data proceeds, ambiguous data detours to a recovery step, garbage goes to a human.
Tool selection: choosing which of several APIs answers a question is a routing decision.
Even escalation is routing — 'model handles it versus human handles it' is the single most important fork in the whole system, and I want it explicit and measured, not implicit in a prompt."

**"How do you set the confidence threshold for the `unclear` route?"**
"Empirically, from the cost asymmetry of the two mistakes.
Routing when unsure risks a misroute — a confidently wrong answer, which for an airline handling money is expensive; clarifying when actually sure costs one extra user turn — mildly annoying, cheap.
So I'd plot, on my labeled set, misroute rate versus clarification rate at different thresholds, and pick the point where the next bit of safety costs too much friction — for money-touching routes I'd sit conservative, clarifying maybe 10% of the time; for the flight-status route, aggressive, because a wrong guess there is trivially corrected.
Per-route thresholds, in other words — one global number is a smell, because it pretends all mistakes cost the same."

**"Isn't the router a single point of failure? Everything flows through it."**
"Structurally yes — every request crosses that one component, so it deserves the most protective engineering in the system.
Concretely: the router gets the tightest timeout, with a degraded fallback behind it — keyword rules plus a generalist prompt — so router trouble means worse routing, never no service.
Its output is validated against the allowed label set, so a malformed answer can't crash the dispatch logic.
It's the first thing I'd put a canary on when changing prompts or models, because a routing regression damages every route at once.
And it's the best-instrumented component I own — if route distribution shifts suddenly, I want the alert within minutes, because that's either a router bug or the users changed, and both are urgent news."

## How the other scenarios morph

The internal employee-helper question — HR, IT, finance — is the airline answer with the nouns swapped and one twist worth voicing: the domains have different *privacy* postures, so the router's label also selects which systems the handler may touch, and misrouting isn't just a wrong answer, it's potentially an HR question answered with access to finance data — say that out loud and you've turned a triage question into a security answer.
The coding-assistant question — debug, explain, translate — moves the router's evidence from words to *artifacts*: the pasted code's language is detectable by cheap deterministic means, so rules carry more weight, and the intent (fix versus explain) comes from the surrounding message; it's also the cleanest example of the book's point that routing selects *tools*, not just conversation paths.
In both cases the skeleton is untouched: one front door, a labeled fork, specialists behind each label, an honest `unclear` lane, and metrics on the fork itself.

## Say it in one breath

Routing puts a classify-then-dispatch decision at the front of the system: a router — rules, embeddings, a trained classifier, or an LLM — labels each incoming request and sends it to a specialist handler, with an explicit `unclear` route falling back to clarification or a human.
It exists because heterogeneous traffic through one generalist pipeline means mediocrity everywhere, while specialists stay small, testable, and independently improvable.
Watch for misrouting, have a multi-intent policy, review the `unclear` bucket for category drift — and remember the pragmatic lifecycle: LLM router first, graduate the high-volume head to a classifier, rules for the giveaways.
