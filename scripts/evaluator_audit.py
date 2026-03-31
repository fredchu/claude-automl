#!/usr/bin/env python3
"""automl evaluator audit — mechanical gate between Phase 1 and Phase 2.

Domain-agnostic. Works for code, articles, trading strategies, prompts, configs.

Core principle: evaluator_semantic must verify OUTCOME (intent), not PROPERTY (form).
Enforced via mandatory type classification + mechanical rules per type.

Required field in each task: evaluator_semantic_type
  - test_runner:  automated test suite (code)
  - eval_script:  custom script that executes + scores the deliverable
  - metric:       extracts a number, compares to threshold
  - checklist:    LLM-as-judge with yes/no questions (articles, design, soft quality)
  - assertion:    verifies pattern presence/absence (REFACTOR ONLY — blocked for feature)

Checks #1-#8: type, assertion block, structural≠semantic, type-specific, blacklist, empty.
Checks #9-#11 (v5.2): impact_path, integration, integration≠semantic.
Checks #12-#14 (v5.3, version-gated): regression mandatory, regression≠other layers,
  regression not trivial.
Note: falsification checks removed in v5.4 — replaced by red team agent.

Exit 0 = all pass, exit 1 = blocked, exit 2 = usage error.
"""
import json, sys, re

# Static inspection patterns — fine as structural, NOT as semantic
# Note: \s* prefix handles negation (! grep) and other shell prefixes
STATIC_INSPECTION = re.compile(
    r'^[!\s]*(grep|rg|test\s+-[fdesr]|stat\s|wc\s|du\s|ls\s|file\s)'
)
# Trivial always-pass commands
TRIVIAL_PASS = re.compile(r'^(exit\s+0|true|echo\b.*|:)$')
# Build-only commands (no test/eval component)
BUILD_ONLY = re.compile(
    r'^(xcodebuild\s+build|cargo\s+build|npm\s+run\s+build|tsc\b|go\s+build)\b'
)
# Test file naming conventions (cross-language)
TEST_FILE = re.compile(r'(?i)(test|spec|_test\.|\.test\.|tests/|__tests__|_spec\.)')
# Threshold/comparison in shell commands (space-padded to avoid matching redirects like >file)
HAS_COMPARISON = re.compile(r'(\s-ge\s|\s-gt\s|\s-le\s|\s-lt\s|>=|<=|\s>\s|\s<\s|==|!=|\bassert)')
# Script invocation patterns — must reference a script FILE, not just bash -c 'trivial'
# Script invocation patterns — must reference a script FILE or module, not just bare interpreter
RUNS_SCRIPT = re.compile(
    r'(python3?\s+\S+\.py'       # python3 script.py
    r'|python3?\s+-m\s+\S+'      # python3 -m module
    r'|node\s+\S+\.js'           # node script.js
    r'|npx\s+\S+'                # npx vitest, npx jest
    r'|ruby\s+\S+\.rb'           # ruby script.rb
    r'|swift\s+\S+\.swift'       # swift script.swift
    r'|\.py\b|\.js\b|\.sh\b|\.rb\b)'  # file extension anywhere in command
)

VALID_TYPES = {'test_runner', 'eval_script', 'metric', 'checklist', 'assertion'}
MIN_CHECKLIST_ITEMS = 3
MIN_IMPACT_PATH_LEN = 10


def strip_cd_prefix(cmd: str) -> str:
    """Remove cd ... && and set -o pipefail && prefixes."""
    core = re.sub(r'^cd\s+\S+\s*&&\s*', '', cmd.strip())
    return re.sub(r'\s*set\s+-o\s+pipefail\s*&&\s*', '', core)


def split_shell_parts(cmd: str) -> list:
    """Split a shell command by && and || into individual parts."""
    return [p.strip() for p in re.split(r'&&|\|\|', cmd) if p.strip()]


def is_all_static_or_trivial(parts: list) -> bool:
    """Check if ALL parts of a command are static inspection or trivial."""
    if not parts:
        return False
    return all(
        STATIC_INSPECTION.match(p) or TRIVIAL_PASS.match(p)
        for p in parts
    )


