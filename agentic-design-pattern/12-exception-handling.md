# Pattern 12: Exception Handling and Recovery — Failing Without Falling Over

## The interview scenario

This one is often the most concrete question in the loop:

- "Your agent calls half a dozen flaky third-party APIs — payments, shipping, a CRM. Any
  of them can time out, rate-limit you, or return garbage. Design the agent to survive."
- "Our workflow agent sends emails, updates records, and creates tickets. Yesterday it
  crashed halfway through a run — some actions done, some not, nobody sure which. What
  should we have built?"
- "The support chatbot falls over whenever the customer database has a blip, and users see
  a raw stack trace. Fix the design, not the bug."

The signal in all three: the world is unreliable, the agent acts on that world, and the
interviewer wants systematic resilience — not a try/catch bolted on at the end.

## What this pattern is, in plain words

Ordinary software fails too, but agents raise the stakes for one specific reason worth
stating in your first breath: agents act. A crashed web page re-renders; an agent that
crashed halfway through "refund the customer and email them" may have moved real money and
not sent the mail, or sent the mail about a refund that never happened. Failures don't
just interrupt agents — they leave side effects behind, half-finished changes to the real
world. Add that agents chain many fallible steps (every tool call is a chance to fail, and
a ten-step task multiplies those chances) and that a model can react to an error
unpredictably — retrying something destructive, or fabricating a success — and you see why
this pattern is a design discipline rather than error-handling hygiene.

The pattern says: assume failure is normal, and give the agent three organized layers of
response. Detect problems quickly and precisely. Handle them in the moment — retry, switch
to a backup, degrade politely. Recover afterwards — undo what shouldn't stand, fix the
approach, or hand off to a human cleanly.

The analogy I like is a good line cook mid-dinner-rush. The fryer dies. A brittle cook
freezes and the kitchen stops. A good one notices in seconds (detection), moves the dish
to the oven (fallback), 86's the one item that truly needs the fryer (graceful degradation
— reduced menu, kitchen still serving), tells the manager (notification), and comps the
table that already ordered it (compensation — undoing the commitment already made).
Nothing about the fryer improved; the system around it absorbed the failure.

## How the design actually works

Walk the three layers in order — detect, handle, recover — then the failure modes of the
machinery itself.

**Detection.** You can't handle what you haven't noticed, and agents fail in both loud and
quiet ways. Loud: explicit API error codes — a 404 meaning the thing you asked for doesn't
exist, a 500 meaning the service itself broke — and thrown exceptions. Quiet, and more
dangerous: a call that "succeeds" but returns malformed or empty data, a response that
doesn't match the expected structure, or model output that's incoherent. So detection
means validating every tool result against expectations — schema checks, sanity ranges,
"did this actually return items" — not just catching errors. Add timeouts: a timeout is a
self-imposed deadline — if the service hasn't answered in, say, ten seconds, stop waiting
and treat it as failed, because an agent hanging forever on a dead service is itself an
outage. And for slow-burn problems, an external watchdog — a monitor outside the agent,
possibly another model, watching for anomalies the agent can't see about itself.

Crucially for agents, classify what you detect, because the right response differs.
Transient errors — timeouts, rate limits, momentary outages — will likely succeed on
retry. Permanent errors — bad credentials, nonexistent resource, malformed request — will
fail identically forever, and retrying them is pure waste. Semantic errors — the call
succeeded but the meaning is wrong: "insufficient funds," "market closed" — need the agent
to change its plan, not the plumbing to try harder. A trading bot hammering the same
invalid order because it treated "insufficient funds" as transient is the canonical
cautionary tale.

**Handling.** Six tools, each with a plain definition. *Logging:* record every failure
with full context — which tool, what arguments, what came back — because you'll debug
tonight what you logged this afternoon, and the log is also what a human reads at
escalation. *Retries with exponential backoff:* for transient errors, try again — but wait
a bit longer each time you retry: one second, then two, then four, and add jitter, a bit
of randomness in the delays, so a hundred agents that failed together don't all retry in
the same instant and knock the recovering service down again. Cap attempts; three-ish is
typical. The precondition for retrying anything is *idempotency* — a fancy word for "safe
to do twice": checking a balance is idempotent; sending an email is not, and retrying a
maybe-sent email is how customers get five copies. For unsafe operations you make them
safe with an idempotency key — a unique ID on the request so the far side can recognize a
duplicate and act once — or you don't auto-retry them at all. *Timeouts* we covered —
every external call gets one, no exceptions. *Fallbacks:* an alternative path when the
primary fails — a backup provider, a cache, a cheaper method that's good enough: precise
geolocation fails, fall back to city-level; live inventory is down, serve the hourly
snapshot labeled as such. *Graceful degradation:* when full function isn't possible,
deliver reduced-but-honest service instead of an error page — the chatbot that can't reach
the account database still answers general questions and says plainly, "account lookups
are temporarily down, here's what I can do meanwhile." Partial value plus honesty beats a
stack trace every time. *Notification:* some failures need a human now; the design
decision is choosing which, and making the alert carry the context to act on.

