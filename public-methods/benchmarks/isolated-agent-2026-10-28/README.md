# Isolated agent availability and required-lookup pilot — 2026-10-28

**This pilot did not establish an OpenAkashic output-quality or token-efficiency advantage.** It finally measures a true resource-absent baseline, fresh task environments, and actual provider usage. The earlier methods-only baseline already contained OpenAkashic material.

Four synthetic tasks: incident-event state reduction, revision/missing-data experiment aggregation, offline inventory product design, and a fictional career decision. The same actual response model (`gpt-6-luna`, medium requested effort) performed each task in a new Docker container. No prior conversation, memory, user config, hooks, skills, private files, credentials, or other answers were mounted. Root was read-only; external networking was disabled. A per-run Unix socket allowed model inference and, only for eligible conditions, frozen read-only public methods routes. Authentication remained in the trusted host broker.

## Observations

Totals below cover four tasks per condition, one run each. Input includes cache; total tokens = input + output, not input + cache + output. Actual usage receipts matched the CLI aggregate for all 12 runs. No dollar price is estimated.

| Condition | Coding /24 | Judgment /24 | Input | Cached within input | Output | Total tokens | Task time sum | Lookup requests |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| No OpenAkashic | 24 | 23 | 100,719 | 59,008 | 6,731 | 107,450 | 96.9s | 0 |
| Optional access | 24 | 23 | 145,142 | 71,040 | 6,711 | 151,853 | 114.6s | 0 |
| Required lookup (exploratory) | 24 | 22 | 186,240 | 121,984 | 7,016 | 193,256 | 127.4s | 6 |

Optional access was used in **0/4** tasks. That primary comparison measures availability, not effects of using retrieved evidence. A subsequently frozen, exploratory diagnostic required a self-chosen lookup on the same tasks. It issued six requests: both code queries returned no candidate; design and career each retrieved context and one full method. No graph traversal occurred. Required lookup consumed **79.9% more total tokens** and **31.4% more observed time** than no access, with judgment 22/24 versus 23/24. One point is not evidence of population harm; neither quality superiority nor same-quality savings was demonstrated.

The task-specific expertise diagnostic (two rubric items, max4) was 4/4,3/4,3/4. It is one model's rubric judgment, **not human professional validation**. Other rubric gaps included training-time constraints, local-vs-server save states, duplicate/recovery handling, and the financial downside of accepting a fictional job offer.

## What was and was not isolated

Each of the 12 valid agent runs had a new filesystem workspace, home and thread; credentials were never mounted. The provider still supplies pretrained knowledge and may reuse prefix-cache computation. That cache is measured, not described as personal memory. The same frozen public DB/index and deployed methods handlers were used; no public write or private retrieval route was exposed. The primary task/fixture/rubric freeze remained unchanged.

This is not exclusive hardware isolation: the host also runs other services. A coding-grading process briefly overlapped late primary runs and was stopped; all final coding grading ran after generation. Treat latency as descriptive observations, not stable speed claims. All preparation, grader costs and embedding compute are outside participant token totals. The requested/observed model alias is recorded; exact backend weight versions and dollar billing are not exposed.

## Evaluation boundaries

- Four synthetic tasks were chosen after catalog metadata inspection. Coverage selection and near-ceiling tasks limit generalization.
- Baseline and optional access were preregistered. Required lookup was added after observing zero optional uses and three partial coding grades; its prompts were frozen before its outputs, with no task feedback supplied. It is not an independent holdout.
- Six programs passed all 72 correlated hidden executions, plus 12 public-example diagnostics. These are six programs on two tasks, not 84 independent tasks.
- Six judgment memos were randomly labeled and source labels normalized before one fresh `gpt-6.1-sol` grader applied the frozen rubric. All 36 evidence quotations matched the normalized artifacts. Model judgment is not a human panel, user utility, or demonstrated expertise.
- Eight original runs stopped in the isolation probe before any model call. All are retained, with the probe repair and fresh retry records. Smoke tests are excluded from task totals.
- No general-web baseline, same-corpus flat RAG baseline, repeated trials, real users, or long-term cross-task preference transfer was measured.

## Audit and replay

`report.json` summarizes evidence boundaries; `measurements.json` contains case-level actual usage/time and isolation checks. `artifacts/` preserves programs, memos, final answers, public command events, provider usage receipts and lookup responses. The public trace omits reasoning summaries and session/thread metadata; no credentials or private context are included. `blind-packet.json`, `blind-grades.json` and `blind-key.json` allow the assessment to be audited. Inputs and rubric are under `protocol/`.

To replay deterministic checks with Docker (no model or API key required):

```sh
python protocol/verify_tasks.py --self-check
python replay_coding.py
```

The replay mounts only one candidate program per disposable offline container and supplies one fixture over stdin. Gold stays on the host. It refuses to overwrite `coding-replay.json`. Timing will differ. The model generation reference implementation is archived under `reference-runtime/`; it contains reference-host paths and must be configured by the operator, not run against somebody else's credentials. It is not a turnkey account-authentication setup. Use a trusted host broker and never mount authentication into candidate workspaces. `snapshot-manifest.json` records frozen DB/index/code hashes; database and model/index binaries are not redistributed. Re-indexing a separately seeded corpus may not produce byte-identical reference state.

Next useful test: examples whose documented failure conditions or contextual exceptions add information missing from a strong baseline, with tasks frozen before retrieval tuning. Adding more generic advice or forcing every task to search is not supported by these results.
