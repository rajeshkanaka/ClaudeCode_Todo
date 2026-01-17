#!/usr/bin/env python3
"""
Todo Enforcement System - Core Module
=====================================

Industry-standard todo state management for Claude Code.

Features:
- Atomic file operations (temp + rename)
- Schema validation
- Per-project isolation
- Auto-cleanup of stale files
- Crash-safe persistence
- Debug logging

Author: Claude Code Hook System
Version: 2.0.0
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
import hashlib
import fcntl  # For file locking on Unix

# ============================================================================
# CONFIGURATION
# ============================================================================

TODO_STATE_DIR = Path.home() / ".claude" / "todo-state"
TODO_STATE_DIR.mkdir(parents=True, exist_ok=True)

DEBUG_LOG = TODO_STATE_DIR / "debug.log"
MAX_STATE_AGE_DAYS = 7  # Auto-cleanup states older than this
MAX_LOG_SIZE_MB = 5  # Rotate log if larger

# Schema version for future migrations
SCHEMA_VERSION = 1

# ============================================================================
# LOGGING
# ============================================================================


def log_debug(message: str) -> None:
    """Write debug message to log file with rotation."""
    try:
        # Rotate if too large
        if (
            DEBUG_LOG.exists()
            and DEBUG_LOG.stat().st_size > MAX_LOG_SIZE_MB * 1024 * 1024
        ):
            backup = DEBUG_LOG.with_suffix(".log.old")
            if backup.exists():
                backup.unlink()
            DEBUG_LOG.rename(backup)

        timestamp = datetime.now().isoformat()
        with open(DEBUG_LOG, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass  # Never crash due to logging


# ============================================================================
# PROJECT IDENTIFICATION
# ============================================================================


def get_project_id() -> str:
    """Generate a unique, stable project ID from the project directory."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    # Use SHA256 hash for consistent, safe filenames
    hash_input = cwd.encode("utf-8")
    return hashlib.sha256(hash_input).hexdigest()[:16]


def get_project_name() -> str:
    """Get human-readable project name."""
    cwd = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    return Path(cwd).name


def get_state_file() -> Path:
    """Get the state file path for current project."""
    return TODO_STATE_DIR / f"todos_{get_project_id()}.json"


# ============================================================================
# SCHEMA VALIDATION
# ============================================================================


def validate_todo(todo: Dict[str, Any]) -> bool:
    """Validate a single todo item against schema."""
    required_fields = ["content", "status", "activeForm"]
    valid_statuses = ["pending", "in_progress", "completed"]

    if not isinstance(todo, dict):
        return False

    for field in required_fields:
        if field not in todo:
            log_debug(f"Todo missing required field: {field}")
            return False

    if todo.get("status") not in valid_statuses:
        log_debug(f"Todo has invalid status: {todo.get('status')}")
        return False

    return True


def validate_state(state: Dict[str, Any]) -> bool:
    """Validate entire state object."""
    if not isinstance(state, dict):
        return False

    if "schema_version" not in state:
        return False

    todos = state.get("todos", [])
    if not isinstance(todos, list):
        return False

    return all(validate_todo(t) for t in todos)


# ============================================================================
# ATOMIC FILE OPERATIONS
# ============================================================================


def atomic_write(filepath: Path, data: Dict[str, Any]) -> bool:
    """
    Write data atomically using temp file + rename.
    This ensures we never have a corrupted state file.
    """
    try:
        # Create temp file in same directory (required for atomic rename)
        fd, temp_path = tempfile.mkstemp(
            dir=filepath.parent, prefix=".tmp_", suffix=".json"
        )

        try:
            with os.fdopen(fd, "w") as f:
                # Acquire exclusive lock
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            shutil.move(temp_path, filepath)
            log_debug(f"Atomic write successful: {filepath.name}")
            return True

        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise e

    except Exception as e:
        log_debug(f"Atomic write failed: {e}")
        return False


def safe_read(filepath: Path) -> Optional[Dict[str, Any]]:
    """Safely read and parse JSON file with locking."""
    if not filepath.exists():
        return None

    try:
        with open(filepath, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            return data
    except (json.JSONDecodeError, IOError) as e:
        log_debug(f"Safe read failed: {e}")
        return None


# ============================================================================
# STATE MANAGEMENT
# ============================================================================


def create_empty_state() -> Dict[str, Any]:
    """Create a new empty state object."""
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": get_project_id(),
        "project_name": get_project_name(),
        "todos": [],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "session_id": os.environ.get("CLAUDE_SESSION_ID", "unknown"),
    }


