# Discourse: the shape of its tests

Measured: https://github.com/discourse/discourse at 008b5fc4585ca178bf10642d3da1dcc39e2ace50 (2026-10-11T19:41:56+11:00, "FIX: Handle AI completion edge cases (#44460)"), default branch `main`.
Counted with notebooks/X-shapes-of-tests/tools/count_lines.py, rules as in
the brief. Deviations in the appendix.

## Summary

Posture: classical (Detroit) and database-backed. Almost every backend test runs in one process against a real PostgreSQL and Redis. A browser suite over a real server covers user flows, and the team has said it is "all in" on it since 2022. Mocking has been discouraged in writing since 2014. The frontend has its own large QUnit suite that runs on a fake server.

| e2e: system specs | api: request specs | backend in-process on real PG/Redis | QUnit acceptance (fake server) | QUnit component | QUnit unit | other |
|---|---|---|---|---|---|---|
| 64,141 (6.9%) | 151,766 (16.3%) | 423,010 (45.3%) | 59,711 (6.4%) | 134,066 (14.4%) | 78,516 (8.4%) | 21,686 (2.3%) |

History: the team moved steadily away from mocks and toward real collaborators. The steps were event-tracking helpers instead of mock expectations (2017), request specs instead of controller specs (2017–2018), speed work so a DB-backed suite stays usable (`fab!`, parallel runs, 2019), and browser system specs (2022). Flakiness was the price, and since 2023 it has been handled by machinery: automatic reruns, flaky-test logs, timeouts and failing on slow finders.

## 1. Posture and classification

Discourse does not label its tests "unit" or "integration" in one taxonomy. It sorts them by **what kind of Rails or Ember object they exercise**, using the folder conventions of rspec-rails and ember-qunit. On top of that, a few written rules say which layer owns which assertion.

The written posture appears in four places:

- **Contribution guidelines** (meta topic 3823, the page CONTRIBUTING.md links to). Sam Saffron added this in revision 30, on 2014-11-02:

  > Mocking is heavily discouraged. Only use mocking when absolutely critical.
  > (Sam Saffron, meta.discourse.org/t/3823, revision 30, 2014-11-02)

  The current wording (revision 65, 2026) reads: "Test contributions are welcomed, especially for untested processes and controller actions. Avoid mocking unless absolutely necessary."
- **Agent skills in the repository.** `.skills/discourse-writing-rspec-tests/SKILL.md` is the testing guide that `AGENTS.md`, `CLAUDE.md` and `.github/instructions/copilot.instructions.md` all point to. It is the most explicit placement policy in the project. The key lines, verbatim:

  > **Each layer asserts what it owns** — models own validations, scopes, callbacks, and persisted state; services own orchestration, authorization, and return values; request specs own the HTTP contract and externally visible effects of the action; jobs own execution behavior and any required idempotency. Don't re-assert a lower layer's contract from above.

  > Use one system test per user flow, not per internal code path. If scenarios look the same to the user but differ internally, test the flow once and cover the branches with cheaper tests.

  > **Don't over-mock** — mock external boundaries (HTTP, third-party services), not internal collaborators. Too many mocks signals a design problem.

  The layer and system-test lines come from PR #41611 (Alan Tan, merged 2026-07-10), which added "public-boundary and test-layer guidance so specs assert behavior owned by the layer under test." The file was edited again on 2026-07-30 (#42122) and 2026-09-09 (#43440).
- **Developer guides** in `docs/developer-guides/` (synced to meta.discourse.org). The system-specs guide says "Make sure you are testing the happy path only, no complicated `context` blocks and branching conditionals". The theme testing guide (2023-10-24) recommends system tests over QUnit for themes.
- **Docs that say nothing on placement.** `docs/TESTING.md` is only about MailHog. CONTRIBUTING.md has no testing section.

The test tree at the snapshot, with one line per category in the project's own words where they exist:

```
spec/                          RSpec, Ruby (core); same layout under plugins/*/spec and themes/*/spec
  system/                      "simulate the actions of a real user using the app in a browser" (Playwright + Capybara)
    page_objects/              helpers: "Always use page objects - never write raw selectors" (skill)
  requests/                    "rather than controller specs ... verify routing, middleware, controller actions, and response payloads end-to-end" (skill)
    api/                       rswag specs: validate documented endpoints against JSON schemas and generate the OpenAPI file
  integration/                 cross-subsystem flows (rate limiting, SMTP, MessageBus, OAuth); request-type by rspec-rails inference
  models/                      "models own validations, scopes, callbacks, and persisted state" (skill)
  services/                    "services own orchestration, authorization, and return values" (skill)
  jobs/                        "jobs own execution behavior and any required idempotency" (skill)
  serializers/                 JSON shape of models
  lib/                         everything under lib/ (the largest folder)
  multisite/                   multi-tenant behaviour; must be `type: :multisite` at top level (enforced by RuboCop)
  integrity/                   repository consistency: coding style, i18n, JS constants match Ruby
  mailers/ helpers/ views/ initializers/ tasks/ script/ db/ migrations/ import_export/ queries/ resources/ generator/   small folders
  support/ fabricators/ fixtures/   helpers and data
frontend/discourse/tests/      QUnit, JavaScript/Glimmer (core); same layout under plugins/*/test/javascripts and themes/*/test
  unit/                        "Unit (lib/utility/service/model)" (skill)
  integration/                 "Component rendering" and "Other integration" (skill)
  acceptance/                  "Acceptance (full app)": "Full-application tests that visit() routes" (skill)
  helpers/ fixtures/           helpers, pretender server and canned JSON
frontend/discourse/type-tests/ TypeScript/Glint compile-time tests
frontend/asset-processor/*.test.mjs   vitest suite for the build pipeline
test/smoke-test.mjs            Playwright smoke test against a running site URL
migrations/*/spec/             the importer toolkit (a separate sub-project with its own workflow)
```

CI makes the same split by **build type**, not by proof. `.github/workflows/tests.yml` runs ten matrix jobs on every pull request:
- `core backend` and `plugins backend`: all RSpec except system specs, through `bin/turbo_rspec`.
- `core frontend`, `plugins frontend` and `themes frontend`: QUnit through `bin/rake qunit:test`, plus the asset-processor vitest suite.
- `core system`, `plugins (core) system`, `plugins (chat) system`, `plugins (official) system` and `themes system`: the system specs.

The plugin and theme jobs also clone the official plugins and themes that are not bundled. That code is outside this snapshot.

Posture in one sentence: a **Rails-classical, DB-backed "fat middle"**. The broad base is not isolated units. It is in-process RSpec examples against a real PostgreSQL and Redis. Above it sit an HTTP contract layer and a deliberately narrow browser layer for happy-path user flows, and beside all of that a large frontend suite on fakes.

## 2. What the names mean

| Their name | Process | Database | Network | Browser | Nearest post category | Fit |
|---|---|---|---|---|---|---|
| `spec/system` (system specs) | test process plus a Puma server thread in the same process (Capybara default), driven by Playwright | real PostgreSQL inside the test's transaction; real Redis | real HTTP over localhost from Chromium to Puma. Since 2026-06 every other host resolves to NXDOMAIN unless the spec opts in with `allow_network:` | Chromium (desktop and a mobile profile) | e2e | Good. The server is not a separate deployment. It shares the test's DB transaction. |
| `spec/requests` (request specs) | in-process Rack integration session through router and middleware | real PostgreSQL + Redis | none: no socket, and WebMock blocks external hosts | no | api | Fair. The skill says they "drive real HTTP requests", but no TCP server is started. The post's api means a real server over HTTP. |
| `spec/requests/api` (rswag) | same as requests | same | none | no | api | Fair. It also validates schemas and generates the public OpenAPI document. |
| `spec/integration` | in-process; rspec-rails infers `type: :request` for this folder; 18 of 37 core files issue HTTP verbs | real PostgreSQL + Redis | none | no | api, partly unit | Poor. It is a mixed folder of cross-subsystem flows. Its "integration" is not the post's or QUnit's "integration". |
| `models`, `services`, `jobs`, `serializers`, `lib`, small folders | in-process | real PostgreSQL in a rolled-back transaction, real Redis flushed after each example; Sidekiq in fake mode (`Jobs.run_later!`), MessageBus on a memory backend | none (WebMock) | no | no slot. By intent unit; by dependencies adapters_free. | Poor. These are "unit" tests that hit a real database. |
| `spec/multisite` | in-process, switching between two test databases | real PostgreSQL (several DBs) | none | no | no slot | Poor (see section 3). |
| `spec/integrity` | in-process; reads repository files, evaluates JS in mini_racer | mostly none | none | no | tooling | Good. |
| QUnit `unit` | Chrome tab driven by testem / Ember Exam, Ember container | none | XHRs answered by pretender. An unhandled request throws. A Rails server only serves the test page and assets. | headless Chrome | unit | Good, except that it runs in a browser. |
| QUnit `integration` (component rendering) | Chrome; renders single components | none | pretender, sinon | headless Chrome | no slot (nearest fast) | Poor. On fakes, but it is the primary proof for component behaviour, not an extra copy. |
| QUnit `acceptance` | Chrome; boots the whole Ember app and visits routes | none | default pretender server (`create-pretender.js`, a 1,572-line file) plus hand-maintained fixtures (1.1 MB) | headless Chrome | fast | Good by mechanics (everything in one process on in-memory fakes). No written rule calls them an extra copy. |
| `type-tests` | `tsc`/Glint at lint time | none | none | no | tooling | Good. |
| asset-processor `*.test.mjs` | Node (vitest) | none | none | no | tooling | Good. |
| `test/smoke-test.mjs` | Node + Playwright against a site URL | the target site's real DB | real network | Chrome | e2e (post-deploy) | Good, but it is not part of the Tests workflow. It runs through `rake smoke:test` / `script/docker_test.rb`. |
| `migrations/*/spec` | in-process; specs tagged `:rails` boot Discourse and run against PostgreSQL, the rest run without Rails on SQLite intermediate databases | SQLite / PostgreSQL | none | no | unit + adapters_free | A separate sub-project. |

