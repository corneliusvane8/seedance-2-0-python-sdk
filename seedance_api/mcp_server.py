"""MCP server exposing Seedance 2.0 as tools over stdio.

    pip install "seedance-2-0-python-sdk[mcp] @ git+https://github.com/corneliusvane8/seedance-2-0-python-sdk"
    SEEDANCE_API_KEY=... python -m seedance_api.mcp_server

The key is read from the server's environment and never accepted as a tool argument.
Works with the MCP Python SDK 2.x (MCPServer) and 1.x (FastMCP).
"""
from typing import Any, Dict, List, Optional

try:  # mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

from .client import SeedanceAPI
from .errors import JobError, SeedanceError
from .models import PRICES_CHECKED, estimate_cost as _estimate

server = _Server("seedance-2-0")
_client: Optional[SeedanceAPI] = None


def _api() -> SeedanceAPI:
    global _client
    if _client is None:
        _client = SeedanceAPI()
    return _client


@server.tool()
def create_video(
    prompt: str,
    model: str = "seedance-2.0",
    duration: int = 5,
    resolution: str = "720p",
    aspect_ratio: Optional[str] = None,
    start_image: Optional[str] = None,
    end_image: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    reference_videos: Optional[List[str]] = None,
    reference_audios: Optional[List[str]] = None,
    generate_audio: bool = True,
) -> Dict[str, Any]:
    """Start a Seedance 2.0 video job and return its request_id without waiting.

    model: seedance-2.0 (480p, 720p, 1080p, 4k), seedance-2.0-fast or seedance-2.0-mini (480p, 720p).
    duration: 4-15 seconds. Give start_image (and optionally end_image) for a frame video, or up to
    9 reference_images, 3 reference_videos and 3 reference_audios (audio needs an image or video),
    named in the prompt as @Image 1, @Video 1, @Audio 1. All media are https URLs.
    The prompt is always required. Reference videos add their seconds to the bill.
    """
    common = {"model": model, "duration": duration, "resolution": resolution, "generate_audio": generate_audio}
    try:
        if start_image:
            submitted = _api().image_to_video(prompt, start_image, end_image=end_image,
                                              aspect_ratio=aspect_ratio or "adaptive", **common)
        elif reference_images or reference_videos or reference_audios:
            submitted = _api().reference_to_video(prompt, images=reference_images or [], videos=reference_videos or [],
                                                  audios=reference_audios or [], aspect_ratio=aspect_ratio or "16:9", **common)
        else:
            submitted = _api().text_to_video(prompt, aspect_ratio=aspect_ratio or "16:9", **common)
    except SeedanceError as exc:
        return {"error": str(exc)}
    return {
        "request_id": submitted["request_id"],
        "estimated_cost_usd_before_reference_videos": _estimate(model, resolution, duration),
        "next": "call get_video_status every 10-15 s until status is done",
    }


@server.tool()
def get_video_status(request_id: str) -> Dict[str, Any]:
    """Return the job: status pending (progress 0-99), done (video.url, usage), failed (error) or expired."""
    try:
        return _api().get_result(request_id)
    except SeedanceError as exc:
        return {"error": str(exc)}


@server.tool()
def download_video(request_id: str, path: str) -> Dict[str, Any]:
    """Save a finished job's MP4 to a local path and return where it went."""
    try:
        return {"saved": str(_api().download(request_id, path))}
    except SeedanceError as exc:
        return {"error": str(exc)}


@server.tool()
def wait_for_video(request_id: str, timeout_seconds: int = 900) -> Dict[str, Any]:
    """Block until the job is done (or the timeout passes) and return the final job with its usage."""
    try:
        return _api().wait_for_completion(request_id, timeout=timeout_seconds)
    except JobError as exc:
        return exc.job
    except SeedanceError as exc:
        return {"error": str(exc)}


@server.tool()
def upload_media(path: str) -> Dict[str, Any]:
    """Upload a local JPEG/PNG, MP4/MOV or MP3/WAV file and return a media_url usable for 7 days."""
    try:
        return {"media_url": _api().upload_file(path)}
    except SeedanceError as exc:
        return {"error": str(exc)}


@server.tool()
def estimate_cost(model: str = "seedance-2.0", resolution: str = "720p", duration: int = 5,
                  reference_video_seconds: float = 0) -> Dict[str, Any]:
    """Price of one job in USD at the per-second rates checked on the date returned."""
    try:
        usd = _estimate(model, resolution, duration, [reference_video_seconds])
    except ValueError as exc:
        return {"error": str(exc)}
    return {"usd": usd, "rates_checked": PRICES_CHECKED}


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
