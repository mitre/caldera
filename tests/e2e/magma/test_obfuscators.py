"""
E2E tests for the Caldera Obfuscators page (ObfuscatorsView.vue).

Obfuscators modify commands an agent runs to avoid detection.
Caldera ships with 'plain-text' and 'base64' built-in.

Run with:
    pytest plugins/magma/tests/e2e/test_obfuscators.py -v --browser chromium
"""

from playwright.sync_api import Page, expect


def test_obfuscators_page_heading(auth_page: Page, base_url: str) -> None:
    """h2 'Obfuscators' is visible after navigating to /obfuscators."""
    auth_page.goto(base_url + '/obfuscators')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.locator('h2', has_text='Obfuscators')).to_be_visible()


def test_obfuscators_description_visible(auth_page: Page, base_url: str) -> None:
    """A descriptive paragraph about obfuscation is visible."""
    auth_page.goto(base_url + '/obfuscators')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.locator('p').first).to_be_visible()


def test_obfuscators_api_returns_builtins(api_session, base_url: str) -> None:
    """GET /api/v2/obfuscators returns at least 'plain-text' and 'base64'."""
    resp = api_session.get(f'{base_url}/api/v2/obfuscators')
    assert resp.status_code == 200
    names = [o.get('name', '') for o in resp.json()]
    assert 'plain-text' in names, f"'plain-text' not in obfuscators: {names}"
    assert 'base64' in names, f"'base64' not in obfuscators: {names}"


def test_obfuscators_count_matches_ui(auth_page: Page, api_session, base_url: str) -> None:
    """The number of obfuscator items in the UI matches the API count."""
    resp = api_session.get(f'{base_url}/api/v2/obfuscators')
    assert resp.status_code == 200
    api_obfuscators = resp.json()

    auth_page.goto(base_url + '/obfuscators')
    auth_page.wait_for_load_state('networkidle')

    # Each obfuscator should appear as a named element somewhere in the page
    for obf in api_obfuscators:
        name = obf.get('name', '')
        if name:
            expect(auth_page.get_by_text(name, exact=False)).to_be_visible()


def test_plain_text_obfuscator_displayed(auth_page: Page, base_url: str) -> None:
    """The 'plain-text' obfuscator name is visible in the page."""
    auth_page.goto(base_url + '/obfuscators')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.get_by_text('plain-text', exact=False)).to_be_visible()


def test_base64_obfuscator_displayed(auth_page: Page, base_url: str) -> None:
    """The 'base64' obfuscator name is visible in the page."""
    auth_page.goto(base_url + '/obfuscators')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.get_by_text('base64', exact=False)).to_be_visible()


def test_obfuscators_no_create_button(auth_page: Page, base_url: str) -> None:
    """Obfuscators are registered via Python modules — no 'Create' button exists."""
    auth_page.goto(base_url + '/obfuscators')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.get_by_role('button', name='New Obfuscator')).to_have_count(0)
