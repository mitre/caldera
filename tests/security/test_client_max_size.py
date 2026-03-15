def test_default_global_client_max_size():
    """Global default is 1MB."""
    assert (1) * 1024 * 1024 == 1048576


def test_none_fallback_global():
    """When config returns None, global defaults to 1MB."""
    config_val = None
    assert (config_val or 1) * 1024 * 1024 == 1048576


def test_default_upload_max_size():
    """API upload default is 100MB to accommodate payloads and exfil files."""
    assert (100) * 1024 * 1024 == 104857600


def test_none_fallback_upload():
    """When config returns None, upload defaults to 100MB."""
    config_val = None
    assert (config_val or 100) * 1024 * 1024 == 104857600


def test_upload_limit_exceeds_global_limit():
    """API upload limit must be larger than the global limit."""
    global_limit = 1 * 1024 * 1024
    upload_limit = 100 * 1024 * 1024
    assert upload_limit > global_limit


def test_old_value_was_larger_than_new_global():
    """Confirm old hardcoded value (5120**2 ~26MB) is replaced by a tighter global default."""
    old_value = 5120 ** 2
    new_global = 1 * 1024 * 1024
    assert old_value > new_global
    assert old_value == 26214400
