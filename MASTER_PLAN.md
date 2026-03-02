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
| 2026-03-02 | DEC-AUDIT-001 | hook-consolidation | Map hook-to-library dependencies via static analysis | Static grep is faster and more reliable than runtime tracing for bash |
| 2026-03-02 | DEC-TIMING-001 | hook-consolidation | Parse .hook-timing.log with awk for timing reports | Tab-separated fields, awk is universal, no new dependencies |
| 2026-03-02 | DEC-DEDUP-001 | hook-consolidation | Tighten hooks to exact-minimum require set | Duplicate requires indicate code rot; exact-minimum aids auditing |
| 2026-03-01 | DEC-STATE-007 | state-mgmt-reliability | Replace inline proof resolution with resolve_proof_file() | Canonical resolver handles worktree breadcrumbs correctly; inline copies diverge |
| 2026-03-01 | DEC-STATE-008 | state-mgmt-reliability | Pervasive validate_state_file before cut | Prevents crashes on corrupt/empty/truncated state files |

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

### Initiative: State Management Reliability
**Status:** active
**Started:** 2026-03-01
**Goal:** Unify all proof-status reads to use canonical `resolve_proof_file()` and harden `validate_state_file()` across the hook system.

> State management has been a recurring source of bugs. 7 hooks read proof-status via inline
> fallback logic instead of canonical `resolve_proof_file()`. This creates divergence when
> worktrees are active. `validate_state_file()` is only called in 1 of ~10 proof-read sites.
> This initiative unifies all reads and hardens all validation, then proves correctness with
> comprehensive tests.

**Dominant Constraint:** reliability

#### Goals
- REQ-GOAL-001: All proof-status reads use `resolve_proof_file()` — zero inline resolution
- REQ-GOAL-002: `validate_state_file()` guards every `cut -d'|'` read
- REQ-GOAL-003: Full E2E test coverage for state lifecycle, corruption, concurrency
- REQ-GOAL-004: Clean-state and session-boundary cleanup verified

#### Non-Goals
- REQ-NOGO-001: Changing proof-status semantics or state machine transitions — stable and correct
- REQ-NOGO-002: Modifying the resolver function itself — it is already correct
- REQ-NOGO-003: Adding new state files or proof types — out of scope

#### Requirements

**Must-Have (P0)**

- REQ-P0-001: task-track.sh, pre-bash.sh, post-write.sh use resolve_proof_file()
  Acceptance: Given these 3 critical hooks, When proof-status is read, Then resolve_proof_file() is used instead of inline resolution

- REQ-P0-002: subagent-start.sh, session-end.sh, stop.sh, prompt-submit.sh use resolve_proof_file()
  Acceptance: Given these 4 hooks, When proof-status is read, Then resolve_proof_file() is used instead of inline resolution

- REQ-P0-003: validate_state_file before every bare `cut -d'|'` on proof files
  Acceptance: Given any proof-status read via cut, When the file is corrupt/empty/truncated, Then validate_state_file catches it before cut executes

- REQ-P0-004: Full lifecycle E2E test suite
  Acceptance: Given tests/test-state-lifecycle.sh with 12-15 tests and expanded test-proof-path-worktree.sh with 6-8 tests, When run, Then 18-23 new tests pass with zero regressions

- REQ-P0-005: Corruption and concurrency test suite
  Acceptance: Given tests/test-state-corruption.sh (8-10 tests) and test-state-concurrent.sh (4-6 tests), When run, Then 12-16 new tests pass with zero regressions

- REQ-P0-006: Clean-state and session boundary test suite
  Acceptance: Given tests/test-clean-state.sh (6-8 tests) and session boundary tests (4-6 tests), When run, Then 10-14 new tests pass with zero regressions

#### Definition of Done

All hooks use canonical proof resolution. validate_state_file guards every read. 40-53 new tests pass. Zero regressions in existing 131+ tests. Shellcheck clean.

#### Architectural Decisions

- DEC-STATE-007: Replace all inline scoped/legacy proof resolution with resolve_proof_file()
  Addresses: REQ-P0-001, REQ-P0-002.
  Rationale: Canonical resolver handles worktree breadcrumb fallback correctly. Inline copies diverge when worktree logic changes, causing proof-gate failures in worktree contexts.

