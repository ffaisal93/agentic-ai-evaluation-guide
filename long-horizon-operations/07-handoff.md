# Handoff: passing the baton without dropping it

## Seven in the morning, twelve patients

Go stand in a hospital ward at shift change.
The night nurse has spent twelve hours with these twelve patients, and almost everything she knows about them lives in her head.
Who's frightened, whose IV keeps occluding, which family member actually answers the phone, and which doctor muttered "keep an eye on that potassium" in a corridor at three in the morning and then went home.
She has about ninety seconds per patient to move all of that into the day nurse's head.
She cannot recite twelve hours, so she compresses, and every compression throws something away.
The thing she throws away might be the potassium.

That's a handoff, and the shape of the problem is identical whether the two parties are nurses or software agents.
**A handoff is a compression problem with stakes.**
You have to transfer everything the next party needs and nothing they don't, and the cruel part is that whatever you dropped is invisible at the moment you drop it.
Nobody notices a missing fact during the handover; they notice it four hours later, when someone redoes work that was already finished, or breaks something that was quietly correct, or burns an hour rediscovering that the staging credentials expired.

Medicine took this seriously because the failure rate of "just tell the next person what's going on" turned out to be measurable in harm.
A multi-site study in the *New England Journal of Medicine* in 2014 rolled out a structured handoff protocol called I-PASS — illness severity, patient summary, action list, situation awareness and contingency planning, and synthesis by the receiver — across nine hospitals and more than ten thousand admissions.
Medical errors dropped 23%, and preventable adverse events dropped 30%.
Nobody got smarter and nobody got more staff; they just stopped improvising the handover and gave it a shape.
And that last letter is the one software people always skip, so hold onto it: **synthesis by the receiver** means the person taking over reads the summary back, so the handoff isn't complete when the sender stops talking, it's complete when the receiver demonstrates they got it.

Software mostly hasn't done any of this, because until very recently the only handoffs in software happened between humans at standup.
Now you have agents delegating to agents, agents escalating to humans, humans handing work back to agents, and agents picking up their own work tomorrow in a brand new context window.
Four kinds of shift change, most of them running unsupervised at three in the morning, and most of them with no structure at all.

## The four handoffs

They look like one thing and they fail like four, so name them separately.

### Agent to agent

This is specialist delegation: a general research agent works out that the real question is about database performance, and hands the job to a database agent.
The OpenAI Agents SDK is worth looking at here, not because it's the only way but because it makes the mechanics unusually visible.
A handoff there is just a tool call — give an agent a handoff to an agent named "Refund Agent" and the model sees a tool called `transfer_to_refund_agent`, which it can invoke like any other.

And here's the default that matters more than anything else in this chapter: when the handoff fires, in the SDK's own words, "it's as though the new agent takes over the conversation, and gets to see the entire previous conversation history."
Everything — every tool result, every dead end, every stack trace, every wrong turn the first agent took before it found the answer.
That default is a defensible engineering choice — losing information is worse than carrying it — but it's the wrong shape for a long run, and the SDK hands you the escape hatch in the same breath.
You can pass an `input_filter`, which receives a `HandoffInputData` object holding the history from before the run, the items generated before this agent's turn, and the items from the current turn, and returns a trimmed version — a framework quietly telling you that *you* decide what crosses the boundary.

The other half of agent-to-agent is discovery, and that's where Google's A2A protocol comes in — Agent2Agent, donated by Google Cloud to the Linux Foundation in June 2025, which is when it stopped being one company's idea and became a standard.
Its core object is an **Agent Card**: a JSON document an agent publishes describing, per the spec, "its identity, capabilities, skills, service endpoint, and authentication requirements."
Think of it as a business card that's machine-readable, so that before you hand work to a stranger you can read what they claim to do and how to talk to them.
A2A also carries two identifiers that matter later: a `taskId` for one unit of work, and a `contextId`, defined as "an identifier that logically groups multiple related Task and Message objects, providing continuity across a series of interactions."
That second one is the thread that survives the hop.

### Agent to human

This is escalation, approval, or giving up well, and it's the handoff most teams treat as an error path rather than a product.
The agent has hit something it cannot or should not decide alone — a refund over the limit, an ambiguous requirement, a credential that doesn't work, a genuine dead end — and control has to move to a person.
The failure here isn't usually that the agent escalates too little; it's that it escalates badly, and that gets a whole section later, because a bad escalation does long-term damage that a missing one doesn't.

