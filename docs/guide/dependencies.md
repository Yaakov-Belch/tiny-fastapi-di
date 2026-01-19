# Dependencies

## Basic `Depends()`

The simplest form - pass a callable:

```python
from tiny_fastapi_di import Depends

def get_db():
    return "database"

async def my_function(db: str = Depends(get_db)):
    return f"Using {db}"
```

## Annotated Syntax

The modern Python approach using `Annotated`:

```python
from typing import Annotated
from tiny_fastapi_di import Depends

def get_db():
    return "database"

async def my_function(db: Annotated[str, Depends(get_db)]):
    return f"Using {db}"
```

## Inferring from Type Annotation

If `Depends()` has no argument, the callable is inferred from the type:

```python
from typing import Annotated
from tiny_fastapi_di import Depends

class DatabaseService:
    def __init__(self):
        self.connection = "connected"

async def my_function(db: Annotated[DatabaseService, Depends()]):
    # DatabaseService() is called automatically
    return db.connection
```

## Nested Dependencies

Dependencies can depend on other dependencies:

```python
def get_config():
    return {"db_url": "postgres://localhost"}

def get_db(config: dict = Depends(get_config)):
    return f"Connected to {config['db_url']}"

async def get_users(db: str = Depends(get_db)):
    return f"Users from {db}"

# Resolves: get_config -> get_db -> get_users
await ctx.call_fn(get_users)
```

## Async Dependencies

Dependencies can be async:

```python
async def get_user_from_api():
    # Imagine an async HTTP call here
    return {"id": 1, "name": "Alice"}

async def process_user(user: dict = Depends(get_user_from_api)):
    return f"Processing {user['name']}"
```

## `Security()` for OpenAPI Metadata

`Security` is a subclass of `Depends` with an additional `scopes` field:

```python
from tiny_fastapi_di import Security

def get_current_user():
    return "authenticated_user"

async def protected_endpoint(
    user: str = Security(get_current_user, scopes=["read", "write"])
):
    return f"Hello, {user}"
```

!!! note
    At runtime, `Security` behaves identically to `Depends`. The `scopes` field is metadata for OpenAPI documentation tooling.

## Disabling Cache

Force a fresh call each time:

```python
import random

def get_random():
    return random.randint(1, 100)

async def my_function(
    a: int = Depends(get_random, use_cache=False),
    b: int = Depends(get_random, use_cache=False),
):
    # a and b will be different random numbers
    return (a, b)
```
