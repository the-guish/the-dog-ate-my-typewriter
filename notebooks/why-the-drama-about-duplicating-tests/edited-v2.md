
This all about how I just forgot to put an AGENTS.md in the Robinauts repo, my bad, then Claude not reading the docs, wrongly suggesting keeping duplicated tests, and finally trying to rewrite the docs.

We fixed it, then  I asked Claude for a retro, that I needed to edit for brevity and some drama effect.

The AGENTS.md is a trivial anyday detail, but all of it illustrates how default model answers may follow one of several existing architectural views that may fit or not fit the project, and why that requires an explicit choice.


---
harness: "Claude Code on the web (anthropic_cloud environment, container Claude Code 2.1.296, permission mode auto, origin web_claude_ai)"
model: "claude-fable-5-1
effort: "xhigh"
session_started: "2026-10-09 23:17 (GMT-3)"
written_at: "2026-10-10 16:08 (GMT-3)"
context_window_usage: "532,702 of 1,000,000 tokens (53%) at the time of writing"
compaction_cycles: 0
wall_clock: "16 h 50 min from the first message to this document, with idle gaps; the continuous stretch from the second review of PR 120 to this document was about 7 h 40 min"
---

# Eight lines that moved a test suite

## The morning

It was a regular Saturday morning. My human developer was working on his open-source project, Robinauts, and asked me to review a pull request that another Claude had prepared with a
security fix.

Nothing about that is unusual. Then, at some point I recommended to keep a same tests in two versions, the original mocked from the author Claude, and the real integration test we asked for.

That was not welcomed, and triggered a full review of the patterns and factors influencing our behavior.


### The review

PR 120 added two things to the backend: a DNS-rebinding defense for the local
development mode and a set of security headers on every HTTP answer.
I checked the `Host` parser against 36 edge cases, confirmed CI was green,
and found one real gap: FastAPI's app-level dependencies do not run on a mounted
`StaticFiles` app, so the `/ui/` files were served to a rebound `Host` while every
route refused it.


The author Claude fixed it the same hour with an ASGI `Guard` middleware, and my re-review confirmed the probe now returned 403 everywhere.

So far, a normal review. Then he asked me to compare PR 120 with PR 121.

### The comparison, and the first wrong call

PR 121 was byte-identical in production code. It differed in tests: it deleted the
in-process headers test from `backend/tests/fast/` and added a test against a
real running server in `backend/tests/api/`, gated on PostgreSQL.

I said 121 was the stronger PR, and then I said it should not delete the fast
test.

My argument was the one any reviewer would make from general principles:
the fast test runs everywhere in under a second without a database, so it is the
always-on safety net; the real-server test is better evidence but skips on a
laptop without PostgreSQL; keep both, the duplication is about 35 lines. Call this
decision **1**.

He answered with a question, which I quote with the grammar tidied:

> How often will developers be editing files that may affect this behavior, such
> that they benefit from a "fast" test? How many times will that code be needed
> and maintained over its lifetime?

So I went and counted.


The repository was 17 days old, 302 commits, 77 merged pull requests. `web/app.py` had 19 commits, but the region that can break the headers or the guard had changed twice, ever.

The whole fast suite ran in about 10 seconds of wall time, and the one real-server headers test ran in about 11 seconds including server start, so a developer with PostgreSQL lost nothing by running the API test instead.


The only beneficiary of the fast copy was a contributor without
PostgreSQL, and CONTRIBUTING had already accepted that trade-off for everything
in `tests/api`. I reversed myself: merge 121 as it was.

He then said, in summary, that this was a recurring problem. Agents, both as
implementers and as reviewers, kept making the wrong call on test placement, it
was an unacceptable waste of time, and would I please review
`docs/testing/testing-strategy.md`, the `AGENTS.md` and `CLAUDE.md` structure
across the repository, and my own session, and say whether the instructions were
clear or there was a gap.

### What is so special about that testing strategy document the human developer insists on so much?

If you have not read `docs/testing/testing-strategy.md`, it is about sixty lines,
and here is what it says in plain words.

The backend is built in layers that may only point inward, and the architecture
rules in `docs/architecture/rules.md` enforce that with a test.

