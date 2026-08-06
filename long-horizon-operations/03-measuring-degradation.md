# Measuring degradation over a long run

## Your eval is testing the wrong thing

Here's an uncomfortable question to ask about your agent's test suite.

How many turns does your longest eval case take?

If the answer is "five or six," and your agent runs sixty turns in production, then your evaluation is structurally incapable of finding your actual failure mode.

Not "might miss it."

*Cannot* find it.

You're testing turns 1 through 6, and every problem in the previous chapter lives at turn 30 and beyond.

This is a specific and very common blind spot, so it's worth being precise about why it happens.

Most evaluation practice was inherited from a world of single-turn question answering, where an eval case is one input and one expected output.

You score accuracy, you compare to last week, you ship.

That framework works fine as long as the thing you're scoring is a *function* — same input, same behavior, no history.

An agent past turn ten is not a function.

It's a process with accumulated state, and the accumulated state is the independent variable that actually predicts failure.

Scoring the process without reference to how far into it you are is like testing a car's brakes only in the first mile.

The benchmark suites don't save you either, because most of them are short by design.

Even the good agentic benchmarks lean toward tasks measured in a handful of tool calls, for the practical reason that long tasks are slow and expensive to grade.

Two exceptions are instructive.

METR's work on task length measures the "50%-task-completion time horizon" — the length of task, measured in how long a human expert takes, that a model can complete with 50% probability — and found it growing on an exponential trend with a doubling time of roughly seven months.

That's a benchmark that treats *duration* as the axis, which is exactly the right instinct.

Vending-Bench goes further and runs agents through a simulated business over runs exceeding 20 million tokens, and found failure patterns — forgotten orders, misread schedules, tangential meltdown loops — that a short eval would never surface.

And τ-bench contributed a metric worth stealing: `pass^k`, which scores whether an agent succeeds on *all* of k repeated trials rather than at least one, and it collapses the numbers dramatically — sub-25% pass^8 in the retail domain for agents that looked much better on single attempts.

The lesson from all three is the same.

Length and repetition are dimensions of your test design, not incidental details.

If you don't vary them on purpose, you're not measuring what production does.

## Building a long-horizon eval

The good news is that you don't need a new framework.

You need to change three things about the eval you already have: the tasks get longer, the scoring gets indexed by turn, and the artifact you report becomes a curve instead of a number.

**Long-task datasets.** You need eval cases that genuinely take as many turns as production does, and there are three honest ways to get them. Write them — expensive, but you control the difficulty. Harvest them from production traces, which is by far the best source because real long tasks fail in ways you'd never have imagined. Or synthesize them by chaining shorter tasks into a session with realistic dependencies between them, which is cheap and a reasonable stopgap as long as you're clear-eyed that chained tasks are easier than genuinely long ones. A rule of thumb: your longest eval case should be at least as long as your 90th-percentile production run, because otherwise your worst production behavior is off the end of your chart.

**Turn-indexed scoring.** This is the actual change. Instead of scoring the run once at the end, score the same quality metric at multiple points — turn 5, 15, 30, 50 — using the same rubric each time. That last part matters more than it sounds. If your turn-50 rubric is different from your turn-5 rubric, you can't compare them, and the whole exercise collapses. So define quality once, in a way that's evaluable at any point in a run ("does this turn follow the constraints, advance the goal, and produce valid output?"), and apply it identically throughout.

**The degradation curve.** Plot quality on the vertical axis, turn index on the horizontal, and *that plot is your deliverable*. Not the average. The average of a run that's excellent for thirty turns and terrible for twenty is a mediocre-looking number that describes neither half. The curve tells you three things a scalar can't: where the knee is, how steep the fall is, and whether it's a gradual slope (context rot) or a cliff (something specific broke, often a compaction event). When you change your compaction strategy, you compare curves, and the improvement is usually visible as the knee moving right — which is a far more honest description of what you did than "quality improved 4%."

