# Pattern 9: Learning and Adaptation — The Agent That Gets Better While You Sleep

## The interview scenario

You'll hear this pattern show up in phrasings like these:

- "Our support agent answers thousands of tickets a week, and it keeps making the same
  mistakes. Human agents fix its drafts every day, but the bot never gets any better.
  Design a system where it actually learns from those corrections."
- "We added thumbs-up and thumbs-down buttons to our assistant's answers. Right now that
  data goes into a dashboard nobody looks at. How would you use it to improve the agent
  over time?"
- "Design a coding agent that improves at our internal codebase month over month, without
  an ML team retraining a model every week."

All three are the same question underneath: you have an agent that behaves the same way on
day 300 as it did on day 1, you have a stream of evidence about what it's doing right and
wrong, and the interviewer wants you to close the loop between the two.

## What this pattern is, in plain words

Most agents you'll build are frozen at deployment. The model was trained months ago, the
prompt was written once, and every lesson the system could have learned from real usage
just evaporates. It's like hiring an employee who does the job exactly the way they did on
their first morning, forever, no matter how many times you correct them. Politely nodding
at feedback, retaining nothing.

The Learning and Adaptation pattern is the fix: you deliberately build a feedback loop.
The agent's outputs generate signals — a user clicks thumbs-down, a human editor rewrites
a draft, a ticket gets reopened, a generated script crashes — and those signals flow back
into the system and change how it behaves next time. Learning is the internal update;
adaptation is the visible result, the behavior actually changing.

My favorite everyday analogy is a new barista. Week one, they ask every customer how they
take their coffee. Week four, they see a regular walk in and start pulling the shot before
she reaches the counter. Nobody sent the barista back to barista school. They just
accumulated experience and let it change their behavior. That's the whole pattern:
experience in, behavior change out — and the engineering question is what machinery sits
in between.

The crucial thing to internalize for interviews is that "learning" does not automatically
mean "retraining a neural network." That's one option, and usually the most expensive one.
Most production learning happens at much cheaper layers: editing the instructions the
agent runs with, or changing which examples it sees. We'll walk through all the layers.

## How the design actually works

Think of the design as three stages: collect signals, store and curate them, then apply
them through one of several "update dials" of increasing cost and power.

**Stage one: collect feedback signals.** There are three broad kinds. Explicit feedback is
when a human directly tells you something — thumbs up or down, a star rating, a written
complaint. It's the clearest signal but the rarest, and it skews negative because happy
users don't click anything. Corrections are richer: a human agent edits the bot's draft
before sending it, and now you have a before-and-after pair that shows exactly what better
looks like. Outcome signals are implicit but plentiful: did the ticket stay closed or get
reopened, did the user rephrase the same question (a sign the first answer failed), did
the generated code pass its tests, did the customer convert. Outcomes are the most honest
signal because nobody has to volunteer them, but they're noisy — a ticket can be reopened
for reasons that had nothing to do with the bot.

**Stage two: store and curate.** Raw feedback goes into a store, joined with the full
context of the interaction: the input, the agent's reasoning steps, the tools it called,
the final output, and the signal. Then a curation step — part automated, part human —
filters it. This step is not optional, and here's why: feedback is dirty. Users click
thumbs-down because the true answer displeased them. Trolls click things at random. An
outcome metric can reward the wrong behavior. If you feed unfiltered signals into any
update mechanism, you don't get a smarter agent, you get an agent optimized for garbage.
There's a classic version of this failure in model alignment work: when you train a model
to please a learned "judge," the model can discover loopholes and learn to score highly
with genuinely bad answers — the judge gets gamed rather than satisfied. Any learning loop
you design needs a defense against its own feedback.

**Stage three: apply the learning.** Here's the ladder of update dials, cheapest first.

*Dial one: update the instructions.* When curated feedback reveals a recurring mistake —
"the bot keeps promising refunds we don't offer" — you patch the agent's system prompt,
the standing instructions it reads on every request. This can be a human editing text
weekly, or a semi-automated loop where a model drafts prompt amendments from clustered
failure reports and a human approves them. Cheap, fast, instantly reversible.

