# Real-World Testing: From Offline Benchmarks to Live Production

> "The offline number told us the new agent was 6% better. We shipped it. Task
> completion dropped 4% and refund requests doubled. The benchmark measured a
> world that did not exist."

Offline evaluation answers *"is this agent better on the data we already have?"*
Real-world testing answers a harder and more valuable question: *"is this agent
better for the users we actually have, on the traffic they actually send, given
the way they actually react to it?"* Those are not the same question, and the
gap between them is where most agent regressions hide.

This chapter is about closing that gap deliberately — with a staged rollout
ladder, honest statistics, and guardrails that catch harm before it scales.

---

## Why It Matters: Offline Scores Do Not Guarantee Real-World Success

An offline eval is a photograph of the past. It scores your agent against a
fixed set of prompts, trajectories, or graded rubrics. That is enormously useful
for catching regressions cheaply and fast — but it is silent about everything
that only exists at runtime:

- **Distribution shift.** Your eval set was sampled weeks ago. Live traffic
  drifted: new intents, new phrasing, a product launch that changed what users
  ask. The agent that wins offline can lose on traffic the eval never saw.
- **Feedback loops.** A recommendation agent changes what users click, which
  changes tomorrow's training and eval data. The agent partly *creates* its own
  test set. Offline evals assume a static world; production is reflexive.
- **Human reaction.** Whether a support agent's answer actually *resolves* the
  ticket depends on the human reading it — did they retry, escalate, churn? No
  offline judge observes that downstream behavior.
- **Latency, cost, and truncation.** Offline runs are patient and generous. In
  production a 9-second p95 makes users abandon before the agent finishes, and a
  token budget truncates the reasoning that made the offline answer good.
- **Second-order effects.** A more "helpful" agent that hands out refunds more
  freely scores great on user satisfaction and quietly destroys margin.

Offline eval is necessary — it is your fast, cheap, deterministic first gate.
But for some qualities it is structurally incapable of being ground truth.

---

## Core Intuition: Production Is the Only Ground Truth for Some Qualities

There are three kinds of agent quality, and they need different evidence:

| Quality type | Example | Best measured by |
|---|---|---|
| **Intrinsic** | Is the SQL syntactically valid? Did it call the right tool? | Offline eval — cheap, deterministic, reproducible |
| **Judgment** | Is this answer helpful, safe, on-brand? | Offline LLM-judge / human raters, *calibrated against* online |
| **Consequential** | Did the ticket get resolved? Did the user come back? Did revenue move? | **Only production.** No offline proxy is trustworthy without validation. |

The rule of thumb: **the further a quality sits from the model's output token and
the closer it sits to a human's downstream decision, the less an offline number
can be trusted.** You can measure "valid JSON" offline forever. You cannot
measure "did this reduce churn" anywhere but in the real world.

This is why mature teams treat offline eval as a *filter* and online eval as the
*verdict*. Offline eval decides what is allowed to be tested on real users.
Production decides what is actually good.

---

## The Rollout Ladder

Do not jump from a green offline dashboard straight to 100% of users. Climb a
ladder where each rung is cheaper to fail on than the next and catches a
different class of problem.

```
   Offline eval  ──►  Shadow  ──►  Canary  ──►  A/B (controlled)  ──►  Full rollout
   (no users)       (0% impact)   (1-5%)        (5-50%)               (100%)
```

| Rung | Users affected | What it catches | What it cannot catch |
|---|---|---|---|
| **1. Offline eval** | None | Regressions on known cases; broken tools; format/safety failures | Distribution shift; real user reaction; downstream outcomes |
| **2. Shadow mode** | None (agent runs, output discarded) | Crashes, latency, cost, tool errors, drift **on real live traffic**; output diffs vs. incumbent | Anything requiring a user to *see* the output (resolution, satisfaction, revenue) |
| **3. Canary** | Tiny slice (1–5%) | Operational blowups at real scale: error spikes, latency regressions, cost overruns, obvious quality collapse | Small effects (underpowered); long-horizon outcomes |
| **4. A/B test** | Controlled split (e.g. 50/50) | The *causal* effect on goal + guardrail metrics with statistical rigor | Effects smaller than your MDE; effects slower than your test window |
| **5. Full rollout** | Everyone | — (this is the decision, monitored by guardrails) | — |

