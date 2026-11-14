"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from .errors import ConfigError

DEFAULT_SARVAM_BASE_URL = "https://api.sarvam.ai"
DEFAULT_DB_PATH = "./bank.sqlite"
DEFAULT_PRODUCTS_DIR = "./products"
DEFAULT_TTS_MODEL = "bulbul:v1"
DEFAULT_TTS_SPEAKER = "meera"
DEFAULT_TTS_LANGUAGE = "en-IN"
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class Settings:
    """All tunable settings for the agent."""

    api_key: str | None = None
    base_url: str = DEFAULT_SARVAM_BASE_URL
    db_path: str = DEFAULT_DB_PATH
    products_dir: str = DEFAULT_PRODUCTS_DIR
    tts_model: str = DEFAULT_TTS_MODEL
    tts_speaker: str = DEFAULT_TTS_SPEAKER
    tts_language: str = DEFAULT_TTS_LANGUAGE
    timeout: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Settings:
        """Build settings from ``env`` (defaults to ``os.environ``)."""
        env = os.environ if env is None else env

        def get(name: str, default: str) -> str:
            value = env.get(name, "").strip()
            return value or default

        raw_timeout = get("SARVAM_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS))
        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ConfigError(
                f"SARVAM_TIMEOUT must be a number of seconds, got {raw_timeout!r}"
            ) from exc
        if timeout <= 0:
            raise ConfigError("SARVAM_TIMEOUT must be greater than zero")

        api_key = env.get("SARVAM_AI_API", "").strip() or None
        return cls(
            api_key=api_key,
            base_url=get("SARVAM_BASE_URL", DEFAULT_SARVAM_BASE_URL).rstrip("/"),
            db_path=get("DB_URL", DEFAULT_DB_PATH),
            products_dir=get("PRODUCTS_DIR", DEFAULT_PRODUCTS_DIR),
            tts_model=get("SARVAM_TTS_MODEL", DEFAULT_TTS_MODEL),
            tts_speaker=get("SARVAM_TTS_SPEAKER", DEFAULT_TTS_SPEAKER),
            tts_language=get("SARVAM_TTS_LANGUAGE", DEFAULT_TTS_LANGUAGE),
            timeout=timeout,
        )

    def require_api_key(self) -> str:
        """Return the API key or raise a helpful :class:`ConfigError`."""
        if not self.api_key or self.api_key.startswith("<"):
            raise ConfigError(
                "SARVAM_AI_API is not set. Copy .env.example to .env, add your key "
                "from https://dashboard.sarvam.ai/ and load it (see README)."
            )
        return self.api_key
