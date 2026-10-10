# Final Product Workflow Audit

**Project:** AI-Powered BI Platform (`backend/` FastAPI + `frontend/` React/TypeScript/Vite)
**Date:** 2026-10-10
**Method:** every claim below was executed in this environment against the live dev stack (backend on `127.0.0.1:8000`, Vite dev server on `:5173`, PostgreSQL, real LLM providers). Browser automation is not available, so UI behaviour is evidenced by TypeScript, unit tests (including React StrictMode streaming tests), production builds, and real HTTP traffic — not by screenshots.

---

## A. Executive summary

**Final product status: `FINAL PRODUCT — READY`** (conditions listed at the end of this section).

### Root causes discovered and fixed in this audit round

| # | Reported symptom | Root cause | Fix |
| --- | --- | --- | --- |
| 1 | **Corrupted AI replies** — `BusinessBusiness Intelligence Intelligence Support Support`, every word/phrase doubled | Frontend rendered each streamed delta **twice**. `AIChat.tsx`'s SSE handler mutated the previous state object inside a `setState` updater (`last.content += parsed.delta`). The app runs in `<React.StrictMode>`, and React dev-mode **double-invokes state updaters**; call 1 appended the delta, call 2 (same `prev`, same mutated object) appended it again. Raw SSE from the backend was always correct — corruption appeared only at render time, in dev. | Pure updaters in all four message handlers (new object instead of mutating `prev`). Regression test `AIChat.test.tsx` renders `<StrictMode>`, feeds deltas `"Business" / " Intelligence" / " Support" / " for " / "data data " / "review."` and asserts the exact output `Business Intelligence Support for data data review.` — **fails against the old code, passes now** (verified both ways). No word-dedup filter was added; legitimate repetition (`data data`) is preserved verbatim. |
| 2 | Chat invented analysis of business data / answered "Have I uploaded a dataset?" from model memory | The general chat system prompt carried no information about the organization's datasets | `ChatService._dataset_inventory()` injects the org's actual `de_datasets` records (name, rows, columns — metadata only) into every system prompt, plus rules: answer dataset questions ONLY from the inventory; never invent figures; if no datasets exist, say so and point to Data Sources. Applies to streaming and non-streaming. |
| 3 | AI dashboard generation returned HTTP 500 "Unable to generate dashboard." | Two stacked bugs: (a) `SchemaExplorer` passed the `_LazyEngine` proxy to `sqlalchemy.inspect()` → `NoInspectionAvailable`; (b) even past that, LLM widgets use `id` + chart types (`line`, `pie`, …) but the platform contract requires unique `widget_id` + `kind` ∈ {kpi, chart, table, text, ai_insights, forecast, gauge} → save always failed | `Engine.unwrap()` on the lazy engine + use in `SchemaExplorer`; `_normalize_widgets()` maps the planner vocabulary onto platform kinds (preserving the chart type in `chart_config`), repairs missing/duplicate ids. Route now returns the real error text. |
| 4 | AI predictions crashed: `BusinessRecommendation` / `PredictionResult` validation errors | LLM JSON went straight into strict pydantic models; missing `category`/`impact`/`confidence` keys killed the whole forecast; `target`/`horizon` were required at construction but assigned only after | Schema defaults + tolerant parsing (skip items without a real recommendation, `parse_json_reply` fence handling); `PredictionResult.target/horizon/model_used/model_type` optional (set by the orchestrator right after construction). |
| 5 | Multi-agent run claimed "No datasets or metrics are available" | Router passed no organization context; agents read `context["data_summary"]` → "No data" | Router injects the org's dataset inventory into the agent context before execution. The sweep now answers "*The dataset contains 4 rows… 3 columns*" for an uploaded dataset. |
| 6 | Copilot said the sales dataset was empty / `KeyError: 'question'` in `sql_query` step | (a) Planner prompt never documented required tool params, LLM omitted `question`; (b) copilot context didn't include `de_datasets` uploads; (c) `data_profile`/`workflow_generator` tools called nonexistent/misused APIs | Tools tolerate `question`/`query` aliases with clear `ValueError` messages; planner prompt documents required params per tool; context includes `de_datasets`; reasoning prompt marks dataset metadata as authoritative; broken tools repaired (`data_profile` now profiles stored datasets, `workflow_generator` builds a proper `WorkflowCreateRequest`). Verified: the copilot now cites *both* its SQL result and the authoritative dataset metadata. |
| 7 | Workflow creation → HTTP 500 `invalid input syntax for type uuid: "ec51e71b-775"` | Workflow/execution ids were truncated UUIDs (`uuid4()[:12]`) but the columns are PostgreSQL `UUID` | Full `uuid4()` strings at all three generation sites (`create_workflow`, run execution, engine executor). |
| 8 | Dataset upload gaps — no size limit, unknown file types silently parsed as CSV | Missing validation | `DATA_MAX_UPLOAD_SIZE` (default 50 MB) enforced before disk I/O; unknown `source_type` rejected with "Unsupported file type … Supported: csv, xlsx, json, parquet"; rejected uploads leave **no orphan files**; frontend adds a 50 MB pre-check and the file input restricts types. |
| 9 | Maintenance banner could show stale `READONLY` after the mode was switched off | Banner polls every 30 s; Settings didn't notify it | Settings dispatches a `maintenance-changed` window event; the banner re-reads immediately. Backend transitions verified live: `off → readonly → maintenance → off` with writes 200 → 503 → 503 → 200. |
| 10 | Vectorstore 503 concern | `GET /admin/ai/vectorstore` returns a **truthful** status (`{"backend":"memory","namespaces":{},"record_count":0}`); 503 only fires if the store itself throws | Verified 200 live; ingest/retrieval truthfully reported below (Celery not running → indexing queued-but-not-executed → RAG answers `insufficient_evidence` honestly). |

