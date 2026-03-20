"""Tests for KernelManager context isolation and concurrency.

These tests run offline — no real Wolfram kernel is needed.
wolframclient is stubbed out before importing KernelManager.
"""

from __future__ import annotations

import re
import sys
import threading
import time
import types
from unittest.mock import MagicMock

import pytest

# Stub wolframclient before importing kernel module.
_wc = types.ModuleType("wolframclient")
_wc_eval = types.ModuleType("wolframclient.evaluation")
_wc_lang = types.ModuleType("wolframclient.language")
_wc_eval.WolframLanguageSession = MagicMock  # type: ignore[attr-defined]
_wc_lang.wlexpr = lambda x: x  # type: ignore[attr-defined]  # identity so we can inspect strings
sys.modules.setdefault("wolframclient", _wc)
sys.modules.setdefault("wolframclient.evaluation", _wc_eval)
sys.modules.setdefault("wolframclient.language", _wc_lang)

from elegua.wolfram.kernel import KernelManager  # noqa: E402


def _make_km(evaluate_fn=None) -> KernelManager:  # type: ignore[no-untyped-def]
    """Create a KernelManager with a mocked session (no real kernel)."""
    km = KernelManager()
    mock_session = MagicMock()
    mock_session.start.return_value = None
    if evaluate_fn is not None:
        mock_session.evaluate.side_effect = evaluate_fn
    else:
        mock_session.evaluate.return_value = "ok"
    km._session = mock_session
    km._init_loaded = True
    return km


# --- Context isolation ---


class TestContextIdWrapping:
    """Verify context_id namespace isolation wrapping."""

    def test_no_context_id_passes_expr_unchanged(self) -> None:
        km = _make_km()
        km.evaluate("1 + 1", timeout_s=5, with_init=False, context_id=None)
        args, _ = km._session.evaluate.call_args
        assert args[0] == "1 + 1"

    def test_context_id_wraps_expr(self) -> None:
        km = _make_km()
        km.evaluate("1 + 1", timeout_s=5, with_init=False, context_id="abc-123")
        args, _ = km._session.evaluate.call_args
        assert args[0] != "1 + 1", "Expression should be wrapped when context_id is given"

    def test_context_id_value_appears_in_wrapped_expr(self) -> None:
        km = _make_km()
        km.evaluate("x = 42", timeout_s=5, with_init=False, context_id="test-abc-123")
        args, _ = km._session.evaluate.call_args
        wrapped = args[0]
        assert "testabc123" in wrapped.lower() or "abc123" in wrapped.lower(), (
            f"context_id not found in wrapped expr: {wrapped!r}"
        )

    def test_two_different_context_ids_produce_different_wrappers(self) -> None:
        km = _make_km()

        km.evaluate("x = 1", timeout_s=5, with_init=False, context_id="session-aaa")
        args_a, _ = km._session.evaluate.call_args

        km.evaluate("x = 2", timeout_s=5, with_init=False, context_id="session-bbb")
        args_b, _ = km._session.evaluate.call_args

        assert args_a[0] != args_b[0], (
            "Different context_ids must produce different wrapping contexts"
        )

    def test_same_context_id_produces_same_wrapper_context(self) -> None:
        km = _make_km()

        km.evaluate("a = 1", timeout_s=5, with_init=False, context_id="stable-id")
        args1, _ = km._session.evaluate.call_args

        km.evaluate("b = 2", timeout_s=5, with_init=False, context_id="stable-id")
        args2, _ = km._session.evaluate.call_args

        ctx_pattern = re.compile(r"Elegua\w+`")
        ctx1 = ctx_pattern.findall(args1[0])
        ctx2 = ctx_pattern.findall(args2[0])
        assert ctx1 and ctx2, "Context name not found in wrapped expressions"
        assert ctx1[0] == ctx2[0], (
            f"Same context_id should produce same context name: {ctx1[0]!r} != {ctx2[0]!r}"
        )

    def test_context_prefix_is_elegua(self) -> None:
        """Context prefix should be elegua-namespaced, not sxAct-namespaced."""
        km = _make_km()
        km.evaluate("x", timeout_s=5, with_init=False, context_id="test1")
        args, _ = km._session.evaluate.call_args
        assert "Elegua" in args[0]
        assert "SxAct" not in args[0]

    def test_expression_injection_via_quotes(self) -> None:
        """Expressions with quotes must not break out of ToExpression wrapping."""
        km = _make_km()
        payload = '"]; Quit[];"'
        km.evaluate(payload, timeout_s=5, with_init=False, context_id="inject-test")
        args, _ = km._session.evaluate.call_args
        wrapped = args[0]
        # The raw payload must NOT appear literally in the wrapped expression —
        # it must be encoded so Wolfram cannot parse it as code.
        assert payload not in wrapped, (
            f"Raw injection payload found in wrapped expression: {wrapped!r}"
        )
        # The session must receive exactly one evaluate call (no split execution).
        assert km._session.evaluate.call_count == 1

    def test_expression_injection_via_newline(self) -> None:
        """Newlines in expressions must not break the string literal."""
        km = _make_km()
        payload = 'x = 1\nDeleteDirectory["/tmp"]'
        km.evaluate(payload, timeout_s=5, with_init=False, context_id="nl-test")
        args, _ = km._session.evaluate.call_args
        wrapped = args[0]
        # A literal newline must not appear in the wrapped expression.
        assert "\n" not in wrapped, f"Literal newline found in wrapped expression: {wrapped!r}"
        assert km._session.evaluate.call_count == 1

    def test_expression_injection_via_backslash_sequence(self) -> None:
        """Backslash sequences must not create Wolfram escape codes."""
        km = _make_km()
        payload = r"x\"; Quit[]; \"y"
        km.evaluate(payload, timeout_s=5, with_init=False, context_id="bs-test")
        args, _ = km._session.evaluate.call_args
        wrapped = args[0]
        assert payload not in wrapped, (
            f"Raw injection payload found in wrapped expression: {wrapped!r}"
        )


