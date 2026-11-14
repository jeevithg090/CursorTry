"""Exception hierarchy for the fintech agent."""


class BulbulError(Exception):
    """Base class for all expected, user-facing errors."""


class ConfigError(BulbulError):
    """Configuration is missing or invalid."""


class DataError(BulbulError):
    """Customer or product data could not be loaded."""


class SarvamError(BulbulError):
    """A call to the Sarvam AI API failed."""


class AudioError(BulbulError):
    """Audio playback or recording is unavailable or failed."""
