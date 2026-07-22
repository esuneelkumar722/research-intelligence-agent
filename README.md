# Research Intelligence Agent

**Production-grade Multi-Agent Research Platform — LangGraph + LangChain on Azure**

Submit a research query. A team of AI agents fans out in parallel — searching the web, pulling financial data, analysing news sentiment — then synthesises everything into a structured, cited report in minutes.

This project demonstrates how to build and deploy enterprise-grade agentic AI applications with LangChain and LangGraph, following the same patterns used by Lyft, Klarna, and C.H. Robinson in production.

---

## What This System Does

```
User Query: "Analyse NVIDIA's competitive position in the AI chip market"
                               │
                               ▼
              ┌─────────────────────────────────┐
              │         SUPERVISOR AGENT         │
              │  Analyses query → builds plan    │
              │  interrupt(): user approves plan │
              └──────────────┬──────────────────┘
                             │  Send() fan-out (parallel)
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
  ┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
  │ Web Research│   │ Market Data  │   │ News & Sentiment  │
  │ Agent       │   │ Agent        │   │ Agent             │
  │ Tavily API  │   │ yfinance     │   │ Tavily News API   │
  └──────┬──────┘   └──────┬───────┘   └────────┬─────────┘
         └─────────────────┼──────────────────────┘
                           ▼  fan-in (all findings)
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
     Tokens used: 4,821 · Estimated cost: $0.0041
```

---

## LangGraph Patterns Demonstrated

This project is specifically built to showcase the **production LangGraph patterns** that enterprise companies use:

| Pattern | Where Used | What It Shows |
|---------|-----------|---------------|
| `StateGraph` + typed `AgentState` | `agents/state.py`, `agents/graph.py` | Shared typed state across all nodes |
| **Supervisor routing** (`Command(goto=...)`) | `agents/supervisor.py` | Dynamic agent dispatch based on query |
| **Parallel fan-out** (`Send()` API) | `agents/supervisor.py` | 3 agents execute simultaneously |
| **`Annotated[list, operator.add]`** | `agents/state.py` | Parallel fan-in aggregation without overwriting |
| **Human-in-the-loop** (`interrupt()`) | `agents/supervisor.py` | Graph pauses for user plan approval |
| **PostgreSQL checkpointer** | `agents/graph.py`, `core/azure_clients.py` | State persists across pod restarts |
| **`RetryPolicy` + `TimeoutPolicy`** | `agents/graph.py` | Per-node fault tolerance |
| **`error_handler`** | `agents/web_research.py` etc. | Graceful degradation when agents fail |
| **SSE streaming** (`astream_events()`) | `api/research.py` | Real-time agent progress to frontend |
| **Subgraph architecture** | All agent files | Each agent is an independent ReAct subgraph |

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
│  → Supervisor → interrupt() → Send() fan-out            │
│  → Synthesis Agent → SSE stream                         │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  STATE LAYER                                             │
│  PostgreSQL Flexible Server — LangGraph checkpointer    │
│  Azure Cache for Redis — semantic cache + rate limiter  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│  EXTERNAL SERVICES (tools the agents call)              │
│  Azure OpenAI GPT-4o  — via Managed Identity (no key)  │
│  Tavily API           — web + news search               │
│  yfinance             — free financial data             │
│  Wikipedia API        — factual background              │
└─────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Core Orchestration | **LangGraph** `StateGraph` | Stateful, checkpointable multi-agent workflows |
| LLM Interface | **LangChain** `AzureChatOpenAI` | Vendor-agnostic; swap model with one line |
| LLM | Azure OpenAI GPT-4o | Data residency in Azure, Managed Identity auth |
| Tools | Tavily, `yfinance`, Wikipedia | Free/cheap, no proprietary data |
| State Persistence | PostgreSQL (`langgraph-checkpoint-postgres`) | Production-grade; survives pod restarts |
| Cache | Azure Cache for Redis | Semantic cache + distributed rate limiter |
| Secrets | Azure Key Vault + Managed Identity | Zero credentials in code |
| Backend | FastAPI + SSE streaming | Async, real-time agent events |
| LLM Observability | **LangFuse self-hosted** (Container App) | Data never leaves Azure — enterprise alternative to LangSmith SaaS |
| Infra Observability | OpenTelemetry → Azure App Insights | Same instrumentation as Datadog; swap exporter to change backend |
| Safety | Azure AI Content Safety | Input/output safety gates |
| IaC | Terraform (7 modules) | Reproducible; full resource lifecycle |
| CI/CD | GitHub Actions + OIDC | Zero long-lived credentials in GitHub |

