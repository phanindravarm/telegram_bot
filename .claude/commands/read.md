Read the file at `$ARGUMENTS` and explain it based on where it lives in the project. Do NOT modify any files.

## Step 1: Read the file

Read the file at `$ARGUMENTS`. If the path is relative, resolve it from the project root. If the file doesn't exist, say so and stop.

## Step 2: Determine the category and explain

Based on the file's location, provide a structured explanation:

### If `.claude/commands/*.md` (Claude Code slash command):
- **Purpose**: One-line summary of what the command does
- **Steps**: Numbered list of what the command instructs Claude to do
- **Triggers**: When/why a developer would use this command

### If `tests/test_*.py` (test file):
- **Module under test**: Which source module this tests
- **Test cases**: For each test function, one line explaining what it verifies
- **Mocking**: What external dependencies are patched
- **Coverage assessment**: Any obvious gaps (untested branches, missing edge cases)

### If `commands/*.py` (bot command handler):
- **Commands**: Which `/command`(s) this module handles
- **Flow**: Step-by-step what happens when the command is called
- **External dependencies**: APIs, DB calls, other modules used
- **Error handling**: How failures are handled and what the user sees

### Otherwise (any other file):
- **Purpose**: What role this file plays in the project
- **Key functions/classes**: Brief description of each
- **Dependencies**: What it imports and what depends on it
