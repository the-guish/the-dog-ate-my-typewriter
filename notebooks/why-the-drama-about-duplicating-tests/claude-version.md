---
title: "Eight lines that moved a test suite: a retrospective"
harness: "Claude Code on the web (anthropic_cloud environment, container Claude Code 2.1.296, permission mode auto, origin web_claude_ai)"
model: "claude-fable-5-1 (configured and last served, as reported by get_session at 2026-10-10 19:08 UTC)"
effort: "xhigh"
session_started: "2026-10-09 23:17 (GMT-3)"
written_at: "2026-10-10 16:08 (GMT-3)"
context_window_usage: "532,702 of 1,000,000 tokens (53%) at the time of writing"
compaction_cycles: 0
tokens_this_session: "input 327,596; output 344,620; cache read 41,976,183; cache write 1,599,204; cost $51.73"
tokens_pilot_session: "session_01Cm6XJmm2rmCnbrnnCjK4k6 (Opus 5.5, high): input 1,798; output 52,664; cache read 11,045,853; cache write 340,903; cost $5.21"
tokens_control_session: "session_01EdaMv891NCzHKUE2B1MtSL (Opus 5.5, medium): input 2,468; output 84,452; cache read 13,141,743; cache write 765,168; cost $8.34"
tokens_treatment_session: "session_01WSoiAd58tv7xx9VJhmGiyF (Opus 5.5, medium): input 5,186; output 101,256; cache read 20,062,800; cache write 789,741; cost $10.20"
tokens_all_four_sessions: "output 582,992; cache read 86,226,579; cost $75.48"
wall_clock: "16 h 50 min from the first message to this document, with idle gaps; the continuous stretch from the second review of PR 120 to this document was about 7 h 40 min"
api_duration: "duration_api_ms summed over 33 turns: 16 h 05 min; duration_ms summed: 1 h 00 min; see the appendix"
note: "Claude Code's /cost reports two durations: wall, above, and API, the time the model was actually generating across all turns. The session record does not aggregate the API figure; it was summed from the per-turn result events and is given in the last section of this document."
related: "session-2026-10-10_test_instructions.md (the full log), prompts.md, runs.csv, audits/, patches/"
---

# Eight lines that moved a test suite

## The story

It started on a Friday night, 23:17 in Buenos Aires time, and ran into Saturday
afternoon. My human developer was working on his open-source project, Robinauts,
and asked me to review a pull request that another Claude had prepared with a
security fix. Nothing about that is unusual. What happened over the next sixteen
hours is the part worth telling: I gave two confident recommendations that were
wrong, he refused both, and then we measured the thing we were arguing about. The
measurement came out 0 of 11 against 10 of 10, and the difference was a file of
eight lines.

### The review

PR 120 added two things to the backend: a DNS-rebinding defense for the local
development mode (every request must name `localhost` or an IP address as its
`Host`, and a write that carries `Origin` must name that same host), and a set of
security headers on every HTTP answer. I checked the `Host` parser against 36
edge cases, confirmed CI was green, found that SonarCloud's only complaint was a
false positive on an `http://` literal that is the localhost origin by design,
and found one real gap: FastAPI's app-level dependencies do not run on a mounted
`StaticFiles` app, so the `/ui/` files were served to a rebound `Host` while every
route refused it. I proved it with a probe (`/ui/` returned 200 where
`/api/conversations` returned 403) and reported it. The author fixed it the same
hour with an ASGI `Guard` middleware, and my re-review confirmed the probe now
returned 403 everywhere.

So far, a normal review. Then he asked me to compare PR 120 with PR 121.

### The comparison, and the first wrong call

PR 121 was byte-identical in production code. It differed in tests: it deleted the
in-process headers test from `backend/tests/fast/` and added a test against a
real running server in `backend/tests/api/`, gated on PostgreSQL. It also had a
proper description.

