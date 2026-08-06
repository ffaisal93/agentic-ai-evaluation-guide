# Operating a fleet of long-running agents

## The night shift at a laundromat

Here's the mental shift, and it's the whole chapter in one image.

Most web services are a coffee shop.

Someone walks up, asks for a flat white, you make it in ninety seconds, they leave, and if something goes wrong you find out immediately because there's a person standing right there holding an empty cup.

The unit of work is small, it's over fast, and "how are we doing?" is a question about *throughput and error rate* across thousands of tiny identical interactions.

A fleet of long-running agents is a laundromat at 2am.

Thirty machines are running, each one is forty minutes into its own cycle, each one has someone's actual clothes inside it, and each one is capable of failing in a way that looks exactly like working.

Nobody is standing there holding an empty cup, and the unit of work is a *job* — long-lived, stateful, expensive, and individually worth inspecting.

You are not serving requests anymore, you are supervising jobs, and that changes almost every instinct you have about monitoring.

## What actually changes when a unit of work lasts an hour

**Averages stop meaning anything.** With 200-millisecond requests you get thousands of samples an hour, so a p99 latency number — the value 99% of requests come in under — is statistically solid and moves smoothly. With one-hour jobs you might have forty samples a day, and forty samples is not a distribution, it's an anecdote with error bars; any dashboard that averages them will be quiet on the day everything falls apart.

**One failure is expensive enough to care about individually.** A dropped HTTP request costs you a retry; a dropped agent run at minute fifty-two costs real money, real wall-clock time, and possibly a half-finished side effect sitting in someone's database. In coffee-shop-land you never open a single trace unless you're debugging; here, opening single runs is a normal daily activity.

**The failure happens long before you see it.** The agent went off the rails at turn 19 and kept going, confidently, until turn 44. Your "run failed" signal fires twenty-five turns and eleven dollars after the actual defect. If your only instrument is the outcome, you are always looking at the crash site rather than the skid marks.

**Most failures aren't failures.** This is the one that breaks people's ops instincts hardest. Drifted runs *complete*, falsely-completed runs return HTTP 200 with a cheerful summary, and your success rate looks great — which is why "did the run error?" is close to worthless as a health metric here, as the false-completion chapter goes into properly.

**The unit has internal state that outlives the process.** A request is stateless; kill it and nothing is lost. A run has a checkpoint, a working directory, a half-written file, an open ticket. Killing it has consequences, and restarting it means resuming rather than re-requesting.

**Backpressure works differently.** Thirty long jobs each hold memory, tokens, tool connections, and rate-limit share for the next forty minutes, so concurrency limits matter more than request-rate limits.

Fewer units, each bigger, each individually inspectable, each capable of failing quietly halfway through: that's a jobs system, and jobs systems get watched differently.

## Instrument per turn, not per run

**Per-run aggregates hide every failure mode in this track.**

*Hide* them completely, by construction — not "obscure them."

Think about what a per-run record actually contains: run ID, start time, end time, total tokens, total cost, final status.

Now try answering any question this track cares about using only that.

Did quality degrade as context grew? You can't tell — one quality number for the whole run, and no context measurements at all.
Did the agent stall? You can't tell — a stalled run and a productive run of the same length are the same row.
Did it burn its budget on retries at step three? You can't tell — a total is the sum of a healthy run and a pathological one alike.
Did it claim completion without verifying? You can't tell — status says `completed`, which is precisely the lie you were trying to catch.

Every single one of those becomes *visible and obvious* the moment you emit one record per turn.

Aggregates are a summary of a story; per-turn records are the story, and you cannot recover a story from its summary.

Here's the record I'd emit on every single turn of every single run.

