# Pattern 21: Exploration and Discovery — Agents That Look for What Nobody Told Them to Find

## The interview scenario

The open-ended flavor sounds like:

- "Design an agent that helps researchers generate and refine novel hypotheses — drug candidates, materials, scientific questions."
- "We want an agent that hunts through our data and market landscape for opportunities we haven't thought to ask about. How would you build it — and, harder, how would you evaluate it?"
- "How is an agent that discovers things architecturally different from an agent that completes tasks?"

This is the pattern interviewers reach for when they want to see you reason beyond well-specified problems.

There's no ticket to resolve and no single right answer — which is exactly the point, and evaluating under that condition is where the good candidates separate from the rest.

## What this pattern is, in plain words

Every pattern so far assumes somebody knows what the task is.

Exploration and discovery is for when nobody does — when the goal is to *find* things: new hypotheses, new strategies, unknown unknowns in an open-ended space too large to enumerate.

Instead of optimizing within a defined problem, the agent ventures into undefined territory and comes back with candidates for what the problem, or the answer, might be.

The engine underneath nearly every discovery system is a generate-test-refine loop, which is the scientific method wearing software clothes.

Generate many candidate ideas. Test them against whatever judgment is available — critiques, simulations, rankings, real experiments. Refine the survivors into the next generation. Repeat.

Google's AI co-scientist runs this loop with specialized agents that generate hypotheses, peer-review them, rank them in tournaments, and evolve the winners.

Systems in the AlphaEvolve style run the same loop over candidate programs, using automated scoring to steer evolution toward better and better solutions. Same loop, different search space.

What varies between domains is the tester in the middle. Code gets scored by running it. Game strategies get scored by playing them. Scientific hypotheses — the hardest case — get scored by critique and comparison, because the real test is a lab experiment you can't afford to run on every candidate.

The cheaper and more automatic your test, the faster and more autonomous your loop can be.

The central tension has a classic name — exploration versus exploitation: try new things versus double down on what already works.

Explore too little and you polish mediocrity, never finding the genuinely new thing two hills over. Explore too much and you burn the budget on scattered novelty that never compounds into anything.

Managing that dial — under an explicit budget on curiosity — is the actual design problem.

## How the design actually works

The reference architecture is a multi-agent loop that mirrors how research communities work, and the co-scientist's role list is worth knowing by name.

A **generation agent** produces candidate hypotheses — from literature exploration, from data, even from simulated scientific debates where agents argue positions to shake loose ideas.

A **reflection agent** plays peer reviewer, critiquing each candidate for correctness, novelty, and quality. Is it consistent with known evidence? Is it actually new, or just obscure-sounding? Is it testable?

A **ranking agent** runs tournaments — pairwise comparisons between hypotheses, argued out in simulated debate, feeding an Elo-style rating.

That's the chess-ranking trick: candidates earn scores by beating each other, rather than by hitting an absolute bar nobody can define.

An **evolution agent** takes top-ranked ideas and refines them — simplifying overcomplicated ones, synthesizing related ones, mutating toward unconventional variants.

A **proximity agent** clusters similar ideas, so the system can see the shape of the landscape it's searching — and notice the regions it hasn't visited.

A **meta-review agent** watches the whole process, extracting recurring critique patterns and feeding them back, so the next generation starts smarter than the last.

The loop improves itself, not just its outputs.

A supervisor coordinates all of it asynchronously, scaling compute up and down as needed.

And the test-time scaling story from Pattern 17 applies directly: feed this loop more compute — more candidates, more tournament rounds, more refinement generations — and measured hypothesis quality climbs.

Three boundary conditions keep this an engineering system rather than an art project.

The novelty-exploitation dial: some protected fraction of each generation is wild swings into new territory; the rest refines proven leaders. The clustering is how you verify the wild swings actually landed somewhere new.

The curiosity budget: exploration is open-ended by nature, so *you* impose the ends — a compute allowance, a generation cap, a stopping rule. Otherwise the loop happily spends forever.