### Human back to agent

The person answers, and now the agent has to resume with the new instruction folded in.
LangGraph's `interrupt` is the cleanest illustration in current tooling: you call `interrupt()` inside a node, and "LangGraph saves the current graph state and waits for you to resume execution with input," then the human replies with `Command(resume=...)`, whose value "becomes the return value of the `interrupt` call."

Two details in there are worth more than the API.
First, you need a checkpointer for any of it to work — "to use `interrupt`, you need a checkpointer to persist the graph state" — which is the previous chapter's machinery showing up as this chapter's foundation, because a pause you can't restore from isn't a pause, it's a crash.
Second, and this one bites: "the runtime restarts the entire node from the beginning — it does not resume from the exact line where `interrupt` was called."
So anything your node did before asking the human happens *again* after they answer, and if that anything was sending an email, the human's approval just sent a second one.
Which is the idempotency conversation from the checkpoint chapter, arriving through a completely different door.

### Session to session

Same agent, tomorrow morning, or five minutes from now after a context reset — the one people don't file under "handoff" at all, and the most common of the four.

Anthropic's engineering writeup on long-running agents frames it exactly right: "Each new session begins with no memory of what came before," which they compare to "engineers working in shifts, where each new engineer arrives with no memory of what happened."
Crucially, they note that compaction — automatically summarising the conversation to free up room — "isn't sufficient," because "it doesn't always pass perfectly clear instructions to the next agent."
Their fix was a progress file, a `claude-progress.txt` logging what agents have done, paired with git history, because "the key insight here was finding a way for agents to quickly understand the state of work when starting with a fresh context window."

Now connect this back to chapter two.
Context drift said your window fills with debris until the goal is a rounding error, and that the fix is eventually a clean window — but a clean window is only useful if something survives the cleaning.
So: **the handoff is the cure for drift.**
"Just start a fresh session" is terrible advice on its own, because it throws away everything you learned.
"Start a fresh session *with a good packet*" is the actual technique, and the packet is what makes the reset survivable rather than merely clean.
Those two chapters are two halves of one operation: drift tells you when to cut, handoff tells you what to carry across the cut.

## The handoff packet

Stop thinking of a handoff as a message and start thinking of it as an **artifact** — a designed object with required fields, built deliberately, validated before it's sent.
Seven things go in it.

**The original goal, verbatim.**
Not summarised, not "improved," not adapted to the receiver: the exact bytes the human typed at the start.

**What's been done and verified.**
Not what the agent claims it did, but what's been checked against the world, with the evidence attached — chapter five earned this distinction, and a handoff is where the difference between a claim and a fact starts costing money.

**What's been tried and failed, and why.**
This is the field everyone omits and it may be the most valuable one in the packet.
Successes tell the receiver where you got to; failures tell them where *not to go*, and without them they will cheerfully spend their budget walking the same three dead ends you already walked.
The "why" is load-bearing — "tried caching, didn't work" is nearly useless, while "tried caching, checkout read its own write and got stale data because replica lag peaks at four seconds" prevents an entire family of retries.

**Current state, and where it lives.**
Branch name, file path, bucket key, ticket number: pointers, not payloads — say where the benchmark output is, don't paste forty kilobytes of it.

**Open questions and blockers.** What you don't know, and what's stopping you.

**Budget consumed and remaining.**
Money, tokens, wall clock, steps — skip this and every handoff silently resets the allowance, so a task that bounces between four agents spends four budgets.

**An explicit next-step recommendation.**
The sender has more context about this task than anyone else ever will, and wasting that by handing over a neutral pile of facts is a strange kind of politeness, so say what you'd do next.

### Good packet, bad packet

Same run, same moment, two handovers, and the bad one is what you get by default:

> Hey, I looked at the orders endpoint performance issue.
> I tried a few things and made some progress — added an index which helped a bit.
> Still not where we want it.
> Can you take a look at making it faster? Everything's on my branch.

Read that as the receiver: which branch, helped a bit from what to what, what's the target, what were the "few things," did any of them fail for a reason you're about to rediscover, is there a constraint you're about to violate, and how much budget is left.
Every one of those costs a round trip, and half of them won't get asked at all — the receiver will just guess, and guessing is how the response schema gets changed by an agent that never knew it wasn't allowed to.

The good one:

