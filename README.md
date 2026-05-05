# claude-automl

Autonomous Evaluation Loop for Claude Code — define success, let the agent iterate until it gets there.

## What It Does

claude-automl gives Claude Code a self-improvement engine. You define what "done" looks like (a test suite, a checklist, a score threshold), and the agent modifies → evaluates → keeps or reverts → repeats until it passes — without asking you anything.

Works on any domain: code, articles, trading strategies, prompt engineering, config files, ML models — anything where you can define an evaluator.

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

**Four Inputs**

**1. Goal** — what you want to achieve

**2. Evaluator** — how to check success. Four layers available: structural (form), semantic (intent), integration (system), regression (preservation). At minimum, provide a semantic evaluator.

**3. Scope** — which files the agent is allowed to modify. Narrower is safer.

**4. Skill** — which skill subagents load before each task. Use `/investigate` for debugging, `/review` for code review, or any other installed skill. Specify `none` only if no skill applies (justification required).

**Usage**

```
/automl make all tests pass
evaluator: pytest tests/ -q
scope: src/
skill: /investigate
```

That is all. automl handles the rest.

## Features

**Dual loop: per-task improvement + cross-task regression check**
Each task gets its own improvement loop. After all tasks pass, a regression check confirms they all still pass simultaneously. If a later fix breaks an earlier task, automl goes back and repairs it.

**Four-layer evaluator model (v5.2+)**
Structural verifies form (builds, format). Semantic verifies intent (tests, quality score). Integration verifies the part works in the whole (end-to-end). Regression verifies existing behavior is preserved. All four must pass for a task to be considered done.

**Two evaluator modes: shell and checklist**
Shell mode uses exit codes or numeric scores — good for tests, builds, linting, word counts. Checklist mode uses the agent as judge — good for writing quality, tone, documentation completeness, anything subjective.

**Evaluator audit gate (v5.1+)**
A Python script (`scripts/evaluator_audit.py`) mechanically validates evaluator design before execution begins — type classification, blacklist enforcement, integration ≠ semantic duplication check, regression mandatory check. Blocks bad evaluators from entering the loop.

**Red team agent (v5.4+)**
Before execution, an independent subagent attempts to game each evaluator — finding ways to make it pass without fulfilling the task intent. Covers domain-specific exploits: fake tests (code), hollow rewrites (articles), overfitting (strategies). If the red team succeeds, the evaluator is automatically strengthened and re-tested.

**Auto-resume: state persists in `.automl/{run_id}/`**
Every run has a unique ID and its own state directory. If a session is interrupted, the next `/automl` call scans for unfinished runs and picks up from the last completed iteration.

**Safety: git tag baseline, whitelist scope, STOP file interrupt, non-git fallback**
A git tag is created before any changes. The agent can only touch files inside the declared scope. Drop a `STOP` file to pause the run. On non-git projects, a file-copy fallback handles backup and revert.

**Subagent architecture: main session dispatches only, never touches code directly**
The main session reads state, decides what to dispatch, and updates scheduling fields. All code edits, evaluator runs, and git operations happen inside subagents. This keeps the main session context clean across long runs.

**Mandatory skills: every task loads a specialized skill before executing**
Phase 2 subagents invoke the declared skill via the `Skill` tool before starting each task — `/investigate` for debugging, `/review` for code review, TDD skill for new features. Specifying `none` requires explicit justification. A Skill Mapping table (`references/skill-mapping.md`) maps task types to recommended skills across all phases.

**Phase 3 subagent verification: three independent subagents replace manual review**
FINAL_VERIFICATION (haiku) re-runs all evaluators and risk scenario test cases. RISK_REVIEW (opus) traces each risk scenario through actual code paths with test quality gate. DELIVERABLE_REVIEW (codex-worker / sonnet fallback) performs diff-aware review with security analysis. All three return structured JSON for reliable parsing.

**Model routing: right model for each job**
Every Agent call carries a `model` parameter — haiku for mechanical tasks, sonnet for execution, opus for deep analysis. Override per-model via `params.model_overrides` in the state file.

