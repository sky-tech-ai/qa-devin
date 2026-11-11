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
        test_name="test-cases",
        user_prompt=f"""
## Objective
Test creating a case, uploading a document, finding the case with global search and archiving the case, first through the Sky External API and then through the app UI the way a user does it.

## Part 1: External API
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

## Part 2: App UI
{DEVIN_QA_LOGIN_INSTRUCTIONS}
- Download {{sample_pdf_url}} to your machine.
- Log in to the app and go to the "Cases" page. If a welcome screen or tour shows up, dismiss it ("Skip to Dashboard", "Skip Tour", "Skip for Now").
- Click "+ Case". In the "Create Case" dialog enter the Case Name "QA UI Case <6 random digits>" and leave the other fields empty.
- Click "Continue" (and "Continue" again on the document handling step, keeping "Automatic"; if a "Possible Duplicates" step appears, click "Create Case").
- CHECK the dialog closes and the new case's page opens with its name as the title.
- In the "Drag & drop documents, images, or audio files" area, click "Choose..." and upload the downloaded PDF.
- CHECK the document appears in the case's file list.
- Wait for processing (up to 10 minutes, checking every 30 seconds).
- CHECK the document's status badge turns green ("Processed" on hover) and the "Launch Sky" button becomes enabled.
- Click "Launch Sky".
- CHECK the case workspace opens with the document in the doc list.

### Global search
- Go to the "Cases" page. Click on an empty area of the page (not an input), then press Ctrl+K (Cmd+K on a Mac).
- CHECK a search dialog opens with a focused "Search" input.
- Type the full case name ("QA UI Case <your 6 digits>") and wait 2 seconds.
- CHECK a "Cases" group lists exactly one result: your case, with the matched text highlighted and "1 file" in its details line.
- Replace the text with "zzqa nomatch <your 6 digits>" and wait 2 seconds.
- CHECK the dialog shows "No results found".
- Press Escape. CHECK the search dialog closes.
- Click the magnifying glass icon in the top header. Type the case name again and click your case in the results.
- CHECK the case page opens in a new browser tab with the case name as the title. Close that tab and go back to the first tab.

### Archive
- Go back to the case page, click the ⋮ ("More actions") button next to the case title, choose "Archive" and confirm with "Archive".
- CHECK the app returns to the Cases list and the case is no longer listed.
- Press Ctrl+K and search for the full case name again (wait 2 seconds).
- CHECK the dialog shows "No results found" (archived cases are not searchable). Press Escape.
        """,
    ),
    create_qa_test(
        test_name="test-doclist",
        user_prompt=f"""
## Objective
Test the main document list flows: organize sections and categories, find sections, and export the doc list.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Document List
Each section row and category header has a ⋮ actions menu. Do the steps in order; they all use the same case.

### Organize Sections
- Rename a section: ⋮ → "Rename", type a new name ending in " QA", press Enter.
- CHECK the new name is shown in the doc list.
- Move that section: ⋮ → "Move To...", pick a different category.
- CHECK it disappears from its old category and appears in the new one, and both categories' page counts update.
- Delete another section: ⋮ → "Delete", confirm.
- CHECK the section is gone and its category's page count drops.

### Organize Categories
- Click "Add Category" in the doc list actions bar, name it "QA Category", press Enter.
- Collapse a section in another category, hover it, and drag it by its grip handle (vertical lines icon) into the "QA Category" drop zone.
- CHECK "QA Category" now contains that section.
- On "QA Category": ⋮ → "Delete", choose a category to move its section to, and confirm.
- CHECK "QA Category" is gone and its section is in the chosen category.
- Refresh the page.
- CHECK the renamed and moved sections, the deleted section and the deleted category look the same as before the refresh.

### Filter
- Type part of a section name into the "Filter" input at the top of the doc list.
- CHECK only sections whose names match are shown. Then clear the filter.

### Duplicates
- Rename one section to exactly the same name as another section, so there is a duplicate.
- Click the "Duplicates" button.
- CHECK a "Duplicates" dialog lists a group containing both sections.
- In that group, select one section to delete, click "Delete 1 Duplicate" and confirm.
- CHECK that section disappears from the document list and the other one is kept.

### Export the Doc List
Exports are delivered by email; don't check file contents.
- Click "Export" in the doc list actions, select one category's checkbox, and click "Export".
- CHECK an "Exporting Your Document" dialog appears saying to check your email, with a file name starting with "Doclist:" and ending in ".pdf".
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
  - CHECK a blue insertion line shows where the section will land (other sections don't move out of the way)
  - CHECK section order updates immediately
  - {CHECK_ORDER_PERSISTS}

### Move Sections Between Categories
- Expand the target category, then drag a collapsed section into it
- CHECK:
  - The section appears in the new category with its pages and page-count badge unchanged
  - Moving out the last section of a category removes that (now empty) category
- Create a new category with "Add category", then drag a section into its dashed drop zone ("Category created, drag sections or pages here to activate it."): CHECK the category becomes a normal category with that section
- Do several moves one after another: CHECK the final state is correct and no "Outdated Version Detected" dialog appears
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
- With throttling on, drop a section and immediately try to drag another section, category or page:
  - CHECK dragging is disabled (no grip handle, nothing moves) while the first move is still saving
  - CHECK dragging works again as soon as the save finishes, and the second move then applies
  - CHECK no "Outdated Version Detected" dialog appears (version conflicts are only for edits by another user)
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
- CHECK "Cancel" is enabled in export mode before any export is started

### Export Full Doc List as PDF
- Select sections and click "Export" (defaults to the full doc list as PDF)
- CHECK:
  - The button shows a spinner and "Exporting..." and can't be clicked again
  - While "Exporting..." is shown, "Cancel" is disabled (the export can't be cancelled once requested). This only lasts a second or two, so take a screenshot right after clicking Export
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
        test_name="test-doclist-no-section-drag-while-filtered",
        user_prompt=f"""
## Objective
Check that sections can't be dragged while the document list filter has text (filtered results are
ordered by match quality, not saved order), and that dragging works again once the filter is cleared.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Section Drag While Filtered

