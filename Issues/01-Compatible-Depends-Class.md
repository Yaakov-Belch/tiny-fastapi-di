# Issue 01: Compatible Depends Class Across Frameworks

## Problem Statement

When building a distributed system with a **server** (using FastAPI or Docket) and a **worker** (using tiny-fastapi-di), developers often want to share dependency definitions between both environments. The challenge is:

1. **Different frameworks, same pattern**: FastAPI, Docket, and tiny-fastapi-di all use a `Depends` class for dependency injection, but they are distinct implementations.

2. **Environment constraints**: Workers should remain lightweight and not load heavy web frameworks. Workers may use different virtual environments where FastAPI or Docket are not installed.

3. **Shared code packages**: Business logic packages defining dependencies should work in both server and worker contexts without modification.

**Current limitation**: The `_solve_arg` method in `TinyDiCtx` checks `isinstance(meta, Depends)` against tiny-fastapi-di's own `Depends` class only (line 122 of `core.py`):

```python
if isinstance(meta, Depends):
    default = meta
    break
```

This means dependencies declared with FastAPI's or Docket's `Depends` are not recognized.

---

## Use Case

```
┌─────────────────────┐     ┌──────────────────────┐
│   Web Server        │     │   Worker Process     │
│   (FastAPI/Docket)  │     │   (tiny-fastapi-di)  │
│                     │     │                      │
│   - Heavy framework │     │   - Lightweight      │
│   - HTTP handling   │     │   - No web framework │
│   - Full features   │     │   - Different venv   │
└──────────┬──────────┘     └──────────┬───────────┘
           │                           │
           └───────────┬───────────────┘
                       │
            ┌──────────▼──────────┐
            │  Shared Package     │
            │  - Business logic   │
            │  - Dependency defs  │
            │  - Services         │
            └─────────────────────┘
```

The shared package declares dependencies like:

```python
# shared_package/services.py
from ??? import Depends  # Which Depends to import?

def get_database():
    return DatabaseConnection()

def get_user_service(db=Depends(get_database)):
    return UserService(db)
```

The question: **Which `Depends` should the shared package import?**

---

## Research: Comparing Depends Implementations

### FastAPI's Depends

**Source**: `fastapi/params.py`

```python
@dataclass(frozen=True)
class Depends:
    dependency: Optional[Callable[..., Any]] = None
    use_cache: bool = True
    scope: Union[Literal["function", "request"], None] = None
```

**Key attributes**:
| Attribute | Type | Default | Purpose |
|-----------|------|---------|---------|
| `dependency` | `Optional[Callable]` | `None` | The callable to invoke |
| `use_cache` | `bool` | `True` | Cache result within request |
| `scope` | `Literal["function", "request"] | None` | `None` | Caching scope control |

**Notes**:
- Frozen dataclass (immutable)
- `dependency` attribute name (not `fn`)
- Has `scope` attribute that tiny-fastapi-di lacks

### Docket's Depends

**Source**: `docket/dependencies.py`

```python
class _Depends(Dependency, Generic[R]):
    dependency: DependencyFunction[R]

    cache: ContextVar[dict[DependencyFunction[Any], Any]] = ContextVar("cache")
    stack: ContextVar[AsyncExitStack] = ContextVar("stack")

    def __init__(self, dependency: Callable[[], R | Awaitable[R] | ...]) -> None:
        self.dependency = dependency
```

**Key observations**:
- Uses `dependency` attribute (same as FastAPI)
- Generic class with `R` type parameter
- Has class-level `ContextVar` for caching (different approach)
- No explicit `use_cache` parameter (always caches via ContextVar)

### tiny-fastapi-di's Depends

**Source**: `src/tiny_fastapi_di/core.py`

```python
@dataclass
class Depends:
    fn: Callable[..., Any] | None = None
    use_cache: bool = True
```

**Key attributes**:
| Attribute | Type | Default | Purpose |
|-----------|------|---------|---------|
| `fn` | `Callable | None` | `None` | The callable to invoke |
| `use_cache` | `bool` | `True` | Cache result within call_fn |

