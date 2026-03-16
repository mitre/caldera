"""
E2E tests for the Caldera Planners UI view (/planners).

Planners are built-in modules that decide which abilities a red team agent
should execute during an operation.  The view is read-only — users cannot
create or delete planners through the UI.

Fixtures used (provided by conftest.py):
    caldera_server  (session) — base URL string
    api_session     (session) — authenticated requests.Session
    auth_page       (function) — Playwright page with auth cookies, not yet navigated
    base_url        (function) — base URL string

Run with:
    pytest plugins/magma/tests/e2e/test_planners.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def navigate_to_planners(page: Page, base_url: str) -> None:
    """Navigate to the /planners route and wait for network activity to settle."""
    page.goto(f"{base_url}/planners")
    page.wait_for_load_state("networkidle")


def get_planners_from_api(api_session, base_url: str) -> list:
    """Return the list of planner objects from the REST API."""
    resp = api_session.get(f"{base_url}/api/v2/planners")
    assert resp.status_code == 200, (
        f"GET /api/v2/planners returned HTTP {resp.status_code}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# 1. h2 heading "Planners" is visible
# ---------------------------------------------------------------------------

def test_planners_page_heading(auth_page: Page, base_url: str) -> None:
    """
    Navigating to /planners must render an <h2> whose text is "Planners".
    This confirms the correct Vue view is mounted by the router.
    """
    navigate_to_planners(auth_page, base_url)

    heading = auth_page.locator("h2", has_text="Planners")
    expect(heading).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Introductory description paragraph is visible
# ---------------------------------------------------------------------------

def test_planners_description_visible(auth_page: Page, base_url: str) -> None:
    """
    Below the heading there must be a descriptive paragraph explaining what
    a planner is.  The text matches the static copy in the Pug template
    (begins with "A planner is a module").
    """
    navigate_to_planners(auth_page, base_url)

    # The Pug template renders "A planner is a module that decides which
    # abilities a red team agent should execute..."
    description = auth_page.locator("p", has_text="A planner is a module")
    expect(description).to_be_visible()


# ---------------------------------------------------------------------------
# 3. GET /api/v2/planners returns a non-empty list
# ---------------------------------------------------------------------------

def test_planners_api_returns_entries(api_session, base_url: str) -> None:
    """
    The planners REST endpoint must return a non-empty JSON array.
    Caldera ships with at least one built-in planner (e.g. "sequential"),
    so an empty response indicates a configuration problem.
    """
    planners = get_planners_from_api(api_session, base_url)
    assert len(planners) > 0, (
        "GET /api/v2/planners returned an empty list — "
        "at least one built-in planner is expected."
    )


# ---------------------------------------------------------------------------
# 4. Planner item count in the UI matches the API count
# ---------------------------------------------------------------------------

def test_planners_count_matches_ui(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    The number of planner cards (or list entries) rendered on the page must
    equal the number of objects returned by GET /api/v2/planners.

    Planners are rendered via a v-for loop; each item is expected to be a
    card (.card) or a list item (<li>) inside the main content area.  We
    try the most specific selector first and fall back gracefully.
    """
    planners = get_planners_from_api(api_session, base_url)
    api_count = len(planners)

    navigate_to_planners(auth_page, base_url)

    if api_count == 0:
        # No planners in the system — nothing should be rendered.
        # This path is unexpected for a standard Caldera install.
        cards = auth_page.locator(".card")
        assert cards.count() == 0, (
            f"API returned 0 planners but {cards.count()} cards are visible"
        )
        return

    # Wait for Vue to finish rendering at least one planner entry.
    # Planners are typically rendered as .card elements in a v-for loop.
    cards = auth_page.locator(".card")
    expect(cards.first).to_be_visible()
    ui_count = cards.count()

    assert ui_count == api_count, (
        f"UI shows {ui_count} planner card(s) but API returned {api_count}"
    )


# ---------------------------------------------------------------------------
# 5. Each planner's name from the API appears on the page
# ---------------------------------------------------------------------------

def test_planner_names_displayed(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    After navigating to /planners, every planner name returned by
    GET /api/v2/planners must appear somewhere on the page, confirming
    the Vue component renders all API data correctly.

    Skipped when the API returns no planners (unexpected for a live server).
    """
    planners = get_planners_from_api(api_session, base_url)

    if not planners:
        pytest.skip("No planners available — cannot verify name rendering.")

    navigate_to_planners(auth_page, base_url)

    for planner in planners:
        name = planner.get("name", "")
        assert name, f"Planner entry is missing a 'name' field: {planner}"

        name_locator = auth_page.locator(f"text={name}")
        expect(name_locator.first).to_be_visible(
            timeout=5000
        ), f"Planner name '{name}' was not found on the /planners page."


# ---------------------------------------------------------------------------
# 6. No "Create" or "New" button is present (planners are read-only)
# ---------------------------------------------------------------------------

def test_planners_are_read_only(auth_page: Page, base_url: str) -> None:
    """
    Planners are built-in modules and cannot be created through the UI.
    Neither a "Create" button nor a "New" button must be present on the page.
    """
    navigate_to_planners(auth_page, base_url)

    # Assert that no button with "Create" or "New" text exists in the DOM.
    # `to_be_hidden()` passes when the element is absent or not visible.
    create_btn = auth_page.locator("button", has_text="Create")
    expect(create_btn).to_be_hidden()

    new_btn = auth_page.locator("button", has_text="New")
    expect(new_btn).to_be_hidden()