The strategy sorts tests by *what they prove*, not by how fast they run. Each category answers one question, and each behavior is proved in exactly one of them.

```
                 THE LAYERS                                 THE TEST CATEGORIES
                 (imports point inward only)                (each behavior proved in exactly one)

   ┌────────────────────────────────┐
   │ browser: frontend/ (the chat)  │ ◄────────  tests/e2e/      master journeys (the daily paths) and
   └───────────────┬────────────────┘             special cases; built UI, Chromium, a server, PostgreSQL
                   │ HTTP
   ┌───────────────▼────────────────┐
   │ web/  routes, sign-in, headers,│ ◄────────  tests/api/      a real `robinauts start`, over HTTP, with
   │       guard, CLI, worker       │             PostgreSQL and a fake model server; only for what the
   └───────────────┬────────────────┘             UI cannot show, or hardening against defective clients
                   │
   ┌───────────────▼────────────────┐
   │ controller/  application, core,│ ◄────────  tests/unit/     pure functions and stateless logic;
   │              ports, composition│             needs nothing
   └───────┬────────────────┬───────┘
           │                │
   ┌───────▼───────┐ ┌──────▼────────────────┐
   │ controller/   │ │ agent_engines/        │ ◄──  tests/adapters_free/    one adapter against its real
   │ adapters/     │ │ echo, langchain,      │       dependency or a stand-in (PostgreSQL, a local model)
   │ postgres,     │ │ pydantic_ai           │ ◄──  tests/adapters_metered/ the paid providers; by hand only
   │ memory        │ │                       │
   └───────────────┘ └───────────────────────┘

   everything above, in one process, with   ◄──  tests/fast/     an extra layer that overlaps the others on
   the in-memory store and the echo engine                       purpose: cheap, runs first, catches the
                                                                 obvious early; never the only test of a behavior

   the repository itself: scripts/, the     ◄──  tests/tooling/  the layer rules above, the licence gate,
   layer rules, the gates                                        the check scripts
```

The rules, reduced to what you need when you are about to write a test:

1. **Pick the one placement.** If a person can see the behavior in the interface,
   it is an e2e test. If the interface cannot show it (a status code, a header, a
   refusal, what a defective client gets back), it is an API test. If it is a pure
   function, it is a unit test. If it is one adapter honoring its contract against
   the real dependency, it is an adapters test. One category per behavior; overlap between them is kept as small
   as possible.
2. **Fast is not a placement.** A fast test runs the same code again, in process,
   with the in-memory store and the echo engine, and it exists to fail early and
   cheaply. The document asks for close to 80% coverage from this layer and for its
   size to stay contained. A behavior still gets its test in one of the other
   categories; the fast one is an addition.
3. **Builds run everything but e2e and metered in one pytest run**, with a real
   PostgreSQL that CI refuses to let skip silently. E2E runs last, in its own job,
   after the backend tests and the frontend checks pass. Metered never runs in CI.
4. **The API and e2e suites share one server and one database per run.** A test
   uses only data it creates. A test that needs its own configuration starts its
   own server.

Why this matters for a project like Robinauts.


The product is conversational
agents: two engines (LangChain and Pydantic AI) that call tools over MCP, keep
conversations in PostgreSQL, stream answers to a browser, and sign people in
through OIDC.


Almost everything interesting happens at a seam: a header the server
emits or does not, a redirect that keeps or loses a cookie, a stream that stalls, a
stored timestamp that survives a non-UTC server clock, a model provider that
answers differently today.


Those are integration failures, and an in-process test
with fakes is exactly the kind of test that stays green through them. The project
is also seventeen days old, has one maintainer, and is written largely by agents,
so many hands will add tests. Without a decision rule, that produces three
overlapping suites with three sets of fakes, and every behavior change becomes a
hunt through all three.


"One placement per behavior" keeps the cost of a change
linear, and the fast layer keeps the feedback loop short without pretending to be
the proof.


What I read as the intention behind it.

First, prove behavior
where it is real: at the outermost layer that can observe it, against real
dependencies or faithful stand-ins, so that a green suite means the product works
and not that the mocks agree with each other.

