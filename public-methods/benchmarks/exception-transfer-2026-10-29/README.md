# Version-sensitive exception transfer — 2026-10-29

Four deliberately exception-focused diagnostic tasks from three product families, two fresh executions per arm: **24 candidate executions** of actual `gpt-6-luna`. This is a narrow documentation-transfer pilot, not broad agent expertise or human utility evidence. Corpus, task/gold, run order, limits and harness were frozen before candidate outputs; exact provenance and the submission-analysis clarification are archived.

## Observed results

No quality or efficiency advantage was established. Delivered decision content scored 48/48 without retrieval, 47/48 with the same corpus flattened, and 48/48 with OpenAkashic structured references. The single flat error contradicted its own correct rationale, so it is not evidence of superior knowledge. Blind model explanation scores were 47/48, 45/48 and 45/48 respectively. Structured access used 52.2% more total provider tokens than no retrieval and 38.3% more than flat, with no explanation advantage. Strict requested-file scores were 42/48, 29/48 and 42/48; missing files are disclosed separately. These four selected tasks have a baseline ceiling and do not establish general usefulness or uselessness.

| Condition | Exact final/file content /48 | Strict requested file /48 | Blind explanation /48 | Input | Cached within input | Output | Total tokens | Observed seconds | Reads |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| base | 48 | 42 | 47 | 259,143 | 175,232 | 11,646 | 270,789 | 209.6 | 0 |
| flat | 47 | 29 | 45 | 288,573 | 174,464 | 9,361 | 297,934 | 259.0 | 10 |
| structured | 48 | 42 | 45 | 400,927 | 251,648 | 11,115 | 412,042 | 277.3 | 18 |

Input includes cached input. Total = input + output. Dollar price is not estimated. Provider receipts are checked against CLI totals; the authentication/isolation smoke test, curation, embedding, upstream validation and grading are separate, not silently included or declared free. Task timing is serial observation on a shared host, not isolated latency proof. Provider response delays are preserved. Repeated requests can reuse provider prefix cache; fresh workspaces do not imply a cold model cache.

Some candidates returned valid JSON but omitted the requested file. Both strict-file and delivered-content scores are shown. The secondary final-response fallback was recorded during execution after observing file absence, before reading/scoring contents; it is not a fully preregistered primary result. No candidate was prompted again or repaired. Rubric grading evaluates content, not file compliance.

## What was compared

- **base:** supplied task and pretrained model, no retrieval.
- **flat:** the same fixed 61-method pool and the same situation/goal hybrid retriever, returned as plain text. It includes full procedural fields when they fit and allows exact full-record fetches.
- **structured:** the deployed service's bounded context representation and exact-record fetch API. It preserves source/version/condition/uncertainty fields. Its context normally leaves procedure steps to the full fetch.

Both retrieval arms must make a first self-chosen lookup, have the same 2,048-token context cap, 20-read limit, 24-request model limit and 300-second runtime limit. Retrieval queries and further fetch decisions are made by the agents; no oracle IDs are injected. Graph traversal is disabled in this focused comparison. Thus flat-versus-structured tests representation and resulting agent behavior, **not graph superiority**, a new retriever, or raw-web RAG. The corpus contains six new pinned method records and 55 previous public distractors. It was curated for these exception families; this is not randomly sampled production traffic.

The tasks cover Streamlit 1.46.0 fragment execution/containers, TanStack Query 5.90.5 cancellation and disabled-query states, and DuckDB 0.10.0 casting. Source cards were prepared by a separate agent before task authoring. Gold and per-task rubric were written by another agent from those sources, before candidate outputs. Version-pinned upstream probes were independently executed without seeing tasks/gold/answers. Their limits are explicit: Streamlit's internal guard only, query-core with simulated transport, and real DuckDB SQL. They do not prove full UI, real HTTP cancellation or production fixes.

## Isolation and scoring

Each run starts a new Docker container and tmpfs home, no memory, history, rules, user configuration, private source, credentials, prior answer or gold mounts. Root is read-only, networking is disabled, UID 65534, capabilities dropped. A per-run Unix socket exposes only model inference and the arm's read-only reference routes. Authentication stays in the trusted host. The harness is archived for audit, not advertised as a turnkey supported authentication SDK. The baseline route and cross-run-ID checks return 403.

There are 24 objective decisions, repeated twice per arm (48 scored items), but only **four distinct tasks and three product families**, not 48 independent test cases. Exact JSON types/enums are scored. Frozen explanation anchors cover conditions, actionable fix and uncertainty (0–2 each). A fresh Sol grader sees anonymized answers and the frozen rubric; no reward for reference count. Citation/style clues can still weaken blinding. This is model grading, not independent human expertise. Gold, adverse results and missing artifacts remain visible.

## Replay and inspect

Run `python replay_archived.py` in this benchmark directory to recompute exact decision scores and provider/CLI token sums from the archived files without a model or API key.

`report.json` and `measurements.json` expose every run. `artifacts/` includes synthetic answers, public command traces, retrieval responses, timing, isolation probes and actual usage receipts; reasoning summaries and session IDs are excluded from public traces. `protocol/` contains all tasks, exact gold and rubric. `corpus/` has pinned sources and documented methods. `upstream/` preserves independent package probes. `experiment-freeze.json` records snapshot/index/runtime hashes; those binary runtime artifacts and model weights are not published. Live IDs differ from evaluation-snapshot IDs; `publication/receipt.json` maps them without claiming UUID identity across instances.

To install the six optional public documentation records with the existing service seed tool (use paths appropriate to your checkout):

```sh
PYTHONPATH=api python api/scripts/seed_methods.py --fixture examples/documented-exceptions.json --archive "$OA_STATE/research.sqlite3" --mapping "$OA_STATE/exception-mapping.json"
```

These are version-scoped documented methods, **not new successful user outcomes**. Rebuild the optional embedding index for your own new IDs. Existing historical benchmarks stay unchanged; adding methods does not inherit their measured accuracy.
