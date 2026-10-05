# Seedance 2.0 API contract

This guide records the public contract used by the client. The live model page is authoritative when availability, pricing, or a model-specific limit changes.

## Endpoints

| Operation | Method | Path | Notes |
| --- | --- | --- | --- |
| Submit | `POST` | `/v1/videos/generations` | Returns an asynchronous request, normally HTTP 202. |
| Status | `GET` | `/v1/videos/{request_id}` | Poll until `done`, `failed`, or `expired`. |
| Content | `GET` | `/v1/videos/{request_id}/content` | Stream the completed video bytes. |
| Upload ticket | `POST` | `/v1/media/uploads` | Returns a signed PUT URL and a media URL. |

All requests use `Authorization: Bearer $ARGOLINK_API_KEY`. The examples use `https://api.argolink.io` as the base URL.

## Submit fields

A minimal request has `model` and `prompt`:

```json
{
  "model": "seedance-2.0",
  "prompt": "A paper kite crosses a quiet coastal town at golden hour"
}
```

The client makes the defaults explicit:

| Field | Values or range | Meaning |
| --- | --- | --- |
| `model` | `seedance-2.0` | Canonical model ID. |
| `prompt` | required without assets; optional with frames or references | Describes the video and can mention assets with `image 1` or `video 1`. |
| `duration` | integer 4–15, default 5 | Output seconds. |
| `resolution` | `480p`, `720p`, `1080p`, `4k`, default `720p` | Output tier. |
| `aspect_ratio` | `adaptive`, `21:9`, `16:9`, `4:3`, `1:1`, `3:4`, `9:16` | Output shape. Frame workflows use `adaptive`. |
| `generate_audio` | boolean, default `true` | Keep or disable the generated soundtrack. |
| `start_image` | HTTPS image URL | First-frame mode. |
| `end_image` | HTTPS image URL | Optional last frame; requires `start_image`. |
| `reference_images` | up to 9 URL objects | Reference image inputs. |
| `reference_videos` | up to 3 URL objects | Reference videos; combined reference-video duration is limited. |
| `reference_audios` | up to 3 URL objects | Reference audio inputs. |

Use either frame fields or reference lists in one request. Do not invent a second output count: the model produces one output per request.

## Reference object shape

```json
{
  "reference_images": [{"url": "https://example.invalid/character.jpg"}],
  "reference_videos": [{"url": "https://example.invalid/movement.mp4"}],
  "reference_audios": [{"url": "https://example.invalid/voice.wav"}]
}
```

Every URL must be HTTPS. A request can contain at most 15 reference assets in total. Reference videos have a combined duration limit on the model page; their seconds are included in billed seconds. Images and audio do not add reference-video seconds.

## Response and billing fields

A submit or status response contains a `request_id` and a `status`. A typical terminal response includes `progress`, `video`, and `usage` fields:

```json
{
  "request_id": "req_example",
  "status": "done",
  "progress": 100,
  "video": {"url": "https://api.argolink.io/v1/videos/req_example/content"},
  "usage": {
    "output_seconds": 5,
    "reference_video_seconds": 0,
    "billed_seconds": 5
  }
}
```

Treat the response as extensible: read fields by name and preserve unknown fields. Completed output seconds and reference-video seconds determine billing. The model page states that failed or rejected jobs are not billed. Customer pricing is live on the model page rather than hardcoded in this repository.

## Upload flow

1. POST a ticket with `model`, `type`, `content_type`, and `size_bytes`.
2. PUT the exact file bytes to `upload_url` with the exact `Content-Type`.
3. Use the returned `media_url` in a reference or frame request.

Upload URLs are temporary signed capabilities. Keep them out of logs and never commit them. The client writes no upload response to disk.

## Unsupported guesses

The public model page does not advertise `seed` or `watermark` controls for this model. Omit them. If the service rejects an unsupported field, preserve the error payload and correct the request rather than retrying with a guessed alias.
