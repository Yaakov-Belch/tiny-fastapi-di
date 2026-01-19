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
from tiny_fastapi_di import Depends, empty_di_ctx

def get_config():
    return {"db_url": "postgres://localhost"}

def get_db(config: dict = Depends(get_config)):
    return f"Connected to {config['db_url']}"

async def get_users(db: str = Depends(get_db)):
    return f"Users from {db}"

# Resolves: get_config -> get_db -> get_users
result = await empty_di_ctx.call_fn(get_users)
```

## Async Dependencies

Dependencies can be async:

```python
async def get_user_from_api():
    # Async HTTP call
    return {"id": 1, "name": "Alice"}

async def process_user(user: dict = Depends(get_user_from_api)):
    return f"Processing {user['name']}"
```

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
