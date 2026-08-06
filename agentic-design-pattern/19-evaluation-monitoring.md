# Pattern 19: Evaluation and Monitoring — Knowing Whether Your Agent Actually Works

## The interview scenario

This one shows up as:

- "You've built an agent and the demo looks great. How do you know it actually works — and how will you know when it stops working?"
- "Our agent's quality seems to have degraded over the past month, but nothing in the code changed. How would you investigate, and what should have been in place?"
- "How do you evaluate an agent when the outputs are free-form text and there's no single right answer?"

The trap is answering like it's a classic software testing question.

Agents are probabilistic — the same input can produce different outputs, "correct" is often a judgment call, and quality can rot with zero code changes. The interviewer wants to see you've internalized all three.

## What this pattern is, in plain words

Evaluation and monitoring is the measurement discipline for agents, and it has two halves separated by the moment you ship.

Offline evaluation happens before: you run the agent against a curated set of test cases with known good answers and score it, so you know whether this version is good enough and whether it beats the last one.

Online monitoring happens after: you watch the live system's accuracy, latency, cost, and behavior, so you notice when reality drifts away from your test set.

Because it will.

Two ideas make agent evaluation different from ordinary testing.

First, because outputs are free-form, exact-match checking is nearly useless. "Paris is the capital of France" and "The capital of France is Paris" fail a string comparison while meaning exactly the same thing.

The workhorse fix is LLM-as-judge: using a language model, armed with a written scoring rubric, to grade another model's output the way a human reviewer would.

Second, for agents you evaluate not just the destination but the route. The trajectory — the sequence of tool calls and steps the agent took — matters, because an agent can stumble into the right answer via an expensive, fragile, or outright dangerous path.

Outcome checks tell you whether it worked. Trajectory checks tell you whether it will keep working.

One housekeeping note: this playbook lives inside a repo with twelve deep chapters on exactly this subject — eval harness construction, judge calibration, metric design, the works.

So here I'll keep to the pattern-level view an interview needs: what to measure, when, and how the pieces close into a loop. When you want the full treatment, it's one directory over.

## How the design actually works

**Offline: eval sets and graders.** You build eval sets — collections of test cases, each with an input, the expected outcome, and, for agents, the expected trajectory: which tools should be called, with which arguments, in what order.

Small, fast test files act like unit tests during development — one session, quick to run, quick to localize a break.

Larger multi-turn eval sets act like integration tests before release, simulating complete realistic conversations.

Scoring combines three grader types, and the tradeoff between them is worth knowing cold.

Automated metrics — exact match, similarity scores — are cheap, objective, and shallow. LLM-as-judge is scalable and handles nuance like helpfulness or tone, but it's only as good as its rubric and its own underlying model. Human review catches the subtlest problems and is too slow and expensive to run on everything.

Mature setups use all three: automated checks for the bulk, judges for nuance, humans to spot-check the judges.

**Trajectory scoring** has its own menu, graded by strictness.

Exact match against the ideal tool sequence, for high-stakes flows where the path is the compliance requirement. In-order match — the right actions in the right order, extra harmless steps tolerated. Any-order match, looser still.

And precision and recall over actions, when the questions are "did it do anything irrelevant?" and "did it miss anything essential?"

You pick strictness per use case, not one global setting.

**Online: monitoring.** In production you watch a dashboard of vitals: task success rate, escalation rate, latency percentiles, token spend per interaction, error rates.

Two failure classes deserve names.

Drift is slow degradation with no code change — the world's inputs shifted away from what you tested on, or an upstream model changed under you.

Anomalies are sudden weirdness — an agent abruptly calling tools it rarely used, which might be a bug, an attack, or an emergent behavior worth investigating.

Both are detectable only if you log richly: every input, tool call, intermediate step, and output, traceably linked, in real storage feeding real dashboards. Not print statements.

**Closing the loop.** The piece that separates a real practice from theater: every interesting production failure gets triaged and added to the offline eval set.

Your test suite grows to mirror the real world's actual difficulty, and the same mistake can't sneak back in twice.

Offline evals gate what ships. Online monitoring catches what evals missed. Failures become new evals.

That circle is the pattern. And if you retain one diagram-in-words from this chapter, make it that circle: interviewers ask "how do you evaluate this" expecting a static answer — a test set, a metric — and the candidates who describe a *loop* instead of a snapshot are the ones who sound like they've operated a real system through a real quarter.

## The complete interview answer, spoken

"Three questions first.

"What does success mean for this agent — is there ground truth, like a resolved ticket, or is it subjective, like report quality?

"Second, what's the cost of a bad output — annoyance, or money and compliance exposure?

"Third, what data already exists — historical interactions I can mine for test cases?

