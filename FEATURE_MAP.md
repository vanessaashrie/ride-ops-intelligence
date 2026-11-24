# RideOps Intelligence — Insight & Feature Map

A preparation guide for explaining the problem, evidence, product decisions and demo. Numbers below come from the supplied 1,444-ticket investigation (2 Jul–30 Sep 2026; status snapshot 30 Sep).

## 1. The business problem in one minute

RideOps runs employee transport for corporate clients. When a client reports a problem, L1 support tries to resolve it. If it cannot, L1 sends it to Engineering. Engineering may fix it or return it to L1 for more information/configuration work. L1 then closes the ticket.

Leadership sees rising open tickets and wants the number down without hiring. The Support Lead thinks Engineering turnaround is the bottleneck. The Engineering Manager thinks too many incomplete or configuration-related issues are being escalated. Our product should help L1 investigate common issues consistently, capture useful evidence and send better handoffs—while giving leaders visibility into the queue.

**Our chosen user: L1 support agent.** The agent is the person who can run checks, gather evidence and improve the quality of a handoff. The dashboard also gives the Support Lead visibility, but the workflow is designed around L1 action.

## 2. What the data says

| Finding | Evidence | Why it matters |
|---|---:|---|
| Ticket inflow is rising | July 390 → August 462 → September 592 (+51.8% July to September) | More incoming work is landing in the support system. |
| First response is slowing | Median 1.99h → 2.49h → 3.18h | A worsening early customer experience is visible alongside higher inflow. |
| Engineering escalation is common | 486 / 1,444 = 33.7% | Roughly one in three tickets is escalated. |
| Two categories dominate | Roster sync 344 + GPS 228 = 572 (39.6%) | A focused workflow can address a large share of tickets. |
| They dominate the open snapshot | 30 of 48 open tickets (62.5%) are roster sync or GPS | These categories are especially relevant to the current queue. |
| Many escalations return for more work | 173 / 486 = 35.6% ended as insufficient-info or config-issue returns | Better pre-escalation checks and evidence may reduce avoidable back-and-forth. |
| Repeat handoffs are frequent | 229 / 486 = 47.1% had 2+ Engineering handoffs | The escalation path is often not one clean transfer. |
| Reopens are a quality signal | 151 tickets reopened at least once; reopened-ticket median final resolution 70.4h | Closing quickly is not enough if the issue comes back. |
| CSAT is incomplete | Mean 3.70/5 among 648 respondents; coverage 44.9% | Always show the sample size and coverage; don't assume respondents represent everyone. |

### Category details to remember

- **Roster / booking not syncing:** 344 tickets, 175 escalated (50.9%), 17 open, median final resolution 44.48h, respondent CSAT 3.42 (n=153).
- **Live tracking / GPS incorrect:** 228 tickets, 127 escalated (55.7%), 13 open, median final resolution 42.73h, respondent CSAT 3.32 (n=105).
- Combined: 572 tickets, 302 escalations and 30 open. The two categories have 52.8% escalation rate (302/572), compared with 184/872 = 21.1% for all other categories.

### A nuanced interpretation

The data supports targeting roster sync and GPS because they are high-volume, highly escalated and account for most of the open snapshot. It does **not** prove that their information/configuration return rate is uniquely worse than other categories. The case is concentration and workflow leverage—not a claim that every Engineering return is preventable.

## 3. What the dataset cannot prove

These caveats are important in Q&A; they show analytical discipline.

- The brief says backlog is up about 60%, but the CSV has only one status snapshot. We cannot independently verify a historical backlog trend.
- There are no timestamps for assignment to Engineering, Engineering response, return to L1 or individual handoff events. We cannot calculate true Engineering waiting time.
- No SLA targets or business-hour rules are provided. We cannot label any ticket SLA-compliant or breached.
- No shifts, tenure or workload snapshots are provided. We should not rank agents by productivity.
- A category and one-line description are not verified root cause.
- CSAT is missing for 55.1% of tickets; the 3.70 mean is for respondents only.
- Observational data cannot establish that our tool causes lower reopen or escalation rates. A pilot is needed.

## 4. Product logic: insight → feature → user action → expected signal

