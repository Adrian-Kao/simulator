/* =========================================================
   BASIC GEOMETRY
========================================================= */

export type Point = {
  x: number;
  y: number;
};

export type CameraBounds = {
  x: number;
  y: number;
  width: number;
  height: number;
};

export type MapMode =
  | "district"
  | "road-focus"
  | "intersection-focus";

/* =========================================================
   POLICY TOOL
========================================================= */

export type PolicyTool =
  | "select"
  | "red-line"
  | "youbike"
  | "parking"
  | "traffic-control"
  | "intersection"
  | "signal";

/* =========================================================
   TURN RESTRICTION
========================================================= */

export type TurnRestrictionType =
  | "forbid-right-turn"
  | "forbid-left-turn"
  | "forbid-entry";

export type TurnRestrictionData = {
  id: string;

  type: TurnRestrictionType;

  /*
   * 被限制的目標道路
   */
  targetRoadId: string;

  note?: string;
};

/* =========================================================
   TRAFFIC SIGNAL
========================================================= */

export type SignalColor =
  | "green"
  | "yellow"
  | "red";

export type SignalPhaseData = {
  name: string;

  seconds: number;

  color: SignalColor;
};

/* =========================================================
   INTERSECTION
========================================================= */

export type IntersectionData = {
  id: string;

  name: string;

  /*
   * SVG World Coordinate
   */
  x: number;
  y: number;

  /*
   * 這個路口連接哪些道路
   */
  connectedRoadIds: string[];

  /*
   * 紅綠燈相位
   */
  phases: SignalPhaseData[];

  /*
   * 禁止右轉 / 左轉 / 進入
   */
  restrictions: TurnRestrictionData[];
};

/* =========================================================
   ROAD
========================================================= */

export type RoadDirection =
  | "one-way"
  | "two-way";

export type RoadAlignment =
  | "vertical"
  | "horizontal";

export type RoadCurbData = {
  left: Point[];
  right: Point[];
};

export type RoadSegmentData = {
  id: string;

  roadName: string;

  from: string;
  to: string;

  /*
   * 目前新版 xinyi.ts 有些道路沒有直接填 lengthMeters，
   * 所以先設 optional。
   */
  lengthMeters?: number;

  direction: RoadDirection;

  alignment: RoadAlignment;

  /*
   * 道路中心線
   */
  points: Point[];

  /*
   * 左右 curb
   */
  curb?: RoadCurbData;

  /*
   * 此道路經過的 Intersection ID
   */
  intersectionIds?: string[];

  /*
   * 道路本身的轉向限制
   */
  turnRestrictions?: TurnRestrictionData[];

  label?: {
    x: number;
    y: number;
    rotate?: number;
  };

  focusBounds: CameraBounds;
};

/* =========================================================
   BUILDING
========================================================= */

export type BuildingData = {
  id: string;

  name: string;

  x: number;
  y: number;

  width: number;
  height: number;
};

/* =========================================================
   PARK
========================================================= */

export type ParkData = {
  id: string;

  name: string;

  x: number;
  y: number;

  width: number;
  height: number;
};

/* =========================================================
   PARKING
========================================================= */

export type ParkingStatus =
  | "existing"
  | "new";

export type ParkingData = {
  id: string;

  name: string;

  x: number;
  y: number;

  spaces: number;

  status: ParkingStatus;
};

export type ParkingDraft = {
  x: number;
  y: number;

  name: string;

  spaces: number;
};

export type ParkingPolicyData = {
  id: string;

  parkingId: string;

  name: string;

  spaces: number;
};

/* =========================================================
   YOUBIKE
========================================================= */

export type YouBikeData = {
  id: string;

  x: number;
  y: number;

  name?: string;

  docks?: number;

  status?: "existing" | "new";
};

/* =========================================================
   SCENARIO POLICY
========================================================= */

export type ScenarioPolicyStatus =
  | "active"
  | "editing"
  | "pending-remove";

export type ScenarioPolicyType =
  | "red-line"
  | "parking"
  | "youbike"
  | "traffic-control"
  | "signal-timing";

export type ScenarioPolicyData = {
  id: string;

  type: ScenarioPolicyType;

  status: ScenarioPolicyStatus;

  title?: string;

  targetId?: string;

  roadId?: string;

  intersectionId?: string;

  parkingId?: string;

  note?: string;
};

/* =========================================================
   SCENARIO / PYTHON SIMULATION API CONTRACT
========================================================= */

export type ScenarioData = {
  id: string;

  name: string;

  policies: ScenarioPolicyData[];
};

export type SimulationDayType =
  | "weekday"
  | "weekend"
  | "event";

export type SimulationRequest = {
  scenario: ScenarioData;

  dayType: SimulationDayType;

  /*
   * V1 先用字串表示，例如 "07:00-09:00"。
   * FastAPI 接上後再與 Python ScenarioConfig 對齊。
   */
  timeSlot: string;

  randomSeed?: number;
};

export type SimulationKpi = {
  travelTimeMinutes: number;

  travelSpeedKph: number;

  congestionVc: number;

  queueVehicles?: number;
};

export type SimulationDelta = {
  travelTimePercent: number;

  travelSpeedPercent: number;

  congestionVcPercent: number;
};

export type SimulationResult = {
  baseline: SimulationKpi;

  scenario: SimulationKpi;

  delta: SimulationDelta;
};

/* =========================================================
   RED LINE
========================================================= */

export type CurbSide =
  | "left"
  | "right";

export type RedLinePolicyData = {
  id: string;

  roadId: string;

  side: CurbSide;

  /*
   * 0..1，表示沿 curb polyline 的正規化位置。
   */
  startOffset: number;

  /*
   * 0..1，表示沿 curb polyline 的正規化位置。
   */
  endOffset: number;

  lengthMeters: number;

  startTime?: string;

  endTime?: string;
};

/* =========================================================
   SCENARIO DIFF

   Scenario = 相對 Baseline 的修改。
   Baseline（道路 / 號誌 / 停車場 / YouBike / 既有紅線）不是 policy，
   所以只有真的改過的項目才會變成 ScenarioDiffEntry。

   Demo 第一版只允許三個變量：
     X1 = signal_green_seconds
     X2 = red_line_meters
     X3 = parking_spaces
========================================================= */

export type ScenarioDiffType =
  | "signal-timing"
  | "red-line"
  | "parking";

export type ScenarioDiffEntry = {
  id: string;

  type: ScenarioDiffType;

  title: string;

  description: string;

  /*
   * 這筆修改對應的 baseline 物件。
   */
  targetId: string;

  intersectionId?: string;
  roadId?: string;
  parkingId?: string;

  baselineLabel: string;
  scenarioLabel: string;

  baselineValue: number;
  scenarioValue: number;

  unit: string;
};

/* =========================================================
   GOALS
========================================================= */

export type GoalMetric =
  | "travel_time_percent"
  | "travel_speed_percent"
  | "congestion_vc_percent"
  | "queue_percent";

/*
 * 目標為「相對 baseline 的百分比變化」，正負號代表方向：
 *   travel_time_percent: -10 → 旅行時間至少下降 10%
 *   travel_speed_percent: 8  → 旅行速度至少上升 8%
 */
export type GoalConfig = Partial<Record<GoalMetric, number>>;