Each rung buys down a specific risk. Shadow buys down *operational* risk with
zero user exposure. Canary buys down *catastrophic* risk with tiny exposure. A/B
buys down *decision* risk — it is the only rung that tells you whether the new
agent is genuinely, causally better. Skipping rungs is how you turn a bad deploy
into a public incident.

---

## A/B Testing for Agents, In Depth

A/B testing (an *online controlled experiment*) randomly assigns units to
variants, then compares metrics. Randomization is what makes the comparison
causal: because assignment is independent of everything else, any statistically
significant metric difference is caused by the variant, not by confounders.

The mechanics are classic. What makes agents *harder* than a button-color test
is described after the fundamentals.

### Unit of randomization

Pick the wrong unit and every downstream number is wrong.

- **Per-request** randomization gives the most power (most units) but leaks: the
  same user gets the old agent on message 1 and the new one on message 3, so the
  experience is incoherent and carryover contaminates both arms.
- **Per-user (or per-session)** randomization is usually correct for
  conversational agents: a user has one consistent experience for the whole test.
  Fewer units, less power, but valid.
- **Per-cluster** (per-account, per-team, per-geo) is needed when users interact
  — see network effects below.

The unit of randomization must match (or be coarser than) the unit of analysis.
Randomize by user, analyze by user. Randomizing by user but computing
per-message significance understates variance and inflates false positives.

### Metrics: goal vs. guardrail

Separate the metric you are trying to *move* from the metrics you refuse to
*break*.

- **Goal (success) metric** — the thing the change is supposed to improve, e.g.
  task-completion rate, tickets resolved without escalation.
- **Guardrail metrics** — things that must not regress even if the goal
  improves: p95 latency, cost per task, safety-violation rate, escalation rate,
  refund rate. Microsoft's and Yahoo's experimentation write-ups stress that
  guardrails are what keep a "winning" experiment from silently causing harm.

### The statistics you must not skip

**Power and Minimum Detectable Effect (MDE).** Before running, ask: *what is the
smallest true improvement worth detecting, and can this test see it?* For a
two-proportion test comparing rates \( p \) (control) and \( p + \delta \)
(treatment) at significance \( \alpha \) and power \( 1-\beta \), the per-arm
sample size is approximately:

\[
n \approx \frac{\left(z_{1-\alpha/2} + z_{1-\beta}\right)^2 \, \big(p(1-p) + (p+\delta)(1-p-\delta)\big)}{\delta^2}
\]

With \( \alpha = 0.05 \) (\( z \approx 1.96 \)), power \( 0.8 \)
(\( z \approx 0.84 \)), and roughly \( p(1-p) \approx (p+\delta)(1-p-\delta) \),
this collapses to the useful rule of thumb:

\[
n \approx \frac{16 \, p(1-p)}{\delta^2}
\]

Example: baseline resolution \( p = 0.60 \), you want to detect an absolute
\( \delta = 0.02 \) (2 points). Then
\( n \approx 16 \times 0.24 / 0.0004 = 9{,}600 \) users **per arm**. Halving the
MDE to 1 point quadruples the requirement to ~38,400 per arm. **MDE is the
single most under-appreciated number in agent experiments** — teams routinely
run a two-week test that never had the power to see the effect they cared about,
then over-interpret the noise.

**Significance and confidence intervals.** Report the lift *with a confidence
interval*, not a bare p-value. "Resolution +1.8% (95% CI: +0.4% to +3.2%)" tells
you both direction and precision. A CI that includes 0 means "not detectably
different at this sample size" — which is not the same as "no effect."

**Variance reduction (CUPED).** You can often halve the sample size (or double
the speed) without touching \( \alpha \) or power by using pre-experiment data.
CUPED (Controlled-experiment Using Pre-Experiment Data) subtracts a covariate
\( X \) (typically the same metric measured *before* the experiment) that is
correlated with the outcome \( Y \):

