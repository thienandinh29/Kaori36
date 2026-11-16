import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.speech import SpeechClient, create_router

WAV = b"RIFF....WAVEfmt "


def tts_service(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/health":
        return httpx.Response(200, json={"status": "ok", "voice": "en_GB-cori-high"})
    if request.url.path == "/speak":
        body = request.read().decode()
        assert '"pace":"slow"' in body.replace(" ", "") or '"pace":"normal"' in body.replace(
            " ", ""
        )
        return httpx.Response(200, content=WAV, headers={"content-type": "audio/wav"})
    return httpx.Response(404)


def app_with(client: SpeechClient | None) -> TestClient:
    app = FastAPI()
    app.include_router(create_router(client))
    return TestClient(app)


@pytest.fixture
def api() -> TestClient:
    return app_with(SpeechClient("http://tts:8030", transport=httpx.MockTransport(tts_service)))


def test_status_names_the_server_voice(api: TestClient) -> None:
    assert api.get("/speech/status").json() == {"available": True, "voice": "en_GB-cori-high"}


def test_speech_returns_the_services_audio(api: TestClient) -> None:
    r = api.post("/speech", json={"text": "important", "pace": "slow"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content == WAV


@pytest.mark.parametrize(
    "body", [{"text": ""}, {"text": "x" * 301}, {"text": "— 12 —"}, {"text": "a", "pace": "fast"}]
)
def test_bad_text_is_refused_before_the_service(api: TestClient, body: dict[str, str]) -> None:
    assert api.post("/speech", json=body).status_code == 422


def test_without_a_voice_service_the_web_falls_back() -> None:
    api = app_with(None)
    assert api.get("/speech/status").json() == {"available": False, "voice": None}
    assert api.post("/speech", json={"text": "important"}).status_code == 503


def test_a_failing_service_is_unavailable_and_answers_502() -> None:
    def down(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    api = app_with(SpeechClient("http://tts:8030", transport=httpx.MockTransport(down)))
    assert api.get("/speech/status").json()["available"] is False
    assert api.post("/speech", json={"text": "important"}).status_code == 502


def test_a_non_audio_answer_is_not_passed_on() -> None:
    def wrong(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"oops": True})

    api = app_with(SpeechClient("http://tts:8030", transport=httpx.MockTransport(wrong)))
    assert api.post("/speech", json={"text": "important"}).status_code == 502


def test_the_route_is_mounted_in_the_app() -> None:
    from app.main import create_app

    paths = set(create_app().openapi()["paths"])
    assert {"/speech", "/speech/status"} <= paths
