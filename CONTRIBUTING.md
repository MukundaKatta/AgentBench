# Contributing to AgentBench

Thank you for your interest in contributing to AgentBench! This document provides guidelines for contributing to this project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Install development dependencies:

```bash
pip install -e ".[dev]"
```

## Development Workflow

1. Create a feature branch from `main`:

```bash
git checkout -b feature/your-feature-name
```

2. Make your changes, following the code style guidelines below.

3. Add or update tests as needed.

4. Run the full check suite:

```bash
make all
```

5. Commit your changes with a clear, descriptive message.

6. Push to your fork and open a Pull Request.

## Code Style

- We use **Ruff** for linting and formatting.
- Run `make lint` to check and `make format` to auto-format.
- Type hints are expected for all public functions.
- Docstrings follow the NumPy style.

## Testing

- All new features must include tests.
- Tests live in the `tests/` directory.
- Run `make test` to execute the test suite.

## Pull Request Process

1. Ensure all tests pass and linting is clean.
2. Update documentation if you changed public APIs.
3. Keep PRs focused — one feature or fix per PR.
4. Fill in the PR template with a clear description.

## Reporting Issues

- Use GitHub Issues to report bugs or request features.
- Include steps to reproduce, expected behaviour, and actual behaviour.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
