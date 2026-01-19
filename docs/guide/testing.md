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

    ctx = empty_di_ctx.with_maps(fn_map={get_database: mock_database})
    result = await ctx.call_fn(get_user_count)
    assert result == 42
```

## Value Injection for Tests

Inject test values directly:

```python
async def process_request(request_id: int, user_id: int):
    return f"Request {request_id} for user {user_id}"

async def test_process_request():
    ctx = empty_di_ctx.with_maps(request_id=999, user_id=123)
    result = await ctx.call_fn(process_request)
    assert result == "Request 999 for user 123"
```

## Combining Substitution and Injection

```python
def get_api_client():
    return RealAPIClient()

async def fetch_data(client = Depends(get_api_client), endpoint: str):
    return client.get(endpoint)

async def test_fetch_data():
    mock_client = MockAPIClient(responses={"/users": [{"id": 1}]})

    ctx = empty_di_ctx.with_maps(
        fn_map={get_api_client: lambda: mock_client},
        endpoint="/users"
    )
    result = await ctx.call_fn(fetch_data)
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

    async with empty_di_ctx.with_maps() as ctx:
        result = await ctx.call_fn(use_resource)
        assert result == "resource"
        assert not cleanup_called  # Not yet

    assert cleanup_called  # Now it's cleaned up
```

## pytest-asyncio Example

```python
import pytest
from tiny_fastapi_di import Depends, empty_di_ctx

@pytest.fixture
def di_ctx():
    return empty_di_ctx.with_maps(
        fn_map={get_real_db: get_mock_db},
        environment="test"
    )

@pytest.mark.asyncio
async def test_my_function(di_ctx):
    async with di_ctx as ctx:
        result = await ctx.call_fn(my_function)
        assert result == expected_value
```
