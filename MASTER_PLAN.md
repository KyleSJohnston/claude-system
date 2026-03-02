# MASTER_PLAN: claude-config-pro

## Identity

**Type:** meta-infrastructure
**Languages:** Bash (85%), Markdown (10%), Python (3%), JSON (2%)
**Root:** /Users/turla/.claude
**Created:** 2026-03-01
**Last updated:** 2026-03-02

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
| 2026-03-02 | DEC-AUDIT-001 | hook-consolidation | Map hook-to-library dependencies via static analysis | Static grep is faster and more reliable than runtime tracing for bash |
| 2026-03-02 | DEC-TIMING-001 | hook-consolidation | Parse .hook-timing.log with awk for timing reports | Tab-separated fields, awk is universal, no new dependencies |
| 2026-03-02 | DEC-DEDUP-001 | hook-consolidation | Tighten hooks to exact-minimum require set | Duplicate requires indicate code rot; exact-minimum aids auditing |

---

## Active Initiatives

### Initiative: Hook Consolidation Testing & Streamlining
**Status:** active
**Started:** 2026-03-02
**Goal:** Validate, audit, and streamline the hook system after the lazy-loading performance refactor.

> The hook-perf merge introduced lazy library loading (`require_*()` in source-lib.sh), `--scope`
> for targeted test runs, and worktree-aware gate skipping in pre-write.sh. These changes lack
> post-merge validation — no wall-clock timing comparison exists, `--scope` edge cases are
> untested, and the migration left inconsistencies (e.g., task-track.sh has duplicate
> `require_git`/`require_plan` calls). context-lib.sh still exists as a compatibility shim
> sourcing all ~3,800 lines. This initiative validates the gains, removes dead weight, and
> updates documentation.

**Dominant Constraint:** maintainability

#### Goals
- REQ-GOAL-001: Validate all 131 tests pass after the hook-perf merge with zero regressions
- REQ-GOAL-002: Produce quantitative before/after timing data proving the lazy loading gains
- REQ-GOAL-003: Eliminate all redundant `require_*()` calls and dead code paths across hooks
- REQ-GOAL-004: Ensure `--scope` works correctly for all 10 defined scopes plus edge cases

#### Non-Goals
- REQ-NOGO-001: Rewriting hook logic or changing gate behavior — purely optimization and cleanup
- REQ-NOGO-002: Changing the domain library boundaries (git-lib, plan-lib, etc.) — they are stable
- REQ-NOGO-003: Adding new gates or hooks — this is about consolidating what exists

#### Requirements

**Must-Have (P0)**

- REQ-P0-001: Full test suite passes on main (131/131)
  Acceptance: Given main branch after hook-perf merge, When `bash tests/run-hooks.sh` is run, Then all 131 tests pass with exit 0

- REQ-P0-002: Per-hook timing report from `.hook-timing.log` data
  Acceptance: Given a representative session with 50+ hook invocations, When timing data is analyzed, Then a report shows p50/p95/max per hook type with comparison to pre-optimization baseline

- REQ-P0-003: Duplicate `require_*()` calls removed from task-track.sh
  Acceptance: Given task-track.sh, When inspected, Then each `require_*()` appears exactly once

- REQ-P0-004: `--scope` validates all 10 scopes and handles edge cases
  Acceptance: Given `--scope unknown`, When run, Then error message printed with available scopes

- REQ-P0-005: Hook dependency audit mapping each hook to its minimum required libraries
  Acceptance: Given the audit, When compared to actual `require_*()` calls, Then no hook loads libraries it does not use

- REQ-P0-006: Documentation (HOOKS.md, README.md) reflects lazy loading architecture
  Acceptance: Given updated docs, When a new contributor reads them, Then they understand `require_*()` pattern and `--scope` usage

**Nice-to-Have (P1)**

- REQ-P1-001: `hook-timing-report.sh` script to parse `.hook-timing.log` and generate formatted reports
- REQ-P1-002: Remove or refactor context-lib.sh shim to reduce test-time parse overhead

**Future Consideration (P2)**

- REQ-P2-001: Automated performance regression detection in CI (timing thresholds)

#### Definition of Done

All 131 tests pass. Timing report shows measurable improvement. No duplicate require calls. Documentation updated. All P0 requirements satisfied.

#### Architectural Decisions

- DEC-AUDIT-001: Map hook-to-library dependencies via static analysis (grep for function calls from each library)
  Addresses: REQ-P0-005.
  Rationale: Static analysis is faster and more reliable than runtime tracing for bash. Each library exports well-known function names that can be grepped.