| Insight | Feature in the demo | What the L1 agent does | What it should improve |
|---|---|---|---|
| Queue and inflow need visibility | Operations Overview | Support Lead sees volume, open snapshot, escalation, reopen and category patterns | Faster prioritisation and a shared operating picture |
| Roster-sync and GPS account for 39.6% of tickets and 62.5% of open tickets | Two targeted diagnostic playbooks | Agent follows a short checklist for the relevant category | More consistent first-line investigation |
| 35.6% of Engineering escalations ended in info/config return verdicts | Evidence checklist + Engineering handoff builder | Agent records checks, identifiers, timestamps, expected vs actual behaviour and evidence | Fewer incomplete handoffs; test this in a pilot |
| 47.1% of escalations had 2+ handoffs | Ticket history fields and handoff context | Agent sees previous handoff count and records work already done | Reduce repeated discovery and improve context continuity |
| Reopened tickets take longer to finally resolve | Reopen visibility in dashboard and ticket details | Agent checks prior reopen history before closing/escalating | Stronger closure quality; monitor reopen rate |
| CSAT coverage is only 44.9% | Dashboard shows CSAT + n + coverage | Support Lead interprets satisfaction cautiously | Avoid misleading conclusions and improve survey instrumentation |

## 5. Feature-by-feature explanation

### A. Operations Overview

**Purpose:** Show where the support workload is concentrated and which signals need attention.

- Total tickets and escalated tickets: size of the observed workload.
- Open tickets: current status as of 30 September, split between L1 and Engineering.
- Reopened tickets: number of tickets reopened at least once.
- Monthly inflow and median first response: show volume and early response trend together.
- Category table: highlights the largest issue categories, their escalation rate and open count.
- Quality signals: Engineering return outcomes, respondent CSAT and repeat handoffs.

**Explain it simply:** “This is not just a chart page. It tells the Support Lead where the queue is concentrated, where Engineering is being pulled in, and where quality signals suggest repeat work.”

### B. Ticket Explorer

**Purpose:** Move from aggregate evidence to an individual case.

The agent can search by ticket ID, client or description, filter by category/status, and open a ticket. The detail view shows client, category, priority, assigned agent, channel, Engineering outcome, handoff count, reopen count and CSAT.

**Explain it simply:** “The dashboard tells us which issue types matter; the ticket explorer lets an agent inspect the actual case and its history.”

### C. Diagnostic Copilot

**Purpose:** Give an agent a consistent starting point, not make an autonomous root-cause decision.

For a roster-sync issue, suggested checks include confirming client/roster date/shift, checking import completion, comparing source and platform values, checking missing or duplicate identifiers, identifying scope and capturing the error.

For GPS, suggested checks include confirming trip and vehicle IDs, checking trip state and device connectivity, recording the last update time, identifying whether one or many trips are affected, and capturing the map symptom.

The current build returns a deterministic rules-based summary because the API key is a placeholder. It is visibly labelled demo mode. It does not pretend to have called an LLM.

**Explain it simply:** “The copilot structures the agent's first investigation. It doesn't claim to know the root cause; it suggests what to verify and what evidence to collect.”

### D. Engineering Handoff Generator

**Purpose:** Make escalation information structured and reusable.

The report contains ticket summary, client and priority context, current status, previous handoff count, reopen count, checks the agent marked as completed, additional notes, evidence still required and the engineering ask.

Only checks explicitly selected by the agent are marked completed. Missing evidence is listed separately. The result is editable/copyable Markdown.

**Explain it simply:** “Instead of sending Engineering a vague description, L1 sends a compact investigation record: what happened, what we checked, what we observed and what is still missing.”

## 6. Data engineering: what happens behind the UI

1. **Ingestion:** Pandas reads the supplied CSV.
2. **Type cleaning:** timestamps are parsed as datetimes; handoffs, reopens and CSAT are numeric.
3. **Derived fields:** `is_escalated`, `is_open`, `reopened`, first-response hours, final-resolution hours, month and open age are computed.
4. **Persistence:** transformed records are loaded into SQLite when the API starts. Indexes are added for category and status.
5. **API layer:** FastAPI exposes overview aggregates, monthly trends, category aggregates, ticket search/detail, playbooks, copilot analysis and handoff generation.
6. **Frontend:** React calls these endpoints and renders the operational views.