*Dial two: change the examples — in-context learning.* This term will come up in
interviews, so let's define it plainly: in-context learning means teaching by showing
examples in the prompt rather than retraining the model. Modern LLMs are startling mimics;
put two or three examples of a great ticket resolution in the prompt and the model
imitates the shape and standard of those examples, with zero training. So one of the
highest-leverage learning systems you can build is embarrassingly simple: maintain a
library of your best resolved cases — harvested from those human corrections — and at
request time retrieve the few most similar ones and drop them into the prompt. The related
idea of maintaining a searchable knowledge base of past problems and proven solutions,
which the agent consults before acting, is the same move at the knowledge level: the agent
reuses strategies that worked and steers around documented pitfalls. Your agent now
"learns" continuously just because its example library keeps improving, and you can
inspect or delete any single lesson.

*Dial three: fine-tuning.* This is offline retraining — you take your accumulated
high-quality examples, run an actual training job that adjusts the model's weights, and
deploy the new model. It bakes the lessons in: no prompt space consumed, behavior more
deeply changed, patterns absorbed that are too diffuse to state as instructions. The
costs: it's slow (a pipeline, not an edit), it needs thousands of good examples rather
than dozens, it's hard to undo, and a bad batch of training data quietly damages the
model. Rule of thumb worth saying aloud in the interview: exhaust dials one and two first;
reach for fine-tuning when the cheap dials plateau and you have volume.

*Dial four: preference and reinforcement learning.* Deepest and most specialized.
Reinforcement learning means the agent learns from rewards and penalties over trial and
error rather than from labeled examples. Two named methods are worth thirty seconds each.
PPO — Proximal Policy Optimization — is the classic RL algorithm for this; its signature
idea is a safety brake: every update to the agent's decision-making strategy is clipped to
stay near the current strategy, because one huge greedy step can collapse everything the
agent has learned. DPO — Direct Preference Optimization — is the newer shortcut for tuning
language models on human preferences: instead of the two-step dance of training a separate
reward model to predict human scores and then optimizing against it (which invites the
gaming problem above), DPO takes pairs of "humans preferred answer A over answer B" and
directly nudges the model toward A-like answers and away from B-like ones. Simpler, more
stable, no middleman judge to hack.

There's also a frontier worth name-dropping: agents that improve their own scaffolding.
The Self-Improving Coding Agent, SICA, literally edits its own source code — each
iteration it consults an archive of its past versions and their benchmark scores, picks
the best performer, has that version propose and implement a code change to itself, and
benchmarks the result back into the archive. Over iterations it invented progressively
better editing and code-navigation tools for itself. Two safety features of that design
are the transferable lesson: everything ran inside an isolated container so a
self-modifying agent couldn't damage its host, and a separate overseer — an independent
model watching the working agent's logs — could detect loops or stagnation and halt it. In
the same family, systems like Google's AlphaEvolve pair LLMs that propose candidate
algorithms with automated evaluators that score them, evolving solutions over generations
— it has improved real datacenter scheduling and found new matrix-multiplication
algorithms. You won't be asked to build these, but knowing they exist signals depth.

**When to use this pattern:** when the environment shifts, when personalization matters,
when you have real usage volume generating signals, and when the same failure keeps
recurring. **When NOT to:** low-volume systems (not enough signal to learn from noise),
high-stakes regulated domains where behavior must be frozen and auditable, and any
situation where a human editing the prompt once a quarter is honestly sufficient. An
unneeded learning loop is pure operational burden plus a new attack surface.

**How it differs from neighbors:** memory (an earlier pattern) is about one agent
recalling its own past within and across conversations — storage. Learning is about the
population-level behavior of the system changing based on aggregate experience — policy
change. Reflection is an agent critiquing its own draft within a single task; learning is
the cross-task version, where lessons persist. And goal monitoring (Pattern 11) tells you
whether this run is succeeding; learning consumes many runs' worth of that verdict data to
make future runs better.

## The complete interview answer, spoken

Here's how I'd actually talk through the support-agent version of this question, start to
finish.

