# Checkpoints and resume: making a long run survivable

## Start with a saved game

Think about the last long video game you played.
Someone on that game's design team had to decide where the save points go, and it was not a casual decision.
Put one after every single action and the game feels weightless, because nothing you do can ever cost you anything.
Put none in at all and the game becomes unplayable, because a phone call at hour three throws away hour three.

Now picture a game with no save points, that takes an hour to finish, that charges you money by the minute, and where some of the things your character does happen in the real world and cannot be taken back.

That's a long-running agent.

Here's the mental shift the whole chapter rests on, and if you only take one thing away, take this one.
A single chat completion is a **request**: it takes two seconds, nothing outside the conversation changes, and if it fails you simply ask again.
A 200-turn agent run is a **process**: it takes an hour, it costs real money, it sends emails and writes rows and moves money, and "just ask again" means burning the hour, burning the money, and possibly refunding the same customer twice.

Requests get *retried*.
Processes get *resumed*.
The rest of this chapter is about the machinery that moves a run from the first category into the second — and about the part almost everybody skips, which is that resuming *safely* is a much harder problem than resuming at all.

## Why agents need this more than your average web service

Most ordinary services don't bother with any of this, and they're mostly right not to.
An HTTP handler runs for eighty milliseconds, the chance of the machine dying inside that window rounds to zero, and if it does die the client retries and nobody notices.

Agents break that arithmetic in three ways, and the three compound.

**Runs are long, so interruption stops being an edge case.**
Suppose the machine your agent runs on has some small chance of being yanked away in any given minute — a deploy, a spot-instance reclaim, an out-of-memory kill, a network partition, a rate limiter that decides you've had enough.
Call that one in a thousand per minute, which is optimistic.
Over eighty milliseconds you'll never see it; over a ninety-minute run, the probability that *nothing* goes wrong is roughly \\(0.999^{90}\\), about 91%, which means one run in eleven dies partway through.
That's not an edge case, that's a Tuesday.

**Runs are expensive, so restarting throws away something real.**
When an eighty-millisecond handler restarts you lose eighty milliseconds.
When a ninety-minute agent restarts you lose the wall-clock, the tokens you paid for across two hundred model calls, and whatever the user's patience was worth.
The cost of a restart isn't the cost of the failed step — it's the cost of everything before it, and in a long run that number only grows.

**Runs have side effects, so restarting can be worse than not finishing at all.**
A read-only data pipeline can be restarted from scratch as often as you like; the worst outcome is a bigger bill.
An agent that files tickets, sends emails, updates CRM records and issues refunds does not have that property, and restarting it from step one means doing all of that again.
The failure mode isn't "wasted work," it's "the customer got three apology emails and two refunds," and that one is visible to people outside your company.

Hold those three together and the conclusion is forced: an agent that does real work needs to be able to stop in the middle and start again from the middle, and it needs to do that without redoing anything that already touched the outside world.

## What's actually in a checkpoint

A **checkpoint** is a saved snapshot of everything a run needs in order to be picked up again by a different process, on a different machine, possibly hours later.
The word people reach for is *durable* — meaning that if the machine running the job dies, another machine picks it up exactly where it left off instead of starting over.

Five things go in, and they're not equally well understood.

**The conversation and working state** — the messages so far, or a compacted version of them, plus whatever scratch variables the run carries.
This is the part everyone remembers, and it's the least interesting.

**The plan and the progress against it** — which steps exist, which are done, which is in flight, which are blocked.
This matters more than the transcript, because it's what lets a resumed run orient itself in one glance rather than re-deriving its own intentions by reading an hour of chat.

**Tool results worth keeping.**
Not every result — most are noise and you'll drown in storage — but the expensive ones, the slow ones, and the ones whose source might change under you are worth freezing, so the resumed run doesn't pay for them twice or get a different answer the second time.

