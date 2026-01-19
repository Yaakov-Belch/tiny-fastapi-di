from dataclasses import dataclass, field
from inspect import Parameter, isasyncgen, isgenerator, isawaitable, signature
from typing import Annotated, Any, Protocol, get_args, get_origin, runtime_checkable


@runtime_checkable
class TypeValidator(Protocol):
    def validate(self, type_: type, value: Any) -> Any: ...


@dataclass
class Depends:
    fn: callable | None = None
    use_cache: bool = True


@dataclass
class Security(Depends):
    scopes: list[str] = field(default_factory=list)


no_value = object()


@dataclass
class TinyDiCtx:
    value_map: dict[str, Any]
    fn_map: dict[callable, callable]
    validator: TypeValidator | None
    _cache: dict = field(repr=False, init=False)
    _lock: set = field(repr=False, init=False, default_factory=set)
    _cleanup_stack: list = field(repr=False, init=False, default_factory=list)

    def __post_init__(self):
        self._cache = {TinyDiCtx: self}

    def with_maps(self, fn_map=no_value, validator=no_value, **kwargs):
        value_map2 = {**self.value_map, **kwargs} if kwargs else self.value_map
        fn_map2 = {**self.fn_map, **fn_map} if fn_map is not no_value else self.fn_map
        if validator is no_value:
            validator2 = self.validator
        else:
            validator2 = validator

        return TinyDiCtx(
            value_map=value_map2,
            fn_map=fn_map2,
            validator=validator2,
        )

    async def call_fn(self, fn: callable, use_cache: bool = True):
        if fn in self.fn_map:
            fn = self.fn_map[fn]

        if use_cache:
            if fn not in self._cache:
                self._cache[fn] = await self.call_fn(fn=fn, use_cache=False)
            return self._cache[fn]
        else:
            if fn in self._lock:
                raise RecursionError(f"Circular dependency detected for {fn}")
            try:
                self._lock.add(fn)
                params = signature(fn).parameters.values()
                kwargs = {
                    p.name: await self.solve_arg(param=p)
                    for p in params
                }
                result = fn(**kwargs)
                if isgenerator(result):
                    gen = result
                    result = next(gen)
                    self._cleanup_stack.append(gen)
                elif isasyncgen(result):
                    gen = result
                    result = await gen.__anext__()
                    self._cleanup_stack.append(gen)
                elif isawaitable(result):
                    result = await result
                return result
            finally:
                self._lock.discard(fn)

    async def solve_arg(self, param: Parameter):
        annotation = param.annotation
        default = param.default

        # Unwrap Annotated: Annotated[User, Depends(...)] -> annotation=User, default=Depends(...)
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            annotation = args[0]
            for meta in args[1:]:
                if isinstance(meta, Depends):
                    default = meta
                    break

        if isinstance(default, Depends):
            fn = default.fn or annotation
            if fn is Parameter.empty:
                raise TypeError(f"Depends() requires a callable or type annotation for '{param.name}'")
            value = await self.call_fn(fn=fn, use_cache=default.use_cache)
        elif param.name in self.value_map:
            value = self.value_map[param.name]
        elif param.default is not Parameter.empty:
            value = param.default
        else:
            raise TypeError(f"No value provided for required argument '{param.name}'")
        if self.validator is not None:
            return self.validator.validate(annotation, value)
        return value

    async def _cleanup(self):
        exception = None
        for gen in reversed(self._cleanup_stack):
            try:
                if isasyncgen(gen):
                    await gen.__anext__()
                else:
                    next(gen)
            except (StopIteration, StopAsyncIteration):
                pass
            except BaseException as new_exc:
                if exception is not None:
                    new_exc.__context__ = exception
                exception = new_exc
        if exception is not None:
            raise exception

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._cleanup()


empty_di_ctx = TinyDiCtx(value_map={}, fn_map={}, validator=None)
