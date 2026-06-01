"""Whisper Wayland - Recording Engine

Core audio recording engine with threading and stream management.
"""

import logging
import threading
import time
import typing

import pyaudio

import whisper_wayland as ww
from whisper_wayland.audio_recorder.native_stderr import suppress_native_stderr

_logger = logging.getLogger(__name__)


class RecordingEngineError(Exception):
    """Raised when recording engine operations fail."""

    pass


class RecordingEngine:
    """Core audio recording engine with threading support."""

    def __init__(
        self,
        audio: pyaudio.PyAudio,
        config: "ww.Config",
        input_device_index: typing.Optional[int] = None,
    ) -> None:
        """Initialize recording engine.

        Args:
            audio: PyAudio instance
            config: Configuration instance
            input_device_index: Input device index, or None for system default
        """
        self._audio = audio
        self._config = config
        self._input_device_index = input_device_index
        self._effective_sample_rate = self._resolve_sample_rate(audio, input_device_index, config)
        self._stream: typing.Optional[pyaudio.Stream] = None
        self._recording = False
        self._recording_thread: typing.Optional[threading.Thread] = None
        self._audio_data: typing.Optional[bytes] = None
        self._lock = threading.Lock()

    def start_recording(self) -> None:
        """Start audio recording in a separate thread.

        Raises:
            RecordingEngineError: If recording cannot be started
        """
        with self._lock:
            if self._recording:
                _logger.warning("Recording already in progress")
                return

            try:
                self._recording = True
                self._audio_data = None
                self._recording_thread = threading.Thread(target=self._record_audio, daemon=True)
                self._recording_thread.start()
                _logger.info("Audio recording started")
            except Exception as e:
                self._recording = False
                _logger.error(f"Failed to start recording: {e}")
                raise RecordingEngineError(f"Failed to start recording: {e}") from e

    def stop_recording(self) -> typing.Optional[bytes]:
        """Stop audio recording and return recorded data.

        Returns:
            Recorded audio data as WAV bytes, or None if no data recorded

        Raises:
            RecordingEngineError: If stopping recording fails
        """
        with self._lock:
            if not self._recording:
                _logger.warning("No recording in progress")
                return None

            try:
                self._recording = False
                _logger.debug("Stopping audio recording...")

                # Wait for recording thread to finish
                if self._recording_thread and self._recording_thread.is_alive():
                    self._recording_thread.join(timeout=5.0)
                    if self._recording_thread.is_alive():
                        _logger.error("Recording thread did not stop within timeout")
                        raise RecordingEngineError("Recording thread timeout")

                self._cleanup_stream()

                audio_data = self._audio_data
                self._audio_data = None
                self._recording_thread = None

                if audio_data:
                    _logger.info(f"Audio recording stopped, captured {len(audio_data)} bytes")
                else:
                    _logger.warning("No audio data captured")

                return audio_data

            except Exception as e:
                _logger.error(f"Failed to stop recording: {e}")
                raise RecordingEngineError(f"Failed to stop recording: {e}") from e

    def _record_audio(self) -> None:
        """Internal method to handle audio recording in separate thread."""
        frames = []
        start_time = time.time()
        max_duration = self._config.max_recording_duration

        try:
            with suppress_native_stderr():
                self._stream = self._audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self._effective_sample_rate,
                    input=True,
                    frames_per_buffer=self._config.audio_chunk_size,
                    input_device_index=self._input_device_index,
                )

            _logger.debug(f"Audio stream opened, recording for up to {max_duration}s")

            while self._recording:
                if time.time() - start_time >= max_duration:
                    _logger.info(f"Maximum recording duration ({max_duration}s) reached")
                    break

                try:
                    data = self._stream.read(
                        self._config.audio_chunk_size, exception_on_overflow=False
                    )
                    frames.append(data)
                except Exception as e:
                    _logger.error(f"Error reading audio data: {e}")
                    break

        except Exception as e:
            _logger.error(f"Error setting up audio stream: {e}")
            return

        finally:
            self._cleanup_stream()

        # Convert frames to WAV format
        if frames:
            try:
                from whisper_wayland.audio_recorder.wav_converter import WavConverter

                wav_converter = WavConverter.new(self._audio, self._config)
                self._audio_data = wav_converter.frames_to_wav(frames, self._effective_sample_rate)
                _logger.debug(f"Converted {len(frames)} frames to WAV format")
            except Exception as e:
                _logger.error(f"Failed to convert audio frames to WAV: {e}")

    def _cleanup_stream(self) -> None:
        """Clean up audio stream resources."""
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
                _logger.debug("Audio stream cleaned up")
            except Exception as e:
                _logger.error(f"Error cleaning up audio stream: {e}")
            finally:
                self._stream = None

    def is_recording(self) -> bool:
        """Check if recording is currently in progress.

        Returns:
            True if recording is active, False otherwise
        """
        with self._lock:
            return self._recording

    @staticmethod
    def _resolve_sample_rate(
        audio: pyaudio.PyAudio,
        input_device_index: typing.Optional[int],
        config: "ww.Config",
    ) -> int:
        """Resolve the effective sample rate for the chosen input device.

        Uses the device's native sample rate when a specific device is selected,
        falling back to the configured rate otherwise.
        """
        if input_device_index is not None:
            try:
                with suppress_native_stderr():
                    info = audio.get_device_info_by_index(input_device_index)
                native_rate = int(info["defaultSampleRate"])
                _logger.debug(f"Using device native sample rate: {native_rate} Hz")
                return native_rate
            except Exception as e:
                _logger.warning(f"Could not read device sample rate, using config value: {e}")
        return config.audio_sample_rate

    @staticmethod
    def new(
        audio: pyaudio.PyAudio,
        config: "ww.Config",
        input_device_index: typing.Optional[int] = None,
    ) -> "RecordingEngine":
        """Create recording engine instance.

        Args:
            audio: PyAudio instance
            config: Configuration instance
            input_device_index: Input device index, or None for system default

        Returns:
            RecordingEngine instance
        """
        return RecordingEngine(audio, config, input_device_index)