**The budget ledger** — steps used, tokens burned, money spent, deadline remaining.
If you don't checkpoint this, every resume hands the agent a fresh full budget, and a run that crashes four times quietly spends five times its allowance.

**The side-effect log** — a record of every action this run has already taken against the outside world, and how to recognise each one again.

That last one is what people leave out, and it's the difference between a resume that *works* and a resume that's *safe*.
Consider two runs that both crash after step 40 of 60.

The first checkpointed conversation and progress: it comes back up, sees "step 41 next," and carries on — and if step 39's refund call succeeded but its result never got written down, nobody will ever know, because nothing in the checkpoint records that a refund was even attempted.

The second checkpointed the side-effect log too: it comes back up, sees "refund for order 8812, intent recorded, outcome unknown," and can go and *ask* whether that refund landed before deciding what to do.

Same crash, same conversation, same progress marker.
One of them can reason about what it has already done to the world; the other can only guess.

## Where checkpoints go, and how often

Two knobs: where you write, and how often.
Where is easy: anywhere that survives the process, which in practice means a database — Postgres is the boring, correct default, and most agent frameworks ship a Postgres-backed saver.
In-memory checkpointers are fine for development, but be honest about what they buy you, which is nothing at all when the machine dies.
A file on local disk is halfway: it survives a process crash, not a machine loss.

How often is the interesting one, because it's a straight trade.
Every turn is safest and most expensive: you pay a write — a few milliseconds locally, tens of milliseconds across a network — on every step, and storage grows as run length times run count.
For a two-hundred-turn run that's two hundred writes and two hundred stored blobs, most of which nobody will ever look at.

Milestones only is cheaper and loses more: checkpoint after each completed phase and a crash costs you the current phase, which might be twenty turns of work — a fine trade for a read-only research agent, a terrible one for an agent that spends money mid-phase.

LangGraph makes this trade explicit with three durability settings, which is a nice way to see the shape of it.
`"exit"` writes only when the graph finishes, which is fastest and gives you no mid-run recovery at all.
`"async"` writes checkpoints in the background while the next step runs, which is a good default for long workflows — with the caveat, stated plainly in their docs, that a crash can occasionally lose the most recent write.
`"sync"` writes each checkpoint before advancing, which costs latency on every step and is what you want when a missed checkpoint means a duplicate email or a duplicate payment.
([durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution))

The rule I'd give you is simpler than the settings: **checkpoint synchronously around side effects, and lazily everywhere else.**
Ten turns of pure reasoning and file reads can share one checkpoint; nobody gets hurt if you replay them.
The single turn that issues the refund gets its own write, before and after, no exceptions.

On storage: checkpoints are append-heavy and read-almost-never, so give them a retention policy on day one — keep everything for runs still in flight, keep the final state for completed runs, delete the intermediate ones after a few days.
The exception is the side-effect log, which is your audit trail; keep it far longer than the snapshots it came with, because "did we ever actually refund this person?" gets asked months later.

## Replay safety, slowly

Here's the thing that catches people out, and it catches them *after* the checkpointing works, which is the worst possible time.

You resume from a checkpoint, the agent picks up at the last recorded step, and it does that step again.

That's not a bug in your code, it's the fundamental shape of resume.
You saved a point in time; you come back to that point in time; anything that happened after that point and before the crash is invisible to you, and the system will redo it.
LangGraph's docs say this out loud for their own model: nodes after the checkpoint re-execute in full on resume, including the LLM calls and the API requests inside them.

So the question isn't "how do I avoid redoing steps," it's "what happens when a step gets done twice, and how do I make that outcome harmless."

### Idempotency, defined properly

**Idempotent** means: doing it twice has the same effect on the world as doing it once.
Not "the second call fails," not "the second call is ignored by luck" — same end state, every time, no matter how many times you run it.

Setting a value is idempotent: `status = "refunded"` written five times leaves exactly the same row as writing it once.
Adding to a value is not: `balance = balance + 40` run five times is a very different afternoon.

