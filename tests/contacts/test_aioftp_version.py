"""Test that aioftp meets the minimum required version (>= 0.21.0) to avoid
the vulnerability flagged in aioftp ~= 0.20.0 by the safety DB."""
import importlib.metadata

import pytest


def test_aioftp_version_meets_minimum():
    """aioftp must be >= 0.21.0 to avoid CVE / safety-DB advisory for 0.20.x."""
    version_str = importlib.metadata.version("aioftp")
    parts = tuple(int(p) for p in version_str.split(".")[:3])
    assert parts >= (0, 21, 0), (
        f"aioftp {version_str} is below the minimum required 0.21.0; "
        "upgrade to 0.27.2 or later."
    )


def test_aioftp_server_api_intact():
    """Ensure the server-side API surface used by contact_ftp is available."""
    import aioftp

    for name in ("Server", "User", "Permission", "ConnectionConditions",
                 "PathPermissions", "worker"):
        assert hasattr(aioftp, name), f"aioftp missing expected attribute: {name}"
