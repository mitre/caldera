"""
Playwright E2E tests for the Caldera Objectives UI view (/objectives).

These tests verify the page structure, dropdown selector, detail panel,
API/UI consistency, and the create-objective flow for the ObjectivesView
component.  Any objectives created during tests are deleted via the API in
cleanup to keep the instance state clean.

Fixtures used (provided by conftest.py):
    caldera_server  (session) — base URL string
    api_session     (session) — authenticated requests.Session
    auth_page       (function) — Playwright page with auth cookies, not yet navigated
    base_url        (function) — base URL string

Run with:
    pytest plugins/magma/tests/e2e/test_objectives.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def navigate_to_objectives(page: Page, base_url: str) -> None:
    """Navigate to the /objectives route and wait for network activity to settle."""
    page.goto(f"{base_url}/objectives")
    page.wait_for_load_state("networkidle")


def get_objectives_from_api(api_session, caldera_server: str) -> list:
    """Return the list of objective objects from the REST API."""
    resp = api_session.get(f"{caldera_server}/api/v2/objectives")
    assert resp.status_code == 200, (
        f"GET /api/v2/objectives returned HTTP {resp.status_code}"
    )
    return resp.json()


def delete_objective_via_api(api_session, caldera_server: str, objective_id: str) -> None:
    """Delete a single objective by id via the REST API (best-effort cleanup)."""
    api_session.delete(f"{caldera_server}/api/v2/objectives/{objective_id}")


# ---------------------------------------------------------------------------
# 1. h2 heading "Objectives" is visible
# ---------------------------------------------------------------------------

def test_objectives_page_heading(auth_page: Page, base_url: str) -> None:
    """
    Navigating to /objectives must render an <h2> element whose text is
    "Objectives", confirming the correct view has been routed to.
    """
    navigate_to_objectives(auth_page, base_url)

    heading = auth_page.locator("h2", has_text="Objectives")
    expect(heading).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Introductory description paragraph is visible
# ---------------------------------------------------------------------------

def test_objectives_description_visible(auth_page: Page, base_url: str) -> None:
    """
    A descriptive paragraph explaining what an objective is must be visible
    below the heading.  The paragraph contains the phrase "objective is a goal"
    as rendered by the static template copy in ObjectivesView.
    """
    navigate_to_objectives(auth_page, base_url)

    # The static template paragraph starts with "An objective is a goal"
    description = auth_page.locator("p", has_text="objective")
    expect(description).to_be_visible()


# ---------------------------------------------------------------------------
# 3. "New Objective" button is visible
# ---------------------------------------------------------------------------

def test_new_objective_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The primary call-to-action button labelled "New Objective" must be present
    and visible in the left toolbar column alongside the selector dropdown.
    """
    navigate_to_objectives(auth_page, base_url)

    new_btn = auth_page.locator("button", has_text="New Objective")
    expect(new_btn).to_be_visible()


# ---------------------------------------------------------------------------
# 4. UI objective count matches API response count
# ---------------------------------------------------------------------------

