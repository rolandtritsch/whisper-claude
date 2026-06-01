"""Whisper Wayland - Key Mapping

Key code mapping and hotkey parsing functionality for evdev integration.
"""

import logging
import typing

try:
    import evdev
except ImportError as e:
    raise ImportError(
        "evdev is required for key monitoring. Install with: pip install evdev or uv add evdev"
    ) from e

_logger = logging.getLogger(__name__)


class KeyMappingError(Exception):
    """Raised when key mapping operations fail."""

    pass


class KeyMapping:
    """Handles key code mapping and hotkey parsing for evdev integration."""

    def __init__(self) -> None:
        """Initialize key mapping."""
        self._key_map = self._build_key_map()

    def _build_key_map(self) -> dict[int, str]:
        """Build mapping from evdev keycodes to key names."""
        key_map = {
            evdev.ecodes.KEY_LEFTCTRL: "ctrl",
            evdev.ecodes.KEY_RIGHTCTRL: "ctrl",
            evdev.ecodes.KEY_LEFTALT: "alt",
            evdev.ecodes.KEY_RIGHTALT: "alt",
            evdev.ecodes.KEY_LEFTSHIFT: "shift",
            evdev.ecodes.KEY_RIGHTSHIFT: "shift",
            evdev.ecodes.KEY_LEFTMETA: "leftmeta",
            evdev.ecodes.KEY_RIGHTMETA: "rightmeta",
            evdev.ecodes.KEY_SPACE: "space",
            evdev.ecodes.KEY_ENTER: "enter",
            evdev.ecodes.KEY_ESC: "esc",
            evdev.ecodes.KEY_TAB: "tab",
            evdev.ecodes.KEY_BACKSPACE: "backspace",
            evdev.ecodes.KEY_DELETE: "delete",
            evdev.ecodes.KEY_COMPOSE: "compose",  # The compose key
            evdev.ecodes.KEY_MENU: "menu",
            # Function keys
            evdev.ecodes.KEY_F1: "f1",
            evdev.ecodes.KEY_F2: "f2",
            evdev.ecodes.KEY_F3: "f3",
            evdev.ecodes.KEY_F4: "f4",
            evdev.ecodes.KEY_F5: "f5",
            evdev.ecodes.KEY_F6: "f6",
            evdev.ecodes.KEY_F7: "f7",
            evdev.ecodes.KEY_F8: "f8",
            evdev.ecodes.KEY_F9: "f9",
            evdev.ecodes.KEY_F10: "f10",
            evdev.ecodes.KEY_F11: "f11",
            evdev.ecodes.KEY_F12: "f12",
        }

        # Add letter keys (keyboard layout order, not alphabetical)
        letter_keys = {
            evdev.ecodes.KEY_A: "a",
            evdev.ecodes.KEY_B: "b",
            evdev.ecodes.KEY_C: "c",
            evdev.ecodes.KEY_D: "d",
            evdev.ecodes.KEY_E: "e",
            evdev.ecodes.KEY_F: "f",
            evdev.ecodes.KEY_G: "g",
            evdev.ecodes.KEY_H: "h",
            evdev.ecodes.KEY_I: "i",
            evdev.ecodes.KEY_J: "j",
            evdev.ecodes.KEY_K: "k",
            evdev.ecodes.KEY_L: "l",
            evdev.ecodes.KEY_M: "m",
            evdev.ecodes.KEY_N: "n",
            evdev.ecodes.KEY_O: "o",
            evdev.ecodes.KEY_P: "p",
            evdev.ecodes.KEY_Q: "q",
            evdev.ecodes.KEY_R: "r",
            evdev.ecodes.KEY_S: "s",
            evdev.ecodes.KEY_T: "t",
            evdev.ecodes.KEY_U: "u",
            evdev.ecodes.KEY_V: "v",
            evdev.ecodes.KEY_W: "w",
            evdev.ecodes.KEY_X: "x",
            evdev.ecodes.KEY_Y: "y",
            evdev.ecodes.KEY_Z: "z",
        }
        key_map.update(letter_keys)

        # Add number keys
        for i in range(10):
            key_map[evdev.ecodes.KEY_1 + i] = str(i + 1)
        key_map[evdev.ecodes.KEY_0] = "0"

        return key_map

    def parse_hotkey_combination(self, hotkey_str: str) -> set[str]:
        """Parse hotkey string into key set for detection.

        Args:
            hotkey_str: Hotkey configuration string

        Returns:
            Set of key names in the hotkey combination

        Raises:
            KeyMappingError: If hotkey format is invalid
        """
        hotkey_normalized = hotkey_str.lower().strip()
        if not hotkey_normalized:
            raise KeyMappingError("Hotkey cannot be empty")

        # Handle single key (like "compose")
        if "+" not in hotkey_normalized:
            return {hotkey_normalized}

        # Split by '+' and normalize key names
        key_parts = [part.strip() for part in hotkey_normalized.split("+")]
        if not key_parts:
            raise KeyMappingError(f"Invalid hotkey format: {hotkey_str}")

        # Map common key names
        key_mapping = {
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "shift": "shift",
            "space": "space",
            "enter": "enter",
            "return": "enter",
            "tab": "tab",
            "esc": "esc",
            "escape": "esc",
            "compose": "compose",
            "menu": "menu",
            "leftmeta": "leftmeta",
            "rightmeta": "rightmeta",
            "leftsuper": "leftmeta",
            "rightsuper": "rightmeta",
        }

        hotkey_combination: set[str] = set()
        for part in key_parts:
            if part in key_mapping:
                hotkey_combination.add(key_mapping[part])
            elif len(part) == 1 and part.isalnum():
                # Single character keys
                hotkey_combination.add(part)
            elif part.startswith("f") and part[1:].isdigit():
                # Function keys like f1, f2, etc.
                hotkey_combination.add(part)
            else:
                _logger.warning(f"Unknown key in hotkey: {part}")
                hotkey_combination.add(part)

        _logger.debug(f"Parsed hotkey combination: {hotkey_combination}")
        return hotkey_combination

    def get_key_name(self, keycode: int) -> typing.Optional[str]:
        """Convert keycode to readable key name.

        Args:
            keycode: evdev keycode

        Returns:
            Key name string or None if not recognized
        """
        if keycode in self._key_map:
            return self._key_map[keycode]

        # Try to get key name from evdev
        try:
            key_val = evdev.ecodes.KEY[keycode]

            # Handle different types that evdev might return
            raw_key_name: typing.Any = None
            if isinstance(key_val, tuple) and key_val:
                raw_key_name = key_val[0]
            else:
                raw_key_name = key_val

            # Convert to string regardless of whether it's bytes or str
            if isinstance(raw_key_name, bytes):
                key_name_str = raw_key_name.decode()
            elif isinstance(raw_key_name, str):
                key_name_str = raw_key_name
            else:
                return None

            # Remove KEY_ prefix if present
            if key_name_str.startswith("KEY_"):
                return key_name_str[4:].lower()
            else:
                return key_name_str.lower()

        except (KeyError, UnicodeDecodeError, AttributeError):
            pass

        return None

    @staticmethod
    def new() -> "KeyMapping":
        """Create key mapping instance.

        Returns:
            KeyMapping instance
        """
        return KeyMapping()