**Time-to-first-error.** Alongside the curve, report a single number that's easy to reason about and easy to alert on: the turn index at which the run first goes wrong. Define "wrong" mechanically — first schema violation, first constraint breach, first turn whose quality drops below threshold — and report the distribution across runs, not the mean, because the mean hides the tail and the tail is what pages you at 3am. "Median time-to-first-error is turn 47, but the 10th percentile is turn 19" is a sentence that tells you exactly what to work on.

## The signals worth instrumenting

Every one of these is per-turn, and per-turn is the whole point.

**Instruction-adherence rate by turn.** The share of turns that obey your checkable system-prompt rules, including the canary instructions from the last chapter. This is your cleanest, cheapest measurement of instruction decay, and the turn where it starts sliding is your re-grounding interval, empirically determined instead of guessed.

**Goal-fidelity score by turn.** Ask the agent to restate its current objective, score the restatement against the original with a judge, and track it. It's noisier than adherence, but it's the only direct read on goal drift, and a run whose goal-fidelity slides from 0.9 to 0.5 while task quality stays flat is a run that's about to fall off a cliff you haven't reached yet.

**Output-schema validity by turn.** Binary, deterministic, free. Validate every structured output against its schema and count. Because it costs nothing and catches format drift early, this is the first thing to instrument if you're instrumenting exactly one thing.

**Tool-error rate by turn.** The fraction of tool calls that fail. Rising tool-error rate late in a run usually means the agent is guessing — flailing at arguments it no longer has good context for — and it's an excellent early warning, because errors then feed back as error-loop pollution and accelerate everything else.

**Context tokens by turn.** Log it every turn, always. The slope is a leading indicator, spikes mean a giant tool result just landed, and the total is what tells you whether you're about to hit a compaction event. Correlating quality dips against compaction boundaries is one of the highest-yield debugging moves in this whole area.

**Cost by turn.** Because context is resent on every call, cost per turn grows with the transcript, which means a 60-turn run is dramatically more expensive than ten 6-turn runs doing the same work. Tracking spend per turn makes that visible, and it's the number that makes the business case for sub-agent isolation without any hand-waving. If turn 5 costs \$0.01 and turn 55 costs \$0.14, that ratio is your argument.

**Repeated-action rate.** The share of turns whose action — tool name plus normalized arguments — the agent has already performed earlier in the run. This is the single best mechanical detector of a spiral. Healthy agents repeat a little (re-reading a file is fine); stuck agents repeat a lot, and the rate climbing past roughly half your recent turns is a reliable "this run is dead, kill it" signal.

Two of these deserve a note about interpretation.

Repeated-action rate and tool-error rate both go up for *good* reasons sometimes — a retry after a transient network failure is correct behavior.

So alert on the trend within a run, not on the absolute value, and always look at them next to the quality curve rather than alone.

## Soak tests and deliberate chaos

Two testing styles from ordinary systems engineering transfer directly, and they're underused with agents.

A **soak test** — sometimes called an endurance test — means running the system under sustained load for far longer than normal and watching for the things that only appear with time. In classic backend work you soak-test to catch memory leaks, connection-pool exhaustion, log-disk fill: problems whose defining feature is that they need hours to become visible. Agents have exactly that class of problem, and the analogy is nearly perfect. Context growth *is* a memory leak. So: take a task that would normally take fifteen turns, structure it so it takes a hundred and fifty, and run it. Not because production does that, but because whatever rots at turn 150 is already faintly rotting at turn 40, and the long run makes it big enough to see. Do this before you ship a new compaction strategy, always.

**Chaos-style injection** is the other half. Chaos engineering, in the original Netflix sense, means deliberately breaking things in a controlled way to find out whether your recovery paths actually work — because untested recovery code is just decorative. For agents, the injections are cheap and specific. Make a tool return an error at turn 20 and see whether the agent recovers or spirals. Make a tool return a *plausible but wrong* answer and see whether that fact gets challenged later or becomes gospel — this is a direct, repeatable test for context poisoning, and almost nobody runs it. Make a tool time out. Make a file the agent wrote at turn 12 change underneath it, and see whether it notices, which tests stale-context handling.

