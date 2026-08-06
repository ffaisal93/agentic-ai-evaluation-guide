# Pattern 20: Prioritization — Deciding What Deserves the Agent's Next Minute

## The interview scenario

You'll meet this as:

- "Our agent serves thousands of requests — some are 'the system is down,' some are 'change my email address.' Right now it processes them in arrival order. Design something better."
- "An agent is midway through a routine task when a critical alert arrives. What should happen, architecturally?"
- "How do you stop important-but-not-urgent work from being postponed forever in an agent system?"

Underneath all three: does your agent know what matters?

And can it change its mind about that when the world changes?

## What this pattern is, in plain words

Any agent doing real work faces more demands than it has capacity — more requests than workers, more sub-tasks than time, sometimes goals that outright conflict.

First-come-first-served treats a data-center outage and a newsletter unsubscribe as equals, which is obviously wrong.

Nobody runs a hospital waiting room that way. Triage exists because arrival order and importance are different things.

Prioritization is the pattern of scoring work and ordering it deliberately.

The classic axes are urgency — how time-sensitive is this, what decays if it waits — and importance — how much does it matter to the actual goal.

They're independent, and confusing them is the classic junior mistake. Plenty of urgent things are trivial. Plenty of vital things have no deadline pressing on them.

Add dependencies (is this task blocking others?), cost versus benefit (what does it take versus what does it return?), and any business weighting like customer tier, and you have scoring criteria.

Score the work. Rank it. Execute from the top.

Three vocabulary words carry the senior version of this answer.

Preemption: dropping or pausing a low-stakes task the moment a high-stakes one arrives, instead of dutifully finishing the queue you happened to start.

Starvation: the failure mode where low-priority work waits forever, because something more important always exists.

And aging: starvation's standard cure — a task's effective priority creeps upward the longer it waits, so everything eventually gets its turn.

## How the design actually works

Four components, in the order the book presents them.

**First, criteria definition.** An explicit, written list of what makes work important here: urgency, importance to the primary objective, dependency structure, resource readiness, effort versus payoff, and domain-specific factors like customer tier or safety impact.

Explicit matters. Criteria in a document can be reviewed, tuned, and defended to an angry stakeholder.

Criteria implicit in an LLM's vibes cannot.

**Second, task evaluation.** Scoring each piece of work against those criteria.

The spectrum runs from plain rules ("outage keywords map to P0") through weighted numeric scoring to an LLM classifying nuanced language.

The model earns its place in the gray zone: it can read "I'm locked out and my presentation to the board is in an hour" and correctly hear urgency that no keyword list would catch.

A robust design layers the two — rules for the unambiguous fast path, model judgment for ambiguity.

**Third, scheduling.** A priority queue — a work list that always serves the highest-ranked item next rather than the oldest — plus the policy around it: how many things run concurrently, what happens on ties, and whether high-priority arrivals preempt work already running.

**Fourth, dynamic re-prioritization.** Priorities are re-evaluated as circumstances change, because a ranking is perishable.

A new critical event, an approaching deadline, a dependency resolving — each can reshuffle the order.

This is also where aging lives: waiting time feeds back into effective priority, so the bottom of the queue rises instead of rotting.

And note the altitudes. Prioritization applies to which overall goal to pursue (strategic), which step of the plan to do next (tactical), and which immediate action to take right now (operational).

Same machinery, three levels — and a good agent runs it at all three.

## The complete interview answer, spoken

"Quick scoping questions.

"What's the mix of work — interactive requests, background tasks, or both? What's the spread of stakes — what's the worst thing that can be in the queue, and the most trivial? And are there hard business rules I must honor, like contractual response times for premium customers?

"Let's say it's an IT operations agent: a mixed stream of incident alerts, employee requests, and scheduled maintenance. Stakes range from 'production is down' to 'please rename my distribution list.'

"And there are premium internal SLAs — service-level agreements, meaning promised response times — for certain systems.

"Perfect prioritization territory: mixed stakes, limited capacity, and a world that changes under you.

"First thing I'd do is write the criteria down, because prioritization you can't explain is prioritization you can't tune. Four axes.

"Urgency: what breaks or decays if this waits an hour? An active outage is maximally urgent; a rename request is not urgent at any hour of any day.

"Importance: business impact. Anything affecting production or many users weights up. A single user's inconvenience weights down — even when that user is loud.

"Dependencies: a task that unblocks five others inherits some of their weight, because finishing it releases more value than its own score shows. Dependency-aware ranking is one of those details that quietly separates good schedulers from naive ones.

