# Agentic factory runbook

## What was implemented

Port is the orchestrator. Three local Claude agents do the work.

1. **Context lake** — GitHub Ocean blueprints restored; `service.yml` per service; `jiraIssue` factory fields.
2. **Runner** — `POST /factory/architect|developer|reviewer` (async 202) plus classic `/webhook/action` with **no default Architect routing**.
3. **Workflows** — `agentic_sdlc_plan`, `agentic_sdlc_build` (human INPUT), `agentic_sdlc_review`.
4. **Governance** — scorecard `ai_readiness` on `jiraIssue`; dashboard `agentic_factory`.

Jira Ocean cannot be OAuth-installed from this MCP client. Follow [blueprints/INSTALL_JIRA.md](blueprints/INSTALL_JIRA.md).

## One-time Port secrets

In Port **Settings → Secrets** add:

- `FACTORY_WEBHOOK_URL` = ngrok origin with **no trailing slash**, e.g. `https://abc.ngrok-free.dev`

## Local runner

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill keys
ngrok http 8000
python run_webhook.py
```

`FACTORY_DRY_RUN=1` writes files on disk instead of opening a GitHub PR.

## Golden path

1. Connect Jira (or use `python scripts/rehearse_factory.py` to upsert `FACTORY-PAY` / `FACTORY-FAIL`).
2. Ticket with a description, related service `payment-service`, status **In Progress**.
3. Architect fills `architectureSpec` and `factoryStage=AwaitingApproval`.
4. Approve the workflow run.
5. Developer opens a PR titled with the Jira key.
6. Reviewer comments; `factoryStage=Done`.

Empty description → Plan workflow upserts `factoryStage=Failed` and never calls Developer.
