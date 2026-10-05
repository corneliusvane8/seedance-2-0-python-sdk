# Character consistency across Seedance 2.0 shots

Keep a stable reference set across shots, then vary the action and camera description. References guide appearance; they do not guarantee identical faces or clothing in every frame.

## Prepare a character reference set

Choose clear images of a fictional character from the front and from a three-quarter view. Keep hair, wardrobe, props, lighting, and age consistent. Use images you have permission to use. Upload them with `SeedanceAPI.upload_file(kind="image")` or host them at HTTPS URLs readable by the service.

Record a small shot manifest:

```json
{
  "character": "an explorer in a mustard raincoat, round glasses, short dark hair",
  "reference_images": ["https://example.invalid/explorer-front.jpg", "https://example.invalid/explorer-side.jpg"],
  "shots": [
    {"id":"arrival","prompt":"Character in image 1 and image 2 steps onto a misty pier. Medium shot, slow dolly forward.","duration":5},
    {"id":"discovery","prompt":"Same character as image 1 and image 2 lifts a brass compass. Close-up, soft overcast light.","duration":5}
  ]
}
```

Replace the example URLs with your own media. The reference array order stays fixed: `image 1` is the first image, `image 2` the second. A reference is guidance, while `start_image` fixes an opening frame. Choose one mode per request.

## Generate and track shots

```python
import json
from pathlib import Path
from seedance_api import SeedanceAPI

api = SeedanceAPI()
manifest = json.loads(Path("shots.json").read_text())
for shot in manifest["shots"]:
    receipt = Path(f"{shot['id']}.job.json")
    if receipt.exists():
        job = json.loads(receipt.read_text())
    else:
        job = api.reference_to_video(
            shot["prompt"], reference_images=manifest["reference_images"],
            duration=shot["duration"], resolution="720p", aspect_ratio="16:9",
        )
        receipt.write_text(json.dumps({"request_id": job["request_id"]}))
    api.wait_for_completion(job["request_id"], max_wait_seconds=900)
    api.download(job["request_id"], f"{shot['id']}.mp4")
```

This sketch avoids repeat submissions when a receipt exists. If submission succeeds but the process exits before saving the receipt, the outcome is uncertain; inspect your job history before submitting again. Keep job receipts private and use a unique output directory for each project.

## Review continuity

Compare opening, middle, and ending frames for face, clothing, handedness, held objects, light direction, and screen direction. Change one factor at a time when a shot drifts. Reuse the same reference images and preserve prompt nouns across shots. A more detailed prompt is useful only when its instructions are consistent.

The integration uses ordinary `reference_images` and frame inputs. It does not provide a persistent character-registration endpoint or a special server-side character token.
