# Apache Superset: the shape of its tests

Measured: https://github.com/apache/superset at 42bbfa49079eff910ead01b7880b94d09c5ca520 (2026-10-11T14:48:29-07:00), default branch master.
Counted with notebooks/X-shapes-of-tests/tools/count_lines.py, rules as in
the brief. Deviations in the appendix.

## Summary

Posture: Superset writes down a test pyramid ("Superset embraces a testing pyramid approach") and its tree is one: a very wide, mock-heavy in-process base, a real-database middle, and a thin browser top.

| category | maps_to | lines | pct | tests |
|---|---|---:|---:|---:|
| Python unit tests (all) | unit / fast | 324,317 | 45.8 | 14,611 |
| Frontend Jest + RTL (all) | none (component tests with fakes) / unit | 288,759 | 40.8 | 13,641 |
| Python integration tests | api / adapters_free (poor fit) | 82,133 | 11.6 | 2,940 |
| Playwright e2e | e2e | 6,106 | 0.9 | 115 |
| testcontainers + satellites | adapters_free / unit | 6,333 | 0.9 | 292 |

History in one sentence: an all-integration Python suite was split in July 2021, Enzyme gave way to React Testing Library (2020 to 2025), and a flaky, costly Cypress suite was cut and replaced by a smaller Playwright suite under SIP-178 (July 2025 to October 2026), pushed in the end by an ASF Infra warning about CI runner use. Between January and October 2026 the Python unit suite grew from 56,542 to 324,317 lines, and half the commits touching Python tests carry an AI co-author line.

## 1. Posture and classification

**Written posture.** Four documents say where a test goes. They agree on a pyramid.

The developer docs' testing overview (added 2025-10-08, [#35217](https://github.com/apache/superset/pull/35217), live at superset.apache.org/developer-docs/testing/overview [2]):

> Superset embraces a testing pyramid approach:
> - Unit Tests: Fast, isolated tests for individual components and functions
> - Integration Tests: Tests that verify component interactions and API endpoints
> - End-to-End Tests: Full user journey testing in browser environments

