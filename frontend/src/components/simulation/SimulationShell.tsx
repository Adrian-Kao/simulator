"use client";

import { useMemo, useState } from "react";

import {
  INTERSECTIONS,
  PARKINGS,
  ROADS,
  YOUBIKES,
} from "@/data/xinyi";

import {
  redLineLengthMeters,
} from "@/features/simulation/curb.utils";

import {
  runSimulation,
  type SimulationApiResult,
  type SimulationPolicyPayload,
  type SimulationStatus,
} from "@/lib/simulation-api";

import type {
  CurbSide,
  ParkingData,
  ParkingDraft,
  ParkingPolicyData,
  PolicyTool,
  RedLinePolicyData,
  RoadSegmentData,
  TurnRestrictionType,
} from "@/features/simulation/simulation.types";

import GoalPanel from "./GoalPanel";
import LeftSidebar from "./LeftSidebar";
import PolicyList from "./PolicyList";
import PolicyToolbar from "./PolicyToolbar";
import SimulationHeader from "./SimulationHeader";
import SimulationMap from "./SimulationMap";

import styles from "@/styles/simulation.module.css";

export default function SimulationShell() {
  const [roads, setRoads] = useState<RoadSegmentData[]>(
    () => structuredClone(ROADS),
  );

  const [selectedRoadId, setSelectedRoadId] =
    useState<string | null>(null);

  const [
    selectedIntersectionId,
    setSelectedIntersectionId,
  ] = useState<string | null>(null);

  const [intersections, setIntersections] =
    useState(() => structuredClone(INTERSECTIONS));

  const [activeTool, setActiveTool] =
    useState<PolicyTool>("select");

  const [parkings, setParkings] =
    useState<ParkingData[]>(
      () => structuredClone(PARKINGS),
    );

  const [parkingDraft, setParkingDraft] =
    useState<ParkingDraft | null>(null);

  const [
    parkingPolicies,
    setParkingPolicies,
  ] = useState<ParkingPolicyData[]>([]);

  const [
    redLineDraft,
    setRedLineDraft,
  ] = useState<RedLinePolicyData | null>(null);

  const [
    redLinePolicies,
    setRedLinePolicies,
  ] = useState<RedLinePolicyData[]>([]);

  const [
    simulationStatus,
    setSimulationStatus,
  ] = useState<SimulationStatus>("idle");

  const [
    simulationResult,
    setSimulationResult,
  ] = useState<SimulationApiResult | null>(
    null,
  );

  const [
    simulationError,
    setSimulationError,
  ] = useState<string | null>(null);

  const selectedRoad = useMemo(() => {
    return (
      roads.find(
        (road) => road.id === selectedRoadId,
      ) ?? null
    );
  }, [roads, selectedRoadId]);

  const selectedIntersection = useMemo(() => {
    return (
      intersections.find(
        (intersection) =>
          intersection.id ===
          selectedIntersectionId,
      ) ?? null
    );
  }, [
    intersections,
    selectedIntersectionId,
  ]);

  const createRedLineDraft = (
    roadId: string,
    side: CurbSide = "left",
  ): RedLinePolicyData | null => {
    const road = roads.find(
      (item) => item.id === roadId,
    );

    if (!road) {
      return null;
    }

    const startOffset = 0.25;
    const endOffset = 0.75;

    return {
      id: `draft-red-line-${roadId}`,
      roadId,
      side,
      startOffset,
      endOffset,
      lengthMeters:
        redLineLengthMeters(
          road,
          startOffset,
          endOffset,
        ),
      startTime: "00:00",
      endTime: "23:59",
    };
  };

  const handleCreateRedLine = () => {
    if (!selectedRoadId) {
      return;
    }

    setActiveTool("red-line");

    setRedLineDraft(
      createRedLineDraft(
        selectedRoadId,
        "left",
      ),
    );
  };

  const handleUpdateRedLineDraft = (
    patch: Partial<RedLinePolicyData>,
  ) => {
    setRedLineDraft((current) => {
      if (!current) {
        return null;
      }

      const next = {
        ...current,
        ...patch,
      };

      const road = roads.find(
        (item) => item.id === next.roadId,
      );

      if (!road) {
        return next;
      }

      const startOffset = Math.max(
        0,
        Math.min(
          1,
          Math.min(
            next.startOffset,
            next.endOffset,
          ),
        ),
      );

      const endOffset = Math.max(
        0,
        Math.min(
          1,
          Math.max(
            next.startOffset,
            next.endOffset,
          ),
        ),
      );

      return {
        ...next,
        startOffset,
        endOffset,
        lengthMeters:
          redLineLengthMeters(
            road,
            startOffset,
            endOffset,
          ),
      };
    });
  };

  const handleCancelRedLine = () => {
    setRedLineDraft(null);
  };

  const handleApplyRedLine = () => {
    if (!redLineDraft) {
      return;
    }

    const road = roads.find(
      (item) =>
        item.id === redLineDraft.roadId,
    );

    if (!road) {
      return;
    }

    const startOffset = Math.min(
      redLineDraft.startOffset,
      redLineDraft.endOffset,
    );

    const endOffset = Math.max(
      redLineDraft.startOffset,
      redLineDraft.endOffset,
    );

    if (
      endOffset - startOffset <
      0.005
    ) {
      return;
    }

    const applied: RedLinePolicyData = {
      ...redLineDraft,
      id: `red-line-${Date.now()}`,
      startOffset,
      endOffset,
      lengthMeters:
        redLineLengthMeters(
          road,
          startOffset,
          endOffset,
        ),
    };

    setRedLinePolicies(
      (current) => [
        ...current,
        applied,
      ],
    );

    setRedLineDraft(null);
  };

  const handleSelectRoad = (
    roadId: string,
  ) => {
    if (
      activeTool === "parking" ||
      activeTool === "youbike"
    ) {
      return;
    }

    const road = roads.find(
      (item) => item.id === roadId,
    );

    if (!road) {
      return;
    }

    setSelectedIntersectionId(null);
    setSelectedRoadId(roadId);
    setActiveTool("red-line");

    setRedLineDraft(
      createRedLineDraft(
        roadId,
        "left",
      ),
    );
  };

  const handleSelectIntersection = (
    intersectionId: string,
  ) => {
    setSelectedRoadId(null);
    setRedLineDraft(null);
    setSelectedIntersectionId(
      intersectionId,
    );
    setActiveTool("traffic-control");
  };

  const handleChangeTool = (
    tool: PolicyTool,
  ) => {
    setActiveTool(tool);

    if (
      tool === "parking" ||
      tool === "youbike"
    ) {
      setSelectedRoadId(null);
      setSelectedIntersectionId(null);
      setRedLineDraft(null);
    }

    if (
      tool === "traffic-control" ||
      tool === "intersection" ||
      tool === "signal"
    ) {
      setSelectedRoadId(null);
      setRedLineDraft(null);
    }

    if (tool !== "parking") {
      setParkingDraft(null);
    }

    if (
      tool !== "red-line" &&
      tool !== "select"
    ) {
      setRedLineDraft(null);
    }

    if (
      tool === "red-line" &&
      selectedRoadId
    ) {
      setRedLineDraft(
        createRedLineDraft(
          selectedRoadId,
          "left",
        ),
      );
    }
  };

  const handleResetRoad = (
    roadId: string,
  ) => {
    const original = ROADS.find(
      (road) => road.id === roadId,
    );

    if (!original) {
      return;
    }

    setRoads((current) =>
      current.map((road) =>
        road.id === roadId
          ? structuredClone(original)
          : road,
      ),
    );

    if (
      selectedRoadId === roadId &&
      activeTool === "red-line"
    ) {
      setRedLineDraft(
        createRedLineDraft(
          roadId,
          "left",
        ),
      );
    }
  };

  const handleBackToDistrict = () => {
    setSelectedRoadId(null);
    setSelectedIntersectionId(null);
    setParkingDraft(null);
    setRedLineDraft(null);
    setActiveTool("select");
  };

  const handleUpdateIntersectionPhase = (
    intersectionId: string,
    phaseIndex: number,
    seconds: number,
  ) => {
    setIntersections((current) =>
      current.map(
        (intersection) => {
          if (
            intersection.id !==
            intersectionId
          ) {
            return intersection;
          }

          return {
            ...intersection,
            phases:
              intersection.phases.map(
                (phase, index) =>
                  index === phaseIndex
                    ? {
                        ...phase,
                        seconds:
                          Math.max(
                            1,
                            seconds,
                          ),
                      }
                    : phase,
              ),
          };
        },
      ),
    );
  };

  const handleAddIntersectionRestriction = (
    intersectionId: string,
    type: TurnRestrictionType,
    targetRoadId: string,
  ) => {
    if (!targetRoadId) {
      return;
    }

    setIntersections((current) =>
      current.map(
        (intersection) => {
          if (
            intersection.id !==
            intersectionId
          ) {
            return intersection;
          }

          return {
            ...intersection,
            restrictions: [
              ...intersection.restrictions,
              {
                id:
                  `restriction-${Date.now()}`,
                type,
                targetRoadId,
                note:
                  "Scenario 新增限制",
              },
            ],
          };
        },
      ),
    );
  };

  const handleRemoveIntersectionRestriction = (
    intersectionId: string,
    restrictionId: string,
  ) => {
    setIntersections((current) =>
      current.map(
        (intersection) => {
          if (
            intersection.id !==
            intersectionId
          ) {
            return intersection;
          }

          return {
            ...intersection,
            restrictions:
              intersection.restrictions.filter(
                (restriction) =>
                  restriction.id !==
                  restrictionId,
              ),
          };
        },
      ),
    );
  };

  const handlePickParkingLocation = (
    x: number,
    y: number,
  ) => {
    if (
      activeTool !== "parking"
    ) {
      return;
    }

    setParkingDraft({
      x,
      y,
      name: "新增停車場",
      spaces: 30,
    });
  };

  const handleUpdateParkingDraft = (
    patch: Partial<ParkingDraft>,
  ) => {
    setParkingDraft((current) => {
      if (!current) {
        return null;
      }

      return {
        ...current,
        ...patch,
      };
    });
  };

  const handleCancelParking = () => {
    setParkingDraft(null);
  };

  const handleConfirmParking = () => {
    if (!parkingDraft) {
      return;
    }

    const parkingId =
      `parking-new-${Date.now()}`;

    const newParking: ParkingData = {
      id: parkingId,
      name:
        parkingDraft.name.trim() ||
        "新增停車場",
      x: parkingDraft.x,
      y: parkingDraft.y,
      spaces: Math.max(
        1,
        parkingDraft.spaces,
      ),
      status: "new",
    };

    setParkings((current) => [
      ...current,
      newParking,
    ]);

    const newPolicy: ParkingPolicyData = {
      id:
        `policy-parking-${Date.now()}`,
      parkingId,
      name: newParking.name,
      spaces: newParking.spaces,
    };

    setParkingPolicies((current) => [
      ...current,
      newPolicy,
    ]);

    setParkingDraft(null);
  };

  const handleRunSimulation = async () => {
    const redLinePayloads:
      SimulationPolicyPayload[] =
      redLinePolicies.map((policy) => ({
        type: "red-line",
        road_id: policy.roadId,
        side: policy.side,
        start_offset: policy.startOffset,
        end_offset: policy.endOffset,
        length_meters: policy.lengthMeters,
        start_time: policy.startTime,
        end_time: policy.endTime,
      }));

    const parkingPayloads:
      SimulationPolicyPayload[] =
      parkingPolicies.map((policy) => ({
        type: "parking",
        parking_id: policy.parkingId,
        name: policy.name,
        spaces: policy.spaces,
      }));

    const orderedIntersections =
      selectedIntersection
        ? [
            selectedIntersection,
            ...intersections.filter(
              (item) =>
                item.id !==
                selectedIntersection.id,
            ),
          ]
        : intersections;

    const signalPayloads:
      SimulationPolicyPayload[] =
      orderedIntersections.map(
        (intersection) => ({
          type: "signal-timing",
          intersection_id:
            intersection.id,
          phases:
            intersection.phases.map(
              (phase) => ({
                name: phase.name,
                seconds: phase.seconds,
                color: phase.color,
              }),
            ),
        }),
      );

    const restrictionPayloads:
      SimulationPolicyPayload[] =
      intersections.flatMap(
        (intersection) =>
          intersection.restrictions.map(
            (restriction) => ({
              type:
                "traffic-restriction" as const,
              intersection_id:
                intersection.id,
              restriction_type:
                restriction.type,
              target_road_id:
                restriction.targetRoadId,
            }),
          ),
      );

    setSimulationStatus("running");
    setSimulationError(null);

    try {
      const result =
        await runSimulation({
          scenario_id: "scenario-a",
          day_type: "weekday",
          time_slot: "17:30",
          random_seed: 42,
          road_id:
            selectedRoadId ??
            "shifu-road",
          road_name:
            selectedRoad?.roadName ??
            "市府路",
          policies: [
            ...signalPayloads,
            ...redLinePayloads,
            ...parkingPayloads,
            ...restrictionPayloads,
          ],
        });

      setSimulationResult(result);
      setSimulationStatus("success");
    } catch (error) {
      setSimulationResult(null);
      setSimulationStatus("error");
      setSimulationError(
        error instanceof Error
          ? error.message
          : "Unknown simulation error",
      );
    }
  };

  return (
    <main className={styles.page}>
      <SimulationHeader />

      <PolicyToolbar
        activeTool={activeTool}
        onChangeTool={handleChangeTool}
      />

      <section
        className={`${styles.workspace} ${
          selectedRoad
            ? styles.workspaceRoadFocus
            : ""
        }`}
      >
        <LeftSidebar
          selectedRoad={selectedRoad}
          selectedIntersection={
            selectedIntersection
          }
          activeTool={activeTool}
          roads={roads}
          parkingDraft={parkingDraft}
          redLineDraft={redLineDraft}
          selectedPolicy={null}
          onUpdateParkingDraft={
            handleUpdateParkingDraft
          }
          onCancelParking={
            handleCancelParking
          }
          onConfirmParking={
            handleConfirmParking
          }
          onCreateRedLine={
            handleCreateRedLine
          }
          onUpdateRedLineDraft={
            handleUpdateRedLineDraft
          }
          onCancelRedLine={
            handleCancelRedLine
          }
          onApplyRedLine={
            handleApplyRedLine
          }
          onUpdateIntersectionPhase={
            handleUpdateIntersectionPhase
          }
          onAddIntersectionRestriction={
            handleAddIntersectionRestriction
          }
          onRemoveIntersectionRestriction={
            handleRemoveIntersectionRestriction
          }
          onSaveIntersection={() => {
            console.log(
              "Intersection 設定已套用",
            );
          }}
          onResetRoad={
            handleResetRoad
          }
        />

        <SimulationMap
          selectedRoadId={
            selectedRoadId
          }
          selectedIntersectionId={
            selectedIntersectionId
          }
          activeTool={activeTool}
          roads={roads}
          intersections={
            intersections
          }
          parkings={parkings}
          youbikes={YOUBIKES}
          parkingDraft={
            parkingDraft
          }
          redLineDraft={
            redLineDraft
          }
          redLinePolicies={
            redLinePolicies
          }
          onSelectRoad={
            handleSelectRoad
          }
          onSelectIntersection={
            handleSelectIntersection
          }
          onBackToDistrict={
            handleBackToDistrict
          }
          onPickParkingLocation={
            handlePickParkingLocation
          }
          onPickYouBikeLocation={() => {
            console.log(
              "YouBike 新增功能尚未接上",
            );
          }}
          onUpdateRedLineDraft={
            handleUpdateRedLineDraft
          }
        />

        <GoalPanel
          simulationStatus={
            simulationStatus
          }
          simulationResult={
            simulationResult
          }
          simulationError={
            simulationError
          }
          onRunSimulation={
            handleRunSimulation
          }
        />
      </section>

      <PolicyList
        parkingPolicies={
          parkingPolicies
        }
        redLinePolicies={
          redLinePolicies
        }
        roads={roads}
      />
    </main>
  );
}