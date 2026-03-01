# MASTER_PLAN: claude-config-pro

## Identity

**Type:** meta-infrastructure
**Languages:** Bash (85%), Markdown (10%), Python (3%), JSON (2%)
**Root:** /Users/turla/.claude
**Created:** 2026-03-01
**Last updated:** 2026-03-01

The Claude Code configuration directory. It shapes how Claude Code operates across all projects via hooks, agents, skills, and instructions. Managed as a git repository (juanandresgs/claude-config-pro). The hook system enforces governance (git safety, documentation, proof gates, worktree discipline) while the agent system dispatches specialized roles (planner, implementer, tester, guardian) for all project work.

## Architecture

    agents/        — Agent instruction files (planner, implementer, tester, guardian)
    hooks/         — Hook entry points (4) + domain libraries (6) — the governance engine
    hooks/*-lib.sh — Domain libraries: core, trace, plan, doc, session, source, git, ci
    scripts/       — Utility scripts (batch-fetch, ci-watch, worktree-roster, statusline)
    skills/        — Research and workflow skills (deep-research, observatory, decide, prd)
    commands/      — Lightweight slash commands (compact, backlog, todos)
    tests/         — Test suite (131 tests via run-hooks.sh + specialized test files)
    templates/     — Document templates for plans and initiatives
    observatory/   — Self-improving flywheel: trace analysis, signal surfacing

## Original Intent

> Build a configuration layer for Claude Code that enforces engineering discipline — git safety, documentation, proof-before-commit, worktree isolation — across all projects. The system should be self-governing: hooks enforce rules mechanically, agents handle specialized roles, and the observatory learns from traces to improve over time.

## Principles

1. **Mechanical Enforcement** — Rules are enforced by hooks, not by convention. If a behavior matters, a hook gates it.
2. **Main is Sacred** — Feature work happens in worktrees. Main only receives tested, reviewed, approved merges.
3. **Proof Before Commit** — Every implementation must be verified by the tester agent before Guardian can commit. The proof chain is: implement -> test -> verify -> commit.
4. **Ephemeral Agents, Persistent Plans** — Agents are disposable; MASTER_PLAN.md and traces persist. Every agent must leave enough context for the next one to succeed.
5. **Fail Loudly** — Silent failures are the enemy. Hooks deny rather than silently allow. Tests assert rather than skip. Traces classify rather than ignore.

---

## Decision Log

| Date | DEC-ID | Initiative | Decision | Rationale |
|------|--------|-----------|----------|-----------|
| 2026-03-01 | DEC-HOOKS-001 | metanoia-remediation | Fix shellcheck violations inline (not suppress) | Real fixes are safer than disable annotations; violations indicate real fragility |
| 2026-03-01 | DEC-TRACE-002 | metanoia-remediation | Agent-type-aware outcome classification via lookup table | Different agents have different success signals; lookup table is extensible |
| 2026-03-01 | DEC-TRACE-003 | metanoia-remediation | Write compliance.json at trace init, update at finalize | Prevents write-before-read race when agents crash early |
| 2026-03-01 | DEC-PLAN-004 | metanoia-remediation | Reduce planner.md by extracting templates | 641 lines / 31KB consumes excessive context; target ~400 lines / ~20KB |
| 2026-03-01 | DEC-STATE-005 | metanoia-remediation | Registry-based state file cleanup | Orphaned state files accumulate; registry + cleanup script prevents drift |
| 2026-03-01 | DEC-TEST-006 | metanoia-remediation | Validation harness follows existing run-hooks.sh pattern | Consistency with 131-test suite; no new framework needed |

---

## Active Initiatives

### Initiative: Production Remediation (Metanoia Suite)
**Status:** active
**Started:** 2026-02-28
**Goal:** Fix defects left by the metanoia hook consolidation across test suite, trace system, and planner reliability.

> The metanoia initiative consolidated ~17 individual hooks into 4 entry points + 6 domain libraries. It shipped but left defects in three areas: shellcheck violations preventing true CI green, trace classification that is not agent-type-aware, and planner reliability issues (silent returns, excessive context consumption). This remediation plan fixes them in 5 phases.

**Dominant Constraint:** reliability

#### Goals
- REQ-GOAL-001: CI green with zero shellcheck violations (excluding SC1091 source-follows)
- REQ-GOAL-002: Trace classification accurately distinguishes success, failure, timeout, skipped, and crashed per agent type
- REQ-GOAL-003: Planner dispatch success rate above 50% (currently estimated ~30-40%)
- REQ-GOAL-004: Zero orphaned state files after worktree cleanup
- REQ-GOAL-005: Automated regression detection for trace classification

#### Non-Goals
- REQ-NOGO-001: Rewriting the hook consolidation — metanoia architecture is stable, we fix defects only
- REQ-NOGO-002: New hook features — no new governance rules until remediation is complete
- REQ-NOGO-003: Observatory improvements — observatory signals are downstream of trace accuracy; fix traces first
- REQ-NOGO-004: Performance optimization — hooks are fast enough; correctness is the priority

#### Requirements

**Must-Have (P0)**

- REQ-P0-001: Fix 7 shellcheck violations across check-guardian.sh, check-implementer.sh, post-write.sh, subagent-start.sh, trace-lib.sh
  Acceptance: `shellcheck` on these 5 files produces 0 warnings/errors (excluding SC1091)

- REQ-P0-002: Agent-type-aware outcome classification in trace-lib.sh finalize_trace (lines 347-359)
  Acceptance: Given a planner trace with summary.md written, When finalize_trace runs, Then outcome is "success" (not "partial"). Given an implementer trace with tests passing, When finalize_trace runs, Then outcome is "success".

- REQ-P0-003: Fix write-before-read race for compliance.json in check-guardian.sh, check-implementer.sh, check-tester.sh
  Acceptance: Given an agent that crashes before compliance.json is written, When check-*.sh reads compliance.json, Then it finds a valid skeleton (not file-not-found)

- REQ-P0-004: Universal PostToolUse:Task fallback in post-task.sh for when subagent_type is missing
  Acceptance: Given a Task completion without subagent_type in stdin, When post-task.sh fires, Then it infers agent type from recent traces and proceeds normally

- REQ-P0-005: Reduce planner.md from 641 lines to ~400 lines without losing instruction content
  Acceptance: `wc -l agents/planner.md` < 450. Planner agent produces valid MASTER_PLAN.md.

- REQ-P0-006: Increase planner max_turns from 40 to 65 in settings.json or CLAUDE.md
  Acceptance: Planner dispatch uses max_turns=65.

- REQ-P0-007: Stale trace repair script scripts/repair-traces.sh
  Acceptance: Given traces missing manifest.json or with status "unknown", When repair-traces.sh runs, Then manifests are reconstructed and statuses are corrected

- REQ-P0-008: Remove stale .active-worktree-path-* breadcrumbs after worktree cleanup
  Acceptance: After `git worktree remove`, no orphaned breadcrumb files remain in .claude/

- REQ-P0-009: Fix proof-gate path mismatch (resolve_proof_file follows breadcrumb to deleted worktree)
  Acceptance: Given a worktree that has been removed, When resolve_proof_file runs, Then it falls back to main proof-status (not ENOENT)

**Nice-to-Have (P1)**

- REQ-P1-001: New test file tests/test-trace-classification.sh covering agent-type-aware classification
  Acceptance: At least 10 test cases covering success/failure/timeout/skipped/crashed for planner, implementer, tester, guardian

- REQ-P1-002: Trace classification accuracy metrics (% correct vs expected)
  Acceptance: repair-traces.sh --report outputs accuracy percentage

**Future Consideration (P2)**

- REQ-P2-001: End-to-end validation harness that runs full agent dispatch cycles in a sandbox
- REQ-P2-002: Automated regression detection integrated with CI

#### Definition of Done

All 5 phases merged to main. `bash tests/run-hooks.sh` passes with 0 failures. `shellcheck` clean on all hook files. Trace classification tested and accurate. Planner dispatches succeed at >50% rate. No orphaned state files.

#### Architectural Decisions

- DEC-HOOKS-001: Fix shellcheck violations inline rather than suppressing
  Addresses: REQ-P0-001.
  Rationale: Real fixes (parameter expansion, glob patterns, redirect consolidation) are safer than `# shellcheck disable` annotations. The violations indicate real fragility (ls iteration, competing redirections).

- DEC-TRACE-002: Agent-type-aware outcome classification via lookup table in finalize_trace
  Addresses: REQ-P0-002.
  Rationale: Different agent types have different success signals. Planner success = plan file written. Implementer success = tests pass. Tester success = verification report generated. A lookup table in trace-lib.sh is extensible without conditional sprawl.

- DEC-TRACE-003: Write compliance.json at trace init, update at finalize
  Addresses: REQ-P0-003.
  Rationale: Current write-before-read race occurs when check-*.sh reads compliance.json before it exists (agent crashes early). Writing a skeleton at init_trace() and updating at finalize_trace() ensures the file always exists.

- DEC-PLAN-004: Reduce planner.md by extracting templates to separate files
  Addresses: REQ-P0-005.
  Rationale: At 641 lines / 31KB, planner.md consumes excessive agent context. Templates (MASTER_PLAN structure, initiative block format) can move to templates/ and be referenced by path. Target: ~400 lines / ~20KB.

- DEC-STATE-005: Registry-based state file cleanup
  Addresses: REQ-P0-008, REQ-P0-009.
  Rationale: Orphaned .active-worktree-path-* and .proof-status-* files accumulate because no registry tracks them. The worktree-roster.sh already tracks worktrees; extend it to clean associated state files on removal.

- DEC-TEST-006: Validation harness follows existing run-hooks.sh pattern
  Addresses: REQ-P0-007, REQ-P1-001.
  Rationale: Consistency with existing 131-test suite. New test files follow the same pass/fail/skip framework. No new test framework needed.

#### Phase 1: CI Green
**Status:** completed
**Decision IDs:** (pre-plan)
**Requirements:** REQ-P0-001 (partial — test migration done, shellcheck deferred to Phase 2)
**Issues:** (completed pre-plan)
**Definition of Done:**
- Test suite migrated to consolidated hook entry points
- 131 tests, 0 failures, 3 skips
- Merged as 919a2f0

##### Decision Log
- 2026-02-28: Migrated test suite to consolidated hooks. Fixed merge-base regex false positive in pre-bash.sh. Fixed doc-gate plan-check isolation. 7 shellcheck violations deferred to Phase 2.

#### Phase 2: Trace Reliability
**Status:** planned
**Decision IDs:** DEC-HOOKS-001, DEC-TRACE-002, DEC-TRACE-003
**Requirements:** REQ-P0-001, REQ-P0-002, REQ-P0-003, REQ-P0-004, REQ-P0-007, REQ-P1-001
**Issues:** #39
**Definition of Done:**
- REQ-P0-001 satisfied: `shellcheck` clean on 5 target files (excluding SC1091)
- REQ-P0-002 satisfied: finalize_trace uses agent-type-aware classification
- REQ-P0-003 satisfied: compliance.json written at trace init
- REQ-P0-004 satisfied: post-task.sh infers agent type when subagent_type missing
- REQ-P0-007 satisfied: repair-traces.sh reconstructs broken manifests
- REQ-P1-001 satisfied: test-trace-classification.sh has 10+ test cases

##### Planned Decisions
- DEC-HOOKS-001: Fix shellcheck violations inline — real fixes safer than suppression — Addresses: REQ-P0-001
- DEC-TRACE-002: Agent-type-aware classification lookup table — extensible without conditional sprawl — Addresses: REQ-P0-002
- DEC-TRACE-003: Write compliance.json skeleton at init_trace() — prevents write-before-read race — Addresses: REQ-P0-003

##### Work Items

**W2-0: Fix 7 shellcheck violations**
- check-guardian.sh:175 — replace `echo | sed` with `${var//pattern/}` (SC2001)
- check-implementer.sh:283 — verify TEST_RESULT assignment or rename (SC2153)
- post-write.sh:41 — remove or use HOOK_INPUT (SC2034)
- post-write.sh:189 — replace `echo | sed` with parameter expansion (SC2001)
- subagent-start.sh:19 — remove or use HOOK_INPUT (SC2034)
- subagent-start.sh:172 — replace `for x in $(ls ...)` with glob (SC2045)
- subagent-start.sh:222-223 — consolidate competing stderr redirections (SC2261)
- trace-lib.sh:229 — replace `for x in $(ls ...)` with glob (SC2045)
- trace-lib.sh:623 — remove or use prev_epoch (SC2034)

**W2-1: Agent-type-aware outcome classification**
- trace-lib.sh lines 347-359: Add lookup table mapping agent_type to success criteria
- Planner: success if summary.md or MASTER_PLAN.md artifact exists
- Implementer: success if test_result == "pass"
- Tester: success if verification report artifact exists
- Guardian: success if commit SHA recorded

**W2-2: compliance.json write-before-read fix**
- trace-lib.sh init_trace(): write skeleton compliance.json with status "in-progress"
- check-implementer.sh:154-187: update existing compliance.json instead of creating
- check-guardian.sh, check-tester.sh: same pattern

**W2-3: Universal PostToolUse:Task fallback**
- post-task.sh: when subagent_type is absent in stdin, scan recent traces (ls -t) to infer agent type
- Fallback order: check .last-tester-trace, check active markers, check trace timestamps

**W2-4: Stale trace repair script**
- New file: scripts/repair-traces.sh
- Scan traces/ for missing manifest.json, reconstruct from directory contents
- Fix traces with status "unknown" by re-running classification logic
- --report flag for accuracy metrics (REQ-P1-002)

**W2-5: Trace classification test file**
- New file: tests/test-trace-classification.sh
- 10+ test cases: success/failure/timeout/skipped/crashed x agent types
- Follows run-hooks.sh pass/fail/skip pattern

##### Critical Files
- `hooks/trace-lib.sh` — finalize_trace outcome classification (lines 347-359), init_trace
- `hooks/post-task.sh` — PostToolUse:Task handler, agent type inference
- `hooks/check-guardian.sh` — compliance.json read, shellcheck fix at line 175
- `hooks/check-implementer.sh` — compliance.json write (lines 154-187), shellcheck fix at line 283
- `hooks/subagent-start.sh` — shellcheck fixes at lines 19, 172, 222-223

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 3: Planner Reliability
**Status:** planned
**Decision IDs:** DEC-PLAN-004
**Requirements:** REQ-P0-005, REQ-P0-006, REQ-GOAL-003
**Issues:** #40
**Definition of Done:**
- REQ-P0-005 satisfied: planner.md < 450 lines
- REQ-P0-006 satisfied: max_turns=65 for planner in CLAUDE.md
- Planner dispatches produce MASTER_PLAN.md on first attempt (manual verification)

##### Planned Decisions
- DEC-PLAN-004: Extract templates from planner.md to templates/ — reduces context consumption — Addresses: REQ-P0-005

##### Work Items

**W3-1: Increase planner max_turns**
- CLAUDE.md dispatch rules table: change planner max_turns from 40 to 65
- Verify no other files reference the old value

**W3-2: Slim planner.md**
- Extract MASTER_PLAN.md full document template to templates/master-plan.md
- Extract initiative block template to templates/initiative-block.md
- Replace inline templates in planner.md with `Read templates/master-plan.md for the full structure`
- Target: 641 -> ~400 lines
- Verify planner agent still produces valid plans (manual test)

**W3-3: Investigate and fix silent dispatch failures**
- Review check-planner.sh for conditions that might cause empty returns
- Review subagent-start.sh planner initialization path
- Check if planner is hitting context limits before producing output
- Add diagnostic logging to planner dispatch path

##### Critical Files
- `agents/planner.md` — planner instructions (641 lines, target ~400)
- `CLAUDE.md` — max_turns dispatch rules
- `hooks/check-planner.sh` — planner compliance checking
- `hooks/subagent-start.sh` — planner dispatch initialization
- `templates/` — destination for extracted templates

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 4: State Cleanup
**Status:** planned
**Decision IDs:** DEC-STATE-005
**Requirements:** REQ-P0-008, REQ-P0-009, REQ-GOAL-004
**Issues:** #41
**Definition of Done:**
- REQ-P0-008 satisfied: worktree removal cleans associated state files
- REQ-P0-009 satisfied: resolve_proof_file handles deleted worktree gracefully
- No orphaned state files in a clean checkout

##### Planned Decisions
- DEC-STATE-005: Extend worktree-roster.sh to clean associated state files on removal — Addresses: REQ-P0-008, REQ-P0-009

##### Work Items

**W4-1: Clean stale breadcrumbs on worktree removal**
- scripts/worktree-roster.sh: in the removal path, also delete .active-worktree-path-* matching the worktree
- hooks/log.sh: verify write_proof_status cleans up on worktree removal
- Add cleanup to session-end.sh or stop.sh worktree sweep

**W4-2: Fix resolve_proof_file for deleted worktrees**
- hooks/log.sh resolve_proof_file(): when breadcrumb points to nonexistent path, fall back to main .proof-status
- Add test case in tests/test-proof-path-worktree.sh for this scenario

**W4-3: State file audit and cleanup script**
- Enumerate all state files in .claude/ (dot-files that are session-scoped)
- Add scripts/clean-state.sh to remove orphaned files
- Document state file lifecycle in hooks/HOOKS.md

##### Critical Files
- `scripts/worktree-roster.sh` — worktree lifecycle management
- `hooks/log.sh` — resolve_proof_file, write_proof_status
- `hooks/stop.sh` — session end cleanup, worktree sweep
- `tests/test-proof-path-worktree.sh` — proof path resolution tests

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 5: Validation Harness
**Status:** planned
**Decision IDs:** DEC-TEST-006
**Requirements:** REQ-P1-002, REQ-P2-001, REQ-P2-002, REQ-GOAL-005
**Issues:** #42
**Definition of Done:**
- End-to-end validation harness runs trace classification against known-good fixtures
- Regression detection flags classification changes between runs
- Accuracy metrics reported (target: >95% correct classification)

##### Planned Decisions
- DEC-TEST-006: Follow existing run-hooks.sh test pattern — consistency with 131-test suite — Addresses: REQ-P1-002, REQ-P2-001

##### Work Items

**W5-1: Trace classification fixtures**
- Create tests/fixtures/traces/ with known-good trace directories per agent type
- Each fixture: manifest.json, artifacts/, summary.md (or specific absence patterns)
- Cover: success, failure, timeout, skipped, crashed for each agent type

**W5-2: Validation harness script**
- New file: tests/test-validation-harness.sh
- Run finalize_trace on each fixture, compare outcome to expected
- Report: total, correct, incorrect, accuracy percentage
- Exit 1 if accuracy < 95%

**W5-3: Regression detection**
- Store baseline classification results in tests/fixtures/trace-baseline.json
- On each run, diff current results against baseline
- Flag any classification changes for review

##### Critical Files
- `tests/test-validation-harness.sh` — the harness itself
- `tests/fixtures/traces/` — known-good trace fixtures
- `hooks/trace-lib.sh` — the classification logic being validated

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Metanoia Remediation Worktree Strategy

Main is sacred. Each phase works in its own worktree:
- **Phase 1:** completed (919a2f0), no worktree needed
- **Phase 2:** `/Users/turla/.claude/.worktrees/trace-reliability` on branch `feature/trace-reliability`
- **Phase 3:** `/Users/turla/.claude/.worktrees/planner-reliability` on branch `feature/planner-reliability`
- **Phase 4:** `/Users/turla/.claude/.worktrees/state-cleanup` on branch `feature/state-cleanup`
- **Phase 5:** `/Users/turla/.claude/.worktrees/validation-harness` on branch `feature/validation-harness`

#### Metanoia Remediation References

- `hooks/HOOKS.md` — Full hook catalog, event model, domain library reference
- `ARCHITECTURE.md` — System architecture, subsystem map
- `README.md` — Project overview, directory structure
- `DECISIONS.md` — Historical decision records
- `tests/run-hooks.sh` — Main test suite (131 tests)
- Existing issues: #16 (phase-1 state registry), #17 (phase-2 multi-context), #18 (phase-3 observatory), #31 (phase-3 test corpus)

---

## Completed Initiatives

| Initiative | Period | Phases | Key Decisions | Archived |
|-----------|--------|--------|---------------|----------|

---

## Parked Issues

| Issue | Description | Reason Parked |
|-------|-------------|---------------|
| #15 | ExitPlanMode spin loop fix | Blocked on upstream claude-code#26651 |
| #14 | PreToolUse updatedInput support | Blocked on upstream claude-code#26506 |
| #13 | Deterministic agent return size cap | Blocked on upstream claude-code#26681 |
| #37 | Close Write-tool loophole for .proof-status bypass | Not in remediation scope |
| #36 | Evaluate Opus for implementer agent | Not in remediation scope |
| #25 | Create unified model provider library | Not in remediation scope |
