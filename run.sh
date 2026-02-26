#!/usr/bin/env bash
# Run `set` to execute this operational step.
set -euo pipefail

# Truly per-run file; auto-cleanup
# Define shell variable `DISPLAY_VALUE` for later commands in this script.
DISPLAY_VALUE="${DISPLAY:-:0}"
# Define shell variable `XAUTH` for later commands in this script.
XAUTH="$(mktemp /tmp/.docker.xauth.XXXXXX)"
# Run `chmod` to execute this operational step.
chmod 600 "$XAUTH"
# Register cleanup logic to avoid leaving temporary files behind.
trap 'rm -f "$XAUTH"' EXIT

# Export so docker compose can use it (e.g., for env substitution in compose.yml)
# Expose this variable so child processes can reuse it.
export DISPLAY="$DISPLAY_VALUE"
# Expose this variable so child processes can reuse it.
export XAUTH

# Copy only the cookie for this DISPLAY into the per-run file
# Run `xauth` to execute this operational step.
xauth nlist "$DISPLAY_VALUE" \
  | sed -e 's/^..../ffff/' \
  | xauth -f "$XAUTH" nmerge - >/dev/null 2>&1 || {
    # Run `echo` to execute this operational step.
    echo "Failed to set Xauthority; is X running and DISPLAY=$DISPLAY_VALUE reachable?"
    # Run `exit` to execute this operational step.
    exit 1
  # Run `}` to execute this operational step.
  }

# Define shell variable `COMPOSE` for later commands in this script.
COMPOSE=("docker" "compose" "-f" "docker-compose.yml" "-f" "docker-compose.x11.yml")

# Run `"${COMPOSE[@]}"` to execute this operational step.
"${COMPOSE[@]}" down

# Define shell variable `MODEL` for later commands in this script.
MODEL="${OLLAMA_MODEL:-}"
# Check this shell condition before running the branch commands.
if [ -z "$MODEL" ] && [ -f .env ]; then
  # Define shell variable `MODEL` for later commands in this script.
  MODEL="$(sed -n 's/^OLLAMA_MODEL=//p' .env | tail -n 1)"
# Close the current shell conditional block.
fi
# Define shell variable `MODEL` for later commands in this script.
MODEL="${MODEL:-gemma3:1b}"

# Check this shell condition before running the branch commands.
if [ "${NO_AUTO_PULL:-0}" != "1" ]; then
  # Run `"${COMPOSE[@]}"` to execute this operational step.
  "${COMPOSE[@]}" up -d ollama

  # Define shell variable `ready` for later commands in this script.
  ready=0
  # Loop through retries/items to complete this step reliably.
  for i in $(seq 1 20); do
    # Check this shell condition before running the branch commands.
    if list_out="$("${COMPOSE[@]}" exec -T ollama ollama list 2>/dev/null)"; then
      # Define shell variable `ready` for later commands in this script.
      ready=1
      # Run `break` to execute this operational step.
      break
    # Close the current shell conditional block.
    fi
    # Run `sleep` to execute this operational step.
    sleep 1
  # End the repeated loop body.
  done

  # Check this shell condition before running the branch commands.
  if [ "$ready" -eq 1 ]; then
    # Check this shell condition before running the branch commands.
    if ! printf "%s\n" "$list_out" | awk 'NR>1{print $1}' | grep -Fxq "$MODEL"; then
      # Run `echo` to execute this operational step.
      echo "Model $MODEL not found; pulling once via ollama_init..."
      # Run `"${COMPOSE[@]}"` to execute this operational step.
      "${COMPOSE[@]}" --profile init run --rm ollama_init
    # Close the current shell conditional block.
    fi
  # Fallback branch when prior conditions fail.
  else
    # Run `echo` to execute this operational step.
    echo "Ollama not ready; skipping auto model pull."
  # Close the current shell conditional block.
  fi
# Close the current shell conditional block.
fi

# Run `"${COMPOSE[@]}"` to execute this operational step.
"${COMPOSE[@]}" up --build