| Field | Why it earns its place |
|---|---|
| `run_id`, `turn_index` | The turn index is the x-axis for everything in this track. Without it you have a pile, not a curve. |
| `tokens_in`, `tokens_out` | Input tokens grow with the transcript; output tokens don't. The ratio tells you how much you're paying to re-read history. |
| `context_tokens` | Size of the window going into this turn. The slope is your leading indicator, and a sudden drop marks a compaction event. |
| `tool_calls`, `tool_errors` | Rising error rate late in a run usually means the agent is guessing at arguments it no longer has good context for. |
| `latency_ms` | Per-turn latency grows with context, so a flat latency curve on a growing run is itself suspicious. |
| `cost_cumulative` | Cumulative, not per-turn, because "how much of the allowance is gone" is the number that drives kill decisions. |
| `progress_signal` | Did this turn move a real artifact — a file written, a test passing, a field filled? Distinct from "did the turn succeed." |
| `state_hash` | A fingerprint of the agent's working state after this turn. Two identical hashes in a row means nothing changed. |

That last one deserves plain English, because "state hash" sounds fancier than it is.

A hash is a short fingerprint computed from a blob of data — same data in, same fingerprint out; change one byte and the fingerprint changes completely.

So you take whatever counts as "the agent's working state" — files modified, the plan, the current subtask, the tool it just called with what arguments — mash it into a string, and hash it.
If turn 28 and turn 29 have the same fingerprint, the agent did a whole turn and moved nothing, and five of those in a row is a stall — detected mechanically, with no model in the loop and no judgment call.

