# Pattern 16: Resource-Aware Optimization — Champagne Answers on a Beer Budget

## The interview scenario

This one arrives dressed as a bill:

- "Our agent's LLM bill hit $80,000 a month — design it to be dramatically cheaper
  without wrecking quality."
- "Users say the assistant is great but slow. Make it fast where it matters, and you
  can't just buy your way out."
- "We're launching the agent to 10x the users next quarter. The unit economics don't
  work. Fix the design."

The tell is any constraint on money, time, or compute: "budget," "latency," "cost per
query," "runs on a phone," "rate limits." Interviewers use this pattern to find out
whether you've ever operated an agent in production, because in production the bill is a
design input, not an afterthought.

## What this pattern is, in plain words

Resource-aware optimization is the discipline of making an agent *spend deliberately*. A
naive agent treats every request identically: biggest model, full context, as many
reasoning steps as it feels like taking. That's like a hospital sending every patient —
sniffles or cardiac arrest — straight to the top surgeon. The results are fine; the
economics are absurd; and the queue for the surgeon wrecks latency for everyone.

The resource-aware agent instead runs triage. It asks, per request: how hard is this,
how much is a good answer worth, and what's the cheapest path to acceptable quality?
Easy factual question — cheap, fast model. Gnarly multi-step reasoning — the expensive
heavyweight, because getting it wrong costs more than the tokens do. The financial-
analyst example from the book captures it: for a quick preliminary read, use the fast
affordable model; for the forecast backing a major investment decision, spend the money
and the minutes on the precise one. Same agent, different spend, chosen on purpose.

The frame that organizes every technique in this space is a **three-way dial between
cost, latency, and quality**. You can generally improve any two at the expense of the
third: cheaper and faster means dumber; smarter and faster means pricier; smarter and
cheaper means slower (smaller models with more retries, batch windows, queues). A senior
answer never claims to win all three; it says *which two this product needs* — a real-
time support chat prioritizes latency and cost and accepts occasional escalation; an
overnight research report prioritizes quality and cost and shrugs at latency. Naming the
dial, and where you're setting it, is half the interview.

And one measurement idea elevates the whole conversation: optimize **cost per successful
task, not cost per request**. A $0.02 request that fails and triggers two retries, an
escalation to the big model, and a human cleanup is more expensive than a $0.15 request
that just works. Cheap requests are not the goal; cheap *outcomes* are. Systems tuned on
per-request cost routinely get more expensive end-to-end as quality collapses — say this
in an interview and you'll sound like you've paid this bill personally.

## How the design actually works

A toolbox of levers, roughly ordered by how often they're the right first move.

**Model routing.** Send easy questions to the cheap fast model, hard ones to the
expensive one. Frontier models often cost tens of times more per token than their small
fast siblings, so if 70% of your traffic is easy, routing is an enormous, almost free
win. The router itself ranges from a dumb heuristic (query length, keyword rules) to a
small classifier, to a cheap LLM that buckets each query — e.g. *simple* → mini model,
*reasoning* → strong model, *needs-current-info* → search-augmented path. The router
must be far cheaper than the savings it unlocks, and it will make mistakes in both
directions: routing hard queries cheap degrades quality (the expensive kind of mistake),
routing easy queries expensive wastes money (the tolerable kind) — so bias the
thresholds accordingly. A *critique agent* — a model pass that grades answer quality —
closes the loop: consistent low grades on the cheap path for some category means the
router's threshold for that category moves. Related trick, same family: hierarchical
splits inside one workflow — the smart model does the *planning*, the cheap model
executes the simple subtasks like lookups and formatting, because drafting a coherent
travel itinerary needs brains but checking a flight price doesn't.

