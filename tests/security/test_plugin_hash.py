import hashlib
import os
import tempfile
import unittest


def _compute_dir_hash(directory):
    """Compute a SHA-256 hash over all files in a directory."""
    sha256 = hashlib.sha256()
    try:
        for root, dirs, files in os.walk(directory):
            dirs.sort()
            for fname in sorted(files):
                filepath = os.path.join(root, fname)
                try:
                    with open(filepath, 'rb') as f:
                        while True:
                            chunk = f.read(8192)
                            if not chunk:
                                break
                            sha256.update(chunk)
                    sha256.update(filepath.encode('utf-8'))
                except (OSError, IOError):
                    continue
    except (OSError, IOError):
        return None
    return sha256.hexdigest()


class TestPluginHash(unittest.TestCase):
    def test_hash_computation_on_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'test.py'), 'w') as f:
                f.write('print("hello")')
            h1 = _compute_dir_hash(tmpdir)
            self.assertIsNotNone(h1)
            self.assertEqual(len(h1), 64)

    def test_hash_changes_when_file_modified(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, 'test.py')
            with open(filepath, 'w') as f:
                f.write('print("hello")')
            h1 = _compute_dir_hash(tmpdir)

            with open(filepath, 'w') as f:
                f.write('print("world")')
            h2 = _compute_dir_hash(tmpdir)
            self.assertNotEqual(h1, h2)

    def test_hash_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, 'test.py'), 'w') as f:
                f.write('print("hello")')
            h1 = _compute_dir_hash(tmpdir)
            h2 = _compute_dir_hash(tmpdir)
            self.assertEqual(h1, h2)


if __name__ == '__main__':
    unittest.main()