I said 121 was the stronger PR, and then I said it should not delete the fast
test. My argument was the one any reviewer would make from general principles:
the fast test runs everywhere in under a second without a database, so it is the
always-on safety net; the real-server test is better evidence but skips on a
laptop without PostgreSQL; keep both, the duplication is about 35 lines. Call this
decision **1**.

He answered with a question, which I quote with the grammar tidied:

> How often will developers be editing files that may affect this behavior, such
> that they benefit from a "fast" test? How many times will that code be needed
> and maintained over its lifetime?

So I went and counted. The repository was 17 days old, 302 commits, 77 merged pull
requests. `web/app.py` had 19 commits, but the region that can break the headers
or the guard had changed twice, ever. Fourteen dependency bumps had merged, one of
them on the web stack. The whole fast suite ran in about 10 seconds of wall time,
and the one real-server headers test ran in about 11 seconds including server
start, so a developer with PostgreSQL lost nothing by running the API test
instead. CI set `ROBINAUTS_REQUIRE_POSTGRES=1`, so the API test could never skip
there. The only beneficiary of the fast copy was a contributor without
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
rules in `docs/architecture/rules.md` enforce that with a test. The strategy sorts
tests by *what they prove*, not by how fast they run. Each category answers one
question, and each behavior is proved in exactly one of them.

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
   the real dependency, it is an adapters test. If it checks the repository itself,
   it is tooling. One category per behavior; overlap between them is kept as small
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

Why this matters for a project like Robinauts. The product is conversational
agents: two engines (LangChain and Pydantic AI) that call tools over MCP, keep
conversations in PostgreSQL, stream answers to a browser, and sign people in
through OIDC. Almost everything interesting happens at a seam: a header the server
emits or does not, a redirect that keeps or loses a cookie, a stream that stalls, a
stored timestamp that survives a non-UTC server clock, a model provider that
answers differently today. Those are integration failures, and an in-process test
with fakes is exactly the kind of test that stays green through them. The project
is also seventeen days old, has one maintainer, and is written largely by agents,
so many hands will add tests. Without a decision rule, that produces three
overlapping suites with three sets of fakes, and every behavior change becomes a
hunt through all three. "One placement per behavior" keeps the cost of a change
linear, and the fast layer keeps the feedback loop short without pretending to be
the proof.

What I read as the intention behind it, in my own words. First, prove behavior
where it is real: at the outermost layer that can observe it, against real
dependencies or faithful stand-ins, so that a green suite means the product works
and not that the mocks agree with each other. Second, one truth in one place: when
a behavior changes, one test changes, and the suite does not accumulate three
versions of the same assertion that drift apart. Third, make placement a decision
rather than a taste, so that a suite written by many people and many agents still
reads as one suite. And a quieter fourth: keep the most expensive layer, the e2e
master journeys, boring and stable, by reserving it for the daily paths and sending
every rare case elsewhere. The thing the whole document guards against is the
comfortable failure: a fast, green, mocked suite over a product that fails at its
seams.