\[
Y_{\text{cuped}} = Y - \theta\,(X - \bar{X}), \qquad \theta = \frac{\mathrm{Cov}(Y, X)}{\mathrm{Var}(X)}
\]

Because \( X \) is pre-treatment it cannot be affected by the variant, so
subtracting it removes variance without biasing the estimate. Microsoft's
experimentation platform reports variance reductions that meaningfully shorten
tests; the reduction is roughly \( \rho^2 \), the squared correlation between
\( X \) and \( Y \).

### Why agents are harder than classic A/B

1. **Long-horizon outcomes.** A button color's effect is visible in a click,
   now. An agent's true effect — did the user's problem *stay* solved, did they
   renew in 60 days — unfolds over weeks. If you stop the test at day 3 you
   measure the short-term proxy, which can point the *opposite* way from the
   long-term outcome (a chattier agent delights users this week and exhausts them
   next month).

2. **Feedback loops.** The agent shapes the data that trains and evaluates the
   next agent. A retrieval agent that surfaces certain docs makes those docs get
   clicked, which makes them rank higher, which… The experiment's own effect
   contaminates the baseline over time. Keep tests short enough that the loop has
   not yet closed, and re-baseline often.

3. **Novelty and primacy effects.** Users react to *change*, not just to
   quality. A new agent voice gets a curiosity bump (novelty) that decays, or a
   confusion dip (primacy) that recovers. Measure the trend over the test window,
   not just the average — if the lift is decaying toward zero, you are looking at
   novelty, not value. Segment new vs. returning users; novelty lives in the
   returning cohort.

4. **Network effects / interference.** A/B testing assumes one unit's treatment
   does not affect another unit's outcome (SUTVA). Agents break this constantly:
   a negotiation agent that gets better deals does so partly *at the expense of*
   control-arm counterparties; a marketplace agent that surfaces more inventory
   shifts demand away from other users. When units interact, per-user
   randomization is biased. LinkedIn's "A/B test of A/B tests" and Airbnb's
   cluster-randomization work show the fix: randomize by **cluster** (network
   community, market, geo) so that spillover stays inside a variant, then analyze
   at the cluster level. You pay in power; you buy back validity.

---

## Shadow Mode Mechanics

In **shadow mode** the candidate agent runs on 100% of real, live traffic in
parallel with the incumbent — but its output is *never shown to the user and
never acted on*. It is a dry run against reality.

```
                  ┌─────────────────┐
   live request ─►│  Incumbent agent│─► response ──► USER
        │         └─────────────────┘
        │ (mirrored, async)
        ▼
   ┌─────────────────┐
   │ Candidate agent │─► response ──► /dev/null + logs + diff vs. incumbent
   └─────────────────┘
```

What shadow catches that offline cannot:

- **Real-traffic operational behavior**: crash rate, exception types, p50/p95/p99
  latency, token/cost per request, tool-call error rates — on the actual
  distribution of live inputs, not a curated eval set.
- **Drift and coverage gaps**: prompts the candidate has never seen, tools that
  time out under real load, context windows that overflow on real conversations.
- **Output divergence**: log where candidate and incumbent *disagree* and sample
  those diffs for human review — a cheap, high-signal eval set of exactly the
  cases that matter.

What shadow *cannot* catch: anything requiring the output to reach a human.
Resolution, satisfaction, revenue, escalation — all invisible in shadow because
no user ever saw the shadow output. Shadow proves the agent *can run safely at
scale*; it says nothing about whether it is *better*.

Cost caveat: shadow doubles inference spend (you run both agents on all traffic).
Sample traffic (e.g. shadow 10%) if cost matters and you only need operational
signal.

---

## Canary Analysis Mechanics

A **canary release** routes a small fraction of live users (typically 1–5%) to
the new agent and watches automated metrics against the control (baseline)
population. If canary metrics degrade beyond a threshold, roll back
automatically; if they hold, ramp: 1% → 5% → 25% → 50% → 100%.

Canary is *not* a statistically powered experiment — 1% of traffic rarely has
the sample size to detect a 1-point effect. Its job is different: **catch
catastrophic, obvious regressions with minimal blast radius.** A canary that
sees error rate jump from 0.2% to 8%, or p95 latency double, or safety
violations spike, trips a rollback in minutes. That decision does not need a
confidence interval; it needs a threshold.

