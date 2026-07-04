Audit test coverage for all bot commands, assess test quality, generate missing tests, and report.

## Step 1: Discover commands and tests

Read `commands/__init__.py` and extract every entry in the `COMMANDS` dict. Group commands by their **source module** (e.g. `/ingest`, `/query`, `/sources`, `/forget` all belong to the `rag` module). Also note utility modules like `ask_config.py` and `document_utils.py` — skip `ask_config.py` (constants only).

List all `tests/test_*.py` files. Map each command module to its corresponding test file (e.g. `rag` → `test_rag.py`). Identify:
- Modules with **no test file**
- Modules with a test file

## Step 2: Assess test quality

For each **existing** test file, read both the test file and its corresponding command source. Evaluate against these criteria:

| Criterion | What to look for |
|-----------|-----------------|
| **Happy path** | At least one test with valid args that asserts a successful response |
| **Edge cases** | Tests for empty args, missing args, or error messages |
| **Dependency mocking** | All external calls (API requests, DB, `send_message`, `send_photo`) are patched |
| **Branch coverage** | Read the source — are all `if/else`, `try/except`, early returns tested? |

Rate each test file:
- **Good** — All four criteria met
- **Adequate** — Happy path + edge cases covered, but missing some branches or mocking gaps
- **Minimal** — Only 1-2 tests, major gaps

## Step 3: Generate missing test files

For any command module that has **no test file**, create `tests/test_<module>.py` following these exact conventions:

- Use `from unittest.mock import patch, MagicMock` at the top
- Use `@patch("commands.<module>.send_message")` decorator pattern (or `send_photo` if applicable)
- Patch all external dependencies (requests, APIs, DB calls)
- Import the handler **inside** each test function: `from commands.<module> import handle_<name>`
- Use `chat_id=123` in all test calls
- Write minimum 3 tests per module:
  1. Empty/missing args → assert usage/error message
  2. Happy path → valid args, mock successful external response
  3. Error/exception → mock external failure, assert error message sent

Do NOT modify or overwrite any existing test files that are passing.

## Step 4: Suggest improvements for weak tests

For test files rated **Adequate** or **Minimal**, present suggested additional test functions as code blocks. Explain what each new test covers. Do NOT modify the existing test files — just show the suggestions.

## Step 5: Run and verify

Run the full test suite:

```bash
source env/bin/activate && pytest tests/ -v 2>&1
```

If any tests fail:
- Only fix **test code**, never modify production source files
- Re-run until all tests pass

## Step 6: Print coverage report

Print a markdown table with these columns:

| Module | Commands | Test File | Status | Happy Path | Edge Cases | Mocking | Rating |
|--------|----------|-----------|--------|------------|------------|---------|--------|

Where:
- **Status**: `✅ Exists` / `🆕 Created` / `⏭️ Skipped`
- **Happy Path / Edge Cases / Mocking**: `✅` / `❌`
- **Rating**: Good / Adequate / Minimal

Then print summary counts:
- Total command modules
- Tests existing before audit
- Tests newly created
- Tests rated Good / Adequate / Minimal
- Actionable recommendations (if any)
