from dataclasses import dataclass, field
from inspect import Parameter, isasyncgen, isgenerator, isawaitable, signature
from typing import Annotated, Any, Callable, Protocol, get_args, get_origin, runtime_checkable


@runtime_checkable
class TypeValidator(Protocol):
    def validate(self, type_: type, value: Any) -> Any: ...


class DependsProtocol(Protocol):
    """Protocol for Depends-like classes from any framework.

    This protocol defines the minimal interface that a Depends class must have
    to be recognized by TinyDiCtx. It is compatible with:
    - tiny-fastapi-di's Depends
    - FastAPI's Depends
    - Docket's Depends

    Attribute:
        dependency: The callable to invoke for this dependency. May be None
            if the callable should be inferred from the type annotation.

    Optional attribute (not declared in protocol, checked at runtime):
        use_cache: bool - Whether to cache the result (default: True if not present)
    """

    dependency: Callable[..., Any] | None


@dataclass
class Depends:
    """Marks a parameter as a dependency to be resolved by TinyDiCtx."""

    dependency: Callable[..., Any] | None = None
    use_cache: bool = True
    scope: Any = None  # FastAPI compatibility; ignored by tiny-fastapi-di


no_value = object()


@dataclass
class TinyDiCtx:
    value_map: dict[str, Any]
    fn_map: dict[Callable[..., Any], Callable[..., Any]]
    validator: TypeValidator | None
    depends_types: tuple[DependsProtocol, ...]
    _cache: dict = field(repr=False, init=False)
    _lock: set = field(repr=False, init=False, default_factory=set)
    _cleanup_stack: list = field(repr=False, init=False, default_factory=list)

    def __post_init__(self):
        self._cache = {TinyDiCtx: self}

    def with_maps(self, fn_map=no_value, validator=no_value, depends_types=no_value, **kwargs):
        value_map2 = {**self.value_map, **kwargs} if kwargs else self.value_map
        fn_map2 = {**self.fn_map, **fn_map} if fn_map is not no_value else self.fn_map
        if validator is no_value:
            validator2 = self.validator
        else:
            validator2 = validator
        if depends_types is no_value:
            depends_types2 = self.depends_types
        else:
            depends_types2 = depends_types

        return TinyDiCtx(
            value_map=value_map2,
            fn_map=fn_map2,
            validator=validator2,
            depends_types=depends_types2,
        )

    async def call_fn(
        self,
        fn: Callable[..., Any],
        fn_map: dict[Callable[..., Any], Callable[..., Any]] | None = None,
        validator: TypeValidator | None = None,
        depends_types: tuple[DependsProtocol, ...] | None = None,
        **kwargs: Any,
    ) -> Any:
        """Call a function with dependency injection.

        This is the main entry point. Creates a scoped context and ensures
        proper cleanup of yield-based dependencies.

        Args:
            fn: The function to call with injected dependencies.
            fn_map: Optional function substitutions (for testing/mocking).
            validator: Optional type validator (e.g., Pydantic).
            depends_types: Tuple of Depends-like classes to recognize.
            **kwargs: Values to inject by parameter name.

        Returns:
            The result of calling fn with resolved dependencies.
        """
        fn_map_arg = no_value if fn_map is None else fn_map
        validator_arg = no_value if validator is None else validator
        depends_types_arg = no_value if depends_types is None else depends_types
        async with self.with_maps(
            fn_map=fn_map_arg, validator=validator_arg, depends_types=depends_types_arg, **kwargs
        ) as ctx:
            return await ctx._resolve_fn(fn)

    async def _resolve_fn(self, fn: Callable[..., Any], use_cache: bool = True) -> Any:
        """Apply fn_map substitution and manage caching."""
        if fn in self.fn_map:
            fn = self.fn_map[fn]
        if use_cache:
            if fn not in self._cache:
                self._cache[fn] = await self._invoke_fn(fn)
            return self._cache[fn]
        return await self._invoke_fn(fn)

    async def _invoke_fn(self, fn: Callable[..., Any]) -> Any:
        """Actually call the function with resolved arguments."""
        if fn in self._lock:
            fn_name = getattr(fn, '__name__', repr(fn))
            raise RecursionError(
                f"Circular dependency detected: {fn_name}() is already being resolved. "
                f"Check the dependency chain for cycles."
            )
        try:
            self._lock.add(fn)
            try:
                params = signature(fn).parameters.values()
            except TypeError as e:
                raise TypeError(f"Depends() requires a callable, got {type(fn).__name__}: {fn}") from e
            kwargs = {p.name: await self._solve_arg(param=p) for p in params}
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

    async def _solve_arg(self, param: Parameter) -> Any:
        annotation = param.annotation
        default = param.default

        # Unwrap Annotated: Annotated[User, Depends(...)] -> annotation=User, default=Depends(...)
        if get_origin(annotation) is Annotated:
            args = get_args(annotation)
            annotation = args[0]
            for meta in args[1:]:
                if isinstance(meta, self.depends_types):
                    default = meta
                    break

        if isinstance(default, self.depends_types):
            fn = getattr(default, "dependency", None) or annotation
            if fn is Parameter.empty:
                raise TypeError(
                    f"Depends() for parameter '{param.name}' has no callable. "
                    f"Provide Depends(callable) or use Annotated[Type, Depends()] with a type annotation."
                )
            use_cache = getattr(default, "use_cache", True)
            value = await self._resolve_fn(fn=fn, use_cache=use_cache)
        elif param.name in self.value_map:
            value = self.value_map[param.name]
        elif param.default is not Parameter.empty:
            value = param.default
        else:
            raise TypeError(
                f"No value provided for required argument '{param.name}'. "
                f"Provide via call_fn(**kwargs), Depends() default, or parameter default."
            )
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


empty_di_ctx = TinyDiCtx(value_map={}, fn_map={}, validator=None, depends_types=(Depends,))