The good news is that the industry is standardizing on roughly this shape.
The OpenTelemetry GenAI semantic conventions — a vendor-neutral agreement on what to name things so tools can interoperate — define operations like `invoke_agent`, `execute_tool`, and `plan`, with attributes including `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, and `gen_ai.conversation.id` for tying turns of the same conversation together ([spec](https://github.com/open-telemetry/semantic-conventions-genai)).

Use those names — you get portability across LangSmith, Langfuse, Arize Phoenix, Braintrust, and your existing tracing backend for free, and you stop arguing about field names in code review.

Add your own attributes for the things the spec doesn't have yet — `turn_index`, `progress_signal`, `state_hash` — and namespace them so they're obviously yours.

## The dashboard that actually catches these bugs

Seven charts — and I've seen teams with forty panels and none of these, and teams with these seven who found real bugs in week one.

**Quality against turn index.** Score the same rubric at turn 5, 15, 30, and 50, and plot it. *Bad looks like:* the curve starting flat and then bending down after some turn — the knee — and the knee walking left week over week. If the knee was at turn 35 last month and it's at turn 22 now, something got more verbose or the model changed under you. It's the chapter-03 curve run continuously on sampled production traffic rather than on an eval set.

**Run-length distribution.** A histogram of how many turns each run took, not the average. *Bad looks like:* the tail fattening. The median barely moves — 15 to 16 turns, who cares — while the p90 goes from 20 to 34 and a new little bump appears right at your step limit. That bump is agents dying at the wall, and the fattening tail is the fleet quietly finding the work harder. It's one of the earliest reliable signals you have, and it costs nothing to compute.

**Budget-exhaustion rate.** The share of runs that hit their step, cost, or time limit instead of finishing. *Bad looks like:* any sustained rise, but especially a rise where total cost is flat — that means the same money is buying fewer completions. Exhaustion going from 2% to 5% is a much bigger deal than it sounds, because those are total losses: you paid full price for nothing.

**False-completion rate caught by verifiers.** Of the runs that claimed success, the share your independent verifier rejected. *Bad looks like:* going up, obviously — but read it carefully, because a rising catch rate is ambiguous. Either the agent got worse, or your verifier got better. Version your verifiers and annotate the chart when they change, or you'll spend a day chasing a regression you caused yourself.

**Stall / no-progress rate.** Share of runs with a window of consecutive turns showing no progress signal and a repeating state hash. *Bad looks like:* a rise concentrated at a particular turn range, which usually points at one specific tool or one specific subtask that agents get wedged on.

**Resume and crash counts.** How often runs were interrupted and picked back up from a checkpoint, and how often they died outright. *Bad looks like:* resumes rising without a matching infrastructure event, which usually means runs are getting long enough to collide with deploys or timeouts. Also watch the *success rate of resumed runs specifically* — if resumed runs succeed much less often than fresh ones, your checkpoints aren't capturing enough state, which the checkpoint-and-resume chapter goes into properly.

**Escalation rate.** Share of runs that asked a human for a decision. *Bad looks like:* either direction. Rising means the agent is less confident or the work got harder, and your humans are about to be swamped. *Falling* is the scarier one, because it often means the agent stopped asking and started guessing — and a confident guess is exactly the input to a false completion.

Two of these — quality-by-turn and false-completion — need a judge or a verifier, so they cost money; run them on a *sample*.

This is normal practice now and every major platform supports it: Langfuse lets you attach an evaluator to live production traffic with a sampling percentage, deterministic per observation so the same subset is chosen consistently ([docs](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)), and LangSmith's online evaluations let you filter production runs and set a sampling rate so the evaluator applies to, say, 10% of traces ([docs](https://docs.langchain.com/langsmith/online-evaluations)).

Five percent of traffic, scored continuously, will tell you more about your fleet than a hundred percent scored never.

## Alerting that isn't noise

Alert fatigue is a plain, unglamorous thing, and it kills more monitoring systems than bad metrics do.

It works like this: the pager goes off, you look, it's nothing, you go back to work — fifteen times.

The sixteenth time you glance, assume it's nothing, and go back to work, except this one was real.

Google's SRE book puts it bluntly: "when pages occur too frequently, employees second-guess, skim, or even ignore incoming alerts, sometimes even ignoring a 'real' page that's masked by the noise," and their standard is that "every page should be actionable" and "every page response should require intelligence" ([Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/)).

Now apply that to agents.

**Per-run alerts are a fatigue machine, and here's the arithmetic.**

Suppose your fleet is healthy and 3% of runs hit their budget wall.

That is a completely fine number.

If you run two thousand jobs a day, "alert when a run exhausts its budget" pages you sixty times a day for a system that is working correctly.

Within a week nobody reads them, and within two weeks somebody adds a filter rule and the channel is functionally dead.

The fix is one sentence: **alert on rates and trends, not on individual runs.**
An individual exhausted run is a *log line*, and maybe a row in a review queue.
The exhaustion *rate* moving from 3% to 7% is a page, because that's a change in the system rather than a sample from it.

The signatures worth wiring up:

- **Exhaustion rate rising.** Runs are hitting the wall more often. Something got harder, slower, or chattier.
- **Verifier catch rate rising.** More claimed successes are being rejected. Either quality dropped or your verifier changed — check the verifier version first.
- **Median run length growing week over week.** The single best early-warning signal in this whole chapter. Same work, more turns, means the agent is struggling before it starts failing.
- **Cost per successful task rising while cost per run is flat.** You're paying the same and getting less. This one is easy to miss because the finance dashboard looks fine.
- **Stall rate rising in a specific turn range or on a specific tool.** Narrow, actionable, usually one bug.
- **Healthy-run share dropping.** The composite. If you can only afford one alert, make it this.

Three practical guards keep even trend alerts from becoming noise.

Put an *absolute floor* on every rule, so a rate going from 0.1% to 0.3% — a tripling! — doesn't page anyone.
Require the change to *persist* across two windows, because a single bad afternoon is usually one flaky upstream API rather than a fleet problem.
And check your sample size before comparing, because with forty runs a day a "20% increase" is often eight runs versus six, which is nothing at all.

## Debugging a bad run after the fact

Somebody escalates a run: fourteen dollars, fifty-one turns, and a confidently wrong answer at the end of it.

Here's the workflow, in order.

**Trace first, never logs first.** A trace is the full, ordered, structured record of what happened — every model call, every tool call, every tool result, nested so you can see what happened inside what; logs are the fallback when you don't have one. Open the trace, collapse it to one row per turn, and look at the shape before you read a single word of content: you want the turn where the *shape* changes, where context jumps, where errors start clustering, where progress stops.

**Find the divergence turn with the state hashes.** This is the payoff for that column. Scan down the hash column and find the first turn where it stops changing, or the first turn where it returns to a value it had before. That's your loop. It is a mechanical lookup — no reading, no judgment — and it usually takes ten seconds. The alternative is reading fifty turns of transcript hunting for the moment things "felt off," which is genuinely awful.

**Read three turns, not fifty.** The turn before the divergence, the divergence turn, and the one after — the story is almost always right there: a tool returned something huge and plausible-but-wrong, an error came back and the agent invented a workaround, or a compaction event dropped the constraint that was holding it steady.

**Replay from the checkpoint just before it.** This is where per-turn instrumentation pays for itself twice. Restore the checkpoint from turn 18, change one thing — the compaction threshold, the tool's output limit, the system prompt — and run forward. Now you have a controlled experiment on a real failure instead of a theory. The mechanics of checkpointing and safe resume are in the checkpoint-and-resume chapter; the mechanics of deterministic replay against a frozen trace are in chapter 03.

**Then turn it into a regression test.** The frozen trace goes in the suite with the assertion "quality at turn 30 must exceed X" — the same instinct as turning every production bug into a unit test, and the difference between a fleet that gets more reliable over time and one that just accumulates folklore.

One habit makes all of this dramatically easier: thread a single correlation ID through everything — the run, every turn, every tool call, every sub-agent, every emitted artifact.
W3C Trace Context standardized this for ordinary distributed systems years ago, and OpenTelemetry's `gen_ai.conversation.id` is the agent-shaped version of the same idea, and without it reconstructing a multi-agent run is archaeology.

## Cost control at fleet scale

Agent costs have a nasty shape that ordinary API costs don't: because the whole transcript is re-sent on every turn, cost per turn *grows* over a run, so total cost scales roughly with the square of the turn count.

Turn 5 might cost a cent and turn 55 fourteen cents, doing comparable work, so a run that goes twice as long costs far more than twice as much.

That means the tail of your run-length distribution isn't just a reliability problem, it's most of your bill.

**Per-run caps.** Every run gets a hard limit on steps, dollars, and wall-clock, checked in the loop, enforced by the harness rather than by the model's good intentions. And tell the agent its remaining budget — an agent with no sense of how much it has left will start a careful six-part plan on step forty-eight, as the retry-budget chapter goes into at length.

**Kill switches for runaway runs.** A supervisor process that watches live per-turn records and kills runs that are demonstrably going nowhere: repeated state hash, no progress for N turns, cost curve steepening while the progress rate flatlines. Killing a stalled run at turn 25 instead of turn 50 halves its cost and loses you nothing, because it wasn't going to produce anything. Make the kill graceful — checkpoint, write a handoff packet, then stop — so the work is resumable rather than incinerated.

**Org-level budgets with degradation, not just denial.** A daily or monthly ceiling across the whole fleet, with tiers. At 70% of budget, drop the sampling rate on your expensive online evaluators. At 85%, route low-priority work to a smaller model or shorten the step limits. At 100%, queue rather than reject where you can. The failure mode to avoid is a hard cliff at midnight on the 28th that takes production down; a budget that degrades gracefully is a budget people will actually let you enforce.

**Report cost per *successful* task, never cost per request.** This is the framing change that matters most, and it's worth being pedantic about. Cost per run averages your successes with your failures and tells you nothing actionable. Cost per successful task divides your total spend — including everything you burned on runs that exhausted, stalled, or lied about finishing — by the number of tasks that actually got done and verified. A cheap run that fails is the most expensive kind of run you have, and only this metric shows that. It's also the number that makes the business conversation easy: "we spend \$2.06 per completed ticket, down from \$3.10" is a sentence an executive can do something with, and "our token spend is up 14%" is not.

## The human side

You will end up with on-call for agents, and it looks different from on-call for services.

The classic page is "the thing is down, go make it up," whereas the agent page is "the fleet is drifting, go work out why" — an investigation rather than a restart, and much less amenable to being handled at 3am by someone half-awake.

Which has a practical consequence: **most agent alerts should not be pages.**

Fleet-drift signals belong in a daily review, because there is nothing useful to do about them in the next fifteen minutes.

Reserve the actual pager for the things that are both urgent and fixable right now: the fleet is stuck and no runs are completing, spend is running away, a tool that everything depends on is down, or a safety gate is failing open.

Runbooks are where the leverage is, and agent runbooks need one section ordinary ones don't: **how to tell a real regression from a moved goalpost**, because half of agent "incidents" turn out to be a model version change, a prompt edit that shipped Tuesday, a tool whose output got 3x more verbose, or a verifier that got stricter.

So page one of the runbook should be a checklist of what changed — model version, prompt version, tool versions, verifier version, traffic mix — before anyone starts reading traces, and writing that once will save you dozens of hours.

The other structure worth building is a **review queue for escalations**, and what makes or breaks it is volume.

Escalations arrive at human speed but are generated at agent speed, and if the queue is too big people stop reading and start approving — approval fatigue, where a rubber-stamped gate is worse than no gate because it manufactures a false record of oversight.

So budget it: decide how many escalations per hour your humans can genuinely consider, and make the agent's escalation threshold a tunable you adjust to hit that number.

Give each queue item the four things a human actually needs — the decision, the minimum context to make it, the agent's recommendation, and the cost of waiting — which is the handoff-packet shape from the previous chapter.
And sample the queue's *outcomes*: if humans approve 98% of escalations without changes, your threshold is too low and you're wasting their attention; if they reject a third of them, the agent is escalating the wrong things and that's a prompt or a policy bug.

## Where the rest of this lives

This chapter is deliberately the long-horizon slice of operations, and there's good general material elsewhere in this guide that I won't restate badly.

For dashboards, SLOs, alert design, and the general practice of watching a live system, go to `12_production_monitoring`.

For getting eval cases out of production traffic and dealing with real-world messiness, `08_real_world_testing`.

For eval harnesses, LLM-as-judge calibration, and running scoring in CI, `09_automated_evaluation`.

And the sibling `llm-serving-inference-guide` repo covers the serving-layer side — batching, KV-cache behavior, GPU utilization, tail latency — which is a genuinely different problem from this one and worth keeping mentally separate.

The relationship is simple: those chapters teach you to watch a system, and this one asks you to watch a system whose unit of work is an hour long, individually expensive, and capable of failing silently — same instruments, very different alerts.

## A worked example

Given a stream of per-turn records across many runs, this computes per-run health, classifies each run, rolls up fleet rates, and fires trend alerts by comparing two weeks.
Standard library only; the simulator at the bottom just manufactures a plausible fleet so you can run it.

```python
"""Fleet health from a stream of per-turn records. Standard library only."""