Now the example that makes it concrete, because refunds are the canonical case and payment companies have thought about this harder than anyone.

Say your agent issues a 40-unit refund by calling the vendor's API.
It sends the request, the refund is created, and then the network eats the response on the way back, so your agent sees a timeout and has no idea whether the money moved.
Then it crashes.
You resume, the step re-runs, it calls the API again — and now there are two refunds, because from the vendor's side those were two perfectly valid, unrelated requests.

The fix is an **idempotency key**: a unique string you generate and attach to the request, which the vendor stores alongside the result.
Stripe's implementation is the canonical one — the first request with a given key has its status code and body saved, and any later request carrying that same key returns the saved result rather than doing the work again, "including 500 errors."
Their keys live for at least 24 hours, and the layer compares the incoming parameters against the original request and errors if they differ, so you can't accidentally reuse a key for a different refund.
([idempotent requests](https://docs.stripe.com/api/idempotent_requests))

With a key, that retry is free: the vendor recognises it, hands back the same receipt, no new money moves.
Without one, the retry is a second refund.

The part people get wrong is where the key comes from — it must be **derived from the work, not from the attempt.**
If you generate a fresh UUID on each call, every retry gets a new key and the key does nothing at all; you've added ceremony without protection.
Build it from things stable across replays: the run ID and the step ID, or the order ID and the action name.
In the code below it's literally `run_id:step_id`, which is boring and exactly right, because the second attempt at step three computes precisely the same string as the first.

### Write-ahead logging, in plain terms

Idempotency keys handle the case where you *know* you're retrying; write-ahead logging handles the case where you don't know what happened at all.
The idea comes straight out of databases, and it's almost embarrassingly simple: **write down what you're about to do, before you do it.**
Every state change is appended to a log on disk *before* the in-memory structures change, so after a crash the system reads the log back and replays its way to a consistent state.
([Write-Ahead Log](https://martinfowler.com/articles/patterns-of-distributed-systems/wal.html))

Applied to an agent, it becomes a three-beat rhythm around every side effect: record the *intent* ("about to refund 40 for order 8812, key `run-4711:s3`") and flush it to durable storage, then actually do it, then record the *outcome* ("done, receipt re_3") and flush that too.

Now walk through where a crash can land.
Crash before beat one, and the log has nothing: you know the action never started, so you just do it.
Crash between two and three — the nasty one, the timeout case — and the log says *pending*.
You know an attempt was made and you don't know if it landed, which sounds bad but is enormously better than not knowing an attempt was made at all.
That single word turns an unanswerable question into a lookup: go ask the vendor whether key `run-4711:s3` exists, adopt the receipt if it does, redo the call with the same key if it doesn't.

Crash after beat three, and the log says *applied*, so you skip the step entirely.

The pending state is the whole reason the pattern is worth the extra write: without it, a crashed refund is indistinguishable from a refund that never happened, and you're choosing between double-paying and under-paying with no evidence either way.

This is exactly how durable execution engines work under the hood, incidentally.
Restate describes it as journaling: every meaningful step is recorded to a persistent log *before* its result is returned to your function, and on recovery the engine replays the completed steps and carries on from the first one that isn't in the journal.
([what is durable execution](https://restate.dev/what-is-durable-execution/))
DBOS does the same with Postgres as the journal — one write per step outcome, plus two per workflow — re-invoking interrupted workflows with their saved inputs and checking before each step whether that step's output is already checkpointed.
([DBOS architecture](https://docs.dbos.dev/architecture))

### At-least-once versus exactly-once

You'll hear "exactly-once" thrown around, usually as a selling point, so here's the honest version.
Across an unreliable network, **exactly-once delivery is not achievable.**
The sender can never distinguish "the request was lost" from "the response was lost," so it has to choose: give up on unclear cases (at-most-once, and you'll drop real work) or try again (at-least-once, and you'll sometimes duplicate).
Every serious system picks at-least-once.

What you *can* have is **exactly-once effects**, and the recipe is short: at-least-once delivery, plus idempotent handling at the far end.
The message may arrive five times; the world changes once.
That's what an idempotency key buys you, and it's why DBOS's own guidance is that steps "should be idempotent, meaning it should be safe to retry them multiple times" — the engine guarantees the retrying, you guarantee the harmlessness.

Say it that way in an interview and you'll sound like someone who has actually shipped this, because the distinction between *delivery* and *effect* is the exact thing people fudge.

## When replay isn't possible: compensation

Some steps can't be made idempotent, because the far end simply doesn't offer you a handle — an API with no idempotency key support, a system that assigns a new ID on every create, a partner integration written in 2009 that fires and forgets.

For those, you can't make the second attempt harmless, so you take the other road: you **undo the first one.**
That's the **Saga** pattern, and stripped of the jargon it's this — a long process is a sequence of small local steps, and each step ships with a paired *compensating* step that reverses it.
If the process fails at step five, you run the undos for four, three, two and one, in reverse order, until the world is back roughly where it started.
([Saga pattern](https://microservices.io/patterns/data/saga.html))

Booking a trip is the standard illustration and it's a good one: reserve the flight, reserve the hotel, charge the card.
The hotel reservation fails, so you run the flight's compensation — cancel it — and stop.
There's no database transaction spanning three companies, so you build the rollback by hand out of ordinary forward actions.

Two things to be honest about.

**Compensation is hand-written, and it's real work.**
The pattern's own documentation says it plainly: you design compensating transactions that explicitly undo earlier changes, because there's no automatic rollback to fall back on.
Every step is now two pieces of code, and the undo path is the one that never gets exercised in testing and is therefore the one that's broken.

**Compensation has no isolation.**
That's the "I" in ACID, and sagas don't have it.
Between the flight being booked and the flight being cancelled the flight is genuinely booked, and anything else looking at the system sees it that way — another process can read that intermediate state and act on it, and now your undo is undoing something someone else already built on top of.

### And some things simply have no undo

This is where you have to stop being clever.
The email is sent, the Slack message is in the channel and eleven people have read it, the wire transfer has left the building, the tweet is up and the screenshot is already circulating.

You can send a follow-up apology, but that's a new action, not a reversal — the original effect is permanently in the world.

For those actions, neither replay safety nor compensation saves you, and the correct engineering answer is not a better retry policy.
It's a **human gate**: the agent prepares the action, checkpoints, stops, and waits for a person to approve before anything leaves the building.

A useful way to sort every side-effecting tool your agent has, on a single sheet of paper:

| Can it be replayed safely? | Can it be undone? | What to do |
| --- | --- | --- |
| Yes (idempotency key) | n/a | Let it retry freely |
| No | Yes (compensation) | Write the undo, register it in the saga |
| No | No | Human gate, every time |

Most teams have never made that table, and making it takes about twenty minutes and changes the design of the system.

## Two reasons you resume, one piece of machinery

Now the nice part, because there's leverage hiding here that people miss: there are two entirely different reasons a run stops and later continues.
**Crash recovery**, which is involuntary — the pod was evicted, the process was OOM-killed, the deploy rolled, the network went away, and nobody planned it or was watching.

**Deliberate pause**, which is voluntary — the agent drafted something that needs human approval, or it's waiting on a six-hour data export, or it's blocked on a colleague who'll be back Monday.

Those feel like different problems, and organisationally they usually belong to different people: one is an infrastructure concern, one is a product concern.
Mechanically they are the same problem.
Both need the run's full state written somewhere durable, both need a way to identify the run later and hand that state to a fresh process, and both need the resumed run to know exactly what it already did to the world so it doesn't do it twice.

Which gives you the design instruction: **build for the deliberate pause, and you get crash recovery for free.**
The reverse doesn't hold, because crash recovery alone doesn't force you to think about the *waiting* — the fact that a run can sit idle for three days, that the world changes underneath it, that a resumed agent should re-check reality rather than trusting an assumption it formed on Friday.
Temporal makes exactly this pitch for agent workloads: the same event history that lets a worker replay after a failure is what lets a workflow park indefinitely on a human signal and pick up when it arrives.
([durable execution meets AI](https://temporal.io/blog/durable-execution-meets-ai-why-temporal-is-the-perfect-foundation-for-ai), July 2025)

## Three practical shapes

**Framework-level persistence.**
LangGraph is the reference example: you attach a *checkpointer* to the graph, hand every invocation a `thread_id` — a string identifying one conversation or run — and the framework snapshots state after each step, keyed to that thread.
Pass the same `thread_id` again and it loads the last snapshot and continues, and the same mechanism powers interrupt-and-resume, so human approval and crash recovery genuinely are one feature.
([persistence](https://docs.langchain.com/oss/python/langgraph/persistence))
The tradeoff: nearly free to adopt, and it only covers what's inside the graph — your checkpoint knows the node finished, but not that the node called Stripe halfway through and got a timeout, so side-effect safety is still yours to build.

**Durable execution engines.**
Temporal, Restate and DBOS sell the same promise: write ordinary-looking code, and the engine journals every step so a crash resumes mid-function instead of restarting it.
Temporal's Event History plus replay, Restate's journal-before-return, DBOS's Postgres-backed step checkpoints — different packaging, same idea.
The tradeoff is that determinism becomes a hard requirement: your orchestration code must make the same decisions on replay, so no `now()`, no un-journalled randomness, and external calls confined to the parts the engine wraps.
That's a real constraint on agent code, where the orchestrator is a language model that is *definitionally* non-deterministic — the usual resolution is that the model call is itself a journalled step whose recorded output gets replayed, rather than something you re-roll.

**Roll your own with an event log.**
Instead of snapshotting state, append every event and rebuild state by replaying the events.
That's **event sourcing**, and its best property here is that the log is an audit trail by construction: you see not just what the state is but how it got there, which is what you want when someone asks why the agent refunded a customer at 3am.
([Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html))
The tradeoff is that you own everything — replay performance, snapshotting so replay doesn't take forever, schema evolution as event shapes change, and the discipline that external calls must never be re-issued during a replay.
For a lot of agent systems the middle path is right, and it's what the example below is: state snapshots for the conversation, an append-only event log for the side effects, no framework at all.

## A checkpointer and effect ledger you can run

Dependency-free, and it does three things: persists run state as JSON, keeps a write-ahead effect ledger with idempotency keys, and resumes across a crash without moving money twice.
The crash is injected at the worst possible moment — after the refund reaches the vendor, before the outcome is recorded — because that's the case that separates a real design from a hopeful one.

```python
import json
import os


class Crashed(Exception):
    """Stands in for the machine dying mid-run."""


class RefundAPI:
    """A mock vendor that honours idempotency keys, the way Stripe does."""

    def __init__(self, honour_keys=True):
        self.honour_keys = honour_keys
        self.by_key = {}
        self.moved = []                          # payments that really happened

    def refund(self, amount, idempotency_key):
        if self.honour_keys and idempotency_key in self.by_key:
            return self.by_key[idempotency_key]  # replay: no new money
        receipt = {"id": "re_%d" % (len(self.moved) + 1), "amount": amount}
        self.moved.append(amount)
        self.by_key[idempotency_key] = receipt
        return receipt

    def lookup(self, idempotency_key):
        return self.by_key.get(idempotency_key)


class Checkpointer:
    """Run state as one JSON file. Swap in Postgres and the shape is the same."""

    def __init__(self, path):
        self.path = path

    def load(self):
        if not os.path.exists(self.path):
            return None
        with open(self.path) as f:
            return json.load(f)

    def save(self, state):
        with open(self.path + ".tmp", "w") as f:
            json.dump(state, f, indent=2)
        os.replace(self.path + ".tmp", self.path)   # atomic: never a half file


def apply_refund(state, ckpt, api, step, log):
    key = "%s:%s" % (state["run_id"], step["id"])   # stable across replays
    rec = state["effects"].get(key)

    if rec and rec["status"] == "applied":          # belt and braces
        log.append("  skip      %s (already applied)" % step["id"])
        return rec["receipt"]

    if rec and rec["status"] == "pending":          # we died mid-flight
        found = api.lookup(key)
        if found:
            state["effects"][key] = {"status": "applied", "receipt": found}
            ckpt.save(state)
            log.append("  reconcile %s -> it did happen, adopting %s"
                       % (step["id"], found["id"]))
            return found
        log.append("  reconcile %s -> never landed, retrying" % step["id"])

    state["effects"][key] = {"status": "pending", "receipt": None}
    ckpt.save(state)                                # write-ahead: intent first
    receipt = api.refund(step["amount"], idempotency_key=key)
    state["effects"][key] = {"status": "applied", "receipt": receipt}
    ckpt.save(state)                                # then the outcome
    log.append("  refund    %s -> %s for %d"
               % (step["id"], receipt["id"], receipt["amount"]))
    return receipt


def run(ckpt, api, steps, run_id, crash_at=None):
    state, log = ckpt.load(), []
    if state is None:
        state = {"run_id": run_id, "cursor": 0, "steps": steps, "effects": {}}
        ckpt.save(state)
        log.append("start  %s" % run_id)
    else:
        log.append("resume %s at step %d" % (state["run_id"], state["cursor"]))

    while state["cursor"] < len(state["steps"]):
        step = state["steps"][state["cursor"]]
        if state["cursor"] == crash_at:             # act, then die before recording
            key = "%s:%s" % (state["run_id"], step["id"])
            state["effects"][key] = {"status": "pending", "receipt": None}
            ckpt.save(state)
            api.refund(step["amount"], idempotency_key=key)
            log.append("  CRASH     after acting on %s, before recording it"
                       % step["id"])
            raise Crashed(log)
        apply_refund(state, ckpt, api, step, log)
        state["cursor"] += 1
        ckpt.save(state)
    return state, log


if __name__ == "__main__":
    steps = [{"id": "s%d" % i, "amount": a} for i, a in enumerate([10, 25, 40, 5], 1)]
    path = "/tmp/run.json"
    if os.path.exists(path):
        os.remove(path)
    ckpt, api = Checkpointer(path), RefundAPI()

    try:
        run(ckpt, api, steps, "run-4711", crash_at=2)
    except Crashed as e:
        print("\n".join(e.args[0]))
    state, log = run(ckpt, api, steps, "run-4711")
    ledger = sum(e["receipt"]["amount"] for e in state["effects"].values())
    print("\n".join(log))
    print("\npayments that actually moved: %s" % api.moved)
    print("total moved: %d   ledger total: %d   steps done: %d/%d"
          % (sum(api.moved), ledger, state["cursor"], len(steps)))

    naive = RefundAPI(honour_keys=False)
    naive.refund(40, idempotency_key="run-4711:s3")
    naive.refund(40, idempotency_key="run-4711:s3")   # same key, no protection
    print("without idempotency the same resume moves: %s" % naive.moved)
```

Its actual output:

```
start  run-4711
  refund    s1 -> re_1 for 10
  refund    s2 -> re_2 for 25
  CRASH     after acting on s3, before recording it
resume run-4711 at step 2
  reconcile s3 -> it did happen, adopting re_3
  refund    s4 -> re_4 for 5

payments that actually moved: [10, 25, 40, 5]
total moved: 80   ledger total: 80   steps done: 4/4
without idempotency the same resume moves: [40, 40]
```

Read the middle three lines slowly, because they're the entire chapter.
The run died at step three at the worst possible instant — the vendor had taken the money, and the ledger said only *pending*.
The resumed run didn't guess: it saw the pending entry, looked the key up at the vendor, found the receipt, adopted it, and moved on.
Eighty units moved, once each, across a crash, with no coordination and no distributed transaction.
The last line is the counterfactual — same resume, same key, a vendor that ignores it, and forty units go out twice.

Two details worth stealing.
`os.replace` is atomic on every mainstream filesystem, so a crash during the write leaves you with either the old checkpoint or the new one, never a half-parsed file — the same trick a database uses, at hobbyist scale.
And the `applied` branch is technically unreachable here because the cursor already skips finished steps; it's there because belt and braces is the right amount of clothing when the failure mode is duplicate payments, and it becomes reachable the moment steps retry independently of the cursor.

What the toy leaves out: the vendor lookup is a local dictionary rather than a real API call that can itself fail, there's no expiry on the effect ledger, and there's no compensation path for steps that can't be replayed.
All three are more code, none are more concept.

## Say it in one breath

A long agent run is a process, not a request, so it needs saving and resuming rather than retrying.
A checkpoint holds the conversation, the plan and progress, the expensive tool results, the budget ledger, and — the part everyone forgets — a log of what the run has already done to the outside world.
Resume always means redoing something, so every side effect needs either an idempotency key that makes a second attempt harmless, or a hand-written compensating action that undoes the first, and if it has neither it belongs behind a human gate.
Write the intent down before you act and the outcome after, because the *pending* state in between is what turns "did that refund happen?" from a guess into a lookup.
Crash recovery and deliberate pause-for-approval are the same machinery, so build the pause and get the crash for free.

## What an interviewer is really testing

Almost everyone will answer "checkpoint the message history to a database" and stop there, which tells the interviewer you've read the framework docs and nothing else.
The signal they're listening for is whether you immediately ask what happens to the refund that was in flight when the process died — and reach for idempotency keys and a write-ahead effect log without being prompted.
The second tell is whether you can state the exactly-once thing precisely: at-least-once delivery plus idempotent handling gives exactly-once *effects*, and anyone selling exactly-once *delivery* across a network is selling something.
The third is knowing where the technique runs out — that compensation is hand-written, has no isolation, and doesn't exist at all for a sent email or a wire transfer, which is an argument for a human gate rather than a cleverer retry.
Volunteer that crash recovery and human-approval pauses are one mechanism and you've shown the architectural instinct the question exists to find.

## Further reading

- [LangGraph: persistence and checkpointers](https://docs.langchain.com/oss/python/langgraph/persistence) — threads, `thread_id`, and the in-memory / SQLite / Postgres savers.
- [LangGraph: durable execution](https://docs.langchain.com/oss/python/langgraph/durable-execution) — the `"exit"` / `"async"` / `"sync"` durability modes and the determinism requirements.
- [Stripe: idempotent requests](https://docs.stripe.com/api/idempotent_requests) — the canonical idempotency-key design, including key retention and parameter matching.
- [Temporal: durable execution meets AI](https://temporal.io/blog/durable-execution-meets-ai-why-temporal-is-the-perfect-foundation-for-ai) — the case for durable execution under agent loops, July 2025.
- [Restate: what is durable execution](https://restate.dev/what-is-durable-execution/) — journaling, replayed results, durable timers and signals.
- [DBOS: architecture](https://docs.dbos.dev/architecture) — Postgres-backed checkpointing, step-level replay, and the requirement that steps be idempotent.
- [microservices.io: Saga pattern](https://microservices.io/patterns/data/saga.html) — compensating transactions, choreography versus orchestration, and the isolation caveat.
- [Martin Fowler: Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html) — rebuilding state by replaying events, and why external systems can't tell a replay from the real thing.
- [Unmesh Joshi: Write-Ahead Log](https://martinfowler.com/articles/patterns-of-distributed-systems/wal.html) — record the change before you apply it.
- [Anthropic: effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — externalised progress state as the thing that survives between agent shifts.
