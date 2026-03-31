# /automl — Reference（Phase 0/1/3 + Evaluator + 參數 + 範例）

> 此檔案由 automl 主檔案按需載入。Phase 2 直跑不需要讀此檔案。

---

## Phase 0 — 釐清意圖（可選）

> 用戶已經想清楚 → 跳過，直接進 Phase 1 或 Phase 2。
> 用戶只有模糊想法 → 用這個 Phase 幫他想清楚。

### 可串接的 skill（依情境選一個）

**`/office-hours`** — 最開放，用戶連「要不要做」都還不確定
- 適用：「我有一個想法…」「這東西值不值得做？」
- 產出：經過追問後的明確目標 + 可行性判斷
- 串接方式：跑完 office-hours 後，把產出的 design doc 帶進 Phase 1

**`superpowers:brainstorming`** — 用戶知道要做什麼，需要釐清 how
- 適用：「幫我寫一篇文章講 X」「我要加一個 Y 功能」
- 產出：design spec（含 2-3 approaches + trade-offs）
- 串接方式：brainstorming 的 terminal state 會自動接 writing-plans → 進 Phase 1

**`/grill-me`** — 用戶有計畫但沒被挑戰過
- 適用：「我想做 X，幫我想想有沒有漏洞」
- 產出：被拷問後更堅固的計畫
- 串接方式：grill-me 結束後整理出明確目標 + 範圍，進 Phase 1

**`/design-consultation`** — 涉及 UI/UX，需要競品研究
- 適用：功能有 UI 元件，需要了解使用者體驗、競品做法
- 產出：UI/UX 方向建議 + 設計決策依據
- 串接方式：design-consultation 結束後，把設計決策帶進 Phase 1

**不串接，automl 自己引導** — 輕量場景
- 從用戶的初始訊息中提取目標、成功條件、範圍
- 缺什麼就用合理預設填入，不中斷流程問用戶
- 適合簡單任務，不需要完整的 brainstorming session

---

## Phase 1 — 拆解 + 定檢驗標準（可選）

> 目標明確但任務大 → 拆成小塊，每塊定義 evaluator。
> 目標明確且任務小 → 跳過，直接進 Phase 2。

### 拆解：可串接的 skill

**`/autoplan`**（預設，強制跑）— 一次跑完三個 review + 自動決策
- CEO / eng / design 三個 review 自動執行
- 6 決策原則自動處理 mechanical decisions，只把 taste decisions 拉出來問用戶
- 如果用戶明確只要跑其中一個 review → 允許覆寫（如「只跑 eng review」）
- 輕量任務直接跳 Phase 2 → `/autoplan` 跳過

**`superpowers:writing-plans`** — 程式碼場景拆 task 輔助
- 把 spec 拆成 bite-sized tasks，每步有驗證指令
- 產出格式：`docs/superpowers/plans/YYYY-MM-DD-<name>.md`
- 每個 task = 2-5 分鐘，一個動作
- 通常在 `/autoplan` 之後使用（autoplan 定方向，writing-plans 細化 task 清單）

**不串接，automl 自己拆** — 非程式碼場景或簡單任務
- 把大目標拆成可獨立檢驗的小塊
- 每塊定義獨立的 evaluator（shell 或 checklist）
- 拆完直接進入 Phase 2，不中斷問用戶

### 審視計畫：可串接的 skill（可選，用戶要求時才跑）

**`/plan-ceo-review`** — 挑戰格局
- 「有沒有想得更大的可能？」「前提假設對嗎？」
- 四種模式：擴大範圍 / 選擇性擴大 / 鎖定範圍 / 縮小範圍

**`/plan-eng-review`** — 鎖定技術
- 架構、資料流、edge cases、效能、測試策略

**`/plan-design-review`** — 設計品質
- 每個設計維度 0-10 評分，說明怎麼做到 10 分

### Phase 1 的產出

