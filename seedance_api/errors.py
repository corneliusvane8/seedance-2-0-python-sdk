"""Exception types. Every error the SDK raises derives from SeedanceError.

HTTP errors carry the API's error object ({"type", "code", "param", "message"});
jobs that end without a video raise JobFailedError or JobExpiredError with the
job's own error object ({"code", "message", "retryable", "field"}).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class SeedanceError(Exception):
    """Base class."""


class ValidationError(SeedanceError, ValueError):
    """The request breaks a documented limit; raised before anything is sent."""


class APIError(SeedanceError):
    """The API answered with an HTTP error status."""

    def __init__(self, status: int, body: Any = None, retry_after: Optional[float] = None):
        error = body.get("error") if isinstance(body, dict) else None
        error = error if isinstance(error, dict) else {}
        self.status = status
        self.body = body
        self.type: Optional[str] = error.get("type")
        self.code: Optional[str] = error.get("code")
        self.param: Optional[str] = error.get("param")
        self.message: str = error.get("message") or (body if isinstance(body, str) else "") or f"HTTP {status}"
        self.retry_after = retry_after
        super().__init__(f"HTTP {status}" + (f" {self.code}" if self.code else "") + f": {self.message}")


class BadRequestError(APIError):
    """400: malformed body (field_invalid, json_invalid) or a combination the model refuses (request_unsupported)."""


class AuthenticationError(APIError):
    """401: missing or invalid API key."""


class PermissionDeniedError(APIError):
    """402 or 403: insufficient balance, or the key's group may not use video models."""


class NotFoundError(APIError):
    """404 video_request_not_found: unknown request_id, or a key that belongs to another user."""


class VideoNotReadyError(APIError):
    """409 job_video_not_ready: the content was requested before the job was done."""


class FailedJobContentError(APIError):
    """424 job_failed: the content of a failed job was requested."""


class RateLimitError(APIError):
    """429: concurrency or rate limit reached; retry when running jobs finish."""


class ServiceUnavailableError(APIError):
    """503 no_capacity or a temporary outage; retry after `retry_after` seconds. Nothing is charged."""


_BY_STATUS = {
    400: BadRequestError,
    401: AuthenticationError,
    402: PermissionDeniedError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: VideoNotReadyError,
    424: FailedJobContentError,
    429: RateLimitError,
    503: ServiceUnavailableError,
}


def api_error(status: int, body: Any = None, retry_after: Optional[float] = None) -> APIError:
    return _BY_STATUS.get(status, APIError)(status, body, retry_after)


class JobError(SeedanceError):
    """A job ended without a video. Nothing is billed for it."""

    def __init__(self, job: Dict[str, Any]):
        error = job.get("error") if isinstance(job.get("error"), dict) else {}
        self.job = job
        self.request_id: Optional[str] = job.get("request_id")
        self.status: Optional[str] = job.get("status")
        self.code: Optional[str] = error.get("code")
        self.message: str = error.get("message") or ""
        self.retryable: bool = bool(error.get("retryable"))
        self.field: Optional[str] = error.get("field")
        detail = f" {self.code}: {self.message}" if self.code else ""
        super().__init__(f"job {self.request_id} {self.status}{detail}")


class JobFailedError(JobError):
    """status == "failed". When `retryable` is True, submitting the same request again is safe."""


class JobExpiredError(JobError):
    """status == "expired"."""


class WaitTimeoutError(SeedanceError):
    """The local wait ran out while the job was still pending. The job may still finish: poll it again later."""

    def __init__(self, request_id: str, last: Dict[str, Any]):
        self.request_id = request_id
        self.last = last
        super().__init__(f"job {request_id} still {last.get('status')} ({last.get('progress', 0)}%) when the wait ran out")
