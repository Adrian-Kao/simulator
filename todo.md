1.機器可讀的「路段/路口分時車流量 (Demand Profile)」
現狀：你的 data/historical/ 裡面有 taipei_traffic_survey_..._segments.pdf 和 ..._intersections.pdf。這些是政府的交通流量調查報告，雖然裡面有車流量，但格式是 PDF，無法直接讓程式讀取。
缺了什麼：你需要把 PDF 裡信義商圈相關的流量資料打成 CSV/JSON（例如：時間、路段 ID、小客車數量、機車數量），才能做成 ScenarioConfig 需要的 demand_profile 和計算 arrivals_per_tick。
VD 車偵器資料：你的 data/traffic/ 和 live/ 裡面有 vd_live.xml。雖然可以轉出車流，但它只有你抓取的那一瞬間的快照，缺乏一整天連續的分時歷史資料來跑完整的情境模擬。
2. 車道飽和流量 (Saturation Flow) 與 BPR 參數 (α, β)
現狀：沒有看到任何 calibration 相關的檔案。
缺了什麼：目前系統只能被迫使用預設值（飽和流量 1800 vph，BPR α=0.15, β=4.0）。不同路口和路段的實際特性差異很大，如果沒有針對信義區校準過這幾個參數，算出來的 Travel Time 和排隊長度會是失真的。
3. 用來驗證模型的歷史 Travel Time / 排隊長度
現狀：data/live/ 裡面有 traffic_travel_time.json，但一樣只是快照。
缺了什麼：當你的模擬器跑出某個時段（例如 17:30）的 Travel Time 是 3 分鐘時，你需要有一份真實的歷史連續資料（例如連續一週的平均旅行時間 CSV）來比對模擬結果準不準。