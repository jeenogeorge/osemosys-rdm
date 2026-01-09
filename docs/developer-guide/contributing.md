# Contributing

Thank you for your interest in contributing to OSeMOSYS-RDM! This guide will help you get started.

## Ways to Contribute

- 🐛 **Report bugs**: Open an issue describing the problem
- 💡 **Suggest features**: Share ideas for improvements
- 📖 **Improve documentation**: Fix typos, add examples
- 🔧 **Submit code**: Fix bugs or implement features
- 🧪 **Add tests**: Improve test coverage

## Getting Started

### Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/osemosys-rdm.git
cd osemosys-rdm

# Add upstream remote
git remote add upstream https://github.com/clg-admin/osemosys-rdm.git
```

### Set Up Development Environment

```bash
# Create development environment
conda env create -f environment.yaml
conda activate AFR-RDM-env

# Install development dependencies
pip install pytest black flake8 mypy
```

### Create a Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feature/your-feature-name
```

## Development Workflow

### 1. Make Changes

Edit the relevant files. Follow existing code style.

### 2. Test Your Changes

```bash
# Run tests
pytest tests/

# Check code style
flake8 src/ scripts/
black --check src/ scripts/

# Run a quick integration test
python run.py rdm --help
```

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: add exponential uncertainty type

- Added interpolation_exponential() function
- Registered new type in experiment manager
- Added tests for edge cases"
```

### 4. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub.

## Code Style

### Python Style

We follow PEP 8 with some modifications:

- Line length: 88 characters (Black default)
- Use meaningful variable names
- Add docstrings to functions

```python
def calculate_something(input_data: pd.DataFrame, year: int) -> float:
    """
    Calculate something important.
    
    Parameters
    ----------
    input_data : pd.DataFrame
        The input data with columns X, Y, Z
    year : int
        The year to calculate for
    
    Returns
    -------
    float
        The calculated value
    
    Examples
    --------
    >>> df = pd.DataFrame({'X': [1, 2], 'Y': [3, 4]})
    >>> calculate_something(df, 2025)
    42.0
    """
    # Implementation
    pass
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, no code change
- `refactor`: Code change without feature/fix
- `test`: Adding tests
- `chore`: Maintenance tasks

Examples:
```
feat(rdm): add logistic uncertainty interpolation
fix(prim): handle empty result sets gracefully
docs: add tutorial for custom uncertainty types
test: add unit tests for interpolation functions
```

## Pull Request Guidelines

### Before Submitting

- [ ] Code follows project style
- [ ] Tests pass locally
- [ ] Documentation updated if needed
- [ ] Commit messages are clear
- [ ] Branch is up to date with main

### PR Description Template

```markdown
## Description
Brief description of changes.

## Motivation
Why is this change needed?

## Changes
- Change 1
- Change 2

## Testing
How were changes tested?

## Checklist
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Review Process

1. Automated checks run on PR
2. Maintainer reviews code
3. Address feedback
4. Merge when approved

## Testing

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_interpolation.py

# With coverage
pytest --cov=src tests/
```

### Writing Tests

```python
# tests/test_my_feature.py
import pytest
from src.workflow import z_auxiliar_code as AUX

class TestMyFeature:
    """Tests for my new feature."""
    
    def test_basic_functionality(self):
        """Test basic case."""
        result = AUX.my_function(input_data)
        assert result == expected
    
    def test_edge_case(self):
        """Test edge case handling."""
        with pytest.raises(ValueError):
            AUX.my_function(invalid_input)
    
    @pytest.mark.parametrize("input,expected", [
        (1, 2),
        (2, 4),
        (3, 6),
    ])
    def test_multiple_cases(self, input, expected):
        """Test with multiple inputs."""
        assert AUX.my_function(input) == expected
```

## Documentation

### Building Docs Locally

```bash
cd docs
pip install -r requirements.txt
sphinx-build -b html . _build/html

# View in browser
open _build/html/index.html
```

### Documentation Style

- Use clear, concise language
- Include examples where helpful
- Add code blocks with syntax highlighting
- Use admonitions for tips/warnings:

```markdown
```{note}
This is a note.
```

```{warning}
This is a warning.
```

```{tip}
This is a tip.
```
```

## Reporting Issues

### Bug Reports

Include:
- OSeMOSYS-RDM version
- Python version
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages (full traceback)

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative approaches considered

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inclusive environment.

### Expected Behavior

- Be respectful and considerate
- Accept constructive criticism gracefully
- Focus on what's best for the community

### Unacceptable Behavior

- Harassment or discrimination
- Personal attacks
- Publishing others' private information

## Getting Help

- **Questions**: Open a Discussion on GitHub
- **Bugs**: Open an Issue
- **Chat**: [Link to community chat if available]

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

## Recognition

Contributors are recognized in:
- GitHub contributor list
- CHANGELOG for significant contributions
- README acknowledgements for major features

Thank you for contributing to OSeMOSYS-RDM! 🎉
