"""Persistent Wolfram kernel manager using WSTP via wolframclient.

The kernel manager handles lifecycle (start/stop/restart), expression
evaluation with thread-safe serialization, configurable init scripts,
and per-context_id namespace isolation.

Configuration via environment variables:
    ELEGUA_WOLFRAM_INIT: Path to a .wl init script loaded on first
        ``/evaluate-with-init`` call. No default — the server starts
        with a bare Wolfram kernel unless configured.
    ELEGUA_WOLFRAM_CLEANUP: Wolfram expression executed on ``/cleanup``.
        Defaults to clearing the Global context only.
"""

from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wolframclient.evaluation import WolframLanguageSession


def _import_wolframclient() -> tuple[type, Any]:
    """Lazy-import wolframclient (only needed at runtime with elegua[wolfram])."""
    try:
        from wolframclient.evaluation import WolframLanguageSession as WLS
        from wolframclient.language import wlexpr as _wlexpr
    except ImportError as exc:
        msg = (
            "wolframclient is required for the Wolfram oracle server. "
            "Install it with: pip install elegua[wolfram]"
        )
        raise ImportError(msg) from exc
    return WLS, _wlexpr


_DEFAULT_CLEANUP = 'Unprotect["Global`*"]; ClearAll["Global`*"]; Remove["Global`*"]; "cleanup-ok"'


class KernelManager:
    """Manages a persistent Wolfram kernel with optional init script.

    Thread-safe: all kernel access is serialized via an RLock and a
    single-worker ThreadPoolExecutor.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._session: WolframLanguageSession | None = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._kernel_path = shutil.which("WolframKernel")
        self._init_loaded = False
        self._init_script: str | None = os.environ.get("ELEGUA_WOLFRAM_INIT")
        self._cleanup_expr: str = os.environ.get("ELEGUA_WOLFRAM_CLEANUP", _DEFAULT_CLEANUP)

    def start(self) -> None:
        """Start the Wolfram kernel."""
        if not self._kernel_path:
            msg = "WolframKernel not found on PATH; set an explicit kernel path."
            raise RuntimeError(msg)
        WLS, _ = _import_wolframclient()
        self._session = WLS(kernel_path=self._kernel_path)
        self._session.start()
        self._init_loaded = False

    @staticmethod
    def _wlexpr(s: str) -> Any:
        """Wrap a string as a Wolfram expression (lazy import)."""
        _, wlexpr_fn = _import_wolframclient()
        return wlexpr_fn(s)

    def _ensure_init(self) -> None:
        """Load the init script if configured and not already loaded."""
        if not self._init_loaded and self._init_script and self._session is not None:
            self._session.evaluate(self._wlexpr(f'Get["{self._init_script}"]'))
            self._init_loaded = True

    def ensure(self) -> None:
        """Ensure kernel is running, starting it if needed."""
        if self._session is None:
            self.start()

    def stop(self) -> None:
        """Stop the kernel."""
        if self._session is not None:
            try:
                self._session.terminate()
            except Exception:
                pass
            finally:
                self._session = None
                self._init_loaded = False

    def restart(self) -> None:
        """Hard-restart the kernel."""
        self.stop()
        self.start()

    def cleanup(self) -> tuple[bool, str | None, str | None]:
        """Execute the configured cleanup expression.

        Returns (ok, result, error).
        """
        with self._lock:
            self.ensure()
            if self._init_script:
                self._ensure_init()

            def _do_eval() -> Any:
                assert self._session is not None
                return self._session.evaluate(KernelManager._wlexpr(self._cleanup_expr))

            fut = self._executor.submit(_do_eval)
            try:
                result = fut.result(timeout=30)
                return True, str(result), None
            except FuturesTimeout:
                self.restart()
                return False, None, "cleanup timed out (kernel restarted)"
            except Exception as e:
                return False, None, f"{type(e).__name__}: {e}"

    def check_clean_state(self) -> tuple[bool, list[str]]:
        """Check for leaked symbols after cleanup.

        Returns (is_clean, leaked_symbols). The check expression is
        configurable — by default it checks that no Global symbols remain.
        """
        check_wl = (
            'Module[{syms = Names["Global`*"]}, '
            'StringJoin["G:", ToString[Length[syms]], ",", '
            'StringRiffle[syms, ","]]]'
        )
        with self._lock:
            self.ensure()
            if self._init_script:
                self._ensure_init()

            def _do_eval() -> Any:
                assert self._session is not None
                return self._session.evaluate(KernelManager._wlexpr(check_wl))

            fut = self._executor.submit(_do_eval)
            try:
                result_str = str(fut.result(timeout=10)).strip().strip('"')
                parts = result_str.split(",", 1)
                g_count = int(parts[0].replace("G:", "")) if parts else -1
                leaked = parts[1].split(",") if len(parts) > 1 and parts[1] else []
                leaked = [s for s in leaked if s]
                return (g_count == 0), leaked
            except (FuturesTimeout, Exception):
                return False, ["check_clean_state evaluation failed"]

    def evaluate(
        self,
        expr: str,
        timeout_s: int,
        with_init: bool = False,
        context_id: str | None = None,
    ) -> tuple[bool, str | None, str | None]:
        """Evaluate a Wolfram expression.

        Parameters:
            expr: The Wolfram expression string.
            timeout_s: Timeout in seconds.
            with_init: Whether to ensure the init script is loaded first.
            context_id: Optional unique ID for isolation.

        Returns (ok, result, error).
        """
        with self._lock:
            self.ensure()

            if context_id:
                safe_id = "".join(c for c in context_id if c.isalnum())
                unique_ctx = f"Elegua{safe_id}`"
                escaped_expr = expr.replace("\\", "\\\\").replace('"', '\\"')
                wrapped_expr = (
                    f'Block[{{$Context = "{unique_ctx}", '
                    f'$ContextPath = Prepend[$ContextPath, "{unique_ctx}"]}}, '
                    f'ToExpression["{escaped_expr}"]]'
                )
            else:
                wrapped_expr = expr

            def _do_eval() -> Any:
                if with_init:
                    self._ensure_init()
                assert self._session is not None
                return self._session.evaluate(KernelManager._wlexpr(wrapped_expr))

            fut = self._executor.submit(_do_eval)
            try:
                result = fut.result(timeout=timeout_s)
                return True, str(result), None
            except FuturesTimeout:
                self.restart()
                return (
                    False,
                    None,
                    f"Evaluation timed out after {timeout_s}s (kernel restarted)",
                )
            except Exception as e:
                self.restart()
                return False, None, f"{type(e).__name__}: {e} (kernel restarted)"
