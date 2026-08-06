# Part 1 self-quiz: the answer key

Use this *after* you've tried each question out loud, not before — reading answers you haven't struggled for feels productive and teaches you almost nothing.
The goal here is fluency, not word-matching: if your phrasing is different but you hit the same substance, that counts as a win, so grade yourself generously on wording and strictly on whether you actually named the thing.
Where I've added a "red flag" line, it's because that particular wrong answer is common enough that I've heard it in real interviews.

---

### 1. What are the five beats of the loop that makes a system an agent rather than a model?

**The short answer, as you'd say it:** Get the mission, gather information, think through a plan, act, and learn from what happened.
If a system does all five, it's an agent; if it only answers from what it already knows, it's just a model.

**Why this is the answer:** This is the five-beat loop Gulli's book opens with, and it's the cleanest definition you can carry into a warm-up question.
The load-bearing beat is *act* — a chatbot answers questions, but an agent does things: searches the web, updates a calendar, files a ticket, writes and runs code.
The other beats matter because they're what makes the acting non-random: a mission gives it a target, gathering gives it grounding, planning gives it sequence, and learning is what closes the loop so the next iteration is informed by the last.
The playbook pairs this with a four-rung ladder you can offer as a follow-on — Level 0 the bare model, Level 1 the tool user, Level 2 the strategic planner doing multi-step work with deliberate context engineering, Level 3 a coordinated team of specialist agents.

**Red flag if you said:** "An agent is an LLM with tools." That's Level 1 only, and it skips the loop entirely — an agent isn't defined by having tools attached, it's defined by *iterating* toward a goal: perceive, plan, act, observe the result, adjust.
Interviewers use this question as a cheap seniority filter, so give them the loop, not the feature list.

---

### 2. Name the four ways a single monolithic prompt fails, by name.

**The short answer, as you'd say it:** Instruction neglect, contextual drift, error propagation, and plain old hallucination.

**Why this is the answer:** These four are worth memorizing *by name* because they're free interview vocabulary — saying "instruction neglect" instead of "it forgets stuff" signals that you've read the literature rather than just noticed the symptom.
Instruction neglect is when you give a model six instructions in one prompt and it quietly drops one or two: it summarizes beautifully and simply forgets you asked for an email at the end.
Contextual drift is the model losing the thread of the original ask over a long generation.
Error propagation is a small early mistake poisoning everything built on top of it.
And hallucination — confidently stating something false — gets *more* likely as the cognitive load of a prompt goes up, which is the important nuance: it isn't a fixed background rate, it's a function of how much you're asking at once.
Chaining attacks all four at once, because each prompt carries one instruction, each step is short enough that there's no thread to lose, and the seams between steps let you catch errors before they compound.

**Red flag if you said:** "It runs out of context window." That's a real constraint but it's a different failure — a monolith fails at *modest* prompt sizes too, long before you hit any token ceiling, because the problem is cognitive load and unverifiability, not capacity.

---

### 3. Why does structured output between chain steps matter more than the prompts themselves?

**The short answer, as you'd say it:** Because a chain is only as reliable as its hand-offs.
If step one gives step two a chatty paragraph, step two has to *interpret* it, and interpretation is where ambiguity and error creep in — but if step one hands over JSON with known fields, my orchestrator can parse it with ordinary code and verify it deterministically before anything downstream sees it.

**Why this is the answer:** This is the single most important engineering decision in the whole pattern, and it's the one candidates skip in favor of talking about prompt wording.
Structured output means forcing each step to answer in a machine-readable format — almost always JSON, a text format of named fields and values like `{"vendor": "Acme", "total": 1050}` — and the list of fields you expect with their types is the *schema*, a contract between the two steps.
Parsing that text with ordinary code is the beautiful part: it either works or it visibly fails, which gives you a free, deterministic checkpoint after every model call.
That's the difference between components that *hand off data* and components that merely *hope the next one understood*.
And notice what the state of your pipeline becomes: not vibes, but a growing, validated bundle of structured data flowing down the line.

**Red flag if you said:** "JSON is just easier to work with in code." True but shallow — the point isn't developer convenience, it's that a parse is a *verification event*.
You get a deterministic pass/fail on a probabilistic component's output for free, which is the only way to stop errors at the seam where they were born.

