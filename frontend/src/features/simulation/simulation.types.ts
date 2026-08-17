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
   RED LINE
========================================================= */

export type CurbSide =
  | "left"
  | "right";

export type RedLinePolicyData = {
  id: string;

  roadId: string;

  side: CurbSide;

  startOffset: number;

  endOffset: number;

  lengthMeters: number;

  startTime?: string;

  endTime?: string;
};