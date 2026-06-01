"""Whisper Wayland - Configuration Tests

Unit tests for configuration module functionality including
environment variable loading and validation."""

import os
import tempfile
import unittest.mock

import pytest

import whisper_wayland as ww


class TestConfig:
    """Test cases for Config class."""

    def test_config_initialization_with_defaults(self) -> None:
        """Test config initialization with default values."""
        with tempfile.NamedTemporaryFile(mode="w") as empty_env:
            with unittest.mock.patch.dict(
                os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}, clear=True
            ):
                test_config = ww.Config(empty_env.name)

                assert test_config.openai_api_key == "sk-test123"
                assert test_config.whisper_model == "base"
                assert test_config.audio_sample_rate == ww.Constants.DEFAULT_SAMPLE_RATE
                assert test_config.audio_chunk_size == ww.Constants.DEFAULT_CHUNK_SIZE
                assert test_config.max_recording_duration == ww.Constants.DEFAULT_RECORDING_DURATION
                assert not test_config.mic_startup_check
                assert test_config.mic_check_duration == ww.Constants.DEFAULT_MIC_CHECK_DURATION
                assert test_config.log_level == "INFO"
                assert test_config.hotkey == "ctrl+compose"

    def test_config_missing_required_api_key(self) -> None:
        """Test config fails when required API key is missing."""
        # Temporarily remove API key to test validation
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": ""}):
            with pytest.raises(ww.ConfigError, match="WW_OPENAI_API_KEY"):
                ww.Config()

    def test_config_empty_api_key(self) -> None:
        """Test config fails when API key is empty."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": ""}):
            with pytest.raises(ww.ConfigError, match="WW_OPENAI_API_KEY"):
                ww.Config()

    def test_config_custom_values(self) -> None:
        """Test config with custom environment values."""
        env_vars = {
            "WW_OPENAI_API_KEY": "sk-custom123",
            "WW_WHISPER_MODEL": "large",
            "WW_AUDIO_SAMPLE_RATE": "44100",
            "WW_AUDIO_CHUNK_SIZE": "2048",
            "WW_MAX_RECORDING_DURATION": "60",
            "WW_MIC_STARTUP_CHECK": "true",
            "WW_MIC_CHECK_DURATION": "0.5",
            "WW_LOG_LEVEL": "DEBUG",
            "WW_HOTKEY": "alt+space",
        }
        expected_mic_check_duration = 0.5

        with unittest.mock.patch.dict(os.environ, env_vars):
            test_config = ww.Config()

            assert test_config.openai_api_key == "sk-custom123"
            assert test_config.whisper_model == "large"
            assert test_config.audio_sample_rate == ww.Constants.HIGH_QUALITY_SAMPLE_RATE
            assert test_config.audio_chunk_size == ww.Constants.LARGE_CHUNK_SIZE
            assert test_config.max_recording_duration == ww.Constants.LONG_RECORDING_DURATION
            assert test_config.mic_startup_check
            assert test_config.mic_check_duration == expected_mic_check_duration
            assert test_config.log_level == "DEBUG"
            assert test_config.hotkey == "alt+space"

    def test_config_invalid_numeric_values(self) -> None:
        """Test config validation of numeric values."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            # Invalid sample rate
            with unittest.mock.patch.dict(os.environ, {"WW_AUDIO_SAMPLE_RATE": "invalid"}):
                with pytest.raises(ww.ConfigError, match="WW_AUDIO_SAMPLE_RATE"):
                    ww.Config()

            # Negative sample rate
            with unittest.mock.patch.dict(os.environ, {"WW_AUDIO_SAMPLE_RATE": "-1000"}):
                with pytest.raises(ww.ConfigError, match="WW_AUDIO_SAMPLE_RATE"):
                    ww.Config()

            # Invalid chunk size
            with unittest.mock.patch.dict(os.environ, {"WW_AUDIO_CHUNK_SIZE": "not_a_number"}):
                with pytest.raises(ww.ConfigError, match="WW_AUDIO_CHUNK_SIZE"):
                    ww.Config()

            # Invalid recording duration
            with unittest.mock.patch.dict(os.environ, {"WW_MAX_RECORDING_DURATION": "zero"}):
                with pytest.raises(ww.ConfigError, match="WW_MAX_RECORDING_DURATION"):
                    ww.Config()

            # Invalid microphone check duration
            with unittest.mock.patch.dict(os.environ, {"WW_MIC_CHECK_DURATION": "invalid"}):
                with pytest.raises(ww.ConfigError, match="WW_MIC_CHECK_DURATION"):
                    ww.Config()

    def test_config_invalid_log_level(self) -> None:
        """Test config handles invalid log levels gracefully."""
        with unittest.mock.patch.dict(
            os.environ, {"WW_OPENAI_API_KEY": "sk-test123", "WW_LOG_LEVEL": "INVALID_LEVEL"}
        ):
            test_config = ww.Config()
            assert test_config.log_level == "INFO"  # Should fallback to default

    def test_config_text_insertion_delay(self) -> None:
        """Test text insertion delay configuration."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            # Default value
            test_config = ww.Config()
            assert test_config.text_insertion_delay == ww.Constants.DEFAULT_TEXT_INSERTION_DELAY

            # Custom value
            with unittest.mock.patch.dict(os.environ, {"WW_TEXT_INSERTION_DELAY": "0.5"}):
                test_config = ww.Config()
                assert test_config.text_insertion_delay == ww.Constants.CUSTOM_TEXT_INSERTION_DELAY

            # Invalid value
            with unittest.mock.patch.dict(os.environ, {"WW_TEXT_INSERTION_DELAY": "invalid"}):
                with pytest.raises(ww.ConfigError, match="WW_TEXT_INSERTION_DELAY"):
                    ww.Config()

            # Negative value
            with unittest.mock.patch.dict(os.environ, {"WW_TEXT_INSERTION_DELAY": "-1.0"}):
                with pytest.raises(ww.ConfigError, match="WW_TEXT_INSERTION_DELAY"):
                    ww.Config()

    def test_config_text_insertion_method(self) -> None:
        """Test text insertion method configuration."""
        # Temporarily remove WW_TEXT_INSERTION_METHOD to test default
        old_method = os.environ.pop("WW_TEXT_INSERTION_METHOD", None)
        try:
            with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
                # Default value (per config.py line 203)
                test_config = ww.Config()
                assert test_config.text_insertion_method == "ydotool"

                # Valid custom value
                with unittest.mock.patch.dict(os.environ, {"WW_TEXT_INSERTION_METHOD": "xdotool"}):
                    test_config = ww.Config()
                    assert test_config.text_insertion_method == "xdotool"
        finally:
            # Restore WW_TEXT_INSERTION_METHOD if it existed
            if old_method:
                os.environ["WW_TEXT_INSERTION_METHOD"] = old_method

        # Test after restoring to ensure proper cleanup
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            # Invalid value (should fallback to default)
            with unittest.mock.patch.dict(
                os.environ, {"WW_TEXT_INSERTION_METHOD": "invalid_method"}
            ):
                test_config = ww.Config()
                assert (
                    test_config.text_insertion_method == "ydotool"
                )  # Fallback per config.py line 210

    def test_config_load_env_file(self) -> None:
        """Test loading configuration from .env file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("WW_OPENAI_API_KEY=sk-envfile123\n")
            f.write("WW_WHISPER_MODEL=small\n")
            f.write("WW_LOG_LEVEL=DEBUG\n")
            env_file_path = f.name

        # Temporarily remove environment variables that would override .env file
        old_api_key = os.environ.pop("WW_OPENAI_API_KEY", None)
        old_model = os.environ.pop("WW_WHISPER_MODEL", None)
        old_log_level = os.environ.pop("WW_LOG_LEVEL", None)

        try:
            test_config = ww.Config(env_file_path)
            assert test_config.openai_api_key == "sk-envfile123"
            assert test_config.whisper_model == "small"
            assert test_config.log_level == "DEBUG"
        finally:
            # Restore environment variables
            if old_api_key:
                os.environ["WW_OPENAI_API_KEY"] = old_api_key
            if old_model:
                os.environ["WW_WHISPER_MODEL"] = old_model
            if old_log_level:
                os.environ["WW_LOG_LEVEL"] = old_log_level
            os.unlink(env_file_path)

    def test_config_load_nonexistent_env_file(self) -> None:
        """Test handling of nonexistent .env file."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            # Should not raise an error, just log a warning
            test_config = ww.Config("/nonexistent/file.env")
            assert test_config.openai_api_key == "sk-test123"

    def test_config_safe_summary(self) -> None:
        """Test safe configuration summary masks sensitive data."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-sensitive123"}):
            test_config = ww.Config()
            summary = test_config._get_safe_config_summary()

            assert summary["openai_api_key"] == "***"
            assert summary["whisper_model"] == "base"
            assert "sk-sensitive123" not in str(summary)

    def test_config_get_static_method(self) -> None:
        """Test Config.get static method."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            test_config = ww.Config.get()
            assert isinstance(test_config, ww.Config)
            assert test_config.openai_api_key == "sk-test123"

    def test_config_get_with_file(self) -> None:
        """Test Config.get with environment file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("WW_OPENAI_API_KEY=sk-filetest123\n")
            env_file_path = f.name

        # Temporarily remove environment variable to test .env file loading
        old_api_key = os.environ.pop("WW_OPENAI_API_KEY", None)

        try:
            test_config = ww.Config.get(env_file_path)
            assert test_config.openai_api_key == "sk-filetest123"
        finally:
            # Restore environment variable
            if old_api_key:
                os.environ["WW_OPENAI_API_KEY"] = old_api_key
            os.unlink(env_file_path)
