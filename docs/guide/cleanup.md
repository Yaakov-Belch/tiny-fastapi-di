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

## Automatic Cleanup

When you call `call_fn()`, cleanup runs automatically after the function returns:

```python
# Cleanup runs automatically after call_fn returns
result = await empty_di_ctx.call_fn(query_users)
# Connection is already closed here
```

This is the recommended pattern. You don't need to manage context manually.

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

await empty_di_ctx.call_fn(my_function)

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
    await empty_di_ctx.call_fn(my_function)
except ValueError as e:
    # ValueError is raised (last cleanup to fail)
    # e.__context__ is TypeError (previous cleanup failure)
    print(f"Error: {e}")
    print(f"Caused by: {e.__context__}")
```

This matches Python's context manager behavior - all cleanup runs, and exceptions are chained via `__context__`.

## Yield Exactly Once

Dependencies must yield exactly once. The code before `yield` runs during setup, and the code after `yield` runs during cleanup.

```python
# Correct: yields exactly once
def get_resource():
    resource = acquire()
    try:
        yield resource
    finally:
        release(resource)

# Wrong: yields twice - cleanup code won't run correctly
def bad_resource():
    yield "first"
    yield "second"  # This breaks cleanup
    actual_cleanup()  # Never runs
```

If a dependency yields more than once, the cleanup code after the second yield will not execute.