---

### 4. Five chained steps at 95% accuracy each — roughly what end-to-end accuracy, and what's the fix?

**The short answer, as you'd say it:** About 77% — that's \\( 0.95^5 \\approx 0.77 \\), 0.95 multiplied by itself five times.
The fix is validating at every seam so errors get caught where they're born instead of compounding, and escalating ambiguity instead of guessing.

**Why this is the answer:** This is error compounding, the chain's signature disease, and the arithmetic is what makes it visceral.
Each step looks great in isolation — 95% is a number you'd happily report — but errors multiply down the line, so five polite little steps land you around 77% end-to-end, which is not a system anyone trusts with money.
The playbook's refund example runs the same math at four stages and gets roughly 81%.
The cure is structural, not prompt-level: parse and validate the structured output at every seam, cross-check against ground truth wherever it exists (in the refund example the order database is the anchor of reality), have each step report per-field confidence so low confidence escalates rather than proceeds, and keep per-stage eval metrics so you know *which* stage is drifting and fix the source rather than the symptom.

**Red flag if you said:** "So don't chain — use one prompt." Backwards.
The monolith has the *same* underlying error rate with none of the visibility, so you get the bad accuracy and no ability to find out where it came from.
The chain's compounding is at least *diagnosable*, and validation at the seams is what converts diagnosable into fixable.

---

### 5. What belongs at the seams of a chain besides the next LLM call?

**The short answer, as you'd say it:** Ordinary deterministic code — parse and validate the JSON, look things up in a real database, call a tool like a calculator, branch on a condition, run a hard guardrail, checkpoint the state, or hand off to a human.
The seams are where the non-AI half of the system lives, and they're the whole reason to chain in the first place.

**Why this is the answer:** This is the pattern's superpower and candidates consistently under-sell it.
A chain isn't LLM–LLM–LLM; it's LLM, *check*, code, LLM, *tool*, *check*, LLM.
The invoice example makes it concrete: the model extracts text, a second step normalizes "one thousand and fifty" into 1050, and then — because LLMs are famously unreliable at arithmetic — the actual math gets delegated to a calculator tool, with the model only deciding *what* to compute.
The refund example adds a hard guardrail in plain code: the amount must not exceed the order total, and anything above a policy threshold routes to human approval no matter how confident the model is.
Also at the seams: checkpointing each validated step's output so a crash at step four resumes from step three, and the pause point where a human approval task gets filed and the chain simply stops until the answer lands.
The unifying principle from the vocabulary section is worth saying out loud — creativity and language on the probabilistic side, verification and consequences on the deterministic side.

**Red flag if you said:** "A validation LLM call." Sometimes fine, but reaching for a model to check a model when plain code could do it is the expensive, less reliable choice.
If the check is mechanical — does it parse, are required fields present, is the total a number, is the amount under the cap — that's an if-statement, and an if-statement can't hallucinate.

---

### 6. A step returns broken JSON — walk the recovery in one sentence.

**The short answer, as you'd say it:** The parser fails, my orchestrator catches it immediately so the garbage never reaches the next step, I retry that one step with the parse error appended to the prompt so the model can self-correct, and after two strikes the request escalates to a human with the full trace attached.

**Why this is the answer:** Notice the four moves packed in there: catch at the seam, contain the blast radius, retry with the error included, and have a bounded give-up.
Including the parser's actual error message in the retry prompt is the detail that earns points — you're not just re-rolling the dice, you're giving the model the information it needs to fix itself, and that fixes the vast majority of cases.
Retrying only *that step* rather than the whole chain matters too, because re-running upstream steps costs money and can re-trigger side effects.
And the cap is what stops an infinite loop: two strikes and a person gets it, with the trace so they can see what actually happened.
The principle to state out loud is the one the playbook gives you: fail loudly at the seam where the error was born, never let it compound downstream.

**Red flag if you said:** "Wrap it in a try/except and skip the step." Silently continuing with a hole in your state is how a chain produces confidently wrong output.
Skipping is only acceptable if you've decided in advance that the field is optional and you label the gap.

---

### 7. What are the four router implementations, and which needs no training data?