Practical mechanics:

- **Compare canary vs. control, not canary vs. history.** Time-of-day and
  weekday effects will fool a canary-vs-yesterday comparison. Route control and
  canary simultaneously and diff them.
- **Automate the rollback.** Define abort criteria up front (e.g. "roll back if
  canary error rate > control + 2%, or p95 > 1.5× control") and wire them to the
  deploy system. Manual canary-watching does not scale and fails at 3 a.m.
- **Ramp on a schedule with soak time.** Hold each step long enough to see
  delayed effects (a memory leak, a cost spike) before widening exposure.
- **Run an SRM check at every ramp step** (see below) — a misconfigured router
  is the most common canary failure and it silently invalidates the comparison.

Canary and A/B overlap in mechanism (both split traffic) but differ in intent:
canary asks *"is it on fire?"* (fast, operational, tiny slice); A/B asks *"is it
better?"* (slow, statistical, powered slice).

---

## The Offline–Online Gap, and How to Measure It

The **offline–online gap** is the discrepancy between what your offline eval
predicts and what production delivers. It is not a bug to be eliminated; it is a
relationship to be *characterized*. The goal is not offline = online (impossible)
but offline *rank-correlated with* online, so offline can be trusted as a filter.

**How to measure it.** Treat each shipped change as a data point: record its
offline score delta and its online (A/B) metric delta. Over many launches you
build a scatter of (offline Δ, online Δ). Then:

- Compute **rank correlation** (Spearman \( \rho \) / Kendall \( \tau \)) between
  offline and online deltas. High rank correlation means offline is a trustworthy
  *gate* even if absolute numbers differ. The RecSys literature on "identifying
  offline metrics that predict online impact" formalizes exactly this: pick the
  offline metric with the strongest empirical link to the online outcome and
  discard offline metrics that do not predict.
- Watch for **directional disagreements** — launches where offline said better
  and online said worse. Each one is a bug in your *eval*, not just your agent.
  Do a root-cause: distribution shift? A judge that rewards verbosity users hate?
  A metric that ignores latency?

**How to close it:**

1. **Feed production back into offline.** Sample real (especially
   disagreement/failure) traffic into the offline eval set continuously. The eval
   set should track the live distribution, not a frozen snapshot.
2. **Calibrate the judge against humans, on production traffic.** If offline uses
   an LLM judge, periodically check its scores against human labels *on live
   samples*, not just on the golden set it was tuned on.
3. **Prefer offline metrics with proven online correlation.** Retire pretty
   offline metrics that do not predict online movement, however satisfying they
   are to report.
4. **Right-size the gate.** If offline–online rank correlation is high, let
   offline auto-promote to shadow. If it is low, force more traffic up the ladder.
   The gate's strictness should be a function of how much you trust it.

---

## Worked Example: A/B Lift with CI + SRM Check on Run Logs

The code below takes agent run logs (one row per user, with the variant they were
assigned and whether their task succeeded), and does two things every honest
readout needs:

1. A **sample-ratio-mismatch (SRM) check** — a chi-square test that the observed
   split matches the intended split. If SRM fires, **stop**: the experiment is
   compromised and the lift number is meaningless.
2. The **lift with a 95% confidence interval** on the difference of two
   proportions (unpooled/Wald standard error), plus a two-proportion z-test.

```python
import math
from dataclasses import dataclass

# --- Input: aggregate your run logs to per-arm (n_users, n_successes) ---
# One row per user (unit of randomization == unit of analysis).
control_n,   control_succ   = 10_142, 6_071   # baseline agent
treatment_n, treatment_succ = 9_958,  6_129   # candidate agent
intended_split = 0.50                          # fraction intended for control


def normal_cdf(z: float) -> float:
    """Standard normal CDF via erf (no scipy dependency)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


@dataclass
class SRMResult:
    chi_square: float
    p_value: float
    flagged: bool


def srm_check(n_a: int, n_b: int, expected_frac_a: float,
              threshold: float = 0.0005) -> SRMResult:
    """Chi-square goodness-of-fit test for sample ratio mismatch (1 dof).

    threshold=0.0005 follows Microsoft's Experimentation Platform default,
    chosen conservatively to keep false SRM alarms rare.
    """
    total = n_a + n_b
    exp_a = total * expected_frac_a
    exp_b = total * (1.0 - expected_frac_a)
    chi_sq = (n_a - exp_a) ** 2 / exp_a + (n_b - exp_b) ** 2 / exp_b
    # Survival function of chi-square with 1 dof:  P(X > x) = 2*(1 - Phi(sqrt(x)))
    p_value = 2.0 * (1.0 - normal_cdf(math.sqrt(chi_sq)))
    return SRMResult(chi_sq, p_value, flagged=p_value < threshold)


@dataclass
class LiftResult:
    p_control: float
    p_treatment: float
    abs_lift: float
    rel_lift: float
    ci_low: float
    ci_high: float
    z: float
    p_value: float
    significant: bool


def ab_lift(c_n, c_succ, t_n, t_succ, alpha: float = 0.05) -> LiftResult:
    """Absolute lift on a success rate with a Wald 95% CI and z-test."""
    p_c = c_succ / c_n
    p_t = t_succ / t_n
    abs_lift = p_t - p_c
    rel_lift = abs_lift / p_c if p_c else float("nan")

    # Unpooled SE for the confidence interval on the difference.
    se_diff = math.sqrt(p_c * (1 - p_c) / c_n + p_t * (1 - p_t) / t_n)
    z_crit = 1.959963985  # 95% two-sided
    ci_low = abs_lift - z_crit * se_diff
    ci_high = abs_lift + z_crit * se_diff

    # Pooled SE for the hypothesis test (H0: p_c == p_t).
    p_pool = (c_succ + t_succ) / (c_n + t_n)
    se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / c_n + 1 / t_n))
    z = abs_lift / se_pool if se_pool else 0.0
    p_value = 2.0 * (1.0 - normal_cdf(abs(z)))

    return LiftResult(p_c, p_t, abs_lift, rel_lift, ci_low, ci_high,
                      z, p_value, significant=p_value < alpha)


# --- 1. Gate on SRM before trusting any lift number ---
srm = srm_check(control_n, treatment_n, intended_split)
print(f"SRM chi-square = {srm.chi_square:.3f}  p = {srm.p_value:.4g}")
if srm.flagged:
    raise SystemExit("SRM DETECTED - split is broken; the lift below is invalid.")

# --- 2. Compute lift only once the split is trustworthy ---
r = ab_lift(control_n, control_succ, treatment_n, treatment_succ)
print(f"control    success rate = {r.p_control:.4f}")
print(f"treatment  success rate = {r.p_treatment:.4f}")
print(f"absolute lift = {r.abs_lift*100:+.2f} pts "
      f"(95% CI: {r.ci_low*100:+.2f} to {r.ci_high*100:+.2f})")
print(f"relative lift = {r.rel_lift*100:+.2f}%")
print(f"z = {r.z:.3f}  p = {r.p_value:.4g}  "
      f"significant={r.significant}")
```

Running it:

```
SRM chi-square = 1.684  p = 0.1943
control    success rate = 0.5986
treatment  success rate = 0.6155
absolute lift = +1.69 pts (95% CI: +0.34 to +3.04)
relative lift = +2.82%
z = 2.451  p = 0.01427  significant=True
```

Read it correctly: SRM did not fire (\( p = 0.19 \gg 0.0005 \)), so the split is
trustworthy. The candidate lifts success by **1.69 points (95% CI +0.34 to
+3.04)**, and the CI excludes 0, so the effect is detectable at this sample size.
But note the lower bound is only +0.34 — if a 0.3-point gain would not justify the
extra cost/latency, this "significant" result is not yet a *decision*. Always
compare the CI against your MDE and your guardrails, not just against zero.

> **Note on peeking.** The z-test above is a *fixed-horizon* test: it is only
> valid if you decide the sample size in advance and read the result once. If you
> watch this dashboard daily and ship the moment `p < 0.05`, your true
> false-positive rate is not 5% — empirically it inflates to ~20%+ under
> continuous peeking, and toward 100% if you peek indefinitely. Use a sequential
> test (always-valid p-values / mSPRT) if you need to monitor continuously. More
> in Pitfalls.

---

## Metrics and Guardrails

| Metric | Type | What it tells you | Watch for |
|---|---|---|---|
| Task completion / resolution rate | Goal | Did the agent actually do the job | The headline; but confirm it is not gamed by early-closing tasks |
| Escalation / handoff-to-human rate | Guardrail | Is the agent silently failing and dumping on humans | A "success" rise that just moved work to a queue you do not measure |
| p95 / p99 latency | Guardrail | Does it stay responsive under real load | Averages hide the tail where users abandon |
| Cost per task (tokens × price) | Guardrail | Unit economics | A better agent that is 3× the cost may be a worse product |
| Safety / policy-violation rate | Guardrail | Harmful, off-policy, or unsafe outputs | Must be a hard blocker, not a tradeable metric |
| Refund / concession rate | Guardrail | Second-order margin damage | The classic Goodhart trap — satisfaction up, margin down |
| User satisfaction (CSAT / thumbs) | Goal/Judgment | Perceived quality | Response bias; only a fraction rate; novelty-sensitive |
| Retention / return rate (D7, D30) | Goal (long-horizon) | Did value actually persist | Slow; needs a long test window; the truest signal |
| Containment rate | Goal | Fraction of sessions resolved without human | Can be gamed by refusing to escalate — pair with CSAT |

**Design rule:** every goal metric needs at least one guardrail that would go the
wrong way if the agent "cheated" to move the goal. Resolution rate is paired with
escalation *and* CSAT so an agent cannot win by prematurely closing tickets.

---

## Failure Modes and Pitfalls

- **Peeking / early stopping.** Repeatedly checking a fixed-horizon test and
  stopping when it turns significant inflates false positives from a nominal ~5%
  to ~20%+ (and to 100% if you peek forever). Fix: pre-register the sample size
  and read once, *or* switch to sequential / always-valid p-values designed for
  continuous monitoring.

- **Sample Ratio Mismatch (SRM).** If your 50/50 split arrives as 51.5/48.5 on
  large N, something is broken — a router bug, differential bot filtering, a
  logging join that drops one arm. SRM means the randomization assumption failed,
  so **the treatment effect is uninterpretable**. Detect with a chi-square test
  (flag at \( p < 0.0005 \)); when it fires, fix the pipeline before reading any
  lift. Notorious cause: a treatment so engaging it trips bot detection and gets
  its users filtered out (Microsoft's MSN carousel case).

- **Feedback loops.** The agent alters the data that trains/evals its successor,
  so the baseline drifts under you. Keep experiments short relative to the loop,
  re-baseline frequently, and hold out a clean slice of traffic that never sees
  the new agent.

- **Goodhart's law.** "When a measure becomes a target, it ceases to be a good
  measure." Optimize hard on CSAT and the agent learns to be sycophantic; on
  containment and it refuses to escalate. Guardrails are your defense — but only
  if they were chosen to be exactly the metric that moves when the goal is gamed.

- **Novelty / primacy effects.** Early lift may be reaction to change, not
  quality. Segment new vs. returning users and check whether the effect decays
  over the window before declaring victory.

- **Interference / SUTVA violation.** When users affect each other (marketplaces,
  social, negotiation, shared inventory), per-user randomization is biased.
  Cluster-randomize and analyze at the cluster level.

- **Underpowered tests.** Running a two-week test with no MDE calculation and
  then reading tea leaves in the noise. Compute required N *before* launch; if you
  cannot reach it, do not pretend the flat result means "no difference."

- **Guardrail blindness.** Shipping on the goal metric alone. The refund-rate
  disaster in this chapter's epigraph is a guardrail you did not watch.

---

## Monitoring and Feedback Capture

Real-world testing does not end at rollout — 100% is a *monitored* state, not a
finished one. The same discipline that gated the launch must run continuously.

- **Log every run as an evaluable trace.** Persist inputs, tool calls,
  intermediate state, final output, latency, cost, and outcome — enough to replay
  and to build tomorrow's offline eval set from real traffic.
- **Online guardrail dashboards with alerts.** Safety-violation rate, p95
  latency, cost per task, and escalation rate should have automated thresholds
  that page a human — the production analog of canary abort criteria.
- **Explicit feedback (sparse, biased, cheap).** Thumbs, ratings, "did this
  solve your problem?" Only a small, self-selected fraction responds, so treat it
  as directional, not representative.
- **Implicit feedback (dense, noisy, honest).** Retries, rephrasings,
  abandonment, escalation, copy-of-answer, follow-up questions. Behavior is
  usually a truer signal of value than a rating.
- **Human-in-the-loop review.** Route a sampled stream — weighted toward
  low-confidence outputs and shadow/canary *disagreements* — to human reviewers.
  Their labels do triple duty: catch live harm, calibrate your LLM judge against
  human ground truth, and become curated offline eval cases.
- **Close the loop.** Feed reviewed failures and production traffic back into the
  offline eval set so the next candidate is gated against the world as it is now,
  not as it was at last quarter's snapshot. This is how the offline–online gap
  gets smaller over time instead of quietly widening.

---

## Interview Questions and Answers

**Q1. Your new agent scores +6% on the offline eval. Do you ship it? Walk me
through the rollout.**
No — an offline win is permission to *start testing*, not to ship. I climb the
ladder: confirm the offline gain is real and not a leak/overfit to the eval set;
run **shadow** on live traffic to verify latency, cost, error rate, and to
collect output diffs vs. the incumbent; **canary** at 1–5% with automated
rollback on operational thresholds; then a **powered A/B** to measure the causal
effect on the goal metric *and* guardrails. Only if the A/B shows a real,
guardrail-safe lift do I ramp to 100% — and I keep monitoring after.

**Q2. What is sample ratio mismatch and why does it invalidate an experiment?**
SRM is when the observed traffic split differs from the intended split by more
than chance (e.g. an intended 50/50 arriving as 51.5/48.5 at large N). It means
randomization is broken — a router bug, differential filtering, a bad logging
join. Since the whole causal claim rests on the two arms being comparable, SRM
makes the treatment effect uninterpretable. I detect it with a chi-square
goodness-of-fit test, flagging at \( p < 0.0005 \), and I fix the pipeline before
trusting any lift.

**Q3. Why is A/B testing agents harder than testing a checkout button?**
Four reasons: (1) **long-horizon outcomes** — the true effect (did the problem
stay solved, did they renew) unfolds over weeks, and short-term proxies can point
the wrong way; (2) **feedback loops** — the agent changes the data that
trains/evaluates its successor, so the baseline drifts; (3) **novelty effects** —
users react to change, so early lift can be curiosity, not quality; (4) **network
effects** — agents in marketplaces or negotiations make one unit's treatment
affect another's outcome, violating SUTVA and biasing per-user randomization.

**Q4. Explain the peeking problem and how you would handle continuous
monitoring.**
Fixed-horizon tests are valid only if you set N in advance and read once. If you
check daily and stop when \( p < 0.05 \), you get many chances to cross the
threshold by luck, inflating the false-positive rate from ~5% to ~20%+ (→100% if
you peek forever). Options: pre-register N and read once; or, if I genuinely need
to monitor live, use a **sequential test** with always-valid p-values (e.g.
mSPRT), which controls error under continuous looking at the cost of some power.

**Q5. What is the difference between a goal metric and a guardrail metric? Give an
agent example.**
The goal metric is what the change is meant to improve (task resolution rate). A
guardrail is something that must not regress even if the goal improves (p95
latency, cost per task, safety-violation rate, escalation rate, refund rate). The
canonical trap: an agent lifts CSAT by handing out refunds freely — goal up,
refund-rate guardrail blown. Every goal metric needs a guardrail that would move
the wrong way if the agent gamed the goal.

**Q6. Shadow mode showed zero errors and great latency. Why can't you ship on
that alone?**
Because in shadow the output never reached a user. Shadow proves the agent can
*run safely at scale* — crashes, latency, cost, tool errors on real traffic — but
it is blind to everything consequential: resolution, satisfaction, revenue,
escalation, because no human ever saw or acted on the shadow output. Shadow
clears operational risk; only a canary/A/B where users actually receive the
output can tell you whether it is *better*.

**Q7. How do you measure and close the offline–online gap?**
Measure it by logging, for every launch, the offline score delta against the
online (A/B) metric delta, then computing **rank correlation** (Spearman/Kendall)
across launches. High rank correlation means offline is a trustworthy gate even
if absolute numbers differ; directional disagreements are bugs in the eval. Close
it by continuously sampling production traffic (especially failures and
shadow/canary disagreements) back into the offline set, calibrating the LLM judge
against human labels on live data, and retiring offline metrics that do not
predict online movement.

**Q8. CUPED — what is it and when does it help?**
CUPED is a variance-reduction technique that subtracts a *pre-experiment*
covariate (usually the same metric measured before the test) from the outcome:
\( Y_{\text{cuped}} = Y - \theta(X - \bar X) \) with
\( \theta = \mathrm{Cov}(Y,X)/\mathrm{Var}(X) \). Because \( X \) is
pre-treatment it cannot be affected by the variant, so the estimate stays
unbiased while variance drops by roughly \( \rho^2 \). It shines when users have
stable, autocorrelated behavior (a heavy user last week is a heavy user this
week) — exactly the case for retained agent users — and can cut required sample
size substantially, shortening the test.

---

## Further Reading

- Diagnosing Sample Ratio Mismatch in A/B Testing — Microsoft Research: https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/
- Deep Dive Into Variance Reduction (CUPED) — Microsoft Research EXP: https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/deep-dive-into-variance-reduction/
- Data-Driven Metric Development for Online Controlled Experiments (Deng & Shi, KDD 2016) — goal vs. guardrail metrics: https://exp-platform.com/Documents/2016KDDMetricDevelopmentLessonsDengShi.pdf
- Peeking at A/B Tests: Why It Matters, and What to Do About It (Johari et al., KDD 2017): http://library.usc.edu.ph/ACM/KKD%202017/pdfs/p1517.pdf
- Wish Tackles Peeking with Always-Valid p-values — Towards Data Science: https://towardsdatascience.com/wish-tackles-peeking-with-always-valid-p-values-8a0782ac9654/
- Detecting Interference: An A/B Test of A/B Tests — LinkedIn Engineering: https://engineering.linkedin.com/blog/2019/06/detecting-interference--an-a-b-test-of-a-b-tests
- Reducing Interference Bias Using Cluster Randomization (Airbnb, Management Science): https://pubsonline.informs.org/doi/10.1287/mnsc.2020.01157
- Identifying Offline Metrics that Predict Online Impact (RecSys 2025): https://dl.acm.org/doi/10.1145/3705328.3748111
- Closing the Online-Offline Gap: A Scalable Framework for Composed Model Evaluation (RecSys 2025): https://dl.acm.org/doi/10.1145/3705328.3748117
- Offline Recommender System Evaluation: Challenges and New Directions (Castells & Moffat, AI Magazine 2022): https://onlinelibrary.wiley.com/doi/10.1002/aaai.12051
- Shadow Deployment vs. Canary Release of ML Models — JFrog ML / Qwak: https://www.qwak.com/post/shadow-deployment-vs-canary-release-of-machine-learning-models
- Safely Deploying ML Models: Four Controlled Strategies (A/B, Canary, Interleaved, Shadow) — MarkTechPost: https://www.marktechpost.com/2026/03/21/safely-deploying-ml-models-to-production-four-controlled-strategies-a-b-canary-interleaved-shadow-testing/
- Guardrail Metrics: The Complete Guide — Mixpanel: https://mixpanel.com/blog/guardrail-metrics/
- CUPED in A/B Testing and Experimentation — Optimizely: https://www.optimizely.com/insights/blog/cuped-in-ab-testing-and-experimentation/

---

*Previous: offline evaluation gives you a fast, cheap gate. This chapter gave you
the ladder — shadow, canary, A/B — that turns a green offline dashboard into a
safe, causal, guardrail-checked production decision. Next: closing the loop with
continuous production monitoring as a first-class eval surface.*
