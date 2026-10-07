# Keeping a character consistent across Seedance 2.0 shots

Seedance 2.0 has no saved-character feature on this API. Consistency comes from sending the same reference images with every shot and writing the prompt so the model knows which image is which. The advice below follows [BytePlus's Seedance 2.0 prompt guide](https://docs.byteplus.com/en/docs/modelark/seedance-2-0-prompt-guide) (checked 2026-10-07); the code uses this SDK.

## 1. Prepare two images, not a character sheet

| Image | What it should show | Why |
|---|---|---|
| Headshot | the face only, neutral expression, plain background, no shoulders or props | a face that fills the frame gets more weight than one inside a busy picture |
| Full body | the same person in the outfit you want, standing | carries clothing, hair and proportions |

Avoid multi-angle character sheets (front / side / back in one image or as several images). BytePlus reports that the model may read the angles as different people, which causes drifting faces and "twins" in the same frame.

```python
from seedance_api import SeedanceAPI

api = SeedanceAPI()
headshot = api.upload_file("refs/mara-headshot.png")    # media_url, readable for 7 days
full_body = api.upload_file("refs/mara-full-body.png")
```

## 2. Bind the name to the images in every prompt

Give the character one label and attach the images each time it appears: `Mara (face from @Image 1, outfit from @Image 2)`. `@Image 1` is the first entry of `images`, so keep the list in the same order for every shot, and put the asset that matters most first.

```python
refs = [headshot, full_body]
api.generate(
    "Mara (face from @Image 1, outfit from @Image 2) pours coffee at a window counter; "
    "she glances up and smiles slightly. Medium close-up, fixed camera, morning light. "
    "Only one Mara in the frame.",
    "shot-1.mp4", images=refs, duration=5, aspect_ratio="9:16",
)
```

The closing sentence is the kind of global constraint BytePlus suggests against duplicated characters.

## 3. Keep the rest of the brief stable

- Repeat the same wardrobe and lighting words in each shot; change only the action and the camera.
- One camera move per shot, and slow, specific actions (BytePlus: fast, large movements are less stable).
- With more than four people, BytePlus suggests generating group images first and using those as references.
- For a recurring voice, send the same `audios` clip each time and describe the voice in words ("low, warm, slightly husky"); audio needs an image or video beside it on the 2.0 family.

## 4. Draft cheaply, then render

The reference limits are the same on all three models, so a shot list can be tested on `seedance-2.0-mini` at 480p ($0.026/s) and re-rendered on `seedance-2.0` at 1080p ($0.28/s) by changing only `model` and `resolution`.

## 5. Chaining shots through frames

To continue exactly where a clip ended, take its last frame and start the next shot from it:

```bash
ffmpeg -sseof -0.1 -i shot-1.mp4 -frames:v 1 -update 1 shot-1-last.png
```

```python
api.generate("Mara walks out of the café into the street", "shot-2.mp4",
             start_image=api.upload_file("shot-1-last.png"), duration=5)
```

The trade-off: frame modes cannot carry reference lists, so this shot relies on the frame alone for the face. Alternate between the two methods depending on whether continuity of position or of identity matters more.

## When a face is refused

Content review can reject a reference that shows a real or well-known person. The job then ends as `failed` with `error.code == "content_policy_violation"` and `error.field` naming the input; it is not billed. BytePlus's own API does not take reference images of real human faces directly and offers preset digital characters and authorised-likeness workflows instead.