And human-in-the-loop framing: real systems are scientist-in-the-loop. The human sets direction, steers mid-flight, and judges what's worth pursuing — because the agent augments expert judgment rather than replacing it, and because a system generating novel hypotheses needs safety review of both its goals and its outputs.

## The complete interview answer, spoken

"Scoping questions first, because 'discover things' is not yet a design brief.

"What space are we exploring — scientific hypotheses, market opportunities, candidate programs?

"What feedback is available, and how expensive is it — can we test candidates with cheap automated checks, or does real validation mean a wet lab and weeks?

"And who consumes the output — is success 'a domain expert says this is genuinely worth pursuing'?

"Say it's a research-support agent for a biotech team. The space is drug-repurposing hypotheses — existing approved drugs that might treat a different disease. Cheap feedback is literature-grounded critique and ranking; expensive feedback is a lab experiment. The consumers are working scientists.

"That feedback asymmetry is the key constraint, and I'd name it immediately: the design's whole job is to use lots of cheap judgment to decide where the few expensive experiments go.

"The architecture is a generate-test-refine loop staffed by specialist agents. I'd describe it as the scientific method run at machine speed — and it's essentially how Google's co-scientist works, so I'm designing from a proven reference.

```
 research goal (from the human scientist)
      |
      v
 [GENERATE] --many hypotheses--> [REFLECT]  peer-review critique
      ^                              |
      |                              v
 [EVOLVE]  <--top candidates--  [RANK]  tournament, Elo-style
  refine / combine / mutate          |
      |        (meta-review learns   |
      +---- from recurring critiques)+
      |
      v
 shortlist --> human scientist --> real experiment
                 (scientist-in-the-loop)
```

"Generation produces dozens or hundreds of candidate hypotheses, grounded in literature search and pushed toward diversity.

"I explicitly do not want a hundred paraphrases of the most obvious idea — so generation includes techniques like having agents argue opposing positions in simulated debate, which shakes loose the non-obvious candidates.

"Reflection critiques each one like a harsh-but-fair reviewer: consistent with known evidence? Actually novel? Testable with realistic resources?

"Weak candidates die here cheaply, before they cost tournament compute.

"Ranking runs tournaments — pairwise 'which hypothesis is stronger' debates feeding an Elo rating.

"I'd pause on why this matters: 'is this a good hypothesis' has no absolute answer, but 'is A stronger than B' is a judgment both models and experts can render reliably. Enough pairwise judgments aggregate into a trustworthy leaderboard.

"And the co-scientist's validation showed that leaderboard correlating with real accuracy — the internal Elo tracked actual correctness on benchmark problems, which is exactly what you want from a proxy.

"Evolution refines the leaders: merging two related hypotheses into a stronger one, simplifying an overcomplicated mechanism, mutating toward an unconventional variant that generation wouldn't have produced directly.

"And a meta-review agent watches recurring critique themes — say, reviewers keep flagging weak dosage rationale — and feeds that back into generation's instructions.

"The loop improves *itself*, not just its candidates. That's the detail that turns iteration into compounding.

"If the team wanted to go further — actually executing computational experiments, not just proposing them — the same skeleton extends, and there's a working reference in the Agent Laboratory framework.

"It arranges agent roles like an academic lab: a professor agent setting direction, postdoc agents planning and interpreting results, engineer agents writing the experiment code, and a panel of three differently-prompted reviewer agents judging the output like a program committee.

"Three reviewers instead of one is worth noticing: it's self-consistency applied to judgment — multiple perspectives, aggregated, beat any single grader's quirks.

"And discoveries can be shared: a repository where agent-produced findings accumulate so later runs build on earlier ones, the way papers cite papers. Discovery compounds when it's cumulative — for machines as for people.

"Now the exploration-exploitation dial, which I'd manage explicitly rather than hope about.

