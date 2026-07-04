#!/bin/bash
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
if [ -n "$FILE" ] && [[ "$FILE" == *.py ]]; then
  cd "$CLAUDE_PROJECT_DIR"
  source env/bin/activate
  black "$FILE" 2>&1
fi
exit 0
