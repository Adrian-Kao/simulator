# Claude Code Implementation Brief
## Xinyi Policy Sandbox — Scenario + Simulation + Gemini Optimization Demo

### Objective

在目前 `Adrian-Kao/simulator` 專案上建立一個**獨立 branch**，不要直接修改 `main`，完成一個可 Demo 的「政策 Scenario → Python 模擬 → Dashboard KPI → Gemini reasoning → 自動修正政策 → 再模擬直到達標」流程。

這一階段的目標不是把所有交通模型做完，而是先完成一條**可信、可展示、可重複執行的 end-to-end vertical slice**。

---

# 0. Git / 工作方式

請先確認目前工作目錄乾淨，並從最新 `main` 建立：

```bash
git checkout main
git pull origin main
git checkout -b feature/scenario-ai-optimizer-demo
```

所有修改只做在：

```text
feature/scenario-ai-optimizer-demo
```

不要 push / merge 到 `main`。

在完成前請自行反覆執行：

```bash
python -m pytest
cd frontend
npm run typecheck
npm run build
```

如果現有測試因為舊功能本身失敗，請先判斷是否為本次修改造成，不要為了讓測試過而刪除既有測試。

---

# 1. 移除 Scenario 的所有預設政策

## 現況問題

目前下方 `PolicyList` 會預設顯示政策，例如：

- 新增 YouBike 站點
- 停車政策
- 道路號誌

而且類似：

```ts
const basePolicyCount = 3;
```

會讓尚未操作的 Scenario 看起來已經存在政策。

這不利於 Demo。

## 需求

初始 Scenario 必須是：

```text
Scenario A
0 筆政策

目前尚未設定政策
請從地圖或工具列新增政策
```

只有使用者實際修改 / 建立過的政策才可以出現在 Scenario 清單。

### 重要規則

Baseline 資料：

```text
道路
號誌
停車場
YouBike
既有紅線
```

不是 Scenario Policy。

只有「相對 Baseline 的修改」才是 Scenario。

---

# 2. 建立 ScenarioDiff，固定 Demo 的 3 個政策變量

第一版 Demo 只允許 AI 最佳化以下三個變量：

```text
X1 = signal_green_seconds
X2 = red_line_meters
X3 = parking_spaces
```

請建立明確的 Scenario / Policy 型別，避免直接把整份 frontend state 傳給後端。

建議概念：

```ts
type ScenarioPolicy =
  | {
      type: "signal-timing";
      intersection_id: string;
      baseline_seconds: number;
      scenario_seconds: number;
    }
  | {
      type: "red-line";
      road_id: string;
      length_meters: number;
    }
  | {
      type: "parking";
      parking_id: string;
      spaces: number;
    };

type ScenarioDiff = {
  scenario_id: string;
  policies: ScenarioPolicy[];
};
```

不一定必須完全照上述型別命名，但語意必須相同。

## 行為

例如使用者做：

```text
市府路紅線 +120m
某路口東西向綠燈 40 → 55 秒
新增停車場 80 格
```

Scenario 清單才顯示三筆。

如果某設定沒有改變 baseline，就不要加入 ScenarioDiff。

---

# 3. 讓三個政策變量都真正影響 Python simulation

## 現況

目前 FastAPI 已經可由 frontend 呼叫：

```text
POST /api/simulations
```

而 signal timing 已經能影響 Queue。

但 red-line 與 parking 目前主要只是 payload / warning，沒有真正改變 simulation outcome。

## 本階段要求

三個 demo 變量都必須對至少一個 KPI 造成**可解釋、可測試、deterministic** 的影響。

不要做「前端假數值」。

所有 KPI 必須由 Python backend 回傳。

### 可接受的 MVP policy effect

在真實校準完成前，可以建立明確標示為 MVP / proxy 的 policy effect，例如：

```text
signal_green_seconds
→ signal capacity
→ queue

red_line_meters
→ curb friction / effective road capacity adjustment
→ travel time / speed / V/C

parking_spaces
→ cruising / access friction adjustment
→ travel time / queue 或相關 KPI
```

