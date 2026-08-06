# Putting it all together

You now hold twenty-one patterns. That's a toolbox, not an answer — interviews hand you scenarios, and the skill is reaching for the right three or four tools fast and composing them out loud.

This closing section is that skill, in three parts: a lookup table, four fully-composed mega-answers, and a short note on how to practice.

## The pattern picker

When the scenario lands, your first silent move is mapping it to patterns. Here's the cheat sheet I'd have burned in before walking into the room.

Pattern numbers refer to this playbook's Parts 1 through 5.

| When the interviewer says... | Reach for |
|---|---|
| "Answer questions from our internal docs" | RAG + Guardrails + Evaluation |
| "A surge of mixed-difficulty requests" | Routing + Resource-Aware Optimization + Prioritization |
| "It gives wrong answers confidently" | Reflection + RAG (grounding) + Evaluation |
| "Automate a multi-step business process" | Prompt Chaining + Tool Use + Exception Handling |
| "It's too slow" | Parallelization + Routing + Resource-Aware Optimization |
| "It's too expensive" | Resource-Aware Optimization + Routing + Evaluation (cost metrics) |
| "It should take real actions (email, payments, records)" | Tool Use + Guardrails + Human-in-the-Loop |
| "It forgets the user / loses context" | Memory Management + Context Engineering |
| "One agent can't handle the whole job" | Multi-Agent + Planning + A2A protocols |
| "It gets manipulated / says harmful things" | Guardrails + Evaluation + Monitoring |
| "Long-running task that drifts off course" | Goal Setting & Monitoring + Planning + Reflection |
| "Users don't trust it with big decisions" | Human-in-the-Loop + Guardrails + Evaluation |
| "Connect it to many external systems" | MCP + Tool Use + Exception Handling |
| "Hard problems it gets wrong on the first try" | Reasoning Techniques + Reflection + Evaluation |
| "Research a topic deeply and report back" | Planning + Parallelization + RAG + Reasoning |
| "Find opportunities/hypotheses we haven't thought of" | Exploration & Discovery + Reasoning + Evaluation |
| "How do we know it works? / It's degrading" | Evaluation & Monitoring + Learning & Adaptation |
| "Many tasks, limited capacity, some urgent" | Prioritization + Goal Monitoring + Exception Handling |

Three habits make the table stick.

First, notice that Guardrails and Evaluation appear constantly. That's not laziness in the table — they genuinely belong in *every* production answer, and saying so unprompted is free senior signal. "And of course this ships with an eval harness and layered guardrails, which I'll detail if you want" costs you one sentence and buys you credibility.

Second, scenarios are rarely one pattern. The interviewer's follow-ups will drag you across three or four, so plan your answer as a composition from the first sentence. The mega-scenarios below are exactly that rehearsal.

Third, don't recite the table — perform the mapping. When the scenario lands, take a visible beat: "okay, so that's routing for the traffic mix, prioritization for the urgency spread, and guardrails because these actions touch money." *Then* start designing.

Naming your pattern selection out loud before diving in is itself a senior move. It shows the interviewer a mental index, and it buys you ten seconds of structure while the rest of the answer assembles.

## Four mega-scenarios, composed

These four composite questions cover most of the interview territory between them.

Each names its pattern stack, then gives a compact spoken answer — tighter than a full single-pattern answer, because in a composition you spend one or two sentences per pattern and save your depth for where the scenario's real tension lives.

### (a) The airline customer-support agent

*Stacks: Routing, Tool Use, Memory, Human-in-the-Loop, Guardrails, Evaluation & Monitoring.*

"Let me confirm scope. The agent handles rebookings, refunds, baggage claims, and general questions, over chat, with access to the reservation system.

"The worst failure is a wrong irreversible action — refunding the wrong ticket, rebooking someone onto a flight they didn't want. Okay. Then the architecture is a routed front door, a tool-using core, and a hard line around consequential actions.

"The front door is a router: a fast, cheap classifier reads each incoming message and sends it down the right lane — general FAQ, flight status, rebooking, refund, or 'distressed customer, get a human now.'

"Routing first matters because the lanes deserve different machinery. A status check is a cheap model plus one API call, answered in a second for a fraction of a cent. A rebooking is a full agent with tools, memory, and approval gates.

