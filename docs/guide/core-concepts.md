# Core Concepts

## The Context (`TinyDiCtx`)

The `TinyDiCtx` is the heart of the dependency injection system. It holds:

- **`value_map`**: Direct values to inject by parameter name
- **`fn_map`**: Function substitutions (for testing)
- **`validator`**: Optional type validator (e.g., Pydantic)
- **`_cache`**: Cached dependency results (internal)
- **`_cleanup_stack`**: Generators awaiting cleanup (internal)

### Creating a Context

```python
from tiny_fastapi_di import empty_di_ctx

# Start with the empty context
ctx = empty_di_ctx

# Create a derived context with values
request_ctx = ctx.with_maps(request_id=123, user_id=456)

# Create another derived context with more values
handler_ctx = request_ctx.with_maps(handler_name="process")
```

!!! note
    `with_maps()` always returns a **new** context. The original is not modified.

## Resolution Order

When resolving a parameter, tiny-fastapi-di checks in this order:

1. **`Depends()`** - If the default is a `Depends`, call the dependency
2. **`value_map`** - If the parameter name exists in `value_map`, use that value
3. **Default value** - If the parameter has a default, use it
4. **Error** - Raise `TypeError` if no value can be found

```python
async def example(
    request_id: int,           # Required - must be in value_map (no default)
    db = Depends(get_db),      # Resolved via Depends
    timeout: int = 30,         # Uses default if not in value_map
):
    ...
```

!!! note "Python syntax"
    Required parameters (without defaults) must come before parameters with defaults. This is standard Python.

## Caching

By default, dependencies are cached within a context:

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
async with empty_di_ctx.with_maps() as ctx:
    await ctx.call_fn(main)
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

tiny-fastapi-di detects circular dependencies and raises a clear error:

```python
def fn_a(b = Depends(fn_b)):
    return b

def fn_b(a = Depends(fn_a)):
    return a

async with empty_di_ctx.with_maps() as ctx:
    await ctx.call_fn(fn_a)
    # Raises: RecursionError: Circular dependency detected for <function fn_a>
```

!!! tip
    FastAPI does not detect circular dependencies - it will stack overflow. tiny-fastapi-di catches this early with a clear error message.

## Decoupling with `fn_map`

The `fn_map` feature allows you to decouple code from its dependencies by mapping types to their implementations. This is powerful for:

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
# Framework code - knows how to build RequestContext from HTTP request
def get_request_context(request, auth_service):  # Framework dependencies
    user = auth_service.get_user(request.headers["Authorization"])
    return RequestContext(
        user_id=user.id,
        permissions=user.permissions,
        request_path=request.path,
    )

# Register the mapping
framework_ctx = empty_di_ctx.with_maps(
    fn_map={RequestContext: get_request_context},
    request=http_request,
    auth_service=auth,
)

# Plugin code runs without knowing where RequestContext comes from
async with framework_ctx as ctx:
    result = await ctx.call_fn(handle_request)
```

The plugin code (`handle_request`) only sees `RequestContext` - it doesn't know about HTTP requests, authentication services, or any framework details. The framework registers how to build `RequestContext` via `fn_map`.