**The short answer, as you'd say it:** Rules in plain code, embedding similarity, a trained classifier, and an LLM prompt.
The LLM router is the one that needs zero training data and ships on day one — rules need no data either, but they need you to hand-write the patterns, and embeddings need only a description of each route.

**Why this is the answer:** Get the tradeoffs on the tip of your tongue, because this comparison is the single most likely probe in a routing interview.
Rules are instant and free and perfectly deterministic — same input, same path, forever — but brittle, because real users phrase things sideways.
LLM routing ("classify this request as booking, refund, baggage, or other; answer with the single word only") is maximally flexible, handles novel phrasing effortlessly, and needs no data at all — but every decision now costs a model call's latency and money, and the model can get creative with its answer, so you must validate its output against the allowed label set and treat anything else as `unclear`.
Embedding routing converts the request into a list of numbers capturing its meaning and picks the nearest route reference — semantic matching without a full model call, so faster and cheaper than LLM routing and smarter than rules, though you get a similarity score rather than reasoning.
A trained classifier takes a few thousand labeled examples and is fast, cheap, and consistent at runtime, with the price being labeling effort and a retraining loop whenever categories shift — and there's a lovely trick worth quoting: use an LLM *offline* to generate synthetic training examples, so the expensive model does the heavy lifting once at training time instead of on every request.

**Red flag if you said:** Only "LLM or rules." Missing embeddings and the trained classifier costs you the whole middle of the tradeoff space, and the classifier in particular is the answer to "this is fine but it's too slow and expensive at our volume."

---

### 8. Why must `unclear` be a first-class route rather than an error?

**The short answer, as you'd say it:** Because if you force the router to pick from only the real categories, it will — confidently and wrongly — and a specialist prompted for baggage will do something confidently useless with a refund request.
An explicit `unclear` route turns doubt into a clarifying question or a warm handoff to a human, which is a good outcome instead of a bad one.

**Why this is the answer:** This is the discriminating detail in a routing interview.
Candidates who have an `unclear` route and a confidence policy read as people who've watched a router be wrong in production; candidates who don't, don't.
Two more reasons to give it real status.
First, it's where your confidence threshold cashes out: below the threshold you clarify rather than guess, and the threshold itself should be set per route from the cost asymmetry — for money-touching routes sit conservative and clarify maybe 10% of the time, for flight status be aggressive because a wrong guess is trivially corrected.
One global number is a smell, because it pretends all mistakes cost the same.
Second, and this is the line to steal: the `unclear` pile is literally your product roadmap telling you which new route to build next.
Review it weekly, and when a new cluster shows up, that's your signal to build route number six — which is also your defense against category drift, the slow failure where the router's January worldview stops matching June's users.

**Red flag if you said:** "The router just picks the closest match." That's exactly the failure mode.
A forced choice among wrong options produces a confidently wrong path, and the user gets a fluent answer to a question they didn't ask.

---

### 9. What's the pragmatic router lifecycle from day one to month three?

**The short answer, as you'd say it:** Day one, an LLM router — zero data needed, ships in an hour, great with messy phrasing — and you log every single decision.
By month two or three those logs are tens of thousands of labeled examples, so you graduate the high-volume head of the distribution to a small trained classifier for speed and cost, add cheap rules to short-circuit the dead-giveaway cases, and keep the LLM as the fallback tier for the weird stuff.

**Why this is the answer:** When an interviewer says "LLM router, embeddings, rules, or a trained classifier — pick one and defend it," the strong move is to gently refuse the premise: it's a lifecycle, not a pick.
The logic is that your constraint on day one is *data*, and your constraint at scale is *cost and latency* — different constraints, different right answers, and the logging is the bridge between them.
At tens of thousands of chats a day, shaving a few hundred milliseconds and most of the routing cost off every single request is real money and real snappiness.
The mental model to say out loud is the funnel: rules, then classifier, then LLM — cheapest adequate decider wins, with the LLM as the safety net.
And if they pin you down and force exactly one forever at high volume, take the trained classifier and pay the labeling cost.

**Red flag if you said:** "Start with the trained classifier, it's the best one." You don't have labels on day one, and you don't yet know what the real categories are — the traffic will teach you, and building a classifier before the traffic speaks means retraining it as soon as you learn anything.