The output of a chaos run isn't pass/fail.

It's a recovery profile: did it recover, how many turns did recovery cost, and did quality return to the pre-injection level or settle permanently lower?

That last question is the interesting one, and the answer is depressingly often "settled lower."

## Replay-based evaluation

The most valuable eval data you will ever have is already being generated, for free, by production.

**Replay** means capturing a real run's full trace — every message, every tool call, every tool result, in order — and then re-running the agent against that captured trace instead of against the live world.

Tool calls are served from the recording rather than actually executed, which is what makes the run deterministic and safe.

Three things make this worth the plumbing.

It's *reproducible*. Live agent runs are non-deterministic in a dozen ways at once, and when a degradation shows up you often can't get it back. A frozen trace gives you the same starting conditions every time, so you can bisect. Change the compaction threshold, replay, compare curves. That's a real experiment.

It's *free of side effects*. You can replay a trace that involved sending emails or writing to a database without sending anything or writing anywhere, because the tool layer is a recording.

And a frozen trace becomes a *regression test*. When you find a run where the agent drifted at turn 34, that trace goes into the suite permanently, with the assertion "quality at turn 34 must be above X." Now every future change is checked against a real failure that really happened, which is worth a hundred synthetic cases. This is the same instinct as turning every production bug into a unit test; it just took the agent world a while to get there.

One caveat to state out loud, because it's the follow-up question: replay only exercises the paths the recording covers.

If your change makes the agent take a *different* action at turn 12, the recording has no result for it.

You either fall back to the live tool, or you accept that the replay diverges and treat it as a signal in itself.

Neither answer is wrong; pretending the problem doesn't exist is.

## Alerting on this in production

Production monitoring for agents usually asks "did the run fail?" and that question is nearly useless here, because drifted runs don't fail.

They complete, confidently, with worse output.

So the alerts have to be comparative, and the comparison that matters is *at the same turn index*.

Concretely, the things worth paging on.

Quality at a fixed turn index, week over week. If turn-30 quality was 0.88 last week and 0.79 this week, something changed — a model update, a prompt change, a tool that got chattier — and you want to know now, not when a customer tells you.

Median turns-to-completion, trending up. Runs getting longer for the same class of task means the agent is working harder to get to the same place, and that's usually the earliest visible symptom of a context problem.

Cost per successful task, trending up. Not cost per run, and not cost per turn — cost per *successful* task, because the failures are what you're actually paying for. A cheap run that fails is the most expensive kind.

Context tokens at turn N, trending up. If your agent used 40k tokens by turn 30 last month and 55k now, someone made a tool more verbose, and that change is silently eating your quality budget.

Compaction frequency per run. A sudden jump means either runs got longer or something is filling the window faster, and both are worth a look.

The framing to carry into an interview: for long-horizon agents, "healthy" is not a threshold, it's a *shape*.

You alert on the shape changing.

## A worked example

Here's a small, dependency-free function that takes per-turn records from one long run and produces the four things this chapter has been arguing for: the degradation curve, the first turn where a rolling quality average drops below threshold, context growth, and repeated-action rate.

Nothing exotic — standard library only, and short enough to read in one sitting.

