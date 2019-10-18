from unittest import TestCase

import asyncio


class TestBaseServiceCase(TestCase):
    @staticmethod
    def run_async(function):
        return asyncio.get_event_loop().run_until_complete(function)