def test_objectives_api_count_matches_ui(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    The number of objective entries available for selection in the dropdown
    or list must equal the count returned by GET /api/v2/objectives.

    The dropdown renders one <option> per objective (excluding any blank
    placeholder option).  When zero objectives exist the selector should be
    empty; when objectives exist their count must match.
    """
    objectives = get_objectives_from_api(api_session, caldera_server)
    api_count = len(objectives)

    navigate_to_objectives(auth_page, base_url)

    # The objective selector is a <select> or a Bulma dropdown; try <select>
    # first as it gives the cleanest option-count assertion.
    select_el = auth_page.locator(".column.is-3 select")
    if select_el.count() > 0:
        # Count <option> elements, ignoring any blank/placeholder option.
        all_options = select_el.locator("option")
        # Filter out options with empty value (placeholder)
        non_blank_options = select_el.locator("option[value]:not([value=''])")
        ui_count = non_blank_options.count()
    else:
        # Fallback: Bulma dropdown items rendered as <a> or <button> in the menu
        dropdown_items = auth_page.locator(
            ".column.is-3 .dropdown-item, .column.is-3 .dropdown-content a"
        )
        ui_count = dropdown_items.count()

    assert ui_count == api_count, (
        f"UI shows {ui_count} objective option(s) but API returned {api_count}"
    )


# ---------------------------------------------------------------------------
# 5. First objective's name appears in the selector / dropdown
# ---------------------------------------------------------------------------

def test_objective_names_in_selector(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    When at least one objective exists, the name of the first objective
    returned by GET /api/v2/objectives must appear as a selectable option
    inside the left-column dropdown/selector, confirming that the Vue
    component populates the selector from API data.

    Skipped when no objectives are present.
    """
    objectives = get_objectives_from_api(api_session, caldera_server)

    if not objectives:
        pytest.skip("No objectives present — cannot verify selector contents.")

    first_name = objectives[0].get("name", "")
    if not first_name:
        pytest.skip("First objective has no name field — skipping.")

    navigate_to_objectives(auth_page, base_url)

    # The name should appear somewhere inside the left selector column.
    selector_column = auth_page.locator(".column.is-3")
    name_in_selector = selector_column.locator(f"text={first_name}")
    expect(name_in_selector.first).to_be_visible()


# ---------------------------------------------------------------------------
# 6. Clicking "New Objective" creates a new entry; clean up via API
# ---------------------------------------------------------------------------

def test_new_objective_creates_entry(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    Clicking the "New Objective" button should trigger a POST to
    /api/v2/objectives and render the new entry in the selector.

    The test records the objective count before and after clicking, asserts
    an increase of exactly one, then deletes the newly created objective via
    the API to restore the original state.
    """
    # Record the count of objectives before the action.
    objectives_before = get_objectives_from_api(api_session, caldera_server)
    count_before = len(objectives_before)
    before_ids = {obj["id"] for obj in objectives_before}

    navigate_to_objectives(auth_page, base_url)

    new_btn = auth_page.locator("button", has_text="New Objective")
    expect(new_btn).to_be_visible()
    new_btn.click()

    # Wait for the network request triggered by the button click to complete.
    auth_page.wait_for_load_state("networkidle")

    # Verify the API now returns one more objective.
    objectives_after = get_objectives_from_api(api_session, caldera_server)
    count_after = len(objectives_after)

    assert count_after == count_before + 1, (
        f"Expected {count_before + 1} objectives after creation but found {count_after}"
    )

    # Identify the newly created objective by finding the id that wasn't there before.
    after_ids = {obj["id"] for obj in objectives_after}
    new_ids = after_ids - before_ids

    # Clean up: delete every objective that was created during this test.
    for new_id in new_ids:
        delete_objective_via_api(api_session, caldera_server, new_id)

    # Confirm restoration.
    objectives_final = get_objectives_from_api(api_session, caldera_server)
    assert len(objectives_final) == count_before, (
        f"Cleanup failed: expected {count_before} objectives but found {len(objectives_final)}"
    )


# ---------------------------------------------------------------------------
# 7. Selecting an objective shows its detail panel
# ---------------------------------------------------------------------------

def test_selecting_objective_shows_details(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    When at least one objective exists, clicking (selecting) the first
    objective in the dropdown should populate the right-hand detail panel
    with the objective's name, description, and goals table/section.

    The detail panel is rendered in the right column (.column.is-9) and
    becomes populated once the Vue reactive selection propagates.

    Skipped when no objectives are present.
    """
    objectives = get_objectives_from_api(api_session, caldera_server)

    if not objectives:
        pytest.skip("No objectives present — cannot verify detail panel.")

    first_objective = objectives[0]
    first_name = first_objective.get("name", "")

    navigate_to_objectives(auth_page, base_url)

    # Locate the selector in the left column and pick the first objective.
    selector_column = auth_page.locator(".column.is-3")

    # Try <select> element first; fall back to Bulma dropdown trigger + item.
    select_el = selector_column.locator("select")
    if select_el.count() > 0:
        # Select the option whose text matches the first objective's name.
        if first_name:
            select_el.select_option(label=first_name)
        else:
            # If name is blank, select by index (skip placeholder at 0).
            select_el.select_option(index=1)
    else:
        # Bulma dropdown: click the trigger to open, then click the first item.
        dropdown_trigger = selector_column.locator(".dropdown-trigger button").first
        dropdown_trigger.click()
        first_item = selector_column.locator(".dropdown-item").first
        expect(first_item).to_be_visible()
        first_item.click()

    # Wait for the Vue reactive update to propagate.
    auth_page.wait_for_load_state("networkidle")

    # The right-hand detail column should now display content.
    detail_column = auth_page.locator(".column.is-9")

    # Assert the Save button is visible — it is rendered only when an objective
    # is selected (controlled by Vue's v-if on the selected objective).
    save_btn = detail_column.locator("button", has_text="Save")
    expect(save_btn).to_be_visible()

    # If the objective has a name, it must be visible in the detail panel.
    if first_name:
        name_in_detail = detail_column.locator(f"text={first_name}")
        expect(name_in_detail.first).to_be_visible()

    # The goals section (table or list) must also be present in the detail panel.
    # Accept a <table>, a <thead>, or an element labelled "goals".
    goals_section = detail_column.locator(
        "table, thead, [class*='goal'], th, td, text=goals"
    )
    expect(goals_section.first).to_be_visible()
