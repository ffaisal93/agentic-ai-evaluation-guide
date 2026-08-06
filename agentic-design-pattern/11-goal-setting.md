# Pattern 11: Goal Setting and Monitoring — Give the Agent a Definition of Done

## The interview scenario

Listen for these setups:

- "We tell our agent 'research this company and produce a due-diligence brief,' and
  sometimes it returns something great, sometimes it browses in circles for twenty minutes
  and returns mush. Make it reliable."
- "Product wants the agent to 'improve the weekly report.' That's the actual ticket. How
  do you turn that into something an autonomous system can be held accountable to?"
- "Our autonomous agent occasionally gets stuck in loops and burned 400 dollars of API
  calls overnight. Design the guardrails."

The common thread: the agent has capability but no operational definition of success, no
self-awareness of progress, and no limits. The interviewer wants you to supply purpose,
measurement, and brakes.

## What this pattern is, in plain words

Think about how you plan a trip. You don't teleport to a destination; you decide where
you're going, note where you're starting from, and map the steps between — book the
flight, pack, get to the airport. But — and this is the part this pattern adds on top of
planning — while traveling you also continuously check yourself against the plan: am I at
the gate on time, did the connection get cancelled, am I actually getting closer to Lisbon
or have I been circling the terminal? Goal setting is fixing the destination in checkable
terms; monitoring is the running comparison between where you are and where you said you'd
be.

For agents, the pattern has two halves. First, take the fuzzy human objective — "improve
the report," "resolve the customer's billing issue" — and compile it into explicit success
criteria a machine can check: conditions that are concretely true or false, with numbers
where possible. Second, wrap the agent's execution in a monitoring loop that continuously
compares reality against those criteria and against expected progress, so the system can
tell the difference between "working," "done," and "stuck" — and act on that difference by
continuing, finishing, replanning, or escalating to a human.

The everyday analogy I'd use: a manager delegating to a new hire. A bad manager says "make
the report better" and checks back in a month. A good manager says "done means: under two
pages, includes the churn numbers, finance signs off, delivered by Friday" — and then
checks in at checkpoints, notices if the hire has been stuck rewriting the intro for three
days, and steps in. This pattern is about building the good manager into the system.

There's a useful acronym interviewers like: goals should be SMART — specific, measurable,
achievable, relevant, and time-bound. It's a management-school term, but it translates
directly into engineering: "measurable" becomes automatically checkable, and "time-bound"
becomes a budget.

## How the design actually works

Four components, in the order data flows through them.

**Component one: goal compilation.** Before the agent takes a single step, the fuzzy
objective gets translated into a goal contract — a structured statement of what done
means. For "resolve the billing inquiry": the billing record reflects the correction, the
customer has been told, and the customer confirms or at least doesn't dispute. For a
research brief: covers financials, leadership, litigation, and market position; every
claim carries a source; under 1,500 words. Some criteria are objectively checkable by code
(word count, record updated, tests pass); some need judgment (is the summary accurate?),
which means a model will act as evaluator — with a caveat coming below. Who writes the
contract? For repeated workflows, developers, ahead of time. For open-ended requests, the
agent itself can draft criteria from the request — and for anything consequential, echo
them to the user for confirmation, which is cheap and catches misunderstandings before
they compound into an hour of wrong work.

**Component two: the execution loop with progress state.** The agent plans sub-goals — the
intermediate steps toward the objective — and works through them, and the system maintains
explicit progress state: which criteria are satisfied, which sub-goals are complete,
what's been tried. This sounds mundane and is everything: without explicit state, "how's
it going?" is unanswerable, and both stuck-detection and resumption after failure become
impossible.

