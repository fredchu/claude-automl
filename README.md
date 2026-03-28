# claude-automl

Autonomous Evaluation Loop for Claude Code — define success, let the agent iterate until it gets there.

## What It Does

claude-automl gives Claude Code a self-improvement engine. You define what "done" looks like (a test suite, a checklist, a score threshold), and the agent modifies → evaluates → keeps or reverts → repeats until it passes — without asking you anything.

The loop runs two layers deep. An inner loop optimizes each task individually. An outer regression check confirms that fixing one task did not break another. Only when everything passes simultaneously does automl declare completion.

## The Loop

```
for each task:
    run baseline evaluator
    while not passing and iterations < max:
        subagent makes minimal change to scope
        run evaluator (N times)
        improved → git commit (keep)
        regressed → git checkout (revert)
        log to changelog

all tasks passing?
    run regression check across all tasks
    any task regressed → fix it, re-check
    all pass simultaneously → done
```

## Quick Start

**Install**

```bash
git clone https://github.com/fredchu/claude-automl ~/.claude/skills/automl
```

**Three Inputs**

**1. Goal** — what you want to achieve

**2. Evaluator** — how to check success. Either a shell command (exit code or numeric score) or a checklist of yes/no quality criteria.

**3. Scope** — which files the agent is allowed to modify. Narrower is safer.

**Usage**

```
/automl make all tests pass
evaluator: pytest tests/ -q
scope: src/
```

That is all. automl handles the rest.

## Features

**Dual loop: per-task improvement + cross-task regression check**
Each task gets its own improvement loop. After all tasks pass, a regression check confirms they all still pass simultaneously. If a later fix breaks an earlier task, automl goes back and repairs it.

**Two evaluator modes: shell and checklist**
Shell mode uses exit codes or numeric scores — good for tests, builds, linting, word counts. Checklist mode uses the agent as judge — good for writing quality, tone, documentation completeness, anything subjective.

**Auto-resume: state persists in `.automl/{run_id}/`**
Every run has a unique ID and its own state directory. If a session is interrupted, the next `/automl` call scans for unfinished runs and picks up from the last completed iteration.

**Safety: git tag baseline, whitelist scope, STOP file interrupt, non-git fallback**
A git tag is created before any changes. The agent can only touch files inside the declared scope. Drop a `STOP` file to pause the run. On non-git projects, a file-copy fallback handles backup and revert.

**Subagent architecture: main session dispatches only, never touches code directly**
The main session reads state, decides what to dispatch, and updates scheduling fields. All code edits, evaluator runs, and git operations happen inside subagents. This keeps the main session context clean across long runs.

## Parameters

**Goal** — what you want to achieve (required)

**Evaluator** — shell command or `checklist` (required)

**Scope** — files or directories the agent may modify (required)

**max** — max iterations per task. Default: 10. Maximum: 50.

**runs_per_iter** — how many times to run the evaluator per iteration, averaged. Default: 1. Recommended 3-5 for checklist or non-deterministic evaluators.

**direction** — `higher_is_better` (default) or `lower_is_better`. Controls whether an increasing score counts as improvement.

**consecutive_passes** — how many consecutive passing iterations required before a task is considered stable. Default: 3.

**max_regression_rounds** — how many rounds of outer regression check to attempt before giving up on conflicting tasks. Default: 3.

## Optional Skill Integrations

automl's Phase 0, 1, and 3 can integrate with external skills if you have them installed. Phase 2 (the core loop) always runs standalone with no dependencies.

**Phase 0 — intent clarification (optional)**
If your goal is vague, automl can hand off to an ideation, brainstorming, or exploration skill before defining the task list.

**Phase 1 — task decomposition (optional)**
For large goals, a task planning skill can break the work into small independently-evaluable tasks. A plan review skill (business, technical, or design perspective) can stress-test the plan before execution begins.

**Phase 3 — delivery (optional)**
A verification skill confirms the final state with evidence before claiming completion. A code review skill catches issues in the diff before you ship.

None of these are required. If you do not have them, automl handles each phase itself.

## Examples

See the `examples/` directory:

**`examples/code-fix-loop.md`** — auto-fix failing pytest tests until the suite is green

**`examples/text-quality-loop.md`** — improve writing quality against a checklist until all criteria pass

## How It Works

**Phase 0 — Clarify intent** (skipped if goal + evaluator + scope are already present)
automl extracts or elicits the three required inputs. If you provide all three upfront, this phase is skipped entirely.

**Phase 1 — Decompose + define evaluators** (skipped for single-task goals)
Large goals get broken into smaller tasks, each with its own evaluator and scope. Scope overlap is checked before execution begins.

**Phase 2 — Dual-loop execution**
The core engine. Main session dispatches subagents. Subagents modify, evaluate, keep or revert, and write to the changelog. Main session reads state and decides what to dispatch next.

**Phase 3 — Delivery verification** (optional)
Final check that everything still passes before declaring done.

## Safety

- Main session never directly edits files or runs evaluators — all execution happens in subagents
- Agent can only modify files inside the declared scope
- Evaluator files are protected — the agent cannot modify its own judge
- Git tag is created before any changes; one command returns you to the starting point
- STOP file interrupt: `touch .automl/{run_id}/STOP` pauses before the next dispatch
- Max iterations cap prevents runaway token usage
- Each evaluator call has a 120-second timeout
- Every run is isolated in its own `.automl/{run_id}/` directory

## License

MIT

---

# claude-automl（繁體中文）

Claude Code 自主優化迴圈 — 定義成功條件，讓 agent 自動迭代直到達標。

## 這是什麼

claude-automl 為 Claude Code 提供自我改善引擎。你定義「完成」的標準（測試套件、checklist、分數門檻），agent 自動執行「修改 → 評估 → keep 或 revert → 重複」，直到通過 — 全程不打擾你。