> **goal** (verbatim): Cut p95 latency on GET /api/orders below 400ms without changing the response schema.
> **verified**: p95 is 1180ms on prod (grafana 2026-08-05T14:02Z); N+1 in order_items is 61% of time (pg_stat_statements); an index alone gets p95 to 940ms (staging, 200 runs).
> **failed**: batching item fetch with an IN clause — flattened nested items, violates the schema constraint. Read-replica routing — stale reads in checkout, replica lag peaks at 4s.
> **state**: branch `perf/orders-n1`, benchmark at `s3://runs/cid-7f31a9/bench.json`.
> **open**: is a 30s cache TTL acceptable to the orders team? (asked, no reply)
> **budget**: \$4.10 spent, \$7.90 remaining.
> **next**: try a materialised view refreshed on write. Do not touch the serializer.

That's shorter than most agent turns and it's a complete transfer, and notice what the *failed* section is doing: it isn't an apology, it's the highest-density information in the packet, because it prunes the receiver's search space before they spend a cent.

## The five ways handoffs fail

**Lossy handoff** is the receiver not having a fact the sender had, and not knowing it's missing.
The classic version is a constraint: the sender knew the response schema was frozen because a human said so at turn three, the packet listed accomplishments and next steps and never mentioned it, and the receiver — competent, unblocked, confident — changes the schema until a mobile client somewhere starts throwing parse errors.
The tell is work that gets *redone* or *undone* rather than work that gets stuck: stuck is visible, while redone looks like progress right up until it isn't.

**Paraphrase drift** is the telephone game, and it scales worst of all of them.
Every hop, the goal gets restated in the sender's own words — slightly, helpfully.
"Cut p95 on GET /api/orders below 400ms without changing the response schema" becomes "improve orders endpoint latency," becomes "make orders faster," becomes "optimise the orders code path."
By hop four the constraint is gone, the endpoint is gone, and the number is gone — nobody lied, each restatement was reasonable, and the drift lives entirely in the composition.
This is worse with language models than with people, because paraphrasing is what they're *good* at — a model handed a goal and asked to pass it along will produce a fluent, well-organised, subtly different goal, every single time.
So the fix is structural rather than behavioural: don't ask anyone to restate the goal, carry it as an immutable field byte-for-byte, and hash it so you can prove it didn't change.

**Responsibility diffusion** is three agents touching a task while each believes another one owns the final answer.
A hands to B for the database part, B does its bit and hands back or sideways or to C, and nobody re-checks the original goal against the finished state because each agent verified only its own slice.
The output is confidently wrong and structurally unowned.
The fix is an explicit owner field on every packet plus the I-PASS rule — the handoff isn't done when the sender sends, it's done when the receiver acknowledges and restates the *acceptance criteria* they're now on the hook for.

**Context dumping** is the lazy inverse of the lossy handoff, and it feels responsible, which is what makes it dangerous.
Instead of choosing what matters you paste the entire raw history and let the receiver sort it out, which transfers nothing and merely relocates the pollution.
The receiver now starts at turn zero with a window that already looks like turn forty, inheriting all the drift, all the failed reasoning, all the abandoned hypotheses the original agent had emotionally moved past but which are still sitting there quietly pulling on attention.

There's a real tension here that deserves an honest airing, because Cognition's engineering blog argues almost the opposite, and their two principles are worth quoting straight: "Share context, and share full agent traces, not just individual messages," and "Actions carry implicit decisions, and conflicting decisions carry bad results."
Their point is sharp and correct — if the receiver sees your conclusion but not your reasoning, they may make a decision that conflicts with one you already implicitly made, and the two will collide downstream.
So which is it, share everything or share a packet?
The resolution is that these disagree about *format*, not *content*.
Cognition is arguing against handing over a one-line summary that discards decisions; this chapter is arguing against handing over a raw transcript that buries them in noise.
What you want is a packet that preserves every decision *explicitly*, which is exactly what the "tried and failed, and why" field is for and why it's mandatory.
A dead end with a reason attached is a recorded decision; a stack trace in a transcript is a decision the receiver has to do archaeology for.
Cognition's own follow-up notes that compressing history well takes real effort and specially tuned models, and that's the honest summary: the packet is harder than the dump, and it's worth it.

**The silent handoff** is control transferring with nothing written down.
A called B, B called a tool, something came back wrong, and three days later you're staring at a bad output with no way to reconstruct who decided what — you can't even tell whether it came from a bad packet, a good packet ignored, or a receiver that was never actually invoked.
This is the one that makes every other failure mode unfixable, because you cannot diagnose a chain you can't see.

