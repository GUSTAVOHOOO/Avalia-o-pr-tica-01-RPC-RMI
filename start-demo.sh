#!/usr/bin/env bash
set -euo pipefail

COMPOSE_CMD="docker compose"
if ! $COMPOSE_CMD version &>/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
fi

echo "[demo] Building and starting services..."
$COMPOSE_CMD up -d --build

echo "[demo] Waiting for bridge to be healthy..."
timeout=120
elapsed=0
while true; do
  health=$($COMPOSE_CMD ps bridge 2>/dev/null | tail -1 | grep -o '(healthy)\|(unhealthy)' || true)
  if [ "$health" = "(healthy)" ]; then
    echo "[demo] Bridge is healthy."
    break
  elif [ "$health" = "(unhealthy)" ]; then
    echo "[demo] ERROR: Bridge is unhealthy. Logs:"
    $COMPOSE_CMD logs --tail=40 bridge
    exit 1
  fi
  if [ "$elapsed" -ge "$timeout" ]; then
    echo "[demo] ERROR: Timed out after ${timeout}s. Logs:"
    $COMPOSE_CMD logs --tail=40
    exit 1
  fi
  sleep 3
  elapsed=$((elapsed + 3))
  echo "[demo]   ...${elapsed}s"
done

echo "[demo] Starting ngrok tunnel on port 5000..."
ngrok http 5000 --log stderr &
NGROK_PID=$!
sleep 4

PUBLIC_URL=$(curl -sf http://localhost:4040/api/tunnels 2>/dev/null \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for t in data.get('tunnels', []):
    if t.get('proto') == 'https':
        print(t['public_url'])
        break
" 2>/dev/null || true)

echo ""
if [ -n "$PUBLIC_URL" ]; then
  echo "=================================================="
  echo "  Public URL: $PUBLIC_URL"
  echo "=================================================="
else
  echo "[demo] ngrok started. Check http://localhost:4040 for the public URL."
fi
echo ""
echo "[demo] Press Ctrl+C to stop ngrok (Docker services keep running)."
echo "[demo] Run '$COMPOSE_CMD down' to tear down all services."
echo ""

wait "$NGROK_PID"
