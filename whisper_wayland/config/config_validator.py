"""Whisper Wayland - Config Validator

Configuration validation and requirement checking.
"""

import logging
import typing

_logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""

    pass


class ConfigValidator:
    """Validates configuration requirements and constraints."""

    def __init__(self) -> None:
        """Initialize config validator."""
        pass

    def validate_required_config(self, config_instance: typing.Any) -> None:
        """Validate that all required configuration is present.

        Args:
            config_instance: Configuration instance to validate

        Raises:
            ConfigValidationError: If required configuration is missing
        """
        required_vars = ["OPENAI_API_KEY"]
        missing_vars = []

        for var in required_vars:
            if not getattr(config_instance, var.lower(), None):
                missing_vars.append(var)

        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            _logger.error(error_msg)
            raise ConfigValidationError(error_msg)

    def get_safe_config_summary(self, config_instance: typing.Any) -> dict:
        """Get configuration summary with sensitive data masked.

        Args:
            config_instance: Configuration instance

        Returns:
            Dictionary with configuration summary
        """
        return {
            "openai_api_key": "***" if config_instance.openai_api_key else None,
            "whisper_model": config_instance.whisper_model,
            "audio_sample_rate": config_instance.audio_sample_rate,
            "audio_chunk_size": config_instance.audio_chunk_size,
            "max_recording_duration": config_instance.max_recording_duration,
            "mic_startup_check": config_instance.mic_startup_check,
            "mic_check_duration": config_instance.mic_check_duration,
            "log_level": config_instance.log_level,
            "hotkey": config_instance.hotkey,
            "text_insertion_delay": config_instance.text_insertion_delay,
            "text_insertion_method": config_instance.text_insertion_method,
        }

    @staticmethod
    def new() -> "ConfigValidator":
        """Create config validator instance.

        Returns:
            ConfigValidator instance
        """
        return ConfigValidator()