**Cross-domain support**
Built for any improvement task: code (tests, builds), articles (quality checklists), trading strategies (backtests, sharpe ratios), prompt engineering (output quality), config files (health checks), ML models (validation accuracy). The evaluator model and red team game methods adapt to each domain.

## Parameters

**Goal** — what you want to achieve (required)

**Evaluator** — four layers: structural (form), semantic (intent, required), integration (system, feature tasks), regression (preservation, feature + refactor tasks). Shell command or `checklist` mode.

**Scope** — files or directories the agent may modify (required)

**Skill** — skill subagents load before each Phase 2 task (required; use `none` with justification if no skill applies)

**max** — max iterations per task. Default: 10. Maximum: 50.

**runs_per_iter** — how many times to run the evaluator per iteration, averaged. Default: 1. Recommended 3-5 for checklist or non-deterministic evaluators.

**direction** — `higher_is_better` (default) or `lower_is_better`. Controls whether an increasing score counts as improvement.

**consecutive_passes** — how many consecutive passing iterations required before a task is considered stable. Default: 3.

**max_regression_rounds** — how many rounds of outer regression check to attempt before giving up on conflicting tasks. Default: 3.

**Flags**

- `--no-codex`：強制不用 codex-dispatch，所有 codex 場景 fallback claude:sonnet（保留條 #3 opus）。給沒裝 codex-dispatch 的用戶 / 想省 ChatGPT quota 的場景。
- `--goal`：Tier 2 autonomous mode（無 budget cap，跑到完）。對齊業界 longer-horizon agentic direction。
- `--cap`：與 `--goal` 同用，opt-in 軟煞車（max_total_ticks=50, max_wall_minutes=480, Phase 3 retry_count<=2）
- `--max-ticks=N` / `--max-wall=M`：custom cap（僅 `--cap` 生效時有效）
- `--autonomous`：v5.10 deprecation alias = `--goal --cap`，v5.11 移除

## Skill Integrations

Skills are a first-class part of automl. Phase 2 requires a skill on every task. Phases 0, 1, and 3 have recommended defaults.

**Phase 0 — intent clarification**
Recommended: `/design-consultation`. If your goal is vague, automl hands off to a design or ideation skill before defining the task list. Falls back to self-guided clarification if not installed.

**Phase 1 — task decomposition**
Default: `/autoplan` (runs CEO + eng + design review with 6-principle auto-decisions). A plan review skill stress-tests the task list before execution begins. Falls back to automl's own decomposition if not installed.

**Phase 2 — execution (required)**
Each task must declare a skill. Recommended mappings: bug fix → `/investigate`, new feature → TDD skill, refactor → `/review`, performance → `/benchmark`. See `references/skill-mapping.md` for the full lookup table.

**Phase 3 — delivery verification (required)**
Three subagents run in sequence: FINAL_VERIFICATION, RISK_REVIEW, CODE_REVIEW. Recommended skills: `/investigate` or `/cso` for risk review, `/review` for code review. Phase 3 retries up to 2 times if regressions are found, logging each failure cause.

## Examples

See the `examples/` directory:

**`examples/code-fix-loop.md`** — auto-fix failing pytest tests until the suite is green

**`examples/text-quality-loop.md`** — improve writing quality against a checklist until all criteria pass

## How It Works

**Phase 0 — Clarify intent** (skipped if goal + evaluator + scope + skill are already present)
automl extracts or elicits the four required inputs. If you provide all four upfront, this phase is skipped entirely.

**Phase 1 — Decompose + define evaluators** (skipped for single-task goals)
Large goals get broken into smaller tasks, each with its own four-layer evaluator and scope. Scope overlap is checked before execution begins.

**Phase 1.5 — Quality gates** (automatic, not skippable)
Three steps: (a) evaluator_audit.py mechanically validates evaluator design, (b) red team agent tries to game each evaluator, (c) auto-fix if red team finds exploits. Only after all three pass does execution begin.

**Phase 2 — Dual-loop execution**
The core engine. Main session dispatches subagents. Subagents modify, evaluate, keep or revert, and write to the changelog. Main session reads state and decides what to dispatch next.

