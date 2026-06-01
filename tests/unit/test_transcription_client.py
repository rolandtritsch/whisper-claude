"""Whisper Wayland - Transcription Client Tests

Unit tests for transcription client module including
OpenAI API integration and error handling."""

import os
import unittest.mock

import openai
import pytest

import whisper_wayland as ww
import whisper_wayland.transcription_client as transcription_client


class TestTranscriptionClient:
    """Test cases for TranscriptionClient class."""

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcription_client_initialization(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription client initialization."""
        mock_client = unittest.mock.Mock()
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)

        assert client.config == test_config
        assert client._client == mock_client
        mock_openai_class.assert_called_once_with(api_key=test_config.openai_api_key)

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcription_client_initialization_failure(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription client initialization failure."""
        mock_openai_class.side_effect = Exception("OpenAI init failed")

        with pytest.raises(
            transcription_client.TranscriptionError, match="OpenAI client initialization failed"
        ):
            transcription_client.TranscriptionClient(test_config)

    def test_model_name_mapping(self, test_config: "ww.Config") -> None:
        """Test model name mapping to API-compatible names."""
        with unittest.mock.patch(
            "whisper_wayland.transcription_client.client_validator.openai.OpenAI"
        ):
            client = transcription_client.TranscriptionClient(test_config)

            # Test various model mappings
            assert client._map_model_name("tiny") == "whisper-1"
            assert client._map_model_name("base") == "whisper-1"
            assert client._map_model_name("large-v3") == "whisper-1"
            assert client._map_model_name("whisper-1") == "whisper-1"
            assert client._map_model_name("unknown") == "whisper-1"

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_audio_success(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test successful audio transcription."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_transcription.create.return_value = "This is transcribed text."
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)

        test_audio = b"fake_audio_data"
        result = client.transcribe_audio(test_audio)

        assert result == "This is transcribed text."
        mock_transcription.create.assert_called_once()

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_audio_empty_data(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription with empty audio data."""
        mock_client = unittest.mock.Mock()
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)

        result = client.transcribe_audio(b"")
        assert result is None

        result = client.transcribe_audio(None)  # type: ignore[arg-type]
        assert result is None

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_audio_api_errors(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription with various OpenAI API errors."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        test_audio = b"fake_audio_data"

        # Test rate limit error
        mock_transcription.create.side_effect = openai.RateLimitError(
            "Rate limit exceeded", response=unittest.mock.Mock(), body=None
        )
        with pytest.raises(
            transcription_client.TranscriptionError, match="API rate limit exceeded"
        ):
            client.transcribe_audio(test_audio)

        # Test authentication error
        mock_transcription.create.side_effect = openai.AuthenticationError(
            "Invalid API key", response=unittest.mock.Mock(), body=None
        )
        with pytest.raises(transcription_client.TranscriptionError, match="API error"):
            client.transcribe_audio(test_audio)

        # Test general API error
        mock_request = unittest.mock.Mock()
        mock_transcription.create.side_effect = openai.APIError(
            "API error", request=mock_request, body=None
        )
        with pytest.raises(transcription_client.TranscriptionError, match="API error"):
            client.transcribe_audio(test_audio)

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_audio_with_retries(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription with retry logic."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        test_audio = b"fake_audio_data"

        # First call fails, second succeeds
        mock_transcription.create.side_effect = [
            Exception("Temporary error"),
            "Transcription successful",
        ]

        with unittest.mock.patch("time.sleep"):  # Speed up test by mocking sleep
            result = client.transcribe_audio(test_audio, max_retries=2)

        assert result == "Transcription successful"
        assert mock_transcription.create.call_count == ww.Constants.EXPECTED_DEVICE_COUNT

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_audio_max_retries_exceeded(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription when max retries are exceeded."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_transcription.create.side_effect = Exception("Persistent error")
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        test_audio = b"fake_audio_data"

        with unittest.mock.patch("time.sleep"):  # Speed up test
            with pytest.raises(
                transcription_client.TranscriptionError, match="Transcription failed"
            ):
                client.transcribe_audio(test_audio, max_retries=1)

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_audio_empty_result(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription with empty result."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_transcription.create.return_value = ""
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        test_audio = b"fake_audio_data"

        result = client.transcribe_audio(test_audio)
        assert result == ""

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_test_connection_success(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test successful API connection test."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_transcription.create.return_value = "Test successful"
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        result = client.test_connection()

        assert result is True
        mock_transcription.create.assert_called_once()

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_test_connection_failure(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test API connection test failure."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_transcription.create.side_effect = Exception("Connection failed")
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        result = client.test_connection()

        assert result is False

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_create_test_audio(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test creation of test audio data."""
        mock_client = unittest.mock.Mock()
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        test_audio = client._create_test_audio()

        assert isinstance(test_audio, bytes)
        assert len(test_audio) > ww.Constants.WAV_HEADER_SIZE  # Should include WAV header

        # Check WAV header magic
        assert test_audio.startswith(b"RIFF")
        assert b"WAVE" in test_audio[:12]

    def test_get_supported_models(self, test_config: "ww.Config") -> None:
        """Test getting supported models list."""
        with unittest.mock.patch(
            "whisper_wayland.transcription_client.client_validator.openai.OpenAI"
        ):
            client = transcription_client.TranscriptionClient(test_config)
            models = client.get_supported_models()

            assert isinstance(models, list)
            assert "whisper-1" in models
            assert "base" in models
            assert "large-v3" in models

    def test_get_supported_languages(self, test_config: "ww.Config") -> None:
        """Test getting supported languages list."""
        with unittest.mock.patch(
            "whisper_wayland.transcription_client.client_validator.openai.OpenAI"
        ):
            client = transcription_client.TranscriptionClient(test_config)
            languages = client.get_supported_languages()

            assert isinstance(languages, list)
            assert "en" in languages
            assert "es" in languages
            assert "fr" in languages

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_client_close(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription client cleanup."""
        mock_client = unittest.mock.Mock()
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        client.close()

        assert client._client is None

    @unittest.mock.patch("whisper_wayland.transcription_client.client_validator.openai.OpenAI")
    def test_transcribe_with_custom_language(
        self, mock_openai_class: unittest.mock.MagicMock, test_config: "ww.Config"
    ) -> None:
        """Test transcription with custom language parameter."""
        mock_client = unittest.mock.Mock()
        mock_transcription = unittest.mock.Mock()
        mock_transcription.create.return_value = "Texto transcrito"
        mock_client.audio.transcriptions = mock_transcription
        mock_openai_class.return_value = mock_client

        client = transcription_client.TranscriptionClient(test_config)
        test_audio = b"fake_audio_data"

        result = client.transcribe_audio(test_audio, language="es")

        assert result == "Texto transcrito"
        # Verify the correct parameters were passed
        call_args = mock_transcription.create.call_args
        assert call_args.kwargs["language"] == "es"

    def test_create_transcription_client(self) -> None:
        """Test TranscriptionClient.new static method."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "sk-test123"}):
            test_config = ww.Config()

        with unittest.mock.patch(
            "whisper_wayland.transcription_client.TranscriptionClient.__init__", return_value=None
        ):
            result = transcription_client.TranscriptionClient.new(test_config)

            assert isinstance(result, transcription_client.TranscriptionClient)
