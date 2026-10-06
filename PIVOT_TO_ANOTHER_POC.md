# Port Customer POC — From Scratch (Acme Payments)

Use this document as the product brief and implementation plan for a **new empty repo**.
Do **not** port or salvage this `port-agentic-sdlc` factory POC. Rebuild with a customer narrative first.

Keep this repo as a reference if useful; start the new project from Phase 0 below.

## Goal

Show a realistic customer journey:

1. Acme already has services, GitHub, and Jira.
2. They adopt Port as the **context lake** (catalog, ownership, readiness).
3. Only then add **one** governed agentic workflow with a human approval gate.

Port is the product spine. Agents are workers behind webhooks, not the hero.

## Non-goals (v1)

- Three independent catalog action buttons as the main demo path
- Perfect monorepo PR→service mapping for every file path
- Port Execution Agent / Kafka
- Replacing local agents with Cursor Cloud Agents on day one
- Shipping/deploy blast-radius gates
- Ngrok + three roles before the catalog story lands

## Customer brief (lock this before code)

**Company:** Acme Payments (fictional)

**Existing world (before Port):**
- Monorepo with 3 FastAPI services: `auth-service`, `payment-service`, `notification-service`
- GitHub org + this monorepo
- Jira Cloud project for feature work
- Ownership tribal (“ask platform”); no single place for tier / deps / “is this ticket AI-ready?”

**Pain:**
Feature tickets bounce between architecture, coding, and review with no shared readiness check and no approval trail.

**Port after:**
- Services, PRs, and Jira issues live in one catalog with relations
- Scorecard blocks unready tickets
- One workflow: ticket ready → Architect plan → human Approve → (later) Developer PR → Reviewer

**Golden ticket (demo identity):**
Jira key is the run ID (e.g. `PAY-12`).
Title: *Add structured success/failure logging to `payment-service` process-with-retry*
Every writeback (`architectureSpec`, `factoryStage`, `prUrl`, `reviewVerdict`) lands on that `jiraIssue` entity.

**Audience:** platform eng first; leadership sees dashboard + approval only.

**Credentials needed (document in `.env.example`, never commit secrets):**
Port client ID/secret (US), Anthropic, GitHub PAT (contents + PRs), Jira (via Port Ocean UI), ngrok only when agents are introduced.

---

## Phase 0 — Repo skeleton (day 0)

Empty git repo. Minimal structure:

```
/
  README.md                 # customer story + phased demo script (10 min)
  .env.example
  services/
    auth-service/
    payment-service/
    notification-service/
      each: FastAPI stub + service.yml + README
  blueprints/               # Port JSON as code
  docs/
    CUSTOMER_BRIEF.md       # copy of the brief above
    DEMO_SCRIPT.md          # minute-by-minute talk track
```

Rules:
- One composition of the story in README: Acme → Port → one workflow.
- Each service has `service.yml`: `name`, `owner`, `language`, `port`, `dependencies`, `path`, `github_repository_id`, `serviceTier` (use Tier 2 for demos; reserve Tier 1 for “blocked” story later).
- No agents, no webhooks, no factory workflows in Phase 0.

Deliverable: `git push` of three runnable stubs + brief. Demo: “this is Acme’s world before Port.”

---

## Phase 1 — Context lake only (no agents)

### 1a. GitHub Ocean
- Install GitHub Ocean in Port.
- Ensure default blueprints exist: `githubOrganization`, `githubRepository`, `githubPullRequest`, `githubUser`, `githubTeam`, `githubWorkflow`, `githubWorkflowRun`, `deployment` (initialize if missing).
- Confirm entities appear after resync.

### 1b. Core `service` blueprint (do not invent a second service catalog)
Properties: `name`, `description`, `language`, `owner`, `repository_url`, `path`, `github_repository_id`, `serviceTier`, `port`, `dependencies`, `tech_stack`, health URL as needed.
Relations: keep lean; ownership via `$team` if teams exist.
Map `kind: file` for `services/**/service.yml` → `service` (identifier = folder name). Keep repo/PR kinds.

