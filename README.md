# Whisper Wayland - Voice-to-Text Service

[![CI][ci-badge]][ci-url]

A push-to-talk voice transcription service that converts speech to text and inserts it at the cursor position in any application. Built for Ubuntu/Wayland without requiring root access.

## What is Whisper Wayland?

Whisper Wayland is a lightweight voice-to-text service that lets you dictate text directly into any application using a simple push-to-talk hotkey. Perfect for:

- **Writing emails and documents** - Dictate naturally instead of typing
- **Coding with voice** - Add comments or documentation quickly
- **Accessibility** - Alternative input method for users with typing difficulties
- **Multi-tasking** - Keep your hands free while entering text

The service runs in the background and works with any application that accepts text input - from web browsers to text editors to chat applications.

## Key Features

- **Push-to-Talk**: Hold Compose key to record, release to transcribe and insert
- **Universal Text Insertion**: Works with any application that accepts text input
- **Wayland Support**: Native support for modern Linux desktop environments
- **High Accuracy**: Uses OpenAI's Whisper API for accurate speech recognition
- **Privacy Focused**: Audio is only sent to OpenAI for transcription, not stored locally
- **Simple Deployment**: Runs natively on your Linux desktop

## Quick Start

### Prerequisites

You'll need:
- Ubuntu/Debian or Fedora/RHEL Linux system with Wayland
- [OpenAI API key][openai-api-keys] (pay-per-use, typically $0.006 per minute)
- Python 3.11+

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install portaudio19-dev python3-dev wtype

# Fedora/RHEL
sudo dnf install portaudio-devel python3-devel wtype
```

### Installation

#### Installation

1. **Install [uv][uv-install] package manager:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Clone and install:**
   ```bash
   git clone https://github.com/rolandtritsch/whisper-wayland.git
   cd whisper-wayland
   uv sync
   ```

3. **Configure your API key:**
   ```bash
   # Create and configure .env file
   cp .env.example .env
   nano .env  # Add your WW_OPENAI_API_KEY
   ```

4. **Run the service:**
   ```bash
   uv run whisper-wayland
   ```


## How to Use

1. **Start the service** using the installation method above
2. **Position your cursor** where you want text to appear in any application
3. **Press and hold the Compose key** (usually right Alt or Menu key)
4. **Speak clearly** while holding the key
5. **Release the key** - transcribed text appears at your cursor position

### Usage Tips

- **Speak naturally** - Whisper handles conversational speech well
- **Use punctuation commands** - Say "period", "comma", "question mark", etc.
- **Keep recordings under 30 seconds** - Default maximum recording duration
- **Ensure good audio quality** - Use a decent microphone for best results

## Configuration

All configuration is handled through environment variables and/or a/the `.env` file:

To load a custom environment file, set `WW_ENV_FILE` before starting:

```bash
WW_ENV_FILE=/path/to/custom.env uv run whisper-wayland
```

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WW_ENV_FILE` | Path to custom environment file to load before configuration | - | No |
| `WW_OPENAI_API_KEY` | OpenAI API key for Whisper service | - | Yes |
| `WW_WHISPER_MODEL` | Model to use (tiny, base, small, medium, large) | `base` | No |
| `WW_AUDIO_SAMPLE_RATE` | Audio recording sample rate | `16000` | No |
| `WW_AUDIO_CHUNK_SIZE` | Audio recording chunk size in samples | `1024` | No |
| `WW_MAX_RECORDING_DURATION` | Maximum recording duration in seconds | `30` | No |
| `WW_MIC_STARTUP_CHECK` | Startup microphone check mode (none, auto, manual) | `none` | No |
| `WW_MIC_CHECK_DURATION` | Microphone startup check duration in seconds | `1.0` | No |
| `WW_SUPPRESS_AUDIO_WARNINGS` | Hide native ALSA/JACK warning output during audio probing | `true` | No |
| `WW_LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` | No |
| `WW_HOTKEY` | Push-to-talk key combination | `ctrl+compose` | No |
| `WW_TEXT_INSERTION_DELAY` | Delay before inserting transcribed text in seconds | `0.1` | No |
| `WW_TEXT_INSERTION_METHOD` | Text insertion method (wtype, ydotool, xdotool, clipboard) | `ydotool` | No |

`WW_MIC_STARTUP_CHECK=auto` samples the selected microphone and reports signal levels.
`WW_MIC_STARTUP_CHECK=manual` prompts you to count from 1 to 10, records the sample,
transcribes it, and verifies that the count was recognized.

### Model Selection Guide

- **tiny**: Fastest, least accurate, cheapest (~$0.0024/min)
- **base**: Good balance of speed and accuracy (~$0.006/min) **Recommended**
- **small**: Better accuracy, slightly slower (~$0.006/min)
- **medium**: High accuracy, slower (~$0.012/min)
- **large**: Best accuracy, slowest (~$0.018/min)

## Troubleshooting

### Common Issues

**Audio not recording:**
- Check your user is in the `audio` group: `sudo usermod -a -G audio $USER`
- Log out and back in after group changes
- Test microphone: `arecord -d 5 test.wav && aplay test.wav`

**Text not inserting:**
- Verify `wtype` is installed: `which wtype`
- Test manually: `echo "test" | wtype -`
- Check Wayland environment variables are set

**Hotkey not working:**
- Verify Compose key is configured: e.g. `setxkbmap -option compose:lctrl`
- Check if another application is using the key
- Try alternative keys by setting `WW_HOTKEY` environment variable

**Service fails to start:**
- Check your OpenAI API key is valid
- Ensure all system dependencies are installed
- Enable debug logging: `WW_LOG_LEVEL=DEBUG`

### Getting Help

For detailed troubleshooting and logs:

```bash
# Enable debug logging
export WW_LOG_LEVEL=DEBUG
uv run whisper-wayland
```

## Cost Considerations

Whisper Wayland uses OpenAI's API on a pay-per-use basis:
- **Typical usage**: $0.006 per minute of audio
- **Example**: 1 hour of dictation per day ≈ $10-15/month
- **Factors**: Longer recordings and higher-quality models cost more

## Privacy & Security

- **Audio processing**: Audio is sent to OpenAI for transcription only
- **No local storage**: Audio data is not saved to your computer
- **API key security**: Store your API key securely in `.env` file
- **Network only**: Service only activates when you press the hotkey

## Support & Contributing

- **Issues**: Report bugs and request features on [GitHub Issues][issues-url]
- **Contributing**: See [CLAUDE.md][claude-md] for development guidelines
- **Discussions**: Join community discussions on [GitHub Discussions][discussions-url]

## License

MIT License - see [LICENSE][license-url] file for details.

---

**For developers**: See [CLAUDE.md][claude-md] for architecture details, development workflow, and contribution guidelines.

[ci-badge]: https://github.com/rolandtritsch/whisper-wayland/actions/workflows/ci.yml/badge.svg
[ci-url]: https://github.com/rolandtritsch/whisper-wayland/actions/workflows/ci.yml
[openai-api-keys]: https://platform.openai.com/api-keys
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[issues-url]: https://github.com/rolandtritsch/whisper-wayland/issues
[discussions-url]: https://github.com/rolandtritsch/whisper-wayland/discussions
[license-url]: https://github.com/rolandtritsch/whisper-wayland/blob/trunk/LICENSE
[claude-md]: https://github.com/rolandtritsch/whisper-wayland/blob/trunk/CLAUDE.md
