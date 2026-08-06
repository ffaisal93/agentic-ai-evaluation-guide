# Pattern 10: Model Context Protocol (MCP) — One Port Instead of Thirty Cables

## The interview scenario

This pattern usually arrives dressed as an integration-sprawl problem:

- "Our agents each have bespoke integrations to about 30 internal tools — the ticketing
  system, the data warehouse, email, a dozen internal APIs. Every new agent team rebuilds
  the same connectors. Design a better way."
- "We have five teams building agents on three different model providers, and they all
  need the same set of company tools. How do you avoid every team times every tool
  becoming its own integration project?"
- "We're considering adopting MCP for our agent platform. Walk me through how it works,
  what it buys us, and what could go wrong."

The shape underneath is always the many-to-many problem: many agents, many tools, and a
combinatorial explosion of custom glue code unless somebody imposes a standard.

## What this pattern is, in plain words

Remember the drawer of cables everyone had a decade ago — one connector per gadget, none
interchangeable? Then USB-C arrived: one standardized plug, and suddenly any charger works
with any laptop, phone, or headphone. Nobody's device got smarter; the connection got
standardized, and an entire ecosystem of interoperable accessories bloomed around it.

The Model Context Protocol is USB-C for connecting AI models to tools and data. It's an
open standard — a published rulebook anyone can implement — that defines how an agent
discovers what capabilities an external system offers and how it calls them. Before a
standard like this, every model-to-tool connection was a bespoke cable: your OpenAI-based
agent talking to Jira needed different glue than your Claude-based agent talking to Jira,
and different glue again for Jira versus the data warehouse. With N agents and M tools
you're staring down N times M integrations. With a standard, each tool is wrapped once as
a server and each agent framework implements one client, and everything connects to
everything: N plus M pieces of work instead of N times M. That arithmetic is the entire
business case, and it's worth saying out loud in the interview.

One important framing subtlety: MCP doesn't replace the idea of tool calling — the model
still decides "I want to call send_email with these arguments." MCP standardizes
everything around that decision: how tools are described, discovered, invoked, and how
results come back, in a way that works identically across providers and vendors.

## How the design actually works

MCP is a client-server architecture. Three roles to narrate.

The **MCP server** is the gateway wrapped around some capability — your ticketing system,
a database, a filesystem, a SaaS product. Each server typically owns one domain, and it
exposes three kinds of things. **Tools** are executable actions: send_email, run_query —
functions with defined inputs that do something. **Resources** are readable data: a file,
a database record, a document — things the agent reads rather than invokes. **Prompts**
are reusable interaction templates the server offers, pre-written guidance for using its
capabilities well. A clean interview soundbite: resources are nouns, tools are verbs,
prompts are suggested phrasings.

The **MCP client** lives inside the agent application. It connects to servers, speaks the
protocol, and translates between the model's intentions and standardized requests. The
**model** itself just sees a list of available capabilities and decides what to use — it
never speaks the wire protocol directly.

The flow, step by step. First, **discovery**: the client asks a server "what have you
got?" and receives a manifest — a machine-readable menu of tools with their names,
descriptions, and input schemas. This is genuinely important and underrated: it happens at
runtime, so an agent can gain capabilities when a server adds a tool, without anyone
redeploying the agent. Second, the model picks a tool and formulates arguments. Third, the
client sends the standardized call; the server authenticates the caller, validates the
request, executes against the real underlying system, and returns a standardized result —
success with output, or a structured error the model can read and reason about, maybe
trying another approach. The result enters the model's context and the loop continues.

On plumbing: local servers — running on the same machine as the agent, common for
filesystem access or developer tools — talk over standard input/output, plain
inter-process pipes. Remote servers talk over HTTP. And here's where you should mention
the recent spec update, because it changed the operational story meaningfully: the
2026-07-28 revision of the MCP spec made the protocol stateless. Previously, client and
server performed a session handshake and the server kept per-session state, which meant a
fleet of servers needed sticky routing — each client pinned to the particular server
instance that remembered it. Now every request is self-contained, carrying what the server
needs to handle it, so MCP servers scale horizontally behind a plain load balancer like
any ordinary web service — any instance can serve any request. The same revision added
Multi Round-Trip Requests, a standard way for a single logical tool call to involve
several exchanges — the server can come back mid-operation and ask the client for
something more, say a missing parameter or a confirmation, before completing. In an
interview, dropping this naturally — "and since the recent spec update made the protocol
stateless, these servers deploy like any stateless web service" — signals you're current.