進入 Phase 2 前，必須有：
```
任務清單：
  Task 1: [描述]
    evaluator_structural（可選）：產出形式/格式正確的驗證
    evaluator_semantic（必填）：產出意圖達成的驗證
    evaluator_semantic_type（必填）：test_runner / eval_script / metric / checklist / assertion
    evaluator_integration（feature 必填）：零件裝回系統後 end-to-end outcome 驗證
    evaluator_integration_mode: shell / script / checklist
    evaluator_regression（feature + refactor 必填）：既有行為沒壞的驗證
    evaluator_regression_mode: shell / checklist
    impact_path:
      deliverable: [零件改動]
      intermediate: [中間環節，可為 null（簡化形式）]
      user_outcome: [用戶可觀察的結果]
    範圍: [可修改的檔案/目錄]
    Risk scenarios: [3-5 個，見下方結構化格式]
    Phase 2 強制技能: [skill 名稱]
    Phase 2 方法論技能（methodology_skill）: [TDD skill 名稱，或 null]
    required_tests: [紅隊產出的必要測試清單，Phase 1 時為空，Phase 1.5c 填入]
    Phase 3 強制技能: [skill 名稱]
    task_type: "feature" 或 "refactor"
  Task 2: [描述]
    evaluator_structural: ...
    evaluator_semantic: ...
    evaluator_semantic_type: assertion（僅限 refactor）
    evaluator_integration: ...
    evaluator_regression（feature + refactor 必填）：既有行為沒壞的驗證
    evaluator_regression_mode: shell / checklist
    範圍: ...
    Risk scenarios: ...
    Phase 2 強制技能: none（理由：純 config 值替換，無需領域知識）
    Phase 3 強制技能: /review
    task_type: "refactor"
  ...

全域參數：
  Max iterations per task：[預設 10]
  Max iterations per dispatch：[預設 5]
  Direction：[higher_is_better / lower_is_better]
  Runs per iter：[預設 1]
  Runs per iter（integration）：[預設 1]
```

### Evaluator 品質關卡（Phase 1.5，三步）

Phase 1 完成 state.json 後，依序執行三步品質關卡：

**Phase 1.5a — Evaluator Audit 腳本（機械性，不可跳過）**
`python3 ~/.claude/skills/automl/scripts/evaluator_audit.py .automl/{run_id}/state.json`
腳本驗證 `evaluator_semantic_type` 分類、feature/assertion 互斥、scope 含 test file、impact_path、integration ≠ semantic、regression 等規則。
`exit 1` = BLOCKED，修改 evaluator 設計後重跑。詳見 SKILL.md「Evaluator Audit Gate」章節。

**Phase 1.5b — RED_TEAM Agent（對抗式驗證，feature task 必跑）**
派獨立 subagent 嘗試 game evaluator：在 scope 內修改檔案讓所有 evaluator pass，但實際上沒達成 task 意圖。
- 常見 game 手法：寫假 test、mock-only regression、硬塞 expected output、跳過 edge case
- 最多 2 輪，找到 game 方式 → BLOCKED，找不到 → PASSED
- refactor task 跳過（refactor 不改功能，紅隊無意義）
- 詳見 SKILL.md「Phase 1.5b — RED_TEAM Agent」章節

**Phase 1.5c — 自動修復（紅隊 BLOCKED 時）**
1. 解析紅隊 JSON `findings`
2. 根據 `fix_suggestion` 修改 evaluator
3. 重跑 Phase 1.5a → 1.5b
4. 最多 2 輪修復，仍 BLOCKED → 停止，讓用戶介入

> v5.4 變更：刪除了 ①②③（反轉/意圖覆蓋/替代測試）和 falsification，改由紅隊 agent 實際嘗試 game 來驗證 evaluator 品質。

### Phase 1 Integration Evaluator 設計流程

Phase 1 拆解 task 後，對每個 feature task：

1. **找 caller / 消費者**（程式：grep public API；文章：哪些段落引用了改動；策略：哪些模組依賴改動）
2. **填 impact_path**：deliverable → intermediate → user_outcome
3. **設計 evaluator_integration**：必須涵蓋 user_outcome 的驗證
4. **設計 evaluator_regression**：驗證既有行為沒壞。判斷方法：「這個 test 在 baseline（改動前）會 pass 還是 fail？」Pass → regression，Fail → integration
5. **跑 Phase 1.5（audit + 紅隊）**：通過才進 Phase 2

