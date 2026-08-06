# Retry budgets: how a well-meaning agent burns your whole budget

Here is a thing that happens to almost everyone who ships their first long-running agent.
You give it a generous allowance — fifty steps, a couple of dollars, five minutes of wall-clock — and you feel like a benevolent god handing out pocket money.
Then you check the logs the next morning and find it spent the whole allowance on step three, politely asking a slightly sick API the same question a few hundred times.

Nobody wrote that behaviour.
It emerged, the way a traffic jam emerges, out of a stack of individually reasonable decisions.
Retries are sensible one at a time and catastrophic when stacked, and agents stack them in ways ordinary software does not.

## The nesting doll problem

Think about a set of Russian nesting dolls, except every doll contains three copies of the next one down.

At the bottom is the HTTP client inside your tool.
Modern SDKs retry automatically — most will quietly try a failed call two or three more times before handing you an error, because that's usually right and it makes the SDK look reliable.
You didn't configure that, and you probably don't know it's on.

One layer up is your tool wrapper, which some sensible engineer wrapped in a retry decorator after reading a blog post about resilience — three attempts, exponential backoff, very tidy.

One layer up from that is the agent loop itself.
The model gets an error back, decides the tool was flaky, and calls it again.
That's not a config setting, that's a *decision the model made*, and no retry library on earth knows about it.

And one layer above *that* is your orchestration framework, which has a notion of "retry the whole step" for robustness.

Four layers, each reasonable in isolation, multiplying into a number nobody designed.

The Amazon Builders' Library makes exactly this point about ordinary distributed systems, with the arithmetic spelled out: if a database is failing and there are five service layers between the client and the database, each retrying three times, "the load on the database will increase 243x, making it unlikely to ever recover."
That's just \\(3^5\\).
Their conclusion is blunt — for most operations, retry at a *single* point in the stack, and nowhere else.
([Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/))

Agents add a fifth layer that AWS didn't have to worry about, because in agents one of the retriers is a language model with opinions.

## Retry amplification, with the arithmetic done out loud

Let's make this visceral, because "amplification" is an abstract word and the numbers are not.

Say you configure an agent with a fifty-step budget.
In your head, "fifty steps" means "up to fifty things happen."
That's the mental model, and it's wrong.

Now say each step, when a tool fails, retries that tool three times before giving up.
Fifty steps times three attempts is a hundred and fifty tool invocations.
Still sounds survivable.

Now add the SDK underneath your wrapper, which quietly retries a 5xx on its own.
Each of those hundred and fifty invocations becomes two actual network calls.
Fifty times three times two is **three hundred requests** hitting the far end — from a budget you described to yourself as "fifty steps."
If the SDK's default is two internal retries rather than one, it's four hundred and fifty.

And that's before the model decides, unprompted, to re-call a tool because it didn't like the answer.
Say it does that on a quarter of the steps.
Now you're comfortably past five hundred.

Here's the part that stings: at no point did anything violate its configured limit.
Every layer stayed inside its own rules.
The rules just multiply, because that's what nested loops do, and nobody owns the product.

The useful habit is to stop thinking in *steps* and start thinking in *leaf calls* — the actual requests that leave your infrastructure and land on someone's server.
When you size a budget, size it in leaf calls, then divide backwards to figure out how many steps that buys you.
If you can only afford two hundred leaf calls and your amplification factor is nine, you have a twenty-two-step agent, and you should tell it so.

## Why agents are worse at this than ordinary software

Three reasons, and they compound.

**The model decides to retry, and no config controls that.**
A retry library retries on an *exception*.
A model retries on *dissatisfaction*.
It called the search tool, got three results, decided they were mediocre, and called it again with slightly different phrasing.
That's not an error path — the tool returned 200 OK — so your retry counters never incremented, your circuit breaker never noticed, and your dashboards show a perfectly healthy system quietly doing four times the work.
This is the single biggest reason agent budgets blow in ways your ops instincts don't predict.

**The agent can't see its own budget unless you tell it.**
This sounds obvious once said and is skipped constantly.
The model has no proprioception — no sense of how much of the run it has used, how much money it has spent, how close it is to the wall.
It'll happily start a careful six-part research plan on step forty-eight of fifty.
You wouldn't send someone shopping without telling them how much cash is in their pocket, and then act surprised at the checkout.