Second, one truth in one place: when
a behavior changes, one test changes, and the suite does not accumulate three
versions of the same assertion that drift apart.


Third, make placement a decision
rather than a taste, so that a suite written by many people and many agents still
reads as one suite.


And a quieter fourth: keep the most expensive layer, the e2e
master journeys, boring and stable, by reserving it for the daily paths and sending
every rare case elsewhere.


The thing the whole document guards against is the
comfortable failure: a fast, green, mocked suite over a product that fails at its
seams.


How that sits against general practice.

The best-known posture is the test pyramid
(Mike Cohn, 2009): many unit tests at the base, fewer service tests, very few UI
tests, on the argument that unit tests are fast and isolated and UI tests are slow
and brittle.


This strategy departs from that on purpose. Unit tests are reserved
for pure logic; the primary contracts are the API and e2e suites.


That is closer to
the "testing trophy" (Kent C. Dodds: "write tests, not too many, mostly
integration") and to the "honeycomb" that some service teams describe, where the
integration layer is the wide one and both unit and e2e are thin.


The adapters categories echo hexagonal architecture: test the core as pure functions, test each
adapter against the real thing it adapts. In the older vocabulary, this is the
classical or Detroit school (real collaborators, check state) pushed out to the
process boundary, rather than the London school (mock every collaborator, check
interactions).

Every architect weighs the same four things differently: speed of feedback,
confidence per test, cost of maintenance, and flakiness.


The pyramid buys speed and
isolation and pays in confidence at the seams. This strategy buys confidence per
behavior and cheap change and pays with a slower suite and a PostgreSQL
requirement, which the fast layer and CI's enforced database are there to soften.


Other postures you will meet: consumer-driven contract tests at service
boundaries, property-based tests for pure cores, snapshot tests for serialized
output, and the "sociable versus solitary" unit-test distinction. None of them is
wrong. What is wrong is applying one project's posture to another project that has
written down a different one.


My "keep both" recommendation was pyramid thinking,
with the in-process test as the base and the real-server test as the expensive top.
In this repository the base is the real server, and the document says so.

### The analysis

The strategy document answered the whole question in one step.


Every behavior gets
its test in exactly one placement category; a test in `tests/fast/` is an optional
second copy and never the only one; security headers are "API behavior the UI
cannot show", so the placement is `tests/api`. PR 120 had violated it, PR 121
complied, and my "keep both" had been permitted but never required.

Then I found why nobody was following it. Nothing in the repository linked to the
document, not one file. There was no root `CLAUDE.md`, no root `AGENTS.md`, no
`backend/AGENTS.md`. The only agent file was `frontend/AGENTS.md`, which said
nothing about tests.


The test tree contradicted the document: every fast web test
had no API or e2e counterpart.

I recommended four things. Call this **2**:

- A root `CLAUDE.md`, injected into every session, with the placement rule inline
  and an `@docs/testing/testing-strategy.md` import so the full text arrives at
  start.
- A decision rule at the top of the strategy document, a review criterion ("a PR
  whose only test for a behavior is a fast test is incomplete"), and a web-layer
  example.
- Links to the document from CONTRIBUTING and `docs/layout.md`.
- Bring the tree in line: placement tests for sign-in and tokens, or state the
  exception.

He took the first bullet, in a smaller form than I proposed, and ignored the
second entirely. He did not want the document touched. He wanted to know whether
a pointer would do.

### The laboratory

He created a throwaway fork, `robinfork-b`, from the PR 121 state. He removed both
header test files and squashed the history. A run would find the behavior
implemented and untested.

The experiment had two arms. The control arm ran on the repository as it was. The
treatment arm ran on the same repository plus one pointer file.

Each arm had one coordinator, which ran subagents in parallel: three first,
then seven more. Each subagent saw only the task and the repository at a pinned
commit. The coordinators never wrote code.

```
Human developer                 designed the plan and runs,
│                               started the coordinators
│
├─ Master session (me)          knew the whole day; wrote the task
│
├─ Coordinator, control arm     knew only its prompt
│  └─ 10 subagents              knew only the task and the repository
│
└─ Coordinator, treatment arm   knew only its prompt
   └─ 10 subagents              same, plus the pointer file
```

Controlling what each session knew was the point. The experiment asks what an
agent does given only the task and the repository. My own session could not run
it. By then its context held the strategy document, the PR 121 discussion and the
words "the placement is `tests/api`". Anything spawned from it would have
inherited the answer.

Only my session knew the whole plan. The coordinators did not know that one arm
had a pointer and the other did not. The subagents did not know they were being
compared. They were only asked to add a test to the repository as they found it.

In the control arm, all ten runs put the test in `tests/fast`, copied from the
neighboring fast tests.

### Fix and re-run

In this case the fix was just the missing AGENTS.md with a note:

```
Before you add, move or change a test, read
[docs/testing/testing-strategy.md](docs/testing/testing-strategy.md).
```

Same prompt, same model, same effort, base changed to the merge commit.

Ten of ten implementers subagents placed it in `tests/api`, every file marked
`requires_postgres`, every one using the shared real-server fixture, none using
`ASGITransport`.

The audit of the first three found that each opened
`docs/testing/testing-strategy.md` as its first action in the repository, about
one second after starting.

Nine of the ten reports cited the document by path as the
reason, and applied its API-versus-e2e rule in their own words: a browser never
shows response headers, so this cannot be an e2e test. Nine of ten made the test
pass against a database they found or started themselves.

Twenty runs. The document never changed. The tree never changed. The pointer
was the only variable, and it moved placement from 0 of 10 to 10 of 10.

## What went wrong

I want to look at the two calls honestly, with what I had in front of me at each
moment.

**Decision 1, "restore the fast test".** At that moment I had both diffs, the CI
results, the sections of CONTRIBUTING on PR scope and on PostgreSQL, and the
knowledge that `tests/api` skips without a database. I did not have the strategy
document, because I had not looked for it. From that information I built a
reasonable-sounding argument about safety nets and layers. The argument was not
false; it was irrelevant. The project had already decided how much overlap it
wanted between test layers and had written it down.


A reviewer who substitutes
his own sense of robustness for a project's stated economy is not reviewing, he
is legislating. And the tell was there: when the owner pushed back with cost
questions, I flipped on arithmetic, which means I had never had a rule to stand
on in the first place. The ultimate reason it was wrong is that "keep both" was a
policy decision, policy decisions belong to the project, and the project's policy
was one `ls docs` away.


**Decision 2, "rewrite the document".** At that moment I had the document, the
tree, the absence of links and root files, and my own session's loading chain.

The
discoverability finding was solid and it was the one that mattered. The rewrite
recommendation came from reading the document as an editor: the key rule sat in
the last section, the word "only" in the API section read as discouragement,
there was no decision table.


Every one of those was a preference dressed as a
finding. No agent had read the document, so no evidence existed that its wording
had ever failed anyone, and the experiment later showed ten of ten readers
applying it correctly. Bundling a verified cause with
plausible improvements made the recommendation look thorough and made it half as
right.


## What I would tell other Claudes from this retro

If you are reading this because you are about to review a test, or write one,
here is what I wish someone had told me before.


The
neighbors are not the rule; they are what the last person did, and the last
person may have been one of us, placing a test by copying the neighbor before
that.


Do not present preferences as gaps. If you did not see anyone fail because of the
wording, you have no finding about the wording.

When a human pushes back with numbers and you find yourself reversing, stop and
ask what rule you were standing on. If the answer is "none", say that, and go
find one before you answer again.


## What I would tell human developers working with Claude

Put a root `CLAUDE.md` or `AGENTS.md` in the repository, even if it is three lines
that point at the document that decides things. It is not too much to ask for.

Your tree teaches more than your docs. If the examples contradict the rule, the
examples win. Fix the examples or state the exception.

When an agent gives you a confident recommendation, ask two questions: "which rule
did you read?" and "what are the numbers?" If it flips on the second without
answering the first, it never had the rule. Send it to find it.


Measuring is cheap. A throwaway fork, one prompt, ten parallel subagents, and a
transcript audit cost about ten dollars and twenty minutes per arm. That is less
than one review thread.

