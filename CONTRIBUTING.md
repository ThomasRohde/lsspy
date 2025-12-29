# Contributing to lsspy

Thank you for your interest in contributing to lsspy! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git

### Setting Up Your Development Environment

1. **Fork and Clone the Repository**

   ```bash
   git clone https://github.com/YOUR_USERNAME/lsspy.git
   cd lsspy
   ```

2. **Install Development Dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

   This installs lsspy in editable mode along with all development dependencies including pytest, ruff, and mypy.

3. **Verify Installation**

   ```bash
   lsspy --version
   ```

## Development Workflow

### Running Tests

Run the test suite with pytest:

```bash
pytest tests/ -v
```

For coverage reporting:

```bash
pytest tests/ --cov=lsspy --cov-report=html
```

### Code Style

This project uses [ruff](https://github.com/astral-sh/ruff) for linting and formatting.

**Check linting:**

```bash
ruff check src/ tests/
```

**Check formatting:**

```bash
ruff format --check src/ tests/
```

**Auto-fix issues:**

```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

### Type Checking

This project uses mypy for static type checking:

```bash
mypy src/
```

All code should include type annotations and pass mypy checks.

## Making Changes

### Before You Start

1. Check existing [issues](https://github.com/lodestar-cli/lsspy/issues) to see if your feature or bug has been reported
2. For new features, open an issue first to discuss the approach
3. Create a new branch for your changes

### Pull Request Process

1. **Create a Feature Branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Your Changes**

   - Write clear, concise commit messages
   - Follow the existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run Tests and Checks**

   Before submitting, ensure all checks pass:

   ```bash
   # Run tests
   pytest tests/ -v
   
   # Check linting
   ruff check src/ tests/
   
   # Check formatting
   ruff format --check src/ tests/
   
   # Type check
   mypy src/
   ```

4. **Push Your Changes**

   ```bash
   git push origin feature/your-feature-name
   ```

5. **Open a Pull Request**

   - Go to the GitHub repository and click "New Pull Request"
   - Provide a clear description of your changes
   - Reference any related issues (e.g., "Fixes #123")
   - Wait for CI checks to pass
   - Respond to any review feedback

## Reporting Issues

When reporting issues, please include:

- A clear, descriptive title
- Steps to reproduce the problem
- Expected behavior
- Actual behavior
- Your environment (Python version, OS, etc.)
- Any relevant error messages or logs

Use the [issue templates](https://github.com/lodestar-cli/lsspy/issues/new/choose) when available.

## Code Review Guidelines

- Be respectful and constructive
- Focus on the code, not the person
- Explain your reasoning
- Be open to feedback

## Questions?

If you have questions or need help, feel free to:

- Open an issue on GitHub
- Check existing documentation in the [README](README.md)
- Review the [Lodestar documentation](https://github.com/lodestar-cli/lodestar)

## License

By contributing to lsspy, you agree that your contributions will be licensed under the MIT License.
