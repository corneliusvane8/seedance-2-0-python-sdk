# Client mapping

| Method | REST mapping |
|---|---|
| `text_to_video` | Prompt plus duration, resolution, ratio, and audio switch. |
| `image_to_video` | `start_image`, optional `end_image`, frame ratio `adaptive`; prompt may be omitted. |
| `reference_to_video` | Up to 9 images, 3 videos, 3 audio tracks, 15 total; audio needs an image or video. |
| `upload_file` | Upload ticket then signed PUT; returns `media_url`. |
| `get_result` | Reads one request by its only accepted `request_id`. |
| `wait_for_completion` | Bounded polling, no submit retry. |
| `download` | Streams terminal content through a temporary file. |
