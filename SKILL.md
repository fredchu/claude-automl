---
name: automl
version: 5.4.0
description: |
  Autonomous Evaluation Loop — 從對齊意圖到自主執行的完整引擎。
  四階段：Phase 0 釐清 → Phase 1 拆解定標準 → Phase 2 執行+自我檢驗 loop → Phase 3 交付驗收。
  每個 Phase 可串接已安裝的 skill，也可以獨立跑（用戶已經想好目標就直接跳到 Phase 2）。
  觸發詞：/automl、「讓它跑到達標」、「自動優化直到」、「無限循環直到完成」。
allowed-tools:
  - Agent
  - Bash
  - Read
  - Write
  - Edit
  - Grep
  - Glob
---

# /automl — Autonomous Evaluation Loop v5

## 核心公式

```
Phase 0: 釐清意圖（可選）
Phase 1: 拆解 + 定檢驗標準（可選）
Phase 2: 雙層循環
  外層 — 全局回歸（regression loop）：
    for each task in task_list:
      內層 — 單 task 優化（improvement loop）：
        while 未達標 && 迭代次數 < max_iter:
            agent 在受控範圍內修改（最小改動）
            自動跑 evaluator（runs_per_iter 次）
            改善 → git commit (keep)
            退步 → git checkout -- [受控檔案] (revert)
            記錄到 changelog → 換策略繼續
    全部 task 內層都達標後 → 回歸檢查：重跑所有 task 的 evaluator
    有任何 task 被後續改動破壞 → 回到那個 task 的內層重修
    全部同時通過 → Phase 3
Phase 3: 交付驗收
```

**六個必要元素（Phase 2 開始前必須就位）：**
1. **成功條件** — 明確、可量化（測試通過、分數 > X、build 成功、字數 < Y、輸出符合格式…）
2. **Evaluator 四層** — 每個 task 的驗證分四層：
   - **Structural**（可選）：產出形式/格式正確（編譯通過、語法正確、格式合規）
   - **Semantic**（**必填**）：產出意圖達成（已知輸入→預期輸出、功能正確、指標達標）
   - **Integration**（**feature 必填**）：零件裝回系統後，end-to-end 新行為正確
   - **Regression**（**feature + refactor 必填**）：既有行為沒壞（baseline 必須 PASS，反轉 inversion）
3. **Semantic Evaluator 類型** — 必填欄位 `evaluator_semantic_type`，強制分類：
   - `test_runner`：自動化測試（scope 必須含 test file）
   - `eval_script`：自訂腳本執行+評分
   - `metric`：提取數值比較門檻
   - `checklist`：LLM-as-judge（最少 3 題）
   - `assertion`：驗 pattern 存在/不存在（**僅限 refactor，feature 禁用**）
4. **受控範圍** — 哪些檔案 agent 可以修改（越窄越好）
5. **強制技能** — 每個 task 必須指定執行技能（預設是「帶技能」，不帶才是例外）。如果真的不需要 skill，填 `skill: none` 且必須附理由。
6. **Task 類型** — `feature`（新增/修改功能）或 `refactor`（功能不變，改內部實作）。影響 baseline 反轉測試和 evaluator 類型限制。

**三條驗證原則：**
1. **Evaluator 即 Spec** — evaluator 不是事後加的檢查，而是 task 規格的可執行形式。寫不出好 evaluator = 不夠理解 task。
2. **驗意圖，不驗形式** — evaluator 必須驗證 task 的意圖（intent）是否達成，不只驗產出的形式（form）。形式正確是必要條件，不是充分條件。
3. **不可被 gaming** — 如果 subagent 能在不真正完成任務的情況下讓 evaluator pass，這個 evaluator 就是壞的。

---

## Phase 偵測 + 懶加載

**偵測方式：** 看用戶的訊息是否已包含目標 + evaluator + 範圍 + 強制技能。

- **四者齊全** → 直接進 Phase 2（本檔案已包含所有需要的資訊）
- **缺任何一個** → 讀 `references/automl-reference.md` 取得 Phase 0/1 指引，引導用戶補齊；同時讀 `references/skill-mapping.md` 取得技能建議
- **Phase 2 完成後** → 讀 `references/automl-reference.md` 取得 Phase 3 交付驗收指引

> Phase 0/1/3 的 skill 串接、evaluator 模式詳解、參數說明、使用範例，全在 reference 檔案中。
> Phase 2 直跑（最常見路徑）不需要讀任何額外檔案。

---

## Evaluator Audit Gate（Phase 1 → Phase 2 之間，不可跳過）

> **解決的問題：** 主 session 設計 evaluator 又自己判品質 = 球員兼裁判。
> **解法：** 用腳本做機械性品質關卡，0 成本、確定性、不可被說服跳過。

Phase 1 完成 state.json 後，Phase 2 開始前，**必須跑 evaluator audit 腳本**：

```bash
python3 "$(dirname "$(readlink -f "$0" 2>/dev/null || echo "$0")")/../scripts/evaluator_audit.py" .automl/{run_id}/state.json
# 或直接用絕對路徑：
python3 ~/.claude/skills/automl/scripts/evaluator_audit.py .automl/{run_id}/state.json
```

- `exit 0` → 進入 Phase 2
- `exit 1` → **BLOCKED** — 修改 evaluator 設計後重跑，直到通過

### 腳本檢查什麼

| 檢查 | 規則 | 為什麼 |
|------|------|--------|
| **type 必填** | `evaluator_semantic_type` 必須是 5 種之一 | 強制分類，防止主 session 含糊帶過 |
| **feature 禁用 assertion** | `assertion` + `feature` = BLOCKED | feature 需要驗行為（outcome），不是驗 pattern（property） |
| **test_runner 需 test file** | scope 必須含 test 檔案 | deliverable 無法包含測試 = 無法驗行為 |
| **checklist 最少 3 題** | `checklist_items` < 3 = BLOCKED | 太少 = 太粗，無法驗意圖 |
| **metric 需比較** | 必須含比較運算或呼叫腳本 | 只提取數字不比較 = 沒有判定標準 |
| **structural ≠ semantic** | 兩層不可相同 | 相同 = semantic 層沒有增量價值 |
| **黑名單** | grep/wc/test -f 不可作為 semantic（assertion 除外） | 這些是 property check，不是 outcome check |
| **空值** | evaluator_semantic 不可為空（checklist 除外） | 空 = 沒有驗證 |
| **impact_path 必填** | feature task 時 `impact_path` 物件存在 + `user_outcome` 非空且≥10字元 | feature task 沒填 impact_path = 沒想清楚改動如何影響用戶 |
| **integration 必填** | feature task 時 `evaluator_integration` 非空（無例外） | feature 改了零件卻不驗系統 = v5.1 的失敗模式 |
| **integration ≠ semantic** | `evaluator_integration` 存在時，按 mode 分策略比較 | 複製貼上 semantic 當 integration = 沒有增量驗證 |
| **regression 必填（v5.3+）** | feature + refactor task 的 `evaluator_regression` 非空（版本門控：`schema_version >= 5.3`） | 沒有 regression evaluator = 不驗既有行為 |
| **regression ≠ 其他層（v5.3+）** | `evaluator_regression` 不可與 structural / semantic / integration 相同 | 複製貼上其他層 = regression 沒有增量驗證 |
| **regression 非 trivial（v5.3+）** | `evaluator_regression` 不可是 trivial/static（同 semantic 黑名單） | `echo pass` 不是有效的 regression 驗證 |