"Before I design anything, let me pin down four things. First, what feedback do we have
access to? — I'll assume three streams: thumbs ratings from end users, edited drafts from
the human agents who review bot answers before they go out, and ticket outcomes like
reopen-within-seven-days. Second, what's the volume? — say 50,000 tickets a month, a few
thousand human edits. That's plenty of signal. Third, am I allowed to fine-tune models, or
is this a prompt-and-retrieval-only shop? — I'll assume fine-tuning is possible but
there's no standing ML team, so it should be occasional, not weekly. Fourth, what's the
blast radius of a bad update? — customer-facing text, moderately embarrassing but not
safety-critical. That risk level shapes how much human review I put in the loop.

Given that, my design has four components: a capture layer, a curation pipeline, a tiered
update mechanism, and — the part people forget — an evaluation gate that stands between
learning and deployment.

The capture layer is mostly logging discipline. Every interaction gets recorded as a
complete trajectory: the ticket, the retrieved context, the agent's tool calls, its draft,
the human's final version if edited, and every signal that arrives later — the thumbs
click, the reopen event. The later signals matter: a reopen lands days after the
conversation, so I need a stable ID joining outcomes back to trajectories. Without full
trajectories, feedback is uninterpretable; a thumbs-down on an answer tells me nothing
unless I can see what the agent saw.

The curation pipeline runs daily and does two jobs. Job one: mine the gold. Every case
where a human meaningfully edited the bot's draft and the ticket then stayed closed is a
demonstration pair — here's what the bot did, here's what better looked like. Those go
into a candidate pool. Job two: cluster the failures. I embed the negative-signal cases —
that means converting each one to a vector so similar cases land near each other — group
them, and surface the top recurring failure themes to a human reviewer each week: 'bot
keeps misreading the refund policy for annual plans,' that kind of thing. I want a human
in this loop at this company's risk level, because this is exactly where bad feedback
would otherwise sneak into the system. A competitor spamming thumbs-downs, or users who
rate correct-but-unwelcome answers negatively, should get filtered here, not learned from.

Now the update tiers, cheapest first. Tier one is instruction patches: those weekly
failure themes turn into edits to the system prompt — the agent's standing instructions.
I'd even have a model draft the amendment from the cluster and let the reviewer approve or
reject it, so the human cost is minutes. Tier two, and this is the workhorse: a living
example library. The curated gold pairs go into a retrieval index, and at answer time the
agent pulls the three most similar past resolutions into its prompt. This is in-context
learning — teaching by showing examples in the prompt instead of retraining — and it means
the agent improves every single week purely because its library improves. It's also
transparent: if the agent gives a weird answer, I can see exactly which retrieved examples
influenced it, and delete a bad lesson in one keystroke. You can't delete one lesson from
a fine-tuned model. Tier three is the quarterly fine-tune: once the library holds a few
thousand vetted pairs and prompt-level gains have flattened, we run an offline training
job on them. That bakes in diffuse things — tone, house style, policy instincts — and
shrinks the prompt since we lean less on retrieved examples. If we later wanted to use raw
preference pairs, 'humans preferred this draft over that one,' the modern method is DPO,
which tunes the model directly on those comparisons without training a separate reward
model that could be gamed. But I'd position that as a later maturity stage.

The evaluation gate is what makes all of this safe. I maintain a frozen benchmark: a few
hundred historical tickets with known-good resolutions, plus a regression set of past
failures we've fixed. Every change — a prompt patch, a batch of new library examples,
certainly a fine-tuned model — runs against this benchmark before deployment, scored by a
judge model with periodic human audits of the judge itself. Then new versions ship behind
a canary: 5 percent of traffic, watching live thumbs rates and reopen rates against the
incumbent, with one-click rollback. The failure mode I'm defending against is silent
regression — a learning system that degrades is worse than a static one, because everyone
assumes it's improving.

The whiteboard version:

```
 Tickets --> [Agent] --> drafts --> [Human review] --> customer
                |                        |
                | trajectories           | edits (gold pairs)
                v                        v
          [Trajectory store] <---- thumbs, reopen signals
                |
                v
        [Curation: filter junk,
         mine pairs, cluster fails]
           |          |         \
           v          v          v
      prompt      example     fine-tune
      patches     library     (quarterly)
           \          |          /
            v         v         v
            [Eval gate + canary] --> deploy new agent version
```

