"""Thin client for the Sarvam AI REST API (text analytics, TTS and STT)."""

from __future__ import annotations

import base64
import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

from .config import Settings
from .errors import SarvamError
from .text import TTS_MAX_CHARS

logger = logging.getLogger(__name__)

TEXT_ANALYTICS_PATH = "text-analytics"
TTS_PATH = "text-to-speech"
STT_PATH = "speech-to-text-translate"


@dataclass(frozen=True)
class Question:
    question: str
    id: int


@dataclass(frozen=True)
class Answer:
    question: Question
    response: str
    reasoning: str
    utterance: str


@dataclass(frozen=True)
class TTS:
    audio: bytes
    text: str


@dataclass(frozen=True)
class STT:
    text: str
    lang_code: str


class Sarvam:
    """Sarvam AI client. Pass a ``requests.Session`` to reuse connections or to test."""

    def __init__(
        self,
        api_key: str,
        *,
        settings: Settings | None = None,
        session: requests.Session | None = None,
    ):
        if not api_key:
            raise ValueError("api_key must not be empty")
        self.settings = settings or Settings(api_key=api_key)
        self.session = session or requests.Session()
        self.session.headers.update({"api-subscription-key": api_key})

    @classmethod
    def from_env(cls) -> Sarvam:
        settings = Settings.from_env()
        return cls(settings.require_api_key(), settings=settings)

    @classmethod
    def from_settings(cls, settings: Settings) -> Sarvam:
        return cls(settings.require_api_key(), settings=settings)

    def _post(self, path: str, operation: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self.settings.base_url}/{path}"
        try:
            response = self.session.post(url, timeout=self.settings.timeout, **kwargs)
        except requests.RequestException as exc:
            raise SarvamError(f"Sarvam {operation} request failed: {exc}") from exc
        if response.status_code != 200:
            # The response body never contains the API key, so it is safe to surface.
            raise SarvamError(
                f"Sarvam {operation} failed with HTTP {response.status_code}: {response.text[:300]}"
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise SarvamError(f"Sarvam {operation} returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise SarvamError(f"Sarvam {operation} returned an unexpected payload")
        return payload

    def answer(self, context: str, question: Question, description: str) -> Answer:
        """Answer ``question`` using ``context`` via the text-analytics endpoint."""
        questions = [
            {
                "id": str(question.id),
                "text": question.question,
                "description": description,
                "type": "short answer",
                "properties": {},
            }
        ]
        payload = self._post(
            TEXT_ANALYTICS_PATH,
            "text-analytics",
            data={"text": context, "questions": json.dumps(questions)},
        )
        try:
            resp = payload["answers"][0]
            return Answer(
                question=question,
                response=str(resp["response"]),
                reasoning=str(resp.get("reasoning", "")),
                utterance=str(resp.get("utterance", "")),
            )
        except (KeyError, IndexError, TypeError) as exc:
            raise SarvamError("Sarvam text-analytics response missing 'answers'") from exc

    def tts(self, text: str) -> TTS:
        """Convert ``text`` (max 500 chars) to WAV audio bytes."""
        if not text.strip():
            raise ValueError("Cannot synthesise empty text")
        if len(text) > TTS_MAX_CHARS:
            raise ValueError(f"TTS input is {len(text)} chars; split it with chunk_text() first")
        payload = self._post(
            TTS_PATH,
            "text-to-speech",
            json={
                "inputs": [text],
                "target_language_code": self.settings.tts_language,
                "speaker": self.settings.tts_speaker,
                "pitch": 0,
                "loudness": 1.5,
                "speech_sample_rate": 8000,
                "enable_preprocessing": False,
                "model": self.settings.tts_model,
            },
        )
        try:
            audio = base64.b64decode(payload["audios"][0])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise SarvamError("Sarvam text-to-speech response missing audio") from exc
        return TTS(audio=audio, text=text)

    def stt(self, audio: bytes) -> STT:
        """Transcribe (and translate to English) WAV ``audio``."""
        payload = self._post(
            STT_PATH,
            "speech-to-text",
            files={"file": ("recording.wav", audio, "audio/wav")},
        )
        try:
            return STT(
                text=str(payload["transcript"]),
                lang_code=str(payload.get("language_code") or ""),
            )
        except KeyError as exc:
            raise SarvamError("Sarvam speech-to-text response missing transcript") from exc