import random, statistics
from collections import defaultdict

STEP_BUDGET, COST_BUDGET = 40, 3.00

# One record per TURN, not per run. Everything below is derived from these.
# fields: run_id week turn context_tokens tool_calls tool_errors
#         cost_usd progress state_hash


def run_health(turns):
    """turns: one run's records, any order. Returns that run's health."""
    turns = sorted(turns, key=lambda t: t["turn"])
    n, last = len(turns), turns[-1]
    cost = sum(t["cost_usd"] for t in turns)

    # Burn: fraction of the allowance spent. Take whichever limit is tighter.
    burn = max(n / STEP_BUDGET, cost / COST_BUDGET)
    # Progress: share of turns that moved a real artifact forward.
    progress_rate = sum(1 for t in turns if t["progress"]) / n
    # Context growth: tokens added per turn.
    growth = (last["context_tokens"] - turns[0]["context_tokens"]) / max(n - 1, 1)

    # Stall: the tail made no progress AND kept landing in the same state.
    tail = turns[-6:]
    stalled = (n >= 6
               and not any(t["progress"] for t in tail)
               and len({t["state_hash"] for t in tail}) <= 2)

    calls = sum(t["tool_calls"] for t in turns)
    err_rate = sum(t["tool_errors"] for t in turns) / calls if calls else 0.0

    # First turn whose state hash repeats an earlier one: where the loop began.
    seen, loop_turn = set(), None
    for t in turns:
        if t["state_hash"] in seen and loop_turn is None:
            loop_turn = t["turn"]
        seen.add(t["state_hash"])

    return dict(run_id=last["run_id"], turns=n, cost=cost, burn=burn,
                progress_rate=progress_rate, context_growth=growth,
                tool_error_rate=err_rate, stalled=stalled,
                loop_started_at=loop_turn, final_context=last["context_tokens"])


