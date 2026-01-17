#!/usr/bin/env python3
"""
Stop Hook - Verify todos complete before stopping
=================================================

Triggers on: When Claude is about to stop responding
Purpose: Warn about incomplete todos, optionally block stop
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo_core import get_incomplete_todos, get_in_progress_todos, log_debug


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    # Check if already in stop hook loop
    stop_hook_active = input_data.get("stop_hook_active", False)
    if stop_hook_active:
        log_debug("Stop hook: Already active, allowing stop to prevent loop")
        sys.exit(0)

    incomplete = get_incomplete_todos()
    in_progress = get_in_progress_todos()

    log_debug(
        f"Stop hook: {len(incomplete)} incomplete, {len(in_progress)} in_progress"
    )

    # If there are in_progress todos, warn Claude
    if in_progress:
        # Build warning message
        tasks = [t.get("content", "Unknown task") for t in in_progress]
        task_list = "\n".join(f"  - {t}" for t in tasks)

        output = {
            "decision": "block",
            "reason": f"""STOP BLOCKED: You have {len(in_progress)} task(s) marked as in_progress:
{task_list}

Please either:
1. Complete these tasks and mark them as 'completed' using TodoWrite
2. Or mark them as 'pending' if you cannot complete them now

Do not stop until all in_progress tasks are resolved.""",
        }
        print(json.dumps(output))
        sys.exit(0)

    # If there are pending todos, just warn but don't block
    if incomplete:
        log_debug(
            f"Stop hook: {len(incomplete)} pending todos, allowing stop with warning"
        )
        # Don't block, just log
        sys.exit(0)

    # All clear
    log_debug("Stop hook: No incomplete todos, allowing stop")
    sys.exit(0)


if __name__ == "__main__":
    main()
