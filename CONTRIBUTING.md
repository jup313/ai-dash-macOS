# Contributing to ai-dash-macOS

Thank you for your interest in contributing!

## Requirements

- macOS with Apple Silicon (ARM64)
- Python 3.11+
- Node 18+ (ARM64 native)
- Ollama installed locally

## Setup

```bash
git clone https://github.com/YOUR_USERNAME/ai-dash-macOS.git
cd ai-dash-macOS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Development Rules

### Code Standards
- All Python code must be async-first
- No blocking I/O in async contexts
- No CPU-bound loops without proper handling
- Use `orjson` for JSON serialization
- Use `httpx` for HTTP clients (async)

### Architecture Rules
- No business logic in API routes
- No circular imports
- All LLM calls go through LLMRouter
- No direct provider usage
- Clear separation of concerns

### Sterility Rules
- Never commit personal data
- No API keys, tokens, or passwords in code
- No absolute paths
- No machine-specific directories
- All config via environment variables
- Only `localhost` may be hardcoded

### Apple Silicon Rules
- ARM64 native only
- No Rosetta dependencies
- No x86 binaries
- Docker must target `linux/arm64`

### Memory Rules
- Operate within 28GB unified memory
- Max 1 heavy model loaded at a time
- Max 2 concurrent agent tasks
- Heavy model auto-unload after inactivity
- Block heavy model load if RAM > 75%

## Testing

```bash
pytest backend/tests/ -v
```

All tests must pass before submitting a PR.

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Code of Conduct

Be respectful, constructive, and inclusive.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
