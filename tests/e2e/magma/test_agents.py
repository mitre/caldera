"""
Playwright E2E tests for the Caldera Agents UI view (/agents).

These tests verify the structure, visibility, and basic interactivity of
the Agents page in the Magma frontend (Vue 3 SPA). They are read-only and
idempotent — no agents are created or deleted.

Fixtures used (provided by conftest.py):
    caldera_server  (session) — base URL string
    api_session     (session) — authenticated requests.Session
    auth_page       (function) — Playwright page with auth cookies, not yet navigated
    base_url        (function) — base URL string
"""

import pytest
from playwright.sync_api import expect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def navigate_to_agents(page, base_url: str) -> None:
    """Navigate to the /agents route and wait for network activity to settle."""
    page.goto(f"{base_url}/agents")
    page.wait_for_load_state("networkidle")


def get_agents_from_api(api_session, caldera_server: str) -> list:
    """Return the list of agent objects from the REST API."""
    resp = api_session.get(f"{caldera_server}/api/v2/agents")
    assert resp.status_code == 200, (
        f"GET /api/v2/agents returned HTTP {resp.status_code}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_agents_page_heading(auth_page, base_url):
    """
    The <h2> on the Agents page must contain the text "Agents".
    This confirms the correct view is rendered.
    """
    navigate_to_agents(auth_page, base_url)

    heading = auth_page.locator("h2")
    expect(heading).to_be_visible()
    expect(heading).to_contain_text("Agents")


def test_agents_page_description(auth_page, base_url):
    """
    A descriptive paragraph about deploying agents should be visible below
    the heading. The text begins with "You must deploy at least 1 agent".
    """
    navigate_to_agents(auth_page, base_url)

    # Locate a paragraph that contains the deployment instruction text.
    description = auth_page.locator("p", has_text="You must deploy at least 1 agent")
    expect(description).to_be_visible()


def test_deploy_agent_button_visible(auth_page, base_url):
    """
    The "Deploy an agent" primary button must be present and visible in the
    toolbar area above the agent table.
    """
    navigate_to_agents(auth_page, base_url)

    deploy_btn = auth_page.get_by_role("button", name="Deploy an agent")
    expect(deploy_btn).to_be_visible()


def test_configuration_button_visible(auth_page, base_url):
    """
    The "Configuration" primary button must be present and visible alongside
    the "Deploy an agent" button.
    """
    navigate_to_agents(auth_page, base_url)

    config_btn = auth_page.get_by_role("button", name="Configuration")
    expect(config_btn).to_be_visible()


def test_deploy_modal_opens(auth_page, base_url):
    """
    Clicking "Deploy an agent" should open a modal overlay.
    The modal is expected to become active (`.modal.is-active`) or to contain
    text related to deployment so users can choose an agent type to deploy.
    """
    navigate_to_agents(auth_page, base_url)

    deploy_btn = auth_page.get_by_role("button", name="Deploy an agent")
    deploy_btn.click()

    # The Bulma modal adds the `is-active` class when open.
    # Also accept any visible element with "Deploy" text as a fallback,
    # in case the component uses a different modal implementation.
    modal = auth_page.locator(".modal.is-active")
    try:
        expect(modal).to_be_visible(timeout=5000)
    except Exception:
        # Fallback: look for any overlay/dialog containing "Deploy"
        overlay = auth_page.locator("[class*='modal'], [role='dialog']", has_text="Deploy")
        expect(overlay).to_be_visible(timeout=3000)


def test_config_modal_opens(auth_page, base_url):
    """
    Clicking the "Configuration" button should open a modal overlay
    for agent configuration settings.
    """
    navigate_to_agents(auth_page, base_url)

    config_btn = auth_page.get_by_role("button", name="Configuration")
    config_btn.click()

    # Expect a Bulma `is-active` modal; fall back to any dialog with config text.
    modal = auth_page.locator(".modal.is-active")
    try:
        expect(modal).to_be_visible(timeout=5000)
    except Exception:
        overlay = auth_page.locator(
            "[class*='modal'], [role='dialog']",
            has_text="Configuration"
        )
        expect(overlay).to_be_visible(timeout=3000)


def test_bulk_actions_dropdown_items(auth_page, base_url):
    """
    Hovering over (or clicking) the "Bulk Actions" button should reveal a
    dropdown menu with three items:
      - "Remove dead agents"
      - "Remove all agents"
      - "Kill all agents"
    """
    navigate_to_agents(auth_page, base_url)

    bulk_btn = auth_page.get_by_role("button", name="Bulk Actions")
    expect(bulk_btn).to_be_visible()

    # The Bulma dropdown activates on hover via CSS; trigger by hovering.
    bulk_btn.hover()

    # Each dropdown item should now be visible.
    dropdown_menu = auth_page.locator(".dropdown-menu[role='menu']")
    expect(dropdown_menu).to_be_visible()

    remove_dead = dropdown_menu.get_by_text("Remove dead agents")
    remove_all = dropdown_menu.get_by_text("Remove all agents")
    kill_all = dropdown_menu.get_by_text("Kill all agents")

    expect(remove_dead).to_be_visible()
    expect(remove_all).to_be_visible()
    expect(kill_all).to_be_visible()


def test_agents_api_matches_ui_count(auth_page, base_url, api_session, caldera_server):
    """
    The agent count shown in the badge on the Agents page should match the
    number of agents returned by GET /api/v2/agents.

    The badge renders text like "N agent(s)" — we verify that the numeric
    count shown in the UI equals the length of the API response array.
    """
    agents = get_agents_from_api(api_session, caldera_server)
    expected_count = len(agents)

    navigate_to_agents(auth_page, base_url)

    # The count badge is a <strong> element inside .tag.is-medium that reads
    # "N agent(s)". Match on the strong that contains the count + "agent".
    count_badge = auth_page.locator(".tag.is-medium strong", has_text="agent")
    expect(count_badge).to_be_visible()

    badge_text = count_badge.inner_text()
    # Badge text is e.g. "3 agent(s)" — extract the leading number.
    badge_number = int(badge_text.strip().split()[0])

    assert badge_number == expected_count, (
        f"UI badge shows {badge_number} agent(s) but API returned {expected_count}"
    )


def test_agents_table_headers_when_agents_exist(auth_page, base_url, api_session, caldera_server):
    """
    When at least one agent is registered, the agents table should be visible
    and its header row must include the columns:
      "id (paw)", "host", "group", "platform"

    If no agents are present the test is skipped (use a fresh-instance guard).
    """
    agents = get_agents_from_api(api_session, caldera_server)
    if not agents:
        pytest.skip("No agents registered — cannot verify table headers.")

    navigate_to_agents(auth_page, base_url)

    table = auth_page.locator("table.table")
    expect(table).to_be_visible()

    thead = table.locator("thead")
    expect(thead).to_be_visible()

    for expected_header in ("id (paw)", "host", "group", "platform"):
        header_cell = thead.get_by_text(expected_header, exact=True)
        expect(header_cell).to_be_visible(), (
            f"Expected table header '{expected_header}' to be visible"
        )


def test_agents_table_absent_when_no_agents(auth_page, base_url, api_session, caldera_server):
    """
    When no agents are registered, the Vue v-if directive hides the table
    entirely. Assert that no `table.table` element is present in the DOM.

    If agents do exist the test is skipped, as the table is expected to be
    visible in that case.
    """
    agents = get_agents_from_api(api_session, caldera_server)
    if agents:
        pytest.skip("Agents are registered — table is expected to be visible.")

    navigate_to_agents(auth_page, base_url)

    # The table must not exist in the DOM (v-if removes it entirely).
    table = auth_page.locator("table.table")
    expect(table).to_have_count(0)
