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

export type MapMode = "district" | "district-overview" | "road-focus";

export type FocusMode = MapMode | "intersection-focus";

export type PolicyTool =
  | "select"
  | "red-line"
  | "youbike"
  | "parking"
  | "traffic-control"
  | "intersection";

export type RoadSegmentData = {
  id: string;
  roadName: string;
  from: string;
  to: string;
  /* 長度一律用 polylineLengthMeters(points) 推導，不存快取值。 */
  direction: "one-way" | "two-way";
  alignment?: "vertical" | "horizontal" | "polyline";

  points: Point[];

  curb?: {
    left: Point[];
    right: Point[];
  };

  intersectionIds?: string[];

  turnRestrictions?: TurnRestriction[];

  label?: {
    x: number;
    y: number;
    rotate?: number;
  };

  focusBounds: CameraBounds;
};

export type IntersectionPhase = {
  name: string;
  seconds: number;
  color: "red" | "yellow" | "green";
};

export type TurnRestrictionType =
  | "forbid-right-turn"
  | "forbid-left-turn"
  | "forbid-entry";

export type TurnRestriction = {
  id: string;
  type: TurnRestrictionType;
  targetRoadId: string;
  note: string;
};

export type IntersectionData = {
  id: string;
  name: string;
  x: number;
  y: number;
  connectedRoadIds: string[];
  phases: IntersectionPhase[];
  restrictions: TurnRestriction[];
};

export type BuildingData = {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

export type ParkData = {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
};

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

export type YouBikeData = {
  id: string;
  name?: string;
  x: number;
  y: number;
  docks?: number;
};




export type ParkingDraft = {
  x: number;
  y: number;

  name: string;
  spaces: number;
};

export type ScenarioPolicyStatus =
  | "editing"
  | "active"
  | "pending-remove";

export type ScenarioPolicyType =
  | "red-line"
  | "ubike-add"
  | "parking-add"
  | "parking-remove"
  | "traffic-control"
  | "intersection-control";

export type ScenarioPolicyData = {
  id: string;
  type: ScenarioPolicyType;
  title: string;
  status: ScenarioPolicyStatus;
  description: string;
  targetId?: string;
  roadId?: string;
  params: Record<string, string | number | boolean>;
};

export type ScenarioData = {
  id: string;
  name: string;
  policies: ScenarioPolicyData[];
  undoStack: ScenarioSnapshot[];
};

export type ScenarioSnapshot = {
  selectedRoadId: string | null;
  selectedIntersectionId: string | null;
  activeTool: PolicyTool;
  roads: RoadSegmentData[];
  intersections: IntersectionData[];
  parkings: ParkingData[];
  youbikes: YouBikeData[];
  parkingDraft: ParkingDraft | null;
  scenarioPolicies: ScenarioPolicyData[];
};

/* =========================================================
   COMPATIBILITY TYPES
========================================================= */

export type Coordinate = [number, number];

export type Building = {
  id: string;
  name: string;
  kind: string;
  footprint: Coordinate[];
};

export type DistrictBoundary = {
  id: string;
  name: string;
  coordinates: Coordinate[];
};

export type ParkingLot = {
  id: string;
  name: string;
  capacity: number;
  coordinate: Coordinate;
  coordinates?: Coordinate[];
};

export type Park = {
  id: string;
  name: string;
  kind?: string;
  footprint?: Coordinate[];
  boundary?: Coordinate[];
};

export type RoadSegment = {
  id: string;
  roadId: string;
  name: string;
  start: string;
  end: string;
  direction: "one-way" | "two-way";
  roadWidthMeters: number;
  lengthMeters: number;
  coordinates: Coordinate[];
};

export type TrafficLight = {
  id: string;
  name: string;
  coordinate: Coordinate;
  coordinates?: Coordinate;
  direction?: string;
};

export type YouBikeStation = {
  id: string;
  name: string;
  coordinate: Coordinate;
  coordinates?: Coordinate;
  docks: number;
};

export type PolicyType = PolicyTool;

export type Goal = {
  id: string;
  metric: string;
  direction: "increase" | "decrease";
  targetPercent: number;
};

export type SimulationState = {
  mapMode: MapMode;
  selectedRoadId: string | null;
  hoveredRoadId: string | null;
  activePolicyType: PolicyType;
  goals: Goal[];
  policies: Array<{
    id: string;
    type: PolicyType;
    name: string;
    status: ScenarioPolicyStatus;
    roadSegmentId?: string;
    params: Record<string, string | number | boolean>;
  }>;
};
