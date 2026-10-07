# Seedance 2.0 Python SDK — from $0.053/s (480p)

**ByteDance Seedance 2.0 is live on [ArgoLink](https://argolink.io/gh-seedance-2-0-python-sdk)**: $0.053/s at 480p, $0.11/s at 720p, $0.28/s at 1080p and $0.58/s at 4K, 25% below the official price, with the Mini variant from $0.026/s. This is a community Python SDK for it: one client for `seedance-2.0`, `seedance-2.0-fast` and `seedance-2.0-mini` that checks each request against the documented limits before sending it, uploads local files, waits with progress, downloads safely, raises typed errors and runs as an MCP server for Claude, Cursor and other agents.

[Model page →](https://argolink.io/en/models/seedance-2.0) · [Install](#install) · [Quick start](#quick-start) · [Methods](#method-reference) · [MCP server](#mcp-server) · [FAQ](#faq)

<sub>Last checked: 2026-10-07. Community project, not affiliated with ByteDance or BytePlus. Default endpoint `https://argolink.io/v1`; set `SEEDANCE_BASE_URL` for any host that speaks the same `/v1/videos` protocol.</sub>

## Features

- **All three 2.0 models** behind one client; pick per call with `model=`.
- **Every input mode**: text, first frame, first + last frame, and reference images, video and audio named as `@Image 1`, `@Video 1`, `@Audio 1`.
- **Checks before you pay**: duration, resolution per model, aspect ratio per mode, reference counts, audio-only references, HTTPS media and prompt size are validated locally, so a bad request fails before any HTTP round trip.
- **Uploads** of local JPEG/PNG, MP4/MOV and MP3/WAV files through `POST /v1/media/uploads`.
- **Safe waiting**: polling retries 429, 503 and dropped connections; submissions are never retried, so a timeout cannot create a second paid job.
- **Typed errors** for every documented HTTP status and job failure code, with `retryable` and `field` exposed.
- **Cost estimates** from the per-second rates, including billed reference-video seconds.
- **MCP server** with six tools, for MCP SDK 1.x and 2.x.

## Install

```bash
pip install "git+https://github.com/corneliusvane8/seedance-2-0-python-sdk"

# with the MCP server (Python 3.10+, which the mcp package requires)
pip install "seedance-2-0-python-sdk[mcp] @ git+https://github.com/corneliusvane8/seedance-2-0-python-sdk"

# or from a clone
git clone https://github.com/corneliusvane8/seedance-2-0-python-sdk && cd seedance-2-0-python-sdk
pip install -e ".[mcp,test]"
```

The library itself needs Python 3.9+ and `requests`.

## Configure

```bash
export SEEDANCE_API_KEY=your-key                     # from the ArgoLink console
export SEEDANCE_BASE_URL=https://argolink.io/v1      # optional; this is the default
```

Or pass them in code: `SeedanceAPI(api_key="...", base_url="...")`.

## Quick start

```python
from seedance_api import SeedanceAPI

api = SeedanceAPI()                                   # model defaults to seedance-2.0
job = api.generate(
    "A paper kite climbs over a windy beach at sunset, slow upward tilt",
    "kite.mp4",
    duration=8,
    resolution="1080p",
    on_progress=lambda j: print(f"{j.get('progress', 0)}%"),
)
print(job["usage"])   # {'output_seconds': 8, 'reference_video_seconds': 0, 'billed_seconds': 8} -> $2.24
```

`generate()` picks the mode from its arguments, waits, and saves the MP4. The lower-level calls below return as soon as the job is accepted.

## Pick a model

| Model | Resolutions | $/s 480p | $/s 720p | $/s 1080p | $/s 4K | Good for |
|---|---|---:|---:|---:|---:|---|
| `seedance-2.0` | 480p · 720p · 1080p · 4k | 0.053 | 0.11 | 0.28 | 0.58 | finals, high resolution |
| `seedance-2.0-fast` | 480p · 720p | 0.042 | 0.091 | — | — | quick turnaround |
| `seedance-2.0-mini` | 480p · 720p | 0.026 | 0.057 | — | — | drafts, volume |

<sub>ArgoLink rates per output second, [checked 2026-10-07](https://argolink.io/en/models/seedance-2.0). BytePlus's list price for 2.0 works out to $0.0703 / $0.1512 / $0.3742 / $0.7776 per second for a 16:9 clip ([ModelArk pricing](https://docs.byteplus.com/en/docs/modelark/model-pricing)). The SDK keeps the rates in `seedance_api.MODELS` for estimates only; the server bills.</sub>

```python
from seedance_api import estimate_cost

estimate_cost("seedance-2.0-mini", "480p", 5)            # 0.13
estimate_cost("seedance-2.0", "4k", 6)                   # 3.48
estimate_cost("seedance-2.0", "720p", 6, [3.5])          # 0.99: 6 s + 3 s of reference video
```

## Modes

### Text to video

```python
submitted = api.text_to_video(
    "Shot 1: a night market in the rain, slow lateral tracking. Shot 2: close-up of a lantern being lifted.",
    model="seedance-2.0-fast", duration=10, resolution="720p", aspect_ratio="9:16",
)
request_id = submitted["request_id"]
```

### First frame, or first + last frame

```python
api.image_to_video(
    "The camera pushes in as steam rises from the cup",
    start_image="https://example.com/cup.png",
    end_image="https://example.com/cup-empty.png",   # optional
    aspect_ratio="adaptive",                          # default: follow the first frame; "16:9" etc. crops it
)
```

### Reference images, video and audio

```python
api.reference_to_video(
    "The dancer in @Image 1 repeats the choreography of @Video 1 to the beat of @Audio 1, wide shot, stage lights",
    images=["https://example.com/dancer.png"],
    videos=["https://example.com/routine-4s.mp4"],   # its 4 s are added to the billed seconds
    audios=["https://example.com/beat.mp3"],          # free, but needs an image or video beside it
    duration=8,
)
```

Up to 9 images, 3 videos and 3 audio clips, 15 together; reference videos and audio are 2–15 s each and 15 s combined. Frames and references cannot share a request; the client refuses that before sending.

### Local files

```python
url = api.upload_file("first-frame.jpg")              # returns a media_url valid for 7 days
api.image_to_video("Leaves drift across the frame", start_image=url)
```

The ticket is free and creates no job. The bytes go straight to storage with the declared `Content-Type` and without your API key.

### Waiting and downloading separately

```python
job = api.wait_for_completion(request_id, timeout=1800, on_progress=print)
api.download(request_id, "out/clip.mp4")             # written to clip.mp4.part, renamed when complete
```

## Errors

Every exception derives from `SeedanceError`.

| Exception | Raised when | What to do |
|---|---|---|
| `ValidationError` | a documented limit is broken; nothing was sent | fix the argument named in the message |
| `BadRequestError` (400) | `field_invalid`, `json_invalid` or `request_unsupported` | read `.code`, `.param`, `.message` |
| `AuthenticationError` (401) | key missing or wrong | check `SEEDANCE_API_KEY` |
| `PermissionDeniedError` (402/403) | low balance, or the key may not use video models | top up or change the key's group |
| `NotFoundError` (404) | unknown `request_id`, or another user's key | use the key that created the job |
| `VideoNotReadyError` (409) | content requested before `done` | wait, then download |
| `FailedJobContentError` (424) | content requested for a failed job | read the job's `error` |
| `RateLimitError` (429) | concurrency or rate limit | retry after running jobs finish |
| `ServiceUnavailableError` (503) | no capacity right now | retry after `.retry_after` seconds |
| `JobFailedError` | the job ended `failed`; not billed | resubmit as is if `.retryable`, else change `.field` |
| `JobExpiredError` | the job ended `expired`; not billed | submit again |
| `WaitTimeoutError` | your local timeout passed while `pending` | the job may still finish: poll `request_id` later |

```python
from seedance_api import JobFailedError

try:
    api.generate("...", "clip.mp4", images=["https://example.com/face.png"])
except JobFailedError as failure:
    print(failure.code, failure.field, failure.retryable)   # e.g. content_policy_violation reference_images False
```

Failure codes you can see on a job: `invalid_input`, `content_policy_violation`, `copyright_violation`, `generation_failed`, `generation_timeout`, `capacity_unavailable`, `internal_error`, `cancelled`.

## MCP server

The `mcp` extra installs a stdio server, `seedance2-mcp` (also `python -m seedance_api.mcp_server`). It reads `SEEDANCE_API_KEY` from its environment; the key is never a tool argument.

| Tool | Does |
|---|---|
| `create_video` | submits a text, frame or reference job and returns `request_id` plus an estimate |
| `get_video_status` | returns the job: `pending` with progress, `done` with `video.url` and `usage`, or the error |
| `wait_for_video` | blocks until the job finishes or a timeout passes |
| `download_video` | saves a finished MP4 to a local path |
| `upload_media` | uploads a local file and returns its `media_url` |
| `estimate_cost` | prices a job from model, resolution, duration and reference-video seconds |

Claude Code:

```bash
claude mcp add --env SEEDANCE_API_KEY=your-key --transport stdio seedance2 -- seedance2-mcp
```

Claude Desktop (`claude_desktop_config.json`) or Cursor (`~/.cursor/mcp.json`, or `.cursor/mcp.json` in a project):

```json
{
  "mcpServers": {
    "seedance2": {
      "command": "seedance2-mcp",
      "env": { "SEEDANCE_API_KEY": "your-key" }
    }
  }
}
```

Use the absolute path of `seedance2-mcp` (from `which seedance2-mcp`) if the client does not inherit your virtualenv's `PATH`. To try the tools by hand: `npx @modelcontextprotocol/inspector seedance2-mcp`.

## Method reference

| Method | Key arguments | Returns |
|---|---|---|
| `SeedanceAPI(api_key=None, *, base_url=None, model="seedance-2.0", timeout=60, poll_interval=10, validate=True)` | env vars when omitted | client |
| `text_to_video(prompt, *, model, duration=5, resolution="720p", aspect_ratio="16:9", generate_audio=True)` | | `{"request_id"}` |
| `image_to_video(prompt, start_image, *, end_image=None, aspect_ratio="adaptive", ...)` | URL string or `{"url": ...}` | `{"request_id"}` |
| `reference_to_video(prompt, *, images=(), videos=(), audios=(), aspect_ratio="16:9", ...)` | up to 9 / 3 / 3 | `{"request_id"}` |
| `submit(payload)` | raw body; validated unless `validate=False` | `{"request_id"}` |
| `get_result(request_id)` | | job dict |
| `wait_for_completion(request_id, *, timeout=1800, on_progress=None, max_transient_errors=5)` | | finished job |
| `download(request_id, destination)` | | `Path` |
| `upload_file(path, *, content_type=None, model=None)` | JPEG/PNG ≤ 20 MiB, MP4/MOV, MP3/WAV ≤ 15 MB | `media_url` |
| `generate(prompt, destination=None, *, on_progress=None, **options)` | any of the above options | finished job |
| `estimate_cost(model, resolution, duration, reference_video_seconds=())` | | USD |
| `validate_payload(body)` | module function | raises `ValidationError` |

## Limits the client enforces

| Rule | Value |
|---|---|
| Duration | 4–15 whole seconds (default 5) |
| Resolution | 480p, 720p on all; 1080p, 4k on `seedance-2.0` |
| Aspect ratio | 21:9, 16:9, 4:3, 1:1, 3:4, 9:16; `adaptive` only with frames |
| Prompt | required in every mode, ≤ 40,000 UTF-8 bytes |
| References | ≤ 9 images, ≤ 3 videos, ≤ 3 audio, ≤ 15 total; audio not alone |
| Media | public `https://` URLs only |
| Not supported | `seed`, `watermark: true`, `n` other than 1 |

The server checks more (media length and pixel size, for example) and stays the authority. Pass `validate=False` to send a body unchanged.

## Character consistency

[CHARACTER_CONSISTENCY.md](./CHARACTER_CONSISTENCY.md) walks through a two-image reference set, prompt binding, draft-then-final rendering and chaining shots through their last frame. [examples/](./examples) has runnable scripts for each mode.

## FAQ

**Is this the official Seedance SDK?**
No. It is an MIT-licensed client for the `/v1/videos` protocol. ByteDance's own API (BytePlus ModelArk) uses a different request shape with a `content` array.

**Does it work with Seedance 2.5?**
Not as written: the model table and the validation rules are the 2.0 family's. Seedance 2.5 has longer clips, bigger reference limits and video editing.

**Why does `submit` never retry?**
A POST that timed out on your side may have created a job on the server; retrying could start a second, billed render. Polling is idempotent and does retry.

**How long should `wait_for_completion` wait?**
Generation usually takes a few minutes. The default 30-minute timeout raises `WaitTimeoutError` with the last state; the job keeps running, so poll it again rather than resubmitting.

**Can I get several videos from one request?**
No, one video per request (`n` must be 1). Submit several jobs and wait on each.

## Run the tests

```bash
pip install -e ".[test]"        # add ,mcp to include the MCP tests
pytest
```

All tests use fake HTTP sessions: no key, no network.

## License

MIT
