# Example: Code Fix Loop — Auto-fix Failing Tests

Let automl iterate until all pytest tests pass. No manual debugging — define the evaluator, set the scope, and let the loop run.

## Scenario

You have a Python project with failing tests. You want automl to automatically fix the source code until all tests pass.

## Command

```
/automl make all tests pass
evaluator: pytest tests/ -q
scope: src/
```

## What Happens

**Phase detection:** All three elements (goal + evaluator + scope) are present. automl skips Phase 0/1 and goes directly to Phase 2.

**Step 1 — Backup:** automl creates a git tag `automl-baseline-{run_id}` so you can always return to the starting point.

**Step 2 — Baseline:** A subagent runs `pytest tests/ -q` to record the initial failure count.

**Step 3 — Improvement loop:** For each failing test, a subagent:
1. Reads the test to understand what is expected
2. Makes the minimal change to `src/` that should fix it
3. Runs `pytest tests/ -q` again
4. If fewer tests fail → `git commit` (keep)
5. If more tests fail → `git checkout -- src/` (revert)
6. Appends the result to `.automl/{run_id}/changelog.md`
7. Continues until all tests pass or `max_iter` is reached

**Step 4 — Regression check:** After all tasks pass individually, a regression subagent re-runs the full test suite to confirm nothing was broken.

## Full Example with Parameters

```
/automl make all tests pass
evaluator: pytest tests/ -q
scope: src/
max: 20
runs_per_iter: 1
consecutive_passes: 3
```

**max: 20** — allow up to 20 iterations per task (default is 10)
**runs_per_iter: 1** — run pytest once per iteration (deterministic, no need for multiple runs)
**consecutive_passes: 3** — require 3 consecutive passes before marking as stable

## Monitoring Progress

While automl runs, check progress in another terminal:

```bash
cat .automl/*/state.json | jq .checkpoint_summary
```

To stop automl gracefully:

```bash
touch .automl/{run_id}/STOP
```

automl will pause before the next subagent dispatch and wait for you to resume.

## To Return to the Starting Point

```bash
git checkout automl-baseline-{run_id}
```

## Final Report (example output)

```
=== AutoML Done ===
Status: passed
Phase 0: skipped
Phase 1: skipped
Phase 2:
  Total inner iterations: 14 (9 keep, 5 revert)
  Regression check: 1 round (0 regressions, all passed)
  Task 1: baseline 6 failures → final 0, 8 iters
  Task 2: baseline 2 failures → final 0, 6 iters
Phase 3: skipped
Last commit: a3f9c12 automl: fix edge case in user auth
Run ID: 20260328-143022-a7f3
Baseline tag: automl-baseline-20260328-143022-a7f3
Changelog: .automl/20260328-143022-a7f3/changelog.md
```

---

# 範例：程式碼修復迴圈 — 自動修復失敗的測試（繁體中文）

讓 automl 迭代直到所有 pytest 測試通過。不需要手動除錯 — 定義 evaluator、設定範圍，讓迴圈自動跑。

## 場景

你有一個 Python 專案，其中有幾個測試失敗。你想讓 automl 自動修改原始碼，直到所有測試通過。

## 指令

```
/automl 讓 pytest 全部通過
evaluator: pytest tests/ -q
範圍: src/
```

## 執行流程

**Phase 偵測：** 三個元素（目標 + evaluator + 範圍）齊全，automl 跳過 Phase 0/1，直接進入 Phase 2。

**Step 1 — 備份：** automl 建立 git tag `automl-baseline-{run_id}`，隨時可以一鍵回到起點。

**Step 2 — Baseline：** subagent 跑 `pytest tests/ -q`，記錄初始失敗數量。

**Step 3 — 優化迴圈：** 對每個失敗的測試，subagent 會：
1. 讀取測試，理解預期行為
2. 對 `src/` 做最小改動來修復
3. 再跑 `pytest tests/ -q`
4. 失敗數減少 → `git commit`（keep）
5. 失敗數增加 → `git checkout -- src/`（revert）
6. 追加結果到 `.automl/{run_id}/changelog.md`
7. 持續到全部通過或達到 `max_iter` 上限

**Step 4 — 回歸檢查：** 所有 task 個別通過後，回歸 subagent 重跑完整測試套件，確認沒有任何東西被破壞。

## 完整範例（含參數）

```
/automl 讓 pytest 全部通過
evaluator: pytest tests/ -q
範圍: src/
max: 20
runs_per_iter: 1
consecutive_passes: 3
```

**max: 20** — 每個 task 最多跑 20 輪（預設 10）
**runs_per_iter: 1** — 每輪跑一次 pytest（確定性結果，不需要多次）
**consecutive_passes: 3** — 連續 3 次通過才算穩定達標

## 監控進度

automl 執行中，在另一個終端機查看進度：

```bash
cat .automl/*/state.json | jq .checkpoint_summary
```

優雅地中止 automl：

```bash
touch .automl/{run_id}/STOP
```

automl 會在下一次派工前暫停，等你手動恢復。

## 回到起點

```bash
git checkout automl-baseline-{run_id}
```
