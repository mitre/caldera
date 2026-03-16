"""Tests that the DNS covert-channel contact uses a CSPRNG (secrets module)
rather than the insecure random module for IP address generation."""
import secrets
import importlib
import sys
import types


class TestDnsIpGenerationUsesCsprng:
    """_generate_random_ipv4_response and _get_random_ipv6_addr must use secrets."""

    def _get_handler_class(self):
        """Import the Handler class from contact_dns without starting asyncio."""
        import app.contacts.contact_dns as dns_mod
        return dns_mod.Handler

    def test_ipv4_response_length(self):
        handler = self._get_handler_class()
        result = handler._generate_random_ipv4_response(True)
        assert len(result) == 4, "IPv4 response must be exactly 4 bytes"

    def test_ipv4_last_octet_even(self):
        handler = self._get_handler_class()
        for _ in range(20):
            result = handler._generate_random_ipv4_response(True)
            last = result[3]
            assert last % 2 == 0, f"Last octet should be even, got {last}"

    def test_ipv4_last_octet_odd(self):
        handler = self._get_handler_class()
        for _ in range(20):
            result = handler._generate_random_ipv4_response(False)
            last = result[3]
            assert last % 2 == 1, f"Last octet should be odd, got {last}"

    def test_ipv4_non_zero(self):
        handler = self._get_handler_class()
        for _ in range(20):
            result = handler._generate_random_ipv4_response(True)
            assert int.from_bytes(result, byteorder='big') != 0

    def test_ipv6_response_length(self):
        handler = self._get_handler_class()
        result = handler._get_random_ipv6_addr()
        assert len(result) == 16, "IPv6 response must be exactly 16 bytes"

    def test_ipv6_randomness(self):
        """Two successive calls should (with overwhelming probability) differ."""
        handler = self._get_handler_class()
        results = {handler._get_random_ipv6_addr() for _ in range(10)}
        assert len(results) > 1, "IPv6 addresses should be random, not constant"

    def test_contact_dns_does_not_use_random_module_for_ip(self):
        """The random module must not be used for IP generation (secrets replaces it)."""
        import app.contacts.contact_dns as dns_mod
        import inspect
        src = inspect.getsource(dns_mod.Handler._generate_random_ipv4_response)
        assert 'random.randrange' not in src
        assert 'random.getrandbits' not in src
        src6 = inspect.getsource(dns_mod.Handler._get_random_ipv6_addr)
        assert 'random.getrandbits' not in src6


class TestBaseWorldGeneratorsUseCsprng:
    """generate_name, generate_number and jitter in BaseWorld must use secrets."""

    def test_generate_name_uses_secrets(self):
        import inspect
        from app.utility.base_world import BaseWorld
        src = inspect.getsource(BaseWorld.generate_name)
        assert 'secrets' in src, "generate_name should use secrets module"
        assert 'choice' not in src.replace('secrets.choice', ''), \
            "generate_name should not use random.choice"

    def test_generate_number_uses_secrets(self):
        import inspect
        from app.utility.base_world import BaseWorld
        src = inspect.getsource(BaseWorld.generate_number)
        assert 'secrets' in src, "generate_number should use secrets module"

    def test_jitter_uses_secrets(self):
        import inspect
        from app.utility.base_world import BaseWorld
        src = inspect.getsource(BaseWorld.jitter)
        assert 'secrets' in src, "jitter should use secrets module"

    def test_generate_name_returns_lowercase_string(self):
        from app.utility.base_world import BaseWorld
        name = BaseWorld.generate_name(size=16)
        assert len(name) == 16
        assert name.islower()
        assert name.isalpha()

    def test_generate_number_range(self):
        from app.utility.base_world import BaseWorld
        for _ in range(20):
            n = BaseWorld.generate_number(size=6)
            assert 100000 <= n <= 999999

    def test_jitter_within_range(self):
        from app.utility.base_world import BaseWorld
        for _ in range(20):
            j = BaseWorld.jitter('2/10')
            assert 2 <= j <= 10