### 1c. Jira Ocean
- Install Jira in Port UI (MCP cannot OAuth-install).
- Use real `jiraIssue` blueprint; extend it (do not invent `workItem`):
  - Relation `service` → `service`
  - Properties: `architectureSpec` (markdown), `factoryStage` enum (`Triage|Plan|AwaitingApproval|Build|Review|Done|Failed`), `prUrl`, `aiReadinessReason`, `reviewVerdict`
  - Mirrors: `serviceTier`, `repoUrl`, `servicePath` from related service
- Confirm tickets sync; manually relate golden ticket to `payment-service` if mapping cannot.

### 1d. Entity pages & catalog UX
- On `jiraIssue` entity Overview: **show** `factoryStage`, `prUrl`, `architectureSpec`, `aiReadinessReason` (do not leave them in `hiddenQuery`).
- Catalog pages for `service` and `jiraIssue`.

**Demo win:** In Port, answer: who owns `payment-service`, what depends on it, which Jira ticket targets it.

Exit criteria: GitHub + Jira + 3 services visible with relations; no agents required.

---

## Phase 2 — Governance without AI

### 2a. Scorecard `ai_readiness` on `jiraIssue`
Bronze rules (example):
- description not empty
- related `service` set (or mirror `servicePath` / `serviceTier` present)
- `serviceTier != Tier 1`

Fail path reason string: store on `aiReadinessReason` when workflow later blocks.

### 2b. Dashboard **Acme Software Factory** (or Agentic Factory)
Table of `jiraIssue` with columns: identifier, title, status, factoryStage, prUrl, related service.
Sidebar folder for the demo.
Intro markdown: 3 bullets only (catalog → readiness → later agents).

### 2c. Human-only workflow (optional but powerful)
`acme_feature_intake`:
1. SELF_SERVE or EVENT on jiraIssue
2. CONDITION scorecard / description
3. INPUT Approve / Decline
4. UPSERT `factoryStage`

**Demo win:** empty description fails scorecard; ready ticket can be approved with an audit trail. Still no Claude.

Exit criteria: leadership can see blocked vs ready tickets on one dashboard.

---

## Phase 3 — One agent (Architect only)

### 3a. Local runner (minimal)
- FastAPI app: `POST /factory/architect` only
- Parse JSON body from Port WEBHOOK (not query-param hacks)
- Return **202**; agent upserts Port via REST (`PORT_CLIENT_ID`/`PORT_CLIENT_SECRET`, prefer client credentials over pasted JWT)
- Port WEBHOOK: `synchronized: false`, `agent: false`
- Document Port secret `FACTORY_WEBHOOK_URL` = ngrok origin, no trailing slash
- Log with `flush=True`; use `PYTHONUNBUFFERED=1`

### 3b. Architect contract
Inputs: jira_key, title, description, service_id, service_path  
Tools: Port REST search/get/upsert only  
Output: structured plan + upsert `architectureSpec`, `factoryStage=AwaitingApproval` on the `jiraIssue`

### 3c. Workflow `acme_plan` (or `agentic_sdlc_plan`)
1. EVENT_TRIGGER `jiraIssue` ENTITY_UPDATED  
   JQ must be plain JQ (no invented helpers like `IN(...)`):
   - status == `"In Progress"`
   - factoryStage == `"Triage"` (or empty treated as Triage via `//`)
2. CONDITION: description non-empty → Architect webhook; else UPSERT Failed + reason
3. Stop. Human approval is a **separate** build workflow or INPUT node in the next phase—prefer two workflows if PR ingest is async later.

**Demo win:** ticket In Progress → plan appears on entity → dashboard stage AwaitingApproval.

Known pitfalls to avoid:
- Entity page hiding factory fields via `hiddenQuery`
- Workflow runs may stay IN_PROGRESS on async webhooks — **entity `factoryStage` is source of truth**, not the run list
- Prefer Port client credentials over a pasted JWT in `.env`