## Escalating to a human without wasting them

Human-facing handoffs deserve their own treatment, because a human is the most expensive receiver you will ever hand to and the only one who gets annoyed, and a human interrupted mid-something needs exactly four things, in this order.

**The decision being asked**, in one sentence, phrased as a choice, at the very top: "Approve refund of \$420 on order 8812, or reject?" — not "I encountered an issue with a refund."
**The minimum context to make it** — not the transcript, but the two or three facts that actually bear on the choice, which for a refund is the amount, the reason, and whether this customer has been refunded before.
**Your recommendation**, because you have more context than they do; a human confirming a good recommendation takes four seconds, while a human reconstructing your reasoning from scratch takes four minutes.
**The cost of waiting** — "blocks the nightly run" versus "no deadline" is the difference between an interruption and a queue item, and only you know which it is.

Get those four right and a crisp escalation stops being an admission of failure and becomes one of the highest-value things your agent can emit.
An agent that says "I got 80% of the way, here's the one thing I need from you, here's what I'd do, and it costs nothing to wait until Monday" has produced *more* value than one that guessed and happened to be right, because it produced the value plus an intact trust relationship.

Now the failure direction, which matters more.
A bad escalation — vague, frequent, transcript-shaped, no recommendation — doesn't just waste one person's afternoon, it trains them.
After the fifth "I encountered an issue, please advise" with four screens of logs attached, the human stops reading and starts clicking approve; after the tenth, they stop opening them at all.
You have now built a system with a human oversight step that provides no oversight, which is strictly worse than having no human step, because everyone including the auditors believes the review is happening.

This has a name in the safety literature — approval fatigue, or rubber-stamping — and the mitigation is unglamorous: treat human attention as a hard budget the way you treat tokens.
Decide up front how many escalations a run gets, make the agent spend that budget on decisions that genuinely need a person, and make each one cost four seconds instead of four minutes.
Fewer, better escalations aren't a nicety; they're what keeps the human step real.

## Structuring it

Three design commitments make all of this work, and none of them are about prompting.

**Schemas over prose.**
A handoff packet should be a typed object with required fields, validated before it's sent, not a paragraph the sending model composes freehand.
A schema does something prose fundamentally cannot: it lets you *reject* an incomplete handoff at the boundary, where it's cheap, instead of discovering the gap three agents downstream, and it forces the sender to answer questions it would otherwise skip — the critical trick being that empty fields must be **asserted, not inferred**.
If nothing failed, the sender has to say "nothing failed" explicitly, because an absent failure list and an empty failure list look identical to the receiver and mean completely different things: one means "no dead ends," the other means "nobody wrote the dead ends down."

**The goal is immutable and passed byte-for-byte.**
Store it once, hash it, carry both, and have every receiver verify the hash before doing anything: if the text and its fingerprint disagree, someone paraphrased, and you find out at the hop instead of at the postmortem.
That's the entire fix for paraphrase drift, and it costs about six lines of code.

**A correlation ID threaded through every hop.**
A **correlation ID** is a shared identifier stamped on every record produced anywhere in the chain — every packet, every log line, every tool call, every escalation — so that afterwards you can pull the whole story by searching for one string.
This isn't an AI idea; it's the oldest trick in distributed systems and it's standardised.
The W3C Trace Context spec exists because "traces that are collected by different tracing vendors cannot be correlated as there is no shared unique identifier," and it fixes that with a `traceparent` header carrying a version, a 16-byte trace-id for the whole trace, an 8-byte span-id for this particular hop, and some flags.
Trace-id is the run, span-id is the hop, parent span-id is whoever handed to you; A2A's `contextId` is the same idea at the agent layer, and the OpenAI SDK's tracing exposes a `trace_id` plus a `group_id` for linking traces across one conversation.
Different names, one concept, and it's the cheapest item on this list: generate a random string at the top of the run, put it in every packet, log it with everything.
The day something goes wrong six hops deep, that string is the difference between an investigation and a shrug.

## A worked example

Here's the whole idea small enough to read: a packet with real validation, a builder that derives one from run state and an effect ledger, and a receiver that reconstructs working context without inheriting the transcript.

