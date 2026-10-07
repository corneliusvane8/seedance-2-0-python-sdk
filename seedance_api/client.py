"""Synchronous client for the Seedance 2.0 video API (/v1/videos protocol)."""
from __future__ import annotations

import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Union
from urllib.parse import quote

import requests

from .errors import (
    JobExpiredError,
    JobFailedError,
    RateLimitError,
    SeedanceError,
    ServiceUnavailableError,
    ValidationError,
    WaitTimeoutError,
    api_error,
)
from .models import FIXED_RATIOS, FRAME_RATIOS, MAX_PROMPT_BYTES, MODELS, estimate_cost, get_spec

DEFAULT_BASE_URL = "https://argolink.io/v1"
DEFAULT_MODEL = "seedance-2.0"

Media = Union[str, Mapping[str, str]]
REFERENCE_FIELDS = ("reference_images", "reference_videos", "reference_audios")
# Upload content types Seedance generation accepts (tickets take a few more).
UPLOAD_TYPES = {
    "image/jpeg": "image", "image/png": "image",
    "video/mp4": "video", "video/quicktime": "video",
    "audio/mpeg": "audio", "audio/wav": "audio",
}
UPLOAD_SIZE_LIMITS = {"image": 20 * 1024 * 1024, "audio": 15_000_000}


def _media(value: Media) -> Dict[str, str]:
    url = value.get("url") if isinstance(value, Mapping) else value
    if not isinstance(url, str) or not url.startswith("https://"):
        raise ValidationError(f"media must be a public https:// URL (upload local files first), got {url!r}")
    return {"url": url}


def validate_payload(body: Mapping[str, Any]) -> None:
    """Check a request body against the documented Seedance 2.0 limits. Raises ValidationError."""
    try:
        spec = get_spec(body.get("model", ""))
    except ValueError as exc:
        raise ValidationError(str(exc)) from None
    prompt = body.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValidationError("prompt is required in every mode, also next to images, videos or audio")
    if len(prompt.encode("utf-8")) > MAX_PROMPT_BYTES:
        raise ValidationError(f"prompt is longer than {MAX_PROMPT_BYTES} bytes")
    duration = body.get("duration", spec.default_duration)
    if isinstance(duration, bool) or not isinstance(duration, int) or not spec.min_duration <= duration <= spec.max_duration:
        raise ValidationError(f"duration must be a whole number of seconds from {spec.min_duration} to {spec.max_duration}")
    resolution = body.get("resolution", "720p")
    if resolution not in spec.resolutions:
        raise ValidationError(f"{spec.model_id} renders {', '.join(spec.resolutions)}, not {resolution!r}")

    frames = "start_image" in body or "end_image" in body
    refs = {name: list(body.get(name) or []) for name in REFERENCE_FIELDS}
    if frames and any(refs.values()):
        raise ValidationError("start_image/end_image cannot be combined with reference_images, reference_videos or reference_audios")
    if "end_image" in body and "start_image" not in body:
        raise ValidationError("end_image needs a start_image")
    ratio = body.get("aspect_ratio", "adaptive" if frames else "16:9")
    allowed = FRAME_RATIOS if frames else FIXED_RATIOS
    if ratio not in allowed:
        raise ValidationError(f"aspect_ratio must be one of {', '.join(allowed)} in this mode, not {ratio!r}")

    images, videos, audios = refs["reference_images"], refs["reference_videos"], refs["reference_audios"]
    for items, cap, label in ((images, spec.max_images, "images"), (videos, spec.max_videos, "videos"), (audios, spec.max_audios, "audio clips")):
        if len(items) > cap:
            raise ValidationError(f"{spec.model_id} takes at most {cap} reference {label}")
    if len(images) + len(videos) + len(audios) > spec.max_assets:
        raise ValidationError(f"{spec.model_id} takes at most {spec.max_assets} reference assets in total")
    if audios and not (images or videos):
        raise ValidationError("audio cannot be the only reference on the 2.0 family: add an image or a video")
    for item in [body.get("start_image"), body.get("end_image"), *images, *videos, *audios]:
        if item is not None:
            _media(item)

    if body.get("n", 1) != 1:
        raise ValidationError("one video per request: n must be 1 or omitted")
    if "seed" in body:
        raise ValidationError("seed is not supported on Seedance 2.0")
    if body.get("watermark") is True:
        raise ValidationError("watermark: true is not supported on Seedance 2.0")


