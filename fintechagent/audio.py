"""Microphone recording and speaker playback.

``sounddevice`` needs the PortAudio system library, so it is imported lazily:
the rest of the package (and text mode) works on machines without audio.
"""

from __future__ import annotations

import logging
import threading
import wave
from io import BytesIO
from types import ModuleType
from typing import Any, cast

import numpy as np
from scipy.io.wavfile import write as write_wav

from .errors import AudioError

logger = logging.getLogger(__name__)

RECORD_SAMPLE_RATE = 16_000
_DTYPES = {1: np.uint8, 2: np.int16, 4: np.int32}


def _sounddevice() -> ModuleType:
    try:
        import sounddevice
    except (OSError, ImportError) as exc:  # PortAudio or package missing
        raise AudioError(
            "Audio is unavailable: the PortAudio library was not found. Install it "
            "(e.g. `brew install portaudio` or `sudo apt install libportaudio2`) "
            "or run with --text to chat via the keyboard."
        ) from exc
    return cast(ModuleType, sounddevice)


def decode_wav(audio: bytes) -> tuple[np.ndarray[Any, Any], int]:
    """Decode WAV bytes into a ``(samples, sample_rate)`` pair."""
    try:
        with wave.open(BytesIO(audio)) as wav:
            sample_rate = wav.getframerate()
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError) as exc:
        raise AudioError(f"Invalid WAV audio: {exc}") from exc
    if width not in _DTYPES:
        raise AudioError(f"Unsupported WAV sample width: {width} bytes")
    samples: np.ndarray[Any, Any] = np.frombuffer(frames, dtype=_DTYPES[width])
    if channels > 1:
        samples = samples.reshape(-1, channels)
    return samples, sample_rate


def encode_wav(samples: np.ndarray[Any, Any], sample_rate: int = RECORD_SAMPLE_RATE) -> bytes:
    """Encode samples as WAV bytes."""
    buffer = BytesIO()
    write_wav(buffer, sample_rate, samples)
    return buffer.getvalue()


class PlayAudio:
    """Plays WAV bytes and records microphone input until Enter is pressed."""

    @staticmethod
    def ensure_available() -> None:
        """Raise :class:`AudioError` early if audio devices cannot be used."""
        _sounddevice()

    def play(self, audio: bytes) -> None:
        samples, sample_rate = decode_wav(audio)
        sd = _sounddevice()
        sd.play(samples, samplerate=sample_rate)
        sd.wait()

    def record(self, prompt: str = "Recording... press Enter to stop.\n") -> bytes:
        sd = _sounddevice()
        stop = threading.Event()
        chunks: list[np.ndarray[Any, Any]] = []
        errors: list[BaseException] = []

        def worker() -> None:
            try:
                with sd.InputStream(
                    samplerate=RECORD_SAMPLE_RATE, channels=1, dtype=np.int16
                ) as stream:
                    while not stop.is_set():
                        data, _ = stream.read(RECORD_SAMPLE_RATE // 10)
                        chunks.append(data)
            except Exception as exc:  # surfaced on the main thread below
                errors.append(exc)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            input(prompt)
        except EOFError:
            pass
        finally:
            stop.set()
            thread.join(timeout=2)
        if errors:
            raise AudioError(f"Recording failed: {errors[0]}") from errors[0]
        if not chunks:
            raise AudioError("No audio was captured from the microphone.")
        return encode_wav(np.concatenate(chunks, axis=0))