### Evaluator 四層模型跨領域範例

| 領域 | Structural | Semantic | Integration | Regression |
|------|-----------|----------|-------------|------------|
| 程式碼 | compiles/lint pass | known input → expected output | end-to-end pipeline test | 全部既有 test 通過 |
| 交易策略 | backtest 能跑完不 crash | sharpe > X, drawdown < Y% | 完整回測（含交互作用） | 原策略 P&L 與凍結參考值一致 ± 1% |
| 文章 | 字數/段落/格式合規 | checklist：論點完整、tone 正確 | 全文連貫性 + 結論合理性 | 既有章節核心論點語義不變 |
| Prompt | output 能 parse、格式正確 | 品質評分 > threshold | 下游 pipeline 仍正常 | 既有功能輸出品質不下降 |
| 設定檔 | syntax valid、service 能啟動 | 效能指標達標 | 系統整體健康檢查 | 既有功能 latency/throughput 不退化 |
| ML 模型 | training completes, output valid shape | validation accuracy > threshold | full inference pipeline pass | 既有 benchmark 分數不退化 |

### Risk Scenarios（風險場景）

每個 task 必須列出 3-5 個「這個改動可能怎麼壞」的場景。這是提前把風險攤開的機制，讓 evaluator 和 Phase 3 有具體的檢查項目。

**撰寫原則：**
- 聚焦在改動本身會引入的風險，不是泛泛的「可能會壞」
- 每個場景是一個具體的 **觸發條件 + 預期行為**，例如：「連續兩次操作，第二次能正常啟動嗎？」
- 不限領域——程式碼、文案、設定檔都適用

**Risk scenario 結構化格式（寫入 state file）：**
```json
{
  "id": "R1",
  "description": "連續兩次操作，第二次能正常啟動嗎？",
  "trigger": "第一次操作完成後立即開始第二次",
  "expected": "第二次正常啟動，不 crash",
  "has_test": true,
  "test_command": "swift test --filter testDoubleStart",
  "evaluator_for_scenario": "swift test --filter testDoubleStart && exit 0 || exit 1"
}
```
- `has_test`：是否有對應的自動化 test case
- `test_command`：有 test 時填 shell 指令；無 test 時填 null
- `evaluator_for_scenario`（可選）：該場景的自動化驗證指令，可以是 shell 指令或 checklist；比 `test_command` 更彈性，允許多步驟組合驗證

**風險場景的用途（自動流入後續階段）：**
- **流入 evaluator**：場景如果可以寫成 test case 或 evaluator 的額外 check → 加入 evaluator（程式碼場景最常見）
- **流入 Phase 3 verification_checklist**：場景如果需要人工驗證 → 自動出現在 Phase 3 的 checklist
- 一個場景可以同時流入兩者

**範例（各領域）：**
- 程式碼：「第一次操作正常，第二次能正常啟動嗎？」「A 模組改完，B 模組的依賴還正確嗎？」
- 文案：「改了標題之後，body 的呼應還成立嗎？」「CTA 語氣和前文一致嗎？」
- 設定檔：「改了 A 參數，B 參數會不會被影響？」「rollback 之後系統能恢復嗎？」

### Scope 重疊檢查（進 Phase 2 前必須做）

- 掃描所有 task 的受控範圍，如果有重疊（同一個檔案/目錄出現在多個 task 中）→ 標記衝突
- 有重疊的 task 必須按順序執行（後面的 task 建立在前面的 commit 之上），不能並行
- 如果重疊不可避免，在相關 task 的 evaluator 裡加入對其他 task 成果的保護性檢查

### Evaluator 檔案保護

- 如果 evaluator 指令引用了腳本檔案（如 `python eval.py`），該檔案必須排除在所有 task 的受控範圍之外
- 防止 subagent 在修改受控範圍時意外改動 evaluator，造成「放水通過」的假陽性

Phase 1 產出後直接進 Phase 2，不中斷問用戶。任務清單會寫入 state file，用戶可隨時查看。

---

## Phase 3 — 交付驗收

