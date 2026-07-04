---
name: new-command
description: Scaffold a new Telegram bot command with handler, test, and registration
---

Create a new bot command called "$ARGUMENTS".

1. Copy `templates/command.py` → `commands/$ARGUMENTS.py`, replacing every `COMMAND_NAME` with `$ARGUMENTS`
2. Copy `templates/test.py` → `tests/test_$ARGUMENTS.py`, replacing every `COMMAND_NAME` with `$ARGUMENTS`
3. In `commands/__init__.py`, add the import and register in COMMANDS dict
4. In `commands/help.py`, add a help text line for `/$ARGUMENTS`
5. Update `tests/test_help.py` to expect the new command in help output
6. Run `source env/bin/activate && pytest tests/test_$ARGUMENTS.py tests/test_help.py -v` to verify
