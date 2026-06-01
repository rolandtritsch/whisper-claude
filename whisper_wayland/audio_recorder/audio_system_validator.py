"""Whisper Wayland - Audio System Validator

Audio system validation and device discovery functionality.
"""

import logging
import math
import sys
import typing
from array import array

import pyaudio

import whisper_wayland as ww
from whisper_wayland.audio_recorder.native_stderr import suppress_native_stderr

_logger = logging.getLogger(__name__)


class AudioSystemValidationError(Exception):
    """Raised when audio system validation fails."""

    pass


class AudioSystemValidator:
    """Validates audio system availability and configuration."""

    def __init__(self) -> None:
        """Initialize audio system validator."""
        pass

    def initialize_audio(self) -> pyaudio.PyAudio:
        """Initialize PyAudio instance with error handling.

        Returns:
            Initialized PyAudio instance

        Raises:
            AudioSystemValidationError: If PyAudio initialization fails
        """
        try:
            with suppress_native_stderr():
                audio = pyaudio.PyAudio()
            _logger.debug("PyAudio initialized successfully")
            return audio
        except Exception as e:
            _logger.error(f"Failed to initialize PyAudio: {e}")
            raise AudioSystemValidationError(f"PyAudio initialization failed: {e}") from e

    def validate_audio_system(self, audio: pyaudio.PyAudio, config: "ww.Config") -> None:
        """Validate audio system availability and configuration.

        Args:
            audio: PyAudio instance
            config: Configuration instance

        Raises:
            AudioSystemValidationError: If audio system validation fails
        """
        try:
            # Check for available input devices
            with suppress_native_stderr():
                device_count = audio.get_device_count()
            input_devices = []

            for i in range(device_count):
                with suppress_native_stderr():
                    device_info = audio.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    input_devices.append(device_info)

            if not input_devices:
                raise AudioSystemValidationError("No audio input devices found")

            _logger.debug(f"Found {len(input_devices)} audio input devices")

            # Test audio format support with default input device
            try:
                with suppress_native_stderr():
                    default_device = audio.get_default_input_device_info()
                    audio.is_format_supported(
                        rate=config.audio_sample_rate,
                        input_device=default_device["index"],
                        input_channels=1,
                        input_format=pyaudio.paInt16,
                    )
                _logger.debug(
                    f"Audio format validated successfully for device: {default_device['name']}"
                )
            except (ValueError, OSError) as e:
                # Log as debug instead of warning since this is just a validation check
                # and the system can still work even if format validation fails
                _logger.debug(f"Audio format validation result: {e}")
            except Exception as e:
                _logger.debug(f"Could not validate audio format support: {e}")

        except Exception as e:
            _logger.error(f"Audio system validation failed: {e}")
            raise AudioSystemValidationError(f"Audio system validation failed: {e}") from e

    def find_preferred_input_device(
        self, audio: pyaudio.PyAudio, config: "ww.Config"
    ) -> typing.Optional[int]:
        """Find the preferred input device, prioritizing USB then Bluetooth headsets.

        Args:
            audio: PyAudio instance

        Returns:
            Device index of preferred device, or None to use the system default
        """
        usb_keywords = ["usb"]
        bt_keywords = ["bluetooth", "bluez", "headset", "headphone"]

        usb_candidates: list[tuple[int, str]] = []
        bt_candidates: list[tuple[int, str]] = []

        try:
            with suppress_native_stderr():
                device_count = audio.get_device_count()
            for i in range(device_count):
                with suppress_native_stderr():
                    info = audio.get_device_info_by_index(i)
                if info["maxInputChannels"] <= 0:
                    continue
                name = str(info["name"]).lower()
                if any(k in name for k in usb_keywords):
                    usb_candidates.append((i, str(info["name"])))
                elif any(k in name for k in bt_keywords):
                    bt_candidates.append((i, str(info["name"])))
        except Exception as e:
            _logger.warning(f"Error scanning audio devices: {e}")
            return None

        for idx, name in usb_candidates:
            if self._can_open_input_device(audio, config, idx):
                _logger.info(f"Auto-selected USB input device: {name} (index {idx})")
                return idx
            _logger.warning(f"Skipping unavailable USB input device: {name} (index {idx})")

        for idx, name in bt_candidates:
            if self._can_open_input_device(audio, config, idx):
                _logger.info(f"Auto-selected Bluetooth input device: {name} (index {idx})")
                return idx
            _logger.warning(f"Skipping unavailable Bluetooth input device: {name} (index {idx})")

        _logger.debug("No USB/Bluetooth headset found, using system default input device")
        return None

    def _can_open_input_device(
        self, audio: pyaudio.PyAudio, config: "ww.Config", input_device_index: int
    ) -> bool:
        """Return whether PyAudio can open an input stream for a device."""
        stream: typing.Any = None
        sample_rate = self._get_check_sample_rate(audio, config, input_device_index)
        try:
            with suppress_native_stderr():
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=config.audio_chunk_size,
                    input_device_index=input_device_index,
                )
            return True
        except Exception as e:
            _logger.debug(f"Input device open check failed for index {input_device_index}: {e}")
            return False
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    _logger.debug(f"Error closing input device check stream: {e}")

    def check_microphone_signal(
        self,
        audio: pyaudio.PyAudio,
        config: "ww.Config",
        input_device_index: typing.Optional[int],
    ) -> None:
        """Run a short startup signal check against the selected microphone."""
        stream: typing.Any = None
        sample_rate = self._get_check_sample_rate(audio, config, input_device_index)
        duration = config.mic_check_duration
        chunk_size = config.audio_chunk_size
        chunks_to_read = max(1, math.ceil(sample_rate * duration / chunk_size))
        frames: list[bytes] = []

        try:
            _logger.info(f"Running microphone startup check for {duration:.1f}s...")
            with suppress_native_stderr():
                stream = audio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    frames_per_buffer=chunk_size,
                    input_device_index=input_device_index,
                )

            for _ in range(chunks_to_read):
                frames.append(stream.read(chunk_size, exception_on_overflow=False))

            metrics = self._calculate_signal_metrics(b"".join(frames))
            self._log_signal_metrics(metrics)
        except Exception as e:
            _logger.warning(f"Microphone startup check could not complete: {e}")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception as e:
                    _logger.debug(f"Error closing microphone check stream: {e}")

    def _get_check_sample_rate(
        self,
        audio: pyaudio.PyAudio,
        config: "ww.Config",
        input_device_index: typing.Optional[int],
    ) -> int:
        """Get the sample rate to use for the startup microphone check."""
        if input_device_index is None:
            return config.audio_sample_rate

        try:
            with suppress_native_stderr():
                info = audio.get_device_info_by_index(input_device_index)
            return int(info["defaultSampleRate"])
        except Exception as e:
            _logger.debug(f"Could not read microphone check sample rate: {e}")
            return config.audio_sample_rate

    def _calculate_signal_metrics(self, audio_data: bytes) -> dict[str, float | int]:
        """Calculate basic signal quality metrics from 16-bit mono PCM data."""
        samples = array("h")
        samples.frombytes(audio_data[: len(audio_data) - (len(audio_data) % 2)])
        if sys.byteorder != "little":
            samples.byteswap()

        sample_count = len(samples)
        if sample_count == 0:
            return {
                "sample_count": 0,
                "rms_dbfs": float("-inf"),
                "peak_dbfs": float("-inf"),
                "clipping_percent": 0.0,
            }

        max_abs = max(abs(sample) for sample in samples)
        rms = math.sqrt(sum(sample * sample for sample in samples) / sample_count)
        clipping_count = sum(
            1 for sample in samples if abs(sample) >= ww.Constants.CLIPPING_SAMPLE_THRESHOLD
        )

        return {
            "sample_count": sample_count,
            "rms_dbfs": self._amplitude_to_dbfs(rms),
            "peak_dbfs": self._amplitude_to_dbfs(max_abs),
            "clipping_percent": clipping_count / sample_count * 100,
        }

    def _log_signal_metrics(self, metrics: dict[str, float | int]) -> None:
        """Log microphone signal metrics and practical warnings."""
        rms_dbfs = float(metrics["rms_dbfs"])
        peak_dbfs = float(metrics["peak_dbfs"])
        clipping_percent = float(metrics["clipping_percent"])

        _logger.info(
            f"Mic check: rms={rms_dbfs:.1f} dBFS, "
            f"peak={peak_dbfs:.1f} dBFS, clipping={clipping_percent:.2f}%"
        )

        if rms_dbfs <= ww.Constants.DEAD_MIC_DBFS_THRESHOLD:
            _logger.warning("Mic check warning: input appears silent or muted")
        elif rms_dbfs <= ww.Constants.QUIET_MIC_DBFS_THRESHOLD:
            _logger.warning("Mic check warning: input level is very quiet")
        elif rms_dbfs >= ww.Constants.NOISY_MIC_DBFS_THRESHOLD:
            _logger.warning("Mic check warning: ambient input level is high")

        if clipping_percent >= ww.Constants.CLIPPING_RATE_WARNING_THRESHOLD:
            _logger.warning("Mic check warning: input appears to be clipping")

    @staticmethod
    def _amplitude_to_dbfs(amplitude: float) -> float:
        """Convert a 16-bit PCM amplitude to dBFS."""
        if amplitude <= 0:
            return float("-inf")
        return 20 * math.log10(amplitude / 32768.0)

    def get_audio_devices(self, audio: pyaudio.PyAudio) -> list[dict[str, typing.Any]]:
        """Get list of available audio input devices.

        Args:
            audio: PyAudio instance

        Returns:
            List of dictionaries containing device information
        """
        devices: list[dict[str, typing.Any]] = []

        try:
            with suppress_native_stderr():
                device_count = audio.get_device_count()
            for i in range(device_count):
                with suppress_native_stderr():
                    device_info = audio.get_device_info_by_index(i)
                if device_info["maxInputChannels"] > 0:
                    devices.append(
                        {
                            "index": i,
                            "name": device_info["name"],
                            "channels": device_info["maxInputChannels"],
                            "sample_rate": device_info["defaultSampleRate"],
                        }
                    )
            _logger.debug(f"Retrieved {len(devices)} audio input devices")
        except Exception as e:
            _logger.error(f"Failed to get audio devices: {e}")

        return devices

    @staticmethod
    def new() -> "AudioSystemValidator":
        """Create audio system validator instance.

        Returns:
            AudioSystemValidator instance
        """
        return AudioSystemValidator()
