# Contributing to CRE

Thanks for your interest in contributing to CRE! This guide will help you get started.

## Development Setup

### 1. Clone and install

```bash
git clone https://github.com/yourusername/cre.git
cd cre
pip install -e ".[dev]"
```

### 2. Run tests

```bash
pytest tests/
pytest tests/ --cov=cre  # with coverage report
```

### 3. Code style

We use `black` and `ruff`. Before committing:

```bash
black cre/ tests/
ruff check cre/ tests/
```

## Architecture Overview

CRE is built in three independent layers:

- **L1 (vector_store.py)**: ChromaDB wrapper for semantic search
- **L2 (memory.py)**: SQLite tiered memory (raw/summary/theme)
- **L3 (sidecar.py)**: Pluggable LLM backends (abstract + 3 implementations)

The **Retriever** (retriever.py) orchestrates all three with token-budget-aware packing.

## Making Changes

### Adding a new sidecar backend

1. Create a subclass of `SidecarBackend` in `cre/sidecar.py`
2. Implement `compress()` and `rank()` methods
3. Add to `get_sidecar()` factory function
4. Add tests in `tests/test_sidecar.py` (new file)

Example:

```python
class MySidecar(SidecarBackend):
    def compress(self, text: str) -> str:
        # Your implementation
        pass

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        # Your implementation
        pass
```

### Adding a new CLI command

1. Add function to `cre/cli.py` with `@app.command()` decorator
2. Use Typer arguments/options for parameters
3. Add Rich console output for user feedback
4. Add help strings to all arguments

Example:

```python
@app.command()
def mycommand(
    arg: str = typer.Argument(..., help="Description"),
    opt: int = typer.Option(10, "--opt", help="Description"),
) -> None:
    """Full help text for mycommand."""
    # Implementation
    console.print("Done!")
```

### Adding tests

- Use `pytest` fixtures for setup/teardown
- Use `tmp_path` fixture for temporary directories
- Follow naming convention: `test_module.py` with `TestClass` and `test_method` functions

Example:

```python
class TestMyFeature:
    @pytest.fixture
    def setup(self, tmp_path):
        # Setup code
        return result

    def test_something(self, setup):
        assert setup is not None
```

## Good First Issues

Looking to contribute? Start with these:

- [ ] Add export format: `injector.py` add `format_xml()` method
- [ ] Add chunking strategy: extend `Chunker` class for semantic chunking
- [ ] Add memory stats visualization: extend `status` command output
- [ ] Write documentation for L2 memory schema
- [ ] Add integration tests for full ingest→retrieve→inject flow

## Code Quality Checklist

Before opening a PR:

- [ ] Tests pass: `pytest tests/`
- [ ] Code is formatted: `black cre/ tests/`
- [ ] No linting issues: `ruff check cre/ tests/`
- [ ] Type hints added (Python 3.10+)
- [ ] Docstrings follow Google style
- [ ] No hardcoded paths (use `Path` and `.cre/` dir)
- [ ] Error messages are user-friendly (use Rich for console output)

## Commit Message Style

- Start with imperative verb: "Add", "Fix", "Refactor", not "Added"
- Reference issue if applicable: "Fix #123"
- Keep to one logical change per commit

Examples:
- ✅ `Add compress command for session logs`
- ✅ `Fix token counting in sliding window chunker`
- ❌ `updates and fixes`
- ❌ `WIP`

## Opening a Pull Request

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes and test thoroughly
3. Push to your fork
4. Open a PR with clear description of what you changed and why
5. Reference related issues: `Fixes #123`

## Reporting Issues

Found a bug or have a feature idea? Open an issue with:

- **Title**: Clear, one-line summary
- **Description**: What you expected vs. what happened
- **Steps to reproduce**: Exact commands to recreate
- **Environment**: OS, Python version, CRE version

Example:

```
Title: Memory tier weighting not respected in injection

Description:
When I run cre inject with a 100-token budget, it seems to ignore the
tier_weights configuration and injects summaries instead of themes.

Steps to reproduce:
1. Create config with tier_weights: [0.5, 0.35, 0.15]
2. Store 5 themes and 5 summaries in memory
3. Run: cre inject "query" --budget 100
4. Observe: Summaries injected first, not themes

Environment:
- macOS 13.5
- Python 3.11
- CRE 0.1.0
```

## Questions?

- Check existing issues and discussions
- Read the [README](README.md) and [architecture docs](docs/architecture.md)
- Ask in GitHub Discussions

---

Thanks for making CRE better! 🔥