def load_state() -> Dict[str, Any]:
    """Load state from disk, creating new if needed."""
    state_file = get_state_file()
    state = safe_read(state_file)

    if state is None or not validate_state(state):
        log_debug("Creating new state (none found or invalid)")
        return create_empty_state()

    return state


def save_state(state: Dict[str, Any]) -> bool:
    """Save state to disk atomically."""
    state["updated_at"] = datetime.now().isoformat()
    state["session_id"] = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    return atomic_write(get_state_file(), state)


def update_todos(todos: List[Dict[str, Any]]) -> bool:
    """Update todos in state and persist."""
    state = load_state()

    # Validate all todos
    valid_todos = [t for t in todos if validate_todo(t)]
    if len(valid_todos) != len(todos):
        log_debug(f"Filtered {len(todos) - len(valid_todos)} invalid todos")

    state["todos"] = valid_todos
    return save_state(state)


def get_incomplete_todos() -> List[Dict[str, Any]]:
    """Get all incomplete (pending or in_progress) todos."""
    state = load_state()
    return [
        t
        for t in state.get("todos", [])
        if t.get("status") in ("pending", "in_progress")
    ]


def get_in_progress_todos() -> List[Dict[str, Any]]:
    """Get todos currently in progress."""
    state = load_state()
    return [t for t in state.get("todos", []) if t.get("status") == "in_progress"]


# ============================================================================
# CLEANUP
# ============================================================================


def cleanup_old_states() -> int:
    """Remove state files older than MAX_STATE_AGE_DAYS. Returns count removed."""
    removed = 0
    cutoff = datetime.now() - timedelta(days=MAX_STATE_AGE_DAYS)

    try:
        for state_file in TODO_STATE_DIR.glob("todos_*.json"):
            try:
                state = safe_read(state_file)
                if state:
                    updated = state.get("updated_at", "")
                    if updated:
                        updated_dt = datetime.fromisoformat(updated)
                        if updated_dt < cutoff:
                            state_file.unlink()
                            removed += 1
                            log_debug(f"Cleaned up old state: {state_file.name}")
            except (ValueError, OSError) as e:
                log_debug(f"Cleanup error for {state_file}: {e}")
    except Exception as e:
        log_debug(f"Cleanup failed: {e}")

    return removed


# ============================================================================
# CONTEXT GENERATION
# ============================================================================


def generate_todo_context(include_reminder: bool = True) -> str:
    """Generate context string for injection into Claude's context."""
    parts = []

    # Get current state
    incomplete = get_incomplete_todos()
    in_progress = get_in_progress_todos()
    state = load_state()

    if incomplete:
        parts.append("<current-todos>")
        parts.append(f"Project: {state.get('project_name', 'Unknown')}")
        parts.append(f"Last updated: {state.get('updated_at', 'Unknown')}")
        parts.append("")

        for i, todo in enumerate(incomplete, 1):
            status = todo.get("status", "pending").upper()
            content = todo.get("content", "Unknown")
            marker = "→" if status == "IN_PROGRESS" else "○"
            parts.append(f"  {marker} [{status}] {content}")

        parts.append("</current-todos>")
        parts.append("")

    if include_reminder:
        parts.append("<todo-protocol>")
        parts.append("MANDATORY: For multi-step tasks, use TodoWrite IMMEDIATELY:")
        parts.append(
            "1. Create ALL deliverables as separate todo items BEFORE starting"
        )
        parts.append("2. Mark in_progress BEFORE working, completed AFTER finishing")
        parts.append("3. Never batch completions - mark done immediately")
        parts.append("</todo-protocol>")

    return "\n".join(parts) if parts else ""


def generate_skill_todo_reminder(skill_name: str) -> str:
    """Generate skill-specific todo reminder."""
    return f"""<skill-todo-enforcement skill="{skill_name}">
SKILL INVOKED: {skill_name}

MANDATORY FIRST ACTION: Use TodoWrite to list ALL expected deliverables.
Skills often produce multiple outputs. Each output = separate todo item.

Example for question paper skills:
- Todo 1: "Create question paper"
- Todo 2: "Create answer key"

Do NOT proceed with the skill until todos are created.
</skill-todo-enforcement>"""


# ============================================================================
# MAIN (for testing)
# ============================================================================

if __name__ == "__main__":
    # Test the module
    print("Todo Core Module Test")
    print("=" * 40)
    print(f"Project ID: {get_project_id()}")
    print(f"Project Name: {get_project_name()}")
    print(f"State File: {get_state_file()}")
    print(f"State exists: {get_state_file().exists()}")

    # Test state operations
    state = load_state()
    print(f"Current todos: {len(state.get('todos', []))}")

    # Test cleanup
    removed = cleanup_old_states()
    print(f"Cleaned up {removed} old state files")
