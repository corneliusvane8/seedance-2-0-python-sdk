"""Text to video in one call: submit, wait, save.

    pip install -e .            # from the repo root
    export SEEDANCE_API_KEY=...
    python examples/quickstart.py
"""
from seedance_api import SeedanceAPI

api = SeedanceAPI()
print("estimated:", api.estimate_cost("seedance-2.0", "1080p", 8), "USD")  # 8 x $0.28 = $2.24

job = api.generate(
    "A paper kite climbs over a windy beach at sunset, slow upward tilt, (light acoustic guitar), keep it subtitle-free",
    "kite.mp4",
    duration=8,
    resolution="1080p",
    aspect_ratio="16:9",
    on_progress=lambda j: print(f"{j.get('progress', 0)}%"),
)
print(job["usage"])  # output_seconds, reference_video_seconds, billed_seconds
