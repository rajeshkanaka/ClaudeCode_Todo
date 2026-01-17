#!/usr/bin/env python3
"""
UserPromptSubmit Hook - Light reminder before each prompt
==========================================================

Triggers on: Every user prompt submission
Purpose: Inject minimal reminder + detect skill invocations
"""

import json
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from todo_core import (
    get_incomplete_todos,
    get_in_progress_todos,
    generate_skill_todo_reminder,
    log_debug,
)

# Patterns that indicate trivial prompts (don't inject reminder)
TRIVIAL_PATTERNS = [
    r"^(hi|hello|hey|thanks|thank you|ok|okay|yes|no|y|n)\s*[!.?]*$",
    r"^\?+$",
    r"^(what|how|why|when|where|who)\s+(is|are|was|were|do|does|did|can|could|would|should)\b",  # Questions
]

# Patterns that indicate skill invocation
SKILL_PATTERNS = [
    r"/(\w[\w-]*)",  # /skill-name
    r"use\s+skill\s+['\"]?(\w[\w-]*)['\"]?",  # use skill 'name'
    r"invoke\s+['\"]?(\w[\w-]*)['\"]?\s+skill",  # invoke 'name' skill
]


def is_trivial_prompt(prompt: str) -> bool:
    """Check if prompt is trivial (no reminder needed)."""
    prompt_clean = prompt.strip().lower()

    # Very short prompts
    if len(prompt_clean) < 5:
        return True

    for pattern in TRIVIAL_PATTERNS:
        if re.match(pattern, prompt_clean, re.IGNORECASE):
            return True

    return False


def detect_skill_invocation(prompt: str) -> str | None:
    """Detect if prompt is invoking a skill, return skill name."""
    for pattern in SKILL_PATTERNS:
        match = re.search(pattern, prompt, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get("prompt", "")
    log_debug(f"UserPromptSubmit: prompt length={len(prompt)}")

    # Skip trivial prompts
    if is_trivial_prompt(prompt):
        log_debug("Trivial prompt detected, skipping reminder")
        sys.exit(0)

    context_parts = []

    # Check for skill invocation - stronger reminder
    skill_name = detect_skill_invocation(prompt)
    if skill_name:
        log_debug(f"Skill invocation detected: {skill_name}")
        context_parts.append(generate_skill_todo_reminder(skill_name))
    else:
        # Standard reminder for non-trivial prompts
        incomplete = get_incomplete_todos()
        in_progress = get_in_progress_todos()

        # Show current todos if any exist
        if incomplete:
            context_parts.append("<active-todos>")
            for todo in incomplete:
                status = todo.get("status", "pending")
                content = todo.get("content", "?")
                marker = "→" if status == "in_progress" else "○"
                context_parts.append(f"  {marker} {content}")
            context_parts.append("</active-todos>")

        # Add reminder only if this looks like a task request
        task_indicators = [
            "create",
            "make",
            "build",
            "implement",
            "add",
            "fix",
            "update",
            "write",
            "generate",
            "develop",
            "design",
            "refactor",
            "test",
        ]
        prompt_lower = prompt.lower()

        if any(ind in prompt_lower for ind in task_indicators):
            context_parts.append("<todo-reminder>")
            context_parts.append(
                "Multi-step task detected. Use TodoWrite to list ALL deliverables first."
            )
            context_parts.append("</todo-reminder>")

    # Output context if any
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
