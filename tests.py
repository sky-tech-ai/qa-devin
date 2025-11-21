from typing import TypedDict


class QATest(TypedDict):
    test_name: str
    user_prompt: str


QA_PREAMBLE = f"""\
Your job is to do QA testing on the {{url}} website.
Please follow the instructions below and make sure every line which starts with "CHECK" is working as expected.
If it is not then you should abort and send message to the user saying what went wrong. No need to send a message if it is working as expected.
After you are done, send a message with all the CHECKs you did and what the results were. You MUST use Devin's structured output feature (not a file) to send a JSON object with 'success' (boolean) and 'message' (string). The message should include whether each CHECK you ran passed or failed (and a reason if it failed).
"""

DEVIN_QA_LOGIN_INSTRUCTIONS = """\
For basic HTTP authentication, use "gloria:wisedocssuck". Log in using the email (DEV_USER_EMAIL) and password (DEV_USER_PASSWORD) from your secrets.
"""


def create_qa_test(test_name: str, user_prompt: str) -> QATest:
    user_prompt = QA_PREAMBLE + "\n\n" + user_prompt
    return {
        "test_name": test_name,
        "user_prompt": user_prompt,
    }


QA_TESTS: list[QATest] = [
    create_qa_test(
        test_name="test-external-api",
        user_prompt=f"""
You should test Sky External API: https://dev-api.app.usesky.ai/external-api/docs-json
Take the bearer token from SKY_API_KEY_DEV secret and use it to authenticate with the API.
You need to:
- Create a new case. dateOfLoss и dateOfBirth should be in ISO format.
- CHECK: You see the case in the list.
- Upload this PDF document https://pdfobject.com/pdf/sample.pdf to this case
- CHECK: You see the document in the list.
- Make a request to chat-status for this case in 30 second intervals and CHECK: the chat status is "COMPLETE". Timeout is 10 minutes.
- If the chat status is not "COMPLETE" after 10 minutes, abort and send a message to the user saying what went wrong.
- After the chat status is "COMPLETE", archive the case using the API.
- CHECK: You don't see the case in the list anymore.
        """,
    ),
    create_qa_test(
        test_name="test-doclist",
        user_prompt=f"""
## Objective
Thoroughly test all functionality of the document list (doc list) feature, including category management, section operations, drag-and-drop, batch operations, export, and edge cases.

## Login Instructions
{DEVIN_QA_LOGIN_INSTRUCTIONS}

## Test Setup Requirements
- Download the zip archive with test case from https://dev-assets.app.usesky.ai/previews/johndoejunior.zip
- Create a new test case & upload files to it using Sky API (https://dev-api.app.usesky.ai/external-api/docs): auth token is in secrets
- Wait until case is in "COMPLETED" status. You can poll chat-status endpoint for that. Wait up to 10 minutes, if it is not ready - STOP, and report failure.
- Click "Launch Sky" button in the case page. CHECK: The button is enabled.
- CHECK you have at least 3-4 categories with 2-3 sections each in the doc list

---

## 1. Section Operations Testing

### 1.1 Rename Section
- Click the section actions menu (three dots) and select "Rename"
- CHECK inline input appears with current name pre-filled
- Test scenarios:
  - Rename with valid name (letters, numbers, special characters)
  - Try empty name (should show validation error)
  - Cancel rename with Escape key
  - Confirm with Enter key
  - CHECK name updates across UI immediately (optimistic update)
  - CHECK persistence after page refresh

### 1.2 Move Section to Different Category
- Select "Move To..." from section actions menu
- CHECK dropdown shows all available categories
- Move section to a different category
- CHECK section disappears from source category and appears in target category
- Check page count updates for both categories
- Test moving to the same category (should be no-op or prevented)
- CHECK section order in target category

### 1.3 Split Section
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

### 1.4 Merge Sections
- Test merge via section actions menu:
  - Select "Merge" from a section's actions
  - Choose target section from dropdown
  - CHECK sections combine with pages in correct order
- Test merge via merge button between sections:
  - Hover between two adjacent sections
  - Click the merge line/button that appears
  - CHECK immediate merge with optimistic UI update
- CHECK merged section name (should use first section's name)
- CHECK page count updates correctly
- Test merging sections from different categories (should move first)

### 1.5 Delete Section
- Select "Delete" from section actions
- CHECK confirmation dialog appears
- Test:
  - Confirm deletion - section should disappear
  - Cancel deletion - section remains
  - CHECK page count updates for category
  - CHECK deletion persists after refresh
- CHECK "Delete" is disabled when only one section exists in fallback category

---

## 2. Category Operations Testing

### 2.1 Rename Category
- Click category actions menu and select "Rename"
- CHECK inline input appears with current name
- Test scenarios:
  - Rename with valid name
  - Try empty name (should validate)
  - Special characters and Unicode
  - Very long names (test UI overflow)
  - Cancel with Escape, confirm with Enter
  - CHECK name updates across all instances

### 2.2 Sort Sections in Category
- Test "Sort by Name":
  - Sort ascending (A-Z)
  - Sort descending (Z-A)
  - CHECK sections reorder alphabetically
  - CHECK order persists after refresh
- Test "Sort by Date":
  - Sort ascending (oldest first)
  - Sort descending (newest first)
  - CHECK correct date-based ordering
  - CHECK persistence

### 2.3 Merge All Sections in Category
- Select "Merge All" from category actions
- CHECK confirmation dialog shows correct section count
- Confirm merge
- CHECK:
  - All sections combine into single section
  - Pages maintain correct order
  - Page count is sum of all sections
  - Merged section uses appropriate name
  - Category now has only one section

### 2.4 Delete Category
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

### 2.5 Create New Category
- Click "Add Category" button in doc list actions bar
- CHECK:
  - New category appears with placeholder name
  - Auto-assigned color (unique from existing)
  - Inline input is active for naming
  - Can drag sections into new empty category
  - Can cancel creation (Escape key)
  - Category saves with Enter key
  - Appears in correct order

---

## 3. Drag & Drop Testing

### 3.1 Reorder Categories
- Drag category by the grip handle (vertical lines icon)
- Test:
  - Move category up in list
  - Move category down in list
  - Move to first position
  - Move to last position
  - Drop on invalid area (should snap back)
  - CHECK visual feedback during drag
  - CHECK order persists after refresh

### 3.2 Reorder Sections Within Category
- Drag section within same category
- Test:
  - Move section up
  - Move section down
  - Drop between other sections
  - CHECK drop zone indicators appear
  - CHECK section order updates immediately
  - Check persistence after refresh

### 3.3 Move Sections Between Categories
- Drag section from one category to another
- Test:
  - Drop into different category
  - Drop into empty category (CHECK empty drop zone works)
  - Drop into collapsed category (should auto-expand)
  - CHECK section appears in new category
  - CHECK page counts update for both categories
  - CHECK section maintains its pages/data
  - Test with multiple rapid moves (stress test)

### 3.4 Reorder Pages Within Section
- Expand a section to show page thumbnails
- Drag individual pages to reorder
- Test:
  - Reorder pages within section
  - Move first page to last position
  - Move last page to first position
  - Rapid reordering (multiple quick moves)
  - CHECK page numbers update correctly
  - CHECK thumbnails display in correct order
  - Check persistence

### 3.5 Drag & Drop Edge Cases
- Test with slow internet (enable throttling)
- Test dragging while API call is in-flight
- Test dragging immediately after another drag
- Test drag + page refresh during drag
- Test with very large sections (50+ pages)
- CHECK error handling for failed drag operations
- Test drag on touch devices (mobile)

---

## 4. Batch Operations & Multi-Select Testing

### 4.1 Multi-Select Sections
- Test selection methods:
  - Click section checkbox to select individual section
  - Shift+click to select range of sections
  - Ctrl/Cmd+click to select non-contiguous sections
  - Click "Select All" checkbox to select all sections
  - Click category checkbox to select all sections in category
- CHECK:
  - Selected sections have visual indicator
  - Selection count appears in UI
  - Batch action buttons become enabled
  - Can deselect individual sections
  - Can clear all selections

### 4.2 Merge Multiple Selected Sections
- Select 2+ sections (same or different categories)
- Click "Merge Selected" button
- CHECK:
  - Confirmation dialog shows section count
  - Merged section name is appropriate
  - All pages combined in correct order
  - Result appears in first selected section's category
  - Selection clears after merge
  - Page count updates correctly

### 4.3 Move Multiple Selected Sections
- Select multiple sections
- Click "Move Selected" button
- Choose target category from dropdown
- CHECK:
  - All selected sections move to target
  - Sections maintain relative order
  - Page counts update for all affected categories
  - Selection clears after move
  - Works with sections from different source categories

### 4.4 Delete Multiple Selected Sections
- Select multiple sections
- Click "Delete Selected" button
- CHECK:
  - Confirmation dialog shows count
  - All sections delete on confirm
  - Page counts update
  - Cannot delete if it would leave category empty (test edge case)
  - Selection clears after deletion

---

## 5. Export Functionality Testing

### 5.1 Enter Export Mode
- Click export button in doc list actions
- CHECK:
  - UI switches to export mode
  - Checkboxes appear for selection
  - Export options panel appears
  - Other actions are disabled/hidden in export mode
  - Can exit export mode

### 5.2 Select Sections for Export
- Test selection in export mode:
  - Select individual sections
  - Select entire category
  - Select all sections
  - Mix of sections from different categories
  - CHECK selection indicators
  - CHECK page count total updates

### 5.3 Export as PDF
- Select sections and click "Export PDF"
- CHECK:
  - Loading indicator appears
  - PDF generation completes
  - PDF downloads automatically
  - PDF contains all selected sections
  - Pages are in correct order
  - PDF quality is acceptable
  - Export mode exits after success

### 5.4 Export TOC Only
- Select sections and choose "TOC Only" option
- Export and CHECK:
  - Table of contents generated
  - All section names included
  - Page numbers are correct
  - Formatting is proper

### 5.5 Export Edge Cases
- Test with no sections selected (should disable export button)
- Test with very large selection (50+ pages)
- Test export failure scenarios (network error)
- Test canceling export mid-process
- Test multiple rapid export attempts

---

## 6. Filter & Search Testing

### 6.1 Basic Search
- Type in filter/search input at top of doc list
- Test:
  - Search by section name (partial match)
  - Search by page content keywords
  - Case-insensitive search
  - Special characters in search
  - Empty search (shows all)
  - Very long search query

### 6.2 Fuzzy Search
- Test fuzzy matching:
  - Misspelled section names
  - Missing characters
  - Transposed characters
  - CHECK matches highlight correctly
  - CHECK non-matches are hidden

### 6.3 Search with Highlighting
- Enter search term
- CHECK:
  - Matching text is highlighted in yellow/accent color
  - Multiple matches per section all highlighted
  - Highlighting clears when search cleared
  - Categories with no matches collapse or hide

### 6.4 Search Edge Cases
- Search while categories are collapsed
- Search with active selection
- Search in export mode
- Clear search rapidly (type and clear multiple times)
- Search with special regex characters (should escape)

---

## 7. Duplicate Detection Testing

### 7.1 Find Duplicates
- Click "Duplicates" button if available
- CHECK:
  - UI shows duplicate detection results
  - Sections with similar content are grouped
  - Similarity percentage/score shown
  - Can navigate to each duplicate section

### 7.2 Merge Duplicates
- From duplicate detection UI:
  - Select duplicate sections to merge
  - Confirm merge
  - CHECK sections combine correctly
  - CHECK duplicates list updates

### 7.3 Dismiss Duplicates
- Test dismissing false positive duplicates
- CHECK dismissed pairs don't reappear
- Test re-running duplicate detection

---

## 8. Expand/Collapse Testing

### 8.1 Category Accordion
- Click category header to expand/collapse
- Test:
  - Single category expand/collapse
  - Expand all / collapse all
  - Auto-expansion behavior (small lists auto-expand)
  - State persists during session
  - Drag into collapsed category auto-expands

### 8.2 Section Page Thumbnails
- Click section to expand page thumbnails
- Test:
  - Thumbnails load correctly
  - Can scroll through many pages
  - Lazy loading behavior
  - Thumbnail quality
  - Page numbers display correctly
"""
    ),
]
