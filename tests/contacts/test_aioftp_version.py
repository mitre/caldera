"""Test that aioftp meets the minimum required version (>= 0.21.0) to avoid
the vulnerability flagged in aioftp ~= 0.20.0 by the safety DB."""
import importlib.metadata

from packaging.version import Version


def test_aioftp_version_meets_minimum():
    """aioftp must be >= 0.21.0 to avoid CVE / safety-DB advisory for 0.20.x."""
    version_str = importlib.metadata.version("aioftp")
    assert Version(version_str) >= Version("0.21.0"), (
        f"aioftp {version_str} is below the minimum required 0.21.0; "
        "upgrade to 0.27.2 or later."
    )


def test_aioftp_server_api_intact():
    """Ensure the server-side API surface used by contact_ftp is available."""
    import aioftp

    expected_classes = {
        "Server": type,
        "User": type,
        "Permission": type,
        "ConnectionConditions": type,
        "PathPermissions": type,
    }
    for name, expected_type in expected_classes.items():
        obj = getattr(aioftp, name, None)
        assert obj is not None, f"aioftp missing expected attribute: {name}"
        assert isinstance(obj, expected_type), (
            f"aioftp.{name} should be a class, got {type(obj)!r}"
        )

    # worker may be a function or coroutine function rather than a class
    assert hasattr(aioftp, "worker"), "aioftp missing expected attribute: worker"
    assert callable(aioftp.worker), (
        f"aioftp.worker should be callable, got {type(aioftp.worker)!r}"
    )
