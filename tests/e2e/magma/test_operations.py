"""
Playwright E2E tests for the Caldera Operations UI view (/operations).

These tests verify the structure, visibility, and basic interactivity of
the Operations page in the Magma frontend (Vue 3 SPA). All tests are
independent and leave no permanent state — the operations list is observed
but never mutated.

Fixtures used (provided by conftest.py):
    caldera_server  (session) — base URL string
    api_session     (session) — authenticated requests.Session
    auth_page       (function) — Playwright page with auth cookies, not yet navigated
    base_url        (function) — base URL string
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def navigate_to_operations(page: Page, base_url: str) -> None:
    """Navigate to the /operations route and wait for network activity to settle."""
    page.goto(f"{base_url}/operations")
    page.wait_for_load_state("networkidle")


def get_operations_from_api(api_session, caldera_server: str) -> list:
    """Return the list of operation objects from the REST API."""
    resp = api_session.get(f"{caldera_server}/api/v2/operations")
    assert resp.status_code == 200, (
        f"GET /api/v2/operations returned HTTP {resp.status_code}"
    )
    return resp.json()


def open_operation_dropdown(page: Page) -> None:
    """
    Click (or hover) the operation selector dropdown button to expand it.

    The selector button in OperationsView is a Bulma dropdown; a click on the
    trigger button exposes the dropdown-menu containing the operation list.
    """
    # The primary selector button shows "Select an operation" when nothing is chosen
    selector_btn = page.locator(
        ".columns .column .is-flex .dropdown button.button.is-primary",
        has_text="operation",
    ).first
    expect(selector_btn).to_be_visible()
    selector_btn.hover()
    # Wait for the dropdown menu to appear
    page.wait_for_selector(".columns .column .is-flex .dropdown .dropdown-menu", state="visible", timeout=5000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_operations_page_heading(auth_page: Page, base_url: str) -> None:
    """
    The <h2> on the Operations page must contain the text "Operations".
    This confirms the correct view is rendered by the Vue router.
    """
    navigate_to_operations(auth_page, base_url)

    heading = auth_page.locator("h2")
    expect(heading).to_be_visible()
    expect(heading).to_contain_text("Operations")


def test_new_operation_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The "New Operation" primary button must be present and visible in the
    toolbar area next to the operation selector.
    """
    navigate_to_operations(auth_page, base_url)

    new_op_btn = auth_page.get_by_role("button", name="New Operation")
    expect(new_op_btn).to_be_visible()


def test_operation_selector_dropdown_visible(auth_page: Page, base_url: str) -> None:
    """
    The operation selector dropdown button must be present and visible,
    initially showing the placeholder text "Select an operation".
    """
    navigate_to_operations(auth_page, base_url)

    # The selector is a primary button that contains the placeholder text
    # when no operation is currently selected.
    selector_btn = auth_page.locator("button.button.is-primary", has_text="Select an operation")
    expect(selector_btn).to_be_visible()


def test_new_operation_modal_opens(auth_page: Page, base_url: str) -> None:
    """
    Clicking "New Operation" should open a modal overlay that contains at
    minimum a text input field for the operation name.

    The Bulma modal becomes active by receiving the `is-active` class.
    """
    navigate_to_operations(auth_page, base_url)

    new_op_btn = auth_page.get_by_role("button", name="New Operation")
    expect(new_op_btn).to_be_visible()
    new_op_btn.click()

    # The Bulma modal gains `is-active` when opened
    modal = auth_page.locator(".modal.is-active")
    try:
        expect(modal).to_be_visible(timeout=5000)
    except Exception:
        # Fallback: accept any visible dialog/overlay containing an input
        modal = auth_page.locator("[class*='modal'], [role='dialog']")
        expect(modal).to_be_visible(timeout=3000)

    # The modal must contain at least one text input (operation name field)
    name_input = modal.locator("input[type='text'], input:not([type])")
    expect(name_input.first).to_be_visible()


def test_operations_api_count_matches_dropdown(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    The number of items shown in the operation selector dropdown must equal
    the count returned by GET /api/v2/operations.

    Steps:
      1. Fetch operations from the API to get the expected count.
      2. Navigate to /operations.
      3. Expand the operation selector dropdown.
      4. Count the rendered dropdown items and assert equality.
    """
    operations = get_operations_from_api(api_session, caldera_server)
    expected_count = len(operations)

    navigate_to_operations(auth_page, base_url)
    open_operation_dropdown(auth_page)

    # Each operation renders as an <a class="dropdown-item"> inside the menu
    dropdown_items = auth_page.locator(
        ".columns .column .is-flex .dropdown .dropdown-menu .dropdown-content a.dropdown-item"
    )
    actual_count = dropdown_items.count()

    assert actual_count == expected_count, (
        f"Dropdown shows {actual_count} operation(s) but API returned {expected_count}"
    )


def test_operation_names_in_dropdown(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    When at least one operation exists, the first operation's name returned by
    GET /api/v2/operations must appear as a visible item in the dropdown.

    If no operations exist the test is skipped.
    """
    operations = get_operations_from_api(api_session, caldera_server)
    if not operations:
        pytest.skip("No operations registered — cannot verify dropdown names.")

    first_name = operations[0]["name"]

    navigate_to_operations(auth_page, base_url)
    open_operation_dropdown(auth_page)

    # The operation's name should appear as a visible dropdown item
    item = auth_page.locator(
        ".columns .column .is-flex .dropdown .dropdown-menu .dropdown-content a.dropdown-item",
        has_text=first_name,
    )
    expect(item).to_be_visible()


def test_delete_button_hidden_when_no_operation_selected(
    auth_page: Page, base_url: str
) -> None:
    """
    When no operation is selected, the "Delete" button must not be visible.

    In the template the Delete button uses `v-if="selectedOperation.id"` so it
    should be absent from the DOM (or hidden) when the selection is empty.
    """
    navigate_to_operations(auth_page, base_url)

    # The Delete button must not be visible when nothing is selected.
    # Using to_not_be_visible covers both the v-if removal from DOM and a
    # CSS display:none scenario.
    delete_btn = auth_page.get_by_role("button", name="Delete")
    expect(delete_btn).not_to_be_visible()


def test_download_report_hidden_when_no_operation_selected(
    auth_page: Page, base_url: str
) -> None:
    """
    When no operation is selected, the "Download Report" button must not be
    visible.

    In the template the button uses `v-if="selectedOperation.id"` so it
    should be absent from the DOM (or hidden) when the selection is empty.
    """
    navigate_to_operations(auth_page, base_url)

    # The Download Report button must not be visible when nothing is selected.
    download_btn = auth_page.get_by_role("button", name="Download Report")
    expect(download_btn).not_to_be_visible()