"Say it's a customer support agent. Success is resolution without human escalation, bad outputs cost customer trust with occasional compliance exposure, and we have a year of human-agent transcripts.

"Good — that history is gold, because the hardest part of evaluation is usually getting realistic test cases, and we can mine ours instead of inventing them.

"I'd structure everything around one sentence: offline evals decide what ships, online monitoring catches what evals missed, and production failures flow back into the eval set. Let me build each piece.

"Offline first. From the transcripts I'd curate an eval set of a few hundred cases.

"Each case has the customer's request, the known good resolution, and the expected trajectory — the tool calls a competent agent should make: look up the order, check the refund policy, issue the refund, confirm to the customer.

"I'd deliberately stratify the set: common cases for coverage, rare-but-important cases so they're not drowned out, known hard cases, and a few adversarial ones borrowed from the guardrails suite. A set that's ninety percent easy cases produces scores that flatter you.

"This set becomes the gate. No prompt change, model upgrade, or new tool ships without beating the current version on it.

"That also gives us A/B discipline for free: two candidate designs, same eval set, pick with data instead of vibes. And when we do ship, we can A/B in production too — split traffic between versions and compare live metrics.

"A word on granularity, because it matters day to day. During active development I want small test files — single sessions, a handful of turns, seconds to run — so a developer knows within a minute whether their change broke something, and exactly which interaction broke.

"The big multi-turn eval sets are the integration layer: full realistic conversations, run before release and nightly. Unit-style checks for speed, integration-style checks for realism — the same division of labor as ordinary software testing, on purpose.

"Scoring is layered, because no single grader is honest about everything.

"Deterministic checks where possible: did the refund tool get called with the right amount? That's just code, and code doesn't hallucinate.

"Trajectory matching against the expected path. For compliance-sensitive flows I require the exact sequence — policy check *before* refund, always. For general queries, in-order matching that tolerates harmless extra steps. Strictness is a per-flow decision.

"And for the free-form reply itself, LLM-as-judge.

"One plain sentence for anyone new to the term: LLM-as-judge means using a language model with an explicit written rubric to grade outputs the way a human reviewer would — scoring accuracy, completeness, and tone, and returning structured scores with rationales. It scales to thousands of cases for pennies each.

"Its known weakness is that the judge can be wrong or biased. So I calibrate it: periodically have humans grade a sample of the same outputs, and measure judge-human agreement.

"If agreement drops, I fix the rubric before I trust the scores. An uncalibrated judge is a random number generator with good grammar.

"Why trajectories and not just outcomes? Because an agent that got the right answer by calling seven tools where two would do is a cost bug today and a reliability bug tomorrow.

"And an agent that guessed right without checking the database is a time bomb — it'll guess wrong tomorrow with the same confidence. The route is evidence about the future in a way the destination alone never is.

"Now online. The whiteboard:

```
        OFFLINE                      ONLINE
  +----------------+          +------------------+
  | eval set       |  gates   | live agent       |
  | - cases        | -------> | - logs: inputs,  |
  | - trajectories |  deploy  |   tools, outputs |
  | - judge rubric |          | - dashboards     |
  +----------------+          +--------+---------+
         ^                             |
         |   failures become new       | drift &
         +-------- test cases <--------+ anomaly
                (close the loop)         alerts
```

"In production, every interaction is logged with full structure — the input, each tool call and its result, the trace of steps, the output, latency, and token counts — into real storage feeding dashboards.

"Structured logs, not console prints, because you can't query a print statement at 2 a.m. during an incident.

"The vitals on the dashboard: resolution rate, escalation rate, latency percentiles, cost per conversation.

"Plus a continuously running LLM-as-judge sampling a slice of live traffic — say five percent — for quality scoring, because you cannot wait for complaint tickets to find out quality dropped. Complaints are a lagging indicator with a terrible signal-to-noise ratio.

"Two alarms I'd wire specifically.

"Drift: quality decaying with no code change. New products launch, customer language shifts, an upstream hosted model gets silently updated. It shows up as a slow slide in judged quality or resolution rate.

"The fix is refreshing both the prompts and the eval set to match the new reality — which is exactly why the eval set can't be a museum piece curated once and admired forever.

"Anomalies: sudden behavioral weirdness. The tool-call distribution shifts overnight; escalations spike at 3 a.m.

"Worth an alert every time, because the cause might be a bug, an attack, or something genuinely new in the world — and all three are things you want to know about within hours, not weeks.

"For the compliance side — imagine some of these flows are regulated — I'd add automated audit reports: periodic summaries of the agent's adherence to policy, generated from the logs, reviewable by a human or even by another agent, with alerts wired to violations.

