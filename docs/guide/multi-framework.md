# Working with Multiple Frameworks

tiny-fastapi-di can recognize `Depends` classes from multiple frameworks, enabling code sharing between different environments.

## The Problem

When building distributed systems, you often have:

- A **web server** running FastAPI or Docket
- **Workers** processing background tasks with tiny-fastapi-di

You want to share dependency definitions between these environments, but each framework has its own `Depends` class.

```
┌─────────────────────┐     ┌──────────────────────┐
│   Web Server        │     │   Worker Process     │
│   (FastAPI/Docket)  │     │   (tiny-fastapi-di)  │
└──────────┬──────────┘     └──────────┬───────────┘
           │                           │
           └───────────┬───────────────┘
                       │
            ┌──────────▼──────────┐
            │  Shared Package     │
            │  - Business logic   │
            │  - Dependency defs  │
            └─────────────────────┘
```

## The Solution: `depends_types`

Configure `TinyDiCtx` to recognize multiple `Depends` classes:

```python
from fastapi import Depends as FastApiDepends
from tiny_fastapi_di import Depends, empty_di_ctx

# Configure context to recognize both Depends classes
ctx = empty_di_ctx.with_maps(
    depends_types=(Depends, FastApiDepends)
)

# Now this works with dependencies declared using either Depends class
result = await ctx.call_fn(my_function)
```

## Complete Example

### Shared Package

```python
# shared_package/services.py
from fastapi import Depends  # Or: from tiny_fastapi_di import Depends

def get_database():
    return DatabaseConnection()

def get_user_service(db=Depends(get_database)):
    return UserService(db)

async def process_order(user_svc=Depends(get_user_service)):
    # Business logic here
    return user_svc.create_order()
```

### Web Server (FastAPI)

```python
# server/main.py
from fastapi import FastAPI, Depends
from shared_package.services import process_order

app = FastAPI()

@app.post("/orders")
async def create_order(result=Depends(process_order)):
    return {"order": result}
```

### Worker (tiny-fastapi-di)

```python
# worker/main.py
from fastapi import Depends as FastApiDepends
from tiny_fastapi_di import Depends, empty_di_ctx
from shared_package.services import process_order

# Configure to recognize FastAPI's Depends
worker_ctx = empty_di_ctx.with_maps(
    depends_types=(Depends, FastApiDepends)
)

async def handle_task():
    result = await worker_ctx.call_fn(process_order)
    return result
```

## Configuring `depends_types`

### Via `with_maps()`

```python
ctx = empty_di_ctx.with_maps(
    depends_types=(Depends, FastApiDepends, DocketDepends)
)
```

### Via `call_fn()`

```python
result = await empty_di_ctx.call_fn(
    my_function,
    depends_types=(Depends, FastApiDepends)
)
```

### Via Constructor

```python
ctx = TinyDiCtx(
    value_map={},
    fn_map={},
    validator=None,
    depends_types=(Depends, FastApiDepends)
)
```

## Attribute Compatibility

tiny-fastapi-di extracts these attributes from any `Depends`-like class:

| Attribute | Purpose | Default |
|-----------|---------|---------|
| `dependency` | The callable to invoke | Required (or infer from type) |
| `use_cache` | Whether to cache the result | `True` |
| `scope` | FastAPI-specific scoping | Ignored |

This means tiny-fastapi-di works with:

- **FastAPI's Depends**: `dependency`, `use_cache`, `scope`
- **Docket's Depends**: `dependency` (implicit caching)
- **tiny-fastapi-di's Depends**: `dependency`, `use_cache`, `scope`

## Choosing Which `Depends` to Import

Your shared package must import a `Depends` class. Options:

### Option 1: Import from the Primary Framework

If your shared code primarily runs on FastAPI:

```python
from fastapi import Depends
```

Workers configure `depends_types` to include `FastApiDepends`.

### Option 2: Import from tiny-fastapi-di

If you want minimal dependencies:

```python
from tiny_fastapi_di import Depends
```

FastAPI will still work because tiny-fastapi-di's `Depends` is compatible.

### Option 3: Conditional Import

```python
# shared_package/compat.py
try:
    from fastapi import Depends
except ImportError:
    from tiny_fastapi_di import Depends
```

This uses FastAPI's `Depends` when available, falling back to tiny-fastapi-di.

## Combining Multiple Frameworks

You can configure a context that works with dependencies from multiple frameworks simultaneously:

```python
from fastapi import Depends as FastApiDepends
from pydocket import Depends as DocketDepends  # hypothetical
from tiny_fastapi_di import Depends, empty_di_ctx

# Works with dependencies from any of these frameworks
ctx = empty_di_ctx.with_maps(
    depends_types=(Depends, FastApiDepends, DocketDepends)
)
```

## Inherited Configuration

The `depends_types` configuration is inherited through `with_maps()`:

```python
# Set depends_types once
base_ctx = empty_di_ctx.with_maps(
    depends_types=(Depends, FastApiDepends)
)

# Derived contexts inherit depends_types
request_ctx = base_ctx.with_maps(request_id=123)
assert request_ctx.depends_types == (Depends, FastApiDepends)
```

## Limitations

### FastAPI's `scope` Parameter

FastAPI's `Depends` has a `scope` parameter for request vs. function scoping. tiny-fastapi-di ignores this parameter because:

1. tiny-fastapi-di always operates at function scope (one `call_fn` = one scope)
2. Request scoping is managed by the web framework, not the DI container

If your code uses `Depends(..., scope="request")`, it will work but the scope is ignored.

### No Duck Typing

tiny-fastapi-di uses `isinstance()` to check if a value is a `Depends` object. It does not use duck typing. This means:

- You must explicitly list all `Depends` classes in `depends_types`
- Random objects with `dependency` attributes won't be mistakenly treated as dependencies

This is intentional to avoid false positives when a parameter's default value happens to have a `dependency` attribute.
