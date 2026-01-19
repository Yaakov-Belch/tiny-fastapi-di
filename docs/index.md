# tiny-fastapi-di

**Production-ready async dependency injection in ~170 lines. FastAPI-compatible patterns, minimal code, nothing that can break.**

## Why tiny-fastapi-di?

- **Production-ready**: ~170 lines of auditable code. No hidden complexity.
- **Familiar API**: Same `Depends()` pattern as FastAPI
- **Framework-agnostic**: Use in CLI tools, workers, pipelines, anywhere
- **Correct by default**: Cleanup runs automatically, circular dependencies detected

## Quick Example

```python
from tiny_fastapi_di import Depends, empty_di_ctx

def get_db():
    return "database_connection"

async def get_user(db: str = Depends(get_db)):
    return f"User from {db}"

# One call handles context and cleanup
result = await empty_di_ctx.call_fn(get_user)
```

## Installation

```bash
pip install tiny-fastapi-di

# With Pydantic validation
pip install tiny-fastapi-di[pydantic]
```

## Feature Highlights

| Feature | tiny-fastapi-di |
|---------|-----------------|
| `Depends()` | ✅ |
| `Depends(use_cache=False)` | ✅ |
| `Annotated[T, Depends()]` | ✅ |
| `yield` dependencies | ✅ |
| Async dependencies | ✅ |
| Circular detection | ✅ |
| Value injection | ✅ |
| Dependency substitution | ✅ |

## Next Steps

- [Getting Started](getting-started.md) - Installation and first steps
- [Core Concepts](guide/core-concepts.md) - Understanding the DI model
- [FastAPI Comparison](fastapi-comparison.md) - Feature-by-feature comparison
