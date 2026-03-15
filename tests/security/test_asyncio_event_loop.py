import ast
from pathlib import Path


SERVER_PY = Path(__file__).resolve().parents[2] / 'server.py'


def _parse_server():
    content = SERVER_PY.read_text()
    return content, ast.parse(content, filename=str(SERVER_PY))


def _get_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _is_asyncio_call(node, method):
    """Return True if node is a Call to asyncio.<method>(...)."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == 'asyncio'
    )


def test_no_bare_get_event_loop_in_server():
    """Verify no bare asyncio.get_event_loop() calls remain in server.py."""
    _, tree = _parse_server()
    for node in ast.walk(tree):
        if _is_asyncio_call(node, 'get_event_loop'):
            raise AssertionError(
                f'Found asyncio.get_event_loop() call at line {node.lineno} in server.py'
            )


def test_run_tasks_uses_new_event_loop():
    """Verify run_tasks creates a new event loop and sets it via AST inspection."""
    _, tree = _parse_server()
    func_node = _get_function(tree, 'run_tasks')
    assert func_node is not None, 'run_tasks not found in server.py'

    has_new_loop = any(_is_asyncio_call(n, 'new_event_loop') for n in ast.walk(func_node))
    has_set_loop = any(_is_asyncio_call(n, 'set_event_loop') for n in ast.walk(func_node))

    assert has_new_loop, 'run_tasks must call asyncio.new_event_loop()'
    assert has_set_loop, 'run_tasks must call asyncio.set_event_loop(loop)'


def test_run_tasks_closes_loop():
    """Verify run_tasks closes the event loop in a finally block."""
    _, tree = _parse_server()
    func_node = _get_function(tree, 'run_tasks')
    assert func_node is not None, 'run_tasks not found in server.py'
    has_finally_close = False
    for node in ast.walk(func_node):
        if isinstance(node, ast.Try):
            for handler in node.finalbody:
                for child in ast.walk(handler):
                    if (isinstance(child, ast.Attribute) and child.attr == 'close'
                            and isinstance(child.value, ast.Name) and child.value.id == 'loop'):
                        has_finally_close = True
    assert has_finally_close, 'run_tasks must close the event loop in a finally block'
