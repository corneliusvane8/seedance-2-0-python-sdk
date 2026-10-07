"""The MCP server registers its tools and answers estimate_cost offline. Skipped without the `mcp` package."""
import asyncio
import json

import pytest

pytest.importorskip("mcp")

from seedance_api import mcp_server  # noqa: E402


def test_tools_are_registered():
    tools = asyncio.run(mcp_server.server.list_tools())
    names = {tool.name for tool in tools}
    assert {"create_video", "get_video_status", "wait_for_video", "download_video", "upload_media", "estimate_cost"} <= names
    create = next(tool for tool in tools if tool.name == "create_video")
    schema = create.model_dump(by_alias=True)["inputSchema"]  # same key in mcp 1.x and 2.x
    assert schema["required"] == ["prompt"]
    assert "api_key" not in json.dumps(schema)


def test_estimate_cost_tool_needs_no_key(monkeypatch):
    monkeypatch.delenv("SEEDANCE_API_KEY", raising=False)
    assert mcp_server.estimate_cost("seedance-2.0", "1080p", 8) == {"usd": 2.24, "rates_checked": "2026-10-07"}
    assert "error" in mcp_server.estimate_cost("seedance-2.0-mini", "4k", 5)
