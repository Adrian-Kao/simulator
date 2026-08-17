"use client";

import { useMemo, useState } from "react";

import {
  INTERSECTIONS,
  PARKINGS,
  ROADS,
  YOUBIKES,
} from "@/data/xinyi";

import type {
  ParkingData,
  ParkingDraft,
  ParkingPolicyData,
  Point,
  PolicyTool,
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

  const [activeTool, setActiveTool] =
    useState<PolicyTool>("select");

  const [
    selectedIntersectionId,
    setSelectedIntersectionId,
  ] = useState<string | null>(null);

  const [intersections, setIntersections] =
    useState(INTERSECTIONS);

  /*
   * 地圖上的停車場
   * 初始值來自 xinyi.ts
   */
  const [parkings, setParkings] =
    useState<ParkingData[]>(PARKINGS);

  /*
   * 使用者目前尚未確認的停車場
   */
  const [parkingDraft, setParkingDraft] =
    useState<ParkingDraft | null>(null);

  /*
   * 新增停車場形成的 Scenario Policy
   */
  const [
    parkingPolicies,
    setParkingPolicies,
  ] = useState<ParkingPolicyData[]>([]);

  const selectedRoad = useMemo(() => {
    return (
      roads.find(
        (road) => road.id === selectedRoadId,
      ) ?? null
    );
  }, [roads, selectedRoadId]);

  const selectedIntersection =
    useMemo(() => {
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

  const handleSelectIntersection = (
    intersectionId: string,
  ) => {
    setSelectedRoadId(null);
    setSelectedIntersectionId(
      intersectionId,
    );

    if (
      activeTool !== "traffic-control"
    ) {
      setActiveTool("intersection");
    }
  };

  const handleSelectRoad = (
    roadId: string,
  ) => {
    if (
      activeTool === "parking" ||
      activeTool === "youbike" ||
      activeTool === "intersection"
    ) {
      return;
    }

    setSelectedIntersectionId(null);
    setSelectedRoadId(roadId);
    setActiveTool("red-line");
  };

  /* ==========================================
     TOOL
  ========================================== */

  const handleChangeTool = (
    tool: PolicyTool,
  ) => {
    setActiveTool(tool);

    if (
      tool === "parking" ||
      tool === "youbike" ||
      tool === "intersection"
    ) {
      setSelectedRoadId(null);
    }

    if (tool !== "parking") {
      setParkingDraft(null);
    }
  };

  /* ==========================================
     ROAD
  ========================================== */

  const handleUpdateRoadPoint = (
    roadId: string,
    pointIndex: number,
    point: Point,
  ) => {
    setRoads((current) =>
      current.map((road) => {
        if (road.id !== roadId) {
          return road;
        }

        return {
          ...road,
          points: road.points.map(
            (currentPoint, index) =>
              index === pointIndex
                ? point
                : currentPoint,
          ),
        };
      }),
    );
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
  };

  const handleBackToDistrict = () => {
    setSelectedRoadId(null);
    setSelectedIntersectionId(null);
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

  /* ==========================================
     PARKING
  ========================================== */

  const handlePickParkingLocation = (
    x: number,
    y: number,
  ) => {
    if (activeTool !== "parking") {
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
        return current;
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
      id: `policy-parking-${Date.now()}`,
      parkingId,
      name: newParking.name,
      spaces: newParking.spaces,
    };

    setParkingPolicies((current) => [
      ...current,
      newPolicy,
    ]);

    /*
     * 新增完成後清除 Draft，
     * 但保持 Parking Mode，
     * 方便繼續新增下一個停車場。
     */
    setParkingDraft(null);
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
          onResetRoad={handleResetRoad}
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
          intersections={intersections}
          parkings={parkings}
          youbikes={YOUBIKES}
          parkingDraft={parkingDraft}
          onSelectRoad={handleSelectRoad}
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
          onBeginRoadEdit={(roadId) => {
            console.log(
              "開始編輯道路:",
              roadId,
            );
          }}
          onUpdateRoadPoint={
            handleUpdateRoadPoint
          }
        />

        <GoalPanel />
      </section>

      <PolicyList
        parkingPolicies={
          parkingPolicies
        }
      />
    </main>
  );
}