但需遵守：

1. 公式集中在 backend，不可散落在 frontend。
2. 不要偷偷宣稱是已校準的真實交通模型。
3. constants 必須有命名。
4. policy effect 必須寫測試。
5. 同樣 input + random_seed 必須得到同樣 output。

如果有更合理且能利用現有 `roads.py`, `signals.py`, `parking.py` 的方式，可以採用。

---

# 4. 建立 Simulation Orchestrator，並改用歷史 Baseline

不要持續把所有邏輯塞進：

```text
api/service.py
```

請新增類似：

```text
simulation/orchestrator.py
```

職責：

```text
load baseline
    ↓
build simulation state
    ↓
apply ScenarioDiff
    ↓
run road/signal/policy effects
    ↓
aggregate KPIs
    ↓
return result
```

## Baseline

優先使用 repo 現有：

```text
data/historical/
simulation/historical.py
simulation/baseline.py
simulation/roads.py
simulation/signals.py
```

目前 API 內類似以下 synthetic constants：

```text
length_m = 500
capacity_vph = 1800
ARRIVALS_PER_TICK = 120
```

請盡量改成從現有 historical baseline / road data 取得。

如果特定欄位目前沒有可靠資料，允許 fallback，但必須：

```text
1. 明確命名為 fallback/default
2. 在 response warnings 或 metadata 中表明
3. 不要讓 frontend 誤以為是真實歷史值
```

## API contract

建議維持：

```text
POST /api/simulations
```

但 response 可擴充。

至少回傳：

```json
{
  "scenario_id": "scenario-a",
  "baseline": {},
  "scenario": {},
  "delta": {},
  "recommended": "...",
  "warnings": [],
  "metadata": {}
}
```

---

# 5. Goal Engine + 右側 Dashboard

目前右側已有 KPI Dashboard 基礎。

請新增真正的 GoalConfig，不要只把：

```text
降低 10%
提升 8%
降低 15%
```

寫死在 UI。

第一版至少支援：

```ts
type GoalConfig = {
  travel_time_percent?: number;
  travel_speed_percent?: number;
  congestion_vc_percent?: number;
  queue_percent?: number;
};
```

範例：

```json
{
  "travel_time_percent": -10,
  "travel_speed_percent": 8,
  "queue_percent": -15
}
```

Backend 或 shared logic 必須有：

```text
goals_met(result, goals)
```

並回傳每個 KPI：

```text
target
current
gap
met
```

Dashboard 顯示：

```text
Travel Time
Baseline    3.40 min
Scenario    3.08 min
Delta       -9.4%
Target      -10.0%
Gap          0.6%
Status      尚未達標
```

達標則顯示：

```text
✓ 已達標
```

---

# 6. Gemini Reasoning API

Gemini 只負責：

```text
讀 Scenario
讀 Simulation Result
讀 Goals
↓
提出下一輪 Policy Patch
```

Gemini **不能自行產生 KPI**。

KPI 一律由 Python simulation 計算。

## API Key

API key 先留空即可。

請新增：

```text
GEMINI_API_KEY=
```

到：

```text
.env.example
```

或 backend 專用 env example。

**不要 commit 真實 API key。**

如果 `GEMINI_API_KEY` 為空：

```text
Gemini endpoint 不應讓整個 backend crash。
應回傳清楚的 "AI unavailable / API key not configured" 狀態。
普通 simulation 仍必須正常工作。
```

## Structured output

請讓 Gemini 回傳固定 JSON schema，不要讓它自由輸出政策文字後再 regex parse。

概念：

```python
class PolicyRecommendation(BaseModel):
    signal_green_seconds: int
    red_line_meters: float
    parking_spaces: int
    reasoning: str
```

AI 必須遵守 bounds，例如：

```text
signal_green_seconds: 20 ~ 68
red_line_meters:      0 ~ 500
parking_spaces:       0 ~ 300
```