---

### 10. A message contains two intents — what's your policy?

**The short answer, as you'd say it:** Have one, decided in advance.
Mine is: the router flags multi-intent, the system handles the primary intent — the one with urgency or money attached — and then explicitly says "I see you also asked about X, want me to do that next?" Users forgive sequencing; they don't forgive being half-ignored.

**Why this is the answer:** "Cancel my flight and also, where's my bag?" is legitimately two categories, and there are three defensible policies: split it into two requests, handle the primary and acknowledge the secondary, or ask the user to pick.
Any of them is fine.
What is *not* fine is having no policy, because then behavior varies by whatever the classifier happened to latch onto that day.
Acknowledged sequencing is the simplest and users respond well to it; splitting into two parallel handler runs is also viable and worth considering once the basics are solid.
The unacceptable option — and this is the one to name explicitly, because naming it shows you know what you're avoiding — is silently answering half the message, because the user has no way to tell whether the other half was refused, forgotten, or misunderstood.

**Red flag if you said:** "Route to whichever intent scores higher." That's a mechanism, not a policy — it says nothing about what happens to the second intent, which is the entire question.

---

### 11. What single property makes two steps safe to parallelize, and what bug appears when you violate it?

**The short answer, as you'd say it:** Independence — and it has two halves: no data dependency, meaning neither step consumes the other's output, and no write conflict, meaning they don't mutate the same state or external resource while running.
Violate the second half and you get race conditions: results that depend on which branch happened to finish first.

**Why this is the answer:** Say the word "independence" explicitly in every parallelization interview — it's the entry ticket, and if step B genuinely needs step A's output, they cannot run together, full stop; a dependency is a wall.
The design skill this tests is dependency analysis: sketch the steps, draw an arrow for every "needs the output of," and everything not connected by arrows is fair game.
Race conditions deserve their own beat because they're the worst bugs to chase — they appear and vanish randomly and they don't reproduce reliably in tests, which is why you prevent them *by construction* rather than trying to catch them afterward.
The discipline is three words long: shared read-only input, each branch owns an exclusive output slot, and only the gather step combines.
That's the cubbyhole model — in the ADK example each researcher sub-agent writes to its own dedicated key in session state and the merger reads all the cubbyholes afterward.

**Red flag if you said:** "Just make sure they don't depend on each other." Half credit — that's the data-dependency half.
The write-conflict half is where the genuinely nasty bugs live, and it's the half that separates people who've read about concurrency from people who've been paged by it.

---

### 12. Fan-out, fan-in, straggler — define all three in one breath.

**The short answer, as you'd say it:** Fan-out is the moment the orchestrator splits one step into many concurrent branches; fan-in — the gather — is where you collect all their results back together; and the straggler is the one slow branch that holds the whole gather hostage, because your parallel block is only ever as fast as its slowest member.

**Why this is the answer:** These three are the vocabulary that makes you sound fluent, and the straggler is where the real engineering insight sits.
Parallelization trades "the sum of all steps" for "the worst step" — a huge improvement that can still be ruined by one slow API.
So the mitigations are per-branch timeouts, plus a *partial-results policy decided in advance*: for a research briefing, four of five sources with a visible note about the missing one beats an error page; for something like a payment-verification fan-out, no — all checks must pass.
Say which one your product is and why.
And watch per-branch p95 latency in production so a chronically slow source gets fixed or replaced rather than silently dragging every request.

---

### 13. Why doesn't parallelization save money?

**The short answer, as you'd say it:** Because it's the same calls, just rearranged in time.
Latency drops, the bill doesn't.
It can even raise costs indirectly, because it makes it painless to do more — you'll fan out ten speculative lookups where a sequential design would have done three carefully.

**Why this is the answer:** Saying this crisply is worth points, because it's a place where people's intuition quietly assumes "faster equals cheaper." If cost is the actual pressure, the levers are elsewhere: fewer or smaller calls, caching, or a router that skips work entirely.
Parallelization buys exactly one thing — time.
The nice follow-through, straight from the due-diligence answer, is caching: briefings repeat, so if three analysts pull the same company this week, the second and third should hit a per-branch cache with freshness windows matched to how fast each source moves — financials until the API's next update, news for an hour or two, leadership basically until it changes.
A cache hit skips the branch entirely, which improves latency *and* cost, which is the combination parallelization alone can't deliver.

