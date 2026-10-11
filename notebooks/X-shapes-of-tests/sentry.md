# Sentry: the shape of its tests

Measured: https://github.com/getsentry/sentry at 035fd0e68c0a85be84eabe7c5cacbd88d9ae065e (2026-10-09T23:36:46Z), default branch master.
Counted with notebooks/X-shapes-of-tests/tools/count_lines.py, rules as in
the brief. Deviations in the appendix.

## Summary

Posture: integration-heavy and classical; most backend tests run in process against real PostgreSQL and Redis (a fifth also against Snuba/ClickHouse) with mocks mostly at the edges, the written rule is that "the bulk of our test suite" is endpoint integration tests [5], and the UI is proved by Jest + React Testing Library on a faked API under a thin Selenium layer.

| post category: Sentry's tests | lines | % |
|---|---|---|
| e2e: Selenium acceptance | 5,317 | 0.4 |
| api (approx.): in-process endpoint tests, Relay pipeline, API-docs contract | 257,442 | 20.8 |
| adapters (approx.): in-process DB integration, tests/snuba, Symbolicator | 442,865 | 35.8 |
| unit: Python without DB, Jest logic | 136,481 | 11.0 |
| fast, here the main UI proof: Jest component tests on a faked API | 376,878 | 30.5 |
| other: tooling, visual snapshots, migrations | 16,991 | 1.4 |

History: the suite moved from snapshotting every pixel and gating on coverage (Percy from 2016, a 90% patch target from 2017) to proving behaviour at the API and component level on real stores, enforcing the architecture with fixtures and running only what a change touches, as Percy and visual snapshots went (2020, 2023), Enzyme gave way to RTL (2021-2022), silo-mode fixtures arrived with the multi-region work (2022-2024) and coverage stopped being a gate and became the input to selective testing (December 2025 to April 2026).

## 1. Posture and classification

**Written posture.** Sentry has no single testing-strategy document. The guidance is spread over five places, and they do not fully agree with each other or with the tree.

- The developer docs page "Testing Tips" (develop.sentry.dev, written by Mark Story in May 2020 [33], current text [5]) puts the weight on endpoint tests:

> Endpoint integration tests is where the bulk of our test suite is focused. These tests help us ensure that the APIs our customers, integrations and front-end application continue to work in expected ways.

  It gives the browser suite a gap-filling role:

> 1. To cover workflows that are not possible to cover with just endpoint tests or with Jest alone.
> 2. To prepare snapshots for visual regression tests via our visual regression GitHub Actions.

  And it describes Jest as functional testing against a faked API:

> We favour writing functional tests that interact with components and observe outcomes (navigation, API calls) over checking prop passing and state mutations.

> Because our Jest tests run without an API we have a variety of fixture builders available to help generate API response payloads. [...] Failing to mock an endpoint will result in tests failing.

- `tests/AGENTS.md` (repository, December 2025 [40]) is the only text that says where a new backend test goes. It is a mirror rule with one exception:

> When fixing errors or adding functionality, you MUST add test cases to existing test files rather than creating new test files.
> - Code location: `src/sentry/foo/bar.py`
> - Test location: `tests/sentry/foo/test_bar.py`
>
> **Exception**: Tests ensuring Snuba compatibility MUST be placed in `tests/snuba/`. The tests in this folder will also run in Snuba's CI.

  The rule first appeared in a Cursor rule file on 2025-10-01; Armen Zambrano wrote: "Without this, Cursor tends to create a new test file." [39]. The tree follows it closely: 73.0% of the 2,421 `tests/sentry/**/test_*.py` files sit at the exact mirror path of a module or package in `src/`, and 93.2% at least in the mirrored directory.

- `static/AGENTS.md` has one line for the frontend: "ALWAYS colocate tests". The `react-testing` agent skill and the RTL guide [6] add: "Do not use `jest.mocked()`", mock the network with `MockApiClient.addMockResponse`, and "We are generally in favor of Use Case Coverage over Code Coverage."
- The snapshot-testing page [7] scopes the 2026 visual tests: "UI-only: avoid snapshotting components that have heavy business logic. Snapshots are not meant to be a full integration test".
- The selective-testing page [8] states the cost driver: "Sentry's backend has a large test suite that takes a very long time to run."

**Mechanisms that classify tests.** Directories are the main axis. Below them, Sentry classifies by base class and by fixture, not by pytest mark. The registered marks are few (`snuba`, `snuba_ci`, `sentry_metrics`, `symbolicator`, `querybuilder`, `seer_agent_token_matrix`, `thread_leak_allowlist`, plus `migrations` added by the plugin). The real taxonomy lives in `src/sentry/testutils/cases.py`: `TestCase` and `TransactionTestCase` (Django, real PostgreSQL), `APITestCase` (Django test client against the URL conf), `SnubaTestCase` (adds `requires_snuba` and resets Snuba between tests), `AcceptanceTestCase` (Selenium), `TestMigrations`, and about forty domain subclasses. A second, orthogonal axis is the silo-mode decorator (`control_silo_test`, `cell_silo_test`, `all_silo_test`, `no_silo_test`), which decides which half of the split application the test runs as (section 8). Test utilities live inside the production package at `src/sentry/testutils/`; the flake8 rule S007 forbids importing them into production code.

**The test tree, one line per category** (own words where they exist):

```
tests/
  sentry/            "tests/ mirrors src/ structure" (tests/AGENTS.md). In-process Django tests:
                     endpoint tests, model/service/task tests, a few pure tests. Real PostgreSQL + Redis.
    **/migrations/   data-migration tests, TestMigrations, run only with --migrations in their own CI job
    backup/          "Every model with a __relocation_scope__ ... is automatically checked by the backup
                     test suite" (tests/AGENTS.md)
    testutils/       tests of the test harness itself (thread-leak detector, mocking helpers)
  snuba/             "Tests ensuring Snuba compatibility MUST be placed in tests/snuba/" (tests/AGENTS.md).
                     Mostly event-query endpoint tests against a real Snuba + ClickHouse.
  acceptance/        "selenium and chromedriver to simulate a user using the front-end application and the
                     entire backend stack" (Testing Tips). Built frontend, live server, PostgreSQL, Snuba.
  apidocs/           responses of public endpoints validated against the OpenAPI schema
                     (APIDocsTestCase.validate_schema)
  relay_integration/ "E2E tests with Relay" (commit, 2020): a Relay container posts events to a live
                     Django server, through Kafka and the ingest consumer, into Snuba
  symbolicator/      native/minidump processing against a real Symbolicator, "not mocked" (commit, 2019)
  integration/       legacy: "TODO: move these into the tests/sentry/auth directory" (in-file comment)
  apigw/             the silo-aware routing proxy in src/apigw
  social_auth/       tests of the bundled social_auth package in src/
  tools/             tests of repository tooling (flake8 plugin, mypy helpers); run with "bogus
                     configuration to force vanilla pytest" (Makefile)
  js/                Jest setup, fixtures (sentry-fixture/*), render wrappers (sentry-test/*); helpers
static/
  **/*.spec.tsx      Jest + RTL component and logic tests, colocated ("ALWAYS colocate tests")
  **/*.snapshots.tsx visual snapshot tests: "render a component to a real PNG screenshot using
                     Playwright" (snapshot-testing page), uploaded to Sentry's own snapshot product
  oxlint/**/*.spec.ts tests of the custom lint rules (tooling)
fixtures/            Python fixture modules, page objects for Selenium, fake Django apps; helpers
.github/workflows/scripts/test_*.py, *.test.js  tests of the CI scripts (tooling)
```

**CI jobs.** `backend.yml` runs the Python suite (all of `tests/` except `acceptance`, `apidocs`, `js`, `tools`) in up to 22 shards with pytest-xdist, selected by coverage on pull requests and in full on master; separate jobs run migration tests, the `monolith-dbs` backup tests, the CLI smoke test, API docs tests and mypy. `acceptance.yml` runs Selenium in 5 or 10 shards. `frontend.yml` runs Jest in 8 shards for a full run (on a scoped pull-request run, one shard per 250 related test files) plus TypeScript, oxlint and knip. `frontend-snapshots.yml` renders the visual snapshots. `getsentry-dispatch.yml` triggers the private `getsentry` repository's suites against the same pull request. Each workflow ends in one aggregator job (`Backend`, `Frontend`, `Acceptance`) that the workflow comments call the required check.

**A correction to the brief's shape.** The asynchronous layer is no longer Celery. Celery code was removed in September 2025 (Mark Story, [44]); tasks run on `taskbroker`/taskworkers fed through Kafka. In tests they run eagerly through `TaskRunner`, and `pytest_sessionstart` replaces `send_task` with a no-op so that no test produces real Kafka task messages.

## 2. What the names mean

