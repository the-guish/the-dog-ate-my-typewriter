# GitLab: the shape of its tests

Measured: https://gitlab.com/gitlab-org/gitlab at `aeb834be5899909c5b720042693640c59f220dc3` (2026-10-11T16:59:14-04:00), default branch `master`.
Counted with notebooks/X-shapes-of-tests/tools/count_lines.py, rules as in
the brief. Deviations in the appendix.

## Summary

Posture: GitLab writes down a test pyramid and its tree has that shape, but its "unit" specs mostly boot Rails against a real PostgreSQL and its UI is proved mainly by Jest in jsdom with the network mocked; in the post's terms, the wide base is in-process tests against a real database, and the browser tests over a real server (3.2% of test lines) are a thin, shrinking backstop.

| category (GitLab's name) | maps_to | lines | pct | files | tests |
|---|---|---:|---:|---:|---:|
| RSpec unit | unit + adapters (hybrid) | 2,138,356 | 52.6% | 17,626 | 191,178 |
| Jest unit and component | fast (role differs) | 1,083,136 | 26.6% | 6,604 | 80,527 |
| RSpec integration | api | 576,864 | 14.2% | 3,121 | 36,234 |
| RSpec system (feature) | e2e (white-box) | 123,893 | 3.0% | 1,397 | 8,998 |
| GitLab QA end-to-end, browser + API | e2e / api | 25,118 | 0.6% | 379 | 571 |
| other product suites (migrations, gems, Workhorse, fixtures, MSW, contracts) | mixed | 120,909 | 3.0% | 1,042 | 6,988 |

History: since 2016 GitLab has kept moving tests down and out of the browser (Spinach to RSpec 2016–2018, Karma to Jest 2018–2021, CI split by level 2019, predictive selection 2020–2021, Capybara to Jest+MSW 2026), taking system tests from 10.9% of all tests in 2019 to 4.31% in 2025 by its own count, while fighting flakiness with retries, then quarantine, then a 24-hour fix SLO.

## 1. Posture and classification

**Written posture.** The testing guide's levels page opens with a "testing priority triangle" diagram. Since 2025-09-22 it also says [2][14]:

> To achieve test coverage with stability and speed, we use the testing pyramid to guide test distribution.
>
> Most of our tests should be at the unit level, with fewer tests as we move up each layer. End-to-end tests at the top are the most expensive to run and maintain. Because of this, they should make up the smallest portion of our total tests.
> — Amy Phillips, `testing_levels.md`, 2025-09-22

The page defines four levels, in the project's own words [2]:

- *Unit tests*: "ensure that a single unit of code (a method) works as expected … These tests should be isolated as much as possible. For example, model methods that don't do anything with the database shouldn't need a DB record."
- *Integration tests*: "ensure that individual parts of the application work well together, without the overhead of the actual app environment (such as the browser). These tests should assert at the request/response level: status code, headers, body."
- *White-box tests at the system level* (system or feature tests): ensure "the GitLab Rails application … works as expected from a browser point of view", while "data needed for the tests are usually created directly using RSpec factories" and "expectations are often set on the database or objects state".
- *Black-box tests at the system level* (end-to-end, GitLab QA): "data needed for the tests can only be created using the GUI or the API" and "expectations can only be made against the browser page and API responses".

The 2025 testing strategy page adds the operating rules. "Every test should earn its keep. No duplication, no waste." "Start at the lowest level possible: Unit → Integration → System → E2E." "Scan existing tests before writing new ones. Don't test the same thing twice." [3]. On system tests the levels page has said since 2017: "If we're confident that the low-level components work well … we shouldn't need to duplicate their thorough testing at the System test level" [2][15]. This is the pyramid practice the post describes: push each test as low as it goes, and avoid copies across layers.

**Classification by machine.** The levels are not only prose. `tooling/quality/test_level.rb` maps every top-level spec folder to a level. `spec/spec_helper.rb` then derives `metadata[:level]` for every `*_spec.rb` file, and it raises `UnknownTestLevelError` for a file in an unmapped folder [4][5]. CI jobs are generated per level: `rspec unit pg17`, `rspec integration pg17`, `rspec system pg17`, `rspec migration pg17`, `rspec background_migration pg17`, each with EE, single-database, Redis, Gitaly-MVCC, ClickHouse and PostgreSQL-version variants [6]. Frontend and end-to-end tests have their own jobs: `jest`, `jest-integration`, `test-storybook`, `e2e:test-on-cng`, `e2e:test-on-omnibus-ee`.

**The tree** at the snapshot [1], one line per category, with what it is for:

```
spec/                      CE (FOSS) RSpec + Jest; ee/spec/ mirrors it for the Enterprise Edition
  models services lib graphql workers finders policies helpers serializers presenters
  views components uploaders validators routing tasks initializers config db events ...
                           "unit" level (TestLevel): one class or method; boots Rails and opens a
                           DB transaction unless the file uses fast_spec_helper
  requests controllers mailers commands
                           "integration": request/response through the Rack stack; request specs
                           preferred, controller specs "legacy" (epic 5076)
  features                 "system" (white-box): Capybara; Selenium + headless Chrome when :js,
                           RackTest otherwise; app served by Puma behind a real Workhorse
  migrations               "migration": schema migrations against a real PostgreSQL
  lib/gitlab/background_migration   "background_migration": data migrations
  frontend/fixtures/*.rb   "frontend_fixture": RSpec specs that call controllers and GraphQL to
                           write JSON/HTML fixtures for Jest
  frontend/**/*_spec.js    Jest "unit" and "component" tests (jsdom, mocked network)
  contracts/               Pact consumer (Jest) and provider (RSpec) contract tests
  rubocop tooling scripts keeps dot_gitlab_ci haml_lint support_specs factories_specs
                           tests of the repository itself (GitLab files them under "unit")
  support/ factories/ fixtures/   helpers, FactoryBot factories, data files
ee/spec/frontend/integration/   "frontend integration" (EE-only): full Vue apps in jsdom, network
                           intercepted by MSW with fixtures generated from the real backend
qa/qa/specs/features/{api,browser_ui,ee}   GitLab QA "black-box" end-to-end, against a
                           deployed GitLab (CNG, Omnibus, staging); smoke subset gates deploys
qa/spec, qa/gems           unit tests of the QA framework itself
gems/*/spec                RSpec for internal gems extracted from the monolith
workhorse/**/*_test.go     Go tests of GitLab Workhorse (in this repository since 2021)
app/assets/javascripts/**/*.stories.js   Storybook stories, rendered by test-storybook
```

Metadata refines the folders: `:js` (browser driver), `quarantine:` (skipped on CI), `:elastic`, `:click_house`, `:sidekiq_inline`, `:clean_gitlab_redis_*`, `feature_category:` (ownership, required by RuboCop), and `:smoke` in QA (48 files) [5][9][10].

## 2. What the names mean

| GitLab name | what the tests actually touch | nearest post category | fit |
|---|---|---|---|
| unit (spec_helper, 93% of files) | one Ruby process with Rails booted; real PostgreSQL in a rolled-back transaction (63% of files create rows through factories); real Gitaly when a project `:repository` trait is used (8%); real Redis for queues and shared state; Rails cache in memory; Sidekiq in fake mode; WebMock blocks outbound HTTP | adapters_free for models and finders; unit or fast for the rest | poor. The post's "unit" needs nothing. GitLab's needs a database, and half the files also stub collaborators |
| unit (fast_spec_helper, 7%) | plain Ruby, no Rails, no DB | unit | good |
| integration (request, controller, mailer specs) | full Rack middleware and router in-process (no socket); real DB, Gitaly, Redis | api | moderate. Real stack, but no real HTTP server, and data comes from factories |
| system / feature, `:js` (87% of files) | headless Chrome over Selenium; app in Puma behind a real Workhorse; real DB, Gitaly, Redis; data from factories | e2e | moderate. Mechanism matches; set-up and assertions are white-box |
| system / feature, RackTest (13%) | HTML through Rack::Test, no browser | api | moderate |
| GitLab QA browser_ui | browser against a deployed GitLab with all services; data through UI or API only | e2e | good |
| GitLab QA api | HTTP against a deployed GitLab | api | good |
| Jest unit / component | Node + jsdom; network adapter fails any unmocked request; 54% of files `shallowMount` (child components stubbed) | unit (pure JS) / fast (components) | poor. It is in-process on fakes like "fast", but it is the main proof for the UI, not an extra copy |
| Jest frontend integration (MSW) | full Vue app in jsdom; GraphQL and REST intercepted by MSW with fixtures recorded from the real backend | fast | poor. Fakes again, but meant as proof of multi-component pages |
| migration, background_migration | real PostgreSQL schema changes | adapters_free | moderate (an adapter against its real store) |
| Workhorse Go tests | Go processes with `httptest` servers as stand-ins; no mock library | unit / adapters_free | good |
| contract (Pact) | consumer in Jest against a Pact mock; provider in RSpec | none | no slot |
| tooling (RuboCop cops, CI scripts, test helpers) | the repository itself | tooling | good |

The two words that mislead most are GitLab's "unit" and "integration". A model spec that saves records and reads them back through PostgreSQL is a unit test at GitLab. "Integration" means a request through the Rails stack, not a test across services.

## 3. Categories outside the post's taxonomy

- **Migration and background-migration specs** (31,906 lines, 364 files). They prove that a schema or data migration runs against a real PostgreSQL and leaves the expected rows. GitLab ships database migrations with every release and supports multi-version upgrades, so these get their own CI jobs. RuboCop forbids FactoryBot in them; they must use `table(:name)` [12].
- **Frontend fixture generators** (10,759 lines, 116 files). These are RSpec specs that hit real controllers and GraphQL resolvers and save the responses as JSON or HTML for Jest [6]. They are the bridge that lets the jsdom suite consume real backend output. The predictive selector uses them: a backend change can trigger Jest specs "via frontend fixtures" [6].
- **Frontend integration with MSW** (8,481 lines, 85 files, EE-only). They prove that a page's components, the Apollo cache and UI state work together against recorded backend responses. They exist because Capybara is slow: the founding MR measured "~5m15s per context" for a Capybara spec against "~13-14s for the same coverage" in Jest [44].
- **Contract tests** (452 lines, 8 files). Pact tests were added in 2022 [43] and have stayed tiny.
- **Storybook stories** (16,300 lines, 270 files, 945 story exports). These are examples that double as tests: the `test-storybook` job serves the built Storybook and renders every story in Playwright Chromium [6].
- **Internal gems** (38,562 lines, 310 files) and **Workhorse** (30,749 lines, 159 files, 884 `Test*` functions and 402 subtests). These are components that live in the monorepo, each with its own suite.
- **As-if-FOSS and as-if-JH runs.** These are modes, not files: the same suite runs with `ee/` removed, or with JiHu overrides, to prove that each edition still passes [6].

## 4. Lines per category

Category totals exclude helpers. The "whole" is the 13 product categories below. Tooling, Storybook stories and docs screenshots are shown beside the whole but left out of it, as the Robinauts chart did with its tooling tests. "Tests" is a static count of `it`, `specify`, `scenario`, `example` and `its` lines (Ruby), `it(` and `test(` (JavaScript), `func Test` (Go), and exported stories.

| category | language | lines | pct of whole | files | tests |
|---|---|---:|---:|---:|---:|
| RSpec unit (product folders) | Ruby | 2,138,356 | 52.6% | 17,626 | 191,178 |
| Jest unit and component | JavaScript (+5 Vitest TypeScript files) | 1,083,136 | 26.6% | 6,604 | 80,527 |
| RSpec integration | Ruby | 576,864 | 14.2% | 3,121 | 36,234 |
| RSpec system / feature | Ruby | 123,893 | 3.0% | 1,397 | 8,998 |
| internal gems | Ruby | 38,562 | 0.9% | 310 | 3,696 |
| Workhorse | Go | 30,749 | 0.8% | 159 | 884 |
| RSpec background migration | Ruby | 21,025 | 0.5% | 143 | 819 |
| GitLab QA end-to-end, browser_ui | Ruby | 19,600 | 0.5% | 312 | 442 |
| RSpec migration | Ruby | 10,881 | 0.3% | 221 | 665 |
| RSpec frontend fixture generators | Ruby | 10,759 | 0.3% | 116 | 519 |
| Jest frontend integration (MSW) | JavaScript | 8,481 | 0.2% | 85 | 383 |
| GitLab QA end-to-end, api | Ruby | 5,518 | 0.1% | 67 | 129 |
| contract (Pact) | JavaScript + Ruby | 452 | 0.01% | 8 | 22 |
| **whole (product tests)** | | **4,068,276** | **100%** | **30,169** | **324,496** |
| *beside the whole:* RSpec tooling | Ruby | 72,401 | (1.8%) | 610 | 5,773 |
| *beside:* Jest tooling | JavaScript | 4,502 | (0.1%) | 25 | 325 |
| *beside:* QA framework unit tests | Ruby | 12,974 | (0.3%) | 120 | 1,045 |
| *beside:* Storybook stories (examples run as tests) | JavaScript | 16,300 | (0.4%) | 270 | 945 |
| *beside:* docs screenshot specs | Ruby | 98 | (0.0%) | 2 | 8 |

**CE and EE separately** (the `spec/` and `ee/spec/` trees; EE Jest also holds the 5 Vitest files of `ee/frontend_islands`; percentages of each tree's product total):

| category | CE lines | CE % | CE files | CE tests | EE lines | EE % | EE files | EE tests | CE+EE lines | CE+EE % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| unit | 1,076,454 | 52.8% | 9,016 | 101,749 | 1,061,902 | 54.9% | 8,610 | 89,429 | 2,138,356 | 53.8% |
| Jest unit/component | 564,619 | 27.7% | 3,602 | 41,536 | 518,517 | 26.8% | 3,002 | 38,991 | 1,083,136 | 27.3% |
| integration | 288,996 | 14.2% | 1,389 | 19,990 | 287,868 | 14.9% | 1,732 | 16,244 | 576,864 | 14.5% |
| system | 78,696 | 3.9% | 872 | 6,339 | 45,197 | 2.3% | 525 | 2,659 | 123,893 | 3.1% |
| background migration | 16,349 | 0.8% | 125 | 655 | 4,676 | 0.2% | 18 | 164 | 21,025 | 0.5% |
| migration | 10,253 | 0.5% | 208 | 607 | 628 | 0.0% | 13 | 58 | 10,881 | 0.3% |
| frontend fixtures | 3,850 | 0.2% | 56 | 218 | 6,909 | 0.4% | 60 | 301 | 10,759 | 0.3% |
| Jest integration (MSW) | 0 | 0.0% | 0 | 0 | 8,481 | 0.4% | 85 | 383 | 8,481 | 0.2% |
| contract | 417 | 0.0% | 7 | 21 | 35 | 0.0% | 1 | 1 | 452 | 0.0% |
| **tree total** | **2,039,634** | | | | **1,934,213** | | | | **3,973,847** | |
| tooling (beside) | 71,766 | | 603 | 5,713 | 635 | | 7 | 60 | 72,401 | |

EE is almost as large as CE. The shapes match, except that EE has proportionally fewer system tests (2.3% against 3.9%).

**Inside GitLab's "unit".** The 2,138,356 unit lines split three ways. 101,624 lines (4.8%, 1,263 files) use `fast_spec_helper` and touch neither Rails nor the database. 349,625 lines (16.3%, 5,291 files) boot Rails but create no factory records. 1,687,107 lines (78.9%, 11,072 files) write rows through FactoryBot or `let_it_be`. By folder, `lib` (711k lines), `services` (551k), `models` (402k) and `graphql` (110k) dominate.

**Collapsed to the post's taxonomy** [57] (approximate; the grouping rules are in the appendix):

| post category | what went in | lines | pct |
|---|---|---:|---:|
| e2e (browser over real server and DB) | QA browser_ui + `:js` system specs | 131,874 | 3.2% |
| api (through the real stack) | integration + RackTest system specs + QA api | 594,001 | 14.6% |
| unit (pure) | `fast_spec_helper` unit specs + internal gems | 140,186 | 3.4% |
| in-process against real PostgreSQL (nearest: adapters) | other unit specs + migrations + background migrations + fixture generators | 2,079,397 | 51.1% |
| in-process on fakes, frontend (nearest: fast) | Jest unit/component + MSW integration | 1,091,617 | 26.8% |
| other | Workhorse (Go), contract | 31,201 | 0.8% |

**Helpers** (excluded above): 353,184 lines in 5,112 files. RSpec `spec/support` and `ee/spec/support` hold 170,558 lines (2,178 files); FactoryBot factories hold 31,711 lines (1,229 files); other RSpec helper files 7,385 lines. Jest helpers, mocks and `mock_data.js` files hold 97,354 lines (711 files). The QA framework (page objects, resources, runtime) holds 40,701 lines (780 files), more than the 25,118 lines of end-to-end specs it serves. Gem spec helpers hold 4,193 lines, contract helpers 749 and Workhorse `testhelper` 533. The RSpec suite also leans heavily on shared examples: 47,923 `it_behaves_like`/`include_examples` call sites draw on 2,986 shared example groups.

**Data files** (excluded): `spec/fixtures` (1,055 files, 7.2 MB), `ee/spec/fixtures` (519 files, 4.1 MB), `qa/qa/fixtures` (61 files, 0.9 MB), Workhorse `testdata` (77 files, 7.8 MB), Jest `__snapshots__` (188 files, 0.4 MB), `spec/frontend/fixtures/static` (15 files, 0.5 MB) and Pact contract JSON (9 files, 52 KB). Code-extension files inside these folders (183 files, 4,472 counted lines) are excluded as data.

**Against GitLab's own published counts.** The levels page estimates example counts per level as of 2025-02-03 [2][13]. Our static counts at the snapshot are lower, because the static count misses shared examples and table-driven `where` blocks (5,281 of them). The proportions, though, agree:

| level | GitLab, 2025-02-03 (examples) | static `it` count, 2026-10-11 | lines, 2026-10-11 |
|---|---:|---:|---:|
| end-to-end (QA) | 704 (0.24%) | 571 (0.24%) | 25,118 (0.88%) |
| system | 12,444 (4.31%) | 8,998 (3.80%) | 123,893 (4.33%) |
| integration | 57,127 (19.79%) | 36,234 (15.29%) | 576,864 (20.14%) |
| unit | 218,459 (75.66%) | 191,178 (80.67%) | 2,138,356 (74.66%) |

GitLab's table does not say whether Jest examples are included. The RSpec static count alone comes close to its unit figure, so it probably counts RSpec only (inference).

## 5. Test-to-code ratio

Production code is `app/` (not `app/assets/` stylesheets or images), `lib/`, `ee/app/`, `ee/lib/`, Ruby files under `config/` and `ee/config/`, `sidekiq_cluster/`, `metrics_server/`, the JavaScript and Vue frontend under `app/assets/javascripts/`, `ee/app/assets/javascripts/` and `ee/frontend_islands/*/src/`, `gems/*/lib`, and Workhorse's non-test Go. That totals 2,041,021 lines. Excluded: `db/` (migrations, 45,023 lines; the 47,297-line `db/structure.sql` and two symlinks to it), the generated `gems/error_tracking_open_api` (2,751 lines), `vendor/`, `locale/`, `qa/`, `scripts/`, `tooling/`, `rubocop/`, `danger/`, `keeps/`, docs and Storybook stories. HAML templates are not in the tool's extension list (2,404 files, 38,132 non-blank lines).

| tests | production code | test lines | code lines | ratio |
|---|---|---:|---:|---:|
| unit, `spec/models` | `app/models` (CE+EE) | 401,651 | 152,562 | 2.63 |
| unit, `spec/services` | `app/services` | 550,589 | 201,866 | 2.73 |
| unit, `spec/lib` | `lib` | 711,431 | 421,262 | 1.69 |
| unit, `spec/graphql` | `app/graphql` | 109,785 | 119,486 | 0.92 |
| unit, `spec/workers` | `app/workers` | 96,195 | 42,540 | 2.26 |
| unit, `spec/policies` | `app/policies` | 42,427 | 9,159 | 4.63 |
| unit, `spec/finders` | `app/finders` | 49,560 | 21,038 | 2.36 |
| integration (all) | controllers + `lib/api` + `app/graphql` + mailers | 576,864 | 259,070 | 2.23 |
| controller specs only | `app/controllers` | 87,158 | 49,214 | 1.77 |
| all product RSpec, CE | CE backend | 1,470,748 | 602,052 | 2.44 |
| all product RSpec, EE | EE backend | 1,400,271 | 489,389 | 2.86 |
| unit (all) | whole backend | 2,138,356 | 1,091,441 | 1.96 |
| system | whole product (backend + frontend) | 123,893 | 2,000,676 | 0.06 |
| QA end-to-end (browser + API) | whole product | 25,118 | 2,000,676 | 0.01 |
| Jest unit/component, CE | CE frontend | 564,619 | 514,715 | 1.10 |
| Jest unit/component, EE | EE frontend | 518,517 | 394,520 | 1.31 |
| Jest integration (MSW) | whole frontend | 8,481 | 909,235 | 0.01 |
| migration + background migration | PostgreSQL migrations + background-migration classes | 31,906 | 38,787 | 0.82 |
| internal gems | `gems/*/lib` | 38,562 | 22,600 | 1.71 |
| Workhorse | Workhorse Go | 30,749 | 17,745 | 1.73 |
| **all product tests** | **all production code** | **4,068,276** | **2,041,021** | **1.99** |

There are two lines of test for every line of product code. The backend carries more test weight (about 2.6 to 1) than the frontend (1.2 to 1). Policies, the authorization rules, are the most heavily tested layer.

## 6. Detroit or London

**Heuristic.** RSpec needs no import to mock, so "uses a mocking facility" means the file contains at least one rspec-mocks or WebMock call site. Call sites are counted with this Python regex:
`\b(?:instance_double|class_double|object_double|instance_spy|class_spy|object_spy|double|spy)\(|\breceive(?:_messages|_message_chain)?\(|\b(?:allow|expect)_any_instance_of\(|\bstub_const\(|\bhave_received\(|\b(?:expect|allow)_next(?:_found)?_instances?_of\(|\bstub_request\(`.
GitLab's configuration stubs (`stub_feature_flags`, `stub_application_setting`, `stub_licensed_features`, `stub_config`, `stub_env` and similar) flip product settings rather than replace collaborators, so they are reported separately.
For Jest the regex is
`\bjest\.(?:mock|fn|spyOn|doMock|createMockFromModule)\(|\.mock(?:Resolved|Rejected)?(?:Value|Implementation|ReturnValue)(?:Once)?\(|\bnew MockAdapter\(|\bmock\w*\.on(?:Get|Post|Put|Patch|Delete|Any)\(|\bcreateMockApollo(?:Provider)?\(|\bstubComponent\(|\bvi\.(?:mock|fn|spyOn)\(|\bhttp\.(?:get|post|put|patch|delete)\(|\bgraphql\.(?:query|mutation)\(`.
`shallowMount(Extended)?(` is counted on its own, and a file also counts as mocking if it imports `msw`. For Go: `gomock`, `mock.Mock` or `testify/mock`.
Real dependencies: `require 'spec_helper'` (boots Rails, opens a PostgreSQL transaction); `\b(?:create|create_list|create_pair)\(\s*:|\blet_it_be(?:_with_reload|_with_refind)?\b|\btable\(:` (writes rows); `create(...:repository|:small_repo|:custom_repo|:empty_repo)` on one line (a real Gitaly repository); `(?:,\s*|\s):js\b|\bjs:\s*true` (a real browser); `\bhttptest\.` in Go (a real HTTP server as stand-in).

| category | files | files using mocks | mock call sites per 1,000 lines | files using config stubs | boot Rails + DB | `fast_spec_helper` | write DB rows | real Gitaly repo | `:js` browser | `shallowMount` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| RSpec unit | 17,626 | 51% | 42.4 | 20% | 93% | 7% | 63% | 8% | 0% | – |
| RSpec integration | 3,121 | 44% | 19.1 | 52% | 100% | 0% | 95% | 13% | 0% | – |
| RSpec system | 1,397 | 23% | 7.3 | 41% | 100% | 0% | 96% | 32% | 87% | – |
| RSpec migration | 221 | 17% | 7.4 | 0% | 100% | 0% | 46% | 0% | 0% | – |
| RSpec background migration | 143 | 16% | 4.0 | 1% | 98% | 2% | 87% | 0% | 0% | – |
| RSpec frontend fixtures | 116 | 25% | 8.6 | 40% | 100% | 0% | 90% | 41% | 0% | – |
| Jest unit/component | 6,604 | 79% | 29.0 | – | – | – | – | – | – | 54% |
| Jest integration (MSW) | 85 | 11% | 2.1 | – | – | – | – | – | – | 0% |
| QA browser_ui | 312 | 0% | 0.0 | 0% | – | – | n/a | – | – | – |
| QA api | 67 | 0% | 0.0 | 0% | – | – | n/a | – | – | – |
| internal gems | 310 | 50% | 59.2 | 6% | 60% | 0% | 0% | 0% | 0% | – |
| Workhorse (Go) | 159 | 0% | 0.0 | – | – | – | – | – | – | 45% `httptest` |
| RSpec tooling | 610 | 50% | 57.7 | 8% | 15% | 34% | 6% | 1% | 0% | – |

QA end-to-end specs also call `create(:project)`, but QA "factories" build data through the API of a live instance, so the DB-write column does not apply to them.

**Reading it.** The backend sits on the Detroit side with stubs at the edges. Every RSpec level, except the `fast_spec_helper` files, runs against a real PostgreSQL, Redis and, where a repository is needed, a Gitaly server that `TestEnv` builds and starts. CI runs these as services (`postgres-17` with `fsync=off`, Redis and Redis Cluster, ClickHouse, Elasticsearch and OpenSearch in their jobs) [6][10]. Half of the unit files still stub something, and the guide asks for it: "Classes that don't need database records should use stubs/doubles as much as possible" [2]. Since 2022 a RuboCop rule has pushed presenters, serializers, helpers, views, components and mailers away from `create` toward `build_stubbed` [50]. The guide also asks contributors to "Mock expensive external operations" such as Git commands and compilation [10]. Higher up, the guide warns the other way: "A system test is often better than an integration test that is stubbing a lot of internals" [2]. Mock density falls steadily as tests climb (42 → 19 → 7 call sites per 1,000 lines), and the database share rises (63% → 95% → 96%).

Two choices make the "real" dependencies less real than they look. The Rails cache is an in-memory store in most specs. Since 2019 Sidekiq jobs are only enqueued in a fake array unless a spec opts into `:sidekiq_inline` [10][42]. Rémy Coutable's reason in 2019 was speed: "This should hopefully make RSpec jobs run faster." [42]

The frontend is London by policy. The levels page lists what to mock in unit tests: "Other exported classes: Every class must be tested in isolation to prevent test scenarios from growing exponentially", "All server requests", and, for component tests, "Child components: Every component is tested individually, so child components are mocked" [2]. It also says to keep Vuex unmocked "to avoid fragile and false-positive tests". In the tree, 79% of Jest files use a mock facility, and 54% shallow-mount. The axios adapter fails any request that is not mocked [24]. The MSW integration suite is classical inside the page and fake at the network: few explicit mocks, but every response is a recorded fixture [44].

GitLab QA has no mocks at all. Workhorse uses real `httptest` servers instead of a mock library.

## 7. The web UI

GitLab tests its UI five ways:

| suite | framework | what is real | lines | where it runs in CI |
|---|---|---|---:|---|
| Jest unit and component (`spec/frontend`, `ee/spec/frontend`) | Jest, Vue Test Utils, jsdom (also Vitest for EE "frontend islands") | the JS module or component; network, children and browser are fakes | 1,083,136 | `jest` (full) and `jest predictive` (tier 1); `jest vue3` variants |
| Frontend integration (`ee/spec/frontend/integration`) | Jest + MSW + generated fixtures | the whole Vue app and Apollo cache; backend replaced by recorded responses | 8,481 | `jest-integration` |
| System / feature specs (`spec/features`) | RSpec, Capybara, Selenium with headless Chrome (Firefox optional) | browser, Puma behind Workhorse, PostgreSQL, Redis, Gitaly; data from factories | 123,893 (112,274 in `:js` files) | `rspec system pg17` and variants; predictive in tier 1, Duo-selected or full in tier 2, full in tier 3 [3][6][39] |
| GitLab QA browser_ui (`qa/qa/specs/features`) | RSpec, Capybara, Selenium, own page-object framework | a deployed GitLab (CNG or Omnibus package) with all services | 19,600 specs + 40,701 framework | `e2e:test-on-cng`, `e2e:test-on-omnibus-*`; full suite in tier 3 since 2024-06-19 [38]; scheduled pipelines; smoke subset on deployments |
| Storybook | Storybook test runner, Playwright Chromium | rendered stories with stub data | 16,300 | `test-storybook` (skipped on tier-1 pipelines since 2026-06-09) [59] |

**Which one is the proof.** By volume and by policy, Jest is. The frontend guide tells developers to "Default to frontend integration tests because they are significantly faster" and to write a Capybara test only when "The test requires a real backend (database writes, authorization checks, server-side validations)" or navigation across server-rendered pages [8]. Since 2018 the levels page has said that system tests should "Only test the happy path" [2]. The testing strategy gives end-to-end tests the job "Validate full critical user journey", and makes the smoke suite the deployment gate [3].

The Jest decision in 2018 knowingly gave up the real browser. The evaluator listed "not testing in a real browser (we can probably handle this separately)" as a minus. Asked whether bundled code would still be tested, the reply was: "We use code bundled by Webpack in the feature specs which I think would be enough." [21] So the real-backend browser layer is the backstop, not the main proof. That is the reverse of Robinauts, where the browser suite is the proof and the in-process suite is the optional extra. Since `:js` feature specs fail on browser console errors (2024) [52], every `:js` Capybara test is also a check on the real compiled assets.

## 8. Enforcement by machine

| mechanism | what it checks | where | added |
|---|---|---|---|
| Test level from folder | every `*_spec.rb` gets `metadata[:level]` from its top folder; an unmapped folder raises `UnknownTestLevelError` and fails the run; CI builds one job family per level | `tooling/quality/test_level.rb`, `spec/spec_helper.rb` | 2019-05-22, foss!27514 [16] |
| No outbound network (backend) | WebMock `disable_net_connect!` except localhost and the search hosts; RuboCop `RSpec/WebMockEnable` forbids calling it directly | `spec/support/webmock.rb` | WebMock predates the available history; current helper form 2020-04-28 (!30422) [58] |
| No unmocked requests (frontend) | Jest's axios adapter fails the test on any request that is not mocked | `spec/frontend/__helpers__/mocks/axios_utils.js` | 2019-02-21, foss!23965 [24] |
| Random order | backend specs run in random order unless listed in a todo file; 7,448 files are still listed | `spec/support/rspec_order.rb`, `rspec_order_todo.yml` | 2022-08-23, !93137 [51] |
| Database guards in tests | cross-database joins and modifications raise; too many SQL queries raise (`QueryLimiting`); `:migration` and `:delete` specs fail if a transaction is already open | `spec/support/database/*`, `spec/spec_helper.rb` | 2021-08-05, !67019; 2023-09-19, !131911 [53] |
| Browser console | `:js` specs fail with `BrowserConsoleError` if the browser logs an error | `spec/support/helpers/browser_console_helpers.rb` | 2024-08-22, !162499 [52] |
| RuboCop for specs | no FactoryBot in migration specs (2018); `*_any_instance_of` autocorrected to GitLab helpers (2019); `build_stubbed` over `create` in presenter, serializer, helper, view, component and mailer specs (2022); no TestProf in migration specs (2022); `feature_category` required and valid (2023); no conditionals in feature specs (2023); no `wait_for_requests` (2026); at most 25 examples per feature spec file (2026) | `rubocop/cop/rspec/*`, `.rubocop.yml`, `gitlab-styles` | [49][50]; todo lists exempt 846 files from `RSpec/VerifiedDoubles`, 2,676 from `RSpec/FeatureCategory`, 381 from `AvoidCreate`, 41 from the 25-example cap |
| ESLint for Jest | the shared `@gitlab/eslint-plugin` Jest config rejects skipped tests, so the documented Jest quarantine is `it.skip` plus `// eslint-disable-next-line jest/no-disabled-tests` (10 such comments in the tree) [9]; any file under `spec/frontend/integration/` fails with "Frontend integration tests are EE-only; use Capybara for FOSS/licensed behavior." | `eslint.config.mjs` | CE path guard 2026-09-18, !255723 [45] |
| Changed lines must be covered | `rspec:undercoverage` fails the MR pipeline if any changed line has zero coverage; `pipeline:skip-undercoverage` lets it fail | `.gitlab/ci`, `scripts/undercoverage` | 2021-12-01, !74859 [40] |
| Fail fast | `rspec fail-fast` runs the specs mapped to the change (10 files at most) and cancels the pipeline on failure | `.gitlab/ci/rails.gitlab-ci.yml` | 2020-09-14, !41081 [35] |
| Tiered pipelines | predictive RSpec and Jest before approval, full suites after; full end-to-end only at tier 3; merge trains require a tier-3 pipeline under 16 hours old | `.gitlab/ci/rules.gitlab-ci.yml`, triage automation | before-approval split 2021-07-26 (!64903) [36]; tiers 2024-05-31 [38]; merge train check June 2024 (!154540) [6] |
| Labels that widen or narrow the run | `pipeline:run-all-rspec`, `pipeline:run-all-jest`, `pipeline:run-as-if-foss`, `pipeline:run-as-if-jh`, `pipeline:run-gitaly-mvcc` widen; `pipeline:expedited`, `pipeline:skip-undercoverage`, `pipeline:skip-rspec-fail-fast` narrow; CI-config changes force the full suite | `.gitlab/ci/rules.gitlab-ci.yml` | various, documented in [6] |
| Quarantine | `quarantine:` examples are skipped when `CI` is set; a fast-quarantine file from a separate repository is applied to every pipeline and cleared weekly | `spec/spec_helper.rb`; fast-quarantine project | 2019-01-15, foss!24369 [28]; fast quarantine 2023-04-28, !118482 [29] |
| Retries | failed specs rerun once in a new RSpec process; a job that fails on a known flaky test exits with code 112 and is retried | `scripts/rspec_helpers.sh`, `.gitlab/ci/rails/shared.gitlab-ci.yml` | 2022-01-25, !76839 [30]; 2024-10-23, !168541 [60] |
| Automated flaky triage | weekly issues for the most disruptive flaky test files; quarantine MRs opened automatically; quarantined tests deleted after 3 months; a flaky-file issue open over 24 hours becomes a severity-3 incident | handbook, `gitlab-org/quality/analytics/ci-alerts` | handbook wording 2025-12-18 to 2026-08-05 [47][48] |
| Danger | warns when app code changes without spec changes; warns on any new file under `spec/controllers` | `danger/specs/Dangerfile` | 2018-07-11; controller warning 2020-12-31 (!50566) [41] |

Lefthook's pre-push hooks run linters and Danger locally but no tests. Nothing enforces the level *proportions*. The pyramid percentages are recounted now and then (2019, 2025) and published as an estimate [2][13]. The closest machine nudges are the 25-example cap on feature spec files and the `build_stubbed` rule for view-layer specs.

## 9. History

**Trouble with earlier approaches, and the steers.** GitLab's test history is a run of steers, mostly in one direction: down the pyramid and out of the browser. Each was driven by speed or flakiness.

1. *Spinach to RSpec feature specs (2016–2018).* In March 2016 Robert Speicher proposed a freeze on Gherkin-style Spinach features [17]. The pain was debugging and maintenance: step definitions scattered across files, failures that did not say where they came from, and timeouts. The team agreed within a week. The freeze went into the first testing style guide (2016-03-30) [18]. Conversion ran as a community campaign (foss#23036), and CI nodes shifted from Spinach to RSpec as it went [19]. Spinach was deleted on 2018-05-15 [20]. The steer succeeded completely, and the browser-level tests survived in RSpec form.
2. *The pyramid made explicit and measured (2017–2019).* On 2017-10-11 Rémy Coutable split the testing guide and gave "Testing levels" its own page, with the triangle diagram and the advice "Consider not writing a system test" [15]. On 2019-04-17 the page first published counts per level [11]. Five weeks later, on 2019-05-22, `Quality::TestLevel` arrived. It derived the level from the folder, split CI into `rspec unit`, `rspec integration` and `rspec system` jobs "to have a better control on the parallelization of the jobs per level", and republished the counts [16].
3. *Karma to Jest (2018–2021).* In 2018 the frontend found Karma and Jasmine tests unsandboxed and slow, and built on an unmaintained jQuery add-on. An evaluation picked Jest, run in jsdom rather than a browser [21][22]. Jest landed on 2018-12-05 [23]. It failed unmocked requests from 2019-02-21 [24], and a Danger rule from 2020-03-03 told authors to prefer it [25]. The last Karma specs, the ones "particularly challenging because there's some special coupling to a real browser environment", were moved to Jest or to RSpec feature specs, and Karma was removed on 2021-09-03 [26]. The steer succeeded.
4. *Making the big suite affordable (2020–2026).* With a suite that "will take hours" to run in full [10], the engineering-productivity team tried running only the tests related to a change. Fail-fast came first (2020-09-14) [35]. Crystalball coverage mapping followed (2020-10 to 2020-12) [34]. A one-week experiment showed about a 10% miss rate, and the team "pivot[ed] the objective from cost saving to providing early feedback on failures" [33]. The compromise, from 2021-07-26, was a predictive subset before approval and the full suite after [36]. It was renamed "predictive" in 2023 [37] and generalized into three pipeline tiers in 2024 [38]. In 2026 GitLab Duo, the company's AI assistant, was added to pick system specs in tier 2 [39]. The steer worked as a compromise: GitLab never trusted the predictive subset to merge alone.
5. *Flakiness (2017–2026).* By 2017 failed examples were retried in-process with `rspec-retry`, and flaky examples were tracked from 2017-08-11 [27]. Quarantine metadata came to end-to-end tests in January 2019 and to Rails tests a week later [28]. Retrying in a fresh RSpec process followed in 2022 [30], and a fast-quarantine file in 2023 [29]. In 2024 `rspec-retry` was dropped directory by directory, because it was slow and hid broken tests [31]. It was removed outright on 2026-03-16 [32]. In 2025–2026 the handbook made flakiness an operational matter: automated weekly reports, automatic quarantine MRs, deletion after three months, and a 24-hour SLO that escalates to a production incident [47][48].
6. *Coverage as a gate on changes (2021).* After an incident in which a changed method had "no coverage … due to stubbing", GitLab made the pipeline fail on any changed line with zero coverage (2021-12-01) [40].
7. *Controller specs to request specs (2020–present).* An epic opened on 2020-12-15 says "Write new request specs. Do not write new controller specs." [41] A Danger warning followed on 2020-12-31. The steer has not succeeded in the tree. The epic counted 260 + 168 = 428 files under `spec/controllers` and `ee/spec/controllers`. At the snapshot there are 286 + 186 = 472.
8. *Capybara to Jest with MSW (2026).* On 2026-03-27 Natalia Tepluhina added Jest integration tests backed by MSW. She showed a ~22x local speed-up over the equivalent Capybara spec, and that they caught a six-week-old regression the feature spec had missed [44]. Between July and October 2026 about twenty merged MRs were titled as migrating or converting specs to MSW, several naming Capybara explicitly, and one removed "Capybara examples covered by MSW drawer tests". The 2020-era MirageJS frontend-integration layer was deleted, and the guide changed to "Default to frontend integration tests" [8][45].

**Did the steer to a pyramid succeed?** By GitLab's own counts, yes, in proportion. System tests were 10.9% of all tests on 2019-05-01 and 4.31% on 2025-02-03. Unit tests rose from 71% to 75.66% [13][16]. In absolute terms every level grew. System tests nearly doubled (6,440 → 12,444), while unit and integration tests grew about five-fold (41,809 → 218,459 and 10,577 → 57,127).

The very first published count (2019-04-16) looks different: system tests at 24.6% of CE tests, unit tests at 37.8% [11]. It should not be read as the starting point. Five weeks later the same author replaced it with numbers produced by the new folder-based classification. CE unit tests jumped from 8,403 to 32,031, and EE system tests fell from 6,585 to 969, the latter apparently because the EE column stopped including CE tests. Both are changes of method, not of the suite (inference from the two diffs).

## 10. Timeline

| date | what changed | who drove it | link |
|---|---|---|---|
| 2014-09-02 | SimpleCov already in use (updated to 0.9.0) | DJ Mountney | [56] |
| 2016-03-08 | Proposal to freeze new Spinach features; agreed by the team | Robert Speicher | [17] |
| 2016-03-30 | First testing style guide, with the Spinach freeze | Robert Speicher | [18] |
| 2016-06-29 | Coveralls removed as unused | Zeger-Jan van de Weg | [56] |
| 2017-03-13 | GitLab QA end-to-end tests added to the CE/EE repositories | Grzegorz Bizon | [46] |
| 2017-08-11 | Flaky examples detected (via `rspec-retry`) and tracked in a report | Rémy Coutable | [27] |
| 2017-10-11 | Testing guide split; "Testing levels" page with the priority triangle and "Consider not writing a system test" | Rémy Coutable | [15] |
| 2018-05-15 | Spinach removed | blackst0ne (community) | [20] |
| 2018-10-09 | Jest chosen over Karma after evaluation | @winh (frontend), Tim Zallmann | [21] |
| 2018-12-05 | Jest test environment set up (`spec/frontend`) | @winh | [23] |
| 2019-01-15 | `quarantine:` metadata for Rails specs (QA had it on 2019-01-09) | Rémy Coutable, Mark Lapierre | [28] |
| 2019-04-17 | First published distribution of tests per level | Rémy Coutable | [11] |
| 2019-05-22 | `Quality::TestLevel`; CI split into unit, integration and system jobs; recount (unit 71%, system 10.9%) | Rémy Coutable | [16] |
| 2019-10-23 | Sidekiq test mode changed from inline to fake | Rémy Coutable | [42] |
| 2020-03-10 | Feature specs served through Workhorse | Nick Thomas | [54] |
| 2020-09-14 | `rspec fail-fast` job | Albert Salim | [35] |
| 2020-12-09 | Crystalball-based test detection in RSpec jobs | Albert Salim | [34] |
| 2020-12-15 | Epic: no new controller specs, use request specs | Takuya Noguchi | [41] |
| 2021-01-08 | Predictive selection shows ~10% miss rate; goal pivots to early feedback | Albert Salim, Kyle Wiebers | [33] |
| 2021-03-11 | Workhorse development moved into this repository | Jacob Vosmaer | [55] |
| 2021-07-26 | Minimal (predictive) RSpec before approval, full suite after | Albert Salim | [36] |
| 2021-09-03 | Karma removed | Vitaly Slobodin, Paul Slaughter | [26] |
| 2021-12-01 | `undercover` fails MRs whose changed lines have zero coverage | Thong Kuah | [40] |
| 2022-01-25 | Failed specs retried in a new RSpec process | Rémy Coutable | [30] |
| 2022-03-08 | Pact contract testing set up | Tomislav Nikić | [43] |
| 2022-08-23 | New backend specs run in random order | Peter Leitzen | [51] |
| 2023-04-28 | Fast quarantine | Rémy Coutable | [29] |
| 2024-01-18 | `rspec-retry` phased out, directory by directory (done 2024-03) | Lin Jen-Shin | [31] |
| 2024-05-31 | Pipeline tiers; full end-to-end only in tier 3 (2024-06-19) | David Dieulivol | [38] |
| 2024-07-10 | "Unhealthy tests" page replaces the flaky-tests page | Rémy Coutable | [9] |
| 2025-02-03 | Distribution recounted: unit 75.66%, integration 19.79%, system 4.31%, e2e 0.24% | John McDonnell | [13] |
| 2025-07-09 | Testing strategy page: "No duplication, no waste" | Chloe Liu | [3] |
| 2025-09-22 | "We use the testing pyramid to guide test distribution" | Amy Phillips | [14] |
| 2026-02-04 | Handbook: automated quarantine MRs, 3-day fast and 3-month long-term limits, automatic deletion | Jay McCure | [48] |
| 2026-03-16 | `rspec-retry` gem removed | andrey | [32] |
| 2026-03-27 | Jest + MSW frontend integration tests introduced | Natalia Tepluhina | [44] |
| 2026-05-05 | GitLab Duo selects system specs in tier-2 pipelines | Jay McCure | [39] |
| 2026-05-06 | RuboCop cap of 25 examples per feature spec file | Eduardo Sanz García | [49] |
| 2026-08-05 | Handbook: 24-hour flaky-test SLO, escalation to incident | drew stachon | [47] |
| 2026-09-17 | MirageJS `spec/frontend_integration` layer deleted; MSW suite is the frontend integration layer | Frédéric Caplette | [45] |

## 11. The arguments, turn by turn

### Spinach to RSpec (2016–2018)

*Pain.* Robert Speicher opened foss#14121 on 2016-03-08 [17]:

> I've been thinking that we should put a freeze on new Spinach feature tests and instead focus on RSpec exclusively, for a couple reasons.
> — Robert Speicher, 2016-03-08

His reasons were that "Natural Language" isn't a benefit for a team without non-technical readers, that Spinach is "a pain to develop and debug", and that it "*induces* bad test design". Yorick Peterse added: "I think Gherkin/Spinach is a waste of time (literally since it keeps timing out). Long live RSpec." [17]

*Against.* Dmytro Zaporozhets defended what Gherkin bought:

> Spinach tests forced people to test what user see instead of testing what is in database. Bad example of feature test is that you submit form and check database record instead of what is rendered on web page to user. So this is something we would like to enforce with Rspec feature tests too .
> — Dmytro Zaporozhets, 2016-03-09

Speicher agreed: "Yes, definitely. The point of a feature/integration test is to keep it as close as possible to a real-world use case." [17] Stan Hu asked about speed: "Would the RSpec tests run faster? I'm wondering if the timeout issues that we get with existing Spinach tests would still be an issue given that we still need to use Capybara and PhantomJS." Speicher could not promise it, and floated moving some cases down: "some of our feature specs could probably be view specs, which are _way_ faster." Zaporozhets pushed back: "not a big fan of testing views separately from controllers. You can have a good coverage but running real request give you 500 error on the page." [17] Ten months later Grzegorz Bizon summed up for an outside critic: "we did not resign from using high level feature tests. We simply moved from using Spinach/Cucumber gherkin-like language in favor of using RSpec" [17].

*Numbers.* CI capacity moved with the conversion. On 2017-10-19 Spinach went down to 4 parallel nodes and RSpec up to 26 (foss!14936). On 2018-02-21 the split was 2 and 28 (foss!16713). On 2018-05-15 Spinach was gone [19][20]. No before-and-after runtime was published; Speicher's "We could convert one of our larger feature files and run benchmarks on both" was not followed up in the thread. Zaporozhets's wish to assert "what is rendered on web page" rather than the database did not become a rule. The levels page says white-box system tests set "expectations … often … on the database or objects state" [2].

### Testing levels and the published distribution (2017–2025)

The 2017 text set the policy that still stands, under "Consider not writing a system test" [15]:

> If we're confident that the low-level components work well (and we should be if we have enough Unit & Integration tests), we shouldn't need to duplicate their thorough testing at the System test level.
> — Rémy Coutable, `testing_levels.md`, 2017-10-11

The same 2017 text goes on: "It's very easy to add tests, but a lot harder to remove or improve tests, so one should take care of not introducing too many (slow and duplicated) tests." [2][15]

*Numbers.* GitLab's published counts per level:

| as of | e2e | system | integration | unit | total | source |
|---|---:|---:|---:|---:|---:|---|
| 2019-04-16 (CE only) | 67 (0.3%) | 5,457 (24.6%) | 8,298 (37.2%) | 8,403 (37.8%) | 22,225 | [11] |
| 2019-05-01 (CE+EE) | 99 (0.17%) | 6,440 (10.9%) | 10,577 (17.9%) | 41,809 (71%) | 58,925 | [16] |
| 2025-02-03 (CE+EE, "estimated") | 704 (0.24%) | 12,444 (4.31%) | 57,127 (19.79%) | 218,459 (75.66%) | 288,734 | [13] |
| 2026-10-11, this report, static `it` count | 571 (0.24%) | 8,998 (3.80%) | 36,234 (15.29%) | 191,178 (80.67%) | 236,981 | §4 |

No MR or method was found for the 2025 recount (commit b4396bc8 has no linked MR). The 2025-09 wording explicitly ties the table to the pyramid: "This should give more clarity to the numbers presented in the test distribution table" (Amy Phillips) [14]. The proportions were never a gate. They are a published observation that moved in the stated direction.

### Karma to Jest (2018–2021)

*Pain.* The evaluation issue (foss#49171, opened 2018-07-12 by the frontend engineer whose account is now shown as "Inactive Account"; colleagues address them as @winh) listed the problems with Karma and Jasmine: "tests are all running in the same context and not sandboxed", "we are relying on the now unmaintained jasmine-jquery", and "we have no snapshots" [21]. One criterion was that "running the tests does not take much longer than currently (2 minutes)".

*Result.* On 2018-10-09 the evaluator reported [21]:

> test run faster even when run individually (roughly by a factor of 2 to 3)
> …
> not testing in a real browser (we can probably handle this separately)
> …
> For me the positive aspect outweigh the negative ones, so I'm closing this issue with the result that we should migrate to Jest.
> — @winh, 2018-10-09

Paul Slaughter asked whether bundled code would still be tested, and got the reply: "We use code bundled by Webpack in the feature specs which I think would be enough." [21] Jose Ivan Vargas had warned that "we would lose the ability to use headless chrome in our frontend tests, since Jest only supports JSDom at the moment" [21]. The evaluator also proposed using the new `spec/frontend/` directory to enforce rules that were "difficult to enforce for the existing tests": "no dependencies between tests", "no unmocked Ajax requests", "no `setTimeout()`" [21].

*Numbers.* The 2–3x speed-up was measured on a proof of concept, not on the whole suite. By November 2020 only the browser-coupled specs were left [26]. They went to Jest or to RSpec feature specs, and Karma was removed on 2021-09-03 [26]. At the snapshot there are 6,604 Jest spec files and none in Karma.

### Predictive selection, fail-fast and tiers (2020–2026)

*Pain.* MR pipelines ran the whole suite on every push. Kyle Wiebers opened #222369 on 2020-06-15: "Consider experimenting with dynamic analysis to identify a test mapping and leverage for executing related tests based on the changed files." [33]

*Argument.* After a one-week experiment, Albert Salim reported [33]:

> Given the data from the 1 week experiment (without excluding flaky tests), we are seeing potentially on average 10% miss rate.
> …
> @kwiebers and I discussed this and we think it may be best to pivot the objective from cost saving to providing early feedback on failures.
> — Albert Salim, 2021-01-08

Pavel Shutsin, who had built such a system elsewhere, agreed: "Yes I think it's unsafe to rely on prediction builds only for MRs until we get close to 100% of prediction safety." [33]

*Numbers.* On a sample MR, the minimal-before-approval change cut mean job duration from 21:24 to 11:08 for `rspec unit`, from 22:07 to 10:44 for `rspec integration`, and from 16:51 to 13:05 for `rspec system` [36]. In February 2024, 61% of pipelines run were end-to-end pipelines, "E2E (38%) and E2E-GDK (23%)". That was the stated reason for tiers: "run time-consuming pipelines less often" (David Dieulivol) [38]. Before 2026-05, tier-2 pipelines "ran all system tests unconditionally" (Jay McCure); Duo now narrows them [39]. No published figure for aggregate savings was found.

### Flakiness: retries, quarantine, SLOs (2017–2026)

*Quarantine.* In January 2019 Mek Stittri asked whether a long-flaky boards spec should be quarantined. That spec had been "flagged as flaky **430** times" between 2017-10-07 and 2018-04-04. Rémy Coutable replied: "We'd have to port the quarantine support to Rails tests (currently this is only implemented for QA tests)." He did so the next day [28].

*Retries.* In January 2024, after one job "took 30 minutes to retry 3 specs" (David Dieulivol) [31], the team debated limits on retries. Peter Leitzen proposed: "I wonder if we should add a timeout to each example execution and fail if the timeout is exceeded." Lin Jen-Shin answered [31]:

> Honestly, I don't think this is doing good for us in the long run, but if I remember correctly, we once removed it and the pipelines became too flaky that we have to add it back.
> — Lin Jen-Shin, 2024-01-16

He also suspected "there are tests which rely on being retried to pass" and worried that "complexity is adding up with all the mechanisms we're adding". Rémy Coutable settled it: "I would be in favor of experimenting not using `rspec-retry` now that we retry in a new RSpec process." [31] The phase-out quarantined eleven specs that failed once retries stopped [31]. The gem itself went in 2026: "We have been retrying tests in a separate process for a few years now so there is no reason for this gem to be used." (andrey) [32]

*Numbers.* At the snapshot, 390 `quarantine` metadata occurrences sit in 258 of the 23,121 RSpec spec files under `spec/` and `ee/spec/` (1.1%). In GitLab QA there are 99 occurrences in 80 of 379 end-to-end spec files (21%). The highest-level suite is also the most quarantined. 7,448 backend spec files are still exempt from random order four years after the switch [51]. No public time series of flaky-test counts was found. The handbook's dashboards are internal [47].

### Capybara to MSW (2026)

*Argument.* The founding MR set out the trade [44]:

> Capybara feature spec: ~5m15s per context (10m30s total for both contexts)
> Jest integration tests: ~13-14s for the same coverage
> …
> Con: The full backend stack isn't exercised - mocked responses always succeed, so DB constraints, authorization edge cases, and server-side validations aren't tested
> Takeaway: Best suited for verifying frontend integration - that components, Apollo cache, and UI state work together correctly. These complement, not fully replace, feature specs
> — Natalia Tepluhina, 2026-03-27

She also reported that the new tests caught a regression "live for ~6 weeks". "A feature spec didn't catch the same regression because it was waiting for refetch to happen." [44] Six months later the practice had gone further than "complement": MRs titled "Remove Capybara examples covered by MSW drawer tests" (2026-09-23) and "Migrate Security Tab spec from Capybara to MSW" (2026-10-06) delete the browser test once the MSW test exists [45]. When the older MirageJS layer was deleted, Frédéric Caplette wrote: "Every spec that lived there moved to a plain Jest unit spec in the preceding commits; coverage is unchanged." [45]

*Numbers.* The suite is new, so the before-and-after is only visible as the guide's change of default and the 85 EE MSW spec files at the snapshot. For the post's question this is the most relevant turn. GitLab is replacing real-backend browser tests with in-process tests on fakes, and it says why: speed and flakiness, at a stated cost in confidence about authorization and validation.

## 12. Coverage

**Measured: yes. Gated on a percentage: no. Gated on changed lines: yes, since 2021-12-01.**

- SimpleCov runs in CI and has since at least 2014 (foss!180 updated it on 2014-09-02) [56]. Coveralls was configured in 2016 and removed on 2016-06-29 as unused [56]. Codecov: not found in the tree or in MR titles.
- Today coverage is collected per suite: SimpleCov to LCOV for RSpec, Istanbul for Jest, Go coverage for Workhorse, and Coverband plus Istanbul for end-to-end runs. It is merged and exported to ClickHouse "to power test selection, coverage analytics, and flaky test analysis" [6][7]. No minimum (`minimum_coverage`, `coverageThreshold`) is configured anywhere in the snapshot.
- On 2021-12-01 Thong Kuah added `undercover`: "This will **fail** the pipeline if changes introduced in this MR has zero coverage" [40]. The trigger was an incident where "there was no coverage for the changed method, due to stubbing, and also exclusion from coverage reports" (Darva Satcher, 2021-11-17) [40]. The gate has an escape label, `pipeline:skip-undercoverage`, and is skipped on `pipeline::expedited` [6].
- The guide's only target is advisory: "Use the coverage reports to ensure your tests cover 100% of your code." (added 2020-02-07) [10][56].
- Coverage also became a test-selection input. Crystalball mapped tests with a coverage strategy from 2020 [34]. !147076 (2024-03-21) made the described-class strategy the default, and the current docs say the mapping holds both [7][56].

## Chart-ready table

`pct` is the share of the 4,068,276-line whole (13 product categories, helpers excluded). Rows marked "beside" are not part of the whole; their pct is given in parentheses for scale. `tests` is the static count described in §4.

category | maps_to (post taxonomy) | lines | pct | files | tests
---|---|---:|---:|---:|---:
RSpec unit (product folders) | unit + adapters (in-process, real PostgreSQL; 4.8% of lines are pure `fast_spec_helper` units) | 2138356 | 52.6 | 17626 | 191178
Jest unit and component | fast (in-process on fakes, but the main proof for the UI) | 1083136 | 26.6 | 6604 | 80527
RSpec integration | api (Rack stack in-process, real DB) | 576864 | 14.2 | 3121 | 36234
RSpec system / feature | e2e (white-box; 87% of files run a real browser) | 123893 | 3.0 | 1397 | 8998
internal gems (RSpec) | unit | 38562 | 0.9 | 310 | 3696
Workhorse (Go) | unit + adapters_free (`httptest` stand-ins) | 30749 | 0.8 | 159 | 884
RSpec background migration | adapters_free (no exact slot) | 21025 | 0.5 | 143 | 819
GitLab QA end-to-end, browser_ui | e2e | 19600 | 0.5 | 312 | 442
RSpec migration | adapters_free (no exact slot) | 10881 | 0.3 | 221 | 665
RSpec frontend fixture generators | no slot (backend-to-frontend bridge) | 10759 | 0.3 | 116 | 519
Jest frontend integration (MSW) | fast (no exact slot) | 8481 | 0.2 | 85 | 383
GitLab QA end-to-end, api | api | 5518 | 0.1 | 67 | 129
contract (Pact) | no slot | 452 | 0.0 | 8 | 22
RSpec tooling (beside) | tooling | 72401 | (1.8) | 610 | 5773
QA framework tests (beside) | tooling | 12974 | (0.3) | 120 | 1045
Jest tooling (beside) | tooling | 4502 | (0.1) | 25 | 325
Storybook stories (beside; examples run as tests) | no slot | 16300 | (0.4) | 270 | 945
docs screenshot specs (beside) | tooling | 98 | (0.0) | 2 | 8

## Sources

All GitLab links are to `gitlab.com`. "foss" means `gitlab-org/gitlab-foss` (formerly `gitlab-ce`); "!" without a prefix is `gitlab-org/gitlab`. Dates are merge, creation or comment dates as stated.

1. GitLab repository at `aeb834be5899909c5b720042693640c59f220dc3`, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/tree/aeb834be5899909c5b720042693640c59f220dc3
2. `doc/development/testing_guide/testing_levels.md` at the snapshot, 2026-10-11 (lines dated by blame as quoted). https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/doc/development/testing_guide/testing_levels.md
3. `doc/development/testing_guide/testing_strategy.md`, added by Chloe Liu in !193990, merged 2025-07-09. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/193990
4. `tooling/quality/test_level.rb` at the snapshot, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/tooling/quality/test_level.rb
5. `spec/spec_helper.rb` at the snapshot, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/spec/spec_helper.rb
6. `doc/development/pipelines/_index.md` and `.gitlab/ci/` at the snapshot, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/doc/development/pipelines/_index.md
7. `doc/development/pipelines/code_coverage.md` at the snapshot, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/doc/development/pipelines/code_coverage.md
8. `doc/development/testing_guide/frontend_testing.md` at the snapshot, 2026-10-11; "Default to frontend integration tests" dated 2026-09-18 (!255723). https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/doc/development/testing_guide/frontend_testing.md
9. `unhealthy_tests.md` and `quarantining_tests.md` at the snapshot, 2026-10-11; "Unhealthy tests" page introduced by Rémy Coutable in !147004, 2024-07-10. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/147004
10. `doc/development/testing_guide/best_practices.md` at the snapshot, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/blob/aeb834be5899909c5b720042693640c59f220dc3/doc/development/testing_guide/best_practices.md
11. foss!27431 "Better document the current states of our testing levels", Rémy Coutable, merged 2019-04-17 (commit b16ee077). https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/27431
12. `.rubocop.yml`, `.rubocop_todo/rspec/*` and `rubocop/cop/rspec/*` at the snapshot, 2026-10-11. https://gitlab.com/gitlab-org/gitlab/-/tree/aeb834be5899909c5b720042693640c59f220dc3/rubocop/cop/rspec
13. Commit b4396bc8 "Docs: update number of tests per level", John McDonnell, 2025-02-03. https://gitlab.com/gitlab-org/gitlab/-/commit/b4396bc8c28a6f3a0e44c03e0ca16bb9c1a233ec
14. !205674 "Update the testing pyramid docs to add some clarity about how we use the pyramid", Amy Phillips, merged 2025-09-22. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/205674
15. Commit 676840ff "Refactor the Development documentation, and divide the Testing documentation into multiple pages", Rémy Coutable, 2017-10-11. https://gitlab.com/gitlab-org/gitlab/-/commit/676840ff9c4e85e44b2f2c6e7c92f62f834e20aa
16. foss!27514 "Reorganize test jobs by level", Rémy Coutable, merged 2019-05-22; re-applied as commit 6145ddf5 the same day (adds `lib/quality/test_level.rb` and the 2019-05-01 table). https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/27514 and https://gitlab.com/gitlab-org/gitlab/-/commit/6145ddf515f93fcc7ed873b911b6369cc2bc0462
17. foss#14121 "Let's stop adding new Spinach features", Robert Speicher, 2016-03-08, with discussion through 2017-01-26. https://gitlab.com/gitlab-org/gitlab-foss/-/issues/14121
18. foss!3465 "First pass at a Testing styleguide", Robert Speicher, 2016-03-30. https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/3465
19. foss#23036 "Replace all Spinach tests with Rspec feature tests", Connor Shea, 2016-10-06, closed 2018-05-15; foss!14936 (2017-10-19) and foss!16713 (2018-02-21) on CI nodes. https://gitlab.com/gitlab-org/gitlab-foss/-/issues/23036 , https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/14936 , https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/16713
20. foss!18869 "Remove Spinach", blackst0ne, merged 2018-05-15. https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/18869
21. foss#49171 "Evaluate new environment for frontend tests", opened 2018-07-12, result note 2018-10-09. https://gitlab.com/gitlab-org/gitlab-foss/-/issues/49171
22. foss#52483 "Migration plan from Karma to Jest", 2018-10-10. https://gitlab.com/gitlab-org/gitlab-foss/-/issues/52483
23. foss!23406 "Setup Jest test environment", merged 2018-12-05. https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/23406
24. foss!23965 "Fail for unmocked axios requests in Jest", merged 2019-02-21; current helper from commit eb45cb8c (Martin Hanzel, 2019-07-17). https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/23965
25. !26161 "Add danger rule to favor jest over karma", Lukas Eipert, merged 2020-03-03. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/26161
26. !68977 "Remove Karma and anything related", Vitaly Slobodin, merged 2021-09-03; epic &4900 "Finish karma", Paul Slaughter, 2020-11-12. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/68977 , https://gitlab.com/groups/gitlab-org/-/epics/4900
27. foss!13021 "Detect and keep track of flaky specs", Rémy Coutable, merged 2017-08-11. https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/13021
28. foss!24022 "Allow tests to be quarantined" (QA), Mark Lapierre, 2019-01-09; foss!24369 "Allow to quarantine tests", Rémy Coutable, 2019-01-15; foss#45044 comments of 2019-01-11 and 2019-01-14. https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/24369 , https://gitlab.com/gitlab-org/gitlab-foss/-/issues/45044
29. !118482 "ci: Allow to fast-quarantine RSpec examples", Rémy Coutable, merged 2023-04-28. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/118482
30. !76839 "ci: Retry failed specs in a new process after the initial run", Rémy Coutable, merged 2022-01-25. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/76839
31. #438270 (David Dieulivol, 2024-01-15, discussion 2024-01-15/16); #438388 "Drop `rspec-retry` except for spec/features" (Lin Jen-Shin, 2024-01-16, closed 2024-03-11); !141874 merged 2024-01-18. https://gitlab.com/gitlab-org/gitlab/-/issues/438270 , https://gitlab.com/gitlab-org/gitlab/-/issues/438388
32. !225448 "Remove rspec-retry gem usage", andrey, merged 2026-03-16. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/225448
33. #222369 "Consider dynamic analysis test mapping to streamline test execution", Kyle Wiebers, 2020-06-15; comments 2021-01-08 (Albert Salim) and 2021-01-11 (Pavel Shutsin). https://gitlab.com/gitlab-org/gitlab/-/issues/222369
34. !44968 (2020-10-28) Crystalball mapping from coverage; !49446 (2020-12-09) test detection in RSpec jobs; !48741 (2020-12-14) minimal RSpec jobs; all Albert Salim. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/49446
35. !41081 "Fail pipeline early when there is rspec failure related to MR changes", Albert Salim, merged 2020-09-14. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/41081
36. !64903 "Run minimal rspec jobs before merge request is approved", Albert Salim, merged 2021-07-26. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/64903
37. !108920 "Minimal to predictive job rename", Jennifer Li, merged 2023-01-17. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/108920
38. Epic "Pipeline tiers in merge requests", David Dieulivol, 2024-05-02; !154918 (2024-05-31); !155099 "Run full e2e tests in pipeline tier 3 and above" (2024-06-19). https://gitlab.com/groups/gitlab-org/quality/engineering-productivity/-/epics/58 , https://gitlab.com/gitlab-org/gitlab/-/merge_requests/155099
39. !229593 "Use Duo test selections in tier2 pipelines for system tests", Jay McCure, merged 2026-05-05. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/229593
40. #345962, Darva Satcher, 2021-11-17; !74859 "Use undercover to enforce changes in MR has coverage", Thong Kuah, merged 2021-12-01. https://gitlab.com/gitlab-org/gitlab/-/issues/345962 , https://gitlab.com/gitlab-org/gitlab/-/merge_requests/74859
41. Epic &5076 "Transition from controller specs to request specs", Takuya Noguchi, opened 2020-12-15 (still open); !50566 Danger warning, 2020-12-31. https://gitlab.com/groups/gitlab-org/-/epics/5076 , https://gitlab.com/gitlab-org/gitlab/-/merge_requests/50566
42. !15479 "Change Sidekiq testing mode to `fake` instead of `inline`", Rémy Coutable, merged 2019-10-23. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/15479
43. !80814 "Basic setup for contract testing", Tomislav Nikić, merged 2022-03-08. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/80814
44. !223953 "Add Frontend integration tests with jest and MSW", Natalia Tepluhina, merged 2026-03-27. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/223953
45. !255454 "Delete unused frontend_integration test layer with MirageJS", Frédéric Caplette, 2026-09-17; !255723 rename and ESLint guard, 2026-09-18; !255829 (2026-09-23) and !258558 (2026-10-06) Capybara removals. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/255454 , https://gitlab.com/gitlab-org/gitlab/-/merge_requests/255829
46. foss!9370 "Add GitLab QA integrations tests to GitLab CE / EE", Grzegorz Bizon, merged 2017-03-13. https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/9370
47. Handbook "Flaky tests", https://handbook.gitlab.com/handbook/engineering/testing/flaky-tests/ ; wording dated by commits 2a01d57e (David Dieulivol, 2025-12-18) and 9dcedf91 (drew stachon, 2026-08-05) in `gitlab-com/content-sites/handbook`. https://gitlab.com/gitlab-com/content-sites/handbook/-/commit/9dcedf91d0a345369a0c780113cb61628bf4cc4f
48. Handbook "Quarantine process", https://handbook.gitlab.com/handbook/engineering/testing/quarantine-process/ ; consolidated 2026-01-08 (commit 2a35a9d6, Jay McCure); timelines and automation 2026-02-04 (commit 80ac67cc, Jay McCure). https://gitlab.com/gitlab-com/content-sites/handbook/-/commit/80ac67cc8e9119a90be395d4781fb4062889cdb7
49. !233270 "Add RuboCop cop to limit examples in feature specs", Eduardo Sanz García, merged 2026-05-06; !236884 moved it to gitlab-styles, 2026-05-22. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/233270
50. Spec cops: `FactoriesInMigrationSpecs` commit 4b035896 (Rémy Coutable, 2018-04-06); !19164 any_instance_of autocorrect (Arturo Herrero, 2019-11-07); !101190 `FactoryBot/AvoidCreate` (Alina Mihaila, 2022-10-18); !106490 `AvoidTestProf` (Mario Celi, 2022-12-12); !109492 feature category validation (Peter Leitzen, 2023-01-26); `AvoidConditionalStatements` config (Alina Mihaila, 2023-05-09); `AvoidWaitForRequests` commit 9fc732ef (Heinrich Lee Yu, 2026-05-01). https://gitlab.com/gitlab-org/gitlab/-/merge_requests/101190
51. !93137 "Run all new backend specs in random order", Peter Leitzen, merged 2022-08-23. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/93137
52. !162499 "Test: Add BrowserConsoleHelpers for Capybara", Paul Slaughter, merged 2024-08-22. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/162499
53. !67019 "Prevent cross-joins across databases", Kamil Trzciński, merged 2021-08-05; !131911 "Enforce no transactions on specs with delete tables strategy", Mario Celi, merged 2023-09-19. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/67019 , https://gitlab.com/gitlab-org/gitlab/-/merge_requests/131911
54. Commit c1e5ad36 "Run feature specs through Workhorse", Nick Thomas, 2020-03-10. https://gitlab.com/gitlab-org/gitlab/-/commit/c1e5ad3620f05a27f1c04ec8a33b8aa71086bc12
55. !48690 "Vendor gitlab-workhorse into the main repository" (2020-12-02) and !54941 "Move Workhorse development to main GitLab repository" (2021-03-11), Jacob Vosmaer. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/54941
56. Coverage history: foss!180 "Update simplecov to 0.9.0" (2014-09-02); foss!5001 "Remove coveralls as its unused" (2016-06-29); commit 9c7cd6e1 "Add simple instructions on coverage" (Robert May, 2020-02-07); !147076 "Change our Crystalball strategy from Coverage to DescribedClass" (David Dieulivol, 2024-03-21). https://gitlab.com/gitlab-org/gitlab-foss/-/merge_requests/5001 , https://gitlab.com/gitlab-org/gitlab/-/merge_requests/147076
57. Post "Why the drama about duplicating tests?", this blog, 2026-10-11, section "How that sits against general practice" (taxonomy and Robinauts figures).
58. !30422 "Fix file descriptor leak with Capybara", Stan Hu, merged 2020-04-28 (current `webmock_enable!` form). https://gitlab.com/gitlab-org/gitlab/-/merge_requests/30422
59. !239574 "Skip test-storybook on tier-1 pipelines", Kev Kloss, merged 2026-06-09. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/239574
60. !168541 "Auto-retry jobs when they failed due to a known flaky test", David Dieulivol, merged 2024-10-23. https://gitlab.com/gitlab-org/gitlab/-/merge_requests/168541

## Appendix: commands and counting decisions

### Snapshot

```sh
SP=<session scratchpad>
mkdir -p $SP/gitlab-clone && cd $SP/gitlab-clone
git clone --depth 1 --single-branch --branch master https://gitlab.com/gitlab-org/gitlab.git repo
git -C repo log -1 --format='%H %cI'
# aeb834be5899909c5b720042693640c59f220dc3 2026-10-11T16:59:14-04:00
```

The clone came from gitlab.com (the canonical repository), not the GitHub mirror. It holds 112,215 files (1.4 GB at depth 1). Nothing in the clone was executed. All scripts ran from outside it with `python3 -I`, taking paths as arguments. The clone was deleted at the end.

### Counting

```sh
TOOL=notebooks/X-shapes-of-tests/tools/count_lines.py
python3 -I $TOOL repo --by-file > count_root.csv                     # 72,022 rows

# Deviation: the tool's default excludes "*/build/*", "*/coverage/*" and "*/vendor/*" also drop
# real GitLab source and spec folders (spec/lib/gitlab/ci/build, lib/gitlab/ci/pipeline/build,
# ee/spec/models/app_sec/fuzzing/coverage, qa/qa/vendor page objects, ...). Without editing the tool,
# re-run it rooted at each such folder and prefix the paths:
(cd repo && find . -path ./.git -prune -o -path '*/node_modules' -prune -o -type d \( -name build -o -name coverage \) -print | sed 's|^\./||'; echo qa/qa/vendor; echo qa/spec/vendor) | sort > rerooted_dirs.txt   # 41 folders
while read d; do python3 -I $TOOL "repo/$d" --by-file | tail -n +2 | sed "s|^|$d/|"; done < rerooted_dirs.txt > count_rerooted.csv
# merge, keeping the first row per path            -> 72,216 rows (194 added by re-rooting)
```

Completeness check: `find repo -path ./.git -prune -o -path '*/node_modules' -prune -o -path ./vendor -prune -o -type f` filtered to the tool's default extensions, minus `*.min.js`, gives 72,214 files, all present in the merged set. The two extra rows are `db/ci_structure.sql` and `db/sec_structure.sql`, symlinks that the tool follows; they are classed "other". Excluded on purpose by the tool's defaults and kept out: top-level `vendor/` (vendored code, including 12 spec files under `vendor/gems`), and `node_modules` folders that are test fixtures of a Jest script test.

`gitlab.counts.csv` holds all 72,216 rows: the tool's columns `path,files,lines,blank,comment,code` plus `category`. Edition is the path prefix (`ee/` is EE; `qa/`, `gems/`, `workhorse/` and `cells-mailroom/` are their own). Categories with `prod_` are production; `*_helpers`, `qa_framework` and `rspec_helpers` are helpers; `data`, `generated`, `migrations_code` and `other` are excluded.

Tool limits, as the brief asks: it does not recognize docstrings. In Ruby it also misses `=begin`/`=end` block comments, which therefore count as code. `.vue` files count template, script and style lines; only `//`, `/* */` and whole-line `<!-- -->` comments are removed. HAML is not in the tool's extension list. It was measured separately with `python3 -I $TOOL repo --ext .haml --include app ee/app --depth 1`: 2,404 files and 38,132 non-blank lines (HAML comments not removed). It is not included in production totals.

### Classification rules (in order)

1. **`spec/` and `ee/spec/`**
   - `fixtures/` at the top, `frontend/fixtures/static/` and `frontend/scripts/infection_scanner/fixtures/` → `data`.
   - `contracts/`: `*_spec.rb` or `*[._]spec.(js|ts)` → `contract`; `contracts/contracts/*` and any `/fixtures/` → `data`; the rest → `contract_helpers`.
   - `frontend/`:
     - `frontend/fixtures/**/*.rb` → `rspec_frontend_fixture` (TestLevel's `frontend_fixture` level).
     - Other `frontend/fixtures/**` → `data`.
     - Files matching Jest's `testMatch` (`[._]spec.(js|ts)`):
       - under `ee/spec/frontend/integration/` → `jest_integration`;
       - under `spec/frontend/{scripts,config,__helpers__}/` → `jest_tooling`;
       - otherwise → `jest_unit`.
     - All other code files under `frontend/` (`mock_data.js`, `__helpers__`, `__mocks__`, `test_setup.js`, MSW handlers and fixture variants) → `jest_helpers`.
   - `docs_screenshots/` → `rspec_docs_screenshots`.
   - `support/`, `factories/` and files directly in `spec/` or `ee/spec/` → `rspec_helpers`.
   - `*_spec.rb` elsewhere → level by `Quality::TestLevel` as at the snapshot. Its regexes are tried in its own order (background_migration, migration, frontend_fixture, unit, integration, system). Every file got a level; none were unclassified.
   - From the `unit` level, the folders `rubocop`, `tooling`, `scripts`, `keeps`, `dot_gitlab_ci`, `haml_lint`, `support_specs` and `factories_specs` were moved to `rspec_tooling`. This is a judgment call: they test the repository, not the product. `test_level.rb` itself comments "tooling and dot_gitlab_ci might be worth to move to another level".
   - Any other `.rb` inside a spec folder (shared examples next to specs) → `rspec_helpers`.
2. **`qa/`**
   - `qa/qa/specs/features/{api,ee/api}/**/*_spec.rb` → `e2e_api`.
   - `qa/qa/specs/features/{browser_ui,ee/browser_ui}/**/*_spec.rb` → `e2e_browser_ui`.
   - Any path containing `/fixtures/` → `data`.
   - `qa/spec/**/*_spec.rb` and `qa/gems/*/spec/**/*_spec.rb` → `qa_framework_tests` (beside the whole); other files under those spec folders → `qa_framework_test_helpers`.
   - Everything else under `qa/` (page objects, resources, runtime, `qa/qa/vendor` page objects, QA gems' `lib`) → `qa_framework` (helpers).
3. **`gems/*` and `cells-mailroom/`**
   - `gems/error_tracking_open_api` → `generated` (its README says it is generated by OpenAPI Generator).
   - `spec/**/*_spec.rb` → `gems_unit`; other files in `spec/` → `gems_helpers`, except `/fixtures/` → `data`.
   - `lib/` and `app/` → `prod_gems`.
4. **`workhorse/`**: `*_test.go` → `workhorse_go`; `internal/testhelper/` → helpers; `testdata/` → `data`; other `.go` → `prod_workhorse`.
5. **Storybook**: `*.stories.js` and `*.stories.ts` → `storybook_stories`. These are examples that double as tests, kept beside the whole and not included in it.
6. **`ee/frontend_islands/`**: `*_spec.ts` (Vitest) → `jest_unit` (EE); `src/` → `prod_frontend`.
7. **Production**
   - `app/assets/javascripts/` and `ee/app/assets/javascripts/` → `prod_frontend`; other `app/assets/` → other.
   - The rest of `app/`, `ee/app/`, `lib/`, `ee/lib/`, `sidekiq_cluster/` and `metrics_server/` → `prod_backend`.
   - `config/**/*.rb` and `ee/config/**/*.rb` → `prod_config`, counted with the backend.
   - `(ee/)db/(*/)(post_)migrate/` → `migrations_code`. Excluded from production; used only for the migration ratio, without `db/click_house`.
   - Everything else (`scripts`, `tooling`, `rubocop`, `danger`, `keeps`, `db/*.sql`, `ee/elastic/migrate`, root configs, `storybook/` config) → `other`.

**The whole** = `rspec_unit`, `rspec_integration`, `rspec_system`, `rspec_migration`, `rspec_background_migration`, `rspec_frontend_fixture`, `contract`, `jest_unit`, `jest_integration`, `e2e_browser_ui`, `e2e_api`, `gems_unit`, `workhorse_go`. Beside it: `rspec_tooling`, `jest_tooling`, `qa_framework_tests`, `storybook_stories`, `rspec_docs_screenshots`. Workhorse and the internal gems are inside the whole because they are product components in this repository. Without them, the Rails and frontend product tests total 3,998,965 lines.

**Collapsed view (§4).**
- e2e = `e2e_browser_ui` + `rspec_system` files matching the `:js` regex.
- api = `rspec_integration` + `rspec_system` files not matching it + `e2e_api`.
- unit (pure) = `rspec_unit` files requiring `fast_spec_helper` + `gems_unit`.
- In-process real DB = the remaining `rspec_unit` + `rspec_migration` + `rspec_background_migration` + `rspec_frontend_fixture`.
- fast-like = `jest_unit` + `jest_integration`.
- other = `workhorse_go` + `contract`.

### Test counts

Static, per file, with Python regexes in multiline mode:
- Ruby: `^\s*(?:it|specify|scenario|example|its)(?:\s|\(|\{|$)`
- JavaScript and TypeScript: `^\s*(?:it|test)(?:\.(?:each|only|skip|todo|failing)\b[^(\n]*)?\s*\(`
- Go: `^func\s+Test\w*\s*\(` (subtests `\bt\.Run\(` reported separately)
- Storybook: `^export const [A-Z]\w*\s*=`

These undercount what runs. The RSpec specs contain 47,923 `it_behaves_like`/`include_examples`/`include_context` calls and 5,281 `where` tables; the Jest specs contain 5,758 `.each` calls. Counting commands:

```sh
grep -rhE --include='*_spec.rb' '^\s*(it_behaves_like|include_examples|it_should_behave_like|include_context)\b' spec ee/spec | wc -l   # 47,923
grep -rhE --include='*_spec.rb' '^\s*where(\(|\s*do|\s*\{)' spec ee/spec | wc -l                                                  # 5,281
grep -rhE --include='*_spec.js' '\b(it|test|describe)\.each' spec/frontend ee/spec/frontend | wc -l                                 # 5,758
```

### Realism heuristics

The regexes are given in §6. Each was applied to whole files. A file counts once for each "files using" column, and call sites are summed with `findall`. In QA specs, `create(:...)` builds data through the API of a live instance, so the DB-write marker is marked n/a for them. `fast_spec_helper` versus `spec_helper` is detected from the `require` line. 11 `rspec_unit` files require neither directly; they load a shared helper file, require plain libraries, or rely on `-r spec_helper` from the runner.

### Other measurements

```sh
grep -c "^- " spec/support/rspec_order_todo.yml                                                      # 7,448 files exempt from random order
grep -rE  --include='*_spec.rb' '(\bquarantine:|:quarantine\b)' spec ee/spec | wc -l                  # 390
grep -rlE --include='*_spec.rb' '(\bquarantine:|:quarantine\b)' spec ee/spec | wc -l                  # 258
grep -rlE --include='*_spec.rb' '(\bquarantine:|:quarantine\b)' qa/qa/specs/features | wc -l         # 80 (99 occurrences)
find spec ee/spec -name '*_spec.rb' | wc -l                                                           # 23,121
find spec/controllers -type f | wc -l; find ee/spec/controllers -type f | wc -l                       # 286, 186
grep -c "^\s*- '" .rubocop_todo/rspec/{verified_doubles,any_instance_of,feature_category,feature_spec_max_examples}.yml .rubocop_todo/rspec/factory_bot/avoid_create.yml
du -sb spec/fixtures ee/spec/fixtures qa/qa/fixtures workhorse/testdata                               # data sizes
```

### History method

The clone has depth 1, so dates come from the GitLab REST API and web endpoints.

- The repository commit-list endpoint (`/projects/278964/repository/commits`) returned a Cloudflare challenge to this client.
- What worked:
  - `repository/files/:path/blame?ref=<sha>`, used to date individual lines;
  - `repository/commits/:sha` and `/diff`;
  - `repository/commits/:sha/merge_requests`;
  - `merge_requests`, `issues` and group `epics` with `search=`;
  - the web endpoint `/<project>/-/issues/<iid>/discussions.json` for issue comments (the notes API returned 401 without authentication; MR discussions were behind the same challenge).
- Pre-2019 history lives in `gitlab-org/gitlab-foss` (project 13083) and was searched there.
- The GitHub mirror's API was refused by this session's policy, so it was not used.
- Handbook dates come from the blame of `gitlab-com/content-sites/handbook` (project 42817607). They date the current wording, not necessarily the first appearance of each rule.
- Where a date is a "blame" date, it is the last change to that line.

The count of MSW migration MRs comes from the MR API with `search=MSW` and `search=Capybara`, `in=title`, `state=merged`, `merged_after=2026-01-01`, keeping titles that say migrate, convert, move or remove (about twenty unique MRs, July to October 2026). The 2025 distribution recount (commit b4396bc8) has no linked MR, and its method was not found. Neither were a public time series of flaky-test or quarantine counts, a published figure for aggregate CI savings from predictive selection or tiers, or the master-pipeline stability indicators that older handbook pages carried (the performance-indicator pages now return 404). One frontend author appears as "Inactive Account"; that author is identified only by the `@winh` handle colleagues used in the thread.

### Leads checked

- `testing_levels.md` describes four levels and a pyramid: verified. Its proportions are observed estimates, not targets, and were never machine-enforced.
- `spec/frontend_integration` exists: no longer. It was deleted on 2026-09-17, and frontend integration now lives in `ee/spec/frontend/integration`.
- `flaky_tests.md`: no longer in the tree. Flaky-test content is in `unhealthy_tests.md` (page introduced 2024-07-10) and `quarantining_tests.md`. `rspec-retry` is gone (2026-03-16). Automatic quarantine MRs and deletion are handbook process (2026), not part of that doc.
- Predictive and fail-fast: verified (2020-09-14, 2020-12, 2021-07-26, renamed 2023-01-17). The measured effect was found only as per-job durations on a sample MR and a ~10% miss rate.
- Karma to Jest "2018–2019": started 2018-12-05, finished 2021-09-03.
- Spinach "2016–2017": decided 2016-03, removed 2018-05-15.
- Codecov: not found. Coverage gating exists only as `undercover` on changed lines.
- Handbook test-health metrics: process pages found; numbers are on internal dashboards only.
- Not in the leads but material: Workhorse has been in this repository since 2021 (159 Go test files), so it is counted here.
