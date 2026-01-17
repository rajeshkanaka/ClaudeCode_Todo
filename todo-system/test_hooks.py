#!/usr/bin/env python3
"""
Todo Hook System - Comprehensive Test Suite
============================================

Tests all hooks for:
- Correctness (expected output)
- Performance (execution time)
- Edge cases (malformed input)
- Integration (full flow)

Run: python3 ~/.claude/hooks/todo-system/test_hooks.py
"""

import json
import subprocess
import time
import os
import sys
from pathlib import Path
from typing import Dict, Any, Tuple, List
from datetime import datetime

# Configuration
HOOK_DIR = Path(__file__).parent
STATE_DIR = Path.home() / ".claude" / "todo-state"
PERFORMANCE_THRESHOLD_MS = 100  # Warn if hook takes longer


# Colors for output
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")


def print_test(name: str, passed: bool, time_ms: float, details: str = ""):
    status = (
        f"{Colors.GREEN}PASS{Colors.END}" if passed else f"{Colors.RED}FAIL{Colors.END}"
    )
    time_color = Colors.YELLOW if time_ms > PERFORMANCE_THRESHOLD_MS else Colors.GREEN
    print(f"  [{status}] {name} ({time_color}{time_ms:.1f}ms{Colors.END})")
    if details:
        print(f"         {Colors.YELLOW}{details}{Colors.END}")


def run_hook(hook_name: str, input_data: Dict[str, Any]) -> Tuple[int, str, str, float]:
    """Run a hook and return (exit_code, stdout, stderr, time_ms)"""
    hook_path = HOOK_DIR / hook_name

    start = time.perf_counter()
    try:
        result = subprocess.run(
            ["python3", str(hook_path)],
            input=json.dumps(input_data),
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(Path.home() / "Neel_Study"),  # Simulate project dir
        )
        elapsed = (time.perf_counter() - start) * 1000
        return result.returncode, result.stdout, result.stderr, elapsed
    except subprocess.TimeoutExpired:
        elapsed = (time.perf_counter() - start) * 1000
        return -1, "", "TIMEOUT", elapsed
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return -1, "", str(e), elapsed


def test_hook_session_start() -> List[Tuple[str, bool, float, str]]:
    """Test SessionStart hook"""
    results = []

    # Test 1: Startup with no existing todos
    code, out, err, ms = run_hook("hook_session_start.py", {"source": "startup"})
    passed = code == 0
    results.append(
        ("SessionStart: startup source", passed, ms, err if not passed else "")
    )

    # Test 2: Resume source
    code, out, err, ms = run_hook("hook_session_start.py", {"source": "resume"})
    passed = code == 0
    results.append(("SessionStart: resume source", passed, ms, ""))

    # Test 3: Compact source
    code, out, err, ms = run_hook("hook_session_start.py", {"source": "compact"})
    passed = code == 0
    results.append(("SessionStart: compact source", passed, ms, ""))

    # Test 4: Empty input (edge case)
    code, out, err, ms = run_hook("hook_session_start.py", {})
    passed = code == 0
    results.append(("SessionStart: empty input", passed, ms, ""))

    # Test 5: Malformed JSON handling
    try:
        result = subprocess.run(
            ["python3", str(HOOK_DIR / "hook_session_start.py")],
            input="not valid json",
            capture_output=True,
            text=True,
            timeout=5,
        )
        passed = result.returncode == 0  # Should exit 0 gracefully
        results.append(("SessionStart: malformed JSON", passed, 0, ""))
    except:
        results.append(("SessionStart: malformed JSON", False, 0, "Exception"))

    return results


