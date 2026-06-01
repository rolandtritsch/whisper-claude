# Whisper Wayland - Developer Documentation

This document explains the architecture, implementation decisions, and development workflow for the Whisper Wayland voice-to-text service.

> **For users**: See [README.md][readme-md] for installation instructions, usage guide, and user documentation.

## Architecture Overview

### Design Philosophy

Whisper Wayland follows a **modular architecture** with clear separation of concerns:

- **Application Layer**: Main orchestrator that coordinates all components
- **Component Management**: Manages lifecycle of audio, transcription, key monitoring, and text insertion
- **Service Components**: Independent modules for core functionality
- **Configuration Management**: Environment-based configuration with validation

### Core Components

#### 1. Application (`whisper_wayland/application/`)
- **`application.py`**: Main orchestrator coordinating all components
- **`component_manager.py`**: Creates and manages component instances
- **`runtime.py`**: Handles main application loop and signal management
- **`hotkey_handler.py`**: Manages push-to-talk functionality
- **`transcription_processor.py`**: Processes audio data through transcription pipeline

#### 2. Audio Recording (`whisper_wayland/audio_recorder/`)
- **`audio_recorder.py`**: High-level audio recording interface
- **`recording_engine.py`**: Low-level PyAudio recording implementation
- **`audio_system_validator.py`**: Validates audio system availability
- **`wav_converter.py`**: Converts audio frames to WAV format

#### 3. Key Monitoring (`whisper_wayland/key_monitor/`)
- **`key_monitor.py`**: High-level keyboard monitoring interface
- **`monitor_loop.py`**: Main monitoring loop with device handling
- **`event_handler.py`**: Processes key events and triggers callbacks
- **`device_manager.py`**: Manages input device discovery and lifecycle
- **`key_mapping.py`**: Handles key combination parsing and mapping

#### 4. Text Insertion (`whisper_wayland/text_inserter/`)
- **`text_inserter.py`**: High-level text insertion interface
- **`method_executors.py`**: Implements different insertion methods (wtype, ydotool, xdotool, clipboard)
- **`capability_tester.py`**: Tests which insertion methods are available
- **`fallback_handler.py`**: Manages fallback between insertion methods
- **`text_processor.py`**: Cleans and processes text for insertion

#### 5. Transcription Client (`whisper_wayland/transcription_client/`)
- **`transcription_client.py`**: High-level OpenAI API interface
- **`transcription_engine.py`**: Handles API communication and retry logic
- **`model_mapper.py`**: Maps model names to API parameters
- **`connection_tester.py`**: Tests API connectivity
- **`test_audio_generator.py`**: Generates test audio for validation

#### 6. Configuration (`whisper_wayland/config/`)
- **`config.py`**: Main configuration orchestrator
- **`property_handlers.py`**: Environment variable processing and validation
- **`config_validator.py`**: Configuration validation and requirements checking
- **`env_loader.py`**: Environment file loading (.env support)
- **`logging_setup.py`**: Logging configuration and setup

### Key Design Decisions

#### Why Modular Architecture?
- **Testability**: Each component can be tested in isolation
- **Maintainability**: Clear boundaries make changes safer and easier
- **Extensibility**: New components or alternatives can be added easily
- **Debugging**: Issues can be traced to specific components

#### Why Configuration-First Design?
- **Environment Variables**: Follows 12-factor app principles
- **No Hard-coding**: All behavior can be controlled externally
- **Easy Deployment**: Configuration changes don't require code changes
- **Testing**: Different configurations can be tested independently

#### Why Push-to-Talk vs. Voice Activation?
- **Privacy**: Audio only sent when user explicitly requests it
- **Accuracy**: No false triggers from background noise
- **Control**: User has complete control over when transcription occurs
- **Cost**: Only pay for intentional transcriptions

## Development Workflow

### Repository Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rolandtritsch/whisper-wayland.git
   cd whisper-wayland
   ```

2. **Install dependencies:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh  # Install uv
   uv sync  # Install project dependencies
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and add your WW_OPENAI_API_KEY
   ```

### Branch Management

**Branch naming convention:**
- Format: `roland/<ticket-id>/<3-word-description>`
- If no ticket exists: `roland/ad-hoc/<3-word-description>`
- Examples:
  - `roland/ISSUE-123/fix-audio-recording`
  - `roland/ad-hoc/update-dependencies`

**Creating a branch:**
```bash
git checkout trunk
git pull origin trunk
git checkout -b roland/<ticket-id>/<3-word-description>
```

### Pull Request Process

**PR title format:**
- `<ticket-id>: <3-word-description>`
- Examples:
  - `ISSUE-123: Fix audio recording`
  - `ad-hoc: Update dependencies`

