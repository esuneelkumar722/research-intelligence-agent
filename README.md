# Research Intelligence Agent

**Production-grade Multi-Agent Research Platform — LangGraph + LangChain on Azure**

Submit a research query. The supervisor analyses it and deploys only the relevant agents in parallel — searching the web, pulling financial data, analysing news sentiment — then synthesises everything into a structured, cited report.

---

## What This System Does

```
User Query: "Analyse NVIDIA's competitive position in the AI chip market"
                               │
                               ▼
              ┌─────────────────────────────────┐
              │         PLANNING NODE            │
              │  LLM analyses query              │
              │  Selects relevant agents only    │
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼──────────────────┐
              │         SUPERVISOR NODE          │
              │  interrupt(): user reviews plan  │
              │  Approves → Send() fan-out       │
              └──────────────┬──────────────────┘
                             │  parallel fan-out (only relevant agents)
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
  │ Web Research│   │ Market Data  │   │ News & Sentiment  │
  │ ReAct Agent │   │ ReAct Agent  │   │ ReAct Agent       │
  │ Tavily API  │   │ yfinance     │   │ Tavily News API   │
  └──────┬──────┘   └──────┬───────┘   └────────┬─────────┘
         └─────────────────┼──────────────────────┘
                           ▼  fan-in (operator.add reducer)
              ┌─────────────────────────────────┐
              │        SYNTHESIS AGENT           │
              │  Cross-references all findings   │
              │  Writes structured Markdown      │
              │  report with numbered citations  │
              └─────────────────────────────────┘
                           │
                           ▼
    "NVIDIA holds ~88% of the AI training chip market..."
     [1] Reuters · [2] Yahoo Finance · [3] Bloomberg
     Tokens used: 33,977 · Estimated cost: $0.11
```

---

## LangGraph Patterns Demonstrated

| Pattern | Where | What It Shows |
|---------|-------|---------------|
| `StateGraph` + typed `AgentState` | `agents/state.py`, `agents/graph.py` | Shared typed state across all nodes |
| **Split supervisor** (planning + interrupt in separate nodes) | `agents/supervisor.py` | Prevents double LLM call on interrupt resume |
| **Dynamic agent selection** | `agents/supervisor.py` | Supervisor picks only relevant agents per query |
| **Parallel fan-out** (`Send()` API) | `agents/supervisor.py` | Agents execute simultaneously |
| **`Annotated[list, operator.add]`** | `agents/state.py` | Parallel fan-in aggregation without overwriting |
| **Human-in-the-loop** (`interrupt()`) | `agents/supervisor.py` | Graph pauses for user plan approval |
| **PostgreSQL checkpointer** | `agents/graph.py`, `core/azure_clients.py` | State persists across restarts (Neon.tech) |
| **`RetryPolicy`** | `agents/graph.py` | Per-node retry on transient LLM/tool failures |
| **SSE streaming** (`astream_events()`) | `api/research.py` | Real-time agent progress to frontend |
| **Nested ReAct subgraphs** | `agents/web_research.py` etc. | Each agent is an independent `create_react_agent` loop |

### Key LangGraph 1.2.x design notes

**Split supervisor pattern** — LangGraph re-runs the entire node function when `interrupt()` resumes. If the LLM call and the interrupt are in the same node, the LLM is called twice: once to create the plan, and again when the user approves. Splitting into `planning_node` (LLM only) → `supervisor_node` (interrupt only) avoids the double call.

**`parent_ids` guard on SSE** — Each research agent uses `create_react_agent` internally, which compiles its own LangGraph. When streaming via `astream_events()`, inner graphs also emit `on_chain_end` with `name == "LangGraph"`. The stream endpoint checks `not event.get("parent_ids")` to only react to the outermost graph's completion.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  ENTRY LAYER                                             │
│  Azure APIM (Consumption) — rate limiting, audit, SSL   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  APPLICATION LAYER                                       │
│  Azure Container Apps (scale-to-zero)                   │
│  FastAPI + LangGraph StateGraph                         │
│  → Content Safety gate (input)                          │
│  → planning_node → supervisor_node → Send() fan-out     │
│  → Synthesis Agent → SSE stream                         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  STATE LAYER                                             │
│  PostgreSQL (Neon.tech) — LangGraph checkpointer        │
│  Azure Cache for Redis — rate limiter                   │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  EXTERNAL SERVICES (tools the agents call)              │
│  Azure OpenAI gpt-5-mini — via API key (dev) /          │
│                             Managed Identity (prod)     │
│  Tavily API           — web + news search               │
│  yfinance             — free financial data             │
│  Wikipedia API        — factual background              │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Core Orchestration | **LangGraph 1.2.x** `StateGraph` | Stateful, checkpointable multi-agent workflows |
| LLM Interface | **LangChain 1.x** `AzureChatOpenAI` | Vendor-agnostic; swap model with one line |
| LLM | Azure OpenAI **gpt-5-mini** | Reasoning model — no `temperature` parameter |
| Tools | Tavily, `yfinance`, Wikipedia | Free/cheap, no proprietary data |
| State Persistence | PostgreSQL via `langgraph-checkpoint-postgres 3.x` | Neon.tech serverless in dev; Azure PostgreSQL in prod |
| Cache | Azure Cache for Redis | Rate limiter (Redis optional; falls back to in-memory) |
| Secrets | Azure Key Vault + Managed Identity | Zero credentials in production code |
| Backend | **FastAPI** + SSE streaming | Async, real-time agent events |
| Frontend | **React + Vite + Tailwind CSS** | TypeScript, SSE-driven live progress UI |
| LLM Observability | **LangFuse self-hosted** | Data never leaves Azure — alternative to LangSmith SaaS |
| Infra Observability | OpenTelemetry → Azure App Insights | Swap exporter to change backend |
| Safety | Azure AI Content Safety | Input safety gate |
| IaC | Terraform (7 modules) | Reproducible; full resource lifecycle |
| CI/CD | GitHub Actions + OIDC (manual trigger) | Zero long-lived credentials in GitHub |

