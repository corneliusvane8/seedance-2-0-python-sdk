"""First + last frame: the model fills the motion between two images you control.

    python examples/first_last_frame.py start.png end.png
"""
import sys

from seedance_api import SeedanceAPI

api = SeedanceAPI(model="seedance-2.0-fast")  # 480p/720p, $0.091/s at 720p
start, end = (api.upload_file(path) for path in sys.argv[1:3])  # local JPEG/PNG -> media_url

job = api.generate(
    "The flower bud opens into full bloom as morning light moves across the petals, fixed macro shot",
    "bloom.mp4",
    start_image=start,
    end_image=end,
    aspect_ratio="adaptive",  # the first frame decides the shape; a fixed ratio would crop it
    duration=6,
)
print(job["usage"])
