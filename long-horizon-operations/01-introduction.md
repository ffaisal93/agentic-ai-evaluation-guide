# The operational reality nobody teaches

Here is a comment I saw about agentic AI courses, and it is one of the sharpest things written on the
subject:

> Most courses stop at tool calling and skip the operational reality — context drift after 30+ turns,
> retry budget exhaustion from looping tool calls, agents that silently self-report completion when
> they're actually stuck. If you find one that covers failure recovery and checkpoint/handoff patterns,
> that's the signal it's worth your time.

That comment is a filter, and it is a good one. This track exists because the filter is right.

## Why the gap exists

Think about how agent material gets written. Someone builds a demo, the demo works, and the demo becomes
the tutorial. Demos are short by nature — you wire up two tools, ask a question, watch the model call
them in the right order, and everyone claps. That teaches you the *shape* of an agent, which is genuinely
worth knowing, and it is where the overwhelming majority of courses stop.

The trouble is that the shape is the easy part. What separates a demo from a system is not the
architecture, it is what happens on turn forty, when the context window is three-quarters full of the
agent's own failed attempts, the retry logic has quietly consumed most of the step budget on one stubborn
API call, and the model — fluent, confident, and completely wrong — announces that the task is complete.

None of those failures throw an exception. That is the whole problem. A crash is a gift: it is loud, it
has a stack trace, and it stops. These failures are silent. They produce output that looks fine, cost
money that looks normal until you check the invoice, and terminate runs that look successful right up
until a customer tells you otherwise.

## Why these bugs only appear at length

There is a structural reason short demos cannot surface any of this, and it is worth stating plainly
because it explains the whole category.

Every one of these failures is *cumulative*. Context drift is the slow accumulation of noise in a
window that started clean. Budget exhaustion is the multiplication of small retry decisions that were
each individually reasonable. False completion becomes likely precisely when the agent has been
struggling for a while and "declaring victory" starts to look like the path of least resistance. Stalls
require enough turns for a loop to form.

Run any of these systems for three turns and they behave beautifully. Run them for sixty and the
arithmetic catches up with you. This is also why your evaluation suite probably cannot see them: if
your test tasks are five turns and your production runs are sixty, your eval is structurally blind to
your actual failure mode, and it will keep reporting green while users experience red.

## What this track covers

Seven chapters, each on one piece of the problem. They are written to be read in order but they stand
alone, so if you came here for one specific thing, go take it.

**[Context drift](02-context-drift.md)** — why turn 40 is a different animal than turn 4. What
accumulates in a long-running context window, the distinct ways it degrades (goal drift, instruction
decay, lost-in-the-middle, context poisoning, error-loop pollution), how to actually *detect* drift
rather than guess at it, and mitigations ranked by how much they genuinely buy you.

**[Measuring degradation over a long run](03-measuring-degradation.md)** — the evaluation companion to
the previous chapter. Turn-indexed scoring, the degradation curve as the artifact you actually report,
soak tests, and replay-based regression testing that reproduces a rot deterministically.

**[Retry budgets](04-retry-budgets.md)** — how a well-meaning agent burns your whole budget. The
arithmetic of nested retries, why agents are worse at this than ordinary software, backoff and jitter,
circuit breakers, and the move most people miss: making the remaining budget visible to the model so it
can wrap up gracefully instead of dying mid-thought.

**[False completion](05-false-completion.md)** — the agent that says "done" and isn't. The taxonomy of
ways a completion claim can be false, the central principle that a self-report is not evidence, writing
completion criteria a machine can actually check, no-progress watchdogs, and designing so that honest
failure is a rewarded outcome rather than something the agent learns to avoid.

**[Checkpoints and resume](06-checkpoint-resume.md)** — making a long run survivable. What a checkpoint
must contain (including the side-effect log, which is what makes resume *safe* rather than merely
possible), replay safety and idempotency, write-ahead logging, compensation when undo is possible, and
human gates for when it isn't.

**[Handoff](07-handoff.md)** — passing the baton without dropping it. The handoff packet as a designed
artifact, the four kinds of handoff, and the connection that ties this track together: a good handoff is
the *cure* for context drift, because when a window is too polluted to continue, the fix is a clean
session that inherits knowledge without inheriting noise.

**[Operating a fleet](08-operating-it.md)** — what changes when you are supervising long-lived jobs
rather than serving requests. Per-turn instrumentation as the thing that makes every failure in this
track visible at all, the dashboards that catch them, alerting that does not become noise, and cost
control at fleet scale.

## How to use this if you are interviewing

Read the comment at the top of this page again, but from the other side of the table. The reason it
works as a filter for courses is the same reason it works as a filter for *candidates* — and
interviewers know it.

Almost everyone can describe a tool-calling loop. Very few people, unprompted, will say "and around
turn thirty this starts to drift, so I'd re-ground the goal every N turns and watch instruction-adherence
by turn index." That sentence cannot be faked from a tutorial. It is the sound of someone who has
watched a system rot in production, and it moves you into a different category within about ten seconds.

So as you read, collect the *failure modes* specifically. Each chapter closes with a "say it in one
breath" summary and a short note on what an interviewer is really testing with that topic. Those two
sections are the interview payload; the rest is the understanding that makes them credible when someone
pushes back.

The habit worth building is simple: whenever you finish describing a design, name what breaks about it
at length before anyone asks. That single move — volunteering the failure mode instead of waiting to be
caught by it — is most of what separates a senior answer from a competent one.
