import pytest
from typing import Annotated

from tiny_fastapi_di import Depends, TinyDiCtx, empty_di_ctx


# --- Basic Depends ---

async def test_basic_depends():
    def get_value():
        return 42

    async def my_fn(value: int = Depends(get_value)):
        return value * 2

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == 84


async def test_depends_infer_from_annotation():
    def get_value():
        return 42

    async def my_fn(value: Annotated[int, Depends(get_value)]):
        return value * 2

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == 84


async def test_depends_infer_callable_from_type():
    class MyService:
        def __init__(self):
            self.value = 99

    async def my_fn(svc: Annotated[MyService, Depends()]):
        return svc.value

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == 99


# --- Caching ---

async def test_depends_cached_by_default():
    call_count = 0

    def get_value():
        nonlocal call_count
        call_count += 1
        return 42

    async def fn1(v: int = Depends(get_value)):
        return v

    async def fn2(v: int = Depends(get_value)):
        return v

    async def my_fn(a: int = Depends(fn1), b: int = Depends(fn2)):
        return a + b

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == 84
    assert call_count == 1  # Only called once due to caching


async def test_depends_use_cache_false():
    call_count = 0

    def get_value():
        nonlocal call_count
        call_count += 1
        return call_count

    async def my_fn(
        a: int = Depends(get_value, use_cache=False),
        b: int = Depends(get_value, use_cache=False),
    ):
        return (a, b)

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == (1, 2)  # Called twice


# --- Circular Dependency Detection ---

async def test_circular_dependency_detected():
    # Create actual circular dependency: A -> B -> A
    def circular_a(b=Depends(lambda: None)):
        return b

    def circular_b(a=Depends(circular_a)):
        return a

    # Patch circular_a to depend on circular_b
    circular_a.__defaults__ = (Depends(circular_b),)

    with pytest.raises(RecursionError, match="Circular dependency detected.*already being resolved"):
        await empty_di_ctx.call_fn(circular_b)


# --- value_map (kwargs injection) ---

async def test_value_map_injection():
    async def my_fn(request_id: int):
        return f"Request {request_id}"

    result = await empty_di_ctx.call_fn(my_fn, request_id=123)
    assert result == "Request 123"


async def test_value_map_with_depends():
    def get_user(request_id: int):
        return f"User for request {request_id}"

    async def my_fn(user: str = Depends(get_user)):
        return user

    result = await empty_di_ctx.call_fn(my_fn, request_id=456)
    assert result == "User for request 456"


# --- fn_map (dependency substitution) ---

async def test_fn_map_substitution():
    def real_db():
        return "real database"

    def mock_db():
        return "mock database"

    async def my_fn(db: str = Depends(real_db)):
        return db

    result = await empty_di_ctx.call_fn(my_fn, fn_map={real_db: mock_db})
    assert result == "mock database"


# --- Async Functions ---

async def test_async_dependency():
    async def get_value():
        return 42

    async def my_fn(value: int = Depends(get_value)):
        return value

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == 42


# --- yield (cleanup) ---

async def test_yield_cleanup():
    cleanup_called = False

    def get_resource():
        nonlocal cleanup_called
        yield "resource"
        cleanup_called = True

    async def my_fn(r: str = Depends(get_resource)):
        return r

    # call_fn handles cleanup automatically
    result = await empty_di_ctx.call_fn(my_fn)
    assert result == "resource"
    assert cleanup_called


async def test_async_yield_cleanup():
    cleanup_called = False

    async def get_resource():
        nonlocal cleanup_called
        yield "async resource"
        cleanup_called = True

    async def my_fn(r: str = Depends(get_resource)):
        return r

    # call_fn handles cleanup automatically
    result = await empty_di_ctx.call_fn(my_fn)
    assert result == "async resource"
    assert cleanup_called


async def test_cleanup_exception_chaining():
    cleanup_order = []

    def resource_a():
        yield "a"
        cleanup_order.append("a")
        raise ValueError("Error in A")

    def resource_b():
        yield "b"
        cleanup_order.append("b")
        raise TypeError("Error in B")

    async def my_fn(a: str = Depends(resource_a), b: str = Depends(resource_b)):
        return a + b

    # LIFO cleanup: B first (TypeError), then A (ValueError)
    # Final exception is ValueError with __context__ = TypeError
    with pytest.raises(ValueError) as exc_info:
        await empty_di_ctx.call_fn(my_fn)

    # Both cleanups ran (LIFO order)
    assert cleanup_order == ["b", "a"]
    # Exceptions are chained: ValueError.__context__ = TypeError
    assert exc_info.value.__context__ is not None
    assert isinstance(exc_info.value.__context__, TypeError)


# --- Default Values ---

async def test_default_value_used():
    async def my_fn(value: int = 100):
        return value

    result = await empty_di_ctx.call_fn(my_fn)
    assert result == 100


async def test_missing_required_arg_raises():
    async def my_fn(required_arg: int):
        return required_arg

    with pytest.raises(TypeError, match="No value provided.*call_fn"):
        await empty_di_ctx.call_fn(my_fn)


async def test_non_callable_depends_raises():
    async def my_fn(value: int = Depends(42)):  # type: ignore
        return value

    with pytest.raises(TypeError, match="requires a callable.*got int"):
        await empty_di_ctx.call_fn(my_fn)


# --- Context Self-Injection ---

async def test_context_self_injection():
    async def my_fn(ctx: TinyDiCtx = Depends()):
        return ctx

    result = await empty_di_ctx.call_fn(my_fn)
    # The injected context is the scoped context created by call_fn
    assert isinstance(result, TinyDiCtx)


# --- with_maps ---

async def test_with_maps_fn_map_only():
    def real_dep():
        return "real"

    def mock_dep():
        return "mock"

    async def my_fn(val: str = Depends(real_dep)):
        return val

    ctx = empty_di_ctx.with_maps(fn_map={real_dep: mock_dep})
    result = await ctx.call_fn(my_fn)
    assert result == "mock"


async def test_with_maps_value_map_only():
    async def my_fn(request_id: int):
        return request_id

    ctx = empty_di_ctx.with_maps(request_id=999)
    result = await ctx.call_fn(my_fn)
    assert result == 999


async def test_with_maps_immutability():
    """Verify with_maps returns a new context without modifying the original."""
    original = empty_di_ctx

    def real_dep():
        return "real"

    def mock_dep():
        return "mock"

    derived = original.with_maps(fn_map={real_dep: mock_dep}, user_id=123)

    # Original should be unchanged
    assert original.value_map == {}
    assert original.fn_map == {}
    assert original.validator is None

    # Derived should have the new values
    assert derived.fn_map == {real_dep: mock_dep}
    assert derived.value_map == {"user_id": 123}


async def test_with_maps_merges_existing():
    """Verify with_maps merges with existing maps."""
    def dep_a():
        return "a"

    def dep_b():
        return "b"

    def mock_a():
        return "mock_a"

    def mock_b():
        return "mock_b"

    ctx1 = empty_di_ctx.with_maps(fn_map={dep_a: mock_a}, val1=1)
    ctx2 = ctx1.with_maps(fn_map={dep_b: mock_b}, val2=2)

    # ctx2 should have both fn_map entries and both value_map entries
    assert ctx2.fn_map == {dep_a: mock_a, dep_b: mock_b}
    assert ctx2.value_map == {"val1": 1, "val2": 2}
