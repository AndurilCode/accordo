# Project Configuration

## Project Structure
<!-- Describe the main directories and their purposes -->
- `src/` - Source code
- `tests/` - Test files
- `docs/` - Documentation

## Dependencies
<!-- List key dependencies and their versions -->
- Python 3.8+
- FastMCP
- Pydantic

## Test Commands
<!-- Commands to run tests and linters -->
```bash
# Run tests
python -m pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## Build Commands
<!-- Commands to build/compile the project -->
```bash
# Install dependencies
uv sync

# Build package
python -m build
```

## Changelog
<!-- Project changelog entries -->
- Initial project setup 