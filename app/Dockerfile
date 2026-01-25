FROM python:3.11-slim

# Keep stdout/stderr unbuffered for clearer logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Tk runtime and certs (include Xvfb for headless)
RUN apt-get update && \
    apt-get install -y --no-install-recommends bash python3-tk tk ca-certificates xvfb xauth && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + seeds
COPY . /app

# Start script handles DB seed + app launch
CMD ["bash", "/app/startapp.sh"]
