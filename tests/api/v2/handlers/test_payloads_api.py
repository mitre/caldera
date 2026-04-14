import os
import pathlib
import tempfile
from http import HTTPStatus

import pytest


@pytest.fixture
def expected_payload_file_paths():
    """
    Generates (and deletes) real dummy files because the payload API looks for payload files in
    "data/payloads" and/or in "plugins/<plugin-name>/payloads".
    :return: A set of relative paths of dummy payloads.
    """
    directory = "data/payloads"
    os.makedirs(directory, exist_ok=True)

    file_paths = set()
    current_working_dir = os.getcwd()

    try:
        for _ in range(3):
            fd, file_path = tempfile.mkstemp(prefix="payload_", dir=directory)
            os.close(fd)
            relative_path = os.path.relpath(file_path, start=current_working_dir)
            file_paths.add(relative_path)
        yield file_paths
    finally:
        for file_path in file_paths:
            os.remove(file_path)


@pytest.fixture
def expected_payload_file_names(expected_payload_file_paths):
    return {os.path.basename(path) for path in expected_payload_file_paths}


class TestPayloadsApi:

    async def test_get_payloads(self, api_v2_client, api_cookies, expected_payload_file_names):
        resp = await api_v2_client.get('/api/v2/payloads', cookies=api_cookies)
        payload_file_names = await resp.json()
        assert len(payload_file_names) >= len(expected_payload_file_names)

        filtered_payload_file_names = {  # Excluding any other real files in data/payloads...
            file_name for file_name in payload_file_names
            if file_name in expected_payload_file_names
        }

        assert filtered_payload_file_names == expected_payload_file_names

    @pytest.mark.parametrize('query_name', ['payload_', 'PAYLOAD_'])
    async def test_get_payloads_name_filter(self, api_v2_client, api_cookies, expected_payload_file_names, query_name):
        resp = await api_v2_client.get(f'/api/v2/payloads?name={query_name}', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        payload_file_names = await resp.json()

        # All expected payloads should be present
        assert expected_payload_file_names <= set(payload_file_names)
        # Every returned payload must match the filter (no false positives)
        assert all('payload_' in pathlib.PurePath(p).name.lower() for p in payload_file_names)

    async def test_get_payloads_name_filter_no_match(self, api_v2_client, api_cookies):
        resp = await api_v2_client.get('/api/v2/payloads?name=__no_match_xyzzy__', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        assert await resp.json() == []

    async def test_get_payloads_name_filter_with_sort_and_add_path(
            self, api_v2_client, api_cookies, expected_payload_file_names):
        resp = await api_v2_client.get('/api/v2/payloads?name=payload_&sort=true&add_path=true', cookies=api_cookies)
        assert resp.status == HTTPStatus.OK
        payload_paths = await resp.json()

        # Results should be sorted
        assert payload_paths == sorted(payload_paths)
        # Every returned path's filename must match the filter
        assert all('payload_' in pathlib.PurePath(p).name.lower() for p in payload_paths)
        # Results should contain paths (not bare filenames)
        assert all(os.sep in p or '/' in p for p in payload_paths)

    async def test_unauthorized_get_payloads(self, api_v2_client):
        resp = await api_v2_client.get('/api/v2/payloads')
        assert resp.status == HTTPStatus.UNAUTHORIZED