> Phase 3 由主 session 調度三個驗收 subagent，主 session 本身禁止直接讀 diff、做 review、跑驗證。

### 三個驗收 subagent

#### ① FINAL_VERIFICATION（機械性驗證）

**執行者**：Claude Agent（固定 model="haiku"，不可覆寫）
**工作**：重跑所有 evaluator + risk scenario 對應的 test case
**強制技能**：`none`（預設）/ `/qa-only`（web app 專案）/ `/benchmark`（效能相關）

```
FINAL_VERIFICATION_PROMPT：

你是 automl 的 final verification subagent。重跑所有 evaluator 做最終確認。

== 環境 ==
工作目錄：{cwd}

== 可用工具 ==
Bash, Read, Grep

== 任務清單 ==
{task_evaluator_list}
（格式：Task ID | evaluator_structural | evaluator_semantic | evaluator_integration | evaluator_regression | structural_mode | semantic_mode | integration_mode | regression_mode | regression_baseline_value | runs_per_iter | runs_per_iter_integration | final_score | direction）

== Risk Scenario Evaluators ==
{risk_scenario_evaluators}
（格式：場景 ID | 場景描述 | evaluator_for_scenario（可能為空）| test_command（可能為空））

== 規則 ==
- 按順序重跑每個 task 的四層 evaluator：先 structural → 再 semantic → 再 integration → 再 regression
- evaluator_structural 或 evaluator_semantic 失敗時，該 task 直接標 fail，不再跑 integration 和 regression
- evaluator_integration 為 null 或 missing 時，integration status = skip（不 block）
- evaluator_regression 為 null 或 missing 時，regression status = skip（不 block）
- evaluator_regression_mode == checklist 時，從 state file 讀取對應 task 的 regression_checklist_items 逐條對照
- 跑 risk scenario 中有 evaluator_for_scenario 或 test_command 的驗證
- 不修改任何檔案，只跑檢查
- evaluator timeout 120 秒

== 完成後回傳（嚴格遵守此 JSON 格式，方便主 session 解析）==
\`\`\`json
{
  "status": "pass" | "fail",
  "tasks": [
    {
      "id": 1,
      "status": "pass",
      "structural": {"status": "pass", "score": 1.0},
      "semantic": {"status": "pass", "score": 0.95},
      "integration": {"status": "pass", "score": 0.9},
      "regression": {"status": "pass", "score": 1.0}
    },
    {
      "id": 2,
      "status": "fail",
      "structural": {"status": "pass", "score": 1.0},
      "semantic": {"status": "fail", "score": 0.3, "error": "錯誤摘要"},
      "integration": {"status": "skip", "reason": "not defined"},
      "regression": {"status": "skip", "reason": "not defined"}
    }
  ],
  "risk_scenarios": [
    {"id": "R1", "status": "pass", "description": "場景描述"},
    {"id": "R2", "status": "fail", "description": "場景描述", "error": "錯誤摘要"},
    {"id": "R3", "status": "skip", "description": "場景描述", "reason": "no evaluator defined"}
  ]
}
\`\`\`
```

#### ② RISK_REVIEW（風險場景逐條驗證）

**執行者**：Claude Agent（固定 model="opus"，trace code path 的關鍵步驟不能省）
**工作**：讀 Phase 1 的 risk_scenarios，trace 實際 code path / 產出，判定 safe 或 bug
**強制技能**：預設必填，主 session 根據領域從 Skill Mapping 對照表指定
**多 skill 處理**：按 `phase3_skill` 分組，同一 skill 的 task 合併成一個 dispatch

