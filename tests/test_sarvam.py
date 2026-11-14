import base64
import json
from typing import Any

import pytest
import requests

from fintechagent import SarvamError, Settings
from fintechagent.sarvam import Question, Sarvam


class FakeResponse:
    def __init__(self, status: int = 200, payload: Any = None, text: str = ""):
        self.status_code = status
        self._payload = payload
        self.text = text or json.dumps(payload)

    def json(self) -> Any:
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class FakeSession(requests.Session):
    def __init__(self, response: FakeResponse | Exception):
        super().__init__()
        self.response = response
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, url, **kwargs):  # type: ignore[override]
        self.calls.append((url, kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def client(response: FakeResponse | Exception) -> tuple[Sarvam, FakeSession]:
    session = FakeSession(response)
    settings = Settings(api_key="test-key", base_url="https://api.test", timeout=7)
    return Sarvam("test-key", settings=settings, session=session), session


def test_answer_success():
    sarvam, session = client(
        FakeResponse(payload={"answers": [{"response": "Great card", "reasoning": "r"}]})
    )
    answer = sarvam.answer("ctx", Question("What?", 3), "desc")
    assert answer.response == "Great card"
    assert answer.utterance == ""
    url, kwargs = session.calls[0]
    assert url == "https://api.test/text-analytics"
    assert kwargs["timeout"] == 7
    sent = json.loads(kwargs["data"]["questions"])
    assert sent[0]["id"] == "3" and sent[0]["text"] == "What?"
    assert session.headers["api-subscription-key"] == "test-key"


def test_tts_success_and_payload():
    wav = b"RIFF....WAVE"
    sarvam, session = client(FakeResponse(payload={"audios": [base64.b64encode(wav).decode()]}))
    result = sarvam.tts("Hello")
    assert result.audio == wav
    body = session.calls[0][1]["json"]
    assert body["inputs"] == ["Hello"]
    assert body["model"] == "bulbul:v1"


@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_tts_rejects_bad_input(text):
    sarvam, session = client(FakeResponse(payload={}))
    with pytest.raises(ValueError):
        sarvam.tts(text)
    assert session.calls == []


def test_stt_success():
    sarvam, session = client(
        FakeResponse(payload={"transcript": "hello", "language_code": "en-IN"})
    )
    result = sarvam.stt(b"RIFF")
    assert (result.text, result.lang_code) == ("hello", "en-IN")
    assert session.calls[0][0].endswith("/speech-to-text-translate")


@pytest.mark.parametrize(
    ("response", "match"),
    [
        (FakeResponse(status=401, text="invalid key"), "HTTP 401"),
        (FakeResponse(status=200, payload=None, text="<html>"), "invalid JSON"),
        (FakeResponse(payload={"oops": 1}), "missing"),
        (requests.ConnectionError("down"), "request failed"),
    ],
)
def test_errors_are_wrapped(response, match):
    sarvam, _ = client(response)
    with pytest.raises(SarvamError, match=match):
        sarvam.answer("ctx", Question("q", 0), "d")


def test_stt_missing_transcript():
    sarvam, _ = client(FakeResponse(payload={"language_code": "en"}))
    with pytest.raises(SarvamError, match="transcript"):
        sarvam.stt(b"RIFF")


def test_empty_key_rejected():
    with pytest.raises(ValueError):
        Sarvam("")
