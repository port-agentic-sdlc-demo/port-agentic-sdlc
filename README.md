# Agentic SDLC POC - Full Implementation

Complete proof-of-concept for orchestrating an Agentic SDLC through Port. This monorepo contains the full pipeline from agent foundation through Port integration.

## Quick Start

**Phase 1: Core Agents** (Foundation - Done ✅)
- Read: [QUICKSTART.md](QUICKSTART.md)
- Run agents locally: `python main.py architect`

**Phase 2: Port Integration** (Web Hooks + Actions - Done ✅)
- Read: [PHASE2_COMPLETE_SETUP.md](PHASE2_COMPLETE_SETUP.md)
- Set up ngrok, import actions, test end-to-end

**Phase 3+: Production** (Deployment, Enhancements)
- Deploy webhook handler to cloud
- Add GitHub/Jira integration
- Monitor and optimize

---

## Overview

This is the **Core Agent Foundation** for orchestrating an Agentic SDLC through Port. It provides three specialized Claude agents that can query Port's software catalog and execute intelligent workflows across the development lifecycle.

## Architecture

```
┌─────────────────┐
│   Port (API)    │  ← Central context lake & orchestrator
└────────┬────────┘
         │
         ├─────────────────────┬─────────────────────┬─────────────────┐
         │                     │                     │                 │
    ┌────▼──────┐      ┌──────▼────┐      ┌─────────▼──┐     ┌────────▼──┐
    │ Architect │      │ Developer │      │  Reviewer  │     │Port Tools │
    │  Agent    │      │   Agent   │      │   Agent    │     └──────┬────┘
    └──────────┘      └───────────┘      └────────────┘            │
         │                  │                   │                   │
         └──────────────────┴───────────────────┴───────────────────┘
                        Claude Agent SDK
                        (with tool use)
```

## Project Structure

**Monorepo containing agents, services, and Port infrastructure:**

```
port-agentic-sdlc/
├── agents/                      # Agent implementations
│   ├── __init__.py
│   ├── base.py                  # BaseAgent class with agent loop
│   ├── architect.py             # Architect Agent
│   ├── developer.py             # Developer Agent
│   └── reviewer.py              # Reviewer Agent
├── tools/                       # Tool integrations
│   ├── __init__.py
│   └── port_api.py              # Port API client & tool definitions
├── services/                    # Microservices (Python/FastAPI)
│   ├── auth-service/            # User authentication
│   ├── notification-service/    # Notification handling
│   └── payment-service/         # Payment processing
├── blueprints/                  # Port infrastructure as code
│   ├── service.json             # Service blueprint definition
│   ├── entities/                # Service entity configurations
│   └── actions/                 # Self-service action definitions
│       ├── design_service.json
│       ├── implement_feature.json
│       └── review_code.json
├── agents/                      # (continued above)
│   └── webhook_handler.py       # Webhook receiver for Port
├── main.py                      # Demo/test entry point
├── run_webhook.py               # Webhook handler startup script
├── test_webhook.py              # Local webhook testing
├── requirements.txt             # Python dependencies
├── .gitignore                   # Prevents credential exposure
├── .env.example                 # Environment template (commit this)
├── README.md                    # This file
├── QUICKSTART.md                # 5-min getting started
├── WEBHOOK_HANDLER.md           # Webhook API docs
├── PHASE2_COMPLETE_SETUP.md     # Full integration guide
└── PHASE2_SETUP.md              # (deprecated, use PHASE2_COMPLETE_SETUP.md)
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

You'll need:
- `anthropic>=0.30.0` - Claude API client
- `requests>=2.31.0` - HTTP requests (for Port API calls)
- `python-dotenv>=1.0.0` - Environment variable management
- `pydantic>=2.0.0` - Data validation

### 2. Configure Environment Variables

Create a `.env` file (or set these in your environment):

```bash
# Anthropic API
ANTHROPIC_API_KEY=your-anthropic-api-key