The word "integration" means three different things here. `spec/integration` is request-type RSpec across subsystems. QUnit `integration` is component rendering in a browser on fakes. Sam Saffron's 2019 sentence "the best tests you have are integration tests that cover large amounts of application code" uses the general sense.

## 3. Categories outside the post's taxonomy

1. **Backend in-process tests on a real database** (`models`, `services`, `jobs`, `serializers`, `lib` and the small folders): 423,010 lines with `multisite`, 45.3% of all test code. The post separates pure `unit` tests (need nothing) from `adapters` tests (one adapter against its real dependency). Discourse merges the two. A model spec checks domain logic *and* the SQL it generates, in one example, against PostgreSQL. The reason is Rails' Active Record design: the model *is* the adapter. The project made this cheap rather than avoiding it. Transactional fixtures roll back every example, `fab!` shares records across a group (section 11), and `turbo_rspec` runs the suite in parallel databases. 79.0% of all Ruby test files create rows through `fab!`, `Fabricate` or `create`/`save` (section 6).
2. **QUnit component tests** (`integration`): 134,066 lines, 14.4%. They render one Ember/Glimmer component in a real browser with network fakes. They prove rendering and interaction for one component. The rspec skill names them as the right home for "behavior [that] is local to a component and does not require browser-server integration". The post's taxonomy has no frontend-component layer.
3. **QUnit acceptance tests on a fake server**: 59,711 lines, 6.4%. Mechanically they are the post's `fast` category. Nothing in the project's writing makes them an optional copy, though. They are the historical frontend proof (developer guide, 2016: they "test your application the same way a user would in their browser"). The chat team began replacing them with system specs in 2022 (section 9).
4. **rswag API documentation specs** (`spec/requests/api`): 4,492 lines, 0.5%. Each documented endpoint's request and response is checked against a JSON schema (82 schema files, 472 KB), and the same specs generate `openapi.yaml` for the public API docs (`spec/regenerate_swagger_docs`). They prove a published contract matches the code.
5. **Multisite specs**: 870 lines, 0.1%. Discourse hosts many sites per process. These specs prove that caches, jobs, settings and storage stay per-site. `turbo_rspec` runs them in their own subprocess (`--tag type:multisite`), and three RuboCop cops restrict how they are written.
6. **Data-migration specs** (`spec/db`, `spec/migrations`, plugin `db` specs): 1,590 lines, inside "other backend". They test individual post-deploy data migrations against real tables.
7. **Core-features smoke specs for extensions**: a shared example, "having working core features", defined in `spec/support/shared_examples/core_features.rb` and included by 35 plugin and theme spec files. It runs login, likes, profile, topic and search flows in the browser with the extension enabled. Loïc Guitaut introduced it on 2025-04-11 (meta t/361381): "These specs ensure the plugin or the theme you’re working on doesn’t break the basic functionality of Discourse." These lines are counted under `system`.
8. **Type tests**: 1,167 lines. Compile-time assertions about public TypeScript and Glimmer component signatures. Positive cases must compile, and negative cases in `*-errors-test.gts` files carry `@glint-expect-error` directives, so they fail the check if they ever start compiling. They run in the Linting workflow (`pnpm lint:types`).
9. **Post-deploy smoke test**: 219 lines. One Playwright script that logs in and browses a running site.
10. **Importer toolkit specs** (`migrations/`): 17,987 lines, 1.9%. A separate set of four gems for importing other forums. It has its own workflow (`migration-tests.yml`) and a tag split between specs that do not boot Rails and `:rails` specs. This is the only explicit fast/slow split in the repository.

## 4. Lines per category

All bundled code is included: core, the 45 plugins under `plugins/` and the two themes under `themes/`. Percentages are of the 932,896 test lines, with helpers excluded.

| Category | Lines | % | Files | Tests (static) | Core lines | Plugin lines | Theme lines | Language |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| system (browser e2e) | 64,141 | 6.9 | 632 | 3,967 | 34,914 | 28,937 | 290 | Ruby |
| requests | 130,692 | 14.0 | 394 | 9,258 | 83,330 | 47,362 | 0 | Ruby |
| requests/api (rswag) | 4,492 | 0.5 | 19 | 111 | 4,091 | 401 | 0 | Ruby |
| integration | 16,582 | 1.8 | 128 | 997 | 8,412 | 8,170 | 0 | Ruby |
| models | 68,568 | 7.4 | 334 | 6,219 | 54,418 | 14,150 | 0 | Ruby |
| services | 61,563 | 6.6 | 435 | 6,130 | 31,638 | 29,925 | 0 | Ruby |
| jobs | 25,615 | 2.7 | 267 | 1,781 | 12,727 | 12,888 | 0 | Ruby |
| serializers | 14,597 | 1.6 | 170 | 1,212 | 8,784 | 5,813 | 0 | Ruby |
| lib | 221,057 | 23.7 | 1,279 | 17,470 | 109,519 | 111,538 | 0 | Ruby |
| other backend (small folders) | 30,740 | 3.3 | 235 | 2,195 | 11,528 | 19,212 | 0 | Ruby |
| multisite | 870 | 0.1 | 10 | 43 | 870 | 0 | 0 | Ruby |
| QUnit acceptance | 59,711 | 6.4 | 361 | 2,070 | 40,958 | 18,415 | 338 | JS 55,149 / GJS 4,562 |
| QUnit integration (component) | 134,066 | 14.4 | 638 | 4,669 | 96,862 | 37,153 | 51 | GJS 129,272 / JS 4,794 |
| QUnit unit | 78,516 | 8.4 | 402 | 4,140 | 51,449 | 27,067 | 0 | JS 75,519 / GJS 1,633 / TS 1,364 |
| integrity (tooling) | 627 | 0.1 | 14 | 34 | 553 | 74 | 0 | Ruby |
| asset-processor vitest (tooling) | 1,686 | 0.2 | 11 | 102 | 1,686 | 0 | 0 | JS (.mjs) |
| type tests | 1,167 | 0.1 | 33 | n/a | 1,167 | 0 | 0 | GTS 986 / TS 181 |
| smoke (post-deploy) | 219 | 0.0 | 1 | n/a | 219 | 0 | 0 | JS (.mjs) |
| importer toolkit (`migrations/`) | 17,987 | 1.9 | 121 | 1,528 | n/a | n/a | n/a | Ruby |
| **All test code** | **932,896** | 100 | **5,484** | **61,926** | | | | Ruby 657,531 (70.5%), JS/GJS/TS 275,365 (29.5%) |
| *Helpers (excluded)* | *38,413* | | *734* | | | | | page objects 20,547; QUnit helpers and boot files 6,703; spec/support 6,396; fabricators 2,926; other 1,841 |

Test counts are static greps: RSpec `it`/`specify`/`scenario` lines, rswag `response "NNN"` blocks, QUnit `test(`/`skip(` plus `conditionalTest`/`chromeTest`/`firefoxTest`, vitest `test(`/`it(`. They undercount generated examples. There are 1,056 `it_behaves_like`/`include_examples` lines, and the core-features shared example alone expands into each of 35 files. QUnit files also contain 2,223 `module(`/`acceptance(` calls.

Without the importer toolkit, which is a separate sub-project, the product's test code is 914,909 lines. Shares then shift by at most 0.5 points, for example lib 24.2% and requests 14.3%. The tooling, type-test and smoke rows are included in the whole above. Together they are 0.4%.

**Test data, excluded from the lines.** `spec/fixtures`: 449 files, about 19 MB (emails, images, HTTP responses, SQL, YAML). `frontend/discourse/tests/fixtures`: 37 JS modules of canned JSON, 1.1 MB, 28,775 code lines by the tool. Plugin fixtures: 43 files, about 1.4 MB. rswag JSON schemas: 82 files, 472 KB. The code-file part of this data (95 files, 30,633 lines) carries the category `data` in the CSV.

