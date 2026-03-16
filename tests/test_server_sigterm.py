"""Tests for SIGTERM handling in server.py (issue #3018).

When Caldera runs as a systemd service, shutdown sends SIGTERM rather than
SIGINT/KeyboardInterrupt.  Without a handler, teardown() is never called and
in-memory state (operations, etc.) is lost.  The fix registers a SIGTERM
handler that converts the signal into KeyboardInterrupt so the existing
teardown path is reused.
"""
import ast
import inspect
import os
import signal
import sys
import types
import unittest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# AST-level structural check
# ---------------------------------------------------------------------------

class TestSigtermHandlerStructure(unittest.TestCase):
    """Verify, without importing server.py, that the SIGTERM handler is
    registered inside run_tasks() using pure AST inspection."""

    def _parse_server(self):
        server_path = os.path.join(
            os.path.dirname(__file__), '..', 'server.py'
        )
        with open(os.path.normpath(server_path)) as fh:
            return ast.parse(fh.read())

    def test_signal_module_imported(self):
        tree = self._parse_server()
        imports = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Import)
        ]
        signal_imported = any(
            alias.name == 'signal'
            for imp in imports
            for alias in imp.names
        )
        self.assertTrue(signal_imported, "'import signal' not found in server.py")

    def _get_run_tasks_body(self):
        tree = self._parse_server()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == 'run_tasks':
                return node
        return None

    def test_sigterm_registered_in_run_tasks(self):
        run_tasks = self._get_run_tasks_body()
        self.assertIsNotNone(run_tasks, "run_tasks() function not found in server.py")

        # Look for signal.signal(signal.SIGTERM, ...) call anywhere inside run_tasks
        sigterm_calls = []
        for node in ast.walk(run_tasks):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == 'signal'):
                continue
            if len(node.args) < 1:
                continue
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Attribute) and first_arg.attr == 'SIGTERM':
                sigterm_calls.append(node)

        self.assertTrue(
            len(sigterm_calls) >= 1,
            "signal.signal(signal.SIGTERM, ...) not found inside run_tasks() in server.py"
        )

    def test_sigterm_handler_raises_keyboard_interrupt(self):
        """The SIGTERM handler function body must raise KeyboardInterrupt."""
        run_tasks = self._get_run_tasks_body()
        self.assertIsNotNone(run_tasks)

        # Find signal.signal(signal.SIGTERM, handler_name) and then verify the
        # handler's body raises KeyboardInterrupt.
        handler_name = None
        for node in ast.walk(run_tasks):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == 'signal'):
                continue
            if len(node.args) < 2:
                continue
            first_arg = node.args[0]
            if isinstance(first_arg, ast.Attribute) and first_arg.attr == 'SIGTERM':
                second_arg = node.args[1]
                if isinstance(second_arg, ast.Name):
                    handler_name = second_arg.id
                break

        self.assertIsNotNone(handler_name, "Could not determine SIGTERM handler name")

        # Locate the handler function definition inside run_tasks
        for node in ast.walk(run_tasks):
            if isinstance(node, ast.FunctionDef) and node.name == handler_name:
                raises = [
                    n for n in ast.walk(node)
                    if isinstance(n, ast.Raise)
                    and n.exc is not None
                    and (
                        (isinstance(n.exc, ast.Call) and
                         isinstance(n.exc.func, ast.Name) and
                         n.exc.func.id == 'KeyboardInterrupt')
                        or
                        (isinstance(n.exc, ast.Name) and n.exc.id == 'KeyboardInterrupt')
                    )
                ]
                self.assertTrue(
                    len(raises) >= 1,
                    f"Handler '{handler_name}' does not raise KeyboardInterrupt"
                )
                return

        self.fail(f"Handler function '{handler_name}' not found inside run_tasks()")


# ---------------------------------------------------------------------------
# Behavioural check: sending SIGTERM to self raises KeyboardInterrupt
# ---------------------------------------------------------------------------

class TestSigtermRaisesKeyboardInterrupt(unittest.TestCase):
    """Install the same handler logic used in server.py and verify that
    sending SIGTERM to the current process raises KeyboardInterrupt."""

    def setUp(self):
        self._original_handler = signal.getsignal(signal.SIGTERM)

    def tearDown(self):
        signal.signal(signal.SIGTERM, self._original_handler)

    def test_sigterm_raises_keyboard_interrupt(self):
        def _handle_sigterm(*args):
            raise KeyboardInterrupt

        signal.signal(signal.SIGTERM, _handle_sigterm)

        with self.assertRaises(KeyboardInterrupt):
            os.kill(os.getpid(), signal.SIGTERM)


if __name__ == '__main__':
    unittest.main()
