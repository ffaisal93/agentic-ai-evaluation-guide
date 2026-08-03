# Benchmark Datasets for Agent Evaluation

> **Why this matters.** Your evaluation is only as good as its data. You can build the most careful harness, the most rigorous metrics, and the most beautiful dashboards — and if the underlying tasks are ambiguous, mislabeled, too easy, or already sitting in your model's pretraining corpus, every number you report is fiction. This chapter is deliberately *not* about metrics (that is Chapter 3). It is about the **data**: how to use standard benchmarks without fooling yourself, how to build a custom benchmark for your own agent and domain, how to prove the dataset is actually good (coverage, calibration, label correctness, inter-annotator agreement), how to keep it out of the training set, when synthetic data helps and when it lies, and how to version, license, and document what you ship. By the end you should be able to (a) *build and validate* an agent eval dataset end to end with runnable code; (b) *reason about* the failure modes that silently inflate benchmark scores; and (c) *convince a senior interviewer* that you understand data quality at the level the 2025–2026 frontier demands.

> **How to read this chapter.** Sections 1–2 build intuition and anatomy. The **2025–2026 landscape** section (right after) is the "what does the field actually do today" briefing — read it before an interview. Sections 3–9 are the mechanics: using standard benchmarks, building your own, measuring agreement, fighting contamination, synthetic data, worked code, and documentation. The **Build it in practice** toolkit gives you a runnable dataset-QA harness. **Production case studies & war stories** shows what goes wrong at scale. **Interview mastery** is the drill sheet. Everything is cross-referenced so you can jump.

---

## 1. Core intuition: the dataset is the ruler

A benchmark dataset is a **measuring instrument**. When you report "our agent scores 71%," you are reading a number off a ruler. If the ruler's tick marks are unevenly spaced (difficulty not calibrated), some marks are in the wrong place (bad labels), or the ruler has been photographed and memorized by the thing you are measuring (contamination), the reading is meaningless — no matter how precisely you read it.

The metric is the *reading device*; the dataset is the *ruler itself*. Chapter 3 sharpens the reading device (pass@k, confidence intervals, judge calibration). This chapter makes sure the ruler is straight. The two failures are independent: a perfectly calibrated metric on a contaminated dataset produces a confidently wrong number, and that is worse than an honestly noisy one, because it *looks* trustworthy.

Three intuitions carry the whole chapter:

1. **Garbage tasks beat good models.** A single ambiguous task with a wrong golden answer can flip a leaderboard ranking. SWE-bench's original test set had tasks where the hidden unit tests rejected *correct* patches; OpenAI found this affected a majority of samples (§2.2, §4). If your data is noisy, you are ranking noise. This is not a metaphor: Northcutt et al. showed that correcting a 6% label-error slice in ImageNet is enough to flip the ResNet-50-beats-ResNet-18 ordering (see Production war stories). The data, not the model, decided the ranking.
2. **A benchmark answers exactly one question, and you must know which.** "Can the agent book a flight?" and "Can the agent book a flight *reliably across 8 tries under an adversarial user*?" are different questions requiring different data. τ-bench exists because the second question needs multi-trial tasks with state-based checks, not single-shot Q&A. Before you touch a dataset, write down the exact sentence it answers. If you cannot, you are not ready to score anything.
3. **Every public benchmark is decaying the moment it is published.** The internet ingests it, the next pretraining run swallows it, and contamination silently inflates scores. A good data strategy plans for this from day one with held-out and canary sets. In 2024–2026 this decay went from a footnote to a first-class design constraint: LiveCodeBench, LiveBench, and GAIA's private split all exist *specifically* to route around it.

A fourth intuition worth internalizing before interviews: **a dataset is a claim about a distribution.** Every task you include is an implicit assertion that "this is the kind of thing our agent will face, and this is what success looks like." When the claim is wrong — because you sampled the easy tail, or invented tasks a real user never asks, or annotated the gold answer by intuition — the benchmark measures a world your agent will never inhabit. Coverage, difficulty calibration, and provenance are all just ways of making that distributional claim honest.

---

## 2. Anatomy of a good benchmark dataset

Whether you use one off the shelf or build your own, a benchmark dataset has the same load-bearing parts. If any are missing, be suspicious.

| Component | What it is | Why it matters |
|---|---|---|
| **Task instances** | The individual problems the agent must solve (a GitHub issue, a customer request, a web goal) | These *are* the benchmark; everything else supports them |
| **Ground truth** | The correct answer, final state, or reference trajectory | Determines what "success" means; the #1 source of silent error |
| **Verifier / scorer** | The mechanism that decides pass/fail (unit tests, state diff, exact match, LLM judge) | A benchmark is task + verifier; a task with no reliable verifier is not a benchmark |
| **Difficulty spread** | A range from easy to hard, ideally with labeled tiers | Flat difficulty gives no signal; you need discrimination across systems |
| **Metadata** | Per-task tags: domain, tools required, length, source, license, creation date | Enables slicing, contamination checks, and honest reporting |
| **Splits** | Public/dev vs. held-out/private vs. canary | Lets you develop without overfitting and detect leakage |
| **Datasheet** | Human-readable documentation of provenance, collection, and intended use | The difference between a dataset and a pile of JSON |

The single most useful reframe: **a benchmark is not the tasks, it is the pair (tasks, verifier).** Two teams shipping "the same" 500 GitHub issues but with different test harnesses have built two different rulers that will disagree. When you cite a benchmark you are implicitly citing its verifier and its harness; when you build one, the verifier is where most of your engineering — and most of your bugs — will live (§4, Step 3).

### 2.1 What ground truth looks like for agents

For agents, "ground truth" is rarely a single string. It comes in three common shapes:

- **Outcome / state-based** (τ-bench, WebArena): success = the final world state matches an annotated goal state (the DB row was updated, the item is in the cart). Robust to *how* the agent got there. Requires an executable environment.
- **Reference-answer** (GAIA): success = the agent's final answer matches a single unambiguous gold answer under quasi-exact match. Cheap to score, but only works when the answer is short and unique.
- **Reference-trajectory / test-based** (SWE-bench): success = the agent's artifact (a code patch) makes a set of `FAIL_TO_PASS` and `PASS_TO_PASS` tests go green. Verifiable and objective, but only as fair as the tests.

> Rule of thumb: prefer *executable* ground truth (tests, state diffs) over *judged* ground truth (LLM-as-judge, human rubric) whenever the domain allows it. Executable checks do not drift, do not have mood, and cost nothing to re-run.

There is a fourth, increasingly common shape you should be able to name: **rubric / judged ground truth**, where a human rubric or an LLM-as-judge scores an open-ended response (a research report, a chat turn, a design doc). It is unavoidable when the output space is too large for an exact match and there is no executable world to diff — but it is the *most* fragile, because the "ground truth" now lives in a prompt or a rubric that can drift, disagree with itself, and be gamed. When you must use it, pin the judge model version, hold out a human-labeled calibration slice, and report judge–human agreement as its own kappa (Chapter 3 covers judge calibration; this chapter covers the *data* side — the rubric and the calibration set are dataset artifacts you must version). A defensible hierarchy of ground truth, best to worst: **executable state diff > passing tests > exact/normalized answer match > human rubric > single LLM judge with no calibration.** Climb as high as your domain allows.

### 2.2 Case studies: how the majors built their data

**SWE-bench Verified** — the canonical lesson in why data quality dominates. The original SWE-bench scraped real GitHub issues + PRs from popular Python repos and used the PR's tests as the verifier. But OpenAI, working with the SWE-bench authors, had **93 experienced Python developers** manually screen **1,699** randomly sampled instances, producing a filtered set of **500** ("Verified"). They rated two failure modes on a 0–3 severity scale: **underspecified problem statements** (found in ~38% of samples) and **unit tests that would reject a valid solution** (~61%). Each sample was independently annotated by **3 developers**, ensembled by taking the *highest* severity label (conservative — bias toward exclusion). GPT-4o jumped from ~16% on the original set to ~33% on Verified — the same model, a cleaner ruler. ([OpenAI](https://openai.com/index/introducing-swe-bench-verified/), [dataset](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified))

The deeper lesson is *what they measured to earn the label*. They did not just eyeball tasks; they defined an explicit **annotation rubric** (is the issue text sufficient to know what "fixed" means? do the `FAIL_TO_PASS` tests actually encode the issue, or do they over-specify implementation details a valid patch might legitimately differ on?), ran it past multiple annotators, and treated the *dataset construction as the experiment*. That is the posture to copy: your dataset build has a protocol, a rubric, annotators, an agreement number, and an errata process, exactly like a small research paper.

