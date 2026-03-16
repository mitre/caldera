"""
E2E tests for the Caldera Contacts page (ContactsView.vue).

Contacts are the C2 channels agents use to communicate with the server.
They are configured at startup and are read-only in the UI.

Run with:
    pytest plugins/magma/tests/e2e/test_contacts.py -v --browser chromium
"""

from playwright.sync_api import Page, expect


def test_contacts_page_heading(auth_page: Page, base_url: str) -> None:
    """h2 'Contacts' is visible after navigating to /contacts."""
    auth_page.goto(base_url + '/contacts')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.locator('h2', has_text='Contacts')).to_be_visible()


def test_contacts_description_visible(auth_page: Page, base_url: str) -> None:
    """A descriptive paragraph about C2 channels is visible."""
    auth_page.goto(base_url + '/contacts')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.locator('p').first).to_be_visible()


def test_contacts_api_returns_list(api_session, base_url: str) -> None:
    """GET /api/v2/contacts returns a list (may be empty)."""
    resp = api_session.get(f'{base_url}/api/v2/contacts')
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_contacts_count_matches_ui(auth_page: Page, api_session, base_url: str) -> None:
    """The number of contact items in the UI matches the API response."""
    resp = api_session.get(f'{base_url}/api/v2/contacts')
    assert resp.status_code == 200
    api_contacts = resp.json()

    auth_page.goto(base_url + '/contacts')
    auth_page.wait_for_load_state('networkidle')

    if not api_contacts:
        return  # nothing to assert

    # Contacts rendered as cards or rows
    rows = auth_page.locator('.card, tr, .box').all()
    assert len(rows) >= len(api_contacts)


def test_contact_names_displayed(auth_page: Page, api_session, base_url: str) -> None:
    """Each contact name from the API appears somewhere in the page."""
    resp = api_session.get(f'{base_url}/api/v2/contacts')
    contacts = resp.json()

    if not contacts:
        return

    auth_page.goto(base_url + '/contacts')
    auth_page.wait_for_load_state('networkidle')

    for contact in contacts[:3]:  # spot-check first 3
        name = contact.get('name', '')
        if name:
            expect(auth_page.get_by_text(name, exact=False)).to_be_visible()


def test_contacts_no_create_button(auth_page: Page, base_url: str) -> None:
    """Contacts are configured at startup — no 'New Contact' button should exist."""
    auth_page.goto(base_url + '/contacts')
    auth_page.wait_for_load_state('networkidle')
    expect(auth_page.get_by_role('button', name='New Contact')).to_have_count(0)
