from typing import TypedDict


class QATest(TypedDict):
    test_name: str
    user_prompt: str


QA_PREAMBLE = f"""\
Your job is to do QA testing on the {{url}} website.
Please follow the instructions below and make sure every line which starts with "CHECK" is working as expected.
If it is not then you should abort and send message to the user saying what went wrong. No need to send a message if it is working as expected.
After you finish each section (and each Part, if there are several), send a one-line progress message, e.g. "Progress: finished Rename Section, 4/4 CHECKs passed". Don't wait for a reply.

## Cleanup (always)
Before you send the final result, archive every case you created in this session, even if a CHECK failed or you aborted early:
- Use the External API ({{external_api_specs_url}}) with the bearer token from the {{api_key_secret}} secret: `PATCH /cases/{{{{caseId}}}}/archive` for each case you created. Skip cases the test already archived.
- Only archive cases you created in this session. Never archive other cases.
- If archiving fails, include the error in the final message. It does not change whether the test passed.
- Put the ids of the cases you archived (including ones the test archived) in 'archived_cases'.

## Final result
When you are done, you MUST use Devin's structured output feature (not a file, not a chat message) with:
- 'success': true only if every CHECK passed.
- 'summary': one short sentence, max 150 characters, e.g. "3 of 4 checks passed; archived cases still appear in GET /cases".
- 'checks': one entry per CHECK you ran: 'name' (what was checked, max 60 characters), 'passed' (boolean), 'details' (if it failed: what happened, max 150 characters, no ids or timestamps unless they matter; empty string if it passed), 'part' (empty string unless told otherwise).
- 'archived_cases': the ids of the cases you archived.
Keep it short: the result is shown in Slack.
"""

DEVIN_QA_LOGIN_INSTRUCTIONS = """\
For basic HTTP authentication, use the username:password from the {basic_auth_secret} secret. Log in using the email ({user_email_secret}) and password ({user_password_secret}) from your secrets.
"""

DOCLIST_TEST_SETUP = f"""\
## Test Setup Requirements
- Log in to the app.
- Download the zip archive from {{johndoejunior_zip_url}}, extract it
- Take the bearer token from {{api_key_secret}} secret and use it to authenticate with the External API: {{external_api_specs_url}}.
- Create a new case using the External API: {{external_api_specs_url}}.
- Upload files to the case using the External API: {{external_api_specs_url}}.
- Keep making requests to chat-status for this case in 30 second intervals and CHECK: the chat status is "COMPLETE". Timeout is 15 minutes.
- Log in to the app.
- Open the case in the app.
- Click "Launch Sky" button
"""

# Common CHECK patterns
CHECK_PERSISTENCE = "CHECK persistence after page refresh"
CHECK_ORDER_PERSISTS = "CHECK order persists after refresh"
CHECK_PAGE_COUNT_UPDATES = "CHECK page count updates"
CHECK_CONFIRMATION_DIALOG = "CHECK confirmation dialog appears"
CHECK_SELECTION_CLEARS = "Selection clears after"

MODAL_DUAL_PANE_CHECKS = """\
- CHECK:
  - A modal window opens
  - Left pane displays the recognized text/content snippet
  - Right pane displays the corresponding PDF page
  - Both panes can be scrolled independently
  - Closing the modal returns to the same state and scroll position
"""


def create_qa_test(test_name: str, user_prompt: str) -> QATest:
    user_prompt = QA_PREAMBLE + "\n\n" + user_prompt
    return {
        "test_name": test_name,
        "user_prompt": user_prompt,
    }


