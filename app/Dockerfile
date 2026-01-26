FROM python:3.11-slim

# Keep stdout/stderr unbuffered for clearer logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Tk runtime and certs (kept minimal; GUI now runs natively, no container UI stack)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash python3-tk tk ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + seeds
COPY . /app

# Keep container available for CLI tasks (no GUI entrypoint)
CMD ["sleep", "infinity"]
