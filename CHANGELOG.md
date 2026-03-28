# Changelog

## v3.0.0 — 2026-03-28

Initial open-source release.

### Features

- Dual-loop engine: per-task improvement loop + cross-task regression check
- Shell evaluator mode: pass/fail (exit code) and scoring (numeric stdout)
- Checklist evaluator mode: LLM-as-judge for subjective quality criteria
- Subagent architecture: main session is dispatcher only, never touches code directly
- Auto-resume with state persistence in `.automl/{run_id}/`
- Git tag baseline before any changes; one command to return to starting point
- Non-git fallback: file-copy backup and revert for non-git projects
- STOP file interrupt mechanism: graceful pause before next subagent dispatch
- Runs-per-iter averaging for non-deterministic evaluators
- Consecutive-passes stability requirement before marking a task complete
- Optional Phase 0/1/3 skill integrations (ideation, task planning, verification, code review)
- Changelog per run: every iteration recorded with strategy, result, and conclusion