```python
"""Handoff packets: build one from a run, validate it, resume from it."""
import hashlib
from dataclasses import dataclass
from typing import Any


class HandoffError(ValueError):
    pass


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class Fact:          # something checked against the world, not something claimed
    claim: str
    evidence: str


@dataclass(frozen=True)
class DeadEnd:       # a road already walked; the 'why' stops the next hop retrying it
    attempt: str
    outcome: str
    why: str


@dataclass
class HandoffPacket:
    correlation_id: str        # identical on every hop of this chain
    hop: int                   # +1 per transfer
    sender: str
    receiver: str
    goal: str                  # verbatim, never paraphrased
    goal_sha: str              # fingerprint of the original goal
    verified: list[Fact]
    dead_ends: list[DeadEnd]
    state_ref: dict[str, str]  # where the work lives: pointers, not payloads
    open_questions: list[str]
    budget: dict[str, float]
    recommendation: str
    # An empty list must be *asserted*, never inferred from absence.
    nothing_verified: bool = False
    nothing_failed: bool = False

    def validate(self) -> None:
        bad = []
        if self.goal_sha != _sha(self.goal):
            bad.append("goal_sha does not match goal (paraphrase drift: the goal "
                       "text changed somewhere along the chain)")
        if bool(self.verified) == self.nothing_verified:
            bad.append("verified list and nothing_verified disagree (receiver can't "
                       "tell 'nothing done' from 'nobody wrote it down')")
        if bool(self.dead_ends) == self.nothing_failed:
            bad.append("no failure history and nothing_failed not asserted "
                       "(receiver will repeat whatever already failed)")
        bad += ["dead end %r has no 'why'" % d.attempt
                for d in self.dead_ends if not d.why.strip()]
        if not self.recommendation.strip():
            bad.append("no next-step recommendation")
        if "remaining_usd" not in self.budget:
            bad.append("budget missing remaining_usd")
        if not self.correlation_id:
            bad.append("no correlation id, chain will be unreconstructible")
        if bad:
            raise HandoffError("; ".join(bad))


@dataclass
class RunState:
    correlation_id: str
    goal: str
    agent: str
    hop: int
    checks: list[tuple[str, str, bool]]   # (claim, evidence, passed)
    artifacts: dict[str, str]
    questions: list[str]
    usd_spent: float
    usd_cap: float


def build_packet(run: RunState, effects: list[dict[str, Any]],
                 receiver: str, recommendation: str) -> HandoffPacket:
    """Derive a packet from run state + the effect ledger. No transcript involved."""
    verified = [Fact(c, e) for c, e, ok in run.checks if ok]
    dead_ends = [DeadEnd(x["action"], x["outcome"], x.get("why", ""))
                 for x in effects if x["status"] == "failed"]
    pkt = HandoffPacket(
        correlation_id=run.correlation_id, hop=run.hop + 1,
        sender=run.agent, receiver=receiver,
        goal=run.goal, goal_sha=_sha(run.goal),
        verified=verified, dead_ends=dead_ends,
        state_ref=dict(run.artifacts), open_questions=list(run.questions),
        budget={"spent_usd": round(run.usd_spent, 2),
                "remaining_usd": round(run.usd_cap - run.usd_spent, 2)},
        recommendation=recommendation,
        nothing_verified=not verified, nothing_failed=not dead_ends)
    pkt.validate()
    return pkt


def resume_from_packet(pkt: HandoffPacket, original_goal: str) -> str:
    """Rebuild working context. Note what is NOT here: the old transcript."""
    pkt.validate()
    if pkt.goal_sha != _sha(original_goal):
        raise HandoffError("goal drifted from the chain's original goal")
    out = ["[%s hop=%d from=%s]" % (pkt.correlation_id, pkt.hop, pkt.sender),
           "GOAL (verbatim, do not restate): " + pkt.goal,
           "ALREADY TRUE (verified, do not redo):"]
    out += ["  - %s  [%s]" % (f.claim, f.evidence) for f in pkt.verified] or ["  - nothing yet"]
    out += ["DO NOT RETRY (already failed):"]
    out += ["  - %s -> %s because %s" % (d.attempt, d.outcome, d.why)
            for d in pkt.dead_ends] or ["  - nothing yet"]
    out += ["STATE: " + ", ".join("%s=%s" % kv for kv in pkt.state_ref.items()),
            "OPEN: " + ("; ".join(pkt.open_questions) or "none"),
            "BUDGET: %.2f USD left of %.2f" % (
                pkt.budget["remaining_usd"],
                pkt.budget["remaining_usd"] + pkt.budget["spent_usd"]),
            "SUGGESTED NEXT: " + pkt.recommendation]
    return "\n".join(out)


GOAL = ("Cut p95 latency on GET /api/orders below 400ms without changing "
        "the response schema.")
RUN = RunState(
    correlation_id="cid-7f31a9", goal=GOAL, agent="perf-agent", hop=0,
    checks=[("p95 is 1180ms on prod", "grafana 2026-08-05T14:02Z", True),
            ("N+1 in order_items is the top cost", "pg_stat_statements: 61%", True),
            ("an index alone gets p95 to 940ms", "staging bench, 200 runs", True),
            ("the orders team approves a cache", "asked, no reply", False)],
    artifacts={"branch": "perf/orders-n1", "bench": "s3://runs/cid-7f31a9/bench.json"},
    questions=["is a 30s cache TTL acceptable to the orders team?"],
    usd_spent=4.10, usd_cap=12.00)
LEDGER = [
    {"action": "add composite index on (order_id, sku)", "status": "ok",
     "outcome": "p95 940ms"},
    {"action": "batch the item fetch with an IN clause", "status": "failed",
     "outcome": "response schema changed",
     "why": "the ORM flattened nested items, violating the no-schema-change constraint"},
    {"action": "enable read replica routing", "status": "failed",
     "outcome": "stale reads in checkout",
     "why": "replica lag peaks at 4s and checkout reads its own write"}]


def reject(label, fn):
    try:
        fn()
        print("%-28s NOT REJECTED (bug)" % label)
    except HandoffError as e:
        print("%-28s REJECTED: %s" % (label, e))


if __name__ == "__main__":
    good = build_packet(RUN, LEDGER, "db-agent",
                        "try a materialised view refreshed on write; "
                        "do not touch the serializer")
    ctx = resume_from_packet(good, GOAL)
    print(ctx, "\n")

    successes_only = build_packet(RUN, LEDGER, "db-agent", "make it faster")
    successes_only.dead_ends = []
    reject("successes only:", successes_only.validate)

    drifted = build_packet(RUN, LEDGER, "db-agent", "add caching")
    drifted.goal = "Make the orders endpoint faster."      # a helpful rewording
    reject("paraphrased goal:", lambda: resume_from_packet(drifted, GOAL))

    orphan = build_packet(RUN, LEDGER, "db-agent", "retry with caching")
    orphan.correlation_id = ""
    reject("silent handoff:", orphan.validate)

    print("\nhanded over: %d chars (the raw transcript is ~48000)" % len(ctx))
```