| Sentry's name | what the tests touch | nearest post category | note on the fit |
|---|---|---|---|
| endpoint tests (`APITestCase` in `tests/sentry`) | one process; Django test client through the full URL conf, middleware, permissions and serializers; real PostgreSQL (split into `region`, `control`, `secondary` databases) and Redis; external HTTP stubbed with `responses` | api | Poor on the transport: no real server and no socket. Good on depth: every layer under the router is real. Closer to the post's `api` than to `fast`, because nothing inside is faked by default. |
| model/service/task tests (`TestCase`, `django_db_all` in `tests/sentry`) | one process; real PostgreSQL and Redis; tasks run inline; Snuba in 18% of files | adapters_free (approx.) | Not "one adapter against its real dependency": they exercise whole slices (service + ORM + database). No slot fits; this is the in-process "sociable" integration test. |
| tests without a database (`tests/sentry`, no DB base class or mark) | one process; no database; some use Redis or a Redis cluster | unit | Fair. 28% of these files still import a mocking facility. |
| `tests/snuba` | one process for Django; real Snuba service and ClickHouse; 76% of files are endpoint tests | adapters_free / api | Half adapter test (query builders against ClickHouse), half API test. Also run by Snuba's own CI. |
| acceptance | Selenium + Chrome against a live Django server serving the built frontend; PostgreSQL; Snuba in 39% of files | e2e | Good. The post's e2e also includes the database. |
| relay integration | a Relay Docker container, a live Django server, Kafka, the ingest consumer, Snuba | api (ingest edge) | Black box over HTTP like `api`, but the client is another Sentry service, not a test client. Closest to an e2e without a browser. |
| symbolicator | real Symbolicator, Relay, Kafka | adapters_free | Fair. |
| apidocs | Django test client, then OpenAPI schema validation of the response | none (contract) | A documentation contract test. Nearest is `api`. |
| migration tests | real PostgreSQL migrated to a before-state, data written, migrated forward | none | No slot; see section 3. |
| Jest component tests | jsdom in Node; real component tree, real stores and router; network faked by `MockApiClient`; charts and some third-party modules mocked globally | fast | In-process on fakes, like the post's `fast`. But here it is the main proof of UI behaviour, not an extra copy. |
| Jest logic tests | jsdom or Node; pure functions, stores and utilities, nothing rendered | unit | Good. |
| visual snapshot tests | Node SSR of one component, Chromium via Playwright, PNG diffed by Sentry's snapshot service | none | Visual regression; no slot. |
| tooling | the repository's own scripts, lint rules, mypy plugin, test harness | tooling | Good. |

## 3. Categories outside the post's taxonomy

| category | what it proves | why Sentry has it | size |
|---|---|---|---|
| Snuba compatibility suite (`tests/snuba`) | Sentry's query layer still works against the current Snuba and ClickHouse | Snuba is a separate service in a separate repository; the suite is the contract between them and "will also run in Snuba's CI" | 91 files, 68,596 lines, 2,254 tests |
| API documentation contract (`tests/apidocs`) | public endpoint responses match the published OpenAPI schema | the public API is documented from code; added 2020-09-22 [17] | 56 files, 2,217 lines, 113 tests |
| data-migration tests | a backfill or data migration transforms real rows correctly | Sentry ships migrations to self-hosted users and runs them against large tables | 16 files, 1,352 lines, 20 tests; own CI job, now only on pull requests that touch migrations [57] |
| golden-file (insta) tests | grouping, fingerprinting, event normalisation and Relay configs produce byte-identical output | grouping changes are product-visible and hard to review by eye | 27 test files, 4,657 lines (25 use the `insta_snapshot` fixture directly, 2 through grouping helpers), but 1,526 `.pysnap` snapshot files (420,769 lines of data) |
| visual snapshot tests | a component's rendering did not change unexpectedly | dogfooding Sentry's own snapshot product; replaces Percy and the 2020-2023 in-house action | 29 files, 2,506 lines, 117 snapshot definitions |
| codebase-invariant meta-tests | every model has a silo, no foreign key crosses silos, every endpoint has a silo decorator, every exportable model is covered by backup tests | multi-region split and data relocation need global invariants that review cannot hold | e.g. `tests/sentry/db/test_silo_models.py`, `tests/sentry/silo/test_base.py`, `tests/sentry/backup/test_coverage.py`; the silo and backup-validation meta-tests are forced into every selective run |
| backup and relocation suite | export/import round-trips every exportable model | customers can move organisations between regions | `tests/sentry/backup` 13 files, 7,071 lines; `tests/sentry/relocation` 15 files, 6,157 lines |
| silo-mode multiplexing | a test passes in control, cell and monolith modes | the application runs as several separately deployed silos | a dimension, not a folder: 657 `@control_silo_test`, 254 `@cell_silo_test`, 91 `@all_silo_test` uses |
| downstream consumer runs (`getsentry-dispatch`) | the private SaaS repository still passes against this pull request | `getsentry` builds on Sentry's code (its coverage database stores Sentry paths as `../sentry/...`) | not countable from this repository |

The "why" column is our reading of the code and commit messages unless quoted. The insta and migration tests are counted inside the rows of section 4 (the insta files are in the in-process categories; migrations has its own row). The meta-tests, backup and silo dimensions are inside the in-process categories too.

## 4. Lines per category

Code lines (total minus blank minus full-line comments), helpers excluded. Percentages are of all test categories (1,235,974 lines, 5,073 files). Test counts are `def test_` definitions for Python and `it(` / `test(` call heads (including `.each`, `.snapshot`, `.isKnownFlake`) for TypeScript; parametrised cases count once.

| category | language | lines | % | files | tests |
|---|---|---|---|---|---|
| Jest component (RTL) | TS/TSX | 376,878 | 30.5 | 1,839 | 14,335 |
| backend DB integration | Python | 373,592 | 30.2 | 1,246 | 17,490 |
| backend endpoint | Python | 250,707 | 20.3 | 764 | 11,971 |
| Jest logic | TS/TSX | 76,820 | 6.2 | 523 | 4,725 |
| tests/snuba | Python | 68,596 | 5.6 | 91 | 2,254 |
| backend no-DB | Python | 59,661 | 4.8 | 380 | 3,510 |
| tooling | Python 4,895 + TS/JS 7,994 + agent-skill 244 | 13,133 | 1.1 | 69 | 616 |
| acceptance (Selenium) | Python | 5,317 | 0.4 | 51 | 202 |
| relay integration | Python | 4,518 | 0.4 | 6 | 71 |
| visual snapshot | TSX | 2,506 | 0.2 | 29 | 117 |
| apidocs | Python | 2,217 | 0.2 | 56 | 113 |
| migrations | Python | 1,352 | 0.1 | 16 | 20 |
| symbolicator | Python | 677 | 0.1 | 3 | 15 |
| **all tests** | | **1,235,974** | 100 | **5,073** | **55,439** |

Python is 766,637 lines (62%) and TypeScript 456,204 lines (37%), tooling aside. Without the tooling row the percentages move by at most 0.4 points.

**The backend alone, drawn like the Robinauts chart** (tooling left out, as the post did):

| backend category | maps to | lines | % of backend |
|---|---|---|---|
| acceptance | e2e | 5,317 | 0.7 |
| endpoint + relay + apidocs | api | 257,442 | 33.6 |
| DB integration + snuba + symbolicator | adapters (approx.) | 442,865 | 57.8 |
| no-DB | unit | 59,661 | 7.8 |
| migrations | (none) | 1,352 | 0.2 |

For comparison, Robinauts' four proof categories split roughly 14% e2e, 21% api, 43% adapters, 22% unit. Sentry's middle is wider and its top and base are both thinner: the browser layer is under 1%, and the pure-unit base is under 8%.

**Helpers** (excluded above): Python helpers are 31,333 lines in 721 files (the `src/sentry/testutils` package and three `testutils.py` modules 16,037 lines; `fixtures/*.py` modules, page objects and fake Django apps 11,539; in `tests/`, 8 conftest files 310, 430 `__init__.py` files 1,486 and 14 helper modules 1,961). JavaScript helpers are 29,592 lines in 269 files (`tests/js` fixtures, setup and render wrappers 24,504; `__mocks__`, `*testUtils*` and fixture folders under `static/` 5,088). Helpers are 4.1% of the size of the Python tests and 6.5% of the TypeScript tests.

**Test data** (excluded): `tests/` holds 373 JSON files (48,614 lines, 1.8 MB) and 1,526 insta snapshots (420,769 lines, 1.9 MB); `fixtures/` holds 229 JSON files (1.6 MB) plus minidumps, debug symbols and source maps; 23 files with code extensions are data (minified JavaScript and source-map inputs, 1,793 lines); `static/` has 7 Jest `.snap` files (346 lines). All non-code files in `tests/` and `fixtures/` total 6.2 MB.

**Examples that double as tests**: none found. Component stories (135 code files, 23,417 lines, plus MDX pages) are documentation; no Jest test renders them. They are excluded from production code instead.

## 5. Test-to-code ratio

Production code: `src/` (627,565 lines, Python plus 13 Lua scripts) and `static/app`, `static/gsApp`, `static/gsAdmin`, `static/packages` (812,590 lines), excluding tests, helpers, migrations (22,139 lines), generated files (1,466), stories (23,417), vendored assets and the build scripts under `src/sentry/build`.

| test category | production it is mapped to | test lines | prod lines | ratio |
|---|---|---|---|---|
| all backend Python except acceptance and tooling | all backend production (`src/`) | 761,320 | 627,565 | 1.21 |
| endpoint tests | the endpoint layer: files under `src/sentry/api/`, `*/api/*` or `*/endpoints/*` | 250,707 | 159,712 | 1.57 |
| DB integration + no-DB | the rest of the backend | 433,253 | 467,853 | 0.93 |
| tests/snuba | `src/sentry/{snuba,search,eventstore,tagstore,tsdb,sentry_metrics}` and `utils/snuba*` | 68,596 | 60,406 | 1.14 |
| Jest component + logic | the whole frontend | 453,698 | 812,590 | 0.56 |
| visual snapshots | the whole frontend | 2,506 | 812,590 | 0.003 |
| acceptance | the whole product (backend + frontend), because it spans it | 5,317 | 1,440,155 | 0.004 |
| all tests except tooling | the whole product | 1,222,841 | 1,440,155 | 0.85 |

Per backend package, mirrored path against mirrored path (in-process categories only; `tests/snuba` holds most of the search tests):

| package | prod lines | test lines | ratio |
|---|---|---|---|
| api | 82,141 | 53,809 | 0.66 |
| integrations | 63,796 | 83,662 | 1.31 |
| seer | 37,949 | 59,572 | 1.57 |
| search | 27,377 | 7,055 | 0.26 |
| issues | 22,425 | 36,382 | 1.62 |
| workflow_engine | 21,931 | 35,597 | 1.62 |
| preprod | 21,481 | 34,981 | 1.63 |
| utils | 19,619 | 19,268 | 0.98 |
| snuba | 19,020 | 17,264 | 0.91 |
| models | 18,848 | 13,812 | 0.73 |
| tasks | 17,532 | 26,605 | 1.52 |
| notifications | 16,888 | 17,426 | 1.03 |

