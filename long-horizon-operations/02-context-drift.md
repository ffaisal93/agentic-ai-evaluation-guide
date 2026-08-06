# Context drift: why turn 40 is a different animal than turn 4

## Start with a kitchen counter

Picture a small kitchen counter at the start of a long cook.

It's clean, you've got the recipe propped up where you can see it, and everything you touch is exactly where you left it.

Two hours later that same counter is a disaster.

There are four dirty pans, three bowls of things you prepped and forgot about, a puddle of something, two empty packets you meant to throw away, and the recipe is under all of it.

You haven't gotten dumber over those two hours.

Your *workspace* got worse, and working in a bad workspace makes you worse.

That's the whole idea behind context drift, and if you hold onto the counter image you'll have most of the intuition you need.

An agent's context window — the fixed-size block of text the model reads before every single response, which holds the instructions, the conversation so far, and everything the tools returned — is that counter.

At turn 4 it's tidy.

At turn 40 it's got forty turns of debris on it, and the recipe is buried somewhere in the middle.

Here's the part that surprises people: the model isn't *forgetting* in the human sense.

Every token is still sitting right there, perfectly legible.

The problem is attention — the mechanism by which a transformer model decides how much weight to give each piece of its input when producing the next word.

Attention is a finite budget spread across everything present.

Anthropic's engineering team describes this directly in their writing on context engineering: models have "an attention budget that they draw on when parsing large volumes of context," and every token you add draws down that budget a little.

So the instruction you wrote at the top — "always ask before deleting anything" — isn't gone at turn 40.

It's just competing with thirty-nine thousand tokens of other stuff for the model's attention, and it's losing.

That gradual loss is what the industry has started calling **context rot**: as the number of tokens in the window goes up, the model's ability to reliably use any particular one of them goes down.

Chroma's 2025 technical report on context rot tested eighteen models across Anthropic, OpenAI, Google, and Alibaba, and found the same shape everywhere — performance "grows increasingly unreliable as input length grows," even on tasks that are trivially easy at short lengths.

Not a cliff at the context limit.

A slope, starting much earlier than you'd like.

## What's actually piling up on the counter

If you're going to manage the mess, you should know what the mess is made of.

Six things accumulate in a long-running agent's context, and they are not equal in size.

**The system prompt and the original goal.** This is the smallest and most important piece, and it's usually written once, at position zero, and then never touched again for the rest of the run. Hold that thought — it matters later.

**Every tool call the agent made.** The actual invocation: `read_file("/app/src/billing/invoice.py")`. Cheap, a few dozen tokens each.

**Every tool *result*.** This is the monster. That file read might come back as 900 lines. A database query might return 4,000 rows. A web fetch returns an entire page of navigation chrome and cookie banners. Nobody wrote these; a machine did, and machines are verbose. In most long-running agents I've looked at, tool results are somewhere between sixty and ninety percent of the context by turn 30, and they're the least deliberately managed part of the whole thing.

**The model's own reasoning.** Every "let me think about this — the user wants X, so first I should..." stays in the transcript and gets re-read on every subsequent turn.

**Retrieved documents.** If you're doing RAG — retrieval-augmented generation, where you search a knowledge base and paste the hits into the prompt so the model can answer from them — those hits stack up too, and old ones rarely get cleaned out.

**Error messages from failed attempts.** Stack traces. Timeouts. "Permission denied." Malformed-JSON complaints. Each one is a small block of low-value, high-token-count text, and they arrive exactly when the agent is already struggling.

The asymmetry is the thing to internalize.

The stuff you carefully wrote — the goal, the constraints, the format rules — is a tiny fraction of the window and it stops growing after turn one.

The stuff nobody wrote grows without limit.

By turn 40, your carefully crafted instructions are a rounding error in a sea of machine output.

## The seven ways it goes wrong

"Context drift" is a bucket term, and buckets are bad for debugging.

What you actually want is the ability to look at a broken transcript and say "that's instruction decay, not goal drift," because the fixes are different.