"And cost-benefit: a thirty-second fix that closes three tickets is a bargain, and the scorer should treat it like one.

"Scoring runs in two stages — cheap first, smart second.

"Stage one is rules. Alert source and keywords map straight to priority bands: anything from the production monitoring system with outage semantics is instantly P0. No model call, no milliseconds wasted, and completely auditable.

"Stage two, for everything ambiguous, is an LLM classifier that reads the request and assigns a band with a one-line rationale.

"It's what can tell 'laptop slow, no rush' from 'laptop dying and I present to the board at nine' — a distinction keyword rules will never make, because the urgency lives in the context, not in any single word.

"The rationale gets logged. When a human asks 'why was my ticket ranked below that one,' 'the model said so' is not an answer — but the logged reasoning is.

"And the scorer applies sensible defaults when information is missing: an unlabeled request gets middle priority and a standard assignee rather than stalling the pipeline waiting for perfect metadata.

"The book's project-manager example does exactly this — no priority mentioned means P1 and a default worker, and the flow keeps moving.

"The whiteboard:

```
 incoming work
      |
 [score]  rules first, LLM for the gray zone
      |
      v
 PRIORITY QUEUE          workers
 | P0: outage   | ---->  [w1] [w2] [w3]
 | P1: SLA risk |            ^
 | P2: routine  |            | preempt: P0 arrival
 | (aging: waiting           |  pauses/checkpoints
 |  raises priority)         |  a P2 in flight
      ^
      | re-score on events & timers
```

"Execution is a priority queue feeding a worker pool — highest rank next, never oldest next.

"And the two policies on top of that queue are where the real design lives.

"Policy one: preemption. When a P0 lands and all workers are busy on routine work, we don't finish the queue we happened to start.

"A worker checkpoints its P2 task at the nearest safe boundary — meaning a point where pausing leaves no half-applied change — and takes the P0 immediately.

"That safe-boundary clause matters. Preempting mid-write can corrupt state. So tasks declare their pause points, and a truly unpausable critical section finishes first, briefly delaying preemption rather than corrupting data.

"The routine task resumes afterward from its checkpoint rather than starting over, so the preempted work isn't wasted — just deferred.

"Policy two: starvation control. Pure priority queues have a cruel property — if high-priority work keeps arriving, low-priority work waits literally forever.

"That rename ticket is nobody's emergency, but week three of waiting is a failure too.

"And worse: some of those quiet tickets are important-but-not-urgent — the certificate renewal, the backup that's been failing silently — exactly the category pure urgency-sorting systematically abuses until it becomes an emergency.

"The fix is aging: effective priority equals base priority plus a bonus that grows with waiting time, so everything eventually climbs high enough to run.

"I'd also reserve a slice of worker capacity — say ten percent — for the lowest band regardless of queue state, which guarantees background progress even during a bad week. Two mechanisms, same goal: nothing waits forever.

"One structural note I'd drop in: this same machinery runs at three altitudes. Strategically — which objectives get the quarter. Tactically — which step of a plan runs next. Operationally — which item gets the next worker, which is what we've been designing.

"A mature agent prioritizes at all three, and the criteria weight differently by altitude: strategy leans on importance, operations leans on urgency. Saying that unprompted shows you see the pattern, not just the queue.

"Then dynamic re-prioritization, because a ranking is a snapshot of a moving world.

"Scores get recomputed on events — a dependency resolving, an incident escalating, three tickets arriving that share a root cause and should merge into one. And on timers — as an SLA deadline approaches, its ticket gets pulled upward automatically.

"Let me make that concrete with one story, because it's the part interviewers most enjoy probing.

"At 9 a.m., a ticket arrives: 'the staging database is slow.' Scored P2 — it's staging, nobody's hard-blocked. At 11, a second ticket: 'deploys are failing.' At 11:30, a third: 'release is blocked, and launch is today.'

"A static system holds three separate mediocre priorities. A dynamic one clusters them — same root cause — re-scores the cluster against the launch deadline, and promotes the whole thing to P0 with a rationale: 'staging degradation is now blocking today's release.'

"That's the behavior the re-scoring triggers exist to produce. The agent that ranked something P2 at 9 a.m. should be capable of calling it P0 at noon without a human forcing the issue.

"Failure modes I'd name unprompted.

"Priority inflation: everyone marks their own request urgent, because of course they do. So the scorer trusts evidence — source system, measured impact, affected user count — over the requester's self-declared severity. The requester's claim is one weak input, not the answer.

"Thrashing: if preemption is too eager, workers ping-pong between tasks and finish nothing. So preemption triggers only across a band gap — P0 over P2, yes; P1 over P1, never — and the decision includes a small switching cost, so marginal swaps don't happen.