### Comparison Matrix

| Attribute | FastAPI | Docket | tiny-fastapi-di |
|-----------|---------|--------|-----------------|
| Callable attr name | `dependency` | `dependency` | `fn` |
| use_cache | `bool = True` | (implicit) | `bool = True` |
| scope | `Literal | None` | N/A | N/A |
| Frozen | Yes | No | No |
| Generic | No | Yes (`R`) | No |

**Key Compatibility Issue**: FastAPI and Docket use `dependency`, while tiny-fastapi-di uses `fn`.

---

## Implementation Plan

### Phase 1: Make Depends Class Configurable

Add a new configuration member to `TinyDiCtx` that specifies which `Depends` class(es) to recognize.

#### Option A: Single or Sequence (Matches `isinstance()` Behavior)

```python
@dataclass
class TinyDiCtx:
    value_map: dict[str, Any]
    fn_map: dict[Callable[..., Any], Callable[..., Any]]
    validator: TypeValidator | None
    depends_types: type | tuple[type, ...] = Depends  # NEW
```

Usage in `_solve_arg`:

```python
if isinstance(meta, self.depends_types):
    # Extract callable: try both 'dependency' and 'fn' attributes
    fn = getattr(meta, 'dependency', None) or getattr(meta, 'fn', None) or annotation
    use_cache = getattr(meta, 'use_cache', True)
    ...
```

#### Option B: Always a Tuple (Clearer API)

```python
depends_types: tuple[type, ...] = (Depends,)
```

This avoids ambiguity and matches how users would provide multiple types.

### Phase 2: Define DependsProtocol (Optional)

A protocol for type checking compatibility:

```python
@runtime_checkable
class DependsProtocol(Protocol):
    @property
    def use_cache(self) -> bool: ...

    def get_callable(self) -> Callable[..., Any] | None: ...
```

**Trade-off**: FastAPI and Docket don't have `get_callable()` method; they have attributes. A protocol may not add much value for duck-typing via `isinstance()`.

### Phase 3: Update `with_maps()` and `call_fn()`

```python
def with_maps(self, fn_map=no_value, validator=no_value, depends_types=no_value, **kwargs):
    ...
    depends_types2 = self.depends_types if depends_types is no_value else depends_types
    return TinyDiCtx(
        value_map=value_map2,
        fn_map=fn_map2,
        validator=validator2,
        depends_types=depends_types2,
    )

async def call_fn(self, fn, fn_map=None, validator=None, depends_types=None, **kwargs):
    ...
```

### Phase 4: Update `empty_di_ctx`

```python
empty_di_ctx = TinyDiCtx(
    value_map={},
    fn_map={},
    validator=None,
    depends_types=(Depends,),  # Our own Depends by default
)
```

### Phase 5: Handle Attribute Name Differences

In `_solve_arg`, extract the callable flexibly:

```python
if isinstance(meta, self.depends_types):
    # Try FastAPI/Docket's 'dependency' first, then our 'fn'
    fn = getattr(meta, 'dependency', None) or getattr(meta, 'fn', None) or annotation
    use_cache = getattr(meta, 'use_cache', True)  # Default True if missing
    ...
```

---

## Research: Environment-Aware Imports

**Question**: Can we provide a package that exports the "correct" `Depends` at import time?

### Common Patterns

**1. Try/Except ImportError**

```python
# compat.py
try:
    from fastapi import Depends
except ImportError:
    try:
        from docket import Depends
    except ImportError:
        from tiny_fastapi_di import Depends
```

**Limitation**: Import order is arbitrary. What if both FastAPI and Docket are installed?

**2. Environment Variable**

```python
import os
DEPENDS_SOURCE = os.environ.get("DEPENDS_SOURCE", "auto")

if DEPENDS_SOURCE == "fastapi":
    from fastapi import Depends
elif DEPENDS_SOURCE == "docket":
    from docket import Depends
elif DEPENDS_SOURCE == "tiny":
    from tiny_fastapi_di import Depends
else:  # auto
    # Try/except chain
    ...
```

