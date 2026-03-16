"""Tests that the DNS covert-channel contact uses a CSPRNG (secrets module)
rather than the insecure random module for IP address generation."""
import secrets
from unittest.mock import patch, MagicMock


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

    def test_ipv4_uses_secrets_token_bytes(self):
        """_generate_random_ipv4_response must call secrets.token_bytes,
        not random.randrange / random.getrandbits."""
        handler = self._get_handler_class()
        sentinel = b'\xfe\xdc\xba\x98'
        # Patch secrets.token_bytes; if the implementation calls it, our sentinel
        # controls the returned bytes (last byte even for is_response=True).
        with patch('secrets.token_bytes', return_value=sentinel) as mock_tb:
            handler._generate_random_ipv4_response(True)
            mock_tb.assert_called()

        # Ensure random.randrange is not used (patching it to raise proves it's
        # not on the hot path).
        with patch('random.randrange', side_effect=AssertionError("random.randrange must not be called")):
            with patch('random.getrandbits', side_effect=AssertionError("random.getrandbits must not be called")):
                handler._generate_random_ipv4_response(True)

    def test_ipv6_uses_secrets_token_bytes(self):
        """_get_random_ipv6_addr must call secrets.token_bytes,
        not random.getrandbits."""
        handler = self._get_handler_class()
        sentinel = b'\x00' * 16
        with patch('secrets.token_bytes', return_value=sentinel) as mock_tb:
            handler._get_random_ipv6_addr()
            mock_tb.assert_called()

        with patch('random.getrandbits', side_effect=AssertionError("random.getrandbits must not be called")):
            handler._get_random_ipv6_addr()


class TestBaseWorldGeneratorsUseCsprng:
    """generate_name, generate_number and jitter in BaseWorld must use secrets."""

    def test_generate_name_uses_secrets(self):
        from app.utility.base_world import BaseWorld
        # Patch random.choice to raise — if generate_name uses it the test fails.
        with patch('random.choice', side_effect=AssertionError("random.choice must not be called")):
            name = BaseWorld.generate_name(size=8)
        assert isinstance(name, str) and len(name) == 8

    def test_generate_number_uses_secrets(self):
        from app.utility.base_world import BaseWorld
        # Patch random.randrange to raise — if generate_number uses it the test fails.
        with patch('random.randrange', side_effect=AssertionError("random.randrange must not be called")):
            n = BaseWorld.generate_number(size=4)
        assert isinstance(n, int)

    def test_jitter_uses_secrets(self):
        from app.utility.base_world import BaseWorld
        with patch('random.randint', side_effect=AssertionError("random.randint must not be called")):
            j = BaseWorld.jitter('2/10')
        assert isinstance(j, (int, float))

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