# --- Concurrency ---


class TestKernelManagerConcurrency:
    """Verify RLock serializes concurrent requests."""

    def test_concurrent_evaluate_calls_serialize(self) -> None:
        call_order: list[tuple[str, str]] = []
        call_lock = threading.Lock()

        def slow_evaluate(expr):  # type: ignore[no-untyped-def]
            with call_lock:
                call_order.append(("start", threading.current_thread().name))
            time.sleep(0.05)
            with call_lock:
                call_order.append(("end", threading.current_thread().name))
            return "ok"

        km = _make_km(evaluate_fn=slow_evaluate)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                km.evaluate("1+1", timeout_s=5, with_init=False)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, name=f"t{i}") for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert not errors, f"Errors in worker threads: {errors}"

        active = 0
        for event, _ in call_order:
            if event == "start":
                active += 1
            else:
                active -= 1
            assert active <= 1, f"Concurrent evaluations detected: {call_order}"

    def test_rlock_is_reentrant(self) -> None:
        km = _make_km()
        with km._lock, km._lock:
            pass


# --- Lifecycle ---


class TestKernelLifecycle:
    """Verify start/stop/restart/ensure."""

    def test_stop_clears_session(self) -> None:
        km = _make_km()
        assert km._session is not None
        km.stop()
        assert km._session is None
        assert km._init_loaded is False

    def test_restart_stops_and_starts(self) -> None:
        km = _make_km()
        # Give it a kernel_path so start() won't raise
        km._kernel_path = "/usr/bin/WolframKernel"
        km.restart()
        # Session was replaced (stop killed old, start created new mock via __init__)
        assert km._init_loaded is False

    def test_cleanup_returns_ok(self) -> None:
        km = _make_km()
        ok, result, error = km.cleanup()
        assert ok is True
        assert result == "ok"
        assert error is None

    def test_evaluate_returns_result(self) -> None:
        km = _make_km()
        ok, result, error = km.evaluate("1+1", timeout_s=5)
        assert ok is True
        assert result == "ok"
        assert error is None


# --- Configurable init ---


class TestConfigurableInit:
    """Verify init script loading is configurable."""

    def test_no_init_script_by_default(self) -> None:
        km = KernelManager()
        # Default: no init script unless ELEGUA_WOLFRAM_INIT is set
        # The _ensure_init should be a no-op when no script is configured
        km._session = MagicMock()
        km._session.evaluate.return_value = "ok"
        km._init_loaded = False
        km._init_script = None
        km._ensure_init()
        assert km._init_loaded is False
        km._session.evaluate.assert_not_called()

    def test_init_script_loaded_when_configured(self) -> None:
        km = KernelManager()
        km._session = MagicMock()
        km._session.evaluate.return_value = "ok"
        km._init_loaded = False
        km._init_script = "/path/to/init.wl"
        km._ensure_init()
        assert km._init_loaded is True
        km._session.evaluate.assert_called_once()

    def test_init_script_loaded_only_once(self) -> None:
        km = KernelManager()
        km._session = MagicMock()
        km._session.evaluate.return_value = "ok"
        km._init_loaded = False
        km._init_script = "/path/to/init.wl"
        km._ensure_init()
        km._ensure_init()
        assert km._session.evaluate.call_count == 1


