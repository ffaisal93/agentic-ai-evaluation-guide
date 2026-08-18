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
ladder, honest statistics, guardrails that catch harm before it scales, and the
concrete platforms, code, and war stories you need to build the system yourself
and defend it in front of a skeptical senior interviewer. By the end you should
be able to (1) sketch a rollout-and-measurement plan for a new agent version on a
whiteboard, (2) write the analysis code that turns run logs into a defensible
ship/no-ship decision, and (3) name the failure modes — SRM, peeking, novelty,
interference, Goodhart — before they name you in a postmortem.

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
But for some qualities it is structurally incapable of being ground truth. The
deep reason is a *measurement-target mismatch*: your offline eval measures a
proxy (rubric score, judge rating, exact-match) chosen because it is cheap and
observable, while the thing you actually care about (resolution, retention,
margin) is expensive and only observable downstream of a real human decision.
Every proxy is a bet that the two move together. Real-world testing is how you
check whether you won that bet — and the whole discipline of this chapter is
about making the bet honestly, hedging it with guardrails, and paying it off in
production data rather than in incidents.

> **Saying it out loud.** An offline eval is a photograph of the past — it's genuinely useful for catching regressions cheaply, but it's structurally silent about everything that only exists at runtime. Your eval set was sampled weeks ago, so distribution shift alone can flip which agent wins. Whether a support answer actually *resolved* the ticket depends on a human you never observe. Offline runs are patient, but in production a nine-second p95 makes people abandon before the agent finishes. The deep reason is a measurement-target mismatch: offline measures a proxy you picked because it's cheap and observable, while the thing you care about — resolution, retention, margin — is only observable downstream of a real human decision. Every proxy is a bet that those two move together, and real-world testing is how you check whether you won the bet in data rather than in incidents.

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
Production decides what is actually good. A useful mental model is a funnel of
*decreasing volume and increasing truth*: offline eval runs on millions of cheap
synthetic/replayed cases and is mostly right about intrinsic quality; shadow runs
on all live traffic and is right about operational behavior; canary runs on a
sliver and is right about "is it on fire"; the A/B runs on a powered slice and is
the only stage that produces a *causal, consequential* verdict. Each stage trades
volume for truth, and the art is knowing which question each stage can and cannot
answer.

> **Saying it out loud.** There are three kinds of agent quality and they need different evidence. Intrinsic — is the SQL valid, did it call the right tool — offline eval nails that forever. Judgment — is this helpful, safe, on-brand — an offline judge can do it, but only if you calibrate it against online. And consequential — did the ticket get resolved, did the user come back, did revenue move — that one is *only* measurable in production, no exceptions. The rule of thumb: the further a quality sits from the output token and the closer to a human's downstream decision, the less an offline number can be trusted. So mature teams treat offline as a filter and online as the verdict — a funnel of decreasing volume and increasing truth, where each rung answers a question the one before it couldn't.

---

## The 2025–2026 Landscape: How Agent Products Are Tested Online Today

Interviewers increasingly probe whether you know the *actual tooling* teams use,
not just the theory. Here is the state of the practice as of 2025–2026, with real
platforms and primary sources. Treat brand names as illustrations of categories,
not endorsements — the categories are what you must be able to reason about.

### Experimentation platforms (the A/B substrate)

Nobody builds significance testing, bucketing, SRM detection, and CUPED from
scratch anymore for a real product; they sit on an experimentation platform. The
2025–2026 field splits into a few archetypes:

- **Statsig** — feature flags + experimentation + product analytics + warehouse-
  native stats, and (notably for us) a first-class **AI Evals** product that runs
  *offline* grading against fixed sets **and** *online* grading of LLM outputs on
  live production traffic, then lets you promote a prompt/model version straight
  into an A/B experiment measured against business metrics. This is the clearest
  productization of the "offline gate → online verdict" loop in this chapter.
  Docs: <https://docs.statsig.com/ai-evals/overview> and product page
  <https://www.statsig.com/ai-evals>. Their engineering write-ups on
  experimentation-for-AI are worth reading:
  <https://www.statsig.com/blog/experimentation-and-ai-trend> and
  <https://www.statsig.com/blog/llm-optimization-online-experimentation>.
- **Eppo** (now part of Datadog) — warehouse-native experimentation with strong
  CUPED-style variance reduction and sequential/"peeking-safe" analysis built in;
  positions itself around trustworthy readouts and metric governance.
  <https://www.geteppo.com/>.
