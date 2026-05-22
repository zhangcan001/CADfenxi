import atexit
import contextlib
import sys
from collections.abc import Generator
from typing import Any


if sys.platform.startswith("win"):
    # Python 3.14 on Windows creates a TCP socket pair for every TestClient event
    # loop. The full suite opens hundreds of TestClient contexts and can exhaust
    # local socket buffers, so tests reuse one AnyIO portal across contexts.
    import anyio.from_thread

    _original_start_blocking_portal = anyio.from_thread.start_blocking_portal
    _portal_context: Any | None = None
    _portal: Any | None = None

    def _close_reused_portal() -> None:
        global _portal_context, _portal
        if _portal_context is not None:
            _portal_context.__exit__(None, None, None)
            _portal_context = None
            _portal = None

    @contextlib.contextmanager
    def _reused_start_blocking_portal(*args: Any, **kwargs: Any) -> Generator[Any, None, None]:
        global _portal_context, _portal
        if _portal is None:
            _portal_context = _original_start_blocking_portal(*args, **kwargs)
            _portal = _portal_context.__enter__()
            atexit.register(_close_reused_portal)
        yield _portal

    anyio.from_thread.start_blocking_portal = _reused_start_blocking_portal