**Creating a PR:**
```bash
# Push your branch
git push -u origin roland/<ticket-id>/<3-word-description>

# Create PR with gh CLI
gh pr create --title "<ticket-id>: <3-word-description>" --body ""
```

### Development Standards

#### Code Quality Requirements
- **All tests must pass**: Both unit and integration tests
- **80% code coverage minimum**: Measured by pytest-cov
- **Type checking**: All code must pass mypy validation
- **Code formatting**: All code must pass ruff formatting and linting

#### Running Quality Checks
```bash
# Run all tests
make tests

# Run code quality checks
make check

# Fix formatting issues
make format-fix
```

#### Commit Guidelines
- **Commit often**: Small, focused commits are preferred
- **Descriptive messages**: Explain the "why", not just the "what"
- **Test before commit**: Ensure tests pass before each commit

### Testing Strategy

#### Test Structure
```
tests/
├── unit/           # Fast, isolated tests with mocks
├── integration/    # End-to-end tests with real dependencies  
└── conftest.py     # Shared test configuration and fixtures
```

#### Testing Principles
- **Unit tests**: Mocked, no external dependencies, test single components
- **Integration tests**: End-to-end, real dependencies, test complete workflows
- **Test isolation**: Each test should be independent and repeatable
- **Mock reuse**: Common mocks defined in `tests/unit/conftest.py`

#### Running Tests
```bash
# Run all tests
make tests

# Run only unit tests
make tests-unit

# Run only integration tests  
make tests-integration

# Run with coverage report
uv run pytest --cov=whisper_wayland --cov-report=html
```

### Merging and Cleanup

**Merge process:**
```bash
# Ensure your PR is up to date
git checkout trunk
git pull origin trunk
git checkout your-branch
git rebase trunk

# Push updates
git push --force-with-lease

# Squash merge via GitHub UI or gh CLI
gh pr merge --squash --delete-branch
```

**Post-merge cleanup:**
```bash
git checkout trunk
git pull origin trunk
git branch -d your-branch-name
```

### Common Development Tasks

#### Adding New Configuration
1. Add property method to `config/property_handlers.py`
2. Add property to main `config/config.py`
3. Add to `.env.example` with documentation
4. Add tests in `tests/unit/test_config.py`
5. Update README.md configuration table if user-facing

#### Adding New Component
1. Create new module directory under `whisper_wayland/`
2. Add `__init__.py` with public interface exports
3. Implement component following existing patterns
4. Add to `application/component_manager.py` if needed
5. Add unit tests in `tests/unit/`
6. Add integration tests if component has external dependencies

#### Debugging Tips
1. **Enable debug logging**: `WW_LOG_LEVEL=DEBUG uv run whisper-wayland`
2. **Component isolation**: Test individual components in isolation
3. **Mock external services**: Use mocks to isolate issues
4. **Check configuration**: Verify environment variables are correct

### Architecture Trade-offs

#### Current Limitations
- **Linux/Wayland only**: Designed specifically for modern Linux desktops
- **OpenAI dependency**: Requires internet and OpenAI API access
- **Python performance**: Not optimized for absolute minimum latency
- **Single hotkey**: Only supports one global hotkey combination

#### Future Extensibility Points
- **Multiple transcription providers**: Architecture supports pluggable transcription backends
- **Additional text insertion methods**: New insertion methods can be added easily
- **Custom hotkey combinations**: Framework supports complex hotkey patterns
- **Local transcription**: Could add local Whisper model support

## Project Structure

```
whisper-wayland/
├── whisper_wayland/           # Main package
│   ├── application/           # Application orchestration
│   ├── audio_recorder/        # Audio recording components
│   ├── key_monitor/           # Keyboard monitoring
│   ├── text_inserter/         # Text insertion methods
│   ├── transcription_client/  # OpenAI API integration
│   ├── config/                # Configuration management
│   ├── constants.py           # Application constants
│   └── main.py                # Entry point
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py            # Test configuration
├── .env.example               # Environment template
├── pyproject.toml             # Project configuration
├── Makefile                   # Development commands
├── README.md                  # User documentation
└── CLAUDE.md                  # Developer documentation (this file)
```

## Contributing Guidelines

1. **Follow the workflow**: Use the branch naming and PR process described above
2. **Write tests**: All new functionality must include appropriate tests
3. **Document changes**: Update documentation for user-facing changes
4. **Review thoroughly**: PRs require passing CI and code review
5. **Keep PRs focused**: One feature or fix per PR
6. **Communicate**: Use GitHub issues and discussions for planning

---

**For users**: See [README.md][readme-md] for installation instructions and usage guide.

[readme-md]: ./README.md