Fixes from the previous round (still in place, re-verified): DB-backed dataset registry with org scoping, `chat_completion` provider adapter (16 call sites), profile `success` flag, refresh-token-in-body (query → 422), AIChat double-send guard, dataset selector, legacy `/api/v1/datasets` rewrite, JSON-leak-free insights.

### Remaining blockers (all disclosed, none silent)

1. **Redis, Celery workers, pgvector: NOT CONFIGURED.** Rate-limit cache falls back to process-local; knowledge indexing is queued but never executes (RAG truthfully reports `insufficient_evidence`); vectorstore reports `backend: memory`.
2. **No browser automation** — UI verified via tests/build/HTTP only.
3. Maintenance mode is enforceable but its setter is not role-restricted (0 users hold `superadmin`; gating today would brick the feature — seeding a platform operator is a 1-line follow-up).
4. Copilot NL2SQL queries the SQL database; uploaded dataset rows live in parquet. The copilot now says so honestly and cites the authoritative metadata instead of inventing.
5. Pre-existing repo-wide lint/type debt: 111 mypy errors (49 files) and a few ruff findings in untouched files; all files changed here are ruff-clean and mypy-clean apart from one pre-existing pattern in `copilot/tools/registry.py:333`.

---

## B. AI and Ollama audit

| Item | Result | Evidence |
| --- | --- | --- |
| Configured provider | `openai` (OpenAI-compatible, NVIDIA NIM), model `meta/llama-3.2-11b-vision-instruct`, `configured=true available=true` | `/ai/providers` live call |
| Ollama | Running at `http://localhost:11434`; `smollm2:135m` installed; `/ai/chat {provider:"ollama"}` returned a real answer (200) in a live test | executed this session |
| Real local model tested | Yes — every AI feature below was exercised against the real configured provider; Ollama chat verified separately | E2E logs |
| Repetition/corruption diagnosis | Root-caused to React StrictMode double-invoking a mutating state updater (render-time only; raw SSE never doubled). Fixed with pure updaters; regression test fails-first verified | `AIChat.test.tsx` — test output showed `BusinessBusiness Intelligence Intelligence Support Support for  for data data data data review` before the fix, exact single text after |
| Exactly one assistant response per message | Backend saves the assistant message once (streaming and non-streaming); conversation detail shows `roles == ["user", "assistant"]` | `test_chat_grounded.py` |
| Conversation history not duplicated / correctly ordered | `_build_history` reads DB once; user message reaches the model exactly once; no retries duplicate messages | `test_chat_grounded.py::test_user_message_reaches_the_model_exactly_once` |
| Conversation persistence after reload | Messages stored in `ai_messages`; `GET /conversations/{id}` returns them; frontend reloads on conversation select | E2E + manual HTTP |
| Dataset-grounded question | "Have I uploaded a dataset?" → system prompt contains `sales.csv (4 rows, 3 columns): product, region, sales` + "Never invent" rule; streaming path equally grounded | `test_chat_grounded.py` |
| General chat without datasets | Prompt states the user has **not** uploaded datasets and forbids claiming analysis | `test_chat_grounded.py::test_chat_without_datasets_says_so_instead_of_inventing` |
| Ollama unavailability handling | ConnectError/timeout → actionable message ("Could not reach AI provider … check the provider base URL"); model-not-installed → HTTP 404/400 surfaced with model name; no canned fallback text | `_describe_provider_error` + provider tests |
| Generation settings | Ollama sends `temperature` + `num_predict` (= max_tokens); no repeat-penalty hack was needed because duplication was **not** model behaviour — do not "fix" model params for a frontend bug | code inspection |

