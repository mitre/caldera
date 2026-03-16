"""
E2E tests for the Caldera Payloads page (PayloadsView.vue).

Covers page structure (heading, description, file upload control), list/API
count parity, payload name rendering, and an upload-then-verify lifecycle
that cleans up after itself.

All tests use the `auth_page` fixture so auth cookies are present before
navigation.  Tests that upload data delete the created payload via
`api_session` so the suite remains idempotent.

Run with:
    pytest plugins/magma/tests/e2e/test_payloads.py -v --browser chromium
"""

import io

import pytest
from playwright.sync_api import expect, Page


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

_TEST_PAYLOAD_NAME = 'test_e2e_payload.txt'
_TEST_PAYLOAD_CONTENT = b'test'


# ---------------------------------------------------------------------------
# 1. h2 heading "Payloads" is visible
# ---------------------------------------------------------------------------

def test_payloads_page_heading(auth_page: Page, base_url: str) -> None:
    """
    Navigating to /payloads must render an <h2> whose text is "Payloads".
    """
    auth_page.goto(base_url + '/payloads')
    auth_page.wait_for_load_state('networkidle')

    heading = auth_page.locator('h2', has_text='Payloads')
    expect(heading).to_be_visible()


# ---------------------------------------------------------------------------
# 2. Introductory description paragraph is visible
# ---------------------------------------------------------------------------

def test_payloads_description_visible(auth_page: Page, base_url: str) -> None:
    """
    The page must display a descriptive paragraph below the heading that
    explains the purpose of payloads (text mentions "abilities", matching
    the copy in the Pug template: "Payloads are files that can be attached
    to abilities...").
    """
    auth_page.goto(base_url + '/payloads')
    auth_page.wait_for_load_state('networkidle')

    description = auth_page.locator('p', has_text='abilities')
    expect(description).to_be_visible()


# ---------------------------------------------------------------------------
# 3. Payload list item count matches the API count
# ---------------------------------------------------------------------------