**Component three: the monitor.** This is the pattern's heart, watching three things.
First, *criteria satisfaction* — after each meaningful step, are more success conditions
true than before? A judge evaluates draft-vs-contract. Here's the caveat the book is
emphatic about, and you should be too: when the same model both produces the work and
grades it, evaluation goes soft. The model may not truly grasp the goal yet confidently
declare success, it may hallucinate quality, and a producer grading its own work struggles
to notice it's headed the wrong direction. The practical fix is separation of concerns: a
distinct judge — separate prompt at minimum, separate model ideally, real code checks
wherever possible (run the tests, count the words, verify the record actually changed) —
because a critic with no authorship stake evaluates far more objectively. Multi-agent
setups take this further: a reviewer agent, a test-writer agent, each with an
adversarial-ish role against the producer. Second, *stuck and loop detection*. Signatures
worth naming: the same tool called with the same arguments repeatedly; many steps with
zero change in criteria satisfied; oscillation, where the agent alternates between two
states, doing and undoing; and thrash, high activity with no progress — long transcripts,
nothing checked off. Detection can be rule-based (hash recent actions, alert on repeats;
alert on N steps without progress) plus, for subtler pathologies, an *overseer* — a
separate model that periodically reads the agent's recent trajectory and answers "is this
going anywhere?" That's exactly the architecture the self-improving-agent research used:
an independent watcher over the logs, empowered to warn or halt. Third, *budgets* — the
guardrails around every goal: maximum steps, maximum tokens, maximum dollars, maximum
wall-clock time, sometimes per-tool caps. Budgets are what turn "the agent looped
overnight and burned 400 dollars" into "the agent stopped at its 5 dollar cap and filed a
report." A goal without a budget is an unbounded liability; every goal ships with its
brakes.

**Component four: the response policy.** Monitoring is worthless unless verdicts trigger
action. All criteria satisfied: finish, and record the final check. Progress but
incomplete: continue. Stuck: intervene — first a nudge (inject the failure summary into
context and ask the agent to reconsider its approach, which is reflection triggered by
monitoring), then replan from the last good checkpoint, then escalate. Budget exhausted or
hard-stuck: stop cleanly and escalate to a human with a structured handoff — goal,
criteria met and unmet, what was tried, best partial result. A great agent's failure mode
is a useful status report, not a dead session.

