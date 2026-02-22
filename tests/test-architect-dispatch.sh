#!/usr/bin/env bash
# test-architect-dispatch.sh — Phase 2 dispatch integration tests for /architect skill.
#
# @decision DEC-ARCH-005
# @title TAP-compatible structure validation for Phase 2 artifacts
# @status accepted
# @rationale Tests validate file structure (templates, schemas, SKILL.md sections)
# rather than LLM behavior. Actual /deep-research dispatch requires API keys
# and is tested via e2e skill execution, not unit tests.
#
# Usage: bash test-architect-dispatch.sh
# Output: TAP format (1..4)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="$(cd "$SCRIPT_DIR/../skills/architect" && pwd)"

PASS=0
FAIL=0
TOTAL=4

echo "1..$TOTAL"

# --- Test 1: Research brief template has required PLACEHOLDER markers ---
TEMPLATE="$SKILL_DIR/templates/research-brief.md"
if [[ -f "$TEMPLATE" ]]; then
    missing=""
    for marker in "PLACEHOLDER: project-name" "PLACEHOLDER: content-type" "PLACEHOLDER: batch-nodes" "PLACEHOLDER: batch-relationships" "PLACEHOLDER: system-context"; do
        if ! grep -q "$marker" "$TEMPLATE"; then
            missing+=" $marker"
        fi
    done
    if [[ -z "$missing" ]]; then
        echo "ok 1 - research-brief.md has all required PLACEHOLDER markers"
        PASS=$((PASS + 1))
    else
        echo "not ok 1 - research-brief.md missing markers:$missing"
        FAIL=$((FAIL + 1))
    fi
else
    echo "not ok 1 - research-brief.md not found at $TEMPLATE"
    FAIL=$((FAIL + 1))
fi

# --- Test 2: Analytics contract schema is valid JSON with 3 analysis types ---
SCHEMA="$SKILL_DIR/schema/analytics-input-schema.json"
if [[ -f "$SCHEMA" ]]; then
    if command -v jq > /dev/null 2>&1; then
        # Validate it's parseable JSON
        if jq empty "$SCHEMA" 2>/dev/null; then
            # Check for 3 analysis type enums
            type_count=$(jq -r '.properties.requested_analyses.items.properties.type.enum | length' "$SCHEMA" 2>/dev/null || echo 0)
            if [[ "$type_count" -eq 3 ]]; then
                echo "ok 2 - analytics-input-schema.json is valid JSON with 3 analysis types"
                PASS=$((PASS + 1))
            else
                echo "not ok 2 - analytics-input-schema.json has $type_count analysis types (expected 3)"
                FAIL=$((FAIL + 1))
            fi
        else
            echo "not ok 2 - analytics-input-schema.json is not valid JSON"
            FAIL=$((FAIL + 1))
        fi
    else
        # No jq — just check it's valid JSON via python
        if python3 -c "import json; json.load(open('$SCHEMA'))" 2>/dev/null; then
            echo "ok 2 - analytics-input-schema.json is valid JSON (jq not available for deep check)"
            PASS=$((PASS + 1))
        else
            echo "not ok 2 - analytics-input-schema.json is not valid JSON"
            FAIL=$((FAIL + 1))
        fi
    fi
else
    echo "not ok 2 - analytics-input-schema.json not found at $SCHEMA"
    FAIL=$((FAIL + 1))
fi

# --- Test 3: SKILL.md Phase 2 section has --research and --analytics handling ---
SKILLMD="$SKILL_DIR/SKILL.md"
if [[ -f "$SKILLMD" ]]; then
    has_research=$(grep -c "\-\-research" "$SKILLMD" 2>/dev/null || echo 0)
    has_analytics=$(grep -c "\-\-analytics" "$SKILLMD" 2>/dev/null || echo 0)
    has_batch=$(grep -ci "batch" "$SKILLMD" 2>/dev/null || echo 0)
    has_improvements=$(grep -c "improvements.md" "$SKILLMD" 2>/dev/null || echo 0)
    has_analytics_contract=$(grep -c "analytics-contract.json" "$SKILLMD" 2>/dev/null || echo 0)

    issues=""
    [[ "$has_research" -lt 3 ]] && issues+=" --research mentions ($has_research < 3)"
    [[ "$has_analytics" -lt 2 ]] && issues+=" --analytics mentions ($has_analytics < 2)"
    [[ "$has_batch" -lt 2 ]] && issues+=" batch mentions ($has_batch < 2)"
    [[ "$has_improvements" -lt 2 ]] && issues+=" improvements.md mentions ($has_improvements < 2)"
    [[ "$has_analytics_contract" -lt 1 ]] && issues+=" analytics-contract.json mentions ($has_analytics_contract < 1)"

    if [[ -z "$issues" ]]; then
        echo "ok 3 - SKILL.md Phase 2 has --research and --analytics handling"
        PASS=$((PASS + 1))
    else
        echo "not ok 3 - SKILL.md Phase 2 insufficient coverage:$issues"
        FAIL=$((FAIL + 1))
    fi
else
    echo "not ok 3 - SKILL.md not found at $SKILLMD"
    FAIL=$((FAIL + 1))
fi

# --- Test 4: Manifest schema supports fields Phase 2 reads ---
MANIFEST_SCHEMA="$SKILL_DIR/schema/manifest-schema.json"
if [[ -f "$MANIFEST_SCHEMA" ]]; then
    if command -v jq > /dev/null 2>&1; then
        has_nodes=$(jq '(.properties | has("nodes"))' "$MANIFEST_SCHEMA" 2>/dev/null || echo false)
        has_edges=$(jq '.properties.nodes.items.properties | has("edges")' "$MANIFEST_SCHEMA" 2>/dev/null || echo false)
        has_diagrams=$(jq '.properties | has("diagrams")' "$MANIFEST_SCHEMA" 2>/dev/null || echo false)
        has_detect_info=$(jq '.properties | has("detect_info")' "$MANIFEST_SCHEMA" 2>/dev/null || echo false)

        issues=""
        [[ "$has_nodes" != "true" ]] && issues+=" nodes"
        [[ "$has_edges" != "true" ]] && issues+=" edges"
        [[ "$has_diagrams" != "true" ]] && issues+=" diagrams"
        [[ "$has_detect_info" != "true" ]] && issues+=" detect_info"

        if [[ -z "$issues" ]]; then
            echo "ok 4 - manifest-schema.json has all Phase 2 required fields (nodes, edges, diagrams, detect_info)"
            PASS=$((PASS + 1))
        else
            echo "not ok 4 - manifest-schema.json missing fields:$issues"
            FAIL=$((FAIL + 1))
        fi
    else
        # No jq — just check keywords exist
        missing=""
        for field in '"nodes"' '"edges"' '"diagrams"' '"detect_info"'; do
            if ! grep -q "$field" "$MANIFEST_SCHEMA"; then
                missing+=" $field"
            fi
        done
        if [[ -z "$missing" ]]; then
            echo "ok 4 - manifest-schema.json contains Phase 2 required field names"
            PASS=$((PASS + 1))
        else
            echo "not ok 4 - manifest-schema.json missing field names:$missing"
            FAIL=$((FAIL + 1))
        fi
    fi
else
    echo "not ok 4 - manifest-schema.json not found at $MANIFEST_SCHEMA"
    FAIL=$((FAIL + 1))
fi

# --- Summary ---
echo ""
echo "# Phase 2 dispatch tests: $PASS/$TOTAL passed, $FAIL failed"

if [[ "$FAIL" -gt 0 ]]; then
    exit 1
fi