**Limitation**: Requires environment configuration. Adds deployment complexity.

**3. Entry Point Detection (Framework-Specific)**

Check if running in an ASGI server vs. worker process. This is fragile and framework-specific.

**4. Explicit Configuration in Shared Package**

```python
# shared_package/__init__.py
from shared_package._compat import configure_depends

# User must call this before importing dependencies
configure_depends("fastapi")  # or "docket" or "tiny"
```

**Limitation**: Requires explicit initialization.

### Recommendation

The **try/except pattern with priority order** is simplest:

```python
# shared_package/compat.py
try:
    from fastapi import Depends
    DEPENDS_SOURCE = "fastapi"
except ImportError:
    try:
        from docket import Depends  # or: from pydocket import Depends
        DEPENDS_SOURCE = "docket"
    except ImportError:
        from tiny_fastapi_di import Depends
        DEPENDS_SOURCE = "tiny"
```

Combined with our configurable `depends_types` in `TinyDiCtx`, users can:

1. **On the server**: Use FastAPI/Docket's `Depends` natively.
2. **On the worker**: Configure `TinyDiCtx` to recognize all `Depends` types:

```python
from fastapi import Depends as FastApiDepends
from tiny_fastapi_di import Depends, empty_di_ctx

worker_ctx = empty_di_ctx.with_maps(
    depends_types=(Depends, FastApiDepends)
)
```

Or, if FastAPI is not installed on the worker, just use tiny-fastapi-di's `Depends` (which is the default).

---

## Open Questions

### 1. Naming: `depends_types` vs `depends_classes`?

| Name | Pros | Cons |
|------|------|------|
| `depends_types` | Matches Python's `isinstance(obj, types)` terminology | Slightly technical |
| `depends_classes` | More explicit about what's expected | "Classes" is less accurate; could be any type |
| `depends` | Short | Ambiguous; conflicts with `Depends` class |
| `recognizes` | Descriptive of behavior | Non-standard naming |

### 2. Singular or Tuple?

Should the parameter accept:
- **Only tuples**: `depends_types: tuple[type, ...]` (consistent, clear)
- **Single or tuple**: `type | tuple[type, ...]` (flexible, matches `isinstance()`)

### 3. Should We Rename `fn` to `dependency`?

For consistency with FastAPI and Docket, we could rename our `fn` attribute to `dependency`. This is a **breaking change** but would simplify the attribute extraction logic.

### 4. Should the Shared Package Be Part of This Repo?

Should tiny-fastapi-di provide a `compat` module for the try/except import pattern? Or leave it to users?

---

## Documentation Updates Required

1. **New section**: "Working with Multiple Frameworks"
2. **Update `TinyDiCtx` documentation**: Add `depends_types` parameter
3. **Example**: Server + Worker shared code pattern
4. **Migration guide**: If we rename `fn` to `dependency`

---

## My Opinion on Naming

**Recommendation: `depends_types`**

1. **Consistency with Python**: `isinstance(obj, types)` uses "types" not "classes".
2. **Consistency with codebase**: We have `TypeValidator`, not `ClassValidator`.
3. **Always a tuple**: I recommend always accepting a tuple, like `(Depends,)`. This avoids special-casing and matches how users would add multiple types. The constructor and `with_maps` should accept `tuple[type, ...]`.

However, the flexibility of `type | tuple[type, ...]` does match Python's `isinstance()` signature exactly, which users already understand.

**My preference**: Accept `tuple[type, ...]` only, with a clear error message if a single type is passed. This trades minor convenience for API clarity.

---

## Analysis Through Three Lenses

### Literal: What Is Said?

The issue describes a technical compatibility problem: `TinyDiCtx._solve_arg()` only recognizes its own `Depends` class, preventing shared code from working across FastAPI, Docket, and tiny-fastapi-di environments.

The proposed solution adds a configurable `depends_types` parameter to `TinyDiCtx` that specifies which `Depends` implementations to recognize. The implementation requires handling different attribute names (`fn` vs `dependency`) across implementations.

### Interpretive: What Does This Mean?

