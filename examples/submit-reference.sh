#!/usr/bin/env bash
set -euo pipefail

: "${ARGOLINK_API_KEY:?Set ARGOLINK_API_KEY first}"
BASE="${ARGOLINK_BASE_URL:-https://api.argolink.io}"
IMAGE_URL="${1:?Usage: $0 IMAGE_URL [VIDEO_URL] [AUDIO_URL]}"
VIDEO_URL="${2:-}"
AUDIO_URL="${3:-}"

jq -n \
  --arg image "$IMAGE_URL" \
  --arg video "$VIDEO_URL" \
  --arg audio "$AUDIO_URL" \
  '{model:"seedance-2.0", prompt:"Use image 1 for the character and follow the reference motion when provided", duration:5, resolution:"720p", aspect_ratio:"16:9", generate_audio:true, reference_images:[{url:$image}]}
   | if $video != "" then .reference_videos=[{url:$video}] else . end
   | if $audio != "" then .reference_audios=[{url:$audio}] else . end' \
  | curl --fail-with-body --silent --show-error \
      -X POST "$BASE/v1/videos/generations" \
      -H "Authorization: Bearer $ARGOLINK_API_KEY" \
      -H 'Content-Type: application/json' \
      --data-binary @- \
  | jq '{request_id, status}'
