import asyncio
import unittest


class TestBase(unittest.TestCase):

    @staticmethod
    def run_async(c):
        return asyncio.get_event_loop().run_until_complete(c)