- DEC-TIMING-001: Parse `.hook-timing.log` with awk for timing reports (no new dependencies)
  Addresses: REQ-P0-002, REQ-P1-001.
  Rationale: The timing log uses tab-separated fields already. awk is available everywhere and handles the aggregation natively. No Python or jq needed.

- DEC-DEDUP-001: Tighten task-track.sh and any other hooks with redundant requires to exact-minimum set
  Addresses: REQ-P0-003, REQ-P0-005.
  Rationale: Duplicate requires indicate code rot and make auditing harder. Idempotent guard means ~0ms cost but the inconsistency obscures the real dependency graph.

#### Phase 1: Testing & Timing Validation
**Status:** planned
**Decision IDs:** DEC-TIMING-001
**Requirements:** REQ-P0-001, REQ-P0-002, REQ-P0-004
**Issues:** #44
**Definition of Done:**
- REQ-P0-001 satisfied: 131/131 tests pass
- REQ-P0-002 satisfied: Timing report produced with p50/p95/max per hook type
- REQ-P0-004 satisfied: `--scope` edge cases tested (unknown scope, empty, --help)

##### Planned Decisions
- DEC-TIMING-001: Parse `.hook-timing.log` with awk — Addresses: REQ-P0-002, REQ-P1-001

##### Work Items

**W1-1: Run full test suite and capture results**
- Execute `bash tests/run-hooks.sh` on main, verify 131/131 pass
- Capture output for baseline evidence

**W1-2: Create `scripts/hook-timing-report.sh`**
- Parse `.hook-timing.log` tab-separated fields (timestamp, hook_name, event_type, elapsed_ms, exit_code)
- Aggregate p50/p95/max per hook type and event type
- Support `--since` flag for time-windowed reports

**W1-3: Generate timing comparison report**
- Run representative session (implementer + tester cycle)
- Compare hook wall-clock times before/after optimization
- Document findings in trace artifacts

**W1-4: Test each `--scope` value individually**
- Run `--scope syntax`, `--scope pre-bash`, `--scope pre-write`, etc.
- Verify each produces the correct test subset (non-zero, less than full)

**W1-5: Test `--scope` edge cases**
- `--scope unknown` — should error with available scopes
- `--scope` with no argument — should error
- `--help` — should print usage
- Multiple `--scope` flags — should OR the scopes

##### Critical Files
- `tests/run-hooks.sh` — test runner with --scope implementation
- `hooks/source-lib.sh` — timing instrumentation and require_*() definitions
- `.hook-timing.log` — raw timing data (33K+ lines)

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 2: Hook Dependency Audit & Deduplication
**Status:** planned
**Decision IDs:** DEC-AUDIT-001, DEC-DEDUP-001
**Requirements:** REQ-P0-003, REQ-P0-005
**Issues:** #45
**Definition of Done:**
- REQ-P0-003 satisfied: No duplicate require_*() calls in any hook
- REQ-P0-005 satisfied: Audit table mapping every hook to its minimum required libraries

##### Planned Decisions
- DEC-AUDIT-001: Map hook-to-library dependencies via static analysis — Addresses: REQ-P0-005
- DEC-DEDUP-001: Tighten hooks to exact-minimum require set — Addresses: REQ-P0-003

##### Work Items

**W2-1: Build hook dependency audit table**
- For each hook: list functions called -> map to source library
- Produce table: hook | require_git | require_plan | require_trace | require_session | require_doc | require_ci

**W2-2: Fix task-track.sh duplicate requires**
- Lines 22-26 duplicate lines 38-40 (require_git, require_plan appear twice)
- Consolidate to single block before first usage

**W2-3: Verify session-init.sh library needs**
- Currently loads all via context-lib.sh shim
- Determine actual minimum set (likely needs most, but verify)

**W2-4: Tighten over-broad requires found in audit**
- Any hook loading libraries whose functions it never calls

**W2-5: Per-hook timing analysis**
- Use timing report from Phase 1 to identify remaining bottlenecks
- Focus on hooks with p95 > 200ms

##### Critical Files
- `hooks/task-track.sh` — duplicate require_git/require_plan on lines 22-26 and 38-40
- `hooks/session-init.sh` — uses context-lib.sh shim, loads all ~3,800 lines
- `hooks/context-lib.sh` — compatibility shim (49 lines)
- `hooks/check-*.sh` — 6 check hooks with selective requires to verify

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 3: Dead Code Removal & Hot Path Optimization
**Status:** planned
**Decision IDs:** DEC-DEDUP-001
**Requirements:** REQ-GOAL-003, REQ-P1-002
**Issues:** #46
**Definition of Done:**
- No dead code paths in hook files
- Hot paths (pre-bash early exit, pre-write worktree skip) verified as optimal
- All 131 tests still pass after changes

