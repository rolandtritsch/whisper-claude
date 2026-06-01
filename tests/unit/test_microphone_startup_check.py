"""Unit tests for startup microphone checks."""

import types
import unittest.mock

from whisper_wayland.application.microphone_startup_check import MicrophoneStartupCheck


class TestMicrophoneStartupCheck:
    """Test cases for startup microphone check orchestration."""

    def test_auto_mode_runs_signal_check(self) -> None:
        """Test auto mode runs the recorder signal check."""
        config = types.SimpleNamespace(mic_startup_check="auto")
        audio_recorder = unittest.mock.Mock()
        transcription_client = unittest.mock.Mock()

        MicrophoneStartupCheck(config, audio_recorder, transcription_client).run()

        audio_recorder.check_microphone_signal.assert_called_once_with()
        transcription_client.transcribe_audio.assert_not_called()

    def test_manual_mode_accepts_counting_transcription(self) -> None:
        """Test manual mode records and accepts a recognized count."""
        config = types.SimpleNamespace(mic_startup_check="manual", mic_check_duration=0.1)
        audio_recorder = unittest.mock.Mock()
        audio_recorder.stop_recording.return_value = b"audio"
        transcription_client = unittest.mock.Mock()
        transcription_client.transcribe_audio.return_value = (
            "one two three four five six seven eight nine ten"
        )

        with unittest.mock.patch("builtins.input", return_value=""):
            with unittest.mock.patch("time.sleep"):
                MicrophoneStartupCheck(config, audio_recorder, transcription_client).run()

        audio_recorder.start_recording.assert_called_once_with()
        audio_recorder.stop_recording.assert_called_once_with()
        transcription_client.transcribe_audio.assert_called_once_with(
            b"audio", language="en", max_retries=1
        )

    def test_manual_mode_skips_without_interactive_input(self) -> None:
        """Test manual mode skips cleanly when stdin is unavailable."""
        config = types.SimpleNamespace(mic_startup_check="manual", mic_check_duration=0.1)
        audio_recorder = unittest.mock.Mock()
        transcription_client = unittest.mock.Mock()

        with unittest.mock.patch("builtins.input", side_effect=EOFError):
            MicrophoneStartupCheck(config, audio_recorder, transcription_client).run()

        audio_recorder.start_recording.assert_not_called()
        transcription_client.transcribe_audio.assert_not_called()

    def test_counting_sequence_accepts_digits(self) -> None:
        """Test counting sequence verification accepts digit transcriptions."""
        checker = MicrophoneStartupCheck(
            types.SimpleNamespace(mic_startup_check="none"),
            unittest.mock.Mock(),
            unittest.mock.Mock(),
        )

        assert checker._contains_counting_sequence("1 2 3 4 5 6 7 8 9 10")