### Phase 1.5 — 品質關卡（三步）

```
Phase 1.5a: evaluator_audit.py    ← 腳本機械性驗證（type 分類、黑名單、impact_path、integration、regression）
Phase 1.5b: RED_TEAM agent        ← 紅隊對抗（嘗試 game evaluator，2 輪上限）
Phase 1.5c: 自動修復              ← 紅隊 blocked 時，主 session 修 evaluator → 重跑紅隊（最多 2 輪）
Phase 2:    baseline inversion    ← 擋沒有鑑別力的 evaluator（自動，baseline subagent）
            ↳ semantic/integration: feature 必須 FAIL（驗「改善」有鑑別力）
            ↳ regression: feature + refactor 必須 PASS（驗「不變」的 evaluator 本身有效）
Phase 3:    RISK_REVIEW           ← impact path 完整性 + test quality gate + regression 覆蓋檢查（opus subagent）
Phase 3:    DELIVERABLE_REVIEW    ← 擋品質不足的 deliverable（LLM 判斷，opus/codex）
```

### Phase 1.5b — RED_TEAM Agent

> **解決的問題：** ①②③（反轉/意圖覆蓋/替代測試）+ falsification 都是主 session 主觀判斷，容易自我說服。
> **解法：** 派獨立 subagent 當紅隊，實際嘗試 game evaluator。抓到 = 設計有缺陷，抓不到 = 通過。

**觸發條件：** Phase 1.5a evaluator_audit.py 通過後，對每個 feature task 自動跑。refactor task 跳過。

**安全閥：** 紅隊最多 2 輪。2 輪都找不到 game 方式 → 視為通過。防止紅隊無限消耗 token。

```
RED_TEAM_PROMPT：

你是 automl 的紅隊 agent。你的任務是嘗試 game evaluator — 找到一種方式讓 evaluator pass 但實際上沒有達成 task 意圖。

== 環境 ==
工作目錄：{cwd}

== 可用工具 ==
Bash, Read, Grep, Glob

== Task ==
Task ID：{task_id}
描述：{task_description}
scope：{scope}

== Evaluators ==
Structural：{evaluator_structural}
Semantic：{evaluator_semantic}（type: {evaluator_semantic_type}）
Integration：{evaluator_integration}
Regression：{evaluator_regression}

== 規則 ==
- 不修改 evaluator 本身，只修改 scope 內的檔案
- 目標：讓所有 evaluator pass，但 task 意圖沒達成
- 常見 game 手法（通用）：
  1. 硬塞 expected output（不走正常邏輯，直接產出預期結果）
  2. 刪除或跳過 edge case（主路徑 pass，邊緣情境壞掉）
  3. 形式正確但內容空洞（通過格式/長度檢查但無實質內容）
- 程式碼領域補充：
  4. 寫假 test（test 永遠 pass，不驗真正行為）
  5. mock-only regression（mock 掉真正依賴，regression test 形同虛設）
- 文章/內容領域補充：
  6. 湊字數或複製既有段落通過 word count / 相似度門檻
  7. 改措辭但論點空洞，通過 checklist 表面項但缺乏深度
- 策略/量化領域補充：
  8. 過度擬合回測區間（in-sample 完美，out-of-sample 崩壞）
  9. cherry-pick 有利時段或 look-ahead bias
- 最多嘗試 2 輪
- 每輪：改 scope 內檔案 → 跑所有 evaluator → 檢查是否全 pass
- 全 pass 但意圖未達成 = 找到 game 方式 → BLOCKED
- 無法讓 evaluator pass 而不達成意圖 = evaluator 有效 → PASSED

== 完成後回傳（嚴格遵守此 JSON 格式）==
\`\`\`json
{
  "status": "BLOCKED" | "PASSED",
  "rounds_used": 1 | 2,
  "findings": [
    {
      "id": "C1",
      "game_method": "描述 game 手法",
      "evaluator_gap": "哪個 evaluator 被 game 了、為什麼",
      "fix_suggestion": "建議怎麼修 evaluator"
    }
  ]
}
\`\`\`

回傳後必須 revert 所有改動：
- git 模式：git checkout -- {scope}
- file-backup 模式：從 snapshot 還原
```

### Phase 1.5c — 紅隊 BLOCKED 自動修復

紅隊回傳 `BLOCKED` 時，主 session 執行以下流程：

1. **解析紅隊 JSON**：讀取 `findings` 陣列
2. **修 evaluator**：根據 `fix_suggestion`，修改對應 evaluator（更嚴格的 assertion、加 integration test 等）
3. **更新 state.json**：把修改後的 evaluator 寫入 task
4. **重跑 Phase 1.5a**：evaluator_audit.py（確保修改後仍通過機械性檢查）
5. **重跑 Phase 1.5b**：紅隊（確認 game 已被堵住）
6. **最多 2 輪修復**：修復 2 次後紅隊仍 BLOCKED → 停止，報告無法解決，讓用戶介入

---

## Phase 2 — 執行 + 自我檢驗 Loop

> 這是 automl 的核心引擎。
> **主 session 是調度器，不是執行者。所有修改都由 subagent 完成。**

### 主 session 的角色（硬性規則，不可違反）

```
Phase 2 期間，主 session 只做四件事：
1. 讀 state file，決定下一步派什麼工
2. 用 Agent tool 派 subagent 執行
3. 收 subagent 回傳，更新 state file 的調度欄位（current_task、phase、regression_round、checkpoint_summary）
   （task 狀態欄位由 subagent 直接寫入，主 session 只讀取確認）
4. 判斷是否進入下一個 task / 回歸檢查 / Phase 3
5. Phase 3 期間，調度三個驗收 subagent（FINAL_VERIFICATION / RISK_REVIEW / DELIVERABLE_REVIEW）

主 session 禁止：
- ❌ 直接使用 Edit / Write 修改受控範圍內的檔案
- ❌ 直接用 Bash 跑 evaluator
- ❌ 直接讀原始碼分析（subagent 會做）
- ❌ Phase 3 期間直接讀 diff、做 review、跑驗證（所有驗收都透過 subagent）
唯一例外：讀寫 .automl/{run_id}/ 下的 state.json 和 changelog.md

違反此規則 = 上下文污染 = bug。
即使任務看起來「很小改一行就好」，也必須派 subagent。

所有 Agent 呼叫必須帶 mode="auto"：
- 讓 subagent 自主執行 Bash、Edit、git 操作，不跳權限確認
- 否則每步都要用戶按確認，違反「不主動問用戶」原則
```

