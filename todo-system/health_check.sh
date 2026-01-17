#!/bin/bash
#
# Todo Hook System - Quick Health Check
# ======================================
# Run: ~/.claude/hooks/todo-system/health_check.sh
#
# Quick checks:
# - All hook files exist and are executable
# - State directory is accessible
# - Debug log is not bloated
# - Recent hook activity in logs
#

set -e

HOOK_DIR="$HOME/.claude/hooks/todo-system"
STATE_DIR="$HOME/.claude/todo-state"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "           TODO HOOK SYSTEM - HEALTH CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check 1: Hook files exist and are executable
echo "📁 Hook Files:"
HOOKS=(
    "todo_core.py"
    "hook_session_start.py"
    "hook_user_prompt.py"
    "hook_post_todowrite.py"
    "hook_pre_compact.py"
    "hook_stop.py"
)

all_ok=true
for hook in "${HOOKS[@]}"; do
    if [[ -x "$HOOK_DIR/$hook" ]]; then
        echo -e "   ${GREEN}✓${NC} $hook"
    else
        echo -e "   ${RED}✗${NC} $hook (missing or not executable)"
        all_ok=false
    fi
done

# Check 2: State directory
echo ""
echo "💾 State Directory:"
if [[ -d "$STATE_DIR" ]]; then
    state_count=$(ls -1 "$STATE_DIR"/todos_*.json 2>/dev/null | wc -l | tr -d ' ')
    state_size=$(du -sh "$STATE_DIR" 2>/dev/null | cut -f1)
    echo -e "   ${GREEN}✓${NC} Exists: $STATE_DIR"
    echo "   📊 State files: $state_count"
    echo "   📊 Total size: $state_size"
else
    echo -e "   ${YELLOW}⚠${NC} Not created yet (will be created on first use)"
fi

# Check 3: Debug log
echo ""
echo "📋 Debug Log:"
DEBUG_LOG="$STATE_DIR/debug.log"
if [[ -f "$DEBUG_LOG" ]]; then
    log_size=$(du -h "$DEBUG_LOG" | cut -f1)
    log_lines=$(wc -l < "$DEBUG_LOG" | tr -d ' ')
    last_entry=$(tail -1 "$DEBUG_LOG" 2>/dev/null | cut -c1-50)
    echo "   📊 Size: $log_size ($log_lines lines)"
    echo "   📊 Last entry: $last_entry..."

    # Check if log is getting big
    log_bytes=$(stat -f%z "$DEBUG_LOG" 2>/dev/null || stat -c%s "$DEBUG_LOG" 2>/dev/null)
    if [[ $log_bytes -gt 5242880 ]]; then
        echo -e "   ${YELLOW}⚠${NC} Log is large (>5MB), will rotate soon"
    fi
else
    echo -e "   ${YELLOW}⚠${NC} Not created yet"
fi

# Check 4: Recent activity
echo ""
echo "⏰ Recent Activity (last 5 entries):"
if [[ -f "$DEBUG_LOG" ]]; then
    tail -5 "$DEBUG_LOG" | while read line; do
        echo "   $line"
    done
else
    echo "   No activity yet"
fi

# Check 5: Settings.json hooks configured
echo ""
echo "⚙️  Settings Configuration:"
SETTINGS="$HOME/.claude/settings.json"
if [[ -f "$SETTINGS" ]]; then
    hooks_configured=0
    for hook_type in "SessionStart" "UserPromptSubmit" "PostToolUse" "PreCompact" "Stop"; do
        if grep -q "todo-system/hook_" "$SETTINGS" 2>/dev/null; then
            hooks_configured=$((hooks_configured + 1))
        fi
    done
    if grep -q "todo-system" "$SETTINGS"; then
        echo -e "   ${GREEN}✓${NC} Todo hooks registered in settings.json"
    else
        echo -e "   ${RED}✗${NC} Todo hooks NOT found in settings.json"
        all_ok=false
    fi
else
    echo -e "   ${RED}✗${NC} Settings file not found"
    all_ok=false
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if $all_ok; then
    echo -e "   ${GREEN}✓ ALL CHECKS PASSED${NC}"
else
    echo -e "   ${RED}✗ SOME CHECKS FAILED${NC}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Run full test suite: python3 $HOOK_DIR/test_hooks.py"
