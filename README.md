# Todo Enforcement Hook System

> **Automatic todo tracking and enforcement for Claude Code sessions**

A production-ready hook system that ensures Claude never forgets tasks, persists state across sessions/compacts, and blocks responses until in-progress work is completed.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [How It Works](#how-it-works)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Commands Reference](#commands-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [Files Reference](#files-reference)

---

## Overview

This system solves a critical problem: **Claude forgetting tasks during long sessions or after context compaction**.

It works by:
1. Injecting todo reminders into every prompt
2. Persisting todos to disk after every TodoWrite
3. Restoring todos on session resume/compact
4. **Blocking Claude from stopping if tasks are incomplete**

---

## Features

| Feature | Description |
|---------|-------------|
| **Auto-persistence** | Todos saved to disk after every TodoWrite |
| **Session recovery** | Todos restored on resume, compact, or restart |
| **Skill detection** | Extra reminders when invoking skills (e.g., `/neel-study-test`) |
| **Stop blocking** | Prevents Claude from finishing if in_progress tasks exist |
| **Per-project isolation** | Each project has its own state file |
| **Atomic operations** | Crash-safe file writes using temp+rename |
| **Auto-cleanup** | Old state files removed after 7 days |
| **Debug logging** | Full audit trail with log rotation |

---

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                      SESSION START                          │
│  SessionStart Hook → Load previous todos → Inject context   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      USER PROMPT                            │
│  UserPromptSubmit Hook → Detect skill/task → Add reminder   │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    CLAUDE PROCESSING                        │
│  Claude sees todos in context → Creates/updates todos       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    TOOL EXECUTION                           │
│  PostToolUse[TodoWrite] Hook → Persist todos to disk        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   RESPONSE COMPLETION                       │
│  Stop Hook → Check in_progress → BLOCK if incomplete        │
└─────────────────────────────────────────────────────────────┘
```

### Hook Chain

| Hook | Event | Purpose |
|------|-------|---------|
| `hook_session_start.py` | SessionStart | Load todos on startup/resume/compact |
| `hook_user_prompt.py` | UserPromptSubmit | Inject reminders on each prompt |
| `hook_post_todowrite.py` | PostToolUse[TodoWrite] | Save todos to disk |
| `hook_pre_compact.py` | PreCompact | Save state before compaction |
| `hook_stop.py` | Stop | Block if in_progress tasks exist |

---

## Installation

The system is already installed. To verify:

```bash
# Check all files exist and are executable
ls -la ~/.claude/hooks/todo-system/

# Verify hooks are registered
grep -A2 "todo-system" ~/.claude/settings.json
```

### Manual Installation (if needed)

1. **Create the hook directory:**
   ```bash
   mkdir -p ~/.claude/hooks/todo-system
   ```

2. **Copy all hook files** (see [Files Reference](#files-reference))

3. **Make executable:**
   ```bash
   chmod +x ~/.claude/hooks/todo-system/*.py
   chmod +x ~/.claude/hooks/todo-system/*.sh
   ```

4. **Add to settings.json** (see [Configuration](#configuration))

---

## Configuration

The hooks are configured in `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|compact|clear",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/todo-system/hook_session_start.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/todo-system/hook_user_prompt.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "TodoWrite",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/todo-system/hook_post_todowrite.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/todo-system/hook_pre_compact.py",
            "timeout": 5000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/todo-system/hook_stop.py",
            "timeout": 5000
          }
        ]
      }
    ]
  }
}
```

### Configuration Options

Edit `todo_core.py` to customize:

| Setting | Default | Description |
|---------|---------|-------------|
| `MAX_STATE_AGE_DAYS` | 7 | Auto-delete states older than this |
| `MAX_LOG_SIZE_MB` | 5 | Rotate debug log at this size |
| `SCHEMA_VERSION` | 1 | For future migrations |

---

## Usage

### Automatic Behavior

Once installed, the system works automatically:

1. **On session start/resume**: Previous todos are loaded
2. **On each prompt**: Reminders are injected based on prompt content
3. **On TodoWrite**: State is persisted to disk
4. **On /compact**: State is saved before compaction
5. **On response end**: Blocked if in_progress tasks exist

### What You'll See

When Claude detects a skill invocation:
```
<skill-todo-enforcement skill="neel-study-test">
SKILL INVOKED: neel-study-test
MANDATORY FIRST ACTION: Use TodoWrite to list ALL expected deliverables.
</skill-todo-enforcement>
```

When Claude has active todos:
```
<active-todos>
  ○ [PENDING] Task 1
  → [IN_PROGRESS] Task 2
</active-todos>
```

When Claude tries to stop with in_progress tasks:
```
STOP BLOCKED: You have 1 task(s) marked as in_progress:
  - Task 2

Please either:
1. Complete these tasks and mark them as 'completed' using TodoWrite
2. Or mark them as 'pending' if you cannot complete them now
```

---

## Commands Reference

### Quick Health Check
```bash
~/.claude/hooks/todo-system/health_check.sh
```
Checks:
- All hook files exist and are executable
- State directory is accessible
- Debug log is healthy
- Settings are configured

### Full Test Suite
```bash
python3 ~/.claude/hooks/todo-system/test_hooks.py
```
Tests:
- All hook input/output formats
- Edge cases (empty, malformed input)
- Performance (should be <100ms per hook)
- State integrity
- Disk usage

### Watch Debug Log (Real-time)
```bash
tail -f ~/.claude/todo-state/debug.log
```

### View Recent Activity
```bash
tail -20 ~/.claude/todo-state/debug.log
```

### View Current State File
```bash
cat ~/.claude/todo-state/todos_*.json | python3 -m json.tool
```

### Clear All State (Reset)
```bash
rm -f ~/.claude/todo-state/todos_*.json
```

### Clear Debug Log
```bash
> ~/.claude/todo-state/debug.log
```

### Test Individual Hooks

```bash
# Test SessionStart
echo '{"source": "resume"}' | python3 ~/.claude/hooks/todo-system/hook_session_start.py

# Test UserPromptSubmit
echo '{"prompt": "/neel-study-test create paper"}' | python3 ~/.claude/hooks/todo-system/hook_user_prompt.py

# Test PostTodoWrite
echo '{"tool_name": "TodoWrite", "tool_input": {"todos": [{"content": "Test", "status": "pending", "activeForm": "Testing"}]}}' | python3 ~/.claude/hooks/todo-system/hook_post_todowrite.py

# Test PreCompact
echo '{"trigger": "manual"}' | python3 ~/.claude/hooks/todo-system/hook_pre_compact.py

# Test Stop
echo '{}' | python3 ~/.claude/hooks/todo-system/hook_stop.py
```

---

## Testing

### Verify System is Active

1. Start a new Claude Code session
2. Check debug log for SessionStart entry:
   ```bash
   tail -5 ~/.claude/todo-state/debug.log
   ```
   You should see: `SessionStart hook triggered: source=startup`

### Test Todo Persistence

1. Ask Claude to create a todo list
2. Check state was saved:
   ```bash
   cat ~/.claude/todo-state/todos_*.json
   ```
3. Run `/compact` or restart session
4. Verify todos are restored in Claude's context

### Test Stop Blocking

1. Ask Claude to create a task and mark it `in_progress`
2. Try to end the conversation
3. Claude should be blocked with "STOP BLOCKED" message

### Performance Testing

```bash
# Run 10 iterations of each hook
python3 ~/.claude/hooks/todo-system/test_hooks.py
```

Expected results:
- Each hook: <100ms average
- Total per-prompt overhead: ~170ms (UserPrompt + Stop)

---

## Troubleshooting

### Hooks Not Firing

**Symptom**: No entries in debug log

**Solutions**:
1. Verify settings.json is valid JSON:
   ```bash
   python3 -m json.tool ~/.claude/settings.json > /dev/null && echo "Valid"
   ```
2. Check hook files are executable:
   ```bash
   ls -la ~/.claude/hooks/todo-system/*.py
   ```
3. Restart Claude Code session

### State Not Persisting

**Symptom**: Todos lost after compact/resume

**Solutions**:
1. Check state directory exists:
   ```bash
   ls -la ~/.claude/todo-state/
   ```
2. Check for write errors in debug log:
   ```bash
   grep -i "error\|fail" ~/.claude/todo-state/debug.log
   ```
3. Verify PostToolUse hook is registered for TodoWrite

### Stop Hook Not Blocking

**Symptom**: Claude finishes despite in_progress tasks

**Solutions**:
1. Verify Stop hook is registered in settings.json
2. Check debug log for Stop hook entries
3. Test hook manually:
   ```bash
   echo '{}' | python3 ~/.claude/hooks/todo-system/hook_stop.py
   ```

### Hook Timeout Errors

**Symptom**: "Hook timed out" messages

**Solutions**:
1. Increase timeout in settings.json (default: 5000ms)
2. Check for slow disk I/O
3. Review debug log for bottlenecks

### Stale State from Wrong Project

**Symptom**: Seeing todos from different project

**Solutions**:
1. Each project has its own state file (SHA256 of path)
2. Clear specific project's state:
   ```bash
   # Find your project's hash
   python3 -c "import hashlib; print(hashlib.sha256(b'/your/project/path').hexdigest()[:16])"
   # Delete that state file
   rm ~/.claude/todo-state/todos_<hash>.json
   ```

### Debug Log Too Large

**Symptom**: Log file consuming disk space

**Solutions**:
1. Log auto-rotates at 5MB
2. Manual clear:
   ```bash
   > ~/.claude/todo-state/debug.log
   ```

---

## Architecture

### State File Format

```json
{
  "schema_version": 1,
  "project_id": "0676fe55db2eb0ed",
  "project_name": "my-project",
  "todos": [
    {
      "content": "Task description",
      "status": "pending",
      "activeForm": "Working on task"
    }
  ],
  "created_at": "2026-01-17T14:30:00",
  "updated_at": "2026-01-17T14:35:00",
  "session_id": "abc123",
  "last_compact": false
}
```

### Safety Guarantees

| Protection | Implementation |
|------------|----------------|
| **Crash-safe writes** | Temp file + atomic rename |
| **Race condition prevention** | fcntl file locking |
| **Data validation** | Schema validation on load |
| **Infinite loop prevention** | `stop_hook_active` flag |
| **Disk bloat prevention** | 7-day auto-cleanup, 5MB log rotation |
| **Project isolation** | SHA256 hash of project path |

### Mermaid Diagram

See `ARCHITECTURE.md` for full Mermaid flow diagram.

---

## Files Reference

```
~/.claude/hooks/todo-system/
├── todo_core.py           # Core module (state management, atomic ops)
├── hook_session_start.py  # SessionStart hook (load on startup/resume)
├── hook_user_prompt.py    # UserPromptSubmit hook (inject reminders)
├── hook_post_todowrite.py # PostToolUse hook (persist on TodoWrite)
├── hook_pre_compact.py    # PreCompact hook (save before compact)
├── hook_stop.py           # Stop hook (block if in_progress)
├── test_hooks.py          # Comprehensive test suite
├── health_check.sh        # Quick health check script
├── ARCHITECTURE.md        # Mermaid diagrams and detailed docs
└── README.md              # This file

~/.claude/todo-state/
├── todos_<hash>.json      # Per-project state files
└── debug.log              # Hook execution logs
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0.0 | 2026-01-17 | Initial production release |

---

## License

Part of the Claude Code configuration. For personal use.

---

## Quick Start Checklist

- [ ] Run health check: `~/.claude/hooks/todo-system/health_check.sh`
- [ ] Start new Claude Code session
- [ ] Ask Claude to create a multi-step task
- [ ] Verify todos appear in context
- [ ] Run `/compact` and verify todos persist
- [ ] Try ending with in_progress task (should be blocked)

**You're all set!**