```python
def analyze_run(records, bucket_size=10, window=5, threshold=0.7):
    """Summarize how one long agent run degraded across its turns.

    records: list of dicts with keys
        turn            int, 1-based
        quality         float in [0, 1], same rubric at every turn
        context_tokens  int, size of the context sent on that turn
        action          str, tool name + normalized args
    """
    rows = sorted(records, key=lambda r: r["turn"])
    if not rows:
        return {"curve": [], "first_bad_turn": None,
                "context_growth": None, "repeated_action_rate": 0.0}

    # 1. Degradation curve: mean quality per bucket of turns.
    buckets = {}
    for r in rows:
        b = (r["turn"] - 1) // bucket_size
        buckets.setdefault(b, []).append(r["quality"])

    curve = []
    for b in sorted(buckets):
        scores = buckets[b]
        curve.append({
            "turns": "%d-%d" % (b * bucket_size + 1, (b + 1) * bucket_size),
            "mean_quality": round(sum(scores) / len(scores), 3),
            "n": len(scores),
        })

    # 2. Time-to-first-error: first turn whose trailing rolling
    #    average of `window` turns falls below the threshold.
    first_bad_turn = None
    for i in range(window - 1, len(rows)):
        recent = [rows[j]["quality"] for j in range(i - window + 1, i + 1)]
        if sum(recent) / window < threshold:
            first_bad_turn = rows[i]["turn"]
            break

    # 3. Context growth: start, end, and average tokens added per turn.
    first, last = rows[0], rows[-1]
    span = last["turn"] - first["turn"]
    growth = {
        "start_tokens": first["context_tokens"],
        "end_tokens": last["context_tokens"],
        "tokens_per_turn": round(
            (last["context_tokens"] - first["context_tokens"]) / span, 1)
        if span else 0.0,
    }

    # 4. Repeated-action rate: share of turns doing something already done.
    seen, repeats = set(), 0
    for r in rows:
        if r["action"] in seen:
            repeats += 1
        seen.add(r["action"])

    return {
        "curve": curve,
        "first_bad_turn": first_bad_turn,
        "context_growth": growth,
        "repeated_action_rate": round(repeats / len(rows), 3),
    }
```

And a synthetic run to show the shape — quality holds until turn 30, then decays, and the agent starts revisiting old queries.

```python
if __name__ == "__main__":
    import random
    random.seed(7)

    demo = []
    for turn in range(1, 61):
        base = 0.95 if turn <= 30 else max(0.30, 0.95 - 0.02 * (turn - 30))
        demo.append({
            "turn": turn,
            "quality": round(min(1.0, max(0.0, base + random.uniform(-0.05, 0.05))), 3),
            "context_tokens": 3000 + 850 * turn,
            "action": "search:q%d" % (turn % 12),
        })

    report = analyze_run(demo)
    for row in report["curve"]:
        print("turns %-7s mean_quality=%.3f  n=%d"
              % (row["turns"], row["mean_quality"], row["n"]))
    print("first_bad_turn:", report["first_bad_turn"])
    print("context_growth:", report["context_growth"])
    print("repeated_action_rate:", report["repeated_action_rate"])
```

Running it prints:

```text
turns 1-10    mean_quality=0.931  n=10
turns 11-20   mean_quality=0.943  n=10
turns 21-30   mean_quality=0.943  n=10
turns 31-40   mean_quality=0.829  n=10
turns 41-50   mean_quality=0.645  n=10
turns 51-60   mean_quality=0.440  n=10
first_bad_turn: 45
context_growth: {'start_tokens': 3850, 'end_tokens': 54000, 'tokens_per_turn': 850.0}
repeated_action_rate: 0.8
```

Read that output the way you'd read it on a real run.

The first three buckets are flat and healthy — whatever's wrong isn't wrong at the start.

The knee is between turn 30 and 40, which is where you'd go looking in the transcript first.

`first_bad_turn: 45` lags the knee, which is expected and correct: a five-turn rolling average is deliberately slow, because you want it to ignore a single bad turn and only fire on sustained decline. If you want it to fire earlier, shorten the window and accept more false alarms — that tradeoff is yours to set, and it's the same tradeoff as any smoothed alert.

`tokens_per_turn: 850` is the leak rate. At that slope you'd cross 100k tokens somewhere around turn 115, which tells you where your compaction boundary is going to land whether you plan it or not.

And `repeated_action_rate: 0.8` says four out of five turns re-did something. Combined with a falling quality curve, that's the signature of a spiral rather than a hard task, and it's a stronger kill signal than the quality drop alone.

Two extensions worth mentioning but not writing out.

Segment the curve by whether a compaction happened in that bucket, so you can see compaction events as steps.

