"""Limits and per-second prices of the three Seedance 2.0 model IDs.

Limits come from the Seedance 2.0 model page and API docs; prices are the
ArgoLink rates per output second, checked on PRICES_CHECKED. The server stays
the authority: these values only let the client reject a request early and
estimate its cost before it is sent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple

PRICES_CHECKED = "2026-10-07"

FIXED_RATIOS: Tuple[str, ...] = ("21:9", "16:9", "4:3", "1:1", "3:4", "9:16")
FRAME_RATIOS: Tuple[str, ...] = ("adaptive",) + FIXED_RATIOS
MAX_PROMPT_BYTES = 40_000


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    resolutions: Tuple[str, ...]
    price_per_second: Dict[str, float] = field(default_factory=dict)
    min_duration: int = 4
    max_duration: int = 15
    default_duration: int = 5
    max_images: int = 9
    max_videos: int = 3
    max_audios: int = 3
    max_assets: int = 15
    reference_media_seconds: Tuple[int, int, int] = (2, 15, 15)  # min each, max each, max combined

    def rate(self, resolution: str) -> float:
        try:
            return self.price_per_second[resolution]
        except KeyError:
            raise ValueError(f"{self.model_id} does not render {resolution}; choose one of {', '.join(self.resolutions)}") from None


MODELS: Dict[str, ModelSpec] = {
    spec.model_id: spec
    for spec in (
        ModelSpec("seedance-2.0", ("480p", "720p", "1080p", "4k"),
                  {"480p": 0.053, "720p": 0.11, "1080p": 0.28, "4k": 0.58}),
        ModelSpec("seedance-2.0-fast", ("480p", "720p"), {"480p": 0.042, "720p": 0.091}),
        ModelSpec("seedance-2.0-mini", ("480p", "720p"), {"480p": 0.026, "720p": 0.057}),
    )
}


def get_spec(model_id: str) -> ModelSpec:
    try:
        return MODELS[model_id]
    except KeyError:
        raise ValueError(f"unknown model {model_id!r}; this SDK covers {', '.join(MODELS)}") from None


def billed_seconds(duration: int, reference_video_seconds: Iterable[float] = ()) -> int:
    """Output seconds plus the combined length of the reference videos, fraction dropped."""
    return int(duration) + math.floor(sum(reference_video_seconds) + 1e-9)


def estimate_cost(model_id: str, resolution: str = "720p", duration: int = 5,
                  reference_video_seconds: Iterable[float] = ()) -> float:
    """Price of one job in USD at the PRICES_CHECKED rates.

    >>> estimate_cost("seedance-2.0", "1080p", 8)
    2.24
    >>> estimate_cost("seedance-2.0", "720p", 6, [3.5])  # 6 s + 3 s of reference video
    0.99
    """
    spec = get_spec(model_id)
    return round(spec.rate(resolution) * billed_seconds(duration, reference_video_seconds), 4)