**Red flag if you said:** "It's more efficient, so it's cheaper." Efficiency of *wall-clock time* isn't efficiency of *tokens*.
The provider bills you per token regardless of whether the calls were in a row or side by side.

---

### 14. What three protections does every fan-out need before production?

**The short answer, as you'd say it:** Per-branch timeouts, a partial-results policy decided at design time, and a concurrency cap with a queue.
Those three are what stand between a working demo and a fan-out that survives stragglers, partial failures, and rate limits.

**Why this is the answer:** Each maps to a named failure mode.
Per-branch timeouts answer the straggler — one slow API can't hold the gather hostage indefinitely.
The partial-results policy answers partial failure: one branch errors while four succeed, and you need to have decided *in advance* whether a labeled partial ships or the request fails, because that's a product decision, not an engineering one.
The mechanics that go with it are retrying the failed branch *alone* — cheap and safe when branches are read-only against the world — rather than re-running the whole fan-out because one branch hiccuped.
And the concurrency cap answers rate-limit collisions: fan out fifty model calls at once and the provider's per-minute cap slams the door, failing calls that would have succeeded politely spaced out.
A governor keeps at most N calls in flight, with backoff on throttle errors and priority in the queue so live users go ahead of batch jobs.
The insight to voice: beyond the cap, more concurrency adds zero speed, because the provider has become the bottleneck — you're just converting polite queueing into errors.

**Red flag if you said:** Only "retries." Retrying into a rate limit makes it worse, and retrying a straggler that's merely slow rather than broken doubles your load for nothing.
If you want a fourth protection to mention, make it the logging discipline: a shared request ID plus a branch label on every log line, because five interleaved branches produce five interleaved log streams and debugging fog is a real tax you should budget for rather than discover.

---

### 15. What's the difference between concurrency and parallelism, and why is it fine for I/O-bound agents?

**The short answer, as you'd say it:** Parallelism is genuinely doing several things at the same instant on different cores; concurrency is one worker juggling many waiting tasks, switching to another whenever one is idle on the network.
In Python this is usually concurrency, not true parallelism — and that's exactly what you want for agent work, because the bottleneck is waiting, not computing.

**Why this is the answer:** This is a precision point that costs you nothing and buys real credibility.
Agentic systems spend most of their lives waiting on the outside world — APIs, searches, database queries — and during a three-second API wait your system is doing *nothing*; it may as well have five other requests in flight.
That's I/O-bound work, and a single async worker handles it beautifully because there's no CPU contention to speak of.
It's also why the framework story lines up: LangChain's RunnableParallel takes a map of named chains and runs them concurrently, and under the hood it's async I/O — one worker juggling waiting tasks, which is the right model since the branches are network-bound.

**Red flag if you said:** "Same thing." They aren't, and the distinction is precisely what makes the design sound: if your branches were CPU-heavy, one async worker would buy you nothing and you'd need real parallelism.
The reason you can be relaxed about it is a fact about *your* workload, and stating that fact is the point.

---

### 16. Why does a separate critic outperform "double-check your own work"?

**The short answer, as you'd say it:** Because it avoids the cognitive bias of an agent grading its own homework.
A producer asked to check itself tends to conclude its work is fine; a critic prompted as "you are a meticulous senior reviewer, your job is to find flaws" is *rewarded* for finding problems, so it finds them.

**Why this is the answer:** The generator-critic split is the heart of the pattern.
They can literally be the same underlying LLM wearing two different system prompts — same model is fine, different instructions are the point — and the separation still works for two reasons.
First, framing: the critic's instructions reward finding flaws, and it reads the draft without the generation context that would bias it toward defending choices it made.
Second, and this is the sharper argument, the asymmetry of the two jobs: generation is open-ended while review against a rubric is constrained, and models are better reviewers than generators of the same content.
You strengthen it further by grounding the critique in objective signals the model can't sweet-talk — run the tests, execute the query, validate the schema — and optionally by using a different model family as critic for genuinely independent eyes.
The playbook is blunt that "the model double-checks itself" is the pattern's cardinal sin: a self-graded exam with the same blind spots on both sides of the desk.

