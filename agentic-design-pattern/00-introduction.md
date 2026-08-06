# The Agentic Design Patterns Interview Playbook

Welcome.
This playbook exists for one reason: to get you ready for the moment an interviewer leans back and says, "Okay — design me an AI agent that does X."
That moment is scary the first time, because agentic system design sits at the intersection of two things most people learn separately: how large language models behave, and how real production systems are built.
This book bridges that gap, pattern by pattern.

The playbook is a study companion to Antonio Gulli's *Agentic Design Patterns*, a book that lays out twenty-one patterns for building AI agents — the recurring shapes that show up over and over once you start assembling LLMs into systems that actually do things.
Gulli's book teaches you the patterns.
This playbook teaches you to *talk about them under pressure*, the way an interview demands: out loud, with tradeoffs, with failure modes, with a whiteboard diagram, in fifteen minutes.

Here is how it is organized.
There are twenty-one patterns, split into five parts that follow the arc of Gulli's book.

**Part 1 — the workflow patterns** (Prompt Chaining, Routing, Parallelization, Reflection): the four
foundational shapes that appear in almost every agentic design answer you will ever give.

**Part 2 — the action patterns** (Tool Use, Planning, Multi-Agent Collaboration, Memory Management):
how an agent stops merely talking and starts doing things, plans them, delegates them, and remembers.

**Part 3 — the self-management patterns** (Learning and Adaptation, Model Context Protocol, Goal
Setting and Monitoring, Exception Handling and Recovery): how an agent improves itself, plugs into
tools through a shared standard, knows what "done" means, and survives things breaking.

**Part 4 — the boundary patterns** (Human-in-the-Loop, Knowledge Retrieval/RAG, Inter-Agent
Communication, Resource-Aware Optimization): the edges — where the agent hands control to a person,
reaches for knowledge it was never trained on, talks to agents it does not own, and meets the budget.

**Part 5 — the judgment patterns** (Reasoning Techniques, Guardrails and Safety, Evaluation and
Monitoring, Prioritization, Exploration and Discovery): the ones separating a demo from something you
would put in front of customers.

It closes with **Putting it all together** — a pattern picker that maps common interview scenarios to
the patterns you'd reach for, and four full mega-scenarios showing how these combine in real answers.
Read that section even if you skip around; composition is what senior interviews actually test.

Every pattern chapter has the same skeleton, and I'd encourage you to use it the same way every time.
First, read **the interview scenario** — two or three realistic phrasings of the question — and then *stop*.
Close the book, set a timer for ten minutes, and try to answer out loud, alone in a room, like a crazy person.
I'm serious about the "out loud" part: interviews are a speaking performance, and the gap between "I understand this" and "I can say this fluently" is enormous.
Only after you've stumbled through your own attempt should you read **the complete interview answer, spoken** — a long model answer written the way a strong candidate would actually talk.
Compare it to what you said.
Notice what you skipped: usually it's failure modes, evaluation, or cost, because those are the parts nobody thinks to practice.
Then drill the **follow-ups**, and before you sleep, recite the **say it in one breath** summary until it's automatic.

If you like structure, here's a one-week plan that has worked for people I've coached.
Days one and two: read the vocabulary section and the answer skeleton, then read Prompt Chaining and do the aloud-attempt ritual — chaining is the foundation everything else builds on, so give it two days.
Day three: Routing, same ritual, and afterward practice explaining out loud how a router and a chain compose, because that composition is the most common two-pattern question in the wild.
Day four: Parallelization, and as a drill, take your day-two chaining answer and find the steps in it that could have run concurrently — retrofitting parallelism onto your own design is exactly the move interviews reward.
Day five: Reflection, then the Part 1 wrap-up, then the four one-breath summaries recited cold.
Days six and seven: mock interviews — grab a friend or record yourself, pull one scenario from each chapter *at random*, and answer for fifteen minutes using only the skeleton; review the recording against the model answers and be honest about which of the seven moves you skipped.
The recording step feels excruciating and is worth more than everything else combined.

One more thing before we start.
This playbook assumes you know how to *use* an LLM — you've written prompts, you've called an API — but it does not assume you know production-systems vocabulary.
Words like "idempotent" and "p95 latency" get thrown around in interviews as if everyone was born knowing them.
Nobody was.
So before the patterns, we're going to spend a few pages building your vocabulary, conversationally, the way a colleague would explain it over coffee.
Do not skip this section.
Half of sounding senior in an interview is using these words correctly and casually, and the other half is quietly knowing what they mean when the interviewer uses them first.

**Where this material comes from.** The pattern catalog is Antonio Gulli's *Agentic Design Patterns:
A Hands-On Guide to Building Intelligent Systems* — a copy lives alongside this playbook in this
folder, and it is worth reading properly for the code examples and framework detail this companion
deliberately leaves out. If you prefer to start by listening, there is a well-made hour-long video
summary of the same catalog at <https://www.youtube.com/watch?v=e2zIr_2JMbE>; the appendix at the end
of this playbook maps its timestamps to these chapters so you can watch and read in step. Everything
here — the scenarios, the spoken answers, the diagrams, the failure-mode walkthroughs — is written
fresh for interview practice rather than lifted from either source.
