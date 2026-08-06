# Pattern 17: Reasoning Techniques — Buying Better Answers with Thinking Time

## The interview scenario

You'll hear this pattern probed in ways like:

- "Our agent gets simple questions right but falls apart on multi-step problems — math, debugging, anything requiring logic. How would you improve its reasoning?"
- "Design an agent that can answer complex research questions requiring information from multiple sources and several steps of deduction."
- "When would you use a 'reasoning model' with a thinking budget versus a regular model, and how do you decide how much thinking to pay for?"

All three are asking the same thing: do you know how to make a language model *deliberate* instead of blurting out the first answer?

And do you understand what that deliberation costs?

## What this pattern is, in plain words

A language model's default mode is a single fast pass: question in, answer out.

That works for easy questions and fails for hard ones, the same way you'd fail a tricky math problem if you were forced to answer in one second.

Reasoning techniques are the family of tricks that buy the model more thinking.

The simplest is chain-of-thought — literally asking the model to show its work, writing out intermediate steps before the final answer. Instead of jumping to a conclusion, it decomposes the problem and walks through it.

A step up is self-consistency: ask the same question several times, get several independent chains of reasoning, and take the majority vote among the answers.

It sounds almost too dumb to work. It works.

Then there's ReAct, short for Reasoning and Acting, which interleaves thinking with *doing* — the model thinks, takes an action like a search, looks at what came back, and thinks again.

That loop is the beating heart of most real agents.

The umbrella idea, which the book calls the scaling inference law, is that you can trade compute at answer time for quality. More thinking steps, more sampled attempts, more tool calls — each costs money and latency, and each tends to buy accuracy.

A smaller model given a generous thinking budget can beat a bigger model answering in one shot. That's a counterintuitive and very useful fact.

In an interview, that framing — reasoning as a purchasable resource with a price tag — is what makes your answer sound senior. You're not listing prompting tricks; you're describing a budget you spend deliberately.

## How the design actually works

There are four levels, and I'd present them as an escalation ladder.

**Level one: chain-of-thought.** You instruct the model to reason step by step before answering — either by literally saying "think step by step" or by showing it a few worked examples of the style you want.

The problem decomposes into sub-problems, each easier than the whole.

You also get a transparent trace you can read when things go wrong. Debugging a bare wrong answer is archaeology; debugging a wrong chain of thought is just reading.

And it's nearly free — the only cost is longer outputs.

**Level two: sampling and voting.** Self-consistency runs the same chain-of-thought prompt several times with some randomness turned on, then takes the most common final answer.

Why does that help? Because wrong reasoning paths tend to scatter across *different* wrong answers, while correct paths tend to converge on the *same* right one. Majority vote filters the noise.

Tree-of-thought generalizes this further. Instead of independent straight-line attempts, the model explores a branching tree of partial solutions, evaluates the branches, and backtracks from dead ends.

That's useful for puzzles and planning problems where a bad early choice needs to be abandoned, not doubled down on.

**Level three: grounding the reasoning in tools.** ReAct runs a loop of thought, action, observation.

The model reasons about what it needs. It calls a tool — a search, a database query, a calculator. It reads the result. It folds that observation into the next thought, and around it goes.

A close cousin is program-aided reasoning: for anything computational, the model writes actual code and runs it, because a Python interpreter doesn't make arithmetic slips and a language model absolutely does.

**Level four: the modern reasoning model.** This is a model *trained* — typically with reinforcement learning on problems with checkable answers, like math and code — to produce long internal thinking before it responds.

The thinking can run thousands of tokens, with self-correction and backtracking happening inside it.

These models expose an adjustable thinking budget: you can ask for a snap answer or let the model chew for a while. Harder problem, bigger budget.

The budget is a dial you turn, and a line item you pay.

How do you choose among the four levels? The book's rule of thumb: reach for these techniques when a problem is too complex for a single pass — when it needs decomposition, multi-step logic, tool interaction, or strategic planning — and when showing the work matters almost as much as the answer.

Then climb only as high as the problem demands. Chain-of-thought is the default. Tools when facts are missing. Sampling when stakes are high. A trained reasoning model when the problem class is genuinely hard and the budget justifies it.

One honesty caveat I'd volunteer unprompted, because it's the mark of someone who's read the fine print: the visible reasoning is not guaranteed to be the *real* reason.

Models sometimes produce a plausible-looking chain of steps and then give an answer driven by something else entirely — researchers call this unfaithfulness.

So treat a reasoning trace as a useful debugging artifact and a quality booster. Don't treat it as a certified explanation you'd hand an auditor as ground truth.

## The complete interview answer, spoken

"Before I design anything, three quick questions.

"First — what kind of hard is the problem? Is it multi-step logic and math, or is it 'needs facts we don't have in the prompt'? Those want different fixes.

"Second, what's the latency tolerance — is this interactive chat where two seconds matters, or a background job where two minutes is fine?

"And third, do we have any way to check answers, even partially — test cases, historical outcomes, anything?