def classify(h, completed, verified):
    """Worst-first, so a run gets the most alarming label that fits."""
    if h["burn"] >= 1.0 and not completed:
        return "exhausted"
    if h["stalled"]:
        return "stalled"
    if completed and not verified:
        return "false_completion"
    if h["burn"] > 0.5 and h["progress_rate"] < 0.4:
        return "degrading"          # spending a lot, achieving little
    if h["context_growth"] > 2500 and h["progress_rate"] < 0.5:
        return "degrading"          # window ballooning, progress drying up
    return "healthy"


def fleet_report(runs):
    """runs: list of (health, completed, verified, escalated, resumed, crashed)."""
    n = len(runs)
    buckets = defaultdict(int)
    for h, completed, verified, *_ in runs:
        buckets[classify(h, completed, verified)] += 1
    lengths = sorted(h["turns"] for h, *_ in runs)
    wins = [r for r in runs if r[1] and r[2]]
    total = sum(h["cost"] for h, *_ in runs)
    rep = {f"{k}_rate": buckets[k] / n for k in
           ("healthy", "degrading", "stalled", "exhausted", "false_completion")}
    rep.update(
        escalation_rate=sum(1 for r in runs if r[3]) / n,
        resume_rate=sum(1 for r in runs if r[4]) / n,
        crash_rate=sum(1 for r in runs if r[5]) / n,
        median_turns=statistics.median(lengths),
        p90_turns=lengths[min(int(0.9 * n), n - 1)],
        cost_per_run=total / n,
        cost_per_successful_task=total / len(wins) if wins else float("inf"))
    return rep