The agent guide `AGENTS.md` (symlinked as `CLAUDE.md`, `GEMINI.md`, `GPT.md`; the section dates from 2025-07-22, [#34194](https://github.com/apache/superset/pull/34194); bold markers removed):

> Testing Strategy Migration
> - Prefer unit tests over integration tests
> - Prefer integration tests over end-to-end tests
> - Use Playwright for E2E tests - Cypress has been removed
> - Use Jest + React Testing Library for component testing
> - Use `test()` instead of `describe()`

The first version, in July 2025, read "Prefer integration tests over Cypress end-to-end tests" and "Cypress is last resort - Actively moving away from Cypress" ([#34194](https://github.com/apache/superset/pull/34194)).

The testing guidelines (`docs/developer_docs/testing/testing-guidelines.md`, imported from the project wiki on 2025-12-15, [#36523](https://github.com/apache/superset/pull/36523)):

> We feel that tests are an important part of a feature and not an additional or optional effort. That's why we colocate test files with functionality [...] Every new component or file added should have an associated test file with the `.test` extension.

> Do not use Playwright when RTL can do it better and faster. Tests that fall into the integration testing category belong in RTL, which is much faster and gives more immediate feedback. Playwright should be used mainly for end-to-end testing, replicating the user experience, with positive and negative flows.

The development-setup page says what the two Python directories are for:

> You can run unit tests found in `./tests/unit_tests` with pytest. It is a simple way to run an isolated test that doesn't need any database setup

> For more complex pytest-defined integration tests (not to be confused with our end-to-end Playwright tests), many tests will require having a working test environment. Some tests require a database, Celery, and potentially other services or libraries installed.

The backend and frontend testing pages are stubs ("🚧 Coming Soon 🚧"), and the CI/CD page names workflows that do not exist in the tree (`test-frontend.yml`, `test-backend.yml`).

**The tree**, one line per category, in the project's words where it has them:

```
tests/                                   Python, pytest (pytest.ini, testpaths = tests)
  unit_tests/          "an isolated test that doesn't need any database setup" (docs)
                       in practice: one process, Flask app per module, in-memory SQLite where needed
  integration_tests/   "Some tests require a database, Celery, and potentially other services" (docs)
                       Flask test client over a real metadata DB (MySQL, PostgreSQL, SQLite)
  testcontainers/      "exercises a real database via testcontainers-python (needs Docker)" (pytest.ini marker)
  common/ consts/ fixtures/ example_data/ conftest.py      shared helpers and example-data loaders
superset-frontend/
  src|packages|plugins/**/*.test.ts(x)   Jest + React Testing Library, colocated, jsdom, global fetch-mock
  spec/                helpers, fixtures, __mocks__ (plus three tests of build scripts)
  playwright/tests/    "Playwright end-to-end tests" against a running Superset
  playwright/{pages,components,helpers,utils}   page objects and API helpers
  **/*.stories.tsx     Storybook; "basic smoke tests" via the Storybook test runner
superset-websocket/spec, superset-embedded-sdk/src/*.test.ts,
superset-core/tests, superset-extensions-cli/tests     tests of satellite packages
```

**Pytest marks.** One mark is registered: `testcontainers`, deselected by default through `addopts = -m "not testcontainers"`. Two unregistered marks select subsets: `chart_data_flow` and `sql_json_flow`, which the Presto and Hive jobs run with `-m 'chart_data_flow or sql_json_flow'`. `query_object` parametrizes a fixture. The rest are plumbing: `parametrize` (2,423 uses), `asyncio` (1,639), `usefixtures` (1,033), `skip` (27), `skipif` (14), `xfail` (2). There is no mark for speed or layer; the directory is the classification.

**CI jobs** (`.github/workflows/`, required checks from `.asf.yaml`):

| Workflow | Job | What runs | Real services | Required |
|---|---|---|---|---|
| Python-Unit | `unit-tests` | `pytest -n auto --dist loadfile tests/common tests/unit_tests`, then two 100% coverage gates | none | yes (`unit-tests-required`) |
| Python-Integration | `test-mysql`, `test-postgres`, `test-sqlite` | `scripts/python_tests.sh`: `superset db upgrade`, `init`, `load-test-users`, `pytest tests/integration_tests` | MySQL 8 / PostgreSQL 17 / SQLite file, Redis, a Celery worker | yes |
| Python Presto/Hive | `test-postgres-presto`, `test-postgres-hive` | same script with `-m 'chart_data_flow or sql_json_flow'` | PostgreSQL + Presto container, or Hive via `docker compose`; Redis; Celery | yes |
| Testcontainers | `testcontainers` (matrix of 22 dialects) | `pytest -m testcontainers tests/testcontainers/db_engine_specs/test_<dialect>.py` | one Docker database per job | no; nightly, and on PRs touching `db_engine_specs` or the suite |
| Frontend Build CI | `sharded-jest-tests` (8 shards), `test-storybook`, `lint-frontend`, `bundle-size` | `npm run test -- --coverage --shard=n/8`; Storybook smoke run | none | only `frontend-build` (the Docker image build) |
| E2E | `playwright-tests` (two app roots), `playwright-tests-gaq` | Playwright: required set, then soft-delete, embedded and mobile steps; GAQ in its own job | gunicorn, PostgreSQL 17, Redis, examples loaded; Celery only for GAQ | yes (`playwright-tests-required`); GAQ job has `continue-on-error: true` |
| Chromatic | `chromatic` | builds Storybook and publishes it to Chromatic | none | no |
| Python-Nightly-Canary | `unit-tests-next` | unit tests on the next Python minor | none | no |
| Embedded SDK, websocket, extensions CLI | per package | Jest or pytest in the package | none | no |

All Python and E2E jobs sit behind a change detector (`scripts/change_detector.py`), so a frontend-only pull request does not run Python tests, and the reverse.

## 2. What the names mean

| Project's name | Where | What the tests actually touch | Nearest post category | Fit |
|---|---|---|---|---|
| unit tests (Python) | `tests/unit_tests/` (until July 2021 the DB-backed CI steps were themselves named "Python unit tests (MySQL)") | One process. Each module builds a full `SupersetApp`; `app_context` is autouse. 137 files open an in-memory SQLite session, 41 drive the Flask test client. No network, no external DB. Heavy mocks. | `unit` for most files; `fast` for the in-memory DB and test-client files | Poor. Not pure functions. In the post, `fast` is a declared extra copy; here nothing marks these tests as copies, and no rule asks for the same behavior to be proved elsewhere. |
| integration tests (Python) | `tests/integration_tests/` | One process. Flask test client (WSGI, no socket) over a real metadata DB, run three times (MySQL, PostgreSQL, SQLite); Redis; a Celery worker is started; examples loaded. 117 of 178 files use the `SupersetTestCase` base class. | `api` for the 68 files that call endpoints; `adapters_free` for the 110 others | Poor. No real server over HTTP, and the non-API files exercise commands, DAOs and models together against the DB, not one adapter. |
| testcontainers | `tests/testcontainers/` | One engine spec against one real database in Docker. No mocks. | `adapters_free` | Good. |
| frontend unit / integration tests (Jest, RTL) | colocated `*.test.ts(x)` | Node and jsdom. `fetchMock.mockGlobal()` is installed for every test; no backend. Redux store real in 210 files. | none; nearest `fast` (component files) and `unit` (logic files) | No slot. The post's taxonomy is backend-shaped. Superset calls RTL tests "integration" ("Tests that fall into the integration testing category belong in RTL"); seven files are named `*.integration.test.ts`, one of them described as an "Integration (mocked-network) port" of a Cypress spec. |
| E2E / end-to-end (Playwright) | `superset-frontend/playwright/tests/` | Chromium, gunicorn, PostgreSQL, Redis, example data; Celery for GAQ. Data created through the REST API per test. | `e2e` | Good. Until 2022 the project called its Cypress suite "integration": CONTRIBUTING.md read "We use [Cypress](https://www.cypress.io/) for integration tests" under a heading "Integration Testing", and the specs lived in `cypress/integration/` until April 2023. |
| Storybook stories | `**/*.stories.tsx` | Headless Chromium renders each story of a static Storybook build and fails on render errors. | none (examples) | No slot. |
| satellite package tests | four packages | In-process Jest or pytest, some mocks | `unit` | Fair. |
| tooling tests | ESLint rules, build scripts, a workflow script | The repository's own tooling | `tooling` | Good. |

## 3. Categories outside the post's taxonomy

**Frontend component tests (Jest and React Testing Library).** 711 files, 156,941 lines, 7,061 tests (files that render with RTL); another 663 files, 131,818 lines, 6,580 tests test frontend logic without rendering. They prove that components and reducers behave as a user would see them, with the network faked. The project keeps them because, in the guidelines' words, RTL "is much faster and gives more immediate feedback" than a browser, and because SIP-56 (2020) made RTL the standard: "It encourages developers to focus on what users see, as opposed to how the components are implemented." [9]. This is the second-largest body of test code in the repository.

**Storybook stories as smoke tests, and visual review.** 148 story files, 17,563 lines, 255 exported stories. Since 2025-12-16 ([#36498](https://github.com/apache/superset/pull/36498)) the `test-storybook` CI job builds Storybook and renders every story; `.storybook/test-runner.ts` calls them "basic smoke tests - they don't test interactions or assertions, just that stories can render successfully." Chromatic publishing of Storybook runs on PRs since 2022-08-23 ([#21095](https://github.com/apache/superset/pull/21095)); it is not a required check. Applitools visual tests ran from 2022-05-09 ([#19956](https://github.com/apache/superset/pull/19956)) until removed on 2026-02-11 ([#37873](https://github.com/apache/superset/pull/37873): "We're no longer using this service."). Counted as the examples row and left out of the whole.

**Cross-database matrix.** Not a separate directory but a dimension: the whole integration suite runs against MySQL, PostgreSQL and SQLite, and the `chart_data_flow`/`sql_json_flow` subset runs with Presto or Hive as the examples database. Superset is a BI tool that talks to many databases, so the metadata store and the query path are tested on several engines. Of 102 flow-marked integration tests, 73 are unconditionally skipped at the snapshot (section 9), so the two Presto and Hive jobs, both required, exercise 29 tests.

**Migration tests.** `tests/unit_tests/migrations` (33 files, 3,905 lines, 143 tests) and `tests/integration_tests/migrations` (13 files, 1,605 lines, 45 tests) check Alembic data migrations. They are inside the unit and integration rows.

**Satellite packages.** `superset-websocket` (2 files, 1,100 lines, 73 tests), `superset-embedded-sdk` (3, 495, 27), `superset-extensions-cli` (9, 2,527, 134), `superset-core` (3, 108, 9). They have their own row in the whole. I found no workflow that runs `superset-core/tests`.

**Tooling tests.** 11 files, 663 lines: ESLint rule tests, three tests of build scripts in `spec/scripts`, the webpack proxy config, a workflow shell script, the data generator used by integration tests, and the Yeoman plugin generator (its two tests are not run by CI). Left out of the whole, as in the Robinauts chart.

**Not tests.** `playwright/generators/docs/*.spec.ts` (545 lines) are Playwright scripts that take documentation screenshots; no workflow runs them. A bundle-size comparison runs on PRs with `fail-on-alert: false`.

## 4. Lines per category

Code lines (total minus blank minus full-line comments), helpers excluded. Percentages are of the whole, which is the nine test rows; tooling and the Storybook examples are shown below the line and not included.

| Category | Language | Files | Code lines | % of whole | Test functions |
|---|---|---:|---:|---:|---:|
| Python unit tests, other | Python | 652 | 238,820 | 33.7 | 11,333 |
| Frontend Jest, component (RTL render) | TypeScript | 711 | 156,941 | 22.2 | 7,061 |
| Frontend Jest, logic | TypeScript | 663 | 131,818 | 18.6 | 6,580 |
| Python unit tests, in-memory DB or test client | Python | 169 | 85,497 | 12.1 | 3,278 |
| Python integration, over the test client | Python | 68 | 46,676 | 6.6 | 1,764 |
| Python integration, other | Python | 110 | 35,457 | 5.0 | 1,176 |
| Playwright e2e | TypeScript | 38 | 6,106 | 0.9 | 115 |
| Satellite packages | Python 2,635 / TS 1,595 | 17 | 4,230 | 0.6 | 243 |
| testcontainers | Python | 22 | 2,103 | 0.3 | 49 |
| **Whole** | | **2,450** | **707,648** | **100** | **31,553** |
| Tooling (outside the whole) | TS, Python, shell | 11 | 663 | | 25 |
| Storybook stories (examples, outside the whole) | TypeScript | 148 | 17,563 | | 255 stories |

By language: Python 408,553 lines (57.7%), TypeScript 294,865 (41.7%), satellites 0.6%. No frontend test file is JavaScript any more; a pre-commit rule has refused new `.js` files in the frontend source trees since 2026-06-24 ([#41385](https://github.com/apache/superset/pull/41385)).

**Same dimension as the Robinauts chart** (backend plus e2e, frontend Jest left out, since Robinauts counted its backend suite):

| Post category | Superset rows | Lines | % | Robinauts % |
|---|---|---:|---:|---:|
| e2e | Playwright | 6,106 | 1.5 | 11.5 |
| api | integration over the test client | 46,676 | 11.3 | 16.9 |
| adapters | integration other + testcontainers | 37,560 | 9.1 | 34.6 |
| unit | unit tests, other | 238,820 | 57.6 | 17.7 |
| fast | unit tests with in-memory DB or test client | 85,497 | 20.6 | 19.2 (extra copy) |
| total | | 414,659 | 100 | 6,500 lines |

**Helpers**, excluded above: 435 files, 21,225 lines. Python integration helpers 5,349 (base classes, test configs, fixture modules such as `fixtures/importexport.py`, 776 lines); Python unit helpers 1,773; shared Python helpers 960; frontend helpers 6,746 (`spec/helpers`, `spec/fixtures`, `__mocks__`, test-only fixture files); Playwright page objects and API helpers 4,762, which is 78% of the size of the Playwright specs; Storybook config 595; satellite helpers and the embedded-SDK browser rig 975; testcontainers helpers 65.

**Test data** is small. `tests/` holds 9 non-code files (0.1 MB: 5 JSON, 1 CSV, 1 PNG, 1 text file, and an editor autosave file `#sqlite_test.py#`); the frontend holds 19 (0.1 MB, mostly JSON, one Jest snapshot). The data that integration and e2e tests run on comes from the product's own examples (`superset/examples`: 135 YAML and 21 Parquet files, 32.8 MB), loaded by `superset load_examples` or by Python loaders in `tests/example_data`.

**The shape over time** (same counting tool on sparse historical checkouts; test files only):

| Date | Python, flat or integration | Python unit | Frontend Jest/Mocha | Cypress | Playwright |
|---|---|---|---|---|---|
| 2018-12-31 | 23 files / 7,149 lines / 341 tests | — | 164 / 11,020 / 861 | 37 / 2,144 / 95 | — |
| 2021-06-30 (before the split) | 108 / 33,580 / 1,452 | — | 341 / 30,554 / 1,927 | 55 / 3,907 / 145 | — |
| 2021-12-31 | 111 / 37,097 / 1,582 | 17 / 3,624 / 125 | 525 / 48,053 / 3,043 | 56 / 4,223 / 151 | — |
| 2022-12-31 | 125 / 39,479 / 1,663 | 81 / 11,491 / 421 | 616 / 63,540 / 3,737 | 59 / 6,216 / 258 | — |
| 2024-12-31 | 118 / 45,575 / 1,782 | 175 / 30,684 / 1,078 | 709 / 101,638 / 4,555 | 54 / 6,774 / 257 | — |
| 2025-07-16 (SIP-178 opened) | 117 / 46,058 / 1,815 | 185 / 36,063 / 1,227 | 778 / 111,129 / 4,946 | 48 / 6,359 / 195 | — |
| 2025-12-31 | 124 / 51,279 / 2,045 | 246 / 56,542 / 2,204 | 884 / 140,743 / 6,556 | 45 / 5,619 / 163 | 2 / 163 / 5 |
| 2026-06-02 | 140 / 57,744 / 2,277 | 388 / 116,100 / 5,591 | 1,047 / 194,190 / 9,144 | 9 / 1,462 / 31 | 10 / 1,695 / 44 |
| 2026-09-29 | 175 / 77,909 / 2,861 | 756 / 270,239 / 12,697 | 1,347 / 272,560 / 13,008 | removed | 35 / 5,231 / 103 |

Cypress counts include files in its `integration/` or `e2e/` folders that CI had excluded by naming them `_skip.*`.

## 5. Test-to-code ratio

Production code excludes tests, `superset/migrations` (416 files, 23,511 lines), two vendored folders, the plugin generator's templates, `.d.ts` stubs in `types/` folders, build and lint scripts, docs, Helm and Docker files. Production totals: backend `superset/` 242,003 lines (1,147 files); frontend `src`, `packages/*/src`, `plugins/*/src` 304,249 (2,360); satellites 4,968 (51).

| Test category | Production component | Test lines | Code lines | Ratio |
|---|---|---:|---:|---:|
| Python unit tests | `superset/` | 324,317 | 242,003 | 1.34 |
| of which MCP service tests | `superset/mcp_service/` | 112,243 | 67,186 | 1.67 |
| of which engine-spec tests | `superset/db_engine_specs/` | 21,170 | 20,753 | 1.02 |
| Python integration tests | `superset/` (whole backend) | 82,133 | 242,003 | 0.34 |
| testcontainers | `superset/db_engine_specs/` | 2,103 | 20,753 | 0.10 |
| All Python tests | `superset/` | 408,553 | 242,003 | 1.69 |
| Jest tests in `src/` | `superset-frontend/src` | 185,520 | 183,127 | 1.01 |
| Jest tests in `packages/` | `packages/*/src` | 41,038 | 34,505 | 1.19 |
| Jest tests in `plugins/` | `plugins/*/src` | 62,201 | 86,617 | 0.72 |
| Playwright e2e | whole product, backend + frontend | 6,106 | 546,252 | 0.011 |
| Satellite tests | satellite packages | 4,230 | 4,968 | 0.85 |
| Whole | whole product incl. satellites | 707,648 | 551,220 | 1.28 |

The MCP service (a tool server for LLM clients, added in 2025) carries 35% of all Python unit-test lines.

## 6. Detroit or London

Heuristic, per test file (exact patterns in the appendix). A file "imports a mocking facility" when it matches the Python or JS file pattern. Mock call sites are creations of doubles and patches (`Mock(`, `MagicMock(`, `patch(`, `patch.object(`, `monkeypatch.setattr(`; `jest.fn(`, `jest.mock(`, `jest.spyOn(`, `fetchMock.get(` and siblings; Playwright `page.route(`). Real-dependency use is read from the CI job a category runs in, plus file patterns for in-memory SQLite and test-client calls.

| Category | Files | Files with a mock facility | Share | Mock call sites | Per 1,000 lines | Real dependencies |
|---|---:|---:|---:|---:|---:|---|
| Python unit, other | 652 | 469 | 72% | 14,022 | 58.7 | none; in-process Flask app |
| Python unit, in-memory DB or test client | 169 | 139 | 82% | 4,958 | 58.0 | SQLite in memory (137 files), Flask test client (41) |
| Python integration, over the test client | 68 | 41 | 60% | 733 | 15.7 | real metadata DB in three engines, Redis, Celery worker |
| Python integration, other | 110 | 59 | 54% | 970 | 27.4 | same |
| testcontainers | 22 | 0 | 0% | 0 | 0 | one Docker database per file |
| Jest, component | 711 | 560 | 79% | 4,866 | 31.0 | none; global `fetchMock`; 149 files route it explicitly; 101 files `jest.mock` child components |
| Jest, logic | 663 | 167 | 25% | 1,331 | 10.1 | none |
| Playwright e2e | 38 | 1 | 3% | 2 | 0.3 | gunicorn, PostgreSQL, Redis, examples; Celery for GAQ |
| Satellites | 17 | 4 | 24% | 95 | 22.5 | none |

**Where each sits.** The unit tests are London. They mock the neighbours and check calls: 406 files under `tests/unit_tests` make 4,237 interaction assertions (`assert_called*`, `assert_any_call`, `assert_has_calls`, `call_count`, `call_args`), against 45 files and 467 in `tests/integration_tests`; on the frontend, 474 test files make 3,403 `toHaveBeenCalled*` assertions. The most patched targets are `superset.daos.dataset.DatasetDAO.find_by_id` (125 patches), `superset.mcp_service.middleware.get_user_id` (111), `DashboardDAO.find_by_id` (111) and `superset.db.session` (72 plus 77 for `superset.extensions.db.session`). Even the in-memory database is injected by a patch: the `get_session` fixture in `tests/unit_tests/conftest.py` does `mocker.patch("superset.db.session", in_memory_session)`. The integration tests are Detroit about the database and London about the edges: they keep the metadata DB real and patch the request user (`superset.security.manager.g`, 117 patches), feature flags, SMTP, screenshots and Slack. The frontend component tests fake the whole backend; the shim installs `fetchMock.mockGlobal()` for every test, but render real children and, in 210 files, a real Redux store, so they are sociable inside the browser and solitary at the network. Playwright and testcontainers are fully Detroit: Playwright intercepts the network only in one GAQ resilience spec, to inject faults.

The newest category is an explicit Detroit move. Its pull request ([#43502](https://github.com/apache/superset/pull/43502), Evan Rusackas, merged 2026-09-09) says the existing engine-spec unit tests "mock the driver/dialect layer entirely, which structurally cannot catch bugs in how SQLAlchemy actually compiles and executes SQL against a real server" and "Only a real round-trip against a live instance catches that class of bug."

Against the post: Robinauts treats the real-server test as the proof and the in-process copy as an optional extra. Superset does the reverse. Its written rule ranks unit above integration above e2e, its unit tests mock heavily, and its browser layer is 1.5% of backend-plus-e2e lines.

## 7. The web UI

Three layers test the UI.

1. **Jest with React Testing Library** (component tests with fakes): 711 rendering files, 156,941 lines, plus 663 logic files, 131,818 lines; 13,641 tests in all. jsdom, a global fetch mock, a custom `render()` in `spec/helpers/testing-library.tsx` with Redux, router and theme providers. CI runs them in eight shards inside a Docker image and uploads coverage to Codecov.
2. **Playwright** (browser over a real backend): 38 spec files, 6,106 lines, 115 tests, with 4,762 lines of page objects and API helpers. CI starts gunicorn on PostgreSQL with the example data, runs a required set twice (at `/` and at `/app/prefix`), then three flag-gated steps (soft delete, embedded dashboards, mobile) and, in a separate non-required job, Global Async Queries with a Celery worker. Chromium only, two workers, two retries in CI.
3. **Storybook**: 255 stories smoke-rendered in CI and published to Chromatic.

**Which is the proof.** By policy, RTL. The guidelines send everything that is not a full user journey to RTL, and the Cypress-to-Playwright migration moved many old browser specs into RTL rather than into Playwright: chart list, dashboard list, controls, database modal, standalone mode, favorite toggle and the remaining Explore specs ([#35181](https://github.com/apache/superset/pull/35181), [#37813](https://github.com/apache/superset/pull/37813), [#38368](https://github.com/apache/superset/pull/38368), [#41436](https://github.com/apache/superset/pull/41436), [#40914](https://github.com/apache/superset/pull/40914), [#40872](https://github.com/apache/superset/pull/40872), [#44838](https://github.com/apache/superset/pull/44838)). By merge gate, Playwright. Since 2025-01-07 ([#31490](https://github.com/apache/superset/pull/31490)) the Jest run lives in `sharded-jest-tests`, which is not in the `.asf.yaml` list of required checks; the required `frontend-build` job only builds the image. Before that date `frontend-build` ran Jest itself. Playwright has been required since 2025-11-10 ([#35938](https://github.com/apache/superset/pull/35938)). Inference: since January 2025 a red Jest shard does not block a merge by machine, only by the reviewers' rule that "Reviewers will not review the code until all CI tests are passed" (contribution guidelines).

## 8. Enforcement by machine

| Mechanism | What it checks | Where | Since |
|---|---|---|---|
| Required status checks | Unit, integration (MySQL, PostgreSQL, SQLite, Presto, Hive), Playwright, pre-commit must pass | `.asf.yaml` | Required review 2021-02-02 ([#12694](https://github.com/apache/superset/pull/12694)); test checks 2021-02-05 to 2021-02-09 ([#12928](https://github.com/apache/superset/pull/12928), [#12969](https://github.com/apache/superset/pull/12969), [#12970](https://github.com/apache/superset/pull/12970), the last one adding Cypress) |
| Required-check anchors that refuse a false green | `playwright-tests-required` fails if change detection did not succeed: "refusing to pass on a skipped matrix" | `superset-e2e.yml` | 2026-06-05 ([#40780](https://github.com/apache/superset/pull/40780)) |
| Strict testcontainers import | With `SUPERSET_TESTCONTAINERS_STRICT`, a missing driver fails the job instead of `importorskip`, so it cannot report "a misleadingly green, zero-tests-run result" | `tests/testcontainers/db_engine_specs/_driver.py`, `testcontainers.yml` | 2026-09-09 ([#43502](https://github.com/apache/superset/pull/43502)) |
| Default deselection | `-m "not testcontainers"` keeps Docker tests out of plain `pytest` runs | `pytest.ini` | 2026-09-09 ([#43502](https://github.com/apache/superset/pull/43502)) |
| No services in the unit job | The unit job has no database, Redis or Celery; a unit test that needs one fails | `superset-python-unittest.yml` | 2021-07-12 ([#15507](https://github.com/apache/superset/pull/15507), Amit Miran: "create unit test workflow to run purely pytest") |
| Global fetch mock | Every Jest test runs with `fetchMock.mockGlobal()`; no test reaches a real backend | `superset-frontend/spec/helpers/shim.tsx` | in the shim since 2026-01-30, with the fetch-mock 12 upgrade ([#36662](https://github.com/apache/superset/pull/36662)); before that, files imported fetch-mock themselves |
| 100% coverage gates | `--cov-fail-under=100` on `superset/sql/` and on `superset/semantic_layers/` inside the required unit job | `superset-python-unittest.yml` | 2025-06-05 for SQL ([#33568](https://github.com/apache/superset/pull/33568)); 2026-05-05 for semantic layers ([#37815](https://github.com/apache/superset/pull/37815)) |
| Frontend core coverage gate (removed) | `npm run core:cover`: 100% statements, branches, functions and lines on `packages/**/src/**/*.{js,ts}` in the required `frontend-build` job | `superset-frontend.yml` | 2022-07-20 ([#20784](https://github.com/apache/superset/pull/20784)); moved to a non-required job 2025-01-07 ([#31490](https://github.com/apache/superset/pull/31490)); removed 2025-06-20 ([#31590](https://github.com/apache/superset/pull/31590)) |
| Jest lint rules | `jest/no-focused-tests`, `jest/no-disabled-tests`, `jest/expect-expect`, `jest/consistent-test-it` with `test` only | `superset-frontend/oxlint.json` | focused tests banned since 2020-08-21 (`no-only-tests`, [#10606](https://github.com/apache/superset/pull/10606)); current set since 2026-02-08 ([#37787](https://github.com/apache/superset/pull/37787)) |
| Un-awaited `userEvent` | Fails a test file that fires `userEvent` without `await`, a named source of flakes | `scripts/check-custom-rules.js` via pre-commit | 2026-10-07 ([#44947](https://github.com/apache/superset/pull/44947)) |
| TypeScript only | Refuses new `.js`/`.jsx` files, tests included, in `src/`, `packages/*/src`, `plugins/*/src` | same | 2026-06-24 ([#41385](https://github.com/apache/superset/pull/41385)) |
| `debug-statements`, `check-docstring-first` | No `pdb`/`breakpoint` left in Python, tests included | `.pre-commit-config.yaml` | not dated |
| Change detection | Runs Python jobs only on Python changes and frontend jobs only on frontend changes | `scripts/change_detector.py` | 2021-02-05 ([#12583](https://github.com/apache/superset/pull/12583)) |
| Hold labels | A `hold*` label fails a check and cancels CI | `no-hold-label.yml`, `hold-label-ci-gate.yml` | not dated |

No label widens the test run. Nothing checks placement: no rule says which directory a new test belongs in, nothing stops a "unit" test from opening a database, and nothing checks that a test file is collected. `tests/unit_tests/sql_lab_execution_context.py` holds six `test_` functions but does not match `python_files` in `pytest.ini`, so by my reading of that configuration pytest has never collected it since it was added on 2024-06-20 ([#29231](https://github.com/apache/superset/pull/29231)). Two silent-skip paths remain: the `playwright-run` shell function returns success with "No test files found ... skipping test run" when a path matches no spec, and 126 integration test functions are unconditionally skipped (section 9).

## 9. History

**The Python suite: from all-integration to a mock-heavy base.** Until mid-2021 every Python test sat in a flat `tests/` folder and ran inside the app with a database: 108 files, 33,580 lines, 1,452 tests on 2021-06-30. The runner had moved from nose to pytest a year earlier, on 2020-06-29 ([#10177](https://github.com/apache/superset/pull/10177), Bogdan, bkyryliuk); the PR states the change but gives no reason or runtime numbers ("Changed test runner from nosetests to pytest"). On 2021-07-01 ofekisr moved everything into `tests/integration_tests` and created an empty `tests/unit_tests` ([#15473](https://github.com/apache/superset/pull/15473)). His premise: "unittests should not depend on app_context or any database". Beto Dealmeida wrote the first unit-test `conftest.py` a week later ([#15578](https://github.com/apache/superset/pull/15578), 2021-07-08) and converted tests in December 2021 ([#17655](https://github.com/apache/superset/pull/17655), [#17689](https://github.com/apache/superset/pull/17689)). So the common account that Beto drove the split is half right: ofekisr made the split, Beto built and populated the unit layer.

The premise did not hold. Beto's own unit tests needed an app context because of import side effects. In August 2022 Jesse Yang made the app context autouse for every unit test ([#20911](https://github.com/apache/superset/pull/20911)), and the unit `conftest.py` grew an in-memory SQLite session and a Flask test client. At the snapshot 169 unit-test files (26% of unit lines) use one of them. The written guidance still says unit tests need no database.

The steer itself succeeded slowly and then all at once. Unit tests passed integration tests in lines and test count only in the second half of 2025 (56,542 against 51,279 lines on 2025-12-31). In 2026 the unit suite went from 56,542 to 324,317 lines and from 2,204 to 14,611 test functions; integration grew from 51,279 to 82,133. That growth coincides with AI-assisted commits: of 1,452 commits in 2026 that touch `tests/unit_tests` or `tests/integration_tests`, 759 (52%) carry an AI co-author or "Generated with" line, against 37 of 306 in 2025 and none of 300 in 2024 (pattern in the appendix). The causal link is my inference. The project's agent guide tells agents to "Prefer unit tests over integration tests", and the tree follows it. By September 2026 the serial unit run took 27 to 28 minutes and had to be parallelized ([#44178](https://github.com/apache/superset/pull/44178)).

In September 2026 the project added the first suite that tests engine specs against the real external databases they wrap, `tests/testcontainers` ([#43502](https://github.com/apache/superset/pull/43502)), after bugs that mocked engine-spec tests could not catch.

**The frontend: Enzyme to React Testing Library.** Jest replaced Mocha and Chai on 2018-10-15 ([#6079](https://github.com/apache/superset/pull/6079)). SIP-56 (Jesse Yang, 2020-11-13, [#11688](https://github.com/apache/superset/issues/11688); vote passed 2020-12-01 [10]) adopted RTL without forcing a migration. Tests moved next to the code from `spec/` into `src/` between 2021-04-23 and 2022-01-07 ([#14200](https://github.com/apache/superset/pull/14200) to [#17902](https://github.com/apache/superset/pull/17902), Michael S. Molina). Files using Enzyme fell from 154 (November 2020) to 116 (end of 2023), 44 (end of 2024) and 11, which were deleted rather than ported on 2025-06-06 ([#33715](https://github.com/apache/superset/pull/33715)). The steer succeeded: no Enzyme left, and the lint rules now enforce `test` over `it`. The "avoid nesting" rule has not landed: 455 of 1,374 Jest files still use `describe`.

**The browser suite: Cypress, flakiness, cost, Playwright.** Cypress arrived on 2018-09-06 ([#5693](https://github.com/apache/superset/pull/5693)). The first flaky test was disabled three weeks later ([#6008](https://github.com/apache/superset/pull/6008), "[cypress] Disable flaky dashboard test"). From 2018 to 2026, 59 merged pull requests have "flaky" in the title; 16 of those titles name Cypress or E2E, and others concern SQL Lab, dashboard and filter tests of the same suite or Python and Jest tests. The suite peaked at 59 files and 258 tests at the end of 2022. Parallelism depended on the paid Cypress Dashboard: the project voted in November 2020 to add a record key to GitHub secrets (passed with 8 binding +1s) [14], switched to `pull_request_target` so that forks could use it ([#11750](https://github.com/apache/superset/pull/11750)), and in June 2024 dropped recording because Preset was paying ([#29077](https://github.com/apache/superset/pull/29077)), then split specs across runners with its own script.

SIP-178 (Joe Li, 2025-07-16, [#34197](https://github.com/apache/superset/issues/34197); vote passed 2025-09-12) proposed replacing Cypress with Playwright, starting with an audit to "Remove any tests that do not represent true end-to-end workflows". Playwright entered CI on 2025-09-17 ([#35110](https://github.com/apache/superset/pull/35110)) and became a required check on 2025-11-10 ([#35938](https://github.com/apache/superset/pull/35938)). On 2026-01-21 the example-data rewrite ([#36538](https://github.com/apache/superset/pull/36538)) renamed 24 Cypress specs to `_skip.*`, taking the active set from 34 files to 11, and the same commit added skips to 112 Python integration tests with the reason "TODO: Fix test class to work with DuckDB example data format". The PR description says "Some Cypress tests temporarily skipped" and "All Python unit and integration tests pass"; it does not mention the Python skips. Those 112 skips are still in the snapshot, and they are why the Presto and Hive jobs run only 29 tests.

The last push came from outside. On 2026-05-22 ASF Infra told the PMC that Superset was "among the top 5 consumers of build time over the past 7 days" and gave it until 2026-06-08 [23]. Evan Rusackas answered that Cypress was "about half the consumption". Within two weeks the project deleted 27 dead `_skip.*` specs ([#40384](https://github.com/apache/superset/pull/40384)), cut Cypress from six shards to two ([#40717](https://github.com/apache/superset/pull/40717)) and moved the `/app/prefix` variant to `master` only ([#40385](https://github.com/apache/superset/pull/40385)). By 2026-06-11 Superset had dropped to seventh. Cypress went to one runner on 2026-08-03 ([#42715](https://github.com/apache/superset/pull/42715)) and was removed on 2026-10-01 ([#44829](https://github.com/apache/superset/pull/44829), [#44854](https://github.com/apache/superset/pull/44854)). Meanwhile the `/app/prefix` and embedded runs came back onto every pull request on 2026-09-06 ([#43919](https://github.com/apache/superset/pull/43919)), because the master-only arrangement meant "pull requests never actually exercised it before merge". The steer worked on cost and tooling. The browser layer ended smaller in tests (258 Cypress tests at the 2022 peak, 115 Playwright tests now) at about the same size in lines (6,216 then, 6,106 now).

**Coverage.** Codecov replaced Coveralls in March 2018. It has not been a required check in `.asf.yaml` since that file appeared in August 2020; the history is in section 12.

## 10. Timeline

| Date | Change | Driven by | Link |
|---|---|---|---|
| 2018-03-06 | Codecov replaces Coveralls | John Bodley | [#4533](https://github.com/apache/superset/pull/4533) |
| 2018-09-06 | Cypress browser tests added | michellethomas | [#5693](https://github.com/apache/superset/pull/5693) |
| 2018-09-28 | First flaky Cypress test disabled | Krist Wongsuphasawat | [#6008](https://github.com/apache/superset/pull/6008) |
| 2018-10-15 | Jest replaces Mocha and Chai for the frontend | Christine Chambers | [#6079](https://github.com/apache/superset/pull/6079) |
| 2018-10-17 | SIP-13 proposes coverage checks, "initially as a non-required check" | Krist Wongsuphasawat | [#6132](https://github.com/apache/superset/issues/6132) |
| 2019-06-03 | `.codecov.yml` with target `auto`, threshold 0% | michellethomas | [#7433](https://github.com/apache/superset/pull/7433) |
| 2020-04-14 | First GitHub Actions workflows | Jianchao Yang | [#9517](https://github.com/apache/superset/pull/9517) |
| 2020-06-29 | pytest replaces nose | Bogdan (bkyryliuk) | [#10177](https://github.com/apache/superset/pull/10177) |
| 2020-11-03 | Vote to add a Cypress record key for recording and parallel runs | Evan Rusackas | dev@ [14] |
| 2020-12-01 | SIP-56 passes; React Testing Library added | Jesse Yang | [#11688](https://github.com/apache/superset/issues/11688), [#11771](https://github.com/apache/superset/pull/11771) |
| 2021-02-05 to 02-09 | Test jobs, Cypress included, become required checks; change detection skips unaffected suites | Elizabeth Thompson, Ville Brofeldt | [#12928](https://github.com/apache/superset/pull/12928), [#12970](https://github.com/apache/superset/pull/12970), [#12583](https://github.com/apache/superset/pull/12583) |
| 2021-02-25 | Codecov statuses made informational | Jesse Yang | [#13329](https://github.com/apache/superset/pull/13329) |
| 2021-04-23 to 2022-01-07 | Frontend tests moved from `spec/` next to the code | Michael S. Molina | [#14200](https://github.com/apache/superset/pull/14200), [#17902](https://github.com/apache/superset/pull/17902) |
| 2021-07-01 | Python tests split into `integration_tests` and `unit_tests` | ofekisr | [#15473](https://github.com/apache/superset/pull/15473) |
| 2021-07-08 | First unit-test `conftest.py` | Beto Dealmeida | [#15578](https://github.com/apache/superset/pull/15578) |
| 2021-07-12 | Separate Python-Unit CI job with no services; the DB jobs become Python-Integration | Amit Miran | [#15507](https://github.com/apache/superset/pull/15507) |
| 2021-12-14 | Codecov target for frontend core packages raised from 95% to 100% | Yongjie Zhao | [#17698](https://github.com/apache/superset/pull/17698) |
| 2022-05-09 | Applitools visual tests added | Geido | [#19956](https://github.com/apache/superset/pull/19956) |
| 2022-07-20 | 100% coverage gate on frontend core packages inside the required job | Yongjie Zhao | [#20784](https://github.com/apache/superset/pull/20784) |
| 2022-08-02 | `app_context` autouse in all unit tests | Jesse Yang | [#20911](https://github.com/apache/superset/pull/20911) |
| 2022-08-23 | Storybook published to Chromatic | Eric Briscoe | [#21095](https://github.com/apache/superset/pull/21095) |
| 2023-04-21 | "#1 flaky test" skipped | Evan Rusackas | [#23772](https://github.com/apache/superset/pull/23772) |
| 2024-06-05 | Cypress recording only on manual runs, for cost | Maxime Beauchemin | [#29077](https://github.com/apache/superset/pull/29077) |
| 2025-01-07 | Jest moves to eight shards outside the required job | Maxime Beauchemin | [#31490](https://github.com/apache/superset/pull/31490) |
| 2025-06-05 | 100% coverage gate for `superset/sql/` | Beto Dealmeida | [#33568](https://github.com/apache/superset/pull/33568) |
| 2025-06-06 | Remaining Enzyme tests deleted | Maxime Beauchemin | [#33715](https://github.com/apache/superset/pull/33715) |
| 2025-06-20 | Frontend core coverage job removed | Maxime Beauchemin | [#31590](https://github.com/apache/superset/pull/31590) |
| 2025-07-16 | SIP-178 (Cypress to Playwright) opened | Joe Li | [#34197](https://github.com/apache/superset/issues/34197) |
| 2025-07-22 | LLM guide: "Prefer unit tests over integration tests" | Maxime Beauchemin | [#34194](https://github.com/apache/superset/pull/34194) |
| 2025-09-12 | SIP-178 vote passes | Joe Li | dev@ [18] |
| 2025-09-17 | Playwright in CI | Joe Li | [#35110](https://github.com/apache/superset/pull/35110) |
| 2025-10-08 | Docs declare a testing pyramid | Evan Rusackas | [#35217](https://github.com/apache/superset/pull/35217) |
| 2025-11-10 | Playwright becomes a required check | Joe Li | [#35938](https://github.com/apache/superset/pull/35938) |
| 2026-01-21 | Example-data rewrite skips 24 Cypress specs and 112 integration tests | Evan Rusackas | [#36538](https://github.com/apache/superset/pull/36538) |
| 2026-05-22 | ASF Infra: Superset among top five CI consumers | Bob Thomson (ASF Infra) | dev@ [23] |
| 2026-06-03 | Cypress shards cut from six to two | Evan Rusackas | [#40717](https://github.com/apache/superset/pull/40717) |
| 2026-09-06 | Embedded and `/app/prefix` Playwright runs required on PRs | Joe Li | [#43919](https://github.com/apache/superset/pull/43919) |
| 2026-09-09 | testcontainers suite against real databases | Evan Rusackas | [#43502](https://github.com/apache/superset/pull/43502) |
| 2026-09-12 | Unit suite parallelized with pytest-xdist | Mike Bridge | [#44178](https://github.com/apache/superset/pull/44178) |
| 2026-10-01 | Cypress removed | Joe Li, Evan Rusackas | [#44829](https://github.com/apache/superset/pull/44829), [#44854](https://github.com/apache/superset/pull/44854) |

## 11. The arguments, turn by turn

**Coverage as a hard gate (2018 to 2019).** SIP-13 [32] wanted automatic coverage checks because "this enforces the contributing guidelines of unit testing", but "initially as a non-required check as we iterate on the configuration settings." When thresholds came in, DiggidyDave asked for more ([#7433](https://github.com/apache/superset/pull/7433), 2019-05-24):

> can we hold a hard line on this and disallow any reduction in coverage? — DiggidyDave

Maxime Beauchemin explained why that could not be bypassed in an emergency:

> Nope I think you need admin to override the blockers, which none of the committers get. — mistercrunch

The threshold was set to 0%. Two years later conditional CI made it noisy, and Jesse Yang turned it off ([#13329](https://github.com/apache/superset/pull/13329), 2021-02-25): "Always let GitHub CodeCov checks pass because we don't always report all test coverage (because of conditional CI jobs)." The PR says the old setting "starts to block some PRs on status check due to false alarms of decreased test coverage". Numbers: none published.

**React Testing Library (2020).** Jesse Yang's SIP-56 [9] argued from behaviour over implementation:

> It encourages developers to focus on what users see, as opposed to how the components are implemented. — ktmud (Jesse Yang)

> Since there is no urgent need to migrate existing Enzyme tests, RTL and Enzyme will live side-by-side for as long as needed. — ktmud

Objections were about scope, not direction:

> While I think that RTL has a lot of merit, I don't think that we should completely throw out the idea of unit tests. — eschutho (Elizabeth Thompson)

> What exactly are the problems with current Enzyme testing that necessitate migrating to a new testing library? — robdiciuccio (Rob DiCiuccio)

> I'd say we don't enforce it as much as simply favoring it for a phase ahead in a transitional period. — mistercrunch (Maxime Beauchemin)

Five years later the leftovers were deleted, not ported ([#33715](https://github.com/apache/superset/pull/33715)):

> As discussed with some core committers, we believe it's a net positive to drop all remaining Enzyme tests even if that means lowering test coverage. — mistercrunch

> There were surprisingly few Enzyme tests left, so I don't think this will have any significant impact on stability. — villebro (Ville Brofeldt)

Numbers: Enzyme files 154 (Nov 2020), 116 (Dec 2023), 44 (Dec 2024), 11 (5 June 2025), 0 (6 June 2025; 12 test files deleted).

**The unit/integration split (2021 to 2022).** Pain: every Python test needed the app and a database. The arguments:

> unittests should not depend on app_context or any database — ofekisr, #15473

> a simple folder migration from tests to tests/integration-tests as preparation for moving only unittests into separated folders that would be ran differently and will eventually reduce tests run time — amitmiran137 (Amit Miran)

> Thank you so much for this PR, @ofekisr! I started adding some (proper) unit tests and it's so good to have them run almost instantaneously. — betodealmeida (Beto Dealmeida)

Beto then named the obstacle while converting tests ([#17655](https://github.com/apache/superset/pull/17655), 2021-12):

> They're not pure unit tests, since some of the imports have side-effects that require mocking `SQLALCHEMY_DATABASE_URI`, but they run in a few seconds. — betodealmeida

> Note that this is a consequence of bad architecture in Superset. — betodealmeida, review reply in #17655

And Jesse Yang gave up on the no-app-context rule ([#20911](https://github.com/apache/superset/pull/20911), 2022-08):

> I have yet to see a test case where having an app_context is troublesome. Since it's fairly cheap to create a new context, we can just autouse the `app_context` fixture to save some boilerplate code. — ktmud

Numbers: before, 108 files and 1,452 tests, all integration (2021-06-30). Six months after, 17 unit files with 125 tests (2021-12-31). Unit overtook integration at the end of 2025. At the snapshot, 821 unit files with 14,611 test functions against 178 integration files with 2,940. Runtime: "The serial suite has grown to ~27–28 minutes"; with xdist "the parallel step ran in 14m07s on the 4-core runners", and a "Local full run, 8 workers, coverage on: 15,128 passed in 3m36s." ([#44178](https://github.com/apache/superset/pull/44178), Mike Bridge, 2026-09-12; the last two quotes are from its commit message). No integration-suite runtime was published that I could find.

**Cypress flakiness and cost (2018 to 2024).** The flaky tests were handled one by one: disabled, retried, skipped. One sample ([#23772](https://github.com/apache/superset/pull/23772), 2023-04-21), whose TODO calls it "the #1 flaky test as of 4/21/23 according to cypress dashboard":

> This test was restarted 11 times before I finally caved in and `xit`ed it in #23751. — villebro

Then money. Evan Rusackas asked dev@ in 2020 for a record key "to improve our Cypress tests by capturing screenshots/recordings, and (hopefully) parallelizing the tests being run" [14]. In 2024 Maxime Beauchemin turned recording off ([#29077](https://github.com/apache/superset/pull/29077)):

> Preset is picking up the bill for Cypress.io and it's getting pricey for the usage we have for it. — mistercrunch

> ok so --parallel is a paid feature, seems we'll have to find some other way to segment/parallelize — mistercrunch

**SIP-178, Cypress to Playwright (2025).** Joe Li's proposal [18]:

> Superset's current E2E suite, built on Cypress, has shown increasing issues with flakiness, slowness, and high maintenance overhead. Additionally, changes in Cypress's licensing model and ecosystem direction have raised concerns about its long-term viability. — sadpandajoe (Joe Li)

Its evaluation table put Cypress at "Parallelism is paywalled" and "Increasingly commercialized, some core features behind login", Playwright at "Native support for parallelism, retries, trace output". Support was unanimous and about developer pain:

> Cypress was a major pain point so switching to Playwright might be the best dev-ex improvement yet. — msyavuz

> It's often quite challenging to determine the root cause when tests fail in CI but not locally, — EnxDev (Enzo Martellucci)

> I love that we're removing flakiness, removing legacy platforms, and consolitating on tooling that people like :) — rusackas (Evan Rusackas)

The only caution was cost: "Pretty typical question, but do we know the cost of running Cypress and Playwright simultaneously" (eschutho). The plan's baseline was "~50+ test files" and a "6-way split", with the target "Playwright tests run 30-50% faster than Cypress". I found no published measurement of that target.

**The ASF runner quota (2026).** The pain arrived as a deadline:

> Your project has been identified as being among the top 5 consumers of build time over the past 7 days and we request that you bring your usage down by stream-lining long-running builds. — Robert Thomson, ASF Infrastructure, 2026-05-22

> Cypress is the obvious killer (about half the consumption). — Evan Rusackas, 2026-05-22

> There’s an alternate (radical) solution of just NOT running E2E tests on PRs, but only running them on master. Sure would “nip it in the bud” cost wise, but has potential repercussions if we don’t keep a close eye on CI on `master` — Evan Rusackas, 2026-06-03

The project did not take the radical option. Numbers from [#40717](https://github.com/apache/superset/pull/40717): "Only 5 spec files / 31 test cases remain under cypress/e2e"; each job spent "~8–10 min" installing before running its slice; "On master that's 6 shards × 2 app_roots = 12 Cypress jobs (~143 runner-minutes for the whole E2E workflow)". After the cuts ASF reported "the project has dropped out of the top 5 to 7" (2026-06-11) and, on 2026-06-22, "superset-e2e (3.4%), supetset-frontend (2.5%), docker (2.3%), superset-python-integration-test (2%) are the largest consumers of the time superset uses" [23]. The master-only `/app/prefix` run was reversed in September because it meant "pull requests never actually exercised it before merge" ([#43919](https://github.com/apache/superset/pull/43919)). Dead tests found on the way: [#40384](https://github.com/apache/superset/pull/40384) "Deletes 27 `_skip.*` spec files that are permanently excluded from CI via `excludeSpecPattern: ['**/_skip.*']` in `cypress.config.ts`" and states "These files never run and exist only as dead code."

**Real databases for engine specs (2026).** Quoted in section 6. The PR lists the bugs that mocks missed: Trino emitting OFFSET before LIMIT ([#42899](https://github.com/apache/superset/issues/42899)) and a CockroachDB dialect broken under SQLAlchemy 2.0. Numbers: 22 dialects, 49 tests, 2,103 lines, nightly plus path-filtered PRs, not required.

## 12. Coverage

**Measured: yes. Gated: partly, and narrowly.**

- 2015-09-28: Coveralls configured ([commit 391b31e](https://github.com/apache/superset/commit/391b31e35)).
- 2018-03-06: Codecov replaces Coveralls ([#4533](https://github.com/apache/superset/pull/4533)).
- 2018-10-17: SIP-13 proposes project and patch coverage checks, non-required at first [32].
- 2019-06-03: `.codecov.yml` sets project target `auto` and threshold 0% ([#7433](https://github.com/apache/superset/pull/7433)). Codecov has never appeared in the required checks of `.asf.yaml` (all 52 versions since 2020-08-03 checked). Whether the Codecov status blocked merges before that file existed is not established: the 2019 discussion speaks of "blockers" that only admins could override, and the 2021 fix says the status "starts to block some PRs", but I found no branch-protection record listing it.
- 2021-02-25 and 2021-03-01: project and patch statuses made informational ([#13329](https://github.com/apache/superset/pull/13329), [#13375](https://github.com/apache/superset/pull/13375)). They still are.
- 2021-11-30: Codecov targets for the frontend core packages, 95% for non-TSX files and 50% for TSX, not informational and not required ([#17552](https://github.com/apache/superset/pull/17552)); raised to 100% for non-TSX on 2021-12-14 ([#17698](https://github.com/apache/superset/pull/17698)).
- 2022-07-20 to 2025-01-07: a real gate. `npm run core:cover` with a 100% Jest threshold on `packages/**/src/**/*.{js,ts}` ran inside the required `frontend-build` job ([#20784](https://github.com/apache/superset/pull/20784)). It moved to a non-required job on 2025-01-07 ([#31490](https://github.com/apache/superset/pull/31490)) and was removed on 2025-06-20 ([#31590](https://github.com/apache/superset/pull/31590)).
- Since 2025-06-05: `--cov-fail-under=100` on `superset/sql/` in the required unit job ([#33568](https://github.com/apache/superset/pull/33568)); since 2026-05-05 also on `superset/semantic_layers/` ([#37815](https://github.com/apache/superset/pull/37815)).
- Uploads at the snapshot: Python unit, MySQL, PostgreSQL, SQLite, Presto and Hive runs, and the Jest shards; carry-forward flags since 2021-03 ([#13677](https://github.com/apache/superset/pull/13677)). Cypress runs uploaded frontend coverage from 2020-04-16 ([#9555](https://github.com/apache/superset/pull/9555)); Playwright does not. Codecov comments on PRs in September and October 2026 report project coverage of 79.42% ([#43919](https://github.com/apache/superset/pull/43919)) and 81.71% ([#44829](https://github.com/apache/superset/pull/44829)).
- One policy statement treats coverage as expendable: the Enzyme deletion accepted "lowering test coverage" ([#33715](https://github.com/apache/superset/pull/33715)).

## Chart-ready table

category | maps_to (post taxonomy) | lines | pct | files | tests
---|---|---:|---:|---:|---:
Playwright e2e | e2e | 6106 | 0.9 | 38 | 115
Python integration, over the Flask test client | api (poor fit: in-process WSGI) | 46676 | 6.6 | 68 | 1764
Python integration, other | adapters_free (poor fit: many adapters at once) | 35457 | 5.0 | 110 | 1176
testcontainers | adapters_free | 2103 | 0.3 | 22 | 49
Python unit, in-memory DB or test client | fast (poor fit: not a declared extra copy) | 85497 | 12.1 | 169 | 3278
Python unit, other | unit (poor fit: mock-heavy, app context) | 238820 | 33.7 | 652 | 11333
Frontend Jest, component (RTL) | none (component tests with fakes) | 156941 | 22.2 | 711 | 7061
Frontend Jest, logic | unit | 131818 | 18.6 | 663 | 6580
Satellite packages | unit | 4230 | 0.6 | 17 | 243
Tooling (not in pct) | tooling | 663 | | 11 | 25
Storybook stories (examples, not in pct) | none | 17563 | | 148 | 255

## Sources

1. apache/superset repository at 42bbfa49079eff910ead01b7880b94d09c5ca520, 2026-10-11: `AGENTS.md`, `pytest.ini`, `.asf.yaml`, `.codecov.yml`, `.pre-commit-config.yaml`, `.github/workflows/*.yml`, `.github/workflows/bashlib.sh`, `scripts/python_tests.sh`, `scripts/change_detector.py`, `tests/unit_tests/conftest.py`, `tests/integration_tests/conftest.py`, `tests/testcontainers/db_engine_specs/_driver.py`, `superset-frontend/jest.config.js`, `playwright.config.ts`, `oxlint.json`, `scripts/check-custom-rules.js`, `spec/helpers/shim.tsx`, `.storybook/test-runner.ts`, `docs/developer_docs/testing/*.md`, `docs/developer_docs/contributing/*.md`.
2. Superset developer docs, Testing Overview, https://superset.apache.org/developer-docs/testing/overview, fetched 2026-10-11.
3. PR #15473, refactor(tests): decouple unittests from integration tests, 2021-07-01. https://github.com/apache/superset/pull/15473
4. PR #15578, feat: validate_parameters for GSheets (first unit conftest), 2021-07-08, https://github.com/apache/superset/pull/15578; PR #15507, move memoized tests to unit tests (creates the Python-Unit job), 2021-07-12, https://github.com/apache/superset/pull/15507
5. PR #17655, feat: convert dataframe tests, 2021-12-09; PR #17689, convert feature flag tests to unit tests, 2021-12-08. https://github.com/apache/superset/pull/17655, https://github.com/apache/superset/pull/17689
6. PR #20911, test: autouse app_context in unit tests, 2022-08-02. https://github.com/apache/superset/pull/20911
7. PR #10177, feat: Switch from nosetest to pytest, 2020-06-29. https://github.com/apache/superset/pull/10177
8. PR #44178, ci(python-unit): run the unit suite in parallel with pytest-xdist, 2026-09-12. https://github.com/apache/superset/pull/44178
9. SIP-56, Adopt React Testing Library, issue #11688, 2020-11-13 to 2020-12-11. https://github.com/apache/superset/issues/11688
10. dev@ threads: [DISCUSS] [SIP-56], 2020-11-14, https://lists.apache.org/thread/jg6cl6ph2x738m3rmjvyrhwjhsgrj22o; [Result][VOTE] SIP-56, 2020-12-01, https://lists.apache.org/thread/qq8nmfndxjvtj0tlm4ylj7pov68vmvr5
11. PR #11771, test: add React Testing Library, 2020-12-01; PR #14200 and #17902, spec files moved to src, 2021-04-23 and 2022-01-07. https://github.com/apache/superset/pull/11771
12. PR #33715, chore: delete remaining Enzyme tests, 2025-06-06. https://github.com/apache/superset/pull/33715
13. PR #5693, Adding simple Cypress tests, 2018-09-06; PR #6008, Disable flaky dashboard test, 2018-09-28; GitHub search of merged PRs with "flaky" in the title (59 results), fetched 2026-10-11. https://github.com/apache/superset/pulls?q=is%3Apr+flaky+in%3Atitle+is%3Amerged
14. dev@ [VOTE] Add Cypress record key to Github secrets, Evan Rusackas, 2020-11-03, https://lists.apache.org/thread/k4z09c6vjxfdoclh4mdyddj0f5grkc6n; [RESULT] 2020-11-07 (8 binding +1s), https://lists.apache.org/thread/lyq9xlzh7oqn5d6h0p3k625pvbdo237o
15. PR #11750, Cypress via pull_request_target, 2020-12-16. https://github.com/apache/superset/pull/11750
16. PR #23772, skip the worst offender of flaky tests, 2023-04-21; PR #21941, most common flaky Cypress tests, 2022-10-27. https://github.com/apache/superset/pull/23772
17. PR #29077, only use cypress.io when triggered manually, 2024-06-05. https://github.com/apache/superset/pull/29077
18. SIP-178, issue #34197, 2025-07-16 to 2026-02-25; dev@ [DISCUSS] 2025-07-17 https://lists.apache.org/thread/t6xxtht9c3qsyj9qxhsntcyp0z3qm038, [VOTE] 2025-09-08 https://lists.apache.org/thread/m0wqgkyrxo7tyk9ncnd80spxflswdfyx, [RESULT][VOTE] 2025-09-12 https://lists.apache.org/thread/26odlkvzpvn5prl87xlw5ko50hb6gzkl. https://github.com/apache/superset/issues/34197
19. PR #32194, migrate E2E testing to Playwright, phase 1, closed 2025-05-09. https://github.com/apache/superset/pull/32194
20. PR #35110, Playwright CI integration, 2025-09-17 (merge commit date; page shows 2025-09-18). https://github.com/apache/superset/pull/35110
21. PR #35938, remove Cypress auth tests, Playwright required, 2025-11-10. https://github.com/apache/superset/pull/35938
22. PR #36538, modernize example data loading, 2026-01-21. https://github.com/apache/superset/pull/36538
23. dev@ thread "Superset Consumption of ASF Shared GitHub-hosted Runners", 2026-05-22 to 2026-06-22. https://lists.apache.org/thread/3n1j78nxp1myqx8dpmjcyvf81h1qmyrj
24. PR #40384, remove dead _skip spec files, 2026-05-23. https://github.com/apache/superset/pull/40384
25. PR #40385, limit /app/prefix to master merges, 2026-05-22. https://github.com/apache/superset/pull/40385
26. PR #40717, reduce Cypress parallelism from 6 shards to 2, 2026-06-03. https://github.com/apache/superset/pull/40717
27. PR #42715, collapse Cypress matrix to 1 runner, 2026-08-03. https://github.com/apache/superset/pull/42715
28. PR #43919, embedded and app-root E2E required, 2026-09-06. https://github.com/apache/superset/pull/43919
29. PR #44829, remove Cypress infrastructure, 2026-10-01; PR #44854, drop cypress-matrix-required, 2026-10-01. https://github.com/apache/superset/pull/44829
30. PR #43502, testcontainers-based db_engine_specs tests, 2026-09-09. https://github.com/apache/superset/pull/43502
31. PR #35181, #37813, #38368, #41436, #40914, #40872, #44838: Cypress specs ported to RTL, 2025-09-18 to 2026-10-02.
32. SIP-13, Proposal for Code Review Process, issue #6132, 2018-10-17. https://github.com/apache/superset/issues/6132
33. PR #4533, replacing coveralls with codecov, 2018-03-06. https://github.com/apache/superset/pull/4533
34. PR #7433, codecov targets and thresholds, 2019-06-03. https://github.com/apache/superset/pull/7433
35. PR #13329, optimize codecov config, 2021-02-25; PR #13375, 2021-03-01; PR #13677, carryforward flags, 2021-03-22.
36. PR #17552, monorepo stage 2 (Codecov core-package targets), 2021-11-30; PR #17698, core coverage to 100%, 2021-12-14; PR #20784, core coverage step, 2022-07-20; PR #31490, Docker-sharded frontend CI, 2025-01-07; PR #31590, Ant Design v5 overhaul (removes core-cover job), 2025-06-20.
37. PR #33568, 100% test coverage for SQL parsing, 2025-06-05; PR #37815, semantic layer extension, 2026-05-05.
38. PR #34194, LLM context guides, 2025-07-22; PR #35217, developer portal, 2025-10-08; PR #36523, contribution guidelines from wiki, 2025-12-15.
39. PR #12694, #12928, #12969, #12970, required checks, 2021-02-02 to 2021-02-09; PR #12583, conditional test skips, 2021-02-05; PR #40780, required-check anchors, 2026-06-05.
40. PR #10606 (no-only-tests), 2020-08-21; PR #36662 (fetch-mock 12, global mock in the Jest shim), 2026-01-30; PR #37787 (Jest rules to oxlint), 2026-02-08; PR #44947 (awaited userEvent), 2026-10-07; PR #41385 (TypeScript only), 2026-06-24.
41. PR #19956 (Applitools), 2022-05-09; PR #37873 (Applitools removed), 2026-02-11; PR #21095 (Chromatic), 2022-08-23; PR #36498 (Storybook test runner in CI), 2025-12-16.
42. PR #6079, Mocha+Chai to Jest, 2018-10-15; PR #9517, GitHub workflows, 2020-04-14; PR #9555, frontend coverage from Cypress, 2020-04-16; PR #29231, SQLLAB_FORCE_RUN_ASYNC (adds the uncollected test file), 2024-06-20.
43. Git history of apache/superset `master` (blobless clone, 23,660 commits), read 2026-10-11, for commit dates, file counts and historical line counts.

## Appendix: commands and counting decisions

**Snapshot.**
```
mkdir -p $SCRATCH/superset-clone && cd $SCRATCH/superset-clone
git clone --depth 1 https://github.com/apache/superset.git
git -C superset log -1 --format='%H %cI'
# 42bbfa49079eff910ead01b7880b94d09c5ca520 2026-10-11T14:48:29-07:00
python3 -I notebooks/X-shapes-of-tests/tools/count_lines.py $CLONE --by-file > all_by_file.csv
```
Default extensions and excludes of the tool. The default excludes removed only two vendored folders (`plugin-chart-calendar/src/vendor`, `plugin-chart-parallel-coordinates/src/vendor`); there are no `build`, `dist` or `coverage` folders in the tree. The tool does not recognise docstrings, so Python docstrings count as code; JSDoc blocks start with `/*` and count as comments. Lines in all tables are the tool's `code` column.

**Grouping rules** (my script `classify.py`, run as `python3 -I classify.py $CLONE all_by_file.csv classified.csv`; the result is `superset.counts.csv` with `category` and an extra `test_functions` column):

- Python test file: under `tests/`, basename matches `*_test.py`, `test_*.py` or `*_tests.py` (pytest.ini `python_files`; the fourth pattern `*viz/utils.py` matches nothing), and contains `^\s*(async\s+)?def\s+test_\w*\s*\(`. Any other `.py` under `tests/` is a helper. This puts `tests/unit_tests/sql_lab_execution_context.py` (6 test functions, not collected by pytest) in helpers.
- `tests/unit_tests` split: a test file is `py_unit_inprocess_db_or_http` if it matches
  `def\s+test_\w*\s*\([^)]*\b(session|client|get_session|full_api_access)\b|create_engine\(\s*["']sqlite|\bsession\.(add|add_all|query|flush|commit|execute)\(|\bclient\.(get|post|put|delete|patch)\(` (DOTALL); else `py_unit_other`. Known noise: a docstring mentioning `db.session.commit()` puts `mcp_service/test_middleware.py` in the first group.
- `tests/integration_tests` split: `py_integration_http` if it matches `\bself\.client\.(get|post|put|delete|patch)\(|\b(test_)?client\.(get|post|put|delete|patch)\(|\bget_assert_metric\(|\bself\.get_json_resp\(|\bself\.get_resp\(|\bself\.post_assert_metric\(|\bself\.put_assert_metric\(|\bself\.delete_assert_metric\(`; else `py_integration_other`.
- `tests/testcontainers`: `test_*.py` are tests; `_driver.py`, `_pagination.py`, `__init__.py` are helpers.
- `tests/common`, `tests/consts`, `tests/fixtures`, `tests/example_data`, `tests/conftest.py`, `tests/__init__.py`: shared Python helpers, except `tests/example_data/data_generator/tests/*`, which is tooling.
- Jest test file: Jest's own `testRegex`, `superset-frontend/(spec|src|plugins|packages|tools)/.*(_spec|\.test)\.[jt]sx?$`. Files under `spec/`, `tools/` and `eslint-rules/` are tooling. Others are `fe_jest_component` if the file matches `@testing-library/react|spec/helpers/testing-library|superset-ui-core/src/spec|from ['"][./]*spec['"]|@superset-ui/core/spec|\brender\(|renderHook\(` and is `.tsx`/`.jsx`, or is `.ts` and also imports `@testing-library/react` or uses `renderHook(`; else `fe_jest_logic`.
- Frontend helpers: non-test files under `spec/`, or under a folder named `test`, `tests`, `__tests__`, `__mocks__`, `fixtures`, `spec` inside `src`, `packages/*` or `plugins/*`, or with a basename like `fixtures`, `mocks`, `testUtils`, `testHelpers`, `testData`. Three fixture-named files are imported by production code and stay production: `src/explore/fixtures.tsx`, `packages/superset-ui-chart-controls/src/fixtures.ts`, `src/utils/testUtils.ts` (checked by grep for imports from non-test files).
- Playwright: `playwright/tests/**/*.spec.ts` are e2e; everything else under `playwright/` plus `playwright.config.ts` is helpers; `playwright/generators/` is excluded (screenshot generators, not run by CI).
- `*.stories.*` under `superset-frontend`: examples row; `.storybook/`: helpers.
- `packages/generator-superset`: excluded as templates (including a 32,160-line `package-lock.erb`), except its `test/*.test.ts`, which are tooling.
- Satellites: `superset-core/tests`, `superset-extensions-cli/tests` (Python test files by the pytest rule; others helpers), `superset-websocket/spec/*.test.ts`, `superset-embedded-sdk/src/*.test.ts`; `superset-embedded-sdk/testrig/` is a manual browser rig, counted as helpers.
- `.github/workflows/scripts/*.test.sh`: tooling.
- Production: `superset/**/*.py` minus `superset/migrations/`; `superset-frontend/src/**` and `superset-frontend/(packages|plugins)/*/src/**` minus tests, helpers and stories; satellite `src/` trees. Not production: `types/*.d.ts` stubs outside `src`, build scripts and configs, `docs/`, `scripts/`, `docker/`, `helm/`, `RELEASING/`, the `.erb` templates. `superset/cli/test_db.py`, `superset/cli/test_loaders.py` and `superset/commands/database/test_connection.py` are production code despite their names.

**Test-function counts.** Python: the `def test_` pattern above, so parametrized cases count once. Jest: `(?<![\w.])(?:it|test)(?:\.(?:each|concurrent|failing)\b[^(]*\([^)]*\))?\s*\(\s*[`'"]`; a plain `grep -oE "(^|[^.a-zA-Z_])(it|test)(\.each)?\("` gives 13,652 against 13,641. Playwright: `(?<![\w.])(?:test|testWithAssets)(?:\.(?:fixme|fail|slow))?\s*\(\s*[`'"]` (69 `test(` plus 46 `testWithAssets(`; `test.skip(` calls are conditional skips inside tests and are not counted). Stories: lines matching `^export const [A-Z]`. ESLint rule tests use `RuleTester` arrays and count as 0.

**Mock and real-dependency patterns** (script `mocks.py`, per file):
- Python file imports a mocking facility: `^\s*(from\s+unittest\s+import\s+[^\n]*\bmock\b|from\s+unittest\.mock\s+import|import\s+unittest\.mock|from\s+mock\s+import|import\s+mock\b|from\s+pytest_mock\s+import)|\bmocker\b|\bmonkeypatch\b` (MULTILINE).
- Python call sites: `\b(?:MagicMock|NonCallableMagicMock|Mock|AsyncMock|PropertyMock|create_autospec)\(|\bpatch(?:\.object|\.dict|\.multiple)?\(|\bmonkeypatch\.(?:setattr|setitem|setenv|delattr|delitem|delenv|syspath_prepend|chdir)\(`.
- JS file: `\bjest\.(?:mock|doMock|unstable_mockModule|spyOn|fn|replaceProperty)\(|from\s+['"](?:fetch-mock|msw[^'"]*|sinon|jest-websocket-mock)['"]|require\(['"](?:fetch-mock|msw|sinon)['"]\)|\bfetchMock\b`.
- JS call sites: `\bjest\.(?:mock|doMock|unstable_mockModule|spyOn|fn|replaceProperty)\(|\bfetchMock\.(?:get|post|put|delete|patch|head|mock|route|once|any|sticky|catch|modifyRoute)\w*\(`; Playwright: `\.route\(|\.routeFromHAR\(`.
- In-memory DB: `def\s+test_\w*\s*\([^)]*\b(session|get_session)\b|create_engine\(\s*["']sqlite|\bsession\.(add|add_all|query|flush|commit|execute)\(`; test client: `\b(self\.)?(test_)?client\.(get|post|put|delete|patch)\(|def\s+test_\w*\s*\([^)]*\bclient\b|\bget_assert_metric\(|\bget_json_resp\(|\bget_resp\(`; metadata DB: `\bSupersetTestCase\b|\bdb\.session\b|\bload_birth_names|\bload_world_bank|\bload_energy|login_as|\bapp_context\b`.
- Interaction assertions: `grep -rhoE "\.assert_(called|not_called|any_call|has_calls)\w*\(|\.call_count|\.call_args" tests/<dir> --include=*.py` (helpers included) and `grep -rhoE "toHaveBeenCalled\w*\("` over `*.test.ts(x)` in `src`, `packages`, `plugins`.
- Patch targets: `grep -rhoE "patch(\.object|\.dict)?\(\s*[\"'][a-zA-Z_.]+" tests/<dir> | sed -E "s/.*[\"']//" | sort | uniq -c | sort -rn`.
- Network fakes in component tests: `fetchMock|spyOn\(SupersetClient|SupersetClient\.(get|post|put|delete|request) *= *jest|jest\.mock\(['"][^'"]*(api|Api|hooks/apiResources|SupersetClient|connection)`; real store: `useRedux`; child-component mocks: `jest\.mock\(['"][^'"]*components/`.
- Real services per category are read from the workflow that runs it, not from files: every integration test runs with a real DB, Redis and a started Celery worker, whatever its file matches.

**Skips** (script `skips.py`, Python `ast` over file text, no import): a test function counts as unconditionally skipped if it, or an enclosing class, has a decorator whose source starts with `pytest.mark.skip(` or equals `pytest.mark.skip`, or the module sets `pytestmark` to a `skip(` that is not `skipif`. Results: integration 126 of 2,938; unit 1 of 14,617; 112 of the integration skips carry "DuckDB" in the reason. Flow-marked tests (`flowmarks.py`): 102 under a `chart_data_flow` or `sql_json_flow` mark, 29 of them not under a skip decorator.

**History** (deviation, see below):
```
git clone --filter=blob:none --no-checkout --single-branch --branch master \
    https://github.com/apache/superset.git superset-history
git log --reverse --format='%h %ad %an | %s' --date=short -- tests/unit_tests        # and other paths
git log --format='%h %cd %an | %s' --date=short -S '<string>' -- <file>             # pickaxe for mechanisms
git rev-list -1 --before='<date> 23:59' HEAD
git worktree add --no-checkout wt <sha>; git -C wt sparse-checkout set --no-cone '/tests/' \
  '/superset-frontend/cypress-base/cypress/' '/superset/assets/cypress/' '*.test.ts' '*.test.tsx' \
  '*.test.js' '*.test.jsx' '*_spec.js' '*_spec.jsx' '*_spec.ts' '*_spec.tsx' '/superset-frontend/playwright/'
git -C wt checkout -q <sha>; python3 -I count_lines.py wt --by-file | snap.py
```
Historical rows use the same test-file rules, except that a Cypress row is every `.js/.ts` file under a Cypress `integration/` or `e2e/` folder (helpers and `_skip.*` files included), and the frontend row is every `(\.test\.|_spec\.)` file outside Cypress, which before 2019 means Mocha `_spec.js` files under `superset/assets/spec`. Enzyme files: test files matching `enzyme|styledMount|styledShallow|spec/helpers/theming|\bshallow\(|\bmount\(`.

AI co-author markers: `git log --since=<y>-01-01 --until=<y>-12-31 --format=%h -E -i --grep="co-authored-by: claude|generated with \[?claude|claude\.ai/code|co-authored-by: copilot|co-authored-by: cursor|codex" -- tests/unit_tests tests/integration_tests | wc -l`, against the same command without `--grep`. It counts commits, not lines, and misses AI use that left no trailer.

Mailing list: `https://lists.apache.org/api/stats.lua?domain=superset.apache.org&list=dev&q=<term>&d=lte=20y` (the form `d=gte=2019-01-01` returned zero hits for every term), then `api/thread.lua?id=` and `api/email.lua?id=` for bodies. Terms tried: pytest, cypress, playwright, SIP-178, flaky, codecov, coverage, unit tests, integration tests, runners, E2E, Enzyme, React Testing Library, Storybook, Applitools, testing strategy, test environments, CI.

Not found, and where I looked: the reason for the nose-to-pytest switch (PR #10177 and its review, dev@ search for "pytest": no hits); an integration-suite runtime (workflow comments, PRs #44178 and #40717, dev@); any measurement of SIP-178's "30-50% faster" target (SIP-178 issue and its PRs); the original author and date of the wiki page "Testing Guidelines and Best Practices" (the wiki URL now shows the wiki home); a preset.io engineering post on test strategy (two web searches; the only hit was a third-party summary of an April 2021 Preset post about GitHub Actions and ephemeral test environments); a SIP on overall test strategy (GitHub SIP issue searches and dev@).

**Judgment calls.**
- The in-memory/test-client split of `tests/unit_tests` is mine, not the project's; it exists to place part of the unit suite near the post's `fast` slot.
- Integration tests over the test client map to `api` although no socket is opened. The post's `api` means a real server over HTTP; nothing in Superset's Python suite starts one.
- Satellite tests are in the whole; tooling and Storybook stories are not. Storybook stories are smoke-rendered in CI, but they assert nothing.
- Frontend Jest is in the whole. For comparison with the Robinauts chart, which is backend-only, the second table in section 4 leaves it out.
- Dates are commit dates on `master` (`%cd`) unless a PR page was read; where they differ by a day (time zones), the PR page wins and both are named where it matters.
- WebFetch summarizes pages, so every quote from a GitHub page was re-requested as character-for-character text before use; quotes from the mailing list come from the raw API; quotes from the repository were copied from the files.

**Deviations from the brief.**
- I made a second, history-only clone (`--filter=blob:none --no-checkout`) and sparse historical worktrees in the scratchpad to date changes and count old trees. The brief says to use GitHub for dates; the GitHub API was not reachable from this session (repository-scoped responses only, search API refused), and `github.com` pages were read through WebFetch. All measurement tables for the current shape use the depth-1 snapshot only. Both clones and the worktree were deleted afterwards.
- `superset.counts.csv` carries one extra column, `test_functions`, after `category`.
- Common accounts of this history that did not hold, recorded in the body: the split was made by ofekisr, not Beto Dealmeida (who built the unit layer); Cypress no longer exists at the snapshot (`cypress-base` was removed on 2026-10-01); Cypress was never moved to a label, and only partly and briefly off the pull-request path (recording on `master` only from 2024, the `/app/prefix` variant on `master` only from May to September 2026); no SIP addresses Python test strategy (SIP-13 touches coverage, SIP-56 the React test library, SIP-178 the browser framework); Codecov was never a required check in `.asf.yaml` (coverage did gate, through Jest and pytest thresholds); and the frontend's `spec/` folder now holds helpers, not tests.