**Failures poison the context, which makes the next attempt dumber.**
Every failed call leaves an error message in the conversation.
Stack traces, timeout notices, JSON blobs of nothing.
Ten retries later, a meaningful chunk of the model's working memory is transcripts of things that didn't work — which is exactly the context drift problem: the further you get into a long run, the more the model's attention is spread across noise instead of the goal.
So the failure mode is doubly nasty.
The retries burn budget *and* they degrade the reasoning that would have found a smarter path.
An agent on its ninth attempt is not just poorer than one on its first; it's also, in a real sense, less intelligent.

## The five ways this actually bites you

Give these names, because naming them is how you spot them in a log at 2am.

**Retry storms.**
A service gets slow.
Every agent talking to it starts retrying.
The retries add load, which makes it slower, which triggers more retries.
The service was going to recover in thirty seconds; instead it stays down for an hour, held under by the very clients trying to reach it.
The AWS write-up puts it nicely: retries are *selfish* — each client demands more resources to improve its own odds, and when everyone is selfish at once the whole thing collapses.

**Budget exhaustion before completion.**
The agent spends forty-eight of fifty steps fighting one stubborn sub-task — a flaky lookup, a permissions issue — and has two steps left for the actual goal.
The tragedy is that the stubborn sub-task was often optional.
It was a nice-to-have enrichment step, and the agent had no way to know it wasn't worth the whole run.

**Silent partial work.**
The budget runs out mid-task, and the run just... stops.
But the agent had already refunded three of seven customers, updated two records, and sent one email.
The world is now in a state no one designed: half-changed, undocumented, and inconsistent.
This is the failure mode that turns a budget problem into an incident, and it's why every consequential action wants an idempotency key and a ledger you can walk backwards.

**Backoff versus deadline.**
Exponential backoff says wait longer each time: one second, two, four, eight, sixteen.
Your user is staring at a spinner with a thirty-second attention span.
Politely backing off is the right thing for the *server* and the wrong thing for the *person*, and if nobody reconciled those two you end up timing out the user in order to be considerate to a machine.
Backoff must always be checked against the remaining deadline; if the nap is longer than the time you have left, don't nap, fail.

**Thrash.**
The agent tries approach A, it fails, so it tries approach B, which also fails, so it goes back to A.
Each attempt looks like a *fresh first attempt* to any retry counter, because the counters are per-approach and the alternation resets them.
The agent is in a loop, it's burning the budget at full speed, and every individual decision looks locally reasonable in the transcript.
Only a view across turns catches this — which is the no-progress watchdog we'll build in the next chapter.

## The toolkit, defined plainly

Now the mechanisms.
Each of these is old and boring in distributed systems, which is exactly why it works.

**Exponential backoff with jitter.**
Backoff means waiting longer between each attempt — one second, then two, then four — so a struggling service gets breathing room instead of a fire hose.
Jitter means randomising that wait — instead of sleeping exactly four seconds, sleep a random amount between zero and four.
Why randomise?
Because a thousand clients that failed at the same instant will, without jitter, all retry at the same instant, and you've built a synchronised wave that knocks the service over again.
Jitter smears them out.
This is the single highest-value line of code in the whole chapter and it's one call to a random number generator.
Use it whenever more than one caller can fail simultaneously — which, for agents running in parallel, is always.