# Individual tests. Selectable by name with --tests, but by default they run
# combined (see QA_TESTS at the bottom) so fewer cases are created in parallel.
SINGLE_TESTS: list[QATest] = [
    create_qa_test(
        test_name="test-external-api",
        user_prompt=f"""
You should test Sky External API: {{external_api_specs_url}}
Take the bearer token from {{api_key_secret}} secret and use it to authenticate with the API.
You need to:
- Create a new case. dateOfLoss и dateOfBirth should be in ISO format.
- CHECK: You see the case in the list.
- Upload this PDF document {{sample_pdf_url}} to this case
- CHECK: You see the document in the list.
- Make a request to chat-status for this case in 30 second intervals and CHECK: the chat status is "COMPLETE". Timeout is 10 minutes.
- If the chat status is not "COMPLETE" after 10 minutes, abort and send a message to the user saying what went wrong.
- After the chat status is "COMPLETE", archive the case using the API.
- CHECK: You don't see the case in the list anymore.
        """,
    ),
    create_qa_test(
        test_name="test-doclist-section-ops",
        user_prompt=f"""
## Objective
Test all section operations in the document list including rename, move, split, merge, and delete.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Section Operations Testing

### Rename Section
- Click the section actions menu (three dots) and select "Rename"
- CHECK inline input appears with current name pre-filled
- Test scenarios:
  - Rename with valid name (letters, numbers, special characters)
  - Try empty name (should show validation error)
  - Cancel rename with Escape key
  - Confirm with Enter key
  - CHECK name updates across UI immediately (optimistic update)
  - {CHECK_PERSISTENCE}

### Move Section to Different Category
- Select "Move To..." from section actions menu
- CHECK dropdown shows all available categories
- Move section to a different category
- CHECK section disappears from source category and appears in target category
- {CHECK_PAGE_COUNT_UPDATES} for both categories
- Test moving to the same category (should be no-op or prevented)
- CHECK section order in target category

### Split Section
- Find a section with 2+ pages
- Select "Split" from section actions
- CHECK split UI appears allowing you to choose split point
- Split section at various page positions (beginning, middle, end)
- CHECK:
  - Two sections created with correct page distribution
  - Page order preserved
  - Both sections appear in same category
  - Page thumbnails display correctly
- CHECK "Split" option is disabled for single-page sections

### Merge Sections
- Test merge via section actions menu:
  - Select "Merge" from a section's actions
  - Choose target section from dropdown
  - CHECK sections combine with pages in correct order
- Test merge via merge button between sections:
  - Hover between two adjacent sections
  - Click the merge (+) button that appears
  - CHECK a Merge dialog opens, pre-filled with the two sections
  - Cancel once: CHECK nothing is merged
  - Open it again and confirm
  - CHECK sections merge and the UI updates immediately after confirming (optimistic update)
- CHECK merged section name (should use first section's name)
- {CHECK_PAGE_COUNT_UPDATES} correctly
- Test merging sections from different categories (should move first)

### Delete Section
- Select "Delete" from section actions
- {CHECK_CONFIRMATION_DIALOG}
- Test:
  - Confirm deletion - section should disappear
  - Cancel deletion - section remains
  - {CHECK_PAGE_COUNT_UPDATES} for category
  - CHECK deletion persists after refresh
- CHECK "Delete" stays available for the only section left in the fallback category (an empty fallback category is allowed)
        """,
    ),
    create_qa_test(
        test_name="test-doclist-category-ops",
        user_prompt=f"""
## Objective
Test all category operations in the document list including rename, sort, merge all, delete, and create.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Category Operations Testing

### Rename Category
- Click category actions menu and select "Rename"
- CHECK inline input appears with current name
- Test scenarios:
  - Rename with valid name
  - Try empty name (should validate)
  - Special characters and Unicode
  - Very long names (test UI overflow)
  - Cancel with Escape, confirm with Enter
  - CHECK name updates across all instances

### Sort Sections in Category
- Test "Sort by Name":
  - Sort ascending (A-Z)
  - Sort descending (Z-A)
  - CHECK sections reorder alphabetically
  - {CHECK_ORDER_PERSISTS}
- Test "Sort by Date":
  - Sort ascending (oldest first)
  - Sort descending (newest first)
  - CHECK correct date-based ordering
  - {CHECK_ORDER_PERSISTS}

### Merge All Sections in Category
- Select "Merge All" from category actions
- CHECK confirmation dialog shows correct section count
- Confirm merge
- CHECK:
  - All sections combine into single section
  - Pages maintain correct order
  - Page count is sum of all sections
  - Merged section uses appropriate name
  - Category now has only one section

### Delete Category
- Select "Delete" from category actions
- CHECK dialog shows:
  - Category name
  - Section count
  - Dropdown to select target category for sections
- Test scenarios:
  - Move sections to different category and delete
  - Cancel deletion
  - CHECK sections move correctly
  - CHECK category disappears
  - CHECK you cannot delete the last remaining category

### Create New Category
- Click "Add Category" button in doc list actions bar
- CHECK:
  - New category appears with placeholder name
  - Auto-assigned color (unique from existing)
  - Inline input is active for naming
  - Can drag sections into new empty category
  - Can cancel creation (Escape key)
  - Category saves with Enter key
  - Appears in correct order
        """,
    ),
    create_qa_test(
        test_name="test-doclist-drag-drop",
        user_prompt=f"""
## Objective
Test all drag and drop functionality in the document list including reordering categories, sections, and pages.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Drag & Drop Testing
Rules in the current app: categories and sections can only be dragged while they are **collapsed** (the grip handle appears on hover), and sections can only be dropped into an **expanded** category. Dragging is off in export mode and multi-select mode.

### Reorder Categories
- Collapse a category, hover it, and drag it by the grip handle (vertical lines icon)
- CHECK an expanded category shows no grip handle and can't be dragged
- Test:
  - Move a category up, down, to the first and to the last position
  - Drop on an invalid area: CHECK it snaps back
  - CHECK visual feedback during drag
  - {CHECK_ORDER_PERSISTS}

### Reorder Sections Within Category
- With the category expanded and the section collapsed, drag a section within the category
- CHECK an expanded section (pages showing) can't be dragged
- Test:
  - Move a section up and down, and drop it between other sections
  - CHECK a gap opens where the section will land
  - CHECK section order updates immediately
  - {CHECK_ORDER_PERSISTS}

### Move Sections Between Categories
- Expand the target category, then drag a collapsed section into it
- CHECK:
  - The section appears in the new category with its pages and page-count badge unchanged
  - Moving out the last section of a category removes that (now empty) category
- Create a new category with "Add category", then drag a section into its dashed drop zone ("Category created, drag sections or pages here to activate it."): CHECK the category becomes a normal category with that section
- Do several moves quickly: CHECK the final state is correct
- {CHECK_ORDER_PERSISTS}

### Reorder Pages Within Section
- Expand a section to show page thumbnails
- Drag individual pages to reorder
- Test:
  - Reorder pages within the section
  - Move the first page to the last position, and the last page to the first
  - CHECK a blue line shows where the page will land
  - CHECK page numbers update correctly
  - CHECK thumbnails display in the correct order
  - {CHECK_ORDER_PERSISTS}

### Drag & Drop Edge Cases
- Test with slow internet (enable throttling): CHECK the order updates immediately and is still correct once the request finishes
- Drag immediately after another drag: CHECK both moves apply
- If a page move fails, CHECK it reverts and the toast "Failed to move the page. Please try again." appears (you may not be able to force a failure; skip if so)
        """,
    ),
    create_qa_test(
        test_name="test-doclist-batch-ops",
        user_prompt=f"""
## Objective
Test batch operations and multi-select functionality in the document list.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Batch Operations & Multi-Select Testing
Batch selection uses **Shift+click and Cmd/Ctrl+click on section rows** (outside export mode). The checkboxes only appear in export mode and are not used for batch actions.

### Multi-Select Sections
- Test selection methods:
  - Cmd/Ctrl+click section rows to select non-contiguous sections
  - Shift+click to select a range of sections
- CHECK:
  - Selected sections have a highlighted (blue) background
  - Once 2 or more sections are selected, a toolbar appears showing "N selected" with Move, AI Rename, Merge, Summarize and Delete
  - Cmd/Ctrl+click a selected section to deselect it
  - The toolbar's close (X) button clears the selection

### Merge Multiple Selected Sections
- Select 2+ sections (same or different categories)
- Click "Merge" in the selection toolbar
- CHECK:
  - The merge starts immediately (there is no confirmation dialog) and a "Merging Sections" / "Please wait..." dialog is shown
  - The result keeps the name and category of the first selected section in list order
  - All pages are combined in the correct order
  - {CHECK_SELECTION_CLEARS} merge
  - {CHECK_PAGE_COUNT_UPDATES} correctly

### Move Multiple Selected Sections
#### Move to an Existing Category in Document-List Order
- Clear any search filter, exit export mode, and clear section selection.
- Find three sections in one source category and record their names and displayed top-to-bottom order as A1, A2, A3. These are labels for this test, not required section names. If needed, split a multi-page section to prepare three sections before continuing.
- Choose a different, already saved target category containing at least one section. Record its current section order and both categories' page counts.
- Hold Ctrl (Cmd on macOS) and click the section row A3 FIRST, then A1. Do not use export checkboxes or Shift-click: click order must be opposite to document-list order.
- CHECK exactly A1 and A3 are selected, A2 is not selected, and the section selection toolbar shows a count of 2.
- Click "Move" in the section selection toolbar, choose the saved target category in "Move To...", then confirm with "Move".
- CHECK:
  - The target's original sections remain in the recorded order, followed by A1 then A3, NOT A3 then A1.
  - A1 and A3 disappear from the source; A2 stays in the source and unselected sections keep their order.
  - {CHECK_PAGE_COUNT_UPDATES} for both categories by the moved sections' page counts.
  - {CHECK_SELECTION_CLEARS} move.
- Refresh the page and reopen the categories.
- {CHECK_ORDER_PERSISTS}: the target still ends with A1, A3, and neither moved section reappears in the source.

#### Move to a New Category in Document-List Order
- Use "Add Category" to create a uniquely named empty category in the document list. If a create-new-name option is offered, select it. Do not refresh or move any documents into it yet: this must still be a new, unsaved category, not an existing saved category.
- Choose two sections from DIFFERENT source categories. Record their names and current top-to-bottom order across the whole document list as U then V, and record their page counts and their source categories' page counts.
- Clear section selection, then Ctrl/Cmd-click V FIRST and U SECOND.
- CHECK exactly U and V are selected and the section selection toolbar shows a count of 2.
- Click "Move" in the section selection toolbar, choose the newly added empty category in "Move To...", then confirm with "Move".
- CHECK:
  - The new category contains exactly U then V, NOT V then U.
  - U and V disappear from their respective source categories; unselected sections keep their order.
  - {CHECK_PAGE_COUNT_UPDATES}: each source loses the moved section's pages and the new category has the sum of U and V's pages.
  - {CHECK_SELECTION_CLEARS} move.
- Refresh the page and reopen the categories.
- {CHECK_ORDER_PERSISTS}: the new category remains saved with exactly U then V, and neither section reappears in its source category.

### Delete Multiple Selected Sections
- Select multiple sections
- Click "Delete" in the selection toolbar
- CHECK:
  - A "Delete Sections" confirmation dialog lists the selected section names
  - Cancel keeps all sections
  - On confirm, all selected sections are deleted
  - {CHECK_SELECTION_CLEARS} deletion
- Deleting every section of a category is allowed
        """,
    ),
    create_qa_test(
        test_name="test-doclist-export",
        user_prompt=f"""
## Objective
Test export functionality in the document list including PDF export and table of contents.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Export Functionality Testing
Exports are generated on the server and **delivered by email**; nothing downloads in the browser, so don't check file contents.

### Enter Export Mode
- Click the "Export" button in the doc list actions
- CHECK:
  - Checkboxes appear for categories and sections, plus a select-all checkbox
  - The header shows the Filter input, "Cancel", and an "Export" button with a ▾ menu
  - The ▾ menu lists "Export Full Doc List as PDF", "Export Table of Contents as PDF", "Export Full Doc List as DOCX" and "Export Table of Contents as DOCX"
  - Section/category action menus are hidden and drag & drop is disabled

### Select Sections for Export
- Test selection in export mode:
  - Select individual sections, an entire category, all sections, and a mix from different categories
  - CHECK "Selected: N" shows the number of selected **sections**
  - CHECK the select-all checkbox shows a partial state when only some sections are selected
- With nothing selected: CHECK the Export button is disabled

### Exit Export Mode
- With some sections selected, click "Cancel"
- CHECK a "Discard Selection" dialog appears; "Keep" stays in export mode with the selection, discarding leaves export mode
- With nothing selected, "Cancel" leaves export mode directly

### Export Full Doc List as PDF
- Select sections and click "Export" (defaults to the full doc list as PDF)
- CHECK:
  - The button shows a spinner and "Exporting..." and can't be clicked again
  - An "Exporting Your Document" dialog appears saying "Check your email" and showing the file name (starting with "Doclist:" and ending in ".pdf")
  - Export mode exits and the Export button briefly shows a check mark

### Export Table of Contents
- Enter export mode again, select sections, and choose "Export Table of Contents as PDF" from the ▾ menu
- CHECK the dialog shows a file name starting with "TOC - " and ending in ".pdf"

### Export Edge Cases
- Select a large number of sections (or all) and export: CHECK it starts normally
- Click Export repeatedly: CHECK only one export starts (the button is disabled while exporting)
        """,
    ),
    create_qa_test(
        test_name="test-doclist-export-error",
        user_prompt=f"""
## Objective
Test that a failed doc list export shows an error and keeps export mode and the selection so the user can retry.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Simulating a Failed Export
The export request has to fail on purpose. Use Playwright in a scratch directory (`npm i playwright`) and attach to the already-open Chrome over CDP (`chromium.connectOverCDP("http://localhost:29229")`), so you keep the logged-in session. Find the page with the case open and add a route that aborts the export requests:
`page.route("**/doclist/export*/async", route => route.abort())` (matches both the PDF and the DOCX export)
Keep that script running while you do the failing exports below, and keep interacting with the app through the browser as usual.

### Failed PDF Export
- Click the "Export" button in the doc list actions to enter export mode
- Select two sections from different categories; CHECK "Selected: 2" is shown
- With the route active, click "Export" (full doc list as PDF)
- CHECK:
  - A red error toast appears saying "Export failed. Please try again."
  - No "Exporting Your Document" / "Check your email" dialog appears
  - The doc list stays in export mode: checkboxes, "Cancel" and the "Export" button are still shown
  - The same two sections are still checked and "Selected: 2" is still shown
  - The "Export" button is enabled again (no spinner, no check mark)

### Failed DOCX Export
- Still in export mode with the same selection, choose "Export Full Doc List as DOCX" from the ▾ menu
- CHECK the same error toast appears, no dialog appears, and export mode and "Selected: 2" are kept

### Retry After the Failure
- Remove the route (`page.unroute("**/doclist/export*/async")`, or stop the script) so requests go through again
- Without changing the selection, click "Export"
- CHECK:
  - An "Exporting Your Document" dialog appears saying "Check your email", with a file name starting with "Doclist:" and ending in ".pdf"
  - Export mode exits after the dialog appears
        """,
    ),
    create_qa_test(
        test_name="test-doclist-search",
        user_prompt=f"""
## Objective
Test filter and search functionality in the document list.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Filter & Search Testing
The "Filter" input at the top of the doc list filters sections by **section name only** (page text is not searched).

### Basic Filtering
- Type part of a section name into the Filter input
- CHECK:
  - Only sections whose name matches are shown; non-matching sections are hidden
  - Matching is case-insensitive
  - Categories that contain matches are expanded automatically
  - Category headers without matches stay visible but show no sections
- Type a word that appears only in a page's text, not in any section name: CHECK no sections match
- Clear the input (or click its X): CHECK all sections are shown again and categories return to their default expanded/collapsed state

### Fuzzy Matching
- Type a section name with some letters left out but in order (e.g. "mdcl rcrd" for "Medical Record")
- CHECK the section still matches
- Matching letters are skipped-letter tolerant, not typo tolerant: a misspelled or transposed name may not match, which is expected

### Highlighting and Order
- Enter a search term
- CHECK:
  - The matched characters in each section name are shown in **bold**
  - For a multi-word query, each word's match is bold
  - Results within a category are ordered by match quality (best match first)
  - Bold highlighting disappears when the search is cleared

### Search Edge Cases
- Search while categories are collapsed: CHECK matching categories expand
- Search in export mode: CHECK the filter still works
- Type and clear the search several times quickly: CHECK the list stays consistent
- Search with special characters such as ( ) [ ] * ?: CHECK nothing breaks
        """,
    ),
    create_qa_test(
        test_name="test-doclist-duplicates",
        user_prompt=f"""
## Objective
Test duplicate detection functionality in the document list.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Duplicate Detection Testing

### Find Duplicates
- If there is no "Duplicates" button or no duplicate groups, create a duplicate first: rename one section to exactly the same name as another section.
- Click the "Duplicates" button
- CHECK:
  - A "Duplicates" dialog opens ("Find and manage duplicate sections using text-based detection.")
  - Duplicate groups are listed, each labelled "Identical" or "Possible match" with a page count (there is no similarity percentage)
  - Selecting a group shows its sections side by side for comparison
  - "Sync scroll" scrolls the compared sections together

### Rename from the Duplicates dialog
- In the side-by-side view, use "Rename" on one section and enter a new name
- CHECK the new name shows in the dialog and in the document list

### Delete Duplicates
- In the side-by-side view, select every section in the group
- CHECK the message "At least one section must be kept" appears and the delete button is disabled
- Unselect sections until one is selected for deletion
- CHECK the button reads "Delete 1 Duplicate" and "1 section to delete" is shown
- Click the delete button: CHECK a confirmation dialog shows which sections will be deleted and which are kept
- Cancel once: CHECK nothing is deleted
- Delete again and confirm
- CHECK the deleted section disappears from the document list and the duplicates list updates (the group disappears if only one section is left)

### Analyze with AI
- Click "Analyze with AI"
- CHECK progress is shown while analyzing, then either groups labelled "AI Detected" appear or the message "No new duplicate groups found by AI analysis." is shown
        """,
    ),
    create_qa_test(
        test_name="test-doclist-expand-collapse",
        user_prompt=f"""
## Objective
Test expand and collapse functionality in the document list.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Expand/Collapse Testing

### Category Accordion
- Click category header to expand/collapse
- Test:
  - Single category expand/collapse
  - Expand all / collapse all
  - Auto-expansion behavior (small lists auto-expand)
  - State persists during session
  - Drag into collapsed category auto-expands

### Section Page Thumbnails
- Click section to expand page thumbnails
- Test:
  - Thumbnails load correctly
  - Can scroll through many pages
  - Lazy loading behavior
  - Thumbnail quality
  - Page numbers display correctly
        """,
    ),
    create_qa_test(
        test_name="test-chat",
        user_prompt=f"""
## Objective
Test chat functionality including sending messages, receiving AI responses, term highlighting, clearing, copying, exporting, and case-based context.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Chat Testing

### Open Chat Tab
- Click the Chat tab in the right panel
- CHECK:
  - Chat interface loads without delay
  - Input field is active
  - Previous messages (if any) are displayed in correct order
  - Placeholder is visible when chat is empty

### Send Message
- Type a message and press Enter
- CHECK:
  - User message appears instantly
  - "Thinking…" or loading indicator appears

### Receive AI Response
- Wait for AI to generate a reply
- CHECK:
  - Response renders fully
  - Formatting (bold, lists, headings) is correct
  - Content is relevant to the query

### Term Definitions
- In an AI response, click a term with a dotted underline
- CHECK:
  - A dialog opens with the term's definition
  - The dialog closes correctly
  - Opening another term's definition works without UI freezes

### Clear
- Click Clear button
- CHECK:
  - All chat messages are cleared
  - Chat resets to default empty state ("Ask SKY anything")
  - Suggested prompts reappear
  - Input remains active

### Copy
- Click Copy button
- CHECK:
  - Entire chat content is copied
  - Button state changes to "Copied"

### Export Chat
- Click Export
- CHECK the options are DOCX, PDF and Plain Text (there is no Email option for chat) and an "Include Sources" option is available
- Export once as DOCX and once as PDF (try "Include Sources")
- CHECK:
  - Export starts without error
  - The downloaded file contains the complete chat
  - Formatting is preserved

### Case-Based Context
- Open Chat on Case A → send message
- Switch to Case B
- CHECK:
  - Case B has separate history
  - No cross-case contamination
- Return to Case A
- CHECK:
  - Case A may open with an empty chat; that is expected
  - The chat history selector ("Select a conversation") lists Case A's earlier conversation, and opening it shows the messages intact
  - Case B's conversation is not listed in Case A's history

### Sources Modal
- In an AI response that shows Sources: 1 2 3…, click on any source number
{MODAL_DUAL_PANE_CHECKS}
        """,
    ),
    create_qa_test(
        test_name="test-pdf-viewer",
        user_prompt=f"""
## Objective
Test PDF viewer functionality including page selection, zoom, OCR text view, rotation, deletion, and toolbar features.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## PDF Viewer Testing

### Page Selection
- Expand a section in the doc list and click one of its page tiles
- CHECK:
  - The selected page opens in the main doc viewer area
  - The page tile is highlighted in the doc list
  - Page number in the top navigation updates accordingly
- Click multiple pages with different content types (text, tables, images)
- CHECK:
  - Each page loads without delays
  - No rendering artifacts or distortion
  - Navigation stays synchronized with the current page
- After selecting a page, check the bottom toolbar
- CHECK it reads "Page N selected" and shows Text, Highlight, Zoom, Crop to Copy, Add Note, Rotate and Delete (and Add to Chronology if enabled), plus a close (X) button

### Zoom Page
- Select a page
- Click Zoom
- CHECK:
  - While hovering the page, the whole page is enlarged (2×) in place and follows the cursor (there is no separate magnifier)
  - The zoomed view is clear and high-resolution
  - Rotate and Delete are disabled while Zoom is on
  - Toggling Zoom off returns the page to normal view
- Test zooming on text, images, small fonts
- CHECK all details remain readable without pixelation

### Text (OCR View)
- Select a page
- Click Text
{MODAL_DUAL_PANE_CHECKS}
- Additional CHECK: Text matches PDF content (accuracy check)

### Rotate Page
- Select a page
- Click Rotate in the bottom toolbar
- CHECK:
  - Page rotates immediately
  - Rotation is visually correct and smooth
  - Left panel thumbnail updates accordingly
  - {CHECK_PERSISTENCE}

### Delete Page
- Select a page
- Click Delete in the bottom toolbar
- Confirm deletion in confirmation dialog
- CHECK:
  - A "Page deleted" toast appears and the page is removed
  - Page numbers update
  - The selection clears and the bottom toolbar disappears (no other page is selected automatically)
  - {CHECK_PERSISTENCE}

### Viewer Sync With Doc List
- Select a section in the doc list that contains multiple pages
- Click a page within that section
- CHECK:
  - Viewer scrolls to the correct page
  - The viewer and the doc list remain synchronized
  - Selecting the next/previous page updates selection in doc list

### Bottom Toolbar Visibility
- Select a page
- CHECK the bottom toolbar appears
- Click the same page again: CHECK the toolbar hides
- Select a page and click the toolbar's close (X) button: CHECK the toolbar hides
        """,
    ),
    create_qa_test(
        test_name="test-version-management",
        user_prompt=f"""
## Objective
Test version management functionality including creating, renaming, deleting, and switching between versions.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Version Management Testing

The versions dropdown and the ⋮ actions button are on the case's files page.

### Open Version List
- Open the versions dropdown (it is disabled while the case has only one version; clone first if needed)
- CHECK:
  - Active version (Master or other) is highlighted
  - All existing versions appear in the list
  - No missing or duplicate entries

### Clone Version
- Wait until all files in the case have finished processing (Clone is disabled until then)
- Click the ⋮ button next to the version select and choose "Clone"
- CHECK a "Create New Version" dialog opens with a default name ending in "(copy)"
- Enter a new version name and confirm
- CHECK:
  - A "Version ready" message appears and the app switches to the new version automatically
  - The cloned version contains the same documents, sections, and page structure as the original
  - The new version appears in the versions dropdown

### Rename Version
- On Master, open the ⋮ menu: CHECK only "Clone" is offered (no Rename or Delete)
- Switch to a non-Master version and click ⋮ next to the version dropdown
- Select Rename
- Enter a new version name and confirm
- CHECK:
  - Version name updates immediately in the dropdown
  - {CHECK_PERSISTENCE}
  - No breaking of version ordering or selection

### Delete Version
- On a non-Master version, click ⋮ next to the version dropdown
- Select Delete
- Confirm deletion
- CHECK:
  - Version disappears from the versions dropdown
  - Other versions remain unchanged
  - The app switches back to the Master version
  - Deleted version's content is no longer accessible

### Switch Between Versions
- Open the versions dropdown
- Select another version
- CHECK:
  - All content updates immediately (documents, sections, pages)
  - Sidebar categories match the selected version
  - Viewer displays content of the selected version
  - No content leakage between versions
        """,
    ),
]


