"""Whisper Wayland - Config

Main configuration orchestrator that coordinates all configuration components.
"""

import logging
import typing

from whisper_wayland.config.config_validator import ConfigValidationError, ConfigValidator
from whisper_wayland.config.env_loader import EnvLoader, EnvLoaderError
from whisper_wayland.config.logging_setup import LoggingSetup
from whisper_wayland.config.property_handlers import PropertyHandlerError, PropertyHandlers

_logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration validation fails."""

    pass


class Config:
    """Configuration manager for Whisper Wayland service.

    Loads and validates all configuration from environment variables
    with reasonable defaults and comprehensive error handling.
    """

    def __init__(self, env_file: typing.Optional[str] = None) -> None:
        """Initialize configuration manager.

        Args:
            env_file: Optional path to .env file to load

        Raises:
            ConfigError: If configuration is invalid
        """
        try:
            # Initialize components
            self._env_loader = EnvLoader.new()
            self._config_validator = ConfigValidator.new()
            self._property_handlers = PropertyHandlers.new()
            self._logging_setup = LoggingSetup.new()

            # Load environment and validate
            self._env_loader.load_env_file(env_file)
            self._config_validator.validate_required_config(self)

            _logger.info("Configuration loaded successfully")
            _logger.debug(f"Configuration: {self._config_validator.get_safe_config_summary(self)}")
        except (EnvLoaderError, ConfigValidationError, PropertyHandlerError) as e:
            raise ConfigError(str(e)) from e
        except Exception as e:
            _logger.error(f"Failed to initialize configuration: {e}")
            raise ConfigError(f"Configuration initialization failed: {e}") from e

    # OpenAI Configuration
    @property
    def openai_api_key(self) -> str:
        """OpenAI API key for Whisper service."""
        return self._property_handlers.get_openai_api_key()

    @property
    def whisper_model(self) -> str:
        """Whisper model to use for transcription."""
        return self._property_handlers.get_whisper_model()

    # Audio Configuration
    @property
    def audio_sample_rate(self) -> int:
        """Audio recording sample rate in Hz."""
        return self._property_handlers.get_audio_sample_rate()

    @property
    def audio_chunk_size(self) -> int:
        """Audio buffer chunk size in samples."""
        return self._property_handlers.get_audio_chunk_size()

    @property
    def max_recording_duration(self) -> int:
        """Maximum recording duration in seconds."""
        return self._property_handlers.get_max_recording_duration()

    @property
    def mic_startup_check(self) -> str:
        """Microphone startup check mode."""
        return self._property_handlers.get_mic_startup_check()

    @property
    def mic_check_duration(self) -> float:
        """Microphone startup check duration in seconds."""
        return self._property_handlers.get_mic_check_duration()

    # Logging Configuration
    @property
    def log_level(self) -> str:
        """Logging level."""
        return self._property_handlers.get_log_level()

    # Hotkey Configuration
    @property
    def hotkey(self) -> str:
        """Push-to-talk key combination."""
        return self._property_handlers.get_hotkey()

    # Text Insertion Configuration
    @property
    def text_insertion_delay(self) -> float:
        """Delay before text insertion in seconds."""
        return self._property_handlers.get_text_insertion_delay()

    @property
    def text_insertion_method(self) -> str:
        """Text insertion method to use."""
        return self._property_handlers.get_text_insertion_method()

    def setup_logging(self, log_file: typing.Optional[str] = None) -> None:
        """Set up logging configuration for the application.

        Args:
            log_file: Optional path to log file for file logging
        """
        self._logging_setup.setup_logging(self.log_level, log_file)

    # Backward compatibility methods for tests
    def _get_safe_config_summary(self) -> dict:
        """Legacy interface for safe config summary."""
        return self._config_validator.get_safe_config_summary(self)

    def _configure_third_party_loggers(self) -> None:
        """Legacy interface for third party logger configuration."""
        self._logging_setup._configure_third_party_loggers()

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance with the given name.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Logger instance
        """
        return logging.getLogger(name)

    @staticmethod
    def get(env_file: typing.Optional[str] = None) -> "Config":
        """Get configuration instance with optional environment file.

        Args:
            env_file: Optional path to .env file

        Returns:
            Config instance

        Raises:
            ConfigError: If configuration is invalid
        """
        try:
            return Config(env_file)
        except Exception as e:
            _logger.error(f"Failed to initialize configuration: {e}")
            raise
