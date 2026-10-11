# Shapes of tests: research brief

One report per open-source project. Same questions, same measurement rules,
same layout, so the reports can be compared with each other and with the
Robinauts survey in the post "why the drama about duplicated tests?"
(`_posts/2026-10-11-why-the-drama-about-duplicating-tests.md`).

This brief is shared by every project agent. Do not edit it. If a rule does
not fit the project you were given, follow it as far as it goes and record the
deviation in the report's appendix.

## Why this exists

The post compares three postures (test pyramid, testing trophy, Spotify's
testing honeycomb) and measures the Robinauts backend suite by lines of test
code per category. We want to know where renowned open-source projects of the
same general shape sit, how they got there, and whether their written policy,
their tooling and their tree agree with each other.

Read the section "How that sits against general practice" in the post before
you start. What to keep in mind from it:

- Robinauts sorts tests by *what they prove*, one placement per behavior:
  `e2e` (browser over a real server and database), `api` (real server over
  HTTP, for what the UI cannot show), `unit` (pure functions), `adapters_free`
  and `adapters_metered` (one adapter against its real dependency),
  `fast` (everything in one process on in-memory fakes, an explicit extra copy,
  never the only proof), `tooling` (tests of the repository itself).
- The post weighs four factors: speed of feedback, confidence per test, cost
  of maintenance, flakiness.
- The Robinauts chart counted lines of test code in October 2026:
  e2e ~750, api ~1,100, adapters ~2,250, unit ~1,150, fast ~1,250 (shown
  beside the others as the extra copy). Shared helpers and the tooling tests
  were left out.
- The post places Robinauts near the classical (Detroit) school: real
  collaborators where possible, check the result. The London (mockist) school
  replaces neighbours with mocks and checks the calls.

## Which projects qualify

A classical business application: a database, a backend, a web UI. Extra
components such as a queue, workers or a scheduler are fine. Not an operating
system, an editor, a compiler, a language runtime, a library or a framework.

## Questions

Answer every question. "Not found" is an acceptable answer when you say where
you looked. Number the report sections exactly as below.

### A. Posture and taxonomy

1. **What is the project's posture, and how does it classify its tests?**
   Folders, pytest marks or their equivalent (tags, rspec metadata, build
   tags), CI job names, and the written docs. Give the test tree with one line
   per category saying what the category is for, in the project's own words
   where it has them.
2. **What does the project mean by each category name?** Projects call tests
   that hit a real database "unit tests", or call a browser suite "integration".
   Give a mapping table: their name, what the tests in it actually touch
   (process, database, network, browser), the nearest category in the post's
   taxonomy, and a note where the fit is poor.
3. **Which categories exist that the post's taxonomy has no slot for?** For
   each: what it proves, why the project has it, and roughly how big it is.

### B. Shape by the numbers

4. **How many lines of test code per category, and what percentage of the
   whole?** Same dimension as the Robinauts chart, so it can be drawn the same
   way. Include the project's own categories from question 3 as their own
   rows. Follow the measurement rules below.
5. **What is the test-to-code ratio per layer or category, where it can be
   computed?** State the mapping you used from test categories to production
   components (for example, API tests against the web package, adapter tests
   against the adapters package). When a category spans the whole product,
   report it against the whole production tree and say so.

### C. Realism