def combine_qa_tests(test_name: str, part_names: list[str]) -> QATest:
    """Run several doclist tests in one Devin session on one case.

    Each test creates its own case and uploads the whole John Doe set, and too
    many of those in parallel leave cases stuck in DRAFT. Combining them means
    one case (one setup) per session; the parts then run one after another.
    Order parts read-only first, so a later part's edits can't break an earlier one.
    """
    by_name = {t["test_name"]: t for t in SINGLE_TESTS}
    objectives, bodies = [], []
    for i, name in enumerate(part_names, 1):
        prompt = by_name[name]["user_prompt"]
        assert prompt.startswith(QA_PREAMBLE) and prompt.count(DOCLIST_TEST_SETUP) == 1, name
        head, body = prompt[len(QA_PREAMBLE):].split(DOCLIST_TEST_SETUP)
        objective = head.split("## Objective", 1)[1].split("## Login Instructions", 1)[0].strip()
        objectives.append(f"{i}. **{name}**: {objective}")
        body = body.strip()
        body = body[3:].strip() if body.startswith("---") else body
        bodies.append(f"---\n\n# Part {i}: {name}\n\n{body}")

    nl = "\n"
    combined = f"""
## Objective
This session runs {len(part_names)} test parts on ONE case, in this order:
{nl.join(objectives)}

Do the test setup once, then run the parts one after another on the same case.
This overrides the "abort" rule above: if a CHECK fails, record it and continue with
the next step and the next part. Only abort if the setup fails or the app is unusable.
In the structured output, 'success' is true only if every CHECK in every part passed,
and each check's 'part' is the test name of the part it belongs to.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

{(nl + nl).join(bodies)}
"""
    return create_qa_test(test_name, combined)


# What runs by default: 7 sessions, 6 of them creating a John Doe case (was 11).
QA_TESTS: list[QATest] = [
    next(t for t in SINGLE_TESTS if t["test_name"] == "test-external-api"),
    combine_qa_tests("test-doclist-expand-and-sections", ["test-doclist-expand-collapse", "test-doclist-section-ops"]),
    combine_qa_tests("test-doclist-duplicates-and-categories", ["test-doclist-duplicates", "test-doclist-category-ops"]),
    combine_qa_tests("test-doclist-search-and-drag-drop", ["test-doclist-search", "test-doclist-drag-drop"]),
    combine_qa_tests("test-pdf-viewer-and-export", ["test-pdf-viewer", "test-doclist-export"]),
    combine_qa_tests("test-chat-and-versions", ["test-chat", "test-version-management"]),
    next(t for t in SINGLE_TESTS if t["test_name"] == "test-doclist-batch-ops"),
]

# Every test that --tests can select by name.
ALL_TESTS: dict[str, QATest] = {t["test_name"]: t for t in SINGLE_TESTS + QA_TESTS}
