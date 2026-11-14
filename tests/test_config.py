import pytest

from fintechagent import ConfigError, Settings
from fintechagent.config import DEFAULT_DB_PATH, DEFAULT_TTS_MODEL


def test_defaults():
    s = Settings.from_env({})
    assert s.api_key is None
    assert s.db_path == DEFAULT_DB_PATH
    assert s.tts_model == DEFAULT_TTS_MODEL


def test_overrides():
    s = Settings.from_env(
        {
            "SARVAM_AI_API": " key ",
            "DB_URL": "data/x.sqlite",
            "SARVAM_BASE_URL": "https://example.test/",
            "SARVAM_TIMEOUT": "5",
            "SARVAM_TTS_SPEAKER": "anushka",
        }
    )
    assert s.api_key == "key"
    assert s.db_path == "data/x.sqlite"
    assert s.base_url == "https://example.test"
    assert s.timeout == 5.0
    assert s.tts_speaker == "anushka"


@pytest.mark.parametrize("value", ["abc", "0", "-1"])
def test_invalid_timeout(value):
    with pytest.raises(ConfigError):
        Settings.from_env({"SARVAM_TIMEOUT": value})


@pytest.mark.parametrize("key", [None, "", "<Get it from the dashboard>"])
def test_require_api_key_missing(key):
    with pytest.raises(ConfigError, match="SARVAM_AI_API"):
        Settings(api_key=key).require_api_key()


def test_require_api_key_present():
    assert Settings(api_key="k").require_api_key() == "k"
