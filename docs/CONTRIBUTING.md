# Contributing to Path Manager

Thank you for your interest in contributing to Path Manager!

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

---

## Code of Conduct

This project follows a standard code of conduct:

- Be respectful and constructive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

### Prerequisites

- Python >=3.10
- Git
- Basic understanding of YAML and Python

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR-USERNAME/path-manager.git
cd path-manager

# Add upstream remote
git remote add upstream https://github.com/original/path-manager.git
```

---

## Development Setup

### 1. Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

### 2. Install Development Dependencies

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

This installs:
- `path-manager` (editable)
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `black` - Code formatting
- `mypy` - Type checking
- `ruff` - Linting

### 3. Verify Installation

```bash
# Run tests
pytest tests/ -v

# Should see: 76 passed
```

---

## Making Changes

### 1. Create a Branch

```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/my-new-feature

# Or bug fix branch
git checkout -b fix/issue-123
```

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test improvements

### 2. Make Your Changes

Keep changes focused:
- One feature or fix per branch
- Keep commits atomic and logical
- Write tests for new features
- Update documentation as needed

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_resolver.py -v

# Run specific test
pytest tests/test_resolver.py::TestPathResolverForward::test_resolve_kind_with_fields -v

# Run with coverage
pytest tests/ --cov=path_manager --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Writing Tests

Tests use pytest. Add tests to appropriate file in `tests/`:

```python
# tests/test_myfeature.py
import pytest
from path_manager.resolver import PathResolver

def test_my_new_feature():
    """Test description."""
    # Arrange
    resolver = PathResolver.from_file('schema.db')

    # Act
    result = resolver.some_new_method()

    # Assert
    assert result == expected_value

    # Cleanup
    resolver.close()
```

#### Test Fixtures

Use fixtures for common setup:

```python
@pytest.fixture
def resolver(tmp_path):
    """Provide resolver with test schema."""
    schema = tmp_path / "schema.db"
    compile_schema('test_schema.yml', schema)

    res = PathResolver.from_file(schema)
    yield res
    res.close()

def test_with_fixture(resolver):
    """Use fixture."""
    path = resolver.get_path('kind', root='/test', proj='demo')
    assert path.exists()
```

#### Parametrized Tests

Test multiple scenarios:

```python
@pytest.mark.parametrize('platform,root_regex', [
    ('linux', '/[A-Za-z0-9/_-]+'),
    ('windows', '[A-Za-z]:/[A-Za-z0-9/_-]+'),
])
def test_platform_roots(platform, root_regex):
    """Test platform-specific roots."""
    # ... test logic ...
```

### Test Coverage

Aim for >80% coverage for new code:

```bash
# Generate coverage report
pytest tests/ --cov=path_manager --cov-report=term-missing

# Check coverage of specific module
pytest tests/ --cov=path_manager.resolver --cov-report=term-missing
```

---

## Code Style

### Python Style Guide

Follow PEP 8 and project conventions:

```bash
# Format code with black
black src/path_manager tests/

# Check formatting (don't modify)
black --check src/path_manager tests/

# Lint with ruff
ruff check src/path_manager tests/

# Fix auto-fixable issues
ruff check --fix src/path_manager tests/
```

### Type Hints

Use type hints for all public APIs:

```python
from __future__ import annotations  # For Python 3.10
from pathlib import Path
from typing import Any

def get_path(
    self,
    kind: str,
    **fields: Any
) -> Path:
    """
    Generate path from kind and fields.

    Args:
        kind: Kind name
        **fields: Field values

    Returns:
        Path object

    Raises:
        ValidationError: If validation fails
    """
    # Implementation
```

#### Type Checking

```bash
# Check types with mypy
mypy src/path_manager

# Strict mode
mypy --strict src/path_manager
```

### Docstrings

Use Google-style docstrings:

```python
def parse(self, kind: str, path: str | Path) -> dict[str, str]:
    """
    Parse path to extract field values.

    Reverse resolution - given a path and expected kind,
    extract field values used to generate it.

    Args:
        kind: Expected kind name
        path: Path to parse (str or Path object)

    Returns:
        Dictionary mapping field names to values

    Raises:
        ValidationError: If path doesn't match kind pattern
        ValueError: If kind doesn't exist

    Example:
        >>> fields = resolver.parse('asset_render', '/proj/demo/asset/tree.jpg')
        >>> print(fields)
        {'root': '/proj', 'proj': 'demo', 'asset': 'tree', 'ext': 'jpg'}
    """
    # Implementation
```

### Code Organization

```python
# Good - organized imports
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from path_manager.exceptions import ValidationError
from path_manager.stores import CompiledStore

# Bad - disorganized
from path_manager.exceptions import ValidationError
import re
from typing import Any
from pathlib import Path
```

---

## Commit Guidelines

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Test additions/changes
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `style`: Code style changes (formatting)
- `chore`: Build process, dependencies

**Examples:**

```
feat: Add support for custom field validators

Add optional validator callbacks for fields to enable
runtime validation beyond regex matching.

Closes #123
```

```
fix: Handle Windows UNC paths correctly

