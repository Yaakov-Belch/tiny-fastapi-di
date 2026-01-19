# API Reference

## Classes

### `TinyDiCtx`

The dependency injection context.

```python
@dataclass
class TinyDiCtx:
    value_map: dict[str, Any]
    fn_map: dict[callable, callable]
    validator: TypeValidator | None
```

#### Methods

##### `with_maps(fn_map=..., validator=..., **kwargs) -> TinyDiCtx`

Create a new context with merged maps.

```python
ctx = empty_di_ctx.with_maps(
    request_id=123,              # Added to value_map
    fn_map={real_fn: mock_fn},   # Merge with fn_map
    validator=my_validator,      # Replace validator
)
```

##### `async call_fn(fn: callable, use_cache: bool = True) -> Any`

Call a function with dependencies resolved.

```python
result = await ctx.call_fn(my_function)
result = await ctx.call_fn(my_function, use_cache=False)
```

##### `async __aenter__() / __aexit__(...)`

Async context manager for cleanup.

```python
async with ctx as c:
    result = await c.call_fn(my_function)
# Cleanup runs here
```

---

### `Depends`

Marks a parameter as a dependency.

```python
@dataclass
class Depends:
    fn: callable | None = None
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

### `Security`

Subclass of `Depends` with OAuth2 scopes metadata.

```python
@dataclass
class Security(Depends):
    scopes: list[str] = field(default_factory=list)
```

#### Usage

```python
def endpoint(user = Security(get_user, scopes=["read", "write"])): ...
```

---

### `TypeValidator` (Protocol)

Protocol for custom validators.

```python
@runtime_checkable
class TypeValidator(Protocol):
    def validate(self, type_: type, value: Any) -> Any: ...
```

---

## Instances

### `empty_di_ctx`

Pre-configured empty context.

```python
empty_di_ctx = TinyDiCtx(value_map={}, fn_map={}, validator=None)
```

### `pydantic_di_ctx`

Context with Pydantic validation (requires `tiny-fastapi-di[pydantic]`).

```python
from tiny_fastapi_di.pydantic import pydantic_di_ctx
```

---

## Exceptions

### `RecursionError`

Raised when circular dependencies are detected.

```python
RecursionError: Circular dependency detected for <function fn_a>
```

### `TypeError`

Raised when a required argument cannot be resolved.

```python
TypeError: No value provided for required argument 'request_id'
TypeError: Depends() requires a callable or type annotation for 'db'
```
