#!/usr/bin/env python3
"""
SessionStart Hook - Load todos at session start/resume/compact
================================================================

Triggers on: startup, resume, clear, compact
Injects previous todos into context for continuity.
"""

import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo_core import (
    load_state,
    get_incomplete_todos,
    generate_todo_context,
    cleanup_old_states,
    log_debug,
)


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    source = input_data.get("source", "unknown")
    log_debug(f"SessionStart hook triggered: source={source}")

    # Run cleanup on startup (not on every resume/compact)
    if source == "startup":
        removed = cleanup_old_states()
        if removed > 0:
            log_debug(f"Cleaned up {removed} old state files")

    # Generate context with previous todos
    incomplete = get_incomplete_todos()

    if incomplete or source in ("resume", "compact"):
        context = generate_todo_context(include_reminder=True)

        if context:
            # Add source-specific message
            if source == "compact":
                context = f'<session-restored reason="context_compacted">\n{context}\n</session-restored>'
            elif source == "resume":
                context = f'<session-restored reason="session_resumed">\n{context}\n</session-restored>'

            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": context,
                }
            }
            print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