class SeedanceAPI:
    """Client for seedance-2.0, seedance-2.0-fast and seedance-2.0-mini.

    Submissions are never retried automatically: a POST that timed out may
    still have created a job. Polling retries 429, 503 and network errors.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        session: Optional[requests.Session] = None,
        timeout: float = 60.0,
        poll_interval: float = 10.0,
        validate: bool = True,
    ) -> None:
        self.api_key = api_key or os.environ.get("SEEDANCE_API_KEY")
        if not self.api_key:
            raise SeedanceError("no API key: pass api_key or set SEEDANCE_API_KEY")
        self.base_url = (base_url or os.environ.get("SEEDANCE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model
        self.session = session or requests.Session()
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.validate = validate

    # -- HTTP -----------------------------------------------------------------
    def _call(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        headers = {"Authorization": f"Bearer {self.api_key}", **kwargs.pop("headers", {})}
        response = self.session.request(method, self.base_url + path, headers=headers,
                                        timeout=kwargs.pop("timeout", self.timeout), **kwargs)
        if response.status_code >= 400:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
            retry_after = response.headers.get("Retry-After") if getattr(response, "headers", None) else None
            raise api_error(response.status_code, body, float(retry_after) if retry_after else None)
        return response

    # -- submit ---------------------------------------------------------------
    def submit(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """POST /videos/generations with a raw body. Returns {"request_id": ...}."""
        body = {"model": self.model, **payload}
        if self.validate:
            validate_payload(body)
        return self._call("POST", "/videos/generations", json=body).json()

    def text_to_video(self, prompt: str, *, model: Optional[str] = None, duration: int = 5, resolution: str = "720p",
                      aspect_ratio: str = "16:9", generate_audio: bool = True) -> Dict[str, Any]:
        return self.submit({"model": model or self.model, "prompt": prompt, "duration": duration,
                            "resolution": resolution, "aspect_ratio": aspect_ratio, "generate_audio": generate_audio})

    def image_to_video(self, prompt: str, start_image: Media, *, end_image: Optional[Media] = None,
                       model: Optional[str] = None, duration: int = 5, resolution: str = "720p",
                       aspect_ratio: str = "adaptive", generate_audio: bool = True) -> Dict[str, Any]:
        """First frame, or first + last frame when end_image is given. "adaptive" follows the first frame."""
        body: Dict[str, Any] = {"model": model or self.model, "prompt": prompt, "duration": duration,
                                "resolution": resolution, "aspect_ratio": aspect_ratio,
                                "generate_audio": generate_audio, "start_image": _media(start_image)}
        if end_image is not None:
            body["end_image"] = _media(end_image)
        return self.submit(body)

    def reference_to_video(self, prompt: str, *, images: Sequence[Media] = (), videos: Sequence[Media] = (),
                           audios: Sequence[Media] = (), model: Optional[str] = None, duration: int = 5,
                           resolution: str = "720p", aspect_ratio: str = "16:9",
                           generate_audio: bool = True) -> Dict[str, Any]:
        """Name assets in the prompt as @Image 1, @Video 1, @Audio 1 (numbered within each list)."""
        body: Dict[str, Any] = {"model": model or self.model, "prompt": prompt, "duration": duration,
                                "resolution": resolution, "aspect_ratio": aspect_ratio, "generate_audio": generate_audio}
        for name, items in zip(REFERENCE_FIELDS, (images, videos, audios)):
            if items:
                body[name] = [_media(item) for item in items]
        return self.submit(body)

    # -- results --------------------------------------------------------------
    def get_result(self, request_id: str) -> Dict[str, Any]:
        return self._call("GET", f"/videos/{quote(request_id, safe='')}").json()

    def wait_for_completion(self, request_id: str, *, timeout: float = 1800,
                            on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
                            max_transient_errors: int = 5) -> Dict[str, Any]:
        """Poll until done. Raises JobFailedError, JobExpiredError or WaitTimeoutError."""
        deadline = time.monotonic() + timeout
        errors_in_a_row = 0
        job: Dict[str, Any] = {"request_id": request_id, "status": "pending"}
        while True:
            try:
                job = self.get_result(request_id)
                errors_in_a_row = 0
            except (RateLimitError, ServiceUnavailableError, requests.ConnectionError, requests.Timeout) as exc:
                errors_in_a_row += 1
                if errors_in_a_row > max_transient_errors:
                    raise
                wait = getattr(exc, "retry_after", None) or self.poll_interval
                time.sleep(min(wait, max(0.0, deadline - time.monotonic())))
                continue
            status = job.get("status")
            if status == "done":
                return job
            if status == "failed":
                raise JobFailedError(job)
            if status == "expired":
                raise JobExpiredError(job)
            if on_progress:
                on_progress(job)
            if time.monotonic() >= deadline:
                raise WaitTimeoutError(request_id, job)
            time.sleep(min(self.poll_interval, max(0.0, deadline - time.monotonic())))

    def download(self, request_id: str, destination: Union[str, Path]) -> Path:
        """Stream the MP4 into destination via a .part file, renamed only when complete."""
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        response = self._call("GET", f"/videos/{quote(request_id, safe='')}/content", stream=True, timeout=600)
        try:
            with partial.open("wb") as out:
                for chunk in response.iter_content(chunk_size=1 << 20):
                    if chunk:
                        out.write(chunk)
            partial.replace(target)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        finally:
            close = getattr(response, "close", None)
            if close:
                close()
        return target

    # -- uploads --------------------------------------------------------------
    def upload_file(self, path: Union[str, Path], *, content_type: Optional[str] = None,
                    model: Optional[str] = None) -> str:
        """Upload a local JPEG/PNG, MP4/MOV or MP3/WAV file and return its media_url (valid 7 days)."""
        source = Path(path)
        if not source.is_file():
            raise ValidationError(f"no such file: {source}")
        mime = content_type or mimetypes.guess_type(source.name)[0] or ""
        mime = {"audio/x-wav": "audio/wav", "audio/wave": "audio/wav", "audio/mp3": "audio/mpeg"}.get(mime, mime)
        kind = UPLOAD_TYPES.get(mime)
        if not kind:
            raise ValidationError(f"{source.name}: Seedance takes JPEG/PNG images, MP4/MOV video and MP3/WAV audio, not {mime or 'this type'}")
        size = source.stat().st_size
        if size > UPLOAD_SIZE_LIMITS.get(kind, size):
            raise ValidationError(f"{source.name} is {size} bytes; the {kind} limit is {UPLOAD_SIZE_LIMITS[kind]}")
        ticket = self._call("POST", "/media/uploads", json={
            "model": model or self.model, "type": kind, "content_type": mime, "size_bytes": size,
        }).json()
        with source.open("rb") as data:
            # Straight to storage: exactly the declared Content-Type, and no API key.
            put = self.session.put(ticket["upload_url"], data=data, headers={"Content-Type": mime}, timeout=600)
        if put.status_code >= 400:
            raise api_error(put.status_code, getattr(put, "text", ""))
        return ticket["media_url"]

    # -- one call -------------------------------------------------------------
    def generate(self, prompt: str, destination: Union[str, Path, None] = None, *,
                 on_progress: Optional[Callable[[Dict[str, Any]], None]] = None, **options: Any) -> Dict[str, Any]:
        """Pick the mode from the options, wait for the job, and save it if destination is given.

        start_image / end_image -> frames; images / videos / audios -> reference; neither -> text.
        """
        if "start_image" in options:
            submitted = self.image_to_video(prompt, options.pop("start_image"), **options)
        elif any(key in options for key in ("images", "videos", "audios")):
            submitted = self.reference_to_video(prompt, **options)
        else:
            submitted = self.text_to_video(prompt, **options)
        job = self.wait_for_completion(submitted["request_id"], on_progress=on_progress)
        if destination is not None:
            self.download(submitted["request_id"], destination)
        return job

    @staticmethod
    def estimate_cost(model: str = DEFAULT_MODEL, resolution: str = "720p", duration: int = 5,
                      reference_video_seconds: Iterable[float] = ()) -> float:
        return estimate_cost(model, resolution, duration, reference_video_seconds)

    @staticmethod
    def models() -> List[str]:
        return list(MODELS)
