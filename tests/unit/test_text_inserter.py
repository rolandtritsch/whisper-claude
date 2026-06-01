"""Whisper Wayland - Text Inserter Tests

Unit tests for text inserter module including
text insertion methods and cross-platform compatibility."""

import os
import subprocess
import typing
import unittest.mock

import whisper_wayland as ww
import whisper_wayland.text_inserter as text_inserter
import whisper_wayland.text_inserter as text_inserter_module


class TestTextInsertionMethod:
    """Test cases for TextInsertionMethod enum."""

    def test_enum_values(self) -> None:
        """Test that enum has correct values."""
        assert text_inserter.TextInsertionMethod.WTYPE.value == "wtype"
        assert text_inserter.TextInsertionMethod.YDOTOOL.value == "ydotool"
        assert text_inserter.TextInsertionMethod.XDOTOOL.value == "xdotool"
        assert text_inserter.TextInsertionMethod.CLIPBOARD.value == "clipboard"


class TestTextInserter:
    """Test cases for TextInserter class."""

    def test_initialization_with_available_method(
        self, test_config_text_inserter: "ww.Config", mock_shutil_which: unittest.mock.Mock
    ) -> None:
        """Test successful initialization with available method."""
        inserter = text_inserter.TextInserter(test_config_text_inserter)

        assert inserter.config == test_config_text_inserter
        assert inserter._preferred_method == text_inserter.TextInsertionMethod.YDOTOOL
        assert inserter._available_methods[text_inserter.TextInsertionMethod.YDOTOOL] is True
        assert inserter._available_methods[text_inserter.TextInsertionMethod.CLIPBOARD] is True

    def test_initialization_no_methods_available(self, test_config: "ww.Config") -> None:
        """Test initialization when no methods are available."""
        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which", return_value=None
        ):
            # Even with no tools, clipboard should be available
            inserter = text_inserter.TextInserter(test_config)
            assert inserter._preferred_method == text_inserter.TextInsertionMethod.CLIPBOARD

    def test_detect_available_methods_all_available(self, test_config: "ww.Config") -> None:
        """Test detection when all methods are available."""
        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which",
            return_value="/usr/bin/tool",
        ):
            inserter = text_inserter.TextInserter(test_config)

            assert all(inserter._available_methods.values())
            # Config is set to use ydotool, so even with all available, should use configured method
            assert inserter._preferred_method == text_inserter.TextInsertionMethod.YDOTOOL

    def test_detect_available_methods_partial(self, test_config: "ww.Config") -> None:
        """Test detection with only some methods available."""

        def mock_which(tool: str) -> typing.Optional[str]:
            return "/usr/bin/tool" if tool in ["ydotool", "xdotool"] else None

        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which", side_effect=mock_which
        ):
            inserter = text_inserter.TextInserter(test_config)

            assert inserter._available_methods[text_inserter.TextInsertionMethod.WTYPE] is False
            assert inserter._available_methods[text_inserter.TextInsertionMethod.YDOTOOL] is True
            assert inserter._available_methods[text_inserter.TextInsertionMethod.XDOTOOL] is True
            assert inserter._available_methods[text_inserter.TextInsertionMethod.CLIPBOARD] is True

    def test_preferred_method_configuration_respected(
        self, mock_shutil_which: unittest.mock.Mock
    ) -> None:
        """Test that configured method is used when available."""
        with unittest.mock.patch.dict(
            os.environ,
            {"WW_OPENAI_API_KEY": "sk-test123", "WW_TEXT_INSERTION_METHOD": "xdotool"},
        ):
            # Make both ydotool and xdotool available
            mock_shutil_which.side_effect = lambda tool: tool in ["ydotool", "xdotool"]

            xdotool_config = ww.Config()
            inserter = text_inserter.TextInserter(xdotool_config)

            assert inserter._preferred_method == text_inserter.TextInsertionMethod.XDOTOOL

    def test_preferred_method_fallback_when_configured_unavailable(self) -> None:
        """Test fallback when configured method is unavailable."""
        with unittest.mock.patch.dict(
            os.environ,
            {
                "WW_OPENAI_API_KEY": "sk-test123",
                "WW_TEXT_INSERTION_METHOD": "nonexistent",  # Configure a method that doesn't exist
            },
        ):
            with unittest.mock.patch(
                "whisper_wayland.text_inserter.capability_tester.shutil.which"
            ) as mock_which:
                # Only make ydotool available
                mock_which.side_effect = lambda tool: tool == "ydotool"

                fallback_config = ww.Config()
                inserter = text_inserter.TextInserter(fallback_config)

                # Should fallback to ydotool since nonexistent method is not available
                assert inserter._preferred_method == text_inserter.TextInsertionMethod.YDOTOOL

    def test_insert_text_success(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test successful text insertion."""
        with unittest.mock.patch.object(
            text_inserter._method_executors, "insert_with_method", return_value=True
        ) as mock_insert:
            result = text_inserter.insert_text("Hello, World!")

            assert result is True
            mock_insert.assert_called_once_with(
                text_inserter_module.TextInsertionMethod.YDOTOOL, "Hello, World!"
            )

    def test_insert_text_empty(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test text insertion with empty string."""
        result = text_inserter.insert_text("")

        assert result is False

    def test_insert_text_none(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test text insertion with None."""
        # Convert None to empty string for cleaning
        with unittest.mock.patch.object(
            text_inserter._text_processor, "validate_text", return_value=False
        ):
            # Cast None to str to match function signature
            result = text_inserter.insert_text(typing.cast(str, None))

            assert result is False

    def test_insert_text_with_cleaning(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test text insertion with text cleaning."""
        with unittest.mock.patch.object(
            text_inserter._method_executors, "insert_with_method", return_value=True
        ) as mock_insert:
            # Text with extra whitespace
            result = text_inserter.insert_text("  Hello,    World!  ")

            assert result is True
            # Should be cleaned to single spaces
            mock_insert.assert_called_once_with(
                text_inserter_module.TextInsertionMethod.YDOTOOL, "Hello, World!"
            )

    def test_insert_text_with_delay(
        self, test_config: "ww.Config", mock_shutil_which: unittest.mock.Mock
    ) -> None:
        """Test text insertion respects configured delay."""
        with unittest.mock.patch.dict(os.environ, {"WW_TEXT_INSERTION_DELAY": "0.5"}):
            delay_config = ww.Config()
            inserter = text_inserter.TextInserter(delay_config)

            with unittest.mock.patch("time.sleep") as mock_sleep, unittest.mock.patch.object(
                inserter._method_executors, "insert_with_method", return_value=True
            ):
                inserter.insert_text("test")

                mock_sleep.assert_called_once_with(0.5)

    def test_insert_text_fallback_on_failure(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test fallback methods when primary method fails."""
        with unittest.mock.patch.object(
            text_inserter._method_executors, "insert_with_method"
        ) as mock_insert, unittest.mock.patch.object(
            text_inserter._fallback_handler, "try_fallback_methods", return_value=True
        ) as mock_fallback:
            # Primary method fails
            mock_insert.return_value = False

            result = text_inserter.insert_text("test")

            assert result is True
            mock_fallback.assert_called_once()

    def test_insert_text_all_methods_fail(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test when all insertion methods fail."""
        with unittest.mock.patch.object(
            text_inserter._method_executors, "insert_with_method", return_value=False
        ), unittest.mock.patch.object(
            text_inserter._fallback_handler, "try_fallback_methods", return_value=False
        ):
            result = text_inserter.insert_text("test")

            assert result is False

    def test_clean_text_for_insertion_basic(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test basic text cleaning."""
        # Test strip whitespace
        assert text_inserter._text_processor.clean_text_for_insertion("  hello  ") == "hello"

        # Test multiple spaces
        assert (
            text_inserter._text_processor.clean_text_for_insertion("hello    world")
            == "hello world"
        )

        # Test combined
        assert (
            text_inserter._text_processor.clean_text_for_insertion("  hello    world  ")
            == "hello world"
        )

    def test_clean_text_for_insertion_edge_cases(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test text cleaning edge cases."""
        # Empty string
        assert text_inserter._text_processor.clean_text_for_insertion("") == ""

        # Only whitespace
        assert text_inserter._text_processor.clean_text_for_insertion("   ") == ""

        # Already clean
        assert (
            text_inserter._text_processor.clean_text_for_insertion("hello world") == "hello world"
        )

    def test_insert_with_wtype(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test wtype insertion method."""
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        with unittest.mock.patch("subprocess.run", return_value=mock_result) as mock_run:
            result = text_inserter._method_executors._insert_with_wtype("test text")

            assert result is True
            mock_run.assert_called_once_with(
                ["wtype", "test text"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_insert_with_ydotool(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test ydotool insertion method."""
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        with unittest.mock.patch("subprocess.run", return_value=mock_result) as mock_run:
            result = text_inserter._method_executors._insert_with_ydotool("test text")

            assert result is True
            mock_run.assert_called_once_with(
                ["ydotool", "type", "test text"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_insert_with_xdotool(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test xdotool insertion method."""
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        with unittest.mock.patch("subprocess.run", return_value=mock_result) as mock_run:
            result = text_inserter._method_executors._insert_with_xdotool("test text")

            assert result is True
            mock_run.assert_called_once_with(
                ["xdotool", "type", "--delay", "10", "test text"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )

    def test_insert_with_clipboard_wl_copy(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test clipboard insertion with wl-copy."""
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        # Mock ydotool available for paste command
        text_inserter._method_executors._available_methods[
            text_inserter_module.TextInsertionMethod.YDOTOOL
        ] = True

        def mock_which(tool: str) -> typing.Optional[str]:
            return "/usr/bin/tool" if tool == "wl-copy" else None

        with unittest.mock.patch("subprocess.run", return_value=mock_result) as mock_run:
            with unittest.mock.patch(
                "whisper_wayland.text_inserter.method_executors.shutil.which",
                side_effect=mock_which,
            ):
                result = text_inserter._method_executors._insert_with_clipboard("test text")

            assert result is True
            assert (
                mock_run.call_count == ww.Constants.EXPECTED_DEVICE_COUNT
            )  # wl-copy + ydotool paste

    def test_insert_with_clipboard_xclip(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test clipboard insertion with xclip."""
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        # Mock xdotool available for paste command
        text_inserter._method_executors._available_methods[
            text_inserter_module.TextInsertionMethod.XDOTOOL
        ] = True

        def mock_which(tool: str) -> typing.Optional[str]:
            if tool == "wl-copy":
                return None  # Not available
            elif tool == "xclip":
                return "/usr/bin/xclip"
            return None

        with unittest.mock.patch("subprocess.run", return_value=mock_result) as mock_run:
            with unittest.mock.patch(
                "whisper_wayland.text_inserter.method_executors.shutil.which",
                side_effect=mock_which,
            ):
                result = text_inserter._method_executors._insert_with_clipboard("test text")

            assert result is True
            assert (
                mock_run.call_count == ww.Constants.EXPECTED_DEVICE_COUNT
            )  # xclip + xdotool paste

    def test_insert_method_failure(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test handling of subprocess failures."""
        # Mock subprocess.run directly to avoid actually calling it
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 1  # Non-zero return code indicates failure

        with unittest.mock.patch("subprocess.run", return_value=mock_result):
            result = text_inserter._method_executors._insert_with_ydotool("test")

            assert result is False

    def test_insert_method_timeout(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test handling of subprocess timeouts."""
        # Test through the wrapper method that has exception handling
        with unittest.mock.patch("subprocess.run") as mock_run:
            # Configure the mock to raise TimeoutExpired
            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 10)

            result = text_inserter._method_executors.insert_with_method(
                text_inserter_module.TextInsertionMethod.YDOTOOL, "test"
            )

            assert result is False

    def test_try_fallback_methods_success(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test successful fallback method."""
        # Make multiple methods available
        text_inserter._available_methods.update(
            {
                text_inserter_module.TextInsertionMethod.WTYPE: True,
                text_inserter_module.TextInsertionMethod.XDOTOOL: True,
            }
        )

        with unittest.mock.patch.object(
            text_inserter._method_executors, "insert_with_method"
        ) as mock_insert:
            # First fallback (YDOTOOL) fails, second (WTYPE) succeeds
            mock_insert.side_effect = [False, True]

            result = text_inserter._fallback_handler.try_fallback_methods(
                "test", text_inserter._preferred_method, text_inserter._available_methods
            )

            assert result is True
            assert mock_insert.call_count == ww.Constants.EXPECTED_DEVICE_COUNT

    def test_try_fallback_methods_all_fail(
        self, text_inserter: text_inserter_module.TextInserter
    ) -> None:
        """Test when all fallback methods fail."""
        # Make multiple methods available
        text_inserter._available_methods.update(
            {
                text_inserter_module.TextInsertionMethod.WTYPE: True,
                text_inserter_module.TextInsertionMethod.XDOTOOL: True,
            }
        )

        with unittest.mock.patch.object(
            text_inserter._method_executors, "insert_with_method", return_value=False
        ):
            result = text_inserter._fallback_handler.try_fallback_methods(
                "test", text_inserter._preferred_method, text_inserter._available_methods
            )

            assert result is False

    def test_test_insertion_wtype(
        self, test_config: "ww.Config", mock_shutil_which: unittest.mock.Mock
    ) -> None:
        """Test insertion capability test for wtype."""
        mock_shutil_which.side_effect = lambda tool: tool == "wtype"

        inserter = text_inserter.TextInserter(test_config)
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        with unittest.mock.patch("subprocess.run", return_value=mock_result):
            result = inserter.test_insertion()

            assert result is True

    def test_test_insertion_ydotool(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test insertion capability test for ydotool."""
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        with unittest.mock.patch("subprocess.run", return_value=mock_result):
            result = text_inserter.test_insertion()

            assert result is True

    def test_test_insertion_xdotool(
        self, test_config: "ww.Config", mock_shutil_which: unittest.mock.Mock
    ) -> None:
        """Test insertion capability test for xdotool."""
        mock_shutil_which.side_effect = lambda tool: tool == "xdotool"

        inserter = text_inserter.TextInserter(test_config)
        mock_result = unittest.mock.Mock()
        mock_result.returncode = 0

        with unittest.mock.patch("subprocess.run", return_value=mock_result):
            result = inserter.test_insertion()

            assert result is True

    def test_test_insertion_clipboard(self, test_config: "ww.Config") -> None:
        """Test insertion capability test for clipboard."""
        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which"
        ) as mock_which:
            # No direct tools available, should fallback to clipboard
            mock_which.side_effect = (
                lambda tool: tool == "wl-copy" if tool in ["wl-copy", "xclip"] else None
            )

            inserter = text_inserter.TextInserter(test_config)
            result = inserter.test_insertion()

            assert result is True

    def test_test_insertion_failure(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test insertion capability test failure."""
        with unittest.mock.patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd")
        ):
            result = text_inserter.test_insertion()

            assert result is False

    def test_get_available_methods(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test getting available methods."""
        # Set up known available methods
        text_inserter._available_methods = {
            text_inserter_module.TextInsertionMethod.YDOTOOL: True,
            text_inserter_module.TextInsertionMethod.CLIPBOARD: True,
            text_inserter_module.TextInsertionMethod.WTYPE: False,
            text_inserter_module.TextInsertionMethod.XDOTOOL: False,
        }

        methods = text_inserter.get_available_methods()

        assert set(methods) == {"ydotool", "clipboard"}

    def test_get_preferred_method(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test getting preferred method."""
        method = text_inserter.get_preferred_method()

        assert method == "ydotool"

    def test_get_preferred_method_none(self, test_config: "ww.Config") -> None:
        """Test getting preferred method when none available."""
        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which", return_value=None
        ):
            # This should still have clipboard as fallback
            inserter = text_inserter.TextInserter(test_config)
            method = inserter.get_preferred_method()

            assert method == "clipboard"

    def test_close(self, text_inserter: text_inserter_module.TextInserter) -> None:
        """Test text inserter cleanup."""
        # Should not raise any errors
        text_inserter.close()


class TestCreateTextInserter:
    """Test cases for TextInserter.new static method."""

    def test_create_text_inserter_success(self, test_config: "ww.Config") -> None:
        """Test successful text inserter creation."""
        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which",
            return_value="/usr/bin/tool",
        ):
            inserter = text_inserter.TextInserter.new(test_config)

            assert isinstance(inserter, text_inserter.TextInserter)
            assert inserter.config == test_config

    def test_create_text_inserter_no_methods_available(self, test_config: "ww.Config") -> None:
        """Test creation when no methods are available."""
        with unittest.mock.patch(
            "whisper_wayland.text_inserter.capability_tester.shutil.which"
        ) as mock_which:
            # Make only clipboard tools unavailable to force error
            mock_which.return_value = None

            # Even with no tools, clipboard should be available as fallback
            inserter = text_inserter.TextInserter.new(test_config)
            assert isinstance(inserter, text_inserter.TextInserter)