def test_payloads_api_count_matches_ui(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    The number of payload rows rendered in the UI must equal the number of
    payload name strings returned by GET /api/v2/payloads.

    When the API returns zero payloads the test passes trivially.
    """
    resp = api_session.get(base_url + '/api/v2/payloads')
    assert resp.status_code == 200, (
        f'GET /api/v2/payloads returned HTTP {resp.status_code}'
    )
    api_payloads = resp.json()
    api_count = len(api_payloads)

    auth_page.goto(base_url + '/payloads')
    auth_page.wait_for_load_state('networkidle')

    # Each payload is rendered as a row in a table or as a list item.
    # We target <tr> elements inside a <tbody> (table layout) as the primary
    # selector, falling back to <li> elements if the view uses a list layout.
    tbody_rows = auth_page.locator('tbody tr')
    list_items = auth_page.locator('ul li, ol li')

    if api_count == 0:
        # Neither selector should produce any visible results
        assert tbody_rows.count() == 0 or list_items.count() == 0, (
            'API returned 0 payloads but row/list elements are visible'
        )
        return

    # Prefer tbody rows; fall back to list items
    if tbody_rows.count() > 0:
        expect(tbody_rows.first).to_be_visible()
        ui_count = tbody_rows.count()
    else:
        expect(list_items.first).to_be_visible()
        ui_count = list_items.count()

    assert ui_count == api_count, (
        f'UI shows {ui_count} payload rows but API returned {api_count} payloads'
    )


# ---------------------------------------------------------------------------
# 4. First payload name from the API appears on the page
# ---------------------------------------------------------------------------

def test_payload_names_displayed(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    After navigating to /payloads, the filename of the first payload returned
    by GET /api/v2/payloads must be visible somewhere on the page, confirming
    that the Vue component has rendered data fetched from the API.

    Skipped when no payloads are present in the system.
    """
    resp = api_session.get(base_url + '/api/v2/payloads')
    assert resp.status_code == 200, (
        f'GET /api/v2/payloads returned HTTP {resp.status_code}'
    )
    payloads = resp.json()

    if not payloads:
        pytest.skip('No payloads available to verify against the UI')

    first_name = payloads[0]

    auth_page.goto(base_url + '/payloads')
    auth_page.wait_for_load_state('networkidle')

    name_locator = auth_page.locator(f'text={first_name}')
    expect(name_locator.first).to_be_visible()


# ---------------------------------------------------------------------------
# 5. File upload input (or upload dropzone / button) is present on the page
# ---------------------------------------------------------------------------

def test_upload_input_present(auth_page: Page, base_url: str) -> None:
    """
    The Payloads page must provide a mechanism for uploading files.  This is
    expected to be either an `<input type="file">` element, a visible button
    labelled "Upload", or a dropzone area — at least one of these must be
    present and attached to the DOM.
    """
    auth_page.goto(base_url + '/payloads')
    auth_page.wait_for_load_state('networkidle')

    # Primary selector: a standard file input
    file_input = auth_page.locator('input[type="file"]')
    upload_button = auth_page.locator('button', has_text='Upload')
    dropzone = auth_page.locator('[class*="dropzone"], [class*="drop-zone"], [class*="upload"]')

    # At least one upload mechanism must be present in the DOM
    has_file_input = file_input.count() > 0
    has_upload_button = upload_button.count() > 0
    has_dropzone = dropzone.count() > 0

    assert has_file_input or has_upload_button or has_dropzone, (
        'No file upload control found on /payloads: '
        'expected input[type="file"], an "Upload" button, or a dropzone element'
    )


# ---------------------------------------------------------------------------
# 6. A payload uploaded via the API appears in the UI; cleaned up afterwards
# ---------------------------------------------------------------------------

def test_payload_upload_via_api_appears_in_ui(
    auth_page: Page, base_url: str, api_session
) -> None:
    """
    A small text payload POSTed directly to POST /api/v2/payloads must appear
    on the /payloads page after navigation, confirming that the Vue component
    renders the full server-side payload list.

    The test payload is deleted via DELETE /api/v2/payloads/{name} after the
    assertion so no state is left behind.
    """
    # --- Ensure no leftover test payload from a previous run ---
    pre_delete = api_session.delete(base_url + f'/api/v2/payloads/{_TEST_PAYLOAD_NAME}')
    # 404 is acceptable here (payload didn't exist); anything else is unexpected
    assert pre_delete.status_code in (200, 204, 404), (
        f'Pre-test cleanup DELETE returned HTTP {pre_delete.status_code}'
    )

    # --- Upload the test payload via the API ---
    upload_resp = api_session.post(
        base_url + '/api/v2/payloads',
        files={
            'file': (
                _TEST_PAYLOAD_NAME,
                io.BytesIO(_TEST_PAYLOAD_CONTENT),
                'text/plain',
            )
        },
    )
    assert upload_resp.status_code in (200, 201), (
        f'POST /api/v2/payloads returned HTTP {upload_resp.status_code}: '
        f'{upload_resp.text}'
    )

    try:
        # --- Navigate to /payloads and verify the uploaded file is listed ---
        auth_page.goto(base_url + '/payloads')
        auth_page.wait_for_load_state('networkidle')

        payload_text = auth_page.locator(f'text={_TEST_PAYLOAD_NAME}')
        expect(payload_text.first).to_be_visible()

    finally:
        # --- Clean up: delete the test payload regardless of assertion outcome ---
        del_resp = api_session.delete(
            base_url + f'/api/v2/payloads/{_TEST_PAYLOAD_NAME}'
        )
        assert del_resp.status_code in (200, 204), (
            f'Cleanup DELETE /api/v2/payloads/{_TEST_PAYLOAD_NAME} returned '
            f'HTTP {del_resp.status_code}'
        )
