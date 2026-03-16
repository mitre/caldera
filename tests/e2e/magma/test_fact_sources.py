"""
E2E tests for the Caldera Fact Sources page (FactSourcesView.vue).

Covers page structure (heading, description, New Source button), list/API
count parity, source name rendering, create-and-delete lifecycle, and the
conditional visibility of the Delete button and fact/relationship/rule tables.

All tests use the `auth_page` fixture so auth cookies are present before
navigation.  Tests that create data clean up after themselves via
`api_session` so the suite remains idempotent.

Run with:
    pytest plugins/magma/tests/e2e/test_fact_sources.py -v --browser chromium
"""

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# 1. h2 heading "Fact Sources" is visible
# ---------------------------------------------------------------------------

def test_fact_sources_page_heading(auth_page: Page, base_url: str) -> None:
    """
    Navigating to /factsources must render an <h2> whose text is
    "Fact Sources".
    """
    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    heading = auth_page.locator('h2', has_text='Fact Sources')
    expect(heading).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Introductory description paragraph is visible
# ---------------------------------------------------------------------------

def test_fact_sources_description_visible(auth_page: Page, base_url: str) -> None:
    """
    Below the heading there must be a descriptive paragraph that mentions
    the purpose of fact sources (text contains "fact source" or "collection
    of facts", matching the copy in the Pug template).
    """
    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    # The Pug template renders "A fact source is a collection of facts..."
    description = auth_page.locator('p', has_text='fact source')
    expect(description).to_be_visible()


# ---------------------------------------------------------------------------
# 3. "New Source" button is visible
# ---------------------------------------------------------------------------

def test_new_source_button_visible(auth_page: Page, base_url: str) -> None:
    """
    The primary action button labelled "New Source" must be present and
    visible in the left sidebar column regardless of how many sources exist.
    """
    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    new_btn = auth_page.locator('button', has_text='New Source')
    expect(new_btn).to_be_visible()


# ---------------------------------------------------------------------------
# 4. Source list item count matches the API count
# ---------------------------------------------------------------------------

