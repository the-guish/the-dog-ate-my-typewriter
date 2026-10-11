# Apache Airflow: the shape of its tests

Measured: https://github.com/apache/airflow at 4ca1f6693bb380ae1f148a6187001adbcadbfa22 (2026-10-11T08:00:35-05:00), default branch main.
Counted with notebooks/X-shapes-of-tests/tools/count_lines.py, rules as in
the brief. Deviations in the appendix.

## Summary

Posture: Airflow's docs and tools describe a pyramid. Most of the suite is in-process pytest code, split by a machine-enforced line into tests that may touch a real database (SQLite, PostgreSQL, MySQL) and tests that may not; real-server and browser suites are thin (under 1% of lines), and most of them date from 2025.

Shape by lines (791,956 test lines in 2,869 files; helpers and tooling excluded):

| unit, no DB | unit, real DB | system tests (example DAGs) | other-language SDKs | Helm | UI Vitest | real-server suites | integration | browser e2e |
|---|---|---|---|---|---|---|---|---|
| 54.6% | 27.2% | 6.6% | 4.1% | 3.1% | 3.1% | 0.7% | 0.4% | 0.2% |

Realism: provider unit tests lean London (82% of their files use a mocking facility, 69 mock calls per 1,000 lines; 72 in the non-DB ones); core DB tests are Detroit on the database and mock the rest.

History: in the record I found, CI cost and flakiness drove the shape more than a written testing philosophy: quarantine (2020), selective checks (2020, under the ASF-wide GitHub Actions limit), the DB/non-DB split (2023, roughly 30 to 45% less CI time), then from 2025 a push toward providers without a DB plus new Playwright and deployed-image suites.

## 1. Posture and classification

**Written posture.** The testing index `contributing-docs/09_testing.rst` [1] lists the suites: unit, integration, Docker Compose, Kubernetes, Helm unit, system, Task SDK integration and Airflow Ctl integration. It adds one rule: "Note that in order for a pull request to be reviewed, **it should have a unit test**". The unit-test guide [2] says two things.

- For external systems it is mockist: "For standard unit tests that do not require integration with external systems, ensure all communications are simulated (mocked)."
- For the database it is pragmatic: "Generally, the fewer DB tests, the better." It also allows the opposite: "sometimes it is better to plug into the existing framework of DagRuns, Dags, Connections, and Variables to use the Database directly rather than mocking all DB access. This decision is up to you." On the preferred direction it says:

  > Generally speaking, it is better to have as many "pure" unit tests (requiring no DB) as possible compared to DB tests. They are usually faster and more reliable.

The most explicit statement of posture is on the dev list. It came up when browser tests were being added (Jarek Potiuk, 2025-09-24 [40]):

> We should have many, many more unit tests than e2e tests. This is the classic test pyramid case [...] The e2e tests are slow, brittle and difficult to maintain and we should have rather small number of those - mostly green path on all major functionalities.

The repository also has written rules for coding agents in `AGENTS.md` [17]:

- "Use `spec`/`autospec` when mocking."
- "Prefer `@mock.patch` decorators"
- "Use `@pytest.mark.db_test` for tests that require database access."
- "Target exactly 100% coverage of what the PR changes — no more, no less."

**How tests are classified.** Airflow classifies its tests on three axes.

1. *By suite (directory and distribution).* This is the axis this report counts:

```
airflow-core/tests/unit/            core unit tests, DB and non-DB ("Python tests that do not require any additional integrations")
airflow-core/tests/integration/     core integration tests (Celery, Kerberos, OpenTelemetry) behind --integration
airflow-core/tests/system/          example_empty.py, the one system test CI runs
providers/<p>/tests/unit/           provider unit tests, DB and non-DB, 109 providers
providers/<p>/tests/integration/    provider tests against docker-compose services ("without connecting to an external API on the internet")
providers/<p>/tests/system/         system tests = example DAGs against real external services ("serve both as examples and test files")
task-sdk/tests/                     Task SDK tests; a test marked db_test fails ("Task SDK tests must not use database")
airflow-ctl/tests/                  airflowctl tests; same guard ("Airflow CTL tests must not use database")
shared/<lib>/tests/                 tests of 14 shared internal libraries
chart/tests/helm_tests/             Helm unit tests: render the chart with `helm template`, assert on the YAML
kubernetes-tests/                   "tests that are run against real Kubernetes cluster" (KinD, the chart, the prod image)
docker-tests/                       prod/CI image tests and the docker-compose quick start
airflow-e2e-tests/                  "comprehensive tests that validate the entire Airflow system", real DAGs on the prod image
task-sdk-integration-tests/         Task SDK against "a running Airflow instance (mainly the execution API server)"
airflow-ctl-tests/                  airflowctl against "a full working Airflow environment" in Docker Compose
clients/python/test_python_client.py   generated Python API client against a running webserver
airflow-core/src/airflow/ui/src/**/*.test.ts(x)   Vitest + React Testing Library + msw
airflow-core/src/airflow/ui/tests/e2e/specs/      Playwright specs over a running Airflow
go-sdk/**/*_test.go, java-sdk/*/src/test, ts-sdk/tests   tests of the other-language task SDKs
dev/breeze/tests, scripts/tests, dev/registry/tests, devel-common/tests   tests of the repository tooling
devel-common/src/tests_common/      the shared pytest plugin and test utilities (helpers)
```

2. *By pytest marker.* The markers are registered in `devel-common/src/tests_common/pytest_plugin.py` [7], and Breeze runs pytest with `--strict-markers`. Usage counts are from the snapshot; the grep is in the appendix.

| marker | purpose (registration text) | uses (lines / files) |
|---|---|---|
| `db_test` | "mark tests that require database to be present" | 1,010 / 478 |
| `non_db_test_override` | override db_test for one test | 25 / 1 |
| `backend(name)` | "run with named backend"; also counts as DB | 73 / 29 |
| `integration(name)` | "run with named integration" | 36 / 34 |
| `system` | added automatically to everything under `tests/system` | 10 / 9 (explicit) |
| `quarantined` | "in quarantine (i.e. flaky, need to be isolated and fixed)" | 3 / 3 |
| `long_running` | "run for a long time (many minutes)" | 1 / 1 |
| `credential_file(name)` | needs a credential file | 1 / 1 |
| `need_serialized_dag` | needs serialized DAGs in the DB | 149 / 33 |
| `want_activate_assets`, `enable_redact`, `mock_plugin_manager`, `platform(name)`, `virtualenv_operator`, `external_python_operator` | environment switches | 4, 64, 8, 2, 2, 2 |
| `execution_timeout` | not registered by Airflow: provided by the `pytest-timeouts` plugin | 83 / 33 |
| `flaky(reruns=...)` | from `pytest-rerunfailures` | 16 / 8 |

3. *By CI job and test type.* `ci-amd.yml` [10] has separate jobs for each backend and group:
   - "Postgres tests: core/providers", "MySQL tests: ...", "Sqlite tests: ...", run with `--run-db-tests-only`.
   - "Non-DB tests: core/providers", run with `--skip-db-tests --backend none --use-xdist`.
   - "Low dep tests" and "Special tests": minimum and latest SQLAlchemy, latest boto, Pendulum 2, quarantined, system.
   - "Integration and System Tests", "Helm tests", "Kubernetes tests", "Task SDK tests", "Airflow CTL tests", "Additional PROD image tests" (the e2e suites), and the Go and Java SDK tests.

   Inside a job, core unit tests are cut into test types used for parallelism and selective runs. The types are `Always`, `API`, `CLI`, `Core`, `Serialization` and `Other`, and the folder mapping is in `dev/breeze/src/airflow_breeze/utils/run_tests.py`. The doc says this exists "to allow selectively running only a subset of test types for some PRs" and "to allow efficient parallel execution" [2].

| core test type | files | lines | tests (DB / non-DB) |
|---|---|---|---|
| Always | 8 | 2,512 | 19 / 111 |
| API | 126 | 65,184 | 2,310 / 363 |
| CLI | 32 | 11,884 | 445 / 111 |
| Core | 110 | 67,670 | 2,133 / 586 |
| Serialization | 15 | 10,458 | 33 / 417 |
| Other | 59 | 26,339 | 662 / 483 |

**Where the docs, the tooling and the tree disagree:**

- The unit-test doc still lists test types `Operators`, `WWW` and `Providers` [2]. Breeze defines `Always, API, CLI, Core, Serialization, Other`, and `WWW` disappeared with the old UI in 2025.
- The integration doc says the tests "are all stored in the `tests/integration` folder" [3]. They live in `airflow-core/tests/integration` and `providers/*/tests/integration`.
- The index `09_testing.rst` does not link the Airflow E2E suite or the Playwright suite, though both have their own docs and CI jobs.
- The index describes integration tests as needing "Postgres, MySQL, Kerberos, etc." In the code, Postgres and MySQL are backends (`--backend`), not integrations (`--integration`).
- The quarantine doc says quarantined tests are "run in isolation and re-run several times". The tree barely uses the mechanism: three quarantine marks remain (section 11), and the CI job runs them once with failures ignored (section 8).

## 2. What the names mean

| Airflow's name | what the tests actually touch | nearest post category | fit |
|---|---|---|---|
| unit test, DB (`@pytest.mark.db_test`) | one process; real SQLite/PostgreSQL/MySQL through the ORM; FastAPI app in process via `TestClient`; external services mocked | none exact; between `fast` and `adapters_free` | Airflow calls these "unit". They are sociable in-process tests on a real database, and they are the proof for models, scheduler and REST API, not an extra copy. |
| unit test, non-DB | one process; DB unusable by construction (connection string set to `bad_schema:///`); SDK clients mocked, AWS often faked with `moto` | `unit` | The post's `unit` means pure functions. Airflow's non-DB tests are mostly solitary tests of hooks and operators with mocked clients. |
| Task SDK tests | one process; DB forbidden; supervisor comms and API client mocked | `unit` | good |
| airflow-ctl tests | one process; `httpx.MockTransport` as the server | `unit` / `fast` | good |
| integration tests | pytest in Breeze plus one or more docker-compose services (Redis, Celery, Kerberos, Trino, MongoDB, Kafka, Pinot and others; 20 compose files) | `adapters_free` | Good. A few core ones exercise the Celery executor rather than one adapter. |
| system tests | an example DAG run by pytest (`get_test_run(dag)`) against real cloud or SaaS services, with credentials | `adapters_metered` | Also the documentation source. CI runs only `example_empty.py`; provider stewards run the rest on their own infrastructure. |
| Helm unit tests | `helm template` subprocess, assertions on the rendered YAML; no cluster | none | Called "unit", but they drive a real external binary. |
| Kubernetes tests | KinD cluster, the Helm chart, the prod image; REST API and `kubectl` | `api` (no browser) | A deployment test. |
| Docker image / compose tests | built prod image, `docker compose` quick start, one DAG triggered over REST | none / `api` | packaging |
| Airflow E2E tests | prod image in Docker Compose (scheduler, api-server, triggerer, DB) via testcontainers; DAGs triggered over REST | `api` | Called "E2E", but there is no browser. |
| Task SDK integration tests | Airflow in Docker Compose; SDK client over HTTP | `api` | Mainly a contract test between two separately released packages. |
| airflow-ctl integration tests | `airflowctl` commands against Airflow in Docker Compose | `api` | good |
| Python API client test | generated client against a webserver | `api` | good |
| UI e2e tests | Chromium, Firefox, WebKit against a running Airflow started by Breeze; setup through the REST API, no network mocking | `e2e` | Good. Page objects hold most of the code. |
| UI unit tests (Vitest) | Node + happy-dom, React Testing Library, a global `msw` fake server | `fast` (front end) | The UI README calls the multi-component ones "Vitest integration test (using React Testing Library)" [6]. |
| Go / Java / TypeScript SDK tests | the SDK library in process | `unit` | Library tests. |
| tooling tests | Breeze, CI scripts, registry generator | `tooling` | Left out of the whole, as in the Robinauts chart. |