**Phase 3 — Delivery verification**
Three subagents run in sequence: FINAL_VERIFICATION re-runs all evaluators and risk scenario test cases; RISK_REVIEW traces each risk scenario through actual code paths; CODE_REVIEW performs diff-aware review with security analysis. Phase 3 supports checkpoint/resume via `phase3.step` in the state file and retries up to 2 times if regressions are found.

## Safety

- Main session never directly edits files or runs evaluators — all execution happens in subagents
- Agent can only modify files inside the declared scope
- Evaluator files are protected — the agent cannot modify its own judge
- Git tag is created before any changes; one command returns you to the starting point
- STOP file interrupt: `touch .automl/{run_id}/STOP` pauses before the next dispatch
- Max iterations cap prevents runaway token usage
- Each evaluator call has a 120-second timeout
- Every run is isolated in its own `.automl/{run_id}/` directory
- Phase 3 retry limit: max 2 retries in `--cap` mode; `--goal` no-cap defaults to `repeat_loop_detector` fallback, with `retry_log` recording each regression's cause and affected tasks
- Phase 3 skill constraint: DELIVERABLE_REVIEW and RISK_REVIEW subagents are restricted to their declared skills and diff scope — cannot expand into Phase 2 execution
- Red team safety cap: max 2 rounds per task, max 2 auto-fix rounds — prevents token waste on evaluators that cannot be strengthened

## Recommended Skills

automl's mandatory skill system works best with these skill ecosystems. automl itself has no hard dependencies — you can always use `skill: none` — but the default skill mappings in `references/skill-mapping.md` reference skills from these projects.