```
RISK_REVIEW_PROMPT：

你是 automl 的 risk review subagent。逐條驗證風險場景。

== 可用工具 ==
Bash, Read, Grep, Glob, Skill

== 強制技能（不可跳過）==
名稱：{skill_name}
Skill 呼叫方式：Skill tool，skill="{skill_name}"

規則：
- 開始分析前，必須先呼叫 Skill tool 載入技能
- 載入後，跳過 gstack preamble 和 telemetry epilogue — 直接使用技能的核心方法論
- 只允許呼叫 {skill_name}，呼叫其他 skill = 違規
- 依照技能的方法論逐條分析每個風險場景

== 環境 ==
工作目錄：{cwd}

== 累積 Diff ==
Baseline tag：{baseline_tag}
（用 git diff {baseline_tag}..HEAD 查看所有改動）

== Impact Path（v5.2 新增，可能為空）==
{impact_path_list}
（格式：Task ID | impact_path.deliverable | impact_path.intermediate | impact_path.user_outcome）

== Impact Path 完整性檢查（不可跳過，如果資料存在）==
逐條驗證：
1. impact_path.intermediate 的每個環節是否仍然正確連接 deliverable → user_outcome？
2. 是否有遺漏的中間環節？（改動可能引入新的依賴或副作用）
3. user_outcome 是否真的可驗證？如果不可驗證，這本身就是風險。
4. **regression evaluator 覆蓋檢查**：regression evaluator 是否真的覆蓋了 impact_path.user_outcome 的既有路徑？如果沒有 → 標 bug
5. **test quality gate**：test_runner 類型的 evaluator 是否真的執行了有意義的驗證？（trace test code，確認不是假 test / mock-only / 硬塞 expected output）

== Risk Scenarios（從 state file 的 risk_scenarios 欄位填入）==
{risk_scenarios_list}
（格式：Task ID | Scenario ID | 場景描述 | 觸發條件 | 預期行為 | has_test | evaluator_for_scenario）

== 規則 ==
- 對每個場景，trace 實際的 code path / 產出 / 設定
- 如果發現 Phase 1 沒列到的新風險場景，一併列出
- 不修改任何檔案，只做分析

== 完成後回傳（嚴格遵守此 JSON 格式）==
\`\`\`json
{
  "status": "safe" | "has_bugs",
  "scenarios": [
    {"id": "R1", "status": "safe", "analysis": "為什麼安全"},
    {"id": "R2", "status": "bug", "analysis": "問題描述", "fix": "建議修法"}
  ],
  "new_findings": [
    {"id": "N1", "status": "safe" | "bug", "description": "新場景", "analysis": "..."}
  ]
}
\`\`\`
```

#### ③ DELIVERABLE_REVIEW（交付物 review）

**執行者**：codex-worker agent（優先）/ Claude Agent（fallback，model="sonnet"）
**工作**：看整個 run 的累積改動，抓架構問題、遺漏、副作用，評估交付物是否完整達到意圖
**強制技能**：
- 程式碼專案：`/review`（review diff，邏輯同舊 CODE_REVIEW）
- 非程式碼專案：`design:design-critique` 或其他適合領域的 skill
**環境偵測**：Phase 3 開始時檢查 `/Users/fredchu/bin/codex-dispatch` 是否存在
- 存在 → 用 codex-worker agent（轉嫁到 ChatGPT 額度）
- 不存在 → 派 Claude Agent（model="sonnet"）

```
DELIVERABLE_REVIEW_PROMPT：

你是 automl 的 deliverable review subagent。對整個 run 的累積改動做 review。

== 可用工具 ==
Bash, Read, Grep, Glob, Skill

== 強制技能（不可跳過）==
名稱：{skill_name}
Skill 呼叫方式：Skill tool，skill="{skill_name}"

規則：
- 開始 review 前，必須先呼叫 Skill tool 載入技能
- 載入後，跳過 gstack preamble 和 telemetry epilogue — 直接使用技能的核心 review 流程
- 只允許呼叫 {skill_name}，呼叫其他 skill = 違規
- 依照技能的完整 review 流程執行

== 環境 ==
工作目錄：{cwd}

== 累積 Diff / 交付物 ==
Baseline tag：{baseline_tag}
（程式碼專案：用 git diff {baseline_tag}..HEAD 查看所有改動）
（非程式碼專案：直接讀取交付物檔案）

== 改動摘要（來自 changelog）==
{changelog_summary}

== Task 意圖清單（review 重點：交付物是否完整達到每個 task 的意圖）==
{task_intent_list}
（格式：Task ID | task description | evaluator_semantic 摘要）

== Skill Review Checklist（方案 A：codex-worker 用，Claude fallback 時此欄位留空）==
{skill_reference_summary}

== 規則 ==
- 程式碼專案：review diff，抓架構問題、遺漏、副作用
- 非程式碼專案：對照 task 意圖，評估交付物是否完整、是否達到意圖、有無遺漏
- Critical issue 標記為必須回 Phase 2 修復
- Important issue 標記為建議修復
- 不修改任何檔案，只做分析
- 如果有 Skill Review Checklist，逐條對照改動/交付物檢查

== 完成後回傳（嚴格遵守此 JSON 格式）==
\`\`\`json
{
  "status": "pass" | "has_critical" | "has_important_only",
  "critical": [
    {"id": "C1", "description": "問題描述", "impact": "什麼會壞", "fix": "怎麼修"}
  ],
  "important": [
    {"id": "I1", "description": "問題描述", "fix": "怎麼修"}
  ],
  "minor": [
    {"id": "M1", "description": "問題描述"}
  ]
}
\`\`\`
```