> **On LangFuse vs LangSmith**: LangSmith SaaS sends prompts and responses to LangChain's cloud, which is a data privacy concern in enterprise environments. This project uses LangFuse self-hosted on Azure Container Apps — same features, all data stays inside your Azure subscription.

---

## Production-Grade Features

These are what separate this from a demo app:

1. **PostgreSQL checkpointer** — sessions survive pod crashes and rolling deployments
2. **`interrupt()` human-in-the-loop** — user approves the research plan before agents execute
3. **`RetryPolicy` + `TimeoutPolicy`** — every agent node retries on transient failures (Tavily/yfinance outages)
4. **Error handlers** — if an agent exhausts retries, a partial result is still returned so synthesis runs with remaining data
5. **Semantic result cache** — identical or similar queries bypass LLM calls entirely (Redis)
6. **Per-user rate limiting** — JWT `oid` claim as key (not IP) — each user behind a corporate NAT gets individual limits
7. **Cost tracking** — token count + USD estimate in every response
8. **Content Safety gates** — Azure AI Content Safety on both input and output
9. **Managed Identity** — Container App accesses Azure OpenAI without any API key
10. **OIDC CI/CD** — GitHub deploys to Azure without any stored credentials

---

## Repository Layout

```
research-intelligence-agent/
├── app/backend/
│   ├── agents/
│   │   ├── state.py          AgentState TypedDict — shared graph state
│   │   ├── graph.py          StateGraph compilation + PostgreSQL checkpointer
│   │   ├── supervisor.py     Supervisor node — query plan + interrupt() H-I-L
│   │   ├── web_research.py   Web Research Agent (Tavily + Wikipedia tools)
│   │   ├── market_data.py    Market Data Agent (yfinance tools)
│   │   ├── news_sentiment.py News + Sentiment Agent (Tavily news)
│   │   └── synthesis.py      Synthesis + Report Writer Agent
│   ├── tools/
│   │   ├── web_search.py     @tool: Tavily web search
│   │   ├── market_data.py    @tool: yfinance (stock info, history, financials)
│   │   ├── news_search.py    @tool: Tavily news endpoint
│   │   └── wikipedia.py      @tool: Wikipedia lookup
│   ├── core/
│   │   ├── config.py         Pydantic Settings — all env vars + feature flags
│   │   ├── azure_clients.py  Lifespan: LLM, checkpointer, Tavily client setup
│   │   ├── rate_limiter.py   slowapi per-user rate limiting (JWT oid key)
│   │   ├── content_safety.py Azure AI Content Safety wrapper
│   │   └── telemetry.py      OpenTelemetry → App Insights + LangFuse handler
│   ├── api/
│   │   ├── research.py       POST /start, POST /approve, GET /stream (SSE), GET /result
│   │   └── health.py         GET /health (Container Apps liveness probe)
│   ├── models/research.py    Pydantic request/response models
│   ├── app.py                FastAPI factory (CORS, rate limiter, routers)
│   ├── main.py               uvicorn entry point
│   └── Dockerfile            Multi-stage production image
├── infra/
│   ├── modules/              One Terraform module per Azure service
│   │   ├── openai/           Azure OpenAI + GPT-4o deployment
│   │   ├── container_apps/   Backend app + LangFuse Container Apps
│   │   ├── container_registry/ ACR
│   │   ├── postgres/         PostgreSQL Flexible Server
│   │   ├── redis/            Azure Cache for Redis
│   │   ├── key_vault/        Key Vault (RBAC mode)
│   │   └── monitoring/       Log Analytics + Application Insights
│   ├── main.tf               Root module — calls all modules + RBAC assignments
│   ├── variables.tf
│   └── outputs.tf
├── tests/unit/               Unit tests (no Azure required)
├── .github/workflows/ci.yml  5-job CI/CD pipeline
├── docker-compose.yml        Local dev: backend + postgres + redis + langfuse
├── Dockerfile.dev            Python-only dev image (no frontend build)
├── pyproject.toml            Dependencies (Poetry)
├── .env.sample               All environment variables documented
└── Makefile                  make dev | test | lint | deploy | destroy
```