def test_hook_user_prompt() -> List[Tuple[str, bool, float, str]]:
    """Test UserPromptSubmit hook"""
    results = []

    # Test 1: Normal prompt
    code, out, err, ms = run_hook(
        "hook_user_prompt.py", {"prompt": "Help me build a feature"}
    )
    passed = code == 0
    results.append(("UserPrompt: normal prompt", passed, ms, ""))

    # Test 2: Trivial prompt (should not inject)
    code, out, err, ms = run_hook("hook_user_prompt.py", {"prompt": "yes"})
    passed = code == 0 and "skill-todo-enforcement" not in out
    results.append(("UserPrompt: trivial prompt", passed, ms, ""))

    # Test 3: Skill invocation
    code, out, err, ms = run_hook(
        "hook_user_prompt.py", {"prompt": "/neel-study-test create paper"}
    )
    passed = code == 0 and "skill-todo-enforcement" in out
    results.append(
        (
            "UserPrompt: skill detection",
            passed,
            ms,
            "" if passed else "Skill not detected",
        )
    )

    # Test 4: Task indicator
    code, out, err, ms = run_hook(
        "hook_user_prompt.py", {"prompt": "implement the authentication system"}
    )
    passed = code == 0
    results.append(("UserPrompt: task indicator", passed, ms, ""))

    # Test 5: Empty prompt
    code, out, err, ms = run_hook("hook_user_prompt.py", {"prompt": ""})
    passed = code == 0
    results.append(("UserPrompt: empty prompt", passed, ms, ""))

    return results


def test_hook_post_todowrite() -> List[Tuple[str, bool, float, str]]:
    """Test PostToolUse[TodoWrite] hook"""
    results = []

    # Test 1: Valid TodoWrite
    input_data = {
        "tool_name": "TodoWrite",
        "tool_input": {
            "todos": [
                {"content": "Test task", "status": "pending", "activeForm": "Testing"}
            ]
        },
    }
    code, out, err, ms = run_hook("hook_post_todowrite.py", input_data)
    passed = code == 0
    results.append(("PostTodoWrite: valid todos", passed, ms, ""))

    # Test 2: Non-TodoWrite tool (should skip)
    code, out, err, ms = run_hook("hook_post_todowrite.py", {"tool_name": "Bash"})
    passed = code == 0
    results.append(("PostTodoWrite: non-TodoWrite skip", passed, ms, ""))

    # Test 3: Empty todos
    code, out, err, ms = run_hook(
        "hook_post_todowrite.py",
        {"tool_name": "TodoWrite", "tool_input": {"todos": []}},
    )
    passed = code == 0
    results.append(("PostTodoWrite: empty todos", passed, ms, ""))

    # Test 4: Invalid todo structure
    code, out, err, ms = run_hook(
        "hook_post_todowrite.py",
        {"tool_name": "TodoWrite", "tool_input": {"todos": [{"invalid": "structure"}]}},
    )
    passed = code == 0  # Should not crash, just filter invalid
    results.append(("PostTodoWrite: invalid structure", passed, ms, ""))

    return results


def test_hook_pre_compact() -> List[Tuple[str, bool, float, str]]:
    """Test PreCompact hook"""
    results = []

    # Test 1: Manual compact
    code, out, err, ms = run_hook("hook_pre_compact.py", {"trigger": "manual"})
    passed = code == 0
    results.append(("PreCompact: manual trigger", passed, ms, ""))

    # Test 2: Auto compact
    code, out, err, ms = run_hook("hook_pre_compact.py", {"trigger": "auto"})
    passed = code == 0
    results.append(("PreCompact: auto trigger", passed, ms, ""))

    # Test 3: Empty input
    code, out, err, ms = run_hook("hook_pre_compact.py", {})
    passed = code == 0
    results.append(("PreCompact: empty input", passed, ms, ""))

    return results


