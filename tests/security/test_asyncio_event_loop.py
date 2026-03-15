import ast
from pathlib import Path


SERVER_PY = Path(__file__).resolve().parents[2] / 'server.py'


def _parse_server():
    return ast.parse(SERVER_PY.read_text(), filename=str(SERVER_PY))


def _get_function(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def test_no_bare_get_event_loop_in_server():
    """Verify no bare asyncio.get_event_loop() calls remain in server.py."""
    content = SERVER_PY.read_text()
    tree = _parse_server()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == 'get_event_loop':
            if isinstance(node.value, ast.Name) and node.value.id == 'asyncio':
                lineno = node.lineno
                line = content.splitlines()[lineno - 1].strip()
                assert line.startswith('#'), \
                    f'Found bare asyncio.get_event_loop() at line {lineno}: {line}'


def test_run_tasks_uses_new_event_loop():
    """Verify run_tasks creates a new event loop and sets it."""
    content = SERVER_PY.read_text()
    tree = _parse_server()
    func_node = _get_function(tree, 'run_tasks')
    assert func_node is not None, 'run_tasks not found in server.py'
    func_src = ast.get_source_segment(content, func_node)
    assert 'asyncio.new_event_loop()' in func_src
    assert 'asyncio.set_event_loop(loop)' in func_src


def test_run_tasks_closes_loop():
    """Verify run_tasks closes the event loop in a finally block."""
    tree = _parse_server()
    func_node = _get_function(tree, 'run_tasks')
    assert func_node is not None, 'run_tasks not found in server.py'
    # Check for a finally handler containing loop.close()
    has_finally_close = False
    for node in ast.walk(func_node):
        if isinstance(node, ast.Try):
            for handler in node.finalbody:
                for child in ast.walk(handler):
                    if (isinstance(child, ast.Attribute) and child.attr == 'close'
                            and isinstance(child.value, ast.Name) and child.value.id == 'loop'):
                        has_finally_close = True
    assert has_finally_close, 'run_tasks must close the event loop in a finally block'