def test_fact_sources_api_count_matches_ui(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    The number of source entries rendered in the sidebar list must equal the
    number of objects returned by GET /api/v2/sources.

    When the API returns zero sources the test passes trivially (empty list).
    """
    resp = api_session.get(base_url + '/api/v2/sources')
    assert resp.status_code == 200, (
        f'GET /api/v2/sources returned HTTP {resp.status_code}'
    )
    api_sources = resp.json()
    api_count = len(api_sources)

    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    # Sources are rendered as clickable list items inside the .is-3 sidebar
    # column.  Each item is a <li> or a block element produced by v-for.
    # We target list items inside the left .column.is-3.
    sidebar = auth_page.locator('.column.is-3')
    source_items = sidebar.locator('li')

    if api_count == 0:
        assert source_items.count() == 0, (
            f'API returned 0 sources but {source_items.count()} list items '
            f'are visible in the sidebar'
        )
        return

    # Wait for Vue to finish rendering the list
    expect(source_items.first).to_be_visible()
    ui_count = source_items.count()

    assert ui_count == api_count, (
        f'UI shows {ui_count} source items but API returned {api_count} sources'
    )


# ---------------------------------------------------------------------------
# 5. First source name from the API appears on the page
# ---------------------------------------------------------------------------

def test_source_names_displayed(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    After navigating to /factsources, the name of the first source returned
    by GET /api/v2/sources must be visible somewhere on the page, confirming
    that the Vue component has rendered data from the API.

    Skipped when no sources are present in the system.
    """
    resp = api_session.get(base_url + '/api/v2/sources')
    assert resp.status_code == 200, (
        f'GET /api/v2/sources returned HTTP {resp.status_code}'
    )
    sources = resp.json()

    if not sources:
        pytest.skip('No fact sources available to verify against the UI')

    first_name = sources[0]['name']

    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    name_locator = auth_page.locator(f'text={first_name}')
    expect(name_locator.first).to_be_visible()


# ---------------------------------------------------------------------------
# 6. Clicking "New Source" creates a new entry in the sidebar list
# ---------------------------------------------------------------------------

def test_new_source_creates_entry(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    Clicking the "New Source" button must cause a new entry to appear in the
    sidebar source list (the count increases by one).

    The newly created source is deleted via the API after the assertion so the
    test is fully self-contained.
    """
    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    # Snapshot the source count before creation
    sidebar = auth_page.locator('.column.is-3')
    source_items = sidebar.locator('li')
    initial_count = source_items.count()

    # Click the "New Source" primary button
    new_btn = auth_page.locator('button', has_text='New Source')
    expect(new_btn).to_be_visible()
    new_btn.click()
    auth_page.wait_for_load_state('networkidle')

    # The list must now contain one more item
    expect(source_items).to_have_count(initial_count + 1)

    # --- Clean up: find the newly created source via the API and delete it ---
    resp = api_session.get(base_url + '/api/v2/sources')
    assert resp.status_code == 200
    sources_after = resp.json()

    # Identify sources that did not exist before (by comparing API count)
    # Fetch the pre-test API state to compare IDs would require an earlier
    # API call; instead we delete the source whose name is the default
    # auto-generated name (typically "New Source" or similar).  If multiple
    # unnamed sources exist, we delete only the most recently created one.
    if len(sources_after) > initial_count:
        # Sort by id descending to get the newest entry first
        newest = sorted(sources_after, key=lambda s: s.get('id', ''), reverse=True)[0]
        del_resp = api_session.delete(base_url + f'/api/v2/sources/{newest["id"]}')
        assert del_resp.status_code in (200, 204), (
            f'Cleanup DELETE /api/v2/sources/{newest["id"]} returned '
            f'HTTP {del_resp.status_code}'
        )


# ---------------------------------------------------------------------------
# 7. Delete button is hidden when no source is selected
# ---------------------------------------------------------------------------

def test_delete_button_hidden_when_no_source_selected(
    auth_page: Page, base_url: str
) -> None:
    """
    The "Delete" danger button uses `v-if="selectedSource.id"` in the
    template, so it must NOT be visible immediately after navigating to
    /factsources (before the user selects any source).
    """
    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    # The Delete button should either be absent from the DOM entirely or
    # hidden via display:none / visibility:hidden.
    delete_btn = auth_page.locator('button.is-danger', has_text='Delete')
    # `to_be_hidden` passes when the element is not in the DOM OR is invisible
    expect(delete_btn).to_be_hidden()


# ---------------------------------------------------------------------------
# 8. Selecting a source reveals the fact/relationship/rule section
# ---------------------------------------------------------------------------

def test_selecting_source_shows_fact_tables(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    Clicking on a source entry in the sidebar must cause the right-hand
    detail column (.column.is-9) to display the fact/relationship/rule
    content for that source.

    Skipped when no sources are present in the system.
    """
    resp = api_session.get(base_url + '/api/v2/sources')
    assert resp.status_code == 200, (
        f'GET /api/v2/sources returned HTTP {resp.status_code}'
    )
    sources = resp.json()

    if not sources:
        pytest.skip('No fact sources available to test selection')

    auth_page.goto(base_url + '/factsources')
    auth_page.wait_for_load_state('networkidle')

    # Click the first source entry in the sidebar list
    sidebar = auth_page.locator('.column.is-3')
    first_item = sidebar.locator('li').first
    expect(first_item).to_be_visible()
    first_item.click()
    auth_page.wait_for_load_state('networkidle')

    # After selection the right-hand .column.is-9 must contain visible content.
    # The template renders tables or sections for facts, relationships, and rules.
    # We assert the detail column is visible and contains at least one table or
    # labelled section heading.
    detail_col = auth_page.locator('.column.is-9')
    expect(detail_col).to_be_visible()

    # Expect at least one <table> or <h4>/<h5> section header to appear inside
    # the detail column, indicating the fact/relationship/rule data has rendered.
    detail_content = detail_col.locator('table, h4, h5')
    expect(detail_content.first).to_be_visible()
