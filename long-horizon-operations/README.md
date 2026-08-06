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

## What's here now

- **[Context drift](02-context-drift.md)** — why turn 40 is a different animal than turn 4. What
  accumulates in a context window, the distinct ways it degrades (goal drift, instruction decay,
  lost-in-the-middle, context poisoning), how to actually detect drift instead of guessing, and the
  mitigations ranked by how much they really buy you.
- **[Measuring degradation over a long run](03-measuring-degradation.md)** — the evaluation companion.
  Why single-turn evals are structurally blind to this, how to build turn-indexed scoring, the
  degradation curve as the artifact you report, soak tests, and replay-based regression testing.
- **[Retry budgets](04-retry-budgets.md)** — how a well-meaning agent burns your whole budget. Retry
  amplification and the arithmetic of nested retries, why agents make this worse than ordinary
  software, backoff and jitter, circuit breakers, and the agent-specific move most people miss:
  making the remaining budget visible to the model so it can wrap up gracefully.

## Still to come

Four chapters are planned and not yet written: **false completion** (the agent that says "done" and
isn't), **checkpoints and resume**, **handoff patterns**, and **operating a fleet of long-running
agents**. The first three chapters stand on their own in the meantime.

## How this relates to the rest of the guide

The numbered chapters (`01_` through `12_`) cover evaluating agents. The
[design patterns track](../agentic-design-pattern/README.md) covers architecting them, and several of
its patterns are the *shapes* whose operational failures this track examines up close — Pattern 11
(Goal Setting and Monitoring) and Pattern 12 (Exception Handling) in particular. `AGENT_ENGINEERING_
FOUNDATIONS.md` covers building one hands-on.

If you're preparing for interviews: this material is disproportionately valuable, because naming these
failure modes unprompted is one of the clearest signals that you've operated a real system rather than
built a demo.
