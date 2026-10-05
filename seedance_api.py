"""Small synchronous client for the public Argolink Seedance 2.0 contract."""

from __future__ import annotations

import mimetypes
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union
from urllib.parse import quote

import requests


MODEL_ID = "seedance-2.0"
DEFAULT_BASE_URL = "https://api.argolink.io"
ALLOWED_RESOLUTIONS = {"480p", "720p", "1080p", "4k"}
ALLOWED_RATIOS = {"adaptive", "21:9", "16:9", "4:3", "1:1", "3:4", "9:16"}
MAX_IMAGES = 9
MAX_VIDEOS = 3
MAX_AUDIOS = 3
MAX_ASSETS = 15


class SeedanceAPIError(RuntimeError):
    """An API, validation, upload, or terminal-job error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        payload: Any = None,
        request_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload
        self.request_id = request_id


class SeedanceAPI:
    """Argolink Seedance 2.0 client.

    The client deliberately does not retry a submit request: retrying a POST after a
    network timeout can create a second paid job. Polling and downloads are separate
    operations so callers can apply their own retry policy safely.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: Optional[str] = None,
        session: Optional[requests.Session] = None,
        timeout: Union[float, tuple] = 30,
        poll_interval: float = 5,
    ) -> None:
        self.api_key = api_key or os.getenv("ARGOLINK_API_KEY")
        if not self.api_key:
            raise SeedanceAPIError("ARGOLINK_API_KEY is required")
        self.base_url = (base_url or os.getenv("ARGOLINK_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.session = session or requests.Session()
        self.timeout = timeout
        self.poll_interval = poll_interval

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _json_or_text(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        headers = dict(self._headers())
        headers.update(kwargs.pop("headers", {}))
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                timeout=kwargs.pop("timeout", self.timeout),
                **kwargs,
            )
        except requests.RequestException as exc:
            raise SeedanceAPIError(f"network error while calling {method} {path}: {exc}") from exc
        if response.status_code >= 400:
            payload = self._json_or_text(response)
            request_id = payload.get("request_id") if isinstance(payload, dict) else None
            detail = payload.get("error") if isinstance(payload, dict) else payload
            raise SeedanceAPIError(
                f"Argolink returned HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
                payload=payload,
                request_id=request_id,
            )
        return response

    def _post_json(self, path: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        response = self._request("POST", path, json=dict(payload))
        decoded = self._json_or_text(response)
        if not isinstance(decoded, dict):
            raise SeedanceAPIError("expected a JSON object from Argolink", status_code=response.status_code, payload=decoded)
        return decoded

    @staticmethod
    def _validate_prompt(prompt: str) -> None:
        if not isinstance(prompt, str) or not prompt.strip():
            raise SeedanceAPIError("prompt is required")

    @staticmethod
    def _validate_common(duration: int, resolution: str, aspect_ratio: str) -> None:
        if isinstance(duration, bool) or not isinstance(duration, int) or not 4 <= duration <= 15:
            raise SeedanceAPIError("duration must be an integer from 4 to 15 seconds")
        if resolution not in ALLOWED_RESOLUTIONS:
            raise SeedanceAPIError("resolution must be one of 480p, 720p, 1080p, or 4k")
        if aspect_ratio not in ALLOWED_RATIOS:
            raise SeedanceAPIError("aspect_ratio is not supported by Seedance 2.0")

    @staticmethod
    def _validate_url(url: str) -> str:
        if not isinstance(url, str) or not url.startswith("https://"):
            raise SeedanceAPIError("all media inputs must be HTTPS URLs")
        return url

    @classmethod
    def _validate_assets(
        cls,
        reference_images: Sequence[str],
        reference_videos: Sequence[str],
        reference_audios: Sequence[str],
    ) -> None:
        if len(reference_images) > MAX_IMAGES:
            raise SeedanceAPIError(f"at most {MAX_IMAGES} reference images are allowed")
        if len(reference_videos) > MAX_VIDEOS:
            raise SeedanceAPIError(f"at most {MAX_VIDEOS} reference videos are allowed")
        if len(reference_audios) > MAX_AUDIOS:
            raise SeedanceAPIError(f"at most {MAX_AUDIOS} reference audio tracks are allowed")
        if len(reference_images) + len(reference_videos) + len(reference_audios) > MAX_ASSETS:
            raise SeedanceAPIError(f"at most {MAX_ASSETS} reference assets are allowed in one request")
        if reference_audios and not (reference_images or reference_videos):
            raise SeedanceAPIError("audio references need at least one image or video")
        for url in [*reference_images, *reference_videos, *reference_audios]:
            cls._validate_url(url)

    @staticmethod
    def _asset_payload(urls: Iterable[str]) -> List[Dict[str, str]]:
        return [{"url": url} for url in urls]

    def _base_payload(
        self,
        prompt: Optional[str],
        *,
        duration: int,
        resolution: str,
        aspect_ratio: str,
        generate_audio: bool,
        required_prompt: bool = True,
    ) -> Dict[str, Any]:
        if required_prompt or prompt is not None:
            self._validate_prompt(prompt)
        self._validate_common(duration, resolution, aspect_ratio)
        if not isinstance(generate_audio, bool):
            raise SeedanceAPIError("generate_audio must be a boolean")
        payload = {
            "model": MODEL_ID,
            "duration": duration,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "generate_audio": generate_audio,
        }
        if prompt is not None:
            payload["prompt"] = prompt
        return payload

    def text_to_video(
        self,
        prompt: str,
        *,
        duration: int = 5,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
    ) -> Dict[str, Any]:
        """Submit a prompt-only video job."""
        payload = self._base_payload(
            prompt,
            duration=duration,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            generate_audio=generate_audio,
        )
        return self._post_json("/v1/videos/generations", payload)

    def image_to_video(
        self,
        prompt: Optional[str] = None,
        *,
        start_image: str,
        end_image: Optional[str] = None,
        duration: int = 5,
        resolution: str = "720p",
        generate_audio: bool = True,
    ) -> Dict[str, Any]:
        """Submit a first-frame or first/last-frame job."""
        if end_image is not None and not start_image:
            raise SeedanceAPIError("end_image requires start_image")
        payload = self._base_payload(
            prompt,
            duration=duration,
            resolution=resolution,
            aspect_ratio="adaptive",
            generate_audio=generate_audio,
            required_prompt=False,
        )
        payload["start_image"] = {"url": self._validate_url(start_image)}
        if end_image is not None:
            payload["end_image"] = {"url": self._validate_url(end_image)}
        return self._post_json("/v1/videos/generations", payload)

    def reference_to_video(
        self,
        prompt: Optional[str] = None,
        *,
        reference_images: Sequence[str] = (),
        reference_videos: Sequence[str] = (),
        reference_audios: Sequence[str] = (),
        duration: int = 5,
        resolution: str = "720p",
        aspect_ratio: str = "16:9",
        generate_audio: bool = True,
    ) -> Dict[str, Any]:
        """Submit a job with reference images, videos, audio, or a combination."""
        if not reference_images and not reference_videos and not reference_audios:
            raise SeedanceAPIError("at least one reference asset is required")
        self._validate_assets(reference_images, reference_videos, reference_audios)
        payload = self._base_payload(
            prompt,
            duration=duration,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            generate_audio=generate_audio,
            required_prompt=False,
        )
        if reference_images:
            payload["reference_images"] = self._asset_payload(reference_images)
        if reference_videos:
            payload["reference_videos"] = self._asset_payload(reference_videos)
        if reference_audios:
            payload["reference_audios"] = self._asset_payload(reference_audios)
        return self._post_json("/v1/videos/generations", payload)

    def upload_file(self, path: Union[str, Path], *, kind: str, content_type: Optional[str] = None) -> Dict[str, Any]:
        """Upload one local image, video, or audio file through a signed ticket."""
        source = Path(path)
        if kind not in {"image", "video", "audio"}:
            raise SeedanceAPIError("kind must be image, video, or audio")
        if not source.is_file():
            raise SeedanceAPIError(f"file does not exist: {source}")
        size_bytes = source.stat().st_size
        if size_bytes <= 0:
            raise SeedanceAPIError("cannot upload an empty file")
        mime = content_type or mimetypes.guess_type(source.name)[0]
        if not mime:
            raise SeedanceAPIError("content_type is required when it cannot be inferred")
        ticket = self._post_json(
            "/v1/media/uploads",
            {
                "model": MODEL_ID,
                "type": kind,
                "content_type": mime,
                "size_bytes": size_bytes,
            },
        )
        upload_url = ticket.get("upload_url")
        media_url = ticket.get("media_url")
        if not upload_url or not media_url:
            raise SeedanceAPIError("upload ticket did not include upload_url and media_url", payload=ticket)
        try:
            with source.open("rb") as handle:
                response = self.session.put(
                    upload_url,
                    data=handle,
                    headers={"Content-Type": mime},
                    timeout=self.timeout,
                )
        except requests.RequestException as exc:
            raise SeedanceAPIError(f"network error while uploading {source.name}: {exc}") from exc
        if response.status_code >= 400:
            raise SeedanceAPIError(
                f"signed upload returned HTTP {response.status_code}",
                status_code=response.status_code,
                payload=self._json_or_text(response),
            )
        return {"media_url": media_url, "upload_url": upload_url, "content_type": mime, "size_bytes": size_bytes}

    def get_result(self, request_id: str) -> Dict[str, Any]:
        if not request_id or "/" in request_id:
            raise SeedanceAPIError("request_id is required and must not contain '/'")
        response = self._request("GET", f"/v1/videos/{quote(request_id, safe='')}")
        decoded = self._json_or_text(response)
        if not isinstance(decoded, dict):
            raise SeedanceAPIError("expected a JSON object from the status endpoint", payload=decoded)
        return decoded

    def wait_for_completion(self, request_id: str, *, max_wait_seconds: float = 1800) -> Dict[str, Any]:
        """Poll a job with a bounded wait and return its terminal response."""
        if max_wait_seconds <= 0:
            raise SeedanceAPIError("max_wait_seconds must be positive")
        deadline = time.monotonic() + max_wait_seconds
        while True:
            result = self.get_result(request_id)
            status = result.get("status")
            if status == "done":
                return result
            if status in {"failed", "expired"}:
                detail = result.get("error") or f"job ended with status {status}"
                raise SeedanceAPIError(str(detail), payload=result, request_id=request_id)
            if status not in {"pending", "running"}:
                raise SeedanceAPIError(f"unknown job status: {status}", payload=result, request_id=request_id)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SeedanceAPIError("polling deadline reached; the job may still be running", payload=result, request_id=request_id)
            time.sleep(min(self.poll_interval, remaining))

    def download(self, request_id: str, destination: Union[str, Path]) -> Path:
        """Stream a completed video to a temporary file, then atomically rename it."""
        if not request_id or "/" in request_id:
            raise SeedanceAPIError("request_id is required and must not contain '/'")
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        try:
            response = self.session.get(
                f"{self.base_url}/v1/videos/{quote(request_id, safe='')}/content",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=self.timeout,
                stream=True,
            )
        except requests.RequestException as exc:
            raise SeedanceAPIError(f"network error while downloading {request_id}: {exc}") from exc
        if response.status_code >= 400:
            raise SeedanceAPIError(
                f"download returned HTTP {response.status_code}",
                status_code=response.status_code,
                payload=self._json_or_text(response),
                request_id=request_id,
            )
        try:
            with partial.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)
            partial.replace(target)
        except (OSError, requests.RequestException) as exc:
            partial.unlink(missing_ok=True)
            raise SeedanceAPIError(f"could not complete download to {target}: {exc}") from exc
        finally:
            close = getattr(response, "close", None)
            if close is not None:
                close()
        return target
