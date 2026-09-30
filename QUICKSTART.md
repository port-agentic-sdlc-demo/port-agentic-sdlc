# Quick Start Guide

Get the Core Agent Foundation up and running in 5 minutes.

## Step 1: Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

## Step 2: Configure Environment (2 min)

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add:
```
ANTHROPIC_API_KEY=sk-ant-your-actual-key
PORT_BASE_URL=https://api.getport.io
PORT_API_TOKEN=your-port-token
```

**Where to get these:**
- **ANTHROPIC_API_KEY**: From https://console.anthropic.com/account/keys
- **PORT_API_TOKEN**: From your Port instance's API settings

## Step 3: Run a Demo (2 min)

```bash
python main.py architect
```

You should see:
1. The agent receives a task
2. The agent calls Port API tools to gather context
3. Claude processes the results
4. The agent returns a detailed response

## What You Just Did

You spun up a Claude agent that:
- ✅ Received a natural language task
- ✅ Autonomously decided what information it needed
- ✅ Called Port API tools to fetch context
- ✅ Reasoned about the context
- ✅ Returned a structured analysis

This is the **core loop** that all three agents use.

## Next: Try the Other Agents

```bash
# Developer agent writing code
python main.py developer

# Reviewer agent analyzing quality
python main.py reviewer
```

## How to Customize

### Change what the agent does:
Edit the system prompt in `agents/architect.py` (or developer/reviewer):

```python
ARCHITECT_SYSTEM_PROMPT = """
Your new instructions here...
"""
```

### Add new Port API calls:
1. Add method to `PortAPIClient` in `tools/port_api.py`
2. Add tool definition to `create_port_tools()`
3. Add handler to `handle_port_tool_call()`

The agent will automatically discover and use the new tool.

### Test with a different Claude model:
Edit `agents/base.py` line 58:
```python
model="claude-sonnet-5-5",  # or claude-haiku-4-5, etc.
```

## Understanding the Code

**Read these files in order:**

1. **`agents/base.py`** (50 lines) - The agent loop
   - Shows how Claude is called
   - Shows how tool results are processed
   - Most important file to understand

2. **`tools/port_api.py`** (150 lines) - Port API integration
   - Shows what tools agents can call
   - Shows how to add new tools

3. **`agents/architect.py`** (15 lines) - Individual agent
   - Just a system prompt wrapper around BaseAgent
   - Customize by changing the prompt

## Debugging

**Agent not responding?**
```bash
# Check your API key works
python -c "import anthropic; print(anthropic.__version__)"
```

**Port API calls failing?**
```bash
# Check environment variables
python -c "import os; print(os.getenv('PORT_API_TOKEN'))"
```

**Want to see the agent's thinking?**
Add debug print in `agents/base.py` line 50:
```python
print(f"[{self.name}] Raw response: {response}")
```

## What's Next

This foundation is ready to integrate with:

1. **Port Webhooks** - Receive tasks from Port, report results back
2. **GitHub Integration** - Clone repos, make commits, open PRs
3. **Jira Integration** - Read tickets, update status
4. **MCP Server** - Run agents from within Cursor IDE

See the main README for the full architecture roadmap.

---

**You're now running the core of an Agentic SDLC!** 🚀
