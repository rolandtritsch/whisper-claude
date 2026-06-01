"""Whisper Wayland - Real API Integration Tests

Integration tests using real OpenAI API. These tests require
a valid WW_OPENAI_API_KEY environment variable and will make
actual API calls to OpenAI.
"""

import os
import tempfile
import unittest.mock

import pytest

import whisper_wayland as ww
import whisper_wayland.transcription_client as transcription_client


class TestRealAPIIntegration:
    """Integration tests with real OpenAI API."""

    @pytest.fixture
    def test_config(self) -> "ww.Config":
        """Create configuration for real API testing."""
        api_key = os.environ.get("WW_OPENAI_API_KEY")
        if not api_key:
            pytest.skip("WW_OPENAI_API_KEY not set, skipping real API tests")

        return ww.Config()

    def test_real_api_connection(self, test_config: "ww.Config") -> None:
        """Test connection to real OpenAI API."""
        client = transcription_client.TranscriptionClient.new(test_config)

        # Test connection
        result = client.test_connection()

        assert result is True
        client.close()

    def test_real_api_transcription_with_test_audio(self, test_config: "ww.Config") -> None:
        """Test transcription with minimal test audio."""
        client = transcription_client.TranscriptionClient.new(test_config)

        try:
            # Use the client's test audio (minimal silence)
            test_audio = client._create_test_audio()

            # Transcribe the test audio
            result = client.transcribe_audio(test_audio, max_retries=1)

            # Result should be a string (may be empty for silence)
            assert isinstance(result, str)

        finally:
            client.close()

    def test_real_api_with_various_models(self, test_config: "ww.Config") -> None:
        """Test transcription with different model configurations."""
        models_to_test = ["base", "tiny", "whisper-1"]

        for model in models_to_test:
            # Update config for this model
            with unittest.mock.patch.dict(os.environ, {"WW_WHISPER_MODEL": model}):
                model_config = ww.Config()

                client = transcription_client.TranscriptionClient.new(model_config)

                try:
                    # Test connection with this model
                    result = client.test_connection()
                    assert result is True

                finally:
                    client.close()

    def test_real_api_error_handling(self, test_config: "ww.Config") -> None:
        """Test error handling with real API."""
        # Create client with invalid model to test validation
        client = transcription_client.TranscriptionClient.new(test_config)

        try:
            # Test with empty audio (should handle gracefully)
            result = client.transcribe_audio(b"", max_retries=1)
            assert result is None

            # Test with very small invalid audio data
            result = client.transcribe_audio(b"invalid", max_retries=1)
            # Should either return None or raise TranscriptionError
            assert result is None or isinstance(result, str)

        finally:
            client.close()

    def test_real_api_language_parameter(self, test_config: "ww.Config") -> None:
        """Test transcription with language parameter."""
        client = transcription_client.TranscriptionClient.new(test_config)

        try:
            test_audio = client._create_test_audio()

            # Test with English
            result_en = client.transcribe_audio(test_audio, language="en", max_retries=1)
            assert isinstance(result_en, str)

            # Test with Spanish (should still work with silence)
            result_es = client.transcribe_audio(test_audio, language="es", max_retries=1)
            assert isinstance(result_es, str)

        finally:
            client.close()

    def test_real_api_supported_features(self, test_config: "ww.Config") -> None:
        """Test supported models and languages."""
        client = transcription_client.TranscriptionClient.new(test_config)

        try:
            # Test supported models list
            models = client.get_supported_models()
            assert isinstance(models, list)
            assert len(models) > 0
            assert "whisper-1" in models

            # Test supported languages list
            languages = client.get_supported_languages()
            assert isinstance(languages, list)
            assert len(languages) > 0
            assert "en" in languages

        finally:
            client.close()


class TestConfigurationIntegration:
    """Integration tests for configuration loading."""

    def test_config_with_real_env_file(self) -> None:
        """Test configuration loading from real .env file."""
        api_key = os.environ.get("WW_OPENAI_API_KEY")
        if not api_key:
            pytest.skip("WW_OPENAI_API_KEY not set, skipping env file test")

        # Create temporary .env file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(f"WW_OPENAI_API_KEY={api_key}\n")
            f.write("WW_WHISPER_MODEL=large\n")
            f.write(f"WW_AUDIO_SAMPLE_RATE={ww.Constants.HIGH_QUALITY_SAMPLE_RATE}\n")
            f.write("WW_LOG_LEVEL=DEBUG\n")
            env_file_path = f.name

        # Temporarily remove environment variables to test .env file loading
        old_env = {}
        env_vars_to_clear = ["WW_LOG_LEVEL", "WW_WHISPER_MODEL", "WW_AUDIO_SAMPLE_RATE"]
        for var in env_vars_to_clear:
            if var in os.environ:
                old_env[var] = os.environ.pop(var)

        try:
            # Load config from env file
            test_config = ww.Config(env_file_path)

            assert test_config.openai_api_key == api_key
            assert test_config.whisper_model == "large"
            assert test_config.audio_sample_rate == ww.Constants.HIGH_QUALITY_SAMPLE_RATE
            assert test_config.log_level == "DEBUG"

        finally:
            # Restore environment variables if they existed
            for var, value in old_env.items():
                os.environ[var] = value
            os.unlink(env_file_path)

    def test_config_validation_with_invalid_api_key(self) -> None:
        """Test configuration validation with invalid API key format."""
        with unittest.mock.patch.dict(os.environ, {"WW_OPENAI_API_KEY": "invalid-key-format"}):
            # Should still create config (validation happens at API level)
            invalid_config = ww.Config()
            assert invalid_config.openai_api_key == "invalid-key-format"

            # But transcription client should fail on API calls
            client = transcription_client.TranscriptionClient.new(invalid_config)

            try:
                # Connection test should fail
                result = client.test_connection()
                assert result is False

            finally:
                client.close()


@pytest.mark.slow
class TestEndToEndIntegration:
    """End-to-end integration tests (marked as slow)."""

    def test_full_audio_workflow_simulation(self) -> None:
        """Test full workflow simulation without actual audio recording."""
        api_key = os.environ.get("WW_OPENAI_API_KEY")
        if not api_key:
            pytest.skip("WW_OPENAI_API_KEY not set, skipping E2E test")

        # Create config
        test_config = ww.Config()

        # Create transcription client
        trans_client = transcription_client.TranscriptionClient.new(test_config)

        try:
            # Test connection
            assert trans_client.test_connection() is True

            # Simulate audio data (use test audio)
            audio_data = trans_client._create_test_audio()
            assert audio_data is not None
            assert len(audio_data) > 0

            # Transcribe audio
            transcription = trans_client.transcribe_audio(audio_data)
            assert isinstance(transcription, str)

            # Simulate saving to file
            with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
                f.write(f"Test transcription: {transcription}\n")
                temp_file = f.name

            try:
                # Verify file was created and has content
                with open(temp_file) as f:
                    content = f.read()
                    assert "Test transcription:" in content

            finally:
                os.unlink(temp_file)

        finally:
            trans_client.close()
