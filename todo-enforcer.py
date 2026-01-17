#!/usr/bin/env python3
"""
Todo Enforcer Hook - Runs before EVERY user prompt

Purpose:
1. Reminds Claude to use TodoWrite for multi-step tasks
2. Reads last known todo state from persistent file
3. Injects todo context after session restart/compact

This runs on UserPromptSubmit event.
"""

import json
import sys
import os
from pathlib import Path
from datetime import datetime

# Persistent todo state file location
TODO_STATE_DIR = Path.home() / ".claude" / "todo-state"
TODO_STATE_DIR.mkdir(parents=True, exist_ok=True)


def get_project_id():
    """Generate a project-specific ID based on current directory."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    # Create a simple hash of the path
    return cwd.replace("/", "_").replace("\\", "_").strip("_")[-50:]


def get_todo_state_file():
    """Get the todo state file for current project."""
    project_id = get_project_id()
    return TODO_STATE_DIR / f"todos_{project_id}.json"


def read_last_todos():
    """Read last known todo state from persistent storage."""
    state_file = get_todo_state_file()
    if state_file.exists():
        try:
            with open(state_file, "r") as f:
                data = json.load(f)
                return data.get("todos", []), data.get("timestamp", "")
        except (json.JSONDecodeError, IOError):
            return [], ""
    return [], ""


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)  # Don't block on bad input

    prompt = input_data.get("prompt", "").lower()

    # Get last known todos
    last_todos, timestamp = read_last_todos()

    # Build context injection
    context_parts = []

    # ALWAYS remind about TodoWrite for any non-trivial prompt
    trivial_keywords = ["hi", "hello", "hey", "thanks", "ok", "yes", "no", "?"]
    is_trivial = (
        any(prompt.strip() == kw for kw in trivial_keywords) or len(prompt) < 10
    )

    if not is_trivial:
        context_parts.append(
            """
<todo-enforcement>
CRITICAL REMINDER: Before starting any multi-step task:
1. IMMEDIATELY use TodoWrite to create a task list with ALL deliverables
2. Each todo item must have BOTH 'content' (imperative) and 'activeForm' (present continuous)
3. Mark tasks in_progress BEFORE starting, completed IMMEDIATELY after finishing
4. For skills: List ALL expected outputs (e.g., Question Paper + Answer Key = 2 separate todos)
</todo-enforcement>
"""
        )

    # If we have previous todos, inject them for continuity
    if last_todos:
        incomplete = [t for t in last_todos if t.get("status") != "completed"]
        if incomplete:
            context_parts.append(
                f"""
<previous-session-todos timestamp="{timestamp}">
IMPORTANT: The following tasks were in progress before session restart/compact:
"""
            )
            for i, todo in enumerate(incomplete, 1):
                status = todo.get("status", "pending")
                content = todo.get("content", "Unknown task")
                context_parts.append(f"  {i}. [{status.upper()}] {content}")

            context_parts.append(
                """
Please use TodoWrite to restore/continue these tasks if they are still relevant.
</previous-session-todos>
"""
            )

    # Output the context injection
    if context_parts:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": "\n".join(context_parts),
            }
        }
        print(json.dumps(output))

    sys.exit(0)


if __name__ == "__main__":
    main()