**Retry budgets as a ratio, not a count.**
This is the idea most people haven't met, and it's the one that gives this chapter its title.
A retry *count* is per-call: "try this up to three times."
A retry *budget* is per-system: "across all recent traffic, retries may not exceed 20% of requests."
Twitter's Finagle popularised it — their default allows retries on 20% of requests, on top of a floor of 10 retries per second, implemented as a token bucket whose credits expire after ten seconds.
([Finagle: retry budgets](https://finagle.github.io/blog/2016/02/08/retry-budgets/))
The beauty of the ratio form is that it behaves correctly in both regimes automatically.
One flaky call in a healthy system? Retry freely, you're nowhere near 20%.
Everything failing at once? The budget is instantly exhausted and retries stop — which is precisely when retrying is most harmful.
It's since been adopted in service meshes and is being standardised into the Kubernetes Gateway API. ([GEP-3388](https://gateway-api.sigs.k8s.io/geps/gep-3388/))
Use ratio budgets at the run level; use counts at the individual-call level; you want both.

**Circuit breakers.**
Named after the thing in your electrical panel.
Count recent failures for a dependency, and past a threshold, *open* the breaker — stop calling that service entirely for a while, failing instantly instead of waiting out another timeout.
After a cooldown the breaker goes *half-open*: let one probe call through, and if it succeeds, close the breaker and resume; if it fails, open again.
([Fowler on circuit breakers](https://martinfowler.com/bliki/CircuitBreaker.html))
For agents there's a bonus: an open breaker is a *fact you can put in the prompt*.
"Shipping API is down, breaker open, don't plan around it" lets the model route around an outage at planning time instead of discovering it five steps deep.

**Deadlines that propagate.**
A timeout is a per-call limit: "give up on this request after ten seconds."
A deadline is an absolute point in time — "this whole run must be finished by 14:32:10" — that travels down the call chain, so a sub-agent three levels deep knows it has four seconds left, not ten.
Timeouts alone let a chain of ten well-behaved ten-second calls take a hundred seconds.
Deadlines are what stop that.
If you only add one thing from this section, add deadlines; they subsume a surprising amount of the rest.

**Per-tool caps versus a global run budget.**
These answer different questions and you want both.
A per-tool cap says "no single tool may consume more than six retries across this entire run," which stops one sick dependency from eating everything.
The global run budget says "this run gets fifty steps and two dollars total, however you spend them."
Without per-tool caps, one bad tool takes the whole run hostage; without a global budget, twelve well-behaved tools can each stay under their cap and collectively bankrupt you.

**Retryable versus non-retryable.**
Retrying something that can never succeed isn't resilience, it's a very expensive way of doing nothing.
The rough split:

| Kind | Examples | Retry? |
|---|---|---|
| Transient | 429 rate-limited, 500, 502, 503, 504, connection reset, timeout | Yes, with backoff and jitter |
| Permanent | 400 malformed, 401 unauthorised, 403 forbidden, 404 missing, 422 invalid | No — fix the request or give up |
| Semantic | "insufficient funds", "market closed", "already refunded" | No — the plan is wrong, not the plumbing |

That third row is the agent-specific one.
The call succeeded, HTTP 200, everything green — but the *meaning* is a refusal.
A model that treats "insufficient funds" as flakiness will re-submit that order until the budget dies, and your logs will show a hundred perfectly successful API calls.
Teach the classifier about semantic failures explicitly, because no HTTP status code will do it for you.

**Idempotency keys.**
Idempotent means "safe to do twice" — reading a balance is idempotent, charging a card is emphatically not.
An idempotency key is a unique string you attach to a request so the far side can recognise a duplicate and act once.
Stripe's implementation is the canonical reference: they save the status code and body of the first request for a given key, and any later request with the same key returns that stored result rather than executing again — including stored 500s — with keys pruned after 24 hours.
([Stripe: idempotent requests](https://docs.stripe.com/api/idempotent_requests))
Without this, "retry on timeout" is a coin flip between resilience and double-charging a customer, because a timeout doesn't tell you whether the work happened.

**Compensation for what can't be undone.**
When a run dies halfway through a multi-system change, there is no cross-system rollback button.
The pattern is a saga: every consequential action gets a paired compensating action that reverses it, and you keep a durable ledger of what you actually did, so on failure you can walk it backwards.
([Saga pattern](https://microservices.io/patterns/data/saga.html))
You don't need the vocabulary in an interview.
You need the ledger.

## The agent-specific moves most courses skip

Everything above is standard distributed-systems hygiene.
These next four are what separate someone who read a resilience blog post from someone who has actually run agents.

**Make the budget visible to the model.**
Put the remaining budget in the context, in plain language, every turn.
"You have 12 steps, roughly 11,000 tokens and \$0.22 of budget left."
Something genuinely useful happens when you do this: the model starts *triaging*.
It skips the optional enrichment step.
It stops opening new lines of investigation.
It writes the summary while it still can.
This costs you about thirty tokens a turn and it's the highest-leverage change in this chapter, because it converts a hard external limit into an internal planning constraint the model can actually reason with.

**Force a graceful-degradation finish.**
Pick a threshold — say 20% of budget remaining — and when you cross it, change the instructions.
Not "you're running low," but a hard switch: stop exploring, write the best partial answer you have, and produce a handoff note saying what's done, what isn't, and what you'd try next.
Compare the two possible endings.
An agent that dies mid-thought at step fifty produces nothing and leaves someone guessing.
An agent that spends step forty-eight writing "I confirmed items 1–4, item 5 is blocked on a permissions error from the CRM, here's the ticket ID" has produced something genuinely valuable.
Same budget.
Completely different product.

**Escalate rather than burn the remainder.**
If the agent is stuck and the budget is half gone, spending the other half on the same wall is the worst available option.
Hand it to a human *with the budget it hasn't spent still on the table*, because that remaining budget is what lets the human's follow-up instruction actually get executed.
The design question is choosing the trigger: repeated failures on the same tool, a semantic refusal, a permissions error, or the no-progress signal from the next chapter.

**Account for budget across sub-agents.**
The moment you spawn sub-agents, the naive design gives each one its own fresh budget, and your fifty-step run becomes five sub-agents times fifty steps.
The fix is a shared ledger: the parent holds the budget and hands out *allocations*, sub-agents spend against the shared pool, and the parent sees the true total.
Say it out loud in an interview and you will sound like someone who has been burned, because you will have described the exact mechanism by which people get a surprise invoice.

## A budget ledger you can actually run

Here's a compact, dependency-free version that ties the pieces together.
It tracks four dimensions at once, exposes the remaining budget in a form you can paste straight into a prompt, enforces per-call and per-tool and per-run retry limits, backs off with jitter, refuses to back off past the deadline, distinguishes retryable from non-retryable, and flips a graceful-finish flag when the budget gets thin.

```python
import random
import time


class Retryable(Exception):
    """The world was briefly unhappy. Trying again might genuinely help."""


class NonRetryable(Exception):
    """The request itself is wrong. Trying again can only waste budget."""


RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def raise_for_status(status, note=""):
    if status < 400:
        return
    if status in RETRYABLE_STATUS:
        raise Retryable(f"{status} {note}")
    raise NonRetryable(f"{status} {note}")


class BudgetLedger:
    def __init__(self, max_steps=50, max_tokens=200_000, max_usd=2.00,
                 max_seconds=300.0, finish_at=0.20, retry_ratio=0.20,
                 retry_floor=3, default_tool_retry_cap=6, tool_retry_caps=None,
                 clock=time.monotonic, sleeper=time.sleep, rng=None):
        self.caps = {"steps": float(max_steps), "tokens": float(max_tokens),
                     "usd": float(max_usd), "seconds": float(max_seconds)}
        self.used = {"steps": 0.0, "tokens": 0.0, "usd": 0.0, "seconds": 0.0}
        self.finish_at = finish_at
        self.retry_ratio = retry_ratio
        self.retry_floor = retry_floor
        self.default_tool_retry_cap = default_tool_retry_cap
        self.tool_retry_caps = dict(tool_retry_caps or {})
        self._clock = clock
        self._sleep = sleeper
        self._rng = rng or random.Random()
        self._t0 = clock()
        self.calls = 0
        self.retries = 0
        self.tool_retries = {}
        self.log = []

    def _tick(self):
        self.used["seconds"] = self._clock() - self._t0

    def spend(self, steps=0, tokens=0, usd=0.0):
        self.used["steps"] += steps
        self.used["tokens"] += tokens
        self.used["usd"] += usd
        self._tick()

    def remaining(self):
        self._tick()
        return {k: self.caps[k] - self.used[k] for k in self.caps}

    def fraction_left(self):
        rem = self.remaining()
        return min(max(rem[k], 0.0) / self.caps[k] for k in self.caps)

    def exhausted(self):
        return any(v <= 0 for v in self.remaining().values())

    def should_finish(self):
        return self.exhausted() or self.fraction_left() <= self.finish_at

    def as_prompt_note(self):
        """The whole point: budget the model can actually see."""
        r = self.remaining()
        note = ("BUDGET LEFT: {steps} steps | {tok:,} tokens | {usd:.2f} USD "
                "| {sec:.0f}s").format(steps=int(max(r["steps"], 0)),
                                       tok=int(max(r["tokens"], 0)),
                                       usd=max(r["usd"], 0.0),
                                       sec=max(r["seconds"], 0.0))
        if self.should_finish():
            note += ("\nYou are nearly out of budget. Stop exploring. Spend what is "
                     "left writing the best partial answer you have plus a handoff "
                     "note saying what is done, what is not, and what you would try next.")
        return note

    def _global_retry_allowance(self):
        """Finagle-style: a ratio of traffic, with a small floor."""
        return max(self.retry_floor, self.retry_ratio * self.calls)

    def _backoff(self, attempt, base=0.5, cap=8.0):
        """Full jitter: sleep somewhere in [0, ceiling), not exactly at it."""
        ceiling = min(cap, base * (2 ** attempt))
        return self._rng.uniform(0, ceiling)

    def call_tool(self, name, fn, *args, max_attempts=3, step_cost=1,
                  tokens_per_call=0, usd_per_call=0.0, reserve_seconds=5.0,
                  **kwargs):
        self.calls += 1
        attempt = 0
        while True:
            self.spend(steps=step_cost, tokens=tokens_per_call, usd=usd_per_call)
            if self.exhausted():
                self.log.append((name, attempt, "budget exhausted"))
                raise NonRetryable(f"budget exhausted before '{name}' succeeded")
            try:
                out = fn(*args, **kwargs)
                self.log.append((name, attempt, "ok"))
                return out
            except NonRetryable as exc:
                self.log.append((name, attempt, f"fatal: {exc}"))
                raise
            except Retryable as exc:
                attempt += 1
                if attempt >= max_attempts:
                    self.log.append((name, attempt, "per-call cap"))
                    raise NonRetryable(f"'{name}' failed {max_attempts}x: {exc}")
                tool_cap = self.tool_retry_caps.get(name, self.default_tool_retry_cap)
                if self.tool_retries.get(name, 0) >= tool_cap:
                    self.log.append((name, attempt, "per-tool cap"))
                    raise NonRetryable(f"'{name}' is out of per-tool retries: {exc}")
                if self.retries >= self._global_retry_allowance():
                    self.log.append((name, attempt, "run retry budget spent"))
                    raise NonRetryable(
                        f"run retry budget spent, '{name}' still failing: {exc}")
                wait = self._backoff(attempt - 1)
                if wait > self.remaining()["seconds"] - reserve_seconds:
                    self.log.append((name, attempt, "deadline beats backoff"))
                    raise NonRetryable(f"no time left to back off for '{name}': {exc}")
                self.retries += 1
                self.tool_retries[name] = self.tool_retries.get(name, 0) + 1
                self.log.append((name, attempt, f"retry after {wait:.2f}s"))
                self._sleep(wait)
```

And a demo, with a fake clock so it runs instantly.
The search backend succeeds on every third call, and one tool is permanently broken.

```python
def demo():
    fake_now = [0.0]
    ledger = BudgetLedger(max_steps=12, max_tokens=20_000, max_usd=0.40,
                          max_seconds=90.0, finish_at=0.25, retry_floor=5,
                          clock=lambda: fake_now[0],
                          sleeper=lambda s: fake_now.__setitem__(0, fake_now[0] + s),
                          rng=random.Random(11))
    hits = {"n": 0}

    def flaky_search(q):
        hits["n"] += 1
        raise_for_status(200 if hits["n"] % 3 == 0 else 503, "search backend")
        return f"3 results for {q!r}"

    def broken_lookup(q):
        raise_for_status(400, "malformed filter expression")

    notes = []
    topics = ["refund policy", "shipping SLA", "tax rules", "returns window",
              "warranty terms"]
    for q in topics:
        print(ledger.as_prompt_note())
        if ledger.should_finish():
            print(">> agent decides to wrap up early\n")
            break
        try:
            notes.append(ledger.call_tool("search", flaky_search, q,
                                          tokens_per_call=900, usd_per_call=0.02))
            print(f">> got: {notes[-1]}\n")
        except NonRetryable as exc:
            print(f">> gave up on {q!r}: {exc}\n")

    try:
        ledger.call_tool("lookup", broken_lookup, "id = ???", tokens_per_call=300)
    except NonRetryable as exc:
        print(f">> non-retryable, not retried once: {exc}\n")

    print("PARTIAL RESULT:", notes or "(nothing)")
    print("HANDOFF NOTE: covered", len(notes), "of", len(topics), "topics;",
          "search backend was flapping with 503s.")
    print("calls:", ledger.calls, "retries:", ledger.retries,
          "per-tool:", ledger.tool_retries)


demo()
```

Running it:

```text
BUDGET LEFT: 12 steps | 20,000 tokens | 0.40 USD | 90s
>> got: 3 results for 'refund policy'

BUDGET LEFT: 9 steps | 17,300 tokens | 0.34 USD | 89s
>> got: 3 results for 'shipping SLA'

BUDGET LEFT: 6 steps | 14,600 tokens | 0.28 USD | 88s
>> gave up on 'tax rules': run retry budget spent, 'search' still failing: 503 search backend

BUDGET LEFT: 4 steps | 12,800 tokens | 0.24 USD | 88s
>> got: 3 results for 'returns window'

BUDGET LEFT: 3 steps | 11,900 tokens | 0.22 USD | 88s
You are nearly out of budget. Stop exploring. Spend what is left writing the best
partial answer you have plus a handoff note saying what is done, what is not, and
what you would try next.
>> agent decides to wrap up early

>> non-retryable, not retried once: 400 malformed filter expression

PARTIAL RESULT: ['3 results for ...', '3 results for ...', '3 results for ...']
HANDOFF NOTE: covered 3 of 5 topics; search backend was flapping with 503s.
calls: 5 retries: 5 per-tool: {'search': 5}
```

Read that trace and notice what the machinery bought you.
The run retried where retrying helped, and twice it *worked* on the second or third try.
It gave up on one topic when the run-level retry budget ran dry, rather than letting one flaky topic swallow everything.
It never retried the 400 — not once, because a malformed request is malformed forever.
And it stopped with two steps still in the tank, spending them on a partial answer and a handoff note instead of dying mid-sentence with nothing to show.

Three of five topics plus an honest note about why, delivered on time, is a shippable outcome.
Zero of five topics and a stack trace is an incident.
The difference is about ninety lines of accounting.

## Say it in one breath

"Retries multiply — the SDK retries, the tool wrapper retries, the framework retries the step, and the model decides on its own to call the tool again, so a fifty-step budget quietly becomes five hundred requests; the fix is to count leaf calls rather than steps, retry at exactly one layer with exponential backoff and jitter, cap retries as a *ratio* of traffic rather than a count so retries switch themselves off precisely when everything is failing, propagate a deadline so backoff can't outlive the user's patience, never retry a 400 or a semantic refusal, use idempotency keys so a retry can't double-charge anyone — and then do the agent-specific bit, which is to put the remaining budget in the prompt so the model can triage, and force a graceful finish that spends the last step on a partial answer and a handoff note instead of dying mid-thought."

## What an interviewer is really testing

They already know you can spell "exponential backoff."
What they're listening for is whether you've noticed the four things below.

**Do you think in multiplication or addition?**
The junior answer adds up limits: three retries, fifty steps, fine.
The senior answer multiplies them and asks who owns the product.
If you volunteer the amplification arithmetic unprompted — and especially if you point out that retrying at multiple layers is the bug, not a belt-and-braces feature — you've cleared the bar in one sentence.

**Do you know retries are a *system* property, not a call property?**
Per-call retry counts are table stakes.
Ratio-based retry budgets, circuit breakers, and propagated deadlines say you've thought about what happens when a thousand of these run at once against one struggling dependency.

**Do you distinguish retryable from non-retryable — including the semantic case?**
Anyone can say "retry 5xx, not 4xx."
The differentiator is the third category: the call returned 200, and the *content* is a refusal, and retrying it is the most expensive no-op in your system.

**Do you know what agents add that ordinary services don't?**
This is the real question hiding inside the question.
Three answers earn it: the model retries by *choice*, invisible to your counters; the model can't see its budget unless you inject it; and failed attempts pollute context so late retries are dumber than early ones.
Finish with the graceful-finish idea — that the last 20% of budget should be reserved for producing a useful partial result and a handoff note — and you've described a system somebody would actually be willing to run overnight.

## Further reading

- [Amazon Builders' Library: Timeouts, retries, and backoff with jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) — the canonical write-up, including the 243x example.
- [AWS Architecture Blog: Exponential backoff and jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/) — the experiments behind "full jitter."
- [Finagle: Retry budgets](https://finagle.github.io/blog/2016/02/08/retry-budgets/) — retries as a percentage of traffic.
- [Gateway API GEP-3388: Retry Budgets](https://gateway-api.sigs.k8s.io/geps/gep-3388/) — the same idea being standardised for Kubernetes.
- [Martin Fowler: Circuit Breaker](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Stripe: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- [microservices.io: Saga pattern](https://microservices.io/patterns/data/saga.html)
- [LangGraph: GRAPH_RECURSION_LIMIT](https://docs.langchain.com/oss/python/langgraph/errors/GRAPH_RECURSION_LIMIT) — what a framework-level step cap looks like in practice, and what it does when you hit it.
