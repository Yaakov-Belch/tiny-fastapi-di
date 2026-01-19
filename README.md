# tiny-fastapi-di

Production-ready async dependency injection in ~190 lines. FastAPI-compatible patterns, minimal code, no hidden complexity.

## Installation

```bash
pip install tiny-fastapi-di

# With Pydantic validation
pip install tiny-fastapi-di[pydantic]
```

## Quick Start

```python
from tiny_fastapi_di import Depends, empty_di_ctx

def get_db():
    return "database_connection"

async def get_user(db: str = Depends(get_db)):
    return f"User from {db}"

# One call handles context and cleanup
result = await empty_di_ctx.call_fn(get_user)
```

## Why tiny-fastapi-di?

- **Production-ready**: ~190 lines of auditable code. No hidden complexity.
- **Familiar API**: Same `Depends()` pattern as FastAPI
- **Framework-agnostic**: Use in CLI tools, workers, pipelines, anywhere
- **Correct by default**: Cleanup runs automatically, circular dependencies detected

## Core Features

```python
from typing import Annotated
from tiny_fastapi_di import Depends, empty_di_ctx

# Basic dependency
async def endpoint(db = Depends(get_db)): ...

# Annotated syntax
async def endpoint(db: Annotated[DB, Depends(get_db)]): ...

# Infer callable from type
async def endpoint(db: Annotated[DB, Depends()]): ...

# Disable caching
async def endpoint(db = Depends(get_db, use_cache=False)): ...

# Yield dependencies with automatic cleanup
def get_db():
    db = connect()
    try:
        yield db
    finally:
        db.close()
```

## Value Injection

```python
result = await empty_di_ctx.call_fn(my_endpoint, request_id=123, user_id=456)
```

## Dependency Substitution (Testing)

```python
result = await empty_di_ctx.call_fn(
    my_endpoint,
    fn_map={real_db: mock_db}
)
```

## Pydantic Validation

```python
from tiny_fastapi_di.pydantic import pydantic_di_ctx

async def endpoint(user: User):  # User is a Pydantic model
    return user

result = await pydantic_di_ctx.call_fn(endpoint, user={"name": "Alice", "age": 30})
```

## Feature Comparison

| Feature | FastAPI | tiny-fastapi-di |
|---------|---------|-----------------|
| `Depends()` | ✅ | ✅ |
| `Depends(use_cache=False)` | ✅ | ✅ |
| `Annotated[T, Depends()]` | ✅ | ✅ |
| `yield` dependencies | ✅ | ✅ |
| Async dependencies | ✅ | ✅ |
| Circular detection | ❌ | ✅ |
| Value injection | ❌ | ✅ |
| Dependency substitution | partial | ✅ |
| Optional validation | ❌ | ✅ |

## License

MIT
