# Getting Started

## Installation

=== "pip"

    ```bash
    pip install tiny-fastapi-di
    ```

=== "uv"

    ```bash
    uv pip install tiny-fastapi-di
    ```

=== "With Pydantic"

    ```bash
    pip install tiny-fastapi-di[pydantic]
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

# Run it
async def main():
    ctx = empty_di_ctx.with_maps()
    result = await ctx.call_fn(get_users)
    print(result)  # "Fetching users from localhost"
```

## Using the Context Manager

For proper cleanup of resources (database connections, file handles, etc.), use the async context manager:

```python
async def main():
    async with empty_di_ctx.with_maps() as ctx:
        result = await ctx.call_fn(get_users)
        # Resources are cleaned up when exiting the context
```

## Injecting Values

You can inject values directly by parameter name:

```python
async def process_request(request_id: int, user_id: int):
    return f"Processing request {request_id} for user {user_id}"

async def main():
    ctx = empty_di_ctx.with_maps(request_id=123, user_id=456)
    result = await ctx.call_fn(process_request)
    print(result)  # "Processing request 123 for user 456"
```

## Next Steps

- Learn about [Core Concepts](guide/core-concepts.md)
- Explore [Dependencies](guide/dependencies.md) in depth
- See [Cleanup & Yield](guide/cleanup.md) for resource management
