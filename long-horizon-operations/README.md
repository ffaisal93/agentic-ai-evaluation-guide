# Long-Horizon Agent Operations

Most agent material — courses, tutorials, even good books — stops at tool calling. You learn to give a
model some functions, watch it call them, and the demo works. Then you ship something that runs for
forty turns instead of four, and you meet an entirely different class of problem that nobody warned you
about.

This track is about that second class of problem: what breaks when an agent runs long.

The failures here are quiet ones. The agent's context slowly fills with its own noise until it forgets
what you originally asked. A retry policy that looks sensible on paper multiplies against a loop and
burns an entire budget on one stubborn subtask. The agent announces it finished, confidently, and it
did not — and because "done" ends the run, nobody finds out until a customer does. None of these throw
an exception. None of them show up in a five-turn eval. They only appear at length, which is exactly
why they're the thing worth learning if you want to sound like someone who has actually run agents in
production rather than someone who has read about them.

## The chapters

Start with **[the introduction](01-introduction.md)** for why this gap exists and how to use the track
if you're interviewing. Then:

- **[Context drift](02-context-drift.md)** — why turn 40 is a different animal than turn 4. What
  accumulates in a context window, the distinct degradation modes (goal drift, instruction decay,
  lost-in-the-middle, context poisoning), how to detect drift instead of guessing, and mitigations
  ranked by what they really buy you.
- **[Measuring degradation over a long run](03-measuring-degradation.md)** — the evaluation companion.
  Why single-turn evals are structurally blind to this, turn-indexed scoring, the degradation curve as
  the artifact you report, soak tests, and replay-based regression testing.
- **[Retry budgets](04-retry-budgets.md)** — how a well-meaning agent burns your whole budget. Retry
  amplification arithmetic, why agents are worse than ordinary software here, backoff and jitter,
  circuit breakers, and making the remaining budget visible to the model so it can finish gracefully.
- **[False completion](05-false-completion.md)** — the agent that says "done" and isn't. The taxonomy
  of false completion claims, the principle that a self-report is not evidence, completion criteria a
  machine can check, no-progress watchdogs, and designing so honest failure is rewarded.
- **[Checkpoints and resume](06-checkpoint-resume.md)** — making a long run survivable. What a
  checkpoint must contain including the side-effect log, replay safety and idempotency, write-ahead
  logging, compensation, and when to put an irreversible action behind a human gate instead.
- **[Handoff](07-handoff.md)** — passing the baton without dropping it. The handoff packet as a
  designed artifact, the four kinds of handoff, and why a good handoff is the *cure* for context drift.
- **[Operating a fleet](08-operating-it.md)** — supervising long-lived jobs rather than serving
  requests. Per-turn instrumentation, the dashboards that catch these bugs, alerting that doesn't
  become noise, and cost control at fleet scale.

Every chapter closes with a "say it in one breath" summary and a note on what an interviewer is really
testing with that topic, plus runnable Python for the mechanisms that deserve code.

## How this relates to the rest of the guide

The numbered chapters (`01_` through `12_`) cover evaluating agents. The
[design patterns track](../agentic-design-pattern/README.md) covers architecting them, and several of
its patterns are the *shapes* whose operational failures this track examines up close — Pattern 11
(Goal Setting and Monitoring) and Pattern 12 (Exception Handling) especially.
`AGENT_ENGINEERING_FOUNDATIONS.md` covers building one hands-on.

If you're preparing for interviews, this material is disproportionately valuable: naming these failure
modes unprompted is one of the clearest signals that you've operated a real system rather than built a
demo.