"Each generation splits its effort: most refines proven high-Elo lineages — exploitation — and a protected fraction, maybe twenty percent, takes wild swings into weakly-explored territory — exploration.

"Protected means protected. Exploitation pressure will always try to eat that budget, because refining a leader always looks locally better than gambling on a stranger.

"The proximity agent's clustering is how I *see* the search. If everything huddles in two clusters, exploration has stalled and the dial turns up. If nothing builds on anything and the leaderboard churns randomly, the dial turns down.

"Naming both failure directions matters: too little novelty polishes mediocrity; too much never compounds.

"Budgets, because open-ended must not mean unbounded.

"The loop gets a compute allowance and a stopping rule — N generations, or stop early when the top-ten leaderboard hasn't meaningfully changed in three rounds. That's diminishing-returns detection: when more compute stops moving the leaders, spend stops.

"The human sets the research goal, steers mid-flight — 'drop that cluster, it's a known dead end; push harder on the inflammation angle' — and owns the final shortlist decision.

"I'd emphasize the framing: this system's product is *better questions for the lab*, not autonomous truth. The expensive resource is experiments, and the agent's job is making each one count.

"Failure modes I'd volunteer unprompted.

"Hallucinated grounding: a hypothesis citing literature that doesn't say what the agent claims. So reflection includes a citation-verification step — check each load-bearing claim against the retrieved source — and anything unverifiable gets marked speculative rather than silently blended into confident prose.

"Judge bias compounding: if the same model family generates and ranks, the system can develop self-reinforcing taste — rewarding its own style rather than quality. I'd diversify: different models or differently-prompted judges in the tournament, plus periodic expert spot-checks of ranking decisions.

"Convergence on the fashionable: literature-grounded generation naturally gravitates toward well-published areas, which means the system can mistake 'heavily studied' for 'promising.' The exploration budget and the clustering view are partly there to fight exactly that gravity — to keep part of the search in the under-published corners where the surprises live.

"Known blind spots, stated with humility: the system reads open literature, so it inherits open literature's gaps — paywalled work it can't see, and negative results that never got published. An experienced scientist knows what *didn't* work in ways the agent structurally cannot. One more reason the human stays in the loop.

"And safety: a system generating novel biochemical hypotheses needs the guardrails pattern applied at both ends — research goals screened at intake for misuse potential, generated hypotheses screened before delivery.

"The co-scientist does exactly this, and adversarial testing across more than a thousand hostile research goals showed it robustly refusing the dangerous ones. For this domain, that's not optional polish; it's table stakes.

"Evaluation is the honest hard part, and I'd meet it head-on: there's no answer key for discoveries, so you evaluate by proxy, in layers.

"Layer one, internal signal: does the Elo of top candidates climb across generations? Does judged quality improve as we spend more compute? The co-scientist showed exactly that curve — more test-time compute, better-rated hypotheses — and it's how you verify the loop works *as a loop*.

"Layer two, expert assessment: scientists rate shortlists for novelty and plausibility, blind, against baselines — the raw model without the loop, and ideally the experts' own best guesses. The co-scientist's outputs beat both in its evaluations, which is the bar to aim at.

"Layer three, the real test: of the hypotheses we sent to the lab, how many validated?

"Slow and small-sample, but it's the metric that justifies the system's existence. And it has been passed in the wild — co-scientist-style systems proposed drug-repurposing candidates later confirmed in vitro against leukemia cell lines, identified novel liver-fibrosis targets that validated in human organoids, and in one famous case independently arrived, in two days, at a hypothesis about how genetic elements spread between bacteria that an independent group had reached after a decade of unpublished work.

"Monitoring in production is mostly cost and diversity: compute per generation, cluster coverage of the search space, leaderboard churn, and expert acceptance rate of shortlists over time.

"Acceptance rate trending down means the system is drifting from what the scientists actually value — that's drift detection, discovery-flavored.