**Red flag if you said:** "Add 'please verify your answer' to the prompt." That's the exact anti-pattern.
It costs you tokens, produces a confident "yes, that looks right," and catches approximately the errors the model was already capable of noticing — which is to say, not the ones you're worried about.

---

### 17. Rank the critic types from most to least trustworthy.

**The short answer, as you'd say it:** Execution and tests first — run the code, run the SQL on a replica; reality doesn't negotiate.
Then deterministic checks: schema validation, length limits, banned-terms scans, which are ground truth for whatever they happen to cover.
Then an LLM with a rubric, which is good but foolable.
Then human review, which is the best judgment available but expensive, slow, and doesn't scale.

**Why this is the answer:** The ranking is really about *objectivity per dollar*, which is why human review sits at the bottom of the practical stack despite having the best judgment — it's rarely fooled but it can't be your default layer.
The design instinct that follows is the important part: stack them, cheapest and most objective first, and only let the expensive subjective layers see work that survived the mechanical ones.
The SQL example shows it in three layers — execute against a read-only replica to catch syntax errors and missing columns for free, then mechanical sanity checks in plain code (did it return zero rows for a question that plainly expects data, did a join explode the row count), then the LLM critic which crucially gets to see the *execution results*, not just the SQL.
A reviewer who can see what the query actually did catches semantic wrongness — right syntax, wrong meaning — far better than one reading code cold.
Two caveats to keep in your pocket: deterministic checks only cover what you wrote, and an LLM critic must be calibrated on planted defects, because otherwise you can't tell a clean pass rate from a lenient one.

**Red flag if you said:** "LLM-as-judge is the most reliable because it's the smartest." Smart isn't the axis — foolability is.
An LLM critic has the same probabilistic nature as the producer, which is why you put un-foolable checks in front of it and reserve it for what genuinely can't be checked mechanically.

---

### 18. Name the three exits every reflection loop needs.

**The short answer, as you'd say it:** The happy exit — the critic passes the work; the budget exit — a hard cap of two or three iterations; and the stall exit — if the critique isn't changing or the drafts aren't improving between laps, stop, because the loop is orbiting rather than converging.

**Why this is the answer:** A loop with only the happy exit is a bug, plain and simple: a too-picky critic against a maxed-out producer will spin forever, and you'll find out via the bill.
The budget exit is set empirically — your eval set gives you quality-per-lap curves and they're always steeply diminishing, so lap one captures most of the gain and lap three is polishing marginalia; the cap belongs where marginal quality drops below marginal cost.
The stall exit catches the subtler disease, oscillation: the producer "fixes" issue A by reintroducing issue B, and the laps alternate forever between two flawed versions.
In the SQL design, the stall check is concrete — if the same critique repeats twice, stop early.
And there's a fourth thing to say that isn't an exit but completes the answer: on exhaustion, don't ship the output as if it were fine.
The user gets the best draft explicitly flagged "unverified — review before trusting," with the critic's outstanding concerns attached.
Honest failure preserves the trust that silent failure would spend.

**Red flag if you said:** "Loop until the critic is satisfied." That's the happy exit alone, and it's the classic way to build something that hangs in production and looks fine in every test where the critic happened to be agreeable.

---

### 19. When do you choose best-of-N over a reflection loop?

**The short answer, as you'd say it:** When the failures are *random* — flaky phrasing, an occasionally weak draft — because five independent rolls of the dice probably include a good one, and best-of-N is fast: all five drafts arrive in one round-trip, a judge picks, done, with no loop latency.
Reflection wins when failures are *systematic*, because if the model reliably misses the same edge case, all five candidates share the flaw and no amount of picking fixes what only feedback can.

