# RideOps Intelligence — Hackathon v0 (Groq-enabled)

A React + FastAPI support-operations demo using the supplied RideOps ticket dataset. The L1 copilot uses Groq when configured and clearly identifies rules-based mode when it is not.

## Stack
- Frontend: React + Vite, Recharts, Lucide icons, custom CSS
- Backend: FastAPI + Pandas
- Storage: SQLite (created automatically from the supplied CSV)
- LLM: Groq Chat Completions API through the OpenAI-compatible Python SDK
- Default model: `openai/gpt-oss-20b` (change via `GROQ_MODEL` if your Groq account has a different currently available model)

## 1. Get a Groq API key
1. Sign in at https://console.groq.com/.
2. Create an API key at https://console.groq.com/keys.
3. Copy `.env.example` to `.env` in the project root.
4. Replace `your_groq_api_key_here` with your key. Do not include quotes.
5. Never paste the key into chat, frontend code, GitHub, or a committed file. `.env` is ignored by Git.

Example `.env`:
```dotenv
GROQ_API_KEY=gsk_your_real_key_here
GROQ_MODEL=openai/gpt-oss-20b
GROQ_BASE_URL=https://api.groq.com/openai/v1
```

## 2. Run the project
Requires Python 3.10+ and Node 20+.

### Terminal 1 — backend
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r ../requirements.txt
uvicorn main:app --reload --port 8000
```

### Terminal 2 — frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

## 3. Confirm the Groq API actually works
The app deliberately does **not** send a paid/limited test request on every startup.

With the backend running, open a third terminal and run:
```bash
curl -X POST http://localhost:8000/api/llm-test
```
Or open http://localhost:8000/docs and execute `POST /api/llm-test`.

This sends one tiny request (maximum 12 output tokens). A successful result returns `GROQ CONNECTION OK` and token usage. The backend terminal prints a clear `[RideOps][Groq] CONNECTION OK` line.

Then open a ticket in the app and click **Analyse ticket**. The response badge should say **GROQ LLM**. If it says **RULE-BASED DEMO**, the key is not configured or remains a placeholder.

## Loud failure diagnostics
Every failed live Groq call prints a large, unmistakable alert in the backend terminal:
- `CREDIT_OR_BILLING_EXHAUSTED`: response indicates exhausted credits/billing/account balance. Check Groq Console billing/usage; retrying won't fix it.
- `RATE_LIMIT_OR_QUOTA`: HTTP 429 without a clear billing/credit error. This can be RPM/TPM/TPD or another model/account rate cap; it is **not automatically a billing failure**.
- `API_ERROR`, `MISSING_API_KEY`, or `CONNECTION_OR_TIMEOUT`: inspect the printed detail, key, model ID, network and service status.

The API returns a visible error to the frontend. When a live Groq call fails, the server does not silently substitute rules-based output and pretend the LLM worked. Rules-based mode is used only when no Groq key is configured.

## Credit-saving measures built into this demo
1. **No startup ping:** no tokens are used just by starting the app.
2. **Explicit calls only:** an LLM request happens only when the user clicks Analyse ticket (or explicitly calls `/api/llm-test`). Dashboard loads, filters, playbooks and handoff generation do not call Groq.
3. **SQLite response cache:** a successful ticket analysis is cached by ticket ID + model + prompt version. Reopening/re-analysing that ticket makes no new API call. Delete `data/rideops.db` only if you intentionally want to clear this cache (it also rebuilds the derived ticket database from CSV).
4. **Small context:** only the selected ticket's relevant fields and a short checklist are sent. No full CSV, ticket history dump, or conversation transcript is sent.
5. **Small output budget:** each analysis is capped at 420 output tokens; the connection test at 12.
6. **No automatic retries:** avoids duplicate token consumption during quota/rate-limit failures. Billing/credit errors are never retried.
7. **Compact prompts and JSON:** limits verbose responses and frontend payloads.
8. **No LLM for handoffs:** handoff reports are assembled deterministically from ticket data and agent-selected checks.

For a hackathon demo, analyse only a few representative tickets: one roster-sync, one GPS, and optionally one general category. Use cached results for repeat demonstrations.

## API endpoints
- `GET /api/health` — app/database/provider configuration status; no LLM call.
- `POST /api/llm-test` — one explicit minimal live Groq test.
- `GET /api/overview`, `/api/trends`, `/api/categories` — analytics; no LLM call.
- `GET /api/tickets`, `/api/tickets/{ticket_id}` — ticket search/detail; no LLM call.
- `GET /api/playbooks` — proposed diagnostic checklists; no LLM call.
- `POST /api/analyze` — Groq analysis if configured; successful result cached; rules-based demo only if no key.
- `POST /api/handoff` — deterministic Markdown handoff; no LLM call.

## Data engineering flow
1. Read the source CSV with Pandas.
2. Parse timestamps and numeric columns; derive escalation/open/reopen flags, response and final-resolution durations, month and open age.
3. Load transformed records into SQLite at `data/rideops.db` on API startup; add indexes for category and status.
4. Store successful LLM analysis results in a separate SQLite cache table.
5. Serve aggregate and ticket-level data through FastAPI endpoints.

## Interpretation guardrails
- Status is a **30 Sep 2026 snapshot**, not a status history.
- Monthly ticket inflow is not backlog. A historical backlog increase cannot be verified from this one snapshot.
- CSAT averages are for respondents only; show response count and coverage.
- Engineering handoffs count round trips per the supplied data dictionary; they do not reveal precise transition times.
- Playbooks are proposed demo checklists, not verified RideOps procedures. Validate them with Support and Engineering before real use.
- Copilot output is decision support, not verified root cause. The handoff generator includes only checks selected by the agent.

## Suggested demo path
1. Overview: point out inflow/response deterioration and the two high-volume categories.
2. Ticket explorer: open a roster-sync or GPS issue.
3. Diagnostic copilot: generate summary and initial checks (first analysis uses Groq; repeat uses cache).
4. Playbooks: explain evidence to capture before Engineering escalation.
5. Engineering handoff: mark only checks actually completed, add notes and generate a structured handoff.

## Deliberately not included in v0
Authentication, roles, live ticket ingestion, real-time queue events, verified root-cause prediction, SLA compliance, agent performance ranking, multi-tenant controls and production deployment hardening.