---

## Quick Start (Local Dev)

**Prerequisites**: Python 3.11+, Docker Desktop, Poetry

```bash
# 1. Clone and enter the project
git clone https://github.com/esuneelkumar722/research-intelligence-agent.git
cd research-intelligence-agent

# 2. Copy and fill environment variables
copy .env.sample .env
# Edit .env — set these three values:
#   AZURE_OPENAI_ENDPOINT  — your Azure OpenAI resource endpoint
#   AZURE_OPENAI_API_KEY   — from Azure portal (local dev only; Managed Identity in prod)
#   TAVILY_API_KEY         — free at https://app.tavily.com (1,000 searches/month)

# 3. Install Python dependencies
poetry install

# 4. Run unit tests (no Azure required)
poetry run pytest tests/unit/ -v

# 5. Start the full local stack (backend + postgres + redis + langfuse)
docker compose up -d

# API docs:    http://localhost:8000/docs
# LangFuse:   http://localhost:3000
```

### Test the research flow

```bash
# Step 1: Start a research session
curl -X POST http://localhost:8000/v1/research/start \
  -H "Content-Type: application/json" \
  -d '{"query": "Analyse NVIDIAs competitive position in the AI chip market"}'

# Returns: {"session_id": "...", "status": "awaiting_approval", "plan": {...}}

# Step 2: Approve the research plan
curl -X POST http://localhost:8000/v1/research/{session_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Step 3: Stream agent events (Server-Sent Events)
curl -N http://localhost:8000/v1/research/{session_id}/stream

# Step 4: Fetch completed report
curl http://localhost:8000/v1/research/{session_id}/result
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/research/start` | Start session, returns research plan for approval |
| `POST` | `/v1/research/{id}/approve` | Approve/reject plan → agents begin working |
| `GET` | `/v1/research/{id}/stream` | SSE stream of agent events (live progress) |
| `GET` | `/v1/research/{id}/result` | Fetch completed report + citations + cost |
| `GET` | `/health` | Liveness probe (Container Apps) |

---

## Deployment to Azure

```bash
# 1. Install Terraform
# 2. Create terraform.tfvars from sample
copy infra\terraform.tfvars.sample infra\terraform.tfvars
# Edit: set tavily_api_key and postgres_admin_password

# 3. Deploy all Azure resources
make deploy ENV=dev

# Outputs: backend URL, LangFuse URL, ACR login server
```

### CI/CD Setup

The GitHub Actions pipeline uses OIDC — no secrets stored in GitHub. Set three repository **Variables** (not secrets):

```
AZURE_CLIENT_ID       — from: az ad app list --display-name "research-agent-oidc"
AZURE_TENANT_ID       — from: az account show --query tenantId -o tsv
AZURE_SUBSCRIPTION_ID — from: az account show --query id -o tsv
```

---

## Architectural Decisions

Key decisions documented in ADRs (see code comments and inline documentation):

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LangFuse over LangSmith SaaS | Self-hosted LangFuse | LangSmith sends traces (prompts + responses) to LangChain's cloud — data privacy concern in enterprise |
| PostgreSQL over in-memory | `langgraph-checkpoint-postgres` | Sessions survive pod restarts, deployments, and scaling events |
| OTel → Azure Monitor over Datadog | Azure Monitor + LangFuse | Cost; same OTel instrumentation works with Datadog by changing one exporter config |
| RBAC over Access Policies (Key Vault) | `enable_rbac_authorization = true` | RBAC is the modern Azure approach; consistent with all other service-to-service auth |
| Container Apps over AKS | Azure Container Apps | Right-sized for this workload; AKS justified at >10 microservices |
| yfinance over Bloomberg | yfinance (unofficial Yahoo Finance) | Free for portfolio project; in production replace with Bloomberg/Refinitiv |

---

## Related Projects

- [azure-openai-rag-solution](https://github.com/esuneelkumar722/azure-openai-rag-solution) — Production-grade RAG platform with hybrid vector search, safety evaluations, and full IaC. Shows static document Q&A; this project shows dynamic multi-agent research.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Security

To report a vulnerability, open a GitHub issue with the `security` label.