---

## Phase 4 — Approve → Developer (real GitHub)

Only after Phase 3 is crisp.

### Developer
- Tools: GitHub branch / put file (prefix-gated to `services/<id>/`) / create PR
- Write `prUrl` + `factoryStage=Review` (or Build then Review) to jiraIssue
- `FACTORY_DRY_RUN=1` for laptop-only rehearsal; default demo path uses real `GITHUB_TOKEN`

### Workflow `acme_build`
1. Trigger when `factoryStage` becomes `AwaitingApproval`
2. INPUT Approve / Decline (Admin)
3. WEBHOOK Developer

### Reviewer (last)
- Separate workflow on `githubPullRequest` ENTITY_CREATED with `jiraIssueKey` or relation set
- Comment on PR; upsert `reviewVerdict` + `factoryStage=Done`
- Do not promise Review without a real PR in Port

**Demo win:** approve → real PR in monorepo → Ocean ingests PR → Reviewer → Done on same ticket row.

---

## Phase 5 — Golden-path rehearsal script

Document in `docs/DEMO_SCRIPT.md`:

1. Show catalog: 3 services, deps, GitHub repo.
2. Show scorecard fail ticket (empty description) vs ready ticket.
3. Move ready ticket to In Progress → Architect plan on entity.
4. Approve → PR link on entity → dashboard Done.
5. Explicitly say what is Port vs what is the local agent.

Failure path always rehearsed.

---

## Lessons from the prior factory POC (do not repeat)

1. Build catalog + scorecard + dashboard before agents.
2. Do not start with three agents and three workflows on day one.
3. Entity Overview must show `factoryStage` / `prUrl` (unhide them).
4. Trigger JQ must be valid plain JQ.
5. Async WEBHOOK runs can look “stuck In progress”; trust the ticket stage.
6. Review workflow needs a real GitHub PR in Port; dry-run compare URLs will not fire it.
7. MCP cannot install Jira OAuth; do that in the Port UI.

---

## Implementation rules for the coding agent

1. Follow phases in order. Do not implement Phase 3–4 until Phase 1–2 exit criteria are met unless the user explicitly skips.
2. Prefer Port MCP for blueprints, scorecards, workflows, pages; use REST in the local runner.
3. Author workflow/blueprint JSON under `blueprints/` and apply via MCP `upsert_*`.
4. One factory run identity = Jira issue key.
5. Fix entity Overview `hiddenQuery` so factory properties are visible.
6. WEBHOOK URLs use `{{ .secrets["FACTORY_WEBHOOK_URL"] }}/factory/...`.
7. Never default unknown action IDs to Architect.
8. Keep the customer story in README; do not create a second parallel ticket blueprint.
9. Mark todos per phase; stop at phase gates for human demo validation.
10. This document is the source of truth for the new repo. Do not depend on the old `FACTORY.md` or plan files in `port-agentic-sdlc` except as optional reference.

---

## Suggested todos (create these in the new repo)

- [ ] phase-0-skeleton — monorepo stubs + service.yml + README customer story
- [ ] phase-1-context-lake — GitHub/Jira blueprints, service mapping, entity pages
- [ ] phase-2-governance — ai_readiness scorecard + Acme dashboard (+ optional human workflow)
- [ ] phase-3-architect — local /factory/architect + plan workflow + secret docs
- [ ] phase-4-build-review — Developer/Reviewer + build/review workflows + real PR path
- [ ] phase-5-rehearsal — DEMO_SCRIPT.md + golden + fail tickets verified end-to-end

---

## First message to the agent in the new repo

Copy `PIVOT_TO_ANOTHER_POC.md` into the new repo (e.g. as `CUSTOMER_POC_PLAN.md`), then paste:

> Implement Phase 0 and Phase 1 of `CUSTOMER_POC_PLAN.md` only. Stop at the Phase 1 exit criteria and summarize what I should click in Port to validate the Acme catalog story. Do not add agents or factory webhooks yet.
