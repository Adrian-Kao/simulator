"use client";

import { useMemo, useState } from "react";

import {
  INTERSECTIONS as BASE_INTERSECTIONS,
  PARKINGS as BASE_PARKINGS,
  ROADS as BASE_ROADS,
  YOUBIKES as BASE_YOUBIKES,
} from "@/data/xinyi";

import type {
  IntersectionData,
  ParkingData,
  ParkingDraft,
  PolicyTool,
  Point,
  RoadSegmentData,
  ScenarioPolicyData,
  ScenarioSnapshot,
  YouBikeData,
} from "@/features/simulation/simulation.types";

import GoalPanel from "./GoalPanel";
import LeftSidebar from "./LeftSidebar";
import PolicyList from "./PolicyList";
import PolicyToolbar from "./PolicyToolbar";
import SimulationHeader from "./SimulationHeader";
import SimulationMap from "./SimulationMap";

import styles from "@/styles/simulation.module.css";

type YouBikeDraft = {
  x: number;
  y: number;
  name: string;
  docks: number;
};

const INITIAL_SCENARIO_POLICIES: ScenarioPolicyData[] = [
  {
    id: "policy-red-line-shifu",
    type: "red-line",
    title: "市府路紅線編輯",
    status: "active",
    description: "市府路（松壽路 - 忠孝東路五段）紅線微調",
    roadId: "shifu-road",
    targetId: "shifu-road",
    params: {
      lengthMeters: 180,
      direction: "two-way",
    },
  },
  {
    id: "policy-ubike-shangpin",
    type: "ubike-add",
    title: "新增 UBIKE 站點",
    status: "active",
    description: "市府路與松智路口東側新增 15 格車柱",
    targetId: "youbike-new-1",
    params: {
      docks: 15,
      stationName: "松智路站",
    },
  },
  {
    id: "policy-parking-remove",
    type: "parking-remove",
    title: "移除停車場",
    status: "pending-remove",
    description: "信義世貿停車場",
    targetId: "parking-xinyi-trade",
    params: {
      spaces: 150,
    },
  },
  {
    id: "policy-traffic-control",
    type: "traffic-control",
    title: "道路管制",
    status: "active",
    description: "市府路 / 松壽路口 14:00-20:00 禁止右轉",
    roadId: "shifu-road",
    targetId: "i-2",
    params: {
      window: "14:00-20:00",
      restriction: "forbid-right-turn",
    },
  },
];

function clone<T>(value: T): T {
  return structuredClone(value);
}

function pointsLength(points: Point[]) {
  return points.reduce((sum, point, index) => {
    if (index === 0) return sum;
    const prev = points[index - 1];
    return sum + Math.hypot(point.x - prev.x, point.y - prev.y);
  }, 0);
}

function formatLength(points: Point[]) {
  return Math.max(1, Math.round(pointsLength(points)));
}

function makeSnapshot(args: {
  selectedRoadId: string | null;
  selectedIntersectionId: string | null;
  activeTool: PolicyTool;
  roads: RoadSegmentData[];
  intersections: IntersectionData[];
  parkings: ParkingData[];
  youbikes: YouBikeData[];
  parkingDraft: ParkingDraft | null;
  youbikeDraft: YouBikeDraft | null;
  scenarioPolicies: ScenarioPolicyData[];
}): ScenarioSnapshot {
  return {
    selectedRoadId: args.selectedRoadId,
    selectedIntersectionId: args.selectedIntersectionId,
    activeTool: args.activeTool,
    roads: clone(args.roads),
    intersections: clone(args.intersections),
    parkings: clone(args.parkings),
    youbikes: clone(args.youbikes),
    parkingPolicies: [],
    scenarioPolicies: clone(args.scenarioPolicies),
  };
}

function buildRoadPolicy(road: RoadSegmentData): ScenarioPolicyData {
  return {
    id: `policy-red-line-${road.id}`,
    type: "red-line",
    title: `${road.roadName} 紅線編輯`,
    status: "editing",
    description: `${road.from} - ${road.to} 路段調整`,
    roadId: road.id,
    targetId: road.id,
    params: {
      lengthMeters: formatLength(road.points),
      direction: road.direction,
      points: road.points.length,
    },
  };
}