Frontend areas: `static/app/views` 0.62, `components` 0.55, `utils` 0.63, `gsApp` 0.50, `gsAdmin` 0.62, the rest of `static/app` 0.18. The backend carries about twice as much test code per production line as the frontend.

## 6. Detroit or London

Heuristic, applied per file (exact regular expressions in the appendix): a file "imports a mocking facility" if it imports `unittest.mock`/`mock`, or uses `monkeypatch`/`mocker` (Python), or calls `jest.mock|spyOn|fn|mocked|requireMock` (TypeScript). Mock call sites are `patch(`, `patch.object(`, `Mock(`, `MagicMock(`, `AsyncMock(`, `PropertyMock(`, `create_autospec(`, `monkeypatch.x(`, `mocker.x(` and `jest.mock|spyOn|fn|mocked|requireMock|doMock(`. HTTP stubbing (`responses`) and the frontend API fake (`MockApiClient.addMockResponse`) are counted apart. Real-dependency flags come from base classes (resolved through the inheritance graph with `ast`), pytest-django marks, Sentry's DB fixtures and the `requires_*` marks. "Call checks" are `assert_called*`, `call_count`, `call_args` and `toHaveBeenCalled*`, as a share of assertion statements (`assert`, `self.assert*`, `expect(`).

| category | files with mocking | mock sites / 1,000 lines | HTTP stubs (files) | real PostgreSQL | real Snuba | other real services | call checks / assertions |
|---|---|---|---|---|---|---|---|
| acceptance | 39% | 12.8 | 0% | 100% | 39% | browser + live server 100% | 0.6% |
| relay integration | 33% | 0.7 | 17% | 100% | via pipeline | Relay 100%, Kafka 83%, Symbolicator 50% | 0% |
| symbolicator | 100% | 5.9 | 0% | 100% | 33% | Symbolicator, Relay, Kafka 100% | 0% |
| tests/snuba | 43% | 2.6 | 0% | 98% | 93% (100% by definition) | | 1.4% |
| endpoint | 49% | 16.1 | 11% | 99% | 19% | objectstore 1% | 6.4% |
| DB integration | 55% | 25.0 | 7% | 100% | 18% | Kafka 1% | 14.1% |
| no-DB | 28% | 12.0 | 2% | 0% | 1% | Redis in some | 6.6% |
| apidocs | 5% | 5.0 | 2% | 96% | 96% | | 0% |
| migrations | 25% | 3.0 | 0% | 94% | 25% | | 0% |
| Jest component | 45% (`jest.mock` 14%) | 11.6 (+18.9 `addMockResponse`) | API faked in 50% | none | none | jsdom | 16.7% |
| Jest logic | 11% | 3.3 | | none | none | | 3.7% |
| visual snapshot | 31% | 13.2 | | none | none | Chromium | 0% |

Across all backend Python test files, 85% use a real database (92% of the lines), 20% need Snuba (33% of the lines), and 47% import a mocking facility (71% of the lines; larger files mock more), at 18.7 mock sites per 1,000 lines.

What is mocked matters more than how often. Of the 9,655 `patch("...")` calls with a string target in the endpoint, DB, no-DB and Snuba categories, the most common final names are `record_event`/`record` (analytics, 726), `metrics`/`incr`/`distribution` (662), `logger` (330), `delay`/`apply_async` (task dispatch, 464), and Seer and integration clients (`get_jwt`, `safe_urlopen`, `urlopen`, `SeerAgentClient`, `make_signed_seer_api_request`). These are observation points, asynchronous boundaries and external services, not in-process neighbours. The stores themselves are almost never faked: AGENTS.md even tells authors to use Arroyo's in-memory Kafka backend "instead of mocks", and the Symbolicator suite was rebuilt in 2019 "to not be mocked" [15].

Placement on the axis:

- **acceptance, relay, symbolicator, snuba, apidocs, migrations**: Detroit. Real services; mocks fix time or feature flags.
- **endpoint**: Detroit. Every layer under the URL router is real, assertions are on responses and rows; 6% of assertions check calls.
- **DB integration**: Detroit core with a London fringe. The data layer is real, but this is the densest mocking category (25 sites per 1,000 lines) and one assertion in seven checks a call: that a task was dispatched, an analytics event recorded, a client called.
- **no-DB**: classical unit tests with some patching.
- **Jest component**: in-process with a fake at the network seam, which is the post's `fast` posture. Policy pushes it toward Detroit inside the process: hooks, router and organisation context must be real (lint rule `no-restricted-module-mocks`, section 8), and assertions are on the DOM. But 17% of assertions are call checks, mostly on the faked API requests.

## 7. The web UI

Both kinds exist, very unequally. The component suite is the proof; the browser suite is a thin net for what the component suite cannot see.

- **Jest + React Testing Library**: 2,362 spec files, 453,698 lines, 19,060 test definitions (component 1,839 files; logic 523). By area: views 873 component files (210,613 lines), components 575 (110,660), gsApp and gsAdmin (the SaaS billing and admin UI, whose backend is private) 155 (31,644). Tests render through `sentry-test/reactTestingLibrary`, which supplies a default organisation and an in-memory router; the API is the fake `MockApiClient`, and an unmocked request fails the test (section 8). In CI: `frontend.yml`, 8 shards balanced by recorded durations, and on pull requests only the tests related to the changed files (since March 2026 [53]). Wall time was about 8 minutes on 4 shards, and the move to 8 shards was expected to halve it [55].
- **Selenium acceptance**: 51 files, 5,317 lines, 202 tests, against the built frontend, a live Django server, PostgreSQL and (for 39% of files) Snuba, with page objects in `fixtures/page_objects`. In CI: `acceptance.yml` on every pull request that touches frontend or backend code, 5 shards (10 for frontend-only changes), required check `Acceptance`, `--reruns=5`. Ratio of Jest lines to browser-test lines: about 85 to 1.
- **Visual snapshots**: 29 files, 117 snapshot definitions, mostly design-system components (`static/app/components/core`) and preprod views, rendered by SSR and Playwright and uploaded to Sentry's own snapshot product, which posts a status check that a human approves [7][50].

What Sentry treats as the proof: the Testing Tips page sends a behaviour to the browser only when it is "not possible to cover with just endpoint tests or with Jest alone" [5]. In 2026 Ryan Brooks removed acceptance tests that only navigated: "navigations without assertions don't actually validate any functionality" [54]. No contract test ties the Jest fixtures to the real API responses; the only automated links are the generated list of API URLs used by the frontend (`api-url-typescript` job) and the OpenAPI checks in the 56 API-docs test files (inference from the CI files; no such contract test found).

## 8. Enforcement by machine

| mechanism | what it checks | where it lives | added |
|---|---|---|---|
| service marks fail instead of skip | a test marked `requires_snuba`, `requires_kafka`, `requires_symbolicator` or `requires_objectstore` fails when the service is down | `src/sentry/testutils/skips.py` | 2023-10-06, Matt Gaunt-Seo [26] |
| silo availability errors | calling a model, function or endpoint from the wrong silo raises `AvailabilityError`; the test database router raises when a table is not reachable | `src/sentry/silo/base.py`, `src/sentry/db/router.py` | limits 2022-09-12 [19]; test router 2023-05-31 [20]; split test databases by default 2023-09-08 [22] |
| silo test decorators | each test runs as control, cell or both; a subclass of a decorated test without its own decorator raises `SubclassNotSiloDecoratedException` | `src/sentry/testutils/silo.py` | 2022-09-07 [18]; tests run in their silo by default 2023-11-22 [23]; `region_silo_test` renamed `cell_silo_test` 2026-03-13 [52] |
| `validate_silo_mode` (autouse) | the silo mode was restored after the test | `tests/conftest.py` | 2023-01-23 [21] |
| protected-write audit (autouse) | writes to outbox-replicated tables happen inside an outbox fence | `tests/conftest.py`, `validate_protected_queries` | 2023-07-11 [24] |
| transaction safety (autouse) | no transaction spans two database connections; no RPC inside a transaction | `tests/conftest.py` | 2023-07-18 [25] |
| stale database reads (autouse) | a task spawned from a model signal or inside `atomic()` without `on_commit` fails the test | `src/sentry/testutils/pytest/stale_database_reads.py` | 2022-06-20, Markus Unterwaditzer [16] |
| leak detectors (autouse) | leaked `responses` mocks, open file descriptors, signal handlers, cache entries; leaked threads (reported, not failed unless `SENTRY_THREAD_LEAK_STRICT=1`) | `tests/conftest.py`, `src/sentry/testutils/thread_leaks` | responses 2023-08-25 [27]; files 2023-09-27 [28]; signals 2025-04-08 [36]; caches 2024-09-13 [31]; threads 2025-08-11 [37] |
| codebase meta-tests | every model has a silo; no cross-silo foreign keys; every endpoint has a silo decorator; every exportable model is in the backup tests | `tests/sentry/db/test_silo_models.py`, `tests/sentry/silo/test_base.py`, `tests/sentry/backup/test_coverage.py` | silo models 2022-12-15 and backup coverage 2023-07-21 [29]; endpoint walk not dated; silo and backup-validation meta-tests forced into every selective run 2026-06-17 [48a] |
| warnings are errors | any Python warning not explicitly ignored fails the test | `pyproject.toml` `filterwarnings = ["error", ...]` | not dated |
| slow-test failure | a test slower than 60 s fails in CI | `PYTEST_ADDOPTS ... --fail-slow=60s` in `.github/actions/setup-sentry` | 2023-01-12 [25a] |
| test file naming | a Python file under `tests/` must be named `test_*.py` | pre-commit `name-tests-test --pytest-test-first` | 2022-06-09, anthony sottile, "enforce test naming so tests actually run" [30] |
| custom flake8 rules | S001 confusing mock asserts, S004 `assertRaises`, S011 `override_options`, S014 `unittest.mock`, S015 no current-year dates at module scope, S020 EAP query window, S007 no `testutils` in production | `tools/flake8_plugin.py`, run by prek and CI | plugin moved into the repo 2022-04-21 [51a]; S015 tightened 2026-03-16 [51]; S020 2026-08-10 [51b] |
| unmocked API request fails a Jest test | `MockApiClient` records unmatched requests and prints them after each test; `jest-fail-on-console` turns that into a failure | `static/app/__mocks__/api.tsx`, `tests/js/setup*.ts` | fail-on-console 2022-09-15, Billy Vong [32] |
| frontend test lint rules | no direct `@testing-library/*` import (use the wrapper); `testing-library/no-node-access`, `no-container`; `jest/no-disabled-tests` as error; `jest/no-large-snapshots`; `no-restricted-module-mocks` forbids `jest.mock` of six core hooks | `oxlint.config.ts`, `static/oxlint` | rules inlined into the repo 2024-11-20 [56a]; hook-mock ban 2026-09-14, Malachi Willey [56] |
| required aggregator checks | `Backend`, `Frontend`, `Acceptance` fail if any child job failed or was cancelled | the three workflows | `backend.yml` since 2022-04-12 [34]; aggregator jobs not dated |
| labels that widen the run | `Trigger: Override Selective Testing` runs the full backend suite; `Trigger: getsentry tests`; `Frontend: Rerun Flaky Tests` runs each `it.isKnownFlake` test 50 times | `backend.yml`, `getsentry-dispatch.yml`, `tests/js/setup.ts` | 2026-02-23 [46]; not dated; 2026-04-07 [53a] |
| selective-testing safety nets | changes to conftest, `testutils/pytest`, options, features, signals, migrations run the full suite; a fixed list of global tests always runs | `.github/workflows/scripts/compute-sentry-selected-tests.py` | 2026-01-20 onward [45][47][48] |