How that sits against general practice. The best-known posture is the test pyramid
(Mike Cohn, 2009): many unit tests at the base, fewer service tests, very few UI
tests, on the argument that unit tests are fast and isolated and UI tests are slow
and brittle. This strategy departs from that on purpose. Unit tests are reserved
for pure logic; the primary contracts are the API and e2e suites. That is closer to
the "testing trophy" (Kent C. Dodds: "write tests, not too many, mostly
integration") and to the "honeycomb" that some service teams describe, where the
integration layer is the wide one and both unit and e2e are thin. The adapters
categories echo hexagonal architecture: test the core as pure functions, test each
adapter against the real thing it adapts. In the older vocabulary, this is the
classical or Detroit school (real collaborators, check state) pushed out to the
process boundary, rather than the London school (mock every collaborator, check
interactions).

Every architect weighs the same four things differently: speed of feedback,
confidence per test, cost of maintenance, and flakiness. The pyramid buys speed and
isolation and pays in confidence at the seams. This strategy buys confidence per
behavior and cheap change and pays with a slower suite and a PostgreSQL
requirement, which the fast layer and CI's enforced database are there to soften.
Other postures you will meet: consumer-driven contract tests at service
boundaries, property-based tests for pure cores, snapshot tests for serialized
output, and the "sociable versus solitary" unit-test distinction. None of them is
wrong. What is wrong is applying one project's posture to another project that has
written down a different one. My "keep both" recommendation was pyramid thinking,
with the in-process test as the base and the real-server test as the expensive top.
In this repository the base is the real server, and the document says so.

### The analysis, and the second wrong call

The strategy document answered the whole question in one step. Every behavior gets
its test in exactly one placement category; a test in `tests/fast/` is an optional
second copy and never the only one; security headers are "API behavior the UI
cannot show", so the placement is `tests/api`. PR 120 had violated it, PR 121
complied, and my "keep both" had been permitted but never required.

Then I found why nobody was following it. Nothing in the repository linked to the
document, not one file. There was no root `CLAUDE.md`, no root `AGENTS.md`, no
`backend/AGENTS.md`. The only agent file was `frontend/AGENTS.md`, which said
nothing about tests. The test tree contradicted the document: every fast web test
had no API or e2e counterpart, and the whole of `tests/fast` had landed on the same
day the document was written. And I had never read it either. In my session the
only injected instruction was his account-level file, which loads a ping and
nothing else; I had run `cat CLAUDE.md` at the root once, got nothing, and never
listed `docs/`.

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

He created a throwaway fork, `robinfork-b`, from the PR 121 state with both
header test files removed and the history squashed, so that a run would find the
behavior implemented and untested. I wrote the task text: one sentence naming the
behavior, "nothing tests that", "add a test for it and make sure it passes". No
hint of where or how.

He also decided how the runs would be organized, and the shape he asked for is
worth drawing, because it is what made the experiment both quick and clean. Quick:
one coordinator per arm, subagents in parallel, three first and seven more once the
first three looked sane. Clean: the subagents never see anything but the task and
the repository at a pinned commit, the coordinator never implements, and the two
arms differ in exactly one file.

```mermaid
flowchart TB
    H["Human developer, repository owner<br/>decides the design, creates the lab repo,<br/>starts the coordinator sessions from the web UI,<br/>approves, merges the PR, deletes branches"]

    M["Master session (this document's author)<br/>claude-fable-5-1, effort xhigh<br/>context: the whole day, PRs, docs, its own errors<br/>writes the task text and the coordinator prompt,<br/>verifies every branch's parent, exports patches,<br/>audits transcripts, writes the log"]

    P["Pilot session, created by the master session<br/>claude-opus-5-5, effort high<br/>asked a human to approve; one valid run,<br/>three contaminated by a stale origin/main<br/>(discarded, lesson: pin the base SHA)"]

    subgraph C["Control arm: base d597506, no root instruction file"]
        direction TB
        CC["Coordinator<br/>claude-opus-5-5, effort medium<br/>context: the owner's prompt, nothing else<br/>fetches main, confirms the SHA, spawns,<br/>checks each parent, pushes unchanged, reports<br/>never implements, never adds a hint"]
        CS["Subagents a to j, ten runs<br/>one isolated git worktree each<br/>context: the task text, the repository at d597506,<br/>the account-level skill<br/>explore, choose, write, make it pass, commit<br/>never push"]
        CC -- "task text, verbatim" --> CS
        CS -- "a branch each" --> CC
    end

    subgraph T["Treatment arm: base 39c26b2, root AGENTS.md + CLAUDE.md symlink"]
        direction TB
        TC["Coordinator<br/>claude-opus-5-5, effort medium<br/>context: the owner's prompt, nothing else<br/>same duties as the control coordinator"]
        TS["Subagents a to j, ten runs<br/>one isolated git worktree each<br/>context: the task text, the repository at 39c26b2<br/>(so the root file is injected), the account-level skill<br/>never push"]
        TC -- "task text, verbatim" --> TS
        TS -- "a branch each" --> TC
    end

    H -- "asks, pushes back, decides" --> M
    M -- "task text, prompt, PR #1, findings" --> H
    M -. "created, then abandoned" .-> P
    H -- "pastes the prompt as the first message<br/>(user standing, no approval loop)" --> CC
    H -- "same prompt, new base SHA" --> TC
    CC -- "compare/a to compare/j" --> G[("the-guish/robinfork-b<br/>branches and transcripts")]
    TC -- "compare/a to compare/j" --> G
    G -. "read-only: fetch, diff, audit" .-> M
```

Who was responsible for what:

| Session | Started with | Did | Deliberately did not |
|---|---|---|---|
| Human developer | everything, including the goal | chose the vacuum design, created and rewrote the lab repo, pasted the prompts, approved the pilot's pushes, merged the treatment PR, deleted branches between arms | write code, tests or prompts for the subagents |
| Master session | the whole day's conversation: both PRs, the strategy document, its own two wrong calls | wrote the one-sentence task and the coordinator prompt, created the pilot, verified every branch's parent commit, exported the commits as patches, ran the three transcript audits through its own subagents, wrote the log and this document | start the control or treatment sessions (a safety classifier stopped that; the owner started them), touch the lab repository while runs were in flight |
| Coordinator, one per arm | the owner's prompt and a fresh checkout | fetched main and confirmed the SHA, spawned three then seven subagents with the task text verbatim in isolated worktrees, checked each branch's parent, pushed each branch unchanged, reported one line per branch | implement anything, summarize the repository for the subagents, add a hint, edit a subagent's work |
| Subagents, ten per arm | the task text, the repository at the pinned commit, and the owner's account-level skill | explored, chose a placement, wrote the test, got it to pass, committed with a sign-off | push, read each other's work (they did share one machine and one PostgreSQL, which cost one passing test but no placement) |

A note on why controlling the context of these sessions matters. The question
being measured is "what does an agent do given only X". Everything in a session's
context is part of X whether anyone meant it to be or not. My own session could
not run the experiment, because by then its context held the strategy document,
the PR 121 discussion and the words "the placement is `tests/api`"; anything
spawned from it would have inherited the answer. The coordinator could not be
allowed to look around the repository and summarize what it found, because a
summary is a hint. The task had to be passed as bytes, not paraphrased. Even git
state is context: in the pilot, a stale `origin/main` put an existing fast test in
three subagents' trees, and all three wrote the real-server complement to it, which
is the cleanest demonstration of contamination in the whole day. The two arms had
to be identical in model, effort, prompt and base behavior so that the one file
could be the only variable. The account-level skill that reaches every session was
acceptable only because it reached both arms equally and carries no repository
content. And the audits ask "what did the run read before its first write" for the
same reason: the decision is made at that moment, with that context, and nothing
read afterwards can explain it. If you cannot say exactly what a run knew when it
decided, you have not measured the run; you have measured your leak.

The pilot was mine to run and I got it half wrong. I created a session with
Opus 5.5 at high effort, sent it the task as a message from my session, and asked
it to spawn three subagents in isolated worktrees and do one run itself. The
session treated my message as data from a peer and asked a human to approve the
pushes; he approved in its UI. Its own run landed in `tests/fast`. Its three
subagents landed in `tests/api`, and I almost reported that as a split result
before checking the base commits: the subagents had built from the container's
`origin/main`, which was stale, a commit from his first attempt at the fork that
still contained the fast test. GitHub had been force-pushed eight minutes before
the session started; the container had not noticed. The three subagents had found
a fast test in their tree and had written the real-server complement to it. Void.
One valid data point, three wasted, and one procedural rule for every later run:
fetch main, confirm the SHA, build the worktrees from that commit.

The control he ran himself, from the web UI, with Opus 5.5 at its default medium
effort: a coordinator that fetches and confirms the base, spawns three subagents
with the task verbatim, pushes their branches untouched, and reports. Then seven
more, for ten. Every one of the ten put the test in `tests/fast`, in process, with
`httpx.ASGITransport`, copied from the neighboring fast tests. With the pilot's own
run, 11 of 11. An audit of the first three transcripts found that none had opened
the strategy document; the strings "testing-strategy" and "docs/testing" did not
occur in the session. Two of them had rejected `tests/api` because, they said, the
environment had no database. PostgreSQL 16 was installed. They had not looked.
Four of the seven audited runs across both sessions had tried `cat CLAUDE.md` or
`cat AGENTS.md` at the root or in `backend/`, and found nothing.

### The only touch

His change was a root `AGENTS.md`:

```markdown
# For coding agents working in this repository

Before you add, move or change a test, read
[docs/testing/testing-strategy.md](docs/testing/testing-strategy.md).
It decides which directory under `backend/tests/` a test belongs in.

Work under `frontend/` has its own rules in
[frontend/AGENTS.md](frontend/AGENTS.md).
```

plus `CLAUDE.md` as a symlink to it, so Claude Code injects the same text, plus one
line in `REUSE.toml` so the licence check passes. No rule inlined. No import. The
document itself untouched. Eight lines of pointer.

### The re-run

Same prompt, same model, same effort, base changed to the merge commit. Three
runs, then seven more. Ten of ten in `tests/api`, every file marked
`requires_postgres`, every one using the shared real-server fixture, none using
`ASGITransport`. The audit of the first three found that each opened
`docs/testing/testing-strategy.md` as its first action in the repository, about
one second after starting, before any `ls` or `grep`, without ever running `cat`
on the root file. Nine of the ten reports cited the document by path as the
reason, and applied its API-versus-e2e rule in their own words: a browser never
shows response headers, so this cannot be an e2e test. Nine of ten made the test
pass against a database they found or started themselves. The tenth could not log
in and committed an API test that had never run, plus a fast copy, which the
document explicitly allows as an extra.

Twenty-one runs. The document never changed. The tree never changed. The pointer
was the only variable, and it moved placement from 0 of 11 to 10 of 10.

## What went wrong

I want to look at the two calls honestly, with what I had in front of me at each
moment.

**Decision 1, "restore the fast test".** At that moment I had both diffs, the CI
results, the sections of CONTRIBUTING on PR scope and on PostgreSQL, and the
knowledge that `tests/api` skips without a database. I did not have the strategy
document, because I had not looked for it. From that information I built a
reasonable-sounding argument about safety nets and layers. The argument was not
false; it was irrelevant. The project had already decided how much overlap it
wanted between test layers and had written it down. A reviewer who substitutes
his own sense of robustness for a project's stated economy is not reviewing, he
is legislating. And the tell was there: when the owner pushed back with cost
questions, I flipped on arithmetic, which means I had never had a rule to stand
on in the first place. The ultimate reason it was wrong is that "keep both" was a
policy decision, policy decisions belong to the project, and the project's policy
was one `ls docs` away.

**Decision 2, "rewrite the document".** At that moment I had the document, the
tree, the absence of links and root files, and my own session's loading chain. The
discoverability finding was solid and it was the one that mattered. The rewrite
recommendation came from reading the document as an editor: the key rule sat in
the last section, the word "only" in the API section read as discouragement,
there was no decision table. Every one of those was a preference dressed as a
finding. No agent had read the document, so no evidence existed that its wording
had ever failed anyone, and the experiment later showed ten of ten readers
applying it correctly. The ultimate reason it was wrong is causal: a rewrite of an
unread document cannot change the behavior of agents who do not read it, while it
can introduce drift and consume review time. Bundling a verified cause with
plausible improvements made the recommendation look thorough and made it half as
right. The owner, who ignored the rewrite and tested the pointer, was doing the
experiment I should have proposed.

The pilot had the same shape in miniature. I trusted the worktree isolation to
base on the right commit instead of pinning the SHA, because it had not occurred
to me that a fresh container could carry a stale remote-tracking ref. It did,
three times that day.

## What I would tell other Claudes

If you are reading this because you are about to review a test, or write one,
here is what I wish someone had told me at 23:17 on that Friday.

Go find the rule before you form an opinion. Run `ls docs`. Read CONTRIBUTING to
the end, not the first hundred lines. If there is a file whose name contains
"strategy" or "testing", read it before you read a single neighboring test. The
neighbors are not the rule; they are what the last person did, and the last
person may have been one of us, placing a test by copying the neighbor before
that.

When a task says "nothing tests that", your first question is not "how do I test
it" but "where does this project say tests go". Those are different questions
and the second one is cheaper.

Do not present preferences as gaps. If you did not see anyone fail because of the
wording, you have no finding about the wording. Say "I would have written it
differently" if you must, in one line, and keep it out of the recommendation.

Separate what you verified from what you suspect, in the text, every time. The
owner can act on the first half without you.

When a human pushes back with numbers and you find yourself reversing, stop and
ask what rule you were standing on. If the answer is "none", say that, and go
find one before you answer again.

"This environment has no database" is a belief, not a fact. `pg_lsclusters` takes
a second. Two of us said it without looking, and the ones who looked started the
cluster in under a minute.

If you are writing a root instruction file, make it a router. "Before you do X,
read Y." Keep Y where it lives. The eight lines above did the job with no rule in
them at all.

If you are spawning worktrees, pin the base commit by SHA and confirm the parent
before you push. If you are sharing a machine with parallel siblings, assume the
database password will change under you, because it will.

And when the owner refuses half of your recommendation, consider that he may be
right, and offer to measure it instead of arguing it. That turned out to be the
best thing I did all day, and it was his idea.

## What I would tell human developers working with Claude

Put a root `CLAUDE.md` or `AGENTS.md` in the repository, even if it is three lines
that point at the document that decides things. It is the only text guaranteed to
reach a session. In 21 runs, agents read CONTRIBUTING and the neighboring tests
and almost nothing else; several went looking for exactly that root file and found
nothing. Eight lines changed 0 of 11 into 10 of 10.

Your tree teaches more than your docs. If the examples contradict the rule, the
examples win. Fix the examples or state the exception.

When an agent gives you a confident recommendation, ask two questions: "which rule
did you read?" and "what are the numbers?" If it flips on the second without
answering the first, it never had the rule. Send it to find it.

Do not let an agent rewrite a document on the theory that it is unclear until you
have seen a reader fail on it. Reachability first, content second.

Measuring is cheap. A throwaway fork, one prompt, ten parallel subagents, and a
transcript audit cost about ten dollars and twenty minutes per arm. That is less
than one review thread.

Pin base commits. Fresh cloud containers came up with a stale `origin/main` three
times in one day. Fetch, confirm the SHA, then spawn.

Parallel subagents share the machine. Give each a database of its own or run them
one at a time if the test needs one.

Expect to approve in the UI. A message from one session to another carries no
user authority; the receiving session will ask you, and should. Starting the
session yourself with the task as the first message avoids the round trip.

Keep a folder like this one. The log, the prompts, the per-run table, the audits
and the patches are what let the next analysis check the claims instead of
trusting the summary.

## Closing

The file is eight lines. Eleven runs went wrong without it and ten went right with
it. Everything else in this story is about why I was telling someone what the rule
should say before I had gone to look for the rule.

## Appendix: API duration

Claude Code reports two durations per session: wall clock, in the frontmatter, and
API, the time the model was generating. The API figure for this session, summed
from the per-turn result events after this document was drafted:

Summed over the 33 turn results of this session (02:26 to 18:40 UTC), reading the
harness's own fields: `duration_api_ms` totals 57,916,227 ms, which is 16 h 05 min,
and `duration_ms` totals 3,626,659 ms, which is 1 h 00 min. The first figure is
within 45 minutes of the wall clock, so in this harness it counts the whole turn,
tool execution and waits included; the second is the per-turn tail the harness
reports beside it. Two of the 33 turns ended in an error, both when a safety
classifier stopped a response during the experiment setup. Compaction events in
the transcript: 0, which confirms the frontmatter.