**Why this is the answer:** The underlying insight is worth stating in exactly these terms: the critique *injects information the producer didn't have*, which resampling never does.
Best-of-N is parallelization applied to quality — the same fan-out machinery, aimed at a quality goal rather than a speed goal — so it costs N generations plus a judge but only one round-trip of latency.
Reflection costs at least two calls per lap and stacks latency serially, but it can actually teach the producer something mid-flight.
And they compose beautifully, which is the senior move to name unprompted: generate three candidates in parallel, have the critic pick the strongest *and* critique it, then run one revision lap on the winner — roughly the quality of three reflection laps at the latency of one.
In the room, naming that hybrid along with the diagnosis that picks between them — random flaws versus systematic ones — is a genuinely strong answer.

---

### 20. What's the one metric that proves a reflection loop is earning its cost?

**The short answer, as you'd say it:** The delta between first-draft pass rate and post-reflection pass rate on your eval set.
If that gap is small, the loop isn't earning its cost and I should ship single-pass with just the objective checks.

**Why this is the answer:** This is the metric because reflection is the one pattern whose entire justification is a quality improvement you're paying real money and latency for — every lap is at least two more LLM calls, so a three-iteration loop can multiply a step's cost and latency several-fold.
The delta is the only number that tells you whether that multiplier bought anything.
It's also honest in a way most metrics aren't: it will sometimes tell you to delete the feature you just built, and being willing to say that out loud in an interview reads as maturity.
Around it, the supporting instrumentation is worth listing quickly — laps per request (creeping up means an unappeasable critic), pass rate per lap, unverified-output rate, p95 latency, cost per request, and the metric that actually matters in production, user corrections: when someone edits or disputes a shipped output, that's a missed defect logged against the critic, and it feeds back into the planted-bugs suite so the critic learns your org's real failure patterns.

**Red flag if you said:** "The critic's pass rate." A pass rate near 100% is at least as likely to mean a lenient critic as a good producer — in fact a suspiciously high pass rate combined with users still finding errors is the *diagnostic signature* of the lenient-critic failure mode.

---

### 21. Recite the seven moves of the universal answer skeleton.

**The short answer, as you'd say it:** Clarify the requirements.
State the simplest thing that could work.
Name the pattern and say why.
Draw the boxes and walk the data flow.
Call out the failure modes before the interviewer does.
Explain how you'd evaluate and monitor it.
Mention cost, and what you'd cut under pressure.

**Why this is the answer:** Learn the skeleton once and you never face a blank whiteboard again — you face a fill-in-the-blanks exercise.
It helps to know what each move is *scoring*, because that changes how you play.
Clarifying scores seniority: junior engineers solve the problem they imagined, senior engineers solve the problem that exists, and asking buys you two minutes of thinking time while looking proactive.
The baseline scores resistance to over-engineering, and it sets up a narrative where everything you add afterward is justified by a specific failure of the simple version.
Naming the pattern scores pattern recognition — just make sure the *because* clause is there, or it's buzzword bingo.
Boxes and data flow score decomposition, and the credit lives in the arrow labels: what data moves, not just that something moves.
Failure modes are the highest-leverage move in the whole skeleton, because every interviewer keeps a private list of holes in your design and every hole you name first transfers from their column to yours.
Eval and monitoring is the single most common gap between people who've shipped LLM systems and people who've only played with them.
And cost plus cuts signals business maturity and judgment — knowing which parts of your own design are load-bearing and which are polish.
The final instruction matters as much as the list: don't recite it like a checklist, *inhabit* it, so the moves come out as one flowing story.

---

### 22. What are the four ways candidates most commonly lose points?

**The short answer, as you'd say it:** Diving straight into architecture without clarifying; complexity worship; the happy-path-only answer; and no numbers anywhere.

**Why this is the answer:** Avoiding a mistake is cheaper than earning a merit, which is why these four are worth memorizing as a list.
Diving in without clarifying is the single most frequent error and it can sink an otherwise brilliant answer, because the interviewer sits there watching you confidently build the wrong thing.
Complexity worship — five agents, three loops, and a vector database for a problem one well-validated chain would solve — gets read not as sophistication but as inexperience, because people who've carried a pager know every component is a thing that breaks at 2 a.m. The happy-path-only answer, narrated as if models never return garbage, APIs never time out, and users never type nonsense, is close to disqualifying with LLM systems specifically, because the components are *guaranteed* to misbehave some percent of the time.
And no numbers anywhere: you don't need precision, but an answer with zero estimates of latency, volume, or cost floats free of reality, and interviewers notice the weightlessness.