"And scorer failure: if the LLM classifier is down or slow, we degrade to rules-plus-FIFO rather than halting intake. A mediocre ordering beats a frozen queue, every time.

"Evaluation and monitoring — the metrics here are queue-shaped.

"Time-to-start and time-to-resolution *per priority band*: P0s should start in seconds, and the P2 tail tells me whether aging actually works.

"Preemption counts, and what preempted what — a preemption spike means either a rough week or a miscalibrated scorer, and I want to know which.

"Scorer accuracy, audited by sampling: a human reviews a slice of rankings weekly, we track agreement, and misranked cases become test cases for the scorer. Same close-the-loop discipline as the evaluation pattern — the scorer is a model, so it gets evaluated like one.

"And one dashboard number I love: the age of the oldest waiting item. If that number grows without bound, starvation is happening, no matter what the averages claim.

"Averages hide the tail. The max exposes it.

"Cost: the machinery is nearly free. A queue is trivial infrastructure, and LLM-scoring a ticket costs a fraction of a cent — only spent on the ambiguous cases anyway, since rules handle the obvious ones.

"The real cost is misprioritization: an outage waiting behind routine work is measured in thousands of dollars a minute.

"This is the cheapest pattern in the book relative to what it protects."

## Follow-ups they will ask

**"Urgency versus importance — why do you keep separating them?"**

"Because collapsing them is how systems rot. Urgent-trivial work steals capacity from important-quiet work — the security patch, the failing backup — which never screams until it's a disaster.

"Scoring them separately lets the policy protect important-but-not-urgent work explicitly, through aging and reserved capacity, instead of hoping it survives the noise. If I only rank by urgency, I've built a machine that manufactures next month's emergencies."

**"When are simple rules enough, and when do you need an LLM scorer?"**

"Rules when the signals are structural — source system, keywords, customer tier. They're fast, free, deterministic, and auditable, and they should always take the unambiguous fast path.

"The LLM earns its cost in the gray zone, where urgency lives in natural language and context. Layer them, and log every model ranking with its rationale so the nuanced half stays as auditable as the rules half."

**"Walk me through preemption and its risks."**

"Preemption is dropping or pausing low-stakes work the moment high-stakes work arrives.

"Risk one is corrupting state by interrupting mid-operation — so pause only at declared safe boundaries, with checkpoints to resume from. Risk two is thrashing — switching so often nothing completes — so require a big priority gap to trigger it and charge a switching cost in the decision.

"Risk three is that the preempted task must actually resume afterward, which means checkpoint-and-resume is a tested code path, not an aspiration in a design doc."

**"Explain starvation and aging like I've never heard the terms."**

"Starvation: in a queue that always serves the most important item first, an unimportant item can wait forever, because something more important always exists.

"Aging is the fix: the longer a task waits, the higher its effective priority creeps, so everything eventually reaches the front.

"It's the difference between 'important things first' and 'important things first, but nothing waits forever' — and only the second is a system you can actually run."

**"Doesn't the planning pattern already order the work? Why is this separate?"**

"Planning orders steps *within* one goal; prioritization arbitrates *across* goals and across arriving work, under change.

"A plan is a static route. Prioritization is the dispatcher deciding which route gets the trucks today — and re-deciding at noon when a bridge closes. Agents juggling real workloads need both, and dynamic re-prioritization is precisely the part a static plan cannot do."

**"How does this show up outside ticket queues?"**

"Everywhere agents face choice under constraint. An autonomous vehicle prioritizes braking over lane discipline over fuel economy — action selection at millisecond scale. A cloud agent gives critical applications resources at peak and shunts batch jobs to off-peak hours. A security agent ranks alerts by threat severity and asset criticality. A trading bot weighs risk, margin, and breaking news before executing. A personal assistant orders your day by deadlines and stated preferences.

"Same skeleton every time: criteria, scoring, selection, re-evaluation."

## Say it in one breath

"Prioritization is how an agent decides what deserves its next minute: define explicit criteria — urgency, importance, dependencies, cost-benefit — score incoming work with cheap rules plus an LLM for the nuanced cases, run a priority queue, and re-score as the world changes. The senior details are preemption — pausing low-stakes work at safe checkpoints when high-stakes work arrives, without thrashing — and starvation control through aging, so low-priority work's rank rises as it waits instead of waiting forever. Log every ranking's rationale, watch time-to-start per band and the age of the oldest waiting item, and remember the machinery costs pennies while misprioritization costs outages."
