# tiny-di

Minimal async dependency injection in ~160 lines. FastAPI-compatible patterns without the framework.

## Installation

```bash
pip install tiny-di

# With Pydantic validation support
pip install tiny-di[pydantic]
```

## Quick Start

```python
from tiny_di import Depends, empty_di_ctx

def get_db():
    return "database_connection"

async def get_user(db: str = Depends(get_db)):
    return f"User from {db}"

async def main():
    async with empty_di_ctx.with_maps() as ctx:
        user = await ctx.call_fn(get_user)
        print(user)  # "User from database_connection"
```

## Features

All FastAPI DI patterns work:

```python
from typing import Annotated
from tiny_di import Depends, Security, empty_di_ctx

# Basic dependency
async def endpoint(db = Depends(get_db)): ...

# Annotated syntax
async def endpoint(db: Annotated[DB, Depends(get_db)]): ...

# Infer from type annotation
async def endpoint(db: Annotated[DB, Depends()]): ...

# Disable caching
async def endpoint(db = Depends(get_db, use_cache=False)): ...

# Security (for OpenAPI metadata)
async def endpoint(user = Security(get_user, scopes=["read"])): ...

# Yield dependencies (cleanup)
def get_db():
    db = connect()
    try:
        yield db
    finally:
        db.close()
```

## Value Injection

Inject values by parameter name:

```python
ctx = empty_di_ctx.with_maps(request_id=123, user_id=456)
result = await ctx.call_fn(my_endpoint)
```

## Dependency Substitution (Testing)

```python
ctx = empty_di_ctx.with_maps(fn_map={real_db: mock_db})
result = await ctx.call_fn(my_endpoint)  # Uses mock_db
```

## Pydantic Validation

```python
from tiny_di.pydantic import pydantic_di_ctx

async def endpoint(user: User):  # User is a Pydantic model
    return user

ctx = pydantic_di_ctx.with_maps(user={"name": "Alice", "age": 30})
result = await ctx.call_fn(endpoint)  # Returns User instance
```

## Feature Comparison with FastAPI

| Feature | FastAPI | tiny-di |
|---------|---------|---------|
| `Depends()` | ✅ | ✅ |
| `Depends(use_cache=False)` | ✅ | ✅ |
| `Annotated[T, Depends()]` | ✅ | ✅ |
| `yield` dependencies | ✅ | ✅ |
| Async dependencies | ✅ | ✅ |
| `Security(scopes=[...])` | ✅ | ✅ |
| Circular detection | ❌ | ✅ |
| Value injection by name | ❌ | ✅ |
| Dependency substitution | partial | ✅ |
| Optional validation | ❌ | ✅ |

## License

MIT