# (metric, direction, relative jump worth paging on, absolute floor to care)
RULES = [("exhausted_rate", "up", 0.50, 0.02),
         ("false_completion_rate", "up", 0.50, 0.03),
         ("stalled_rate", "up", 0.50, 0.03),
         ("median_turns", "up", 0.20, 0.0),
         ("cost_per_successful_task", "up", 0.25, 0.0),
         ("healthy_rate", "down", 0.10, 0.0)]


def trend_alerts(prev, curr):
    out = []
    for metric, direction, jump, floor in RULES:
        a, b = prev[metric], curr[metric]
        if a == 0:
            # Zero last week is a real signal, not a divide-by-zero to skip.
            if direction == "up" and b > 0 and b >= floor:
                out.append((metric, a, b, float("inf")))
            continue
        delta = (b - a) / a
        fired = delta >= jump if direction == "up" else -delta >= jump
        if fired and max(a, b) >= floor:
            out.append((metric, a, b, delta))
    return out


def simulate(week, n_runs, sickness, rng):
    """sickness in [0,1]: how much harder the fleet is finding its work."""
    fleet = []
    for i in range(n_runs):
        rid, ctx, turns = f"w{week}-r{i:03d}", 4000, []
        target = max(6, min(int(rng.gauss(14 + 26 * sickness, 4)), STEP_BUDGET + 4))
        froze = target - 5 if rng.random() < 0.25 + 0.45 * sickness else None
        for turn in range(1, target + 1):
            late = turn / target
            ctx += max(int(rng.gauss(1400 + 2200 * sickness, 400)), 100)
            calls = rng.randint(1, 3)
            turns.append(dict(
                run_id=rid, week=week, turn=turn, context_tokens=ctx,
                tool_calls=calls,
                tool_errors=sum(rng.random() < 0.04 + 0.2 * late * (0.4 + sickness)
                                for _ in range(calls)),
                cost_usd=round(ctx * 3e-6 + 0.016, 5),
                progress=rng.random() < max(0.05, 0.85 - 0.55 * late - 0.35 * sickness),
                state_hash=f"{rid}:frozen" if froze and turn >= froze else f"{rid}:s{turn}"))
        h = run_health(turns)
        done = h["burn"] < 1.0 and not h["stalled"] and rng.random() < 0.9
        fleet.append((h, done, done and rng.random() > 0.04 + 0.22 * sickness,
                      rng.random() < 0.05 + 0.25 * sickness,    # escalated
                      rng.random() < 0.08 + 0.20 * sickness,    # resumed
                      rng.random() < 0.02 + 0.06 * sickness))   # crashed
    return fleet