## 3. Categories outside the post's taxonomy

1. **DB unit tests.** In-process tests that need a real database. They prove that queries, the schema and the scheduling logic work on every supported database: "It is crucial to run these tests against all real databases that Airflow supports to check if SQLAlchemy queries and the database schema are correct" [2]. They exist because Airflow's core is a state machine stored in a relational DB. Size: 215,657 lines, 27.2% of the whole, 8,534 tests. They are 73% of core test definitions but 14% of provider ones.
2. **System tests that are also the examples and the docs.** The doc gives their purpose as to "serve both as examples and test files" and says "the excerpts from these system tests are used to generate documentation" [4]. Size: 519 files, 52,518 lines, 520 tests in 78 provider folders and core. They are metered (paid cloud). CI runs one; Amazon, Google, Teradata and an LLM-provider group publish external dashboards [44].
3. **Helm template tests.** They render the chart for many value sets and check the output. Airflow ships a Helm chart, and the doc says "we have decided to stick with pythonic testing for our Helm chart" [5]. Size: 76 files, 24,389 lines, 1,289 tests.
4. **Packaging tests.** These cover the prod and CI images, the docker-compose quick start, the Kustomize overlays, and provider distributions installed from wheels. Size: 451 lines in `docker-tests`; the distribution checks live in CI workflows rather than test files.
5. **Matrix modes that re-run the same tests.** Provider tests run against older Airflow releases ("Compatibility Provider unit tests against older Airflow releases"). There are "lowest direct dependency resolution" runs, minimum and latest SQLAlchemy, latest boto and Pendulum 2 [2][10]. They prove compatibility of independently released packages and add no lines.
6. **Contract tests between distributions.** Task SDK integration and airflow-ctl integration tests check "the interface contract" between packages released on different schedules [5]. Size: 1,205 lines. They fit `api` by mechanism but `tooling`-like compatibility by purpose.
7. **Repository-structure tests that enforce test policy.** `test_project_structure.py` fails if a provider module has no test file. The known exceptions are listed (65 files), and a stale exception also fails. For six providers (Google, Amazon, Elasticsearch, CNCF Kubernetes, Slack, Docker) it also fails if an operator lacks an example DAG [14]. Counted as tooling.
8. **Other-language SDK tests.** Go, Kotlin and TypeScript task SDKs with their own tests: 32,369 lines, 4.1%.

## 4. Lines per category

Code lines are total lines minus blank and full-line comment lines, counted per file with the tool. Helpers are excluded and tooling is out of the whole.

| category | lines | pct of whole | pct without system tests | files | tests |
|---|---|---|---|---|---|
| Unit, DB (core) | 146,198 | 18.5 | 19.8 | 210 | 5,602 |
| Unit, DB (providers) | 69,460 | 8.8 | 9.4 | 158 | 2,932 |
| Unit, non-DB (core) | 37,849 | 4.8 | 5.1 | 140 | 2,071 |
| Unit, non-DB (providers) | 340,952 | 43.1 | 46.1 | 1,205 | 18,389 |
| Task SDK tests | 39,888 | 5.0 | 5.4 | 88 | 2,288 |
| airflow-ctl tests | 6,585 | 0.8 | 0.9 | 13 | 317 |
| Shared library tests | 7,255 | 0.9 | 1.0 | 24 | 428 |
| Integration tests | 2,860 | 0.4 | 0.4 | 33 | 85 |
| System tests (example DAGs) | 52,518 | 6.6 | — | 519 | 520 |
| Helm unit tests | 24,389 | 3.1 | 3.3 | 76 | 1,289 |
| Kubernetes tests | 1,876 | 0.2 | 0.3 | 5 | 57 |
| Docker image / compose tests | 451 | 0.1 | 0.1 | 4 | 17 |
| Airflow E2E tests | 2,158 | 0.3 | 0.3 | 19 | 96 |
| Task SDK integration tests | 866 | 0.1 | 0.1 | 8 | 39 |
| airflow-ctl integration tests | 339 | <0.1 | <0.1 | 3 | 17 |
| Python API client test | 82 | <0.1 | <0.1 | 1 | 1 |
| UI e2e (Playwright, TypeScript) | 1,364 | 0.2 | 0.2 | 26 | 105 |
| UI unit/component (Vitest, TypeScript) | 24,497 | 3.1 | 3.3 | 230 | 1,403 |
| Go SDK tests | 15,608 | 2.0 | 2.1 | 47 | 539 |
| Java SDK tests (Kotlin) | 8,461 | 1.1 | 1.1 | 30 | 409 |
| TypeScript SDK tests | 8,300 | 1.0 | 1.1 | 30 | 624 |
| **Whole** | **791,956** | 100 | (739,438) | 2,869 | 37,228 |

Notes on what the table includes:

- **System tests.** They are included in the whole because they are Airflow's own test category (AIP-47). Without them the whole is 739,438 lines; that is the second percentage column.
- **DB and non-DB lines.** 152 files mix DB and non-DB tests (26 core, 126 providers). Their lines were split by the line spans of DB-marked and unmarked tests (appendix). The file counts put each mixed file in its majority side.
- **Languages.** Everything is Python except the UI rows (TypeScript, plus 17 lines of JavaScript), Go, Kotlin and the TypeScript SDK.

The same numbers collapsed onto the post's taxonomy:

| post category | Airflow rows | lines | pct |
|---|---|---|---|
| e2e (browser) | UI e2e | 1,364 | 0.2 |
| api (real server, no browser) | Airflow E2E, Kubernetes, Docker, Task SDK integration, airflow-ctl integration, client | 5,772 | 0.7 |
| adapters_free | integration | 2,860 | 0.4 |
| adapters_metered | system tests (example DAGs) | 52,518 | 6.6 |
| no slot: in-process on a real DB | unit, DB | 215,657 | 27.2 |
| unit (Python, no DB) | unit non-DB, Task SDK, airflow-ctl, shared | 432,530 | 54.6 |
| fast/unit, front end | Vitest | 24,497 | 3.1 |
| unit, other-language SDKs | Go, Kotlin, TypeScript | 32,369 | 4.1 |
| no slot: Helm templates | Helm | 24,389 | 3.1 |

**Left out of the whole:**

- Shared helpers: 1,718 files, 27,312 lines. The largest parts are `devel-common/src/tests_common` at 7,772 lines, Playwright page objects and fixtures at 3,827, provider test helpers and package files at 3,443, system-test helpers at 3,097, core fixtures and test DAGs at 2,491, and the Airflow E2E harness at 1,946.
- Tooling tests: 164 files, 33,974 lines, 2,029 tests. Breeze has 15,261 lines and CI scripts 13,027.
- Example DAGs shipped in `src`: 143 files, 10,661 lines. Every one is imported by `test_example_dags.py`, and the e2e suites run some of them, but they are not tests. SDK examples: 25 files, 1,853 lines.
- Test data files: 222 files of JSON, YAML, XML, CSV, SQL and similar, 51,433 lines, about 2.0 MB. Eight more `.sql` files (168 code lines) sit in test folders and were excluded as data.

**Trend.** Test definitions in core and provider unit tests, using the same AST rules at three commits (appendix):

| snapshot | core unit tests (DB share) | provider unit tests (DB share) | all (DB share) |
|---|---|---|---|
| 2023-10-31, merge of the DB split (a7e76baf60) | 3,820 (73%) | 7,354 (26%) | 11,174 (42%) |
| 2025-06-22, before the provider cleanup (14b00ed5e2) | 2,935 (71%) | 11,279 (29%) | 14,214 (37%) |
| 2026-10-11, this snapshot | 7,621 (73%) | 21,321 (14%) | 28,942 (29%) |

The core dip in 2025 matches Airflow 3 removing the old webserver and connexion API and moving core operators to the `standard` provider (inference from the tree contents at both commits). Code lines in provider unit tests went from 150,342 (2023) to 242,690 (2025) to 410,412 (2026). Most of the suite is younger than three years.

## 5. Test-to-code ratio

Production code is source under `*/src/` plus the SDKs. Excluded:

- migrations: 167 files, 12,012 lines
- generated code: generated `get_provider_info.py` (11,809 lines), datamodel-codegen output, Go `*.gen.go`, the TS SDK `generated/`, and the UI `openapi-gen` clients (32,007 lines)
- vendored code: 64 lines
- example DAGs
- docs, build config, and the `dev/`, `scripts/`, `registry/` and `performance/` tooling

| tests | production counterpart | test lines | prod lines | ratio |
|---|---|---|---|---|
| core unit (DB + non-DB) | `airflow-core/src/airflow` Python | 184,047 | 99,268 | 1.85 |
| of which DB unit | same | 146,198 | 99,268 | 1.47 |
| core `API` test type | `api_fastapi/` + `api/` Python | 65,184 | 32,496 | 2.01 |
| provider unit | `providers/*/src` | 410,412 | 318,688 | 1.29 |
| provider unit + integration + system | `providers/*/src` | 465,383 | 318,688 | 1.46 |
| Task SDK tests | `task-sdk/src` | 39,888 | 31,182 | 1.28 |
| airflow-ctl tests | `airflow-ctl/src` | 6,585 | 4,242 | 1.55 |
| shared library tests | `shared/*/src` | 7,255 | 7,346 | 0.99 |
| Vitest (core UI only) | `airflow-core/src/airflow/ui/src` | 24,328 | 50,855 | 0.48 |
| Playwright specs | same UI | 1,364 | 50,855 | 0.03 (0.10 with page objects) |
| Helm unit tests | `chart/templates` (YAML; see appendix) | 24,389 | 8,863 | 2.75 |
| Go / Kotlin / TS SDK tests | each SDK's source | 15,608 / 8,461 / 8,300 | 8,438 / 5,220 / 4,715 | 1.85 / 1.62 / 1.76 |
| all real-server and browser suites | whole product (spans everything) | 7,136 | 534,547 | 0.013 |
| all Python test rows | all Python production | 733,726 | 460,726 | 1.59 |
| whole | whole production | 791,956 | 534,547 | 1.48 |

Integration tests (407 core lines, 2,453 provider lines) span hooks and executors. They are reported only inside the provider combination above. The real-server and browser suites exercise the whole product and are reported against the whole production tree.

## 6. Detroit or London

**Heuristic.** It was applied per test file with Python regexes run by my own script from outside the clone; the exact patterns are in the appendix.