##### Planned Decisions
- DEC-DEDUP-001: Remove dead code identified in audit — Addresses: REQ-GOAL-003

##### Work Items

**W3-1: Remove dead code paths identified in Phase 2 audit**
- Functions defined but never called
- Branches that can never execute

**W3-2: Verify pre-bash.sh early-exit gate**
- Non-git commands should exit in <30ms
- Profile the fast path

**W3-3: Verify pre-write.sh worktree detection**
- `_IN_WORKTREE` path correctly skips plan-check and lightens doc-gate
- Verify no false positives/negatives

**W3-4: Assess context-lib.sh shim**
- Can it be removed? (depends on what still sources it directly)
- If kept, can it be slimmed?

**W3-5: Re-run full test suite after all changes**
- 131/131 must still pass
- Timing comparison with Phase 1 baseline

##### Critical Files
- `hooks/pre-bash.sh` — hot path for every bash command
- `hooks/pre-write.sh` — hot path for every write/edit (715 lines)
- `hooks/post-write.sh` — post-tool hook, verify minimal loading
- `hooks/context-lib.sh` — compatibility shim (removal candidate)

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 4: Documentation Update
**Status:** planned
**Requirements:** REQ-P0-006
**Issues:** #47
**Definition of Done:**
- REQ-P0-006 satisfied: HOOKS.md documents lazy loading, --scope, worktree skipping

##### Planned Decisions
- No new architectural decisions — documentation only

##### Work Items

**W4-1: Update `hooks/HOOKS.md` — lazy loading architecture**
- Document `require_*()` pattern and when to use each
- Document `require_all()` vs selective loading

**W4-2: Update `hooks/HOOKS.md` — `--scope` usage**
- Available scopes and what each covers
- Edge case behavior

**W4-3: Update `README.md` — test runner usage**
- Add `--scope` to test runner documentation

**W4-4: Refresh `ARCHITECTURE.md` — hook subsystem**
- Domain library split (core-lib, git-lib, plan-lib, trace-lib, session-lib, doc-lib, ci-lib)
- Timing instrumentation
- Line counts and load costs

##### Critical Files
- `hooks/HOOKS.md` — primary hook documentation
- `README.md` — project overview
- `ARCHITECTURE.md` — system architecture reference

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Hook Consolidation Worktree Strategy

Main is sacred. Each phase works in its own worktree:
- **Phase 1:** `/Users/turla/.claude/.worktrees/hook-test-validate` on branch `feature/hook-test-validate`
- **Phase 2:** `/Users/turla/.claude/.worktrees/hook-audit` on branch `feature/hook-audit`
- **Phase 3:** `/Users/turla/.claude/.worktrees/hook-streamline` on branch `feature/hook-streamline`
- **Phase 4:** `/Users/turla/.claude/.worktrees/hook-docs` on branch `feature/hook-docs`

#### Hook Consolidation References

- `.hook-timing.log` — 33K+ lines of raw timing data
- `hooks/source-lib.sh` — lazy loading architecture (DEC-SPLIT-002, DEC-PERF-001, DEC-PERF-002)
- `hooks/context-lib.sh` — compatibility shim (DEC-SPLIT-001)
- `hooks/pre-write.sh` — worktree-aware gate skipping (DEC-PERF-003)

---

## Completed Initiatives

| Initiative | Period | Phases | Key Decisions | Archived |
|-----------|--------|--------|---------------|----------|
| Production Remediation (Metanoia Suite) | 2026-02-28 to 2026-03-01 | 5 | DEC-HOOKS-001 thru DEC-TEST-006 | No |

### Production Remediation (Metanoia Suite) — Summary

Fixed defects left by the metanoia hook consolidation (17 hooks -> 4 entry points + 6 domain libraries). Five phases over 3 days:

1. **CI Green** (919a2f0): Migrated 131 tests to consolidated hooks, 0 failures.
2. **Trace Reliability** (1372603): Shellcheck clean, agent-type-aware classification, compliance.json race fix, repair-traces.sh, 15 trace classification tests.
3. **Planner Reliability** (3796e35): planner.md slimmed 641->389 lines via template extraction, max_turns 40->65, silent dispatch fixes.
4. **State Cleanup** (22aff13): Worktree-roster cleans breadcrumbs on removal, resolve_proof_file falls back gracefully, clean-state.sh audit script.
5. **Validation Harness** (b36f3ad): 20 trace fixtures across 4 agent types x 5 outcomes, validation harness with 95% accuracy gate, regression detection via baseline diffing.

All P0 requirements satisfied. 6 architectural decisions recorded (DEC-HOOKS-001 through DEC-TEST-006). Issues closed: #39, #40, #41, #42.

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
