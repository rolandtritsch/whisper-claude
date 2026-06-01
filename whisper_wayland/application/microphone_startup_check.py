"""Startup microphone check orchestration."""

import logging
import re
import time
import typing

import whisper_wayland as ww

_logger = logging.getLogger(__name__)


class MicrophoneStartupCheck:
    """Runs configured startup microphone checks."""

    _COUNTING_WORDS = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
    }

    def __init__(
        self,
        config: typing.Any,
        audio_recorder: typing.Any,
        transcription_client: typing.Any,
    ) -> None:
        """Initialize startup microphone check."""
        self.config = config
        self.audio_recorder = audio_recorder
        self.transcription_client = transcription_client

    def run(self) -> None:
        """Run the configured microphone startup check."""
        mode = self.config.mic_startup_check
        if mode == "none":
            return

        if mode == "auto":
            self.audio_recorder.check_microphone_signal()
            return

        if mode == "manual":
            self._run_manual_check()
            return

        _logger.warning(f"Unknown microphone startup check mode: {mode}")

    def _run_manual_check(self) -> None:
        """Record, transcribe, and verify a spoken count from one to ten."""
        duration = max(
            self.config.mic_check_duration, ww.Constants.DEFAULT_MANUAL_MIC_CHECK_DURATION
        )

        try:
            input(
                "Manual mic check: press Enter, then count clearly from 1 to 10 "
                f"within {duration:.1f} seconds..."
            )
        except EOFError:
            _logger.warning("Manual mic check skipped: no interactive input available")
            return

        try:
            _logger.info(f"Manual mic check recording for {duration:.1f}s...")
            self.audio_recorder.start_recording()
            time.sleep(duration)
            audio_data = self.audio_recorder.stop_recording()

            if not audio_data:
                _logger.warning("Manual mic check failed: no audio data captured")
                return

            transcription = self.transcription_client.transcribe_audio(
                audio_data, language="en", max_retries=1
            )
            if not transcription:
                _logger.warning("Manual mic check failed: transcription was empty")
                return

            if self._contains_counting_sequence(transcription):
                _logger.info("Manual mic check passed: recognized count from 1 to 10")
            else:
                _logger.warning(
                    f"Manual mic check failed: expected count from 1 to 10, "
                    f"recognized '{transcription}'"
                )
        except Exception as e:
            _logger.warning(f"Manual mic check could not complete: {e}")

    def _contains_counting_sequence(self, transcription: str) -> bool:
        """Return whether transcription contains each count from 1 through 10."""
        tokens = set(re.findall(r"[a-z0-9]+", transcription.lower()))
        return all(
            str(number) in tokens or word in tokens for number, word in self._COUNTING_WORDS.items()
        )

    @staticmethod
    def new(
        config: typing.Any,
        audio_recorder: typing.Any,
        transcription_client: typing.Any,
    ) -> "MicrophoneStartupCheck":
        """Create startup microphone check instance."""
        return MicrophoneStartupCheck(config, audio_recorder, transcription_client)
