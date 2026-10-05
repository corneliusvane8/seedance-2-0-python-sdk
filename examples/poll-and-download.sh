#!/usr/bin/env bash
set -euo pipefail

: "${ARGOLINK_API_KEY:?Set ARGOLINK_API_KEY first}"
BASE="${ARGOLINK_BASE_URL:-https://api.argolink.io}"
REQUEST_ID="${1:?Usage: $0 REQUEST_ID OUTPUT_FILE}"
OUTPUT="${2:?Usage: $0 REQUEST_ID OUTPUT_FILE}"
MAX_POLLS="${MAX_POLLS:-180}"
SLEEP_SECONDS="${SLEEP_SECONDS:-5}"

for ((poll=1; poll<=MAX_POLLS; poll++)); do
  RESPONSE=$(curl --fail-with-body --silent --show-error \
    "$BASE/v1/videos/$REQUEST_ID" \
    -H "Authorization: Bearer $ARGOLINK_API_KEY")
  STATUS=$(jq -r '.status // "unknown"' <<<"$RESPONSE")
  echo "poll $poll/$MAX_POLLS: $STATUS" >&2
  case "$STATUS" in
    done)
      mkdir -p "$(dirname "$OUTPUT")"
      PART=$(mktemp "${OUTPUT}.XXXXXX.part")
      trap 'if [ -n "${PART:-}" ]; then rm -f -- "$PART"; fi' EXIT
      curl --fail-with-body --silent --show-error \
        "$BASE/v1/videos/$REQUEST_ID/content" --location \
        -H "Authorization: Bearer $ARGOLINK_API_KEY" \
        -o "$PART"
      mv -- "$PART" "$OUTPUT"
      PART=""
      echo "$OUTPUT"
      exit 0
      ;;
    failed|expired)
      jq '{request_id, status, error}' <<<"$RESPONSE" >&2
      exit 1
      ;;
    pending|running) sleep "$SLEEP_SECONDS" ;;
    *) jq . <<<"$RESPONSE" >&2; exit 1 ;;
  esac
done

echo "polling deadline reached; save $REQUEST_ID and poll again later" >&2
exit 2