# --- Configurable cleanup ---


class TestConfigurableCleanup:
    """Verify cleanup expression is configurable."""

    @pytest.fixture(autouse=True)
    def _reset_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ELEGUA_WOLFRAM_CLEANUP", raising=False)

    def test_default_cleanup_clears_global(self) -> None:
        km = _make_km()
        km.cleanup()
        args, _ = km._session.evaluate.call_args
        expr = args[0]
        assert "Global" in expr

    def test_custom_cleanup_expression(self) -> None:
        km = _make_km()
        km._cleanup_expr = 'Manifolds = {}; Tensors = {}; "ok"'
        km.cleanup()
        args, _ = km._session.evaluate.call_args
        expr = args[0]
        assert "Manifolds" in expr
        assert "Tensors" in expr


# --- Assertions replaced with explicit checks (elegua-bwy) ---


class TestSessionNoneRaisesRuntimeError:
    """Assert statements are replaced with explicit RuntimeError checks."""

    def test_evaluate_with_none_session_raises_runtime_error(self) -> None:
        """evaluate() must raise RuntimeError (not AssertionError) if session is None."""
        km = _make_km()
        km._session = None
        # Bypass ensure() and restart() which would try to start a real kernel
        km.ensure = lambda: None  # type: ignore[assignment]
        km.restart = lambda: None  # type: ignore[assignment]
        ok, _result, error = km.evaluate("1+1", timeout_s=5)
        assert ok is False
        assert error is not None
        assert "RuntimeError" in error

    def test_cleanup_with_none_session_raises_runtime_error(self) -> None:
        km = _make_km()
        km._session = None
        km.ensure = lambda: None  # type: ignore[assignment]
        ok, _result, error = km.cleanup()
        assert ok is False
        assert error is not None
        assert "RuntimeError" in error

    def test_check_clean_state_with_none_session_raises_runtime_error(self) -> None:
        km = _make_km()
        km._session = None
        km.ensure = lambda: None  # type: ignore[assignment]
        is_clean, _leaked = km.check_clean_state()
        assert is_clean is False


# --- Executor shutdown (elegua-5i3) ---


class TestExecutorShutdown:
    """Verify ThreadPoolExecutor is shut down when KernelManager stops."""

    def test_stop_shuts_down_executor(self) -> None:
        km = _make_km()
        km.stop()
        assert km._executor._shutdown is True

    def test_context_manager_calls_stop(self) -> None:
        km = _make_km()
        with km:
            pass
        assert km._session is None
        assert km._executor._shutdown is True


# --- check_clean_state logging (elegua-53s) ---


class TestCheckCleanStateParsing:
    """Verify check_clean_state handles malformed responses."""

    def test_malformed_response_includes_actual_result(self) -> None:
        """When Wolfram returns unexpected output, the error should include it."""
        km = _make_km(evaluate_fn=lambda _: "UNEXPECTED GARBAGE")
        is_clean, leaked = km.check_clean_state()
        assert is_clean is False
        # The leaked list should contain something more useful than just
        # "check_clean_state evaluation failed"
        error_msg = " ".join(leaked)
        assert "UNEXPECTED" in error_msg or "ValueError" in error_msg


# --- Init path validation (elegua-pdf) ---


class TestInitPathValidation:
    """Verify ELEGUA_WOLFRAM_INIT path is validated at construction time."""

    def test_nonexistent_init_path_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ELEGUA_WOLFRAM_INIT", "/nonexistent/init.wl")
        with pytest.raises(FileNotFoundError, match="ELEGUA_WOLFRAM_INIT"):
            KernelManager()

    def test_valid_init_path_accepted(self, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
        init_file = tmp_path / "init.wl"
        init_file.write_text("(* init *)")
        monkeypatch.setenv("ELEGUA_WOLFRAM_INIT", str(init_file))
        km = KernelManager()
        assert km._init_script == str(init_file)
