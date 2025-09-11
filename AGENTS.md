# AGENTS.md

## Mission
Build and run the LeftTurn stack: chat-facing agents (domain/carrier/customer) routing
via an orchestrator to **Structured** (Fabric SQL) and **Unstructured** (Azure AI Search)
tools, plus the Excel validation & notifications flow. Everything must be reproducible,
testable, and evidence-backed.

## Hard rules
- Agents: numbers → Fabric SQL; narrative/clauses → AI Search; Graph only by explicit intent.
- **No raw SQL** from user prompts; use named, parameterized templates.
- Every answer payload includes **evidence** (rows or citations: file/page/clause_id).
- Repo stays strict: type hints, lint clean, tests green, no `pass`/`...` stubs.

## How to work
1. Read this file and `README.md` first.
2. Use `/src/agents/router.py` for intent → tool routing.
3. Approved SQL lives in `/src/services/sql_templates.py` (add template + tests).
4. HTTP calls go through `/src/services/http_client.py` (timeouts, retries).
5. Keep PRs small; update tests and docs together.

## Build / Test
```bash
pip install -r requirements.txt
pre-commit run --all-files
pytest -q
```

## Verification checklist
- [ ] Numeric claims come from curated tables (Fabric).
- [ ] At least one citation for narrative answers (AI Search).
- [ ] No secrets in logs; correlation IDs present.
- [ ] SQL templates parameterized; no string-concat queries.

## Anti-goals
- Ad-hoc OneOff SQL in services, untyped public functions, deprecated SDKs.

---

Friendly reminder to agents (and humans): prefer small, verified changes over grand, untestable gestures.