### 主 session 決策樹（每個 loop tick 的邏輯）

```
讀 state.json
├── phase == "done" → 已完成，報告結果
├── 有 subagent 失敗/timeout 記錄？
│   ├── 重試次數 < 2 → 重新派同一個 subagent
│   └── 重試次數 >= 2 → 標記 task 為 stuck，跳到下一個 task
├── current_task 還沒跑 baseline？
│   └── 派 BASELINE_PROMPT subagent → 等回傳
├── current_task baseline 是 ERROR？
│   └── 停止整個 run，報告 evaluator 設定問題
├── current_task status == "in_progress" 或 "not_started" 或 "needs_continue"？
│   └── 派 TASK_LOOP_PROMPT subagent → 等回傳
├── current_task status == "failed"？
│   └── 標記 task 為 failed（已耗盡 max_iter），跳到下一個 task
├── current_task status == "stuck"？
│   └── 標記 task 為 stuck，跳到下一個 task
├── current_task status == "passed" && 還有下一個 task？
│   └── current_task++ → 回到頂部（跑下一個 task 的 baseline）
├── 所有 task 都 passed？
│   └── 派 REGRESSION_CHECK_PROMPT subagent → 等回傳
├── regression 結果全部 pass？
│   └── 進入 Phase 3（見下方 Phase 3 調度邏輯）
├── regression 有失敗的 task？
│   ├── regression_round < max_regression_rounds
│   │   └── 對失敗的 task 重新派 TASK_LOOP_PROMPT → 完成後再跑 regression
│   └── regression_round >= max_regression_rounds
│       └── 停止，報告 task 衝突
└── 不應到達此處 → 報告異常狀態
```

### Phase 3 主 session 調度邏輯

**斷點續傳**：Phase 3 開始時，讀 `state.json` 的 `phase3.step` 欄位，從上次中斷的 step 繼續（跟 Phase 2 的 Step 0 同理）。已完成的 step 結果保存在 state file 中，不重跑。

**回退計數**：`retry_count` 是整個 Phase 3 流程共用的 counter。語意：**Phase 3 總共最多回退 Phase 2 兩次**。不管是哪個 step 觸發的回退，都計入同一個 counter。超過 2 次代表 Phase 2 反覆修不好，繼續重試沒有意義。

**回退後的重啟流程**：任何 step 觸發回退時：
1. `retry_count++`，記錄原因到 `retry_log`
2. 重置 `phase3.step = 1`（Phase 3 從頭開始，因為 Phase 2 修改可能影響所有驗收結果）
3. 把 `state.json` 的 `phase` 改回 `2`，記錄需要修復的 task
4. Phase 2 對失敗的 task 重跑 loop → regression check 通過後 → `phase` 自動切回 `3`
5. 主 session 讀到 `phase == 3` + `phase3.step == 1` → 從 FINAL_VERIFICATION 重新開始

```
讀 state.json（phase == 3）
├── phase3.retry_count >= 2？
│   └── 停止，報告「Phase 3 回退已達上限（2/2），仍有未解問題」
│       列出每次回退的原因（從 phase3.retry_log 讀取）
│
├── 從 phase3.step 繼續（斷點續傳）：
│
├── step 1: 派 Claude agent (model="haiku") 跑 FINAL_VERIFICATION → 等回傳
│   ├── 回傳正常 JSON？
│   │   ├── 解析 status == "pass" → 記錄結果到 state，phase3.step = 2，繼續
│   │   └── 解析 status == "fail" → retry_count++，記錄原因到 retry_log，回 Phase 2
│   └── 回傳異常（非 JSON / timeout / subagent 錯誤）？
│       ├── 重試 1 次（同一 step）
│       └── 連續 2 次異常 → 停止，報告 FINAL_VERIFICATION subagent 錯誤
│
├── step 2: RISK_REVIEW（可能多個 dispatch，按 phase3_skill 分組）
│   ├── 按 phase3_skill 分組 task 的 risk_scenarios + impact_path
│   │   例：group_A（/investigate）= Task 1, 3 的 scenarios + impact_path；group_B（/cso）= Task 2 的 scenarios
│   ├── 對每個 group 派一個 Claude agent (model="opus") 跑 RISK_REVIEW → 等回傳
│   ├── 合併所有 group 的回傳結果
│   │   ├── 全部 status == "safe" → 記錄結果，phase3.step = 3，繼續
│   │   └── 任一 status == "has_bugs" → retry_count++，記錄 bug 到 retry_log，回 Phase 2
│   └── 任一 group 回傳異常？ → 同上重試邏輯
│
├── step 3: 派 codex-worker / Claude agent (model="sonnet") 跑 DELIVERABLE_REVIEW → 等回傳
│   ├── 環境偵測：檢查 /Users/fredchu/bin/codex-dispatch 是否存在
│   │   ├── 存在 → 用 codex-worker agent（ChatGPT 額度）
│   │   └── 不存在 → 派 Claude Agent（model: sonnet）
│   ├── 回傳正常 JSON？
│   │   ├── 解析 status == "pass" 或 "has_important_only" → 記錄，繼續
│   │   └── 解析 status == "has_critical" → retry_count++，記錄到 retry_log，回 Phase 2
│   └── 回傳異常？ → 同上重試邏輯；codex-worker 失敗自動 fallback 到 Claude Agent（不算重試）
│
└── 三個都通過 → 編譯最終報告 + verification checklist，phase = "done"
```

**Timeout**：Phase 3 各 step 的 Agent call timeout：
- FINAL_VERIFICATION（haiku）：300 秒
- RISK_REVIEW（opus）：600 秒
- DELIVERABLE_REVIEW（codex-worker/sonnet）：600 秒

### 主 session 自我檢查（每次要使用工具前）

```
Phase 2 期間，主 session 每次呼叫工具前，自我檢查：

✅ 允許的操作：
- Read .automl/{run_id}/state.json
- Read .automl/{run_id}/changelog.md
- Write/Edit .automl/{run_id}/state.json（只更新調度欄位）
- Agent tool（派 subagent）
- Glob/Grep .automl/ 目錄（掃描未完成的 run）

❌ 禁止的操作（如果發現自己要做，立刻停下來改派 subagent）：
- Edit/Write 受控範圍內的任何檔案
- Bash 跑 evaluator 指令
- Bash 跑 git commit/checkout（應該由 subagent 做）
- Read 受控範圍的原始碼（分析工作是 subagent 的事）

檢查方式：在心裡問「這個操作是調度還是執行？」
- 調度 → 自己做
- 執行 → 派 subagent
```

### Run ID + 目錄結構

每次 `/automl` 啟動時，產生唯一 run ID：`{YYYYMMDD-HHMMSS}-{4位隨機hex}`

所有狀態檔放在 `.automl/{run_id}/` 下：
```
.automl/
  20260328-143022-a7f3/     ← 第一次執行
    state.json
    changelog.md
  20260328-160501-b2e1/     ← 同專案第二次執行（可能不同 session）
    state.json
    changelog.md
```