**codex-worker 注意事項：**
- codex-worker 沒有 Skill tool，強制技能改為方案 A：主 session 在派工前讀 skill reference，摘要塞進 `{skill_reference_summary}` 欄位
- Claude fallback 時，`{skill_reference_summary}` 留空，由 subagent 自行呼叫 Skill tool（方案 B）
- `{skill_reference_summary}` 的內容：從 skill 的 SKILL.md 中提取核心 review checklist（跳過 preamble 和 telemetry），控制在 ~2k tokens 以內

### Phase 3 Subagent 失敗處理

```
Phase 3 subagent 回傳異常時的處理：

1. 回傳非 JSON（無法解析結構化結果）
   → 嘗試從文字中提取 pass/fail/safe/bug/critical 關鍵字做粗略判斷
   → 如果能判斷 → 以粗略結果繼續（降級處理）
   → 如果無法判斷 → 標記為 subagent_error，重試一次

2. Subagent timeout / context 用盡
   → 標記為 subagent_error，重試一次

3. 同一 step 連續 2 次 subagent_error
   → 停止整個 run，報告哪個 step 的 subagent 失敗
   → 不算入 retry_count（這不是 Phase 2 能修的問題）

4. codex-worker 失敗（DELIVERABLE_REVIEW step）
   → 自動 fallback 到 Claude Agent（sonnet），不算重試
```

### Phase 3 回退機制

- Phase 3 最多回退 Phase 2 兩次（共用 `retry_count` counter）
- FINAL_VERIFICATION fail、RISK_REVIEW has_bugs、DELIVERABLE_REVIEW has_critical 都會觸發回退
- 超過 2 次 → 停止，報告「Phase 3 回退已達上限，仍有未解問題」，列出每次回退原因

### v3 → v4 遷移路徑

**未完成的 v3 run（state.json 裡沒有新欄位）：**
- Phase 2 Step 0（斷點偵測）讀到舊格式 state file 時：
  - 檢查 task 是否有 `skill` 欄位
  - 沒有 → 視為 v3 run，以 v3 模式繼續（不帶強制技能）
  - 有 → 視為 v4 run
- 不自動升級舊 state file，避免破壞進行中的 run

**新的 run：** 一律使用 v4 格式

### v5.1 → v5.2 遷移路徑

**未完成的 v5.1 run（state.json 裡沒有 `impact_path` / `evaluator_integration` 欄位）：**
- Phase 2 斷點偵測讀到舊格式 state file 時：
  - 檢查 task 是否有 `evaluator_integration` 欄位
  - 沒有 → 視為 v5.1 run，以 v5.1 模式繼續（不帶 integration evaluator）
  - 有 → 視為 v5.2 run
- 不自動升級舊 state file，避免破壞進行中的 run

**新的 run：** 一律使用 v5.2 格式（feature task 必填 `evaluator_integration`、`impact_path`）

### v5.2 → v5.3 遷移路徑

**未完成的 v5.2 run（state.json 裡沒有 `evaluator_regression` / `schema_version` 欄位）：**
- Phase 2 斷點偵測讀到舊格式 state file 時：
  - 檢查 state file 是否有 `schema_version` 欄位
  - 沒有 → 視為 v5.2 run，regression 層 status = skip（不 block）
  - 有且 >= "5.3" → 視為 v5.3 run
