"""
E2E tests for the Caldera Abilities page (AbilitiesView.vue).

These tests cover page structure, filter controls, the ability list, and the
create-ability modal.  All tests use the `auth_page` fixture so auth cookies
are already present before navigation.

Run with:
    pytest plugins/magma/tests/e2e/test_abilities.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# 1. h2 heading "Abilities" is visible
# ---------------------------------------------------------------------------

def test_abilities_page_heading(auth_page: Page, base_url: str) -> None:
    """
    Navigating to /abilities must render an <h2> whose text is "Abilities".
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    heading = auth_page.locator('h2', has_text='Abilities')
    expect(heading).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Introductory ATT&CK description paragraph is visible
# ---------------------------------------------------------------------------

def test_abilities_page_description(auth_page: Page, base_url: str) -> None:
    """
    The page must display a descriptive paragraph that mentions ATT&CK — the
    text matches the static copy rendered just below the <h2>.
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    # The paragraph contains the phrase used in the Vue template
    description = auth_page.locator('p', has_text='ATT&CK')
    expect(description).to_be_visible()


# ---------------------------------------------------------------------------
# 3. "Create an Ability" button is visible
# ---------------------------------------------------------------------------

def test_create_ability_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The primary call-to-action button labelled "Create an Ability" must be
    present and visible in the left sidebar column.
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    create_btn = auth_page.locator('button', has_text='Create an Ability')
    expect(create_btn).to_be_visible()


# ---------------------------------------------------------------------------
# 4. Search input with placeholder "Find an ability..." is visible
# ---------------------------------------------------------------------------

def test_search_input_visible(auth_page: Page, base_url: str) -> None:
    """
    A text input with placeholder "Find an ability..." must be rendered in the
    filter sidebar so users can search the ability list by name.
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    search_input = auth_page.locator('input[placeholder="Find an ability..."]')
    expect(search_input).to_be_visible()


# ---------------------------------------------------------------------------
# 5. Tactic filter dropdown is visible and contains an "All" option
# ---------------------------------------------------------------------------

def test_tactic_filter_dropdown_visible(auth_page: Page, base_url: str) -> None:
    """
    The Tactic filter must be rendered as a <select> element.  It must contain
    at least the catch-all "All" option (value="").
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    # Locate the label "Tactic" and then find the sibling select element
    tactic_label = auth_page.locator('label.label', has_text='Tactic')
    expect(tactic_label).to_be_visible()

    # The select is within the same .field block as the label
    tactic_field = auth_page.locator('.field', has=auth_page.locator('label.label', has_text='Tactic'))
    tactic_select = tactic_field.locator('select')
    expect(tactic_select).to_be_visible()

    # Verify the "All" option is present
    all_option = tactic_select.locator('option', has_text='All')
    expect(all_option).to_be_attached()


# ---------------------------------------------------------------------------
# 6. "Clear Filters" button is visible
# ---------------------------------------------------------------------------

def test_clear_filters_button_visible(auth_page: Page, base_url: str) -> None:
    """
    A "Clear Filters" button must be rendered below the filter form so users
    can reset all active filters at once.
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    clear_btn = auth_page.locator('button', has_text='Clear Filters')
    expect(clear_btn).to_be_visible()


# ---------------------------------------------------------------------------
# 7. Row count in the UI matches the count returned by the API
# ---------------------------------------------------------------------------

def test_abilities_api_count_matches_ui(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    The number of ability rows rendered in the right-hand column must equal the
    number of ability objects returned by GET /api/v2/abilities.

    If the API returns zero abilities the test passes trivially (no rows shown).
    """
    # Fetch abilities directly from the API
    resp = api_session.get(base_url + '/api/v2/abilities')
    assert resp.status_code == 200, (
        f'GET /api/v2/abilities returned HTTP {resp.status_code}'
    )
    abilities = resp.json()
    api_count = len(abilities)

    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    if api_count == 0:
        # No abilities in the system — the list column should be empty
        # We verify by confirming no ability-row elements are present.
        # The right-hand column is .column.is-10; rows are typically <tr> or
        # list items rendered by v-for.  Accept zero matches gracefully.
        rows = auth_page.locator('.column.is-10 tbody tr')
        assert rows.count() == 0, (
            f'API returned 0 abilities but {rows.count()} rows are visible'
        )
        return

    # When abilities exist they are rendered as table rows inside the right column
    rows = auth_page.locator('.column.is-10 tbody tr')
    # Wait for at least one row to appear (Vue renders after the API call resolves)
    expect(rows.first).to_be_visible()
    ui_count = rows.count()

    assert ui_count == api_count, (
        f'UI shows {ui_count} ability rows but API returned {api_count} abilities'
    )


# ---------------------------------------------------------------------------
# 8. Typing in the search box filters the displayed ability list
# ---------------------------------------------------------------------------

def test_search_filters_ability_list(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    Typing an ability's name into the search input must reduce the visible list
    to entries that contain that name.

    Skipped when no abilities are present in the system.
    """
    resp = api_session.get(base_url + '/api/v2/abilities')
    assert resp.status_code == 200
    abilities = resp.json()

    if not abilities:
        pytest.skip('No abilities available to search for')

    # Use the name of the first ability returned by the API
    target_name = abilities[0]['name']

    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    # Type the ability name into the search field
    search_input = auth_page.locator('input[placeholder="Find an ability..."]')
    expect(search_input).to_be_visible()
    search_input.fill(target_name)

    # Wait for the reactive filter to propagate
    auth_page.wait_for_load_state('networkidle')

    # The target ability's name must now appear somewhere in the right-hand column
    ability_column = auth_page.locator('.column.is-10')
    matching_text = ability_column.locator(f'text={target_name}')
    expect(matching_text.first).to_be_visible()


# ---------------------------------------------------------------------------
# 9. Clicking "Create an Ability" opens a modal with form fields
# ---------------------------------------------------------------------------

def test_create_ability_modal_opens(auth_page: Page, base_url: str) -> None:
    """
    Clicking the "Create an Ability" button must open a modal dialog that
    contains at least one input field, indicating the creation form is active.
    """
    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    create_btn = auth_page.locator('button', has_text='Create an Ability')
    expect(create_btn).to_be_visible()
    create_btn.click()

    # A Bulma modal becomes active by gaining the "is-active" class.
    # We wait for it to appear before making assertions.
    modal = auth_page.locator('.modal.is-active')
    expect(modal).to_be_visible()

    # The modal must contain at least one input or textarea (the creation form)
    form_input = modal.locator('input, textarea').first
    expect(form_input).to_be_visible()


# ---------------------------------------------------------------------------
# 10. First ability name from the API appears somewhere on the page
# ---------------------------------------------------------------------------

def test_ability_data_matches_api(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    After navigating to /abilities, the name of the first ability returned by
    GET /api/v2/abilities must be visible somewhere on the page, confirming
    that the Vue component has correctly rendered data fetched from the API.

    Skipped when no abilities are present in the system.
    """
    resp = api_session.get(base_url + '/api/v2/abilities')
    assert resp.status_code == 200, (
        f'GET /api/v2/abilities returned HTTP {resp.status_code}'
    )
    abilities = resp.json()

    if not abilities:
        pytest.skip('No abilities available to verify against the UI')

    first_ability_name = abilities[0]['name']

    auth_page.goto(base_url + '/abilities')
    auth_page.wait_for_load_state('networkidle')

    # The ability name must appear somewhere in the page body
    name_locator = auth_page.locator(f'text={first_ability_name}')
    expect(name_locator.first).to_be_visible()