**Failure modes of the pattern itself.** The lenient judge — self-graded success theater —
countered by separation and code checks as above. The mis-compiled goal: perfect pursuit
of the wrong criteria, countered by echoing the contract to the human up front. Metric
gaming: the agent satisfies the letter of a criterion while missing its point ("include
churn numbers" produces a table with no analysis) — countered by writing criteria about
outcomes not artifacts, and keeping a judgment-based criterion alongside mechanical ones.
And monitoring overhead: judging after every step can cost more than the work; calibrate
cadence to checkpoints, not tokens.

**When to use and not.** Use it whenever an agent runs multi-step and unattended —
autonomy without monitoring is hope as a strategy. Skip the heavy machinery for
single-shot Q&A or workflows so short a human watches every step; there, budgets alone (a
timeout and a token cap) are plenty. **Neighbors:** planning decides the route;
goal-monitoring checks you're on it and notices when you're not — planning without
monitoring is a map with no driver awareness. Reflection is the agent critiquing its work;
monitoring is the standing system that decides when critique or replanning is warranted
and enforces limits regardless. Exception handling (next pattern) catches operations
failing loudly — errors, timeouts; goal monitoring catches the quieter disease: everything
succeeding while the mission fails.

## The complete interview answer, spoken

Spoken answer to "our research agent sometimes returns mush and once looped overnight —
make it reliable."

"Clarifying questions first. What does the output feed into — a human analyst reviewing
it, or something automated? — assume a human analyst, so partial results have value and
escalation is acceptable. Latency and cost envelope per brief? — say a soft target of ten
minutes and about 2 dollars, hard ceiling of thirty minutes and 5 dollars. And how uniform
are the requests? — mostly a repeatable shape, 'due-diligence brief on company X,' so we
can invest in a standing goal template rather than deriving criteria fresh each run.

My design is: compile the goal into a contract, execute against explicit progress state,
monitor with a separate judge plus a stuck-detector, enforce budgets, and define exactly
what happens on each monitor verdict.

Goal compilation. 'Research the company and produce a brief' becomes a contract with two
kinds of criteria. Mechanical, checkable by code: covers the four required sections —
financials, leadership, legal exposure, market position; between 800 and 1,500 words;
every factual claim has a citation; at least five distinct sources; delivered inside
budget. Judgment-based, needing an evaluator: claims are supported by cited sources, no
glaring omissions given what the sources contain, coherent for an analyst audience. I'd
keep the mechanical list dominant, because code checks can't be sweet-talked. The contract
is a standing template with per-request parameters, and the agent's first step is
instantiating it and echoing one line back to the requester — 'producing a four-section
cited brief on X, ten-minute target' — a cheap catch for mis-scoped requests before we
spend anything.

Execution with progress state. The agent plans sub-goals — identify sources, gather per
section, draft, verify citations — and the system tracks a live scoreboard: sections
drafted, criteria satisfied, sources collected, budget consumed. This makes the run
legible in real time; an operator can glance at any in-flight brief and see a checklist,
not a wall of transcript.

Monitoring, three layers. Layer one, the judge: at checkpoints — end of each section and
end of full draft, not every step, to keep evaluation overhead maybe ten percent of run
cost — a separate evaluator scores the work against the contract. Separate is
load-bearing. If the writer grades itself, evaluation goes soft: the same model that
misunderstood the goal will confidently certify the misunderstanding, and a producer
rarely notices it's going in the wrong direction. So: distinct judge prompt with a strict
rubric, ideally a different model, and it never sees the writer's reasoning — only the
draft and the contract, like a reviewer with no authorship stake. Mechanical criteria
don't even go to a model; code counts the words and verifies each citation URL was
actually fetched during the run — which is our hallucination tripwire, since fabricated
sources fail that check instantly.

Layer two, the stuck-detector, aimed at the overnight-loop incident. Rules: hash each tool
call with arguments and flag repeats — same query re-searched three times is a loop
signature; flag N consecutive steps with zero scoreboard movement; flag oscillation, where
the draft alternates between two states as the agent does and undoes the same edit. Rules
are cheap and catch the common cases. For subtler thrash — lots of plausible activity, no
convergence — a lightweight overseer model reads a trajectory summary every few minutes
and answers one question: is this progressing toward the contract? That
watcher-over-the-worker design comes straight from self-improving-agent research, where an
independent overseer monitors for stagnation and can halt the agent, and it's the right
shape here.

Layer three, budgets — the non-negotiable brakes: 5 dollars, thirty minutes, a step cap
around 60 tool calls, and a per-source cap so one bottomless website can't eat the run.
Enforced by the harness outside the model — the agent can't talk its way past them — with
a warning injected at 80 percent so it can prioritize finishing over exploring.

Response policy, the monitor's verdicts wired to actions. All criteria pass: finalize,
attach the scoreboard as a quality receipt. Progress, incomplete: continue. Judge fails a
section: one targeted revision with the judge's specific findings injected — that's
reflection, triggered by monitoring rather than by habit — and a section that fails twice
gets flagged in the deliverable rather than looped on, because the second identical
failure predicts a third. Stuck-detector fires: checkpoint, then a strategy nudge — 'your
last four searches returned overlapping results; change approach' — then one replan from
the last good checkpoint; still stuck, stop. Budget out or hard-stopped: emit a structured
partial — sections done, criteria unmet, sources found, what was attempted — because the
analyst getting three solid cited sections plus an honest gap report beats both mush and
nothing. That single change, honest partials instead of degraded completions, is half the
perceived-reliability win.

The whiteboard:

```
 request --> [Goal compiler] --> contract (criteria + budgets)
                                    |
                                    v
        +----------> [Agent: plan / act / draft]
        |                 |            ^
        |                 v            | nudge / revise / replan
        |          [Progress state] ---+
        |            |         |
        |            v         v
        |   [Judge vs      [Stuck detector
        |    contract]      + overseer + budgets]
        |        \             /
        |         v           v
        +------ continue   stop --> finish (all pass)
                                --> escalate (partial + report)
```

Evaluation of the system itself: I'd keep a benchmark set of companies with analyst-graded
reference briefs and score the pipeline weekly — completion rate inside budget,
criteria-pass rate, analyst satisfaction, and dollars per accepted brief. The two
dashboard numbers I'd watch daily: percentage of runs finishing under soft budget, and
escalation rate. Escalations trending up means the contract or the tools drifted from
reality; near-zero escalations with mediocre output means the judge has gone lenient —
both are drift alarms.

Cost: monitoring adds judge calls and the overseer — roughly ten to fifteen percent per
run. Against it: the loop incident alone burned 400 dollars, and every mush brief costs an
analyst's hour plus trust. Bounded runs plus honest partials pays for the overhead many
times over."

## Follow-ups they will ask

**"How exactly do you detect a stuck agent?"** Layered. Cheap rules: repeated identical
tool calls (hash action plus arguments), N steps with no change in criteria satisfied, and
oscillation between two states. Then an overseer — a separate model periodically reading
the trajectory and judging whether it's converging, which catches thrash that rules miss:
plenty of plausible activity, zero progress. And budgets as the backstop that bounds the
damage even when detection fails.

**"Can the agent judge its own success?"** For mechanical criteria, code judges — no model
involved. For quality, a self-graded agent is unreliable: it may misconstrue the goal and
confidently certify the misconstrual, hallucinate quality, and struggle to see it's
off-course while it's the author. So separate the judge — distinct prompt, ideally
distinct model, seeing only the artifact and the contract. Multi-agent crews formalize
this: a dedicated reviewer, a dedicated test-writer, each structurally independent of the
producer.

**"Budget's exhausted but the agent says it's 90 percent done — what happens?"** The hard
ceiling holds; that's what makes it a ceiling — models predictably claim near-completion,
and 'just one more step' is exactly the loop failure mode. Design instead: a warning at 80
percent so the agent lands the plane, and on exhaustion a structured partial — criteria
met, criteria missed, best artifact — so a human can spend one extra dollar knowingly if
warranted. Extension is a human decision, never the agent's.

**"What stops the agent gaming the criteria?"** Goodhart's law applies to agents: make the
metric the target and it stops measuring what you meant. Defenses: write criteria about
outcomes, not artifacts — 'claims verified against fetched sources,' not 'has citations';
check what can't be faked, like whether the cited URL was actually retrieved this run; and
always pair mechanical criteria with one judgment-based criterion scored by an independent
judge, so ticking boxes hollowly still fails.

**"How is this different from just planning?"** Planning produces the route; this pattern
is the instrumentation for the journey — the checkable definition of the destination, the
live comparison of position against route, and the tripwires for off-course, stuck, or out
of fuel. A plan without monitoring fails silently; monitoring without a plan has nothing
to measure against. They compose: the monitor is what triggers replanning.

**"What makes a goal well-formed for an agent?"** SMART, translated to engineering:
specific — unambiguous scope; measurable — every criterion checkable by code or a
rubric-bound judge; achievable — within the agent's actual tools, verified rather than
assumed; relevant — traceable to what the requester meant, which the echo-back confirms;
time-bound — budgets on time, steps, tokens, and dollars. If a criterion can't be checked,
it isn't a criterion yet — decompose until it can be.

## Say it in one breath

Goal Setting and Monitoring compiles a fuzzy objective into a contract of checkable
success criteria, then wraps execution in a watchdog: a judge — separate from the
producer, because self-graded work goes soft — scores progress against the contract, a
stuck-detector catches loops and thrash, and budgets on steps, tokens, dollars, and time
bound the blast radius. Every verdict is wired to an action — continue, revise, replan, or
stop and hand a human an honest partial with a status report. It's how an agent knows the
difference between working, done, and stuck — instead of hoping.
