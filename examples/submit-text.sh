#!/usr/bin/env bash
set -euo pipefail

: "${ARGOLINK_API_KEY:?Set ARGOLINK_API_KEY first}"
BASE="${ARGOLINK_BASE_URL:-https://api.argolink.io}"
PROMPT="${1:?Usage: $0 'prompt' [duration] [resolution] [aspect_ratio]}"
DURATION="${2:-5}"
RESOLUTION="${3:-720p}"
ASPECT_RATIO="${4:-16:9}"

curl --fail-with-body --silent --show-error \
  -X POST "$BASE/v1/videos/generations" \
  -H "Authorization: Bearer $ARGOLINK_API_KEY" \
  -H 'Content-Type: application/json' \
  --data-binary @- <<JSON | jq '{request_id, status}'
{
  "model": "seedance-2.0",
  "prompt": $(jq -Rn --arg value "$PROMPT" '$value'),
  "duration": $DURATION,
  "resolution": $(jq -Rn --arg value "$RESOLUTION" '$value'),
  "aspect_ratio": $(jq -Rn --arg value "$ASPECT_RATIO" '$value'),
  "generate_audio": true
}
JSON
