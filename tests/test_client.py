"""Client behaviour against a fake HTTP session: no key, no network."""
import json

import pytest
import requests

import seedance_api
from seedance_api import client as client_module


class FakeResponse:
    def __init__(self, status=200, payload=None, body=b"", headers=None):
        self.status_code = status
        self._payload = payload
        self._body = body
        self.headers = headers or {}
        self.text = json.dumps(payload) if payload is not None else body.decode()

    def json(self):
        if self._payload is None:
            raise ValueError("not JSON")
        return self._payload

    def iter_content(self, chunk_size=1):
        yield self._body

    def close(self):
        pass


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []
        self.puts = []

    def request(self, method, url, headers=None, timeout=None, **kwargs):
        self.requests.append({"method": method, "url": url, "headers": headers, **kwargs})
        answer = self.responses.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer

    def put(self, url, data=None, headers=None, timeout=None):
        self.puts.append({"url": url, "headers": headers, "bytes": data.read()})
        return FakeResponse(200, {})


@pytest.fixture(autouse=True)
def instant_sleep(monkeypatch):
    monkeypatch.setattr(client_module.time, "sleep", lambda s: None)


def make(responses, **kwargs):
    session = FakeSession(responses)
    return seedance_api.SeedanceAPI("key-1", session=session, **kwargs), session


def test_text_to_video_posts_a_complete_body():
    api, session = make([FakeResponse(202, {"request_id": "r1"})])
    assert api.text_to_video("a kite over dunes", duration=8, resolution="1080p") == {"request_id": "r1"}
    sent = session.requests[0]
    assert sent["method"] == "POST" and sent["url"] == "https://argolink.io/v1/videos/generations"
    assert sent["headers"]["Authorization"] == "Bearer key-1"
    assert sent["json"] == {"model": "seedance-2.0", "prompt": "a kite over dunes", "duration": 8,
                            "resolution": "1080p", "aspect_ratio": "16:9", "generate_audio": True}


def test_frames_default_to_adaptive_and_accept_plain_urls():
    api, session = make([FakeResponse(202, {"request_id": "r2"})])
    api.image_to_video("dusk falls", "https://x.test/a.png", end_image={"url": "https://x.test/b.png"}, model="seedance-2.0-mini")
    body = session.requests[0]["json"]
    assert body["aspect_ratio"] == "adaptive"
    assert body["start_image"] == {"url": "https://x.test/a.png"} and body["end_image"] == {"url": "https://x.test/b.png"}
    assert body["model"] == "seedance-2.0-mini"


def test_reference_lists_only_include_what_was_given():
    api, session = make([FakeResponse(202, {"request_id": "r3"})])
    api.reference_to_video("@Image 1 dances like @Video 1", images=["https://x.test/i.png"], videos=["https://x.test/v.mp4"])
    body = session.requests[0]["json"]
    assert body["reference_images"] == [{"url": "https://x.test/i.png"}]
    assert body["reference_videos"] == [{"url": "https://x.test/v.mp4"}]
    assert "reference_audios" not in body


def test_wait_returns_done_job_and_reports_progress():
    api, _ = make([
        FakeResponse(200, {"request_id": "r", "status": "pending", "progress": 0}),
        FakeResponse(200, {"request_id": "r", "status": "pending", "progress": 70, "estimated_seconds_remaining": 30}),
        FakeResponse(200, {"request_id": "r", "status": "done", "progress": 100, "usage": {"billed_seconds": 5}}),
    ])
    seen = []
    job = api.wait_for_completion("r", on_progress=lambda j: seen.append(j["progress"]))
    assert job["usage"]["billed_seconds"] == 5 and seen == [0, 70]


def test_wait_survives_transient_errors_but_not_forever():
    api, _ = make([
        FakeResponse(503, {"error": {"type": "overloaded_error", "code": "no_capacity", "message": "busy"}}, headers={"Retry-After": "2"}),
        requests.ConnectionError("reset"),
        FakeResponse(200, {"request_id": "r", "status": "done"}),
    ])
    assert api.wait_for_completion("r")["status"] == "done"

    api, _ = make([FakeResponse(429, {"error": {"type": "rate_limit_error"}})] * 3)
    with pytest.raises(seedance_api.RateLimitError):
        api.wait_for_completion("r", max_transient_errors=2)