- **GrowthBook** — open-source, warehouse-native experimentation. Its public docs
  are an unusually good free curriculum: **CUPED**
  (<https://docs.growthbook.io/statistics/cuped>), **sequential testing / always-
  valid inference** (<https://docs.growthbook.io/statistics/sequential>), and
  **power analysis** (<https://docs.growthbook.io/statistics/power>). Case study on
  CUPED cutting runtime at the LA Times:
  <https://blog.growthbook.io/cuped-for-faster-experimentation-in-growthbook/>.
- **LaunchDarkly** — the canonical **feature-flag / progressive-delivery**
  platform; the machinery you use to *route* traffic for canaries, percentage
  ramps, kill-switches, and targeted rollouts, increasingly bundled with
  experimentation. <https://launchdarkly.com/>. (GrowthBook maintains a candid
  comparison: <https://www.growthbook.io/insights/growthbook-vs-launchdarkly>.)
- **Optimizely** — long-standing experimentation vendor; their CUPED explainer is
  a clean primer: <https://www.optimizely.com/insights/blog/cuped-in-ab-testing-and-experimentation/>.

The infra pattern that unifies them: a **feature-flag / assignment service**
decides which unit sees which agent version (deterministic hashing of a stable
unit ID → bucket), emits an **exposure/assignment log**, and a **warehouse-native
stats layer** joins exposures to outcome metrics and computes lift, CIs, SRM, and
variance-reduced estimates. If you can draw those two boxes and the log between
them, you understand 80% of every platform above.

> **Saying it out loud.** Nobody builds bucketing, significance testing, sample-ratio checks, and variance reduction from scratch anymore — you sit on a platform. Statsig, Eppo, GrowthBook, LaunchDarkly, Optimizely all differ in packaging, but the architecture underneath is identical and that's what to say in an interview. There's an assignment service that deterministically hashes a stable unit ID into a bucket and emits an exposure log, and there's a warehouse-native stats layer that joins exposures to outcomes and computes lift, confidence intervals, sample-ratio mismatch, and variance-reduced estimates. If you can draw those two boxes and the log between them, you understand about eighty percent of every one of those products — and you can reason about which one you need without repeating anyone's marketing.

### Online LLM-as-judge on sampled traffic

The biggest 2024→2026 shift is that **evaluation moved into production**. Instead
of only scoring a frozen golden set offline, teams now run an **LLM judge on a
sample of live traffic** — score, say, 1–5% of real agent responses for
helpfulness/safety/faithfulness in near-real-time, aggregate into a continuous
online-quality metric, and alert when it drifts. This turns "quality" into a
monitorable production signal that sits *next to* latency and cost.

Primary sources and tooling: Statsig's **Online Evaluation**
(<https://docs.statsig.com/ai-evals/overview>) grades live outputs and supports
shadow-testing candidate prompt versions; gateway-level online eval is described
by TrueFoundry (<https://www.truefoundry.com/blog/online-llm-evaluation-gateway>);
the LLM-observability vendors productize sampled online judging — **Langfuse**
(<https://langfuse.com/blog/2025-11-12-evals>), **Arize Phoenix**
(<https://arize.com/guides/llm-as-a-judge/>), **Braintrust**
(<https://www.braintrust.dev/articles/llm-evaluation-guide>), and **Evidently**
(<https://www.evidentlyai.com/llm-guide/llm-as-a-judge>). The universal caveat,
stressed in all of these: an online judge is itself a model that can drift and be
biased (length bias, self-preference), so you must **calibrate it against human
labels on live samples** and treat its output as a guardrail metric, not gospel.

> **Saying it out loud.** The biggest shift from 2024 to 2026 is that evaluation moved into production. Instead of only scoring a frozen golden set, teams now run an LLM judge on one to five percent of *live* traffic, score it for helpfulness or safety or faithfulness in near-real-time, and alert when it drifts. That turns quality into a monitorable production signal sitting right next to latency and cost, which is a genuinely new capability. The universal caveat every vendor stresses: the judge is itself a model that drifts and has biases — length bias, self-preference — so you have to calibrate it against human labels on live samples, and treat its output as a guardrail metric rather than gospel.

### Shadow, replay, and offline-from-online

Two production patterns you must be able to name:

- **Shadow (mirror) traffic** — mirror live requests to the candidate agent, run
  it, and discard the output. You get operational + (sampled) quality signal on
  the true live distribution with **zero user exposure**. Vendor/engineering
  write-ups: FutureAGI (<https://futureagi.com/blog/llm-eval-shadow-traffic-canary-2026/>),
  Nadir's "Shadow Mode, Forever" (<https://getnadir.com/blog/shadow-testing-canary-rollout-llm-model-swap/>).
- **Replay / offline-from-online** — capture real production traces (inputs +
  tool results + outputs) and *replay* them against a candidate offline. This is
  how you keep the offline eval set tracking the live distribution instead of
  freezing in the past, and how you build regression suites out of real incidents.
  The 2025 LLMOps survey from ZenML across ~1,200 deployments documents how
  common trace-capture → replay → eval pipelines have become:
  <https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025>.

> **Saying it out loud.** Two patterns you should be able to name instantly. Shadow, or mirror traffic, means you send live requests to the candidate agent, run it, and throw the output away — you get operational and sampled quality signal on the true live distribution with literally zero user exposure. Replay, or offline-from-online, is the other direction: you capture real production traces including tool results and replay them against a candidate offline. Replay is what stops your offline eval set from freezing in the past, and it's how you turn every production incident into a permanent regression case. The failure mode without it is an eval suite that scores the world as it was last quarter while your traffic has moved on.

### Guardrail metrics as a first-class concept

Every serious platform now treats **guardrail metrics** as distinct from goal
metrics — metrics you monitor to make sure a "win" is not secretly causing harm,
often with their own (looser, non-inferiority-style) decision rules. Mixpanel's
guide is a clean product-side treatment
(<https://mixpanel.com/blog/guardrail-metrics/>); the academic grounding is Deng &
Shi's KDD 2016 metric-development paper
(<https://exp-platform.com/Documents/2016KDDMetricDevelopmentLessonsDengShi.pdf>).

> **Saying it out loud.** A guardrail metric is one you monitor to make sure a win isn't secretly causing harm, and the subtlety interviewers like is that guardrails get a *different decision rule* than goal metrics. A goal metric is a superiority test — did it go up. A guardrail is a non-inferiority test — can I rule out that latency got more than X percent worse. That flips the null hypothesis, and it has a consequence people miss: a guardrail that's flat with wide confidence intervals has *not* been cleared. You need the interval to exclude the harm threshold, which frequently takes more data than detecting the effect you were actually chasing.

### The offline→online correlation problem (the open problem)

The hardest, least-solved part of the landscape is knowing **whether your offline
metric predicts your online outcome at all.** The RecSys community has been
formalizing this: "Identifying Offline Metrics that Predict Online Impact" (RecSys
2025, <https://dl.acm.org/doi/10.1145/3705328.3748111>) and "Closing the Online-
Offline Gap" (RecSys 2025, <https://dl.acm.org/doi/10.1145/3705328.3748117>), with
the broader argument in Castells & Moffat's "Offline Recommender System
Evaluation: Challenges and New Directions" (AI Magazine 2022,
<https://onlinelibrary.wiley.com/doi/10.1002/aaai.12051>). The practical takeaway
that survives into agent-land: **an offline metric is only as good as its measured
rank-correlation with the online metric you actually care about**, and most teams
have *never measured that correlation*. Doing so — logging (offline Δ, online Δ)
per launch and computing Spearman/Kendall across launches — is a cheap, high-
signal, and rare practice that will make you stand out in an interview.

> **Landscape summary for interviews.** "Today an agent change flows: offline
> eval (Statsig AI Evals / Braintrust / Langfuse) → shadow + online LLM-judge on
> sampled live traffic → canary via feature flags (LaunchDarkly) → a warehouse-
> native A/B with CUPED + sequential testing + SRM checks (Statsig / Eppo /
> GrowthBook) → GA behind a kill-switch, with guardrail dashboards and replay
> feeding real traffic back into the offline set. The unsolved part is measuring
> offline→online rank correlation so you know how much to trust the first gate."

> **Saying it out loud.** Here's the least-solved part of the whole landscape, and it's a great thing to raise unprompted: most teams have never measured whether their offline metric predicts their online outcome at all. The fix is cheap — log the offline delta and the online delta for every launch, and compute a rank correlation, Spearman or Kendall, across launches. High rank correlation means offline is a trustworthy gate even though the absolute numbers differ, and you can let it auto-promote. Low correlation means you should be forcing more traffic up the ladder. The really valuable data points are the directional disagreements — a launch where offline said better and online said worse is a bug in your *eval*, not just your agent, and each one deserves a root-cause.

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

**Which rungs can you skip, and when?** The ladder is a default, not a law. A
trivial, reversible, flag-guarded prompt tweak with a strong offline signal and a
robust kill-switch might go straight to a small canary. A change to the agent's
tool-calling contract, its safety policy, or anything touching money should ride
*every* rung. The heuristic: **the blast radius of being wrong sets the minimum
number of rungs.** Cheap-to-reverse + small-blast-radius = fewer rungs; expensive-
to-reverse or large-blast-radius = all of them. What you must never skip is the
*kill-switch*: every rung above shadow should be behind a flag you can flip to 0%
in seconds without a redeploy.

> **Saying it out loud.** Don't jump from a green offline dashboard to a hundred percent of users — climb a ladder where each rung is cheaper to fail on than the next and catches a different class of problem. Offline catches regressions on known cases. Shadow catches crashes, latency, and cost on real live traffic with zero user exposure. Canary catches operational blowups at a one-to-five percent blast radius. The A/B is the only rung that gives you a *causal* answer about whether it's actually better. And the heuristic for which rungs you can skip is blast radius: a reversible flag-guarded prompt tweak might go straight to a small canary, but anything touching the tool contract, the safety policy, or money rides every rung. The one thing you never skip is the kill-switch — everything above shadow should be behind a flag you can flip to zero in seconds without a redeploy.

---

## A/B Testing for Agents, In Depth

A/B testing (an *online controlled experiment*) randomly assigns units to
variants, then compares metrics. Randomization is what makes the comparison
causal: because assignment is independent of everything else, any statistically
significant metric difference is caused by the variant, not by confounders. This
is the entire reason we bother — an observational "we shipped it and the number
went up" comparison is confounded by time-of-day, seasonality, cohort mix, and a
dozen other things randomization neutralizes for free.

The mechanics are classic. What makes agents *harder* than a button-color test
is described after the fundamentals.

> **Saying it out loud.** The reason we bother with randomization is that it's what makes the comparison *causal*. Because assignment is independent of everything else, any significant difference is caused by the variant — whereas the observational version, "we shipped it and the number went up," is confounded by time of day, seasonality, cohort mix, and a dozen other things randomization neutralizes for free. That's the entire argument in one sentence, and it's worth saying plainly before you get into mechanics, because a surprising number of "experiments" people describe in interviews are actually before-and-after comparisons wearing an experiment's clothes.

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
per-message significance understates variance and inflates false positives — the
messages within a user are correlated, so treating them as independent samples
fabricates statistical power you do not have. If you truly must analyze at the
message level while randomizing at the user level, use a **cluster-robust
standard error** (or the delta method / bootstrap over users) so the variance
accounts for within-user correlation.

**Assignment mechanics.** In practice you assign with a deterministic hash:
`bucket = hash(unit_id + experiment_salt) % 1000`, then map bucket ranges to
arms. Determinism guarantees a returning user re-enters the same arm (sticky
bucketing), and the per-experiment salt guarantees independence across
overlapping experiments. The exposure is logged *at the moment the user is
actually eligible and served* — logging assignment for users who never hit the
agent is a classic source of dilution and SRM.

> **Saying it out loud.** Pick the wrong unit and every number downstream is wrong. Per-request randomization gives you the most units and therefore the most power, but for a conversational agent it leaks — the same user gets the old agent on message one and the new one on message three, so the experience is incoherent and carryover contaminates both arms. Per-user is usually correct: fewer units, less power, but valid. Per-cluster is what you need when users actually interact. And the rule that catches people: the unit of randomization has to match or be coarser than the unit of analysis. Randomize by user and compute per-message significance, and you've fabricated statistical power you don't have, because messages within a user are correlated — if you must analyze at message level, use cluster-robust standard errors.

### Metrics: goal vs. guardrail

Separate the metric you are trying to *move* from the metrics you refuse to
*break*.

- **Goal (success) metric** — the thing the change is supposed to improve, e.g.
  task-completion rate, tickets resolved without escalation.
- **Guardrail metrics** — things that must not regress even if the goal
  improves: p95 latency, cost per task, safety-violation rate, escalation rate,
  refund rate. Microsoft's and Yahoo's experimentation write-ups stress that
  guardrails are what keep a "winning" experiment from silently causing harm.

A subtlety interviewers love: guardrails are usually evaluated as
**non-inferiority** tests, not superiority tests. You are not asking "did latency
improve?" — you are asking "can I rule out that latency got *more than X% worse*?"
That flips the null hypothesis and changes the decision rule. A guardrail that is
flat-with-wide-CIs has *not* been cleared; you need the CI to exclude the harm
threshold, which often requires more data than detecting the goal effect.

> **Saying it out loud.** Separate the metric you're trying to move from the metrics you refuse to break. The goal metric is the thing the change is supposed to improve — resolution rate, tickets closed without escalation. Guardrails are the things that must not regress even if the goal improves: p95 latency, cost per task, safety violations, escalation rate, refund rate. And the subtlety worth stating is that guardrails are non-inferiority tests, not superiority tests — you're not asking "did latency improve," you're asking "can I rule out that it got more than X percent worse." Which means a guardrail sitting flat with a wide confidence interval hasn't been cleared at all; it's just been under-measured.

### The statistics you must not skip

The formulas below answer one practical question: how many users do you need before your test could possibly see the effect you care about. The short version is that sample size scales with the inverse square of the effect size, so wanting to detect small effects is punishingly expensive.

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
then over-interpret the noise. The \( \delta^2 \) in the denominator is the
whole story: sample size scales with the *inverse square* of the effect you want
to detect, so wanting to see small effects is punishingly expensive. This is
exactly why variance reduction (CUPED, below) is not a nicety — halving variance
is equivalent to doubling your traffic for free.

**Significance and confidence intervals.** Report the lift *with a confidence
interval*, not a bare p-value. "Resolution +1.8% (95% CI: +0.4% to +3.2%)" tells
you both direction and precision. A CI that includes 0 means "not detectably
different at this sample size" — which is not the same as "no effect." Train
yourself and your stakeholders to read the *interval*, not the star next to the
p-value: a result of "+0.1% (95% CI −2.0% to +2.2%)" and a result of "+0.1% (95%
CI −0.05% to +0.25%)" are wildly different decisions (the first is uninformative,
the second is a confident "no meaningful effect") even though both are "not
significant."

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
\( X \) and \( Y \). A concrete worked CUPED example — including the estimator and
the variance it saves — appears in the "Build it in practice" section below.

> **Saying it out loud.** The single most under-appreciated number in agent experiments is the minimum detectable effect. Rule of thumb: you need roughly sixteen times p-times-one-minus-p, divided by delta squared, per arm. So at a 60% baseline resolution rate, detecting a two-point absolute improvement takes about 9,600 users per arm — and halving that to one point quadruples it to about 38,400. That delta-squared in the denominator is the whole story, and it's why teams run a two-week test that never had the power to see the effect they cared about, then read tea leaves in the noise. It's also why CUPED variance reduction isn't a nicety: halving variance is mathematically equivalent to doubling your traffic for free. And always report the lift with a confidence interval, never a bare p-value — "plus 0.1 percent, CI minus two to plus two" and "plus 0.1 percent, CI minus 0.05 to plus 0.25" are completely different decisions even though both are "not significant."

### Why agents are harder than classic A/B

1. **Long-horizon outcomes.** A button color's effect is visible in a click,
   now. An agent's true effect — did the user's problem *stay* solved, did they
   renew in 60 days — unfolds over weeks. If you stop the test at day 3 you
   measure the short-term proxy, which can point the *opposite* way from the
   long-term outcome (a chattier agent delights users this week and exhausts them
   next month). The standard mitigations: pick a **surrogate metric** whose link
   to the long-term outcome you have *validated historically*, and/or run a
   smaller long-horizon **holdback** cohort that stays on control for 30–60 days
   so you can measure the durable effect after the main test has shipped.

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
   returning cohort (they have an old experience to be surprised by; brand-new
   users do not).

4. **Network effects / interference.** A/B testing assumes one unit's treatment
   does not affect another unit's outcome (SUTVA). Agents break this constantly:
   a negotiation agent that gets better deals does so partly *at the expense of*
   control-arm counterparties; a marketplace agent that surfaces more inventory
   shifts demand away from other users. When units interact, per-user
   randomization is biased. LinkedIn's "A/B test of A/B tests" and Airbnb's
   cluster-randomization work show the fix: randomize by **cluster** (network
   community, market, geo) so that spillover stays inside a variant, then analyze
   at the cluster level. You pay in power; you buy back validity.

5. **Non-stationarity of the model itself.** Unlike a static UI change, an agent's
   behavior can depend on an upstream foundation model that the provider silently
   updates, on retrieval indices that refresh, and on prompt-cache state. Your
   "control" is not guaranteed to be constant across the test window. Pin model
   versions where you can, log the model/version on every trace, and treat an
   unexpected shift in *control* metrics as a signal that something moved under
   you — not as noise.

> **Saying it out loud.** Five things make agents harder than a button-color test. Long-horizon outcomes — a chattier agent delights users this week and exhausts them next month, so a day-three readout can point the opposite way from the truth; mitigate with a historically validated surrogate metric and a long-horizon holdback cohort. Feedback loops — the agent shapes the data that trains and evaluates its successor, so the baseline drifts under you. Novelty and primacy — users react to *change*, not just quality, so check whether the lift is decaying and segment new versus returning. Interference — A/B assumes one unit's treatment doesn't affect another's outcome, and marketplace or negotiation agents break that constantly, so you cluster-randomize and pay in power to buy validity. And non-stationarity of the model itself — your provider can silently update the foundation model mid-test, so pin versions, log the model on every trace, and treat an unexplained shift in the *control* arm as a signal that something moved under you.

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

**The side-effect trap (agent-specific and dangerous).** Shadowing a *chatbot* is
easy: discard the text. Shadowing an *agent that takes actions* is not — if the
candidate's trajectory includes `issue_refund()`, `send_email()`, or
`delete_row()`, running it in shadow will fire real side effects unless every
tool is sandboxed or mocked. This is the single most common way a "safe" shadow
deployment causes a production incident. The fix is a **tool-execution shim** that,
in shadow mode, either routes writes to a sandbox, returns recorded/stubbed
results, or hard-blocks any non-idempotent tool and logs "would have called X."
Read-only tools (retrieval, search) can pass through; anything that mutates state
or spends money must be intercepted. Interviewers who have run agents in prod will
ask about this specifically.

Cost caveat: shadow doubles inference spend (you run both agents on all traffic).
Sample traffic (e.g. shadow 10%) if cost matters and you only need operational
signal. Pair shadow with an **online LLM-judge on the sampled shadow outputs** to
get an early, exposure-free read on quality divergence before you risk a canary.

> **Saying it out loud.** Shadow mode runs the candidate on real live traffic in parallel with the incumbent and throws its output away — a dry run against reality. It catches what offline can't: crash rate, real p95 latency, tool timeouts under load, context overflows on actual conversations, plus the highest-value artifact, the set of cases where candidate and incumbent *disagree*, which is a free high-signal eval set. What it can't catch is anything requiring a human to see the output — resolution, satisfaction, revenue are all invisible. And here's the agent-specific trap that interviewers who've run agents in production will ask about: shadowing a chatbot is easy because you discard text, but shadowing an *action-taking* agent will fire real side effects unless every write tool is intercepted. If the trajectory includes `issue_refund` or `send_email`, your zero-impact test just issued refunds. Read-only tools pass through; anything that mutates state or spends money gets shimmed.

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
- **Weight the abort rules toward one-sided, fast-moving guardrails.** Operational
  metrics (errors, latency, cost, safety flags) move fast and are cheap to
  monitor; long-horizon goal metrics do not belong in a canary abort rule because
  the canary will never have the power or the time to read them. The canary asks
  a *safety* question; save the *value* question for the A/B.

Canary and A/B overlap in mechanism (both split traffic) but differ in intent:
canary asks *"is it on fire?"* (fast, operational, tiny slice); A/B asks *"is it
better?"* (slow, statistical, powered slice). A mature pipeline often runs them
back-to-back on the *same* flag: canary at 1→5% to clear operational risk, then
open the same flag to 50% and let it run as a powered A/B.

> **Saying it out loud.** The key thing to understand about a canary is that it is *not* a statistically powered experiment — one percent of traffic will never detect a one-point effect. Its job is different: catch catastrophic, obvious regressions with a minimal blast radius. Error rate jumping from 0.2% to 8%, p95 doubling, safety flags spiking — that decision doesn't need a confidence interval, it needs a threshold and an automated rollback, because manual canary-watching fails at three in the morning. Three practical rules: compare canary against a simultaneous control, not against yesterday, or time-of-day effects will fool you; run a sample-ratio check at every ramp step, since a misconfigured router silently invalidates everything; and keep long-horizon goal metrics out of your abort rules. Canary asks "is it on fire." The A/B asks "is it better."

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

**A concrete way to picture it.** Plot offline Δ on the x-axis and online Δ on the
y-axis, one point per launch. Four quadrants:

| | Online worse (−) | Online better (+) |
|---|---|---|
| **Offline better (+)** | *False promote* — the dangerous quadrant; your gate lets harm through | True positive — gate working |
| **Offline worse (−)** | True negative — gate working | *False block* — you are killing good changes; your gate is too strict |

A trustworthy gate keeps points on the diagonal (both-better or both-worse). The
off-diagonal points are your eval's error budget: *false promotes* cost you
incidents, *false blocks* cost you velocity. Counting them per quarter turns "is
our offline eval any good?" from a vibe into a metric.

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

> **Saying it out loud.** The offline-online gap isn't a bug to eliminate, it's a relationship to characterize. You'll never get offline equals online, and you don't need to — you need offline to be *rank-correlated* with online so it can be trusted as a filter. Picture a scatter with offline delta on the x-axis and online delta on the y, one point per launch. The diagonal points are your gate working. The off-diagonal points are your error budget: false promotes, where offline said better and online said worse, cost you incidents; false blocks, where you killed a good change, cost you velocity. Counting those per quarter turns "is our offline eval any good" from a vibe into a number. Then you close the gap by feeding production traffic — especially the disagreements — back into the offline set, calibrating your judge against humans on live samples, and retiring pretty offline metrics that don't predict.

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
> continuous peeking, and toward 100% if you peek indefinitely. The next section
> *demonstrates and fixes* this with runnable code.

> **Saying it out loud.** The readout has two parts and the order matters: sample-ratio mismatch first, lift second. Sample-ratio mismatch is a chi-square on the observed split — if you asked for 50/50 and got 51.5/48.5 on large N, something is broken, and it means the randomization assumption failed, so the treatment effect is *uninterpretable*, not just noisy. Flag it at a strict threshold like p below 0.0005 and fix the pipeline before you read any lift at all. Only then do you compute the lift with a confidence interval, and you compare the whole interval against your minimum detectable effect rather than just against zero. No amount of downstream statistical sophistication rescues a broken randomizer.

---

## Build It in Practice: A Realistic A/B Analysis for an Agent Rollout

The worked example above is the *core readout*. A production analysis needs three
more things that separate a credible engineer from someone who read one blog post:
a **peeking guardrail** (so a continuously-watched dashboard does not lie), a
**sample-ratio-mismatch gate** (already shown), and **variance reduction** (so the
test finishes before the quarter does). This section builds all three as
self-contained, dependency-free Python you can actually run (stdlib only —
`random` and `math`), and every printed number below is real output from running
the code, not a plausible-looking guess.

### 1. Demonstrate the peeking problem, then control it

First, prove the danger. We simulate 4,000 experiments in which **the treatment is
identical to control** (the null is true, so any "win" is a false positive). Each
experiment is peeked at 10 times (think: a daily dashboard over a two-week test),
and we stop-and-declare-victory the first time the naive \( |z| > 1.96 \):

```python
import random, math

def normal_cdf(z): return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def two_prop_z(cn, cs, tn, ts):
    pc, pt = cs / cn, ts / tn
    pp = (cs + ts) / (cn + tn)
    se = math.sqrt(pp * (1 - pp) * (1 / cn + 1 / tn))
    return (pt - pc) / se if se else 0.0

def run_peeking(n_experiments, users_per_arm, n_looks,
                p_true=0.60, seq_z=None):
    """Simulate repeated experiments under the NULL and count how often each
    rule ever crosses. seq_z, if given, is an alternative (sequential) boundary."""
    z_naive = 1.959963985
    fp_naive = fp_seq = 0
    look_sizes = [int(users_per_arm * (k + 1) / n_looks) for k in range(n_looks)]
    for _ in range(n_experiments):
        cs = ts = prev = 0
        crossed_naive = crossed_seq = False
        for size in look_sizes:
            add = size - prev; prev = size
            cs += sum(1 for _ in range(add) if random.random() < p_true)
            ts += sum(1 for _ in range(add) if random.random() < p_true)
            z = abs(two_prop_z(size, cs, size, ts))
            if z > z_naive:            crossed_naive = True
            if seq_z and z > seq_z:    crossed_seq = True
        fp_naive += crossed_naive
        fp_seq  += crossed_seq
    return fp_naive / n_experiments, (fp_seq / n_experiments if seq_z else None)

random.seed(7)
fpr_naive, _ = run_peeking(4000, 8000, 10)
print(f"naive fixed-horizon z, 10 looks, null true -> FPR = {fpr_naive:.3f}")
```

Output:

```
naive fixed-horizon z, 10 looks, null true -> FPR = 0.194
```

**Nearly one in five "significant wins" is pure noise.** That is the peeking tax,
demonstrated. Now control it. Rather than derive a closed-form always-valid
boundary (mSPRT / confidence sequences — the modern approach productized by Eppo,
GrowthBook, and Optimizely), we do the transparent thing: **calibrate a constant
boundary by Monte Carlo** so that the probability of *ever* crossing across all 10
looks — under the null — is exactly 5%. This is a legitimate group-sequential
approach (it is how you would sanity-check a vendor's boundary) and it is
impossible to get subtly wrong, because it is defined by the error rate it
controls:

```python
def calibrate_boundary(target_fpr, users_per_arm, n_looks,
                       p_true=0.60, n_cal=6000, seed=11):
    """Find the constant |z| threshold whose family-wise 'ever cross' rate
    under the null equals target_fpr, given this peek schedule."""
    random.seed(seed)
    look_sizes = [int(users_per_arm * (k + 1) / n_looks) for k in range(n_looks)]
    max_zs = []
    for _ in range(n_cal):
        cs = ts = prev = 0; mz = 0.0
        for size in look_sizes:
            add = size - prev; prev = size
            cs += sum(1 for _ in range(add) if random.random() < p_true)
            ts += sum(1 for _ in range(add) if random.random() < p_true)
            mz = max(mz, abs(two_prop_z(size, cs, size, ts)))
        max_zs.append(mz)
    max_zs.sort()
    return max_zs[min(int((1 - target_fpr) * len(max_zs)), len(max_zs) - 1)]

zc = calibrate_boundary(0.05, 8000, 10)
print(f"calibrated boundary for 5% family-wise FPR over 10 looks = z*={zc:.3f}")

random.seed(99)
fpr_naive2, fpr_seq = run_peeking(4000, 8000, 10, seq_z=zc)
print(f"with z*={zc:.3f}:  naive FPR={fpr_naive2:.3f}   sequential FPR={fpr_seq:.3f}")
```

Output:

```
calibrated boundary for 5% family-wise FPR over 10 looks = z*=2.560
with z*=2.560:  naive FPR=0.193   sequential FPR=0.045
```

The lesson in three numbers: peeking with the naive \( z=1.96 \) boundary gives a
**19.3%** false-positive rate; raising the bar to the calibrated \( z^\*=2.56 \)
pulls it back to the **4.5%** you thought you had. That higher bar is exactly the
price of the right to look early — sequential methods (mSPRT, GAVI, group-
sequential) all trade a little power for the freedom to monitor continuously.
Spotify's framework comparison is the best practitioner survey of the options
(<https://engineering.atspotify.com/2023/03/choosing-sequential-testing-framework-comparisons-and-discussions>).

> **Saying it out loud.** Peeking is the one statistical failure everyone commits and nobody names. Watch a fixed-horizon test on a daily dashboard and stop the moment it crosses p equals 0.05, and your false positive rate isn't five percent — the simulation here gives 19.4% under a *true null* where treatment is literally identical to control, and if you peek forever it goes to a hundred percent. So a dashboard that's watched continuously and read with a fixed-horizon threshold is not evidence. The two legitimate fixes are: pre-register the sample size and read once, or switch to sequential, always-valid p-values that are designed for continuous monitoring. Saying "we used a sequential boundary because we watch the dashboard daily" is one of the cheapest ways to sound senior.

### 2. CUPED variance reduction: finish the test twice as fast

CUPED means: subtract off the part of each user's outcome you could already predict from their behavior *before* the experiment started. Because that pre-period data can't have been affected by the treatment, subtracting it removes noise without biasing the result.

CUPED subtracts a pre-experiment covariate correlated with the outcome. Below we
simulate users with a stable latent "propensity" so that each user's *pre-period*
metric \( X \) correlates with their *experiment-period* outcome \( Y \) — exactly
the situation for retained agent users (a heavy user last month is a heavy user
this month). We compute \( \theta = \mathrm{Cov}(Y,X)/\mathrm{Var}(X) \), form
\( Y_{\text{cuped}} = Y - \theta(X - \bar X) \), and compare standard errors:

```python
def cuped_demo(n=8000, seed=3, true_effect=0.05):
    random.seed(seed)
    def gen(effect):
        Xs, Ys = [], []
        for _ in range(n):
            base = random.gauss(0, 1)               # latent user propensity
            Xs.append(base + random.gauss(0, 0.6))   # pre-period metric
            Ys.append(base + random.gauss(0, 0.6) + effect)  # experiment outcome
        return Xs, Ys
    Xc, Yc = gen(0.0)              # control
    Xt, Yt = gen(true_effect)     # treatment (true +0.05 effect)

    allX, allY = Xc + Xt, Yc + Yt
    mx = sum(allX) / len(allX);  my = sum(allY) / len(allY)
    cov  = sum((x-mx)*(y-my) for x, y in zip(allX, allY)) / len(allX)
    varx = sum((x-mx)**2 for x in allX) / len(allX)
    vary = sum((y-my)**2 for y in allY) / len(allY)
    theta = cov / varx
    rho   = cov / math.sqrt(varx * vary)

    def mean_var(v):
        m = sum(v)/len(v); return m, sum((x-m)**2 for x in v)/(len(v)-1)

    mc, vc = mean_var(Yc);  mt, vt = mean_var(Yt)
    se_raw = math.sqrt(vc/n + vt/n)

    Yc_a = [y - theta*(x-mx) for x, y in zip(Xc, Yc)]
    Yt_a = [y - theta*(x-mx) for x, y in zip(Xt, Yt)]
    mca, vca = mean_var(Yc_a);  mta, vta = mean_var(Yt_a)
    se_cuped = math.sqrt(vca/n + vta/n)
    return rho, theta, se_raw, se_cuped, mt-mc, mta-mca

rho, theta, se_raw, se_cuped, d_raw, d_cuped = cuped_demo()
print(f"corr(X,Y) rho={rho:.3f}  theta={theta:.3f}")
print(f"SE raw   = {se_raw:.5f}   diff={d_raw:+.4f}")
print(f"SE cuped = {se_cuped:.5f}   diff={d_cuped:+.4f}")
print(f"variance reduction = {(1-(se_cuped/se_raw)**2)*100:.1f}%  "
      f"(theory ~ rho^2 = {rho**2*100:.1f}%)")
```

Output:

```
corr(X,Y) rho=0.735  theta=0.742
SE raw   = 0.01852   diff=+0.0614
SE cuped = 0.01255   diff=+0.0546
variance reduction = 54.0%  (theory ~ rho^2 = 54.0%)
```

The estimate barely moves (both recover the true +0.05 effect — CUPED is
*unbiased* because \( X \) is pre-treatment and cannot be affected by the
variant), but the standard error drops from 0.0185 to 0.0126 — a **54% variance
reduction, matching the theoretical \( \rho^2 = 0.54 \)** for \( \rho = 0.735 \).
A 54% variance cut is equivalent to **more than doubling your sample size for
free**: the same precision in roughly half the calendar time. That is why every
serious platform ships CUPED — GrowthBook's docs
(<https://docs.growthbook.io/statistics/cuped>) and the LA Times case study
(<https://blog.growthbook.io/cuped-for-faster-experimentation-in-growthbook/>) are
good next reads.

> **Saying it out loud.** CUPED is the closest thing to free money in experimentation. The idea is that a heavy user last month is a heavy user this month, so a lot of the variance in your outcome metric is just stable between-user differences that have nothing to do with your treatment. You subtract a pre-experiment covariate scaled by its regression coefficient, and because that covariate is pre-treatment it cannot possibly be affected by the variant — so you remove variance without introducing bias. The reduction is roughly rho-squared, the squared correlation between the pre-period and experiment-period metrics, and in practice a 40% narrower confidence interval means your test reads clean in two weeks instead of a month. The tradeoff is that it only helps for metrics where users have a stable pre-period history, so it does nothing for brand-new users.

### 3. Putting it together: the analysis checklist

A defensible agent A/B readout runs these gates *in order*, and stops at the first
red:

1. **SRM gate.** Chi-square on the split. Red → the pipeline is broken; fix it
   before reading anything else. (No amount of downstream sophistication rescues a
   broken randomizer.)
2. **Guardrails (non-inferiority).** Latency p95, cost/task, safety-violation
   rate, escalation, refund/concession. Red → do not ship regardless of the goal.
3. **Peeking discipline.** If the dashboard was watched continuously, use the
   sequential boundary, not \( z=1.96 \). Fixed-horizon p-values on a peeked test
   are not evidence.
4. **Goal metric with CUPED-reduced CI.** Report absolute lift + CI, compare the
   *whole interval* against your MDE, not just against zero.
5. **Segment + trend checks.** New vs. returning (novelty), top geographies /
   segments (interference, heterogeneous effects), and the day-by-day trend (is
   the lift decaying?).

Only a change that is green on all five earns a ramp to GA — behind a kill-switch.

> **Saying it out loud.** A defensible readout runs five gates in order and stops at the first red. Sample-ratio mismatch first — red means the pipeline is broken and nothing downstream is interpretable. Then guardrails as non-inferiority tests — red means don't ship regardless of how good the goal looks. Then peeking discipline — if the dashboard was watched continuously, use a sequential boundary, because a fixed-horizon p-value on a peeked test isn't evidence. Then the goal metric with a variance-reduced confidence interval, compared against the minimum detectable effect rather than against zero. Then segment and trend checks for novelty and heterogeneous effects. Only green on all five earns a ramp — and the ramp still goes behind a kill-switch.

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
| Online judge score (sampled) | Guardrail/Judgment | Live quality drift on real outputs | The judge itself drifts; calibrate against human labels |
| Tool-call error / retry rate | Guardrail | Is the agent's tool use degrading | Silent partial failures the user "recovers" from by re-asking |

**Design rule:** every goal metric needs at least one guardrail that would go the
wrong way if the agent "cheated" to move the goal. Resolution rate is paired with
escalation *and* CSAT so an agent cannot win by prematurely closing tickets.

**The metric hierarchy interviewers want you to name.** Serious experimentation
programs organize metrics into tiers: an **Overall Evaluation Criterion (OEC)** —
the single (possibly composite) metric the experiment is judged on, chosen to be
short-term-measurable but validated to predict long-term value; **guardrail
metrics** that gate the decision via non-inferiority; **debug/diagnostic metrics**
that explain *why* the OEC moved (per-tool success, per-intent resolution, token
counts) but never decide the ship. The most common junior mistake is conflating a
diagnostic metric with the OEC — celebrating that "average tokens dropped 12%"
when nobody signed up to ship a cheaper-but-worse agent. Decide the OEC and the
guardrails *before* launch and write them down; post-hoc metric shopping is how
noise becomes a "win."

> **Saying it out loud.** The design rule that carries this whole section: every goal metric needs at least one guardrail that would move the wrong way if the agent cheated to move the goal. Resolution rate gets paired with escalation rate *and* satisfaction, so the agent can't win by prematurely closing tickets. Containment rate gets paired with satisfaction, so it can't win by refusing to escalate. And name the hierarchy — there's an overall evaluation criterion, the one metric the experiment is judged on; guardrails that veto via non-inferiority; and diagnostic metrics that explain *why* the OEC moved but never decide the ship. The classic junior mistake is promoting a diagnostic to an OEC — celebrating that average tokens dropped twelve percent when nobody signed up to ship a cheaper-but-worse agent. Write the OEC and the guardrails down before launch, because post-hoc metric shopping is how noise becomes a win.

---

## Failure Modes and Pitfalls

- **Peeking / early stopping.** Repeatedly checking a fixed-horizon test and
  stopping when it turns significant inflates false positives from a nominal ~5%
  to ~20%+ (and to 100% if you peek forever) — as demonstrated with runnable code
  above (empirical 19.4%). Fix: pre-register the sample size and read once, *or*
  switch to sequential / always-valid p-values designed for continuous monitoring.

- **Sample Ratio Mismatch (SRM).** If your 50/50 split arrives as 51.5/48.5 on
  large N, something is broken — a router bug, differential bot filtering, a
  logging join that drops one arm. SRM means the randomization assumption failed,
  so **the treatment effect is uninterpretable**. Detect with a chi-square test
  (flag at \( p < 0.0005 \)); when it fires, fix the pipeline before reading any
  lift. Notorious cause: a treatment so engaging it trips bot detection and gets
  its users filtered out (Microsoft's MSN carousel case). Agent-specific causes:
  the candidate is slower, so more of its sessions time out and drop before the
  outcome is logged; or an exception in one arm's code path silently loses events.

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

- **Shadow side effects.** Running an action-taking agent in shadow without
  sandboxing its tools, so a "no-user-impact" test actually issues refunds or
  sends emails. Intercept every non-idempotent tool in shadow mode.

- **Simpson's paradox / mix shift.** A treatment can win in every segment yet lose
  overall (or vice versa) if the arms have different segment mixes — often itself a
  symptom of SRM or of ramping arms at different times. Always inspect key segments
  alongside the pooled number, and be suspicious when pooled and segmented results
  disagree in direction.

- **Multiple comparisons.** Slicing an experiment into 30 metrics × 10 segments and
  celebrating the one cell with \( p<0.05 \) is guaranteed to find noise. Correct
  for multiplicity (Benjamini–Hochberg) or pre-register the few slices that matter.

> **Saying it out loud.** If I had to rank them: peeking, because it silently takes your false-positive rate from five percent to about twenty. Sample-ratio mismatch, because it means your beautiful p-value is measuring your logging pipeline instead of your agent. Goodhart, because any metric you optimize hard enough stops being a measure — push on satisfaction and the agent gets sycophantic, push on containment and it refuses to escalate. Underpowered tests, where a flat result gets read as "no difference" when it was never able to see one. And the two agent-specific ones: shadow side effects, where an unsandboxed action agent issues real refunds during a supposedly zero-impact test; and Simpson's paradox, where the treatment wins in every segment and loses overall because the arms have different segment mixes — which is usually itself a symptom of a sample-ratio problem.

---

## Production Case Studies and War Stories

Theory sticks when it is attached to a scar. These are composite but realistic
patterns drawn from how teams actually stage agent rollouts and where they get
burned; the mechanisms are the ones documented in the primary sources cited
throughout this chapter.

### The canonical rollout: offline → shadow → canary → A/B → GA

A support-automation team shipping a new tool-using resolution agent runs the full
ladder:

1. **Offline (day 0).** Replay 20k captured production tickets against the
   candidate; the LLM-judge resolution proxy is +4.1% and tool-call validity is
   +2%. Green — permission to test, not to ship.
2. **Shadow (days 1–4).** Mirror 100% of live tickets to the candidate with all
   write-tools (refund, ticket-close, email) routed to a sandbox. Finds two things
   offline missed: p95 latency is +2.3s on long multi-tool tickets (a real-tool
   timeout the replay's cached tool results had hidden), and a 0.4% rate of an
   exception on tickets with attachments. Both fixed before any user is exposed.
3. **Canary (days 5–7).** 2% of users, auto-rollback wired to "error rate >
   control + 1% or p95 > 1.4× control." Holds. SRM checked at each step — clean.
4. **A/B (days 8–21).** 50/50, per-user randomization, OEC = resolution-without-
   escalation, guardrails = CSAT, refund rate, cost/task, p95. CUPED on each
   user's prior-month resolution rate cuts the CI width ~40%, so the test reads
   clean in two weeks instead of a month.
5. **GA (day 22+).** Ramp 50→100% behind a kill-switch; guardrail dashboards with
   paging thresholds stay on; a 5% long-horizon holdback stays on control for D30
   retention.

The point: **every rung caught a different class of problem, and the ones shadow
and canary caught (latency, attachment crash) would each have been a visible
incident at GA.**

> **Saying it out loud.** Here's what the full ladder actually buys you, rung by rung, on one real-shaped example. Offline replay of twenty thousand captured tickets says plus four percent — that's permission to test, not permission to ship. Shadow on a hundred percent of live tickets with write-tools sandboxed finds two things replay hid: p95 up 2.3 seconds on long multi-tool tickets, because the replay used cached tool results, and a crash on tickets with attachments. Both fixed with zero users exposed. Canary at two percent with an automated rollback rule holds. Then a two-week fifty-fifty A/B with CUPED cutting the interval width about forty percent gives the causal read. Then GA behind a kill-switch with a five percent long-horizon holdback. The point is that each rung caught a *different class* of problem, and the two that shadow and canary caught would each have been a visible incident at GA.

### War story 1 — the offline win that tanked a business metric

*Setup.* A billing-support agent's new version scored **+6% on the offline
resolution eval** — the epigraph of this chapter. The offline judge rewarded
"resolving the user's stated problem," and the new agent resolved more of them.

*What happened online.* Task completion (as the judge measured it) did rise. But
the agent resolved billing complaints disproportionately by **issuing refunds and
credits** — the fastest path to a "resolved" ticket. Refund rate nearly doubled;
gross margin on the supported segment dropped. CSAT was up (users love refunds!),
so two metrics were green while the business bled.

*Root cause.* The OEC was a **proxy** (judge-rated resolution) that was
Goodhart-vulnerable, and **refund rate was not a pre-registered guardrail.** The
offline eval could never have caught it: no offline judge sees a P&L.

*The fix and the lesson.* Refund/concession rate became a hard guardrail on every
support experiment; the OEC was redefined as "resolved *without* a concession
above threshold." The durable lesson: **for any agent that can take a costly
action to satisfy a user, the cost of that action must be a guardrail — the goal
metric alone will happily buy satisfaction with your margin.**

> **Saying it out loud.** A billing-support agent scored plus six percent on the offline resolution eval, and online, resolution genuinely did rise — because the agent had discovered that the fastest path to a resolved ticket is to issue a refund. Refund rate nearly doubled, margin dropped, and satisfaction went *up*, because users love refunds. So two metrics were green while the business bled. The root cause is that the OEC was a Goodhart-vulnerable proxy and refund rate was never a pre-registered guardrail — and no offline judge could ever have caught it, because no offline judge sees a P&L. The generalizable rule: for any agent that can take a costly action to satisfy a user, the cost of that action must be a guardrail, or the goal metric will happily buy satisfaction with your margin.

### War story 2 — the SRM that invalidated a "winner"

*Setup.* A coding-assistant team ran a 50/50 test of a new planning-heavy agent
and saw a beautiful **+3.2% task-success lift, p = 0.002.** Champagne on ice.

*The catch.* A reviewer ran the SRM check: the split had arrived as **51.4 /
48.6** on ~180k sessions — chi-square \( p \approx 10^{-6} \), a screaming SRM.

*Root cause.* The new agent was slower (more planning tokens). Sessions in the
treatment arm were more likely to hit a **client-side timeout** that dropped the
session before the success event was logged. The dropped sessions were
disproportionately the *hard, ultimately-failed* ones — so the treatment arm's
logged population was **survivorship-biased toward easy wins.** The "+3.2%" was an
artifact of *which sessions got recorded*, not of agent quality.

*The fix and the lesson.* Fix the logging to record the outcome before the timeout
boundary, re-run, and the lift collapsed to a non-significant +0.3%. Lesson:
**SRM is not a formality — it is the smoke alarm that tells you your beautiful
p-value is measuring your logging pipeline, not your agent.** Any latency-changing
agent change is an SRM risk, because latency changes *who survives to be counted*.

> **Saying it out loud.** A coding-assistant team saw plus 3.2% task success at p equals 0.002 and was ready to celebrate. Then someone ran the sample-ratio check: the fifty-fifty split had arrived as 51.4 to 48.6 on about 180,000 sessions, chi-square p around ten to the minus six. Root cause — the new agent was slower because it planned more, so treatment sessions were more likely to hit a client-side timeout and get dropped before the success event was logged, and the dropped ones were disproportionately the hard, ultimately-failed sessions. So the treatment arm's *recorded* population was survivorship-biased toward easy wins. Fixed the logging, re-ran, and the lift collapsed to a non-significant plus 0.3%. The lesson: any agent change that moves latency is a sample-ratio risk, because latency changes who survives to be counted.

### War story 3 — novelty masquerading as value

*Setup.* A consumer chat agent got a new, chattier, more proactive persona.
Week-1 A/B showed engagement (messages/session) **+11%** and thumbs-up rate up.
Ship it?

*The catch.* Segmenting new vs. returning users, the lift lived almost entirely in
**returning** users, and the day-by-day trend was **decaying** — +18% on day 1,
+4% by day 7. New users (no prior experience to be surprised by) showed ~0.

*Root cause.* **Novelty effect.** Returning users were reacting to *change*, not
to durable value; the chattier persona was a curiosity bump that was already
fading, and qualitative feedback showed some users found it "exhausting."

*The fix and the lesson.* Extend the test, weight the decision toward the new-user
segment and the asymptotic (late-window) effect, and add a D30 holdback. The
durable engagement gain was ~+2%, not +11%. Lesson: **an average over a short
window conflates novelty with value; measure the trend and segment by
exposure-to-change before you believe a launch-week number.**

> **Saying it out loud.** A consumer chat agent got a chattier, more proactive persona, and week one showed engagement up eleven percent with thumbs-up rising. Ship it? No — because when they segmented, the lift lived almost entirely in *returning* users, and the day-by-day trend was decaying: plus eighteen percent on day one, plus four by day seven, and roughly zero for brand-new users who had no prior experience to be surprised by. That's the signature of a novelty effect: people were reacting to change, not to durable value, and qualitative feedback said some found the persona exhausting. The real durable gain was about plus two percent, not eleven. The rule: an average over a short window conflates novelty with value — measure the trend and segment by exposure-to-change before you believe a launch-week number.

### The meta-lesson across the war stories

Every one of these was invisible offline and every one was caught by a *specific*
online discipline: guardrails (war story 1), SRM (war story 2), trend + segmenting
(war story 3). The offline eval was not "wrong" — it was answering a different,
narrower question than the one the business cared about. Real-world testing is the
machinery that keeps the narrow question from being mistaken for the important one.

---

## Monitoring and Feedback Capture

Real-world testing does not end at rollout — 100% is a *monitored* state, not a
finished one. The same discipline that gated the launch must run continuously.

- **Log every run as an evaluable trace.** Persist inputs, tool calls,
  intermediate state, final output, latency, cost, and outcome — enough to replay
  and to build tomorrow's offline eval set from real traffic. Include the model
  and prompt version on every trace so you can attribute a metric shift to a
  specific change (and detect a silent upstream model update).
- **Online guardrail dashboards with alerts.** Safety-violation rate, p95
  latency, cost per task, and escalation rate should have automated thresholds
  that page a human — the production analog of canary abort criteria.
- **Online LLM-judge on sampled traffic.** Score 1–5% of live outputs
  continuously for helpfulness/safety/faithfulness and alert on drift — but
  calibrate the judge against human labels on live samples so you are monitoring
  quality, not the judge's bias.
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

> **Saying it out loud.** A hundred percent rollout is a monitored state, not a finished one. Log every run as a replayable trace with the model and prompt version attached, so you can attribute a metric shift to a specific change — and detect a silent upstream model update, which is a real thing that happens. Run guardrail dashboards with thresholds that page a human, which is just canary abort criteria applied forever. Keep the sampled online judge running, calibrated against human labels. And know the difference between your two feedback channels: explicit feedback like thumbs is sparse, self-selected, and biased, so treat it as directional; implicit feedback — retries, rephrasings, abandonment, escalation — is dense and noisy but usually a truer signal of value than any rating. Then close the loop by feeding reviewed failures back into the offline set, which is how the offline-online gap shrinks instead of quietly widening.

---

## Interview Mastery

This section is engineered to get you through a senior interview on real-world
agent testing: a bank of Q&A, a 60-second set-piece, a system-design prompt with a
worked sketch, decision tables you can redraw on a whiteboard, and the red/green
flags interviewers listen for.

### The 60-second answer: "explain the offline–online gap"

> Offline eval scores the agent against a frozen dataset with a cheap proxy metric
> — a rubric or an LLM judge. It is fast, deterministic, and great for catching
> regressions, but it measures a *proxy* on a *past* distribution. The
> offline–online gap is the difference between that proxy and what actually happens
> when real users, on today's traffic, react to the output: distribution shift,
> latency and cost, human downstream decisions, and second-order effects like
> margin. You can't eliminate the gap — no offline number equals a churn or revenue
> outcome — but you can *characterize* it: log every launch's offline delta and its
> online A/B delta, and compute the rank correlation across launches. High
> correlation means offline is a trustworthy gate; directional disagreements are
> bugs in your *eval*, not just your agent. You close the gap by feeding production
> traffic (especially failures and shadow disagreements) back into the offline set
> and calibrating your judge against human labels on live data. In one line: offline
> tells you what's *allowed to ship*; online tells you what's *actually better*.

### Q&A bank

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
trusting any lift. For agents specifically, a slower treatment arm that drops more
timed-out sessions is a classic SRM generator — and it biases *which* sessions get
counted.

**Q3. Why is A/B testing agents harder than testing a checkout button?**
Four reasons: (1) **long-horizon outcomes** — the true effect (did the problem
stay solved, did they renew) unfolds over weeks, and short-term proxies can point
the wrong way; (2) **feedback loops** — the agent changes the data that
trains/evaluates its successor, so the baseline drifts; (3) **novelty effects** —
users react to change, so early lift can be curiosity, not quality; (4) **network
effects** — agents in marketplaces or negotiations make one unit's treatment
affect another's outcome, violating SUTVA and biasing per-user randomization. A
fifth, agent-specific one: the underlying foundation model can change under you,
so even "control" is not guaranteed stationary.

**Q4. Explain the peeking problem and how you would handle continuous
monitoring.**
Fixed-horizon tests are valid only if you set N in advance and read once. If you
check daily and stop when \( p < 0.05 \), you get many chances to cross the
threshold by luck, inflating the false-positive rate from ~5% to ~20%+ (→100% if
you peek forever) — I've simulated it at ~19%. Options: pre-register N and read
once; or, if I genuinely need to monitor live, use a **sequential test** with
always-valid p-values (e.g. mSPRT, GAVI, or group-sequential boundaries), which
controls error under continuous looking at the cost of some power. The intuition
is that the significance bar has to be *raised* (in my simulation from z=1.96 to
z≈2.56) to buy back the right to look early.

**Q5. What is the difference between a goal metric and a guardrail metric? Give an
agent example.**
The goal metric is what the change is meant to improve (task resolution rate). A
guardrail is something that must not regress even if the goal improves (p95
latency, cost per task, safety-violation rate, escalation rate, refund rate). The
canonical trap: an agent lifts CSAT by handing out refunds freely — goal up,
refund-rate guardrail blown. Every goal metric needs a guardrail that would move
the wrong way if the agent gamed the goal. Guardrails are usually tested for
*non-inferiority* (rule out harm > X%), not superiority.

**Q6. Shadow mode showed zero errors and great latency. Why can't you ship on
that alone?**
Because in shadow the output never reached a user. Shadow proves the agent can
*run safely at scale* — crashes, latency, cost, tool errors on real traffic — but
it is blind to everything consequential: resolution, satisfaction, revenue,
escalation, because no human ever saw or acted on the shadow output. Shadow
clears operational risk; only a canary/A/B where users actually receive the
output can tell you whether it is *better*. And I'd stress: shadowing an
action-taking agent requires sandboxing its write-tools, or the "zero-impact" run
issues real refunds.

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
unbiased while variance drops by roughly \( \rho^2 \) — in my simulation a
\( \rho=0.735 \) covariate cut variance 54%, halving the required runtime. It
shines when users have stable, autocorrelated behavior (a heavy user last week is
a heavy user this week) — exactly the case for retained agent users.

**Q9. Choose the unit of randomization for a multi-turn conversational agent, and
justify it.**
Per-**user** (or per-account), not per-request. Per-request maximizes power but
gives a user an incoherent old-agent/new-agent experience within one conversation
and lets carryover contaminate both arms. The unit of randomization must be at
least as coarse as the unit of analysis; I randomize by user and analyze by user.
If I need message-level diagnostics I use cluster-robust standard errors so
within-user correlation doesn't fabricate power. If the agents interact across
users (marketplace, negotiation), I go coarser still — cluster by market/geo.

**Q10. You have a two-week test but only enough traffic for a 3-point MDE; the
effect you care about is 1 point. What do you do?**
Recognize the test is underpowered *before* running it — \( n \propto 1/\delta^2 \),
so a 1-point MDE needs ~9× the traffic of a 3-point one. Options, roughly in
order: apply **CUPED** (a good covariate can halve variance ≈ double effective N);
extend the duration if the effect is stable; pick a **more sensitive OEC** or a
validated surrogate; reduce variance by trimming outliers/capping; or accept that
I can only make a decision at the 3-point resolution and say so honestly rather
than over-reading noise. What I will *not* do is run it anyway and interpret a
flat, underpowered result as "no difference."

**Q11. Design an automated rollback for a canary. What trips it, and what
doesn't?**
Trip on fast, one-sided, operational guardrails compared **canary-vs-concurrent-
control** (never vs. yesterday): error rate > control + threshold, p95 latency >
k×control, cost/task spike, safety-violation spike, and an SRM check at each ramp
step. These need thresholds, not confidence intervals — the decision is "is it on
fire," and it must fire in minutes without a human at 3 a.m. What must *not* be in
the abort rule: long-horizon goal metrics (resolution durability, retention) — the
canary has neither the power nor the time to read them; those are the A/B's job.

**Q12. Give a scenario where per-user randomization is biased, and the fix.**
A negotiation or marketplace agent: a treatment-arm buyer that negotiates better
prices does so partly at the expense of control-arm sellers, so treatment's gain
is control's loss — SUTVA is violated and the measured lift is inflated. Or a
shared-inventory recommender that shifts demand between users. Fix:
**cluster-randomize** — assign whole markets/geos/social-communities to a variant
so spillover stays inside an arm — and analyze at the cluster level (fewer units,
less power, but unbiased). LinkedIn's "A/B test of A/B tests" and Airbnb's
cluster-randomization work are the references.

**Q13. Your offline judge and your online metric disagree on a launch — offline
said better, online said worse. How do you debug it?**
Treat it as a bug in the *eval*, not just the agent. Check, roughly in order:
(1) **SRM** — is the online read even valid? (2) **distribution shift** — is live
traffic different from the offline set (new intents, longer conversations)?
(3) **judge bias** — is the offline judge rewarding something users dislike
(verbosity, sycophancy) that doesn't help the real outcome? (4) **missing cost
dimension** — does offline ignore latency/cost/margin that the online metric
captures? (5) **long-horizon vs. short** — did the online metric capture a
downstream effect offline can't see? Each answer either fixes the eval (add the
missing dimension, resample traffic, recalibrate the judge) or confirms the agent
is genuinely worse. Log the disagreement — it is a data point for your
offline–online correlation.

**Q14. How do you separate a novelty effect from a real, durable improvement?**
Don't trust the window average. (1) Plot the **day-by-day trend** — a lift decaying
toward zero is novelty. (2) **Segment new vs. returning** users — novelty lives in
returning users who have an old experience to react to; new users show the durable
effect. (3) Run a **long-horizon holdback** (a slice kept on control for D30/D60)
and read the asymptotic effect. If the late-window, new-user, holdback-confirmed
effect is small, the launch-week number was novelty.

**Q15. What is shadow mode, when is it the right tool, and what is its biggest
agent-specific pitfall?**
Shadow runs the candidate on live traffic in parallel with the incumbent and
discards its output — zero user exposure. It's the right tool to clear
*operational* risk (latency, cost, crashes, tool errors, drift) on the true live
distribution, and to harvest incumbent-vs-candidate disagreements as a high-signal
eval set — before you expose anyone. Biggest agent-specific pitfall: **side
effects.** If the candidate's trajectory calls write-tools (refund, email, delete),
shadow will fire them for real unless every non-idempotent tool is sandboxed,
stubbed, or blocked. A "safe" shadow deploy that isn't sandboxed is a live
incident waiting to happen.

**Q16. Walk me through why sample size scales as \( 1/\delta^2 \), and one
consequence.**
For a proportion, per-arm \( n \approx 16\,p(1-p)/\delta^2 \) at 80% power / 5%
significance. The signal you're trying to detect is the effect \( \delta \); the
noise is the standard error, which shrinks like \( 1/\sqrt{n} \). To keep a fixed
signal-to-noise ratio as \( \delta \) shrinks, \( \sqrt{n} \) must grow like
\( 1/\delta \), so \( n \) grows like \( 1/\delta^2 \). Consequence: halving the
effect you want to see **quadruples** the traffic and time — which is exactly why
variance reduction (CUPED) and sensitive OECs are not luxuries; a 50% variance cut
is worth as much as doubling your users.

**Q17. What goes in the trace you log for every production agent run, and why?**
Inputs, full tool-call sequence with args and results, intermediate state/reasoning
where feasible, final output, latency (per step and total), token cost, the
**model and prompt version**, the experiment arm, and the eventual outcome
(resolved/escalated/refunded). Why: it lets me (1) replay real traffic against
future candidates so the offline set tracks live distribution, (2) attribute a
metric shift to a specific version and detect silent upstream model changes,
(3) sample disagreements/low-confidence cases for human review and judge
calibration, and (4) reconstruct any incident. Traces are the substrate the whole
offline↔online loop runs on.

**Q18. When would you deliberately *not* run a full A/B, and ship on a lesser
signal?**
When the cost of the A/B exceeds the risk it buys down: a trivially reversible,
flag-guarded change with a strong offline signal and a robust kill-switch (e.g. a
typo-level prompt fix); an urgent safety hotfix where the risk of *waiting* exceeds
the risk of shipping (ship behind a flag, monitor guardrails, roll back on alert);
or a change with such a huge, unambiguous shadow/canary operational signal that an
A/B would only confirm the obvious. The discipline is the same — kill-switch,
guardrail monitoring — but the number of rungs scales with blast radius, not
dogma. I'd still log it for the offline–online correlation.

### System-design prompt: "Design the rollout + measurement plan for a new agent version"

A common senior-level whiteboard prompt. A strong answer names the components, the
data flow, the statistics, and the failure handling. Here is a compact sketch.

**Restate scope.** New version of a customer-support resolution agent (multi-turn,
uses tools: KB search, order lookup, refund). Goal: ship it iff it improves
resolution-without-escalation without harming CSAT, refund rate, latency, or cost.

**Architecture sketch.**

```
                      ┌──────────────────────────────────────────┐
   user request ─────►│  Assignment service (feature flag)        │
                      │  bucket = hash(user_id + salt) % 1000      │
                      │  → arm; emits EXPOSURE log                 │
                      └───────────────┬──────────────────────────┘
                          control │        │ treatment
                                  ▼        ▼
                      ┌───────────┐    ┌───────────┐
                      │ Agent v1  │    │ Agent v2  │──► tool shim (sandbox writes in shadow)
                      └─────┬─────┘    └─────┬─────┘
                            └──────┬─────────┘
                                   ▼
                      ┌──────────────────────────┐
                      │  Response to user + TRACE │  (inputs, tools, latency,
                      │  log (arm, version, cost) │   cost, version, outcome)
                      └───────────┬──────────────┘
                                  ▼
        ┌────────────────────────────────────────────────────────────┐
        │  Warehouse: join EXPOSURE ⋈ TRACE ⋈ OUTCOME ⋈ pre-period X  │
        └───────────┬───────────────────────────────┬────────────────┘
                    ▼                                ▼
        ┌───────────────────────┐        ┌─────────────────────────────┐
        │ Guardrail dashboards  │        │ Experiment analysis          │
        │ (p95, cost, safety,   │        │ SRM → guardrails(non-infer.) │
        │ escalation) + paging  │        │ → CUPED lift + CI (seq. if   │
        │ + canary auto-rollback│        │ peeked) → segments/trend     │
        └───────────────────────┘        └─────────────────────────────┘
                    ▲                                │
   online LLM-judge on sampled traffic ─────────────┘  (feeds offline set + judge calib.)
```

**Rollout plan (the ladder).** Offline replay gate → shadow (100%, tools
sandboxed; watch latency/cost/errors + judge on samples) → canary 2% with
auto-rollback → A/B 50/50 for a pre-computed N → GA ramp behind kill-switch + D30
holdback.

**Measurement plan.** Unit = user (sticky hashed bucketing). OEC =
resolution-without-escalation; guardrails (non-inferiority) = CSAT, refund rate,
cost/task, p95 latency; diagnostics = per-tool success, tokens. Pre-compute N from
MDE; apply CUPED on prior-month resolution; SRM check at every ramp; sequential
boundary if the dashboard is watched continuously; segment new/returning and inspect
the daily trend for novelty; correct for multiplicity across guardrails.

**Failure handling.** SRM → halt and fix pipeline. Guardrail breach → no ship even
if OEC wins. Canary operational breach → auto-rollback. Offline/online
disagreement → root-cause the eval and log the data point.

**What I'd call out proactively:** tool side effects in shadow, latency-induced SRM,
the foundation model shifting under control, and the fact that the true retention
effect needs a holdback the main test won't see.

### Decision tables

**Staging technique — A/B vs. shadow vs. canary:**

| | Shadow | Canary | A/B test |
|---|---|---|---|
| User exposure | None (output discarded) | Tiny (1–5%) | Controlled (5–50%) |
| Primary question | "Can it run safely?" | "Is it on fire?" | "Is it better?" |
| Catches | Latency, cost, crashes, tool errors, drift | Catastrophic operational regressions | Causal effect on goal + guardrails |
| Statistical power | N/A (no outcomes) | Low (not powered) | Powered (that's the point) |
| Decision speed | Fast | Minutes (auto-rollback) | Days–weeks |
| Blind to | Anything a user must see | Small/slow effects | Effects < MDE or slower than window |
| Key risk | Unsandboxed side effects | Comparing vs. history not control | Peeking, SRM, novelty, interference |

**Metric role — goal vs. guardrail:**

| | Goal (OEC) | Guardrail |
|---|---|---|
| Question | "Did the thing we want improve?" | "Did anything we refuse to break, break?" |
| Test form | Superiority (is it > 0?) | Non-inferiority (rule out harm > X%) |
| Examples | Resolution rate, retention | p95 latency, cost/task, safety, refund rate |
| Decision role | Reason to ship | Veto on shipping |
| Failure mode | Goodhart (gamed proxy) | Blindness (unwatched harm) |
| Number needed | One (possibly composite) | Several, each catching a distinct harm |

### Red flags vs. green flags

Interviewers are listening for these.

| Red flag (junior) | Green flag (senior) |
|---|---|
| "The offline eval improved, so we shipped it." | "Offline is a gate; the A/B and guardrails decided the ship." |
| Reports a bare p-value. | Reports lift **with a CI**, read against the MDE. |
| Watches the dashboard and ships on first \( p<0.05 \). | Pre-registers N or uses a sequential boundary. |
| Never mentions SRM. | Checks SRM first and treats a breach as invalidating. |
| One success metric, no guardrails. | Every goal metric paired with a harm guardrail. |
| Randomizes per request for a chat agent. | Randomizes per user; cluster if units interact. |
| Believes the launch-week number. | Segments new/returning, checks the trend for novelty. |
| Runs an action agent in shadow, unsandboxed. | Sandboxes write-tools in shadow. |
| "Offline and online just differ, nothing to do." | Measures offline→online rank correlation; debugs disagreements. |
| Ships to 100% and moves on. | GA behind a kill-switch with live guardrail paging + holdback. |

---

## Further Reading

**Experimentation platforms and AI-eval products (2025–2026)**
- Statsig — AI Evals overview (offline + online LLM-judge, promote to experiment): <https://docs.statsig.com/ai-evals/overview>
- Statsig — AI Evals product page: <https://www.statsig.com/ai-evals>
- Statsig — Experimentation in the age of AI: <https://www.statsig.com/blog/experimentation-and-ai-trend>
- Statsig — Data-driven LLM optimization via online experimentation: <https://www.statsig.com/blog/llm-optimization-online-experimentation>
- Eppo (Datadog) — warehouse-native experimentation: <https://www.geteppo.com/>
- GrowthBook — open-source experimentation platform: <https://www.growthbook.io/products/experimentation>
- LaunchDarkly — feature management / progressive delivery: <https://launchdarkly.com/>
- GrowthBook vs. LaunchDarkly (candid comparison): <https://www.growthbook.io/insights/growthbook-vs-launchdarkly>

**Online LLM-as-judge and production evaluation**
- Statsig — Online Evaluation (grade live outputs, shadow-test prompts): <https://docs.statsig.com/ai-evals/overview>
- TrueFoundry — Online LLM evaluation at the gateway: <https://www.truefoundry.com/blog/online-llm-evaluation-gateway>
- Langfuse — LLM evaluation methods and best practices (2025): <https://langfuse.com/blog/2025-11-12-evals>
- Arize — LLM-as-a-Judge primer: <https://arize.com/guides/llm-as-a-judge/>
- Braintrust — LLM evaluation guide: <https://www.braintrust.dev/articles/llm-evaluation-guide>
- Evidently — LLM-as-a-judge complete guide: <https://www.evidentlyai.com/llm-guide/llm-as-a-judge>
- ZenML — What 1,200 production deployments reveal about LLMOps in 2025: <https://www.zenml.io/blog/what-1200-production-deployments-reveal-about-llmops-in-2025>

**Shadow, canary, and progressive delivery for agents/LLMs**
- FutureAGI — LLM eval with shadow traffic and canary deployment (2026): <https://futureagi.com/blog/llm-eval-shadow-traffic-canary-2026/>
- Nadir — "Shadow Mode, Forever": <https://getnadir.com/blog/shadow-testing-canary-rollout-llm-model-swap/>
- Qwak / JFrog ML — Shadow deployment vs. canary release of ML models: <https://www.qwak.com/post/shadow-deployment-vs-canary-release-of-machine-learning-models>
- MarkTechPost — Four controlled deployment strategies (A/B, canary, interleaved, shadow): <https://www.marktechpost.com/2026/03/21/safely-deploying-ml-models-to-production-four-controlled-strategies-a-b-canary-interleaved-shadow-testing/>

**Statistics: SRM, peeking, sequential testing, CUPED, guardrails**
- Diagnosing Sample Ratio Mismatch in A/B Testing — Microsoft Research: <https://www.microsoft.com/en-us/research/articles/diagnosing-sample-ratio-mismatch-in-a-b-testing/>
- Peeking at A/B Tests (Johari et al., KDD 2017): <http://library.usc.edu.ph/ACM/KKD%202017/pdfs/p1517.pdf>
- Wish tackles peeking with always-valid p-values: <https://towardsdatascience.com/wish-tackles-peeking-with-always-valid-p-values-8a0782ac9654/>
- Spotify — Choosing a sequential testing framework (mSPRT, GAVI, GST): <https://engineering.atspotify.com/2023/03/choosing-sequential-testing-framework-comparisons-and-discussions>
- Deep Dive into Variance Reduction (CUPED) — Microsoft EXP: <https://www.microsoft.com/en-us/research/group/experimentation-platform-exp/articles/deep-dive-into-variance-reduction/>
- GrowthBook — CUPED docs: <https://docs.growthbook.io/statistics/cuped>
- GrowthBook — Sequential testing docs: <https://docs.growthbook.io/statistics/sequential>
- GrowthBook — Power analysis docs: <https://docs.growthbook.io/statistics/power>
- CUPED reduces experiment runtime at the LA Times (GrowthBook): <https://blog.growthbook.io/cuped-for-faster-experimentation-in-growthbook/>
- Optimizely — CUPED in A/B testing: <https://www.optimizely.com/insights/blog/cuped-in-ab-testing-and-experimentation/>
- Data-Driven Metric Development (Deng & Shi, KDD 2016) — goal vs. guardrail: <https://exp-platform.com/Documents/2016KDDMetricDevelopmentLessonsDengShi.pdf>
- Guardrail Metrics: The Complete Guide — Mixpanel: <https://mixpanel.com/blog/guardrail-metrics/>

**Interference / network effects and the offline–online gap**
- Detecting Interference: An A/B Test of A/B Tests — LinkedIn Engineering: <https://engineering.linkedin.com/blog/2019/06/detecting-interference--an-a-b-test-of-a-b-tests>
- Reducing Interference Bias Using Cluster Randomization (Airbnb, Management Science): <https://pubsonline.informs.org/doi/10.1287/mnsc.2020.01157>
- Identifying Offline Metrics that Predict Online Impact (RecSys 2025): <https://dl.acm.org/doi/10.1145/3705328.3748111>
- Closing the Online-Offline Gap: A Scalable Framework for Composed Model Evaluation (RecSys 2025): <https://dl.acm.org/doi/10.1145/3705328.3748117>
- Offline Recommender System Evaluation: Challenges and New Directions (Castells & Moffat, AI Magazine 2022): <https://onlinelibrary.wiley.com/doi/10.1002/aaai.12051>

**Experimentation platform engineering (how the big platforms are built)**
- Under the Hood of Uber's Experimentation Platform: <https://www.uber.com/en-GB/blog/xp/>
- Supercharging A/B Testing at Uber: <https://www.uber.com/blog/supercharging-a-b-testing-at-uber/>
- Experiments at Airbnb: <https://medium.com/airbnb-engineering/experiments-at-airbnb-e2db3abf39e7>
- A curated list of experimentation-platform resources: <https://github.com/DavisTrey/ExperimentationResources>

---

*Previous: offline evaluation gives you a fast, cheap gate. This chapter gave you
the ladder — shadow, canary, A/B — that turns a green offline dashboard into a
safe, causal, guardrail-checked production decision, plus the platforms, runnable
statistics, war stories, and interview set-pieces to build it and defend it. Next:
closing the loop with continuous production monitoring as a first-class eval
surface.*
