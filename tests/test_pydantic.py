import pytest
from typing import Annotated

from pydantic import BaseModel

from tiny_di import Depends
from tiny_di.pydantic import pydantic_di_ctx


class User(BaseModel):
    name: str
    age: int


async def test_pydantic_validation():
    async def my_fn(user: User):
        return user

    ctx = pydantic_di_ctx.with_maps(user={"name": "Alice", "age": 30})
    result = await ctx.call_fn(my_fn)
    assert isinstance(result, User)
    assert result.name == "Alice"
    assert result.age == 30


async def test_pydantic_validation_error():
    async def my_fn(user: User):
        return user

    ctx = pydantic_di_ctx.with_maps(user={"name": "Alice", "age": "not a number"})
    with pytest.raises(Exception):  # Pydantic ValidationError
        await ctx.call_fn(my_fn)


async def test_pydantic_coercion():
    async def my_fn(value: int):
        return value

    ctx = pydantic_di_ctx.with_maps(value="42")
    result = await ctx.call_fn(my_fn)
    assert result == 42
    assert isinstance(result, int)


async def test_pydantic_with_depends():
    def get_user_data():
        return {"name": "Bob", "age": 25}

    async def my_fn(user: Annotated[User, Depends(get_user_data)]):
        return user

    result = await pydantic_di_ctx.call_fn(my_fn)
    assert isinstance(result, User)
    assert result.name == "Bob"