The same shape, grouped like the Robinauts chart:

| Band | Lines | % |
|---|---:|---:|
| e2e (system) | 64,141 | 6.9 |
| api (requests, rswag, spec/integration) | 151,766 | 16.3 |
| backend in-process on real PostgreSQL/Redis (no slot) | 423,010 | 45.3 |
| frontend acceptance on a fake server (≈ fast) | 59,711 | 6.4 |
| frontend component tests on fakes (no slot) | 134,066 | 14.4 |
| frontend unit | 78,516 | 8.4 |
| tooling (integrity, vitest, type tests) | 3,480 | 0.4 |
| smoke (post-deploy) | 219 | 0.0 |
| importer toolkit | 17,987 | 1.9 |

## 5. Test-to-code ratio

Production code is defined as follows:
- Ruby (`.rb`, `.rake`) in `app/`, `lib/` and `config/`, and in `plugins/*` outside `spec/`, `test/` and `db/`.
- JavaScript/TypeScript/Glimmer in `frontend/discourse/{app,admin,select-kit,float-kit,truth-helpers,dialog-holder}`, `frontend/{pretty-text,discourse-markdown-it,pretty-text-processor,discourse-i18n,asset-processor}`, plugin assets and the bundled themes.

Excluded: `db/` (migrations and seeds, 26,023 lines), `plugins/*/db` (15,352), `script/` (importers and benchmarks, 47,781), `.erb` view templates (4,395), frontend build configuration (2,199), type generators and build shims (495), stylesheets, YAML, and vendored code (the tool's default `vendor` exclusion). Backend production: 366,728 lines (core 197,080, plugins 169,648). Frontend production: 471,089 lines (core 295,798, plugins 174,180, themes 1,111). Whole product: 837,817.

| Test category | Mapped production | Test lines | Prod lines | Ratio |
|---|---|---:|---:|---:|
| requests (+ rswag) | controllers: `app/controllers` + `plugins/*/app/controllers` | 130,692 (135,184) | 35,468 | 3.68 (3.81) |
| models | `app/models` (core + plugins) | 68,568 | 49,832 | 1.38 |
| services | `app/services` | 61,563 | 36,591 | 1.68 |
| jobs | `app/jobs` + plugin `jobs/` | 25,615 | 14,848 | 1.73 |
| serializers | `app/serializers` | 14,597 | 14,306 | 1.02 |
| lib | `lib/` (core + plugins) | 221,057 | 192,823 | 1.15 |
| all backend RSpec except system | backend production | 575,403 | 366,728 | 1.57 (core 1.65, plugins 1.47) |
| system | **whole product** (spans backend and frontend) | 64,141 | 837,817 | 0.08 |
| QUnit component tests (509 files under `components/`) | frontend `components/` directories | 86,816 | 236,301 | 0.37 |
| QUnit unit | frontend outside `components/` | 78,516 | 234,788 | 0.33 |
| QUnit acceptance | **whole frontend** | 59,711 | 471,089 | 0.13 |
| all QUnit | frontend production | 272,293 | 471,089 | 0.58 (core 0.64, plugins 0.47) |
| all tests except importer toolkit | whole product | 914,909 | 837,817 | 1.09 |
| importer toolkit | `migrations/` production | 17,987 | 20,918 | 0.86 |

The backend carries about 1.6 lines of test per line of code. The frontend carries about 0.6. The request-spec ratio is the highest. *Inference:* one controller action is exercised through many permission and parameter cases, and each case builds its own records.

## 6. Detroit or London

**Heuristic.** Ruby has no import line for mocks, because Mocha and rspec-mocks are loaded globally in `spec/support/mocks.rb` through `rspec-multi-mock`. So "a file that uses a mocking facility" means a file with at least one call site. The patterns, applied per file:

- Mocha: `\.(stubs|expects)\(|\bstub_everything\b`
- rspec-mocks: `\breceive(_messages|_message_chain)?\(|\bhave_received\(|\b(instance_|class_|object_)?(double|spy)\(|\bstub_const\(`
- WebMock (network-boundary stubs, reported separately): `\bstub_request\(`
- Creates DB rows: `\bfab!\(|\bFabricate\(|\.create!?\(|\.update!?\(|\.save!?\b|\bDB\.(exec|query|query_single)\b`
- QUnit sinon: `\bsinon\.\w+\(` call sites; a file counts if it has a call site or `from "sinon"`
- QUnit pretender route definitions: `\b(server|pretender)\.(get|post|put|delete|patch)\(|\bneeds\.pretender\(`

| Category | Files with object mocks | Object-mock sites / 1k lines | Files with WebMock | WebMock / 1k | Files creating DB rows |
|---|---:|---:|---:|---:|---:|
| system | 6.2% | 1.4 | 2.2% | 0.6 | 91.8% |
| requests | 25.9% | 5.1 | 9.1% | 1.1 | 95.9% |
| requests/api (rswag) | 15.8% | 3.1 | 5.3% | 0.2 | 100% |
| integration | 14.1% | 1.4 | 10.2% | 2.1 | 85.9% |
| models | 21.6% | 5.4 | 2.7% | 0.9 | 84.1% |
| services | 32.6% | 10.9 | 2.8% | 1.0 | 86.4% |
| jobs | 41.9% | 30.5 | 8.6% | 3.3 | 89.9% |
| serializers | 11.8% | 4.5 | 0% | 0 | 97.6% |
| lib | 24.8% | 9.7 | 12.0% | 4.6 | 58.4% |
| other backend | 20.9% | 9.9 | 2.1% | 0.8 | 81.7% |
| multisite | 30.0% | 33.3 | 0% | 0 | 60.0% |
| integrity | 7.1% | 1.6 | 0% | 0 | 0% |
| **all product RSpec** | **22.4%** | **8.1** | **6.8%** | **2.3** | **79.0%** |
| importer toolkit | 35.5% | 23.6 | 0% | 0 | 10.7% |

Mocha accounts for 3,220 of the 5,168 product call sites and rspec-mocks for 1,948.

| QUnit category | Files using sinon | sinon sites / 1k | Files defining pretender routes | Route definitions / 1k |
|---|---:|---:|---:|---:|
| acceptance | 9.4% | 0.8 | 66.2% | 21.2 |
| integration (component) | 11.6% | 2.4 | 20.8% | 3.3 |
| unit | 16.7% | 4.2 | 11.9% | 2.4 |
| all QUnit | 12.5% | 2.6 | 30.0% | 7.0 |

**Real dependencies.**
- **Every RSpec example** runs inside a PostgreSQL transaction (`use_transactional_fixtures = true`) and uses a real Redis, which `rails_helper.rb` flushes after each example.
- **System specs** additionally start a real Puma server and a real Chromium. The core system job adds a MinIO service container for 3 S3 spec files (`setup_or_skip_s3_system_test`).
- **No QUnit test** reaches a database. Every acceptance test runs on the default pretender server even when its file defines no routes, so 100% of acceptance tests are on a fake backend.

**What gets mocked.** The most frequent Mocha receivers are environment and configuration objects (`SiteSetting` 121, `Discourse` 110, `GlobalSetting` 40) and external services:
- Stripe classes (about 80 call sites across `Stripe::*`),
- AI translation detectors (`DiscourseAi::Translation::*`, about 100),
- `Oneboxer`, `FileHelper`, `DiscourseIpInfo`, S3.

The most frequent WebMock hosts are `api.openai.com` (52), `api.github.com` (46) and `slack.com` (33). The AI plugin also has an in-house fake LLM (`with_prepared_responses`, 517 call sites in 72 files). Internal collaborators do get mocked too (`Guardian.any_instance` 28, `Post.any_instance` 17, `PostAlerter` 16). Jobs specs are the most London-leaning folder, at 30.5 sites per 1,000 lines.

Reading: Discourse sits near the **Detroit end** in every category. About three quarters of Ruby test files mock nothing: 73.2% have neither an object mock nor a WebMock stub. Most mocks sit at configuration or network boundaries. The project builds tracking helpers so tests can assert outcomes instead of calls: `DiscourseEvent.track_events` in 89 files, `MessageBus.track_publish` in 154, `expect_enqueued_with` in 95. The system layer is the most realistic (6.2% of files mock anything). The frontend is the exception by design: QUnit's network is always a fake.

## 7. The web UI

**Both.** Two frameworks test the Ember UI:

1. **QUnit (ember-qunit, @ember/test-helpers, qunit-dom) in headless Chrome**, on pretender and sinon fakes: 272,293 lines in 1,401 files. CI jobs: `core frontend` (5 min 58 s at the snapshot commit), `plugins frontend` (6 min 4 s) and `themes frontend` (1 min 48 s), all through `bin/rake qunit:test` → `bin/qunit --standalone`. That command starts a test-mode Rails server only to serve the test page and assets.
2. **RSpec system specs (Capybara over Playwright/Chromium) against the real Rails app, PostgreSQL and Redis**: 64,141 lines in 632 files, plus 20,547 lines of page objects. CI jobs at the snapshot commit: `core system` (11 min 23 s on a 16-core runner), `plugins (core) system` (8 min 47 s), `plugins (chat) system` (9 min 10 s), `plugins (official) system` (5 min 7 s) and `themes system` (7 min 20 s). Job run time across the whole Tests run was 1 h 14 min 29 s, and wall time 11 min 41 s (run 38125724506).

**Which one is the proof.** Since 2022 the written direction treats system specs as the proof of a user flow:
- The chat team: "We are all in on system specs" (Martin Brennan, PR #19434, December 2022).
- The theme testing guide: "This document will focus on writing Rails system tests for themes and is what we recommend theme authors focus on when writing tests for their themes as well." (2023-10-24)
- Plugins and themes get the core-features smoke specs (2025).

The rspec skill limits system specs to "one system test per user flow" and sends component-local behaviour to QUnit:

> Use a QUnit component test instead when the behavior is local to a component and does not require browser-server integration.

QUnit acceptance tests are still a large, live suite (361 files). The plugin tutorial on meta still teaches them. **What they prove:** the Ember application renders and reacts correctly *given* the JSON a hand-written pretender route or fixture returns. They do not prove that the server returns that JSON.
- Unhandled requests fail the test (`pretender.unhandledRequest` throws "Unhandled request in test environment"), so a test cannot quietly fall through to the real server.
- Nothing checks the canned fixtures against the serializers, apart from one generated module: `rake javascript:update_constants` writes notification types into `tests/fixtures/concerns/notification-types.js`.
- The only schema-checked JSON contract is the rswag set, which covers documented API endpoints, not the payloads the Ember app consumes.

No written rule says whether a behaviour proved in a system spec should also have a QUnit acceptance test, or the reverse. Where both exist, the overlap is ungoverned.

## 8. Enforcement by machine

| Mechanism | What it checks | Where | Added |
|---|---|---|---|
| WebMock `disable_net_connect!(allow_localhost: true)` | any Ruby test that reaches a non-local host fails | `spec/rails_helper.rb` | 2017-05-26, Alan Tan, commit 56f98de ("Use webmock to stub external web requests.") |
| Chrome `--host-resolver-rules` with `MAP * ~NOTFOUND`, `allow_network:` opt-in | the browser in system specs cannot reach the internet | `spec/support/system/driver.rb` | 2026-06-17, David Taylor, PR #40685 |
| pretender `unhandledRequest` throws | a QUnit test that makes an XHR with no fake route fails | `frontend/discourse/tests/setup-tests.js` | in place by 2016 (a fix for "Unhandled request /tag_groups" is dated 2016-07-05); pretender itself adopted 2014-07-31 (commit d3cc85c). Origin commit not found. |
| Re-raise of a Capybara finder timeout after a passing example | a system spec that passed but waited the full Capybara timeout at least once fails | `spec/rails_helper.rb` (`_capybara_timeout_exception`) | 2023-08-08, David Taylor, PR #22686 |
| Per-spec timeout (45 s on CI) with thread backtraces | hung examples fail | `spec/support/ci.rb` | 2023-05-19, Jarek Radosz, PR #21648; raised to 45 s 2023-12-08 (#24798); backtraces 2024-01-22 (#25356) |
| Ember deprecations raise | QUnit and system specs fail on a deprecation for core and preinstalled plugins/themes | `EmberDeprecations` in `rails_helper.rb`, `tests/helpers/raise-on-deprecation.js` | extended to preinstalled plugins and themes 2025-12-16, PR #36445 (David Taylor, Jarek Radosz); the earlier core-only start was not dated |
| Retry-and-log flaky tests | if 10 or fewer examples fail, they are rerun once; examples that pass on rerun are logged as flaky and the build passes; more than 10 failures are never retried | `bin/turbo_rspec`, `lib/turbo_tests/flaky/`, `tests.yml` | 2023-12-12, Alan Tan, PR #24811; the "more than 10" rule 2023-12-26 (#25031); reports pushed to the Patch Triage bot 2026-09-07 (#43250) |
| Pending-migration check | the suite refuses to run with pending migrations | `spec/support/suite_setup.rb`, `lib/turbo_tests/runner.rb` | turbo runner check 2019-06-27 (Daniel Waterworth, "DEV: Check for pending migrations before starting the turbo tests") |
| CI-only BIGINT widening | foreign keys referencing BIGINT columns get sequences above the INT range, so type mismatches fail | `spec/support/suite_setup.rb` | date not found |
| `turbo_rspec` excludes `spec/system` by default | the default local and backend run stays fast; system specs need an explicit path or flag | `bin/turbo_rspec` | 2022-09-28, PR #16311 |
| RuboCop cops from `rubocop-discourse` on `**/spec/**` | `Discourse/NoMockingJobs` (no `Jobs.expects(:enqueue)`, use Sidekiq helpers); `TimeEqMatcher`; `NoDirectMultisiteManipulation`, `OnlyTopLevelMultisiteSpecs`, `NoMixingMultisiteAndStandardSpecs`; `NoSystemSpecMetadata`; RSpec cops such as `ExampleWording` (bans "works", "succeeds" ...), `RepeatedDescription`; local `RSpec/InstanceVariable` for `spec/models`; `Lint/Debugger` flags a leftover `pause_test` | `rubocop-discourse` config, `.rubocop.yml`; run in the Linting workflow and the lefthook pre-commit hook | `NoMockingJobs` 2020-07-15 (Alan Tan, rubocop-discourse f80bc08); others not dated |
| ESLint (`@discourse/lint-configs`) | `eslint-plugin-qunit` recommended rules, `qunit/no-loose-assertions`, `discourse/test-filename-suffix` (files under `tests/{acceptance,integration,unit}` must end in `-test`) | `eslint.config.mjs` → `@discourse/lint-configs` | not dated |
| Type tests in `pnpm lint:types` (`ember-tsc -b`) | positive signature cases compile; negative cases marked `@glint-expect-error` must keep failing | Linting workflow | not dated |
| `spec/integrity` | post-migration drops use the `DROPPED_*` constants; no non-colocated component templates; i18n keys; JS constants equal Ruby constants | RSpec, core backend job | not dated |
| CI checks around the suite | model annotations up to date, `structure.sql` up to date, Zeitwerk reload works, the app boots with `SKIP_DB_AND_REDIS=1` | `tests.yml` backend jobs | not dated |

What does **not** exist:
- No CI guard against skipped tests. The system-specs guide recommends "Use `skip` or `xit` for tests that are known to be flaky in CI environments", and the snapshot has 56 `skip`/`xit` lines in RSpec.
- No labels that widen the test run. `labeler.yml` only labels by plugin, and every pull request runs the full ten-job matrix.
- No coverage gate (section 12).
- No machine check that a behaviour is tested in exactly one place. The "each layer asserts what it owns" rule is enforced by review and by the agent skill only.

## 9. History

**2013–2014: the base is set.** The backend used RSpec from the start. Sam Saffron wrote in 2019 that "from the very early days of Discourse we opted to run our tests in random order". In June 2013 Robin Ward replaced Jasmine with QUnit for the Ember app ("Experiment: QUnit for integration Ember integration tests", 2013-06-12; "Migrate all jasmine specs to Qunit. Removed Jasmine.", 2013-06-19). In July 2014 he introduced pretender "for more flexible server responses" (commit d3cc85c, 2014-07-31). That gave the frontend the fake-server design it still has. In November 2014 Sam Saffron wrote the anti-mock rule into the contribution guidelines.

**2017: brittle mocks and an unstable suite.**
- Alan Tan replaced Mocha expectations on `DiscourseEvent.trigger` with a tracking helper, because the mocks failed whenever an unrelated event fired.
- WebMock was configured to block the network.
- Sam Saffron removed the Timecop gem after "3 days of an unstable test suite", writing `freeze_time` on top of Mocha so it would always clean up.
- Travis was distrusted ("flaky and slow").

The first three changes push the same way: fewer test-only mechanisms, more outcome assertions.

**2017–2018: request specs replace controller specs.** Between 2017-10-02 ("Remove controller spec that is rewritten as request spec.", Alan Tan) and 2018-06-11 (the last `spec/controllers` commit, a run of "REFACTOR: ... controller specs to requests" commits by Osama Sayegh merged by Alan Tan), every controller spec was rewritten as a request spec. No commit or meta post found states the reason. One commit body (2018-05-07, push notifications) says the rewrite improved assertions to "test for the outcome we expected instead" of only checking for a 200 response. *Inference, not stated by the project:* the move followed the general Rails 5 advice. The RSpec 3.5 release post (July 2016) says: "The official recommendation of the Rails team and the RSpec core team is to write request specs instead." It gives the reason that request specs "involve the router, the middleware stack, and both rack requests and responses". The project's own words today are in the skill: "Make real HTTP calls — don't stub the controller".

**2019: speed and flakiness as one problem.** Sam Saffron's post "Tests that sometimes fail" (2019-05-28) describes the state:
- a team "game" that assigned each flaky failure to the test's author,
- a catalogue of "heisentests",
- Roman Rizzi's system that reran the suite in a loop on a cloud server and quarantined flaky specs.

The same year Daniel Waterworth added `fab!` (TestProf's `let_it_be`, about 10% faster) and `bin/turbo_rspec`. David Taylor had added `parallel_tests`. The suite had "11,000 or so Ruby tests", taking 5 min 40 s single-threaded and 1 min 15 s in parallel. Throughout, the DB-backed integration style was defended rather than abandoned: "the best tests you have are integration tests that cover large amounts of application code". In December 2019 CI moved from Travis to GitHub Actions (PR #8441). A smoke test was added to Actions on 2020-01-07 and reverted the next day: "This is proving unreliable, so removing for now".

**2022: system specs.** Martin Brennan opened PR #16311 in March 2022, and it merged on 2022-09-28 with Selenium and headless Chrome. It was scoped narrowly from day one: happy paths only, excluded from `turbo_rspec` by default. In November and December the chat plugin, then being rebuilt, converted its JS acceptance tests to system specs "to ensure as little regressions as possible while changing paradigm" (Joffrey Jaffeux, #19531). Martin Brennan then declared "We are all in on system specs" (#19434). The steer took hold: system specs grew to 632 files and 3,967 static examples at the snapshot, split almost evenly between core (296 files) and plugins (331).

**2023: the bill for flakiness.** System specs made CI flaky enough that developers merged real failures, assuming flakes (PR #24811). The response was machinery:
- per-spec timeouts (May),
- failing a spec whose finder waited out the full timeout (August),
- automatic rerun of up to 10 failures with flaky logging (December),
- since then, a steady stream of fixes: 589 commits in the repository mention "flaky", and the ten most recent of them date from 2026-09-07 to 2026-10-08.

The steer to system specs held. It did not get cheaper.

**2024–2026: infrastructure and codification.**
- rspec-mocks was enabled next to Mocha, between the v3.3.0 tag (2024-07-30) and the v3.4.0 tag (2025-02-04; tag years inferred); the commit was not found.
- Selenium was replaced by Playwright (#31977, 2025-05-06).
- 30 official plugins moved into the core repository (July 2025), so "it'll be easier for us to keep them all tested & up-to-date" (David Taylor).
- Deprecations became test failures (December 2025).
- The browser was cut off from the internet (June 2026).
- The testing guidance was written down as agent skills (May–July 2026).
- Flaky-test reports are now pushed to an internal bot, Patch Triage (September 2026).

Did the steers succeed?
- The anti-mock steer did: 73% of Ruby test files mock nothing.
- The request-spec steer did: no controller specs remain.
- The system-spec steer did by volume, at the cost of a permanent flakiness programme.
- No before-and-after flaky rates were found in public sources.

## 10. Timeline

| Date | What changed | Who | Link |
|---|---|---|---|
| 2013-06-12 → 06-19 | Jasmine replaced by QUnit for the Ember app | Robin Ward | commits a104c37, 8c4aac7 |
| 2013 (by the v0.9.0 tag, 10 May; year inferred) | SimpleCov available behind `COVERAGE=1`, never in CI | not found | `spec/spec_helper.rb` at v0.9.0 |
| 2014-07-31 | pretender fake server for JS tests | Robin Ward | commit d3cc85c |
| 2014-11-02 | "Mocking is heavily discouraged" added to the contribution guidelines | Sam Saffron | meta t/3823 revision 30 |
| 2017-05-26 | WebMock blocks real network in RSpec | Alan Tan | commit 56f98de |
| 2017-06-01 | `DiscourseEvent` tracking helper replaces Mocha expectations | Alan Tan | meta t/63729 |
| 2017-07-25 | Timecop removed; `freeze_time` on Mocha | Sam Saffron | meta t/66773 |
| 2017-10-02 → 2018-06-11 | controller specs rewritten as request specs | Alan Tan, Osama Sayegh | github.com/discourse/discourse/commits/main/spec/controllers |
| 2019 (early) | flaky "game", heisentest catalogue, continuous rerun and quarantine | Sam Saffron, Roman Rizzi | samsaffron.com/archive/2019/05/15/tests-that-sometimes-fail |
| 2019-04-01 | SimpleCov re-added as a test dependency (opt-in) | Gerhard Schlager | PR #7271 |
| 2019-05-07 | `fab!` (prefabrication via TestProf `let_it_be`) | Daniel Waterworth | PR #7414 |
| 2019-06-21 | `bin/turbo_rspec` parallel runner | Daniel Waterworth | PR #7778 |
| 2019-12-10 | CI on GitHub Actions | Joffrey Jaffeux, David Taylor | PR #8441 |
| 2020-07-15 | RuboCop cop forbids mocking `Jobs.enqueue` | Alan Tan | discourse/rubocop-discourse f80bc08 |
| 2022-09-28 | Rails system specs (Selenium) | Martin Brennan, David Taylor | PR #16311 |
| 2022-12-21 / 12-23 | chat converts JS acceptance tests to system specs; "all in on system specs" | Joffrey Jaffeux; Martin Brennan | PRs #19531, #19434 |
| 2023-05-19 | per-spec timeout on CI | Jarek Radosz | PR #21648 |
| 2023-08-08 | spec fails if a Capybara finder waited the full timeout | David Taylor | PR #22686 |
| 2023-10-24 | theme guide recommends system tests | Discourse docs | meta t/281579 |
| 2023-12-12 | automatic rerun and flaky-test logging | Alan Tan | PR #24811 |
| 2024-07-30 → 2025-02-04 | rspec-mocks enabled alongside Mocha | not found | `spec/rails_helper.rb` at v3.3.0 and v3.4.0 |
| 2025-04-11 | core-features smoke specs for plugins and themes | Loïc Guitaut | meta t/361381 |
| 2025-05-06 | Playwright replaces Selenium | Joffrey Jaffeux | PR #31977 |
| 2025-07-10 | popular plugins bundled into the core repository | David Taylor | meta t/373574 |
| 2025-10-22 | `app/assets/javascripts` → `frontend/` (preparation commit) | David Taylor | commit e56a4bf |
| 2025-12-16 | deprecation-free tests enforced for core and preinstalled extensions | David Taylor, Jarek Radosz | PR #36445 |
| 2026-06-17 | browser in system specs blocked from external hosts | David Taylor | PR #40685 |
| 2026-07-10 | agent skill: "each layer asserts what it owns", public-boundary assertions | Alan Tan | PR #41611 |
| 2026-09-07 | flaky-test reports pushed to Patch Triage | Alan Tan | PR #43250 |

## 11. The arguments, turn by turn

Quotes from GitHub were read through a page-fetching tool that returns excerpts. Excerpts are marked "…" where a sentence continues.

**Mocks out, outcomes in (2014–2017).**

> Mocking is heavily discouraged. Only use mocking when absolutely critical.
> (Sam Saffron, contribution guidelines, meta t/3823 rev. 30, 2014-11-02)

> However, these mocks make test cases super brittle because the test case would fail when another `DiscourseEvent` that is not "expected" is triggered. As a result, the developer would have to mock every single `DiscourseEvent` trigger that would trigger even if he is only concerned about testing a single trigger.
> (Alan Tan, meta t/63729, 2017-06-01)

> The catalyst for the change was 3 days of an unstable test suite, caused by misuse of the Timecop library.
> (Sam Saffron, meta t/66773, 2017-07-25)

> Additionally, Discourse uses mocha for all object mocking. You end up having 2 mocking libraries and if you mock `Time` with with both you can very quickly get very unexpected results.
> (Sam Saffron, same post)

No counter-argument was found. The numbers that moved are indirect. The tracking helpers are used in 89 (`track_events`) and 154 (`track_publish`) spec files today. The "single mocking library" position was later reversed: rspec-mocks now accounts for 1,948 of 5,168 product call sites. No rationale was found for that reversal.

**Controller specs → request specs (2017–2018).** No argument was found in commits, pull requests or meta. The one stated benefit is in a commit body: the rewrite let assertions "test for the outcome we expected instead" of only a 200 status (Alan Tan, 2018-05-07, found through GitHub commit search). Result: zero controller specs remained after 2018-06-11. At the snapshot there are 394 request-spec files, the second-largest backend category by lines.

**`fab!` (2019).** Review of PR #7414 weighed speed against authoring cost and test isolation:

> This PR makes the tests ~10% faster, but there are still many unexploited opportunities to apply this.
> (Daniel Waterworth, PR #7414, 2019-04-23)

> I worry that the new syntax makes it harder for people to author tests.
> (Sam Saffron, PR #7414, 2019-04-23)

> My biggest concern here is the potential for this to introduce leaky state / bugs
> (Robin Ward, PR #7414, 2019-04-23)

> Nice I ran this locally and saw a speed up of about 50 seconds from 9mins 32 seconds.
> (Alan Tan, PR #7414, 2019-04-23)

> 6:06s down from 7:10s for 11146 specs this is not too shabby at all, awesome work!
> (Sam Saffron, PR #7414, 2019-05-07)

Daniel Waterworth also reported test-prof figures: total factory usage fell from 22,773 to 17,205 objects. The leaky-state concern has stayed live. Two RuboCop cops exist because mixing multisite and standard specs "can lead to errors, e.g. when using `fab!` helper", and the agent skill warns that `fab!` "cannot depend on `let` or other per-example setup". Today `fab!` appears 16,189 times in 2,636 spec files.

**Parallelism (2019).** Daniel Waterworth's turbo runner "makes each subprocess use a machine-readable formatter and parses this output in order to provide a better overall summary" (PR #7778). Sam Saffron: "From my perspective this is how "parallel tests" should work". His post gives the effect of parallel tests:

> At the moment Discourse has 11,000 or so Ruby tests it takes them 5m40s to run single threaded on my PC and 1m15s or so to run tests concurrently.
> (Sam Saffron, "Tests that sometimes fail", 2019-05-28)

The same post states the trade-off the project chose:

> For years at Discourse we have invested in speeding up our test suite. There is a balancing act though, on one hand the best tests you have are integration tests that cover large amounts of application code. You do not want the quest for speed to compromise the quality of your test suite.

and its flaky-test policy:

> At Discourse we opted to quarantine and fix. Though to be completely honest, at some points we ignored and we considered just deleting.

**System specs (2022).** The introducing commit framed system specs as expensive and therefore narrow:

> For system tests, since they are so slow, we want to focus on the "happy path" and not do every different possible context and branch check using them.
> (Martin Brennan, PR #16311, merged 2022-09-28)

> I have modified `bin/turbo_rspec` to exclude `spec/system` by default, support for parallel system specs is a little shaky right now and we don't want them slowing down the turbo by default either.
> (same)

The chat rewrite made them the safety net:

> converting (and adding new) existing js acceptances tests into system tests. … This change was necessary to ensure as little regressions as possible while changing paradigm
> (Joffrey Jaffeux, PR #19531, 2022-12-21)

> We are all in on system specs, so this commit moves all the chat quoting acceptance tests (some of which have been skipped for a while) into system specs.
> (Martin Brennan, PR #19434, 2022-12-23)

No published argument for keeping QUnit acceptance tests as the frontend proof was found. Numbers: 632 system spec files and 3,967 static examples at the snapshot. Chat alone has its own CI job of 9 min 10 s. Historical counts were not measured, because the GitHub API was not available to this session.

**Flakiness becomes machinery (2023).**

> If a selenium finder takes the full wait duration to resolve, that means it has been written inefficiently.
> (David Taylor, PR #22686, 2023-08-08)

> Our builds on Github actions have been extremely flaky mostly due to system tests. … This has led to a drop in confidence in our test suite … developers tend to assume that a failed job is due to a flaky system test … changes that resulted in legitimate test failures are merged into the `main` branch
> (Alan Tan, PR #24811, 2023-12-11)

> … lower accuracy of our tests but we accept this as an acceptable trade-off … a fragile build has a much greater impact on our developers' time
> (same)

In review, Dave McClure reported that chat system tests hit the 10-failure threshold ("Retry and log flaky tests was enabled but ignored because there are more than 10 failures"). No flaky-rate numbers before or after were published. The only signal is the volume of commits that mention "flaky": 589 in total, the ten most recent between 2026-09-07 and 2026-10-08.

**Playwright (2025).** The pull request states what changed, not why: "This commit is replacing the system specs driver (selenium) by Playwright" (Joffrey Jaffeux, PR #31977, opened 2025-03-24, merged 2025-05-06). The trade-offs it records are operational: `fill_in` no longer generates key events, and the `CHROME_DEV_TOOLS` option was removed ("use `pause_test` and inspect browser for now"). No timing comparison was found.

**Plugins into core (2025).**

> Over the next few weeks, we'll be moving a number of popular Discourse plugins into the core repository. That means that Discourse will come with a larger number of plugins by default, and it'll be easier for us to keep them all tested & up-to-date.
> (David Taylor, meta t/373574, 2025-07-10)

Numbers: plugin test code is now 361,105 of the 932,896 measured test lines (38.7%; 39.5% of the product's tests without the importer toolkit). The backend `lib` category is split almost exactly in half between core and plugins.

**Codifying placement (2026).** PR #41611 (Alan Tan, 2026-07-10) added "public-boundary and test-layer guidance so specs assert behavior owned by the layer under test" and "fabricator, system-test cost, deterministic transient-state, URL, and page-object guidance to reduce brittle tests". It is too recent for any measured effect.

## 12. Coverage

**Measured: only on demand. Gated: never, as far as the public record shows.**

- `spec/rails_helper.rb` starts SimpleCov only when `COVERAGE` is set, with Rails groups for libraries, scripts, serializers, services and tasks. No workflow in `.github/workflows/` sets `COVERAGE`. No JavaScript coverage tool is configured (`grep -i coverage` over `package.json`, `testem.js`, workflows and rake tasks finds nothing relevant).
- History:
  - The `if ENV['COVERAGE']` block is in `spec/spec_helper.rb` at the v0.9.0 tag (tagged 10 May; 2013 inferred) and in every tag checked through v1.2.0.
  - `simplecov` was in the Gemfile through v1.6.0 and absent at v1.7.0, v1.8.0, v2.0.0, v2.1.0 and v2.2.0, so it was dropped in 2016.
  - It was re-added on 2019-04-01 ("DEV: Add simplecov as test dependency", Gerhard Schlager, PR #7271).
  - `.travis.yml` at the tags checked (v0.8.0 to v2.2.0) has no coverage step.
  - The GitHub Actions workflow (`ci.yml` at v2.5.0, `tests.yml` at v2.8.0, v3.0.0, v3.2.0 and v3.4.0) has none either.
- From 2013 to at least v1.8.0 (2017) the README carried a Code Climate badge. *Inference:* it was the maintainability badge, not a coverage badge. The badge URL is the plain repository badge, and no Code Climate test reporter appears in the Gemfile or `.travis.yml` at those tags.
- Meta searches for "code coverage", "test coverage" and `COVERAGE=1` returned no team post on the subject.
- The importer toolkit's "converter coverage" check (`disco check` in `migration-tests.yml`) checks that import converters cover the target schema's columns. It is not code coverage.

## Chart-ready table

| category | maps_to (post taxonomy) | lines | pct | files | tests |
|---|---|---:|---:|---:|---:|
| system | e2e | 64141 | 6.9 | 632 | 3967 |
| requests | api (in-process, no socket) | 130692 | 14.0 | 394 | 9258 |
| requests_api_docs (rswag) | api + docs (outside taxonomy) | 4492 | 0.5 | 19 | 111 |
| integration (spec/integration) | api / mixed (poor fit) | 16582 | 1.8 | 128 | 997 |
| models | none: DB-backed unit (unit + adapters_free) | 68568 | 7.4 | 334 | 6219 |
| services | none: DB-backed unit | 61563 | 6.6 | 435 | 6130 |
| jobs | none: DB-backed unit | 25615 | 2.7 | 267 | 1781 |
| serializers | none: DB-backed unit | 14597 | 1.6 | 170 | 1212 |
| lib | none: DB-backed unit | 221057 | 23.7 | 1279 | 17470 |
| other_backend | none: DB-backed unit | 30740 | 3.3 | 235 | 2195 |
| multisite | none (multi-tenant) | 870 | 0.1 | 10 | 43 |
| qunit_acceptance | fast (by mechanics; not declared an extra copy) | 59711 | 6.4 | 361 | 2070 |
| qunit_integration (component) | none: frontend component on fakes (nearest fast) | 134066 | 14.4 | 638 | 4669 |
| qunit_unit | unit | 78516 | 8.4 | 402 | 4140 |
| integrity | tooling | 627 | 0.1 | 14 | 34 |
| tooling_vitest (asset-processor) | tooling | 1686 | 0.2 | 11 | 102 |
| type_tests | tooling (type-level) | 1167 | 0.1 | 33 | 0 |
| smoke | e2e (post-deploy) | 219 | 0.0 | 1 | 0 |
| migrations_toolkit | separate sub-project (unit + adapters_free) | 17987 | 1.9 | 121 | 1528 |

## Sources

1. discourse/discourse at 008b5fc (2026-10-11): `spec/rails_helper.rb`, `spec/support/{prefabrication,ci,mocks,test_setup,suite_setup,server_error_tracking}.rb`, `spec/support/system/driver.rb`, `bin/turbo_rspec`, `lib/turbo_tests/`, `bin/qunit`, `frontend/discourse/testem.js`, `frontend/discourse/tests/setup-tests.js`, `lib/tasks/{qunit,javascript}.rake`, `.github/workflows/{tests,linting,migration-tests}.yml`, `.rubocop.yml`, `lefthook.yml`, `Gemfile`. https://github.com/discourse/discourse/tree/008b5fc4585ca178bf10642d3da1dcc39e2ace50 (2026-10-11)
2. `.skills/discourse-writing-rspec-tests/SKILL.md` and `references/*.md`; `.skills/discourse-writing-js-tests/SKILL.md`; `AGENTS.md` (snapshot, 2026-10-11)
3. Developer guide "Write end-to-end system specs for the Discourse user interface", `docs/developer-guides/docs/03-code-internals/21-system-specs.md` = https://meta.discourse.org/t/325937 (created 2024-09-11, revision 12, 2026-10-09)
4. "End-to-end system testing for themes and theme components", https://meta.discourse.org/t/281579 (2023-10-24)
5. "Write acceptance tests and component tests for Ember code in Discourse", https://meta.discourse.org/t/49167 (2016-08-24); "How to run Discourse core, plugin and theme QUnit test suites", `docs/developer-guides/docs/03-code-internals/05-run-test-suites.md` (snapshot)
6. "Contributing to Discourse development", https://meta.discourse.org/t/3823, revision 30 by Sam Saffron (2014-11-02) and current revision 65 (2026); revisions via https://meta.discourse.org/posts/8791/revisions/30.json
7. Alan Tan, "New helper to test `DiscourseEvents` triggers in RSpec", https://meta.discourse.org/t/63729 (2017-06-01)
8. Sam Saffron, "Removal of timecop", https://meta.discourse.org/t/66773 (2017-07-25)
9. Sam Saffron, reply in "Plugin QUnit tests are not running as part of rake qunit:test", https://meta.discourse.org/t/59577/8 (2017-07-17)
10. Commit 56f98de "Use webmock to stub external web requests." https://github.com/discourse/discourse/commit/56f98de (2017-05-26)
11. Commit history of `spec/controllers`, https://github.com/discourse/discourse/commits/main/spec/controllers (last commit 2018-06-11), and GitHub commit search "request specs" sorted oldest first (2017-10-02 onward), https://github.com/search?q=repo%3Adiscourse%2Fdiscourse+%22request+specs%22&type=commits&s=committer-date&o=asc (read 2026-10-11)
12. PR #7414 "DEV: Prefabrication (test optimization)", https://github.com/discourse/discourse/pull/7414 (2019-04-22 to 2019-05-07)
13. Sam Saffron, "Tests that sometimes fail - flaky test tips", https://samsaffron.com/archive/2019/05/15/tests-that-sometimes-fail (dated 2019-05-28 on the page)
14. PR #7778 "DEV: Add a new way to run specs in parallel with better output", https://github.com/discourse/discourse/pull/7778 (2019-06-21)
15. PR #8441 "DEV: introduces GitHub Actions for CI", https://github.com/discourse/discourse/pull/8441 (2019-12-10); commits 38b4e3b (2020-01-07) and 007c44e (2020-01-08, revert of the smoke test)
16. PR #7271 "DEV: Add simplecov as test dependency", https://github.com/discourse/discourse/pull/7271 (2019-04-01)
17. discourse/rubocop-discourse `config/default.yml`, `rubocop-rspec.yml`, `lib/rubocop/cop/discourse/*.rb` (main, read 2026-10-11); commit f80bc08 "Add cop to disable mocking of `Jobs` in tests." https://github.com/discourse/rubocop-discourse/commits/main/lib/rubocop/cop/discourse/no_mocking_jobs.rb (2020-07-15)
18. discourse/lint-configs `lint-configs/eslint.mjs` and `eslint-rules/test-filename-suffix.mjs`, https://github.com/discourse/lint-configs (main, read 2026-10-11)
19. PR #16311 "DEV: Minimal first pass of rails system test setup", https://github.com/discourse/discourse/pull/16311 (opened 2022-03-29, merged 2022-09-28); commit 57caf08
20. PR #18881 "DEV: initial system tests for chat and plugins", https://github.com/discourse/discourse/pull/18881 (2022-11-04)
21. PR #19531 "DEV: start glimmer-ification and optimisations of chat plugin", https://github.com/discourse/discourse/pull/19531 (2022-12-21)
22. PR #19434 "DEV: Move chat transcript tests into system specs", https://github.com/discourse/discourse/pull/19434 (2022-12-23)
23. PR #21648 "DEV: Add a per-spec timeout" (2023-05-19), PR #24798 (2023-12-08), PR #25356 (2024-01-22), https://github.com/discourse/discourse/pull/21648
24. PR #22686 "DEV: Raise exception when capybara finder times out", https://github.com/discourse/discourse/pull/22686 (2023-08-08)
25. PR #24811 "DEV: Introduce automatic reruns to RSpec tests on Github actions", https://github.com/discourse/discourse/pull/24811 (2023-12-11 to 2023-12-12); PR #25031 (2023-12-26)
26. Loïc Guitaut, "New core features system specs in plugins and themes", https://meta.discourse.org/t/361381 (2025-04-11)
27. PR #31977 "DEV: replace selenium driver with playwright", https://github.com/discourse/discourse/pull/31977 (2025-03-24 to 2025-05-06)
28. David Taylor, "Bundling more popular plugins with Discourse core", https://meta.discourse.org/t/373574 (2025-07-10)
29. Commit e56a4bf "DEV: Prepare for rename of `app/assets/javascripts/` -> `frontend/`", https://github.com/discourse/discourse/commit/e56a4bf (2025-10-22)
30. PR #36445 "DEV: Enforce deprecation-free tests for preinstalled plugins/themes", https://github.com/discourse/discourse/pull/36445 (2025-12-16)
31. PR #40685 "DEV: Block external requests in system specs via Chrome DNS resolver", https://github.com/discourse/discourse/pull/40685 (2026-06-17)
32. PR #41611 "DEV: Improve RSpec agent testing guidance", https://github.com/discourse/discourse/pull/41611 (2026-07-10); PR #40111 (2026-05-18)
33. PR #43250 "DEV: Notify Patch Triage about flaky test reports", https://github.com/discourse/discourse/pull/43250 (2026-09-07); "Discourse-patch-triage bot", https://meta.discourse.org/t/402898 (2026-05-13)
34. Commits a104c37 (2013-06-12), 8c4aac7 (2013-06-19) on QUnit and d3cc85c (2014-07-31) on pretender, via GitHub commit search https://github.com/search?q=repo%3Adiscourse%2Fdiscourse+qunit&type=commits&s=committer-date&o=asc (read 2026-10-11)
35. Historical files via raw.githubusercontent.com: `spec/spec_helper.rb` at v0.9.0 to v1.2.0, `Gemfile` and `.travis.yml` at v0.8.0 to v2.5.0, `spec/rails_helper.rb` at v1.6.0 to v2026.4.0, `README.md` at v0.9.0 to v2.0.0 (read 2026-10-11); tag dates v3.3.0 (30 July) and v3.4.0 (4 February) from https://github.com/discourse/discourse/releases; the pages show no year, so 2024 and 2025 are inferred from the release sequence
36. Tests workflow run 38125724506 for the snapshot commit, job usage, https://github.com/discourse/discourse/actions/runs/38125724506/usage (2026-10-11)
37. rspec-rails `lib/rspec/rails/configuration.rb`, `DIRECTORY_MAPPINGS` (main), https://github.com/rspec/rspec-rails (read 2026-10-11)
38. GitHub commit searches: "flaky" (589 results), "full wait duration", "unhandled request", "webmock", "simplecov", "system tests" (read 2026-10-11), https://github.com/search?q=repo%3Adiscourse%2Fdiscourse+flaky&type=commits
39. The Robinauts post, `_posts/2026-10-11-why-the-drama-about-duplicating-tests.md` (2026-10-11)
40. RSpec core team, "RSpec 3.5 has been released!", https://rspec.info/blog/2016/07/rspec-3-5-has-been-released/ (July 2016)

## Appendix: commands and counting decisions

**Snapshot.**
```
mkdir -p $SCRATCH/discourse-clone && cd $SCRATCH/discourse-clone
git clone --depth 1 https://github.com/discourse/discourse.git
git -C discourse log -1 --format='%H %cI %s'
# 008b5fc4585ca178bf10642d3da1dcc39e2ace50 2026-10-11T19:41:56+11:00 FIX: Handle AI completion edge cases (#44460)
```

**Counting.** One run over the whole clone, per file:
```
python3 -I notebooks/X-shapes-of-tests/tools/count_lines.py $CLONE --by-file \
  --ext .rb,.rake,.js,.mjs,.cjs,.ts,.gjs,.gts,.erb > all_by_file.csv      # 19,451 files
```
The tool's default excludes applied, including `*/vendor/*` (which removes `plugins/discourse-events/vendor/holidays` and its own specs), `node_modules`, `dist` and `build`. A helper script run from the scratchpad (`python3 -I classify.py $CLONE all_by_file.csv out.csv detail.csv`) added `category` and `origin` columns and per-file grep counts. The CSV saved as `discourse.counts.csv` is the tool's output for all 19,451 files with those two columns added. Categories: `test:*`, `helper`, `data`, `prod:backend`, `prod:frontend`, `prod:migrations_toolkit` and `excluded:*`.

**Grouping rules (in order).**
1. `migrations/**`: files under a `spec/` directory are `test:migrations_toolkit` if `*_spec.rb`, `data` if under `fixtures/`, otherwise `helper`. All other files are `prod:migrations_toolkit`.
2. `test/smoke-test.mjs` → `test:smoke`.
3. Ruby specs under `spec/`, `plugins/*/spec/` and `themes/*/spec/`:
   - `fixtures/` → `data`;
   - `support/`, `fabricators/`, any `page_objects/`, `spec/system/helpers/` → `helper`;
   - non-`*_spec.rb` files → `helper` (rails_helper, swagger_helper, plugin_helper, shared examples, schema loader);
   - `requests/api/**/*_spec.rb` → `requests_api_docs`;
   - otherwise by the first folder below `spec/`: `system`, `requests` (plus 2 legacy plugin `controllers/` specs in `poll`), `models`, `services`, `jobs`, `serializers`/`serializer`, `integration`, `multisite`, `integrity`, `lib`;
   - everything else, including spec files at the root of a plugin's `spec/`, → `other_backend`. That covers core `script`, `mailers`, `tasks`, `helpers`, `db`, `migrations`, `initializers`, `import_export`, `views`, `queries`, `resources`, `generator`, and plugin `triggers`, `scripts`, `queries`, `components`, `evals`, `actions`, `configuration`, `discourse_narrative_bot`, `mailers`, `migrations`, `reports`, `tasks`, `automation`, `db`, `validators`, `helpers`, `shared`, `resources`. Size by folder: core `script` 3,317, plugin roots 3,160, core `mailers` 2,607, plugin `triggers` 2,549, core `tasks` 2,418, the rest below 2,400 each.
4. QUnit under `frontend/discourse/tests/`, `plugins/*/test/javascripts/` and `themes/*/test/`:
   - files directly in the test root → `helper` (boot files), except `chat-fixtures.js` → `data`;
   - `fixtures/` → `data`;
   - `helpers/` and files not ending in `-test.{js,gjs,ts,gts}` → `helper` (includes `tests/integration/components/empty-topic-filter.gjs`);
   - `integration/`, `components/`, `component/`, `addons/` → `qunit_integration`;
   - `acceptance/` → `qunit_acceptance`;
   - `unit/`, `lib/` → `qunit_unit`.
5. `frontend/discourse/type-tests/**` → `type_tests`. `frontend/asset-processor/**/*.test.mjs` → `tooling_vitest`.
6. Production:
   - `app/`, `lib/`, `config/` `.rb`/`.rake` → `prod:backend`; `.erb` → `excluded:templates`.
   - `frontend/discourse/{app,admin,select-kit,float-kit,truth-helpers,dialog-holder}` and `frontend/{pretty-text,discourse-markdown-it,pretty-text-processor,discourse-i18n,asset-processor}` → `prod:frontend`. Other `frontend/discourse` files (build config, testem, `scripts/js`) → `excluded:build_config`. `frontend/discourse-types`, `deprecation-silencer`, `polyfills.js` → `excluded:generated_or_build`.
   - Plugins: `db/` → `excluded:migrations`; `.rb`/`.rake` → `prod:backend`; other code → `prod:frontend`.
   - Themes likewise.
   - `db/` → `excluded:migrations_and_seeds`; `script/` → `excluded:scripts`; everything else (dotfiles, `docs/`, `stylelint-rules/`, `public/javascripts`, `.skills`) → `excluded:other`.

**Test-function and mock greps.** Python `re`, multiline, per file:
- RSpec examples: `^\s*(it|specify|scenario)\b(?!_)\s*(\(|"|'|\{|do\b|$)`; rswag adds `^\s*response\s+["']\d`.
- QUnit tests: `^\s*(test|skip|todo)\s*\(` plus `^\s*(conditionalTest|chromeTest|firefoxTest)\s*\(`; modules: `^\s*(module|acceptance)\s*\(`.
- vitest: `^\s*(test|it)\s*\(`.
- Mock patterns as listed in section 6.

Other greps, run with `grep -r --include=*_spec.rb` over `spec plugins themes`: `fab!(` (16,189 sites in 2,636 files), `Fabricate(` variants (28,762), `let!(` (1,402), `with_prepared_responses` (517 sites in 72 files), `track_publish` (154 files), `track_events|DiscourseEvent.track` (89 files), `expect_enqueued_with|expect_not_enqueued_with` (95 files), `run_immediately!` (225 files), `freeze_time` (376 files), `^\s*(xit|skip)\b` (56 lines), `it_behaves_like|include_examples|it_should_behave_like` (1,056 lines), `"core features"` (35 files). Top mock receivers: `grep -rhoE '\b[A-Z][A-Za-z0-9_:]*(\.any_instance)?\.(stubs|expects)\(' | sort | uniq -c`. WebMock hosts: `grep -rhoE 'stub_request\(\s*:\w+,\s*"https?://[^/"]+'`.

**Judgment calls.**
- **Bundled plugins and themes count as product.** CI tests them on every pull request, and 38.7% of test code lives there. Core and plugin splits are given for every row. Official plugins and themes that CI clones at run time are not in the snapshot and are not counted.
- **The importer toolkit (`migrations/`) is its own row and is included in the whole.** It is a separate sub-project with its own workflow. Shares without it are within 0.5 points (section 4).
- **Tooling, type-test and smoke rows are included in the whole.** They total 0.4%.
- **Page objects are helpers, not system-test lines.** This follows the brief ("test utilities"). They are 20,547 lines, 32% on top of the system specs.
- **QUnit `fixtures/` modules are data**, although they are `.js` files: they are canned JSON. They are listed as data with their size.
- **`spec/integration` stays its own row.** rspec-rails gives it `type: :request`, but the project keeps it apart from `spec/requests`.
- **Production `evals/` in `discourse-ai` (3,175 lines) is counted as backend production.** It is an LLM evaluation harness shipped in the plugin tree.
- **The component/non-component split for the frontend ratio uses the path substring `/components/`**, on both the production and the test side.

**Deviations from the brief.**
- **Comment stripping.** The counting tool does not know `.gjs`, `.gts` or `.rake`, so their full-line comments are counted as code. Measured separately with the tool's JavaScript comment rules plus `{{!`: 1,839 comment lines remain in QUnit integration (1.4% of its count), 66 in other QUnit categories (about 1%), 216 in type tests (21.9%), 10,792 in production `.gjs`/`.gts` (3.9%). `.rake` comments were not measured. Docstrings are not recognised, as the brief notes. RSpec description strings count as code.
- **Static test counts.** They miss examples generated by shared examples, loops and `it_behaves_like`, and they count the 56 skipped examples.
- **GitHub API unavailable.** The session's proxy refused `api.github.com` for this repository. Dates and pull-request texts were read from github.com pages (pull requests, commit pages, path histories, commit search) through a web-fetch tool that returns excerpts of at most about 125 characters, so longer GitHub quotes are given as marked excerpts. Historical file contents were read from raw.githubusercontent.com at release tags. Meta posts were read verbatim through meta's `/raw/` and `.json` endpoints. Historical test counts (for example, system spec files per year) were therefore not measured.
- **No git history was used.** The clone is depth 1. The only git command run in the blog repository was a read-only `git status`.

**Things looked for and not found.**
- The stated reason for the 2017–2018 controller-to-request-spec rewrite: searched commit search for "request specs" and "request spec", meta for "request specs" and "controller specs".
- The stated reason for the Playwright switch: PR #31977 and meta.
- Before-and-after flaky-test rates for PR #24811: the PR and meta searches "flaky", "flakiness", "flaky specs", "flaky system tests", "flaky test" from 2023 to 2024.
- Any meta post by the team in 2023–2024 about reducing system-test flakiness: same searches, plus searches by author `@tgxworld`.
- The commit that enabled rspec-mocks next to Mocha: commit search "MultiMock", "rspec-mocks", "rspec-multi-mock".
- The original author of the theme system-test guide: meta now shows the Discourse account.
- The commit that made unhandled pretender requests throw.
- Any coverage gate or coverage discussion by the team.