So here are the seven distinct failure modes, each with what it actually looks like when you read the log.

### Goal drift

The agent gradually optimizes for a subgoal and loses the original ask.

This one is sneaky because every individual step looks reasonable.

You asked for: "Find out why our checkout conversion dropped last week."

By turn 12 the agent has decided it needs clean analytics data first, which is fair.

By turn 25 it is writing a data-validation script.

By turn 40 it is debugging the test suite for the data-validation script, and it has not thought about checkout conversion in twenty-eight turns.

In the transcript you'll see the objective quietly restated in a smaller form: turn 3 says "to understand the conversion drop," turn 20 says "to get reliable data," turn 35 says "to make these tests pass."

Nobody lied to you.

The goal just got replaced by its own scaffolding, one reasonable substitution at a time.

### Instruction decay

Rules from the system prompt stop being followed somewhere around turn N.

You wrote "never modify files outside `/workspace`" at the top.

Turns 1 through 22, honored perfectly.

Turn 23, the agent edits something in `/etc` because it seemed necessary and nothing in its recent attention said not to.

The tell in a transcript is that the violation is *casual*.

There's no reasoning about the rule, no "the user said not to, but...".

The rule simply isn't in the model's effective working set anymore, so it never comes up.

This is the most direct consequence of the attention-budget problem, and it's why the fix is re-injection rather than stronger wording.

Writing "NEVER, UNDER ANY CIRCUMSTANCES" at position zero does not make position zero more attended-to at turn 40.

### Persona and format drift

The shape of the output degrades even when the content is fine.

You asked for JSON with four specific fields.

Turns 1 through 15: clean JSON.

Turn 22: JSON wrapped in a markdown code fence.

Turn 30: JSON with a chatty preamble, "Sure! Here's the updated record:".

Turn 38: prose, with the four fields mentioned in a sentence.

Tone does the same thing — a support agent that started crisp and professional gets progressively more casual as the transcript fills with its own increasingly informal turns, because the model is imitating the recent past, and the recent past is itself.

That's the feedback loop that makes format drift accelerate rather than plateau.

### Lost in the middle

Facts buried in the middle of a long context get under-used, even though they're right there.

This one has a real, well-known paper behind it: Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," published in TACL.

They tested multi-document question answering and key-value retrieval, moving the location of the relevant information around, and found a U-shaped curve — "performance is often highest when relevant information occurs at the beginning or end of the input context, and significantly degrades when models must access relevant information in the middle of long contexts, even for explicitly long-context models."

In a transcript this looks like the agent confidently doing something the user explicitly ruled out at turn 18.

The constraint is there.

It's just at the bottom of the counter with a pan on top of it.

The practical consequence is a positioning rule you'll use constantly: if a fact must survive, it goes near the end, not the middle.

### Context poisoning

One wrong fact enters the history and is thereafter treated as ground truth.

This is the nastiest of the seven, because contexts are append-only by default.

Say at turn 9 a tool returns a truncated result and the agent concludes "the `users` table has no `created_at` column."

That sentence is now in the transcript.

At turn 15 it writes a query that avoids `created_at`.

At turn 24 it builds a whole workaround table.

At turn 33, when a different tool result plainly shows `created_at` right there in the schema, the model has two conflicting facts and often sides with the one it has been repeating for twenty turns.

Drew Breunig's writeup on how contexts fail names this one directly — "when a hallucination or other error makes it into the context, where it is repeatedly referenced" — and points at the Gemini Pokémon-playing agent, where a corrupted goals section led the model to pursue impossible objectives for long stretches.

The reason poisoning is so bad is that it is self-reinforcing.

Every turn where the agent acts on the bad fact produces more text asserting the bad fact.

### Error-loop pollution

Failed attempts fill the window with noise that makes the next attempt worse.

The agent tries a command, gets a 40-line stack trace, tries a slight variation, gets a nearly identical 40-line stack trace, and repeats.

By attempt six you've spent 250 lines of context on six almost-identical failures, and the model is now pattern-matching on "here is a thing that fails" rather than on the original task.