---

## Repository Layout

```
research-intelligence-agent/
├── app/
│   ├── backend/
│   │   ├── agents/
│   │   │   ├── state.py          AgentState TypedDict — shared graph state
│   │   │   ├── graph.py          StateGraph compilation + PostgreSQL checkpointer
│   │   │   ├── supervisor.py     planning_node (LLM) + supervisor_node (interrupt + fan-out)
│   │   │   ├── web_research.py   Web Research ReAct Agent (Tavily + Wikipedia)
│   │   │   ├── market_data.py    Market Data ReAct Agent (yfinance)
│   │   │   ├── news_sentiment.py News + Sentiment ReAct Agent (Tavily news)
│   │   │   └── synthesis.py      Synthesis + Report Writer
│   │   ├── tools/
│   │   │   ├── web_search.py     @tool: Tavily web search
│   │   │   ├── market_data.py    @tool: yfinance (stock info, history, financials)
│   │   │   ├── news_search.py    @tool: Tavily news endpoint
│   │   │   └── wikipedia.py      @tool: Wikipedia lookup
│   │   ├── core/
│   │   │   ├── config.py         Pydantic Settings — all env vars
│   │   │   ├── azure_clients.py  Lifespan: LLM, checkpointer, Tavily client
│   │   │   ├── rate_limiter.py   slowapi per-user rate limiting
│   │   │   ├── content_safety.py Azure AI Content Safety wrapper
│   │   │   └── telemetry.py      OpenTelemetry + LangFuse handler
│   │   ├── api/
│   │   │   ├── research.py       POST /start · POST /approve · GET /stream · GET /result
│   │   │   └── health.py         GET /health liveness probe
│   │   ├── models/research.py    Pydantic request/response models
│   │   ├── app.py                FastAPI factory (CORS, rate limiter, routers)
│   │   └── main.py               uvicorn entry point (sets WindowsSelectorEventLoopPolicy)
│   └── frontend/
│       ├── src/
│       │   ├── App.tsx            Main app state machine (idle→planning→streaming→complete)
│       │   ├── api/research.ts    API client + SSE stream handler
│       │   ├── components/
│       │   │   ├── QueryForm.tsx      Query input + example prompts
│       │   │   ├── PlanReview.tsx     Plan approval UI (human-in-the-loop)
│       │   │   ├── ResearchProgress.tsx  Live agent progress cards
│       │   │   └── FinalReport.tsx    Report display with citations + cost
│       │   └── types/research.ts  Shared TypeScript types
│       ├── vite.config.ts         Dev proxy: /v1 → localhost:8000
│       └── package.json
├── infra/
│   ├── modules/                   One Terraform module per Azure service
│   └── main.tf
├── tests/unit/
├── .github/workflows/ci.yml       Manual-trigger only (workflow_dispatch)
├── pyproject.toml                 Python dependencies (Poetry)
├── .env.sample                    All environment variables documented
└── Makefile
```

---

## Quick Start (Local Dev)

**Prerequisites**: Python 3.12, Poetry, Node.js 18+

> Python 3.12 specifically — Python 3.13+ breaks asyncpg and tiktoken wheel builds.

### 1. Clone and configure

```bash
git clone https://github.com/esuneelkumar722/research-intelligence-agent.git
cd research-intelligence-agent

copy .env.sample .env
```

Edit `.env` — minimum required values:

```env
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-5-mini
AZURE_OPENAI_API_VERSION=2024-12-01-preview
AZURE_OPENAI_API_KEY=<your-key>

TAVILY_API_KEY=<your-key>         # free at https://app.tavily.com

POSTGRES_HOST=<neon-host>
POSTGRES_DB=<db>
POSTGRES_USER=<user>
POSTGRES_PASSWORD=<password>

# Must be JSON array format (pydantic-settings 2.x requirement)
ALLOWED_ORIGINS=["http://localhost:5173","http://localhost:3001"]
```

