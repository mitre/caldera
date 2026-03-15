import pytest
from app.service.file_svc import FileSvc


@pytest.mark.parametrize('name', [
    'test.ps1',
    'my-payload_v2.exe',
    'agent.bin',
    'a' * 255,
])
def test_valid_filenames(name):
    assert FileSvc._validate_filename(name)


@pytest.mark.parametrize('name', [
    '../../../etc/passwd',
    '..\\windows\\system32',
    'test\x00.ps1',
    'test file.ps1',
    'test;rm -rf /.ps1',
    '<script>.js',
    '',
    'a' * 256,
])
def test_invalid_filenames(name):
    assert not FileSvc._validate_filename(name)


def test_path_traversal_not_bypassed_by_split():
    """Validate that traversal sequences in the full field.filename are rejected
    BEFORE os.path.split() strips them — the critical fix for the path traversal bypass.
    os.path.split('../../../etc/passwd') returns ('../../..', 'passwd');
    validating only 'passwd' would incorrectly pass."""
    traversal_filenames = [
        '../../../etc/passwd',
        '../../secret.yml',
        'uploads/../../../etc/shadow',
    ]
    for raw_name in traversal_filenames:
        assert not FileSvc._validate_filename(raw_name), \
            f'Expected {raw_name!r} to be rejected by _validate_filename (traversal bypass risk)'