Manus, the agent product team, argues in their context engineering writeup that you should generally *keep* errors in context, because seeing a failure is how the model learns to stop repeating it — and I think that's right for the first error or two.

What kills you is the eighth copy of the same trace.

The distinction worth holding: one error is signal, six identical errors are noise, and the difference between a healthy agent and a spiraling one is whether anything in your system notices the transition.

### Stale context

The world changed and the agent is reasoning from an old snapshot.

At turn 5 the agent reads a config file and learns the service runs on port 8080.

At turn 30 — possibly because the agent itself edited that file at turn 22 — it's 9090.

The turn-5 read is still sitting in context, stated as fact, with no timestamp and no marker saying "this may be out of date."

The agent confidently connects to 8080 and fails, and then spends five turns debugging a network problem that doesn't exist.

Stale context is the failure mode that gets worse the more *effective* your agent is, because an agent that changes the world invalidates its own notes.

### The seven, on one card

Worth memorizing as a set, because in an interview the fastest way to sound like you've done this is to name the specific mode instead of saying "the context got messy."

| Failure mode | What you see in the log | First thing to reach for |
| --- | --- | --- |
| Goal drift | Objective quietly restated smaller each time | Periodic goal restatement + re-grounding |
| Instruction decay | A system-prompt rule broken casually, with no reasoning about it | Canary instructions + re-injection |
| Persona/format drift | Schema violations, chattier tone, creeping preambles | Per-turn validation, few-shot re-anchoring |
| Lost in the middle | A mid-context constraint ignored while early and late ones hold | Move critical facts to the tail |
| Context poisoning | A wrong fact repeated and defended across many turns | Verify-before-commit, prune the poisoned span |
| Error-loop pollution | Six near-identical stack traces in a row | Collapse repeats, cap retries, escalate |
| Stale context | Acting on a value the agent itself changed later | Timestamp facts, re-read before relying |

## Summarization is not a free fix

The obvious response to a crowded counter is to clean it, and the obvious way to clean a context is **compaction** — summarizing the older part of the conversation and replacing it with the summary, so the run can continue in a smaller footprint.

Anthropic describes it as "taking a conversation nearing the context window limit, summarizing its contents, and reinitiating a new context window with the summary."

It works.

It is also lossy, by construction, and this is where people get burned.

Compaction is not "making the context smaller."

Compaction is *choosing what to throw away*, and whatever you throw away determines which of the seven failure modes you get.

Drop the original goal statement in favor of recent progress, and you've built a goal-drift machine.

Drop the system-prompt constraints because they're "static instructions, not conversation," and you get instruction decay on a schedule.

Drop the raw tool results but keep the model's interpretation of them, and you've locked in whatever mistakes were in that interpretation — poisoning, permanently, with the evidence deleted.

And then there's the spiral.

Summarize turns 1-40 into a paragraph.

Continue to turn 80, then summarize [that paragraph plus turns 41-80] into a new paragraph.

Continue to turn 120, summarize again.

You are now summarizing a summary of a summary, and each pass is a lossy compression of an already-lossy compression.

It's the photocopy-of-a-photocopy problem.

Details go first, then nuance, then whole constraints, and what survives to the third generation is a generic, confident-sounding blur — "the user wants the billing system improved" — that has lost every specific the run actually depended on.

The counterintuitive fix is to make compaction *less* free-form, not more clever, and we'll get to that in the mitigations.

## Actually detecting drift

Here's the part most courses skip entirely, and it's the part that separates people who've run agents in production from people who've read about them.

You cannot fix drift you can't see, and drift is specifically the failure mode that doesn't throw an exception.

The run completes.

The agent sounds confident.

Everything looks fine until a human reads turn 40 closely.

So you need instrumentation, and here are six things that actually work.