**[gstack](https://github.com/garrytan/gstack)** — Strongly recommended. Most of automl's default skill mappings come from gstack:
- Phase 1: `/autoplan` (auto-runs CEO + eng + design review)
- Phase 2: `/investigate` (systematic debugging), `/careful` (destructive command safety)
- Phase 3: `/review` (pre-landing review with SQL/LLM/dependency security), `/cso` (security audit), `/qa-only` (report-only QA), `/benchmark` (performance regression), `/design-review` (visual QA)

**[superpowers](https://github.com/obra/superpowers)** — Recommended. Provides several skills used in automl's skill mapping:
- Phase 2: `superpowers:test-driven-development`, `superpowers:writing-skills`
- Phase 3: `superpowers:requesting-code-review`, `superpowers:systematic-debugging`, `superpowers:verification-before-completion`

**[Anthropic Knowledge Work Plugins](https://github.com/anthropics/knowledge-work-plugins)** — Optional. Provides domain-specific skills:
- Phase 2: `engineering:architecture` (refactoring), `design:design-critique`
- Phase 3: `engineering:code-review`, `design:design-critique`
- Also includes `swift-concurrency`, `swiftui-expert-skill`

**[notebooklm-py](https://github.com/teng-lin/notebooklm-py)** — Recommended for v5.7+ Environment Gap Research Gate. When SCD C5 (Test Environment Gap) confidence is low, automl uses NotebookLM deep research to validate assumptions about production behavior before designing evaluators. 300+ web sources + multi-round Q&A produces significantly better evaluators than guessing. Falls back to WebSearch if not installed.
- Install: `pip install notebooklm-py && notebooklm skill install`
- Phase 1 Step B': `notebooklm source add-research` + `notebooklm ask` (multi-round)
- Phase 2 Emergency Gate: same workflow when subagent is stuck on production-only behavior

**Without any of these installed**, automl still works — subagents use their built-in knowledge. But with the recommended skills, hit rates improve significantly and Phase 3 reviews catch more issues.

## License

MIT

---

# claude-automl（繁體中文）

Claude Code 自主優化迴圈 — 定義成功條件，讓 agent 自動迭代直到達標。

## 這是什麼

claude-automl 為 Claude Code 提供自我改善引擎。你定義「完成」的標準（測試套件、checklist、分數門檻），agent 自動執行「修改 → 評估 → keep 或 revert → 重複」，直到通過 — 全程不打擾你。

適用於任何領域：程式碼、文章、交易策略、prompt 工程、設定檔、ML 模型 — 只要你能定義 evaluator。

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

**四個必要元素**

**1. 成功條件** — 你想達到什麼

**2. Evaluator** — 如何判斷是否成功。四層模型：structural（形式）、semantic（意圖，必填）、integration（系統，feature task 必填）、regression（既有行為保全，feature + refactor 必填）。每層可以是 shell 指令或 checklist。

**3. 受控範圍** — agent 可以修改哪些檔案。範圍越窄越安全。

**4. Skill** — subagent 在每個 task 執行前載入的 skill。除錯用 `/investigate`，code review 用 `/review`，或其他已安裝的 skill。只有在真的沒有適用 skill 時才指定 `none`（需附理由）。

**使用方式**

```
/automl 讓 pytest 全部通過
evaluator: pytest tests/ -q
範圍: src/
skill: /investigate
```

就這樣。automl 處理其餘一切。

## 功能特色

**雙層迴圈：per-task 優化 + 跨 task 回歸檢查**
每個 task 有自己的優化迴圈。所有 task 通過後，回歸檢查確認它們同時仍然通過。如果後面的修復破壞了前面的 task，automl 會回去修復。

**四層 evaluator 模型（v5.2+）**
Structural 驗形式（build、格式）。Semantic 驗意圖（測試、品質分數）。Integration 驗零件裝回系統（end-to-end）。Regression 驗既有行為不壞。四層都過才算 task 完成。

**兩種 evaluator 模式：shell 和 checklist**
Shell 模式使用 exit code 或數值分數，適合測試、build、linting、字數檢查。Checklist 模式讓 agent 自己當評判，適合寫作品質、語氣、文件完整性等主觀標準。

**Evaluator 品質關卡（v5.1+）**
Python 腳本（`scripts/evaluator_audit.py`）在 Phase 2 開始前機械性驗證 evaluator 設計 — type 分類、黑名單、integration ≠ semantic 重複檢查、regression 必填檢查。擋住設計不良的 evaluator。

**紅隊 agent（v5.4+）**
執行前，獨立 subagent 嘗試 game 每個 evaluator — 找到讓 evaluator pass 但意圖未達成的方式。涵蓋跨領域手法：假 test（程式碼）、湊字數空洞改寫（文章）、過度擬合（策略）。紅隊成功 → 自動強化 evaluator 並重測。

**自動續傳：狀態持久化在 `.automl/{run_id}/`**
每次執行有唯一 run ID 和獨立的狀態目錄。Session 中斷後，下次 `/automl` 自動掃描未完成的 run，從最後完成的迭代繼續。

**安全護欄：git tag 備份、受控範圍白名單、STOP 檔案中斷、非 git 環境 fallback**
修改前建立 git tag。Agent 只能碰受控範圍內的檔案。建立 `STOP` 檔案可以暫停執行。非 git 專案有檔案備份 fallback。

**Subagent 架構：主 session 只派工，從不直接碰程式碼**
主 session 讀取狀態、決定派什麼工、更新調度欄位。所有程式碼修改、evaluator 執行、git 操作都在 subagent 內完成。這讓主 session 的 context 在長時間執行中保持乾淨。

**強制 Skill：每個 task 在執行前都載入對應的專業 skill**
Phase 2 subagent 在執行每個 task 前，透過 `Skill` 工具 invoke 宣告的 skill — 除錯用 `/investigate`，code review 用 `/review`，新功能用 TDD skill。指定 `none` 需附理由。`references/skill-mapping.md` 提供 task 類型到推薦 skill 的完整對照表，涵蓋所有 phase。

**Phase 3 三 subagent 驗收：三個獨立 subagent 取代人工 review**
FINAL_VERIFICATION（haiku）重跑所有 evaluator 和 risk scenario 測試案例。RISK_REVIEW（opus）追蹤每個 risk scenario 在實際程式碼路徑上的走向，含 test quality gate。DELIVERABLE_REVIEW（codex-worker / sonnet fallback）做 diff-aware review 含安全分析。三者均回傳結構化 JSON，確保可靠解析。

**Model routing：每個工作用對應的模型**
每次 Agent 呼叫都帶 `model` 參數 — haiku 處理機械性任務，sonnet 執行主要工作，opus 做深度分析。可透過 state file 中的 `params.model_overrides` 自訂各 model 對應。

**跨領域支援**
適用於任何改善任務：程式碼（測試、build）、文章（品質 checklist）、交易策略（回測、sharpe ratio）、prompt 工程（output 品質）、設定檔（健康檢查）、ML 模型（validation accuracy）。Evaluator 模型和紅隊 game 手法依領域自適應。

## 參數

**成功條件** — 你想達到什麼（必填）

**Evaluator** — 四層：structural（形式）、semantic（意圖，必填）、integration（系統，feature task）、regression（保全，feature + refactor）。Shell 指令或 checklist 模式。

**受控範圍** — agent 可以修改的檔案或目錄（必填）

**Skill** — Phase 2 subagent 在每個 task 執行前載入的 skill（必填；若真的沒有適用 skill，填 `none` 並附理由）

**max** — 每個 task 最多迭代次數。預設：10。最高：50。

**runs_per_iter** — 每輪跑幾次 evaluator 取平均。預設：1。Checklist 或非確定性 evaluator 建議設 3-5。

**direction** — `higher_is_better`（預設）或 `lower_is_better`。決定分數上升是否代表改善。

**consecutive_passes** — 連續幾次通過才算穩定達標。預設：3。

**max_regression_rounds** — 外層回歸檢查的最大輪數。預設：3。

## Skill 串接

Skill 在 automl 是一等公民。Phase 2 的每個 task 都必須宣告 skill。Phase 0、1、3 有預設的推薦 skill。

**Phase 0 — 意圖釐清**
建議：`/design-consultation`。目標模糊時，automl 交由設計或 ideation skill 處理，再定義 task list。未安裝時退回 automl 自己引導。

**Phase 1 — 任務拆解**
預設：`/autoplan`（自動跑 CEO + eng + design 三視角 review，含 6 原則自動決策）。Plan review skill 在執行前挑戰 task list 假設。未安裝時退回 automl 自己拆解。

**Phase 2 — 執行（必填）**
每個 task 必須宣告 skill。推薦對應：bug 修復 → `/investigate`，新功能 → TDD skill，重構 → `/review`，效能 → `/benchmark`。完整對照表見 `references/skill-mapping.md`。

**Phase 3 — 交付驗收（必填）**
三個 subagent 依序執行：FINAL_VERIFICATION、RISK_REVIEW、CODE_REVIEW。Risk review 建議用 `/investigate` 或 `/cso`，code review 建議用 `/review`。發現 regression 最多重試 2 次（`--cap` 模式；`--goal` no-cap 預設由 repeat_loop_detector 兜底），每次失敗原因記錄在 retry_log。

## 使用範例

詳見 `examples/` 目錄：

**`examples/code-fix-loop.md`** — 自動修復失敗的 pytest 測試，直到測試套件全部通過

**`examples/text-quality-loop.md`** — 根據 checklist 反覆改善文章品質，直到所有標準通過

## 運作原理

**Phase 0 — 釐清意圖**（如果目標 + evaluator + 範圍 + skill 已就位，跳過）
automl 提取或引導用戶提供四個必要元素。四者齊全時，直接跳到 Phase 2。

**Phase 1 — 拆解 + 定 evaluator**（單一 task 目標時跳過）
大型目標拆成較小的 task，每個 task 有獨立的四層 evaluator 和受控範圍。執行前檢查範圍重疊。

**Phase 1.5 — 品質關卡**（自動執行，不可跳過）
三步：(a) evaluator_audit.py 機械性驗證 evaluator 設計，(b) 紅隊 agent 嘗試 game evaluator，(c) 紅隊發現漏洞時自動修復。三步都通過才開始執行。

**Phase 2 — 雙層迴圈執行**
核心引擎。主 session 派 subagent。Subagent 修改、評估、keep 或 revert，並寫入 changelog。主 session 讀取 state 決定下一步。

**Phase 3 — 交付驗收**
三個 subagent 依序執行：FINAL_VERIFICATION 重跑所有 evaluator 和 risk scenario 測試案例；RISK_REVIEW 追蹤每個 risk scenario 在實際程式碼路徑上的走向，含 test quality gate；DELIVERABLE_REVIEW 做 diff-aware review 含安全分析。透過 state file 中的 `phase3.step` 欄位支援 checkpoint/resume，最多重試 2 次。

## 安全護欄

- 主 session 永遠不直接編輯檔案或跑 evaluator，所有執行在 subagent 內完成
- Agent 只能修改受控範圍內的檔案
- Evaluator 檔案受保護，agent 不能修改自己的評判標準
- 修改前建立 git tag，一行指令回到起點
- STOP 檔案中斷：`touch .automl/{run_id}/STOP` 在下次派工前暫停
- Max iterations 上限防止無限燒 token
- 每次 evaluator 執行有 120 秒 timeout
- 每次執行隔離在獨立的 `.automl/{run_id}/` 目錄
- Phase 3 重試上限：最多重試 2 次，每次記錄 regression 原因和受影響 task — 防止 Phase 3 無限迴圈
- Phase 3 skill 範圍限制：DELIVERABLE_REVIEW 和 RISK_REVIEW subagent 限定在宣告的 skill 和 diff 範圍內，不能擴展成 Phase 2 執行
- 紅隊安全閥：每個 task 最多 2 輪紅隊、最多 2 輪自動修復 — 防止在無法強化的 evaluator 上浪費 token

## 推薦 Skill 生態系

automl 的強制技能機制搭配這些 skill 生態系效果最好。automl 本身沒有硬依賴 — 你可以填 `skill: none` — 但 `references/skill-mapping.md` 的預設對照表引用了以下專案的 skill。

**[gstack](https://github.com/garrytan/gstack)** — 強烈推薦。automl 大部分預設 skill 來自 gstack：
- Phase 1：`/autoplan`（自動跑 CEO + eng + design 三視角 review）
- Phase 2：`/investigate`（系統性 debug）、`/careful`（破壞性指令防護）
- Phase 3：`/review`（含 SQL/LLM/dependency 安全分析）、`/cso`（安全審計）、`/qa-only`（純報告 QA）、`/benchmark`（效能回歸偵測）、`/design-review`（視覺 QA）

**[superpowers](https://github.com/obra/superpowers)** — 推薦。提供多個 automl skill mapping 使用的技能：
- Phase 2：`superpowers:test-driven-development`、`superpowers:writing-skills`
- Phase 3：`superpowers:requesting-code-review`、`superpowers:systematic-debugging`、`superpowers:verification-before-completion`

**[Anthropic Knowledge Work Plugins](https://github.com/anthropics/knowledge-work-plugins)** — 選用。提供領域專業技能：
- Phase 2：`engineering:architecture`（重構）、`design:design-critique`
- Phase 3：`engineering:code-review`、`design:design-critique`
- 也包含 `swift-concurrency`、`swiftui-expert-skill`

**[notebooklm-py](https://github.com/teng-lin/notebooklm-py)** — v5.7+ Environment Gap Research Gate 推薦。當 SCD C5（測試環境差距）信心不足時，automl 用 NotebookLM deep research 驗證 production 環境假設再設計 evaluator。300+ 網路來源 + 多輪問答，效果遠優於猜測。未安裝時 fallback 到 WebSearch。
- 安裝：`pip install notebooklm-py && notebooklm skill install`
- Phase 1 Step B'：`notebooklm source add-research` + `notebooklm ask`（多輪）
- Phase 2 Emergency Gate：subagent 卡在 production-only 行為時同樣觸發

**以上都沒裝也能用** — subagent 會用自身的內建知識。但搭配推薦 skill，命中率顯著提升，Phase 3 review 也能抓到更多問題。

## 授權

MIT
