import typing
from dataclasses import dataclass
from inspect import Parameter

from .core import empty_di_ctx


@dataclass
class PyValidator:
    def validate(self, type_: type, value):
        if type_ is Parameter.empty:
            return value
        origin = typing.get_origin(type_)
        check_type = origin if origin is not None else type_
        if isinstance(value, check_type):
            return value
        if isinstance(value, str):
            if type_ in (int, float):
                return type_(value)
            if type_ is bool and value in ('0', '1'):
                return bool(int(value))
        type_name = getattr(type_, '__name__', str(type_))
        raise TypeError(f"Expected {type_name}, got {type(value).__name__}: {value!r}")


py_di_ctx = empty_di_ctx.with_maps(validator=PyValidator())
