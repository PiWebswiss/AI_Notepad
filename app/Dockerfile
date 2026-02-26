# lightweight Python base image
FROM python:3.11-slim  

# This image is mainly used as a utility/debug container in this project.
# The primary GUI app runs on the host OS (not inside this container).

# Ensure logs appear immediately (useful for container debugging).
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal runtime deps for Python + Tk support + TLS certificates.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash python3-tk tk ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt  # install Python dependencies

COPY . /app

# Keep container alive for maintenance/debug tasks (GUI runs natively on host).
CMD ["sleep", "infinity"]
