#!/usr/bin/env bash
# test-proof-status-scoping.sh — Tests for proof-status scoping bug fixes
#
# Validates three bug fixes:
#   1. post-write.sh invalidation uses write_proof_status() (all three paths updated)
#   2. prompt-submit.sh empty-prompt path uses scoped proof file with legacy fallback
#   3. Test file edits (paths matching is_test_file()) don't invalidate proof status
#
# Root cause: post-write.sh line 118 used single-file echo instead of write_proof_status().
# This caused deadlock: source edit reset scoped file but left legacy at "verified".
#
# @decision DEC-PROOF-SCOPE-003
# @title Test suite for proof-status scoping bug fixes
# @status accepted
# @rationale The three-path invariant (scoped + legacy + worktree must agree) was
#   broken by post-write.sh's single-file invalidation. Centralizing invalidation
#   via write_proof_status() ensures atomicity. These tests enforce the invariant
#   and document the expected behavior for future implementers.
#
# Usage: bash tests/test-proof-status-scoping.sh
# Returns: 0 if all tests pass, 1 if any fail

set -euo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$TEST_DIR/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/hooks"

mkdir -p "$PROJECT_ROOT/tmp"

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    TESTS_RUN=$((TESTS_RUN + 1))
    echo "Running: $test_name"
}

pass_test() {
    TESTS_PASSED=$((TESTS_PASSED + 1))
    echo "  PASS"
}

fail_test() {
    local reason="$1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    echo "  FAIL: $reason"
}

# ─────────────────────────────────────────────────────────────────────────────
# Part A: Syntax validation
# ─────────────────────────────────────────────────────────────────────────────

run_test "Syntax: post-write.sh is valid bash"
if bash -n "$HOOKS_DIR/post-write.sh"; then
    pass_test
else
    fail_test "post-write.sh has syntax errors"
fi

run_test "Syntax: prompt-submit.sh is valid bash"
if bash -n "$HOOKS_DIR/prompt-submit.sh"; then
    pass_test
else
    fail_test "prompt-submit.sh has syntax errors"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Part B: write_proof_status() three-path invariant
# Verifies that write_proof_status writes scoped, legacy, and resolved paths
# ─────────────────────────────────────────────────────────────────────────────

run_test "write_proof_status: writes all three paths (scoped, legacy, and resolved)"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-wps-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"