**Canary instructions.** Plant a small, checkable, harmless rule in the system prompt whose violation you can detect mechanically. Something like: "End every response with the token `<<OK>>`." It costs you six tokens per turn and buys you a binary signal — the turn where the canary stops appearing is, roughly, the turn where your system prompt stopped being effectively read. Coal miners used actual canaries for exactly this reason: you want the cheap thing to die first, while there's still time to react. Use two or three canaries of different kinds (a format rule, a content rule, a refusal rule) because they decay at different rates and tell you different things.

**Periodic goal restatement.** Every N turns, ask the agent to state, in one sentence, what it's currently trying to accomplish and why. Then diff that against the original ask — string similarity is enough to start, an LLM judge scoring "does this still describe the same objective?" is better. When the restatement stops mentioning the original noun, you have goal drift, and you have it with a turn number attached.

**Per-turn format validators.** If the agent is supposed to emit structured output, validate every single turn against the schema — a schema being a formal description of the required shape, like "an object with keys `status`, `findings`, and `next_action`." Don't sample. Validation is nearly free and format drift is your earliest, loudest warning that attention is thinning out.

**A drift probe.** Every N turns, inject a small question whose correct answer you already know and which depends on something stated early in the context. "What was the budget limit I gave you?" If it answers right, the early context is still live. If it hedges or invents, it isn't. This is the closest thing to a direct measurement of "is the top of my context still being read," and it's cheap enough to run every ten turns.

**Quality metric versus turn index.** This is the key move, and if you take one operational habit from this chapter, take this one. Whatever quality metric you already have — judge score, task success, human rating — stop reporting it as a single number per run and start plotting it against turn number. A run that scores 0.82 overall might be 0.95 for thirty turns and 0.45 for the last twenty, and those two facts have completely different fixes. The average hides the cliff. The curve shows you exactly where it is, which tells you where to put your compaction boundary. The next chapter is entirely about building this properly.

**Context size growth per turn.** Log the token count of the context at every turn and watch the slope, not just the total. A healthy run grows roughly linearly and gently. A run that suddenly adds 30,000 tokens in two turns just ate a giant tool result, and that's your leading indicator for every other problem on this list — usually minutes before quality visibly drops.

The theme across all six: drift is gradual, so your instruments have to be *per-turn*, not per-run.

Anything you measure once at the end will tell you the patient died without telling you when they got sick.

## Fixing it, with the tradeoffs stated

There's no single fix, and anyone who tells you "just use a bigger context window" hasn't watched quality fall off a cliff at 60k tokens inside a 200k window.

Here's the toolkit, roughly in order of how much I reach for each.

**Structured compaction.** Instead of "summarize the conversation," compact *into a schema*. Something like: `original_goal` (copied verbatim, never re-summarized), `hard_constraints` (a list, verbatim), `completed_steps`, `current_state`, `open_questions`, `known_dead_ends`. The schema is what protects you, because free-form summarization drops whatever the summarizer felt was less interesting, while a schema has a slot that must be filled. Copy the goal and constraints by reference rather than re-summarizing them each time, and you've broken the photocopy spiral for exactly the fields that matter most. Tradeoff: you have to design the schema per agent type, and a schema that doesn't fit the task will squeeze out information you needed.

**Externalize state to a file.** Give the agent a scratchpad — a file it writes progress notes to and re-reads when it needs them — and treat that file, not the transcript, as the source of truth. Anthropic's writing on long-running agents describes exactly this pattern for coding agents: a progress file plus a structured feature list plus git history, so a fresh session can reconstruct where things stand. Manus does the same with a `todo.md` that the agent rewrites as it goes. The elegant side effect is that rewriting the todo list pushes the current objective back to the *end* of the context on every update — which, per the lost-in-the-middle finding, is exactly where it needs to be. Tradeoff: the agent has to actually maintain the file, and an agent that lies to its own scratchpad is worse than one with no scratchpad.

**Re-grounding.** Every N turns, re-inject the goal and the hard constraints as a fresh message near the end of the context. Not a rewrite, not a summary — the same text, again, in a position with attention on it. It costs you a few hundred tokens per re-injection and it directly counteracts instruction decay and lost-in-the-middle at the same time. Tradeoff: if you re-inject too often you're burning budget and training the model to skim repeated blocks; every 10-20 turns is a reasonable starting point, tuned by where your canaries actually start failing.