git tag 也帶 run ID：`automl-baseline-{run_id}`

### Step 0 — 斷點偵測

Phase 2 開始時，掃描 `.automl/` 目錄：

**沒有未完成的 run** → 全新執行，產生新 run ID，進 Step 1。

**有未完成的 run（state.json 裡 phase ≠ "done"）** → 斷點續傳（自動選擇，不問用戶，符合「不主動問」原則）：
1. 列出所有未完成的 run，報告 checkpoint_summary
2. 如果只有一個未完成的 run → 直接續傳
3. 如果有多個未完成的 run → 續最近更新的那個（用戶可手動刪除 state.json 來丟棄不需要的 run）
4. 讀該 run 的 state file + changelog 最後 3 筆 → 從斷點繼續
5. 如果有 STOP 檔案 → 刪除 STOP 檔案後繼續

### State File 格式

`.automl/{run_id}/state.json`

**寫入責任分工（明確，不可混用）：**
- **Subagent 寫**：state.json 的 task 狀態（status、score、iters_used、consecutive_pass_count）+ changelog 追加
- **主 session 寫**：state.json 的調度欄位（current_task、phase、regression_round、checkpoint_summary）
- **主 session 讀**：所有欄位（包括 task 狀態）— 讀取用於填入 subagent prompt 的參數（如 consecutive_pass_count）
- 規則：subagent 不碰調度欄位，主 session 不寫 task 狀態欄位。兩者寫不同的 key，不會衝突。主 session 讀所有欄位是正常操作。

```json
{
  "schema_version": "5.4",
  "run_id": "20260328-143022-a7f3",
  "phase": 2,
  "current_task": 3,
  "current_iter": 7,
  "task_list": [
    {
      "id": 1,
      "description": "...",
      "evaluator_structural": "...",
      "evaluator_structural_mode": "shell",
      "evaluator_semantic": "...",
      "evaluator_semantic_type": "test_runner",
      "evaluator_semantic_mode": "shell",
      "evaluator_integration": "...",
      "evaluator_integration_mode": "shell",
      "evaluator_regression": "xcodebuild test -project ... -scheme ...",
      "evaluator_regression_mode": "shell",
      "regression_checklist_items": null,
      "regression_baseline_value": null,
      "task_type": "feature",
      "scope": "...",
      "skill": "/investigate",
      "phase3_skill": "/investigate",
      "impact_path": {
        "deliverable": "...",
        "intermediate": ["...", "..."],
        "user_outcome": "..."
      },
      "risk_scenarios": [
        {
          "id": "R1",
          "description": "連續兩次操作，第二次能正常啟動嗎？",
          "trigger": "第一次操作完成後立即開始第二次",
          "expected": "第二次正常啟動，不 crash",
          "has_test": true,
          "test_command": "swift test --filter testDoubleStart"
        },
        {
          "id": "R2",
          "description": "改了 A 模組，B 模組的依賴還正確嗎？",
          "trigger": "A 模組 API 變更",
          "expected": "B 模組 build 通過 + 行為不變",
          "has_test": false,
          "test_command": null
        }
      ],
      "status": "passed",
      "baseline_score": 0.4,
      "final_score": 0.95,
      "iters_used": 5
    },
    {
      "id": 2,
      "description": "...",
      "task_type": "refactor",
      "impact_path": null,
      "evaluator_structural": "...",
      "evaluator_structural_mode": "shell",
      "evaluator_semantic": "...",
      "evaluator_semantic_type": "assertion",
      "evaluator_semantic_mode": "shell",
      "evaluator_integration": null,
      "evaluator_integration_mode": null,
      "evaluator_regression": "xcodebuild test -project ... -scheme ...",
      "evaluator_regression_mode": "shell",
      "regression_checklist_items": null,
      "regression_baseline_value": null,
      "skill": "none",
      "phase3_skill": "/review",
      "risk_scenarios": [],
      "status": "passed",
      "baseline_score": 0.6,
      "final_score": 1.0,
      "iters_used": 3
    },
    {
      "id": 3,
      "description": "...",
      "task_type": "feature",
      "impact_path": {
        "deliverable": "...",
        "intermediate": ["..."],
        "user_outcome": "..."
      },
      "evaluator_structural": "...",
      "evaluator_structural_mode": "shell",
      "evaluator_semantic": "...",
      "evaluator_semantic_type": "test_runner",
      "evaluator_semantic_mode": "shell",
      "evaluator_integration": "...",
      "evaluator_integration_mode": "shell",
      "evaluator_regression": "xcodebuild test -project ... -scheme ...",
      "evaluator_regression_mode": "shell",
      "regression_checklist_items": null,
      "regression_baseline_value": null,
      "skill": "/investigate",
      "phase3_skill": "/investigate",
      "risk_scenarios": [],
      "status": "in_progress",
      "baseline_score": 0.3,
      "best_score": 0.6,
      "iters_used": 7,
      "consecutive_pass_count": 1
    }
  ],
  "regression_round": 0,
  "baseline_tag": "automl-baseline-20260328-143022-a7f3",
  "params": {
    "max_iter": 10,
    "max_iter_per_dispatch": 5,
    "direction": "higher_is_better",
    "runs_per_iter": 1,
    "runs_per_iter_integration": 1,
    "max_regression_rounds": 3,
    "consecutive_passes": 3,
    "model_overrides": {
      "task_loop": "sonnet",
      "risk_review": "opus"
    }
  },
  "phase3": {
    "step": 1,
    "retry_count": 0,
    "max_retries": 2,
    "retry_log": [],
    "deliverable_review_executor": "codex-worker",
    "final_verification": null,
    "risk_review": null,
    "deliverable_review": null,
    "critical_issues": [],
    "important_issues": [],
    "verification_checklist": []
  },
  "checkpoint_summary": {
    "updated_at": "2026-03-28T14:35:00",
    "completed": 2,
    "total": 3,
    "current_task": "Task 3 描述",
    "progress": "Task 1: pass (5 iters), Task 2: pass (3 iters), Task 3: in_progress iter 7/10",
    "total_iters": 15,
    "keeps": 10,
    "reverts": 5,
    "stuck_tasks": []
  },
  "last_updated": "2026-03-28T14:35:00"
}
```

**State file 的角色是「當前快照」，changelog 的角色是「完整歷史」。兩者互補。**

### Step 1 — 備份

```bash
git tag automl-baseline-{run_id}
```
無論 loop 跑出什麼結果，都能一鍵回到起點。建立 `.automl/{run_id}/` 目錄和 state file 初始狀態。

**非 git 環境 fallback：**
如果工作目錄不是 git repo（例如獨立檔案、伺服器設定檔），改用檔案備份機制：
- 備份：`cp -r {scope} .automl/{run_id}/backup/`（取代 git tag）
- keep：`cp {modified_files} .automl/{run_id}/snapshots/iter-N/`（取代 git commit）
- revert：`cp .automl/{run_id}/snapshots/iter-{N-1}/{files} {scope}`（取代 git checkout）
- 偵測方式：Step 1 跑 `git rev-parse --is-inside-work-tree`，失敗就進入 fallback 模式
- State file 的 `baseline_tag` 欄位改為 `backup_path`

