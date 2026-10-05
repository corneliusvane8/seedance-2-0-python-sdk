"""Optional MCP tools for the Argolink Seedance 2.0 client."""

from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from seedance_api import SeedanceAPI

mcp = FastMCP("argolink-seedance-2.0")


def _client() -> SeedanceAPI:
    return SeedanceAPI()


@mcp.tool()
def text_to_video(prompt: str, duration: int = 5, resolution: str = "720p", aspect_ratio: str = "16:9") -> Dict[str, Any]:
    """Submit a prompt-only Seedance 2.0 video job."""
    return _client().text_to_video(prompt, duration=duration, resolution=resolution, aspect_ratio=aspect_ratio)


@mcp.tool()
def image_to_video(prompt: str, start_image: str, end_image: Optional[str] = None, duration: int = 5) -> Dict[str, Any]:
    """Submit a first-frame or first/last-frame job using HTTPS image URLs."""
    return _client().image_to_video(prompt, start_image=start_image, end_image=end_image, duration=duration)


@mcp.tool()
def reference_to_video(
    prompt: str,
    reference_images: Optional[List[str]] = None,
    reference_videos: Optional[List[str]] = None,
    reference_audios: Optional[List[str]] = None,
    duration: int = 5,
) -> Dict[str, Any]:
    """Submit a job with reference media URLs."""
    return _client().reference_to_video(
        prompt,
        reference_images=reference_images or [],
        reference_videos=reference_videos or [],
        reference_audios=reference_audios or [],
        duration=duration,
    )


@mcp.tool()
def get_task_status(request_id: str) -> Dict[str, Any]:
    """Read one asynchronous job status."""
    return _client().get_result(request_id)


if __name__ == "__main__":
    mcp.run()
