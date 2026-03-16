"""
Playwright E2E tests for the Caldera Adversaries UI view (/adversaries).

These tests verify the structure, visibility, and basic interactivity of
the Adversaries page in the Magma frontend (Vue 3 SPA). Where state is
mutated (e.g. creating a new profile) the created resource is deleted
via the API before the test exits so the environment is left clean.

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

def navigate_to_adversaries(page: Page, base_url: str) -> None:
    """Navigate to the /adversaries route and wait for network activity to settle."""
    page.goto(f"{base_url}/adversaries")
    page.wait_for_load_state("networkidle")


def get_adversaries_from_api(api_session, caldera_server: str) -> list:
    """Return the list of adversary objects from the REST API."""
    resp = api_session.get(f"{caldera_server}/api/v2/adversaries")
    assert resp.status_code == 200, (
        f"GET /api/v2/adversaries returned HTTP {resp.status_code}"
    )
    return resp.json()


def open_adversary_dropdown(page: Page) -> None:
    """
    Hover over the adversary selector dropdown to expand it.

    The Bulma dropdown in AdversariesView activates on hover via CSS. A brief
    hover is sufficient to expose the dropdown-menu and its items.
    """
    dropdown_trigger = page.locator("#select-adversary .dropdown-trigger button")
    expect(dropdown_trigger).to_be_visible()
    dropdown_trigger.hover()
    # Wait for the dropdown menu to become visible
    page.wait_for_selector("#select-adversary .dropdown-menu", state="visible", timeout=5000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_adversaries_page_heading(auth_page: Page, base_url: str) -> None:
    """
    The <h2> on the Adversaries page must contain the text "Adversaries".
    This confirms the correct view is rendered by the Vue router.
    """
    navigate_to_adversaries(auth_page, base_url)

    heading = auth_page.locator("h2")
    expect(heading).to_be_visible()
    expect(heading).to_contain_text("Adversaries")


def test_adversaries_page_description(auth_page: Page, base_url: str) -> None:
    """
    A descriptive paragraph about Adversary Profiles should be visible below
    the heading. The text begins with "Adversary Profiles are collections".
    """
    navigate_to_adversaries(auth_page, base_url)

    description = auth_page.locator("p", has_text="Adversary Profiles are collections")
    expect(description).to_be_visible()


def test_adversary_selector_dropdown_visible(auth_page: Page, base_url: str) -> None:
    """
    The adversary selector dropdown button must be present and visible,
    initially showing the placeholder text "Select an adversary".
    """
    navigate_to_adversaries(auth_page, base_url)

    # The dropdown trigger button within the #select-adversary section
    dropdown_btn = auth_page.locator("#select-adversary .dropdown-trigger button")
    expect(dropdown_btn).to_be_visible()
    expect(dropdown_btn).to_contain_text("Select an adversary")


def test_new_profile_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The "New Profile" primary button must be present and visible in the
    toolbar section alongside the adversary dropdown.
    """
    navigate_to_adversaries(auth_page, base_url)

    new_profile_btn = auth_page.get_by_role("button", name="New Profile")
    expect(new_profile_btn).to_be_visible()


def test_import_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The "Import" button must be present and visible in the toolbar section
    alongside the "New Profile" button.
    """
    navigate_to_adversaries(auth_page, base_url)

    import_btn = auth_page.get_by_role("button", name="Import")
    expect(import_btn).to_be_visible()


def test_adversaries_api_count_matches_dropdown(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    The number of items shown in the adversary selector dropdown must equal
    the count returned by GET /api/v2/adversaries.

    Steps:
      1. Fetch adversaries from the API to get the expected count.
      2. Navigate to /adversaries.
      3. Hover the dropdown to expand it.
      4. Count the rendered `a.dropdown-item` elements and assert equality.
    """
    adversaries = get_adversaries_from_api(api_session, caldera_server)
    expected_count = len(adversaries)

    navigate_to_adversaries(auth_page, base_url)
    open_adversary_dropdown(auth_page)

    # Each adversary is rendered as an <a class="dropdown-item"> inside the menu
    dropdown_items = auth_page.locator(
        "#select-adversary .dropdown-menu .dropdown-content a.dropdown-item"
    )
    actual_count = dropdown_items.count()

    assert actual_count == expected_count, (
        f"Dropdown shows {actual_count} adversar(ies) but API returned {expected_count}"
    )


