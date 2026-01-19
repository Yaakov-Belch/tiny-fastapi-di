# API Reference

[:fontawesome-brands-github: **View the Source** (~170 lines)](https://github.com/Yaakov-Belch/tiny-fastapi-di/blob/main/src/tiny_fastapi_di/core.py){ .md-button }

---

## Classes

### `TinyDiCtx`

The dependency injection context.

```python
@dataclass
class TinyDiCtx:
    value_map: dict[str, Any]
    fn_map: dict[Callable[..., Any], Callable[..., Any]]
    validator: TypeValidator | None
```

#### Methods

#### **`call_fn`**

```python
async def call_fn(fn, fn_map=None, validator=None, **kwargs) -> Any
```

Call a function with dependency injection. This is the main entry point.

```python
# Basic call
result = await ctx.call_fn(my_function)

# With value injection
result = await ctx.call_fn(my_function, request_id=123)

# With dependency substitution (testing)
result = await ctx.call_fn(my_function, fn_map={real_db: mock_db})

# With validation
result = await ctx.call_fn(my_function, validator=my_validator)
```

Parameters are merged with the context's existing maps. Cleanup of yield-based dependencies runs automatically.

#### **`with_maps`**

```python
def with_maps(fn_map=..., validator=..., **kwargs) -> TinyDiCtx
```

Create a new context with merged maps. The original context is not modified.

```python
# Create a derived context
test_ctx = empty_di_ctx.with_maps(
    fn_map={real_db: mock_db},
    validator=pydantic_validator,
)

# Use the derived context
result = await test_ctx.call_fn(my_function, request_id=123)
```

---

### `Depends`

Marks a parameter as a dependency.

```python
@dataclass
class Depends:
    fn: Callable[..., Any] | None = None
    use_cache: bool = True
```

#### Usage

```python
# Explicit callable
def endpoint(db = Depends(get_db)): ...

# Infer from type
def endpoint(db: Annotated[Database, Depends()]): ...

# Disable cache
def endpoint(db = Depends(get_db, use_cache=False)): ...
```

---

### `TypeValidator` (Protocol)

Protocol for custom validators.

```python
@runtime_checkable
class TypeValidator(Protocol):
    def validate(self, type_: type, value: Any) -> Any: ...
```

Implement this protocol to add custom validation or coercion. See [Pydantic Integration](guide/pydantic.md) for an example.

---

## Instances

### `empty_di_ctx`

Pre-configured empty context with no value_map, fn_map, or validator.

```python
from tiny_fastapi_di import empty_di_ctx

result = await empty_di_ctx.call_fn(my_function)
```

### `pydantic_di_ctx`

Context with Pydantic validation (requires `tiny-fastapi-di[pydantic]`).

```python
from tiny_fastapi_di.pydantic import pydantic_di_ctx

result = await pydantic_di_ctx.call_fn(my_function, user={"name": "Alice"})
```

---

## Exceptions

All exceptions include actionable error messages.

### `RecursionError`

Raised when circular dependencies are detected.

```
RecursionError: Circular dependency detected: get_user() is already being resolved.
Check the dependency chain for cycles.
```

### `TypeError`

Raised when a dependency cannot be resolved.

```
TypeError: No value provided for required argument 'request_id'.
Provide via call_fn(**kwargs), Depends() default, or parameter default.

TypeError: Depends() for parameter 'db' has no callable.
Provide Depends(callable) or use Annotated[Type, Depends()] with a type annotation.

TypeError: Depends() requires a callable, got int: 42
```

---

## FastAPI's Security Class

If you need FastAPI-compatible `Security` with OAuth2 scopes metadata, you can implement it yourself:

```python
from dataclasses import dataclass, field
from tiny_fastapi_di import Depends

@dataclass
class Security(Depends):
    """Depends subclass with OAuth2 scopes metadata."""
    scopes: list[str] = field(default_factory=list)

# Usage
async def endpoint(user = Security(get_user, scopes=["read", "write"])):
    return user
```

The `scopes` field is metadata only. Enforcement is your responsibility, exactly as in FastAPI.
