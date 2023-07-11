import pytest

from unittest.mock import patch

from app.contacts.contact_gist import Contact
from app.utility.base_world import BaseWorld


@pytest.fixture
def test_tokens_and_expected_results():
    token_old_len39 = '841fa61ea1cc4a2ea616f743bad140bf43bad14'
    token_old_len40 = token_old_len39 + '0'
    token_old_len255 = 'ad1401234567890' + (token_old_len40 * 6)
    token_old_len256 = token_old_len255 + '9'
    token_old_badchar = '841fa61ea1cc4a2ea616f74s2A82(*ad1403ri1x'
    token_new_len39 = 'ghp_a0s9cu2hFJKjcjisIz3t92w80dulk3rfa35'
    token_new_len40 = token_new_len39 + '2'
    token_new_len255 = 'ghp_j' + ('a0s9cu2hfkjcjisiz3t92w8g0dulk3rfas35shkk310e0vkqjw' * 5)
    token_new_len256 = token_new_len255 + '9'
    token_new_badchar = 'ghp_a0s9cu2hfkjcjisiz3t92w8g0dulk3rf'
    token_new_bad_suffix = 'gh0_a0s9cu2hfkjcjisiz3t92w8g0dulk3rf'
    return [
        (token_old_len39, False),
        (token_old_len40, True),
        (token_old_len255, True),
        (token_old_len256, False),
        (token_old_badchar, False),
        (token_new_len39, False),
        (token_new_len40, True),
        (token_new_len255, True),
        (token_new_len256, False),
        (token_new_badchar, False),
        (token_new_bad_suffix, False),
    ]


@pytest.fixture
def test_contact(app_svc):
    return Contact(app_svc.get_services())


class TestContactGist:
    def test_valid_config(self, test_contact, test_tokens_and_expected_results):
        for token_and_expected_result in test_tokens_and_expected_results:
            token = token_and_expected_result[0]
            expected_result = token_and_expected_result[1]
            assert test_contact.valid_config(token) == expected_result

    async def test_retrieve_config(self, app_svc, test_tokens_and_expected_results):
        expected_num_op_loops = 0
        with patch.object(Contact, '_start_operation_loop', return_value=None) as start_op_loop:
            for token_and_expected_result in test_tokens_and_expected_results:
                test_contact = Contact(app_svc.get_services())
                token = token_and_expected_result[0]
                expected_result = token_and_expected_result[1]
                with patch.object(BaseWorld, 'get_config', return_value=token) as get_config:
                    await test_contact.start()
                    assert get_config.call_count == 1
                    if expected_result:
                        expected_num_op_loops += 1
                        assert test_contact.retrieve_config() == token
                    else:
                        assert not test_contact.retrieve_config()
                    assert start_op_loop.call_count == expected_num_op_loops