### Step 2+3 — Per-task 順序執行（baseline → 內層 loop）

> **重要：baseline 和 loop 是 per-task 順序執行的，不是先跑完所有 baseline 再跑 loop。**
> 流程：Task 1 baseline → Task 1 loop → Task 2 baseline → Task 2 loop → ... → 回歸檢查

**每個 task 的流程：**

**a) 先派 baseline subagent：**
```
Agent(prompt=BASELINE_PROMPT, description="automl baseline task M", mode="auto", model="haiku")
```

Baseline subagent 的工作：跑 runs_per_iter 次 evaluator，回傳一行結果。

主 session 根據回傳判定：
- evaluator 無法執行（crash/timeout/command not found）→ 停止整個 run，報告錯誤
- structural pass + semantic fail → 正常（功能還沒做）→ 進入 loop
- structural pass + semantic pass 且 task_type == "feature" → **EVALUATOR_QUALITY_ISSUE**（還沒做就 pass = evaluator_semantic 沒有鑑別力）→ 停止此 task，報告品質問題
- structural pass + semantic pass 且 task_type == "refactor" → 正常（refactor 不改功能）→ 進入 loop
- structural fail → 正常（可能是預期的）→ 進入 loop

**b) 再派 loop subagent：**

```
Agent(
  prompt=TASK_LOOP_PROMPT,
  description="automl task M improvement loop",
  mode="auto",
  model="sonnet"  # 預設；用戶可在 state.json params.model_overrides.task_loop 覆寫
)
```

Subagent 獨立跑該 task 的完整內層 loop（改 → 檢驗 → keep/revert → 下一輪），跑完回傳一行：

```
Task M: [passed/failed/stuck/needs_continue], baseline X → current Y, N iters (K keep, R revert)
```

**Subagent 內部行為（寫在 prompt 裡）：**
- 每輪修改原則：一次改一個方向、最小改動、連續 3 輪同方向失敗就切策略
- 每輪更新 `.automl/{run_id}/state.json` 的 task 狀態欄位（status、score、iters_used、consecutive_pass_count）+ 追加 `.automl/{run_id}/changelog.md`
- 不碰 state.json 的調度欄位（current_task、phase、regression_round、checkpoint_summary）— 那是主 session 的事
- 每輪跑 evaluator_structural（快速回饋）
- 當 evaluator_structural 的 consecutive_pass_count 達標時，額外跑 evaluator_semantic
- evaluator_structural pass 但 evaluator_semantic fail → consecutive_pass_count 歸零，繼續迭代
- 三層 evaluator 都 pass → 才算真正 passed（evaluator_integration 為 null 時跳過該層）
- 如果 task_type == "feature"，deliverable 必須包含 evaluator_semantic 可驗證的產出（例如：測試檔案、eval script、golden output、checklist 回答）。只交付實作而沒有可驗證證據 = 該輪未達標。
- 程式碼場景可用 TDD（先寫 failing test → 最小實作 → refactor）
- 內層終止條件：連續 3 次達標(passed) / 達到 max_iter_per_dispatch 且全局未到上限(needs_continue) / 達到 max_iter_per_dispatch 且全局已到上限(failed) / 連續 5 輪卡住(stuck)

**Subagent 單次迭代上限：**
- 每個 subagent 最多跑 `max_iter_per_dispatch` 輪（預設 5，不超過 max_iter）
- 如果 5 輪內沒達標，subagent 回傳當前狀態 + 「需要繼續」
- 主 session 讀 state file，判斷是否派新的 subagent 繼續（帶上 changelog 最後 3 筆作為策略參考）
- 這防止單一 subagent context 爆炸（5 輪 loop 約 20-30k tokens，安全範圍內）
- 累計迭代次數仍受 max_iter 限制

**主 session 收到結果後：**
- 讀 state file 確認狀態
- 決定：派下一個 task / 繼續當前 task（再派新 subagent）/ 進入回歸檢查

**Subagent 失敗處理：**
```
Subagent 回傳異常時的處理邏輯：

1. Subagent 回傳格式不符（無法解析 pass/fail/score）
   → 讀 state file + changelog 嘗試推斷狀態
   → 如果 state file 有更新 → 以 state file 為準繼續
   → 如果 state file 沒更新 → 標記為 subagent_error，重試一次

2. Subagent 被 kill / context 用盡（沒有回傳）
   → 讀 state file 找最後更新的 iter
   → 從該 iter 繼續（派新 subagent，帶 changelog 最後 3 筆）
   → 如果 state file 完全沒更新 → 標記為 subagent_error，重試一次

3. 同一 task 連續 2 次 subagent_error
   → 標記 task 為 stuck
   → 跳到下一個 task（不阻塞整個 run）
   → 最終報告中標註哪些 task 因 subagent error 而 stuck

4. Changelog 與 state.json 不同步（subagent 半途崩潰）
   → 讀 changelog 最後一筆的 Task ID + Iter N
   → 讀 state.json 的 iters_used
   → 如果 changelog 有 iter N 但 state.json 還停在 iter N-1
     → 以 changelog 為準，把 state.json 補到 iter N（保守處理：status 維持 in_progress）
   → 如果 state.json 有 iter N 但 changelog 沒有
     → 以 state.json 為準繼續（changelog 少了一筆紀錄，可接受）
   → 原則：寧可少一筆 changelog，不可丟失 state 進度
```

### Step 4 — 外層 Loop（派 subagent 做回歸檢查）

全部 task 的 subagent 都回報達標後：

```
Agent(
  prompt=REGRESSION_CHECK_PROMPT,
  description="automl regression check round R",
  mode="auto",
  model="haiku"
)
```

**回歸檢查 subagent 的工作：**
- 按順序重跑所有 task 的 evaluator_structural + evaluator_semantic + evaluator_integration + evaluator_regression
- 回傳結果列表：

```
Regression Round R:
Task 1: pass ✅ (structural: pass, semantic: pass, integration: pass, regression: pass)
Task 2: REGRESSED ❌ — [哪層失敗, 錯誤摘要]
Task 3: pass ✅ (structural: pass, semantic: pass, integration: skip, regression: pass)
```

**主 session 根據回傳判定：**
- 全部通過 → 進 Phase 3
- 有 regression → 對被破壞的 task 再派一個內層 loop subagent 重修 → 修完再派回歸檢查
- 外層超過 3 輪 → 停止，報告 task 衝突

---

## Subagent Prompt 模板

> 主 session 填空即可派工，不需要思考 prompt 怎麼組。
> **自帶完整 context 原則：** 每個 prompt 模板必須包含 subagent 需要的所有資訊。
> Subagent 不會看到 Phase 0/1 的對話歷史，也不會看到其他 subagent 的對話。
> 如果 task 有來自 Phase 0/1 的重要 context（例如 brainstorming 的結論、plan review 的約束），
> 主 session 必須在派工時把這些 context 摘要塞進 prompt 的「== 背景 ==」欄位。