Fix path parsing for Windows UNC paths (\\server\share).
Update regex to accept UNC format.

Fixes #456
```

```
docs: Add deployment guide for NFS environments

Add comprehensive guide covering NFS deployment,
CI/CD integration, and monitoring.
```

### Atomic Commits

Make focused commits:

```bash
# Good - one logical change
git commit -m "feat: Add MsgPack storage backend"

# Bad - multiple unrelated changes
git commit -m "Add MsgPack, fix bug in SQLite, update README"
```

### Commit Often

```bash
# Make small, frequent commits
git add src/path_manager/stores/msgpack_store.py
git commit -m "feat: Add MsgPackStore class"

git add tests/test_msgpack_store.py
git commit -m "test: Add MsgPackStore tests"

git add docs/API_REFERENCE.md
git commit -m "docs: Document MsgPackStore API"
```

---

## Pull Request Process

### 1. Prepare Your Branch

```bash
# Update from upstream
git fetch upstream
git rebase upstream/main

# Run tests
pytest tests/ -v

# Format code
black src/path_manager tests/

# Check lint
ruff check src/path_manager tests/
```

### 2. Push to Your Fork

```bash
git push origin feature/my-new-feature
```

### 3. Create Pull Request

On GitHub:
1. Go to your fork
2. Click "New Pull Request"
3. Select your branch
4. Fill in PR template

### PR Title Format

Use same format as commit messages:

```
feat: Add support for custom validators
fix: Handle Windows UNC paths
docs: Improve schema writing guide
```

### PR Description

Include:

1. **What**: What changes were made
2. **Why**: Why these changes are needed
3. **How**: How the changes work
4. **Testing**: How to test the changes

**Example:**

```markdown
## What

Add support for Windows UNC paths (\\server\share format).

## Why

Users on Windows networks need to reference paths on network shares,
which use UNC format.

## How

- Updated root field regex to accept UNC format
- Modified path parsing to handle backslashes
- Added platform detection for automatic format selection

## Testing

```bash
pytest tests/test_resolver.py::TestWindowsUNC -v
```

## Checklist

- [x] Tests added
- [x] Documentation updated
- [x] All tests passing
- [x] Code formatted with black
```

### 4. Code Review

Address reviewer feedback:

```bash
# Make changes based on feedback
# ... edit files ...

git add .
git commit -m "Address review feedback"
git push origin feature/my-new-feature
```

### 5. Squash Commits (if requested)

```bash
# Interactive rebase
git rebase -i upstream/main

# Squash commits in editor
# Save and force push
git push --force origin feature/my-new-feature
```

---

## Reporting Bugs

### Before Reporting

1. Search existing issues
2. Check latest version
3. Verify it's reproducible

### Bug Report Template

```markdown
**Describe the bug**
A clear description of the bug.

**To Reproduce**
Steps to reproduce:
1. Create schema with '...'
2. Run resolver with '...'
3. See error

**Expected behavior**
What you expected to happen.

**Actual behavior**
What actually happened.

**Environment**
- OS: [e.g., Ubuntu 22.04, Windows 11]
- Python version: [e.g., 3.10.5]
- Path Manager version: [e.g., 0.1.0]

**Schema** (if applicable)
```yaml
# Minimal schema that reproduces issue
```

**Code** (if applicable)
```python
# Minimal code that reproduces issue
```

**Error message** (if applicable)
```
Full error message and traceback
```
```

---

## Suggesting Features

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem.

**Describe the solution you'd like**
What you want to happen.

**Describe alternatives you've considered**
Other solutions you've thought about.

**Use case**
Concrete examples of when/how this would be used.

**Additional context**
Any other context or screenshots.
```

---

## Development Tips

### Debugging

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Use breakpoint() for debugging
def some_function():
    # ... code ...
    breakpoint()  # Debugger stops here
    # ... more code ...
```

### Testing Changes Locally

```bash
# Install local version
pip install -e .

# Test in another project
cd /path/to/other/project
python -c "from path_manager.resolver import PathResolver; print(PathResolver)"
```

### Running Specific Tests

```bash
# Test one file
pytest tests/test_resolver.py -v

# Test one class
pytest tests/test_resolver.py::TestPathResolverForward -v

# Test one method
pytest tests/test_resolver.py::TestPathResolverForward::test_resolve_kind_with_fields -v

# Test with pattern
pytest tests/ -k "platform" -v
```

### Performance Profiling

```python
# Profile code
import cProfile

cProfile.run('resolver.get_path("kind", root="/test", proj="demo")')

# Or use pytest-benchmark
def test_performance(benchmark):
    benchmark(resolver.get_path, "kind", root="/test", proj="demo")
```

---

## Questions?

If you have questions:

1. Check documentation in `docs/`
2. Search existing issues
3. Ask in discussions (if enabled)
4. Open an issue with question label

---

## License

By contributing, you agree that your contributions will be licensed
under the same license as the project.

---

## Recognition

Contributors will be recognized in:
- CONTRIBUTORS file
- Release notes
- Documentation credits

Thank you for contributing! 🎉
