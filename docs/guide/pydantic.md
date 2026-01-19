# Pydantic Integration

## Installation

```bash
pip install tiny-fastapi-di[pydantic]
```

## Using `pydantic_di_ctx`

The `pydantic_di_ctx` automatically coerces and validates values using Pydantic:

```python
from pydantic import BaseModel
from tiny_fastapi_di.pydantic import pydantic_di_ctx

class User(BaseModel):
    name: str
    age: int

async def greet_user(user: User):
    return f"Hello, {user.name}!"

# Pass a dict - it gets validated and converted to User
result = await pydantic_di_ctx.call_fn(
    greet_user,
    user={"name": "Alice", "age": 30}
)
print(result)  # "Hello, Alice!"
```

## Type Coercion

Pydantic automatically coerces compatible types:

```python
async def process(count: int, ratio: float):
    return count * ratio

# Strings are coerced to int/float
result = await pydantic_di_ctx.call_fn(
    process,
    count="42",
    ratio="1.5"
)
print(result)  # 63.0
```

## Validation Errors

Invalid data raises Pydantic's `ValidationError`:

```python
from pydantic import ValidationError

async def process(user: User):
    return user

try:
    await pydantic_di_ctx.call_fn(
        process,
        user={"name": "Alice", "age": "not a number"}
    )
except ValidationError as e:
    print(e)
    # age: Input should be a valid integer
```

## With Dependencies

Pydantic validation works with `Depends` too:

```python
from typing import Annotated
from tiny_fastapi_di import Depends

def get_user_data():
    return {"name": "Bob", "age": 25}

async def greet(user: Annotated[User, Depends(get_user_data)]):
    return f"Hello, {user.name}!"

result = await pydantic_di_ctx.call_fn(greet)
print(result)  # "Hello, Bob!"
```

## Custom Validator

You can create your own validator by implementing the `TypeValidator` protocol:

```python
from tiny_fastapi_di import empty_di_ctx
from inspect import Parameter

class MyValidator:
    def validate(self, type_: type, value):
        if type_ is Parameter.empty:
            return value
        # Your validation logic here
        return type_(value)

my_ctx = empty_di_ctx.with_maps(validator=MyValidator())
result = await my_ctx.call_fn(my_function, data="123")
```

## How It Works

The `CachingPydanticValidator` class:

1. Caches `TypeAdapter` instances per type (for performance)
2. Skips validation if no type annotation exists
3. Uses `validate_python()` to coerce and validate

```python
from dataclasses import dataclass, field
from inspect import Parameter
from pydantic import TypeAdapter

@dataclass
class CachingPydanticValidator:
    _cache: dict[type, TypeAdapter] = field(repr=False, init=False, default_factory=dict)

    def validate(self, type_: type, value):
        if type_ is Parameter.empty:
            return value
        if type_ not in self._cache:
            self._cache[type_] = TypeAdapter(type_)
        return self._cache[type_].validate_python(value)
```