**Architectural Implication**: tiny-fastapi-di is evolving from a "FastAPI-compatible" library to an "interoperability layer" for dependency injection across multiple frameworks. This positions it as:

1. **A bridge technology**: Enabling code sharing between web servers and workers.
2. **A testing/mocking tool**: Workers can simulate server-side DI without heavy frameworks.
3. **A standardization effort**: Implicitly defining what a "Depends-like" object should look like.

**User Mental Model**: Users will think of `TinyDiCtx` as a DI runtime that can "understand" multiple DI notations, rather than a framework with its own DI syntax.

**Trade-off Space**: The solution trades some purity (hardcoded `Depends`) for flexibility (configurable types). This is the right trade for a library aiming to be a lightweight alternative.

### Tension: Important Unresolved Questions

**1. Semantic Drift Between Frameworks**

FastAPI's `Depends` has a `scope` parameter that tiny-fastapi-di lacks. If shared code uses `Depends(..., scope="request")`, what should tiny-fastapi-di do?

- Ignore unknown attributes silently? (Pragmatic but lossy)
- Warn about unrecognized attributes? (Noisy)
- Fail? (Strict but breaks interoperability goal)

**2. Version Coupling**

If FastAPI changes its `Depends` class (adds/removes attributes), shared code may break on the worker. tiny-fastapi-di becomes implicitly coupled to FastAPI's API stability.

**3. The "Correct" Depends Problem**

The auto-detection approach (try/except import chain) has hidden assumptions:
- Import order implies priority
- "Whichever is installed" may not match user intent
- Testing becomes environment-dependent

A truly robust solution might require explicit configuration, but that adds ceremony.

**4. Identity vs. Structural Typing**

The solution uses `isinstance()` which checks identity/inheritance. An alternative is structural typing (duck typing): if it has `dependency` or `fn` and `use_cache`, treat it as Depends-like. This would work with any compatible class, even from unknown frameworks.

However, this risks false positives: what if a user's unrelated class happens to have these attributes?

**5. Should tiny-fastapi-di Adopt FastAPI's Naming?**

Renaming `fn` to `dependency` would be a breaking change but aligns with the broader ecosystem. Is ecosystem alignment worth the migration pain? For a library claiming "FastAPI-compatible patterns," using different attribute names is a subtle but real incompatibility.

---

## Next Steps

1. Decide on attribute naming (`depends_types` recommended)
2. Decide on type signature (tuple-only vs single-or-tuple)
3. Decide whether to rename `fn` to `dependency` (breaking change)
4. Implement the configurable `depends_types`
5. Update documentation with new patterns
6. Consider providing a `compat` module in a future version
● Session Retrospective                                                                      
                                                                                             
  What Slowed Us Down                                                                        
                                                                                             
  1. Research was scattered - Multiple web searches/fetches for FastAPI and Docket. A single 
  targeted GitHub fetch would have been faster.                                              
  2. Over-engineered the initial implementation:                                             
    - Added scope attribute (you removed it)                                                 
    - Added single-type normalization (you removed it)                                       
    - Wrote verbose docstrings (you simplified them)                                         
    - I was trying to be "helpful" but added complexity you didn't want.                     
  3. Created a verbose issue document - 200+ lines when a focused analysis would have        
  sufficed.                                                                                  
  4. Implemented before validating decisions - I built features that were later removed.     
  Should have confirmed design choices first.                                                
                                                                                             
  How to Improve Next Time                                                                   
  ┌──────────────────────────┬────────────────────────────────────────────────┐              
  │         Problem          │                    Solution                    │              
  ├──────────────────────────┼────────────────────────────────────────────────┤              
  │ Over-engineering         │ Ask upfront: "Minimal or flexible API?"        │              
  ├──────────────────────────┼────────────────────────────────────────────────┤              
  │ Verbose docs             │ Ask upfront: "Documentation style preference?" │              
  ├──────────────────────────┼────────────────────────────────────────────────┤              
  │ Removed features         │ Propose design, get approval, then implement   │              
  ├──────────────────────────┼────────────────────────────────────────────────┤              
  │ Scattered research       │ One targeted fetch per source, in parallel     │              
  ├──────────────────────────┼────────────────────────────────────────────────┤              
  │ Test for removed feature │ Only test documented/intentional behavior      │              
  └──────────────────────────┴────────────────────────────────────────────────┘              
  What Worked Well                                                                           
                                                                                             
  - The three lenses analysis (but should use it during design, not after)                   
  - Incremental commits with clear messages                                                  
  - Running tests after each change                                                          
  - The _resolve_fn/_invoke_fn refactor discussion before implementation                     
                                                                                             
  Key Lesson                                                                                 
                                                                                             
  Ask first, implement second. A 2-minute conversation about "should depends_types accept    
  single types?" would have saved the implementation and removal cycle.                      
                                                                                             
