"""Opt-in tests against the real Sarvam API: `uv run pytest -m live`."""

import os

import pytest

from fintechagent import Sarvam
from fintechagent.sarvam import Question
from tests.conftest import ROOT

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("SARVAM_AI_API"), reason="SARVAM_AI_API not set"),
]


def test_live_answer():
    answer = Sarvam.from_env().answer(
        "The World Safari card has zero forex markup.",
        Question("What is the forex markup?", 1),
        "Answer from the context.",
    )
    assert answer.response


def test_live_tts():
    assert Sarvam.from_env().tts("Hello from BulBul").audio.startswith(b"RIFF")


def test_live_stt():
    assert Sarvam.from_env().stt((ROOT / "sample.wav").read_bytes()).text