"Let's say it's a technical support agent that diagnoses problems from logs and documentation. So it's both multi-step *and* needs external facts. Latency tolerance is maybe thirty seconds.

"And we have a few hundred historical tickets with known correct diagnoses — great, that last part means we can measure whatever we build.

"My design philosophy here is one sentence: reasoning is something you buy, so build a ladder and spend only what each query needs.

"The base of the ladder is chain-of-thought. The agent's prompt instructs it to work through a diagnosis explicitly — restate the symptom, list candidate causes, check each one against the evidence, then conclude.

"This alone is a large win over one-shot answering, and it costs only some extra output tokens.

"It also gives me a trace I can read when a diagnosis is wrong. That's not a nice-to-have. When this system misfires in production, the difference between 'the answer was wrong' and 'here's the exact step where the logic went sideways' is the difference between a week of guessing and an afternoon of fixing.

"Next rung. The agent can't diagnose from thin air, so I'd make it a ReAct loop — think, act, observe, repeat.

"The thought might be: 'this looks like a memory issue, I should check the resource metrics.' The action is a tool call — search the docs, pull the logs, query the metrics API. The observation is what comes back, and it feeds the next thought.

"Maybe the metrics look fine, so the hypothesis dies and a new one forms. That's the loop earning its keep: it adapts to what it finds instead of committing to a plan made in ignorance.

"I'd say this plainly to the interviewer: reasoning that can't touch the world is just eloquent guessing. The ReAct loop is what turns a clever essay into a diagnosis.

"For anything numeric — parsing timestamps, computing error rates — the agent writes and runs a small piece of code rather than doing arithmetic in prose. Language models are unreliable calculators. Interpreters aren't. Offload the symbolic work.

"I'd also seed the loop with a few worked examples — complete thought-action-observation trajectories from our best historical diagnoses. Models imitate demonstrated problem-solving style remarkably well, and two good examples in the prompt buy more reliability than a page of abstract instructions.

"And there's a dial on how often the agent thinks. For knowledge-heavy work like diagnosis, a thought before every action keeps the logic tight. For long mechanical sequences, thinking at every step is waste — the agent can act several times between deliberations. That's a tunable, not a constant.

"On the whiteboard, the core loop looks like this:

```
  Question
     |
     v
 +--------+   act    +---------+
 | THINK  | -------> |  TOOL   |  (search / logs / code)
 | (CoT)  | <------- |         |
 +--------+  observe +---------+
     |  repeat until confident
     |  (hard cap on steps)
     v
 [draft answer] --> self-check --> final answer
      (optionally: sample 3x, majority vote)
```

"Now the escalation rungs above that.

"For high-stakes or visibly hard queries, I add self-consistency: run the whole diagnosis three or five times independently and take the majority answer.

"It's brutally simple and it works, because independent wrong paths rarely agree with each other, while correct paths keep landing in the same place.

"It multiplies cost by the number of samples, so it's a dial, not a default. I'd trigger it when the single-pass answer comes back with low confidence, or when the ticket is tagged critical. Most traffic never touches it.

"For the planning-heavy tickets — the ones that read 'our deployment strategy needs rethinking' rather than 'this crashed' — I'd mention tree-of-thought: instead of one line of reasoning, the agent explores a few branches of partial solutions, evaluates them, and backtracks from dead ends before committing.

"It's more expensive than straight chain-of-thought, so it's reserved for problems where an early wrong turn is costly. Most diagnoses don't need it. The occasional strategy question does.

"And at the top of the ladder: for genuinely gnarly problems, I'd route to a dedicated reasoning model — one trained to generate long internal deliberation — with a thinking budget set by problem tier. Easy tickets get a small budget. Escalated ones get a big one.

"This is the scaling inference law in practice. Performance rises predictably with inference-time compute, so the budget is a knob I tune against measured accuracy, not a fixed cost I grudgingly accept.

"And it cuts the other way too — sometimes a smaller model with a generous budget beats a bigger model answering fast, which is a cost win worth testing for explicitly.

"Tradeoffs I'd flag before being asked.

"First, latency. Every rung adds seconds, so the ladder must be tiered — most queries should resolve on the cheap rungs, and I'd track what fraction escalate. If half my traffic is climbing to the top rung, my routing is broken or my base rung is too weak.

"Second, verbosity isn't intelligence. A model can produce a long, confident, wrong chain of thought. That's why I want the ReAct loop grounding claims in actual tool observations rather than pure armchair reasoning — every factual claim in the final diagnosis should trace back to something a tool returned.

"Third, the faithfulness caveat. I'd tell the team explicitly: the visible reasoning is a quality tool and a debugging aid, but it is not a guaranteed window into the model's true computation.

"Models can rationalize — produce a tidy justification for an answer that was actually driven by something else. So we never present the trace as a compliance-grade explanation. For auditability, we lean on the objectively checkable parts: which tools were called, what they returned, whether the cited evidence supports the conclusion.

"Failure handling. The ReAct loop needs a step cap — say ten thought-action cycles — because a confused agent will happily loop forever, re-searching the same phrase with minor rewordings.

