# Getting Started

## Installation

=== "pip"

    ```bash
    pip install tiny-fastapi-di
    ```

=== "uv"

    ```bash
    uv add tiny-fastapi-di
    ```

=== "pip with Pydantic"

    ```bash
    pip install tiny-fastapi-di[pydantic]
    ```

=== "uv with Pydantic"

    ```bash
    uv add tiny-fastapi-di[pydantic]
    ```

## Your First Dependency

```python
from tiny_fastapi_di import Depends, empty_di_ctx

# Define a dependency
def get_database():
    return {"host": "localhost", "port": 5432}

# Use it in a function
async def get_users(db: dict = Depends(get_database)):
    return f"Fetching users from {db['host']}"

# Run it - one call handles everything
async def main():
    result = await empty_di_ctx.call_fn(get_users)
    print(result)  # "Fetching users from localhost"
```

## Injecting Values

Inject values directly by parameter name:

```python
async def process_request(request_id: int, user_id: int):
    return f"Processing request {request_id} for user {user_id}"

async def main():
    result = await empty_di_ctx.call_fn(
        process_request,
        request_id=123,
        user_id=456
    )
    print(result)  # "Processing request 123 for user 456"
```

## Resource Cleanup

Dependencies that use `yield` are automatically cleaned up:

```python
def get_db_connection():
    print("Opening connection")
    connection = connect()
    try:
        yield connection
    finally:
        print("Closing connection")
        connection.close()

async def query_users(db = Depends(get_db_connection)):
    return db.query("SELECT * FROM users")

# Cleanup runs automatically after call_fn returns
result = await empty_di_ctx.call_fn(query_users)
```

## Next Steps

- Learn about [Core Concepts](guide/core-concepts.md)
- Explore [Dependencies](guide/dependencies.md) in depth
- See [Cleanup & Yield](guide/cleanup.md) for resource management