6. **Where on the Detroit-to-London axis does each category sit?** Per
   category, report mock density: the share of test files that import a
   mocking facility (`unittest.mock`, `mocker`, `MagicMock`, `monkeypatch`,
   `jest.mock`, `vi.mock`, `sinon`, `msw`, `rspec-mocks` doubles, or the
   project's equivalent) and the count of such call sites per 1,000 lines.
   Also report real-dependency usage: tests that open a database session,
   start a real server, or need a service from a compose file. State the
   heuristic you used, with the exact grep patterns, so it can be repeated.
7. **How is the web UI tested?** Component tests with fakes, browser tests
   over a real backend, or both. Which one the project treats as the proof,
   which frameworks, how many lines, and where they run in CI.

### D. Enforcement

8. **What enforces the testing policy by machine rather than by review?**
   Fixtures that fail a test for touching something it should not, pre-commit
   hooks, lint rules, CI guards that refuse to skip, labels that widen the test
   run. For each mechanism: what it checks, where it lives, and when it was
   added, with a link to the commit or pull request.

### E. History

9. **What is the history behind the test strategy?** Did the project find
   trouble with earlier approaches? Did it steer its policy, and did the steer
   succeed? Search the team's own discussions and arguments, not secondary
   summaries.
10. **Build a dated timeline of turning points, with links.** One line per
    turn: date, what changed, who drove it, link.
11. **For each turning point: what was the pain, who argued what, and did the
    numbers move afterwards?** Quote the arguments verbatim, with the author's
    name and a link. Where before-and-after numbers exist (suite runtime,
    test counts, flaky-test counts, CI minutes), give them.
12. **Does the project measure coverage, and did it ever gate on it?** Yes or
    no, with dates and links for each change of policy.

## Measurement rules

Pin everything, so the next agent can repeat it on another project.

- **Snapshot.** Clone the default branch with `git clone --depth 1` and record
  the commit SHA and the commit date. Measure that snapshot only.
- **Counting tool.** Use `notebooks/X-shapes-of-tests/tools/count_lines.py`.
  It counts code lines as total lines minus blank lines minus full-line
  comments. It does not try to recognise docstrings; say so in the appendix.
  Run it with `--by-file` and group the files yourself when the project's
  categories do not align with directories.
- **Languages.** Count the languages the project's tests are written in
  (Python, TypeScript, JavaScript, Ruby, Go, Java, Kotlin, PHP, Clojure,
  Elixir, and so on). Report per language when a category mixes them.
- **What is test code.** Files under the project's test directories or
  matching its test-file patterns. Shared helpers (`conftest.py`, fixture
  modules, factories, test utilities, custom assertions) are counted
  separately and excluded from the category totals, as the Robinauts chart did.
  Test data files (JSON, YAML, SQL dumps, recorded cassettes, snapshots) are
  excluded from the lines; mention their size in a sentence.
- **Examples that double as tests.** Sample code the project runs as tests
  (example DAGs, demo apps, cookbook scripts) is counted as its own row. Say
  whether you include it in the whole.
- **Production code.** Source files excluding tests, docs, generated code,
  vendored code and migrations. State what you excluded.
- **Report lines, files and test counts.** Lines favour verbose suites, so
  also give the number of test files and, where a grep is cheap, the number
  of test functions (`def test_`, `it(`, `test(`, `scenario`, and so on).
- **Percentages** are of the category totals, helpers excluded.
- Save the raw per-file output of the counting tool, with your category
  column added, as `notebooks/X-shapes-of-tests/<project>.counts.csv`.
- **Tool change, 2026-10-11, after the first five reports.** The counter's
  default excludes used to drop every directory named `build`, `dist`,
  `coverage` or `vendor` at any depth, which also dropped real code. They now
  apply at the root only, and the tool lists every pruned directory on
  stderr. Read that list. When a nested `vendor` directory holds third-party
  code, exclude it yourself with `--exclude '*/vendor/*'` and say so. Effect
  on the five first reports: GitLab recovered its 194 affected files by hand
  (its appendix); Discourse missed 315 test lines and 333 production lines in
  its migrations toolkit; Sentry missed 185 production lines under
  `src/sentry/build`; Airflow and Superset were unaffected. No percentage in
  any report moves by more than a few hundredths of a point.

## Sources and evidence

- Primary sources first: the repository's contributing and testing docs, the
  tree, the CI workflow files, the pre-commit configuration, the pytest or
  test-runner configuration and its registered markers. Then the project's
  own history: the developer mailing list archives, design proposals (AIPs,
  RFCs, ADRs), issues, pull requests, discussions, maintainers' blog posts and
  talks.
- Every historical claim carries a link and a date. Quotes are verbatim and
  attributed by name. Mark inferences as inferences.
- Do not rely on memory for facts about the project. Verify in the repository
  or in the source you link. If something cannot be verified, say so. Do not
  fill a gap with a plausible story.

## Working rules

- Clone into a new, empty directory under the session scratchpad. Do not run
  the project's code, test suite, build, install or setup scripts. Read and
  count only. Run your own scripts from outside the clone and pass paths as
  arguments. Delete the clone when you are done.
- The GitHub MCP tools in this session are scoped to this blog's repository.
  Do not point them at the studied project. Use `git clone` and web fetches
  (github.com pages, api.github.com, mailing-list archives, wikis).
- Write only two files into this repository: the report at
  `notebooks/X-shapes-of-tests/<project>.md` and the CSV named above. Do not
  commit. Do not edit the brief, the counting tool or anything else.

## Report layout

```
# <Project>: the shape of its tests

Measured: <repo url> at <sha> (<commit date>), default branch <name>.
Counted with notebooks/X-shapes-of-tests/tools/count_lines.py, rules as in
the brief. Deviations in the appendix.

## Summary
Ten lines at most: the posture in one sentence, the shape table, the
history in one sentence.

## 1. Posture and classification
## 2. What the names mean
## 3. Categories outside the post's taxonomy
## 4. Lines per category
## 5. Test-to-code ratio
## 6. Detroit or London
## 7. The web UI
## 8. Enforcement by machine
## 9. History
## 10. Timeline
## 11. The arguments, turn by turn
## 12. Coverage

## Chart-ready table
category | maps_to (post taxonomy) | lines | pct | files | tests

## Sources
Numbered, each with a date.

## Appendix: commands and counting decisions
The exact commands, the grouping rules, every judgment call.
```

Style: plain prose, short sentences, tables for numbers, quotes as block
quotes with attribution. No marketing language. As long as the evidence
needs, typically 2,000 to 5,000 words plus tables.