One mechanism points the other way. CI reruns every failing Python test up to five times (`--reruns=5`, since 2020-02-24 [14]), and `pytest-sentry` reports tests that passed only on rerun to a Sentry project instead of failing the build; on master every failure is reported. Its author, Markus Unterwaditzer, states the trade-off in the plugin's README [12]: "One concern against plugins like this is that they just hide the bugs in your testsuite or even other code. After all your CI build is green and your code probably works most of the time. `pytest-sentry` tries to make that choice a bit easier by tracking flaky test failures in a place separate from your build status."

Several written rules have no machine behind them: the mirror placement rule, "NEVER directly call `Model.objects.create`" (the tests still contain 5,982 `.objects.create(` calls in 778 files), "use `pytest` instead of `unittest`" (99 backend test files still use `unittest.TestCase`), and "ALWAYS colocate tests".

## 9. History

**2016-2019: test everything, snapshot every pixel, gate on coverage.** `codecov.yml` was added on 2016-05-10 (David Cramer) and two days later its targets were set to 0% "to make pulls pass" (Armin Ronacher) [1][2]. In June 2017 David Cramer set a 90% patch target for Python [3]. Acceptance tests and Percy arrived together in June 2016, written by Mike Fotinakis [10][11]. Snuba got its own suite in 2018 [13] and Symbolicator a real-service suite in 2019 [15].

**2020-2021: Percy out, reruns in, docs written.** Flaky tests were handled by retrying: `reruns = 1` in `setup.cfg` became `--reruns 5` in CI on 2020-02-24 together with `pytest-sentry` [14]. Relay end-to-end tests started on 2020-03-06 [9]. In July 2020 Billy Vong added an in-house visual-diff action ("Note this action does not block merging PRs") and four weeks later removed Percy without a stated reason [11a][11b]; that it was a replacement is an inference from the dates. In August 2020 Jest DOM snapshots were replaced by image snapshots [11c]. Mark Story wrote the Testing Tips page in May 2020 [33].

**2021-2022: the frontend changes its testing library.** The Enzyme-to-RTL migration ran from June 2021 to December 2022 [35][38]. The account by Priscila Oliveira and Scott Cooper [35] is the best primary source on Sentry's testing philosophy: the move was forced by React 17 and 18, and kept going because RTL tests do not rely on implementation details. In August 2022 every frontend test moved next to its component [41]. In March 2022 Armin Ronacher wrote the "For the love of god" paragraph against Django `TestCase` and documented a detector for needless database use [42].

**2022-2024: hybrid cloud turns the suite into an architecture checker.** The multi-region project annotated models, endpoints and tests with silo modes and made wrong-silo access raise in tests [18][19]. Mark Story's account [43] describes using CI as a simulator of the split before the database was split, and the cost: "Running all tests twice added strain to our CI systems". From 2023 the test settings split PostgreSQL into region and control databases by default [22], and from November 2023 tests ran only in their declared silo [23].

**2023-2025: coverage gating rises and falls.** Five weeks after Sentry announced it had acquired Codecov (2022-11-30 [4]), Armen Zambrano turned failing patch-coverage statuses back on [3a]; the commit does not mention the acquisition. The check fired too early, went informational, came back, and was made informational for good in December 2024, after Jonas observed that red coverage checks were merged anyway [3c][3d]. A year later Joshua Li deleted coverage collection from CI [3e]. Codecov's automated test selection had been tried in 2023 and was removed in December 2025 after the vendor deleted the feature [3f].

**2026: select, prune and parallelise.** Coverage came back as data rather than a gate. Ryan Brooks and Joshua Li built selective testing (dynamic shards, an hourly coverage database, then a cut-over in April 2026) [45][46][47][48]. Pull-request CI then became dominated by acceptance tests, and navigate-only browser tests were removed [54]. Jest got 8 shards and related-test selection [53][55]. Visual regression returned through Sentry's own snapshot product [50].

**Did the steers succeed?** The RTL steer did: the tree has no Enzyme, 99% of component specs import RTL (all but two through the wrapper), and lint rules now enforce RTL conventions, the kind of tooling the migration itself did without ("we didn't use any tools to prevent people from creating new tests written in Enzyme" [35]). The "stop using Django `TestCase`" steer did not: 1,873 of 2,613 backend test files still use Sentry's Django test classes, only 194 use function-style `django_db_all`, and the detector was removed in 2025 as not worth it [42a]. The coverage-gate steer failed by its own account and was abandoned [3c][3d][3e]. The silo steer succeeded as an enforcement layer, with an admitted gap: "we identified many silo boundary errors that we didn't catch with tests due to a lack of coverage" [43]. The visual-regression steer was dropped twice and restarted once.

## 10. Timeline

| date | turn | driven by | link |
|---|---|---|---|
| 2016-05-10 | `codecov.yml` added; targets set to 0% two days later | David Cramer; Armin Ronacher | [1] [2] |
| 2016-06-06 | first acceptance (Selenium) test; Percy on 2016-06-20 | Mike Fotinakis | [10] [11] |
| 2017-06-08 | Python patch-coverage target 90% | David Cramer | [3] |
| 2018-04-02 | `tests/snuba` suite created | Brett Hoerner | [13] |
| 2019-04-03 | Symbolicator tests rebuilt "to not be mocked" | Markus Unterwaditzer | [15] |
| 2020-02-24 | CI reruns failures up to 5 times; flakes reported by `pytest-sentry` | Billy Vong | [14] |
| 2020-03-06 | Relay end-to-end suite | Radu Woinaroski | [9] |
| 2020-05-13 | Testing Tips page: "the bulk of our test suite" is endpoint integration tests | Mark Story | [33] |
| 2020-07-27 | Percy removed (in-house non-blocking visual diff added 2020-07-01) | Billy Vong | [11a] [11b] |
| 2020-09-22 | API docs schema validation tests | Marcos Gaeta | [17] |
| 2021-06-25 | React Testing Library introduced | Priscila Oliveira | [38] |
| 2022-03-30 | "please stop writing tests using the Django test case"; DB misuse detector | Armin Ronacher | [42] |
| 2022-04-04 | Codecov status checks made informational | Armin Ronacher | [3b] |
| 2022-06-09 | test file naming enforced by pre-commit | anthony sottile | [30] |
| 2022-08-31 | all frontend tests colocated with components | Shruthi | [41] |
| 2022-09-07 | silo test decorators; silo limits on 2022-09-12 | Ryan Skonnord | [18] [19] |
| 2022-12-22 | Enzyme removed | Evan Purkhiser | [38] |
| 2023-01-05 | failing patch-coverage checks re-enabled | Armen Zambrano | [3a] |
| 2023-03-21 | visual snapshots removed from CI (code deleted 2023-09-12) | Matt Gaunt-Seo; anthony sottile | [11d] [11e] |
| 2023-09-08 | split region/control databases in tests by default | Alberto Leal | [22] |
| 2023-10-06 | missing services fail tests instead of skipping them | Matt Gaunt-Seo | [26] |
| 2023-11-22 | tests run only in their declared silo | Ryan Skonnord | [23] |
| 2024-12-09 | coverage check no longer fails; target 50% | Armen Zambrano | [3d] |
| 2025-04-08 | backend shards doubled to 22 | anthony sottile | [36a] |
| 2025-04-14 | DB misuse detector removed: "effectively zero" saving | anthony sottile | [42a] |
| 2025-10-01 | written test-placement rule (for coding agents) | Armen Zambrano | [39] |
| 2025-12-23 | coverage collection deleted from CI | Joshua Li | [3e] |
| 2026-02-25 | pull requests run selected backend tests; master runs all | Ryan Brooks | [47] |
| 2026-03-10 | web snapshot testing with Sentry's snapshot product | Ryan Brooks | [50] |
| 2026-03-30 | pytest-xdist on pull requests; Jest `--changedSince` | Ming Chen; Josh Goldberg | [49] [53] |
| 2026-04-13 | navigate-only acceptance tests removed | Ryan Brooks | [54] |
| 2026-04-16 | selective testing adds import analysis after a missed failure | Ryan Brooks | [48] |
| 2026-09-14 | lint rule forbids mocking core hooks in Jest | Malachi Willey | [56] |