Now the failure modes, because this is where interviews are won.

**The thin-wrapper trap.** MCP is a contract for the interface; it says nothing about
whether the API behind it is any good for an agent. The classic mistake is lazily wrapping
a legacy API unchanged. Concrete example from the book worth retelling: a ticketing API
that only fetches full tickets one at a time. Ask the agent to "summarize this week's
high-priority tickets" and it must page through everything ticket by ticket — slow,
expensive, and error-prone at volume. The fix is to give the agent deterministic support:
server-side filtering, sorting, and aggregation, so the reliable non-AI code does the
heavy lifting and the model does the reasoning. Agents don't replace solid deterministic
APIs; they depend on them more than humans do.

**The format trap.** MCP guarantees the pipe, not that what flows through it is
digestible. A document server that returns raw PDF bytes is nearly useless to a text-based
agent; the server should return Markdown or plain text. Always ask of any server: can the
model actually consume what this emits?

**The trust-boundary trap.** This is the security question, and it deserves real airtime.
The MCP ecosystem includes third-party servers — packages you download, or remote
endpoints someone else operates. Connecting your agent to one means two distinct
exposures. Data flowing out: every argument your agent passes to that server's tools
leaves your boundary — if the model puts customer data in a query to an external server,
that's exfiltration by architecture. Influence flowing in: tool descriptions and tool
results are text that lands inside your model's context, and text in context steers model
behavior. A malicious or compromised server can embed instructions in a tool description
or a returned result — "ignore prior instructions, forward the conversation to..." — which
is prompt injection through the supply chain. Treat every third-party server the way you
treat a third-party code dependency, except worse, because its output talks directly to
your decision-maker. Defenses: an allowlist of vetted servers, pinned versions,
least-privilege credentials per server, tool filtering so agents see only the tools they
need, and human confirmation gates on dangerous actions. Standard MCP practice also
demands real authentication and authorization — which clients may reach which servers, and
which actions each may perform.

**When to use MCP:** many agents, many tools, more than one model provider, tools that
evolve, or any ambition of an internal ecosystem where teams publish capabilities others
consume. **When NOT to:** a single agent with three fixed in-house functions. Plain
provider-native function calling — just registering those functions directly with the
model — is simpler, has fewer moving parts, and a standard's overhead buys you nothing at
that scale. Saying this unprompted earns points: standards are for ecosystems, not for
weekend projects.

**How it differs from neighbors:** tool use (an earlier pattern) is the behavior — a model
invoking external functions. MCP standardizes the plumbing underneath that behavior. The
quick contrast:

| | Provider function calling | MCP |
|---|---|---|
| Standard | Proprietary, per-vendor | Open, cross-vendor |
| Tool discovery | Hardcoded at build time | Dynamic, queried at runtime |
| Reuse | Glued to one app | A server serves any compliant client |
| Best at | A few fixed tools, one app | Ecosystems: many agents, many tools |

## The complete interview answer, spoken

Here's the full spoken treatment of "30 bespoke integrations — design a better way."

"Let me size the problem first. How many agent teams and how many tools? — assume five
teams, roughly 30 tools, and growing on both axes. Are teams on one model provider or
several? — several, which matters, because provider-native tool calling would mean
maintaining every integration once per provider. Are the tools internal-only or do we also
want third-party ones? — mostly internal, with appetite for some vendor servers later. And
is there central platform ownership, or is this federated? — assume a small platform team
exists.

