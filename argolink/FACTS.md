# Checked Argolink facts

Checked 2026-10-04 against `/en/models/seedance-2.0`, the catalog, and the local video contract.

- Canonical model ID: `seedance-2.0`; endpoint `/v1/videos/generations`.
- Duration 4–15 seconds; default 5.
- Resolutions 480p, 720p, 1080p, and 4k; default 720p.
- Ratios 21:9, 16:9, 4:3, 1:1, 3:4, and 9:16; frame inputs may use `adaptive`.
- Up to 9 images, 3 videos, 3 audio tracks, 15 assets total; reference videos total 15 seconds.
- Prompt is required for prompt-only requests and may be omitted when assets provide the subject.
- Generated audio is on by default and can be disabled.
- One output per request; `seed` and `watermark` controls are not supported.
- Completed output and reference-video seconds determine billing; failed/rejected jobs are not billed.