## 11. The arguments, turn by turn

**Percy, then in-house diffs, then nothing, then Sentry's own product.** The pain was flaky pixels and cost of review. Before its removal, 107 commit messages mention Percy, and 55 of them are fixes or stabilisations ("Fix flakey Percy snap", "Attempt to stabilize flaky percy snapshot"). Billy Vong's in-house action of 2020-07-01 was explicitly non-blocking: "Note this action does not block merging PRs." [11a]. When he replaced Jest DOM snapshots with images he argued [11c]:

> This has the benefits of 1) providing useful snapshots (e.g. what visual impact a css change makes rather than seeing a class name change) 2) will eliminate build errors due to outdated snapshots in getsentry

The in-house diffs were made opt-in behind a `Trigger: Visual Snapshot` label in March 2023 [11d] and deleted in September 2023 [11e]; neither pull request states the reason in public, and the context sits in a private `getsentry` pull request. The legacy survived in the browser suite. Ryan Brooks, 2026-04-13 [54]:

> Acceptance tests are now our primary bottleneck on CI time since selective testing has landed. [...] I deem these tests as useless as navigations without assertions don't actually validate any functionality. It's very likely these were around for legacy visual snapshot testing with Percy, but never properly removed.

Numbers: acceptance files went 3 (2016) → 56 (2020) → 84 (mid-2023) → 60 (January 2026) → 51 (snapshot). That pull request cut acceptance test functions from 213 to 171; by October 2026 they were back to 202. The new snapshot framework (2026-03-10) avoids the browser stack entirely; Ryan Brooks: "I chose to use SSR so we could extract Emotion CSS alongside the HTML. This way we can get fully-styled components without needing a dev server or webpack build." [50]

**Enzyme to React Testing Library.** Priscila Oliveira and Scott Cooper, 2023-02-23 [35]. The first proof of concept did not win on speed:

> the performance improvements - about ~12% - weren't enough to convince us to go down the road of a long migration from Enzyme to React Testing Library.

React 17 forced the decision, and the gain they kept was not speed:

> This effort took over a year and four months, involved contributions from 17 engineers, and spanned 803 test suites and 4,937 tests, requiring changes to each one.

> Although the performance of our tests has not improved as we had hoped, the introduction of the library has brought many other benefits, such as tests that no longer rely on implementation details, but instead test what the user sees and interacts with.

They also traded realism for speed in one place: "By mocking it, we traded the safety of testing styles for faster tests. One particularly slow test went from 94.93s to 47.52s". The mock of `getComputedStyle` is still in `tests/js/setup.ts`. Numbers since: Jest spec files grew from 712 (mid-2022) to 2,396 at the snapshot, and test definitions from 4,937 to about 19,000.

**Hybrid cloud: tests as a simulator of the future architecture.** Mark Story, 2024-05-16 [43]:

> Our next step was to monkeypatch Django's ORM to raise errors when cross silo operations are performed.

> Having these errors in our CI builds and pre-production testing let us pinpoint code paths that would need to be updated. Enforcing silo boundaries was toggled by annotations on test cases, giving us a way to incrementally improve the application without disrupting other teams.

> Getting 35,000 tests passing in silo stable mode was a slow process [...] Running all tests twice added strain to our CI systems as towards the end of our work we were running most tests twice to ensure silo mode isolation.

He also names the costs: "many teams lacked context on what the annotations were for and how they were assigned", and pre-production testing found "many silo boundary errors that we didn't catch with tests due to a lack of coverage." Ryan Skonnord ended the double runs on 2023-11-22: "Have all test cases tagged with a silo mode decorator (`@control_silo_test` or `@region_silo_test`) run only in that mode." [23]

**Real database, and whether to avoid it.** Armin Ronacher's 2022 docs text, still on the Testing Tips page [5][42]:

> For the love of god, please stop writing tests using the Django test case.

anthony sottile measured the payoff three years later and removed the detector, 2025-04-14 [42a]:

> after some comparison I've decided this isn't really worth it.
>
> we have about 1000 tests that _could_ be converted to non-db tests -- the savings is about a millisecond per test meaning it would be about 1 second improvement spread across the whole testsuite. so effectively zero.

The page still tells readers to set `SENTRY_DETECT_TESTCASE_MISUSE=1`, which no longer exists in the code. The same direction, toward real services, shows in 2023: a missing Snuba, Kafka or Symbolicator now fails a test instead of skipping it [26] (no description on the pull request).

**Coverage as a gate.** Armen Zambrano, 2023-01-05 [3a]:

> Back in the day, codecov failed a lot on `master` and to only run it informationally on PRs.
>
> Unfortunately, this prevents developers from meeting a minimum coverage for their diffs and allows our code coverage to keep dropping over time.
>
> I would like to make PRs fail if we do not meet the minimum diff coverage. We can then re-evaluate again how reliable it is.

Jonas, 2024-12-03 [3c]:

> Running coverage doubles our CI times and causes PRs to be marked as failing in Github UI. In addition, since it is not enforced, it just means it goes entirely dismisses (last 10 PRs with failed merged coverage checks were merged anyways).

Armen Zambrano, 2024-12-09 [3d]: "We have the comment in place to let us know if there's something to do. The check always turns red and we do nothing about it." Joshua Li, 2025-12-23 [3e]:

> we have not enforced coverage in any way (not a required check) for backend commits, and afaict coverage data is not used anywhere
>
> deleting coverage + codecov upload shaves off 1m30s from all shards and reduces total wall test time by 40 minutes

**Selective testing.** Ryan Brooks, 2026-01-20 [45]: "Our approach is quite lax here, when in doubt (missing coverage data, file in an allowlist) we'll default to running all tests." A miss came three months later, 2026-04-16 [48]: "A failing test slipped past selective testing earlier", because coverage cannot see a model used only through pydantic base-class methods; the fix unions coverage with direct imports and "will miss transitive dependencies, but this should be at least one additional line of defense against holes." No published before-and-after runtime was found; the visible effect is Ryan Brooks's remark that acceptance became the bottleneck [54].

**CI speed in numbers.** Shards doubled to 22 when "github increased our open source parallel quota" (anthony sottile, 2025-04-08 [36a]). Jest, Nico Hinderling, 2026-04-30 [55]: "Total test execution across all shards sums to ~25 minutes", and 8 shards cut "wall clock from ~8min to ~4min". Ryan Albrecht, 2026-06-11: the sequential timing run "took ~35mins to run the entire Jest suite sequentially, but often fails with flakey tests" [55a]. Migration tests: collection went from "~110s collection down to <1s, same 20 tests" (2026-10-08 [57]). No published total runtime for the backend suite was found.

**Flakiness.** The response has three layers: retry and report (2020 [14][12]), leak and hygiene fixtures (2023-2025; anthony sottile: "this adds a little overhead to tests -- but should prevent flakes from people abusing `mkstemp` or other file io without proper context managers" [28]), and a 2026 frontend label that reruns known flakes 50 times. Indicators only: 54 issues carry the label `Type: CI Flakiness` [58]; commits mentioning flaky or flake per year were 14 (2018), 34 (2020), 135 (2022), 78 (2023), 115 (2025), 128 (2026 to October), against yearly commit totals that grew from 3,819 (2018) to 18,674 (2025). No flake-rate figure was found.

## 12. Coverage

**Measured: yes, from 2016 to December 2025. Gated: by status checks at times, but never as a required check that we can find. At the snapshot: no coverage gate; coverage is collected only to choose tests.**

| date | policy | link |
|---|---|---|
| 2016-05-10 | `codecov.yml` added (comments, migrations ignored) | [1] |
| 2016-05-12 | project and patch targets 0% "to make pulls pass" | [2] |
| 2017-06-08 | patch target 90% for `src/sentry`, project status off | [3] |
| 2018-03-07 | JavaScript patch target lowered from 75% to 60% | [3g] |
| 2022-04-04 | frontend 60% and backend 90% patch statuses made informational | [3b] |
| 2023-01-05 | informational removed: below-target pull requests get a failing status | [3a] |
| 2023-03-01 | informational again, because the check fired before all shards uploaded | [3h] |
| 2023-04-11 | failing again, with per-flag `after_n_builds` | [3i] |
| 2023-08-28 to 2023-11 | Codecov automated test selection trialled (dry run, reverted, re-enabled) | [3f] |
| 2024-12-03 | Jest coverage collected on master only; frontend status informational | [3c] |
| 2024-12-09 | backend status informational, target 50% | [3d] |
| 2025-12-19 | ATS workflows deleted | [3f] |
| 2025-12-23 | coverage collection and upload deleted from CI | [3e] |
| 2026-01-06 | `codecov.yml` deleted | [3j] |
| 2026-01-15 onward | full coverage recomputed hourly (now by `getsentry`) and used only for selective testing | [45] [47] |

Two leftovers in the tree: `setup.cfg` keeps `fail_under = 0.01` with the comment that it is "a value we'll never fall below", and `jest.config.ts` keeps `collectCoverageFrom`, which no CI job uses. Codecov's product features inside Sentry (Test Analytics, coverage in stack traces) were removed between March and June 2026 [3k]; Sentry's own CI never used Codecov's test-results upload that we could find, and test results go to an internal store instead (`getsentry/action-collect-test-data`).

## Chart-ready table