"One size fits all means overpaying on easy traffic and underserving hard traffic — routing is where the economics of the whole system get decided.

"Inside the transactional lanes, the agent works a tool-use loop against an allow-list of APIs: look up reservation, search alternative flights, quote fare difference, rebook, refund, file a claim.

"The tools enforce least privilege in their own code — the lookup is bound to the authenticated customer's own bookings, so even a manipulated agent can't read a stranger's itinerary. That's the guardrails pattern's most important layer showing up as a tool-design decision.

"Tool errors are first-class citizens, not crashes. The fare API times out mid-rebooking? That's an observation the agent reasons about — retry with backoff, try the alternate endpoint, or tell the customer honestly that pricing is briefly unavailable.

"Exception handling woven into the loop, not bolted on after the first outage.

"Memory in two tiers. Session memory keeps the conversation coherent — the flight numbers, dates, and preferences already mentioned, so the customer never repeats themselves within a chat.

"Long-term memory stores durable facts across conversations — seat preferences, home airport, the open claim from last week — retrieved at session start.

"'I see you contacted us Tuesday about the delayed bag — is this about that?' is the single cheapest moment of delight in this entire design. It costs one retrieval. It sounds like being known.

"One caution on memory, and I'd raise it myself: remembered data is personal data. Preferences and claim history get retention policies, and what a customer says in distress doesn't become permanent profile material without a reason. Memory design is partly privacy design, and saying so costs one sentence.

"Now the consequential-action line, where I'd spend my emphasis, because it's where this design earns trust.

"Three tiers. Reading data: fully autonomous. Reversible, small actions — sending an itinerary email, filing a claim: autonomous with logging.

"Irreversible or high-value actions — refunds above a threshold, involuntary rebookings, anything touching money at scale: the agent prepares the complete action, shows the customer, and policy decides whether a human agent must also approve.

"I'd frame human-in-the-loop correctly: it's not a fallback for a weak model. It's the correct permanent design for irreversible actions in a trust business. The airline's own human agents have approval limits too — the agent is joining an existing control structure, not inventing one.

"Guardrails, layered, briefly: input screening for prompt injection and abuse — remembering injection can hide in things the agent *reads*, like a forwarded email attached to a claim. Output screening so we never leak another passenger's data or invent a refund policy that doesn't exist. And the tool allow-list as the deterministic backstop under all of it.

"A support agent confidently inventing policy is a viral screenshot and a regulatory letter. I'd say that risk out loud — naming the business consequence is part of the answer.

"Evaluation and monitoring. Offline: an eval set mined from historical transcripts — request, correct resolution, expected tool trajectory — gating every prompt or model change.

"Trajectory checks matter here specifically: a refund reached without the policy check is a compliance problem even when the amount happens to be right.

"Online: resolution rate, escalation rate, latency, cost per conversation, and an LLM-judge sampling live chats for tone and accuracy — this agent is a brand voice as much as a problem solver. Drift alarms on all of it, because fare rules and routes change constantly under the agent.

"And the loop closes weekly: every bad outcome a human catches becomes a new eval case.

```
 customer --> [guardrail in] --> ROUTER
                        |----> FAQ lane (cheap model + RAG)
                        |----> status lane (model + 1 API)
                        '----> transaction lane:
                               agent + tools (allow-list)
                                  |--> reversible: do + log
                                  '--> irreversible: HITL gate
              [guardrail out] --> reply     [memory r/w throughout]
                    [logs --> dashboards --> eval set]
```

"Cost story to close: routing keeps eighty percent of traffic on pennies-per-chat machinery; the expensive full agent runs only where it earns its keep.

"And the eval harness is what lets me confidently swap cheaper models into lanes later. The measurement pays for the optimization."

### (b) The deep-research agent

*Stacks: Planning, Parallelization, Multi-Agent, RAG, Reasoning Techniques, Resource-Aware Optimization.*

"Scope check. The user asks a broad question — 'assess the competitive landscape for solid-state batteries' — grants a time budget of minutes rather than seconds, and expects a structured, cited report.

"That budget is the defining constraint. This is a background workflow trading latency for depth, and the whole design is about spending the budget well.

"First, planning. A planner model decomposes the question into sub-questions — key players, technology approaches, manufacturing barriers, patent landscape, market forecasts.