if __name__ == "__main__":
    rng = random.Random(7)
    prev = fleet_report(simulate(31, 300, 0.05, rng))
    this = simulate(32, 300, 0.22, rng)
    curr = fleet_report(this)

    print("FLEET REPORT                    week 31   week 32")
    for k in ("healthy_rate", "degrading_rate", "stalled_rate", "exhausted_rate",
              "false_completion_rate", "escalation_rate", "resume_rate", "crash_rate"):
        print(f"  {k:<28} {prev[k]:6.1%}    {curr[k]:6.1%}")
    for k in ("median_turns", "p90_turns", "cost_per_run", "cost_per_successful_task"):
        print(f"  {k:<28} {prev[k]:6.2f}    {curr[k]:6.2f}")

    print("\nTREND ALERTS (week 31 -> week 32)")
    for metric, a, b, d in trend_alerts(prev, curr) or [("none", 0, 0, 0)]:
        arrow = "NEW" if d == float("inf") else f"{d:+.0%}"
        print(f"  [PAGE] {metric}: {a:.3f} -> {b:.3f} ({arrow})")

    print("\nWORST THREE RUNS THIS WEEK (what on-call opens first)")
    for h, done, ok, *_ in sorted(this, key=lambda r: -r[0]["burn"])[:3]:
        loop = f"loop@turn {h['loop_started_at']}" if h["loop_started_at"] else "no loop"
        print(f"  {h['run_id']}  {classify(h, done, ok):<10} turns={h['turns']:>2} "
              f"burn={h['burn']:.2f} progress={h['progress_rate']:.2f} "
              f"ctx={h['final_context'] // 1000}k  {loop}")
```

Here's what it actually prints.

```
FLEET REPORT                    week 31   week 32
  healthy_rate                  91.3%     78.0%
  degrading_rate                 1.3%     10.7%
  stalled_rate                   2.3%      3.0%
  exhausted_rate                 0.0%      2.0%
  false_completion_rate          5.0%      6.3%
  escalation_rate                9.0%      8.0%
  resume_rate                   11.0%     14.0%
  crash_rate                     1.7%      2.3%
  median_turns                  15.00     19.00
  p90_turns                     20.00     24.00
  cost_per_run                   0.99      1.68
  cost_per_successful_task       1.20      2.06

TREND ALERTS (week 31 -> week 32)
  [PAGE] exhausted_rate: 0.000 -> 0.020 (NEW)
  [PAGE] median_turns: 15.000 -> 19.000 (+27%)
  [PAGE] cost_per_successful_task: 1.198 -> 2.058 (+72%)
  [PAGE] healthy_rate: 0.913 -> 0.780 (-15%)

WORST THREE RUNS THIS WEEK (what on-call opens first)
  w32-r033  exhausted  turns=31 burn=1.25 progress=0.45 ctx=64k  loop@turn 27
  w32-r066  exhausted  turns=31 burn=1.23 progress=0.48 ctx=60k  loop@turn 27
  w32-r249  exhausted  turns=30 burn=1.14 progress=0.37 ctx=58k  no loop