"On hitting the cap, it summarizes what it found and what it ruled out, and escalates to a human rather than fabricating a conclusion. A crisp 'here's what I checked and I'm stuck' is a genuinely useful artifact. A confident fabrication is a landmine.

"Tool failures feed back into the loop as observations — 'the metrics API timed out' — so the model can reason around them, try an alternative source, or note the gap. That's exactly what makes ReAct more robust than a fixed pipeline: the plan bends instead of breaking.

"Evaluation — this is where those historical tickets pay off.

"I'd build a test set of ticket-to-diagnosis pairs and measure accuracy at each rung of the ladder: plain chain-of-thought, ReAct, ReAct plus self-consistency, reasoning model at several budget settings.

"That gives me an accuracy-versus-cost curve, and the business picks the operating point with eyes open. Maybe triple-sampling buys four points of accuracy for triple the cost — worth it on critical tickets, absurd on password resets. Without the curve, that conversation is vibes.

"In production I monitor step counts per query, escalation rates between rungs, and token spend per resolution. And I sample traces weekly and actually read them, watching for drift in reasoning quality.

"Rollout would be staged. Week one, shadow mode: the agent diagnoses alongside humans, and nobody sees its output but the eval pipeline. That builds the accuracy numbers risk-free.

"Then assisted mode: the agent's diagnosis and trace appear as a suggestion for the human engineer, who accepts or overrides — and every override is labeled training signal, collected for free.

"Only after the numbers hold does it answer autonomously, and only on the ticket classes where it's proven. Autonomy is granted per tier, with evidence — the same way you'd extend trust to a new hire.

"Cost, concretely. If a one-shot answer is roughly a cent, chain-of-thought might make it three cents. ReAct with five tool calls, maybe ten cents. Triple self-consistency on top of that, thirty cents. A big thinking budget on a reasoning model can run toward a dollar per query.

"Every one of those numbers is still cheap next to fifteen minutes of a support engineer's time — but only if the accuracy gain is real.

"Which is why the eval harness comes first, not last."

## Follow-ups they will ask

**"Why does self-consistency actually work? Isn't it just asking the same model again?"**

"Because errors are inconsistent and correct reasoning is convergent. With sampling randomness on, each run takes a somewhat different path. Flawed paths land on scattered wrong answers; sound paths keep arriving at the same right one. Majority vote is a cheap noise filter.

"Where it fails is systematic misconception — if the model fundamentally misunderstands the problem, all five runs agree on the same wrong answer, confidently. Voting can't fix a shared blind spot."

**"Chain-of-thought versus a reasoning model with a thinking budget — when do you pick which?"**

"CoT is prompting: the thinking is visible, cheap, and I control its structure. A reasoning model is trained to deliberate: its thinking is longer, often hidden, better at self-correction and backtracking, and priced by budget.

"I prototype with CoT because it's free to try, and I move the hard tier of traffic to a reasoning model once my evals show the accuracy gap justifies the price. It's rarely either-or — it's a routing decision per difficulty tier."

**"How is ReAct different from just doing chain-of-thought and then calling tools?"**

"Interleaving. A plan-then-execute pipeline commits to a plan before seeing any data. ReAct re-thinks after every observation, so when the logs contradict the initial hypothesis, the very next thought pivots.

"You pay for that adaptivity with more model calls and the risk of loops — which is why the step cap isn't optional."

**"Can you trust the reasoning trace as an explanation for users or auditors?"**

"Not fully, and I'd say that out loud to stakeholders. Traces are useful for debugging and quality, but models can produce reasoning that doesn't reflect what actually drove the answer — that's the unfaithfulness problem.

"For auditability I lean on the parts that are objectively checkable: the tool calls made, the data returned, whether cited evidence actually supports the conclusion. Those are facts; the prose in between is helpful narration."

**"How do you stop thinking budgets from blowing up your costs?"**

"Tier and measure. Route by estimated difficulty so easy queries never touch the expensive rungs. Cap steps and budgets per tier. Monitor spend per resolved query as a first-class metric with an owner.

"The scaling inference law says more compute buys more quality, but the curve flattens — my eval harness tells me where the knee is, and that's where the dial gets set."

**"What about several models debating each other?"**

"That's the chain-of-debates idea — multiple models propose answers, critique each other's reasoning, exchange counterarguments, and converge. It's a peer-review flavor of the same principle: spend more inference compute, reduce any single model's blind spots, get a better-validated answer.

"It's also the most expensive rung of all, so I'd reserve it for high-stakes offline work — not per-request serving."

## Say it in one breath

"Reasoning techniques trade inference-time compute for answer quality: chain-of-thought makes the model show its work, self-consistency samples several chains and takes the majority, ReAct interleaves thinking with tool calls in a think-act-observe loop, and modern reasoning models make deliberation a tunable budget. I'd build it as an escalation ladder, route by difficulty, cap the loops, and measure accuracy against cost on a real test set — remembering that a visible chain of thought is a debugging aid, not sworn testimony about why the model answered the way it did."
