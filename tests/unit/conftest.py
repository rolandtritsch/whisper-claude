"""Whisper Wayland - Unit Test Configuration

Pytest configuration and fixtures specifically for
unit tests of the Whisper Wayland service."""

import os
import tempfile
import typing
import unittest.mock

import pytest

import whisper_wayland as ww


@pytest.fixture(autouse=True)
def default_unit_api_key() -> typing.Generator[None, None, None]:
    """Provide a default API key for unit tests that construct Config directly."""
    with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
        yield


@pytest.fixture
def test_config() -> ww.Config:
    """Create test configuration."""
    with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
        return ww.Config()


@pytest.fixture
def test_config_with_hotkey() -> typing.Generator[ww.Config, None, None]:
    """Create test configuration with specific hotkey."""
    with unittest.mock.patch.dict(
        os.environ, {"WW_OPENAI_API_KEY": "sk-test123", "WW_HOTKEY": "ctrl+compose"}
    ):
        yield ww.Config()


@pytest.fixture
def mock_evdev_devices() -> typing.List[unittest.mock.Mock]:
    """Create mock evdev devices."""
    mock_device1 = unittest.mock.Mock()
    mock_device1.name = "Test Keyboard 1"
    mock_device1.path = "/dev/input/event0"
    mock_device1.fd = 10
    mock_device1.capabilities.return_value = {
        1: [1, 2, 3, 28, 57]  # EV_KEY with some key codes including space
    }
    mock_device1.read.return_value = []
    mock_device1.close = unittest.mock.Mock()

    mock_device2 = unittest.mock.Mock()
    mock_device2.name = "Test Keyboard 2"
    mock_device2.path = "/dev/input/event1"
    mock_device2.fd = 11
    mock_device2.capabilities.return_value = {
        1: [1, 2, 3, 28, 57]  # EV_KEY with some key codes including space
    }
    mock_device2.read.return_value = []
    mock_device2.close = unittest.mock.Mock()

    return [mock_device1, mock_device2]


@pytest.fixture
def mock_evdev(
    mock_evdev_devices: typing.List[unittest.mock.Mock],
) -> typing.Generator[unittest.mock.Mock, None, None]:
    """Mock evdev module."""
    with unittest.mock.patch("whisper_wayland.key_monitor.device_manager.evdev") as mock_evdev:
        # Mock list_devices to return device paths
        mock_evdev.list_devices.return_value = [
            "/dev/input/event0",
            "/dev/input/event1",
        ]

        # Mock InputDevice constructor to return our mock devices
        mock_evdev.InputDevice.side_effect = mock_evdev_devices

        # Mock ecodes constants
        mock_evdev.ecodes.EV_KEY = 1
        mock_evdev.ecodes.KEY_SPACE = 57
        mock_evdev.ecodes.KEY_ENTER = 28
        mock_evdev.ecodes.KEY_COMPOSE = 127

        yield mock_evdev


@pytest.fixture
def mock_shutil_which() -> typing.Generator[unittest.mock.Mock, None, None]:
    """Mock shutil.which to control available tools."""
    with unittest.mock.patch(
        "whisper_wayland.text_inserter.capability_tester.shutil.which"
    ) as mock:
        # By default, make ydotool available
        mock.side_effect = lambda tool: tool == "ydotool"
        yield mock


@pytest.fixture
def test_config_text_inserter() -> ww.Config:
    """Create test configuration for text inserter with specific settings."""
    with unittest.mock.patch.dict(
        os.environ,
        {
            "WW_OPENAI_API_KEY": "sk-test123",
            "WW_TEXT_INSERTION_METHOD": "ydotool",
            "WW_TEXT_INSERTION_DELAY": "0.1",
        },
    ):
        return ww.Config()


@pytest.fixture
def text_inserter(
    test_config_text_inserter: ww.Config, mock_shutil_which: unittest.mock.Mock
) -> typing.Any:
    """Create text inserter with mocked dependencies."""
    import whisper_wayland.text_inserter as text_inserter

    return text_inserter.TextInserter(test_config_text_inserter)


def create_mock_audio_instance() -> unittest.mock.Mock:
    """Create mock PyAudio instance with required methods."""
    mock_audio = unittest.mock.Mock()
    mock_audio.get_device_count.return_value = 1
    mock_audio.get_device_info_by_index.return_value = {
        "name": "Test Microphone",
        "maxInputChannels": 1,
        "defaultSampleRate": 44100,
    }
    mock_audio.is_format_supported.return_value = True
    mock_audio.get_sample_size.return_value = 2
    return mock_audio


def create_mock_stream() -> unittest.mock.Mock:
    """Create mock audio stream with required methods."""
    mock_stream = unittest.mock.Mock()
    mock_stream.read.return_value = b"\x00\x01" * 512  # Mock audio data
    return mock_stream


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