**Recovery.** After the incident, restore a stable state. *State rollback and
compensation:* the agent-specific crown jewel. Database transactions can be rolled back
natively, but an agent's actions cross systems — an email, a CRM update, a payment — and
there's no cross-system undo button. The pattern is compensation: for every consequential
action, define a compensating action that reverses its effect — refund the charge, send
the correction email, delete the created ticket — and keep an action ledger, a durable
record of every side-effectful thing the agent did, so on failure you can walk the ledger
backwards and compensate in reverse order. (Distributed-systems folks call this a saga;
you don't need the term, you need the ledger.) *Diagnosis and self-correction:* here's
where this pattern shakes hands with reflection — feed the failure back to the model
("your query returned zero rows; the date format was likely wrong") and let it attempt a
refined approach; a failed attempt plus analysis frequently produces a successful second
attempt. But bound it: a repair loop without a cap is a new way to loop forever.
*Escalation:* the designed exit — when retries, fallbacks, and self-correction are
exhausted, stop and hand a human a structured package: goal, ledger of actions taken,
failures encountered, current state. An agent that fails into a clean, actionable handoff
is trustworthy; one that fails into mystery is not deployable.

One more handling tool deserves its own paragraph because interviewers love it: the
*circuit breaker*. Borrowed from electrical panels: stop calling a service that keeps
failing, and check back later. Concretely, a wrapper counts recent failures per
dependency; past a threshold the breaker "opens" and calls fail instantly without touching
the service — no more 30-second timeouts in a loop, no more retry traffic pounding a
service that's already drowning. After a cooldown it goes "half-open": one probe call is
allowed through; success closes the breaker and traffic resumes, failure re-opens it. For
agents there's a bonus benefit: an open breaker is knowable — the agent can be told
"shipping API is down, breaker open, use the fallback" at planning time and route around
the outage instead of discovering it mid-task, five steps deep.

**Failure modes of the failure handling** — naming these is senior-signal. Retrying
non-idempotent actions: the double-charged customer; cure is idempotency keys and a
no-auto-retry rule for unsafe verbs. Retry storms: synchronized clients re-flooding a
recovering service; cure is jitter plus breakers. Fallbacks that silently lie: stale cache
served as fresh; cure is labeling degraded data as degraded, to the model and the user
both. Compensation that itself fails: the refund call errors out; cure is treating
compensations as retryable jobs on a queue with escalation on exhaustion, not
fire-and-forget. Masking real bugs: aggressive auto-recovery hiding a permanent defect
that then fires on every request forever; cure is alerting on retry and breaker-trip
rates, not just final failures.

**When to use and not:** any agent in production touching external systems — which is
nearly every agent worth building — needs at minimum timeouts, classified errors, capped
retries, and honest degradation. Full ledger-and-compensation machinery is proportional to
side effects: essential where money moves and records change, overkill for a read-only
research agent, where a timeout, a retry, and a clear apology may be the whole story.
**Neighbors:** goal monitoring (Pattern 11) notices strategy-level failure — no progress
toward the objective — while exception handling catches operation-level failure — this
call, right now, broke; monitoring might conclude "abandon the approach" while exception
handling concludes "retry with backoff." Reflection is the repair brain this pattern
invokes for semantic errors. And robust tool design (good APIs, clear errors) is what
makes all of this tractable — a tool that fails vaguely can't be handled precisely.

## The complete interview answer, spoken

Spoken answer to "your agent calls flaky third-party APIs and takes real actions — design
it to survive."

"Scoping questions first. Which actions have side effects? — assume the payment call and
the customer email are consequential; CRM lookups and shipping quotes are read-only. Do
the flaky vendors give us structured errors and idempotency support? — assume decent error
codes, and the payment provider accepts idempotency keys; the shipping API is the true
wild card. Is a human available for escalation? — yes, an ops queue with same-hour
response. And roughly what reliability are we aiming for? — the workflow should either
complete fully, or fail into a state a human can resolve in five minutes. That last
sentence is really the spec: no mystery states.

My design wraps every external dependency in a resilience layer the model never bypasses,
keeps a durable ledger of consequential actions with compensations, and defines a strict
escalation contract.

First, the tool wrapper layer. The model never calls a vendor API raw; every tool call
goes through a wrapper that enforces, uniformly: a timeout per dependency — a few seconds
for lookups, longer for payments — because an agent hanging on a dead service is itself an
outage; response validation, checking the result against an expected schema so a
200-with-garbage is detected as the failure it is, since the quiet failures are the
dangerous ones; and error classification into three bins — transient, like timeouts and
rate limits; permanent, like bad credentials or a nonexistent resource; and semantic, like
insufficient funds, where the plumbing worked but the meaning demands a plan change.
Classification drives everything downstream, and it's the step naive designs skip — which
is how you get a bot hammering an invalid request forever because it treated 'insufficient
funds' as a network blip.

Second, per-class policy. Transient: retry with exponential backoff and jitter — wait one
second, then two, then four, with randomness so a fleet of agents doesn't re-flood the
recovering service in lockstep — capped at three attempts. But an automatic retry is only
allowed on idempotent calls, the ones safe to repeat. Reads qualify. The payment doesn't —
except we make it: every payment request carries an idempotency key, a unique ID letting
the provider detect a duplicate and charge once, so a timeout on a payment (where we
genuinely can't know if it landed) is safely retryable. The email has no such support, so
it's never auto-retried; on ambiguity we check sent-status via a lookup or route to a
human. Permanent errors: zero retries — log, and move straight to fallback or escalation.
Semantic errors: surface the meaning to the model in plain language — 'insufficient funds
on the customer's stored card' — and let it replan: try the backup payment method, or
pause the workflow and ask the customer. That's reflection doing recovery work: failure
plus analysis in, revised approach out — bounded to one or two repair attempts so the
repair loop can't itself become the runaway.

Third, circuit breakers per dependency. A wrapper-level counter tracks recent failures per
vendor; past threshold, the breaker opens — meaning stop calling a service that keeps
failing — and calls to it fail instantly instead of burning a timeout apiece. After a
cooldown, it half-opens: one probe goes through; success closes it, failure re-opens. Two
payoffs: we stop kicking a service that's already down, and — the agent-specific one —
breaker state feeds the agent's context at planning time, so it knows 'shipping API
unavailable' before step one and routes around it, choosing the fallback carrier quote or
telling the user shipping estimates are delayed, rather than discovering the outage
mid-workflow.

Fourth — the heart, given side effects — the action ledger and compensation. Before any
consequential action, the agent writes an intent record to durable storage: about to
charge X on order Y, key Z. After, it records the outcome. So the ledger always knows each
action's status: intended, confirmed, ambiguous, failed. Every consequential action
registers a compensating action at design time — its undo: charge → refund; confirmation
email → correction email; ticket created → ticket closed with note. When a workflow dies
mid-flight — our 'crashed halfway, nobody knows what happened' scenario — recovery is
mechanical, not forensic: read the ledger, resolve ambiguous entries by querying providers
with the idempotency keys, then either resume forward from the last confirmed step or
compensate backwards in reverse order to a clean state. Policy choice: forward-first if
the customer's intent was clear, rollback when in doubt. And compensations get the same
resilience treatment as actions — they're queued, retryable jobs, because a refund call
can flake too; a compensation that exhausts retries escalates at top priority.

Fifth, degradation and escalation. Degradation ladder per capability: full service;
reduced service, honestly labeled — cached shipping rates marked as estimates, general
answers while account lookups are down — because partial value with honesty beats an error
page; then pause-and-notify. Escalation is a designed artifact, not a stack trace: goal,
ledger with statuses, errors encountered with classifications, current breaker states, and
a suggested next action. Target: the five-minute human resolution we specced. Every
failure also logs to structured telemetry, and the dashboards alert on rates, not just
outcomes — retry rate and breaker-trip rate per vendor are leading indicators; a retry
rate quietly climbing all week is a vendor degrading before it's an incident. That's also
how auto-recovery avoids masking real bugs: a permanent error being 'handled' a thousand
times a day is a defect, and rate alerts surface it.

The whiteboard:

```
 [Agent/LLM] -- plan, replan on semantic errors
      |                     ^
      v                     | errors in plain language,
 [Tool wrapper layer]       | breaker states at planning
   timeout | validate | classify
      |         |         |
   transient permanent semantic
      |         |         |
   retry w/   no retry   surface to
   backoff    fallback/  model -> replan
   +jitter    escalate
      |
 [Circuit breaker per vendor]
      |
   Vendor APIs (payments, shipping, CRM, email)

 [Action ledger] intent -> confirm  --> resume forward
        (on crash: reconcile)       --> or compensate backward
 [Escalation] structured handoff -> ops queue
```

Cost and tradeoffs: retries and probes add modest spend — bounded by the caps and
breakers, which exist precisely to bound it. The ledger adds a write before and after each
consequential action; trivial next to a payment call, and it's the difference between
five-minute recovery and an afternoon of forensic spreadsheet-diffing. The real cost is
engineering time on compensations, so I'd spend it proportionally: full
intent/confirm/compensate treatment for the two consequential actions, lightweight
retry-and-fallback for the read-only calls. Testing: failure paths that are never
exercised don't work when needed, so fault injection in staging — a chaos proxy randomly
returning timeouts, 500s, and garbage from fake vendors — and the test suite asserts the
interesting things: duplicate suppression via idempotency keys, ledger-driven recovery
from a kill at every step of the workflow, breakers opening and closing on schedule."

## Follow-ups they will ask

**"When do you retry and when not?"** Two gates. Gate one, classification: transient
errors — timeouts, rate limits, momentary outages — are retryable; permanent errors — bad
auth, missing resource — never are, identical failure guaranteed; semantic errors —
insufficient funds — need a plan change, not a retry. Gate two, idempotency: auto-retry
only what's safe to repeat, or what's been made safe with an idempotency key so the far
side deduplicates. Then backoff with jitter and a hard cap, so retries stay a courtesy
rather than a siege.

**"Explain a circuit breaker like I'm not a distributed-systems person."** It's the
electrical panel idea: a wire that keeps overheating gets its circuit cut rather than
letting the house burn. Per flaky service, count recent failures; too many, and the
breaker opens — stop calling that service entirely, fail fast — sparing you the timeouts
and sparing the drowning service your traffic. After a cooldown, let one probe call
through: works, resume; fails, wait again. For agents, the extra win is telling the model
which breakers are open before it plans, so it routes around the outage instead of hitting
it mid-task.

**"The agent already sent the wrong email — how do you 'undo' that?"** You can't unsend;
that's exactly why compensation is a design-time obligation. Every consequential action
registers its best-available reversal up front — for email, a prompt correction message;
for a charge, a refund; for a record, restore-from-ledger. The action ledger makes it
systematic: on failure, walk the completed actions backwards and run each compensation as
a retryable job. And for the truly irreversible-and-costly — large payments, external
publication — the compensation-doesn't-really-exist realization argues for a confirmation
gate before the action instead: human approval, because prevention is the only clean undo.

**"How does the model itself participate in error handling?"** The wrapper handles
mechanics — timeouts, retries, breakers — below the model, deterministically; you don't
want a probabilistic system improvising backoff. The model handles meaning: semantic
failures are translated into plain-language context — 'the query returned zero rows; the
date range may be wrong' — and the model replans, which is reflection applied to recovery.
The boundary rule: plumbing decisions in code, plan decisions in the model, and the
model's repair attempts are capped like any other loop.

**"How do you test any of this?"** Fault injection, because failure paths rot if
unexercised. A chaos proxy between agent and (fake) vendors injects timeouts, 500s, rate
limits, and schema-garbage on demand; the suite kills the workflow at every step and
asserts ledger-driven recovery lands in a clean state; sends duplicate payment requests
and asserts single-charge via idempotency keys; and drives a vendor's failure rate up and
down to watch breakers open, half-open, and close. In staging, run scheduled chaos
continuously — the failure handling should be the most-tested code in the system, since it
runs precisely when everything else is going wrong.

**"Why do agents need all this more than normal software does?"** Three compounding
reasons. Agents act — failures leave real-world side effects, so recovery must include
undoing, not just restarting. Agents chain — a ten-step task multiplies per-call failure
odds, so 'rare' failures become routine at the task level. And agents improvise — an
unhandled error surfaced raw to a model can trigger unpredictable behavior, from
destructive retries to fabricated success; structured handling turns failures into
information the model can reason about safely.

## Say it in one breath

Exception Handling and Recovery treats failure as normal: detect it precisely — timeouts,
validation of every result, and classification into transient, permanent, and semantic;
handle it in the moment — retries with exponential backoff and jitter for transient errors
on idempotent calls only, fallbacks, honest graceful degradation, and circuit breakers
that stop calling a service that keeps failing and probe it later; recover afterwards — an
action ledger with compensating undo for every consequential step, bounded model-driven
replanning on semantic errors, and escalation as a structured handoff rather than a stack
trace. Agents need this more than ordinary software because they act — their failures
leave side effects in the real world, and surviving that is a design discipline, not a
try/catch.
