#!/bin/bash
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.filePath // empty')
if [ -n "$FILE" ] && echo "$FILE" | grep -qE '(\.env|\.env\..*)$'; then
  echo "BLOCKED: Cannot edit .env files — contains secrets" >&2
  exit 2
fi
exit 0
