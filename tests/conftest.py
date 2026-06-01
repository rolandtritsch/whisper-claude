"""Whisper Wayland - Pytest Configuration

Pytest configuration and fixtures for testing the
Whisper Wayland voice transcription service."""

import os
import tempfile
import typing

import dotenv
import pytest

import whisper_wayland as ww

dotenv.load_dotenv()


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )


@pytest.fixture(autouse=True)
def clean_environment() -> typing.Generator[None, None, None]:
    """Clean environment for each test."""
    # Store original environment
    original_env = dict(os.environ)

    # Ensure clean test environment
    test_env_vars = [
        "WW_OPENAI_API_KEY",
        "WW_WHISPER_MODEL",
        "WW_AUDIO_SAMPLE_RATE",
        "WW_AUDIO_CHUNK_SIZE",
        "WW_MAX_RECORDING_DURATION",
        "WW_MIC_STARTUP_CHECK",
        "WW_MIC_CHECK_DURATION",
        "WW_LOG_LEVEL",
        "WW_HOTKEY",
        "WW_TEXT_INSERTION_DELAY",
        "WW_TEXT_INSERTION_METHOD",
        "WW_SUPPRESS_AUDIO_WARNINGS",
        "WW_ENV_FILE",
    ]

    yield

    # Restore original environment
    for key in test_env_vars:
        if key in os.environ:
            if key in original_env:
                os.environ[key] = original_env[key]
            else:
                del os.environ[key]
        elif key in original_env:
            os.environ[key] = original_env[key]


@pytest.fixture
def test_config() -> typing.Generator[ww.Config, None, None]:
    """Provide test configuration loaded from .env file."""
    # Ensure .env file is loaded and API key is available
    if not os.getenv("WW_OPENAI_API_KEY"):
        pytest.skip(
            "WW_OPENAI_API_KEY not found in environment. Ensure .env file is properly configured."
        )

    yield ww.Config()


@pytest.fixture
def temp_transcription_file() -> typing.Generator[str, None, None]:
    """Create temporary transcription file for tests."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        temp_file = f.name

    yield temp_file

    # Cleanup
    try:
        os.unlink(temp_file)
    except OSError:
        pass  # File may have been deleted by test