**Red flag if you said:** "Not knowing the patterns." Honestly the rarest failure of the four.
People lose these interviews on process and judgment far more often than on knowledge, which is good news, because process is the part you can fix this week.

---

### 23. Compose all four patterns into one sentence describing a production support system.

**The short answer, as you'd say it:** A router at the front door labels each incoming message and sends it to a specialist chain, that chain fans out into independent lookups in parallel wherever nobody's output feeds anyone else's, and a reflection loop wraps the one step whose mistakes are expensive — with an honest `unclear` lane to a human behind all of it.

**Why this is the answer:** That composite — fork, then road, then wide road, then U-turn — is, in one diagram, most production agentic systems in the wild today, and the book's own examples keep converging on it.
The sorting routine that produces it is worth being able to speak, because interviewers push you across pattern borders and this is how you navigate.
First: does every request need the same steps?
If yes it's a chain and your energy goes into the seams; if no, a router goes in front with each kind behind its own door.
Second: inside whatever path a request takes, which steps actually depend on each other?
Draw the needs-the-output-of arrows, and everything unconnected is a candidate to fan out — though whether you bother depends entirely on whether anyone feels the wait.
Third: where does a mistake actually hurt?
That's where a reflection loop earns its cost, guarded by the most objective critic you can build and a lap budget, while everything else ships single-pass.
And the closing discipline: justify each piece by a requirement, because the difference between architecture and decoration is a reason.

**Red flag if you said:** A sentence with all four patterns in it and no *reasons*.
Composition isn't a checklist of names — every element needs a "because" tied to something in the requirements, or you've decorated rather than designed.

---

### 24. For each pattern: what does it buy, and what does it cost?

**The short answer, as you'd say it:** Chaining buys reliability and debuggability and costs stacked latency; routing buys specialist quality and costs a decision tax on every request; parallelization buys latency collapse and costs concurrency complexity — notably not money, which it neither saves nor spends; and reflection buys error-catching before shipping and costs multiplied cost and latency.

**Why this is the answer:** This is the card to redraw from memory the morning of the interview.

| Pattern | One-line trigger | What it buys | What it costs | Signature failure |
|---|---|---|---|---|
| Prompt Chaining | Distinct stages, each feeding the next | Reliability, debuggability, tool seams | Stacked latency, more parts | Error compounding across steps |
| Routing | Different kinds of requests, one front door | Specialist quality per category | A decision tax on every request | Misrouting; category drift |
| Parallelization | Independent steps, someone waiting | Latency collapse to the slowest branch | Concurrency complexity, debugging fog | Stragglers; rate-limit collisions |
| Reflection | Quality bar higher than a first draft | Error catching before shipping | Multiplied cost and latency | Lenient critic; endless loop |

The reason this table is the last thing in Part 1 rather than the first is that the *costs* column is what separates candidates.
Anyone can list what a pattern is good for; naming the price unprompted — the latency the chain stacked, the tax the router charges every single request, the money parallelism didn't save, the multiplier reflection put on the bill — is what marks you as someone who can be trusted to run these things rather than merely someone who read about them.
So when you finish an answer, say the costs out loud without being asked.
And when you're stuck mid-answer, return to dependencies and stakes: "what needs what" chooses between chain and parallel, "what varies" chooses whether routing exists, and "what's expensive to get wrong" chooses where reflection lives.

---

## What to do with your score

Twenty or more answered fluently and you're interview-ready on these four patterns — spend your remaining time on mock interviews rather than rereading, because at this point the bottleneck is your mouth, not your understanding.
Fifteen to nineteen means solid foundations with specific gaps, and the thing to notice is *which* patterns your misses cluster in: a cluster means reread that chapter, while scattered misses just mean redo the quiz tomorrow after some sleep.
Below fifteen is no shame at all, but don't move on to Part 2 yet — the later patterns assume these four are automatic, and shaky foundations compound exactly the way chain errors do.

And whatever you scored, retake this quiz forty-eight hours from now.
The answers you had to *reconstruct* rather than *recall* are precisely the ones that will desert you under interview pressure, and two spaced repetitions is usually what it takes to pin them down for good.
