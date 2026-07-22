# ── Stage 1: Build frontend ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY app/frontend/package*.json ./
RUN npm ci --quiet
COPY app/frontend/ ./
RUN npm run build

# ── Stage 2: Python dependencies ─────────────────────────────────────────────
FROM python:3.11-slim AS python-deps
WORKDIR /app
RUN pip install --no-cache-dir poetry==1.8.3
COPY pyproject.toml poetry.lock* ./
RUN poetry config virtualenvs.create false \
  && poetry install --only main --no-interaction --no-ansi

# ── Stage 3: Final runtime image ──────────────────────────────────────────────
FROM python:3.11-slim AS runtime
WORKDIR /app

# Security: run as non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy installed Python packages from deps stage
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Copy application code
COPY app/backend/ ./app/backend/

# Copy built frontend static files (served by FastAPI static files handler)
COPY --from=frontend-builder /frontend/dist ./app/frontend/dist

# Remove write permissions from application files (defence-in-depth)
RUN chown -R appuser:appgroup /app && chmod -R 755 /app

USER appuser

EXPOSE 8000

# Healthcheck used by Docker and Azure Container Apps
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

CMD ["python", "-m", "app.backend.main"]
