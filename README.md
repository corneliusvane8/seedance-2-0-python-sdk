# Seedance 2.0 Python SDK

A practical Python client, MCP server, shell examples, and implementation notes for the **Argolink Seedance 2.0** video API. The repository is organized around the workflows that an integration needs: text-to-video, first-frame and first/last-frame generation, reference assets, asynchronous polling, media uploads, and safe downloads.

[Argolink Seedance 2.0 model page →](https://argolink.io/gh-seedance-2-0-python-sdk) · [Argolink API docs →](https://argolink.io/gh-unified-api-docs)

> This is an integration guide. The model page is the source of truth for live availability, customer pricing, limits, and model-specific behavior.

## What is included

- `seedance_api.py`: a small synchronous Python client using the public REST contract.
- `mcp_server.py`: optional MCP tools for submit, status, and the three input modes.
- `examples/`: executable `curl` workflows for submit, reference assets, uploads, polling, and download.
- `docs/api-contract.md`: endpoint, request, response, billing, and limit details.
- `docs/troubleshooting.md`: actionable handling for validation, authentication, upload, timeout, and terminal-job errors.
- `argolink/FACTS.md`: the checked Argolink model facts used by this repository.
- `argolink/VIDEO_MAPPING.md`: the mapping from the public methods to the REST fields.

## Requirements

- Python 3.9 or newer for the client.
- `requests` for the Python client.
- An Argolink API key in `ARGOLINK_API_KEY`.
- `curl`, `jq`, and `file` for the shell examples.

Install the Python dependencies in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The client uses `https://api.argolink.io` by default. Set `ARGOLINK_BASE_URL` only when testing against an explicitly approved compatible environment.

## Quickstart: text-to-video

```python
import os
from seedance_api import SeedanceAPI

client = SeedanceAPI(api_key=os.environ["ARGOLINK_API_KEY"])
job = client.text_to_video(
    prompt="A paper kite crosses a quiet coastal town at golden hour, cinematic motion",
    duration=5,
    resolution="720p",
    aspect_ratio="16:9",
)
print(job["request_id"])

result = client.wait_for_completion(job["request_id"], max_wait_seconds=900)
if result["status"] == "done":
    client.download(result["request_id"], "seedance-2-result.mp4")
```

The submit response is asynchronous. Store `request_id`, poll the status endpoint, and download only after the job is `done`. Do not automatically resubmit a timed-out request: a timeout does not prove that the server did not accept the original job.

## Input modes

### Prompt only

`text_to_video()` sends a prompt with the selected duration, resolution, ratio, and soundtrack switch.

### First frame or first and last frame

`image_to_video()` accepts HTTPS image URLs. Frame workflows use `adaptive` ratio so the input frame controls the shape. An ending frame requires a starting frame. The API also accepts fixed ratios for frames; this client chooses adaptive framing.

```python
job = client.image_to_video(
    prompt="The camera slowly pushes forward while the subject turns toward the light",
    start_image="https://example.invalid/start.jpg",
    end_image="https://example.invalid/end.jpg",
    duration=6,
)
```

### Reference assets

`reference_to_video()` accepts up to nine images, three videos, and three audio tracks, with at most fifteen assets in one request. A prompt is required for text-only generation; frame and reference requests may omit it. Audio references must accompany an image or video. Use the mention syntax described on the model page when a prompt needs to identify an asset:

```python
job = client.reference_to_video(
    prompt="Use image 1 for the character and video 1 for the camera movement",
    reference_images=["https://example.invalid/character.jpg"],
    reference_videos=["https://example.invalid/movement.mp4"],
)
```

Reference videos have a combined duration limit, and their seconds are included in billing. Reference images and audio are accepted as inputs without adding reference-video seconds to the bill. Confirm the current model page before relying on a limit in a long-running production workflow.

## Character consistency

Use the same reference image set across scenes and keep the identity, clothing, and lighting brief stable. See [CHARACTER_CONSISTENCY.md](CHARACTER_CONSISTENCY.md) for a complete multi-shot example and continuity checks.

## Shell workflow

```bash
export ARGOLINK_API_KEY='your-key'
./examples/submit-text.sh "A slow dolly shot through a rain-lit market"
./examples/poll-and-download.sh REQUEST_ID ./result.mp4
```

The examples print request IDs and status values, never API keys. Read `examples/README.md` before adapting them for CI.

## MCP server

Install the optional MCP dependency and run the server over stdio:

```bash
python -m pip install 'mcp[cli]>=1.0'
python mcp_server.py
```

The server exposes four narrow tools: text submit, frame submit, reference submit, and status lookup. It reads `ARGOLINK_API_KEY` from the process environment; it does not accept keys in tool arguments or persist them.

## API behavior that matters in production

- Submit with `POST /v1/videos/generations`; the normal response is HTTP 202.
- Poll with `GET /v1/videos/{request_id}` until `done`, `failed`, or `expired`.
- Fetch the generated bytes with `GET /v1/videos/{request_id}/content` after completion.
- Upload large local assets through `POST /v1/media/uploads`, then PUT bytes to the returned signed URL with the exact content type.
- Completed output seconds and reference-video seconds determine billing. Failed and rejected jobs are not billed according to the model page.
- The model accepts one output per request. Unsupported options should be omitted instead of guessed; the API returns a validation error when a field is not supported.

For the complete field mapping, error shapes, and current limits, see [`docs/api-contract.md`](docs/api-contract.md) and [`docs/troubleshooting.md`](docs/troubleshooting.md).

## License and security

This repository is released under the MIT License. See [`SECURITY.md`](SECURITY.md) for the reporting path and key-handling rules. Never commit `.env`, API keys, signed upload URLs, generated media, or production responses.
