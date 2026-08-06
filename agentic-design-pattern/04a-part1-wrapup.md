# Part 1 wrap-up: choosing among the four, out loud

Before you move on, let's zoom out, because interviews rarely stay inside one pattern — the follow-ups push you across their borders, and the strongest answers *compose* them.
Here's the mental sorting routine, as you'd actually speak it while staring at a fresh problem.

First question: **does every request need the same steps?**
If yes — the work always has the same stages, in the same order — you have a chain; your energy goes into the seams: structured hand-offs, validation, tools where the model is weak, checkpoints where things pause.
If no — requests fall into genuinely different kinds — a router goes in front, and each kind gets its own (usually chained) path behind its own door, plus the honest door marked "not sure."

Second question: **inside whatever path a request takes, which steps actually depend on each other?**
Draw the needs-the-output-of arrows; everything unconnected is a candidate to fan out in parallel, and whether you bother depends entirely on whether anyone feels the wait — parallelize the parts users feel, leave the rest sequential and simple.

Third question: **where does a mistake actually hurt?**
That's where a reflection loop earns its cost — the one or two steps whose errors are expensive, guarded by the most objective critic you can build, with a lap budget — while everything else ships single-pass.

Notice what this routine produces: a system with a router at the door, chains behind each route, a parallel block where the chain fans into independent lookups, and a reflection loop wrapped around the step that matters most.
That composite — fork, then road, then wide road, then U-turn — is, in one diagram, most production agentic systems in the wild today, and the book's own examples keep converging on it: the research agent that fans out its gathering and then chains its synthesis, the pipeline that routes on extraction quality, the generator whose reviewer gets the final word.
If you internalize nothing else from this part, internalize the composite — and the habit of *justifying* each piece by a requirement, because the difference between architecture and decoration is a reason.

Here are the four on one card — the table to redraw from memory the morning of the interview:

| Pattern | One-line trigger | What it buys | What it costs | Signature failure |
|---|---|---|---|---|
| Prompt Chaining | Distinct stages, each feeding the next | Reliability, debuggability, tool seams | Stacked latency, more parts | Error compounding across steps |
| Routing | Different kinds of requests, one front door | Specialist quality per category | A decision tax on every request | Misrouting; category drift |
| Parallelization | Independent steps, someone waiting | Latency collapse to the slowest branch | Concurrency complexity, debugging fog | Stragglers; rate-limit collisions |
| Reflection | Quality bar higher than a first draft | Error catching before shipping | Multiplied cost and latency | Lenient critic; endless loop |

Two closing exam tips.
When you're stuck, return to dependencies and stakes: "what needs what" chooses between chain and parallel; "what varies" chooses whether routing exists; "what's expensive to get wrong" chooses where reflection lives.
And when you're finished, say the costs unprompted — the latency the chain stacked, the tax the router charges every request, the money parallelism didn't save, the multiplier reflection put on the bill — because every one of these patterns buys its benefit with something, and naming the price is what separates a candidate who read about the patterns from one who can be trusted to run them.

## The rapid-fire self-quiz

Close the book and answer these aloud — if any takes you more than fifteen seconds to start, reread that section.

1. What are the five beats of the loop that makes a system an agent rather than a model?
2. Name the four ways a single monolithic prompt fails, by name.
3. Why does structured output between chain steps matter more than the prompts themselves?
4. Five chained steps at 95% accuracy each — roughly what end-to-end accuracy, and what's the fix?
5. What belongs at the seams of a chain besides the next LLM call?
6. A step returns broken JSON — walk the recovery in one sentence.
7. What are the four router implementations, and which needs no training data?
8. Why must `unclear` be a first-class route rather than an error?
9. What's the pragmatic router lifecycle from day one to month three?
10. A message contains two intents — what's your policy?
11. What single property makes two steps safe to parallelize, and what bug appears when you violate it?
12. Fan-out, fan-in, straggler — define all three in one breath.
13. Why doesn't parallelization save money?
14. What three protections does every fan-out need before production?
15. What's the difference between concurrency and parallelism, and why is it fine for I/O-bound agents?
16. Why does a separate critic outperform "double-check your own work"?
17. Rank the critic types from most to least trustworthy.
18. Name the three exits every reflection loop needs.
19. When do you choose best-of-N over a reflection loop?
20. What's the one metric that proves a reflection loop is earning its cost?
21. Recite the seven moves of the universal answer skeleton.
22. What are the four ways candidates most commonly lose points?
23. Compose all four patterns into one sentence describing a production support system.
24. For each pattern: what does it buy, and what does it cost?

When you're done, the answer key is the next page: [Part 1 self-quiz: the answer key](04b-part1-quiz-answers.md).
Attempt every question aloud *before* you open it — reading answers you haven't struggled for feels productive and teaches almost nothing.

How to grade yourself, honestly.
Twenty or more answered fluently: you're interview-ready on these four patterns — spend your remaining time on mock interviews, not rereading.
Fifteen to nineteen: solid foundations with specific gaps — notice *which* patterns your misses cluster in, because a cluster means reread that chapter, while scattered misses mean redo the quiz tomorrow after sleep.
Below fifteen: no shame, but don't move to Part 2 yet — the later patterns assume these four are automatic, and shaky foundations compound exactly like chain errors do.
And regardless of score, retake the quiz forty-eight hours later; the answers you had to reconstruct rather than recall are the ones that will desert you under interview pressure, and two spaced repetitions is usually what pins them down.

## What's coming in Part 2

A short preview, so the foundations you just built have somewhere to go.
The next stretch of Gulli's book — and of this playbook — moves from *workflow shapes* to *capabilities*: tool use in earnest, where the agent's hands get real and the safety questions get serious; planning, where the model starts writing its own to-do lists instead of following yours; multi-agent collaboration, where routing's dispatcher grows into a team with roles and handoffs; and memory, which turns the stateless machinery of this part into systems that remember you between conversations.
Every one of them stands on this part's shoulders: a plan is a self-written chain, a coordinator is a router with employees, a research team is a fan-out with job titles, and a reviewer agent is reflection given a desk of its own.
Master the four shapes here and Part 2 will feel less like new material and more like promotions for patterns you already know.

*End of Part 1.
You now hold the four foundational patterns — the straight road, the fork, the wide road, and the U-turn.
Part 2 picks up with tool use, planning, and multi-agent collaboration: the patterns that turn these workflows into systems that act on the world.*
