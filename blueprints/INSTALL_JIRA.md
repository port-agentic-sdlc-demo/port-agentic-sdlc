# Connect Jira to this Port org

This MCP client cannot start the Jira OAuth install UI. Complete the install in Port, then the existing `jiraIssue` blueprint (already created with factory fields) will receive tickets.

## Install

1. Open [Data sources](https://app.us.port.io/settings/data-sources) (US) and install **Jira**.
2. Authenticate with a Jira Cloud site that has a demo project (for example `DEMO` or `PAY`).
3. Keep the default `jiraIssue` mapping. Do **not** create a second ticket blueprint.
4. After the first sync, confirm `jiraIssue` entities appear. Factory properties already exist on the blueprint:
   - `architectureSpec`, `factoryStage`, `prUrl`, `aiReadinessReason`, `reviewVerdict`
   - relation `service` → `service`
   - mirrors `serviceTier`, `repoUrl`, `servicePath`
5. If the Jira integration mapping overwrites the blueprint, re-add those properties with `upsert_blueprint` using [jiraIssue.json](jiraIssue.json).
6. Map Jira labels if available so tickets tagged `factory` match the workflow condition. If labels are an array property created by Jira, the workflow JQ is:

```
(.diff.after.properties.labels // []) | index("factory") != null
```

Until labels sync, the workflow also accepts tickets whose status becomes `In Progress`.

## Golden-path ticket

Create an issue:

- Summary: `PAY-?? Add structured success/failure logging to payment-service process-with-retry`
- Description: non-empty, mention `payment-service`
- Label: `factory` (if labels are enabled)
- Transition to In Progress
- In Port, set relation `service` = `payment-service` if Architect does not fill it
