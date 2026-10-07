"""Keep one character across shots with a headshot and a full-body photo as references.

See CHARACTER_CONSISTENCY.md for the reasoning behind each choice.
"""
from seedance_api import SeedanceAPI, JobFailedError

api = SeedanceAPI()
headshot = api.upload_file("refs/mara-headshot.png")
full_body = api.upload_file("refs/mara-full-body.png")

shots = [
    "Mara (face from @Image 1, outfit from @Image 2) unlocks a bicycle outside a bakery, medium shot, fixed camera",
    "Mara (face from @Image 1, outfit from @Image 2) rides along a canal at sunset, side tracking shot",
]
for number, prompt in enumerate(shots, 1):
    try:
        job = api.generate(prompt, f"shot-{number}.mp4", images=[headshot, full_body], duration=5, aspect_ratio="9:16")
        print(number, job["usage"]["billed_seconds"], "s billed")
    except JobFailedError as failure:  # failed jobs are not billed
        print(number, "failed:", failure.code, failure.message, "retryable" if failure.retryable else "")