**Why this stack?** React provides a polished and flexible interface. FastAPI is lightweight and keeps the analytical/business logic in Python, where Pandas is useful. SQLite avoids infrastructure overhead for a static hackathon dataset. We can build and explain the whole flow without adding cloud databases, queues or microservices.

## 7. How to measure whether the product works

Do not claim the historical dataset proves the product has improved outcomes. Define a pilot and compare a consistent baseline with the pilot cohort.

**Primary measure:** Engineering return rate for insufficient-information/configuration-issue verdicts = those verdicts ÷ Engineering escalations. Baseline in this dataset: 173/486 = 35.6%.

**Supporting measures:**
- Open ticket count and age bands from repeated weekly snapshots.
- Median first useful response, cut by priority and channel.
- Median final resolution time, cut by category and priority.
- Reopen rate, using a consistent ticket cohort and observation window.
- CSAT mean plus response count and coverage.
- Playbook completion and whether recommendations were accepted/rejected.
- Under-escalation audit: sample cases not escalated and reviewed by Engineering.

**Guardrail:** We must not reduce escalation by hiding genuine product defects. A lower Engineering return rate is only good if true bugs are still escalated and customer outcomes do not worsen.

## 8. Four-week next step plan

- **Week 1 — Validate:** Review 20–30 tickets with Support and Engineering; validate checklist steps; agree definitions and instrumentation.
- **Week 2 — Pilot:** Try queue visibility and structured handoff with a small L1 group; capture checklist completion, recommendation disposition and handling time.
- **Week 3 — Refine:** Add/adjust roster and GPS playbooks; review returned escalations and reopened cases with Engineering.
- **Week 4 — Evaluate:** Compare pilot to baseline/cohort; audit under-escalation; review CSAT coverage and resolution quality; decide whether to expand.

## 9. What we deliberately left out

Authentication, roles, live ticket ingestion, real-time event streaming, SLA timers, agent performance ranking, autonomous root-cause classification, complex vector search/RAG, multi-tenant controls and production deployment hardening. None is necessary to demonstrate the core operational hypothesis in this v0.

## 10. A 90-second demo narrative

1. “The dataset has 1,444 tickets. Inflow rose 51.8% from July to September, while median first response moved from 1.99 to 3.18 hours.”
2. “Roster-sync and GPS represent 39.6% of tickets and 30 of the 48 open tickets in the snapshot, so we focus the workflow there.”
3. “The data also shows 35.6% of Engineering escalations ended in an insufficient-info or configuration return, and 47.1% had at least two handoffs.”
4. “Here is a real ticket. The copilot gives the agent a structured starting point and a category-specific checklist.”
5. “The agent records only checks actually completed. The handoff generator then creates a structured report and makes remaining evidence visible.”
6. “We would pilot this with L1 and measure Engineering return rate, reopen rate and resolution quality. We would not claim causality from this historical dataset.”

## 11. Likely questions and concise answers

**Why focus on L1 instead of Engineering?** L1 controls the quality of first-line checks and the information sent with an escalation. It is the intervention point we can influence with a lightweight tool.

**Why these two categories?** They account for 39.6% of tickets and 62.5% of open tickets in the snapshot. Their escalation rates are about 51–56%, much higher than the other categories combined (21.1%).

**Are all 173 info/config returns avoidable?** No. They are a signal that some escalations returned for more information or configuration work. We need case review to determine which are preventable.

**Does the data prove backlog rose 60%?** No. Only one open-status snapshot is supplied. We can show ticket inflow growth, not historical backlog growth.

**Why no vector database or RAG?** The v0 has two explicit checklists and deterministic logic. Retrieval infrastructure would add complexity without enough verified procedural documents to justify it.

**Why SQLite?** This is a single-user/internal demo over a fixed dataset. SQLite is enough and keeps the build reproducible. A production pilot could move to managed Postgres.

**Is the copilot really using an LLM?** Not in this placeholder build. It uses transparent deterministic rules and is labelled as such. The API key placeholder allows a provider integration later; we won't claim an LLM was called when it wasn't.

**How do we know it reduces return loops?** We don't yet. That is the hypothesis. Run a small pilot, measure return outcomes and handling time, and audit for under-escalation.
