# ══════════════════════════════════════════════════════════════════════
#  Research Intelligence Agent — Makefile
#  Common developer commands. Run: make help
# ══════════════════════════════════════════════════════════════════════

.PHONY: help install dev stop build lint test clean deploy destroy

PYTHON     := python
POETRY     := poetry
DOCKER     := docker
COMPOSE    := docker compose
TERRAFORM  := terraform
ENV        ?= dev
IMAGE_TAG  ?= local

## help          Show this help
help:
	@grep -E '^## ' Makefile | sed 's/## //'

## install       Install Python dependencies
install:
	$(POETRY) install

## dev            Start local dev stack (backend + postgres + redis + langfuse)
dev:
	$(COMPOSE) up -d
	@echo "Backend: http://localhost:8000"
	@echo "LangFuse: http://localhost:3000"
	@echo "Docs:    http://localhost:8000/docs"

## stop           Stop local dev stack
stop:
	$(COMPOSE) down

## logs           Tail backend logs
logs:
	$(COMPOSE) logs -f backend

## build          Build Docker image locally
build:
	$(DOCKER) build -t research-agent:$(IMAGE_TAG) -f app/backend/Dockerfile .

## lint           Run ruff linter + mypy type check
lint:
	$(POETRY) run ruff check app/ tests/
	$(POETRY) run mypy app/backend/

## test           Run all unit tests with coverage
test:
	$(POETRY) run pytest tests/ -v --cov=app --cov-report=term-missing

## test-unit      Run unit tests only (no Azure services needed)
test-unit:
	$(POETRY) run pytest tests/unit/ -v

## plan           Terraform plan (dry run)
plan:
	cd infra && $(TERRAFORM) init && $(TERRAFORM) plan -var="environment=$(ENV)"

## deploy         Deploy to Azure (ENV=dev by default)
deploy:
	cd infra && $(TERRAFORM) init && $(TERRAFORM) apply -auto-approve \
		-var="environment=$(ENV)" -var="image_tag=$(IMAGE_TAG)"

## destroy        Tear down all Azure resources (use to save cost)
destroy:
	cd infra && $(TERRAFORM) destroy -auto-approve -var="environment=$(ENV)"

## clean          Remove build artifacts and caches
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov coverage.xml

## env-sample     Copy .env.sample to .env (first-time setup)
env-sample:
	cp .env.sample .env
	@echo ".env created — fill in your values before running 'make dev'"