- A file "uses a mocking facility" if it matches any of these: `from unittest import ... mock`, `from unittest.mock import`, `import unittest.mock`, `import mock`, `from pytest_mock import`, the identifiers `mocker`, `monkeypatch`, `requests_mock` or `MockTransport`, or `from moto import`.
- Mock call sites are matches of these: `mock.patch(` and its `.object`, `.dict`, `.multiple` forms, a bare `patch(`, `MagicMock(`, `AsyncMock(`, `PropertyMock(`, `Mock(`, `create_autospec(`, `mocker.<attr>`, `monkeypatch.<attr>`, `@mock_aws`, `requests_mock.<attr>` and `MockTransport(`.
- TypeScript: `vi.mock|fn|spyOn|stubGlobal|mocked|doMock|stubEnv`, imports from `msw`, `jest.mock|fn|spyOn`, `page.route(` and `sinon`. Call sites also include `server.use(` and `http.get|post|put|patch|delete(`.
- Go and Kotlin use rough equivalents (testify mock, gomock, fakes; mockk, Mockito).
- "DB-marked" means the file contains `pytest.mark.db_test` or `pytest.mark.backend`. "DB session use" matches `create_session`, `provide_session`, `dag_maker`, `clear_db_*`, `settings.Session`, `testing_dag_bundle` or `session.add|query|execute|scalar|scalars|merge|commit|flush|get|delete(`.

| category (files) | files using a mocking facility | mock calls per 1,000 lines | real dependencies | placement |
|---|---|---|---|---|
| Unit, DB, core, DB-only files (201) | 62.7% | 16.9 | real DB in every test. Of all 350 core unit files, 53% use DB-session APIs and 83 match the in-process client patterns (`TestClient`, `test_client`, `client.get(` and similar) | Detroit on the DB, London at the edges |
| Unit, DB, providers, DB-only files (123) | 69.1% | 49.5 | real DB (often only to create Connections, per the 2025 cleanup thread [39]) | mixed |
| mixed DB/non-DB files (26 core / 126 providers) | 96.2% / 95.2% | 30.9 / 69.9 | some tests on a real DB | mixed |
| Unit, non-DB, core (123) | 46.3% | 27.6 | none | London-leaning |
| Unit, non-DB, providers (1,114) | 82.1% | 72.1 | none. `moto` in-memory AWS fakes in 69 files; the Mongo provider starts a real MongoDB with testcontainers | London |
| Task SDK (88) | 69.3% | 33.6 | none (DB forbidden) | London-leaning |
| airflow-ctl (13) | 100% | 53.2 | fake HTTP transport | London |
| shared libraries (24) | 58.3% | 16.0 | none | mixed |
| integration (33) | 51.5% | 24.5 | all 33 marked `integration(...)`: a docker-compose service | Detroit for the service under test; the far side of transfers (GCS, Hive) and some Celery internals are mocked |
| system (519) | 0.2% | 0.1 | real cloud services | Detroit |
| Helm (76) | 2.6% | 0.0 | real `helm` binary | Detroit |
| Kubernetes (5) | 40% | 24.5 | real KinD cluster | Detroit |
| Docker (4) | 25% | 4.4 | real images, compose | Detroit |
| Airflow E2E (19), Task SDK integration (8), airflow-ctl integration (3) | 0% / 12.5% / 33% | 0 / 1.2 / 56.0 | full stack in Docker Compose | Detroit |
| UI Vitest (230) | 63.9% explicit; 100% run under a global `msw` server | 41.6 | none; 181 of 230 files render components | London-leaning (fakes) |
| UI Playwright (26) | 0% | 0 | real browser, server, DB; no `page.route` mocking | Detroit |
| Go / Kotlin / TS SDK | 8.5% / 6.7% / 53.3% | 2.9 / 1.4 / 6.1 | none | mostly classical library tests |

**Reading.** The center of mass is London. 43% of all test lines are provider non-DB tests, and four out of five of those files patch or mock. The written rule supports this: external communication in unit tests should be "simulated (mocked)" [2]. The core is different. Its DB tests run the real scheduler, models and API against a real database, and that is why Airflow runs them on three database engines. The project argues about where the line should be:

> We have to be aware of making our tests overly fragile if we replace everything with mocks, then we are only testing our mocks and not the real behaviour.
> — Ash Berlin-Taylor, 2025-02-07 [34]

> I think it's not about "slow" - it's about using ORM SQLalchemy objects and effectively requiring the DB. As outlined before - I want all our Provider tests to be non-DB tests. Soon. they will not even have DB to talk to.
> — Jarek Potiuk, 2025-02-07 [34]

The direction since 2025 is away from the real DB for providers. Jarek Potiuk did not argue that the replacement is a mock. He argued that it is what production does: "requiring providers to use Task SDK's equivalent of Connection in this case. Which will be 100% what Providers will be doing in "production" for Airflow 3" [34].

The cost of mocks by module path showed up in October 2026. Shahar Epstein, PR #74123, 2026-10-03 [63]:

> cncf.kubernetes tests reload airflow.executors.executor_loader and leave its state behind, so a test that mocks ExecutorLoader through the module path can pass in its PR and fail on every canary build and release-candidate check afterwards.

## 7. The web UI

The Airflow 3 UI (`airflow-core/src/airflow/ui`, React and TypeScript) has two layers.

- **Vitest component and unit tests.** There are 230 files with 24,497 lines and 1,403 tests: 225 in the core UI, 1 in the simple-auth login UI and 4 in provider UI plugins.
  - They run in Node with `happy-dom`.
  - `testsSetup.ts` starts a global `msw` server with fake API handlers for every test. It also mocks the graph layout and Chart.js modules [6].
  - 181 of the 230 files render components with React Testing Library. 9 override the fake API per test.
  - They run in "Basic tests" (`pnpm test`) whenever selective checks see UI files change.