實際 bounds 若依現有資料更合理可以調整，但請集中管理。

建議新增 endpoint：

```text
POST /api/reason
```

request：

```json
{
  "scenario": {},
  "result": {},
  "goals": {}
}
```

response：

```json
{
  "recommendation": {
    "signal_green_seconds": 55,
    "red_line_meters": 160,
    "parking_spaces": 80
  },
  "reasoning": "..."
}
```

請將 Gemini client 封裝，例如：

```text
api/gemini_service.py
```

不要直接寫在 FastAPI route 裡。

---

# 7. 建立 Optimization Loop

這是本 branch 最重要的 Demo 功能。

需要完成：

```text
Initial Scenario
    ↓
simulate
    ↓
check goals
    ↓
if not met
    ↓
Gemini reason
    ↓
validate policy patch
    ↓
apply patch
    ↓
simulate again
    ↓
repeat
```

直到：

```text
A. goals_met == true
或
B. 達到 max_iterations
```

第一版：

```text
max_iterations = 5
```

即可。

## 安全限制

每次 Gemini recommendation 都要由程式 validation。

不能讓 Gemini：

```text
直接寫資料庫
直接改 source code
直接改 baseline
產生未允許的 policy type
跳過 bounds
```

它只能修改：

```text
signal_green_seconds
red_line_meters
parking_spaces
```

## 建議 endpoint

可以做：

```text
POST /api/optimize
```

request：

```json
{
  "initial_scenario": {},
  "goals": {},
  "max_iterations": 5
}
```

response：

```json
{
  "status": "goal_reached",
  "iterations": [
    {
      "iteration": 1,
      "scenario": {},
      "result": {},
      "goal_status": {},
      "reasoning": "..."
    },
    {
      "iteration": 2,
      "scenario": {},
      "result": {},
      "goal_status": {},
      "reasoning": "..."
    }
  ],
  "final_scenario": {},
  "final_result": {}
}
```

Gemini key 為空時：

```text
/api/optimize
```

可回：

```text
status = ai_unavailable
```

不要 fake reasoning。

---

# Frontend Demo UX

希望 Demo 可以照這個流程：

```text
1. 一開始 Scenario = 0 policies
2. 使用者在地圖手動改三項：
   - 號誌
   - 紅線
   - 停車
3. 下方 Scenario 清單顯示剛才實際改過的三項
4. 按「開始模擬」
5. Python backend 回 KPI
6. 右側 Dashboard 顯示 baseline / scenario / delta / goal
7. 按「AI 最佳化」
8. 顯示：
   Iteration 1
   Gemini reasoning
   Policy changes
   KPI
9. 自動執行下一輪
10. 最後顯示：
   Goal Reached
   或
   Max Iterations Reached
```

## AI Optimization History UI

可以放在右側 Dashboard 下方，形式不必華麗，但至少清楚：

```text
AI Policy Optimization

Iteration 1
Signal      45 → 55 sec
Red Line   100 → 150 m
Parking    100 → 80 spaces

Travel Time   -6.5% / target -10%  ✕
Queue        -12.0% / target -15%  ✕

Reasoning:
目前主要瓶頸仍為路口排隊...

────────────────

Iteration 2
...
```

不要為了 UI 重寫整個地圖。

沿用現在的：

```text
SimulationShell
SimulationMap
PolicyList
GoalPanel
```

做增量修改即可。

---

# 建議檔案結構

不是硬性要求，但建議朝：

```text
api/
├─ main.py
├─ schemas.py
├─ service.py
├─ gemini_service.py
└─ optimizer_service.py

simulation/
├─ orchestrator.py
├─ goals.py
├─ policy_effects.py
├─ baseline.py
├─ historical.py
├─ roads.py
├─ signals.py
├─ parking.py
└─ ...

frontend/src/
├─ lib/
│  ├─ simulation-api.ts
│  └─ optimizer-api.ts
├─ features/simulation/
│  ├─ simulation.types.ts
│  └─ scenario.utils.ts
└─ components/simulation/
   ├─ SimulationShell.tsx
   ├─ PolicyList.tsx
   ├─ GoalPanel.tsx
   └─ ...
```

