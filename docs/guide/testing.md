# Testing

## Dependency Substitution with `fn_map`

Replace real dependencies with mocks using `fn_map`:

```python
from tiny_fastapi_di import Depends, empty_di_ctx

# Production dependency
def get_database():
    return RealDatabase("postgres://production")

# Your function under test
async def get_user_count(db = Depends(get_database)):
    return db.count("users")

# Test with mock
async def test_get_user_count():
    def mock_database():
        return MockDatabase(user_count=42)

    result = await empty_di_ctx.call_fn(
        get_user_count,
        fn_map={get_database: mock_database}
    )
    assert result == 42
```

## Value Injection for Tests

Inject test values directly:

```python
async def process_request(request_id: int, user_id: int):
    return f"Request {request_id} for user {user_id}"

async def test_process_request():
    result = await empty_di_ctx.call_fn(
        process_request,
        request_id=999,
        user_id=123
    )
    assert result == "Request 999 for user 123"
```

## Combining Substitution and Injection

```python
def get_api_client():
    return RealAPIClient()

async def fetch_data(endpoint: str, client = Depends(get_api_client)):
    return client.get(endpoint)

async def test_fetch_data():
    mock_client = MockAPIClient(responses={"/users": [{"id": 1}]})

    result = await empty_di_ctx.call_fn(
        fetch_data,
        fn_map={get_api_client: lambda: mock_client},
        endpoint="/users"
    )
    assert result == [{"id": 1}]
```

## Testing Cleanup

Verify cleanup runs correctly:

```python
async def test_cleanup_runs():
    cleanup_called = False

    def get_resource():
        nonlocal cleanup_called
        yield "resource"
        cleanup_called = True

    async def use_resource(r = Depends(get_resource)):
        return r

    result = await empty_di_ctx.call_fn(use_resource)
    assert result == "resource"
    assert cleanup_called  # Cleanup ran automatically
```

## pytest-asyncio Example

```python
import pytest
from tiny_fastapi_di import Depends, empty_di_ctx

@pytest.fixture
def test_ctx():
    return empty_di_ctx.with_maps(fn_map={get_real_db: get_mock_db})

@pytest.mark.asyncio
async def test_my_function(test_ctx):
    result = await test_ctx.call_fn(my_function, environment="test")
    assert result == expected_value
```

## Isolation

Each `call_fn` invocation is isolated:

- Fresh cache for each call
- No shared state between tests
- No global overrides to clean up

This makes tests reliable and parallelizable.
