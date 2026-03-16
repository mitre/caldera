"""
E2E tests for the Caldera home/dashboard page (HomeView.vue).

All tests use the `auth_page` fixture, which supplies a Playwright `page`
pre-loaded with authenticated session cookies so the Vue router allows
access to the protected home route.

The `api_session` fixture is used in one test to independently verify that
the backend config endpoint (consumed by HomeView on mount) behaves correctly.

Run with:
    pytest plugins/magma/tests/e2e/test_home.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page
import requests


# ---------------------------------------------------------------------------
# 1. Home page loads for an authenticated user
# ---------------------------------------------------------------------------

def test_home_page_loads(auth_page: Page, caldera_server: str) -> None:
    """
    Navigating an authenticated session to / must NOT redirect to /login.
    All four status .box elements defined in HomeView.vue must be present
    and visible on the page.
    """
    auth_page.goto(caldera_server + '/')
    auth_page.wait_for_load_state('networkidle')

    # Must not have been kicked back to the login page
    assert '/login' not in auth_page.url, (
        f"Authenticated user was unexpectedly redirected to login; URL: {auth_page.url}"
    )

    # All four dashboard boxes must be rendered
    boxes = auth_page.locator('.box')
    assert boxes.count() >= 4, (
        f"Expected at least 4 .box elements on the home page, found {boxes.count()}"
    )
    # Verify each of the first four is individually visible
    for i in range(4):
        expect(boxes.nth(i)).to_be_visible()


# ---------------------------------------------------------------------------
# 2. "Manage Agents" link is present and points to /agents
# ---------------------------------------------------------------------------

def test_home_has_manage_agents_link(auth_page: Page, caldera_server: str) -> None:
    """
    The home page must contain a visible link or button with the text
    'Manage Agents' that resolves to the /agents route.
    """
    auth_page.goto(caldera_server + '/')
    auth_page.wait_for_load_state('networkidle')

    # Locate the router-link rendered as an <a> tag containing the text
    manage_agents = auth_page.locator('a', has_text='Manage Agents')
    expect(manage_agents).to_be_visible()

    # The href attribute should reference the /agents path
    href = manage_agents.get_attribute('href')
    assert href is not None and href.endswith('/agents'), (
        f"'Manage Agents' link href expected to end with '/agents', got: '{href}'"
    )


# ---------------------------------------------------------------------------
# 3. "Manage Operations" link is present and points to /operations
# ---------------------------------------------------------------------------

def test_home_has_manage_operations_link(auth_page: Page, caldera_server: str) -> None:
    """
    The home page must contain a visible link or button with the text
    'Manage Operations' that resolves to the /operations route.
    """
    auth_page.goto(caldera_server + '/')
    auth_page.wait_for_load_state('networkidle')

    manage_ops = auth_page.locator('a', has_text='Manage Operations')
    expect(manage_ops).to_be_visible()

    href = manage_ops.get_attribute('href')
    assert href is not None and href.endswith('/operations'), (
        f"'Manage Operations' link href expected to end with '/operations', got: '{href}'"
    )


# ---------------------------------------------------------------------------
# 4. Backend config endpoint returns a valid response (API sanity check)
# ---------------------------------------------------------------------------

def test_home_api_config_matches_display(
    api_session: requests.Session, caldera_server: str
) -> None:
    """
    GET /api/v2/config/main — the same endpoint HomeView.vue fetches on
    mount — must respond with HTTP 200 and a non-empty JSON object.

    This validates that the data underpinning the home page dashboard is
    accessible, without coupling the test to specific config key names.
    """
    response = api_session.get(f'{caldera_server}/api/v2/config/main')

    assert response.status_code == 200, (
        f"Expected HTTP 200 from /api/v2/config/main, got {response.status_code}"
    )

    config = response.json()
    assert isinstance(config, dict), (
        f"Expected a JSON object from /api/v2/config/main, got: {type(config)}"
    )
    assert len(config) > 0, (
        "Config response was an empty dict — expected at least one key"
    )


# ---------------------------------------------------------------------------
# 5. Clicking "Manage Agents" navigates to /agents
# ---------------------------------------------------------------------------

def test_navigation_to_agents_from_home(auth_page: Page, caldera_server: str) -> None:
    """
    Clicking the 'Manage Agents' link from the home page should perform
    a client-side Vue router navigation that changes the URL to end with
    /agents.
    """
    auth_page.goto(caldera_server + '/')
    auth_page.wait_for_load_state('networkidle')

    # Click the link and wait for the SPA route change to settle
    auth_page.locator('a', has_text='Manage Agents').click()
    auth_page.wait_for_load_state('networkidle')

    assert auth_page.url.endswith('/agents'), (
        f"Expected URL to end with '/agents' after clicking 'Manage Agents', "
        f"but current URL is: {auth_page.url}"
    )