function buildIntersectionPolicy(
  intersection: IntersectionData,
): ScenarioPolicyData {
  return {
    id: `policy-intersection-${intersection.id}`,
    type: "intersection-control",
    title: `${intersection.name} 路口設定`,
    status: "editing",
    description: `${intersection.connectedRoadIds.length} 條道路與號誌相位設定`,
    targetId: intersection.id,
    params: {
      phases: intersection.phases.length,
      restrictions: intersection.restrictions.length,
    },
  };
}

function buildParkingPolicy(parking: ParkingData): ScenarioPolicyData {
  return {
    id: `policy-parking-${parking.id}`,
    type: "parking-add",
    title: `${parking.name} 停車場`,
    status: parking.status === "new" ? "editing" : "active",
    description: `${parking.spaces} 格車位`,
    targetId: parking.id,
    params: {
      spaces: parking.spaces,
    },
  };
}

function buildYouBikePolicy(station: YouBikeData): ScenarioPolicyData {
  return {
    id: `policy-youbike-${station.id}`,
    type: "ubike-add",
    title: `${station.name ?? "UBIKE 站點"}`,
    status: "active",
    description: `${station.docks ?? 15} 格車柱`,
    targetId: station.id,
    params: {
      docks: station.docks ?? 15,
    },
  };
}