❯ I appended your answer to the Issues document.  This is valuable.  Let's trace your        
  points back to what **I** could have improved.  I see the following points:                
  * (1) Provide you with a better web search tool (tavily).  Note:  You did your work        
  well and even though the search took many steps, it did not take much time and             
  produced the desired result.  But having more precise tools is important because you       
  could have missed important details without them.                                          
  * (2,4) The real problem is that you did not know what I really want -- and I did not      
  know either until I saw your work.  I did not know about the `scope` attribute and I       
  needed to make a real decision about how I want to handle it.  Your approach of making     
  your own informed choices is right -- even when I eventually disagree.  The lever to       
  make this more efficient is to find a way to highlight all these decisions that you        
  took (without the decisions that I already confirmed) so that I can find them without      
  having to review every of your changes.  Also -- I would need to document my               
  preferences (concise vs. verbose code) in a clear way for you to find out whenever you     
  need. Sometimes it's better to ask first, sometimes it's better to show what you           
  think and get a feedback on the solution.  How do we decide what's best in each case?      
  Often, we can live with the other approach.                                                
  * I like the issue document:  I need it to improve my own work.  This is extra value       
  created. What do you think?                                                                
                                                                                             
● Your reframing is insightful. Let me engage with each point:                               
                                                                                             
  On (2,4): "You didn't know, I didn't know"                                                 
                                                                                             
  This is the core insight: decisions emerge from seeing concrete work. You couldn't have    
  told me "no scope attribute" before I showed you the research revealing it exists.         
                                                                                             
  When to ask first vs. show work:                                                           
  ┌─────────────────────────────────────────┬──────────────────────────────────────────┐     
  │                Ask First                │             Show Work First              │     
  ├─────────────────────────────────────────┼──────────────────────────────────────────┤     
  │ Decision affects public API contract    │ Decision is about implementation details │     
  ├─────────────────────────────────────────┼──────────────────────────────────────────┤     
  │ Costly to undo (breaking change)        │ Easy to undo (internal refactor)         │     
  ├─────────────────────────────────────────┼──────────────────────────────────────────┤     
  │ Clear alternatives with known tradeoffs │ Need to see it concrete to evaluate      │     
  ├─────────────────────────────────────────┼──────────────────────────────────────────┤     
  │ User has stated preferences             │ User's preference is unknown             │     
  └─────────────────────────────────────────┴──────────────────────────────────────────┘     
  The lever you identified: Surface decisions without requiring full review. Options:        
                                                                                             
  1. Decisions summary at the end of implementation: "Decisions I made: (a) added scope for  
  FastAPI compat, (b) allowed single-type, (c) verbose docstrings"                           
  2. Mark uncertain decisions in code with # DECISION: comments (removed after review)       
  3. CLAUDE.md preferences: Document your style ("prefer concise docstrings", "explicit APIs 
  over flexible ones")                                                                       
                                                                                             
  On the Issue Document                                                                      
                                                                                             
  You're right - it's valuable. It forced structured thinking about the problem before       
  coding. The three lenses section caught tensions that would have surfaced later anyway.    
                                                                                             
  The document serves two purposes:                                                          
  1. Alignment tool (before implementation)                                                  
  2. Decision record (after implementation)                                                  
                                                                                             
  Both are worth the time invested.                                                          