**Sub-agent isolation.** This is the strongest fix, and it's worth understanding *why* rather than just doing it. Everything above manages a context that keeps growing. Sub-agent isolation refuses to let it grow. You hand a subtask to a fresh agent with a clean context, it burns thirty turns of its own doing the messy exploratory work, and it returns a short distilled result — Anthropic quotes "often 1,000-2,000 tokens" — to the parent. The parent's context grows by two thousand tokens instead of forty thousand. Every one of the seven failure modes is a function of how much junk is in the window, so the fix that structurally bounds the junk beats all the fixes that clean it up afterward. This is also why "should I use multi-agent?" is often really a context-management question wearing a costume. Tradeoff: the sub-agent can't see the parent's context, so you have to brief it well, and a bad brief means it solves the wrong problem in isolation. You also pay for the extra model calls and you lose the ability to easily debug what happened inside.

**Tool-result truncation and lazy expansion.** Cap what any single tool result can contribute — say, the first 2,000 tokens — and replace the rest with a reference the agent can expand on demand: "[truncated: 8,400 more tokens; call `read_more(handle=...)` to see them]". This is the highest-leverage change per unit of effort, because tool results are the bulk of the problem and almost nobody bounds them. The frameworks have grown real support for it. LangChain's `ContextEditingMiddleware` with `ClearToolUsesEdit` clears older tool outputs once you cross a token threshold while keeping the most recent few, and Anthropic's Developer Platform ships server-side context editing that clears stale tool results automatically — their reported result on a 100-turn web search evaluation was completing workflows that would otherwise have died of context exhaustion "while reducing token consumption by 84%," with a 29% performance improvement from context editing alone and 39% when combined with a persistent memory tool. Tradeoff: truncate the wrong 8,000 tokens and the agent re-fetches, which costs you a turn. Lazy expansion makes that recoverable; hard deletion doesn't.

**Position critical facts at the end.** Cheap, mechanical, and follows straight from the U-shaped curve. Whatever must not be missed — the current constraint set, the active goal, the most recently discovered facts — goes in the last block before the model responds, not in the middle. Tradeoff: this fights with prompt caching, where a stable prefix is billed at a steep discount, so shuffling content late in the context can invalidate cache and raise cost. The usual resolution is a stable cached prefix plus a small, deliberately re-written "current state" block at the tail.

**Know when to stop and hand off.** Sometimes the counter is too dirty to wipe, and the right move is a new session with a deliberate handoff — a compact, structured briefing that lets a fresh context pick up the work. That deserves its own chapter, and it has one; this is the forward reference.

## What this looks like in the wild

The coding agents are the most-watched long-running agents in existence right now, and their design choices are a decent proxy for what actually holds up.

Claude Code runs auto-compaction: as the session approaches the window limit it compacts automatically, and it exposes manual controls — `/compact` to do it on demand, `/clear` to start clean, and an `autocompact` setting to control the threshold. The distinction between those two commands is the whole chapter in miniature: `/compact` keeps a lossy summary and continues, `/clear` throws everything away and restarts. Experienced users reach for `/clear` more than you'd expect, because a clean context plus a good `CLAUDE.md` project file — an externalized-state file the agent re-reads at the start of every session — beats a compacted context carrying forty turns of accumulated confusion.

Anthropic's own writeup on harnesses for long-running agents is blunt that "compaction isn't sufficient" on its own, and describes their working setup as an initializer agent that lays down scaffolding — an `init.sh`, a progress file, an initial git commit — followed by coding agents that each start a shift by reading the progress file and the git log and running the tests before touching anything. Their analogy is engineers working shifts, each arriving with no memory of the last one. The state lives on disk, not in anyone's head.

The Manus team's version is the same instinct from a different angle: treat the filesystem as unlimited external memory, compress observations by dropping content while *keeping the reference* — the URL, the file path — so the compression is reversible.

