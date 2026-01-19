# Core Concepts

## The Context (`TinyDiCtx`)

The `TinyDiCtx` is the heart of the dependency injection system. It holds:

- **`value_map`**: Direct values to inject by parameter name
- **`fn_map`**: Function substitutions (for testing/decoupling)
- **`validator`**: Optional type validator (e.g., Pydantic)

Internal state (managed automatically):

- **`_cache`**: Cached dependency results
- **`_cleanup_stack`**: Generators awaiting cleanup

### Using the Context

```python
from tiny_fastapi_di import empty_di_ctx

# Call a function with injected values
result = await empty_di_ctx.call_fn(my_function, request_id=123)

# Or create a derived context for multiple calls
test_ctx = empty_di_ctx.with_maps(fn_map={real_db: mock_db})
result = await test_ctx.call_fn(my_function, request_id=123)
```

`with_maps()` always returns a **new** context. The original is not modified.

## Resolution Order

When resolving a parameter, tiny-fastapi-di checks in this order:

1. **`Depends()`** - If the default is a `Depends`, call the dependency
2. **`value_map`** - If the parameter name exists in `value_map`, use that value
3. **Default value** - If the parameter has a default, use it
4. **Error** - Raise `TypeError` with actionable guidance

```python
async def example(
    request_id: int,           # Required - must be in value_map
    db = Depends(get_db),      # Resolved via Depends
    timeout: int = 30,         # Uses default if not in value_map
):
    ...
```

## Caching

By default, dependencies are cached within a single `call_fn` invocation:

```python
call_count = 0

def get_expensive_resource():
    global call_count
    call_count += 1
    return "resource"

async def fn_a(r = Depends(get_expensive_resource)):
    return r

async def fn_b(r = Depends(get_expensive_resource)):
    return r

async def main(a = Depends(fn_a), b = Depends(fn_b)):
    return (a, b)

# get_expensive_resource is only called ONCE
await empty_di_ctx.call_fn(main)
assert call_count == 1
```

Disable caching with `use_cache=False`:

```python
async def main(
    a = Depends(get_resource, use_cache=False),
    b = Depends(get_resource, use_cache=False),
):
    # get_resource called twice
    ...
```

## Circular Dependency Detection

tiny-fastapi-di detects circular dependencies immediately:

```python
def fn_a(b = Depends(fn_b)):
    return b

def fn_b(a = Depends(fn_a)):
    return a

await empty_di_ctx.call_fn(fn_a)
# Raises: RecursionError: Circular dependency detected: fn_a() is already being resolved.
# Check the dependency chain for cycles.
```

FastAPI does not detect circular dependencies (it will stack overflow). tiny-fastapi-di catches this early with a clear error message.

## Decoupling with `fn_map`

The `fn_map` feature maps callables to their implementations. This enables:

- **Framework/plugin separation**: Plugin code sees only what it needs
- **Testing**: Swap real implementations for mocks
- **Configuration**: Different implementations for different environments

### Example: Decoupled Plugin Code

```python
from dataclasses import dataclass
from typing import Annotated
from tiny_fastapi_di import Depends, empty_di_ctx

# Plugin code only knows about this dataclass - no framework details
@dataclass
class RequestContext:
    user_id: int
    permissions: list[str]
    request_path: str

# Plugin function - clean, framework-agnostic
async def handle_request(ctx: Annotated[RequestContext, Depends()]):
    if "admin" in ctx.permissions:
        return f"Admin {ctx.user_id} accessing {ctx.request_path}"
    return f"User {ctx.user_id} accessing {ctx.request_path}"
```

```python
# Framework code - knows how to build RequestContext
def get_request_context(request, auth_service):
    user = auth_service.get_user(request.headers["Authorization"])
    return RequestContext(
        user_id=user.id,
        permissions=user.permissions,
        request_path=request.path,
    )

# Plugin code runs without knowing where RequestContext comes from
result = await empty_di_ctx.call_fn(
    handle_request,
    fn_map={RequestContext: get_request_context},
    request=http_request,
    auth_service=auth,
)
```

The plugin code (`handle_request`) only sees `RequestContext`. It doesn't know about HTTP requests, authentication services, or any framework details.

## fn_map Key Identity

The `fn_map` uses callable identity (not equality) for lookup. This works reliably for:

- Named functions (`def my_func(): ...`)
- Classes (`class MyService: ...`)

Be careful with:

- **Lambdas**: Each `lambda` creates a new object. You can't map a lambda defined elsewhere.
- **Bound methods**: `obj.method` creates a new object each time.

If you need to map these, assign them to a variable first:

```python
my_factory = lambda: SomeService()

# Now you can map it
result = await ctx.call_fn(my_fn, fn_map={my_factory: mock_factory})
```