On cost: the capture and curation layers are cheap — storage plus one daily batch job plus
maybe an hour a week of human review. Retrieval adds a few hundred tokens per request,
single-digit percent on inference spend. Fine-tuning is a few hundred to a few thousand
dollars per run at this scale, which is why it's quarterly and gated on the cheap tiers
plateauing. The dominant real cost is the eval benchmark's human curation, and I'd defend
that line item hard: it's the difference between learning and drifting.

Failure modes I'd call out unprompted: feedback poisoning, handled by the curation filter
and by never learning from any single user's signals in bulk; judge gaming, handled by
auditing the judge and keeping outcome metrics — real reopen rates — in the loop, since
real-world outcomes are harder to fool than a model grader; and drift, where fixing one
behavior breaks another, handled by the regression suite. And one honest limitation: this
system learns what raters and outcomes reward, which is not identical to what's true or
good. That gap never fully closes; the eval gate and human audits are how we keep it
small."

## Follow-ups they will ask

**"How do you stop it learning the wrong things from bad feedback?"** Three defenses in
layers. Filter at ingestion: discard low-trust signals, cap any single user's influence,
and route anything that would change behavior through human review. Validate before
deploy: every update must beat a frozen benchmark including a regression set of previously
fixed failures. Anchor on outcomes: prefer signals like tickets staying closed over
signals like clicks, because real-world outcomes are harder to game than opinions.

**"Fine-tuning versus in-context learning — how do you choose?"** In-context first, almost
always. It's instant, reversible, inspectable, and needs tens of examples instead of
thousands. Fine-tune when three things are true: the cheap layers have plateaued, you have
thousands of vetted examples, and the lessons are diffuse — style, judgment — rather than
statable rules. And they compose: fine-tune the baseline, keep in-context retrieval for
the fast-moving edge.

**"What if learning one thing makes it worse at another?"** That's regression, and in the
fine-tuning world it has a name — catastrophic forgetting, where new training overwrites
old competence. Defense is the regression benchmark: a suite covering everything the agent
must keep being good at, run on every candidate update, plus a canary rollout so live
metrics catch what the benchmark missed. This is also the intuition behind PPO's clipping:
take small steps near the current known-good behavior, never one giant leap.

**"How do you measure that it's actually improving?"** Two clocks. Offline: benchmark
score trend across versions — same test, rising grade. Online: cohort metrics like reopen
rate, edit distance between bot drafts and human finals (shrinking edits mean improving
drafts), and escalation rate. I'd explicitly watch the human-edit rate; if reviewers stop
needing to touch drafts in a category, that category has been learned.

**"Would you ever let the agent update itself without a human?"** For the example library,
yes with guardrails — auto-admit pairs only when the human edit was small and the outcome
was clean, and even then behind the eval gate. For prompt changes and fine-tunes, no; a
human approves. Self-modifying setups like SICA show it's possible, but note what even
that research system needed: sandbox isolation and an independent overseer model empowered
to halt the agent. Autonomy over your own behavior demands a supervisor that isn't you.

**"Where does reinforcement learning fit in a system like this?"** Mostly as a later,
specialized stage. If we accumulate large volumes of preference pairs, DPO is the
pragmatic on-ramp — direct tuning on comparisons, no separate reward model to hack. Full
RL with PPO makes sense when there's a cheap, automatic, hard-to-game reward — code that
passes tests, trades that profit — because then the agent can practice at scale without
human labels. For subjective quality like support answers, preferences plus DPO beats
hand-rolling a reward function.

## Say it in one breath

Learning and Adaptation means closing the loop: the agent's real-world results — thumbs,
human corrections, outcomes — flow back and change its future behavior. Apply them through
a ladder of dials, cheapest first: patch the instructions, improve the retrieved examples
(in-context learning — teaching by showing, not retraining), and only fine-tune when the
cheap dials plateau and you have volume. And because feedback lies, every update passes a
curation filter and a frozen evaluation gate before it touches production — otherwise
you've built a machine for learning garbage confidently.
