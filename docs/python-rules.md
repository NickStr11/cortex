# Python Development Rules

## Environment
- Use `uv` for dependency management
- Virtual environment must be in `.venv` directory
- Always run `uv sync` before executing code

## Type Safety
- All functions must have complete type annotations (parameters and return types)
- Use `from __future__ import annotations` at the top of every file
- Prefer `list[str]` over `List[str]` (modern syntax)
- Use `X | None` instead of `Optional[X]`
- No `Any` types unless absolutely necessary (and document why)

## Runtime Type Checking
- Use `beartype` decorator on all public functions
- Import pattern:
  ```python
  from beartype import beartype

  @beartype
  def my_function(name: str, count: int) -> list[str]:
      ...
  ```

## Project Setup
When creating a new project:
1. `uv init`
2. `uv add beartype`
3. `uv add --dev mypy pyright`

## Running Code
Always run through uv:
- `uv run python script.py`
- `uv run mypy .`
- `uv run pyright`

## pyproject.toml Settings
Include these settings:
```toml
[tool.mypy]
strict = true
python_version = "3.12"

[tool.pyright]
typeCheckingMode = "strict"
pythonVersion = "3.12"
```

## File Template
Every Python file should start with:
```python
from __future__ import annotations
from beartype import beartype
```
