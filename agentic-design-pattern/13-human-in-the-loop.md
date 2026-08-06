# Pattern 13: Human-in-the-Loop — Knowing When the Machine Should Raise Its Hand

## The interview scenario

You'll hear this pattern hiding inside prompts like these:

- "Design an agent that drafts contract clauses for our legal team — but the lawyers
  must stay in control of anything that gets sent to a client."
- "We want an agent that can issue refunds and account credits automatically. How do you
  make sure it never gives away money it shouldn't?"
- "Build a content moderation system that handles millions of posts a day, but where
  humans still make the judgment calls on the hard cases."

The common thread: the agent is capable, the action is consequential, and somebody with
a job title is accountable for the outcome. The moment you hear words like "lawyers must
approve," "irreversible," "compliance," or "we can't afford a mistake," you should be
thinking Human-in-the-Loop.

## What this pattern is, in plain words

Human-in-the-Loop — everyone shortens it to HITL — is the design decision that an AI
agent should not act completely alone. Somewhere in its workflow, a real person gets to
look at what the agent wants to do, and either wave it through, change it, or stop it.

The best mental model is a junior employee with a smart manager. You don't watch a good
junior employee type every keystroke — that would defeat the purpose of hiring them. But
you also don't let them wire $2 million out of the company account on their first week.
You give them standing permission for routine work, and you ask them to come to your
desk before doing anything risky, expensive, or hard to undo. HITL is exactly that
arrangement, formalized in software.

There are a few flavors, and interviewers love it when you name them. In the *reviewer*
flavor, the agent does the work and a human checks the output before it ships — think a
human editor reviewing AI-drafted marketing copy. In the *approval gate* flavor, the
agent pauses before a specific risky action — sending an email, executing a trade,
deleting data — and waits for a thumbs-up. In the *escalation* flavor, the agent handles
the easy cases end-to-end and only hands off the hard or ambiguous ones, the way a
chatbot transfers an angry customer to a human support rep. And in the *collaboration*
flavor, human and agent work side by side: the agent crunches data and drafts options,
the human makes the final call — sometimes called decision augmentation, because the AI
is informing a human decision rather than making it.

There's also a cousin worth one sentence in an interview: *human-on-the-loop*, where the
human doesn't approve individual actions but instead sets the policy — "never invest
more than 5% in one stock, auto-sell anything down 10%" — and the agent executes at
machine speed within those guardrails. Humans write the rules slowly and carefully; the
machine applies them fast.

One more idea underneath all of this: the human input isn't just a safety brake, it's a
learning signal. Every time a person corrects the agent, you've generated a labeled
example of what "right" looks like. Fed back into the system — through fine-tuning,
better prompts, or preference training — those corrections make the agent need less
supervision over time. That's the same idea behind reinforcement learning from human
feedback, where human preferences literally shape how the model behaves.

## How the design actually works

Let me walk through the machinery you'd actually build, because "a human checks it"
hides a surprising amount of engineering.

**Risk tiers first.** You can't put a human in front of everything — people are slow and
expensive, and if you ask them to approve ten thousand trivial actions a day they'll
stop reading and just click "approve" on everything, which is worse than no review at
all (reviewers call this rubber-stamping, and it's the death of any HITL system). So the
first design move is classifying actions by risk. Reading data: low risk, fully
automatic. Drafting a document that a human will send: low-to-medium. Sending money,
signing contracts, deleting records, emailing customers: high risk, gated. The general
rule I'd state in an interview: *gate the actions that are irreversible or expensive,
automate the ones that are cheap to undo.*

**Confidence-based escalation second.** Risk isn't the only trigger — uncertainty is the
other one. The agent should estimate how sure it is (via a confidence score from a
classifier, a self-assessment, or simply detecting that a case matches known-ambiguous
patterns) and interrupt a human only when it's unsure or the stakes are high. That
single sentence — "the agent only interrupts a human when it's unsure or the stakes are
high" — is the heart of the pattern, and it's worth saying verbatim in an interview.
Everything else is plumbing around it.

**The interrupt/resume mechanic.** Here's the part interviewers probe because it's
genuinely tricky: what does it mean, mechanically, for an agent to "pause and ask"? The
agent is mid-run — it has context, partial work, a plan. You can't just kill the process
and start over when the human answers three hours later. So the framework has to
*checkpoint* the run: serialize the agent's state (its conversation history, working
memory, and the pending action) to durable storage, emit a review request into a queue,
and go dormant. When the human decides — approve, edit, or reject — the run is
rehydrated from the checkpoint and continues as if the pause never happened, with the
human's decision injected as a new input. Modern agent frameworks (LangGraph's
interrupts, ADK's escalation tools) build this in, but you should be able to describe it
framework-free: pause, persist, notify, decide, resume.

**The review queue.** Human decisions need a workplace. That's a review queue: a
dashboard where pending items line up, each showing the agent's proposed action, its
reasoning, the relevant context, and buttons for approve / edit / reject / escalate
further. Good queues are triaged (highest risk and oldest items first), have SLAs —
service-level agreements, promises like "every item reviewed within 4 hours" — and route
items to the *right* human, because a paralegal shouldn't be approving what needs a
partner's signature. The book's caveat matters here: HITL is only as good as the humans
in it. A skilled reviewer catches the subtle error in generated code; an untrained one
adds latency and false confidence.

