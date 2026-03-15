import unittest


class TestSubprocessExec(unittest.TestCase):
    def test_no_create_subprocess_shell_in_start_vue(self):
        """Verify create_subprocess_shell is not used in start_vue_dev_server."""
        with open('server.py', 'r') as f:
            content = f.read()
        # Find the start_vue_dev_server function
        start = content.find('async def start_vue_dev_server')
        end = content.find('\n\n', start)
        func_content = content[start:end]
        self.assertNotIn('create_subprocess_shell', func_content)
        self.assertIn('create_subprocess_exec', func_content)


if __name__ == '__main__':
    unittest.main()
