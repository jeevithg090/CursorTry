import numpy as np
import pytest

from fintechagent import AudioError
from fintechagent.audio import decode_wav, encode_wav
from tests.conftest import ROOT


def test_wav_roundtrip():
    samples = (np.sin(np.linspace(0, 10, 1600)) * 3000).astype(np.int16)
    wav = encode_wav(samples, 16_000)
    assert wav.startswith(b"RIFF")
    decoded, rate = decode_wav(wav)
    assert rate == 16_000
    np.testing.assert_array_equal(decoded, samples)


def test_decode_sample_file():
    samples, rate = decode_wav((ROOT / "sample.wav").read_bytes())
    assert rate > 0 and samples.size > 0


def test_decode_invalid():
    with pytest.raises(AudioError):
        decode_wav(b"not a wav")


class FakeStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, frames):
        return np.ones((frames, 1), dtype=np.int16), False


class FakeSoundDevice:
    InputStream = FakeStream

    def __init__(self):
        self.played = None

    def play(self, samples, samplerate):
        self.played = (samples, samplerate)

    def wait(self):
        pass


@pytest.fixture
def fake_sd(monkeypatch):
    sd = FakeSoundDevice()
    monkeypatch.setattr("fintechagent.audio._sounddevice", lambda: sd)
    return sd


def test_play_uses_decoded_samples(fake_sd):
    from fintechagent.audio import PlayAudio

    PlayAudio().play(encode_wav(np.zeros(800, dtype=np.int16), 8000))
    assert fake_sd.played[1] == 8000


def test_record_stops_on_enter(fake_sd, monkeypatch):
    import time

    from fintechagent.audio import PlayAudio

    def press_enter(_prompt):
        time.sleep(0.05)
        return ""  # a bare Enter must stop recording (used to hang)

    monkeypatch.setattr("builtins.input", press_enter)
    wav = PlayAudio().record()
    samples, rate = decode_wav(wav)
    assert rate == 16_000 and samples.size > 0


def test_missing_portaudio_is_friendly(monkeypatch):
    import sys

    from fintechagent.audio import _sounddevice

    monkeypatch.setitem(sys.modules, "sounddevice", None)
    with pytest.raises(AudioError, match="--text"):
        _sounddevice()