RESULT=$(bash -c "
    source '$HOOKS_DIR/log.sh'
    export CLAUDE_DIR='$TEMP_PROJ/.claude'
    export PROJECT_ROOT='$TEMP_PROJ'
    write_proof_status 'pending' '$TEMP_PROJ'
    PHASH=\$(project_hash '$TEMP_PROJ')
    echo \"scoped=\$PHASH\"
" 2>/dev/null)

PHASH=$(echo "$RESULT" | grep "^scoped=" | cut -d= -f2)
SCOPED_FILE="$TEMP_PROJ/.claude/.proof-status-${PHASH}"
LEGACY_FILE="$TEMP_PROJ/.claude/.proof-status"

SCOPED_OK=false
LEGACY_OK=false
[[ -f "$SCOPED_FILE" ]] && [[ "$(cut -d'|' -f1 "$SCOPED_FILE")" == "pending" ]] && SCOPED_OK=true
[[ -f "$LEGACY_FILE" ]] && [[ "$(cut -d'|' -f1 "$LEGACY_FILE")" == "pending" ]] && LEGACY_OK=true

if [[ "$SCOPED_OK" == "true" && "$LEGACY_OK" == "true" ]]; then
    pass_test
else
    fail_test "write_proof_status missing paths: scoped=$SCOPED_OK legacy=$LEGACY_OK (phash='$PHASH')"
fi
rm -rf "$TEMP_PROJ"

# ─────────────────────────────────────────────────────────────────────────────
# Part C: post-write.sh invalidation writes all three paths
# Simulates a source file edit with verified proof status and checks all paths
# ─────────────────────────────────────────────────────────────────────────────

run_test "post-write.sh: source file invalidation resets all three paths"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-pw-inv-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"

# Get the project hash for this temp project
PHASH=$(bash -c "
    source '$HOOKS_DIR/log.sh'
    project_hash '$TEMP_PROJ'
" 2>/dev/null)
SCOPED_FILE="$TEMP_PROJ/.claude/.proof-status-${PHASH}"
LEGACY_FILE="$TEMP_PROJ/.claude/.proof-status"

# Write verified to all paths (as write_proof_status would)
echo "verified|12345" > "$SCOPED_FILE"
echo "verified|12345" > "$LEGACY_FILE"

# Create a real source file to edit
FAKE_SH="$TEMP_PROJ/myapp.sh"
echo "#!/bin/bash" > "$FAKE_SH"
echo "echo hello" >> "$FAKE_SH"

# Invoke post-write.sh with this source file
INPUT_JSON=$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$FAKE_SH")
(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    CLAUDE_SESSION_ID="test-scoping-$$" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/post-write.sh" > /dev/null 2>&1) || true

SCOPED_STATUS=$(cut -d'|' -f1 "$SCOPED_FILE" 2>/dev/null || echo "missing")
LEGACY_STATUS=$(cut -d'|' -f1 "$LEGACY_FILE" 2>/dev/null || echo "missing")

if [[ "$SCOPED_STATUS" == "pending" && "$LEGACY_STATUS" == "pending" ]]; then
    pass_test
else
    fail_test "Invalidation incomplete: scoped=$SCOPED_STATUS legacy=$LEGACY_STATUS (should both be 'pending')"
fi
rm -rf "$TEMP_PROJ"

# ─────────────────────────────────────────────────────────────────────────────
# Part D: post-write.sh test file exclusion via is_test_file()
# ─────────────────────────────────────────────────────────────────────────────

run_test "post-write.sh: test file in /tests/ dir does NOT invalidate proof"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-pw-excl-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"
mkdir -p "$TEMP_PROJ/tests"

# Get the project hash
PHASH=$(bash -c "
    source '$HOOKS_DIR/log.sh'
    project_hash '$TEMP_PROJ'
" 2>/dev/null)
SCOPED_FILE="$TEMP_PROJ/.claude/.proof-status-${PHASH}"
LEGACY_FILE="$TEMP_PROJ/.claude/.proof-status"

# Set proof to verified
echo "verified|12345" > "$SCOPED_FILE"
echo "verified|12345" > "$LEGACY_FILE"

# Create a test file in /tests/ directory
TEST_FILE="$TEMP_PROJ/tests/test-myfeature.sh"
echo "#!/bin/bash" > "$TEST_FILE"
echo "echo 'test'" >> "$TEST_FILE"

# Invoke post-write.sh with the test file
INPUT_JSON=$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$TEST_FILE")
(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    CLAUDE_SESSION_ID="test-scoping-$$" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/post-write.sh" > /dev/null 2>&1) || true

SCOPED_STATUS=$(cut -d'|' -f1 "$SCOPED_FILE" 2>/dev/null || echo "missing")
LEGACY_STATUS=$(cut -d'|' -f1 "$LEGACY_FILE" 2>/dev/null || echo "missing")

if [[ "$SCOPED_STATUS" == "verified" && "$LEGACY_STATUS" == "verified" ]]; then
    pass_test
else
    fail_test "Test file in /tests/ triggered proof invalidation: scoped=$SCOPED_STATUS legacy=$LEGACY_STATUS"
fi
rm -rf "$TEMP_PROJ"

run_test "post-write.sh: .test. file pattern does NOT invalidate proof"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-pw-excl2-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"

PHASH=$(bash -c "
    source '$HOOKS_DIR/log.sh'
    project_hash '$TEMP_PROJ'
" 2>/dev/null)
SCOPED_FILE="$TEMP_PROJ/.claude/.proof-status-${PHASH}"
LEGACY_FILE="$TEMP_PROJ/.claude/.proof-status"

echo "verified|12345" > "$SCOPED_FILE"
echo "verified|12345" > "$LEGACY_FILE"

TEST_FILE="$TEMP_PROJ/myapp.test.sh"
echo "#!/bin/bash" > "$TEST_FILE"

INPUT_JSON=$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$TEST_FILE")
(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    CLAUDE_SESSION_ID="test-scoping-$$" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/post-write.sh" > /dev/null 2>&1) || true

SCOPED_STATUS=$(cut -d'|' -f1 "$SCOPED_FILE" 2>/dev/null || echo "missing")
LEGACY_STATUS=$(cut -d'|' -f1 "$LEGACY_FILE" 2>/dev/null || echo "missing")

if [[ "$SCOPED_STATUS" == "verified" && "$LEGACY_STATUS" == "verified" ]]; then
    pass_test
else
    fail_test ".test. file triggered proof invalidation: scoped=$SCOPED_STATUS legacy=$LEGACY_STATUS"
fi
rm -rf "$TEMP_PROJ"

# ─────────────────────────────────────────────────────────────────────────────
# Part E: is_test_file() unit tests via core-lib.sh
# ─────────────────────────────────────────────────────────────────────────────

call_is_test_file() {
    local path="$1"
    bash -c "
        source '$HOOKS_DIR/log.sh'
        source '$HOOKS_DIR/context-lib.sh'
        is_test_file '$path' && echo 'test' || echo 'source'
    " 2>/dev/null
}

run_test "is_test_file: /tests/test-foo.sh is a test file"
RESULT=$(call_is_test_file "/project/tests/test-foo.sh")
if [[ "$RESULT" == "test" ]]; then
    pass_test
else
    fail_test "Expected 'test', got '$RESULT'"
fi

run_test "is_test_file: /test/foo.sh is a test file"
RESULT=$(call_is_test_file "/project/test/foo.sh")
if [[ "$RESULT" == "test" ]]; then
    pass_test
else
    fail_test "Expected 'test', got '$RESULT'"
fi

run_test "is_test_file: foo.test.ts is a test file"
RESULT=$(call_is_test_file "/project/src/foo.test.ts")
if [[ "$RESULT" == "test" ]]; then
    pass_test
else
    fail_test "Expected 'test', got '$RESULT'"
fi

run_test "is_test_file: hooks/post-write.sh is NOT a test file"
RESULT=$(call_is_test_file "/project/hooks/post-write.sh")
if [[ "$RESULT" == "source" ]]; then
    pass_test
else
    fail_test "Expected 'source', got '$RESULT'"
fi

run_test "is_test_file: src/main.py is NOT a test file"
RESULT=$(call_is_test_file "/project/src/main.py")
if [[ "$RESULT" == "source" ]]; then
    pass_test
else
    fail_test "Expected 'source', got '$RESULT'"
fi

# ─────────────────────────────────────────────────────────────────────────────
# Part F: prompt-submit.sh empty-prompt scoped proof file lookup
# ─────────────────────────────────────────────────────────────────────────────

run_test "prompt-submit.sh: empty prompt finds scoped proof file and shows approval hint"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-ps-scope-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"

# Get the project hash to know which scoped file to write
PHASH=$(bash -c "
    source '$HOOKS_DIR/log.sh'
    cd '$TEMP_PROJ'
    project_hash '$TEMP_PROJ'
" 2>/dev/null)
SCOPED_FILE="$TEMP_PROJ/.claude/.proof-status-${PHASH}"

# Write ONLY the scoped file (no legacy) in pending state
echo "pending|12345" > "$SCOPED_FILE"
# Confirm legacy does NOT exist
rm -f "$TEMP_PROJ/.claude/.proof-status"

# Send empty prompt
INPUT_JSON='{"hook_event_name":"UserPromptSubmit","prompt":""}'
OUTPUT=$(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/prompt-submit.sh" 2>/dev/null || true)

# Should inject hint about approval keywords (not the generic enter-as-approval message)
if echo "$OUTPUT" | grep -qi "approval\|approved\|keyword\|gate"; then
    pass_test
else
    fail_test "Expected approval-keyword hint in output when scoped proof is pending. Got: $OUTPUT"
fi
rm -rf "$TEMP_PROJ"

run_test "prompt-submit.sh: empty prompt falls back to legacy .proof-status when scoped missing"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-ps-legacy-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"

# Write ONLY the legacy file in pending state (no scoped file)
echo "pending|12345" > "$TEMP_PROJ/.claude/.proof-status"

INPUT_JSON='{"hook_event_name":"UserPromptSubmit","prompt":""}'
OUTPUT=$(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/prompt-submit.sh" 2>/dev/null || true)

# Should still show approval hint (legacy fallback works)
if echo "$OUTPUT" | grep -qi "approval\|approved\|keyword\|gate"; then
    pass_test
else
    fail_test "Expected approval-keyword hint via legacy fallback. Got: $OUTPUT"
fi
rm -rf "$TEMP_PROJ"

run_test "prompt-submit.sh: empty prompt with no proof file shows generic continue hint"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-ps-noproof-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"
# No proof file at all

INPUT_JSON='{"hook_event_name":"UserPromptSubmit","prompt":""}'
OUTPUT=$(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/prompt-submit.sh" 2>/dev/null || true)

# Should show generic continue hint, not an error
if echo "$OUTPUT" | grep -qi "approval\|continuation\|enter"; then
    pass_test
else
    fail_test "Expected continue hint in output. Got: $OUTPUT"
fi
rm -rf "$TEMP_PROJ"

# ─────────────────────────────────────────────────────────────────────────────
# Part G: Regression — verified source files still invalidate proof status
# ─────────────────────────────────────────────────────────────────────────────

run_test "post-write.sh: non-test .sh source file DOES invalidate verified proof"
TEMP_PROJ=$(mktemp -d "$PROJECT_ROOT/tmp/test-pw-reg-XXXXXX")
git -C "$TEMP_PROJ" init > /dev/null 2>&1
mkdir -p "$TEMP_PROJ/.claude"
mkdir -p "$TEMP_PROJ/hooks"

PHASH=$(bash -c "
    source '$HOOKS_DIR/log.sh'
    project_hash '$TEMP_PROJ'
" 2>/dev/null)
SCOPED_FILE="$TEMP_PROJ/.claude/.proof-status-${PHASH}"
LEGACY_FILE="$TEMP_PROJ/.claude/.proof-status"

echo "verified|12345" > "$SCOPED_FILE"
echo "verified|12345" > "$LEGACY_FILE"

SOURCE_FILE="$TEMP_PROJ/hooks/my-hook.sh"
echo "#!/bin/bash" > "$SOURCE_FILE"

INPUT_JSON=$(printf '{"tool_name":"Write","tool_input":{"file_path":"%s"}}' "$SOURCE_FILE")
(cd "$TEMP_PROJ" && \
    CLAUDE_PROJECT_DIR="$TEMP_PROJ" \
    CLAUDE_SESSION_ID="test-scoping-$$" \
    printf '%s' "$INPUT_JSON" | bash "$HOOKS_DIR/post-write.sh" > /dev/null 2>&1) || true

SCOPED_STATUS=$(cut -d'|' -f1 "$SCOPED_FILE" 2>/dev/null || echo "missing")
LEGACY_STATUS=$(cut -d'|' -f1 "$LEGACY_FILE" 2>/dev/null || echo "missing")

if [[ "$SCOPED_STATUS" == "pending" && "$LEGACY_STATUS" == "pending" ]]; then
    pass_test
else
    fail_test "Expected both paths to be 'pending' after source edit: scoped=$SCOPED_STATUS legacy=$LEGACY_STATUS"
fi
rm -rf "$TEMP_PROJ"

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo "=========================================="
echo "Test Results: $TESTS_PASSED/$TESTS_RUN passed"
echo "=========================================="

if [[ $TESTS_FAILED -gt 0 ]]; then
    echo "FAILED: $TESTS_FAILED tests failed"
    exit 1
else
    echo "SUCCESS: All tests passed"
    exit 0
fi