- 不自動升級舊 state file，避免破壞進行中的 run

**新的 run：** 一律使用 v5.3 格式（feature + refactor task 必填 `evaluator_regression`，state file 帶 `schema_version: "5.3"`）

**Phase 3 追蹤 block 不存在：**
- 如果 state.json 沒有 `phase3` key → 視為 Phase 3 尚未開始，建立初始 block

### v5.3 → v5.4 遷移路徑

**v5.4 的變更：**
- 刪除 `falsification` 欄位
- 刪除 ①②③ 品質關卡，改為 Phase 1.5b RED_TEAM agent
- evaluator_audit.py 刪除 falsification checks，重編號 regression checks 為 #12-#14

**未完成的 v5.3 run（state.json 有 `falsification` 欄位）：**
- 以 v5.3 模式繼續（忽略 falsification，不跑紅隊）
- RISK_REVIEW 跳過 falsification 交叉驗證（欄位可能存在但不再使用）
- 不自動升級舊 state file

**新的 run：** 一律使用 v5.4 格式（無 `falsification`，`schema_version: "5.4"`，Phase 1.5b 紅隊必跑）

### Verification Checklist（Phase 3 必輸出）

Phase 3 結束時，必須輸出一份 **verification checklist**，供用戶做最終驗證：

```
Verification Checklist：
1. [測試步驟] ✅/❌ — 來源：Phase 1 risk scenario / Phase 3 review 發現
2. [測試步驟] ✅/❌
...
```

**Checklist 來源（按優先順序合併）：**
1. Phase 1 的 `risk_scenarios` 中需要人工驗證的項目
2. Phase 3 review 中發現的新風險場景
3. Deliverable review / quality review 的 findings 對應的驗證項目

**排序規則：** crash / data loss 風險在前，UX 退化在中，外觀/文案在後。

---

## Evaluator 模式

### 模式一：shell（預設）

evaluator 是一條 shell 指令，靠 exit code 或 stdout 數字判定。適合有確定性結果的場景（build、test、lint、字數檢查…）。

常見模板：
```bash
# pass/fail 型 — 任何指令，exit 0 = pass，exit 1 = fail
<your_command> && exit 0 || exit 1

# 分數型 — 指令的 stdout 最後一行輸出數字
<your_scoring_command>

# 內容比對型 — grep/diff 檢查輸出是否包含期望結果
<your_command> | grep -q "expected_pattern" && exit 0 || exit 1

# 多條件組合 — 所有條件都通過才算 pass
<check_1> && <check_2> && exit 0 || exit 1
```

範例（各領域）：
- 測試：`pytest tests/ -q`、`npm test`、`go test ./...`
- Build：`npx tsc --noEmit`、`cargo build`、`swift build`
- Lint / 格式：`eslint src/ --max-warnings 0`、`ruff check .`
- 文字品質：`wc -w output.md`（字數）、自訂評分腳本
- 任何可量化的目標：只要能寫成 shell 指令就能當 evaluator

**分數型 evaluator**：解析 stdout 最後一行作為分數。改善方向由 `direction` 決定：`higher_is_better`（預設）= 分數上升為改善；`lower_is_better` = 分數下降為改善（如 error count、loss）。

### 模式二：checklist（LLM-as-judge）

用 3-6 個 yes/no 問題組成 checklist，由 agent 自己對輸出結果打分。適合評「軟品質」（文案好不好、風格是否一致、有沒有廢話…）。

checklist 範例：
```
- 標題有沒有包含具體數字或結果？
- 全文是否沒有出現「革命性」「行業領先」等零資訊量詞彙？
- CTA 是否告訴用戶做完這步之後會發生什麼？
```

**checklist 評分方式：** 通過項數 / 總項數 = 通過率（0-100%）。改善 = 通過率上升。
**checklist 數量建議：** 3-6 題。超過 6 題容易 gaming（為了通過 checklist 犧牲整體品質）。

---

## 參數一覽