- **Playwright end-to-end tests over a real backend.** There are 26 spec files with 1,364 lines and 105 tests, plus 47 page-object, fixture and API-helper files with 3,827 lines.
  - `breeze testing ui-e2e-tests` starts Airflow with Docker Compose from the prod image, and specs create their data through the REST API.
  - CI runs Chromium, Firefox and WebKit as three jobs ("Additional PROD image tests"). They run on pull requests that change UI files, or when the `full tests needed` label is set (`run_ui_e2e_tests` in `selective_checks.py` [12]).
  - In CI, Playwright retries a failing test up to 4 times and uses 2 workers. A daily workflow analyses e2e flakiness and posts to Slack (#64446, 2026-03-30 [64]).

**Which layer is the proof.** The written rule makes Vitest the proof and Playwright the exception. From `tests/e2e/README.md` [6]:

> **Write an E2E test only when** the behavior requires a real browser and a running Airflow backend — for example, full authentication flows, cross-page navigation state, or interactions that depend on live scheduler/API behavior.

The latest commit in that area moved checks from Playwright down to Vitest. Brent Bovenzi, #74367, 2026-10-08 [65]:

> Covering those in Vitest and asserting each page's details in a single page load keeps the Playwright suite focused on flows that need a real Airflow backend, so the e2e jobs finish sooner and spend less time exposed to runner instability.

**History.**

- The new UI started on 2024-08-30 with Vitest from its first commit (#41846, Brent Bovenzi [55]).
- There was no browser test of any kind before November 2025. I searched commit messages for Selenium, Cypress and Playwright and found nothing earlier.
- The trigger was a dev-list thread. Rahul Vats wrote on 2025-09-23 that "the UI has undergone a complete revamp, and new changes are naturally more prone to regressions" [40]. Vincent Beck answered with the dependency-upgrade case: "Today we have no way of knowing whether these PRs break the UI, in order to merge these PRs we need to compile the front-end assets and test manually whether the UI work." [40]
- The Playwright framework landed on 2025-11-28 (#58548) and its CI workflow on 2025-12-10 (#58901), both by Rahul Vats [56][57].

Counts at points in time, from the history clone:

| date | Vitest files (core UI) | Playwright spec files |
|---|---|---|
| 2024-12-31 | 8 | 0 |
| 2025-09-23 (thread opened) | 14 | 0 |
| 2025-12-31 | 16 | 3 |
| 2026-03-31 | 27 | 22 |
| 2026-06-30 | 76 | 24 |
| 2026-10-11 | 225 | 26 |

## 8. Enforcement by machine

| mechanism | what it checks | where | added |
|---|---|---|---|
| Non-DB run with a broken DB | `--skip-db-tests` sets the SQLAlchemy URL to `bad_schema:///`. `SkipDBTestsSession` raises "Your test accessed the DB but `_AIRFLOW_SKIP_DB_TESTS` is set. Either make sure your test does not use database or mark the test with `@pytest.mark.db_test`" | `devel-common/src/tests_common/pytest_plugin.py`; `airflow-core/src/airflow/settings.py` [7][8] | #35264 and #35160, 2023-10-30/31, Jarek Potiuk [37] |
| DB/non-DB deselection at collection | DB tests never reach xdist workers in non-DB runs (cause: out-of-memory on Python 3.14) | `pytest_collection_modifyitems` in the plugin | #63791, 2026-03-19, Dev-iL [66] |
| Task SDK and airflow-ctl refuse DB tests | `pytest.fail("Task SDK tests must not use database")`, same for CTL | `task-sdk/tests/conftest.py`, `airflow-ctl/tests/conftest.py` [19] | #43181 (2024-10-21, Kaxil Naik), #44690 (2024-12-06), #48099 (2025-03-31) [52] |
| Ratchet against new DB tests in providers | prek hook `check-pytest-mark-db-test-in-providers` fails on `pytest.mark.db_test` in 50 listed providers | `providers/.pre-commit-config.yaml` [13] | #52017 and #52021, 2025-06-22, Jarek Potiuk [53] |
| No `unittest.TestCase` | prek hook fails on classes inheriting `TestCase` | `airflow-core/.pre-commit-config.yaml`, `scripts/ci/prek/unittest_testcase.py` | #30775, 2023-05-02, Vincent Beck [49] |
| Tests in known folders | prek hook against a list of allowed test folders | `scripts/ci/prek/check_tests_in_right_folders.py` | #38520, 2024-03-27 |
| Every provider module has a test file | `test_providers_modules_should_have_tests`; 65 listed exceptions; a stale exception fails | `airflow-core/tests/unit/always/test_project_structure.py` [14] | #7346, 2020-02-03, Kamil Breguła [46] |
| Operators have example DAGs (system tests) | `ExampleCoverageTest` per provider; prek `check-system-tests-present` | same file; `.pre-commit-config.yaml` | #7404 (2020-02-13), #23351 (2022-05-08) |
| No test-only imports in production | prek `check-test-only-imports-in-src` | `scripts/ci/prek/check_test_only_imports_in_src.py` | #61713, 2026-02-10, Shahar Epstein |
| Forbidden warnings | an uncaught `AirflowProviderDeprecationWarning` fails the test | `pyproject.toml` `forbidden_warnings`; plugin | in a plugin since at least #39411 (2024-05-10) |
| Strict markers, timeouts, fail-fast | `--strict-markers`, per-test setup/execution/teardown timeouts (pytest-timeouts), `--maxfail=50` | `dev/breeze/src/airflow_breeze/utils/run_tests.py` | not dated |
| Quarantine | `quarantined` tests skipped in normal runs, run in a separate job whose failure is ignored (the script appends `\|\| true` with the comment "Do not remove") | `special-tests.yml`, `scripts/ci/testing/run_unit_tests.sh` [11] | #8511, 2020-04-23, Jarek Potiuk [47] |
| Retries for flaky layers | integration jobs retried once after a Docker restart; Playwright `retries: 4` in CI; 16 `flaky(reruns=...)` marks | `run_integration_tests_with_retry.sh`; `playwright.config.ts` | — |
| Selective checks | the changed files decide which test types, versions and suites run | `selective_checks.py` (2,537 lines) with a 4,423-line test file | #11417, 2020-10-12 [48] |
| Labels that widen the run | `full tests needed`, `all versions`, `canary`, `area:e2e-tests`, `area:kubernetes-tests`, `upgrade to newer dependencies`, among others | same file | `full tests needed`: #11828, 2020-10-29 [50] |
| Process-global side effects | providers known to leak state are added to the PR run in canary order | `selective_checks.py` | #74123, 2026-10-03 [63] |
| Monitoring, not gating | daily e2e flakiness report; CI duration trend alert to Slack | `e2e-flaky-tests-report.yml`, `ci-duration-monitor.yml` | #64446 (2026-03-30), #68368 (2026-06-14) |

**What does not gate.** No CI status is a required check on `main`. `.asf.yaml` requires one approving review, linear history and resolved conversations [16]. A required status check ("Finalize tests") was enabled for an auto-merge experiment on 2025-04-26 and removed. The experiment itself was removed on 2025-04-30 (#49746, #50009). Jarek Potiuk explained the drawback [38]:

> We currently cannot override the protection from GitHub UI, and it's not possible to merge PR that did not pass one of the checks

Elad Kalif replied: "I find the lack of ability to merge PRs fast very limiting but it might be just something to get used to." [38] Merging on green CI is therefore a committer norm, not a machine rule (inference from `.asf.yaml` and the thread; rulesets configured outside `.asf.yaml` are not visible from the repository). Coverage gates nothing (section 12).

A detail of the quarantine machinery is that `run_ci_tests.sh` updates the quarantine issue only when `TEST_TYPE == "Quarantined"`. Breeze now passes `All-Quarantined`, so that branch looks dormant. This is an inference from the code; I did not see a CI run.

## 9. History

**Before 2020: one suite on a real database.** In 2016 Airflow already ran its tests on SQLite with the SequentialExecutor. Siddharth Anand noted on 2016-05-04 that "we rely on the SequentialExecutor and one the SQLite DB for our tests" [20]. Flaky builds were already a topic. Vijay Bhat traced "random Travis failures" to "a subtle race condition in the backfill execution loop that creates deadlocks every now and then" (2016-10-21 [21]). In that case, a flaky test that used real collaborators exposed a real product bug (inference).

Two things followed by the end of 2019:

- In 2018 Jarek Potiuk proposed AIP-4: run Google Cloud system tests, built from example DAGs, in Cloud Build [41].
- In 2019 Tomasz Urbaszek's AIP-27 replaced nose with pytest. Merged as #6472 on 2019-12-05, with the new `TESTING.rst` [22][23][42].

**2020: CI as an emergency.** In April 2020 the team made "an emergency migration to Github Actions" from Travis. Jarek Potiuk found that flakiness was partly theirs: "while we were blaming Travis for everything wrong that happened in our builds, it was not always Travis' fault" [25]. He proposed and merged the quarantine mechanism (#8511, 2020-04-23). In the same year:

- Integrations were split out behind markers in January (#7091).
- The Kubernetes tests moved to the Helm chart and the prod image in July (#9468).
- Helm chart tests were rewritten from helm-unittest to Python in October (#11693, #11827).

In October 2020 GitHub Actions' concurrency limit, shared across all ASF projects, caused delays of over three hours. Airflow answered with two changes:

- **Selective tests**, planned since August as issue #10507 and merged on 2020-10-12 (#11417).
- **Unapproved PRs run only the default matrix.** Merged on 2020-10-29 (#11828), with a `full tests needed` label for core changes [28][29].

**2021 to 2023: consolidation.** Coverage upload was switched off for PRs in November 2021 (#19523). AIP-47 (2022) turned system tests into self-contained example DAGs runnable by pytest; the old ones were "not integrated into the CI process and rarely being executed" [43]. The `unittest.TestCase` classes were removed in waves:

| date | test files with `TestCase` classes |
|---|---|
| June 2021 | 560 of 787 |
| June 2022 | 586 of 931 |
| December 2022 | 80 of 954 |
| October 2023 | 0 |

Andrey Anshin drove most of the waves (#26831 to #28378). A hook has banned `TestCase` since May 2023 (#30775).

The biggest structural turn came on 2023-10-31: the DB/non-DB split. Its motivation was CI time and parallelism. Non-DB tests could run once with pytest-xdist instead of on every database. Jarek Potiuk reported 30 to 45% less build time (section 11) [32][33].

**2024 to 2026: a monorepo of distributions, and the outer layers.**

- Testing docs moved to `contributing-docs/testing/` (#36969, 2024-01-26).
- Task SDK tests became DB-free (#43181, 2024-10-21).
- The repository split into provider sub-projects (announced 2025-02-09 [35]), a `devel-common` test package (#47281, 2025-03-05), `task-sdk` (#47451) and `airflow-core` (#47798, 2025-03-21 [37]). Ash Berlin-Taylor proposed the `tests/unit` name on 2025-02-15 [36].
- In June 2025 a crowd-sourced cleanup removed `db_test` marks from providers, locked in by a ratchet hook [39].
- Out-of-process suites appeared one after another:
  - Task SDK integration tests (2025-07-25, Amogh Desai: "We have experienced regressions in recent release candidates and patch releases that could have been caught with proper integration testing between Airflow core and the Task SDK." [58])
  - Airflow E2E tests on the prod image (2025-09-11)
  - airflow-ctl integration tests (2025-10-20)
  - Playwright UI e2e tests (2025-11-28)

**Did the steers succeed?**

| steer | outcome |
|---|---|
| Quarantine | Partly. The marked population shrank (section 11), but flaky handling moved to reruns and job-level retries, and the issue-tracking branch looks dormant. |
| Selective checks | Yes. They are still the core of CI, now with their own 4,423-line test file. |
| DB/non-DB split | Yes for CI time and for providers: DB share of provider tests 26% to 14%. No for core, which stays near 73% DB. |
| System tests (AIP-47) | Yes as examples and documentation: 518 example-DAG tests. Only partly as CI tests. The 2022 hope to run them "likely daily" against real services on donated cloud credits (Jarek Potiuk [30]) ended up as external dashboards run by provider companies [44]; Airflow's own CI runs one. |
| Browser coverage of the UI | Started in late 2025. The latest move pushes checks back down to Vitest. |

## 10. Timeline

| date | what changed | who drove it | link |
|---|---|---|---|
| 2016-05-30 | `.codecov.yml` added, PR comments disabled | Bolke de Bruin | [commit 7678492269](https://github.com/apache/airflow/commit/7678492269) |
| 2018-08-25 | Codecov wired into the Docker CI build (replacing coveralls) | Fokko Driesprong | [#3780](https://github.com/apache/airflow/pull/3780) |
| 2018-09 | AIP-4, automation of system tests (GCP, Cloud Build) | Jarek Potiuk | [AIP-4](https://cwiki.apache.org/confluence/spaces/AIRFLOW/pages/93324355/AIP-4+Automation+of+System+Tests+Deps+AIP-47) |
| 2019-12-05 | pytest replaces nose (AIP-27); `TESTING.rst` created 2019-12-04 | Tomasz Urbaszek; Jarek Potiuk | [#6472](https://github.com/apache/airflow/pull/6472), [#6585](https://github.com/apache/airflow/pull/6585) |
| 2020-01-13 | integrations separated; `integration`/`backend` markers | Jarek Potiuk | [#7091](https://github.com/apache/airflow/pull/7091) |
| 2020-02-03 | test fails if a provider module has no test | Kamil Breguła | [#7346](https://github.com/apache/airflow/pull/7346) |
| 2020-04-23 | quarantine marker and non-blocking Quarantined job, after the Travis to GitHub Actions move | Jarek Potiuk | [#8511](https://github.com/apache/airflow/pull/8511) |
| 2020-07-01 | Kubernetes tests deploy via the Helm chart and prod image | Jarek Potiuk | [#9468](https://github.com/apache/airflow/pull/9468) |
| 2020-08-03 | quarantine status tracked in issue #10118 | Jarek Potiuk | [#10119](https://github.com/apache/airflow/pull/10119) |
| 2020-08-07 | coverage becomes an informational status | Jarek Potiuk | [#10208](https://github.com/apache/airflow/pull/10208) |
| 2020-10-12 | selective tests by changed files; test types split | Jarek Potiuk | [#11417](https://github.com/apache/airflow/pull/11417), [#11402](https://github.com/apache/airflow/pull/11402) |
| 2020-10-13 | ASF-wide 180-job GitHub Actions limit raised with Infra | Jarek Potiuk | [builds@ thread](https://lists.apache.org/thread/fxy5orhk8yp0mt0zbrs3r53234w9khl4) |
| 2020-10-29 | unapproved PRs run a subset; `full tests needed` label | Jarek Potiuk, Tobiasz Kędzierski | [#11828](https://github.com/apache/airflow/pull/11828) |
| 2020-10-27/30 | Helm chart tests move to Python | Daniel Imberman; Kamil Breguła | [#11693](https://github.com/apache/airflow/pull/11693), [#11827](https://github.com/apache/airflow/pull/11827) |
| 2021-11-10 | coverage disabled for PRs (memory) | Jarek Potiuk | [#19523](https://github.com/apache/airflow/pull/19523) |
| 2021-11-24 | Docker image tests in Python | Kamil Breguła | [#19737](https://github.com/apache/airflow/pull/19737) |
| 2022-02-24 / 03-25 | AIP-47 accepted; new system-test design merged | Mateusz Nojek, Bartłomiej Hirsz, Eugene Kostieiev | [AIP-47](https://cwiki.apache.org/confluence/display/AIRFLOW/AIP-47+New+design+of+Airflow+System+Tests), [#22311](https://github.com/apache/airflow/pull/22311) |
| 2022-10-10 to 2023-01-06 | `unittest` classes converted to pytest in waves | Andrey Anshin | [#26831](https://github.com/apache/airflow/pull/26831), [#28378](https://github.com/apache/airflow/pull/28378) |
| 2023-01-11 | stable tests released from quarantine | Andrey Anshin | [#28767](https://github.com/apache/airflow/pull/28767) |
| 2023-03-30 | new service providers expected to bring system tests and a dashboard | Jarek Potiuk | [dev@ thread](https://lists.apache.org/thread/xf4wn1hw08cs725fp962252y7mmptk3b) |
| 2023-05-02 | prek hook bans `unittest.TestCase` | Vincent Beck | [#30775](https://github.com/apache/airflow/pull/30775) |
| 2023-10-31 | DB / non-DB split of unit tests | Jarek Potiuk | [#35264](https://github.com/apache/airflow/pull/35264), [#35160](https://github.com/apache/airflow/pull/35160) |
| 2024-01-26 | testing docs move to `contributing-docs/testing/` | Jarek Potiuk | [#36969](https://github.com/apache/airflow/pull/36969) |
| 2024-08-30 | new React UI with Vitest | Brent Bovenzi | [#41846](https://github.com/apache/airflow/pull/41846) |
| 2024-10-21 | Task SDK tests run without a DB | Kaxil Naik | [#43181](https://github.com/apache/airflow/pull/43181) |
| 2025-02-09 to 03-21 | providers, `devel-common`, `task-sdk`, `airflow-core` become separate distributions | Jarek Potiuk and many contributors | [#47281](https://github.com/apache/airflow/pull/47281), [#47798](https://github.com/apache/airflow/pull/47798) |
| 2025-04-26 to 04-30 | required status check tried for auto-merge, then removed | Jarek Potiuk; Kaxil Naik | [#49746](https://github.com/apache/airflow/pull/49746), [#50009](https://github.com/apache/airflow/pull/50009) |
| 2025-06-22 | DB-free connection fixture; ratchet hook; provider cleanup | Amogh Desai; Jarek Potiuk | [#51930](https://github.com/apache/airflow/pull/51930), [#52017](https://github.com/apache/airflow/pull/52017), [#52020](https://github.com/apache/airflow/issues/52020) |
| 2025-07-25 | Task SDK integration tests | Amogh Desai | [#53332](https://github.com/apache/airflow/pull/53332) |
| 2025-09-11 | Airflow E2E tests on the prod image (testcontainers) | GPK (commit author name) | [#54072](https://github.com/apache/airflow/pull/54072) |
| 2025-10-20 | airflow-ctl integration tests | Bugra Ozturk | [#56124](https://github.com/apache/airflow/pull/56124) |
| 2025-11-28 / 12-10 | Playwright UI e2e framework and CI workflow | Rahul Vats | [#58548](https://github.com/apache/airflow/pull/58548), [#58901](https://github.com/apache/airflow/pull/58901) |
| 2026-03-19 | DB tests deselected at collection time | Dev-iL | [#63791](https://github.com/apache/airflow/pull/63791) |
| 2026-06-14/15 | CI duration monitor; AGENTS.md "exactly 100% coverage of what the PR changes" | Jarek Potiuk; Shahar Epstein | [#68368](https://github.com/apache/airflow/pull/68368), [#68502](https://github.com/apache/airflow/pull/68502) |
| 2026-10-03 | providers that leak process state are run in canary order on PRs | Shahar Epstein | [#74123](https://github.com/apache/airflow/pull/74123) |
| 2026-10-08 | UI-only checks moved from Playwright to Vitest | Brent Bovenzi | [#74367](https://github.com/apache/airflow/pull/74367) |

## 11. The arguments, turn by turn

**pytest replaces nose (2019).**

- *Pain:* nose was described as "rather an old package" [42].
- *Argument for:* Tomasz Urbaszek, 2019-10-14 [22]:

  > I think this proposal will improve our test suite especially that it seems that we only need to fix 16 tests to obtain green CI build.

- *Earlier attempt:* Ash Berlin-Taylor, the same day: "I tried this at the start of the year but we were a few 100 failing tests away." [22]
- *After the merge:* Jarek Potiuk wrote "There were a lot of side effects to remove and head-scratching" (2019-12-05 [23]). A few days later he proposed "to switch to using the standard asserts instead of deriving from TestCase class" (2019-12-09 [24]).
- *Numbers:* AIP-27 records Ash's wish to defer mass conversion until 2.0 [42]. The `TestCase` count shows the conversion happened in late 2022 (section 9). No runtime numbers found.

**Quarantine (April 2020).**

- *Pain:* flaky tests surfaced after the emergency move to GitHub Actions.
- *Proposal:* Jarek Potiuk, 2020-04-20 [25]:

  > tests that are marked as @pytest.mark.quarantined are skipped in regular runs (I identified 58 potential candidates - not all of them are flaky but I wanted to be safe) [...] failure of any of the Quarantine tests does not fail the whole CI [...] the goal is to move all our tests out of Quarantine

- *Question:* Tomasz Urbaszek asked "are we marking single tests or whole classes? This question is mostly related to tests that requires some side effects from previous tests." [25]
- *Review:* on the first PR, Ash Berlin-Taylor noted that it was doing two things, "adding in pytest-rerunfailures and quarantining tests which is an entirely new feature". This is quoted from the #8393 review as rendered on GitHub. The work was split, and #8511 carried the quarantine.
- *Numbers:* lines carrying `pytest.mark.quarantined` were 14 on 2020-04-24, 18 on 2020-08-04, 20 on 2021-06-30, 5 on 2022-12-31, 3 on 2023-10-31, and 3 today. The 2022/23 drop followed the pytest conversion and #28767.

**Selective tests and the GitHub Actions limit (August to October 2020).**

- *Pain:* the build matrix competed with every other ASF project for GitHub Actions jobs. Jarek Potiuk to builds@apache.org, 2020-10-13 [29]:

  > At Apache Airflow, we are starting to hit - more and more often - concurrency limits in GitHub Actions where we seem to compete with other Apache projects. [...] We have - apparently 180 concurrency limit for all Apache projects.

- *Daniel Imberman's proposal (2020-10-01):* gate the full suite on committer review, "I propose that we allow unverified PR's to run basic and static tests, but not perform the full test suite or integration test without first being reviewed." [28]
- *Jarek Potiuk's counter:* run a reduced matrix and select by files instead. He wrote, "Matrix strategy of builds causes enormous strain on Github Actions if the whole matrix is run for all PRs" (2020-10-22), and "there is a really small number of tests that actually NEED to run the full matrix of tests. Those are all the tests that touch "Core" of airflow really." (2020-10-28) [28]
- *Rule written into the commit message (#11417):* "If some of the core/other files change, all tests are run."
- *Numbers:* the #11417 description, as rendered on GitHub, gives 51 checks instead of 110 for an API-only change. Jarek estimated "further 20%-30% less unneeded build job time" for the approval rule (2020-10-28 [28]). Today's doc still frames it as cost: "Running everything for every change would burn an enormous amount of GitHub Actions minutes and make contributors wait an hour or more for feedback on a one-line doc fix" (emphasis markers removed) [12].

**System tests as example DAGs (AIP-47, 2022).**

- *Pain, per the AIP page:* old system tests were "not integrated into the CI process and rarely being executed", relied on credential files and a `variables.env`, and broke the docs generated from them [43].
- *Argument for:* Jarek Potiuk, 2022-01-25 [30]:

  > we will be able to regularly (not with all PR but likely daily) run the example dags with the real services and make sure that at least big part of our Providers code (Hooks/Operators) are still "working as expected" - at least that they pass "smoke tests".
  >
  > Currently we rely mostly on the manual tests done when we release providers

- *AWS position:* Niko Oliveira (AWS) already had "a proof of concept running (internally to AWS) built with AWS Code Pipeline and Code Build" [30].
- *Numbers:* 144 system tests in 10 providers on 2022-03-14, per the AIP page [43]. Today there are 518 example-DAG system tests in 78 provider folders plus core. CI runs one (`example_empty.py`).
- *Policy:* softened. In 2023 Jarek Potiuk called system tests and a dashboard "the minimum requirement" for new service providers [31]. Today's `ACCEPTING_PROVIDERS.rst` says the community "encourages stewards to run system tests and publish results on a publicly accessible dashboard" [18].

**DB / non-DB split (October 2023).**

- *Proposal:* Jarek Potiuk, 2023-10-24 [32]:

  > I believe we can get at least 30-50% reduction in our CI test execution time (and build test time) at the expense of the necessity of marking tests as "db_tests" when they need the DB. [...] This topic has been brought up occasionally in the past - why do we run our tests on multiple versions of multiple databases.

- *Support:* Vincent Beck added a design argument: "I also think, as a contributor, it is a good exercise to, when writing tests, figure out whether the tests I am writing is using the DB." [32]
- *Before:* "~9200 non-DB tests and ~7300 DB tests so ~55% of our tests are non-DB tests" (2023-10-26; emphasis markers removed) [32].
- *After, measured on the PR:* Jarek Potiuk, 2023-10-29 [32]:

  > We got just under 10 minutes for full DB tests in most cases (down from 16-20) [...] The non-DB tests run on self-hosted runners run in under 5 minutes [...] instead of tests = 7x 20 (140) minutes build time we will have 7x 10 DB tests and + 1x 5 non-DB test = 75 minutes. This gives ~ 45% shorter build time needed

- *Public runners, the same day:* 175 build minutes became 125, "~ 30 % improvements on Public Runners" [32].
- *What it did not cover:* Jarek noted that it "does not impact "integration", "helm", "kubernetes" , "docker-compose" (and "system") tests of ours, so this will generally mean that now the focus should be put there" [32].
- *Later numbers:* I found no later public before/after timings beyond the CI duration monitor, which posts to Slack. The test mix did move: DB share of definitions was 42% at the merge and is 29% now (section 4).

**Providers without a DB (2025).**

- *Proposal:* David Blain, 2025-02-07 [34]:

  > I think it would be a good practise to not define and create real Airflow connections within the providers unit tests (which use the Airflow test database), as normally when writing unit tests those should be isolated and not be depend on any external systems like a database.

- *Responses in the same thread:*
  - Jarek Potiuk: "+10 on that. My next step after finishing Provider's move, was to make essentially all unit tests in Providers non-DB tests" [34].
  - Ash Berlin-Taylor warned about mocks (quoted in section 6). He also pointed out that "you can set `ARIFLOW_CONN_*` environment variables and those will be looked at before the DB" [34].
  - Jens Scheffler summed up that "there should rather be a generic Fixture that can build on top of Monkeypatch.Setenv" [34].
- *Implementation:* #51930 (Amogh Desai, 2025-06-22) introduced a "fixture to create `Connections` without DB in provider tests" (commit title). Jarek's call for help followed the same day: "likely there are many providers that only used db to create a Connection and we can turn those tests into non-db tests" [39].
- *Numbers:*
  - Providers with no DB-marked tests, counted by provider test folders: 27 of 97 on 2025-06-22, 64 of 109 today.
  - Provider DB test definitions: 3,257 to 2,932.
  - Provider non-DB test definitions: 8,022 to 18,389.

**UI end-to-end tests (September 2025 to October 2026).** The proposal and the dependency-upgrade argument are quoted in section 7. The design debate was about where the code should live and how much e2e is enough.

- Brent Bovenzi: "With E2E we are testing the UI more than we are testing the API so I think the code should sit closer to the UI code."
- Pierre Jeambrun: "I like playwright and I feel this is the modern solution to go to."
- Jarek Potiuk, on cost [40]:

  > Keeping the tests stable and side-effect free will be a challenge - so likely a good 'reset the environment' before each test is a must. Also they need to be run with all UI changes in CI which will make UI PR run longer.

- *Numbers:* 0 browser specs on 2025-09-23 and 26 today. Vitest files went from 14 to 225. Rahul Vats's figure of "only about 4 test files covering major pages" probably counted page-level tests only (inference). Retries (4) and a daily flaky-test report followed, and in October 2026 checks moved back down to Vitest (section 7).

## 12. Coverage

**Yes, Airflow measures coverage. I found no evidence that it ever gated merges on it.** Branch protection history before `.asf.yaml` is not visible from the repository.

- **2016-05-30:** a `.codecov.yml` with "Do not add comments to pull requests" (Bolke de Bruin).
- **2018-08-25:** Codecov enabled on the Docker CI build in place of coveralls (#3780).
- **2020-08-07:** Jarek Potiuk made coverage an informational status (#10208). The commit message promised a possible gate that never came:

  > we also remove comment from coverage report and replace it with (for now) informational status message published to github. If we see that it works, we can change it to a PR-failing status if coverage drops for a given PR.

- **2021-11-10:** coverage disabled for PRs (#19523): "The change only uses test coverage for `main` builds where we have a lot of memory available." Since then `run_coverage` returns true only for pushes to `main` in `apache/airflow` (`ci_commands.py` [15]).
- **2023-10-23:** Ephraim Anierobi added local per-area coverage scripts (`scripts/cov/*.py`) that flag any covered file whose coverage drops, and any file on the not-yet-fully-covered list that reaches 100%. His commit says: "Currently, the coverage is not enforced even on the CI." The scripts are still not called from any workflow.
- **2024-03-18:** coverage disabled on Python 3.12 because it "runs slower and occasionally timeouts" (#38255).

Today:

- `codecov.yml` keeps the project status `informational: true`. Its path filters still name the pre-2025 `airflow/` layout.
- Uploads happen only from `main` pushes (Python versions other than 3.12 and 3.13).
- No status is required by `.asf.yaml` [15][16].
- The only coverage rule that applies to every PR is written for agents in `AGENTS.md`: "Target exactly 100% coverage of what the PR changes — no more, no less" (#68502, 2026-06-15). It is not machine-checked.

## Chart-ready table

category | maps_to (post taxonomy) | lines | pct | files | tests
---|---|---|---|---|---
Unit, DB (core) | none (in-process, real DB; nearest adapters_free) | 146198 | 18.46 | 210 | 5602
Unit, DB (providers) | none (in-process, real DB; nearest adapters_free) | 69460 | 8.77 | 158 | 2932
Unit, non-DB (core) | unit | 37849 | 4.78 | 140 | 2071
Unit, non-DB (providers) | unit | 340952 | 43.05 | 1205 | 18389
Task SDK tests | unit | 39888 | 5.04 | 88 | 2288
airflow-ctl tests | unit | 6585 | 0.83 | 13 | 317
Shared library tests | unit | 7255 | 0.92 | 24 | 428
Integration tests | adapters_free | 2860 | 0.36 | 33 | 85
System tests (example DAGs) | adapters_metered (examples row) | 52518 | 6.63 | 519 | 520
Helm unit tests | none | 24389 | 3.08 | 76 | 1289
Kubernetes tests | api | 1876 | 0.24 | 5 | 57
Docker image / compose tests | none (packaging) | 451 | 0.06 | 4 | 17
Airflow E2E tests | api | 2158 | 0.27 | 19 | 96
Task SDK integration tests | api | 866 | 0.11 | 8 | 39
airflow-ctl integration tests | api | 339 | 0.04 | 3 | 17
Python API client test | api | 82 | 0.01 | 1 | 1
UI e2e (Playwright) | e2e | 1364 | 0.17 | 26 | 105
UI unit/component (Vitest) | fast (front end) | 24497 | 3.09 | 230 | 1403
Go SDK tests | unit | 15608 | 1.97 | 47 | 539
Java SDK tests (Kotlin) | unit | 8461 | 1.07 | 30 | 409
TypeScript SDK tests | unit | 8300 | 1.05 | 30 | 624
(excluded) tooling tests | tooling | 33974 | — | 164 | 2029
(excluded) shared helpers | — | 27312 | — | 1718 | —

## Sources

Repository files are cited at the snapshot (2026-10-11) unless a date is given.

1. `contributing-docs/09_testing.rst`, snapshot 2026-10-11.
2. `contributing-docs/testing/unit_tests.rst`, snapshot 2026-10-11 (file created 2024-01-26 by #36969).
3. `contributing-docs/testing/integration_tests.rst`, snapshot.
4. `contributing-docs/testing/system_tests.rst`, snapshot.
5. `contributing-docs/testing/{helm_unit_tests,k8s_tests,docker_compose_tests,airflow_e2e_tests,task_sdk_integration_tests,airflow_ctl_tests,python_client_tests}.rst`, snapshot.
6. `airflow-core/src/airflow/ui/tests/e2e/README.md`, `playwright.config.ts`, `vite.config.ts`, `testsSetup.ts`, snapshot.
7. `devel-common/src/tests_common/pytest_plugin.py`, snapshot.
8. `airflow-core/src/airflow/settings.py` (`SkipDBTestsSession`), snapshot.
9. `pyproject.toml` `[tool.pytest]`, snapshot.
10. `.github/workflows/ci-amd.yml`, `run-unit-tests.yml`, `special-tests.yml`, `integration-system-tests.yml`, `additional-prod-image-tests.yml`, `ui-e2e-tests.yml`, `e2e-flaky-tests-report.yml`, `ci-duration-monitor.yml`, snapshot.
11. `scripts/ci/testing/run_unit_tests.sh`, `run_integration_tests_with_retry.sh`, `scripts/in_container/run_ci_tests.sh`, snapshot.
12. `dev/breeze/src/airflow_breeze/utils/selective_checks.py` and `dev/breeze/doc/ci/04_selective_checks.md`, snapshot.
13. `.pre-commit-config.yaml`, `airflow-core/.pre-commit-config.yaml`, `providers/.pre-commit-config.yaml`, snapshot.
14. `airflow-core/tests/unit/always/test_project_structure.py`, snapshot.
15. `codecov.yml`, `.github/actions/post_tests_success/action.yml`, `dev/breeze/src/airflow_breeze/commands/ci_commands.py`, `scripts/cov/cov_runner.py`, snapshot.
16. `.asf.yaml`, snapshot.
17. `AGENTS.md` (symlinked as `CLAUDE.md`), snapshot; test-scope line added 2026-06-15 by #68502.
18. `providers/ACCEPTING_PROVIDERS.rst`, snapshot.
19. `task-sdk/tests/conftest.py`, `airflow-ctl/tests/conftest.py`, snapshot.
20. Siddharth Anand, "Why do we need SQLite in Airflow?", dev@, 2016-05-04. https://lists.apache.org/thread/c1mmtmlx28d2btw475cnbs5kohdl8rg4
21. Vijay Bhat, "Travis random failure investigation", dev@, 2016-10-21. https://lists.apache.org/thread/tzms033z94x4trh4tr07pjjxtmoqp2tx
22. Tomasz Urbaszek, "[PROPOSAL] Migrate to Pytest", dev@, 2019-10-14, and Ash Berlin-Taylor's reply the same day. https://lists.apache.org/thread/zhzr6tqh54ppzh19mdh788vqgqkljgot , https://lists.apache.org/thread/9fksnmbzmfwcfoz3ll2m2pnxomkdsvq8
23. Jarek Potiuk, "[ANNOUNCEMENT] just merged Pytest test change", dev@, 2019-12-05. https://lists.apache.org/thread/b2clghrqc36x0cfwr0dcvo818vldbhpl
24. Jarek Potiuk, "[DISCUSS] Revenge of the asserts", dev@, 2019-12-09. https://lists.apache.org/thread/0hbvqyxohgt7kxkhlbwf9yygzrox8m1w
25. Jarek Potiuk, "CI tests idea - Quarantined tests idea", dev@, 2020-04-20, with Tomasz Urbaszek's replies. https://lists.apache.org/thread/zhszpb5nvws1vb5odvm0k1z9sxl21mfp , https://lists.apache.org/thread/zdlv8gsqwn1q7yx1qz81l6p1om2nqz5f , https://lists.apache.org/thread/9djtw9l0xgl8fspr5rj69toxzmnw928t
26. Jarek Potiuk, "(hopefully) more stable Github Actions CI with Quarantine", dev@, 2020-04-23. https://lists.apache.org/thread/n3qxlbdzn9nlxxst9r0nk08mmkng02q4
27. Jarek Potiuk, "Quarantined tests - gethering stats", dev@, 2020-08-04. https://lists.apache.org/thread/rj2j1l969mp4tq4841g54v2mjmrr4pm8
28. Daniel Imberman, "Add /ready-to-test bot to airflow CI", dev@, 2020-10-01, and Jarek Potiuk's replies of 2020-10-02, 2020-10-22 and 2020-10-28. https://lists.apache.org/thread/1q9tqf732nk4nv0dg3hg65t1lvsw84ob , https://lists.apache.org/thread/1z9bgqgrjb1p67p1h4zocfd02vr5dn15 , https://lists.apache.org/thread/2xd7znpd3bkjtho0fyjkmx50hs4m4qdp , https://lists.apache.org/thread/dfgo6drlgcwl4ggy774o18ljn848togb , https://lists.apache.org/thread/o0z0q930q18m7744bqkgw2bcwhm6dx6r
29. Jarek Potiuk, "GitHub Actions Concurrency Limits for Apache projects", builds@apache.org, 2020-10-13. https://lists.apache.org/thread/fxy5orhk8yp0mt0zbrs3r53234w9khl4
30. Mateusz Nojek, "[DISCUSSION] AIP-47 New design of Airflow System Tests", dev@, 2022-01-25, with replies by Jarek Potiuk and Niko Oliveira the same day. https://lists.apache.org/thread/htd4013yn483qfhwv11vc26jpf2yvjph , https://lists.apache.org/thread/9f2oxfftq4gz77x6b3w2xo5n5745p3c0 , https://lists.apache.org/thread/0wbcrbdsbmlfwbgtsn9ovpsbrjnsszt7
31. Jarek Potiuk, "[DISCUSS] Describing (new) provider approval policies", dev@, 2023-03-30. https://lists.apache.org/thread/xf4wn1hw08cs725fp962252y7mmptk3b
32. Jarek Potiuk, "[PROPOSAL] (likely) significantly shorten CI test time: splitting to db/non-db tests", dev@, 2023-10-24, with replies by Vincent Beck (2023-10-24) and Jarek Potiuk (2023-10-26, 2023-10-29 ×2). https://lists.apache.org/thread/bbojb6kqbdvqcshnh80hqw0vhtd6ccwn , https://lists.apache.org/thread/4xo1nz9wb3hk5g65s5c0pbdg1zhbbtms , https://lists.apache.org/thread/0hcg2bsbqcd6v6jwxokt43vcy3wfgsmh , https://lists.apache.org/thread/n2znyc4ryvgkw7kld8wk64160dks5dgo , https://lists.apache.org/thread/145j70bbnl8w2nkdgldnhmyf2co5jzg6
33. Jarek Potiuk, "[ANNOUCEMENT] HOPEFULLY BIG Speed/Stability improvements of CI by DB / NonDB test splitting merged", dev@, 2023-10-31. https://lists.apache.org/thread/tt0nqbtloyfxs0qrz6ok53h8npf4xm2h
34. David Blain, "[PROPOSAL] Remove creation of real Airflow connections in provider unit tests", dev@, 2025-02-07, with replies by Jarek Potiuk, Ash Berlin-Taylor (2025-02-07) and Jens Scheffler (2025-02-08). https://lists.apache.org/thread/5ygm6sl5fox0qoywo5w6ojj3c7mtw6mo , https://lists.apache.org/thread/6g9lwlsoz50gg6gg6wzvy1yj2qylm135 , https://lists.apache.org/thread/nncmj8qv3nhnm8sm7qvxs9wfqxdjk2xf , https://lists.apache.org/thread/mmyvp2zcljvd1vsff50ffscvjnb6cvyj , https://lists.apache.org/thread/2r57gj2ogbd5rhrfnct3whvglh90xtz2 , https://lists.apache.org/thread/35nfpm03hgv643t18c78n0jmz3nrk2wt
35. Jarek Potiuk, "[ANNOUNCE] All providers moved to the new provider's structure !", dev@, 2025-02-09. https://lists.apache.org/thread/3jsz0y54dlr22f420sonf3nxg8xv4fxs
36. Jarek Potiuk, "[DISCUSS] Tests structure for providers", dev@, 2025-02-15, and Ash Berlin-Taylor's reply. https://lists.apache.org/thread/xm6th19xw2v1zo8k8kjomsbzz51njxgv , https://lists.apache.org/thread/oj7t2fccp7s5pmj26xlo5536ccvwqgr2
37. Jarek Potiuk, "[ANNOUNCEMENT] airflow-core is there (finally!)", dev@, 2025-03-21. https://lists.apache.org/thread/vjx3j1o5j1h2m6qdcqpmt35wq5lwbsl9
38. Jarek Potiuk, "[DISCUSS} Enabled experiment auto-merge feature", dev@, 2025-04-26, and Elad Kalif's reply 2025-04-29. https://lists.apache.org/thread/dmd288rypcffds2ossg2hhwwhfzn9cy4 , https://lists.apache.org/thread/b1hb5ks2qt51ccp4dpw24x0jvsyf1dg6
39. Jarek Potiuk, "[HELP NEEDED] Cleanup pytest.mark.db_tests", dev@, 2025-06-22. https://lists.apache.org/thread/qwssqm25fo3nwrm983jhf5v9ol4v86kd
40. Rahul Vats, "[Discuss] Improving Airflow UI Testing Coverage", dev@, 2025-09-23, with replies by Vincent Beck and Brent Bovenzi (2025-09-23), Pierre Jeambrun and Jarek Potiuk (2025-09-24), and Rahul Vats (2025-12-12). https://lists.apache.org/thread/hpbbmo2tokj6zzc9044vc66tdqcnbrjd , https://lists.apache.org/thread/0ss60j7jc5f8gvsqnzn0dohrv46dvnl9 , https://lists.apache.org/thread/o868ccnzbdty8xcdx9okqry7rr4zdltt , https://lists.apache.org/thread/m3k6d1bkgjn3scwtm8636crgf1zg85bv , https://lists.apache.org/thread/66h4o20g2rg7gphpghrl6dtjfkyltq18 , https://lists.apache.org/thread/85f7wb86pn41r6grdv2w6nf6zsxmo4sw
41. AIP-4 "Automation of System Tests [Deps: AIP-47]", Apache wiki; created by Jarek Potiuk, earliest comment 2018-09-19, last updated 2024-06-12. https://cwiki.apache.org/confluence/spaces/AIRFLOW/pages/93324355/AIP-4+Automation+of+System+Tests+Deps+AIP-47
42. AIP-27 "Migrate to pytest", Apache wiki; created by Tomek Urbaszek, comments 2019-10-14, completed in 1.10.7. https://cwiki.apache.org/confluence/display/AIRFLOW/AIP-27+Migrate+to+pytest
43. AIP-47 "New design of Airflow System Tests", Apache wiki; accepted 2022-02-24, completed 2022-03-25. https://cwiki.apache.org/confluence/display/AIRFLOW/AIP-47+New+design+of+Airflow+System+Tests
44. "Airflow Provider System Test Dashboards", airflow.apache.org/ecosystem, accessed 2026-10-11. https://airflow.apache.org/ecosystem/#airflow-provider-system-test-dashboards
45. PR #6472 "Running tests with pytest", merged 2019-12-05. https://github.com/apache/airflow/pull/6472
46. PR #7346 "Detect missing tests for providers package", merged 2020-02-03. https://github.com/apache/airflow/pull/7346
47. PR #8393 "Bring back CI optimisations", opened 2020-04-16, closed unmerged 2020-04-21 (review by Ash Berlin-Taylor); PR #8511 "Move some tests to quarantine", merged 2020-04-23. https://github.com/apache/airflow/pull/8393 , https://github.com/apache/airflow/pull/8511
48. Issue #10507 "[OPTIMISATION] Selective builds for different types of tests", opened 2020-08-24; PR #11417, merged 2020-10-12. https://github.com/apache/airflow/issues/10507 , https://github.com/apache/airflow/pull/11417
49. PR #30775 "Add pre-commit hook to ban usage of unittest.TestCase in unit tests", merged 2023-05-02. https://github.com/apache/airflow/pull/30775
50. PR #11828 "The PRs which are not approved run subset of tests", merged 2020-10-29. https://github.com/apache/airflow/pull/11828
51. PR #10208 "Improves stability of reported coverage and makes it nicer", merged 2020-08-07; PR #19523 "Disable test code coverage for PRs", merged 2021-11-10; PR #35061 "Add Code Coverage Helper Tool for Airflow", merged 2023-10-23; PR #38255 "Disable coverage for Python 3.12", merged 2024-03-18.
52. PR #43181 "Run Task SDK tests without DB", merged 2024-10-21; PR #44690 "Fix accidental db tests in Task SDK", merged 2024-12-06; PR #48099, merged 2025-03-31.
53. PRs #51930, #52017, #52021, merged 2025-06-22; issue #52020.
54. PR #35264 and PR #35160, merged 2023-10-30 and 2023-10-31. https://github.com/apache/airflow/pull/35160
55. PR #41846 "Initialize new airflow/ui directory", merged 2024-08-30. https://github.com/apache/airflow/pull/41846
56. PR #58548 "Add UI E2E testing framework with Playwright and Breeze integration", merged 2025-11-28. https://github.com/apache/airflow/pull/58548
57. PR #58901 "Add CI workflow for UI e2e tests", merged 2025-12-10. https://github.com/apache/airflow/pull/58901
58. PR #53332 "Task SDK Integration Testing Infrastructure", merged 2025-07-25 (commit message by Amogh Desai). https://github.com/apache/airflow/pull/53332
59. PR #54072 "Introduce e2e testing with testcontainers", merged 2025-09-11. https://github.com/apache/airflow/pull/54072
60. PR #56124 "Implement integration test for airflowctl with 3.1", merged 2025-10-20. https://github.com/apache/airflow/pull/56124
61. PRs #11693 (2020-10-27) and #11827 (2020-10-30), Helm tests in Python; PR #9468 (2020-07-01), Kubernetes tests via the chart; PR #19737 (2021-11-24), Docker image tests.
62. PRs #26831 (2022-10-10) to #28378 (2023-01-06), unittest to pytest waves; PR #28767 (2023-01-11), quarantine cleanup.
63. PR #74123 "Run leaking provider tests with providers changed after them in CI", merged 2026-10-03 (commit message by Shahar Epstein). https://github.com/apache/airflow/pull/74123
64. PR #64446 (2026-03-30), e2e flaky report; PR #68368 (2026-06-14), CI duration monitor; PR #68502 (2026-06-15), AGENTS.md test scope.
65. PR #74367 "UI: Move UI-only e2e checks to unit tests", merged 2026-10-08 (commit message by Brent Bovenzi). https://github.com/apache/airflow/pull/74367
66. PR #63791 "Deselect DB tests at collection time instead of skipping at runtime", merged 2026-03-19. https://github.com/apache/airflow/pull/63791
67. PRs #49746 (2025-04-26) and #50009 (2025-04-30), auto-merge experiment and removal.
68. Issue #10118 "Quarantined tests master", opened 2020-08-02. https://github.com/apache/airflow/issues/10118

## Appendix: commands and counting decisions

**Snapshot.** All work ran from the session scratchpad. The clone was never executed: no pytest, breeze, uv, prek or scripts from it.

```
git clone --depth 1 https://github.com/apache/airflow.git          # in scratchpad/airflow-clone/
git log -1 --format='%H %cI'   -> 4ca1f6693bb380ae1f148a6187001adbcadbfa22 2026-10-11T08:00:35-05:00
```

**Counting.**

```
python3 -I notebooks/X-shapes-of-tests/tools/count_lines.py airflow-clone/airflow --by-file > all_by_file.csv   # 9,981 files
python3 -I classify.py   airflow-clone/airflow all_by_file.csv categorized.csv details.json   # my script, outside the clone
python3 -I aggregate.py  categorized.csv details.json
python3 -I final.py      categorized.csv details.json airflow.counts.csv
# Helm templates for the ratio only (YAML is not in the tool's default extensions):
python3 -I notebooks/X-shapes-of-tests/tools/count_lines.py airflow-clone/airflow/chart --ext .yaml,.tpl,.json --include templates values.yaml values.schema.json --depth 1
```

The tool's default excludes (`build/`, `dist/`, `vendor/`, `coverage/`, `node_modules/`) matched no directory in this tree. The tool does not recognise docstrings, so docstrings count as code. That inflates Python rows relative to TypeScript, Go and Kotlin.

**Grouping rules.** The first rule that matches wins, by path.

- **UI roots.** These are `airflow-core/src/airflow/ui/`, the simple auth manager UI, and the `edge3` and `common/ai` provider `www` plugins.
  - `openapi-gen/` is generated and excluded.
  - `tests/e2e/specs/*` are Playwright tests. The rest of `tests/e2e/` (pages, fixtures, utils, global setup) is helpers.
  - `*.test.(ts|tsx|js|mjs)` are Vitest tests.
  - `src/mocks/**`, `testsSetup.ts` and `src/utils/{Wrapper,AppWrapper,ChakraWrapper,RouterWrapper}.tsx` are helpers. The wrappers are imported only by tests.
  - `rules/`, `dev/` and the config files are build config.
  - All other `src/` files are UI production.
- **`airflow-core/tests/unit`.** `test_*.py` files are core unit tests, except `always/test_project_structure.py` and `always/test_provider_yaml_schema.py`, which are tooling tests. Everything else in the folder is helpers: conftest, `__init__`, test DAGs, plugins, `testconfig`.
- **`tests/integration`** (core or provider): `test_*.py` are integration tests; the rest are helpers.
- **`tests/system`** (core or provider): `example_*.py` and `test_*.py` are system tests. The rest, and anything under `resources/` or `resources_cleanup/`, are helpers.
- **`providers/*/tests/unit`:** `test_*.py` are provider unit tests; the rest are helpers.
- **`task-sdk/tests`, `airflow-ctl/tests`, `shared/*/tests`:** `test_*.py` are tests; the rest are helpers.
- **Out-of-process suites.** In `airflow-e2e-tests`, `task-sdk-integration-tests`, `airflow-ctl-tests`, `kubernetes-tests` and `docker-tests`, `test_*.py` files under `tests/` are tests. Everything else (conftest, harness, DAGs, Java and Go bundles used by e2e) is helpers.
- **Helm:** `chart/tests/{helm_tests,overlay_tests}/test_*.py` are Helm tests; `chart_utils` and conftests are helpers.
- **Python client:** `clients/python/test_python_client.py`.
- **Go:** `*_test.go` are tests; `testdata/` and `internal/contexttest` are helpers; `*.gen.go` are generated; `example/` and `dags/` are SDK examples.
- **Java SDK:** `*/src/test/**/*Test.kt` are tests. Other test-source files and `src/testFixtures/` are helpers. `src/main` is production; `example/` and `scala_spark_example/` are examples.
- **TS SDK:** `tests/**/*.test.ts` are tests and other files in `tests/` are helpers. `docs/tests` and `scripts/*.test.mjs` are tooling tests. `src/generated/` is generated; `src/` is production; `example/` is examples.
- **Tooling:** `dev/breeze/tests`, `dev/registry/tests`, `dev/mypy/tests`, `scripts/tests`, `devel-common/tests` and `performance/tests` are tooling tests. `devel-common/src/tests_common` is helpers (the shared test framework). The rest of `dev/`, `scripts/`, `devel-common/`, `performance/` and `registry/` is tooling code, excluded.
- **Demotion rule.** A `test_*.py` (or `_test.go`, `*.test.ts`, `*Test.kt`) file that defines no test and no `Test*` class becomes a helper. Examples are the test DAG files named `test_*.py` and `kubernetes_tests/test_base.py`. Tooling tests were not demoted.
- **Excluded from production:**
  - migrations: `airflow-core/src/airflow/migrations`, provider `migrations/`
  - generated code: `get_provider_info.py` (marked "AUTOMATICALLY GENERATED"), `task-sdk/.../datamodels/_generated.py`, `airflow-ctl/.../datamodels/*generated*.py`, Go `*.gen.go`, `ts-sdk/src/generated`, UI `openapi-gen`
  - vendored code: `_vendor`
  - example DAGs in `src`
  - `.sql` files inside test trees, counted as data

**DB / non-DB attribution.** My script parsed every Python test file with `ast`.

- A test is a `def test*` or `async def test*` at module level or in any class, with nested classes included and parametrization not expanded.
- A test is DB if its effective marks contain `db_test` or `backend` and not `non_db_test_override`. Effective marks are the union of:
  - module `pytestmark`
  - class decorators and class-level `pytestmark`
  - marks of base classes defined in the same module
  - function decorators

  This mirrors `_is_db_test` in the plugin [7].
- For files containing both kinds of test:
  - Code lines inside DB-test spans count as DB and lines inside non-DB spans count as non-DB. A span runs from the first decorator to `end_lineno`, and a code line follows the tool's rule.
  - Shared lines (imports, fixtures, helpers) are split in the same proportion.
  - The file goes to the side with the larger share in the file counts.
  - The per-file share is the `db_line_share` column of the CSV.

**Test counts in other languages:**

- TypeScript: lines matching `^\s*(it|test)(\.(each|only|skip|concurrent|todo|fails|fixme|fail|slow))?\s*` followed by `(` or a backtick (template-literal `it.each`)
- Go: `^func Test\w+\(`
- Kotlin: `@Test`
- System tests: one test per example DAG that calls `get_test_run(`

**Mocking and real-dependency regexes** (Python, applied to the whole file text):

```
MOCK_FILE  = ^\s*from unittest import [^\n]*\bmock\b | ^\s*from unittest\.mock import | ^\s*import unittest\.mock
             | ^\s*import mock\b | ^\s*from mock import | ^\s*from pytest_mock import | \bmocker\b | \bmonkeypatch\b
             | ^\s*from moto import | \brequests_mock\b | \bMockTransport\b
MOCK_CALL  = \bmock\.patch(?:\.object|\.dict|\.multiple)?\s*\( | (?<![\w.])patch(?:\.object|\.dict|\.multiple)?\s*\(
             | \b(?:NonCallableMagicMock|MagicMock|AsyncMock|PropertyMock|Mock|create_autospec)\s*\(
             | \bmocker\.\w+ | \bmonkeypatch\.\w+ | @mock_aws\b | \brequests_mock\.\w+ | \bMockTransport\s*\(
DB_MARKED  = pytest\.mark\.(?:db_test|backend)\b
DB_USE     = \b(?:create_session|provide_session|dag_maker|clear_db_[a-z_]+|settings\.Session|testing_dag_bundle)\b
             | \bsession\.(?:add|add_all|query|execute|scalar|scalars|merge|commit|flush|get|delete)\s*\(
INPROC_SRV = \bTestClient\b | \btest_client\b | \bunauthenticated_test_client\b | \bclient\.(?:get|post|put|patch|delete)\s*\(
COMPOSE    = \bpytest\.mark\.integration\s*\(
TS files   = \bvi\.(?:mock|fn|spyOn|stubGlobal|mocked|doMock|stubEnv)\b | from ["']msw(?:/node)?["'] | \bjest\.(?:mock|fn|spyOn)\b | \bpage\.route\s*\( | \bsinon\b
TS calls   = \bvi\.(?:mock|fn|spyOn|stubGlobal|mocked|doMock|stubEnv)\s*\( | \bjest\.(?:mock|fn|spyOn)\s*\( | \bpage\.route\s*\(
             | \bserver\.use\s*\( | \bhttp\.(?:get|post|put|patch|delete)\s*\(
Go calls   = \bmock\.\w+\( | \.On\(" | \bfake[A-Z]\w*\{ | \bmock[A-Z]\w*\{
Kotlin calls = \bmockk\s*[<(] | \bevery\s*\{ | \bverify\s*\{ | \bspyk\s*[<(] | Mockito\.\w+\(
Go files   = "github.com/stretchr/testify/mock" | gomock | mockery | \bfake[A-Z]\w* | \bmock[A-Z]\w*
Kotlin     = \bmockk\b | Mockito | \bmock< | \bspyk\b | \bfake[A-Z]\w*
```

Mocks per 1,000 lines = call sites / tool code lines × 1,000. `monkeypatch` counts as a mocking facility, as the brief asks, even though Airflow mostly uses it for environment variables. That raises the shares a little.

**Marker census:** `grep -rn --include=*.py "pytest\.mark\.<name>\b" .`, excluding the plugin file.

**Test data:**

```
find <all test roots> -type f | grep -v '\.(py|ts|tsx|go|java|kt|sh|mjs|js)$' | grep -v '__pycache__|README|\.md$|\.toml$|\.lock$|gitignore|\.gradle$|\.properties$' | xargs wc -lc
```

Result: 222 files, 51,433 lines, 2,047,505 bytes.

**History.** I could not reach `api.github.com` or `github.com` from the shell; the session proxy returned 403 for apache/airflow. GitHub facts therefore come from two places:

- A second, history-only clone, `git clone --filter=blob:none --no-checkout --single-branch --branch main` in `scratchpad/airflow-history/`, with the same HEAD SHA and 41,961 commits. Dates are committer dates (`%cs`). Commit messages are quoted verbatim from `git show -s`. Additions were dated with `git log --diff-filter=A`, and hook and string introductions with `git log -S`.
- `WebFetch` of github.com PR pages for titles and review comments. Two short quotes come from rendered PR pages and are marked as such: Ash Berlin-Taylor on #8393, and the 51-versus-110 checks figure on #11417.

Point-in-time counts used sparse worktrees of that clone:

```
git worktree add --no-checkout ../wt-X <sha>
git sparse-checkout set --no-cone '/tests/'   # or '/airflow-core/tests/' '/providers/**/tests/'
git checkout
```

| commit | date | used for |
|---|---|---|
| a7e76baf60 | 2023-10-31 | DB/non-DB trend |
| 14b00ed5e2 | 2025-06-22 | DB/non-DB trend |
| 8e2a0bc2e3 | 2021-06-30 | `TestCase` and quarantine counts |
| f77417eb0d | 2021-12-31 | `TestCase` counts |
| ca361ee188 | 2022-06-30 | `TestCase` counts |
| 378c8faba1 | 2022-12-31 | `TestCase` and quarantine counts |

- The trend counts used the same AST function (scripts `compare_old.py` and `compare_new.py`). They counted code lines with the tool's rule re-implemented, not with the tool itself.
- The 2023 tree has core and provider tests under one `tests/` folder (`tests/providers/**` taken as providers). Test DAG and `test_utils` folders were skipped.
- Quarantine counts are lines matching `pytest.mark.quarantined`, not starting with `#`. For 2020-04-24 and 2020-08-04 they come from `git grep` on the history clone.
- UI file counts come from `git ls-tree -r` at the last commit before each date.

The mailing-list archive was read through `https://lists.apache.org/api/stats.lua?domain=airflow.apache.org&list=dev&q=<terms>&d=dfr=<from>|dto=<to>` and `https://lists.apache.org/api/email.lua?id=<id>`. Quoted lines are from the message body with quoted replies (`>`) removed. Where a source used `*bold*` markers, I removed them and say so.

**Judgment calls:**

1. System tests are included in the whole. The `src` example DAGs and SDK examples are not.
2. The language SDK tests are included in the whole. They are product code, but they are library tests.
3. DB tests are mapped to no post category ("nearest adapters_free"). They are in-process like `fast`, but they use the real dependency and are the main proof.
4. The two repository-meta tests in `airflow-core/tests/unit/always` were moved to tooling.
5. The Helm ratio uses YAML templates counted with the tool's `--ext` option. The tool strips no YAML or `{{/* */}}` comments, so template lines are slightly overstated.
6. In the Vitest row, 181 of 230 files render components and 49 test pure functions; they were not split into `unit` and `fast`.
7. Test counts are definitions, not collected items. Airflow's own 2023 counts (9,000 non-DB, 7,578 DB) were probably collected items, including parametrization (inference), so they are not directly comparable with mine.

**Deviations from the brief:**

- The CSV adds three columns after `category`: `tests`, `tests_db`, and `db_line_share`. The last one makes the mixed-file split reproducible.
- `category` values:
  - `test:*`: counted test rows. Core and provider unit files carry the suffix `-db`, `-nondb` or `-mixed`.
  - `helper:*`: helpers.
  - `prod:*`: production.
  - `examples:*`: examples.
  - `excluded:*`, `data:*`: everything else.
- Mock-density figures for Go and Kotlin use rough heuristics (patterns above), less reliable than the Python and TypeScript ones.
- The helper scripts (`classify.py`, `aggregate.py`, `final.py`, `compare_old.py`, `compare_new.py`) lived in the session scratchpad and are not committed. Their rules are written out above in full.