- DEC-STATE-008: Add validate_state_file() before every bare `cut -d'|'` on proof files
  Addresses: REQ-P0-003.
  Rationale: Prevents crashes on corrupt/empty/truncated files. Currently only 1 of ~10 proof-read sites validates, leaving 9 sites vulnerable to malformed state.

#### Phase 1: Proof-Read Unification (Critical Hooks)
**Status:** planned
**Decision IDs:** DEC-STATE-007
**Requirements:** REQ-P0-001
**Issues:** #48
**Definition of Done:**
- REQ-P0-001 satisfied: task-track.sh, pre-bash.sh, post-write.sh all use resolve_proof_file()
- Existing tests pass with zero regressions

##### Planned Decisions
- DEC-STATE-007: Replace inline proof resolution with resolve_proof_file() — Addresses: REQ-P0-001

##### Work Items

**W1-1: task-track.sh Gate A — resolve_proof_file() (#48)**
- Replace inline scoped/legacy proof-status resolution in Gate A with resolve_proof_file()
- Verify gate behavior unchanged via existing test-proof-chain.sh tests

**W1-2: pre-bash.sh Check 8 — resolve_proof_file() (#48)**
- Replace inline proof-status read in Check 8 with resolve_proof_file()
- Verify early-exit and proof-gate behavior unchanged

**W1-3: post-write.sh proof invalidation — resolve_proof_file() + write_proof_status() (#48)**
- Replace inline proof resolution in write/edit invalidation path
- Use both resolve_proof_file() for reads and write_proof_status() for writes
- Verify proof invalidation behavior unchanged

##### Critical Files
- `hooks/task-track.sh` — Gate A proof-status check (highest-traffic proof read)
- `hooks/pre-bash.sh` — Check 8 proof gate (every bash command)
- `hooks/post-write.sh` — proof invalidation on file writes (715 lines)
- `hooks/log.sh` — resolve_proof_file(), write_proof_status(), project_hash()

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 2: Lower-Priority Fixes + validate_state_file Hardening
**Status:** planned
**Decision IDs:** DEC-STATE-007, DEC-STATE-008
**Requirements:** REQ-P0-002, REQ-P0-003
**Issues:** #49
**Definition of Done:**
- REQ-P0-002 satisfied: subagent-start.sh, session-end.sh, stop.sh, prompt-submit.sh all use resolve_proof_file()
- REQ-P0-003 satisfied: validate_state_file guards every bare cut -d'|' read

##### Planned Decisions
- DEC-STATE-007: Replace inline proof resolution with resolve_proof_file() — Addresses: REQ-P0-002
- DEC-STATE-008: Pervasive validate_state_file before cut — Addresses: REQ-P0-003

##### Work Items

**W2-1: subagent-start.sh — resolve_proof_file() (#49)**
- Replace inline proof-status resolution with resolve_proof_file()
- Verify subagent dispatch gate behavior unchanged

**W2-2: Informational readers — resolve_proof_file() (#49)**
- session-end.sh, stop.sh, prompt-submit.sh use resolve_proof_file()
- These are read-only/informational — lower risk but same inconsistency

**W2-3: Pervasive validate_state_file before cut (#49)**
- Audit all ~10 locations where `cut -d'|'` parses proof files
- Add validate_state_file() guard before each bare cut
- Handle validation failure gracefully (log warning, use safe default)

##### Critical Files
- `hooks/task-track.sh` — subagent-start handler, multiple cut -d'|' sites
- `hooks/pre-bash.sh` — prompt-submit integration, proof reads
- `hooks/post-write.sh` — session-end and stop handlers
- `hooks/core-lib.sh` — validate_state_file() definition

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 3: Lifecycle E2E + Resolver Consistency Tests
**Status:** planned
**Requirements:** REQ-P0-004
**Issues:** #50
**Definition of Done:**
- REQ-P0-004 satisfied: 18-23 new tests pass
- Zero regressions in existing suite

##### Planned Decisions
- No new architectural decisions — test-only phase

##### Work Items

**W3-1: New tests/test-state-lifecycle.sh (12-15 tests) (#50)**
- Full proof-status lifecycle: needs-verification -> verified -> committed
- Worktree lifecycle: breadcrumb creation, resolution, cleanup
- Cross-worktree proof isolation
- Session boundary transitions

**W3-2: Expand tests/test-proof-path-worktree.sh (6-8 tests) (#50)**
- Resolver consistency: same result from all 7 hooks for same state
- Breadcrumb fallback when scoped file missing
- Legacy path fallback when no breadcrumb exists
- Edge cases: missing directories, permission errors

##### Critical Files
- `tests/test-state-lifecycle.sh` — new file (12-15 tests)
- `tests/test-proof-path-worktree.sh` — existing file (26 tests, expand to 32-34)
- `tests/test-proof-chain.sh` — existing proof chain tests (18 tests, verify no regressions)

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 4: Corruption + Concurrency Tests
**Status:** planned
**Requirements:** REQ-P0-005
**Issues:** #51
**Definition of Done:**
- REQ-P0-005 satisfied: 12-16 new tests pass
- Zero regressions in existing suite

##### Planned Decisions
- No new architectural decisions — test-only phase

##### Work Items

**W4-1: New tests/test-state-corruption.sh (8-10 tests) (#51)**
- Empty proof file handling
- Truncated proof file (missing fields)
- Malformed delimiters (wrong separator, extra pipes)
- Binary/garbage content in proof file
- Permission-denied on proof file read
- Proof file disappears mid-read (race condition)

**W4-2: New tests/test-state-concurrent.sh (4-6 tests) (#51)**
- Simultaneous proof writes from two processes
- Read during write (partial content)
- Rapid state transitions (write-read-write without delay)
- File locking behavior verification

##### Critical Files
- `tests/test-state-corruption.sh` — new file (8-10 tests)
- `tests/test-state-concurrent.sh` — new file (4-6 tests)
- `hooks/core-lib.sh` — validate_state_file() behavior under corruption
- `hooks/log.sh` — write_proof_status() atomicity

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### Phase 5: Clean-state E2E + Session Boundary Tests
**Status:** planned
**Requirements:** REQ-P0-006
**Issues:** #52
**Definition of Done:**
- REQ-P0-006 satisfied: 10-14 new tests pass
- Full suite green (131+ existing + 40-53 new tests)

##### Planned Decisions
- No new architectural decisions — test-only phase

##### Work Items

**W5-1: New tests/test-clean-state.sh (6-8 tests) (#52)**
- clean-state.sh removes all proof files correctly
- clean-state.sh preserves non-proof state files
- clean-state.sh handles missing state directory gracefully
- Post-cleanup: hooks function correctly with no state
- Idempotent cleanup (running twice is safe)

**W5-2: Session boundary cleanup tests (4-6 tests) (#52)**
- Session end triggers appropriate state cleanup
- Orphaned proof files detected and cleaned
- Worktree removal cleans associated proof breadcrumbs
- New session starts with clean state after prior session cleanup

##### Critical Files
- `tests/test-clean-state.sh` — new file (6-8 tests)
- `scripts/clean-state.sh` — cleanup script under test
- `hooks/task-track.sh` — session boundary handlers
- `hooks/log.sh` — proof file management functions

##### Decision Log
<!-- Guardian appends here after phase completion -->

#### State Management Reliability Worktree Strategy

Main is sacred. Each phase works in its own worktree:
- **Phase 1:** `/Users/turla/.claude/.worktrees/state-mgmt-p1` on branch `feature/state-mgmt-p1`
- **Phase 2:** `/Users/turla/.claude/.worktrees/state-mgmt-p2` on branch `feature/state-mgmt-p2`
- **Phase 3:** `/Users/turla/.claude/.worktrees/state-mgmt-p3` on branch `feature/state-mgmt-p3`
- **Phase 4:** `/Users/turla/.claude/.worktrees/state-mgmt-p4` on branch `feature/state-mgmt-p4`
- **Phase 5:** `/Users/turla/.claude/.worktrees/state-mgmt-p5` on branch `feature/state-mgmt-p5`

#### State Management Reliability References

- `hooks/log.sh` — resolve_proof_file(), write_proof_status(), project_hash()
- `hooks/core-lib.sh` — validate_state_file()
- `tests/test-proof-chain.sh` — existing proof chain tests (18 tests)
- `tests/test-proof-path-worktree.sh` — existing worktree proof tests (26 tests)
- `scripts/clean-state.sh` — state cleanup script

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