@pytest.mark.parametrize("status,error_type", [("failed", seedance_api.JobFailedError), ("expired", seedance_api.JobExpiredError)])
def test_terminal_states_raise_typed_errors(status, error_type):
    error = {"code": "capacity_unavailable", "message": "no capacity within 10 minutes", "retryable": True}
    api, _ = make([FakeResponse(200, {"request_id": "r", "status": status, "error": error})])
    with pytest.raises(error_type) as raised:
        api.wait_for_completion("r")
    assert raised.value.code == "capacity_unavailable" and raised.value.retryable is True


def test_wait_timeout_keeps_the_last_state(monkeypatch):
    api, _ = make([FakeResponse(200, {"request_id": "r", "status": "pending", "progress": 99})])
    with pytest.raises(seedance_api.WaitTimeoutError) as raised:
        api.wait_for_completion("r", timeout=0)
    assert raised.value.last["progress"] == 99


@pytest.mark.parametrize("status,error_type", [
    (400, seedance_api.BadRequestError), (401, seedance_api.AuthenticationError), (402, seedance_api.PermissionDeniedError),
    (404, seedance_api.NotFoundError), (409, seedance_api.VideoNotReadyError), (424, seedance_api.FailedJobContentError),
])
def test_http_errors_map_to_classes(status, error_type):
    body = {"error": {"type": "invalid_request_error", "code": "x_code", "param": "resolution", "message": "nope"}}
    api, _ = make([FakeResponse(status, body)])
    with pytest.raises(error_type) as raised:
        api.get_result("r")
    assert (raised.value.status, raised.value.code, raised.value.param) == (status, "x_code", "resolution")


def test_download_writes_through_a_part_file(tmp_path):
    api, session = make([FakeResponse(200, body=b"MP4DATA")])
    target = api.download("r", tmp_path / "clips" / "out.mp4")
    assert target.read_bytes() == b"MP4DATA"
    assert not (tmp_path / "clips" / "out.mp4.part").exists()
    assert session.requests[0]["url"].endswith("/videos/r/content")


def test_upload_requests_a_ticket_then_puts_without_the_key(tmp_path):
    clip = tmp_path / "voice.wav"
    clip.write_bytes(b"RIFF" + b"\x00" * 60)
    api, session = make([FakeResponse(200, {"upload_url": "https://store.test/u", "media_url": "https://media.test/m"})])
    assert api.upload_file(clip) == "https://media.test/m"
    assert session.requests[0]["json"] == {"model": "seedance-2.0", "type": "audio", "content_type": "audio/wav", "size_bytes": 64}
    assert session.puts == [{"url": "https://store.test/u", "headers": {"Content-Type": "audio/wav"}, "bytes": clip.read_bytes()}]


def test_generate_picks_the_reference_mode_and_saves(tmp_path):
    api, session = make([
        FakeResponse(202, {"request_id": "g1"}),
        FakeResponse(200, {"request_id": "g1", "status": "done", "usage": {"billed_seconds": 9}}),
        FakeResponse(200, body=b"MP4"),
    ])
    job = api.generate("@Image 1 waves", tmp_path / "g.mp4", images=["https://x.test/i.png"], duration=6)
    assert "reference_images" in session.requests[0]["json"]
    assert job["usage"]["billed_seconds"] == 9 and (tmp_path / "g.mp4").read_bytes() == b"MP4"


def test_key_and_base_url_from_environment(monkeypatch):
    monkeypatch.setenv("SEEDANCE_API_KEY", "env-key")
    monkeypatch.setenv("SEEDANCE_BASE_URL", "https://proxy.test/v1/")
    api = seedance_api.SeedanceAPI(session=FakeSession([]))
    assert (api.api_key, api.base_url) == ("env-key", "https://proxy.test/v1")
    monkeypatch.delenv("SEEDANCE_API_KEY")
    with pytest.raises(seedance_api.SeedanceError):
        seedance_api.SeedanceAPI(session=FakeSession([]))