And the honest caveat, because it keeps you from over-promising in an interview: this doesn't fully solve long-horizon reliability yet. Vending-Bench, a benchmark that runs agents through a simulated vending-machine business over runs exceeding 20 million tokens, found agents that forget orders they placed, misread delivery schedules, and occasionally spiral into tangential "meltdown" loops they rarely recover from. The finding worth remembering is that the authors found no clear correlation between those failures and the point where the context window fills up. Context pressure is a major cause of long-run failure. It is not the only one, and an answer that claims compaction solves long-horizon agents is overclaiming.

## Say it in one breath

"Context drift is what happens when an agent's context window — the block of text the model re-reads before every response — fills up with forty turns of tool output, reasoning, and errors, so the original goal and the system prompt's rules get drowned out; not forgotten, just out-attended. It shows up as seven distinct failures — goal drift, instruction decay, format drift, lost-in-the-middle, context poisoning, error-loop pollution, and stale context — and summarizing the history doesn't fix it for free, because compaction is lossy and *what you drop* decides which failure you get. You detect it with per-turn instruments: canary instructions, periodic goal restatement, schema validation every turn, and above all by plotting your quality metric against turn index so you can see where the cliff is. You mitigate it with structured compaction that copies the goal verbatim, an externalized state file the agent re-reads, re-grounding every N turns, tool-result truncation with lazy expansion, and — strongest of all — sub-agent isolation, where a subtask burns its own fresh context and returns a two-thousand-token summary, because bounding the junk beats cleaning it up."

## What an interviewer is really testing

They want to know whether you've actually operated an agent past turn ten, because everyone has built a three-turn demo and almost nobody has watched one rot at turn forty.

The tell they're listening for is whether you name specific failure modes with specific fixes, rather than saying "we'd summarize the history" and stopping — because that answer reveals you think of context as a size problem rather than a *composition* problem.

They also want to see you say out loud that compaction is lossy and that the loss is a design decision you own, since candidates who treat summarization as free are the ones who ship goal-drift bugs.

If you volunteer the detection story — canaries, goal restatement, quality-versus-turn-index curves — you've separated yourself from the field, because that's the half that only comes from production.

And if you reach for sub-agent isolation and can explain that it wins by *structurally bounding* context growth rather than cleaning up after it, you're demonstrating the systems instinct the whole question exists to find.

## Where this comes from

Everything cited above is real and worth reading in the original, roughly in the order I'd read them.

- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts," TACL — the U-shaped position curve: <https://aclanthology.org/2024.tacl-1.9/>
- Chroma, "Context Rot: How Increasing Input Tokens Impacts LLM Performance," 2025 — eighteen models, same slope: <https://research.trychroma.com/context-rot>
- Anthropic, "Effective context engineering for AI agents" — attention budget, compaction, structured note-taking, sub-agents: <https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents>
- Anthropic, "Effective harnesses for long-running agents" — shift-handoff design, why compaction alone isn't enough: <https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents>
- Anthropic, "Managing context on the Claude Developer Platform" — context editing and the memory tool, with the 84% / 29% / 39% numbers: <https://claude.com/blog/context-management>
- Drew Breunig, "How Long Contexts Fail" — poisoning, distraction, confusion, clash: <https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html>
- Manus, "Context Engineering for AI Agents: Lessons from Building Manus" — recitation via `todo.md`, filesystem as context, keeping errors in: <https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus>
- Andon Labs, "Vending-Bench: A Benchmark for Long-Term Coherence of Autonomous Agents" — long-run meltdowns uncorrelated with context fullness: <https://arxiv.org/abs/2502.15840>
- Claude Code context window docs — auto-compaction, `/compact`, `/clear`: <https://code.claude.com/docs/en/context-window>
- LangChain middleware reference — `SummarizationMiddleware` and `ContextEditingMiddleware`: <https://docs.langchain.com/oss/python/langchain/middleware/built-in>

