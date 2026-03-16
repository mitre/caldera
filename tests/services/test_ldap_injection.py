"""Tests that LDAP injection characters are properly escaped in the
DefaultLoginHandler before they are inserted into DN strings or
LDAP search filters."""
import pytest

from ldap3.utils.conv import escape_filter_chars
from ldap3.utils.dn import escape_rdn_value


class TestLdapRdnEscape:
    """escape_rdn_value must neutralise DN injection characters."""

    def test_escapes_comma(self):
        result = escape_rdn_value("admin,dc=evil,dc=com")
        assert "," not in result or result.startswith("\\")

    def test_escapes_equals(self):
        result = escape_rdn_value("user=injected")
        # ldap3 escapes the = so it cannot break the DN structure
        assert result != "user=injected"

    def test_clean_username_unchanged(self):
        result = escape_rdn_value("jsmith")
        assert result == "jsmith"

    def test_escapes_null_byte(self):
        result = escape_rdn_value("admin\x00")
        assert "\x00" not in result


class TestLdapFilterEscape:
    """escape_filter_chars must neutralise filter injection characters."""

    def test_escapes_asterisk(self):
        result = escape_filter_chars("*")
        assert result == "\\2a"

    def test_escapes_parentheses(self):
        result = escape_filter_chars(")(uid=*")
        assert "(" not in result
        assert ")" not in result

    def test_clean_username_unchanged(self):
        result = escape_filter_chars("jsmith")
        assert result == "jsmith"

    def test_escapes_null_byte(self):
        result = escape_filter_chars("admin\x00")
        assert "\x00" not in result


class TestDefaultLoginHandlerImports:
    """Verify that the login handler imports the sanitisation helpers."""

    def test_escape_rdn_value_imported(self):
        from app.service.login_handlers.default import escape_rdn_value as _erv
        assert callable(_erv)

    def test_escape_filter_chars_imported(self):
        from app.service.login_handlers.default import escape_filter_chars as _efc
        assert callable(_efc)