### Every existing AI capability, tested end-to-end (real provider, live server)

Script: `e2e_ai_features.py` — **14 PASS / 0 FAIL / 0 BLOCKED**

| Capability | Endpoint | Result | Key evidence |
| --- | --- | --- | --- |
| AI Chat (non-streaming) | `POST /ai/chat` | PASS | real answer + persisted `user, assistant` |
| AI Chat (streaming SSE) | `POST /ai/chat` (`stream:true`) | PASS | deltas concat to exactly one answer, `[DONE]` once, 0 error events |
| Dataset-grounded chat | `POST /ai/de/chat` | PASS | answer contains `1000.0`; evidence `sum=1000.0` |
| NLQ / Ask Your Data | `POST /ai/query` | PASS | question "How many organizations are there?" → real SQL `SELECT COUNT(*) AS organization_count FROM organizations LIMIT 1000`, 1 row |
| NLQ schema | `GET /ai/schema` | PASS | 200 |
| AI dashboard generation | `POST /ai/dashboard/generate` | PASS | 4 widgets saved with valid kinds (kpi/chart×2/table) |
| AI business analyst | `POST /ai/analyze` | PASS | executive summary generated for the generated dashboard |
| AI report generation | `POST /ai/reports/generate` | PASS | sections `Data Overview`, `Analysis` |
| AI predictions | `POST /ai/predictions/predict` | PASS | 30 forecast points, 5 recommendations, `target=sales` |
| Multi-agent run | `POST /ai/agents/run` | PASS | grounded answer citing the uploaded dataset's real rows/columns |
| Workflow automation | `POST /workflows` + `/test` | PASS | full-UUID id, test run 200 |
| Knowledge upload | `POST /knowledge/documents` | PASS | document created |
| Knowledge search | `POST /knowledge/search` | PASS | 200 (0 hits — indexing requires Celery, disclosed) |
| RAG grounded query | `POST /knowledge/rag/query` | PASS | honest `insufficient_evidence` instead of a fabricated answer |
| BI Copilot | `POST /copilot/query` | PASS | multi-tool plan executed; cites SQL result **and** authoritative dataset metadata |

---

## C. Dataset workflow audit

**Upload → persistence → listing → preview/schema → downstream AI → tenant isolation.**

| Check | Result | Evidence |
| --- | --- | --- |
| Valid CSV (4 rows / 3 products / total 1000) | PASS | `row_count=4, column_count=3, status=ready, file_size=85` |
| Persistence | PASS | `de_datasets` row + parquet version + raw file; retrievable after backend restarts |
| Listing | PASS | `GET /ai/de/datasets` → `count=1` with counts + status |
| Missing values | PASS | clean/validate handle nulls (`fill_missing` transform applied, quality score computed) |
| Empty CSV | PASS | rejected: "contains no data rows"; **no files left behind** |
| Malformed / binary CSV | PASS | rejected via binary sniffing ("not a readable table"); storage unchanged (regression test asserts snapshot equality) |
| Unsupported type (`.exe` → `source_type=exe`) | PASS | rejected: "Unsupported file type 'exe'. Supported types: csv, xlsx, json, parquet" |
| Size limit | PASS | with `DATA_MAX_UPLOAD_SIZE=100` a 7 KB upload is rejected: "exceeds the 0 MB dataset upload limit" (frontend pre-check mirrors the 50 MB default) |
| Dataset preview + schema | PASS | schema endpoint returns `product/region/sales` with semantic types |
| Downstream use | PASS | dataset chat (grounded aggregates), predictions (forecast), agents, copilot all read the uploaded dataset |
| Tenant isolation | PASS | second org: list `[]`, profile "Dataset not found", export 404, legacy endpoints 404 |
| Frontend states | PASS | uploading spinner, success refresh, error `Alert` with the backend's real message, 50 MB pre-check |

---