### TASK_LOOP_PROMPT（內層 loop）

```
你是 automl 的執行 subagent。獨立完成一個 task 的完整優化 loop。

== 任務 ==
描述：{task_description}
Task 類型：{task_type}（feature / refactor）
受控範圍：{scope}
方向：{direction}
本次最多跑：{max_iter_per_dispatch} 輪（全局上限 {max_iter}）
Runs per iter：{runs_per_iter}
Consecutive passes：{consecutive_passes}

== 背景（來自 Phase 0/1 的 context，可能為空）==
{background_context}

== 強制技能（dispatch 開始時載入一次，不可跳過）==
（此區塊僅在 skill != none 時存在）
名稱：{skill_name}
Skill 呼叫方式：Skill tool，skill="{skill_name}"

規則：
- 第一輪 edit 之前，呼叫 Skill tool 載入技能
- 載入後，跳過 gstack preamble（bash 腳本區塊）和 telemetry epilogue — 不要執行，直接使用技能的核心方法論
- 後續各輪沿用已載入的技能引導，不重複呼叫 Skill tool（內容已在 context 中）
- 只允許呼叫 {skill_name}，呼叫其他 skill = 違規
- 跳過此步驟的改動 = 該輪作廢，必須 revert 後重來
- Changelog 必須記錄「使用了哪個技能、技能給了什麼引導」

== 環境 ==
工作目錄：{cwd}
版本控制：{vcs_mode}（git / file-backup）

== 可用工具 ==
Bash（跑 evaluator、git commit/checkout）、Read、Write（更新 state file）、Edit（修改受控範圍檔案）、Grep、Glob、Skill（條件性：skill != none 時才加）

== 版本控制操作 ==
- **git 模式**：改善 → `git add {files} && git commit -m "automl: ..."`, 退步 → `git checkout -- {files}`
- **file-backup 模式**：改善 → `cp {files} .automl/{run_id}/snapshots/iter-N/`, 退步 → `cp .automl/{run_id}/snapshots/iter-{N-1}/{files} {scope}`

== 狀態檔 ==
State file：{state_file_path}
Changelog：{changelog_path}
當前 baseline 分數：{baseline_score}
已完成迭代：{completed_iters}（從此處繼續）
已連續通過次數：{consecutive_pass_count}（需達 {consecutive_passes} 才算穩定通過）

== 前次策略參考（changelog 最後 3 筆，可能為空）==
{last_3_changelog_entries}

== Checklist（僅 checklist 模式）==
Semantic checklist：{checklist_items}
Integration checklist（evaluator_integration_mode == checklist 時）：{integration_checklist_items}

== Impact Path（改動如何影響最終結果）==
Deliverable：{deliverable}
中間環節：{intermediate}
用戶可觀察結果：{user_outcome}

== Evaluator（四層）==
Structural（每輪跑）：{evaluator_structural}
Structural 模式：{evaluator_structural_mode}
Semantic（structural 穩定後跑）：{evaluator_semantic}
Semantic 模式：{evaluator_semantic_mode}
Integration（semantic pass 後跑）：{evaluator_integration}
Integration 模式：{evaluator_integration_mode}
Regression（integration pass 後跑）：{evaluator_regression}
Regression 模式：{evaluator_regression_mode}
Regression checklist（evaluator_regression_mode == checklist 時）：{regression_checklist_items}
Regression baseline value（非確定性領域凍結值，null = 確定性）：{regression_baseline_value}

== Evaluator 執行方式 ==
- **Structural（每輪）**：快速回饋。shell 模式用 Bash 跑，exit 0 = pass。checklist 模式自行對照。
- **Semantic（structural 穩定後）**：驗證意圖達成。當 structural consecutive passes 達標，額外跑 semantic。structural pass 但 semantic fail → consecutive_pass_count 歸零。
- **Integration（semantic pass 後）**：驗證系統 end-to-end 新行為。
  runs_per_iter 使用 {runs_per_iter_integration}（預設 1，獨立於 structural/semantic 的 {runs_per_iter}）。
- **Regression（integration pass 後）**：驗證既有行為沒壞。為 null 時跳過（v5.2 run）。
  如果 regression_baseline_value 非 null（非確定性領域），regression 結果必須 >= regression_baseline_value × 0.99（容差 1%）才算 pass。
  Regression fail → triage：本輪改動有因果關聯 → revert + 歸零；無關聯 → 重跑確認，仍 fail 則標記 REGRESSION_INVESTIGATION_NEEDED，本輪計分 neutral。
- **四層都 pass 才算真正 passed。**
- **shell 模式輔助分數**：stdout 含可解析數字時，用該數字判斷「改善」（數字改善即使還沒全 pass 也 commit）。
- **checklist 模式**：閱讀產出檔案，逐條對照回答 yes/no。通過率 = yes 數 / 總題數。
- **pass/fail 取平均**：runs_per_iter > 1 時，通過率 = pass 次數 / 總次數。>= 100% 才算達標。

== 規則 ==
- 每輪只改一個方向，最小改動優先
- 改完跑 evaluator（依上述方式），改善就 commit，退步就 revert
- 每輪更新 state file 的 task 狀態欄位（status、score、iters_used、consecutive_pass_count）+ 追加 changelog
- 連續通過計數：達標時 consecutive_pass_count++，未達標時歸零。起始值為 {consecutive_pass_count}
- consecutive_pass_count >= {consecutive_passes} → 回傳 passed
- 連續 5 輪沒改善 → 回傳 stuck
- 達到本次上限 {max_iter_per_dispatch} 輪：
  - 如果 {completed_iters} + {max_iter_per_dispatch} >= {max_iter}（全局上限已到）→ 回傳 failed
  - 否則 → 回傳 needs_continue
- 只改受控範圍內的檔案，範圍外一律不碰
- 不可修改 evaluator 指向的檔案（{evaluator_structural} / {evaluator_semantic} / {evaluator_integration} 中引用的腳本）
- evaluator timeout 120 秒
- 修改 deliverable 後，必須確認中間環節和 user_outcome 仍然正確
- 每輪 evaluator 執行順序：structural → semantic → integration → regression
- semantic pass 但 integration fail → 改動方向可能對但破壞了系統，changelog 記錄分析
- integration pass 但 regression fail → triage：本輪改動與 fail 有因果關聯 → revert + 歸零；無關聯 → 重跑一次，仍 fail 則標記 REGRESSION_INVESTIGATION_NEEDED，本輪 neutral
- 如果發現中間環節有問題（即使不在 scope 內），列進 changelog 作為發現（但不改 scope 外檔案）

== 完成後回傳 ==
一行結果：「Task {task_id}: [passed/failed/stuck/needs_continue], baseline {baseline} → current {current}, N iters (K keep, R revert)」
```

### REGRESSION_CHECK_PROMPT（回歸檢查）

