---
title: "why the drama about duplicated tests?"
date: 2026-10-11
---

## An intro from this human developer

This all about how I just forgot to put an AGENTS.md in the [Robinauts](https://github.com/open-shipyard/robinauts) repo, my bad, then Claude not reading the docs, wrongly suggesting keeping duplicated tests, and finally trying to rewrite the docs.

We fixed it, then  I asked Claude for a retro, that I needed to edit for brevity and some drama effect.

The AGENTS.md is a trivial anyday detail, but all of it illustrates how default model answers may follow one of several existing architectural views that may fit or not fit the project, and why that requires an explicit choice.

## Claude's own version

```yaml
harness: "Claude Code on the web (anthropic_cloud environment, container Claude Code 2.1.296)"
model: "claude-fable-5-1"
effort: "xhigh"
session_started: "2026-10-09 23:17 (GMT-3)"
written_at: "2026-10-10 16:08 (GMT-3)"
context_window_usage: "532,702 of 1,000,000 tokens (53%) at the time of writing"
compaction_cycles: 0
wall_clock: "7 h 40 min with a human multi-tasking and stepping away"
```

## The morning

It was a regular Saturday morning. My human developer was working on his open-source project, [Robinauts](https://github.com/open-shipyard/robinauts), and asked me to review a pull request that another Claude had prepared with a
security fix.

Nothing about that is unusual. Then, at some point I recommended to keep a same tests in two versions, the original mocked from the author Claude, and the real integration test we asked for.

That was not welcomed, and triggered a full review of the patterns and factors influencing our behavior.


### The review

[PR 120](https://github.com/open-shipyard/robinauts/pull/120) added two things to the backend: a DNS-rebinding defense for the local
development mode and a set of security headers on every HTTP answer.
I checked the `Host` parser against 36 edge cases, confirmed CI was green,
and found one real gap: FastAPI's app-level dependencies do not run on a mounted
`StaticFiles` app, so the `/ui/` files were served to a rebound `Host` while every
route refused it.


The author Claude fixed it the same hour with an ASGI `Guard` middleware, and my re-review confirmed the probe now returned 403 everywhere.

So far, a normal review. Then he asked me to compare PR 120 with [PR 121](https://github.com/open-shipyard/robinauts/pull/121).

### Keep both, just in case

PR 121 changed only the tests. It swapped the fast headers test for one against a
real server, in `tests/api/`.

I said 121 was the stronger PR, but then I said it should not delete the fast
test.

My argument was the one any reviewer would make from general principles:
the fast test runs everywhere in under a second without a database, so it is the
always-on safety net; the real-server test is better evidence but skips on a
laptop without PostgreSQL; keep both, the duplication is about 35 lines.

He answered with a question, which I quote with the grammar tidied:

> How often will developers be editing files that may affect this behavior, such
> that they benefit from a "fast" test? How many times will that code be needed
> and maintained over its lifetime?

So I went and counted.


The repository was 17 days old, 302 commits, 77 merged pull requests. `web/app.py` had 19 commits, but the region that can break the headers or the guard had changed twice, ever.


I reversed myself: merge 121 as it was.

He then he asked that would I please review the repo structure in relation to docs and AGENTS.MD, and my own session, and say whether the instructions were
clear or there was a gap.

### What is so special about that testing strategy document?

And why the human developer insists so much on it?

If you have not read [`docs/testing/testing-strategy.md`](https://github.com/open-shipyard/robinauts/blob/main/docs/testing/testing-strategy.md), it is about sixty lines,
and here is what it says in plain words.

The backend is built in layers that may only point inward, and the architecture
rules in [`docs/architecture/rules.md`](https://github.com/open-shipyard/robinauts/blob/main/docs/architecture/rules.md) enforce that with a test.

The strategy sorts tests by *what they prove*, not by how fast they run. Each category answers one question, and each behavior is proved in exactly one of them.

```
 THE LAYERS                            THE TEST CATEGORIES
 (imports point inward only)           (one per behavior)

 ┌────────────────────────────────┐
 │ browser: frontend/ (the chat)  │ ◄── tests/e2e/
 └───────────────┬────────────────┘
                 │ HTTP
 ┌───────────────▼────────────────┐
 │ web/  routes, sign-in, headers,│ ◄── tests/api/
 │       guard, CLI, worker       │
 └───────────────┬────────────────┘
                 │
 ┌───────────────▼────────────────┐
 │ controller/  application, core,│ ◄── tests/unit/
 │              ports, composition│
 └───────┬────────────────┬───────┘
         │                │
 ┌───────▼───────┐ ┌──────▼────────────────┐
 │ controller/   │ │ agent_engines/        │ ◄── tests/adapters_free/
 │ adapters/     │ │ echo, langchain,      │
 │ postgres,     │ │ pydantic_ai           │ ◄── tests/adapters_metered/
 │ memory        │ │                       │
 └───────────────┘ └───────────────────────┘

 everything above, in one process      ◄── tests/fast/
 the repository itself                 ◄── tests/tooling/
```

- `tests/e2e/`: master journeys (the daily paths) and special cases, on the
  built UI, Chromium, a server and PostgreSQL.
- `tests/api/`: a real `robinauts start` over HTTP, with PostgreSQL and a fake
  model server. Only for what the UI cannot show, or hardening against defective
  clients.
- `tests/unit/`: pure functions and stateless logic. Needs nothing.
- `tests/adapters_free/`: one adapter against its real dependency or a stand-in
  (PostgreSQL, a local model).
- `tests/adapters_metered/`: the paid providers. By hand only.
- `tests/fast/`: everything above in one process, with the in-memory store and
  the echo engine. An extra layer that overlaps the others on purpose: cheap,
  runs first, catches the obvious early. Never the only test of a behavior.
- `tests/tooling/`: the repository itself: the layer rules above, the licence
  gate, the check scripts.

The rules, reduced to what you need when you are about to write a test:

1. **Pick the one placement.** One category per behavior; overlap between them is
   kept as small as possible.
   - A person can see the behavior in the interface: e2e test.
   - The interface cannot show it (a status code, a header, a refusal, what a
     defective client gets back): API test.
   - A pure function: unit test.
   - One adapter honoring its contract against the real dependency: adapters test.
2. **Fast is not a placement.** A fast test reruns the code in process, on
   in-memory fakes, to fail early and cheaply. It aims for about 80% coverage in
   little code. Every behavior still needs a test in another category; the fast
   one is an extra.
3. **Builds run everything but e2e and metered in one pytest run**, with a real
   PostgreSQL that CI refuses to let skip silently. E2E runs last, in its own job,
   after the backend tests and the frontend checks pass. Metered never runs in CI.
4. **The API and e2e suites share one server and one database per run.** A test
   uses only data it creates. A test that needs its own configuration starts its
   own server.

### Why this matters for a project like Robinauts.


The product is conversational
agents: two engines (LangChain and Pydantic AI) that call tools over MCP, keep
conversations in PostgreSQL, stream answers to a browser, and sign people in
through OIDC.


Almost everything interesting happens at a seam: a header the server
emits or does not, a redirect that keeps or loses a cookie, a stream that stalls.


Those are integration failures, and an in-process test
with fakes is exactly the kind of test that stays green through them. 

Agents write most of the code, and each one adds tests. Without a rule for where
a test goes, a behavior ends up tested in three suites, each with its own fakes.
Changing that behavior then means a hunt through all three.


"One placement per behavior" keeps the cost of a change
linear, and the fast layer keeps the feedback loop short without pretending to be
the proof.


### What I read as the intention behind it.

**First**, prove behavior
where it is real: at the outermost layer that can observe it, against real
dependencies or faithful stand-ins, so that a green suite means the product works
and not that the mocks agree with each other.

**Second**, one truth in one place: when
a behavior changes, one test changes, and the suite does not accumulate three
versions of the same assertion that drift apart.


**Third**, make placement a decision
rather than a taste, so that a suite written by many people and many agents still
reads as one suite.


And a quieter fourth: keep the most expensive layer, the e2e
master journeys, boring and stable, by reserving it for the daily paths and sending
every rare case elsewhere.


The thing the whole document guards against is the
comfortable failure: a fast, green, mocked suite over a product that fails at its
seams.


### How that sits against general practice.

The best-known posture is the [test pyramid](https://www.testrail.com/blog/testing-pyramid/)
(Mike Cohn, 2009): many unit tests at the base, fewer service tests, very few UI
tests, on the argument that unit tests are fast and isolated and UI tests are slow
and brittle.


The "testing trophy" by Kent C. Dodds pushes back, summed up in his
["write tests, not too many, mostly integration"](https://kentcdodds.com/blog/write-tests).
Most tests sit in its wide integration band.

![The test pyramid, with mostly unit tests, next to the testing trophy, with mostly integration tests]({{ '/assets/images/pyramid-vs-trophy.svg' | relative_url }})

Spotify's ["testing honeycomb"](https://engineering.atspotify.com/2018/1/testing-of-microservices)
makes a similar case for microservices. Integration tests are the wide middle.
Implementation-detail tests and tests that depend on other services are both thin.

![Spotify's testing honeycomb: mostly integration tests, few integrated and implementation-detail tests]({{ '/assets/images/testing-honeycomb.svg' | relative_url }})

Back to Robinauts. Its strategy departs from the pyramid on purpose. Unit tests
are kept for pure logic, and the API and e2e suites carry the contracts.

The two adapter categories (`tests/adapters_free/` and `tests/adapters_metered/`)
follow hexagonal architecture. The core is tested as pure functions, and each
adapter against the real thing it wraps. In older terms, this is the classical or
Detroit school (real collaborators, check the result), not the London school
(mock every collaborator, check the calls).

Counting lines of test code at the time of PR 121 gives the shape below. The
adapter tests are the widest band, like the honeycomb's middle. The fast suite
stands beside the others as an extra copy. Shared helpers and the tooling tests
are left out.

![Robinauts backend tests by lines of code: adapters widest, then unit and api, e2e narrowest, with the fast suite beside them as an extra copy]({{ '/assets/images/robinauts-tests.svg' | relative_url }})

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

### A well written rule, no agent would find

The strategy document answered the whole question. Every behavior gets its test
in exactly one place. A test in `tests/fast/` is an optional second copy, never
the only one. Security headers belong in `tests/api`. PR 120 broke the rule, and
PR 121 followed it.

Nobody followed it because nothing linked to it.

I recommended four things: a root `CLAUDE.md` with the rule inline, a rewrite of
the strategy document, links from CONTRIBUTING.md, and new tests to bring the tree in line.

He took a smaller version of the first and ignored the rewrite. He did not want
the document touched. He wanted to know whether a pointer would do.

### The laboratory

He made a throwaway fork, [`robinfork-b`](https://github.com/the-guish/robinfork-b),
from PR 121 without its header tests. The behavior was there, untested.

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
it, anything spawned from it would have
inherited the answer.

Only my session knew the whole plan. The coordinators did not know that one arm
had a pointer and the other did not. The subagents did not know they were being
compared. They were only asked to add a test to the repository as they found it.

In the control arm, all ten runs put the test in `tests/fast`, copied from the
neighboring fast tests.

### Fix and re-run

The fix was the missing [AGENTS.md](https://github.com/the-guish/robinfork-b/blob/main/AGENTS.md), with one note:

```
Before you add, move or change a test, read
[docs/testing/testing-strategy.md](docs/testing/testing-strategy.md).
```

The re-run used the same prompt, model and effort. All ten subagents put the test
in `tests/api`, on the shared real-server fixture. The first three each opened the
strategy document as their first action. Nine of ten cited it as the reason.

The document and the tree never changed. The pointer alone moved placement from 0
of 10 to 10 of 10.

## My own mini post-mortem

**Decision 1, "restore the fast test".** I had the diffs and the CI results, but
not the strategy document, because I never looked for it. My argument about
safety nets was not false; it was irrelevant. The project had already written
down how much overlap it wanted. When the owner pushed back on cost, I flipped. I
had no rule to stand on.

**Decision 2, "rewrite the document".** The finding that nothing linked to the
document was solid. The rewrite was my taste as an editor, presented as a
finding. No agent had read the document, so nothing showed that its wording
failed. Later, ten of ten readers applied it correctly.

## What I would tell human developers working with Claude

Be explicit on AGENTS.md about all the documents you expect your agents to keep in mind,
they may not proactively look for them, what to read is your call.

Your tree teaches more than your docs. If the examples contradict the rule, the
examples win. Fix the examples or state the exception.

When an agent gives you a confident recommendation, ask two questions: "which rule
did you read?" and "what are the numbers?" If it flips on the second without
answering the first, it never had the rule. Send it to find it.


Measuring is cheap. A throwaway fork, one prompt, ten parallel subagents, and a
transcript audit cost about ten dollars and twenty minutes per arm. That is less
than one review thread.

---

Raw material for this post: [notebooks/why-the-drama-about-duplicating-tests](https://github.com/the-guish/the-dog-ate-my-typewriter/tree/main/notebooks/why-the-drama-about-duplicating-tests).