export default function SimulationShell() {
  const [selectedRoadId, setSelectedRoadId] = useState<string | null>(null);
  const [selectedIntersectionId, setSelectedIntersectionId] = useState<
    string | null
  >(null);
  const [activeTool, setActiveTool] = useState<PolicyTool>("select");

  const [roads, setRoads] = useState<RoadSegmentData[]>(clone(BASE_ROADS));
  const [intersections, setIntersections] = useState<IntersectionData[]>(
    clone(BASE_INTERSECTIONS),
  );
  const [parkings, setParkings] = useState<ParkingData[]>(clone(BASE_PARKINGS));
  const [youbikes, setYoubikes] = useState<YouBikeData[]>(clone(BASE_YOUBIKES));

  const [parkingDraft, setParkingDraft] = useState<ParkingDraft | null>(null);
  const [youbikeDraft, setYoubikeDraft] = useState<YouBikeDraft | null>(null);
  const [scenarioPolicies, setScenarioPolicies] = useState<ScenarioPolicyData[]>(
    clone(INITIAL_SCENARIO_POLICIES),
  );
  const [history, setHistory] = useState<ScenarioSnapshot[]>([]);

  const selectedRoad = useMemo(() => {
    return roads.find((road) => road.id === selectedRoadId) ?? null;
  }, [roads, selectedRoadId]);

  const selectedIntersection = useMemo(() => {
    return (
      intersections.find((item) => item.id === selectedIntersectionId) ?? null
    );
  }, [intersections, selectedIntersectionId]);

  const selectedPolicy = useMemo(() => {
    if (selectedRoadId) {
      return (
        scenarioPolicies.find((policy) => policy.roadId === selectedRoadId) ??
        null
      );
    }

    if (selectedIntersectionId) {
      return (
        scenarioPolicies.find(
          (policy) => policy.targetId === selectedIntersectionId,
        ) ?? null
      );
    }

    return null;
  }, [scenarioPolicies, selectedIntersectionId, selectedRoadId]);

  const pushHistory = () => {
    setHistory((current) => [
      makeSnapshot({
        selectedRoadId,
        selectedIntersectionId,
        activeTool,
        roads,
        intersections,
        parkings,
        youbikes,
        parkingDraft,
        youbikeDraft,
        scenarioPolicies,
      }),
      ...current,
    ].slice(0, 20));
  };

  const syncRoadPolicy = (roadId: string, nextRoads: RoadSegmentData[]) => {
    const road = nextRoads.find((item) => item.id === roadId);
    if (!road) return;

    const nextPolicy = buildRoadPolicy(road);
    setScenarioPolicies((current) => {
      const exists = current.some((item) => item.id === nextPolicy.id);
      return exists
        ? current.map((item) => (item.id === nextPolicy.id ? nextPolicy : item))
        : [nextPolicy, ...current];
    });
  };

  const syncIntersectionPolicy = (
    intersectionId: string,
    nextIntersections: IntersectionData[],
  ) => {
    const intersection = nextIntersections.find((item) => item.id === intersectionId);
    if (!intersection) return;

    const nextPolicy = buildIntersectionPolicy(intersection);
    setScenarioPolicies((current) => {
      const exists = current.some((item) => item.id === nextPolicy.id);
      return exists
        ? current.map((item) => (item.id === nextPolicy.id ? nextPolicy : item))
        : [nextPolicy, ...current];
    });
  };

  const syncParkingPolicy = (parking: ParkingData) => {
    const nextPolicy = buildParkingPolicy(parking);
    setScenarioPolicies((current) => {
      const exists = current.some((item) => item.id === nextPolicy.id);
      return exists
        ? current.map((item) => (item.id === nextPolicy.id ? nextPolicy : item))
        : [nextPolicy, ...current];
    });
  };

  const syncYouBikePolicy = (station: YouBikeData) => {
    const nextPolicy = buildYouBikePolicy(station);
    setScenarioPolicies((current) => {
      const exists = current.some((item) => item.id === nextPolicy.id);
      return exists
        ? current.map((item) => (item.id === nextPolicy.id ? nextPolicy : item))
        : [nextPolicy, ...current];
    });
  };

  const restoreSnapshot = (snapshot: ScenarioSnapshot) => {
    setSelectedRoadId(snapshot.selectedRoadId);
    setSelectedIntersectionId(snapshot.selectedIntersectionId);
    setActiveTool(snapshot.activeTool);
    setRoads(clone(snapshot.roads));
    setIntersections(clone(snapshot.intersections));
    setParkings(clone(snapshot.parkings));
    setYoubikes(clone(snapshot.youbikes));
    setScenarioPolicies(clone(snapshot.scenarioPolicies));
  };

  const handleUndo = () => {
    setHistory((current) => {
      const [latest, ...rest] = current;
      if (!latest) return current;
      restoreSnapshot(latest);
      return rest;
    });
  };

  const handleChangeTool = (tool: PolicyTool) => {
    setActiveTool(tool);

    if (tool !== "parking") {
      setParkingDraft(null);
    }

    if (tool !== "youbike") {
      setYoubikeDraft(null);
    }

    if (tool === "select") {
      setSelectedIntersectionId(null);
      setSelectedRoadId(null);
    }
  };

  const handleSelectRoad = (roadId: string) => {
    const road = roads.find((item) => item.id === roadId);
    if (!road) return;

    pushHistory();
    setSelectedRoadId(roadId);
    setSelectedIntersectionId(null);
    if (activeTool === "select") {
      setActiveTool("red-line");
    }
    syncRoadPolicy(roadId, roads);
  };

  const handleSelectIntersection = (intersectionId: string) => {
    const intersection = intersections.find((item) => item.id === intersectionId);
    if (!intersection) return;

    pushHistory();
    setSelectedIntersectionId(intersectionId);
    setSelectedRoadId(null);
    if (activeTool === "select") {
      setActiveTool("traffic-control");
    }
    syncIntersectionPolicy(intersectionId, intersections);
  };

  const handleBackToDistrict = () => {
    setSelectedRoadId(null);
    setSelectedIntersectionId(null);
    setActiveTool("select");
  };

  const handleRoadPointMove = (
    roadId: string,
    pointIndex: number,
    point: Point,
  ) => {
    setRoads((current) => {
      const next = current.map((road) => {
        if (road.id !== roadId) return road;
        const points = road.points.map((currentPoint, index) =>
          index === pointIndex ? point : currentPoint,
        );
        const updated = {
          ...road,
          points,
          lengthMeters: formatLength(points),
        };
        return updated;
      });

      syncRoadPolicy(roadId, next);
      return next;
    });
  };

  const handleBeginRoadEdit = () => {
    pushHistory();
  };

  const handleResetRoad = (roadId: string) => {
    const baseline = BASE_ROADS.find((road) => road.id === roadId);
    if (!baseline) return;

    pushHistory();
    setRoads((current) =>
      current.map((road) => (road.id === roadId ? clone(baseline) : road)),
    );
    setScenarioPolicies((current) =>
      current.filter(
        (policy) =>
          policy.id !== `policy-red-line-${roadId}` &&
          policy.roadId !== roadId,
      ),
    );
  };

  const handleParkingLocation = (x: number, y: number) => {
    if (activeTool !== "parking") return;

    setParkingDraft({
      x,
      y,
      name: "新停車場",
      spaces: 30,
    });
  };

  const handleYouBikeLocation = (x: number, y: number) => {
    if (activeTool !== "youbike") return;

    pushHistory();

    const station: YouBikeData = {
      id: `youbike-${Date.now()}`,
      name: "新 UBIKE 站點",
      x,
      y,
      docks: 15,
    };

    setYoubikes((current) => [...current, station]);
    syncYouBikePolicy(station);
  };

  const handleUpdateParkingDraft = (patch: Partial<ParkingDraft>) => {
    setParkingDraft((current) => {
      if (!current) return current;
      return { ...current, ...patch };
    });
  };

  const handleCancelParking = () => {
    setParkingDraft(null);
  };

  const handleConfirmParking = () => {
    if (!parkingDraft) return;

    pushHistory();

    const parkingId = `parking-new-${Date.now()}`;
    const newParking: ParkingData = {
      id: parkingId,
      name: parkingDraft.name.trim() || "新停車場",
      x: parkingDraft.x,
      y: parkingDraft.y,
      spaces: Math.max(1, parkingDraft.spaces),
      status: "new",
    };

    setParkings((current) => [...current, newParking]);
    syncParkingPolicy(newParking);
    setParkingDraft(null);
  };

  const handleUpdateIntersectionPhase = (
    intersectionId: string,
    phaseIndex: number,
    seconds: number,
  ) => {
    pushHistory();

    setIntersections((current) => {
      const next = current.map((intersection) => {
        if (intersection.id !== intersectionId) return intersection;
        const phases = intersection.phases.map((phase, index) =>
          index === phaseIndex ? { ...phase, seconds: Math.max(1, seconds) } : phase,
        );
        return { ...intersection, phases };
      });

      syncIntersectionPolicy(intersectionId, next);
      return next;
    });
  };

  const handleAddIntersectionRestriction = (
    intersectionId: string,
    type: "forbid-right-turn" | "forbid-left-turn" | "forbid-entry",
    targetRoadId: string,
  ) => {
    pushHistory();

    setIntersections((current) => {
      const next = current.map((intersection) => {
        if (intersection.id !== intersectionId) return intersection;
        const restriction = {
          id: `restriction-${intersectionId}-${Date.now()}`,
          type,
          targetRoadId,
          note:
            type === "forbid-entry"
              ? "禁止進入"
              : type === "forbid-left-turn"
                ? "禁止左轉"
                : "禁止右轉",
        };
        return {
          ...intersection,
          restrictions: [...intersection.restrictions, restriction],
        };
      });

      syncIntersectionPolicy(intersectionId, next);
      return next;
    });
  };

  const handleRemoveIntersectionRestriction = (
    intersectionId: string,
    restrictionId: string,
  ) => {
    pushHistory();

    setIntersections((current) => {
      const next = current.map((intersection) => {
        if (intersection.id !== intersectionId) return intersection;
        return {
          ...intersection,
          restrictions: intersection.restrictions.filter(
            (restriction) => restriction.id !== restrictionId,
          ),
        };
      });

      syncIntersectionPolicy(intersectionId, next);
      return next;
    });
  };

  const handleDeletePolicy = (policyId: string) => {
    const policy = scenarioPolicies.find((item) => item.id === policyId);
    if (!policy) return;

    pushHistory();

    setScenarioPolicies((current) => current.filter((item) => item.id !== policyId));

    if (policy.type === "red-line" && policy.roadId) {
      const baseline = BASE_ROADS.find((road) => road.id === policy.roadId);
      if (baseline) {
        setRoads((current) =>
          current.map((road) => (road.id === baseline.id ? clone(baseline) : road)),
        );
      }
    }

    if (policy.type === "intersection-control" && policy.targetId) {
      const baseline = BASE_INTERSECTIONS.find((item) => item.id === policy.targetId);
      if (baseline) {
        setIntersections((current) =>
          current.map((item) => (item.id === baseline.id ? clone(baseline) : item)),
        );
      }
    }

    if (policy.type === "parking-add" && policy.targetId) {
      setParkings((current) => current.filter((item) => item.id !== policy.targetId));
    }

    if (policy.type === "ubike-add" && policy.targetId) {
      setYoubikes((current) => current.filter((item) => item.id !== policy.targetId));
    }
  };

  const handleEditPolicy = (policy: ScenarioPolicyData) => {
    if (policy.roadId) {
      setSelectedRoadId(policy.roadId);
      setSelectedIntersectionId(null);
      setActiveTool("red-line");
      return;
    }

    if (policy.type === "intersection-control" && policy.targetId) {
      setSelectedIntersectionId(policy.targetId);
      setSelectedRoadId(null);
      setActiveTool("traffic-control");
      return;
    }

    if (policy.type === "parking-add" && policy.targetId) {
      const parking = parkings.find((item) => item.id === policy.targetId);
      if (parking) {
        setActiveTool("parking");
        setParkingDraft({
          x: parking.x,
          y: parking.y,
          name: parking.name,
          spaces: parking.spaces,
        });
      }
      return;
    }
  };

  const handleSaveIntersection = () => {
    if (!selectedIntersection) return;
    pushHistory();
    syncIntersectionPolicy(selectedIntersection.id, intersections);
  };

  return (
    <main className={styles.page}>
      <SimulationHeader />

      <PolicyToolbar activeTool={activeTool} onChangeTool={handleChangeTool} />

      <section
        className={`${styles.workspace} ${
          selectedRoad || selectedIntersection ? styles.workspaceRoadFocus : ""
        }`}
      >
        <LeftSidebar
          activeTool={activeTool}
          roads={roads}
          selectedRoad={selectedRoad}
          selectedIntersection={selectedIntersection}
          parkingDraft={parkingDraft}
          onUpdateParkingDraft={handleUpdateParkingDraft}
          onCancelParking={handleCancelParking}
          onConfirmParking={handleConfirmParking}
          onUpdateIntersectionPhase={handleUpdateIntersectionPhase}
          onAddIntersectionRestriction={handleAddIntersectionRestriction}
          onRemoveIntersectionRestriction={handleRemoveIntersectionRestriction}
          onSaveIntersection={handleSaveIntersection}
          onResetRoad={handleResetRoad}
          selectedPolicy={selectedPolicy}
        />

        <SimulationMap
          activeTool={activeTool}
          roads={roads}
          intersections={intersections}
          parkings={parkings}
          youbikes={youbikes}
          selectedRoadId={selectedRoadId}
          selectedIntersectionId={selectedIntersectionId}
          parkingDraft={parkingDraft}
          onSelectRoad={handleSelectRoad}
          onSelectIntersection={handleSelectIntersection}
          onBackToDistrict={handleBackToDistrict}
          onPickParkingLocation={handleParkingLocation}
          onPickYouBikeLocation={handleYouBikeLocation}
          onBeginRoadEdit={handleBeginRoadEdit}
          onUpdateRoadPoint={handleRoadPointMove}
        />

        <GoalPanel />
      </section>

      <PolicyList
        scenarioName="Scenario A"
        policies={scenarioPolicies}
        canUndo={history.length > 0}
        onUndo={handleUndo}
        onEditPolicy={handleEditPolicy}
        onDeletePolicy={handleDeletePolicy}
      />
    </main>
  );
}