**The audit trail.** Every gated action, every approval, every edit, every rejection
gets logged: who decided, when, what they saw, what changed. This is non-negotiable in
regulated domains — when the auditor asks "why did the system send this clause to the
client?", the answer must be "the agent proposed it at 2:14pm, attorney Chen edited
paragraph two and approved at 3:02pm," not a shrug. The audit trail is also your
training-data goldmine: it's a perfectly labeled record of agent proposals and expert
corrections.

**The tension you must name: safety versus throughput.** Every human gate you add makes
the system safer and slower. Humans don't scale — that's the pattern's fundamental
caveat. One reviewer can handle maybe a few hundred decisions a day; your agent can
propose a million. So the design is always a hybrid: automation for volume, humans for
judgment, and a dial you can turn. As the agent proves itself — measured by how often
humans approve without edits — you raise the autonomy threshold and gate less. If
quality slips, you turn the dial back. Frame HITL as a *dial, not a switch*, and you'll
sound like someone who has run one of these in production.

One honest caveat to volunteer: privacy. Putting a human in the loop means showing that
human real user data, which may need anonymizing or masking first — another pipeline
stage, more complexity. Mentioning that unprompted signals real-world experience.

## The complete interview answer, spoken

Here's how I'd handle "Design an agent that drafts contract clauses — lawyers must stay
in control," out loud, start to finish.

"Before I design anything, let me pin down three things. First, what's the volume — are
we drafting ten clauses a day or ten thousand? That decides how much human review we can
afford. Second, what's the blast radius of a mistake — is a bad clause caught
internally, or could it reach a client and bind the company? Third, who are the humans —
a handful of senior attorneys, or a larger team with paralegals who can do first-pass
review?"

*(Interviewer: say a mid-size firm, a few hundred clauses a day, and yes, a bad clause
reaching a client is the nightmare scenario.)*

"Great — a few hundred a day is squarely in 'humans can review everything that matters'
territory, and the nightmare scenario is irreversible harm, so I'm going to design this
as a Human-in-the-Loop system where the agent is a fast, tireless first-drafter and the
lawyers are the deciders. The agent never sends anything to a client. Ever. That's my
first invariant, and I'd state it in the design doc in bold.

Let me sketch the flow on the whiteboard:

```
  Request ("draft an indemnification clause for the Acme deal")
      |
      v
  +-----------+     retrieves firm templates,
  |   Agent   |---- precedent clauses, deal context
  +-----------+
      |
      v  drafts clause + self-assessed confidence + cited precedents
  +---------------------+
  |    Risk & confidence |----- low risk + high confidence ---> lawyer's
  |      classifier      |                                      inbox (async)
  +---------------------+
      |
      | high risk OR low confidence
      v
  +----------------+   approve / edit / reject
  |  Review queue  | <------------------------- attorney
  |  (checkpointed |
  |   agent runs)  |------ decision ------> agent RESUMES from checkpoint
  +----------------+                              |
      |                                           v
      +---- every event ----> [ Audit log ]   final clause -> document system
```

Walking through it: a lawyer asks for a clause. The agent retrieves relevant firm
templates and precedent language, drafts the clause, and — this is important — attaches
its receipts: which precedents it drew from, and a self-assessment of how confident it
is. Novel deal structure it's never seen? Low confidence. Boilerplate indemnification
it's drafted five hundred times? High confidence.

Then a classification step sorts the draft into two lanes. Routine, high-confidence
drafts go straight into the requesting lawyer's inbox as a normal work product — the
lawyer was always going to read it before using it, so that human review comes for free.
But anything risky — unusual liability terms, deviations from firm-approved templates,
low agent confidence, or high-value deals — gets gated: the agent's run is checkpointed,
meaning we save its full state to storage, and a review item appears in a queue for a
senior attorney.

Let me be concrete about that pause, because it's the mechanical heart of HITL. The
agent isn't killed; it's suspended mid-run. Its conversation state, retrieved documents,
and the pending draft are persisted. The attorney might respond in five minutes or
tomorrow morning. When they do — approve as-is, edit the language, or reject with a note
— we rehydrate the run from the checkpoint, feed the decision in as new input, and the
agent continues: incorporating edits, regenerating if rejected, and finalizing if
approved. Interrupt, decide, resume. The human is a step *inside* the workflow, not a
wall at the end of it.

Now the review queue itself, because that's where this succeeds or dies. Each item shows
the draft, a diff against the nearest firm-approved template — lawyers review diffs far
faster than raw text — the agent's reasoning and cited precedents, and one-click
actions. The queue is triaged by deal value and deadline. And I'd set an explicit SLA,
say four business hours, because an unbounded review queue quietly becomes the
bottleneck for the whole firm.

