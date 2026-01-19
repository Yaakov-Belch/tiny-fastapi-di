# tiny-fastapi-di

**Minimal async dependency injection in ~160 lines. FastAPI-compatible patterns without the framework.**

## Why tiny-fastapi-di?

- **Familiar API**: Uses the same `Depends()` pattern as FastAPI
- **Lightweight**: ~160 lines of code, no dependencies (Pydantic optional)
- **Framework-agnostic**: Use in CLI tools, workers, pipelines - anywhere
- **Feature-complete**: Caching, yield cleanup, async support, circular detection

## Quick Example

```python
from tiny_fastapi_di import Depends, empty_di_ctx

def get_db():
    return "database_connection"

async def get_user(db: str = Depends(get_db)):
    return f"User from {db}"

async def main():
    async with empty_di_ctx.with_maps() as ctx:
        user = await ctx.call_fn(get_user)
        print(user)  # "User from database_connection"
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
