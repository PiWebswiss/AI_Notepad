######
# This file was developed with the assistance of Claude by Anthropic.
######

# ── Build stage: install Python deps ──────────────────────────────────────────
FROM python:3.13-slim AS builder

WORKDIR /app

# Copy only requirements first (Docker caches this layer if unchanged)
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Final image ───────────────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy app source
COPY server.py .
COPY public/ ./public/

# Icons are pre-vendored under public/icons and copied with public/.

# The port the app listens on (overridable via docker-compose or env)
EXPOSE 3000

# Start with uvicorn (no --reload in production)
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3000"]