def audit_task(task: dict, schema_version: tuple = (5, 2)) -> dict:
    tid = task['id']
    sem = task.get('evaluator_semantic', '') or ''
    sem_type = task.get('evaluator_semantic_type', '')
    sem_mode = task.get('evaluator_semantic_mode', 'shell')
    scope = task.get('scope', '') or ''
    ttype = task.get('task_type', 'feature')
    structural = task.get('evaluator_structural', '') or ''
    reasons = []

    # --- Check 1: type field exists and is valid ---
    if not sem_type:
        reasons.append(
            'missing evaluator_semantic_type — '
            'must be one of: test_runner, eval_script, metric, checklist, assertion'
        )
        return {'id': tid, 'verdict': 'fail', 'reasons': reasons}

    if sem_type not in VALID_TYPES:
        reasons.append(f'invalid evaluator_semantic_type: "{sem_type}"')
        return {'id': tid, 'verdict': 'fail', 'reasons': reasons}

    # --- Check 1b: evaluator_semantic must not be empty ---
    if sem_type != 'checklist' and not sem.strip():
        reasons.append('evaluator_semantic is empty — no verification defined')
        return {'id': tid, 'verdict': 'fail', 'type': sem_type, 'task_type': ttype, 'reasons': reasons}

    # --- Check 2: assertion blocked for feature tasks ---
    if sem_type == 'assertion' and ttype == 'feature':
        reasons.append(
            'assertion type blocked for feature tasks — '
            'feature requires outcome verification (test_runner/eval_script/metric/checklist), '
            'not pattern matching. assertion is only valid for refactor tasks.'
        )

    # --- Check 3: structural == semantic duplication ---
    if structural and sem and structural.strip() == sem.strip():
        reasons.append(
            'evaluator_structural and evaluator_semantic are identical — '
            'semantic layer adds no incremental verification'
        )

    # --- Check 4: type-specific rules ---

    if sem_type == 'checklist':
        # Checklist must have items defined and meet minimum count
        items = task.get('checklist_items', [])
        if not items:
            reasons.append(
                'checklist type but no checklist_items defined'
            )
        elif isinstance(items, list) and len(items) < MIN_CHECKLIST_ITEMS:
            reasons.append(
                f'checklist has {len(items)} items — '
                f'minimum {MIN_CHECKLIST_ITEMS} required (3-6 recommended). '
                f'Too few items = too coarse to verify intent.'
            )
        if sem_mode != 'checklist':
            reasons.append(
                'checklist type but evaluator_semantic_mode is not "checklist"'
            )

    elif sem_type == 'test_runner':
        # Scope must include test file
        if not TEST_FILE.search(scope):
            reasons.append(
                'test_runner type but scope has no test file — '
                'deliverable cannot include tests'
            )
        core = strip_cd_prefix(sem)
        # Command must not be just static inspection
        m = STATIC_INSPECTION.match(core)
        if m:
            reasons.append(
                f'test_runner type but evaluator_semantic is static inspection '
                f'({m.group()}) — not a test runner'
            )
        # Must not be build-only
        if BUILD_ONLY.match(core):
            reasons.append(
                'test_runner type but evaluator_semantic is build-only — '
                'build checks form, not intent'
            )

    elif sem_type == 'eval_script':
        core = strip_cd_prefix(sem)
        # Must not be just static inspection
        m = STATIC_INSPECTION.match(core)
        if m:
            reasons.append(
                'eval_script type but evaluator_semantic is static inspection — '
                'eval_script must execute and score the deliverable'
            )
        # Must not be trivial (echo/true/exit 0)
        parts = split_shell_parts(core)
        if is_all_static_or_trivial(parts):
            reasons.append(
                'eval_script type but evaluator_semantic is trivial or all static — '
                'eval_script must do substantive execution'
            )

    elif sem_type == 'metric':
        # Command should have comparison OR invoke a script (comparison inside)
        has_visible_comparison = HAS_COMPARISON.search(sem)
        runs_external_script = RUNS_SCRIPT.search(sem)
        if not has_visible_comparison and not runs_external_script:
            reasons.append(
                'metric type but evaluator_semantic has no comparison/threshold '
                'and does not invoke a script — '
                'metric must compare a measured value against a target '
                '(comparison can be in the shell command or inside a script)'
            )

    elif sem_type == 'assertion':
        # Already checked feature block above; for refactor, assertion is fine
        pass

    # --- Check 5: universal blacklist for non-assertion/checklist types ---
    # Skip if eval_script branch already checked (avoid duplicate output)
    if sem_type not in ('assertion', 'checklist', 'eval_script') and sem_mode == 'shell':
        core = strip_cd_prefix(sem)
        parts = split_shell_parts(core)
        if is_all_static_or_trivial(parts):
            reasons.append(
                'evaluator_semantic is entirely static/trivial commands — '
                'this checks form (properties), not intent (outcomes)'
            )

    # --- Check 9: impact_path mandatory for feature tasks ---
    if ttype == 'feature':
        impact_path = task.get('impact_path')
        if not impact_path or not isinstance(impact_path, dict):
            reasons.append(
                'feature task missing impact_path — '
                'must define at least user_outcome (>=10 chars)'
            )
        else:
            user_outcome = (impact_path.get('user_outcome') or '').strip()
            intermediate = impact_path.get('intermediate')
            deliverable = (impact_path.get('deliverable') or '').strip()

            if not user_outcome or len(user_outcome) < MIN_IMPACT_PATH_LEN:
                reasons.append(
                    f'impact_path.user_outcome is missing or too short '
                    f'(need >={MIN_IMPACT_PATH_LEN} chars)'
                )
            else:
                # Determine form: simplified (F6) vs full
                if intermediate is None:
                    # Simplified form — only user_outcome required, intermediate must be null
                    pass
                else:
                    # Full form — all three must be non-empty
                    # intermediate can be a list or string
                    if not intermediate:
                        reasons.append(
                            'impact_path.intermediate is empty — '
                            'full form requires all three fields non-empty '
                            '(or set intermediate to null for simplified form)'
                        )
                    if not deliverable:
                        reasons.append(
                            'impact_path.deliverable is empty — '
                            'full form requires all three fields non-empty'
                        )

    # --- Check 10: evaluator_integration mandatory for feature tasks ---
    integration = (task.get('evaluator_integration') or '').strip()
    if ttype == 'feature' and not integration:
        reasons.append(
            'feature task missing evaluator_integration — '
            'integration test is mandatory for feature tasks (no opt-out)'
        )

    # --- Check 11: integration != semantic (no duplication) ---
    integration_mode = task.get('evaluator_integration_mode', 'shell')
    if integration and sem:
        if integration_mode == sem_mode:
            if integration_mode in ('shell', 'script'):
                # Shell/script mode: identical command string → fail
                if integration.strip() == sem.strip():
                    reasons.append(
                        'evaluator_integration is identical to evaluator_semantic — '
                        'integration layer adds no incremental verification'
                    )
            elif integration_mode == 'checklist':
                # Checklist mode: compare items overlap
                sem_items = set(task.get('checklist_items') or [])
                int_items = set(task.get('integration_checklist_items') or [])
                if sem_items and int_items:
                    overlap = len(sem_items & int_items)
                    total = max(len(sem_items), len(int_items))
                    if total > 0 and overlap / total >= 0.5:
                        reasons.append(
                            f'evaluator_integration checklist overlaps >={overlap}/{total} '
                            f'items with evaluator_semantic checklist — '
                            f'integration must test different concerns'
                        )
            # Mixed mode (one shell, one checklist) → auto-pass
        # else: mixed mode → auto-pass

    # --- Checks #12-#14: regression evaluator (v5.3+, version-gated) ---
    # Note: falsification checks removed in v5.4 — replaced by red team agent
    if schema_version >= (5, 3):
        regression = (task.get('evaluator_regression') or '').strip()

        # Check 12: regression mandatory for feature and refactor tasks
        if ttype in ('feature', 'refactor') and not regression:
            reasons.append(
                f'{ttype} task missing evaluator_regression — '
                'must verify existing behavior is preserved'
            )

        if regression:
            # Check 13: regression must differ from all other evaluators
            if regression == structural.strip():
                reasons.append(
                    'evaluator_regression identical to evaluator_structural'
                )
            if regression == sem.strip():
                reasons.append(
                    'evaluator_regression identical to evaluator_semantic'
                )
            if regression == integration.strip():
                reasons.append(
                    'evaluator_regression identical to evaluator_integration'
                )

            # Check 14a: regression checklist minimum items
            regression_mode = task.get('evaluator_regression_mode', 'shell')
            if regression_mode == 'checklist':
                reg_items = task.get('regression_checklist_items', [])
                if not reg_items:
                    reasons.append(
                        'regression checklist type but no regression_checklist_items defined'
                    )
                elif isinstance(reg_items, list) and len(reg_items) < MIN_CHECKLIST_ITEMS:
                    reasons.append(
                        f'regression checklist has {len(reg_items)} items — '
                        f'minimum {MIN_CHECKLIST_ITEMS} required'
                    )

            # Check 14b: regression must not be trivial/static
            if regression_mode == 'shell':
                core = strip_cd_prefix(regression)
                parts = split_shell_parts(core)
                if is_all_static_or_trivial(parts):
                    reasons.append(
                        'evaluator_regression is trivial/static — '
                        'must verify actual behavior, not just form'
                    )

    return {
        'id': tid,
        'verdict': 'fail' if reasons else 'pass',
        'type': sem_type,
        'task_type': ttype,
        'reasons': reasons,
    }


def main():
    if len(sys.argv) < 2:
        print('Usage: evaluator_audit.py <state.json>', file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1]) as f:
        state = json.load(f)

    sv_str = state.get('schema_version', '5.2')
    try:
        sv_tuple = tuple(int(x) for x in sv_str.split('.'))
    except (ValueError, AttributeError):
        sv_tuple = (5, 2)

    results = [audit_task(t, schema_version=sv_tuple) for t in state['task_list']]
    failed = [r for r in results if r['verdict'] == 'fail']

    for r in results:
        icon = {'pass': '✅', 'fail': '❌'}.get(r['verdict'], '⏭️')
        type_label = f" [{r.get('type','?')}/{r.get('task_type','?')}]"
        print(f"Task {r['id']}: {icon} {r['verdict']}{type_label}")
        for reason in r.get('reasons', []):
            print(f"  → {reason}")

    if failed:
        print(f"\n❌ BLOCKED — {len(failed)} task(s) failed evaluator audit.")
        print("Fix evaluator_semantic_type and evaluator_semantic, then re-run.")
        sys.exit(1)
    else:
        print(f"\n✅ All tasks passed evaluator audit.")
        sys.exit(0)


if __name__ == '__main__':
    main()
