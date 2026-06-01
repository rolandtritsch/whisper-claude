"""Whisper Wayland - Key Monitor Tests

Unit tests for key monitor module including evdev implementation
and global hotkey detection functionality."""

import os
import unittest.mock

import pytest

import whisper_wayland as ww
import whisper_wayland.key_monitor as key_monitor


class TestKeyMonitor:
    """Test cases for KeyMonitor class with evdev implementation."""

    def test_key_monitor_initialization(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test key monitor initialization with valid config."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        assert monitor.config == test_config_with_hotkey
        assert monitor._event_handler._callback is None
        assert monitor._event_handler._release_callback is None
        assert not monitor.is_monitoring()
        assert not monitor.is_hotkey_pressed()
        assert monitor._event_handler._hotkey_combination == {"ctrl", "compose"}

    def test_key_monitor_initialization_custom_hotkey(self) -> None:
        """Test key monitor initialization with custom hotkey."""
        with unittest.mock.patch.dict(os.environ, {"HOTKEY": "ctrl+shift+f1"}):
            hotkey_config = ww.Config()
            monitor = key_monitor.KeyMonitor(hotkey_config)

            assert monitor._event_handler._hotkey_combination == {"ctrl", "shift", "f1"}

    def test_key_monitor_initialization_single_key(self) -> None:
        """Test key monitor initialization with single key."""
        with unittest.mock.patch.dict(os.environ, {"HOTKEY": "f10"}):
            f10_config = ww.Config()
            monitor = key_monitor.KeyMonitor(f10_config)

            assert monitor._event_handler._hotkey_combination == {"f10"}

    def test_key_monitor_initialization_invalid_hotkey(self) -> None:
        """Test key monitor initialization with invalid hotkey."""
        with unittest.mock.patch.dict(os.environ, {"HOTKEY": ""}):
            empty_config = ww.Config()
            with pytest.raises(key_monitor.KeyMonitorError, match="Hotkey cannot be empty"):
                key_monitor.KeyMonitor(empty_config)

    def test_parse_hotkey_combination_various_formats(self) -> None:
        """Test hotkey parsing with various input formats."""
        test_cases = [
            ("compose", {"compose"}),
            ("ctrl+space", {"ctrl", "space"}),
            ("ctrl+alt+space", {"ctrl", "alt", "space"}),
            ("shift+a", {"shift", "a"}),
            ("ctrl+shift+enter", {"ctrl", "shift", "enter"}),
            ("f5", {"f5"}),
            ("menu", {"menu"}),
            ("ctrl+leftmeta", {"ctrl", "leftmeta"}),
            ("ctrl+rightmeta", {"ctrl", "rightmeta"}),
            ("ctrl+leftsuper", {"ctrl", "leftmeta"}),
            ("ctrl+rightsuper", {"ctrl", "rightmeta"}),
        ]

        for hotkey_str, expected in test_cases:
            with unittest.mock.patch.dict(os.environ, {"HOTKEY": hotkey_str}):
                test_hotkey_config = ww.Config()
                monitor = key_monitor.KeyMonitor(test_hotkey_config)
                assert monitor._event_handler._hotkey_combination == expected

    def test_set_callback(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test setting press callback for key monitor."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        def callback() -> None:
            """Test callback function."""
            return None

        monitor.set_callback(callback)
        assert monitor._event_handler._callback == callback

    def test_set_release_callback(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test setting release callback for key monitor."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        def release_callback() -> None:
            """Test release callback function."""
            return None

        monitor.set_release_callback(release_callback)
        assert monitor._event_handler._release_callback == release_callback

    def test_build_key_map(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test building of key code mapping."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)
        key_map = monitor._key_mapping._key_map

        # Test some expected mappings
        assert key_map[57] == "space"  # KEY_SPACE
        assert key_map[28] == "enter"  # KEY_ENTER
        assert key_map[127] == "compose"  # KEY_COMPOSE
        assert key_map[125] == "leftmeta"  # KEY_LEFTMETA
        assert key_map[126] == "rightmeta"  # KEY_RIGHTMETA

        # Test letter keys
        assert key_map[30] == "a"  # KEY_A
        assert key_map[48] == "b"  # KEY_B

        # Test number keys
        assert key_map[2] == "1"  # KEY_1
        assert key_map[11] == "0"  # KEY_0

    def test_get_key_name(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test key name resolution."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        # Test mapped keys
        assert monitor._key_mapping.get_key_name(57) == "space"
        assert monitor._key_mapping.get_key_name(28) == "enter"
        assert monitor._key_mapping.get_key_name(127) == "compose"
        assert monitor._key_mapping.get_key_name(125) == "leftmeta"
        assert monitor._key_mapping.get_key_name(126) == "rightmeta"

        # Test unmapped key
        assert monitor._key_mapping.get_key_name(999) is None

    @unittest.mock.patch("whisper_wayland.key_monitor.monitor_loop.select.select")
    def test_start_monitoring_success(
        self,
        mock_select: unittest.mock.Mock,
        test_config_with_hotkey: "ww.Config",
        mock_evdev: unittest.mock.Mock,
    ) -> None:
        """Test successful start of key monitoring."""
        mock_select.return_value = ([], [], [])

        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)
        monitor.start_monitoring()

        assert monitor.is_monitoring()
        assert (
            len(monitor._device_manager.get_devices()) == ww.Constants.EXPECTED_DEVICE_COUNT
        )  # Two mock devices

    def test_start_monitoring_already_active(
        self, test_config_with_hotkey: "ww.Config", mock_evdev: unittest.mock.Mock
    ) -> None:
        """Test starting monitoring when already active."""
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.monitor_loop.select.select", return_value=([], [], [])
        ):
            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)
            monitor.start_monitoring()  # Start monitoring first

            # Should not raise an error when starting again
            monitor.start_monitoring()
            assert monitor.is_monitoring()

    def test_start_monitoring_no_devices(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test handling when no devices are found."""
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.device_manager.evdev.list_devices", return_value=[]
        ):
            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

            with pytest.raises(key_monitor.KeyMonitorError, match="No keyboard devices found"):
                monitor.start_monitoring()

    def test_start_monitoring_permission_error(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test handling of permission errors."""
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.device_manager.evdev.list_devices",
            side_effect=PermissionError("Access denied"),
        ):
            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

            with pytest.raises(key_monitor.KeyMonitorError, match="Permission denied"):
                monitor.start_monitoring()

    def test_stop_monitoring(
        self, test_config_with_hotkey: "ww.Config", mock_evdev: unittest.mock.Mock
    ) -> None:
        """Test stopping key monitoring."""
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.monitor_loop.select.select", return_value=([], [], [])
        ):
            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)
            monitor.start_monitoring()

            assert monitor.is_monitoring()

            monitor.stop_monitoring()

            assert not monitor.is_monitoring()
            assert len(monitor._device_manager.get_devices()) == 0

    def test_stop_monitoring_not_active(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test stopping monitoring when not active."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        # Should not raise any errors
        monitor.stop_monitoring()
        assert not monitor.is_monitoring()

    def test_check_hotkey_state_press_release(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test hotkey state detection with press and release."""
        # Mock threading in the event handler module to prevent actual thread creation
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.event_handler.threading.Thread"
        ) as mock_thread:
            mock_thread.return_value.start = unittest.mock.Mock()

            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)
            press_callback = unittest.mock.Mock()
            release_callback = unittest.mock.Mock()

            monitor.set_callback(press_callback)
            monitor.set_release_callback(release_callback)

            # Simulate pressing ctrl+compose keys by directly manipulating event handler state
            with monitor._event_handler._lock:
                monitor._event_handler._pressed_keys.add("ctrl")
                monitor._event_handler._pressed_keys.add("compose")
                monitor._event_handler._check_hotkey_state()

            assert monitor._event_handler._hotkey_pressed
            # Verify thread would have been created to call the callback
            mock_thread.assert_called()

            # Reset for release test
            mock_thread.reset_mock()

            # Simulate releasing compose key (ctrl still held)
            with monitor._event_handler._lock:
                monitor._event_handler._pressed_keys.remove("compose")
                monitor._event_handler._check_hotkey_state()

            assert not monitor._event_handler._hotkey_pressed
            # Verify release thread would have been created
            mock_thread.assert_called()  # type: ignore[unreachable]

    def test_check_hotkey_state_combination(self) -> None:
        """Test hotkey state with key combination."""
        with unittest.mock.patch.dict(os.environ, {"HOTKEY": "ctrl+alt"}):
            with unittest.mock.patch(
                "whisper_wayland.key_monitor.event_handler.threading.Thread"
            ) as mock_thread:
                mock_thread.return_value.start = unittest.mock.Mock()

                combo_config = ww.Config()
                monitor = key_monitor.KeyMonitor(combo_config)
                press_callback = unittest.mock.Mock()

                monitor.set_callback(press_callback)

                # Press only ctrl - should not trigger
                with monitor._event_handler._lock:
                    monitor._event_handler._pressed_keys.add("ctrl")
                    monitor._event_handler._check_hotkey_state()

                assert not monitor._event_handler._hotkey_pressed
                mock_thread.assert_not_called()

                # Press ctrl+alt - should trigger
                with monitor._event_handler._lock:
                    monitor._event_handler._pressed_keys.add("alt")
                    monitor._event_handler._check_hotkey_state()

                assert monitor._event_handler._hotkey_pressed
                mock_thread.assert_called_once()  # type: ignore[unreachable]

    def test_is_hotkey_pressed(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test checking if hotkey is currently pressed."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        assert not monitor.is_hotkey_pressed()

        # Set hotkey pressed state on the event handler (the real state)
        monitor._event_handler._hotkey_pressed = True
        assert monitor.is_hotkey_pressed()

    def test_get_pressed_keys(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test getting currently pressed keys."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        # Initially empty
        assert monitor.get_pressed_keys() == set()

        # Add some keys to the event handler (the real state)
        monitor._event_handler._pressed_keys.add("ctrl")
        monitor._event_handler._pressed_keys.add("space")

        pressed = monitor.get_pressed_keys()
        assert pressed == {"ctrl", "space"}

        # Should return a copy
        pressed.add("alt")
        assert monitor._event_handler._pressed_keys == {"ctrl", "space"}

    def test_callback_error_handling(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test error handling in callbacks."""
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.event_handler.threading.Thread"
        ) as mock_thread:
            # Mock the thread to call the callback immediately and catch exceptions
            def mock_start() -> None:
                try:
                    failing_callback()
                except Exception:
                    pass  # Error should be caught and logged

            mock_thread.return_value.start = mock_start

            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

            # Create callback that raises an error
            def failing_callback() -> None:
                raise Exception("Callback error")

            monitor.set_callback(failing_callback)

            # Should not raise an error when callback fails - error is caught in thread
            with monitor._event_handler._lock:
                monitor._event_handler._pressed_keys.add("compose")
                monitor._event_handler._check_hotkey_state()

            # Test should pass without hanging

    def test_close(
        self, test_config_with_hotkey: "ww.Config", mock_evdev: unittest.mock.Mock
    ) -> None:
        """Test key monitor cleanup."""
        with unittest.mock.patch(
            "whisper_wayland.key_monitor.monitor_loop.select.select", return_value=([], [], [])
        ):
            monitor = key_monitor.KeyMonitor(test_config_with_hotkey)
            monitor.start_monitoring()

            assert monitor.is_monitoring()

            monitor.close()

            assert not monitor.is_monitoring()

    def test_create_key_monitor(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test KeyMonitor.new static method."""
        monitor = key_monitor.KeyMonitor.new(test_config_with_hotkey)

        assert isinstance(monitor, key_monitor.KeyMonitor)
        assert monitor.config == test_config_with_hotkey

    def test_device_cleanup(
        self, test_config_with_hotkey: "ww.Config", mock_evdev_devices: unittest.mock.Mock
    ) -> None:
        """Test device cleanup functionality."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        # Set devices in the device manager (where cleanup actually happens)
        monitor._device_manager._devices = mock_evdev_devices.copy()

        monitor._device_manager.cleanup_devices()

        # Check that all devices were closed
        for device in mock_evdev_devices:
            device.close.assert_called_once()

        assert len(monitor._device_manager._devices) == 0

    def test_handle_key_event_press_release(self, test_config_with_hotkey: "ww.Config") -> None:
        """Test key event handling."""
        monitor = key_monitor.KeyMonitor(test_config_with_hotkey)

        # Create mock event for key press
        press_event = unittest.mock.Mock()
        press_event.type = 1  # EV_KEY
        press_event.code = 127  # KEY_COMPOSE
        press_event.value = 1  # Key press

        # Handle press event
        monitor._event_handler.handle_key_event(press_event)
        assert "compose" in monitor.get_pressed_keys()

        # Create mock event for key release
        release_event = unittest.mock.Mock()
        release_event.type = 1  # EV_KEY
        release_event.code = 127  # KEY_COMPOSE
        release_event.value = 0  # Key release

        # Handle release event
        monitor._event_handler.handle_key_event(release_event)
        assert "compose" not in monitor.get_pressed_keys()
