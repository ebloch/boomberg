# Claude Code Instructions

## Development Approach

Use **Red-Green TDD** (Test-Driven Development) when building features or fixing bugs:

1. **Red**: Write a failing test first that describes the expected behavior
2. **Green**: Write the minimum code needed to make the test pass
3. **Refactor**: Clean up the code while keeping tests green

## Running Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/unit/services/test_portfolio.py

# Run specific test
python -m pytest tests/unit/services/test_portfolio.py::TestPortfolioService::test_name -v

# Run with verbose output
python -m pytest -v
```

## Project Structure

- `src/boomberg/` - Main application code
- `tests/unit/` - Unit tests
- `~/.boomberg/` - User data directory (portfolio.json, etc.)
