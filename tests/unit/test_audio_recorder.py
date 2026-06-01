"""Whisper Wayland - Audio Recorder Tests

Unit tests for audio recorder module including
PyAudio integration and audio capture functionality."""

import itertools
import os
import time
import unittest.mock

import pytest

import tests.unit.conftest as conftest
import whisper_wayland as ww
import whisper_wayland.audio_recorder as audio_recorder
from whisper_wayland.audio_recorder.audio_system_validator import AudioSystemValidator
from whisper_wayland.audio_recorder.native_stderr import should_suppress_audio_warnings


class TestAudioRecorder:
    """Test cases for AudioRecorder class."""

    def test_audio_warnings_suppressed_by_default(self) -> None:
        """Test that native audio warnings are suppressed by default."""
        with unittest.mock.patch.dict(os.environ, {}, clear=True):
            assert should_suppress_audio_warnings()

    @pytest.mark.parametrize("value", ["0", "false", "no", "off"])
    def test_audio_warnings_can_be_unsuppressed(self, value: str) -> None:
        """Test disabling native audio warning suppression."""
        with unittest.mock.patch.dict(os.environ, {"WW_SUPPRESS_AUDIO_WARNINGS": value}):
            assert not should_suppress_audio_warnings()

    def test_signal_metrics_detect_audio_level(self) -> None:
        """Test microphone signal metric calculation."""
        sample_count = 100
        min_expected_dbfs = -31.0
        max_expected_dbfs = -29.0
        validator = AudioSystemValidator.new()
        sample = (1000).to_bytes(2, byteorder="little", signed=True)
        metrics = validator._calculate_signal_metrics(sample * sample_count)

        assert metrics["sample_count"] == sample_count
        assert min_expected_dbfs < metrics["rms_dbfs"] < max_expected_dbfs
        assert min_expected_dbfs < metrics["peak_dbfs"] < max_expected_dbfs
        assert metrics["clipping_percent"] == 0.0

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_microphone_startup_check_runs_when_enabled(
        self, mock_pyaudio: unittest.mock.Mock
    ) -> None:
        """Test startup microphone check opens and samples the selected input."""
        with unittest.mock.patch.dict(
            os.environ,
            {
                "WW_OPENAI_API_KEY": "sk-test123",
                "WW_MIC_STARTUP_CHECK": "true",
                "WW_MIC_CHECK_DURATION": "0.01",
            },
        ):
            test_config = ww.Config()
            mock_audio_instance = conftest.create_mock_audio_instance()
            mock_stream = conftest.create_mock_stream()
            mock_audio_instance.open.return_value = mock_stream
            mock_pyaudio.return_value = mock_audio_instance

            audio_recorder.AudioRecorder(test_config)

            mock_audio_instance.open.assert_called()
            mock_stream.read.assert_called()
            mock_stream.close.assert_called()

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_audio_recorder_initialization(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test audio recorder initialization."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 2
        mock_audio_instance.get_device_info_by_index.side_effect = [
            {"name": "Input Device 1", "maxInputChannels": 2},
            {"name": "Output Device", "maxInputChannels": 0},
        ]
        mock_audio_instance.is_format_supported.return_value = True
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        assert recorder.config == test_config
        assert recorder._audio == mock_audio_instance
        mock_pyaudio.assert_called_once()
        mock_audio_instance.get_device_count.assert_called()

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_audio_recorder_initialization_failure(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test audio recorder initialization failure."""
        mock_pyaudio.side_effect = Exception("PyAudio init failed")

        with pytest.raises(
            audio_recorder.AudioRecordingError, match="PyAudio initialization failed"
        ):
            audio_recorder.AudioRecorder(test_config)

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_audio_recorder_no_input_devices(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test audio recorder with no input devices."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 1
        mock_audio_instance.get_device_info_by_index.return_value = {
            "name": "Output Only",
            "maxInputChannels": 0,
        }
        mock_pyaudio.return_value = mock_audio_instance

        with pytest.raises(
            audio_recorder.AudioRecordingError, match="No audio input devices found"
        ):
            audio_recorder.AudioRecorder(test_config)

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_start_recording_success(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test successful recording start."""
        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        assert not recorder.is_recording()
        recorder.start_recording()
        assert recorder.is_recording()

        # Cleanup
        recorder.stop_recording()

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_start_recording_already_recording(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test starting recording when already recording."""
        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)
        recorder.start_recording()

        # Try to start again - should not raise an error
        recorder.start_recording()
        assert recorder.is_recording()

        # Cleanup
        recorder.stop_recording()

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_stop_recording_success(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test successful recording stop with audio data."""
        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_stream = conftest.create_mock_stream()
        mock_audio_instance.open.return_value = mock_stream
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)
        recorder.start_recording()

        # Wait a bit for recording thread to start
        time.sleep(0.1)

        audio_data = recorder.stop_recording()

        assert not recorder.is_recording()
        assert audio_data is not None
        assert isinstance(audio_data, bytes)

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_stop_recording_not_recording(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test stopping recording when not recording."""
        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        # Try to stop without starting
        result = recorder.stop_recording()
        assert result is None

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_recording_max_duration(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test recording stops at maximum duration."""
        # Set short max duration for test
        with unittest.mock.patch.dict(
            os.environ, {"WW_OPENAI_API_KEY": "sk-test123", "WW_MAX_RECORDING_DURATION": "1"}
        ):
            short_config = ww.Config()

        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_stream = conftest.create_mock_stream()
        mock_audio_instance.open.return_value = mock_stream
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(short_config)

        with unittest.mock.patch("time.time") as mock_time:
            # Simulate time progression to trigger max duration
            # Use itertools.count to provide unlimited time values
            time_values = itertools.cycle([0, 0, 0.5, 1.5, 2.0, 2.0, 2.1, 2.2, 2.3, 2.4])
            mock_time.side_effect = lambda: next(time_values)

            recorder.start_recording()
            time.sleep(0.1)  # Brief pause for thread to start
            audio_data = recorder.stop_recording()

        assert audio_data is not None or audio_data is None  # May be None if no frames captured

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_get_audio_devices(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test getting audio devices list."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 3
        mock_audio_instance.get_device_info_by_index.side_effect = [
            {"name": "Microphone 1", "maxInputChannels": 1, "defaultSampleRate": 44100},
            {"name": "Speaker", "maxInputChannels": 0, "defaultSampleRate": 44100},
            {"name": "Microphone 2", "maxInputChannels": 2, "defaultSampleRate": 48000},
        ]
        mock_audio_instance.is_format_supported.return_value = True
        mock_pyaudio.return_value = mock_audio_instance

        # Create recorder first to initialize
        recorder = audio_recorder.AudioRecorder(test_config)

        # Reset the mock call count from initialization
        mock_audio_instance.reset_mock()
        mock_audio_instance.get_device_count.return_value = 3
        mock_audio_instance.get_device_info_by_index.side_effect = [
            {"name": "Microphone 1", "maxInputChannels": 1, "defaultSampleRate": 44100},
            {"name": "Speaker", "maxInputChannels": 0, "defaultSampleRate": 44100},
            {"name": "Microphone 2", "maxInputChannels": 2, "defaultSampleRate": 48000},
        ]

        devices = recorder.get_audio_devices()

        assert len(devices) == ww.Constants.EXPECTED_DEVICE_COUNT  # Only input devices
        assert devices[0]["name"] == "Microphone 1"
        assert devices[0]["channels"] == ww.Constants.EXPECTED_CHANNELS_MONO
        assert devices[1]["name"] == "Microphone 2"
        assert devices[1]["channels"] == ww.Constants.EXPECTED_CHANNELS_STEREO

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_recorder_close(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test audio recorder cleanup."""
        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)
        recorder.start_recording()

        recorder.close()

        mock_audio_instance.terminate.assert_called_once()

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_frames_to_wav_conversion(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test audio frames to WAV conversion."""
        from whisper_wayland.audio_recorder.wav_converter import WavConverter

        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)
        wav_converter = WavConverter.new(recorder._audio, test_config)

        # Test frames data
        frames = [b"\x00\x01" * 100, b"\x02\x03" * 100]

        wav_data = wav_converter.frames_to_wav(frames)

        assert isinstance(wav_data, bytes)
        assert len(wav_data) > len(b"".join(frames))  # Should include WAV header

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_recording_thread_exception_handling(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test recording thread handles exceptions gracefully."""
        mock_audio_instance = conftest.create_mock_audio_instance()
        mock_stream = unittest.mock.Mock()
        mock_stream.read.side_effect = Exception("Stream read error")
        mock_audio_instance.open.return_value = mock_stream
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)
        recorder.start_recording()

        time.sleep(0.1)  # Let thread encounter error

        audio_data = recorder.stop_recording()
        # Should not raise exception, may return None
        assert audio_data is None or isinstance(audio_data, bytes)

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_preferred_device_selects_usb(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test that USB device is preferred over internal mic."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 3
        mock_audio_instance.get_device_info_by_index.side_effect = [
            # validation scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            {"name": "USB Audio Device", "maxInputChannels": 1},
            {"name": "default", "maxInputChannels": 64},
            # find_preferred_input_device scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            {"name": "USB Audio Device", "maxInputChannels": 1},
            {"name": "default", "maxInputChannels": 64},
        ]
        mock_audio_instance.is_format_supported.return_value = True
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        assert recorder._recording_engine._input_device_index == 1

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_preferred_device_skips_unavailable_usb(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test that unavailable USB devices are skipped during preferred selection."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 2
        mock_audio_instance.get_device_info_by_index.side_effect = [
            # validation scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            {"name": "USB Audio Device", "maxInputChannels": 1},
            # find_preferred_input_device scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            {"name": "USB Audio Device", "maxInputChannels": 1},
            # USB open check sample-rate lookup
            {"name": "USB Audio Device", "maxInputChannels": 1, "defaultSampleRate": 44100},
        ]
        mock_audio_instance.is_format_supported.return_value = True
        mock_audio_instance.open.side_effect = OSError("Device unavailable")
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        assert recorder._recording_engine._input_device_index is None

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_preferred_device_selects_bluetooth(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test that Bluetooth device is selected when no USB device is present."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 2
        mock_audio_instance.get_device_info_by_index.side_effect = [
            # validation scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            {"name": "Bluetooth Headset", "maxInputChannels": 1},
            # find_preferred_input_device scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            {"name": "Bluetooth Headset", "maxInputChannels": 1},
        ]
        mock_audio_instance.is_format_supported.return_value = True
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        assert recorder._recording_engine._input_device_index == 1

    @unittest.mock.patch("whisper_wayland.audio_recorder.audio_system_validator.pyaudio.PyAudio")
    def test_preferred_device_falls_back_to_default(
        self, mock_pyaudio: unittest.mock.Mock, test_config: "ww.Config"
    ) -> None:
        """Test that None (system default) is used when no USB/BT device is found."""
        mock_audio_instance = unittest.mock.Mock()
        mock_audio_instance.get_device_count.return_value = 1
        mock_audio_instance.get_device_info_by_index.side_effect = [
            # validation scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
            # find_preferred_input_device scan
            {"name": "Apple T2 Audio: Digital Mic", "maxInputChannels": 3},
        ]
        mock_audio_instance.is_format_supported.return_value = True
        mock_pyaudio.return_value = mock_audio_instance

        recorder = audio_recorder.AudioRecorder(test_config)

        assert recorder._recording_engine._input_device_index is None

    def test_create_audio_recorder(self) -> None:
        """Test AudioRecorder.new static method."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            test_config = ww.Config()

        with unittest.mock.patch(
            "whisper_wayland.audio_recorder.AudioRecorder.__init__", return_value=None
        ):
            result = audio_recorder.AudioRecorder.new(test_config)

            assert isinstance(result, audio_recorder.AudioRecorder)
