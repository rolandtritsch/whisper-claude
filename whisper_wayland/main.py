"""Whisper Wayland - Main Entry Point

A push-to-talk voice transcription service that converts speech to text
and inserts it at the cursor position in any application.
"""

import os
import sys

import whisper_wayland as ww


def main() -> None:
    """Main entry point for the application."""
    try:
        if len(sys.argv) > 1:
            print("Error: whisper-wayland does not accept command-line arguments")
            print("Set WHISPER_WAYLAND_ENV_FILE to load a custom environment file")
            sys.exit(1)

        env_file = os.getenv("WHISPER_WAYLAND_ENV_FILE")
        if env_file:
            env_file = env_file.strip()
            if not os.path.exists(env_file):
                print(f"Error: Environment file '{env_file}' not found")
                sys.exit(1)

        # Create and run application
        app = ww.Application(env_file or None)
        app.run()
        sys.exit(0)

    except ww.ConfigError as e:
        print(f"Configuration error: {e}")
        print("Please check your environment variables or .env file")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
