# Select the base image that all following build steps extend.
FROM python:3.11-slim  # small Python base image

# Keep stdout/stderr unbuffered for clearer logs
# Define runtime environment defaults inside the image.
ENV PYTHONUNBUFFERED=1

# Set the default working directory for subsequent image steps.
WORKDIR /app

# Tk runtime and certs (kept minimal; GUI now runs natively, no container UI stack)
# Execute build-time commands to install or prepare dependencies.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      bash python3-tk tk ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Copy project files into the image filesystem.
COPY requirements.txt .
# Execute build-time commands to install or prepare dependencies.
RUN pip install --no-cache-dir -r requirements.txt  # install Python deps

# App code + seeds
# Copy project files into the image filesystem.
COPY . /app

# Keep container available for CLI tasks (no GUI entrypoint)
# Provide the default command when a container starts from this image.
CMD ["sleep", "infinity"]