"A broad question researched as one undifferentiated blob produces shallow mush; decomposition is what makes depth possible.

"The plan is explicit and inspectable, which also gives us a progress spine: at any moment we know which sub-questions are answered, in flight, or starved.

"Then parallelization. The sub-questions are largely independent, so worker agents research them concurrently — five in parallel turns a fifty-minute sequential job into roughly ten minutes.

"Independence is the criterion: where one sub-question feeds another, those two run in sequence, and the planner marks the dependency.

"Structurally this is multi-agent in the supervisor-workers shape. An orchestrator owns the plan and the budget. Workers own one sub-question each. A synthesis agent owns the final report.

"Cleanly separated roles keep each prompt small, each behavior testable, and each failure isolated.

"Each worker runs the ReAct loop from the reasoning pattern — think, search, read, re-think — and iterates: initial searches, analyze the results, notice gaps and contradictions, run refined follow-up searches to fill them.

"That reflective iteration is precisely what separates deep research from a one-pass search summary, and it's the loop the real Deep Research products run.

"Retrieval discipline is RAG doing the grounding work: every claim in a worker's findings carries its source, and un-sourced claims get flagged as speculation rather than laundered into confident prose.

"Hallucinated citations are this product's cardinal sin — one fabricated source discovered by the user poisons trust in the whole report — so grounding is a hard rule, not a hope.

"The synthesis stage gets the reasoning depth. Merging five workers' findings, resolving their contradictions, and structuring a coherent narrative is the hardest cognitive step in the pipeline — so it gets the strongest model with a generous thinking budget, per the scaling-inference logic.

"Spend the compute where the leverage is.

"Contradictions between workers get surfaced in the report as genuine disagreement in the sources — 'analysts differ on manufacturing timelines, here are both positions' — which is information, not failure. Papering over disagreement would be the failure.

"One escalation path worth naming: if two workers return findings that flatly contradict on something load-bearing, the orchestrator can spawn a small verification task targeted at just that conflict, budget permitting. Contradiction-triggered follow-up is the multi-agent version of self-correction, and it's cheap because it's narrow.

"Resource-aware optimization runs through everything, because an unbounded research loop will happily spend forever.

"The orchestrator holds the budget: caps on search rounds per worker; a model-tier policy — cheap models for query generation and skimming, the expensive model only for analysis and synthesis; and diminishing-returns detection — when a worker's follow-up searches stop surfacing new information, it stops early and returns what it has.

"If the total budget nears exhaustion with sub-questions still open, the orchestrator triages by importance — prioritization at small scale — and the final report honestly marks which sections got thin coverage.

"An honest gap beats a confident fabrication every single time, and I'd design the report template to make gaps easy to declare.

"Failure handling: a worker that errors or times out doesn't sink the report. The orchestrator retries once, then synthesis proceeds with the gap declared. Partial delivery with honesty is the contract.

```
 question --> PLANNER --> sub-questions
                 |  (budget & progress owner)
     +-----------+-----------+
     v           v           v
 [worker1]   [worker2]   [worker3]   ... parallel
  search<->reason loops, cited findings (RAG)
     +-----------+-----------+
                 v
           SYNTHESIS (strong model, big thinking budget)
                 v
      cited report + confidence notes + declared gaps
```

"Evaluation — the interesting challenge, since there's no single right answer. Layered proxies, borrowing from the discovery pattern.

"Offline: a benchmark set of research questions with expert-built rubrics — coverage of known-essential facts for each question, citation accuracy checked mechanically (does the cited source actually contain the claim?), and an LLM judge for structure and reasoning quality, calibrated by periodic human grading.

"Online: cost per report, budget-utilization curves, and user signals — do readers ask follow-ups that the report should have covered? That's a quiet but honest quality metric.

"Cost: one to a few dollars per report at this design, against hours of an analyst's time — trivially justified.

"But only because the budget machinery keeps the tail from occasionally running to fifty dollars. The cap is the business model."

### (c) The coding agent that opens pull requests

*Stacks: Planning, Tool Use, Reflection, Exception Handling, Evaluation, Human-in-the-Loop.*

"Scope: the agent takes a ticket — a bug fix or a small feature — works in a real repository, and its output is a pull request: a proposed code change packaged for human review.