"Cost, frankly: this is a compute-hungry pattern. Hundreds of generations, critiques, and tournament debates can run tens to hundreds of dollars per research goal, and deep multi-week explorations more.

"The comparison that makes it rational is the alternative: expert-months of literature work, and misdirected experiments that cost thousands each.

"If the loop meaningfully raises the hit rate of experiments you were going to run anyway, it pays for itself on the first avoided dead end."

## Follow-ups they will ask

**"How is this actually different from the deep-research agent pattern?"**

"Deep research finds and synthesizes what's already known — the answer exists in documents somewhere, and the job is retrieval plus synthesis. Discovery generates candidates for what *isn't* known yet and filters them through critique and tournaments.

"Research retrieves; discovery proposes. The architectures overlap — both loop, both search — but discovery adds generation of genuinely new candidates, competitive ranking because there's no ground truth to check against, and evolution across generations."

**"Explain exploration versus exploitation like I'm new to it."**

"It's 'try new things' versus 'double down on what works,' and it's a genuine dilemma because both extremes fail.

"All exploitation: you refine your current best idea forever and never find the better one two hills over. All exploration: you sample endlessly and never compound progress on anything.

"The practical management is a protected split — most effort exploits the leaderboard, a fixed fraction explores — with the ratio tuned by watching cluster diversity and leaderboard churn. It's the oldest problem in decision-making under uncertainty, wearing an agent costume."

**"Why tournament ranking instead of just scoring each hypothesis?"**

"Because absolute scores need an absolute standard, and for novel ideas there isn't one — 'rate this hypothesis 7 out of 10' is noise.

"Comparative judgment is far more reliable: 'is A stronger than B, argue it out' is a question judges answer consistently, and many pairwise results aggregate into a stable Elo-style leaderboard. It's the same reason human peer review compares work against a field rather than scoring against a cosmic yardstick."

**"How do you evaluate discovery when there's no right answer?"**

"Layered proxies. Internally: quality metrics rising across generations — is the loop's own selection pressure working? Externally: blind expert ratings of novelty and plausibility against baselines. Ultimately: downstream validation rate — of what we pursued, what panned out. Slow and small-sample, but real.

"The trap to name is proxy-gaming — the system optimizing 'what impresses the judge' instead of 'what's true' — which is why expert spot-checks calibrate the judges and lab results calibrate everything."

**"How do you stop it wasting enormous compute on nonsense?"**

"Budgets and early stopping as first-class design, not afterthoughts. Hard caps per research goal. Diminishing-returns detection on the leaderboard. Cheap reflection filters killing weak candidates before they reach expensive tournament rounds. Human checkpoints between major phases.

"The scaling law says more compute buys better hypotheses, but the curve flattens — you spend to the knee, then hand the shortlist to humans."

**"Where does the human sit — isn't the point autonomy?"**

"The point is *augmentation*, and the strongest real systems are explicit about it — the co-scientist's own framing is scientist-in-the-loop.

"The human sets the goal, steers between generations, and judges what deserves expensive validation. The agent contributes tireless breadth: reading everything, generating and stress-testing hundreds of candidates, running the critique-and-rank machinery around the clock.

"The division plays to strengths — machine does volume, human does taste, responsibility, knowledge of unpublished dead ends, and safety judgment, which for novel-hypothesis generation you never fully delegate."

## Say it in one breath

"Exploration and discovery is for open-ended spaces with no single right answer: a generate-test-refine loop where specialist agents generate candidate hypotheses, critique them like peer reviewers, rank them in Elo-style tournaments, and evolve the winners — the scientific method at machine speed, as in Google's co-scientist. Manage the novelty-versus-exploitation dial with a protected exploration fraction, cap the loop with compute budgets and diminishing-returns stopping, keep a scientist in the loop for steering and safety, and evaluate by proxy layers — internal quality curves, blind expert ratings, and ultimately how many pursued discoveries actually validate — because when there's no answer key, disciplined proxies are the whole game."