### Baseline (no filter)
- Make sure the filter input at the top of the doc list is empty and all sections are collapsed.
- Note the order of the sections in a category that has at least 3 sections.
- CHECK the grip handle (vertical lines icon) is shown on collapsed section rows.

### Filter active
- Type a term in the filter that matches at least 2 sections (e.g. part of a section name that occurs more than once).
- CHECK only matching sections are shown.
- CHECK no grip handle is shown on any visible section row.
- Try to drag a visible section (press and drag on the row, and on where the grip normally is) below another visible section.
- CHECK the section doesn't move and no drop zone indicator appears.
- Refresh the page and clear the filter.
- CHECK the section order is the same as the order noted in the baseline (nothing was saved).

### Filter cleared
- Type a term in the filter again, then clear it completely.
- CHECK all sections are shown again and the grip handles are back on collapsed section rows.
- Drag a section one position down within its category.
- CHECK the section moves to the dropped position.
- {CHECK_ORDER_PERSISTS}
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
  - A dialog titled "Duplicates" opens, with no red error message under the title (its description is screen-reader-only, so don't check for visible description text)
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
- CHECK progress is shown while analyzing, then either groups labelled "AI Detected" appear or a notification "AI analysis complete" with "No new duplicate groups found." appears (it disappears after a few seconds, so watch for it as soon as analysis ends)
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
Test the main chat flow: ask a question about the case, get an answer with sources, open a source, and clear the chat.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Chat Testing

### Ask a Question
- Click the Chat tab in the right panel.
- Type "What injuries did the patient have?" and press Enter.
- CHECK your message appears and a loading indicator shows while the answer is generated.
- Wait for the answer.
- CHECK the answer is about the John Doe case and contains inline source citations (small reference chips).

### Open a Source
- Click one of the citations (if several are grouped behind a "Show N sources" button, open it and click one).
- CHECK the document viewer jumps to the cited page and highlights the cited text.

### Clear
- Click the Clear button.
- CHECK the messages are gone and the empty chat state ("Ask SKY anything") is shown.
        """,
    ),
    create_qa_test(
        test_name="test-case-workspace",
        user_prompt=f"""
## Objective
Test the main case workspace flows besides the doc list and chat: the PDF viewer (select a page, zoom, OCR text, rotate, delete a page), the Summary and Notes tabs, and sharing the case.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## PDF Viewer Testing

### Select a Page
- Expand a section in the doc list and click one of its page tiles.
- CHECK the page opens in the viewer, its tile is highlighted in the doc list, and a bottom toolbar reads "Page N selected".

### Zoom
- Click Zoom in the bottom toolbar and hover the page.
- CHECK the page is shown enlarged and readable. Click Zoom again to turn it off.

### Text (OCR View)
- Click Text in the bottom toolbar.
- CHECK a dialog shows the page's recognized text next to the PDF page, and the text matches the page. Close it.

### Rotate Page
- Click Rotate in the bottom toolbar.
- CHECK the page and its doc list thumbnail rotate.
- {CHECK_PERSISTENCE}

### Delete Page
- Select a page and click Delete in the bottom toolbar, then confirm.
- CHECK the page is removed from the viewer and the doc list, and the section's page count drops by one.
- {CHECK_PERSISTENCE}

## Summary Tab
- Click a section in the doc list, then open the "Summary" tab in the right panel.
- CHECK after a few seconds a summary appears under the section's name (in capitals) and it describes that section's document.
- Click a page tile of that section.
- CHECK the title changes to "<SECTION NAME> – PAGE <N>" and the summary changes to that page.

## Notes Tab
- Open the "Notes" tab and type "QA note <6 random digits>" in the editor.
- Wait 5 seconds.
- CHECK the status under the editor reads "Edited just now by …" (it may briefly show "Saving...").
- Refresh the page and open the Notes tab again.
- CHECK your note text is still there.

## Share the Case
- Click "Share" in the doc list header.
- CHECK a "Guest Access" dialog opens.
- Enter "qa+guest-<6 random digits>@example.com" and click "Create Link".
- CHECK a card with that email and a share link (with a "Copy" button) appears.
- Click the trash icon ("Revoke Access") on that guest.
- CHECK the guest is removed from the dialog.
        """,
    ),
    create_qa_test(
        test_name="test-chronology",
        user_prompt=f"""
## Objective
Test the main Chronology flows: see the case's events, open a source, edit and confirm an event, and add an event from the PDF viewer.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Chronology Testing
The event list only renders rows that are on screen. To work with a specific event, type a distinctive word from it into the "Filter" box above the list instead of scrolling. Each row's ⋮ "Actions" button only appears while you hover the row.

### Events
- Open the "Chronology" tab in the right panel.
- If a "Case Chronology" view with a "Generate" button is shown, click "Generate" and wait until the grey placeholder rows turn into events (up to 5 minutes, checking every 30 seconds).
- CHECK the tab lists events, each with a date (undated ones are grouped under "Undated") and a page source badge.
- Click the source badge of one event.
- CHECK the document viewer opens that page.

### Edit and Confirm an Event
- Pick an event and filter the list to it. Hover it, click ⋮ "Actions" → "Edit".
- CHECK an "Edit Event" dialog opens with the event's Detail filled in.
- Add " QA edit" at the end of Detail and click "Save".
- CHECK the row shows the new detail and an "Edited" badge.
- Refresh the page, open the Chronology tab and filter to "QA edit" again.
- CHECK the edit is still there.
- Clear the filter, pick a different event that has no review badge, hover it and click ⋮ "Actions" → "Confirm".
- CHECK that event now shows a "Confirmed" badge.

### Add an Event from the Viewer
- Select a page in the document viewer and click "Add to Chronology" in the bottom toolbar.
- CHECK an "Add Event" dialog opens. Wait until "Pre-filling fields with AI…" is gone.
- Set Detail to "QA added event", fill in a Date if it is empty, and click "Create".
- CHECK the right panel switches to the Chronology tab and, after filtering to "QA added event", the event is listed with a "Manual" badge.
        """,
    ),
    create_qa_test(
        test_name="test-version-management",
        user_prompt=f"""
## Objective
Test the main version flows: clone a version, switch between versions, and delete a version.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Version Management Testing

The versions dropdown and the ⋮ actions button are on the case's files page.

### Create a Version
- Wait until all files in the case have finished processing (creating a version is disabled until then).
- Click the ⋮ button next to the version select, choose "Create Version", enter a new version name and confirm.
- CHECK a "Version ready" message appears, the app switches to the new version, and it has the same documents as Master.

### Switch Between Versions
- Open the versions dropdown and select Master, then the new version again.
- CHECK the documents and doc list update to the selected version each time.

### Delete Version
- On the new version, click ⋮ next to the version dropdown, choose Delete, and confirm.
- CHECK the version disappears from the dropdown and the app switches back to Master.
        """,
    ),
    create_qa_test(
        test_name="test-custom-reports",
        user_prompt=f"""
## Objective
Test the main custom report flow end to end: create a report template in Settings, generate a report from it on a case, work with the report (sources, edit, section rewrite), make it outdated by changing the doc list and rewrite it, export it, then delete the template.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

{DOCLIST_TEST_SETUP}

---

## Rules for this test
- Report templates are shared by the whole organization and other QA sessions may run at the same time. Pick a unique template name now: "QA Report " followed by 6 random digits (e.g. "QA Report 482913"), and use it everywhere below as TEMPLATE_NAME.
- Only touch the template you created. Do not set any template as default, and do not edit or delete other templates.
- Report generation takes a few minutes. When a step says to wait for the report, wait up to 10 minutes, checking every 30 seconds.
- Cleanup: at the end, even if a CHECK failed or you aborted, delete TEMPLATE_NAME (see "Delete the Template"). If deleting fails, mention it in the summary.

## Create a Report Template
- Open Settings and click "Reports" in the settings menu (URL ends with /settings/reports).
- Click "+ Template". CHECK a "Create Report Template" dialog opens at "Step 1 of 2".
- Click "Continue" with the fields empty. CHECK the validation message "The name field can't be empty" appears and you stay on step 1.
- Fill in:
  - Template name: TEMPLATE_NAME
  - Definition: "QA test template with two short sections"
- Click "Continue". CHECK step 2 shows one empty section.
- Fill in the first section:
  - Title: "Case Overview"
  - Purpose: "Summarize the case"
  - Prompt (click "Click to add prompt" to open it): "In 3 to 5 sentences, summarize who the patient is, what happened, and the main injuries. Cite the source pages."
- Click "+ Section" and fill in the second section:
  - Title: "Treatment Summary"
  - Purpose: "Summarize the treatment"
  - Prompt: "List the main treatments and providers as a short bullet list. Cite the source pages."
- Click "Save".
- CHECK:
  - The dialog closes
  - A card named TEMPLATE_NAME appears in the template list with a "New" badge
- Using the External API with the bearer token from {{api_key_secret}}: `GET /reports/templates`. CHECK the response includes a template named TEMPLATE_NAME.

## Generate a Report
- Go back to the case and click "Launch Sky".
- Open the "Reports" tab in the right panel.
- Open the report selector: the combobox at the top of the panel. It may say "Choose a Report or Template" or show another report's name. If a "Generated Reports" card list is shown, use the selector above it.
- Type "QA Report" in "Search templates" and select TEMPLATE_NAME.
- CHECK a "Generate Report" view appears with TEMPLATE_NAME as its title and a "Generate" button.
- Click "Generate".
- CHECK generation progress is shown (e.g. "Preparing your report" and/or "N of 2 sections ready" in the panel, or a "Generating 1 report" widget in the bottom-right corner).
- Wait for the report to finish.
- CHECK:
  - The report shows two sections titled "Case Overview" and "Treatment Summary"
  - Both sections have generated text about the John Doe case (not empty, no "Failed to generate this section" error)
  - The text contains inline source citations (small reference chips)
- Using the External API: `GET /cases/{{{{caseId}}}}/reports`. CHECK it includes a report for TEMPLATE_NAME.

## Sources
- In "Case Overview", click one inline source citation (if several are grouped behind a "Show N sources" button, open it and click one).
- CHECK the document viewer jumps to the cited document page.

## Edit a Section
- Hover over "Case Overview" and click "Edit" (pencil icon) in the action bar.
- CHECK the section turns into an inline editor (no modal) with "Cancel" and "Save Changes" buttons.
- Add the sentence "QA edit marker." at the end of the section text and click "Save Changes".
- CHECK the editor closes and the section shows "QA edit marker.".
- Refresh the page and open TEMPLATE_NAME's report in the Reports tab again (via the selector or the "Generated Reports" cards). CHECK "QA edit marker." is still there.

## Rewrite a Section
- Hover over "Treatment Summary" and click "Rewrite".
- CHECK the panel shows that the section is being rewritten (e.g. "Rewriting “Treatment Summary”").
- Wait until it finishes.
- CHECK:
  - "Treatment Summary" shows regenerated text (not empty, no error)
  - "Case Overview" still contains "QA edit marker." (other sections are unchanged)

## Outdated Report after a Doc List Change
- In the doc list on the left, move any section to a different category (section ⋮ menu → "Move To...").
- Go back to the Reports tab with TEMPLATE_NAME open.
- CHECK:
  - A "Documents changed" banner with a "Rewrite" button appears
  - The section-level "Rewrite" button is disabled while the report is outdated
- Click "Rewrite" in the banner and wait for the report to finish.
- CHECK:
  - The "Documents changed" banner is gone
  - Both sections have generated text again

## Export
- Click "Export" at the bottom of the report panel.
- CHECK an "Export Report" dialog opens with an "Export as" format select (DOCX selected by default) and a checked "Show References" option.
- Keep DOCX and click "Export".
- CHECK an "Exporting Your Document" dialog appears, saying to check your email, with a file name ending in ".docx". Close it.
  (The file is delivered by email; don't check the mailbox.)

## Delete the Template
- Go to Settings → Reports and find the TEMPLATE_NAME card.
- Open its ⋮ menu ("More actions") and click "Delete".
- CHECK a "Delete Template" confirmation dialog names TEMPLATE_NAME. Click "Delete".
- CHECK the TEMPLATE_NAME card is gone from the list.
- Using the External API: `GET /reports/templates`. CHECK TEMPLATE_NAME is no longer included.
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


# What runs by default: 5 sessions, 4 of them creating a John Doe case.
# Main user flows only: Devin sessions are expensive. The detailed doc list
# specs above stay selectable by name with --tests.
QA_TESTS: list[QATest] = [
    next(t for t in SINGLE_TESTS if t["test_name"] == name)
    for name in [
        "test-cases",
        "test-doclist",
        "test-case-workspace",
    ]
] + [
    combine_qa_tests(
        "test-chat-chronology-and-versions",
        ["test-chat", "test-chronology", "test-version-management"],
    ),
    next(t for t in SINGLE_TESTS if t["test_name"] == "test-custom-reports"),
]

# Every test that --tests can select by name.
ALL_TESTS: dict[str, QATest] = {t["test_name"]: t for t in SINGLE_TESTS + QA_TESTS}