And normalize the horizontal axis by cumulative tokens instead of turn number when your turns vary wildly in size, since context pressure — not turn count — is the thing actually causing the decay.

## Where the rest of the eval story lives

This chapter is deliberately narrow: it's about the *turn-index* dimension, which the standard evaluation material doesn't cover because it wasn't a problem until agents got long.

Everything else about evaluation is covered properly elsewhere in this guide, and there's no sense in me restating it badly.

For metric definitions, rubric design, and how to pick what to measure at all, go to `03_metrics_and_benchmarks`.

For getting eval cases out of production and dealing with the messiness of real traffic, `08_real_world_testing`.

For eval harnesses, LLM-as-judge calibration, and running all of this in CI, `09_automated_evaluation`.

For dashboards, alert design, and the operational side of watching a live system, `12_production_monitoring`.

The mental model that stitches them together: those four chapters teach you to measure quality.

This one asks you to measure it *as a function of how long the agent has been running* — same instruments, one extra axis, completely different bugs found.

## Say it in one breath

"Single-turn evals and most benchmark suites can't see long-horizon degradation, because if your eval tasks are five turns and production runs sixty, the failures all live off the end of your chart. So you build long-task eval cases — harvested from production traces where possible — and you score the same rubric at turn 5, 15, 30, and 50, and the artifact you report is the degradation curve, not an average, because an average hides the knee. Alongside it you track instruction adherence, goal fidelity, schema validity, tool-error rate, context tokens, cost, and repeated-action rate, all indexed by turn, plus time-to-first-error as the headline number. You soak-test on purpose by running a fifteen-turn task for a hundred and fifty turns, you chaos-inject a failing or subtly-wrong tool result to see whether the agent recovers or spirals, and you freeze real traces for deterministic replay so a degradation you found once becomes a permanent regression test. And in production you alert on the shape, not the failure — quality at turn 30 versus last week, runs getting longer, cost per successful task creeping up — because drifted runs don't crash, they finish confidently with worse output."

## What an interviewer is really testing

The first thing they want to hear is that you understand your eval can be *structurally blind* — that a passing test suite tells you nothing about turn 40 if every case ends at turn 5 — because that's a reasoning failure, not a tooling gap, and it's the one that separates people who've shipped from people who've read.

Then they're listening for whether you report a curve instead of a number, since "quality by turn index" is the single move that turns a vague complaint about the agent getting worse into a debuggable, comparable artifact.

Bonus points for naming a cheap deterministic signal like schema validity or repeated-action rate, because it shows you know that not every measurement needs an LLM judge and a budget.

More points for replay, since capturing traces as regression tests is the thing that makes any of this repeatable, and most candidates never mention it.

And the closing move that lands well is stating that production alerting has to be comparative — same turn index, week over week — because that proves you've internalized the core fact of this whole topic: long-horizon agents don't fail loudly, they degrade quietly, and you only catch quiet things by watching the shape change.

## Where this comes from

- METR, "Measuring AI Ability to Complete Long Tasks" — the 50% time-horizon metric and the ~7-month doubling trend: <https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/>
- Andon Labs, "Vending-Bench: A Benchmark for Long-Term Coherence of Autonomous Agents" — 20M-token runs, meltdown loops: <https://arxiv.org/abs/2502.15840>
- Yao et al., "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains" — the `pass^k` consistency metric: <https://arxiv.org/abs/2406.12045>
- Chroma, "Context Rot: How Increasing Input Tokens Impacts LLM Performance" — degradation as a function of input length across 18 models: <https://research.trychroma.com/context-rot>
- Adobe Research, "NoLiMa: Long-Context Evaluation Beyond Literal Matching" — why needle-in-a-haystack scores overstate long-context ability; 10 of 12 models fall below half their short-context baseline at 32K tokens: <https://github.com/adobe-research/NoLiMa>
- Anthropic, "Managing context on the Claude Developer Platform" — the 100-turn web search evaluation used to measure context editing: <https://claude.com/blog/context-management>