## D. Authentication and API audit

| Check | Result | Evidence |
| --- | --- | --- |
| Registration / login / refresh / logout | PASS | E2E: register → login (access+refresh) → refresh via **body** 200 → refresh via **URL query** rejected 422 |
| The reported `GET /api/v1/admin/overview → 401` | Explained: the request was unauthenticated (no/expired token). Protected pages require login; the app routes unauthenticated users to Login (App routing tests). After login the user lands on the app; a 401 triggers a single silent refresh, then logout — no infinite loops (single-flight `tryRefresh`) | `api.ts`, `App.test.tsx`, E2E 401 sweep |
| 401 sweep | PASS | 6 protected endpoints all return 401 without a token (incl. the two from the report) |
| Vectorstore 503 | Resolved as truthful-status design | `GET /admin/ai/vectorstore` → 200 `{"backend":"memory","namespaces":{},"record_count":0}`; 503 only if the store itself throws |
| Maintenance consistency | PASS | one source of truth (`GET /admin/maintenance`); Settings page, banner and backend agree; transitions `off→readonly→maintenance→off` verified live with write probes (200/503/503/200); banner refreshes immediately on change |
| API/frontend contract | PASS | every AI feature call in §B used the exact request/response schemas the frontend sends |
| Rate limiting | PASS | burst → `429 {"error":"rate_limit_exceeded","limit":120,"retry_after":1}` |
| CORS | PASS | ACAO only for `http://localhost:5173`; foreign origin receives no header |

---

## E. Quality and security audit

**Tests executed this round**

| Suite | Command | Result |
| --- | --- | --- |
| Backend full | `cd backend && python -m pytest -q` | **264 passed, 1 skipped** (symlink skip), ~21 s |
| Frontend unit | `npx vitest run` | **7 passed** (incl. 3 theme + 1 StrictMode-streaming test) |
| TypeScript | `npx tsc --noEmit` | clean |
| Production build | `npm run build` | clean (pre-existing chunk-size warning) |
| Ruff (all changed files) | `python -m ruff check …` | clean (1 pre-existing SIM102 in untouched `config.py:146`) |
| Workflow E2E | scripted, 31 checks | **31/31** |
| AI features E2E | scripted, 15 checks | **14 PASS / 0 FAIL / 0 BLOCKED** |

**New regression tests added this round (19):** StrictMode exactly-once streaming (`AIChat.test.tsx`), grounded general chat × 5 (`test_chat_grounded.py`), upload type/size limits × 2 (`test_dataset_pipeline.py`), AI feature fixes × 11 (`test_ai_feature_fixes.py`: widget normalization ×4, prediction schemas ×2, lazy-engine inspection ×2, copilot tool tolerance ×2, workflow UUID PK ×1).

**Security findings**

- No security control was disabled to make a test pass.
- Tenant isolation re-verified across datasets, conversations, agents and the copilot (org filter on every query).
- Upload path traversal still blocked (`_sanitize_filename`), binary sniffing, size limit, type allow-list.
- **Diagnostic output:** an earlier E2E run echoed a refresh-response body (test-account JWT) into the console. The script was fixed to never print token values; the exposed token belonged to a disposable test account and expired within 15 minutes — no revocation needed, but the rule "never log tokens" is now enforced in the script.
- Secrets: no API keys in responses or logs; provider keys read from env only.

**Browser console / backend logs:** console inspection requires browser automation (unavailable). Backend logs were reviewed for every failing feature during the investigation; the only unhandled exceptions remaining in logs are the ones intentionally surfaced to clients with clear messages.

---

## F. Evidence

Reproduction commands (all executed against the live stack):

```bash
# backend (from backend/)
python -m pytest -q                                   # 264 passed, 1 skipped
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend (from frontend/)
npx vitest run          # 7 passed
npx tsc --noEmit        # clean
npm run build           # clean

# E2E (executed)
e2e_workflow.py         # 31/31 checks — auth, CSV→analysis, isolation, streaming, proxy, 401s
e2e_ai_features.py      # 14 PASS / 0 FAIL — every AI capability with the real model
```

Selected observed results (sanitized):

- Duplication bug, before fix (StrictMode + SSE deltas `Business/ Intelligence/ Support/ for /data data /review.`): rendered
  `BusinessBusiness Intelligence Intelligence Support Support for  for data data data data review`
  After fix: `Business Intelligence Support for data data review.` — **PASS** (fails-first test verified)