**Caching, twice.** First, *response caching*: many queries repeat ("how do I reset my
password"), so serve the stored answer — cost approximately zero, latency approximately
zero; use semantic matching so paraphrases hit too, and give entries a shelf life so
stale answers expire. Second — the one candidates forget — *prompt caching*, also called
context caching: providers can cache the *prefix* of your prompt (the long system
prompt, tool definitions, standing documents) so on subsequent calls you pay a steeply
discounted rate on those tokens instead of reprocessing them. Agents resend a huge,
mostly-identical preamble on every single step of every loop, so structuring prompts as
*stable prefix first, volatile stuff last* can cut token spend dramatically with zero
quality impact. It's often the highest-ROI change on the whole list because it's
invisible to users.

**Context pruning and summarization.** Input tokens cost money on *every* call, and
agent conversation histories grow without bound — so an agent that naively resends its
whole history gets more expensive with every step. The fix: summarize older turns into a
compact digest, keep recent turns verbatim, drop what's irrelevant, and cap retrieved
content to what's actually needed (summaries instead of full downloads when the question
doesn't need the raw data). Bonus: trimmed context often *improves* quality, because
models reason better without a haystack of stale text in the window.

**Batching.** For anything not interactive — nightly classification jobs, bulk document
processing, eval runs — group requests and use provider batch tiers, which typically
price at deep discounts (often around half) in exchange for relaxed turnaround. Pure
cost-for-latency trade; take it everywhere latency doesn't matter.

**Budgets and step caps.** Agents loop, and loops can run away — a stuck agent happily
burning $40 of tokens re-trying the same failed plan at 3am is a rite of passage. So
enforce hard ceilings: maximum steps per task, maximum tokens or dollars per task, per-
user and global daily budgets, with defined behavior at the ceiling — stop and return
the best partial answer, or escalate to a human — rather than an opaque crash. This is
the circuit breaker of agent design: boring until the day it saves you, and interviewers
who've operated agents *always* ask about it.

**Fallbacks and graceful degradation.** The preferred model will sometimes be down,
overloaded, or rate-limited. A resource-aware system fails *sideways*, not down: an
ordered fallback chain (primary model → secondary provider → smaller model) so service
continues at reduced quality instead of stopping — degraded answers beat error pages.
Model-gateway services (OpenRouter is the name to drop) make this a config line: give
them an ordered model list and they route to the first one that succeeds, and can even
auto-select a cost-appropriate model per prompt.

At most one table per pattern, and this is the one that earns it — the levers at a
glance:

| Lever | Saves | Costs you | Reach for it when |
|---|---|---|---|
| Model routing | 50–90% on routed traffic | Router errors on hard queries | Traffic mixes easy and hard |
| Prompt/context caching | Big cut on input tokens | Prompt restructuring work | Long stable system prompts, agent loops |
| Response caching | ~100% on hits | Staleness risk | Repetitive queries |
| Context pruning | Grows with history length | Possible loss of old detail | Long conversations, long agent runs |
| Batching | Often ~50% | Latency (minutes–hours) | Offline/bulk workloads |
| Step & budget caps | Bounds tail-risk spend | Some tasks cut short | Always — this is a seatbelt |
| Fallback chains | Availability, graceful degradation | Quality dip during failover | Always, for production |

## The complete interview answer, spoken

Spoken end-to-end for "our agent bill hit $80,000 a month — make it cheaper without
wrecking quality."

"First, questions, because you can't optimize a bill you haven't decomposed. Do we have
per-request cost telemetry — do we know where the $80k actually goes, by feature, by
model, by input-versus-output tokens? What's the traffic shape — how much looks
repetitive or simple versus genuinely hard? And what quality bar is contractual — are
there answers we simply cannot get wrong, and do we have an eval suite that would catch
a regression if I start swapping models underneath?"

*(Interviewer: telemetry is thin — one big bill. Support-style traffic, probably lots of
repetition. There's a decent offline eval suite.)*

"The eval suite is the crucial yes — it's my safety net; without it, cost optimization
is just quality roulette with a delay. Thin telemetry means step zero is measurement:
tag every model call with feature, model, token counts, and task ID, and give it a week.
I'll predict what we'll find, because agent bills almost always decompose the same way:
a majority of spend on *input* tokens — agents resend a giant, mostly-identical context
every step of every loop — a large share of traffic that's simple or repeated, and a
scary tail of runaway runs, individual tasks that looped and burned dollars each. Then
I'd attack in three phases, ordered by savings-per-unit-risk. Whiteboard:

```
                        request
                           |
                     [semantic cache] --hit--> cached answer   (~free)
                           | miss
                     [router: cheap LLM classifier]
                      /            |                \
                 simple        reasoning         needs-tools/search
                    |              |                  |
              mini model     strong model      mid model + tools
                    \              |                  /
                     \       [step cap: N steps]     /
                      \      [budget cap: $X/task]  /
                       +----------+----------------+
                                  |
                          [critique agent (async, sampled)]
                                  |               feeds back to
                            answer out            router thresholds

  every call: stable prompt prefix first  -> prompt caching discount
  history:    old turns summarized        -> context pruning
  offline:    bulk jobs -> batch API      -> ~half price
  outage:     model down -> fallback chain (secondary -> smaller model)
  dashboard:  cost per SUCCESSFUL task, by feature, with alerts
```

Phase one — the zero-quality-risk wins, worth doing in week one. Prompt caching:
restructure every prompt so the stable parts — system prompt, tool definitions, standing
context — form an identical prefix, and let the provider cache it; agents are extreme
prefix-repeaters, so if input tokens dominate the bill, this alone can take a serious
bite out of the $80k, and no user can tell the difference because the outputs are byte-
for-byte unchanged. Context pruning: cap history growth by summarizing older turns into
a digest and keeping recent turns verbatim, so cost per conversation stops growing
linearly with its length. Budget caps: hard per-task step and dollar ceilings, with
'return best partial answer and flag it' at the limit — that kills the runaway tail, and
the tail is pure waste, tokens spent producing nothing. And batch anything offline —
nightly jobs, evals — onto the batch tier at roughly half price. I'd conservatively
expect these four to cut 30 to 40% with essentially zero quality exposure.

Phase two — the big structural win, model routing, which does carry quality risk, hence
the eval suite. Today every query hits the frontier model. I'd put a cheap classifier in
front — a small fast model that buckets each query as *simple*, *reasoning*, or *needs-
current-info*, exactly the triage a hospital runs. Simple factual stuff — the bulk of
support traffic — goes to a mini model at a small fraction of the cost per token.
Genuinely hard reasoning keeps the frontier model; that's not where we save, and
shouldn't be. The needs-current-info bucket goes to a mid-tier model with search or
retrieval attached, because fresh facts beat raw model IQ for those. The router costs a
fraction of a cent per query and unlocks order-of-magnitude savings on the majority of
traffic.

The risk is misrouting, and the two directions aren't symmetric: sending an easy query
to the expensive model wastes pennies; sending a hard query to the cheap model produces
a bad answer, and bad answers have downstream costs — retries, escalations, churn — that
dwarf token prices. So I'd bias thresholds toward over-routing to the strong model, and
start with the router in shadow mode: for a week it classifies but doesn't route, we run
both models on a sample, and the eval suite plus a critique agent — a model pass that
grades answers — measures where the cheap path actually holds up. Only categories that
prove out get switched. After launch, the critique agent keeps grading a sample of
production answers asynchronously; if the cheap path's grades sag for some category,
that category's threshold moves back. The router is a learning system, not a config
file.

On top: a semantic response cache in front of everything, because support traffic
repeats heavily. Paraphrase-tolerant matching, aggressive TTLs — a shelf life on entries
— so policy changes don't serve stale answers, and instant invalidation hooks for the
docs team. Depending on repetition, that's another meaningful slice served at
effectively zero cost and zero latency, which also *improves* the user experience — a
reminder that cost and latency often improve together; the three-way dial with quality
is cost-latency-quality, and here I'm holding quality fixed and winning the other two.

Phase three — resilience, which is secretly also cost. Fallback chains: when the primary
model is overloaded or rate-limited, fail sideways to a secondary provider, then to a
smaller model, rather than failing down to an error page — graceful degradation. A
model-gateway layer makes this configuration rather than code, and having second sources
has a way of helping your pricing conversations too.

Now the measurement philosophy that makes this durable, and it's the most important
thing I'll say: the dashboard metric is **cost per successful task, not cost per
request**. If I cut per-request cost 60% but the cheap model fails more — triggering
retries, escalations to the big model, and human cleanup — end-to-end cost can go *up*
while my vanity metric goes down. So we define success per feature — issue resolved, no
escalation, positive rating — and track dollars per *success*, segmented by route. That
metric also arbitrates the dial honestly: if the mini model is 10x cheaper per request
but only slightly less successful, it wins; if its failures are expensive downstream,
the frontier model was the cheap option all along and the numbers will say so.

Monitoring and guardrails, concretely: real-time spend dashboards by feature and model
with anomaly alerts — a runaway loop should page someone within minutes, not appear as a
surprise line item at month-end; router-distribution drift alerts, because if the
'simple' bucket quietly grows from 60% to 85%, either the traffic changed or the router
is misclassifying, and quality is about to slip; weekly eval regression runs pinned to
every routing or prompt change; and the critique-agent quality scores per route,
trended.

Rough arithmetic on the outcome: phase one takes the \$80k to roughly \$50k with no
quality risk. Routing plus response caching plausibly takes it near \$25–30k if the
traffic mix is as support-like as described, with quality protected by shadow rollout,
eval gates, and the critique loop. The remaining spend concentrates exactly where it
should: on the hard queries where the expensive model genuinely earns its price. And
latency improves as a side effect for most traffic, since most traffic now hits a cache
or a small fast model.

Summary: measure first, then harvest the free wins — prompt caching, context pruning,
budget caps, batching — then restructure with routing plus caching behind an eval safety
net and a critique feedback loop, keep fallback chains so failures degrade gracefully
instead of catastrophically, and steer the whole thing by cost per successful task,
because cheap requests that fail are the most expensive requests you can buy."

## Follow-ups they will ask

**"How do you know the router is routing correctly, and what if it's wrong?"** Shadow-
mode launch (classify but don't switch; compare both paths offline), then per-category
cutover gated on evals. In production: a critique agent grades sampled answers per
route; sagging grades on the cheap path move that category's threshold back. Asymmetric-
cost point: over-route to the strong model by default, because a wasted penny beats a
failed task. Also monitor the router's *distribution* for drift — traffic changes
silently.

**"Isn't the router itself an extra cost and an extra failure point?"** Yes — own it.
The router must cost a small fraction of what it saves (a tiny classifier or mini-model
call versus frontier-model tokens saved: easily hundred-fold return). Failure handling:
if the router errors or times out, default-route everything to the strong model — fail
expensive-but-correct, never cheap-and-wrong. And keep the router simple enough to be
boring; a router that needs its own router has gone wrong.

**"Where does quality actually degrade first when you do all this, and how would you
catch it?"** Likeliest suspects in order: hard queries misrouted cheap (catch with
critique sampling and escalation-rate monitoring), stale cache hits after content
changes (catch with TTLs, invalidation hooks, and freshness audits), over-aggressive
context summarization losing a detail from early in a long conversation (catch with
long-conversation evals specifically), and tasks truncated by step caps (catch by
tracking cap-hit rate and reviewing a sample). The meta-answer: every optimization ships
with the metric that would expose it.

**"Explain prompt caching versus response caching — they sound the same."** Response
caching stores the *final answer* to a repeated question and skips the model entirely —
full cost and latency win, but only on genuine repeats, with staleness risk. Prompt
(context) caching stores the processed *prefix* of the input — the long stable system
prompt and tool definitions — so the model call still happens and generates fresh
output, but the repeated preamble tokens are billed at a deep discount and processed
faster. Response caching helps repetitive *traffic*; prompt caching helps repetitive
*prompt structure*, which for agents is essentially all of them.

**"Latency, cost, quality — how do you decide where to sit on that dial?"** Product-by-
product, not globally: name the binding constraint. Interactive support chat: latency
and cost, accept occasional escalation as the quality valve. Compliance answers: quality
is non-negotiable, spend money, hide latency with streaming and progress UX. Overnight
analysis: quality and cost, latency is free — batch it. The senior move is stating
explicitly which two you're buying and what mechanism absorbs the third (escalation
paths, streaming, queues).

**"What stops an agent loop from burning $500 at 3am?"** Layered circuit breakers: per-
task step caps and token/dollar ceilings with defined stop behavior (return best partial
result, flag for review), per-user and global daily budgets, no-progress detection (same
tool called with same arguments repeatedly means halt, not retry), and real-time spend
anomaly alerts that page a human. Also idempotency on retries after provider errors, so
failure-retry storms don't multiply spend. The theme: every loop in the system has a
ceiling, and every ceiling has a defined, graceful behavior.

## Say it in one breath

"Resource-aware optimization means the agent spends deliberately: route easy questions
to the cheap fast model and hard ones to the expensive one, cache both answers and
prompt prefixes, prune and summarize context so history stops inflating every call,
batch whatever isn't urgent, cap steps and dollars so no run can quietly burn the
budget, fall back sideways to backup models instead of failing outright — and steer it
all by cost per successful task, not per request, because a cheap request that fails is
the most expensive kind there is."