```

**Cost per run went up 70%, and cost per successful task went up 72%** — but only the second number tells you that you're getting *less* for the money, because the first one could just mean you did harder work. Watch them side by side and the story is unambiguous.

**The `stalled_rate` and `false_completion_rate` alerts did not fire**, even though both numbers went up. That's the absolute floor and the relative-jump threshold doing their job: 5.0% to 6.3% on three hundred runs is noise, and paging on it is exactly how you train people to ignore the channel. A monitoring system that fires four alerts is a monitoring system people read.

**`exhausted_rate` fired on a zero baseline**, which is a real trap in trend alerting — the natural implementation divides by last week's value, sees a zero, and silently skips the rule. Going from "never happens" to "happens 2% of the time" is one of the loudest signals you'll ever get, and the code handles it explicitly rather than crashing or shrugging.

**And `loop@turn 27`** is the per-turn state hash earning its keep. On-call opens `w32-r033`, jumps straight to turn 27, and reads three turns instead of thirty-one. That number does not exist in any per-run aggregate, at any level of dashboard sophistication, because the information was thrown away before the dashboard ever saw it.

## Say it in one breath

"Once a unit of work lasts an hour instead of 200 milliseconds, you're not serving requests anymore, you're supervising jobs — few of them, each expensive, each stateful, each individually worth opening — so averages get thin, single failures matter, and the defect happens twenty turns before the outcome tells you anything. The move that makes everything else possible is instrumenting *per turn* rather than per run: turn index, tokens in and out, context size, tool calls and errors, latency, cumulative cost, a progress signal, and a state hash — because per-run aggregates structurally hide drift, exhaustion, stalls, and false completion, and no dashboard can recover a story from its own summary. Then seven charts: quality against turn index, run-length distribution where a fattening tail means agents are struggling, budget-exhaustion rate, false-completion rate caught by verifiers, stall rate, resume and crash counts, and escalation rate — watching escalations fall as anxiously as watching them rise. Alert on rates and trends rather than individual runs, because with a healthy 3% exhaustion rate and two thousand runs a day, per-run alerts page you sixty times for a system that's working, and within a week nobody reads the channel. Debug by trace first, use the state hashes to find the exact turn things diverged, replay from the checkpoint before it, and turn the trace into a regression test. Control cost with per-run caps, an org budget that degrades in tiers instead of cliff-edging, a supervisor that kills demonstrably stalled runs, and — the framing that matters — cost per *successful* task, because a cheap run that fails is the most expensive kind you have."

## What an interviewer is really testing

They want to know whether you've actually operated one of these, and the fastest tell is whether you reach for per-turn granularity unprompted — because everyone who has debugged a real long-horizon failure has had the experience of staring at a per-run row that contained none of the information they needed.

The second tell is alerting maturity: if you propose paging on individual failed runs, you've never been on the receiving end of that pager, and if you propose rates, trends, absolute floors, and two-window persistence, you have.

Naming cost per successful task rather than cost per run is a small phrase that carries a lot of signal, since it shows you understand that failures are the expensive part and that the finance dashboard can look perfectly healthy while the fleet rots.

The strongest single move is connecting the instrumentation back to the failure modes explicitly — "the state hash is what makes stalls mechanically detectable, and the turn index is what makes drift a curve instead of a vibe" — because that proves you designed the telemetry from the failure modes backwards rather than logging whatever was convenient.

And if you volunteer the human side — that most agent alerts should be a daily review rather than a page, and that an escalation queue nobody has time to read becomes a rubber stamp that manufactures false confidence in your oversight — you're describing an operable system rather than a monitored one, which is the distinction the question is really after.

## Further reading

- [OpenTelemetry GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — `invoke_agent`, `execute_tool`, `plan`; `gen_ai.usage.input_tokens` / `output_tokens`; `gen_ai.conversation.id`.
- [Google SRE Book: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) — alert fatigue, "every page should be actionable," symptoms over causes.
- [Langfuse: LLM-as-a-judge evaluators](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge) — running evaluators on live traffic with deterministic per-observation sampling.
- [LangSmith: Online evaluations](https://docs.langchain.com/langsmith/online-evaluations) — filters plus sampling rate on production traces.
- [Arize AX: Run online evals on traces](https://arize.com/docs/ax/evaluate/run-evals-on-traces) — continuous evaluation over production spans.
- [Arize Phoenix](https://arize.com/docs/phoenix) — open-source, OpenTelemetry-native tracing and evaluation for agents.
- [Braintrust docs](https://www.braintrust.dev/docs) — experiments, logging, and scoring production traffic.
- [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — progress files, session structure, what the harness owns rather than the model.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — `traceparent` and the correlation-ID discipline that makes multi-hop runs reconstructible.
- [METR: Measuring AI Ability to Complete Long Tasks](https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/) — why run lengths keep growing, and why your operational assumptions have a shelf life.