"Regulators and risk teams don't want dashboards; they want evidence trails. The logging we already built produces them nearly for free.

"And the loop-closer, which I'd call out as the single highest-leverage habit in this whole pattern: a weekly triage of production failures — wrong answers, bad escalations, judge-flagged samples — where each interesting one becomes a new eval case.

"Six months in, the eval set is no longer what we imagined users would ask. It's what they actually ask, weighted toward what we actually get wrong. That compounding is what makes the practice real.

"Tradeoffs. Eval sets cost curation time and rot without maintenance. LLM-as-judge adds its own model spend and its own error bars.

"Logging everything has storage and privacy implications — transcripts get retention policies and personal-data scrubbing, and I'd say so before the interviewer asks.

"And a subtle one: overfitting to your own evals. If the team optimizes the same three hundred cases for a year, you get an agent that's great at those three hundred cases and stale at reality. Rotation, held-out cases, and fresh sampling from production are the antidote.

"Cost, to put numbers on it. Judging a few hundred eval cases with a small model costs a few dollars per run — cheap enough to run on every change in CI. Sampled online judging at five percent of traffic adds low single-digit percent to model spend. Storage for logs is rounding error.

"Compare that to flying blind: a quality regression you discover from churn a month late costs incomparably more.

"Measurement is the cheapest component in the entire system, and it's the one that makes every other component improvable."

## Follow-ups they will ask

**"How do you evaluate when there's no single right answer?"**

"Rubric-based judging. You can't string-match a good research summary, but you can decompose 'good' into named criteria — factual accuracy, completeness, clarity, tone — and have an LLM judge score each criterion with a rationale.

"Then calibrate: humans periodically grade the same samples, and you measure agreement. If judge and humans diverge, fix the rubric before trusting the scores. Subjective doesn't mean unmeasurable; it means measured through a calibrated proxy."

**"What's the difference between evaluating an agent and evaluating a model?"**

"A model gets one input and produces one output — you grade the output. An agent takes a journey: tool selections, arguments, intermediate steps, recovery from errors.

"So agents get trajectory evaluation on top of outcome evaluation — comparing the path taken against a reference path, with strictness matched to stakes. Two agents with identical final answers can deserve opposite grades once you look at how they got there."

**"How would you evaluate a multi-agent system?"**

"Per-agent plus system-level, like grading a team project. Each specialist gets its own evals, but the interesting failures live in the handoffs.

"Did the flight-booking agent pass the correct dates to the hotel-booking agent, or did someone get a room for the wrong week? Did the system follow its plan, or did an agent book out of order — or get stuck endlessly optimizing one step? Did the router pick the right specialist, or did a generic agent answer a question a specialist should have taken?

"And the question people skip: when you add another agent, does end-to-end performance actually improve, or did you just add coordination overhead? Measure the system, not just the parts."

**"What is drift, concretely?"**

"Performance decaying with no code change, because the world moved. The input distribution shifts — new products, new slang, new failure modes — or an upstream dependency like a hosted model changes beneath you.

"You catch it with trend monitoring on quality metrics over weeks, not with point-in-time tests. It's the reason evaluation is a continuous practice rather than a launch task."

**"Where do 'AI contracts' fit into this picture?"**

"They're the accountability endpoint of the whole evaluation story. Instead of a vague prompt, the task is specified like a formal agreement — exact deliverables, scope, quality criteria, even expected cost and completion time — so the output is objectively checkable against terms.

"The agent can negotiate ambiguities up front, flag inaccessible resources, decompose big jobs into subcontracts for other agents, and self-validate its work against the terms before submitting. It's evaluation moved from after-the-fact grading into the task definition itself, and it's where high-stakes agent deployment is heading."

**"What's the minimal viable evaluation for a two-week-old prototype?"**

"Twenty to fifty representative cases in a file, run on every change. Score with simple deterministic checks plus a rough LLM judge. Log everything from day one, even if nobody's dashboarding it yet — you can build dashboards later, but you can't log retroactively.

"That's an afternoon of work, and it beats 'it seemed fine when we tried it' by roughly infinity."

## Say it in one breath

"Evaluation and monitoring is how you know your agent works: offline, a curated eval set with expected outcomes and expected trajectories gates every change, scored by deterministic checks, LLM-as-judge — a model grading against a written rubric — and calibrated human spot-checks; online, structured logging feeds dashboards for success, latency, cost, and judged quality, with alarms for drift and behavioral anomalies; and the loop closes by turning every interesting production failure into a new test case. Outcome checks tell you whether it worked, trajectory checks tell you whether it'll keep working — and this repo has twelve chapters going deeper, because this is the pattern the whole guide exists for."
