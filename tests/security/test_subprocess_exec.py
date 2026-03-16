import ast
from pathlib import Path


SERVER_PY = Path(__file__).resolve().parents[2] / 'server.py'


def test_no_create_subprocess_shell_in_start_vue():
    """Verify create_subprocess_shell is not used in start_vue_dev_server."""
    content = SERVER_PY.read_text(encoding='utf-8')
    tree = ast.parse(content, filename=str(SERVER_PY))
    func_node = None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == 'start_vue_dev_server':
            func_node = node
            break
    assert func_node is not None, "start_vue_dev_server function not found in server.py"
    func_content = ast.get_source_segment(content, func_node)
    assert func_content is not None, "Could not extract source for start_vue_dev_server"
    assert 'create_subprocess_shell' not in func_content
    assert 'create_subprocess_exec' in func_content
