#!/usr/bin/env python3
"""
PreCompact Hook - Save state before context compression
========================================================

Triggers on: Before manual or auto compact
Purpose: Ensure todo state is saved before context is compressed
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo_core import load_state, save_state, get_incomplete_todos, log_debug


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    trigger = input_data.get("trigger", "unknown")
    log_debug(f"PreCompact hook triggered: trigger={trigger}")

    # Load current state and re-save to update timestamp
    state = load_state()
    incomplete = get_incomplete_todos()

    if incomplete:
        log_debug(
            f"PreCompact: Saving {len(incomplete)} incomplete todos before compact"
        )

        # Mark that this state was saved before a compact
        state["last_compact"] = True
        state["compact_trigger"] = trigger

        save_state(state)

    # Don't block compact
    sys.exit(0)


if __name__ == "__main__":
    main()