"That last clause anchors the whole design. The PR *is* the human-in-the-loop gate, built into the workflow's very shape. The agent never pushes to production; it proposes, humans dispose.

"I'd open with that, because it converts the scariest stakeholder question — 'you let an AI change our code?' — into 'we let it draft, under the same review bar as any engineer.'

"The loop starts with planning. Read the ticket. Explore the codebase — search for the relevant files, read them, trace the failing behavior to its source. Then produce an explicit plan: which files change, what the approach is, which tests will prove the fix.

"For a non-trivial change I'd have the agent post that plan as a comment before writing code. A wrong plan caught at the comment stage costs one human minute; a wrong plan discovered during review costs everyone's afternoon and the agent's credibility.

"Execution is tool use in a sandbox. The agent edits files, runs the build, and executes tests in an isolated environment — no production access, no secrets, no network beyond what the build needs.

"This is the guardrails pattern's sandbox applied to its most natural case: 'agent runs code it just wrote' is exactly the scenario sandboxes exist for.

"Its tool set is an allow-list: read, edit, run tests, run linters, open PR. Notably absent: deploy, force-push, delete branches.

"The absence list is a design artifact worth saying out loud.

"The heart of the design is reflection against ground truth, and I'd stress why coding is the *best-case* domain for the reflection pattern: the agent gets objective feedback nobody has to hand-craft.

"Write code. Run the tests. Read the failures. Revise. Run again.

"That generate-verify-refine loop is reflection with a real oracle instead of self-judgment — the model isn't grading its own homework, the test suite is — and it's the main reason coding agents work as well as they do.

"The loop is capped. After, say, five failed iterations, the agent stops, summarizes what it tried, what failed, and what it believes is wrong, and asks for help.

"A stuck agent that reports its stuckness crisply is genuinely valuable — that summary is a head start for the human. One that thrashes silently through fifty test runs is a cost bug wearing a cape.

"Exception handling runs throughout, because real repositories misbehave in ways that have nothing to do with the agent's change.

"Flaky tests that fail intermittently: detected by running the suite *before* any edits to establish a baseline — pre-existing failures don't get blamed on the agent, and known-flaky tests get retried before being believed.

"A broken build environment: reported as an environment problem, not hallucinated into a code problem.

"Merge conflicts against a moving main branch: rebase, rerun, then proceed.

"Each failure type is classified and handled, not swallowed. An agent that mistakes environmental noise for its own bugs will 'fix' things that were never broken, and that's how trust dies.

"The PR itself is engineered as a communication artifact. The description states the ticket, the approach, what was tested, and — this is the part I'd insist on — what the agent is *unsure* about: 'I changed the retry logic in the payment path; I'd particularly appreciate review of the timeout handling.'

"Declared uncertainty is what makes reviewing agent code tractable instead of adversarial. It points scarce human attention at the risky ten lines instead of spreading it thin across three hundred.

"Guardrails get one more sentence because they're mostly inherited: the sandbox, the tool allow-list, and branch protection — the repository setting that says nothing merges without review and passing checks — which conveniently is a guardrail the organization already trusts, enforced by the platform, not the model.

```
 ticket --> [plan: explore repo, propose approach]
               |
               v        (sandbox, allow-listed tools)
        [edit code] --> [run tests] --fail--> [reflect, revise]
               ^                                  |
               +------- loop, capped at N --------+
               |
           tests pass
               v
        [self-review + lint] --> OPEN PULL REQUEST --> human review
                                        |
                            [merge outcomes --> eval set]
```

"Evaluation. Offline: a benchmark of historical tickets with known fixes — did the agent's patch pass the real test suite, and how does its diff compare with what the humans actually shipped? That's a trajectory-and-outcome eval built from data the org already has.

"Online is the beautiful part: this workflow generates its own labels.

"PR acceptance rate, review-round counts, human-edit distance before merge, post-merge defect rates — all logged by the normal engineering process, no extra instrumentation needed. Rejected PRs and reviewer comments feed straight back into the eval set and the prompts.

"Few agent domains hand you a feedback loop this clean, and I'd say so.

"Cost: a PR might cost fifty cents to a few dollars of compute across the iteration loop, against engineer-hours per ticket — the economics are absurd in the agent's favor, *provided* the acceptance rate is high enough that review time doesn't eat the savings.

