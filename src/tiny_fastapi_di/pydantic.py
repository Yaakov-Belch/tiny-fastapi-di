from dataclasses import dataclass, field
from inspect import Parameter

from pydantic import TypeAdapter

from .core import empty_di_ctx


@dataclass
class CachingPydanticValidator:
    _cache: dict[type, TypeAdapter] = field(repr=False, init=False, default_factory=dict)

    def validate(self, type_: type, value):
        if type_ is Parameter.empty:
            return value
        if type_ not in self._cache:
            self._cache[type_] = TypeAdapter(type_)
        return self._cache[type_].validate_python(value)


pydantic_di_ctx = empty_di_ctx.with_maps(validator=CachingPydanticValidator())