```
你是 automl 的回歸檢查 subagent。重跑所有 task 的 evaluator，確認沒有 regression。

== 環境 ==
工作目錄：{cwd}

== 可用工具 ==
Bash（跑 evaluator）、Read、Grep

== 任務清單 ==
{task_evaluator_list}
（格式：Task ID | evaluator_structural | evaluator_semantic | evaluator_integration | evaluator_regression | structural_mode | semantic_mode | integration_mode | regression_mode | regression_baseline_value | runs_per_iter | runs_per_iter_integration | final_score | direction）

== Regression 判定標準 ==
- 跑 evaluator_structural + evaluator_semantic + evaluator_integration + evaluator_regression
- pass/fail 型：exit 0 = pass，non-zero = REGRESSED
- 分數型：與 final_score 比較，允許 5% 波動
- checklist 型：通過率 >= final_score × 0.95

== Regression Checklist（各 task 的 regression_checklist_items，若 regression_mode == checklist）==
{regression_checklist_by_task}
（格式：Task ID | regression_checklist_items；若 regression_mode 非 checklist 則該 task 此欄為空）

== 規則 ==
- 按順序重跑每個 task 的四層 evaluator：evaluator_structural → evaluator_semantic → evaluator_integration → evaluator_regression
- evaluator_integration 為 null 時跳過該層（適用 refactor task 和 v5.1 舊 run）
- evaluator_regression 為 null 時跳過該層（適用 v5.2 舊 run）
- evaluator_regression_mode == checklist 時，使用上方 regression_checklist_items 逐條對照
- integration 回歸用 runs_per_iter_integration（預設 1）
- 不修改任何檔案，只跑檢查
- 每個 structural/semantic evaluator 跑 runs_per_iter 次

== 完成後回傳 ==
Regression Round {round}:
Task 1: pass ✅ (structural: pass, semantic: pass, integration: pass, regression: pass) / REGRESSED ❌ — [哪層失敗, 錯誤摘要]
Task 2: pass ✅ (structural: pass, semantic: pass, integration: skip, regression: pass) / REGRESSED ❌ — [錯誤摘要]
...
```

### BASELINE_PROMPT（baseline 檢查）

```
你是 automl 的 baseline 檢查 subagent。跑一次 evaluator 確認初始狀態。

== 環境 ==
工作目錄：{cwd}

== 可用工具 ==
Bash（跑 evaluator）、Read、Write（寫入 state file baseline_score）

== 任務 ==
Task ID：{task_id}
Task 類型：{task_type}（feature / refactor）
Evaluator Structural：{evaluator_structural}
Evaluator Structural 模式：{evaluator_structural_mode}
Evaluator Semantic：{evaluator_semantic}
Evaluator Semantic 模式：{evaluator_semantic_mode}
Evaluator Integration：{evaluator_integration}
Evaluator Integration 模式：{evaluator_integration_mode}
Evaluator Regression：{evaluator_regression}
Evaluator Regression 模式：{evaluator_regression_mode}
Runs per iter：{runs_per_iter}
Runs per iter（integration）：{runs_per_iter_integration}
State file：{state_file_path}

== Checklist（僅 checklist 模式）==
Semantic checklist：{checklist_items}
Integration checklist（evaluator_integration_mode == checklist 時）：{integration_checklist_items}
Regression checklist（evaluator_regression_mode == checklist 時）：{regression_checklist_items}

== 規則 ==
- 不修改任何檔案，只跑 evaluator
- 跑 evaluator_structural + evaluator_semantic
- 如果 evaluator_integration 存在，也跑它（跑 runs_per_iter_integration 次）
- 如果 evaluator_regression 存在，也跑它
- 跑完把 baseline_score（structural + semantic + integration + regression 各自）寫入 state file
- **反轉測試（semantic）**：如果 task_type == "feature" 且 evaluator_semantic baseline PASS → 回傳 EVALUATOR_QUALITY_ISSUE（還沒做就 pass = evaluator 沒有鑑別力）
- **反轉測試（integration）**：如果 task_type == "feature" 且 evaluator_integration baseline PASS
  → 回傳 EVALUATOR_QUALITY_ISSUE（系統 end-to-end 在實作前就正常 = integration evaluator 沒有鑑別力）
- **反轉測試（regression，反向）**：如果 evaluator_regression baseline FAIL → 回傳 EVALUATOR_QUALITY_ISSUE（既有行為本來就壞了 = regression evaluator 無效）
  # 正常 case: regression baseline PASS → 記錄 regression_baseline = pass，繼續
- 如果 evaluator_regression 是數值型（stdout 輸出數字），把數值寫入 state file 的 `regression_baseline_value`（供後續迭代做漂移比較）。確定性領域（pass/fail 型 evaluator）`regression_baseline_value` 維持 null
- 如果 task_type == "refactor" 且 semantic baseline PASS → 正常（refactor 不改功能）
- 如果 task_type == "refactor" 且 integration baseline PASS → 正常
- evaluator timeout 120 秒

== 完成後回傳 ==
一行結果：「Task {task_id} baseline: structural=[pass/fail], semantic=[pass/fail/score X.XX], integration=[pass/fail/skip], regression=[pass/fail/skip]」
如果是 feature task 且 semantic 或 integration baseline pass：
  「Task {task_id} baseline: EVALUATOR_QUALITY_ISSUE — [semantic/integration] pass before implementation」
如果 regression baseline fail（feature 或 refactor task 皆適用）：
  「Task {task_id} baseline: EVALUATOR_QUALITY_ISSUE — regression fail before implementation (existing behavior already broken)」
如果 evaluator 無法執行：「Task {task_id} baseline: ERROR — [錯誤訊息]」
```

---

## Changelog 記錄

在 `.automl/{run_id}/changelog.md` 每輪追加一筆：
```
### Task M, Iter N — [keep ✅ / revert ❌]
- 強制技能：{skill_name}，引導內容：[技能給了什麼建議]
- 策略：[這輪要改什麼]
- 改動摘要：[改了哪些檔案的哪些部分]
- Structural：[pass/fail]
- Semantic：[pass/fail/score/skipped]（skipped = structural 還沒穩定）
- Integration：[pass/fail/skip]（skip = semantic 未 pass 或 evaluator_integration 為 null）
- Regression：[pass/fail/skip]（skip = integration 未 pass 或 evaluator_regression 為 null）
- 結論：[為什麼 keep 或 revert，學到什麼]
```
這份 changelog 是最有價值的產出 — 記錄什麼有用、什麼沒用，下次接續或換模型時直接讀取。

---

## 中途 Checkpoint（被動式，不中斷執行）

> **原則：automl 永遠不主動問用戶問題，只被動提供進度資訊。**

checkpoint 機制：
- 每完成一個 task（或 subagent 回傳 needs_continue 時），主 session 在 state.json 寫入 checkpoint 摘要
- State file 的 `checkpoint_summary` 欄位持續更新（格式見上方 State File 格式章節的 JSON 範例）