def test_hook_stop() -> List[Tuple[str, bool, float, str]]:
    """Test Stop hook"""
    results = []

    # First, set up a clean state
    run_hook(
        "hook_post_todowrite.py",
        {"tool_name": "TodoWrite", "tool_input": {"todos": []}},
    )

    # Test 1: No todos (should allow stop)
    code, out, err, ms = run_hook("hook_stop.py", {})
    passed = code == 0 and "block" not in out.lower()
    results.append(("Stop: no todos (allow)", passed, ms, ""))

    # Test 2: With in_progress todo (should block)
    run_hook(
        "hook_post_todowrite.py",
        {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {
                        "content": "In progress task",
                        "status": "in_progress",
                        "activeForm": "Working",
                    }
                ]
            },
        },
    )
    code, out, err, ms = run_hook("hook_stop.py", {})
    passed = code == 0 and "block" in out.lower()
    results.append(
        ("Stop: in_progress (block)", passed, ms, "" if passed else "Did not block")
    )

    # Test 3: With pending only (should allow)
    run_hook(
        "hook_post_todowrite.py",
        {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {
                        "content": "Pending task",
                        "status": "pending",
                        "activeForm": "Waiting",
                    }
                ]
            },
        },
    )
    code, out, err, ms = run_hook("hook_stop.py", {})
    passed = code == 0 and "block" not in out.lower()
    results.append(("Stop: pending only (allow)", passed, ms, ""))

    # Test 4: Loop prevention (stop_hook_active)
    run_hook(
        "hook_post_todowrite.py",
        {
            "tool_name": "TodoWrite",
            "tool_input": {
                "todos": [
                    {
                        "content": "Task",
                        "status": "in_progress",
                        "activeForm": "Working",
                    }
                ]
            },
        },
    )
    code, out, err, ms = run_hook("hook_stop.py", {"stop_hook_active": True})
    passed = code == 0 and "block" not in out.lower()
    results.append(
        (
            "Stop: loop prevention",
            passed,
            ms,
            "" if passed else "Loop prevention failed",
        )
    )

    # Cleanup
    run_hook(
        "hook_post_todowrite.py",
        {"tool_name": "TodoWrite", "tool_input": {"todos": []}},
    )

    return results


def test_performance_stress() -> List[Tuple[str, bool, float, str]]:
    """Stress test all hooks for performance"""
    results = []
    iterations = 10

    hooks = [
        ("hook_session_start.py", {"source": "resume"}),
        (
            "hook_user_prompt.py",
            {"prompt": "Build a complex feature with multiple steps"},
        ),
        (
            "hook_post_todowrite.py",
            {"tool_name": "TodoWrite", "tool_input": {"todos": []}},
        ),
        ("hook_pre_compact.py", {"trigger": "manual"}),
        ("hook_stop.py", {}),
    ]

    for hook_name, input_data in hooks:
        times = []
        for _ in range(iterations):
            _, _, _, ms = run_hook(hook_name, input_data)
            times.append(ms)

        avg_ms = sum(times) / len(times)
        max_ms = max(times)
        passed = avg_ms < PERFORMANCE_THRESHOLD_MS
        details = f"avg={avg_ms:.1f}ms, max={max_ms:.1f}ms"
        results.append((f"Perf: {hook_name}", passed, avg_ms, details))

    return results


def test_state_integrity() -> List[Tuple[str, bool, float, str]]:
    """Test state file integrity"""
    results = []

    # Create test todos
    test_todos = [
        {"content": "Task 1", "status": "pending", "activeForm": "Working 1"},
        {"content": "Task 2", "status": "in_progress", "activeForm": "Working 2"},
        {"content": "Task 3", "status": "completed", "activeForm": "Working 3"},
    ]

    run_hook(
        "hook_post_todowrite.py",
        {"tool_name": "TodoWrite", "tool_input": {"todos": test_todos}},
    )

    # Find the state file
    state_files = list(STATE_DIR.glob("todos_*.json"))
    if not state_files:
        results.append(("State: file creation", False, 0, "No state file found"))
        return results

    state_file = state_files[0]

    # Test 1: File exists
    passed = state_file.exists()
    results.append(("State: file exists", passed, 0, ""))

    # Test 2: Valid JSON
    try:
        with open(state_file) as f:
            state = json.load(f)
        passed = True
    except:
        passed = False
        state = {}
    results.append(("State: valid JSON", passed, 0, ""))

    # Test 3: Schema version
    passed = state.get("schema_version") == 1
    results.append(("State: schema version", passed, 0, ""))

    # Test 4: Todos preserved
    saved_todos = state.get("todos", [])
    passed = len(saved_todos) == len(test_todos)
    results.append(
        (
            "State: todos preserved",
            passed,
            0,
            f"Expected {len(test_todos)}, got {len(saved_todos)}",
        )
    )

    # Test 5: File permissions (secure)
    mode = oct(state_file.stat().st_mode)[-3:]
    passed = mode in ("600", "644", "640")
    results.append(("State: secure permissions", passed, 0, f"Mode: {mode}"))

    return results