"Which is exactly why acceptance rate is the north-star metric, and why the reflection loop and self-review exist: every failure caught before the PR opens is human attention saved after it opens."

### (d) The ops / incident-response agent

*Stacks: Goal Setting & Monitoring, Prioritization, Exception Handling, A2A/MCP, Guardrails.*

"Scope: the agent sits in the on-call loop for a production platform — ingesting alerts, triaging, diagnosing, executing safe remediations, and escalating everything else to humans.

"Stakes are maximal — this agent touches production — so I'll design conservative and say so up front: its default posture is 'diagnose and recommend,' and autonomous action is reserved for an explicitly pre-approved playbook.

"Trust is granted action by action, with evidence.

"Start with goal setting and monitoring, because an incident agent needs an explicit representation of desired state. Service-level objectives — error rates below X, latency below Y — are encoded as goals the agent continuously monitors.

"An incident *is* a monitored goal in violation.

"That framing gives the agent its purpose structure: detect the deviation, work to restore the goal state, verify restoration, stand down.

"It also prevents the classic drift failure — an agent chasing an interesting symptom down a rabbit hole while the user-facing objective stays violated. Progress is measured against the SLO, not against activity.

"Prioritization carries the most load here, because incidents arrive in bursts and are never equal.

"Every alert gets scored. Rules handle the unambiguous cases — production-down sources map straight to P0, instantly, no model in the path. An LLM assessor handles the ambiguous ones, reading the alert text and recent context to judge blast radius: how many users, which systems, is it spreading?

"A priority queue orders the work. Preemption is live: when a P0 lands mid-P2-investigation, the agent checkpoints the P2 at a safe boundary and swings immediately.

"Aging protects the low-priority tail — those quiet warnings that presage next week's outage get slowly rising priority instead of eternal deferral, because today's ignored disk-space warning is Friday's P0.

"And correlated alerts get clustered: fifty alerts from one root cause is one incident, not fifty. Recognizing that *is* triage — it's the difference between responding and drowning.

"During a genuine storm — multiple simultaneous incidents — the same machinery arbitrates between them: blast radius first, preemption across incidents, and an explicit note in the channel when a lower-band incident is being consciously parked.

"Consciously parked, with a note, is triage. Silently starved is a second incident.

"Diagnosis is a ReAct loop over the observability stack, and here's where the integration patterns earn their slot in this stack.

"The agent reaches metrics, logs, deployment history, and runbooks through MCP — the standard protocol that lets one agent talk to many tools without bespoke glue code per system.

"And it coordinates with the org's other automation through A2A-style agent-to-agent protocols: it can task the deployment system's agent with 'roll back service X to the previous version' as a structured request with a verifiable response, rather than screen-scraping a dashboard and hoping.

"In a big organization, incident response is inherently multi-system. The protocol layer is what keeps the design maintainable as the tool count grows from five to fifty.

"Action policy: three rings, enforced by guardrails — meaning deterministic code — not by politeness.

"Ring one, always autonomous: read-only diagnosis. Query anything, change nothing.

"Ring two, autonomous within a pre-approved playbook: restart the flapping service, roll back the deployment that correlates with the error spike, scale up the saturated pool. Each entry is an action humans have explicitly blessed, with bounded blast radius, implemented as an allow-listed tool with argument validation.

"Ring three, human-approved: everything else. The agent proposes, with its evidence and its confidence, and a human clicks.

"The ring boundaries are code. A confused or manipulated agent cannot talk its way from ring one to ring three.

"And 'manipulated' is not hypothetical here, which is the non-obvious threat I'd name for the interviewer: this agent *reads* attacker-influenceable content. Log lines can contain injection payloads aimed at automated systems.

"Logs are untrusted input, screened and demarcated like any other — because prompt injection through a log message into an agent with production access is a genuinely bad day.

"Exception handling is recursive, because this agent's whole job is other systems' failures — and its own tools fail during exactly the chaos it's responding to.

"The metrics store times out mid-incident: degrade to alternative signals and say so in the incident channel, explicitly.

"An action fails halfway: verify actual state before retrying — never assume, because blindly retrying a half-applied change is how incidents get worse instead of better.

"And the agent itself gets a watchdog: if it errors or goes silent during a P0, paging falls through to humans on a timer, unconditionally.

"The agent must never become a single point of failure in the escalation path. I'd engrave that sentence on the design doc.