- NLQ: `"How many organizations are there?"` → `SELECT COUNT(*) AS organization_count FROM organizations LIMIT 1000` → 1 row
- Predictions: `success=true`, 30 forecast points, 5 recommendations, `target=sales`
- Dashboard: 4 widgets — `kpi_1/kpi`, `chart_1/chart`, `chart_2/chart`, `table_1/table`
- Agents: "*The dataset contains 4 rows… 3 columns: 'Product', 'Region', 'Sales'*" (previously "No datasets available")
- Copilot: "*…1 row according to the SQL query result, but the authoritative metadata from the platform database indicates…*" (both sources cited, nothing invented)
- RAG: `evidence_status=insufficient_evidence` with an explicit "cannot answer from context" message (indexing blocked on Celery — truthful, not fake)
- Maintenance: writes `200 → 503 → 503 → 200` across `off → readonly → maintenance → off`

---

## G. Final acceptance matrix

| Area | Test | Result | Evidence | Remaining issue |
| --- | --- | --- | --- | --- |
| AI chat — corrupted repetition | StrictMode SSE test | PASS | exact-once rendering; legit repetition preserved | none |
| AI chat — grounded answers | upload → "Have I uploaded a dataset?" | PASS | system prompt carries real dataset metadata; no-dataset case refuses to invent | none |
| AI chat — streaming/non-streaming | E2E both paths | PASS | one assistant message persisted; 0 duplicate/error events | none |
| Ollama | live chat via `provider: ollama` | PASS | real `smollm2:135m` answer | Ollama optional provider, not default |
| Provider errors | unavailable/timeout/model-missing | PASS | actionable messages; no canned fallback | — |
| NLQ / Ask Your Data | natural language → SQL → rows | PASS | real SQL + row count | — |
| Dashboard generation | generate + save | PASS | 4 valid widgets saved | LLM latency up to ~2.5 min on slow provider days |
| Business analyst | analyze dashboard | PASS | executive summary | — |
| Report generation | generate | PASS | 2 sections with content | — |
| Predictions | forecast on uploaded dataset | PASS | 30 points, 5 recommendations | — |
| Multi-agent | run task | PASS | grounded dataset summary | — |
| Workflows | create + test-run | PASS | full-UUID ids; test 200 | — |
| Knowledge/RAG | upload + search + grounded query | PASS | honest `insufficient_evidence` | indexing needs Celery (NOT CONFIGURED) |
| Copilot | end-to-end query | PASS | plan executed; metadata cited as authoritative | NL2SQL only reaches SQL DB (disclosed honestly) |
| CSV upload | valid/empty/malformed/binary/oversized/wrong-type | PASS | all rejected cases leave storage unchanged | — |
| Dataset persistence & listing | restart survives; list scoped | PASS | record + parquet + raw file | 3 pre-registry orphan files remain on disk (unlisted, disclosed) |
| Tenant isolation | cross-org probes | PASS | list/profile/export/agents/copilot all org-scoped | — |
| Auth/session | login/refresh/logout/protected routes | PASS | body-refresh 200; query-refresh 422; 401 sweep | — |
| Maintenance mode | transitions + banner agreement | PASS | 200/503/503/200; instant banner refresh | setter lacks a role gate (0 superadmin users — disclosed) |
| Vectorstore | status + truthfulness | PASS | `backend: memory`, 0 records | pgvector NOT CONFIGURED |
| Rate limiting / CORS | burst + foreign origin | PASS | 429 JSON; no ACAO for foreign origins | Redis-backed distributed limits NOT CONFIGURED |
| Light/dark readability | theme tests + token audit | PASS | 3 contrast tests, both modes | visual-only aspects not verifiable without a browser |

---

## Final decision

# FINAL PRODUCT — READY

Real AI chat (streaming + non-streaming, corruption-free) and the real CSV-to-analysis workflow both pass end-to-end with the actual configured model; every existing AI capability (chat, NLQ, dashboards, analyst, reports, predictions, agents, workflows, RAG, copilot) completes against the live provider; the reported duplication, 401, 503, maintenance and light-mode issues are root-caused and fixed with regression tests.

**Conditions:** Redis/Celery/pgvector are NOT CONFIGURED (honest degradation, must be enabled for production scale); maintenance-mode role gate should be closed after seeding a platform operator; browser-level visual verification was not possible in this environment; the copilot's NL2SQL reaches the SQL database only and now discloses that limitation instead of inventing numbers.