def test_disk_usage() -> List[Tuple[str, bool, float, str]]:
    """Check disk usage is reasonable"""
    results = []

    # State directory size
    state_size = sum(f.stat().st_size for f in STATE_DIR.glob("*") if f.is_file())
    state_size_kb = state_size / 1024
    passed = state_size_kb < 1024  # Less than 1MB
    results.append(("Disk: state dir size", passed, 0, f"{state_size_kb:.1f}KB"))

    # Debug log size
    debug_log = STATE_DIR / "debug.log"
    if debug_log.exists():
        log_size_kb = debug_log.stat().st_size / 1024
        passed = log_size_kb < 5 * 1024  # Less than 5MB (rotation threshold)
        results.append(("Disk: debug log size", passed, 0, f"{log_size_kb:.1f}KB"))
    else:
        results.append(("Disk: debug log size", True, 0, "Not created yet"))

    # Number of state files
    state_count = len(list(STATE_DIR.glob("todos_*.json")))
    passed = state_count < 50  # Reasonable number
    results.append(("Disk: state file count", passed, 0, f"{state_count} files"))

    return results


def main():
    print_header("TODO HOOK SYSTEM - TEST SUITE")
    print(f"  Test started: {datetime.now().isoformat()}")
    print(f"  Hook directory: {HOOK_DIR}")
    print(f"  State directory: {STATE_DIR}")

    all_results = []

    # Run all test suites
    test_suites = [
        ("SessionStart Hook", test_hook_session_start),
        ("UserPrompt Hook", test_hook_user_prompt),
        ("PostTodoWrite Hook", test_hook_post_todowrite),
        ("PreCompact Hook", test_hook_pre_compact),
        ("Stop Hook", test_hook_stop),
        ("Performance Stress", test_performance_stress),
        ("State Integrity", test_state_integrity),
        ("Disk Usage", test_disk_usage),
    ]

    for suite_name, test_func in test_suites:
        print(f"\n{Colors.BOLD}[{suite_name}]{Colors.END}")
        try:
            results = test_func()
            all_results.extend(results)
            for name, passed, time_ms, details in results:
                print_test(name, passed, time_ms, details)
        except Exception as e:
            print(f"  {Colors.RED}Suite failed: {e}{Colors.END}")
            all_results.append((suite_name, False, 0, str(e)))

    # Summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, p, _, _ in all_results if p)
    total = len(all_results)
    failed = total - passed

    print(f"  {Colors.GREEN}Passed: {passed}{Colors.END}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.END}")
    print(f"  Total:  {total}")

    if failed > 0:
        print(f"\n{Colors.RED}FAILED TESTS:{Colors.END}")
        for name, p, _, details in all_results:
            if not p:
                print(f"  - {name}: {details}")

    # Performance summary
    perf_results = [(n, t) for n, p, t, _ in all_results if "Perf:" in n]
    if perf_results:
        total_avg = sum(t for _, t in perf_results)
        print(f"\n{Colors.BOLD}Performance Impact:{Colors.END}")
        print(f"  Total hook overhead per prompt: ~{total_avg:.0f}ms")
        print(f"  (SessionStart + UserPrompt + Stop = typical flow)")

    print(f"\n  Test completed: {datetime.now().isoformat()}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