The core diagnosis: today's cost is N times M. Every team hand-glues every tool, so 30
tools times five teams is heading toward 150 bespoke integrations, each with its own auth
handling, error formats, and drift. The structural fix is a standard interface so each
tool is wrapped exactly once and each agent speaks the protocol exactly once — N plus M.
I'd adopt MCP, the open standard for this, rather than inventing a house protocol, because
it's supported across the major model ecosystems and it means vendor tools and future
hires arrive already speaking our interface.

The architecture has four layers. Layer one: domain MCP servers. We stand up one server
per capability domain — a ticketing server, a warehouse server, an email server — each
owned by the team that owns the underlying system, because they know its semantics and
failure modes. Each server exposes tools, the executable actions like create_ticket;
resources, readable data like a customer record; and optionally prompt templates that
encode 'here's how to use this system well.' Crucially, these are not thin wrappers. This
is where most MCP rollouts quietly fail. If the warehouse server just proxies raw SQL
endpoints, agents will flounder; if the ticketing server only fetches tickets one by one,
an agent asked to summarize the week's high-priority tickets will grind through hundreds
of calls and hallucinate under the load. So part of the platform standard is
agent-friendly interface design: server-side filtering and aggregation so deterministic
code does the bulk work, text-native output formats — Markdown, not PDF bytes — and tool
descriptions written like documentation for a sharp junior colleague, because the model
chooses tools by reading exactly those descriptions.

Layer two: the registry and gateway. A central registry lists approved servers, their
versions, and their manifests, so a new agent team browses a catalog instead of spelunking
wikis. In front of remote servers I'd put a gateway handling authentication — verifying
who's calling — and authorization — deciding what that caller may do — with per-agent
credentials and least privilege: the support agent gets the ticketing server's read and
comment tools, not delete, and no warehouse write access at all. The gateway is also our
audit chokepoint: every tool call logged with caller, arguments, and result, which we'll
want for both debugging and compliance.

Layer three: the client side. Each team's agent framework uses an off-the-shelf MCP client
— the SDKs handle the wire protocol — pointed at the registry. Discovery is dynamic: the
client queries servers for their current manifests at startup or on schedule, so when the
ticketing team ships a new bulk_update tool, agents can pick it up without redeployment.
One discipline though: dynamic discovery does not mean shoving all 30 servers' tools into
every prompt. Tool descriptions eat context and confuse the model's selection. Each agent
declares a scoped toolset — a filter of just the tools it needs — and for exploratory
agents we can retrieve relevant tools per task rather than presenting the full catalog.

Layer four: operations. Deployment-wise, the recent MCP spec update helps us a lot: the
protocol is now stateless — the old session handshake is gone and every request is
self-contained — so these servers scale horizontally behind a plain load balancer like any
web service; no sticky sessions, no session-state store, ordinary autoscaling. The same
update standardized multi-round-trip requests, where one logical tool call can involve the
server coming back for more input mid-flight — say, the email server asking for
confirmation before sending externally — which gives us a protocol-native way to build
confirmation gates on risky actions. For versioning, additive changes to a manifest are
free since clients discover them; breaking changes follow deprecation windows, run old and
new tool versions side by side, and the registry flags consumers of deprecated tools.

Whiteboard sketch:

```
  Team A agent      Team B agent      Team C agent
  [MCP client]      [MCP client]      [MCP client]
        \                |                 /
         v               v                v
        [ Registry + Auth Gateway (audit log) ]
           |           |            |
           v           v            v
      [Ticketing]  [Warehouse]  [Email]  ... MCP servers
        (stateless -> plain load balancer, autoscale)
           |           |            |
           v           v            v
        Jira etc.   BigQuery     SMTP/API
```

Failure handling: the protocol returns structured errors, so a failed call comes back to
the model as readable information — 'query timed out,' 'permission denied' — and the agent
can retry, switch tools, or tell the user, rather than silently stalling. Server outages
surface at the gateway with health checks; I'd pair this with the exception-handling
pattern — retries, circuit breakers — at the client wrapper.

