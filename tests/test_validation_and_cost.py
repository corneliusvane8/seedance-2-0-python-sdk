"""Client-side limits and cost estimates. Nothing here touches the network."""
import doctest

import pytest

import seedance_api
from seedance_api import models, validate_payload

URL = "https://x.test/a.png"


def body(**fields):
    return {"model": "seedance-2.0", "prompt": "a lighthouse at dusk", **fields}


@pytest.mark.parametrize("fields", [
    {},
    {"duration": 15, "resolution": "4k", "aspect_ratio": "21:9"},
    {"start_image": {"url": URL}, "aspect_ratio": "adaptive"},
    {"start_image": {"url": URL}, "end_image": {"url": URL}, "aspect_ratio": "9:16"},
    {"reference_images": [{"url": URL}] * 9, "reference_videos": [{"url": URL}] * 3, "reference_audios": [{"url": URL}] * 3},
])
def test_valid_bodies_pass(fields):
    validate_payload(body(**fields))


@pytest.mark.parametrize("fields,message", [
    ({"prompt": "  "}, "prompt is required"),
    ({"duration": 3}, "duration"),
    ({"duration": 16}, "duration"),
    ({"duration": 5.5}, "duration"),
    ({"model": "seedance-2.0-mini", "resolution": "1080p"}, "renders 480p, 720p"),
    ({"model": "seedance-2.0-fast", "resolution": "4k"}, "renders 480p, 720p"),
    ({"aspect_ratio": "adaptive"}, "aspect_ratio"),
    ({"start_image": {"url": URL}, "aspect_ratio": "2:1"}, "aspect_ratio"),
    ({"end_image": {"url": URL}}, "needs a start_image"),
    ({"start_image": {"url": URL}, "reference_images": [{"url": URL}]}, "cannot be combined"),
    ({"reference_images": [{"url": URL}] * 10}, "at most 9"),
    ({"reference_videos": [{"url": URL}] * 4}, "at most 3"),
    ({"reference_audios": [{"url": URL}]}, "audio cannot be the only reference"),
    ({"reference_images": [{"url": "http://x.test/a.png"}]}, "https://"),
    ({"seed": 7}, "seed"),
    ({"watermark": True}, "watermark"),
    ({"n": 2}, "n must be 1"),
    ({"model": "seedance-2.5"}, "unknown model"),
])
def test_invalid_bodies_are_rejected_before_sending(fields, message):
    with pytest.raises(seedance_api.ValidationError, match=message):
        validate_payload(body(**fields))


def test_prompt_size_is_counted_in_bytes():
    validate_payload(body(prompt="é" * 20_000))  # 40,000 bytes
    with pytest.raises(seedance_api.ValidationError):
        validate_payload(body(prompt="é" * 20_001))


@pytest.mark.parametrize("args,usd", [
    (("seedance-2.0", "480p", 5), 0.265),
    (("seedance-2.0", "4k", 6), 3.48),
    (("seedance-2.0-fast", "720p", 10), 0.91),
    (("seedance-2.0-mini", "480p", 4), 0.104),
    (("seedance-2.0", "720p", 5, [2.4]), 0.77),       # 5 + 2 billed seconds
    (("seedance-2.0", "720p", 5, [1.6, 1.6]), 0.88),  # 3.2 s of reference video -> 3
])
def test_estimate_cost(args, usd):
    assert seedance_api.estimate_cost(*args) == pytest.approx(usd)


def test_estimate_cost_rejects_unrendered_tiers():
    with pytest.raises(ValueError):
        seedance_api.estimate_cost("seedance-2.0-mini", "1080p", 5)


def test_doctests_in_models():
    assert doctest.testmod(models).failed == 0
