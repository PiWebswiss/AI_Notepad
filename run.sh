#!/usr/bin/env bash
# Exit immediately on error, treat unset variables as errors, propagate pipe failures.
set -euo pipefail

# Linux launcher for AI Notepad.
# It prepares X11 auth for containerised UI access, ensures Ollama/model
# availability, then starts the full compose stack.

# Use the current DISPLAY or fall back to :0 (primary screen).
DISPLAY_VALUE="${DISPLAY:-:0}"
# Create a temporary Xauthority file so the container can connect to the host X server.
XAUTH="$(mktemp /tmp/.docker.xauth.XXXXXX)"
chmod 600 "$XAUTH"
# Always delete the temp file on exit, even on error.
trap 'rm -f "$XAUTH"' EXIT

export DISPLAY="$DISPLAY_VALUE"
export XAUTH

# Extract the X11 MIT-MAGIC-COOKIE for this display and write it to the temp file.
# 'ffff' replaces the display-specific prefix so the cookie works from inside the container.
xauth nlist "$DISPLAY_VALUE" \
  | sed -e 's/^..../ffff/' \
  | xauth -f "$XAUTH" nmerge - >/dev/null 2>&1 || {
    echo "Failed to set Xauthority; is X running and DISPLAY=$DISPLAY_VALUE reachable?"
    exit 1
  }

# Use both the base compose file and the X11 overlay (mounts XAUTH + DISPLAY).
COMPOSE=("docker" "compose" "-f" "docker-compose.yml" "-f" "docker-compose.x11.yml")

# Tear down any stale containers/networks before starting fresh.
"${COMPOSE[@]}" down

# Read OLLAMA_MODEL from the environment or from the .env file.
# The default model is not set here — app/app.py is responsible for the fallback.
MODEL="${OLLAMA_MODEL:-}"
if [ -z "$MODEL" ] && [ -f .env ]; then
  # Parse the last matching line in .env to support overrides at the bottom of the file.
  MODEL="$(sed -n 's/^OLLAMA_MODEL=//p' .env | tail -n 1)"
fi
# Expose the resolved value so containers inherit it via environment.
if [ -n "$MODEL" ]; then
  export OLLAMA_MODEL="$MODEL"
fi

# Pull the model once if it is not already cached in the Ollama container.
# Set NO_AUTO_PULL=1 to skip this check (useful in offline environments).
if [ "${NO_AUTO_PULL:-0}" != "1" ]; then
  # Start Ollama in the background before checking the model list.
  "${COMPOSE[@]}" up -d ollama

  if [ -n "$MODEL" ]; then
    # Retry up to 20 times (1 s apart) while Ollama is booting.
    ready=0
    for i in $(seq 1 20); do
      if list_out="$("${COMPOSE[@]}" exec -T ollama ollama list 2>/dev/null)"; then
        ready=1
        break
      fi
      sleep 1
    done

    if [ "$ready" -eq 1 ]; then
      # awk skips the header line; grep checks for an exact match on the model name.
      if ! printf "%s\n" "$list_out" | awk 'NR>1{print $1}' | grep -Fxq "$MODEL"; then
        echo "Model $MODEL not found; pulling once via ollama_init..."
        # ollama_init is a one-shot init container defined under the 'init' profile.
        "${COMPOSE[@]}" --profile init run --rm ollama_init
      fi
    else
      echo "Ollama not ready; skipping auto model pull."
    fi
  else
    echo "OLLAMA_MODEL not set; skipping auto model pull."
  fi
fi

# Build images if needed, then start all services (Ollama + app container).
"${COMPOSE[@]}" up --build
