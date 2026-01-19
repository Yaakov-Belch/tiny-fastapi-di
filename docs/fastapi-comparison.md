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
| `Security(scopes=[...])` | ✅ | ✅ | Identical API |
| Circular detection | ❌ | ✅ | **tiny-fastapi-di wins** |
| Value injection by name | ❌ | ✅ | **tiny-fastapi-di wins** |
| `fn_map` substitution | partial¹ | ✅ | **tiny-fastapi-di wins** |
| Optional type validation | ❌ | ✅ | **tiny-fastapi-di wins** |
| Path/Query/Body params | ✅ | ②  | Web framework specific |
| Request scoping | auto | manual³ | Different approach |
| OpenAPI generation | ✅ | ❌ | Documentation tooling |

¹ FastAPI has `app.dependency_overrides` but it's global, not per-request  
² Can be implemented as regular `Depends()` functions  
³ Use `async with ctx.with_maps()` explicitly

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

    # Call it
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

    # Cleanup happens when exiting the context
    async with empty_di_ctx.with_maps() as ctx:
        result = await ctx.call_fn(endpoint)
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

    ctx = empty_di_ctx.with_maps(fn_map={get_db: mock_db})
    result = await ctx.call_fn(endpoint)
    # No cleanup needed - ctx is isolated
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
- You need per-request isolation without global state
- You want circular dependency detection
- You're learning how DI works (~160 readable lines)

## Migration Guide

If you're familiar with FastAPI, tiny-fastapi-di should feel natural:

1. Replace `from fastapi import Depends` with `from tiny_fastapi_di import Depends`
2. Create a context: `ctx = empty_di_ctx.with_maps()`
3. Call functions: `await ctx.call_fn(my_endpoint)`
4. For cleanup, wrap in `async with ctx:`

The `Depends()`, `Security()`, and `Annotated` patterns work identically.
