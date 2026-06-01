"""Whisper Wayland - Audio System Validator

Audio system validation and device discovery functionality.
"""

import logging
import typing

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

    def find_preferred_input_device(self, audio: pyaudio.PyAudio) -> typing.Optional[int]:
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

        if usb_candidates:
            idx, name = usb_candidates[0]
            _logger.info(f"Auto-selected USB input device: {name} (index {idx})")
            return idx
        if bt_candidates:
            idx, name = bt_candidates[0]
            _logger.info(f"Auto-selected Bluetooth input device: {name} (index {idx})")
            return idx

        _logger.debug("No USB/Bluetooth headset found, using system default input device")
        return None

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
