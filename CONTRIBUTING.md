# Contributing to Debian Desktop Optimizer

Thank you for your interest in contributing!

## Ways to Contribute

- Report bugs via GitHub Issues
- Suggest new cleanup categories
- Add missing language definitions to `languages.yaml`
- Improve documentation
- Write tests
- Submit pull requests

## Pull Request Checklist

- [ ] Tests pass (`pytest -m "not gui"`)
- [ ] Ruff clean (`ruff check src/ tests/`)
- [ ] Black formatted (`black src/ tests/`)
- [ ] Mypy clean (`mypy src/ddo/backend/`)
- [ ] Conventional commit message
- [ ] Updated CHANGELOG if applicable

## Code of Conduct

Be respectful. We follow the [Debian Code of Conduct](https://www.debian.org/code_of_conduct).

## License

All contributions are licensed under GPL-3.0-only.
