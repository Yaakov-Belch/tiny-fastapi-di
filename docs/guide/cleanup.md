# Cleanup & Yield Dependencies

## Yield Dependencies

Use `yield` to create dependencies that need cleanup:

```python
def get_db_connection():
    print("Opening connection")
    connection = open_database()
    try:
        yield connection
    finally:
        print("Closing connection")
        connection.close()

async def query_users(db = Depends(get_db_connection)):
    return db.query("SELECT * FROM users")
```

## Using the Context Manager

Cleanup runs when exiting the async context:

```python
async with empty_di_ctx.with_maps() as ctx:
    result = await ctx.call_fn(query_users)
    # Connection is open here
# Connection is closed here (after exiting the context)
```

!!! warning
    If you don't use `async with`, cleanup will **not** run automatically.

## Async Yield Dependencies

For async cleanup operations:

```python
async def get_async_resource():
    print("Acquiring resource")
    resource = await acquire_resource()
    try:
        yield resource
    finally:
        print("Releasing resource")
        await release_resource(resource)
```

## Cleanup Order (LIFO)

Cleanup happens in reverse order (Last In, First Out):

```python
def resource_a():
    print("Setup A")
    yield "A"
    print("Cleanup A")

def resource_b():
    print("Setup B")
    yield "B"
    print("Cleanup B")

async def my_function(a = Depends(resource_a), b = Depends(resource_b)):
    return f"{a}{b}"

async with ctx as c:
    await c.call_fn(my_function)

# Output:
# Setup A
# Setup B
# Cleanup B  (reversed order)
# Cleanup A
```

## Exception Handling

All cleanups run even if exceptions occur. Exceptions are chained:

```python
def resource_a():
    yield "A"
    raise ValueError("Error in A cleanup")

def resource_b():
    yield "B"
    raise TypeError("Error in B cleanup")

async def my_function(a = Depends(resource_a), b = Depends(resource_b)):
    return f"{a}{b}"

try:
    async with ctx as c:
        await c.call_fn(my_function)
except ValueError as e:
    # ValueError is raised (last cleanup)
    # e.__context__ is TypeError (previous cleanup)
    print(f"Error: {e}")
    print(f"Caused by: {e.__context__}")
```

!!! info
    This matches Python's context manager behavior - all `__exit__` methods run, and exceptions are chained via `__context__`.