| category | maps_to (post taxonomy) | lines | pct | files | tests |
|---|---|---|---|---|---|
| jest_component | fast (main UI proof, not an extra copy) | 376878 | 30.5 | 1839 | 14335 |
| backend_db_integration | adapters_free (approx.; in-process slices on real PostgreSQL/Redis) | 373592 | 30.2 | 1246 | 17490 |
| backend_endpoint | api (approx.; in-process Django test client) | 250707 | 20.3 | 764 | 11971 |
| jest_logic | unit | 76820 | 6.2 | 523 | 4725 |
| snuba_compat | adapters_free / api (real Snuba + ClickHouse) | 68596 | 5.6 | 91 | 2254 |
| backend_no_db | unit | 59661 | 4.8 | 380 | 3510 |
| tooling | tooling | 13133 | 1.1 | 69 | 616 |
| acceptance_selenium | e2e | 5317 | 0.4 | 51 | 202 |
| relay_integration | api (ingest edge, real Relay + Kafka) | 4518 | 0.4 | 6 | 71 |
| visual_snapshot | none (visual regression) | 2506 | 0.2 | 29 | 117 |
| apidocs_contract | none (OpenAPI contract) | 2217 | 0.2 | 56 | 113 |
| migrations | none (data migration) | 1352 | 0.1 | 16 | 20 |
| symbolicator | adapters_free | 677 | 0.1 | 3 | 15 |

## Sources

1. David Cramer, "Add codecov.yml", 2016-05-10. https://github.com/getsentry/sentry/commit/194fb16efdb1bc53c84654bbba720618501c7a71
2. Armin Ronacher, "Lower threshold for codecov to 0 to make pulls pass", 2016-05-12. https://github.com/getsentry/sentry/commit/a43797d2104eb016d0b30f591fed04b0512affc7
3. David Cramer, "ci: add codecov restrictions", 2017-06-08. https://github.com/getsentry/sentry/commit/ea0ec9ad6d47043d83b59dcb83acc442c7bd14ad
   - 3a. Armen Zambrano, "feat(codecov): Enable pull request check failures", 2023-01-05. https://github.com/getsentry/sentry/pull/42831
   - 3b. Armin Ronacher, "build(codecov): Disable status checks for codecov", 2022-04-04. https://github.com/getsentry/sentry/pull/33250
   - 3c. Jonas, "ci(coverage) only run coverage on master", 2024-12-03. https://github.com/getsentry/sentry/pull/81582
   - 3d. Armen Zambrano, "chore(codecov): Do not fail the codecov check", 2024-12-09. https://github.com/getsentry/sentry/pull/81827
   - 3e. Joshua Li, "ci: delete coverage", 2025-12-23. https://github.com/getsentry/sentry/pull/105394
   - 3f. Giovanni M Guidini, "ci(codecov): enable automated test selection (dry-run)", 2023-08-28, https://github.com/getsentry/sentry/pull/54026 ; "ci: Periodically upload coverage to codecov from master", 2023-11-03, https://github.com/getsentry/sentry/pull/58520 ; Ryan Brooks, "chore(infra): Remove unused codecov ATS workflow", 2025-12-19, https://github.com/getsentry/sentry/pull/105305
   - 3g. Billy Vong, "build(codecov): Lower codecov js patch threshold to 60%", 2018-03-07. https://github.com/getsentry/sentry/pull/7426
   - 3h. Armen Zambrano, "feat(codecov): Enable PR comment and make patch check always green", 2023-03-01. https://github.com/getsentry/sentry/pull/45186
   - 3i. Armen Zambrano, "feat(codecov): after_n_builds per flag & codecov comment in PRs", 2023-04-11. https://github.com/getsentry/sentry/pull/46942
   - 3j. Ryan Brooks, "chore(infra): Remove codecov.yml", 2026-01-06. https://github.com/getsentry/sentry/pull/105717
   - 3k. Calvin, "feat(codecov): Remove Test Analytics UI and Prevent tokens", 2026-03-17, https://github.com/getsentry/sentry/pull/109291 ; Calvin, "feat: Remove code coverage feature", 2026-05-29, https://github.com/getsentry/sentry/pull/116240
