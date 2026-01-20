# FastAPI Comparison

## Feature Matrix

| Feature | FastAPI | tiny-fastapi-di | Notes |
|---------|---------|-----------------|-------|
| `Depends()` | ✅ | ✅ | Identical API |
| `Depends(use_cache=False)` | ✅ | ✅ | Identical API |
| `Annotated[T, Depends()]` | ✅ | ✅ | Identical API |
| Infer callable from type | ✅ | ✅ | Identical API |
| `yield` dependencies | ✅ | ✅ | Identical behavior |
| Async `yield` dependencies | ✅ | ✅ | Identical behavior |
| Cleanup (LIFO order) | ✅ | ✅ | Identical behavior |
| Async/sync dependencies | ✅ | ✅ | Identical behavior |
| Sub-dependencies | ✅ | ✅ | Identical behavior |
| Circular detection | ❌ | ✅ | **tiny-fastapi-di wins** |
| Value injection by name | ❌ | ✅ | **tiny-fastapi-di wins** |
| `fn_map` substitution | partial¹ | ✅ | **tiny-fastapi-di wins** |
| Optional type validation | ❌ | ✅ | **tiny-fastapi-di wins** |
| Path/Query/Body params | ✅ | ②  | Web framework specific |
| Request scoping | auto | auto³ | Both handle cleanup |
| OpenAPI generation | ✅ | ❌ | Documentation tooling |

¹ FastAPI has `app.dependency_overrides` but it's global, not per-request
² Can be implemented as regular `Depends()` functions
³ `call_fn()` handles cleanup automatically

## Code Comparison

### Basic Dependency

=== "FastAPI"

    ```python
    from fastapi import Depends, FastAPI

    app = FastAPI()

    def get_db():
        return "database"

    @app.get("/")
    def endpoint(db: str = Depends(get_db)):
        return {"db": db}
    ```

=== "tiny-fastapi-di"

    ```python
    from tiny_fastapi_di import Depends, empty_di_ctx

    def get_db():
        return "database"

    async def endpoint(db: str = Depends(get_db)):
        return {"db": db}

    # One call - cleanup handled automatically
    result = await empty_di_ctx.call_fn(endpoint)
    ```

### Yield Dependency

=== "FastAPI"

    ```python
    def get_db():
        db = connect()
        try:
            yield db
        finally:
            db.close()

    @app.get("/")
    def endpoint(db = Depends(get_db)):
        return db.query()
    # Cleanup happens automatically per-request
    ```

=== "tiny-fastapi-di"

    ```python
    def get_db():
        db = connect()
        try:
            yield db
        finally:
            db.close()

    async def endpoint(db = Depends(get_db)):
        return db.query()

    # Cleanup happens automatically after call_fn returns
    result = await empty_di_ctx.call_fn(endpoint)
    ```

### Testing with Mocks

=== "FastAPI"

    ```python
    from fastapi.testclient import TestClient

    def mock_db():
        return "mock_database"

    app.dependency_overrides[get_db] = mock_db
    client = TestClient(app)
    response = client.get("/")
    app.dependency_overrides.clear()  # Don't forget!
    ```

=== "tiny-fastapi-di"

    ```python
    def mock_db():
        return "mock_database"

    result = await empty_di_ctx.call_fn(
        endpoint,
        fn_map={get_db: mock_db}
    )
    # No cleanup needed - each call is isolated
    ```

## When to Use Each

### Use FastAPI when:

- Building a web API
- You need OpenAPI documentation
- You want automatic request/response handling
- You need Path/Query/Body parameter parsing

### Use tiny-fastapi-di when:

- Building CLI tools
- Building background workers
- Building data pipelines
- You want DI without a web framework
- You need per-call isolation without global state
- You want circular dependency detection
- You want auditable code (~220 lines)

### Use Both Together

tiny-fastapi-di can recognize FastAPI's `Depends` class, enabling code sharing between web servers and workers. See [Working with Multiple Frameworks](guide/multi-framework.md) for details.

## Migration Guide

If you're familiar with FastAPI, tiny-fastapi-di should feel natural:

1. Replace `from fastapi import Depends` with `from tiny_fastapi_di import Depends`
2. Call functions directly: `await empty_di_ctx.call_fn(my_endpoint)`
3. Pass values and mocks: `call_fn(my_fn, request_id=123, fn_map={...})`

The `Depends()` and `Annotated` patterns work identically.

## Security Class

FastAPI's `Security` class is a `Depends` subclass with an `scopes` field for OAuth2 metadata. If you need this, implement it yourself:

```python
from dataclasses import dataclass, field
from tiny_fastapi_di import Depends

@dataclass
class Security(Depends):
    scopes: list[str] = field(default_factory=list)
```

The `scopes` field is metadata only - enforcement is your responsibility, exactly as in FastAPI.
