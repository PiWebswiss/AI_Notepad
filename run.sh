#!/usr/bin/env bash
set -euo pipefail

# Truly per-run file; auto-cleanup
DISPLAY_VALUE="${DISPLAY:-:0}"
XAUTH="$(mktemp /tmp/.docker.xauth.XXXXXX)"
chmod 600 "$XAUTH"
trap 'rm -f "$XAUTH"' EXIT

# Export so docker compose can use it (e.g., for env substitution in compose.yml)
export DISPLAY="$DISPLAY_VALUE"
export XAUTH

# Copy only the cookie for this DISPLAY into the per-run file
xauth nlist "$DISPLAY_VALUE" \
  | sed -e 's/^..../ffff/' \
  | xauth -f "$XAUTH" nmerge - >/dev/null 2>&1 || {
    echo "Failed to set Xauthority; is X running and DISPLAY=$DISPLAY_VALUE reachable?"
    exit 1
  }

COMPOSE=("docker" "compose" "-f" "docker-compose.yml" "-f" "docker-compose.x11.yml")

"${COMPOSE[@]}" down

MODEL="${OLLAMA_MODEL:-}"
if [ -z "$MODEL" ] && [ -f .env ]; then
  MODEL="$(sed -n 's/^OLLAMA_MODEL=//p' .env | tail -n 1)"
fi
MODEL="${MODEL:-gemma3:1b}"

if [ "${NO_AUTO_PULL:-0}" != "1" ]; then
  "${COMPOSE[@]}" up -d ollama

  ready=0
  for i in $(seq 1 20); do
    if list_out="$("${COMPOSE[@]}" exec -T ollama ollama list 2>/dev/null)"; then
      ready=1
      break
    fi
    sleep 1
  done

  if [ "$ready" -eq 1 ]; then
    if ! printf "%s\n" "$list_out" | awk 'NR>1{print $1}' | grep -Fxq "$MODEL"; then
      echo "Model $MODEL not found; pulling once via ollama_init..."
      "${COMPOSE[@]}" --profile init run --rm ollama_init
    fi
  else
    echo "Ollama not ready; skipping auto model pull."
  fi
fi

"${COMPOSE[@]}" up --build