The failure mode I'm most worried about isn't the agent — it's the humans. If I gate too
much, attorneys see two hundred items a day, stop reading, and rubber-stamp. That's the
worst of both worlds: all the latency of review with none of the safety. So I'd watch
two metrics from day one: median review time per item — if it drops toward two seconds,
people aren't reading — and edit rate, the fraction of gated items that reviewers
actually change. If the edit rate on a category falls below a few percent for weeks,
that category has earned auto-approval and I move it to the fast lane. This is the
safety-versus-throughput dial: I start conservative, gating maybe 40% of drafts, and let
the data earn the agent more autonomy over time.

Other failure handling: if the classifier itself errs — calls a risky clause routine —
the requesting lawyer is still a human backstop, since no clause reaches a client
without an attorney attaching it. Defense in depth: two human touchpoints for the scary
path, one for the routine path, zero fully-autonomous paths to the outside world. If the
agent goes down entirely, lawyers just draft manually — the system degrades to the
status quo, which is the gentlest failure mode you can ask for. And if a reviewer is out
sick, items past SLA re-route to a backup reviewer automatically.

Everything writes to an immutable audit log: prompt, retrieved sources, draft,
classifier verdict, reviewer identity, edits, timestamps. Two reasons. Compliance — when
a client dispute happens, we can reconstruct exactly who approved what. And improvement
— every attorney edit is a free, expert-labeled training example. Monthly, we mine the
edits: if attorneys keep fixing the same limitation-of-liability phrasing, that goes
into the templates or the agent's instructions, and next month's edit rate drops. The
humans aren't just a safety net; they're the teachers.

Evaluation: I'd track approval-without-edit rate as the headline quality number,
escalation precision — of the items we gated, how many actually needed human judgment —
and escalation recall, which we estimate by sampling the fast lane and having attorneys
audit whether anything risky slipped through. Plus time-to-final-clause versus the old
manual baseline, because the business case is speed.

On cost: a few hundred drafts a day is maybe $150 a day in model calls at strong-model
prices — a rounding error against attorney time. The real cost is reviewer hours, which
is exactly why the autonomy dial matters: every point of edit-rate improvement converts
directly into recovered attorney time, and 'senior attorney hours saved per month' is
the number I'd put on the executive dashboard.

So to summarize the design in three sentences: the agent drafts everything and sends
nothing — humans own the send button. Risk and confidence decide which drafts get an
extra senior review, with interrupt-and-resume mechanics so review is a pause in the
workflow, not a dead end. And the audit trail plus edit-mining turns every human
correction into training signal, so the system needs less supervision every quarter."

## Follow-ups they will ask

**"Won't the reviewers just rubber-stamp everything?"** Yes, if you let them — that's
alert fatigue, the biggest practical failure of HITL. Answer with countermeasures: gate
less (only genuinely risky items), triage well, show diffs instead of walls of text,
monitor median review time and edit rates to detect rubber-stamping, and occasionally
inject known-bad items as a canary — if reviewers approve a planted error, your review
layer has decayed and you need to reduce volume or rotate reviewers.

**"How does the system scale if humans are the bottleneck?"** State the trade honestly:
humans don't scale, so the design must shrink the fraction needing review over time.
Tiered review (cheap first-pass reviewers, experts for the top tier), confidence
thresholds that tighten as the agent proves out, and human-on-the-loop policies
replacing per-item approval for categories with sustained near-zero edit rates.

**"Where does the confidence score come from? Can you trust an LLM saying it's
confident?"** Be skeptical — self-reported confidence from a language model is poorly
calibrated. Prefer converging signals: a separate trained classifier on features like
deviation-from-template, novelty of the request, self-consistency (sample the answer
several times; disagreement means uncertainty), and hard business rules (deal value over
a threshold always gates regardless of any score).

**"What exactly happens to the agent's state while it waits a day for approval?"**
They're testing interrupt/resume. Answer: the run is checkpointed — state serialized to
durable storage, a review request emitted, compute released. On decision, the run is
rehydrated and the decision enters as new input. Bonus points for edge cases: expiring
stale checkpoints if the world changed underneath (the deal terms were renegotiated),
and idempotency so a double-clicked "approve" doesn't execute twice.

**"How is human feedback used to improve the model?"** Edits and rejections are expert-
labeled data. Short term, they drive prompt and template fixes; medium term, fine-tuning
on before/after pairs; long term, preference-style training where the human choice
teaches the model which outputs experts prefer. Note the caveat: correctors may need
training themselves to give corrections that make clean training data.

**"When would you *not* use HITL?"** When actions are cheap and reversible (drafting
internal notes), when volume makes review impossible and per-item risk is tiny (ranking
millions of feed items — use sampling and monitoring instead), or when latency is so
tight no human could respond (real-time bidding). Knowing when a pattern doesn't apply
is half the interview.

## Say it in one breath

"Human-in-the-Loop means the agent does the heavy lifting but a person keeps the
judgment: risky or irreversible actions hit an approval gate, the agent checkpoints mid-
run and resumes after the human decides, ambiguous cases escalate on low confidence —
the agent only interrupts a person when it's unsure or the stakes are high — everything
lands in an audited review queue, and every human correction becomes training data, so
the safety-versus-throughput dial keeps shifting toward autonomy as the agent earns it."