```
 alerts --> [screen] --> [score & cluster] --> PRIORITY QUEUE
                                          (preempt / age)
                v
        [ReAct diagnosis]
      MCP: metrics, logs, deploys, runbooks
      A2A: task other org agents
                v
     ring 1: read-only  (always)
     ring 2: playbook   (autonomous, allow-listed, validated)
     ring 3: propose    (human approves)
                v
     verify SLO restored --> stand down --> postmortem log
        [watchdog: agent silent on P0 => page humans]
```

"Evaluation. Offline: replay — historical incidents re-run through the agent, comparing its triage, diagnosis, and proposed actions against what the human responders actually determined.

"That's a rich eval set nobody has to invent; the postmortem archive already contains it.

"Online: time-to-triage and time-to-mitigate per priority band, against the human baseline. Diagnostic-accuracy audits in postmortems. False-page rate — an agent that cries wolf gets muted by the on-call rotation, and a muted safety system is worse than none, so alert precision is a first-class metric. And ring-2 action success rate, tracked per playbook entry.

"The loop closes through the postmortem process the team already runs: new failure signatures become eval cases, and validated remediations graduate into the ring-2 playbook — one at a time, each with its own metrics, each earning its autonomy with a track record.

"Cost is barely worth mentioning against what it protects — model spend of cents per incident versus downtime measured in thousands of dollars a minute.

"The real cost risk is trust: one bad autonomous action sets adoption back a year. Which is exactly why the rings, the playbook graduation process, and the conservative default posture aren't caution bolted onto the design.

"They *are* the design."

## How to practice with this playbook

A short coaching note to close, because knowing these patterns and performing them under interview pressure are different skills — and only one of them got trained by reading this far.

Rehearse out loud. Not in your head — out loud, alone in a room, phone timer running.

The "complete interview answer" sections in this playbook are written as transcripts on purpose: they're scripts to perform until the *shape* is muscle memory, not the words.

You'll discover something humbling the first time you try: sentences you can read fluently, you cannot yet say fluently. Your mouth doesn't know them yet.

That gap closes only by speaking, and it closes fast — two or three spoken passes per pattern, and the structure starts arriving on its own.

Record yourself once per pattern if you can bear it. The recording catches the two things you can't hear while performing: filler storms — the "um, so, basically" clusters that spike when you don't know your next beat — and pace collapse, where you sprint through the parts you know and stall on the parts you don't.

Both are fixable in one more pass, once you've heard them.

Whiteboard the diagrams from memory. Every pattern here has a small ASCII sketch, and each takes about twenty seconds to draw.

Practice producing them on paper *while talking*, because drawing-while-explaining is its own coordination skill, and it's the one that makes you look like you've done this before.

A candidate who walks to the whiteboard unprompted and lays down five boxes while narrating reads as someone who has designed real systems. The diagrams are deliberately minimal — five to ten boxes — because that's what fits in an interview minute.

Resist the urge to add boxes. The small version is the rehearsed version.

Drill the pattern picker as a flash exercise: have a friend read scenario phrasings from the table above in random order, and give yourself ten seconds to name the pattern stack for each.

That ten-second reflex is the difference between opening your answer with structure and opening it with a stall.

Run every answer through the universal skeleton from Part 1.

Clarify the requirements with two or three questions, and assume answers out loud. Name the pattern and its plain-words idea. Narrate the design along the path the data travels. State the tradeoffs honestly. Describe the failure modes and what the design does about them. Say how you'd evaluate it offline and monitor it online. Put rough dollars on it.

That spine holds for every pattern in this book and every scenario an interviewer can invent.

When you get the question this playbook never covered — and you will — the skeleton is what you fall back on, and it will carry you through territory you've never rehearsed.

And the meta-rule, the one thing to keep if you keep only one: name failure modes unprompted.

Anyone prepared can describe a system that works. Senior engineers describe how it *breaks* — the retrieval that returns nothing, the loop that never terminates, the queue that starves its tail, the judge that drifts, the guardrail that fails open — and what the design does about each one, *before being asked*.

Interviewers are listening for exactly that, because it's the trait that predicts what you'll do when the pager goes off at 2 a.m.

Every pattern in this playbook handed you its failure modes on a plate. Serve them first.

Go get the job.