Its actual output:

```
[cid-7f31a9 hop=1 from=perf-agent]
GOAL (verbatim, do not restate): Cut p95 latency on GET /api/orders below 400ms without changing the response schema.
ALREADY TRUE (verified, do not redo):
  - p95 is 1180ms on prod  [grafana 2026-08-05T14:02Z]
  - N+1 in order_items is the top cost  [pg_stat_statements: 61%]
  - an index alone gets p95 to 940ms  [staging bench, 200 runs]
DO NOT RETRY (already failed):
  - batch the item fetch with an IN clause -> response schema changed because the ORM flattened nested items, violating the no-schema-change constraint
  - enable read replica routing -> stale reads in checkout because replica lag peaks at 4s and checkout reads its own write
STATE: branch=perf/orders-n1, bench=s3://runs/cid-7f31a9/bench.json
OPEN: is a 30s cache TTL acceptable to the orders team?
BUDGET: 7.90 USD left of 12.00
SUGGESTED NEXT: try a materialised view refreshed on write; do not touch the serializer 

successes only:              REJECTED: no failure history and nothing_failed not asserted (receiver will repeat whatever already failed)
paraphrased goal:            REJECTED: goal_sha does not match goal (paraphrase drift: the goal text changed somewhere along the chain)
silent handoff:              REJECTED: no correlation id, chain will be unreconstructible

handed over: 925 chars (the raw transcript is ~48000)
```

Four things in there are the transferable bits.

The failed check — "the orders team approves a cache: asked, no reply" — never reaches the receiver's *verified* list, because unverified is not the same as false, so it surfaces as an open question instead.
That's chapter five doing its job inside chapter seven.

The rejection for a missing failure list is the one that saves the most real money: that packet had successes, a goal, a budget and a recommendation, and it still got refused at the boundary, because a receiver with no dead-end list will re-run the read-replica experiment and rediscover the stale checkout reads on someone else's dime.

