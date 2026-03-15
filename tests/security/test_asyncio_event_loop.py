import unittest


class TestAsyncioEventLoop(unittest.TestCase):
    def test_no_bare_get_event_loop_in_server(self):
        """Verify no bare asyncio.get_event_loop() calls remain in server.py."""
        with open('server.py', 'r') as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if 'asyncio.get_event_loop()' in stripped and not stripped.startswith('#'):
                self.fail(f'Found bare asyncio.get_event_loop() at line {i}: {stripped}')

    def test_new_event_loop_in_run_tasks(self):
        """Verify run_tasks uses asyncio.new_event_loop()."""
        with open('server.py', 'r') as f:
            content = f.read()
        start = content.find('def run_tasks')
        end = content.find('\ndef ', start + 1)
        func_content = content[start:end]
        self.assertIn('asyncio.new_event_loop()', func_content)
        self.assertIn('asyncio.set_event_loop(loop)', func_content)


if __name__ == '__main__':
    unittest.main()
