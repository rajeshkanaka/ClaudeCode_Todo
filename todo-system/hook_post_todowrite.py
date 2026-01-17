#!/usr/bin/env python3
"""
PostToolUse[TodoWrite] Hook - Persist todo state after writes
==============================================================

Triggers on: After TodoWrite tool completes
Purpose: Capture and persist todo state to disk for session continuity
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo_core import update_todos, log_debug


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        log_debug("PostToolUse[TodoWrite]: Failed to parse input")
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")

    # Only process TodoWrite
    if tool_name != "TodoWrite":
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    todos = tool_input.get("todos", [])

    if not todos:
        log_debug("PostToolUse[TodoWrite]: No todos in input")
        sys.exit(0)

    log_debug(f"PostToolUse[TodoWrite]: Persisting {len(todos)} todos")

    # Persist to disk
    success = update_todos(todos)

    if success:
        log_debug("PostToolUse[TodoWrite]: State persisted successfully")
    else:
        log_debug("PostToolUse[TodoWrite]: Failed to persist state")

    # Always exit 0 - don't block Claude
    sys.exit(0)


if __name__ == "__main__":
    main()