用戶介入方式（非 automl 主動觸發）：
1. **用戶自行檢查**：隨時讀 `.automl/{run_id}/state.json` 查看進度
2. **用戶在另一個 session 查看**：`cat .automl/*/state.json | jq .checkpoint_summary`
3. **用戶手動中斷**：在 `.automl/{run_id}/` 下建立 `STOP` 檔案
   - 主 session 每次派 subagent 前檢查 `STOP` 檔案是否存在
   - 存在 → 停止執行，更新 state 為暫停狀態，等用戶下次手動恢復
4. **用戶手動調整**：直接修改 state.json 的 params（如調低 max_iter）→ 下次 dispatch 時生效

---

## 最終報告

> Phase 3 的三個驗收 subagent 調度邏輯已在上方說明，prompt 模板在 reference 檔案。以下是 Phase 3 全部通過後，主 session 輸出的最終報告格式。

```
=== AutoML 完成 ===
狀態：達標 ✅ / 未達標 ❌
Phase 0：[用了什麼 skill / 跳過]
Phase 1：[幾個 tasks / 用了 /autoplan / 跳過]
Phase 2：
  內層總迭代：N 輪（K keep, R revert）
  外層回歸檢查：R 輪
  Task 1: baseline [X] → 最終 [Y]，N 輪，強制技能：{skill_name}
  Task 2: baseline [X] → 最終 [Y]，N 輪，強制技能：{skill_name}
  ...
Phase 3：
  Final Verification：pass ✅ / fail ❌（haiku，{N} evaluators + {M} risk scenarios）
  Risk Review：safe ✅ / {N} bugs 🔴（opus，技能：{skill_name}）
    [如有 bug，列出每個]
  Code Review：pass ✅ / {N} critical 🔴（{executor}，技能：{skill_name}）
    [如有 critical/important，列出每個]
  Phase 3 回退次數：{retry_count}/{max_retries}
最後 commit：[hash + message]
Run ID：{run_id}
Baseline tag：automl-baseline-{run_id}（回到起點：git checkout automl-baseline-{run_id}）
Changelog：.automl/{run_id}/changelog.md
建議：[如果未達標，說明卡在哪裡 + changelog 中的模式分析]

Verification Checklist：
1. [測試步驟] ✅/❌ — 來源：Phase 1 risk scenario / Phase 3 review 發現
2. [測試步驟] ✅/❌ — 來源：Phase 1 risk scenario / Phase 3 review 發現
...
（排序：crash > data loss > UX > cosmetic）
```

**完成後清理：** 更新 state file 的 phase 為 `"done"`，保留檔案供日後參考（不刪除）。

---

## 安全護欄

1. **主 session 不動手** — Phase 2 期間主 session 禁止直接 Edit/Write 受控範圍的檔案，禁止直接 Bash 跑 evaluator。所有修改和檢驗都透過 subagent。唯一例外：讀寫 `.automl/{run_id}/` 下的 state.json 和 changelog.md
2. **白名單制** — subagent 只修改受控範圍內的檔案，範圍外一律不碰（包括 CLAUDE.md、AGENTS.md、memory.md、.env、lock files、CI config 等）。**額外排除 evaluator 指向的檔案**（如 `eval.py`、`test_config.json`），防止 subagent 修改評判標準本身
3. **只 revert 受控範圍** — `git checkout -- [specific files]`，不用 `git reset --hard`
4. **commit 前先確認 diff** — 每次 commit 都記錄本輪改了什麼
5. **max_iter 強制上限** — 預設 10，最高 50，防止無限燒 token
6. **evaluator timeout** — 每次 evaluator 執行上限 120 秒，超時算失敗並 revert
7. **changelog 只追加** — `.automl/{run_id}/changelog.md` 只能追加，不能刪除或修改已有記錄
8. **state file 每輪覆寫** — `.automl/{run_id}/state.json` 每輪結束時更新
9. **baseline tag 不可刪除** — loop 期間不可刪除 `automl-baseline-*` tag
10. **run 目錄隔離** — 每次執行有獨立 run ID 和目錄，多 session 不互相干擾
11. **STOP 檔案檢查** — 每次派 subagent 前，檢查 `.automl/{run_id}/STOP` 是否存在。存在 → 暫停執行，更新 state
12. **Prompt 自帶 context** — subagent prompt 必須包含所有需要的資訊，不依賴 Phase 0/1 對話歷史
13. **Subagent 迭代上限** — 單次 dispatch 最多 max_iter_per_dispatch 輪（預設 5），防止 subagent context 爆炸
14. **不主動問用戶** — Phase 2 期間不使用 AskUserQuestion，所有進度透過 state file 被動提供
15. **Phase 3 主 session 不動手** — Phase 3 期間主 session 禁止直接讀 diff、做 review、跑驗證。所有驗收都透過 subagent。主 session 只讀寫 `.automl/{run_id}/` 下的 state.json 和 changelog.md
16. **Skill 限定** — subagent 只能呼叫被指定的 skill，呼叫其他 skill 視為違規
17. **Phase 3 回退上限** — Phase 3 發現問題回 Phase 2 修復，最多 2 次。超過就停止，報告未解問題
18. **Changelog skill 記錄** — 有強制技能的 task，changelog 每輪必須記錄 skill 使用痕跡。缺少記錄 = 該輪可疑，主 session 可要求重做
19. **Evaluator 品質關卡** — feature 型 task 的 evaluator_semantic 在 baseline 階段如果已 pass，停止該 task 並報告 evaluator 品質不足（EVALUATOR_QUALITY_ISSUE）。不允許無鑑別力的 evaluator 進入 loop。
20. **Evaluator integration 檔案保護** — evaluator_integration 指向的檔案也排除在受控範圍外，與 evaluator_semantic 同規則

---

## v5.1 → v5.2 遷移

**未完成的 v5.1 run（state.json 沒有新欄位）：**
- Phase 2 Step 0 讀到舊格式時，檢查 task 是否有 `impact_path` 欄位
- 沒有 → 視為 v5.1 run，以 v5.1 模式繼續（不帶 integration evaluator）
- 有 → 視為 v5.2 run
- 不自動升級舊 state file

**Phase 3 mid-flight 處理：**
- 如果 `evaluator_integration` 為 `null` 或 missing，integration 層 status = `skip`，不 block task pass

## v5.3 → v5.4 遷移

**v5.4 的變更：**
- 刪除 `falsification` 欄位（state.json schema 不再包含）
- 刪除 ①②③ 品質關卡（反轉測試、意圖覆蓋、替代測試）
- 新增 Phase 1.5b RED_TEAM agent + Phase 1.5c 自動修復
- evaluator_audit.py 已刪除 falsification checks（#12 #13 → 重編號 #12-#14 for regression）

**未完成的 v5.3 run（state.json 有 `falsification` 欄位）：**
- 以 v5.3 模式繼續（忽略 falsification，不跑紅隊）
- 不自動升級舊 state file

**新的 run：** 一律使用 v5.4 格式（無 `falsification`，Phase 1.5b 紅隊必跑）
