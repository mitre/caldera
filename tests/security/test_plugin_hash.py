"""Tests for plugin directory hash integrity checking."""
import pytest
from app.service.app_svc import AppService


def _make_tree(root, files):
    """Helper to create a file tree from a {relative_path: content} dict."""
    for path, content in files.items():
        full = root / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(content if isinstance(content, bytes) else content.encode())


def test_hash_is_deterministic(tmp_path):
    """Calling _compute_dir_hash on the same directory twice returns the same hash."""
    plugin = tmp_path / 'plugin'
    _make_tree(plugin, {'hook.py': b'print("hello")', 'data/file.txt': b'data'})
    h1 = AppService._compute_dir_hash(str(plugin))
    h2 = AppService._compute_dir_hash(str(plugin))
    assert h1 is not None
    assert h1 == h2


def test_hash_differs_on_content_change(tmp_path):
    """Modifying a file's content produces a different hash."""
    plugin = tmp_path / 'plugin'
    _make_tree(plugin, {'hook.py': b'version_1'})
    h1 = AppService._compute_dir_hash(str(plugin))

    (plugin / 'hook.py').write_bytes(b'version_2')
    h2 = AppService._compute_dir_hash(str(plugin))
    assert h1 != h2


def test_hash_nested_dirs_stable(tmp_path):
    """Hash is stable across repeated calls for a nested directory structure."""
    plugin = tmp_path / 'plugin'
    _make_tree(plugin, {
        'hook.py': b'root',
        'subdir/file.py': b'nested',
        'subdir/deep/data.txt': b'deep',
    })
    h1 = AppService._compute_dir_hash(str(plugin))
    h2 = AppService._compute_dir_hash(str(plugin))
    assert h1 is not None
    assert h1 == h2


def test_hash_changes_when_file_added(tmp_path):
    """Adding a new file to the directory produces a different hash."""
    plugin = tmp_path / 'plugin'
    _make_tree(plugin, {'hook.py': b'content'})
    h1 = AppService._compute_dir_hash(str(plugin))

    _make_tree(plugin, {'extra.py': b'new file'})
    h2 = AppService._compute_dir_hash(str(plugin))
    assert h1 != h2


def test_hash_consistent_across_different_absolute_paths(tmp_path):
    """Same file tree at different absolute paths must produce the same hash."""
    files = {'hook.py': b'print("hello")', 'data/file.txt': b'data'}
    dir_a = tmp_path / 'location_a' / 'plugin'
    dir_b = tmp_path / 'location_b' / 'plugin'
    _make_tree(dir_a, files)
    _make_tree(dir_b, files)
    h_a = AppService._compute_dir_hash(str(dir_a))
    h_b = AppService._compute_dir_hash(str(dir_b))
    assert h_a is not None
    assert h_a == h_b