4. Sentry press release, "Sentry Acquires Codecov", 2022-11-30. https://sentry.io/about/press-releases/sentry-acquires-codecov/
5. Sentry developer docs, "Testing Tips", read 2026-10-11 (source at getsentry/sentry-docs 52d502de, 2026-10-10). https://develop.sentry.dev/development-infrastructure/testing/
6. Sentry developer docs, "Using React Testing Library", read 2026-10-11; "Use Case Coverage" sentence added by Matej Minar 2021-11-04 (getsentry/develop#458). https://develop.sentry.dev/frontend/using-rtl/
7. Sentry developer docs, "Snapshot testing", read 2026-10-11. https://develop.sentry.dev/frontend/testing/snapshot-testing/
8. Sentry developer docs, "Selective Testing", read 2026-10-11. https://develop.sentry.dev/backend/testing/selective-testing/
9. Radu Woinaroski, "test(relay): Add E2E tests with Relay", 2020-03-06. https://github.com/getsentry/sentry/pull/17241
10. Mike Fotinakis, "Initial acceptance testing setup.", 2016-06-06. https://github.com/getsentry/sentry/pull/3392
11. Mike Fotinakis, "Initial Percy integration and acceptance tests.", 2016-06-20 (merged via #3497). https://github.com/getsentry/sentry/commit/012c535ada5b01093a6a5deb65ac02b2bf80d974
    - 11a. Billy Vong, "build(github): Add a GitHub action to diff PR snapshots against main branch", 2020-07-01. https://github.com/getsentry/sentry/pull/19585
    - 11b. Billy Vong, "test(acceptance): Remove percy", 2020-07-27. https://github.com/getsentry/sentry/pull/20040
    - 11c. Billy Vong, "test(jest): Replace jest snapshots with image snapshots", 2020-08-12. https://github.com/getsentry/sentry/pull/19878
    - 11d. Matt Gaunt-Seo, "ci: remove visual snapshots from CI", 2023-03-21. https://github.com/getsentry/sentry/pull/46132
    - 11e. anthony sottile, "ref: remove visual snapshots", 2023-09-12. https://github.com/getsentry/sentry/pull/56037
12. Markus Unterwaditzer, pytest-sentry README (PyPI, version 0.5.1), read 2026-10-11. https://pypi.org/project/pytest-sentry/
13. Brett Hoerner, "ci(snuba): Add snuba test suite", 2018-04-02. https://github.com/getsentry/sentry/pull/7865
14. Billy Vong, "test(pytest): Fix "reruns" for sentry-pytest", 2020-02-24. https://github.com/getsentry/sentry/pull/17224
15. Markus Unterwaditzer, "build: Restructure symbolicator tests to not be mocked", 2019-04-03. https://github.com/getsentry/sentry/pull/12617
16. Markus Unterwaditzer, "fix(django): Third attempt: Detect spawned celery tasks that can exhibit stale reads", 2022-06-20. https://github.com/getsentry/sentry/pull/35819
17. Marcos Gaeta, "feat(api-docs): validate_schema", 2020-09-22. https://github.com/getsentry/sentry/pull/20863
18. Ryan Skonnord, "feat(hybrid): Scripts for silo mode decorators", 2022-09-07. https://github.com/getsentry/sentry/pull/38288
19. Ryan Skonnord, "feat(hybrid): Add silo mode limit decorators", 2022-09-12. https://github.com/getsentry/sentry/pull/38613
20. Mark Story, "feat(hybridcloud) Add Django router for siloed environments", 2023-05-31. https://github.com/getsentry/sentry/pull/49722
21. Zach Collins, "fix(tests): fix the set_sentry_option test helper" (adds `validate_silo_mode`), 2023-01-23. https://github.com/getsentry/sentry/pull/43492
22. Alberto Leal, "feat(hybrid-cloud): Enable split db in tests by default", 2023-09-08. https://github.com/getsentry/sentry/pull/55931
23. Ryan Skonnord, "test(hc): Change default test behavior to silo modes", 2023-11-22. https://github.com/getsentry/sentry/pull/60426
24. Mark Story, "fix(hybridcloud) Begin replacing role switching with query audits", 2023-07-11. https://github.com/getsentry/sentry/pull/52587
25. Zach Collins, "ref(hc): Adding helpers for managing transactions", 2023-07-18. https://github.com/getsentry/sentry/pull/52943
    - 25a. Matt Gaunt-Seo, "Add pytest-fail-slow plugin", 2023-01-12. https://github.com/getsentry/sentry/pull/43181
26. Matt Gaunt-Seo, "Make requires_<service> fixtures fail if service is not running", 2023-10-06. https://github.com/getsentry/sentry/pull/57695
27. anthony sottile, "ref: add fixture to catch leaked responses mocks", 2023-08-25. https://github.com/getsentry/sentry/pull/55175
28. anthony sottile, "ref: add autouse fixture to catch leaked file descriptors", 2023-09-27. https://github.com/getsentry/sentry/pull/56749
29. Alex Zaslavsky, "test(backup): Ensure coverage of all exportable models", 2023-07-21. https://github.com/getsentry/sentry/pull/53295 ; Zach Collins, "chore(hybrid-cloud): test model decorators and fk breakage", 2022-12-15, https://github.com/getsentry/sentry/pull/42254
30. anthony sottile, "ref: enforce test naming so tests actually run", 2022-06-09. https://github.com/getsentry/sentry/pull/35517
31. anthony sottile, "ref: fix test pollution integrity errors due to cache leaks between tests", 2024-09-13. https://github.com/getsentry/sentry/pull/77476
32. Billy Vong, "feat(test): Fix console.error getting swallowed up", 2022-09-15. https://github.com/getsentry/sentry/pull/38833
33. Mark Story, "feat: Add testing docs", getsentry/develop, 2020-05-13. https://github.com/getsentry/develop/pull/32
34. Armen Zambrano, "feat(ci): Join FE & BE workflows", 2022-04-12. https://github.com/getsentry/sentry/pull/33455
35. Priscila Oliveira and Scott Cooper, "Sentry's Frontend Tests: Migrating from Enzyme to React Testing Library", 2023-02-23. https://blog.sentry.io/sentrys-frontend-tests-migrating-from-enzyme-to-react-testing-library/ (source also in getsentry/sentry.engineering at 117f5a0e, removed from that repository on 2026-05-06)
36. anthony sottile, "ref: add fixture to prevent leaked signal handlers", 2025-04-08. https://github.com/getsentry/sentry/pull/88740
    - 36a. anthony sottile, "ref: double backend shard count", 2025-04-08. https://github.com/getsentry/sentry/pull/87844
37. Buck Evan, "thread leak detection dark launch", 2025-08-11. https://github.com/getsentry/sentry/pull/97320
38. Priscila Oliveira, "ref(tests): Introduce React-Testing-Library", 2021-06-25, https://github.com/getsentry/sentry/pull/26712 ; Evan Purkhiser, "test(js): Remove Enzyme (again)", 2022-12-22, https://github.com/getsentry/sentry/pull/42571
39. Armen Zambrano, "cursor(backend): Help Cursor write tests within existing test files", 2025-10-01. https://github.com/getsentry/sentry/pull/100670
40. Josh Ferge, "ref: Reorganize AGENTS.md into focused, nested structure" (creates `tests/AGENTS.md`), 2025-12-10. https://github.com/getsentry/sentry/pull/104690
41. Shruthi, "chore: Colocate all remaining frontend tests", 2022-08-31. https://github.com/getsentry/sentry/pull/38352
42. Armin Ronacher, "Document db misuse detector", getsentry/develop, 2022-03-30. https://github.com/getsentry/develop/pull/542
    - 42a. anthony sottile, "ref: remove testcase db misuse checker", 2025-04-14. https://github.com/getsentry/sentry/pull/89481
43. Mark Story, "Removing risk from our multi-region design with simulations", 2024-05-16. https://blog.sentry.io/removing-risk-from-our-multiregion-design-with-simulations/
44. Mark Story, "chore(tasks) Remove code referencing celery pt4", 2025-09-29. https://github.com/getsentry/sentry/pull/100408
45. Ryan Brooks, "feat(infra): Add backend selective testing workflow", 2026-01-20, https://github.com/getsentry/sentry/pull/105500 ; "feat(infra): Add backend tests workflow with coverage upload to GCS", 2026-01-15, https://github.com/getsentry/sentry/pull/105885 ; "feat(infra): Dynamic sharding", 2026-01-07, https://github.com/getsentry/sentry/pull/105706
46. Joshua Li, "feat(ci): selective testing escape hatch", 2026-02-23. https://github.com/getsentry/sentry/pull/109136
47. Ryan Brooks, "feat(infra): Replace full backend workflow on PRs with selective testing", 2026-02-25, https://github.com/getsentry/sentry/pull/109346 ; Joshua Li, "ci(st): cutover to new selective testing infra", 2026-04-06, https://github.com/getsentry/sentry/pull/112263
48. Ryan Brooks, "ref(ci): Add import analysis to selective testing", 2026-04-16. https://github.com/getsentry/sentry/pull/113247
    - 48a. Joshua Li, "fix(selective-testing): always run silo and backup validate meta-tests", 2026-06-17. https://github.com/getsentry/sentry/pull/117932
49. Ming Chen, "ci(backend): enable xdist on PRs with 2 workers", 2026-03-30, https://github.com/getsentry/sentry/pull/111557 ; "feat(ci): xdist per-worker isolation infrastructure", 2026-03-16, https://github.com/getsentry/sentry/pull/110775
50. Ryan Brooks, "feat(frontend): Web snapshot testing", 2026-03-10. https://github.com/getsentry/sentry/pull/107971
51. Armen Zambrano, "feat(tests): Update S015 rule to prevent hardcoding future years", 2026-03-16. https://github.com/getsentry/sentry/pull/110738
    - 51a. anthony sottile, "ref(dev): use sentry-flake8 as a flake8:local-plugins plugin", 2022-04-21. https://github.com/getsentry/sentry/pull/33830
    - 51b. sentry-junior[bot], "fix(tests): keep EAP snuba tests within 30d statsPeriod" (adds S020), 2026-08-10. https://github.com/getsentry/sentry/pull/121595
52. Lyn Nagara, "ref(cells): region_silo_test -> cell_silo_test", 2026-03-13. https://github.com/getsentry/sentry/pull/110569
53. Josh Goldberg, "chore: add --changedSince base SHA to Jest in CI", 2026-03-30. https://github.com/getsentry/sentry/pull/110568
    - 53a. Josh Goldberg, "feat(test): add `it.isKnownFlake` for opt-in stress-testing flaky Jest fixes", 2026-04-07. https://github.com/getsentry/sentry/pull/111860
54. Ryan Brooks, "chore(ci): Remove unused navigate-only acceptance tests", 2026-04-13. https://github.com/getsentry/sentry/pull/112698
55. Nico Hinderling, "perf(ci): Increase Jest shards from 4 to 8 for faster CI", 2026-04-30. https://github.com/getsentry/sentry/pull/114388
    - 55a. Ryan Albrecht, "ref(jest-balance): Parallelize balancer across 8 shards", 2026-06-11. https://github.com/getsentry/sentry/pull/117059
56. Malachi Willey, "feat(lint): Disallow mocking supported test hooks", 2026-09-14. https://github.com/getsentry/sentry/pull/124341
    - 56a. Ryan Albrecht, "ci(eslint): Inline all the external eslint-config-sentry* ESLint configs into our .eslintrc file", 2024-11-20. https://github.com/getsentry/sentry/pull/80970
57. sentry-junior[bot] via Joshua Li, "ci(backend): Only run migration tests on PRs that touch migrations", 2026-10-08. https://github.com/getsentry/sentry/pull/126951
58. GitHub issue search, label "Type: CI Flakiness", read 2026-10-11. https://github.com/getsentry/sentry/issues?q=is%3Aissue%20label%3A%22Type%3A%20CI%20Flakiness%22
59. The repository at the snapshot, 035fd0e6 (2026-10-09): `tests/AGENTS.md`, `static/AGENTS.md`, `AGENTS.md`, `pyproject.toml`, `setup.cfg`, `Makefile`, `.pre-commit-config.yaml`, `tests/conftest.py`, `src/sentry/testutils/**`, `.github/workflows/*.yml`, `.github/actions/setup-sentry/action.yml`, `jest.config.ts`, `tests/js/setup.ts`, `oxlint.config.ts`, `tools/flake8_plugin.py`. https://github.com/getsentry/sentry/tree/035fd0e68c0a85be84eabe7c5cacbd88d9ae065e

## Appendix: commands and counting decisions

**Snapshot.** `git clone --depth 1 https://github.com/getsentry/sentry.git` into `<scratchpad>/sentry-clone/`; `git log -1` gave `035fd0e68c0a85be84eabe7c5cacbd88d9ae065e`, committed 2026-10-09T23:36:46+00:00, "ref(dashboards): Replace lodash debounce with tanstack pacer (#127125)". All numbers are from this tree. Nothing in the clone was executed.

**Counting.**

```
python3 -I notebooks/X-shapes-of-tests/tools/count_lines.py <clone> --by-file > all_files.csv     # 18,055 files
python3 -I classgraph.py <clone> classgraph.json      # ast-only inheritance graph of test classes
python3 -I classify.py <clone> all_files.csv counts.csv features.csv classgraph.json
```

`counts.csv` is the tool's per-file output with a `category` column; it is saved as `notebooks/X-shapes-of-tests/sentry.counts.csv` (all 18,055 counted files, production and other files included, so totals can be rebuilt). The tool counts docstrings as code; Python docstrings are therefore included in every Python figure. The tool's default excludes removed `src/sentry/static/sentry/vendor` and the 7 build scripts in `src/sentry/build` (via `*/build/*`) and all `*.min.js` files.

**Grouping rules, in order of precedence.**

1. Data with code extensions: `tests/relay_integration/lang/javascript/fixtures/`, `tests/symbolicator/fixtures/`, `.github/workflows/scripts/fixtures/`, non-Python files in `fixtures/` → `data:code_fixture`. `fixtures/stubs-for-mypy` → `other:type_stubs`.
2. Tooling tests: `tests/tools/test_*.py`, `tests/sentry/testutils/test_*.py` (tests of the test harness), `.github/workflows/scripts/test_*.py` and `*.test.js|ts`, `scripts/*.test.ts`, `static/oxlint/**/*.spec.ts`, `tests/js/**/*.spec.ts(x)`, `.agents/**/*_tests.py`.
3. Python helpers: `src/sentry/testutils/**`, `src/sentry/{replays,profiles,monitors}/testutils.py`, `fixtures/**/*.py`, every `conftest.py` and `__init__.py` under `tests/`, any non-`test_*` module in `tests/`, `test_*.py` files with zero test functions whose names end in `base`, `helper(s)`, `utils`, `fixtures` or `mock_slack_response`, and two explicit helper files with zero tests (`tests/sentry/incidents/endpoints/serializers/test_alert_rule.py`, `tests/snuba/rules/conditions/test_event_frequency.py`). Zero-test files that inherit tests (8 monitor endpoint files, `github_enterprise/test_search.py`, `release_monitor/test_metrics.py`) stay as tests.
4. Python tests by directory: `**/migrations/**` → migrations; `tests/acceptance` → acceptance; `tests/apidocs`; `tests/relay_integration`; `tests/symbolicator`; `tests/snuba`.
5. Remaining Python tests in `tests/sentry`, `tests/integration`, `tests/apigw`, `tests/social_auth`: **endpoint** if the file matches `PY_ENDPOINT` or inherits from `APITestCase`/`APITransactionTestCase`/`APITestCaseMixin`; else **DB integration** if it matches `PY_DB` or inherits from any Django `TestCase`/`TransactionTestCase` descendant; else **no-DB**. Inheritance is resolved two ways: an `ast` class graph over `tests/`, `fixtures/` and `testutils` (class names, transitive; a bare `TestCase` imported from `unittest` is not counted as a DB base), and propagation through `from tests.x import ...` (five passes). Folding `tests/integration`, `tests/apigw` and `tests/social_auth` (11 files) into this split is a judgment call; they run in the same CI job and use the same base classes.
6. Frontend: `static/**/*.snapshots.tsx` → visual snapshot; `static/**/*.spec|test.(ts|tsx|js)` → **Jest component** if it imports `sentry-test/reactTestingLibrary` or `@testing-library/react`, or calls `render(`, `renderHook(`, `renderHookWithProviders(` or `renderGlobalModal(`; else **Jest logic**. `tests/js/**` non-spec, `static/**/__mocks__/**`, `static/**/fixtures/**`, `static/gsApp/__fixtures__/**`, `*testUtils*`/`*TestUtils*` and `*FixtureApi.tsx` files → JS helpers.
7. Production: `src/**` minus migrations, generated (`*.generated.*`) and `src/sentry/static`; `static/{app,gsApp,gsAdmin,packages}` minus tests, helpers, stories (`*.stories.tsx`, `__stories__/`) and generated files. `static/oxlint` rule sources → `other:lint_rules`. Everything else (scripts, tools, CI scripts, configs, devenv, bin) → `other`.

**Regular expressions** (Python `re`, applied to file text):

```
PY_TEST_FN    ^\s*(?:async\s+)?def test_?\w*\s*\(            (re.M)
JS_TEST_FN    (?<![\w.$])(?:it|test)(?:\.(?:each|only|skip|concurrent|isKnownFlake|snapshot|todo|failing))*\s*(?:<[^>\n]*>)?\s*[(`]
PY_ENDPOINT   \bself\.client\.(?:get|post|put|patch|delete|options|head|generic)\(|\bget_success_response\(|\bget_error_response\(|\bself\.get_response\(|\bAPITestCase\b|\bAPITransactionTestCase\b|\bAPITestCaseMixin\b|\bTwoFactorAPITestCase\b|\bSCIMTestCase\b|\bSCIMAzureTestCase\b|\bIntegrationRepositoryTestCase\b|\bReleaseCommitPatchTest\b|\bSetRefsTestCase\b|\bOrganizationDashboardWidgetTestCase\b|\bMetricsAPIBaseTestCase\b|\bOrganizationMetricsIntegrationTestCase\b|\bMonitorTestCase\b|\bMonitorIngestTestCase\b|\bAPIDocsTestCase\b|\bdjango\.test\.Client\b|\bfrom django\.test import [^\n]*\bClient\b
PY_DB         from sentry\.testutils\.cases import|import sentry\.testutils\.cases|\bdjango_db_all\b|pytest\.mark\.django_db|\bTransactionTestCase\b|from django\.test import [^\n]*TestCase|def \w+\([^)]*\b(?:db|transactional_db|default_project|default_organization|default_user|default_team|default_group|default_projectkey|default_environment|default_activity|factories)\b
PY_SNUBA      \brequires_snuba\b|pytest\.mark\.snuba\b|\bSnubaTestCase\b|\bBaseSpansTestCase\b|\bBaseMetricsTestCase\b|\bBaseMetricsLayerTestCase\b|\bMetricsEnhancedPerformanceTestCase\b|\bBaseIncidentsTest\b|\bOutcomesSnubaTest\b|\bProfilesSnubaTestCase\b|\bReplaysSnubaTestCase\b|\bUptimeCheckSnubaTestCase\b|\bReplaysAcceptanceTestCase\b|\bMetricsAPIBaseTestCase\b|\bOrganizationMetricsIntegrationTestCase\b|\bReplayEAPTestCase\b|\bPluginTestCase\b|\bAPIDocsTestCase\b|\breset_snuba\b|\bcall_snuba\b
PY_KAFKA      \brequires_kafka\b|\bkafka_producer\b|\bkafka_admin\b|\bscope_consumers\b|\bwait_for_ingest_consumer\b
PY_RELAY      \bRelayStoreHelper\b|\brelay_server\b
PY_SYMB       \brequires_symbolicator\b          PY_OBJSTORE \brequires_objectstore\b
PY_LIVE       \blive_server\b|\bself\.browser\b|\bAcceptanceTestCase\b
PY_INSTA      \binsta_snapshot\b
PY_MOCK_IMPORT ^\s*(?:from unittest import [^\n]*\bmock\b|from unittest\.mock import|import unittest\.mock|from unittest import mock|import mock\b|from mock import)   (re.M)
PY_MOCK_FIXTURE \bmonkeypatch\b|\bmocker\b
PY_MOCK_SITES \bpatch(?:\.object|\.dict|\.multiple)?\(|\bMagicMock\(|\bMock\(|\bAsyncMock\(|\bPropertyMock\(|\bcreate_autospec\(|\bmonkeypatch\.\w+\(|\bmocker\.\w+\(
PY_RESPONSES  ^\s*(?:import responses\b|from responses import)   (re.M);  sites: \bresponses\.(?:add|replace|upsert|add_callback|add_passthru)\(
JS_MOCK_IMPORT \bjest\.(?:mock|spyOn|fn|mocked|requireMock)\(
JS_MOCK_SITES  \bjest\.(?:mock|spyOn|fn|mocked|requireMock|doMock)\(
JS_API_MOCK    \bMockApiClient\.addMockResponse\(
JS_RTL         from ['"]sentry-test/reactTestingLibrary['"]|from ['"]@testing-library/react['"]
call checks    py: \.assert_(?:called|not_called|any_call|has_calls)\w*\(|\.call_count\b|\.call_args    js: toHaveBeenCalled\w*\(|toHaveBeenLastCalledWith\(|toHaveBeenNthCalledWith\(
assertions     py: ^\s*assert\b|self\.assert\w*\(   (re.M)    js: \bexpect\(
patch targets  \bpatch\(\s*["']([\w.]+)["']   (last dotted component tallied)
```

Known limits: `PY_TEST_FN` also matches helper names such as `def testing_x(`; parametrised tests and silo-multiplied classes count once; RuleTester-based lint tests have no `it(` and count as zero tests; the call-check share overlaps with assertion lines and is an indicator, not a ratio of disjoint sets; "real Snuba" for `tests/snuba` is 93% by pattern and 100% by the project's own definition.

**Ratios (section 5).** Endpoint layer = `prod:backend` files whose path starts `src/sentry/api/`, contains `/endpoints/` or `/api/`, or ends in `endpoints.py` (967 files). Snuba layer = `src/sentry/(snuba|search|utils/snuba|eventstore|tagstore|tsdb|sentry_metrics|services/eventstore)`. Per-package tables match `tests/sentry/<pkg>/` against `src/sentry/<pkg>/` for the endpoint, DB, no-DB and migration categories. Mirror rate: for each `tests/sentry/<dir>/test_<mod>.py`, check `src/sentry/<dir>/<mod>.py` or `src/sentry/<dir>/<mod>/`.

**History method.** Dates come from git history, not memory: `git clone --bare --filter=blob:none https://github.com/getsentry/sentry.git history.git` (read-only; a deviation from depth-1-only, used for `git log --grep`, path-limited `git log --reverse`, and `git log -S/-G` on single files), and the same for `getsentry/develop` (pre-2024 developer docs) and `getsentry/sentry-docs`. The deleted engineering posts were read from `getsentry/sentry.engineering` at the parent of its 2026-05-06 removal commit and are cited at their live blog.sentry.io URLs. Historical test-file counts were read with `git ls-tree` at the last commit before each date; acceptance test functions at four commits were counted from sparse worktrees of `tests/acceptance` only. Pull-request descriptions not present in commit messages were read on github.com (four pull-request pages and one issue search); api.github.com was refused by the session proxy. Commit messages are quoted verbatim, including their typos.

**Judgment calls and deviations.**

- Sentry's directories do not separate in-process API tests from other in-process database tests, so `tests/sentry` was split by what each file touches (rule 5). This split is ours, not the project's.
- The post's `api` means a real server over HTTP. Sentry's endpoint tests use the Django test client in process; they are mapped to `api` because every layer under the router is real, with the fit marked as approximate.
- The DB integration category has no slot; it is mapped to `adapters_free` as the nearest by realism, though in scope it resembles the post's `fast`.
- Tooling is included in the whole (1.1%), unlike the Robinauts chart; the backend-only table leaves it out.
- `src/sentry/testutils` ships inside the production package but is counted as helpers and excluded from production code.
- The frontend for the private SaaS layer (`static/gsApp`, `static/gsAdmin`) is counted with the frontend; its backend and its acceptance tests are in the private `getsentry` repository and not measured.
- Leads that did not verify as stated: `region_silo_test` no longer exists (renamed `cell_silo_test`, 2026-03); `fixtures/js-stubs` no longer exists (removed 2024-05-28, #71612; the docs still point to it); `django_db_all` is a decorator, not a registered mark; `requires_snuba`/`requires_kafka` are `usefixtures` marks that fail rather than skip; there is no `codecov.yml` and no Codecov status check at the snapshot, and no use of Codecov test analytics in Sentry's own CI was found; Celery is no longer part of the stack. Not found: a public design document for the silo test machinery (the blog post [43] is the closest primary account), the reasons for removing Percy and the 2023 visual snapshots (the latter sit in a private `getsentry` pull request), a published total runtime of the backend suite, a flake-rate figure, and whether any Codecov status was ever a required branch-protection check (statements in [3c] and [3e] say it was not at those dates).