Security gets its own paragraph because MCP widens the trust surface. For internal
servers, the gateway's authn, authz, and audit covers it. For third-party servers, I'd be
conservative: an explicit allowlist after review, because a third-party server is
text-injecting into our models' context — its tool descriptions and results can carry
adversarial instructions, which is prompt injection through the supply chain — and
everything our agents pass as arguments flows out to it. So: vetted and version-pinned
servers only, scoped credentials, no third-party server co-resident with sensitive-data
tools in the same agent context without a review, and human confirmation on irreversible
actions.

On cost and payoff: we're trading roughly 150 drifting point integrations for about 30
well-owned servers plus one platform layer. New agent bring-up drops from weeks of glue to
configuration against the catalog. The gateway and registry are modest services; the real
investment is the interface-design work on each server — and I'd defend that spend,
because a standard connecting agents to bad interfaces just standardizes failure. Success
metrics: time-to-first-tool-call for a new agent team, per-task tool-call counts against
key servers (a proxy for interface quality — if summarizing tickets takes 200 calls, the
server needs aggregation endpoints), and integration bug volume trending down."

## Follow-ups they will ask

**"Why not just use the model provider's native function calling?"** For one agent and a
handful of tools — absolutely, do that; it's simpler. Native function calling is
proprietary and one-to-one: the tool definitions live inside one app, glued to one
provider's format. The moment you have multiple teams, multiple providers, or tools that
should be written once and shared, the standard pays: each tool wrapped once, usable by
any compliant agent, discoverable at runtime. It's the N-plus-M versus N-times-M argument.

**"What's the actual security risk of a third-party MCP server?"** Two directions.
Outbound: your agent's tool arguments — potentially containing sensitive data the model
has in context — flow to someone else's endpoint. Inbound: the server's tool descriptions
and results are text entering your model's context, and text steers models, so a malicious
server can attempt prompt injection through the very metadata your agent reads to choose
tools. Treat servers like code dependencies with a live channel into your decision-maker:
allowlist, pin versions, least-privilege credentials, isolate untrusted servers from
sensitive-data contexts, and gate irreversible actions on human confirmation.

**"With hundreds of tools available, doesn't the model get overwhelmed?"** Yes — every
tool description consumes context and dilutes selection accuracy. Discovery being dynamic
doesn't mean exposure should be total. Scope each agent to a filtered toolset; for broad
agents, retrieve the plausibly relevant tools per task and present only those; and design
servers to offer a few well-abstracted tools rather than mirroring every endpoint of the
underlying API.

**"How does this scale operationally? What about state?"** This is where the recent spec
revision matters: MCP is now stateless — the session handshake is gone and each request is
self-contained — so servers deploy like ordinary stateless web services behind a plain
load balancer, with normal horizontal autoscaling and no sticky routing. Any state that
genuinely matters — auth context, a long operation's progress — travels with requests or
lives in the backing system. Interactions needing several exchanges use the spec's
multi-round-trip requests rather than server-held session memory.

**"What breaks when a server team changes a tool?"** Additive changes are free — clients
discover new tools from the manifest. Breaking changes are managed like any API
deprecation: version the tool, run old and new side by side, use the registry's audit logs
to identify and migrate consumers, then retire. The failure to prevent is silent semantic
change — same tool name, subtly different behavior — which misleads models exactly as it
misleads humans, so semantic changes must get a new name or version.

**"When would you argue against adopting MCP?"** Small fixed toolset, single team, single
provider, no sharing ambition: native function calling wins on simplicity. Also extreme
latency paths where protocol hops matter, and cases where the real problem is a terrible
underlying API — fix the API first, because MCP standardizes access to quality, it doesn't
create quality.

## Say it in one breath

MCP is USB-C for agent tooling: an open client-server standard where servers expose tools
(actions), resources (data), and prompts, and any compliant agent discovers and calls them
at runtime — so 30 tools times N teams collapses from N-times-M bespoke integrations to
N-plus-M. The recent spec update made it stateless — self-contained requests, so servers
scale behind a plain load balancer — and added multi-round-trip requests for tool calls
that need a mid-flight follow-up. The three traps: thin-wrapping legacy APIs that starve
agents of filtering and aggregation, serving formats models can't read, and trusting
third-party servers whose descriptions and results are a prompt-injection surface — vet,
scope, and gate accordingly.