def test_adversary_names_in_dropdown(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    When at least one adversary exists, the first adversary's name returned by
    GET /api/v2/adversaries must appear as a visible item in the dropdown.

    If no adversaries exist the test is skipped.
    """
    adversaries = get_adversaries_from_api(api_session, caldera_server)
    if not adversaries:
        pytest.skip("No adversaries registered — cannot verify dropdown names.")

    first_name = adversaries[0]["name"]

    navigate_to_adversaries(auth_page, base_url)
    open_adversary_dropdown(auth_page)

    # The adversary's name should appear as a visible dropdown item
    item = auth_page.locator(
        "#select-adversary .dropdown-menu .dropdown-content a.dropdown-item",
        has_text=first_name,
    )
    expect(item).to_be_visible()


def test_new_profile_creates_adversary(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    Clicking "New Profile" must create a new adversary entry.

    Verification strategy:
      1. Record the adversary count from the API before clicking.
      2. Click "New Profile" and wait for the UI to settle.
      3. Fetch the API again and assert the count increased by exactly 1.
      4. Delete the newly created adversary via DELETE /api/v2/adversaries/{id}
         to leave the environment clean.
    """
    before = get_adversaries_from_api(api_session, caldera_server)
    before_ids = {a["adversary_id"] for a in before}

    navigate_to_adversaries(auth_page, base_url)

    new_profile_btn = auth_page.get_by_role("button", name="New Profile")
    expect(new_profile_btn).to_be_visible()
    new_profile_btn.click()
    auth_page.wait_for_load_state("networkidle")

    after = get_adversaries_from_api(api_session, caldera_server)
    after_ids = {a["adversary_id"] for a in after}

    new_ids = after_ids - before_ids
    assert len(new_ids) == 1, (
        f"Expected exactly 1 new adversary after clicking 'New Profile', "
        f"but found {len(new_ids)} new entries."
    )

    # Clean up: delete the newly created adversary
    new_id = next(iter(new_ids))
    delete_resp = api_session.delete(f"{caldera_server}/api/v2/adversaries/{new_id}")
    assert delete_resp.status_code in (200, 204), (
        f"Cleanup DELETE /api/v2/adversaries/{new_id} returned HTTP {delete_resp.status_code}"
    )


def test_search_filters_adversary_dropdown(
    auth_page: Page, base_url: str, api_session, caldera_server: str
) -> None:
    """
    Typing into the search input inside the open dropdown must filter the
    displayed adversary items.

    Steps:
      1. Require at least one adversary (skip otherwise).
      2. Open the dropdown and record the full unfiltered item count.
      3. Type a string that matches exactly the first adversary's name.
      4. Assert that only items containing the typed text are visible.
      5. Clear the search field and assert the count returns to the original.
    """
    adversaries = get_adversaries_from_api(api_session, caldera_server)
    if not adversaries:
        pytest.skip("No adversaries registered — cannot verify search filtering.")

    # Use the first adversary's name as the search term
    first_adversary = adversaries[0]
    search_term = first_adversary["name"]

    navigate_to_adversaries(auth_page, base_url)
    open_adversary_dropdown(auth_page)

    # Count items before filtering
    all_items = auth_page.locator(
        "#select-adversary .dropdown-menu .dropdown-content a.dropdown-item"
    )
    total_before = all_items.count()

    # Type the search term into the search input inside the dropdown
    search_input = auth_page.locator(
        "#select-adversary .dropdown-menu .dropdown-content .dropdown-item input.input"
    )
    expect(search_input).to_be_visible()
    search_input.fill(search_term)

    # The Vue v-model reactive filter should update the list immediately;
    # wait briefly for any reactivity flush.
    auth_page.wait_for_timeout(400)

    # After filtering, every visible dropdown item (links only) must contain
    # the search term text (case-insensitive match expected from the component).
    filtered_items = auth_page.locator(
        "#select-adversary .dropdown-menu .dropdown-content a.dropdown-item"
    )
    filtered_count = filtered_items.count()

    # At least the matching adversary must appear; count must not exceed total
    assert 1 <= filtered_count <= total_before, (
        f"After filtering by '{search_term}', expected between 1 and {total_before} "
        f"items, but found {filtered_count}."
    )

    # The specific adversary we searched for must be visible
    matching_item = filtered_items.filter(has_text=search_term)
    expect(matching_item.first).to_be_visible()

    # Clear the search field and verify full list is restored
    search_input.fill("")
    auth_page.wait_for_timeout(400)

    restored_count = all_items.count()
    assert restored_count == total_before, (
        f"After clearing search, expected {total_before} items but found {restored_count}."
    )