迴圈分兩層。內層迴圈對每個 task 個別優化。外層回歸檢查確認修好一個 task 沒有破壞其他 task。所有 task 同時通過，automl 才宣告完成。

## 迴圈結構

```
for each task:
    跑 baseline evaluator
    while 未達標 and 迭代次數 < max:
        subagent 對受控範圍做最小改動
        跑 evaluator（N 次）
        改善 → git commit（keep）
        退步 → git checkout（revert）
        記錄到 changelog

所有 task 通過後：
    對所有 task 跑回歸檢查
    有 task 退步 → 修復後再檢查
    全部同時通過 → 完成
```

## 快速開始

**安裝**

```bash
git clone https://github.com/fredchu/claude-automl ~/.claude/skills/automl
```

**三個必要元素**

**1. 成功條件** — 你想達到什麼

**2. Evaluator** — 如何判斷是否成功。可以是 shell 指令（exit code 或數值分數），或一組 yes/no 品質標準的 checklist。

**3. 受控範圍** — agent 可以修改哪些檔案。範圍越窄越安全。

**使用方式**

```
/automl 讓 pytest 全部通過
evaluator: pytest tests/ -q
範圍: src/
```

就這樣。automl 處理其餘一切。

## 功能特色

**雙層迴圈：per-task 優化 + 跨 task 回歸檢查**
每個 task 有自己的優化迴圈。所有 task 通過後，回歸檢查確認它們同時仍然通過。如果後面的修復破壞了前面的 task，automl 會回去修復。

**兩種 evaluator 模式：shell 和 checklist**
Shell 模式使用 exit code 或數值分數，適合測試、build、linting、字數檢查。Checklist 模式讓 agent 自己當評判，適合寫作品質、語氣、文件完整性等主觀標準。

**自動續傳：狀態持久化在 `.automl/{run_id}/`**
每次執行有唯一 run ID 和獨立的狀態目錄。Session 中斷後，下次 `/automl` 自動掃描未完成的 run，從最後完成的迭代繼續。

**安全護欄：git tag 備份、受控範圍白名單、STOP 檔案中斷、非 git 環境 fallback**
修改前建立 git tag。Agent 只能碰受控範圍內的檔案。建立 `STOP` 檔案可以暫停執行。非 git 專案有檔案備份 fallback。

**Subagent 架構：主 session 只派工，從不直接碰程式碼**
主 session 讀取狀態、決定派什麼工、更新調度欄位。所有程式碼修改、evaluator 執行、git 操作都在 subagent 內完成。這讓主 session 的 context 在長時間執行中保持乾淨。

## 參數

**成功條件** — 你想達到什麼（必填）

**Evaluator** — shell 指令或 `checklist`（必填）

**受控範圍** — agent 可以修改的檔案或目錄（必填）

**max** — 每個 task 最多迭代次數。預設：10。最高：50。

**runs_per_iter** — 每輪跑幾次 evaluator 取平均。預設：1。Checklist 或非確定性 evaluator 建議設 3-5。

**direction** — `higher_is_better`（預設）或 `lower_is_better`。決定分數上升是否代表改善。

**consecutive_passes** — 連續幾次通過才算穩定達標。預設：3。

**max_regression_rounds** — 外層回歸檢查的最大輪數。預設：3。

## 可選的 Skill 串接

automl 的 Phase 0、1、3 可以串接外部 skill（如果你有安裝的話）。Phase 2（核心迴圈）永遠獨立執行，無需任何外部依賴。

**Phase 0 — 意圖釐清（可選）**
目標模糊時，automl 可以交由 ideation、brainstorming 或探索類 skill 處理，再定義 task list。

**Phase 1 — 任務拆解（可選）**
大型目標可以交由 task planning skill 拆解為小型可獨立檢驗的任務。Plan review skill（商業、技術或設計視角）可以在執行前挑戰計畫假設。

**Phase 3 — 交付驗收（可選）**
Verification skill 在宣稱完成前用證據確認最終狀態。Code review skill 在交付前審查 diff。

這些都不是必須的。沒有安裝時，automl 自己處理各個 phase。

## 使用範例

詳見 `examples/` 目錄：

**`examples/code-fix-loop.md`** — 自動修復失敗的 pytest 測試，直到測試套件全部通過

**`examples/text-quality-loop.md`** — 根據 checklist 反覆改善文章品質，直到所有標準通過

## 運作原理

**Phase 0 — 釐清意圖**（如果目標 + evaluator + 範圍已就位，跳過）
automl 提取或引導用戶提供三個必要元素。三者齊全時，直接跳到 Phase 2。

**Phase 1 — 拆解 + 定 evaluator**（單一 task 目標時跳過）
大型目標拆成較小的 task，每個 task 有獨立的 evaluator 和受控範圍。執行前檢查範圍重疊。

**Phase 2 — 雙層迴圈執行**
核心引擎。主 session 派 subagent。Subagent 修改、評估、keep 或 revert，並寫入 changelog。主 session 讀取 state 決定下一步。

**Phase 3 — 交付驗收**（可選）
宣告完成前的最後確認。

## 安全護欄

- 主 session 永遠不直接編輯檔案或跑 evaluator，所有執行在 subagent 內完成
- Agent 只能修改受控範圍內的檔案
- Evaluator 檔案受保護，agent 不能修改自己的評判標準
- 修改前建立 git tag，一行指令回到起點
- STOP 檔案中斷：`touch .automl/{run_id}/STOP` 在下次派工前暫停
- Max iterations 上限防止無限燒 token
- 每次 evaluator 執行有 120 秒 timeout
- 每次執行隔離在獨立的 `.automl/{run_id}/` 目錄

## 授權

MIT