# Port Configuration
PORT_BASE_URL=https://api.getport.io  # or your Port instance URL
PORT_API_TOKEN=your-port-api-token    # Port API token
```

⚠️ **SECURITY**: The `.gitignore` file prevents `.env` from being committed. **Never commit API keys or credentials to Git.** If you accidentally commit a key:
1. Revoke the key immediately in the service (Anthropic dashboard, Port settings)
2. Generate a new key
3. Update your `.env` file

Use `.env.example` as a template for new developers without exposing actual credentials.

## Running the Agents

### Run All Demos
```bash
python main.py
```

### Run Individual Agent Demos
```bash
python main.py architect
python main.py developer
python main.py reviewer
```

## How It Works

### The Agent Loop

Each agent inherits from `BaseAgent`, which implements the core agentic loop:

1. **Send** user input + system prompt to Claude
2. **Claude thinks** and decides if it needs to call a tool
3. **Tool Use**: If Claude calls a tool:
   - Extract tool name and inputs
   - Execute tool (Port API calls)
   - Feed results back to Claude
4. **Repeat** until Claude completes the task (max 10 iterations)
5. **Return** final response

### Available Tools

The agents have access to the following Port API tools:

| Tool | Purpose |
|------|---------|
| `port_get_entity` | Fetch a service, ticket, or other entity from Port's catalog |
| `port_search_entities` | Search for entities by blueprint type (e.g., 'service', 'jira-ticket') |
| `port_get_service_dependencies` | Get upstream/downstream deps and tech stack for a service |
| `port_trigger_action` | Trigger a self-service action in Port |
| `port_update_action_status` | Report back action status (running, success, failure) |

### The Three Agents

#### 1. **Architect Agent**
- **Role**: Designs new services and features with organizational standards
- **Workflow**: Queries existing services → Understands patterns → Proposes architecture
- **Output**: Architecture specification, tech stack recommendations, dependency analysis

#### 2. **Developer Agent**
- **Role**: Implements features and bug fixes, writes code, opens PRs
- **Workflow**: Receives ticket → Queries service context → Writes code → Opens PR
- **Output**: Pull request URL, code changes, ticket status update

#### 3. **Reviewer Agent**
- **Role**: Conducts security, style, and performance reviews
- **Workflow**: Reviews PR → Finds issues → Reports findings
- **Output**: Security findings, style violations, performance concerns, remediation suggestions

## Extending the Agents

### Adding New Port Tools

1. Add the tool logic to `tools/port_api.py` (PortAPIClient class)
2. Add the tool definition to `create_port_tools()`
3. Add handler in `handle_port_tool_call()`

### Customizing Agent Behavior

Each agent's behavior is defined by its system prompt. To change an agent's behavior:

1. Edit the `SYSTEM_PROMPT` in the agent file (e.g., `agents/architect.py`)
2. The agent will automatically use the new instructions on the next run

### Using a Different Claude Model

Edit `agents/base.py`, line 58:
```python
response = self.client.messages.create(
    model="claude-opus-5-5",  # Change this to claude-sonnet-5-5, etc.
    ...
)
```

## Integration Points

This foundation is designed to integrate with:

1. **Port**: Queries the software catalog and triggers actions via API
2. **GitHub**: (Next phase) Clone repos, open PRs, commit code
3. **Jira**: (Next phase) Read tickets, update status
4. **CI/CD**: (Next phase) Run builds, verify changes

## Next Steps

After validating the core agent loop, the POC will add:

### Phase 2: Port Integration Layer
- Self-service action webhooks
- Action status reporting
- Real Port instance integration

### Phase 3: MCP Bridge for Cursor
- Build Port MCP Server
- Integrate Cursor with agent orchestration
- Developer experience optimization

### Phase 4: End-to-End Demo
- Wire GitHub integration
- Connect Jira
- Build AI adoption dashboard in Port

## Security

### Protecting Credentials

This project uses `.gitignore` to prevent accidental credential exposure:

**Protected files:**
- `.env` - API keys, tokens, credentials (never commit)
- `.env.local` - Local overrides (never commit)
- `secrets.json`, `credentials.json` - Credential files (never commit)

**Best practices:**
1. Use `.env.example` as a template showing what variables are needed
2. Never commit actual `.env` files with real credentials
3. Use environment variables in CI/CD (GitHub Actions secrets, etc.)
4. Rotate API keys immediately if accidentally exposed
5. Use minimal-scope API tokens (only what's needed)

**If you accidentally commit a credential:**
1. Revoke the credential immediately (Anthropic, Port, etc.)
2. Generate a replacement
3. Force-push to remove the commit (for private repos only)
4. Never attempt to "hide" exposed credentials in later commits

## Troubleshooting

### "ModuleNotFoundError: No module named 'anthropic'"
Run: `pip install -r requirements.txt`

### Agents not responding
- Check `ANTHROPIC_API_KEY` is set
- Verify API key has access to Claude models
- Check the model name in `agents/base.py`

### Port API calls failing
- Verify `PORT_BASE_URL` and `PORT_API_TOKEN` are correct
- Port API endpoints use mock responses by default for testing

### ".env file not being loaded"
- Verify `.env` file exists in project root
- Check that `.env` is not in `.gitignore` (it should be — the .env file itself, not the .env.example)
- Verify `load_dotenv()` is called in `main.py` before accessing environment variables

## Key Files to Know

- **`agents/base.py`**: The core agent loop - this is where the magic happens
- **`tools/port_api.py`**: Port API integrations - add new tools here
- **`main.py`**: Demo/test entry point - start here to see the agents in action

---

**Status**: Core Foundation Complete ✓
**Ready for**: Phase 2 - Port Integration Layer