The paraphrase rejection fired because the *goal text* changed while its fingerprint didn't, and no model had to notice anything — it's a hash comparison, and fluency can't defeat it.

The last line is the whole argument in one number: 925 characters crossed the boundary instead of a 48,000-character transcript, and every fact the receiver needs is in the 925.

What the toy leaves out: the packet isn't signed, so a hostile hop could rewrite the goal *and* the hash together; there's no per-hop span-id, only a chain-level correlation ID; and nothing enforces the I-PASS synthesis step where the receiver acknowledges before starting.
All three are more code, none are more concept.

## Say it in one breath

A handoff is a compression problem with stakes — you must move everything the next party needs and nothing they don't, and whatever you drop stays invisible until it costs you.

Treat the packet as a designed artifact rather than a message: the original goal carried byte-for-byte and hashed so nobody can paraphrase it, what's been verified against the world with evidence, what's been tried and failed *and why* so the receiver doesn't re-walk your dead ends, where the state lives, what's open, what's left of the budget, and what you'd do next.

Reject an incomplete packet at the boundary where it's cheap, make empty fields asserted rather than inferred, and stamp a correlation ID on every record so the chain is reconstructible afterwards.

For humans, lead with the decision, the minimum context, your recommendation and the cost of waiting — because a vague escalation doesn't just waste one person's afternoon, it teaches them to stop reading, and then your oversight step is theatre.

And remember what this is for: when the window is too polluted to continue, the answer is a clean session plus a good packet, which is why the handoff is the cure for drift rather than a separate topic.

## What an interviewer is really testing

They want to know whether you've ever watched a multi-agent system produce a confidently wrong answer and then been unable to work out which agent produced it.

The junior answer is "we pass the conversation along"; the senior answer treats the handoff as a typed artifact with required fields and a rejection path, because you only build that after a receiver has silently dropped a constraint on you.

The strongest single tell is whether you volunteer the *negative* information — that what failed and why belongs in the packet, and that an empty failure list has to be asserted rather than inferred — since almost everyone lists accomplishments and stops.

Naming paraphrase drift and proposing an immutable hashed goal, then threading a correlation ID through every hop, moves you from prompt-engineering instincts to observability instincts, which is what the question is hunting for.

And if you connect it back to context drift out loud — that the packet is what makes a fresh window survivable, so "just start a new session" is only ever half of the advice — you've shown you think about these as one system rather than seven chapter titles.

## Further reading

- [OpenAI Agents SDK: Handoffs](https://openai.github.io/openai-agents-python/handoffs/) — handoffs as `transfer_to_<agent>` tools, the full-history default, and `input_filter` / `HandoffInputData` for controlling what crosses.
- [OpenAI Agents SDK: Tracing](https://openai.github.io/openai-agents-python/tracing/) — `trace_id` and `group_id` for linking traces across one conversation.
- [A2A Protocol specification](https://a2a-protocol.org/latest/specification/) — Agent Cards, and `contextId` versus `taskId`.
- [Google Cloud donates A2A to the Linux Foundation](https://developers.googleblog.com/en/google-cloud-donates-a2a-to-linux-foundation/) — June 2025, the governance move that made A2A a real standard.
- [Linux Foundation: Agent2Agent Protocol Project launch](https://www.linuxfoundation.org/press/linux-foundation-launches-the-agent2agent-protocol-project-to-enable-secure-intelligent-communication-between-ai-agents) — the announcement and founding members.
- [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) — `interrupt()`, `Command(resume=...)`, the checkpointer requirement, and the node-replays-from-the-top caveat.
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — engineers-working-shifts, progress files, and why compaction alone isn't enough.
- [Anthropic: Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — compaction, structured note-taking, and sub-agent context isolation.
- [Cognition: Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) — "share context, and share full agent traces"; "actions carry implicit decisions."
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — `traceparent`, trace-id and span-id: the original correlation-ID standard.
- [Changes in Medical Errors after Implementation of a Handoff Program](https://www.nejm.org/doi/full/10.1056/NEJMsa1405556) — the I-PASS study, NEJM 2014: 23% fewer medical errors, 30% fewer preventable adverse events.
- [AHRQ TeamSTEPPS: I-PASS tool](https://www.ahrq.gov/teamstepps-program/curriculum/communication/tools/ipass.html) — the mnemonic itself, including synthesis by the receiver.