```
目標：[用戶說要達到什麼]
Evaluator：[用戶提供的指令，或需要協助定義]
Evaluator 模式：[shell (預設) / checklist]
受控範圍：[可修改的檔案/目錄]
Max iterations per task：[預設 10，最高 50]
Max iterations per dispatch：[預設 5 — 單次 subagent 最多跑幾輪，防 context 爆炸]
Direction：[higher_is_better (預設) / lower_is_better]
Runs per iter：[預設 1 — 每次改動後跑幾次 evaluator 取通過率]
Max regression rounds：[預設 3 — 外層回歸檢查上限]
Consecutive passes：[預設 3 — 連續幾次達標才算穩定]
```

### Runs per iter（統計信心）

每次改動後跑 `runs_per_iter` 次 evaluator，取通過率 / 平均分數作為該輪結果。
- **確定性 evaluator**（build、test）→ `runs_per_iter: 1` 就夠
- **有隨機性的 evaluator**（checklist / LLM 輸出 / 有隨機種子的腳本）→ 建議 `runs_per_iter: 3-5`
- 判定改善/退步時，比較的是**本輪平均**與**上輪平均**

---

## 快速入口

> 用戶可以從任何 Phase 開始，automl 自動判斷。

**從零開始（Phase 0）：**
```
/automl 我想寫一篇文章講 AI 工具的使用心得
```
→ 偵測到缺目標 + evaluator + 範圍 → 進入 Phase 0 引導（建議用 brainstorming）

**有目標但沒 evaluator（Phase 1）：**
```
/automl 幫我寫一個 CLI 工具，可以查詢股票價格
```
→ 偵測到有目標但缺 evaluator + 範圍 → 進入 Phase 1 拆解（建議用 writing-plans）

**全部就位（Phase 2）：**
```
/automl 讓 pytest 全部通過
evaluator: pytest tests/ -q
範圍: src/core/
max: 20
```
→ 三要素齊全 → 直接進 Phase 2 loop

---

## 使用範例

**程式碼 — 直接跑**
```
/automl 讓 pytest 全部通過
evaluator: pytest tests/ -q
範圍: src/core/
max: 20
```

**程式碼 — 從頭引導**
```
/automl 幫我加一個用戶登入功能
```
→ Phase 0: brainstorming → Phase 1: writing-plans + plan-eng-review → Phase 2: TDD loop → Phase 3: deliverable review

**文字 / 內容優化**
```
/automl 把 README 壓到 500 字以內且保留所有 section
evaluator: bash -c 'test $(wc -w < README.md) -le 500 && grep -q "## Install" README.md && grep -q "## Usage" README.md'
範圍: README.md
```

**Skill / Prompt 優化（checklist 模式）**
```
/automl 優化我的 landing page copy skill
evaluator: checklist
checklist:
  - 標題是否包含具體數字或結果？
  - 全文是否沒有「革命性」「行業領先」等空洞詞彙？
  - CTA 是否告訴用戶下一步會得到什麼？
  - 開頭第一句是否點出具體痛點場景？
範圍: .claude/skills/landing-page.md
runs_per_iter: 3
max: 15
```

**寫文章 — 從頭引導**
```
/automl 幫我寫一篇文章，主題是我用 Claude Code 搭建 AI 特助系統的心得
```
→ Phase 0: brainstorming（釐清角度、讀者、tone）→ Phase 1: 拆成大綱段落 + 每段 checklist → Phase 2: 逐段寫 + checklist 檢驗 → Phase 3: 全文 final review

**設定檔 / 配置調校**
```
/automl 讓 nginx 設定通過語法檢查且 response time < 200ms
evaluator: nginx -t && curl -so /dev/null -w '%{time_total}' http://localhost | awk '{exit ($1 < 0.2) ? 0 : 1}'
範圍: /etc/nginx/conf.d/app.conf
```

**大型重構 — 搭配完整 review chain**
```
/automl 重構 payment module，把 callback 全部改成 async/await
```
→ Phase 0: grill-me（追問邊界條件）→ Phase 1: writing-plans + plan-ceo-review（需不需要趁機改更大？）+ plan-eng-review（鎖定架構）→ Phase 2: TDD loop per task → Phase 3: verification + deliverable review
