"""
Playwright E2E tests for the Caldera Schedules UI view (/schedules).

These tests verify the page structure, visibility of key elements, modal
interaction, and API/UI consistency for the SchedulesView component.

Fixtures used (provided by conftest.py):
    caldera_server  (session) — base URL string
    api_session     (session) — authenticated requests.Session
    auth_page       (function) — Playwright page with auth cookies, not yet navigated
    base_url        (function) — base URL string

Run with:
    pytest plugins/magma/tests/e2e/test_schedules.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def navigate_to_schedules(page: Page, base_url: str) -> None:
    """Navigate to the /schedules route and wait for network activity to settle."""
    page.goto(f"{base_url}/schedules")
    page.wait_for_load_state("networkidle")


def get_schedules_from_api(api_session, caldera_server: str) -> list:
    """Return the list of schedule objects from the REST API."""
    resp = api_session.get(f"{caldera_server}/api/v2/schedules")
    assert resp.status_code == 200, (
        f"GET /api/v2/schedules returned HTTP {resp.status_code}"
    )
    return resp.json()


# ---------------------------------------------------------------------------
# 1. h2 heading "Schedules" is visible
# ---------------------------------------------------------------------------

def test_schedules_page_heading(auth_page: Page, base_url: str) -> None:
    """
    Navigating to /schedules must render an <h2> element whose text is
    "Schedules", confirming the correct view has been routed to.
    """
    navigate_to_schedules(auth_page, base_url)

    heading = auth_page.locator("h2", has_text="Schedules")
    expect(heading).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Introductory description paragraph is visible
# ---------------------------------------------------------------------------

def test_schedules_description_visible(auth_page: Page, base_url: str) -> None:
    """
    A descriptive paragraph explaining that schedules allow automatic operation
    runs must be visible below the heading.  The text is part of the static
    template copy rendered by the SchedulesView component.
    """
    navigate_to_schedules(auth_page, base_url)

    # The paragraph is introduced by the template with "Schedules allow you to
    # automatically run an operation at a given time"
    description = auth_page.locator("p", has_text="automatically")
    expect(description).to_be_visible()


# ---------------------------------------------------------------------------
# 3. "Create a schedule" primary button is visible
# ---------------------------------------------------------------------------

def test_create_schedule_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The primary call-to-action button labelled "Create a schedule" must be
    present and visible in the button toolbar area.
    """
    navigate_to_schedules(auth_page, base_url)

    create_btn = auth_page.locator("button", has_text="Create a schedule")
    expect(create_btn).to_be_visible()


# ---------------------------------------------------------------------------
# 4. Clicking "Create a schedule" opens a modal with form fields
# ---------------------------------------------------------------------------

def test_create_schedule_modal_opens(auth_page: Page, base_url: str) -> None:
    """
    Clicking the "Create a schedule" button must open a modal dialog that
    contains at least one input field, indicating the create-schedule form
    is active and ready to receive user input.
    """
    navigate_to_schedules(auth_page, base_url)

    create_btn = auth_page.locator("button", has_text="Create a schedule")
    expect(create_btn).to_be_visible()
    create_btn.click()

    # A Bulma modal becomes active by gaining the "is-active" class.
    # Wait for the transition before asserting.
    modal = auth_page.locator(".modal.is-active")
    expect(modal).to_be_visible()

    # The modal must contain at least one input or select element (the form).
    form_field = modal.locator("input, select, textarea").first
    expect(form_field).to_be_visible()


# ---------------------------------------------------------------------------
# 5. UI schedule item count matches API response count
# ---------------------------------------------------------------------------

def test_schedules_api_count_matches_ui(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    The number of schedule entries rendered in the schedule list must equal
    the number of schedule objects returned by GET /api/v2/schedules.

    When the API returns zero schedules the test verifies that no list items
    are present; when schedules exist, the DOM row count must match.
    """
    schedules = get_schedules_from_api(api_session, caldera_server)
    api_count = len(schedules)

    navigate_to_schedules(auth_page, base_url)

    if api_count == 0:
        # With no schedules the list should be empty — verify no schedule rows.
        # Schedule entries are expected to be rendered as list items or table
        # rows in a repeating block; accept zero as confirmation of empty state.
        rows = auth_page.locator(".schedule-item, tbody tr, [data-schedule]")
        assert rows.count() == 0, (
            f"API returned 0 schedules but {rows.count()} items are visible in the UI"
        )
        return

    # When schedules exist wait for at least one row to appear.
    # Schedule entries are rendered inside a repeating list; rows may be <tr>
    # elements inside a table or generic container items depending on template.
    # Try table rows first, then fall back to a broader list-item selector.
    rows = auth_page.locator("tbody tr")
    if rows.count() == 0:
        rows = auth_page.locator(".schedule-item, [data-schedule]")

    expect(rows.first).to_be_visible()
    ui_count = rows.count()

    assert ui_count == api_count, (
        f"UI shows {ui_count} schedule row(s) but API returned {api_count}"
    )


# ---------------------------------------------------------------------------
# 6. First schedule's name from the API appears on the page
# ---------------------------------------------------------------------------

def test_schedule_names_displayed(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    When at least one schedule exists, the name of the first schedule returned
    by GET /api/v2/schedules must be visible somewhere on the page, confirming
    that the Vue component has rendered data fetched from the API.

    Skipped when no schedules are present in the system.
    """
    schedules = get_schedules_from_api(api_session, caldera_server)

    if not schedules:
        pytest.skip("No schedules present — cannot verify name display.")

    first_name = schedules[0].get("name", "")
    if not first_name:
        pytest.skip("First schedule has no name field — skipping.")

    navigate_to_schedules(auth_page, base_url)

    name_locator = auth_page.locator(f"text={first_name}")
    expect(name_locator.first).to_be_visible()


# ---------------------------------------------------------------------------
# 7. Schedule cron expression is visible on the page
# ---------------------------------------------------------------------------

def test_schedule_cron_expression_displayed(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    When at least one schedule has a non-empty 'schedule' (cron) field, that
    cron expression string must appear somewhere visible on the /schedules page.

    This confirms the template renders the schedule expression alongside the
    schedule name in the list.

    Skipped when no schedules with a cron expression are present.
    """
    schedules = get_schedules_from_api(api_session, caldera_server)

    # Find the first schedule that has a non-empty schedule/cron field.
    target_cron: str | None = None
    for sched in schedules:
        cron = sched.get("schedule", "")
        if cron:
            target_cron = cron
            break

    if target_cron is None:
        pytest.skip("No schedules with a cron expression found — skipping.")

    navigate_to_schedules(auth_page, base_url)

    cron_locator = auth_page.locator(f"text={target_cron}")
    expect(cron_locator.first).to_be_visible()
