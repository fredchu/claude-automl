# Autonomous Evaluation Loop — Reference（Phase 0/1/3 + Evaluator + 參數 + 範例）

> 此檔案由 automl 主檔案按需載入。Phase 2 直跑不需要讀此檔案。

---

## Phase 0 — 釐清意圖（可選）

> 用戶已經想清楚 → 跳過，直接進 Phase 1 或 Phase 2。
> 用戶只有模糊想法 → 用這個 Phase 幫他想清楚。

### 可串接的 skill（依情境選一個）

**Ideation / brainstorming skill** — 最開放，用戶連「要不要做」都還不確定
- 適用：「我有一個想法…」「這東西值不值得做？」
- 產出：經過追問後的明確目標 + 可行性判斷
- 串接方式：跑完後，把產出的 design doc 帶進 Phase 1
- 如果你有 ideation/exploration 類 skill（例如 office-hours、思路討論、可行性分析），可以在此串接

**Brainstorming skill** — 用戶知道要做什麼，需要釐清 how
- 適用：「幫我寫一篇文章講 X」「我要加一個 Y 功能」
- 產出：design spec（含 2-3 approaches + trade-offs）
- 串接方式：brainstorming 的 terminal state 會自動接 task planning → 進 Phase 1
- 如果你有 brainstorming/design exploration 類 skill，可以在此串接

**Plan challenge skill** — 用戶有計畫但沒被挑戰過
- 適用：「我想做 X，幫我想想有沒有漏洞」
- 產出：被拷問後更堅固的計畫
- 串接方式：plan challenge 結束後整理出明確目標 + 範圍，進 Phase 1
- 如果你有 devil's advocate / plan stress-test 類 skill，可以在此串接

**不串接，automl 自己引導** — 輕量場景
- 從用戶的初始訊息中提取目標、成功條件、範圍
- 缺什麼就用合理預設填入，不中斷流程問用戶
- 適合簡單任務，不需要完整的 brainstorming session

---

## Phase 1 — 拆解 + 定檢驗標準（可選）

> 目標明確但任務大 → 拆成小塊，每塊定義 evaluator。
> 目標明確且任務小 → 跳過，直接進 Phase 2。

### 拆解：可串接的 skill

**Task planning skill** — 程式碼場景最佳選擇
- 把 spec 拆成 bite-sized tasks，每步有驗證指令
- 如果你有 task planning / writing-plans 類 skill，可以在此串接
- 每個 task = 2-5 分鐘，一個動作
- 注意：如果你的 task planning skill 有預設的產出路徑，可忽略或依你的專案結構調整

**不串接，automl 自己拆** — 非程式碼場景或簡單任務
- 把大目標拆成可獨立檢驗的小塊
- 每塊定義獨立的 evaluator（shell 或 checklist）
- 拆完直接進入 Phase 2，不中斷問用戶

### 審視計畫：可串接的 skill（可選，用戶要求時才跑）

**Plan review skill（CEO 視角）** — 挑戰格局
- 「有沒有想得更大的可能？」「前提假設對嗎？」
- 四種模式：擴大範圍 / 選擇性擴大 / 鎖定範圍 / 縮小範圍
- 如果你有 business/strategy 視角的 plan review skill，可以在此串接

**Plan review skill（工程師技術審查）** — 鎖定技術
- 架構、資料流、edge cases、效能、測試策略
- 如果你有 technical review / architecture review 類 skill，可以在此串接

**Plan review skill（設計品質檢查）** — 設計品質
- 每個設計維度 0-10 評分，說明怎麼做到 10 分
- 如果你有 design quality review 類 skill，可以在此串接

### Phase 1 的產出

進入 Phase 2 前，必須有：
```
任務清單：
  Task 1: [描述]
    Evaluator: [shell 指令 或 checklist]
    範圍: [可修改的檔案/目錄]
  Task 2: [描述]
    Evaluator: ...
    範圍: ...
  ...

全域參數：
  Max iterations per task：[預設 10]
  Max iterations per dispatch：[預設 5]
  Direction：[higher_is_better / lower_is_better]
  Runs per iter：[預設 1]
```

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

### 可串接的 skill

**Verification skill** — 跑完才能說完
- 強制 evidence-based：跑驗證指令 → 讀 output → 確認 exit code → 才能 claim 完成
- 防止「我覺得應該過了」的假完成
- 如果你有 verification-before-completion / evidence-based verification 類 skill，可以在此串接

**Code review skill** — 程式碼場景
- 派 code-reviewer subagent 做 diff-aware review
- Critical issue 立即修（回到 Phase 2 的 loop）
- Important issue 修完再交付
- 如果你有 code review / requesting-code-review 類 skill，可以在此串接

**不串接，automl 自己驗收** — 單 task 或輕量場景
- Phase 2 的外層回歸檢查已確保所有 task 同時通過
- 此處再做最後一次 final verification 作為雙重保險

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
→ 偵測到有目標但缺 evaluator + 範圍 → 進入 Phase 1 拆解（建議用 task planning skill）

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
→ Phase 0: brainstorming → Phase 1: task planning + technical review → Phase 2: TDD loop → Phase 3: code review

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
→ Phase 0: plan challenge（追問邊界條件）→ Phase 1: task planning + CEO/business review（需不需要趁機改更大？）+ technical review（鎖定架構）→ Phase 2: TDD loop per task → Phase 3: verification + code review