### 2. Install backend dependencies

```bash
# Select Python 3.12 explicitly if your system has a newer default
poetry env use python3.12
poetry install
```

### 3. Start the backend

```bash
# Must run as a module — sets WindowsSelectorEventLoopPolicy before uvicorn starts (Windows)
poetry run python -m app.backend.main
# → http://localhost:8000  (auto-reloads on file changes)
# → http://localhost:8000/docs  (Swagger UI)
```

### 4. Start the frontend

```bash
cd app/frontend
npm install
npm run dev
# → http://localhost:5173
```

### 5. Test the full flow

Open `http://localhost:5173`, enter a research query, review the plan, approve it, and watch agents run live.

**Or via curl:**

```bash
# Step 1: Start research — returns plan for approval
curl -X POST http://localhost:8000/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyse NVIDIAs competitive position in the AI chip market"}'

# Returns:
# {"session_id": "...", "status": "awaiting_approval", "plan": {"assigned_agents": [...]}}

# Step 2: Stream agent events + approve in one call
curl -N "http://localhost:8000/v1/research/{session_id}/stream?approved=true"

# Step 3: Fetch completed report
curl http://localhost:8000/v1/research/{session_id}/result
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/research/start` | Start session — LLM creates plan, returns it for approval |
| `POST` | `/v1/research/{id}/approve` | Approve/reject plan (blocking, returns when complete) |
| `GET` | `/v1/research/{id}/stream` | SSE stream — resumes graph + streams live agent events |
| `GET` | `/v1/research/{id}/result` | Fetch completed report + citations + token cost |
| `GET` | `/health` | Liveness probe (Container Apps) |

---

## Agent Selection Logic

The supervisor uses the LLM to select only agents relevant to the query:

| Query type | Agents assigned |
|------------|----------------|
| Conceptual / educational ("What is Agentic AI?") | `web_research`, `news_sentiment` |
| Financial / stock ("NVIDIA earnings Q1 2025") | `web_research`, `market_data`, `news_sentiment` |
| Strategy / comparison ("AWS vs Azure cloud strategy") | `web_research`, `news_sentiment` |
| Mixed ("Microsoft cloud revenue and AI strategy") | `web_research`, `market_data`, `news_sentiment` |

---

## Deployment to Azure

```bash
# 1. Create terraform.tfvars
copy infra\terraform.tfvars.sample infra\terraform.tfvars
# Set: tavily_api_key, postgres_admin_password

# 2. Deploy all Azure resources
make deploy ENV=dev
```

### CI/CD Setup (OIDC — no secrets in GitHub)

Set three repository **Variables** (not secrets):

```
AZURE_CLIENT_ID       — az ad app list --display-name "research-agent-oidc"
AZURE_TENANT_ID       — az account show --query tenantId -o tsv
AZURE_SUBSCRIPTION_ID — az account show --query id -o tsv
```

The pipeline is **manual-trigger only** (`workflow_dispatch`) — no auto-deploy on push.

---

## Architectural Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Split supervisor (planning + approval nodes) | Two LangGraph nodes | LangGraph re-runs the entire node on interrupt resume; separating LLM call from interrupt prevents double LLM invocation |
| LangFuse over LangSmith SaaS | Self-hosted LangFuse | LangSmith sends traces to LangChain's cloud — data privacy concern in enterprise |
| PostgreSQL over in-memory | `langgraph-checkpoint-postgres` | Sessions survive pod restarts and rolling deployments |
| Python 3.12 not 3.13+ | asyncpg + tiktoken wheels | No pre-built wheels for Python 3.13+ |
| `ALLOWED_ORIGINS` as JSON array | pydantic-settings 2.14 | pydantic-settings 2.x JSON-decodes list fields; comma-separated strings fail |
| `WindowsSelectorEventLoopPolicy` | Windows + psycopg | psycopg requires SelectorEventLoop; Python 3.8+ defaults to ProactorEventLoop on Windows |
| No `temperature` on gpt-5-mini | Azure reasoning model | Reasoning models only support default temperature (1) |
| `prompt=` not `state_modifier=` | LangGraph 1.2.x | `create_react_agent` parameter renamed in 1.2.x |
| `parent_ids` guard on SSE | LangGraph 1.2.x event model | Inner `create_react_agent` graphs emit `on_chain_end` with `name == "LangGraph"` — must filter to outermost graph only |
| yfinance over Bloomberg | Portfolio project | Free; in production replace with Bloomberg/Refinitiv |

---

## Related Projects

- [azure-openai-rag-solution](https://github.com/esuneelkumar722/azure-openai-rag-solution) — Production-grade RAG platform with hybrid vector search and safety evaluations. Shows static document Q&A; this project shows dynamic multi-agent research.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Security

To report a vulnerability, open a GitHub issue with the `security` label.