---

# 不要做的事情

本 branch 不要：

```text
1. 重寫整個 frontend
2. 更換地圖架構
3. 修改 main
4. 把 Gemini API key 寫死
5. 讓 Gemini 產生假的 KPI
6. 為了 Demo 寫死「一定第三輪達標」
7. 為了讓結果漂亮而直接 hardcode Dashboard 數字
8. 把 commuter / visitor / YouBike 的完整 agent 校準一起做進來
```

Commuter / Visitor / YouBike Agent 可以保留現況。

這一 branch 的核心是：

```text
Scenario
→ Simulation
→ KPI
→ Goal
→ Gemini reasoning
→ Policy patch
→ Simulation
```

先把這條 loop 做完整。

---

# Acceptance Criteria

完成前請自行確認：

### Scenario

- [ ] 初始 Scenario 顯示 0 筆政策
- [ ] 沒修改 baseline 的項目不會出現在 Scenario
- [ ] 使用者修改號誌後才新增 signal policy
- [ ] 使用者建立紅線後才新增 red-line policy
- [ ] 使用者建立停車政策後才新增 parking policy

### Backend

- [ ] `/health` 正常
- [ ] `/api/simulations` 正常
- [ ] 三個 policy variable 都會實際影響 simulation
- [ ] 所有 KPI 來自 Python backend
- [ ] 同 input + seed 結果 deterministic
- [ ] historical baseline 優先於 synthetic fallback
- [ ] fallback 使用時有 warning / metadata

### Goals

- [ ] GoalConfig 不再只是 frontend hardcode label
- [ ] backend/shared logic 可判斷每個 goal 是否達標
- [ ] Dashboard 顯示 target/current/gap/met

### Gemini

- [ ] API key 從 env 讀取
- [ ] `.env.example` key 留空
- [ ] key 為空不會影響普通 simulation
- [ ] Gemini output 使用 structured schema
- [ ] AI 只能改三個允許的政策變量
- [ ] recommendation 有 bounds validation

### Optimization

- [ ] 可執行多輪 simulate → reason → patch → simulate
- [ ] 達標就停止
- [ ] max iterations 到就停止
- [ ] 每輪保留 scenario/result/reasoning history
- [ ] frontend 可以顯示 iteration history

### Quality

- [ ] `python -m pytest` 通過
- [ ] `npm run typecheck` 通過
- [ ] `npm run build` 通過
- [ ] 不 commit `.venv`
- [ ] 不 commit `.env.local`
- [ ] 不 commit Gemini API key

---

# 建議測試

至少新增：

```text
tests/test_scenario_diff.py
tests/test_policy_effects.py
tests/test_goals.py
tests/test_optimizer.py
```

其中 optimizer 測試不要真的打 Gemini API。

請 mock Gemini recommendation，例如：

```text
iteration 1 -> signal 50, red 120, parking 80
iteration 2 -> signal 55, red 150, parking 70
```

測試：

```text
1. recommendation 被 validation
2. scenario 正確更新
3. 每輪重新執行 simulation
4. goals_met 時停止
5. max_iterations 時停止
```

Gemini integration 可以另外做一個 optional/manual test。

---

# 完成後請回報

完成後不要 merge。

請提供：

```text
1. branch name
2. changed files
3. architecture summary
4. API endpoints
5. simulation policy effect formulas / assumptions
6. Gemini schema
7. optimization loop 行為
8. test results
9. known limitations
10. Demo 操作步驟
```

最後確認：

```bash
git status
git log --oneline -5
```

並將 branch push 到 origin：

```bash
git push -u origin feature/scenario-ai-optimizer-demo
```

等待 review，不要自行 merge main。