**GAIA** — **466** questions that are "conceptually simple for humans yet challenging for advanced AIs," designed so that **humans score ~92%** while GPT-4 with plugins scored **~15%**. Three difficulty **levels** by the number of steps and tools required: Level 1 (few steps, at most one tool), Level 2 (several steps, multiple tools), Level 3 (long open-ended tool use). Each question has a **single unambiguous answer** graded by quasi-exact match, and 300 answers are held private for the leaderboard. The design philosophy is a deliberate inversion of "make it harder for humans." ([arXiv](https://arxiv.org/abs/2311.12983))

GAIA's authoring discipline is the part interviewers probe: questions were **hand-written by humans**, then each was constrained to have *one* correct, non-gameable, order-invariant answer that a search engine cannot return directly — the authors deliberately avoided questions whose answer is a single web lookup, because those measure retrieval, not assistant capability. The "conceptually simple for humans" criterion is a **validity gate**: if a smart human with a browser cannot solve it in a reasonable time, the task is probably ambiguous or wrong, not "hard." Human ceiling ~92% (not 100%) is itself a signal — it tells you the residual ambiguity in the set and puts a realistic cap on what any agent can score.

**τ-bench** — tasks in **retail** and **airline** domains where a language agent talks to an **LLM-simulated user** while calling domain APIs under written policy. Success is scored by **comparing the final database state to an annotated goal state** — objective, no judge. It introduced **pass^k** (the probability all k independent trials of a task succeed) to measure *reliability*, not just average success; even strong models fell below 25% pass^8 in retail. Task authoring bundles a database schema, an API/tool set, a policy document, and per-task goal states. ([arXiv](https://arxiv.org/abs/2406.12045), [Sierra](https://github.com/sierra-research/tau2-bench))

τ-bench (and its 2025 successor **τ²-bench**, which adds a "dual-control" setting where the user can also act on the environment) shows how to author a *stateful* agent benchmark: you do not write a question and an answer, you write a **world** (schema + seed data), a **contract** (the policy document the agent must obey), a **tool surface** (the APIs), and a **goal predicate** (the DB state that counts as done). Every one of those is a versioned artifact. The user is *simulated by an LLM* so trials are reproducible and cheap, but that introduces a second-order data question the authors had to answer: is the simulated user faithful and consistent enough that the task's difficulty comes from the domain and not from a flaky user? Pinning the user-simulator model and prompt is part of the dataset spec.

**WebArena** — **812** tasks over **self-hostable, reproducible** web apps (a fork of GitLab, a Reddit-like forum, an e-commerce CMS, a wiki). Because the sites are self-hosted and deterministic, evaluation uses **functional correctness** — programmatic checks on the resulting page/DB state or exact information match — rather than screenshots. The reproducible environment *is* the ground truth. ([arXiv](https://arxiv.org/pdf/2307.13854), [repo](https://github.com/web-arena-x/webarena))

WebArena's move — ship the *environment*, not screenshots — is the deepest data idea in agent evals: when the world is deterministic and self-hostable, the world itself becomes the golden reference and you never have to annotate "what the page should look like." The cost is operational (you host a small internet), but the payoff is a verifier that cannot drift and tasks that cannot be solved by memorized text, only by *doing*.

The pattern across all four: **objective, executable verifiers + explicit human quality control + difficulty tiers + a plan for contamination.** Copy that pattern. Notice what they share: none of them trusts a single string label produced by intuition, all of them either execute or exact-match, all of them did explicit human validation, and the strongest ones (GAIA, LiveCodeBench, τ-bench) built contamination resistance into the *distribution* (private answers, time-sliced problems, LLM-simulated users) rather than bolting it on afterward.

---

## 3. The 2025–2026 landscape: how today's agent datasets are actually built and validated

If you walk into a senior interview in 2026 and describe benchmark construction the way papers did in 2021 — scrape, split, publish — you will sound a generation behind. The field has converged on a set of practices in response to three pressures: **frontier models saturate static benchmarks within months**, **contamination is now assumed rather than feared**, and **agents need stateful, executable, multi-trial tasks** that a Q&A pair cannot express. This section is the briefing on what "good" looks like right now.

### 3.1 Human-validation pipelines are now standard, not exceptional

SWE-bench Verified (Aug 2024) made **human validation of a scraped benchmark a mandatory step**, and the field internalized it. The recipe that is now considered table stakes:

1. **Over-sample** the raw source (SWE-bench: 1,699 instances to yield 500).
2. **Write an explicit rubric** with named failure categories and a severity scale (0–3), not a thumbs-up/down.
3. **Triple-annotate** every instance with independent experts.
4. **Ensemble conservatively** — take the *worst* severity across annotators so a single credible objection removes a task.
5. **Report the agreement** and the fraction removed, so downstream users can see how noisy the raw source was.

The number that should stick with you: on the *original* SWE-bench, roughly **38%** of sampled tasks were underspecified and roughly **61%** had tests that could reject a valid patch. Those are not edge cases; that is the *majority* of a widely cited benchmark. The 2025 follow-up "Are 'Solved Issues' in SWE-bench Really Solved Correctly?" pushed further, showing that even *passing* patches are often not genuine fixes — the tests pass but the patch is wrong — which means an executable verifier is necessary but not sufficient. ([SWE-bench Verified — OpenAI](https://openai.com/index/introducing-swe-bench-verified/), [arXiv 2503.15223](https://arxiv.org/html/2503.15223v1))

### 3.2 GAIA and τ-bench: authoring for validity and reliability

The 2023–2025 wave of *agent* benchmarks shifted the authoring center of gravity from "collect and label" to "design a world and a validity gate."

- **GAIA (Meta, arXiv 2311.12983, Nov 2023)** hand-authored 466 questions under a strict validity constraint: **one unambiguous, order-invariant answer that cannot be returned by a single search**, and a human ceiling near 92%. The private-answer split (300 held back) is the contamination defense baked into the release. ([arXiv](https://arxiv.org/abs/2311.12983), [dataset](https://huggingface.co/datasets/gaia-benchmark/GAIA))
- **τ-bench / τ²-bench (Sierra, arXiv 2406.12045, Jun 2024; τ² in 2025)** authored *stateful worlds* — schema, seed DB, policy doc, tool APIs, goal-state predicate — and scored by **database-state equality**, then introduced **pass^k** so the benchmark measures reliability, not just average success. The LLM-simulated user is pinned as part of the spec. ([arXiv](https://arxiv.org/abs/2406.12045), [repo](https://github.com/sierra-research/tau2-bench))

The through-line: modern agent authoring produces **executable artifacts with an explicit validity gate**, not string labels. If your custom benchmark is a spreadsheet of prompts and expected answers, you are building 2021's ruler.

### 3.3 Living / contamination-aware benchmarks

Because static benchmarks decay, the strongest 2024–2026 benchmarks are **living**: they add fresh tasks on a schedule and expose *creation dates* so you can score only post-cutoff items.

- **LiveCodeBench (arXiv 2403.07974, Mar 2024)** continuously collects new competitive-programming problems from LeetCode, AtCoder, and Codeforces **with release timestamps**, so you can evaluate a model *only* on problems published after its training cutoff — a clean, built-in contamination control. It also evaluates *holistically* (self-repair, test output prediction, execution), not just pass@1. ([livecodebench.github.io](https://livecodebench.github.io/), [arXiv](https://arxiv.org/abs/2403.07974))
- **LiveBench (arXiv 2406.19314, 2024, updated through 2025)** releases new questions monthly across math, coding, reasoning, and data, with objective ground-truth scoring and a rolling refresh so saturated categories get replaced. ([github.com/livebench/livebench](https://github.com/livebench/livebench))
- **GSM1k (Scale AI, arXiv 2405.00332, May 2024)** is a one-shot version of the same idea: rebuild a saturated benchmark (GSM8k) from scratch, held private, to measure the *overfitting gap*. It found accuracy drops of up to ~8% on some model families and a Spearman correlation (r² ≈ 0.36) between a model's probability of *generating* GSM8k examples and its GSM8k→GSM1k performance drop — a memorization fingerprint. ([arXiv](https://arxiv.org/abs/2405.00332))

The design principle: **make time a first-class dimension of the dataset.** Timestamped tasks turn "is this contaminated?" from a forensic guess into a slicing operation.

### 3.4 Contamination detection has matured into a toolkit

By 2026 contamination detection is a named subfield with three families of method, each with different access requirements (full mechanics in §7; here is the landscape):

- **Surface overlap** — n-gram / substring matching between test items and any available training corpus. Cheap, catches direct copies, blind to paraphrase. Scaled with MinHash/LSH and Bloom filters.
- **Canary strings** — a unique GUID embedded in the dataset (the **BIG-bench canary** convention, 2022) that trainers are asked to exclude and evaluators can later probe for. It does not prevent ingestion; it makes ingestion *detectable and filterable*. ([BIG-bench](https://github.com/google/BIG-bench))
- **Membership inference / memorization probes** — statistical tests on the model itself. **Min-K% Prob (Detecting Pretraining Data, arXiv 2310.16789)** flags text whose k% least-likely tokens are anomalously *not* low-probability, a signature of memorization; **Min-K%++ (arXiv 2404.02936, ICLR'25)** improves the baseline. Guided/quiz prompting and perturbation probing are the black-box cousins. ([arXiv 2310.16789](https://arxiv.org/abs/2310.16789), [Min-K%++](https://arxiv.org/html/2404.02936v2), [survey arXiv 2502.14425](https://arxiv.org/html/2502.14425v2))

The senior-level nuance: **no single method is proof.** N-gram overlap has false negatives (paraphrase) and false positives (common boilerplate); membership-inference methods have modest AUC on modern large models and are sensitive to distribution shift between "member" and "non-member" probe sets. You *triangulate* — surface overlap + a recency cliff + a memorization probe agreeing is a case; any one alone is a hint.

### 3.5 Synthetic data for evals: from novelty to normal, with guardrails

Synthetic task generation (see §8) went mainstream because frontier models can now author plausible tasks cheaply. The 2025–2026 consensus is *not* "generate your benchmark"; it is "**generate candidates, then verify and human-filter**." The durable recipe traces to **Self-Instruct (arXiv 2212.10560)**: seed with human tasks, over-generate, then filter hard for validity and diversity. What changed by 2026:

- **Generator ≠ evaluatee, always.** Using model X to author tasks you then use to grade model X (or its siblings) measures agreement with X's priors, not capability. Teams now use a *stronger, different* generator and disclose it.
- **Verifier-in-the-loop generation.** The strongest pipelines only keep a synthetic task if an *independent executable verifier* confirms the gold answer (e.g., generate a coding task, then require reference tests to actually pass on a reference solution). Unverified LLM "gold" labels are treated as radioactive.
- **Synthetic stays a labeled minority.** It fills coverage gaps (rare, adversarial, privacy-sensitive cases) on top of a real-data core; the synthetic fraction is *reported*, not hidden.
- **Persona / scenario expansion** for user-facing agents (parameterize a validated task family across personas, locales, edge policies) is now a standard coverage tool — but each expanded task still passes the same validity gate.

The honest framing for an interview: synthetic data is a **coverage and scaling tool bolted onto human-validated cores and executable verifiers**, never a replacement for either.

### 3.6 Dataset documentation norms: datasheets and Croissant

Two documentation standards are now expected of a serious release:

- **Datasheets for Datasets (Gebru et al., arXiv 1803.09010)** — the human-readable provenance document: motivation, composition, collection, preprocessing, uses, distribution, maintenance. Answering its questions is how you turn JSON into an instrument others can trust and critique. ([arXiv 1803.09010](https://arxiv.org/pdf/1803.09010))
- **Croissant (MLCommons, 2024)** — a **machine-readable** metadata format (JSON-LD, built on schema.org) that describes a dataset's resources, fields, splits, and semantics so tools can load and audit it uniformly. Hugging Face, Kaggle, and OpenML emit Croissant; it is the "package.json for datasets." The 2025 work connecting Croissant to MCP makes datasets discoverable and loadable by agents directly. ([announcement, Mar 2024](https://mlcommons.org/2024/03/croissant_metadata_announce/), [spec](https://docs.mlcommons.org/croissant/docs/croissant-spec.html), [Croissant+MCP, Oct 2025](https://mlcommons.org/2025/10/croissant-mcp/))

The relationship to remember: a **datasheet is the prose a human reads to decide whether to trust and how to use the data; Croissant is the structured metadata a machine reads to load, validate, and track it.** A mature release ships both, plus semantic versions and per-task content hashes (§9).

### 3.7 The landscape in one table

| Pressure (2025–2026) | Old practice | Current practice | Named example |
|---|---|---|---|
| Benchmarks saturate fast | Publish once, cite for years | Living benchmarks with dated tasks | LiveCodeBench, LiveBench |
| Contamination assumed | Ignore or hope | Canary + recency slice + MI probe | BIG-bench canary, Min-K%++ |
| Scraped data is noisy | Trust the scrape | Rubric + triple-annotate + errata | SWE-bench Verified |
| Agents are stateful | Q&A pairs | Executable worlds + state-diff verifiers | τ-bench, WebArena |
| Coverage gaps | Wait for real data | Verifier-filtered synthetic minority | Self-Instruct lineage |
| Trust & reproducibility | A README | Datasheet + Croissant + semver + hashes | Gebru datasheets, MLCommons Croissant |

---

## 4. Using standard benchmarks correctly

Off-the-shelf benchmarks are tempting because they give you comparability. They also give you a dozen ways to lie to yourself.

**Do:**
- **Pin the exact version and split.** "SWE-bench" is ambiguous; "SWE-bench Verified, 500 instances, HF revision `abc123`" is not. Record the revision hash, not just the name — datasets mutate on the Hub.
- **Report the harness.** The same tasks under different scaffolds (retrieval, max turns, tool set, timeout, retries) produce wildly different scores. State yours in full. A SWE-bench number without the agent scaffold, model, and turn budget is uninterpretable; two "SWE-bench Verified 55%" claims can be a factor-of-two apart in real capability.
- **Report trials and variance.** Agents are stochastic. One seed is an anecdote. Report pass@k / pass^k and dispersion (Chapter 3), and give confidence intervals — a 3-point gap on 500 tasks is often within noise.
- **Slice by metadata.** A single aggregate hides that you fail every Level-3 GAIA task. Break down by difficulty tier, domain, tool-count, and — critically — by task creation date relative to your model's cutoff.
- **Check the benchmark's own known errata.** Most mature benchmarks publish a list of retired/broken tasks. Use it, and cite which errata revision you applied.
- **Read the datasheet and the verifier code.** Know what the pass/fail actually checks before you quote the number. Many "reasoning" benchmarks are exact-match on a normalized string; a formatting mismatch reads as a wrong answer.

**Don't:**
- **Don't tune on the test set.** If you iterate against the public benchmark, you are overfitting to it. Keep a private slice you look at rarely (§8.1 on dev-to-test bleed).
- **Don't compare across harness versions** as if they were the same experiment. Leaderboard deltas across scaffold changes are not model deltas.
- **Don't assume the benchmark measures what its name says.** SWE-bench measures "resolve a scraped GitHub issue whose PR had good tests," which is narrower than "software engineering." GAIA measures "multi-step tool use with a unique answer," not "general intelligence." Read the datasheet.
- **Don't ignore contamination just because the benchmark is popular** — popularity *causes* contamination (§8). The more cited a static benchmark, the more crawled its tasks and solutions.
- **Don't trust a single leaderboard cell.** Reproduce at least a slice yourself. Leaderboards mix harnesses, prompt formats, and sometimes silent test-set fixes.

> The one-line policy: **treat a public benchmark number as a claim you must be able to reproduce, with a pinned (dataset revision, harness, model, trials) tuple, or you do not cite it.**

---

## 5. Building a custom benchmark, step by step

Standard benchmarks rarely match your agent's actual job. When you build your own, treat it as a small research project with reviews and acceptance criteria, not a spreadsheet someone fills in on a Friday.

**Step 1 — Define the question and the unit of evaluation.** Write one sentence: "Can our support agent resolve a billing dispute end-to-end, correctly updating the ledger, under our refund policy?" That sentence fixes the domain, the ground-truth shape (state-based ledger diff), and the verifier. If you cannot write the sentence, stop; you will build a ruler for a length you have not defined. A good acceptance sentence names the *actor*, the *task family*, the *success condition*, and the *constraints* — all four.

**Step 2 — Source raw tasks.** Prefer real distribution over invented tasks. Good sources, roughly in order of value:
- **Production logs / transcripts** (anonymized) — the true distribution of what users ask. Sample stratified by intent so rare-but-critical cases appear. Log-derived tasks carry a contamination *advantage* too: they are post-cutoff and private by default.
- **Domain experts** authoring realistic scenarios the logs miss (edge cases, adversarial users, policy corners).
- **Existing tickets, docs, or issue trackers** — like SWE-bench mining GitHub. Capture the *creation date* per task for later recency slicing.
- **Synthetic generation** (§9) — to fill coverage gaps, never as the backbone, and only verifier-filtered.

**Step 3 — Author golden answers / trajectories *and the verifier*.** For each task, produce the ground truth and, crucially, the *verifier*. This is where most of the work — and most of the bugs — live:
- For **state-based** tasks: write the goal-state assertion (SQL/JSON diff) and a **seed database** the task runs against. Test the assertion against a known-good and a known-bad final state before you trust it.
- For **answer-based** tasks: write the unambiguous gold answer *and* the matching rule (exact, numeric-tolerance, set-equality, case/whitespace normalization). Ambiguity in the *matching rule* is as damaging as a wrong answer.
- For **trajectory/test-based** tasks: write reference tests, and — as SWE-bench learned — also `PASS_TO_PASS` guards so an agent cannot "fix" the issue by breaking everything else. Then apply the 2025 lesson (arXiv 2503.15223): a passing test is necessary, not sufficient — spot-check that passing patches are *genuine* fixes, or your verifier will bless plausible-but-wrong solutions.
- **Verify the verifier.** For every task, run the reference/gold solution through the verifier (must pass) and at least one deliberately wrong solution (must fail). A verifier you never tested is a coin flip.

**Step 4 — Calibrate difficulty.** Run 2–3 baselines (a weak model, a strong model, a human). Bucket tasks by observed solve rate: **easy** (>80% solve), **medium** (20–80%), **hard** (<20%). A benchmark where every task is solved or none is has zero discriminative power. Aim for a spread centered where you expect frontier systems to sit, so the ruler has ticks near the interesting region. Borrow from item-response theory: a task that *every* system passes or fails carries no information about *ranking*; the informative tasks are the ones that split your systems.

**Step 5 — Review.** Every task gets independent review by ≥2 people who did *not* author it, checking: (a) is the problem statement fully specified? (b) is the gold answer correct? (c) does the verifier accept all correct solutions and reject all wrong ones? Adopt SWE-bench's conservative ensembling: if any reviewer flags a severe problem, pull the task. Use a written rubric with named categories and a severity scale so reviews are comparable and you can compute agreement on them.

**Step 6 — Measure quality.** Compute inter-annotator agreement (§7), coverage against your intent taxonomy, and a contamination scan (§8) before you trust a single score. Set explicit gates: e.g., ship only if label-correctness \( \kappa \ge 0.7 \), every taxonomy cell has ≥N tasks, and no task exceeds your n-gram contamination threshold against the corpora you can access.

**Step 7 — Version, document, license (§11).** Freeze it, datasheet it, emit Croissant metadata, content-hash every task, and split off a held-out canary set before anyone runs an agent on it.

> Coverage checklist: build an explicit **taxonomy** of the capabilities/intents you care about (e.g., refund, address-change, plan-upgrade, fraud-hold) and require ≥N tasks per cell, including the adversarial and multi-tool cells. Coverage is a property you *design in*, not one you hope for. A coverage matrix (intent × difficulty × tool-count) with a task count in every cell is the artifact to show an interviewer.

**The build as a pipeline.** Steps 1–7 are a directed pipeline with gates, and it is worth being able to draw it:

```
define question ─▶ source tasks ─▶ author gold + verifier ─▶ verify the verifier
      │                                                              │
      ▼                                                              ▼
 acceptance sentence                                        calibrate difficulty
                                                                     │
   ship ◀─ version/datasheet/Croissant ◀─ QA gates ◀── independent review
           (semver + hashes + canary)     (κ≥0.7,
                                            coverage,
                                            contamination)
```

Each arrow is a gate that can send a task back or out. The gates — not the collection — are what make it a benchmark rather than a pile of tasks.

---

## 6. Build it in practice: a runnable dataset-QA toolkit

Theory is cheap; here is a toolkit you can actually run. It does three jobs that every serious benchmark build needs: (1) **measure inter-annotator agreement** and flag the contentious tasks, (2) **screen for contamination** with a canary probe and an n-gram overlap scan (plus a recency slice), and (3) **generate synthetic tasks and route them through an independent verifier and a human-filter queue**. It is pure standard library except where noted, and every function is designed to be correct enough to lift into a real pipeline.

### 6.1 A minimal task schema

Give every task a stable identity, provenance, a creation date (for recency slicing), and a content hash (for versioning). This one object threads through the whole toolkit.

```python
"""dataset_qa.py — a small, correct dataset-QA toolkit for agent benchmarks."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import date
from collections import Counter
import hashlib
import json


@dataclass
class Task:
    id: str
    prompt: str                     # what the agent is asked to do
    gold: str                       # gold answer OR goal-state spec (JSON string)
    verifier: str                   # name of the scorer: "exact" | "state_diff" | "tests"
    domain: str
    difficulty: str = "unknown"     # easy | medium | hard, set during calibration
    created: str = "1970-01-01"     # ISO date; enables recency-based contamination checks
    source: str = "unknown"         # logs | expert | scraped | synthetic
    tags: list[str] = field(default_factory=list)

    def content_hash(self) -> str:
        """Stable hash over the load-bearing fields; changing any of these is a NEW task."""
        payload = json.dumps(
            {"prompt": self.prompt, "gold": self.gold, "verifier": self.verifier},
            sort_keys=True, ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def release_hash(tasks: list[Task]) -> str:
    """One hash for a whole release: anyone can verify they ran the exact data you did."""
    joined = "\n".join(sorted(t.content_hash() for t in tasks))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]
```

### 6.2 Inter-annotator agreement and low-agreement flagging

Cohen's \( \kappa \) for two raters, Fleiss' \( \kappa \) for a panel, plus a helper that returns the *specific* tasks reviewers split on — those are the ones to fix or cut before you trust any score computed on the set.

```python
# ---------- Cohen's kappa (2 annotators) ----------
def cohens_kappa(a: list, b: list) -> float:
    """a, b: equal-length lists of categorical labels from two raters."""
    assert len(a) == len(b) and len(a) > 0
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n           # observed agreement
    ca, cb = Counter(a), Counter(b)
    cats = set(ca) | set(cb)
    p_e = sum((ca[c] / n) * (cb[c] / n) for c in cats)    # chance agreement
    return 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)


# ---------- Fleiss' kappa (n raters per item, fixed panel size) ----------
def fleiss_kappa(ratings: list[list]) -> tuple[float, list[float]]:
    """ratings: list of items; each item is a list of labels (one per rater).
    Returns (aggregate kappa, per-item agreement P_i)."""
    cats = sorted({lbl for item in ratings for lbl in item})
    idx = {c: j for j, c in enumerate(cats)}
    N = len(ratings)
    n = len(ratings[0])
    assert all(len(item) == n for item in ratings), "fixed rater count required"

    M = [[0] * len(cats) for _ in range(N)]               # N x k count matrix
    for i, item in enumerate(ratings):
        for lbl in item:
            M[i][idx[lbl]] += 1

    P_i = [(sum(c * c for c in M[i]) - n) / (n * (n - 1)) for i in range(N)]
    P_bar = sum(P_i) / N
    p_j = [sum(M[i][j] for i in range(N)) / (N * n) for j in range(len(cats))]
    P_e = sum(p * p for p in p_j)
    kappa = 1.0 if P_e == 1 else (P_bar - P_e) / (1 - P_e)
    return kappa, P_i


def flag_low_agreement(ratings: list[list], threshold: float = 0.5) -> list[int]:
    """Indices of items whose per-item agreement P_i is below threshold — the tasks to fix/cut."""
    _, P_i = fleiss_kappa(ratings)
    return [i for i, p in enumerate(P_i) if p < threshold]


def gate_on_agreement(ratings: list[list], min_kappa: float = 0.7) -> dict:
    """A QA gate: is the set's label agreement high enough to publish scores from?"""
    kappa, P_i = fleiss_kappa(ratings)
    contentious = [i for i, p in enumerate(P_i) if p < 0.5]
    return {"kappa": round(kappa, 3), "pass": kappa >= min_kappa,
            "n_contentious": len(contentious), "contentious_items": contentious}
```

### 6.3 Contamination screening: canary probe + n-gram overlap + recency slice

Three complementary screens. The canary probe is black-box (does the model regurgitate a GUID you planted?). The n-gram scan is corpus-based (does a test task appear verbatim in text you can access?). The recency slice needs no corpus at all — it just compares solve rates before and after the model's cutoff, and a cliff *is* the signal.

```python
# ---------- Canary strings ----------
import uuid

def make_canary() -> str:
    """A unique GUID to embed in the dataset (BIG-bench convention). Ship it in the
    datasheet and ask trainers to exclude any document containing it."""
    return f"BENCHMARK-CANARY-GUID:{uuid.uuid4()}"


def canary_leak_probe(canary: str, model_generate) -> bool:
    """Black-box check: prompt the model to continue the canary; if it reproduces the
    exact GUID, the dataset (or a doc quoting it) was in training. `model_generate` is
    any callable str->str (your model API)."""
    prefix = canary.split(":")[0] + ":"          # give only the label, hide the GUID
    out = model_generate(f"Complete this identifier exactly: {prefix}")
    return canary.split(":", 1)[1] in out


# ---------- N-gram overlap ----------
def ngrams(text: str, n: int = 8) -> set[tuple]:
    toks = text.lower().split()
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def contamination_score(test_item: str, corpus_ngrams: set, n: int = 8) -> float:
    """Fraction of the test item's n-grams that appear in the training corpus.
    ~0 = clean; near 1 = the item is essentially in the corpus."""
    tg = ngrams(test_item, n)
    if not tg:
        return 0.0
    return len(tg & corpus_ngrams) / len(tg)


def scan_contamination(test_items: list[str], corpus_texts: list[str],
                       n: int = 8, flag_at: float = 0.5) -> list[tuple[int, float]]:
    corpus_ngrams: set = set()
    for doc in corpus_texts:
        corpus_ngrams |= ngrams(doc, n)
    flagged = []
    for i, item in enumerate(test_items):
        s = contamination_score(item, corpus_ngrams, n)
        if s >= flag_at:
            flagged.append((i, round(s, 3)))
    return flagged


# ---------- Recency slice (no corpus needed) ----------
def recency_cliff(tasks: list[Task], solve: dict[str, bool], cutoff: str) -> dict:
    """Compare solve rate on tasks created BEFORE vs AFTER the model's training cutoff.
    A large positive (pre - post) gap is a contamination signal."""
    pre = [t for t in tasks if t.created <= cutoff]
    post = [t for t in tasks if t.created > cutoff]
    def rate(ts):
        vals = [solve[t.id] for t in ts if t.id in solve]
        return sum(vals) / len(vals) if vals else float("nan")
    r_pre, r_post = rate(pre), rate(post)
    return {"n_pre": len(pre), "n_post": len(post),
            "solve_pre": round(r_pre, 3), "solve_post": round(r_post, 3),
            "cliff": round(r_pre - r_post, 3)}
```

Notes on correctness and scale:
- The n-gram scanner is a **screen, not a proof** — it catches direct/near-direct copies at the chosen `n`. Lower `n` catches more (and more false positives); it will *not* catch paraphrase leakage, for which you need the perplexity/probing methods in §8.2. In production, hash n-grams and use a **Bloom filter or MinHash/LSH** (the `datasketch` library) so you can scan a test set against a terabyte-scale corpus without holding it in RAM.
- `recency_cliff` is the cheapest contamination signal you own and needs no training corpus — which is why timestamped tasks (§3.3) are worth the bookkeeping. Interpret it with a confidence interval: a 2-point cliff on 40 tasks is noise; a 20-point cliff is a finding.
- `canary_leak_probe` cannot *prevent* ingestion; it makes it *detectable*. A negative result is weak evidence (the model may know the GUID but not surface it); a positive result is strong.

### 6.4 Synthetic task generation with a verifier gate and a human-filter queue

The safe pattern from §3.5 and §9, made concrete: over-generate with a *strong, different* model, **discard anything the independent verifier cannot confirm**, deduplicate against existing tasks, and route the survivors to a **human-filter queue** — synthetic tasks are candidates, never auto-admitted.

```python
"""synth.py — generate, verify, dedup, and human-filter synthetic eval tasks."""
from difflib import SequenceMatcher


def generate_candidates(seed_tasks: list[Task], generator, n: int = 50) -> list[Task]:
    """Over-generate candidates from human seeds using a STRONGER, DIFFERENT model than
    any under test. `generator(prompt) -> str` returns a JSON task spec. We never trust
    the generator's 'gold' until an independent verifier confirms it (next step)."""
    seeds_txt = "\n".join(f"- {t.prompt}" for t in seed_tasks[:10])
    out = []
    for i in range(n):
        raw = generator(
            "You are authoring EVAL tasks. Given these seed tasks, write ONE new, "
            f"realistic task in the same family but a distinct scenario:\n{seeds_txt}\n"
            "Return JSON with keys: prompt, gold, verifier, domain."
        )
        try:
            d = json.loads(raw)
            out.append(Task(id=f"syn-{i}", prompt=d["prompt"], gold=d["gold"],
                            verifier=d["verifier"], domain=d["domain"],
                            source="synthetic", created=str(date.today())))
        except (json.JSONDecodeError, KeyError):
            continue                                   # malformed generations are dropped
    return out


def verify_gold(task: Task, run_reference_solution) -> bool:
    """INDEPENDENT verifier gate: execute a reference solution against the task's verifier.
    Only keep synthetic tasks whose 'gold' is actually confirmed correct. `run_reference_
    solution(task) -> bool` returns True iff a known-good solution passes task.verifier."""
    return run_reference_solution(task)


def dedup(candidates: list[Task], existing: list[Task], max_sim: float = 0.8) -> list[Task]:
    """Drop candidates too similar to any existing task (self-contamination / low diversity).
    SequenceMatcher stands in for the ROUGE-L overlap filter used by Self-Instruct."""
    kept = []
    corpus = [t.prompt for t in existing]
    for c in candidates:
        if all(SequenceMatcher(None, c.prompt, e).ratio() < max_sim for e in corpus):
            kept.append(c)
            corpus.append(c.prompt)                    # dedup among candidates too
    return kept


def human_filter_queue(candidates: list[Task]) -> list[dict]:
    """Emit review cards. Synthetic tasks are CANDIDATES: a human must accept each before
    it enters the benchmark, and the accepted set stays a labeled minority."""
    return [{"id": c.id, "prompt": c.prompt, "gold": c.gold, "source": c.source,
             "decision": None, "reviewer": None} for c in candidates]


def synth_pipeline(seed_tasks, existing, generator, run_reference_solution,
                   n: int = 50) -> dict:
    cands = generate_candidates(seed_tasks, generator, n=n)
    verified = [t for t in cands if verify_gold(t, run_reference_solution)]
    deduped = dedup(verified, existing)
    queue = human_filter_queue(deduped)
    return {"generated": len(cands), "verifier_passed": len(verified),
            "after_dedup": len(deduped), "to_human_review": queue,
            "synthetic_fraction": round(len(deduped) / (len(existing) + len(deduped)), 3)}
```

### 6.5 Putting it together — a demo you can run

```python
if __name__ == "__main__":
    # --- IAA on a small panel ---
    r1 = [1, 1, 0, 1, 0, 1]; r2 = [1, 0, 0, 1, 0, 1]
    print("Cohen's kappa:", round(cohens_kappa(r1, r2), 3))
    panel = [[1,1,1],[1,0,1],[0,0,0],[1,1,0],[0,0,0],[1,1,1]]
    print("Agreement gate:", gate_on_agreement(panel, min_kappa=0.7))

    # --- Contamination screens ---
    tests = ["reset the user password and email a confirmation to the account owner"]
    corpus = ["to reset the user password and email a confirmation to the account owner you call ..."]
    print("N-gram flags:", scan_contamination(tests, corpus, n=6, flag_at=0.4))
    canary = make_canary(); print("Ship this canary in the datasheet:", canary)

    # --- Recency cliff (fake solve results) ---
    tasks = [Task("a","...","x","exact","support",created="2023-01-01"),
             Task("b","...","y","exact","support",created="2026-02-01")]
    solve = {"a": True, "b": False}
    print("Recency:", recency_cliff(tasks, solve, cutoff="2025-06-01"))

    # --- Content + release hashes for versioning ---
    print("Release hash:", release_hash(tasks))
```

What the toolkit gives you, mapped to the earlier theory: `gate_on_agreement` operationalizes §7 (do not publish below \( \kappa = 0.7 \)); the three contamination functions operationalize §8; `synth_pipeline` operationalizes the §9 safe-synthetic rules (different generator, verifier gate, dedup, human filter, reported fraction); and `content_hash`/`release_hash` operationalize §11 versioning. Wire these into CI and a benchmark cannot regress silently: a PR that lowers agreement, raises contamination, or mutates a task hash fails the build.

---

## 7. Validating quality: inter-annotator agreement

If two competent humans disagree about whether a task's answer is correct, the *task* is broken, not the annotators. Inter-annotator agreement (IAA) quantifies this. Raw percent agreement is misleading because raters agree partly **by chance** — if 90% of items are "pass," two raters who guess "pass" blindly agree 81% of the time while knowing nothing. Chance-corrected agreement fixes this. IAA is the single most important quality number to report about a hand-labeled benchmark: it is the calibration certificate on your ruler.

### 7.1 Cohen's kappa (two annotators)

Cohen's \( \kappa \) compares observed agreement to chance agreement:

\[
\kappa = \frac{p_o - p_e}{1 - p_e}
\]

where \( p_o \) is the observed proportion of items the two raters agree on, and \( p_e \) is the agreement expected by chance, computed from each rater's marginal label frequencies:

\[
p_e = \sum_{c} \left( \frac{n_{1c}}{N} \cdot \frac{n_{2c}}{N} \right)
\]

Here \( c \) indexes categories, \( n_{1c} \) is how many items rater 1 put in category \( c \), and \( N \) is the number of items. \( \kappa = 1 \) is perfect agreement, \( \kappa = 0 \) is chance-level, and negative means worse than chance.

**Worked calculation.** Two reviewers label \( N = 100 \) agent outputs as **pass** or **fail**. The confusion matrix:

|  | R2: pass | R2: fail | R1 total |
|---|---|---|---|
| **R1: pass** | 45 | 10 | 55 |
| **R1: fail** | 15 | 30 | 45 |
| **R2 total** | 60 | 40 | 100 |

Observed agreement (the diagonal):
\[
p_o = \frac{45 + 30}{100} = 0.75
\]

Chance agreement from the marginals (R1 pass = 0.55, R2 pass = 0.60; R1 fail = 0.45, R2 fail = 0.40):
\[
p_e = (0.55 \times 0.60) + (0.45 \times 0.40) = 0.33 + 0.18 = 0.51
\]

Therefore:
\[
\kappa = \frac{0.75 - 0.51}{1 - 0.51} = \frac{0.24}{0.49} \approx 0.49
\]

So despite 75% raw agreement, chance-corrected agreement is only **~0.49 — "moderate."** That is a warning sign: a nontrivial share of your tasks are ambiguous enough that trained reviewers split on them, and any score you compute on this set inherits that noise.

**The kappa paradox — a trap interviewers set.** Kappa can be *low even when agreement is high* if the labels are very imbalanced (say 95% "pass"). Because \( p_e \) is then huge, there is little room above chance and \( \kappa \) collapses toward 0 even at 95% raw agreement. The fix is to *not* read kappa in a vacuum: report raw agreement, the marginal distribution, and kappa together, and on skewed sets consider prevalence-adjusted measures (PABAK) or Gwet's AC1. The senior-level takeaway: kappa measures agreement *beyond chance given your label distribution*; a low kappa on a skewed set may mean "the labels are easy and imbalanced," not "the annotators are bad." Diagnose before you act.

### 7.2 Interpreting kappa (Landis & Koch scale)

| \( \kappa \) | Interpretation |
|---|---|
| < 0.00 | Worse than chance |
| 0.00–0.20 | Slight |
| 0.21–0.40 | Fair |
| 0.41–0.60 | Moderate |
| 0.61–0.80 | Substantial |
| 0.81–1.00 | Almost perfect |

For a benchmark you will publish scores from, target **\( \kappa \ge 0.7 \)** on label correctness. Below that, revise task wording and rubrics before proceeding — low agreement is a data-quality bug, not a personality difference. The Landis & Koch bands are *conventions*, not laws; some fields demand \( \kappa \ge 0.8 \) for clinical-grade labels. State the threshold you chose and why.

### 7.3 Fleiss' kappa (three or more annotators)

When each item is rated by \( n \) raters (possibly a different panel per item) across \( k \) categories, use Fleiss' \( \kappa \). Build \( N \times k \) matrix \( M \) where \( M_{ij} \) = number of raters assigning item \( i \) to category \( j \) (each row sums to \( n \)).

Per-item agreement:
\[
P_i = \frac{1}{n(n-1)} \left( \sum_{j=1}^{k} M_{ij}^2 - n \right)
\]

Mean observed agreement and per-category expected probability:
\[
\bar{P} = \frac{1}{N} \sum_{i=1}^{N} P_i, \qquad p_j = \frac{1}{N n} \sum_{i=1}^{N} M_{ij}, \qquad P_e = \sum_{j=1}^{k} p_j^2
\]

\[
\kappa = \frac{\bar{P} - P_e}{1 - P_e}
\]

The same [0,1] interpretation applies. Beyond the aggregate score, the per-item \( P_i \) tells you *which* tasks are contentious — those are the ones to fix or cut. That per-item signal is exactly what `flag_low_agreement` in §6.2 returns, and routing low-\( P_i \) tasks back to a third reviewer (or out of the set) is the single highest-leverage quality action you can take.

### 7.4 Which agreement statistic, when

| Situation | Use | Why |
|---|---|---|
| 2 raters, categorical labels | Cohen's \( \kappa \) | Standard pairwise, chance-corrected |
| ≥3 raters, categorical, possibly varying panel | Fleiss' \( \kappa \) | Handles many raters and per-item panels |
| Ordinal labels (0–3 severity) | Weighted \( \kappa \) / Krippendorff's \( \alpha \) | Credits "close" disagreements, penalizes "far" ones |
| Any level, missing data, mixed scales | Krippendorff's \( \alpha \) | Most general; handles gaps and any measurement level |
| Highly skewed labels | PABAK / Gwet's AC1 | Robust to the kappa-paradox prevalence problem |
| Continuous scores (e.g., 1–10 quality) | ICC / Pearson | Correlation of continuous ratings, not categories |

A subtle but important choice: when your labels are the **0–3 severity scale** SWE-bench Verified used, plain Fleiss' kappa treats a 0-vs-3 disagreement the same as 2-vs-3. Use **weighted kappa** or **Krippendorff's \( \alpha \)** so "far apart" disagreements cost more — otherwise you understate how badly reviewers disagree on the tasks that matter most.

---

## 8. Contamination and leakage

**Contamination** is when your evaluation data (or something too close to it) has leaked into the model's training set, so the model "solves" tasks by recall rather than capability. It is the single most under-reported source of inflated agent scores, and in 2025–2026 it is *assumed* by default — the question is not "is it contaminated?" but "how much, and can I bound it?"

### 8.1 How it happens

- **Direct ingestion.** You benchmark on a public dataset; a later pretraining crawl scoops up the dataset, its GitHub repo, and every blog post quoting it.
- **Solution leakage.** For SWE-bench-style tasks, the *fixing PR and its discussion* are on the public web — the model may have seen the exact patch, not just the issue.
- **Indirect / paraphrase leakage.** The model saw a reworded version (a tutorial, a Kaggle notebook, a Stack Overflow answer), so n-gram checks miss it.
- **Dev-to-test bleed.** Your team tunes prompts against the "held-out" set until it is effectively training data. This is contamination you cause yourself, and it is the most common kind in a real eval team. It has no crawler to blame; only a policy prevents it.
- **Benchmark-in-benchmark leakage.** Your new benchmark reuses tasks from an older public one (directly or by paraphrase), inheriting its contamination silently.

### 8.2 How to detect it

| Method | How it works | Access needed | Catches |
|---|---|---|---|
| **N-gram / string overlap** | Look for long exact substrings shared between test items and the training corpus | Training corpus | Direct copies |
| **Canary strings** | Embed a unique GUID in the dataset; later, prompt the model to reproduce it | Model (black-box) | Whole-dataset ingestion |
| **Perplexity / Min-K% / Min-K%++** | Memorized text has anomalously low perplexity / few low-probability tokens vs. fresh text | Token logprobs | Memorization |
| **Guided / quiz prompting** | Give the first half of a test item; see if the model completes the exact continuation | Model (black-box) | Instance memorization |
| **Perturbation probing** | Offer the original vs. reworded variants; a model that always picks the original memorized it | Model (black-box) | Instance memorization |
| **Timestamp / recency split** | Score tasks created *after* the model's training cutoff separately | Metadata | Temporal leakage |
| **Generation-probability correlation** | Correlate a model's probability of *emitting* a benchmark example with its score gap on a fresh clone | Token logprobs | Fingerprint of memorization |

The last row is the GSM1k method (§12): Scale AI found a Spearman **r² ≈ 0.36** between how likely a model was to *generate* GSM8k items and how much it dropped from GSM8k to the fresh GSM1k — a direct, quantitative memorization fingerprint. ([survey arXiv 2502.14425](https://arxiv.org/html/2502.14425v2), [Min-K% arXiv 2310.16789](https://arxiv.org/abs/2310.16789), [Min-K%++ arXiv 2404.02936](https://arxiv.org/html/2404.02936v2), [GSM1k arXiv 2405.00332](https://arxiv.org/abs/2405.00332))

**The 60-second detection story (memorize this for interviews).** "Contamination is when the eval data leaked into training, so the model recalls instead of reasons. I never trust one signal — I triangulate three. First, a **recency slice**: I compare solve rate on tasks created before vs after the model's cutoff; a cliff is the cheapest, most convincing signal and needs no corpus. Second, **n-gram overlap** against any training text I can access, scaled with MinHash/LSH — this catches verbatim copies but misses paraphrase. Third, a **memorization probe** — Min-K%++ on token logprobs, or a black-box guided-completion test where I feed half a task and see if the model reproduces the exact continuation. If all three agree, I have a case; any one alone is a hint. The real fix isn't detection though — it's a **held-out private set with post-cutoff tasks and a canary string**, so I'm measuring capability, not recall."

### 8.3 How to prevent it

- **Canary GUID.** Ship the dataset with a unique random string and publicly ask trainers to exclude any document containing it (the BIG-bench canary convention). It does not stop contamination but makes it detectable and gives trainers a filter. ([BIG-bench](https://github.com/google/BIG-bench))
- **Hold out a private test set.** Publish a dev split; keep the scoring split behind an API or fully offline. GAIA keeps 300 answers private; τ-bench and SWE-bench evolve. This is the only robust defense.
- **Rotate and refresh.** Treat benchmarks as perishable. Add new post-cutoff tasks each cycle; retire tasks once solve rates saturate suspiciously. This is exactly what LiveCodeBench and LiveBench institutionalize (§3.3).
- **Encrypt / gate.** Distribute test payloads encrypted or under access agreements so crawlers cannot ingest raw text.
- **Recency-stratify.** Always keep a slice of tasks provably created after the newest model's cutoff, and watch for a score cliff between pre- and post-cutoff tasks — that cliff *is* the contamination signal (`recency_cliff` in §6.3).
- **Time-box your own dev usage.** Log every scoring run against the private set; make repeated runs against it require sign-off. The cheapest contamination to prevent is the one you cause.

> Discipline beats cleverness here: a well-guarded held-out set of 50 fresh tasks is worth more than a 5,000-task public benchmark everyone (and every crawler) has seen. The half-life of a public benchmark's trustworthiness is now measured in *months*, not years.

---

## 9. Synthetic data for evals

LLM-generated tasks are attractive: cheap, scalable, and able to hit coverage gaps on demand. **Self-Instruct** is the canonical recipe — bootstrap from a small pool of human-written seed tasks (the paper used **175** seeds) and prompt an LLM to generate many more (they reached **~52K** instructions), then **filter** aggressively for validity and diversity (e.g., drop new tasks whose ROUGE-L overlap with existing ones exceeds a threshold). ([Self-Instruct arXiv 2212.10560](https://arxiv.org/abs/2212.10560))

**When synthetic data helps:**
- **Coverage of rare/edge cases** you cannot find enough of in logs (fraud attempts, policy-corner requests).
- **Scaling up structure** once you have a validated template and verifier (parameterize a known-good task family).
- **Adversarial/red-team inputs** where you want systematic variation.
- **Privacy** — generating synthetic analogues of sensitive real transcripts.
- **Persona/locale expansion** — apply a validated task family across personas, languages, and edge policies for user-facing agents.

**The risks — and they are serious for evals specifically:**
- **The generator's blind spots become the benchmark's blind spots.** If a model generates and (implicitly) knows how to solve the tasks, you measure agreement with the generator, not capability.
- **Self-contamination.** Tasks generated by model X are trivially easy for model X and its relatives — you cannot use X-authored tasks to fairly grade X.
- **Distribution drift.** Synthetic tasks cluster around the generator's priors and miss the messy, ungrammatical, contradictory reality of real users.
- **Unverified gold answers.** LLM-authored "correct" answers are frequently wrong. Never trust a synthetic label without an independent check.
- **Diversity collapse.** Naive over-generation produces near-duplicates; without a dedup/diversity filter you inflate task count without adding information.

**Rules for using synthetic eval data safely:** (1) always pass every synthetic task through **human filtering** and an **independent verifier** (the `synth_pipeline` in §6.4); (2) use a *different, stronger* model to generate than the ones you evaluate, and never the one under test; (3) keep synthetic tasks a labeled *minority* of the benchmark, sitting on top of a real-data core; (4) **report the synthetic fraction**; (5) dedup against existing tasks to preserve diversity. Synthetic data is a coverage tool, not a foundation.

**The one sentence to say in an interview:** "I use synthetic data to *reach coverage I can't find in logs* — rare, adversarial, privacy-sensitive cases — but only as a human-filtered, verifier-confirmed, reported minority on top of a real-data, human-validated core. I never let the model I'm grading author the tasks that grade it, and I never trust an LLM-written gold label without an executable check."

---

## 10. A compact worked example

The §6 toolkit is the production version. Here is the condensed, dependency-free reference implementation of the two most-asked-about pieces — inter-annotator agreement and an n-gram contamination check — in a single self-contained file. Keep this in your head for whiteboard interviews; it (a) computes Cohen's and Fleiss' kappa on annotations and flags low-agreement items for review, and (b) runs a simple n-gram contamination check between test tasks and a training corpus. Pure standard library plus optional scikit-learn.

```python
"""Benchmark dataset QA: inter-annotator agreement + contamination check."""
from collections import Counter
from itertools import combinations


# ---------- 1. Cohen's kappa (2 annotators) ----------
def cohens_kappa(a, b):
    """a, b: equal-length lists of categorical labels from two raters."""
    assert len(a) == len(b) and len(a) > 0
    n = len(a)
    p_o = sum(x == y for x, y in zip(a, b)) / n           # observed agreement
    ca, cb = Counter(a), Counter(b)
    cats = set(ca) | set(cb)
    p_e = sum((ca[c] / n) * (cb[c] / n) for c in cats)    # chance agreement
    return 1.0 if p_e == 1 else (p_o - p_e) / (1 - p_e)


# ---------- 2. Fleiss' kappa (n raters, per-item panel) ----------
def fleiss_kappa(ratings):
    """ratings: list of items; each item is a list of labels (one per rater).
    Assumes a fixed number of raters n per item."""
    cats = sorted({lbl for item in ratings for lbl in item})
    idx = {c: j for j, c in enumerate(cats)}
    N = len(ratings)
    n = len(ratings[0])
    assert all(len(item) == n for item in ratings), "fixed rater count required"

    M = [[0] * len(cats) for _ in range(N)]               # N x k count matrix
    for i, item in enumerate(ratings):
        for lbl in item:
            M[i][idx[lbl]] += 1

    P_i = [(sum(c * c for c in M[i]) - n) / (n * (n - 1)) for i in range(N)]
    P_bar = sum(P_i) / N
    p_j = [sum(M[i][j] for i in range(N)) / (N * n) for j in range(len(cats))]
    P_e = sum(p * p for p in p_j)
    kappa = 1.0 if P_e == 1 else (P_bar - P_e) / (1 - P_e)
    return kappa, P_i                                     # P_i flags contentious items


def flag_low_agreement(ratings, threshold=0.5):
    """Return indices of items whose per-item agreement P_i is below threshold."""
    _, P_i = fleiss_kappa(ratings)
    return [i for i, p in enumerate(P_i) if p < threshold]


# ---------- 3. Simple n-gram contamination check ----------
def ngrams(text, n=8):
    toks = text.lower().split()
    return {tuple(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def contamination_score(test_item, corpus_ngrams, n=8):
    """Fraction of the test item's n-grams that appear in the training corpus.
    ~0 = clean; near 1 = the item is essentially in the corpus."""
    tg = ngrams(test_item, n)
    if not tg:
        return 0.0
    return len(tg & corpus_ngrams) / len(tg)


def scan_contamination(test_items, corpus_texts, n=8, flag_at=0.5):
    corpus_ngrams = set()
    for doc in corpus_texts:
        corpus_ngrams |= ngrams(doc, n)
    flagged = []
    for i, item in enumerate(test_items):
        s = contamination_score(item, corpus_ngrams, n)
        if s >= flag_at:
            flagged.append((i, round(s, 3)))
    return flagged


# ---------- Demo ----------
if __name__ == "__main__":
    # Two reviewers labeling 6 agent outputs pass(1)/fail(0)
    r1 = [1, 1, 0, 1, 0, 1]
    r2 = [1, 0, 0, 1, 0, 1]
    print("Cohen's kappa:", round(cohens_kappa(r1, r2), 3))

    # Three reviewers per item, 6 items
    panel = [
        [1, 1, 1],   # unanimous pass
        [1, 0, 1],   # split -> low P_i
        [0, 0, 0],   # unanimous fail
        [1, 1, 0],   # split
        [0, 0, 0],
        [1, 1, 1],
    ]
    k, P_i = fleiss_kappa(panel)
    print("Fleiss' kappa:", round(k, 3))
    print("Low-agreement items:", flag_low_agreement(panel, threshold=0.5))

    # Contamination: test task vs. a training corpus containing a near-copy
    tests = ["reset the user password and email a confirmation to the account owner"]
    corpus = ["to reset the user password and email a confirmation to the account owner you call ..."]
    print("Contamination flags:", scan_contamination(tests, corpus, n=6, flag_at=0.4))
```

Notes on correctness and use:
- `cohens_kappa` reproduces the §7.1 worked value on the 100-item matrix (feed it the expanded label lists) and returns ~0.49.
- `fleiss_kappa` returns both the aggregate and the per-item \( P_i \); route items below your threshold back to a third reviewer or cut them.
- The n-gram scanner is a **screen, not a proof** — it catches direct/near-direct copies at the chosen `n`. Lower `n` catches more (and more false positives); it will *not* catch paraphrase leakage, for which you need the perplexity/probing methods in §8.2. In production, hash n-grams and use a Bloom filter or MinHash/LSH so you can scan a test set against a terabyte-scale corpus without holding it in RAM.

---

## 11. Versioning, licensing, and datasheets

A benchmark you cannot cite exactly is a benchmark you cannot trust. Treat datasets like software releases.

**Versioning.**
- **Immutable, semantic versions.** `v1.0.0`, `v1.1.0` (added tasks), `v2.0.0` (changed a verifier — breaking). Never mutate a released version in place; a score is only comparable within a fixed version. A "silent fix" to a task is the most insidious way to make last quarter's numbers incomparable with this quarter's.
- **Content-hash every task** and record the set hash for a release, so anyone can verify they ran the exact data you did (`content_hash` / `release_hash` in §6.1). A shared release hash turns "which SWE-bench did you run?" from an argument into a string comparison.
- **Changelog + errata.** Log every task added, retired, or corrected, with a reason. Retire (don't silently delete) broken tasks so old results remain interpretable — publish an errata revision id that others cite.
- **Track provenance and creation date per task** — essential for the recency-stratified contamination check and for honest reporting of what distribution you sampled.

**Licensing.**
- **Know the license of every source.** Scraped GitHub code carries the repo's license; production transcripts carry privacy obligations; another benchmark's tasks carry *its* license (many are research-only / non-commercial). A single GPL or non-commercial task can poison the redistributability of your whole release.
- **Choose a clear license for your release.** Permissive (CC-BY, Apache-2.0, MIT) maximizes reuse; a custom eval license or gated access may be warranted for a held-out set you must keep uncontaminated.
- **PII and consent.** If tasks derive from real user data, anonymize, get consent where required, and document the process. This is a legal and ethical requirement, not a nicety, and it belongs in the datasheet.

**Datasheets.** Ship a **datasheet** (Gebru et al.) alongside the data answering: *motivation* (why it was created, by whom, funded how), *composition* (what a task is, how many, what's labeled, sensitive content), *collection* (sources, sampling, who annotated, IAA achieved), *preprocessing/cleaning*, *uses* (intended and out-of-scope), *distribution and license*, and *maintenance* (who owns it, how errata are handled, how it's versioned). This is the artifact that turns your JSON into an instrument other people can trust and critique. ([Datasheets for Datasets arXiv 1803.09010](https://arxiv.org/pdf/1803.09010))

**Croissant — the machine-readable half.** A datasheet is prose for humans; **Croissant** (MLCommons, 2024) is structured metadata for machines. It is a JSON-LD format (built on schema.org) that describes a dataset's files, fields, splits, and semantics so any tool can load, validate, and track it uniformly — Hugging Face, Kaggle, TensorFlow Datasets, and OpenML all emit or consume it. Think of it as the `package.json` of a dataset: it makes your benchmark discoverable, loadable, and auditable without bespoke glue code, and the 2025 Croissant-plus-MCP work lets agents load datasets directly by their metadata. A mature release in 2026 ships **both** a datasheet (human trust) and a Croissant record (machine interoperability), on top of semantic versions and per-task content hashes. ([Croissant announcement, Mar 2024](https://mlcommons.org/2024/03/croissant_metadata_announce/), [spec](https://docs.mlcommons.org/croissant/docs/croissant-spec.html), [Croissant + MCP, Oct 2025](https://mlcommons.org/2025/10/croissant-mcp/))

| Documentation artifact | Audience | Answers | Standard |
|---|---|---|---|
| Datasheet | Humans deciding whether to trust/use | provenance, composition, consent, intended use | Gebru et al. 2018 |
| Croissant record | Tools & agents loading/validating | files, fields, splits, types, semantics | MLCommons 2024 |
| Semantic version + changelog | Anyone comparing scores over time | what changed, when, why | SemVer convention |
| Content/release hashes | Anyone reproducing a number | did I run the exact data you did | your pipeline |

---

## 12. Production case studies & war stories

Theory is abstract; the failures are specific. These are real, documented incidents (and the durable curation practices behind good golden datasets). Each ends with the lesson to repeat in an interview.

### 12.1 How good teams curate a golden dataset

Across strong eval teams the golden-dataset lifecycle looks the same, and it looks like software:

1. **Seed from production, not imagination.** Sample real, anonymized transcripts stratified by intent so the rare-but-critical cases (fraud, refunds at policy edges) appear at usable frequency. Real logs also happen to be post-cutoff and private — free contamination resistance.
2. **Author the verifier with the task.** For every golden item, write the executable check *and* run the reference solution through it (must pass) plus a known-wrong solution (must fail). A golden set without a tested verifier is decoration.
3. **Double- or triple-review with a rubric**, ensemble conservatively, and record the IAA. Below \( \kappa = 0.7 \), the set goes back for rewording, not out the door.
4. **Calibrate difficulty with baselines** so the set discriminates between the systems you actually compare.
5. **Freeze, hash, datasheet, and split off a private slice** before a single agent touches it.
6. **Treat it as living:** a standing errata process, a refresh cadence, and retirement (not deletion) of saturated or broken tasks.
7. **Guard the private slice with policy:** logged, infrequent scoring runs; no prompt-tuning against it. The discipline, not the cleverness, is what keeps the ruler straight.

The recurring theme: the teams that trust their numbers are the ones that treat the dataset build as an engineering project with gates, reviews, and version control — exactly the §5 pipeline.

### 12.2 War story: SWE-bench's original verifiers rejected correct code

**What happened.** The original SWE-bench used the real PR's tests as the verifier on scraped GitHub issues. When OpenAI and the authors put 1,699 sampled tasks in front of 93 developers, they found roughly **38% had underspecified problem statements** and roughly **61% had tests that could reject a valid solution** — the *majority* of a widely cited benchmark was measuring the wrong thing. Filtering to 500 clean tasks ("Verified") moved GPT-4o from ~16% to ~33% *on the same model*. The 2025 follow-up "Are 'Solved Issues' in SWE-bench Really Solved Correctly?" showed the inverse failure too: many *passing* patches are not genuine fixes — the tests are too weak, not too strict. ([SWE-bench Verified — OpenAI, Aug 2024](https://openai.com/index/introducing-swe-bench-verified/), [arXiv 2503.15223](https://arxiv.org/html/2503.15223v1))

**Lesson.** An executable verifier is necessary but not sufficient. A verifier can be **too strict** (rejects valid solutions — inflates difficulty, penalizes good agents) or **too weak** (accepts wrong solutions — inflates scores). You must test the verifier in *both* directions: run known-good solutions (must all pass) and known-bad solutions (must all fail). The single most valuable sentence: "the same model scored twice as high when the ruler was fixed — data quality dominated capability."

### 12.3 War story: GSM8k saturation was partly memorization (GSM1k)

**What happened.** GSM8k (grade-school math) was near-saturated and widely quoted as evidence of reasoning. Scale AI rebuilt it from scratch as **GSM1k** — same distribution, held private — and re-evaluated. Some model families dropped **up to ~8%**, and there was a **Spearman r² ≈ 0.36** between a model's probability of *generating* GSM8k examples and its GSM8k→GSM1k performance gap. Frontier models showed little drop; several smaller/open models showed the largest gaps. The benchmark had been partly measuring memorization, not arithmetic reasoning. ([GSM1k, Scale AI, arXiv 2405.00332, May 2024](https://arxiv.org/abs/2405.00332))

**Lesson.** Saturation on a popular static benchmark is *ambiguous*: it can mean "the models got good" or "the benchmark leaked." The way to disambiguate is a **fresh private clone of the same distribution** — the recency/private-set defense in operational form. And the generation-probability correlation gives you a quantitative contamination fingerprint you can actually compute.

### 12.4 War story: 3.3% of "ground truth" was wrong — and it flipped rankings

**What happened.** Northcutt, Athalye, and Mueller audited the test sets of ten of the most cited ML benchmarks (MNIST, ImageNet, CIFAR, etc.) and found an average of **at least 3.3% label errors**, with **~6% in the ImageNet validation set**. The consequence was not cosmetic: on ImageNet, correcting the mislabeled slice was enough that **ResNet-18 overtakes ResNet-50** once the originally-mislabeled test prevalence rises by ~6% — i.e., the *lower-capacity* model was actually better on correctly-labeled data, and the label noise had hidden it. Benchmark rankings were partly an artifact of wrong labels. ([Pervasive Label Errors, arXiv 2103.14749, 2021](https://arxiv.org/abs/2103.14749))

**Lesson.** "Ground truth" is a claim, not a fact, and even canonical benchmarks carry a few percent of wrong labels — enough to invert model comparisons. This is *the* argument for measuring label correctness (IAA, independent gold review) before trusting any ranking, and for reporting per-slice results: a small mislabeled slice can dominate a close comparison. For agents, where a single ambiguous task can flip a leaderboard, the effect is larger, not smaller.

### 12.5 War story: the self-inflicted contamination of a "held-out" set

**What happened (composite, representative of many eval teams).** A team keeps a "held-out" eval set and, over six months, iterates prompts, tool schemas, and scaffolds against it daily — because it is the only realistic set they have. Dev score climbs steadily from 61% to 78%. Production quality does not move. The held-out set had quietly become training data: the team had *fit the scaffold to the specific tasks*, learning their idiosyncrasies rather than the capability. There was no crawler to blame; the leak was the team's own workflow.

**Lesson.** The most common contamination in a real org is **dev-to-test bleed**, and it is a *policy* failure, not a modeling one. Fixes: demote the overused set to "dev," cut a fresh private set (ideally post-cutoff) you look at *rarely* and *log*, require sign-off for scoring runs against it, and — the tell — watch for a growing gap between held-out score and production outcomes, which is the fingerprint of overfitting to your own ruler.

### 12.6 The pattern behind every war story

| Incident | Root cause | Signal that would have caught it | Durable fix |
|---|---|---|---|
| SWE-bench too-strict tests | Untested verifier (too strict) | Reference-solution rejection rate | Verify the verifier both directions |
| SWE-bench weak tests | Untested verifier (too weak) | Known-wrong-solution pass rate | Same; spot-check genuine fixes |
| GSM8k saturation | Contamination / memorization | Recency clone score cliff; gen-prob correlation | Fresh private clone, timestamped tasks |
| ImageNet ranking flip | Wrong labels | Label-correctness IAA; independent gold review | Measure IAA; per-slice reporting |
| Held-out overfit | Dev-to-test bleed | Held-out vs production gap growing | Logged, infrequent private-set runs |

Every one traces to a *data* property — verifier fidelity, contamination, label correctness, or split hygiene — that a metric can never fix. That is the chapter's whole thesis in one table.

---

## 13. Failure modes and pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| **Ambiguous tasks** | Low inter-annotator \( \kappa \); reviewers argue | Rewrite for a single unambiguous answer; cut irreparable ones |
| **Wrong golden answers** | Strong agents "fail" tasks humans solve trivially | Independent gold-answer review; executable verifiers |
| **Over-strict verifiers** | Correct solutions rejected (SWE-bench's original flaw) | Add `PASS_TO_PASS` guards; test the verifier against known-good and known-bad solutions |
| **Over-weak verifiers** | Wrong solutions accepted; passing patches aren't real fixes | Strengthen tests; spot-check that passes are genuine (arXiv 2503.15223) |
| **Flat difficulty** | Every system scores ~the same | Calibrate with baselines; ensure an easy/medium/hard spread |
| **Contamination** | Score cliff between pre- and post-cutoff tasks; suspicious jumps | Canary strings, held-out set, recency split |
| **Test-set overfitting** | Dev score climbs, real-world flat | Freeze a private slice; look at it rarely |
| **Synthetic monoculture** | High scores that don't transfer to production | Human-filter; keep synthetic a minority; verify labels |
| **Aggregate-only reporting** | One number hides total failure on a whole category | Report per-slice and per-difficulty; publish variance |
| **Silent mutation** | Old and new scores incomparable | Semantic versioning + content hashes + changelog |
| **Too small** | Score swings wildly between runs | Power-check size; report confidence intervals |
| **Kappa paradox misread** | Low \( \kappa \) on obviously-clean skewed labels | Report raw agreement + marginals; use PABAK/AC1 when skewed |
| **Unpinned harness** | Two "same" benchmark numbers differ 2x | Pin (dataset revision, harness, model, trials) tuple |

---

## 14. Tools and datasets

| Name | Type | What it gives you | Link |
|---|---|---|---|
| SWE-bench / Verified | Coding benchmark | 500 human-vetted real GitHub issues, test-based scoring | [swebench.com](https://www.swebench.com/verified.html) |
| GAIA | General-assistant benchmark | 466 tool-use questions, 3 difficulty levels, private answers | [arXiv](https://arxiv.org/abs/2311.12983) |
| τ-bench / τ²-bench | Tool-agent-user | State-based scoring, pass^k reliability, retail/airline | [repo](https://github.com/sierra-research/tau2-bench) |
| WebArena | Web agents | 812 tasks on self-hostable reproducible sites | [repo](https://github.com/web-arena-x/webarena) |
| LiveCodeBench | Living code benchmark | Timestamped problems for contamination-free eval | [site](https://livecodebench.github.io/) |
| LiveBench | Living broad benchmark | Monthly-refreshed, objective, contamination-resistant | [repo](https://github.com/livebench/livebench) |
| GSM1k | Contamination probe | Fresh private clone of GSM8k to measure overfitting | [arXiv](https://arxiv.org/abs/2405.00332) |
| BIG-bench | Broad LM benchmark | Canary-string convention for contamination | [repo](https://github.com/google/BIG-bench) |
| Min-K% / Min-K%++ | Contamination detection | Membership-inference / memorization probes | [arXiv](https://arxiv.org/abs/2310.16789) |
| cleanlab | Label-QA library | Finds likely label errors automatically | [github.com/cleanlab/cleanlab](https://github.com/cleanlab/cleanlab) |
| Hugging Face Datasets | Data platform | Versioned hosting, revisions, dataset cards, Croissant | [hf.co/datasets](https://huggingface.co/datasets) |
| Croissant (MLCommons) | Metadata standard | Machine-readable dataset description (JSON-LD) | [docs.mlcommons.org/croissant](https://docs.mlcommons.org/croissant/) |
| scikit-learn | Library | `cohen_kappa_score`, metrics | [sklearn](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html) |
| statsmodels | Library | `fleiss_kappa`, IAA stats | [statsmodels](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html) |
| Krippendorff (PyPI) | Library | Krippendorff's \( \alpha \) for any measurement level | [pypi.org/project/krippendorff](https://pypi.org/project/krippendorff/) |
| datasketch | Library | MinHash / LSH for scalable overlap scans | [datasketch](https://github.com/ekzhu/datasketch) |

---

## 15. Interview mastery

This section is the drill sheet. First the rapid-fire Q&A, then a 60-second set-piece, then a system-design walkthrough, then the tradeoff tables and the red-flag/green-flag lists that let you audit any benchmark on sight.

### 15.1 Rapid-fire Q&A

**Q1. Why did SWE-bench Verified score higher than the original SWE-bench for the same model, and what does that teach you?**
Because ~68% of original tasks were filtered out for underspecified problem statements or unit tests that reject valid patches; 93 developers triple-annotated 1,699 samples down to 500 clean ones. GPT-4o went from ~16% to ~33% on the *same model* — the benchmark got more accurate, not the model better. Lesson: label/verifier quality can dominate the score more than model capability.

**Q2. You have 78% raw agreement between two reviewers. Is the benchmark trustworthy?**
Not from that number alone. Raw agreement ignores chance; on a skewed label distribution you can hit 78% while knowing nothing. Compute Cohen's \( \kappa \). If \( \kappa \) is ~0.4 (moderate), a meaningful fraction of tasks are ambiguous and you should revise wording/rubrics before publishing scores. And watch the kappa paradox: if labels are 95% one class, even a *low* kappa may be fine — report raw agreement, marginals, and kappa together.

**Q3. How would you detect that a public benchmark has contaminated the model you're testing?**
Multiple signals: (1) recency split — compare tasks created before vs. after the training cutoff; a score cliff is a red flag; (2) n-gram overlap between tasks and any available training corpus; (3) black-box probes — guided completion of a masked task, or preferring the original over perturbed variants; (4) perplexity/Min-K%(++) memorization tests; (5) the GSM1k trick — correlate the model's probability of *generating* a benchmark item with its score gap on a fresh clone. No single method is proof; triangulate.

**Q4. When is synthetic eval data appropriate, and how do you keep it honest?**
For coverage of rare/edge/adversarial cases and for scaling a validated task template — never as the benchmark's backbone. Keep it honest by: generating with a different, stronger model than any under test; passing every task through human filtering and an independent verifier; verifying gold labels rather than trusting them; keeping synthetic tasks a labeled minority; and reporting the synthetic fraction.

**Q5. Why does τ-bench score by database state instead of an LLM judge, and why introduce pass^k?**
State comparison is objective, cheap, and drift-free — the ledger either matches the goal or it doesn't, no judge bias. pass^k measures *reliability*: the probability that all k independent trials succeed. Average success hides that an agent that passes 60% of the time may pass all 8 tries only 20% of the time — which is what deployment actually cares about.

**Q6. What belongs in a datasheet, and why bother?**
Motivation, composition, collection process (including who annotated and the IAA achieved), preprocessing, intended and out-of-scope uses, distribution/license, and maintenance/versioning. It bothers because it makes provenance auditable, surfaces license and PII constraints, and lets others reproduce and critique your scores. A dataset without a datasheet is an instrument with no calibration certificate. Pair it with a Croissant record so machines can load and validate it too.

**Q7. How do you calibrate difficulty when building a custom benchmark?**
Run 2–3 baselines (a weak model, a strong model, and ideally a human) and bucket tasks by observed solve rate into easy/medium/hard. Ensure a spread — if everything solves or nothing does, the benchmark has no discriminative power. Center the mass of medium tasks where you expect frontier systems to sit so the ruler has ticks in the region you care about. The information is in the tasks that *split* your systems.

**Q8. Your held-out set has been used for prompt tuning over six months. What's the problem and the fix?**
It is no longer held out — you've turned it into training data by overfitting your prompts/scaffold to it, a self-inflicted contamination. Fix: retire it to the "dev" tier, cut a fresh private test set you look at rarely (ideally with post-cutoff tasks), and enforce a policy that scoring runs on the private set are infrequent and logged. The tell is a growing gap between held-out score and production outcomes.

**Q9. A verifier gives you 100% reproducible pass/fail. Is that enough to trust it?**
No — reproducible is not the same as correct. A verifier can be reproducibly *too strict* (rejects valid solutions, as original SWE-bench did) or reproducibly *too weak* (accepts wrong ones; passing tests that aren't genuine fixes). Test the verifier in both directions: every known-good solution must pass, every known-bad solution must fail. Reproducibility is table stakes; fidelity is the property you actually need.

**Q10. Your benchmark has 50 tasks and your agent scores 72%. A rival scores 76%. Who's better?**
Unknown — 4 points on 50 tasks is almost certainly inside the confidence interval, and agents are stochastic across seeds. Report pass@k/pass^k with confidence intervals and per-slice breakdowns; a single-run aggregate on a small set is an anecdote. Also confirm both numbers used the same dataset revision and harness, or you're comparing different rulers.

**Q11. Why prefer executable ground truth over an LLM judge when you can?**
Executable checks (state diffs, tests, exact match) don't drift, don't have mood, cost nothing to re-run, and can't be gamed by persuasive prose. LLM judges are unavoidable for open-ended outputs but are the most fragile ground truth — the "answer" lives in a prompt that can drift and disagree with itself. Hierarchy: state diff > tests > normalized match > human rubric > uncalibrated single judge. Climb as high as the domain allows, and if you must use a judge, pin its version and report judge–human kappa.

**Q12. What's the difference between a datasheet and Croissant, and do you need both?**
A datasheet is human-readable prose (motivation, provenance, consent, intended use) that helps a person decide whether to trust and how to use the data. Croissant is machine-readable JSON-LD metadata (files, fields, splits, types) that lets tools and agents load and validate it uniformly. They are complementary — humans read the datasheet, machines read Croissant — and a mature release ships both plus semantic versions and content hashes.

**Q13. How big should a benchmark be?**
Big enough that the confidence interval on your headline metric is smaller than the differences you need to detect, *and* big enough that every slice you report (each difficulty tier, each intent) has enough tasks to be non-anecdotal. Power-analyze it: for a proportion, the CI half-width is roughly \( 1.96\sqrt{p(1-p)/N} \), so distinguishing 70% from 75% reliably needs low hundreds of tasks *per slice*, not in total. Quality and coverage beat raw size — 50 well-guarded fresh tasks can be worth more than 5,000 contaminated ones.

**Q14. A benchmark is saturating — top models all score >95%. What do you conclude and do?**
Two hypotheses: the models genuinely mastered the capability, or the benchmark leaked/is too easy. Disambiguate with a fresh private clone of the same distribution (the GSM1k move) and a recency slice. If the fresh clone shows a cliff, it was contamination; if not, the benchmark has lost discriminative power and you should retire the saturated tasks and add harder, post-cutoff ones. Either way, a saturated static benchmark is done as a ranking tool.

**Q15. Someone hands you a leaderboard number. What do you ask before believing it?**
Which dataset revision (hash)? Which split (public/dev/private)? What harness — scaffold, tool set, max turns, retries, timeout? Which model version and decoding settings? How many trials and what variance? Any errata revision applied? Any contamination check for this model's cutoff? Without the (dataset revision, harness, model, trials) tuple, the number is a claim you can't reproduce.

**Q16. Your agent passes 90% of tasks but users complain. What data problem might explain it?**
Distribution mismatch: the benchmark samples the easy/common tail while users hit the messy, adversarial, long-tail cases the benchmark under-covers. Check the coverage matrix (intent × difficulty × tool-count) for empty or thin cells, compare the benchmark's intent distribution to production logs, and confirm the hard/adversarial cells actually have tasks. High benchmark score plus low production quality is usually a coverage or difficulty-calibration failure, not a metric bug.

### 15.2 The 60-second set-piece: "explain benchmark contamination and how you'd detect it"

> "Contamination is when the eval data — or something close enough, like the fixing PR or a paraphrase — leaked into the model's training set, so the model *recalls* answers instead of *reasoning* to them. That silently inflates scores, and in 2026 I assume every public benchmark is at least partly contaminated. I never trust one signal; I triangulate three. **One, a recency slice**: split tasks by creation date around the model's training cutoff and compare solve rates — a cliff where old tasks are solved and fresh ones aren't is the cheapest, most convincing evidence, and it needs no training corpus. **Two, n-gram overlap** against any training text I can reach, scaled with MinHash or a Bloom filter — this catches verbatim copies but misses paraphrase. **Three, a memorization probe** — Min-K%++ on token logprobs, or a black-box guided-completion test where I feed the first half of a task and see if the model reproduces the exact continuation. If all three agree, I have a case; any one alone is a hint. But detection is the consolation prize — the real fix is prevention: a **held-out private set with post-cutoff tasks and a canary GUID**, so I'm measuring capability, not recall. A well-guarded 50-task fresh set beats a 5,000-task benchmark every crawler has seen."

### 15.3 System-design prompt: "design a custom eval dataset for a domain agent"

**Prompt:** *"Design an evaluation dataset for a customer-support agent that handles billing disputes for a SaaS company — it can issue refunds, adjust plans, and place fraud holds, all under a written refund policy."*

**A strong answer walks the interviewer through the §5 pipeline, made concrete:**

**1. The question (one sentence).** "Can the agent resolve a billing dispute end-to-end — correctly mutating the ledger and subscription state — while obeying the refund policy and escalating when it should?" That fixes the actor (support agent), family (billing disputes), success condition (correct final DB state), and constraints (policy compliance + correct escalation).

**2. Ground-truth shape.** State-based. Each task ships a **seed database** (accounts, invoices, subscriptions, prior tickets), a **policy document**, a **tool/API surface** (`refund`, `change_plan`, `place_fraud_hold`, `escalate`), and a **goal-state predicate** (the exact ledger/subscription rows that must hold after). Score by DB-state equality plus a policy-compliance assertion — objective, drift-free, no judge. This is the τ-bench pattern.

**3. Sourcing + coverage matrix.** Seed from anonymized production transcripts, stratified by intent, then have domain experts author the edge/adversarial cells. Build an explicit coverage matrix and require ≥N tasks per cell:

```
                | happy path | policy-edge | adversarial user | multi-tool | should-escalate
----------------+------------+-------------+------------------+------------+----------------
refund          |    N        |     N        |       N           |    N        |      N
plan change     |    N        |     N        |       N           |    N        |      N
fraud hold      |    N        |     N        |       N           |    N        |      N
mixed dispute   |    N        |     N        |       N           |    N        |      N
```

The adversarial column (user lies, demands out-of-policy refunds, tries prompt injection) and the should-escalate row (agent must *refuse* and hand off) are where support agents actually fail and where naive benchmarks are empty.

**4. Verifier, tested both ways.** For each task, run a reference "correct" trajectory (must satisfy the goal predicate and policy check) and a known-wrong one (must fail). A verifier that only ever saw the gold path is untested.

**5. Difficulty calibration.** Run a weak model, a strong model, and a human agent; bucket by solve rate into easy/medium/hard; ensure a spread centered where you expect the deployed model to sit.

**6. Reliability, not just average.** Score with **pass^k** — a support agent that refunds correctly 60% of the time is not deployable; you need it to hold across independent trials. Report per-cell and per-difficulty, with confidence intervals.

**7. Contamination + split hygiene.** These are post-cutoff, private-by-construction (real transcripts), which helps. Still: hold out a private scoring slice, embed a canary GUID, timestamp every task, and keep a policy of logged, infrequent private-set runs. Refresh the adversarial cells each cycle as attackers adapt.

**8. Documentation + versioning.** Datasheet (provenance, the anonymization/consent process, IAA achieved) + Croissant record + semantic version + per-task content hashes + errata process.

**The sketch to draw on the whiteboard:**

```
 production logs ──stratify by intent──▶ seed tasks ──experts add edge/adversarial──▶ task pool
                                                                                          │
   coverage matrix (intent × difficulty × path)  ◀── require ≥N per cell ────────────────┘
                                                                                          │
 each task = { seed DB, policy doc, tools, goal-state predicate }                         │
                                                                                          ▼
        verify the verifier (gold passes, known-bad fails) ──▶ calibrate difficulty (3 baselines)
                                                                                          │
        triple review + rubric ──▶ IAA gate (κ≥0.7) ──▶ contamination screen ──▶ freeze  │
                                                                                          ▼
     datasheet + Croissant + semver + hashes + PRIVATE held-out slice (canary, timestamps)
                                                                                          │
                               score with pass^k, per-cell, with CIs ◀────────────────────┘
```

**What separates a senior answer:** naming the ground-truth *shape* (state-based, not a judge) and why, insisting the verifier is tested in both directions, designing coverage as a *matrix* with adversarial/escalation cells, scoring for *reliability* (pass^k) not average, and treating contamination and documentation as first-class from the start — not bolt-ons.

### 15.4 Tradeoff table: human vs. synthetic labels

| Dimension | Human labels | Synthetic (LLM-generated) labels |
|---|---|---|
| Cost / speed | Slow, expensive | Fast, cheap |
| Coverage of rare/edge cases | Limited by what you can find/afford | Excellent — generate on demand |
| Correctness of gold | High if reviewed; still ~few % error | Frequently wrong; must be verifier-confirmed |
| Distribution realism | Matches real users | Clusters around generator's priors |
| Contamination risk | Low (private, post-cutoff) | High — self-contamination with the generator family |
| Diversity | Naturally messy/varied | Collapses to near-duplicates without dedup |
| Best role | The validated core of the benchmark | A reported, verifier-filtered, human-approved minority |

**Verdict:** humans for the core and the gold; synthetic to *extend coverage* under a verifier gate. Never let synthetic labels stand unverified, and never let the model under test author its own tasks.

### 15.5 Tradeoff table: static vs. living datasets

| Dimension | Static (frozen once) | Living (refreshed on a cadence) |
|---|---|---|
| Comparability over time | Perfect within a version | Requires careful versioning to compare across refreshes |
| Contamination resistance | Decays fast — crawled within months | Strong — fresh, timestamped, post-cutoff tasks |
| Maintenance cost | Low after release | Ongoing (authoring, review, retirement) |
| Discriminative lifespan | Short once frontier saturates it | Long — saturated tasks retired, harder ones added |
| Reproducibility of a number | Trivial (fixed set) | Needs per-refresh version + hash to reproduce |
| Best for | A stable, citable baseline within a paper/quarter | Tracking a moving frontier without re-contaminating |
| Named examples | Original SWE-bench, GSM8k | LiveCodeBench, LiveBench, GAIA (private split) |

**Verdict:** ship a **static, hashed core** for reproducible comparison *and* a **living, timestamped extension** for contamination-resistant frontier tracking. They serve different jobs; mature programs run both.

### 15.6 Red flags vs. green flags — audit any benchmark on sight

| 🚩 Red flags (be suspicious) | ✅ Green flags (earned trust) |
|---|---|
| No datasheet; unknown provenance | Datasheet + Croissant + provenance per task |
| Single aggregate number, one run, no CI | Per-slice, per-difficulty, pass^k, confidence intervals |
| Verifier never tested against wrong solutions | Verifier tested both ways (gold passes, bad fails) |
| No IAA reported, or raw-agreement only | Chance-corrected \( \kappa \ge 0.7 \) reported with marginals |
| Public, popular, years old, no refresh | Private held-out slice, canary, timestamped, living |
| "SWE-bench: 60%" with no harness stated | Pinned (dataset revision, harness, model, trials) tuple |
| Gold answers authored by an LLM, unchecked | Executable/human-verified gold; synthetic a reported minority |
| Flat difficulty; every system scores alike | Calibrated easy/medium/hard spread with baselines |
| Silent in-place edits to tasks | Semantic versions, content hashes, published errata |
| Coverage "looks fine" (hoped for) | Coverage matrix with ≥N per cell, adversarial cells filled |

If you can run this two-column audit out loud against a benchmark someone hands you, you have demonstrated the judgment this chapter is meant to build.

---

## 16. Further reading

**Human-validated & agent benchmarks**
- Introducing SWE-bench Verified — OpenAI (Aug 2024): https://openai.com/index/introducing-swe-bench-verified/
- SWE-bench Verified dataset — Hugging Face: https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified
- Are "Solved Issues" in SWE-bench Really Solved Correctly? — arXiv 2503.15223 (2025): https://arxiv.org/html/2503.15223v1
- GAIA: a benchmark for General AI Assistants — arXiv 2311.12983 (2023): https://arxiv.org/abs/2311.12983
- GAIA dataset — Hugging Face: https://huggingface.co/datasets/gaia-benchmark/GAIA
- τ-bench: Tool-Agent-User Interaction — arXiv 2406.12045 (2024): https://arxiv.org/abs/2406.12045
- τ²-bench (Sierra) repo: https://github.com/sierra-research/tau2-bench
- WebArena: A Realistic Web Environment — arXiv 2307.13854 (2023): https://arxiv.org/pdf/2307.13854
- WebArena code: https://github.com/web-arena-x/webarena

**Living / contamination-aware benchmarks**
- LiveCodeBench: Holistic and Contamination-Free Evaluation — arXiv 2403.07974 (2024): https://arxiv.org/abs/2403.07974
- LiveCodeBench site: https://livecodebench.github.io/
- LiveBench: A Challenging, Contamination-Free LLM Benchmark: https://github.com/livebench/livebench
- A Careful Examination of LLM Performance on Grade School Arithmetic (GSM1k) — arXiv 2405.00332 (2024): https://arxiv.org/abs/2405.00332

**Contamination detection & membership inference**
- A Survey on Data Contamination for LLMs — arXiv 2502.14425 (2025): https://arxiv.org/html/2502.14425v2
- Detecting Pretraining Data from LLMs (Min-K% Prob) — arXiv 2310.16789 (2023): https://arxiv.org/abs/2310.16789
- Min-K%++: Improved Baseline for Detecting Pre-Training Data — arXiv 2404.02936 (ICLR'25): https://arxiv.org/html/2404.02936v2
- BIG-bench (canary string convention): https://github.com/google/BIG-bench

**Label quality & data-centric evaluation**
- Pervasive Label Errors in Test Sets Destabilize ML Benchmarks — arXiv 2103.14749 (Northcutt et al., 2021): https://arxiv.org/abs/2103.14749
- Label Errors project page (interactive): https://l7.curtisnorthcutt.com/label-errors
- cleanlab (automatic label-error detection): https://github.com/cleanlab/cleanlab

**Synthetic data for evals**
- Self-Instruct: Aligning LMs with Self-Generated Instructions — arXiv 2212.10560 (2022): https://arxiv.org/abs/2212.10560

**Dataset documentation & metadata standards**
- Datasheets for Datasets (Gebru et al.) — arXiv 1803.09010 (2018): https://arxiv.org/pdf/1803.09010
- Croissant: A Metadata Format for ML-Ready Datasets — MLCommons announcement (Mar 2024): https://mlcommons.org/2024/03/croissant_metadata_announce/
- Croissant format specification: https://docs.mlcommons.org/croissant/docs/croissant-spec.html
- Croissant meets MCP — MLCommons (Oct 2025): https://mlcommons.org/2025/10/croissant-mcp/

**Agreement statistics**
- statsmodels `fleiss_kappa`: https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html
- scikit-learn `cohen_kappa_score`: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html
- Krippendorff's alpha (PyPI): https://pypi.org/project/krippendorff/
- datasketch (MinHash / LSH): https://github.com/ekzhu/datasketch
