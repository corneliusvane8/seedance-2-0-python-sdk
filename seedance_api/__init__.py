"""Community Python SDK for the Seedance 2.0 video API: seedance-2.0, seedance-2.0-fast, seedance-2.0-mini.

    from seedance_api import SeedanceAPI

    api = SeedanceAPI()                      # SEEDANCE_API_KEY, optional SEEDANCE_BASE_URL
    job = api.generate("A kite over a beach at sunset", "kite.mp4", resolution="1080p")
"""
from .client import DEFAULT_BASE_URL, SeedanceAPI, validate_payload
from .errors import (
    APIError,
    AuthenticationError,
    BadRequestError,
    FailedJobContentError,
    JobError,
    JobExpiredError,
    JobFailedError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    SeedanceError,
    ServiceUnavailableError,
    ValidationError,
    VideoNotReadyError,
    WaitTimeoutError,
)
from .models import MODELS, PRICES_CHECKED, ModelSpec, billed_seconds, estimate_cost

__version__ = "0.2.0"

__all__ = [
    "DEFAULT_BASE_URL", "SeedanceAPI", "validate_payload",
    "MODELS", "PRICES_CHECKED", "ModelSpec", "billed_seconds", "estimate_cost",
    "SeedanceError", "ValidationError", "APIError", "BadRequestError", "AuthenticationError",
    "PermissionDeniedError", "NotFoundError", "VideoNotReadyError", "FailedJobContentError",
    "RateLimitError", "ServiceUnavailableError", "JobError", "JobFailedError", "JobExpiredError",
    "WaitTimeoutError",
]
