# Changelog

## v3.1.0 — 2026-03-29

Risk scenario analysis and verification checklist — catch bugs before manual testing.

### Features

- **Phase 1: Risk Scenarios** — each task now requires 3-5 "how could this break?" scenarios. Scenarios auto-flow into evaluators (as test cases) and Phase 3 checklist (as manual verification items). Domain-agnostic: works for code, text, config, and any other task type.
- **Phase 3: Risk Scenario Review** — mandatory step: trace each risk scenario through the actual implementation, rating ✅ Safe or 🔴 Bug with explanation. Reviewer also identifies new scenarios not listed in Phase 1.
- **Phase 3: Verification Checklist** — mandatory output: prioritized test checklist (crash > data loss > UX > cosmetic) assembled from Phase 1 risk scenarios + Phase 3 review findings. User runs the full list in one pass, reports failures, minimizing ping-pong.
- **Final report** now includes risk scenario results and verification checklist.

### Motivation

In a real-world iOS architecture rewrite (replacing IPC polling with Darwin notifications), automl v3.0.0 caught build errors but missed a race condition, an audio session leak, and two state machine bugs — all found only through manual testing. Post-mortem analysis showed that listing "what could break?" upfront would have identified all 5 bugs before Phase 2 even started.

---

## v3.0.0 — 2026-03-28

Subagent architecture rewrite. Main session becomes pure dispatcher.

### Breaking changes from v2

- Main session no longer executes code changes or runs evaluators directly
- Removed `confirm_every_n` parameter (replaced by passive STOP file mechanism)
- State file format changed: split into dispatcher fields (main session) and task fields (subagent)
- Changelog moved from project root (`automl-changelog.md`) to `.automl/{run_id}/changelog.md`

### Features

- **Subagent architecture**: main session is dispatcher only, never touches code directly
- **Prompt templates**: BASELINE_PROMPT, TASK_LOOP_PROMPT, REGRESSION_CHECK_PROMPT — fill-in-the-blank dispatching
- **State file write separation**: main session writes dispatch fields, subagent writes task fields, no conflicts
- **Run ID isolation**: `{YYYYMMDD-HHMMSS}-{4hex}`, multiple sessions don't interfere
- **Auto-resume**: scan `.automl/` for incomplete runs, pick up where left off
- **Main session self-check**: before every tool call, ask "dispatch or execute?"
- **mode="auto"**: subagents run autonomously without permission prompts
- **SKILL.md + reference.md split**: Phase 2 fast path doesn't load reference (token lazy-loading)
- Non-git fallback: file-copy backup and revert for non-git projects
- STOP file interrupt mechanism: graceful pause before next subagent dispatch
- Subagent failure handling: retry logic, stuck detection, changelog/state desync recovery

### Carried over from v2

- Dual-loop engine: per-task improvement loop + cross-task regression check
- Shell evaluator mode: pass/fail (exit code) and scoring (numeric stdout)
- Checklist evaluator mode: LLM-as-judge for subjective quality criteria
- Runs-per-iter averaging for non-deterministic evaluators
- Consecutive-passes stability requirement
- Scope overlap detection and evaluator file protection
- Optional Phase 0/1/3 skill integrations

---

## v2.0.0 — 2026-03-28

Transition release. Added Agent tool support and removed user interrupts.

### Changes from v1

- Added `Agent` to allowed-tools (subagent dispatching)
- Removed `AskUserQuestion` — adopted "never ask user" principle
- Added `max_iter_per_dispatch` parameter (default 5, caps single subagent context usage)
- Added scope overlap detection before entering Phase 2
- Added evaluator file protection (evaluator scripts excluded from controlled scope)
- Phase 0 "self-guide" mode: extract goal/evaluator/scope from user message, fill defaults for missing parts
- Phase 1 no longer pauses for user confirmation

### Known issues (fixed in v3)

- Blurry boundary between main session and subagent responsibilities
- No state file format definition, unreliable resume
- No prompt templates, ad-hoc prompt composition per dispatch
- No main session self-check mechanism

---

## v1.0.0 — 2026-03-28

First version. Monolithic architecture — main session does everything.

### Features

- Four-phase workflow: Phase 0 (intent) → Phase 1 (decompose) → Phase 2 (loop) → Phase 3 (deliver)
- Dual-loop engine: inner per-task loop + outer regression check
- Shell evaluator (pass/fail + scoring) and checklist evaluator (LLM-as-judge)
- Git tag baseline + per-iteration commit/revert
- Changelog per iteration
- `confirm_every_n` parameter for periodic user check-ins
- Skill integrations: office-hours, brainstorming, grill-me, writing-plans, TDD, code review

### Known issues (fixed in v2/v3)

- Context explosion: main session holds all code diffs + evaluator output + changelog
- `AskUserQuestion` interrupts break automation flow
- No evaluator file protection (subagent could modify evaluator to game results)
- No state persistence, session break = start over
