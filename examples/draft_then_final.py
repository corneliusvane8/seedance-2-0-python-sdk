"""Iterate on a prompt with Mini at 480p, then render the keeper on Seedance 2.0 at 1080p.

Three 5 s drafts on seedance-2.0-mini cost 3 x 5 x $0.026 = $0.39;
the final 5 s at 1080p costs 5 x $0.28 = $1.40 (2026-10-07 rates).
"""
from seedance_api import SeedanceAPI

api = SeedanceAPI()
drafts = [
    "A fox steps out of the fog onto a mossy log, close-up, slow push-in",
    "Shot 1: wide shot, fog over a pine forest at dawn. Shot 2: a fox steps onto a mossy log and looks back, slow push-in",
    "Shot 1: wide shot, fog over a pine forest at dawn. Shot 2: a fox steps onto a mossy log, ears twitching, slow push-in. <birdsong>",
]
for number, prompt in enumerate(drafts, 1):
    api.generate(prompt, f"draft-{number}.mp4", model="seedance-2.0-mini", resolution="480p", duration=5)
    print("saved", f"draft-{number}.mp4")

chosen = drafts[int(input("Which draft becomes the final (1-3)? ")) - 1]
job = api.generate(chosen, "final-1080p.mp4", model="seedance-2.0", resolution="1080p", duration=5)
print("final billed seconds:", job["usage"]["billed_seconds"])
