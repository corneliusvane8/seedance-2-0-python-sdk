#!/usr/bin/env bash
set -euo pipefail

: "${ARGOLINK_API_KEY:?Set ARGOLINK_API_KEY first}"
BASE="${ARGOLINK_BASE_URL:-https://api.argolink.io}"
FILE="${1:?Usage: $0 FILE [image|video]}"
KIND="${2:?Usage: $0 FILE [image|video]}"

case "$(uname -s)" in
  Darwin) SIZE_BYTES=$(stat -f%z "$FILE") ;;
  *) SIZE_BYTES=$(stat -c%s "$FILE") ;;
esac
CONTENT_TYPE=$(file --brief --mime-type "$FILE")
case "$KIND" in
  image) REFERENCE_FIELD="reference_images" ;;
  video) REFERENCE_FIELD="reference_videos" ;;
  audio) echo "Audio alone is not valid; upload with the Python client and pair it with an image or video" >&2; exit 2 ;;
  *) echo "kind must be image, video, or audio" >&2; exit 2 ;;
esac

TICKET=$(curl --fail-with-body --silent --show-error \
  -X POST "$BASE/v1/media/uploads" \
  -H "Authorization: Bearer $ARGOLINK_API_KEY" \
  -H 'Content-Type: application/json' \
  --data "$(jq -n --arg kind "$KIND" --arg type "$CONTENT_TYPE" --argjson size "$SIZE_BYTES" '{model:"seedance-2.0",type:$kind,content_type:$type,size_bytes:$size}')")
UPLOAD_URL=$(jq -er '.upload_url' <<<"$TICKET")
MEDIA_URL=$(jq -er '.media_url' <<<"$TICKET")

# The signed URL is a capability; do not echo it or add the bearer token.
curl --fail-with-body --silent --show-error \
  -X PUT "$UPLOAD_URL" \
  -H "Content-Type: $CONTENT_TYPE" \
  --upload-file "$FILE" >/dev/null

jq -n --arg media "$MEDIA_URL" --arg field "$REFERENCE_FIELD" \
  '{model:"seedance-2.0", prompt:"Use the uploaded reference to guide a short cinematic shot", duration:5, resolution:"720p", aspect_ratio:"16:9"} | .[$field]=[{url:$media}]' \
  | curl --fail-with-body --silent --show-error \
      -X POST "$BASE/v1/videos/generations" \
      -H "Authorization: Bearer $ARGOLINK_API_KEY" \
      -H 'Content-Type: application/json' \
      --data-binary @- \
  | jq '{request_id, status}'
