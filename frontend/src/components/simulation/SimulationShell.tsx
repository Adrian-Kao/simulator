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
  applyOptimizedScenarioToUi,
  buildScenarioDiff,
  toSimulationPolicies,
} from "@/features/simulation/scenario.utils";

import {
  runSimulation,
  type SimulationApiResult,
  type SimulationRequestPayload,
  type SimulationStatus,
} from "@/lib/simulation-api";

import {
  DEFAULT_MAX_ITERATIONS,
  runOptimization,
  type OptimizeApiResult,
  type OptimizerRunStatus,
} from "@/lib/optimizer-api";

import type {
  CurbSide,
  GoalConfig,
  GoalMetric,
  ParkingData,
  ParkingDraft,
  PolicyTool,
  RedLinePolicyData,
  RoadSegmentData,
  TurnRestrictionType,
} from "@/features/simulation/simulation.types";

import GoalConfigPanel from "./GoalConfigPanel";
import GoalPanel from "./GoalPanel";
import LeftSidebar from "./LeftSidebar";
import PolicyList from "./PolicyList";
import PolicyToolbar from "./PolicyToolbar";
import SimulationHeader from "./SimulationHeader";
import SimulationMap from "./SimulationMap";

import styles from "@/styles/simulation.module.css";

const SCENARIO_ID = "scenario-a";
const SCENARIO_NAME = "Scenario A";

const DEFAULT_DAY_TYPE =
  "weekday" as const;

const DEFAULT_TIME_SLOT =
  "17:30";

const DEFAULT_RANDOM_SEED =
  42;

const DEFAULT_ROAD_ID =
  "shifu-road";

const DEFAULT_ROAD_NAME =
  "市府路";

/*
 * 使用者可以從地圖右側 GoalConfigPanel 修改。
 *
 * Backend / Simulation / Optimizer
 * 都會使用同一份 goals。
 */
const DEFAULT_GOALS: GoalConfig = {
  travel_time_percent: -8,
  travel_speed_percent: 8,
  congestion_vc_percent: -15,
  queue_percent: -15,
};

export default function SimulationShell() {
  /* =======================================================
     MAP / ROAD STATE
  ======================================================= */

  const [
    roads,
    setRoads,
  ] = useState<RoadSegmentData[]>(
    () => structuredClone(ROADS),
  );

  const [
    selectedRoadId,
    setSelectedRoadId,
  ] = useState<string | null>(
    null,
  );

  const [
    selectedIntersectionId,
    setSelectedIntersectionId,
  ] = useState<string | null>(
    null,
  );

  const [
    intersections,
    setIntersections,
  ] = useState(
    () =>
      structuredClone(
        INTERSECTIONS,
      ),
  );

  const [
    activeTool,
    setActiveTool,
  ] = useState<PolicyTool>(
    "select",
  );

  /* =======================================================
     PARKING
  ======================================================= */

  const [
    parkings,
    setParkings,
  ] = useState<ParkingData[]>(
    () =>
      structuredClone(
        PARKINGS,
      ),
  );

  const [
    parkingDraft,
    setParkingDraft,
  ] = useState<ParkingDraft | null>(
    null,
  );

  /* =======================================================
     RED LINE
  ======================================================= */

  const [
    redLineDraft,
    setRedLineDraft,
  ] =
    useState<RedLinePolicyData | null>(
      null,
    );

  const [
    redLinePolicies,
    setRedLinePolicies,
  ] = useState<
    RedLinePolicyData[]
  >([]);

  /* =======================================================
     PYTHON SIMULATION
  ======================================================= */

  const [
    simulationStatus,
    setSimulationStatus,
  ] =
    useState<SimulationStatus>(
      "idle",
    );

  const [
    simulationResult,
    setSimulationResult,
  ] =
    useState<SimulationApiResult | null>(
      null,
    );

  const [
    simulationError,
    setSimulationError,
  ] = useState<string | null>(
    null,
  );

  /* =======================================================
     GOALS
  ======================================================= */

  const [
    goals,
    setGoals,
  ] =
    useState<GoalConfig>(
      DEFAULT_GOALS,
    );

  /* =======================================================
     AI OPTIMIZER
  ======================================================= */

  const [
    optimizerStatus,
    setOptimizerStatus,
  ] =
    useState<OptimizerRunStatus>(
      "idle",
    );

  const [
    optimizerResult,
    setOptimizerResult,
  ] =
    useState<OptimizeApiResult | null>(
      null,
    );

  const [
    optimizerError,
    setOptimizerError,
  ] = useState<string | null>(
    null,
  );

  /* =======================================================
     SELECTED ROAD
  ======================================================= */

  const selectedRoad =
    useMemo(() => {
      return (
        roads.find(
          (road) =>
            road.id ===
            selectedRoadId,
        ) ?? null
      );
    }, [
      roads,
      selectedRoadId,
    ]);

  /* =======================================================
     SELECTED INTERSECTION
  ======================================================= */

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

  /* =======================================================
     CREATE RED LINE DRAFT
  ======================================================= */

  const createRedLineDraft = (
    roadId: string,
    side: CurbSide = "left",
  ): RedLinePolicyData | null => {
    const road =
      roads.find(
        (item) =>
          item.id === roadId,
      );

    if (!road) {
      return null;
    }

    const startOffset =
      0.25;

    const endOffset =
      0.75;

    return {
      id:
        `draft-red-line-${roadId}`,

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

      startTime:
        "00:00",

      endTime:
        "23:59",
    };
  };

  /* =======================================================
     RED LINE - CREATE
  ======================================================= */

  const handleCreateRedLine =
    () => {
      if (
        !selectedRoadId
      ) {
        return;
      }

      setActiveTool(
        "red-line",
      );

      setRedLineDraft(
        createRedLineDraft(
          selectedRoadId,
          "left",
        ),
      );
    };

  /* =======================================================
     RED LINE - UPDATE DRAFT
  ======================================================= */

  const handleUpdateRedLineDraft =
    (
      patch:
        Partial<RedLinePolicyData>,
    ) => {
      setRedLineDraft(
        (current) => {
          if (!current) {
            return null;
          }

          const next = {
            ...current,
            ...patch,
          };

          const road =
            roads.find(
              (item) =>
                item.id ===
                next.roadId,
            );

          if (!road) {
            return next;
          }

          const startOffset =
            Math.max(
              0,
              Math.min(
                1,
                Math.min(
                  next.startOffset,
                  next.endOffset,
                ),
              ),
            );

          const endOffset =
            Math.max(
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
        },
      );
    };

  /* =======================================================
     RED LINE - CANCEL
  ======================================================= */

  const handleCancelRedLine =
    () => {
      setRedLineDraft(
        null,
      );
    };

  /* =======================================================
     RED LINE - APPLY
  ======================================================= */

  const handleApplyRedLine =
    () => {
      if (
        !redLineDraft
      ) {
        return;
      }

      const road =
        roads.find(
          (item) =>
            item.id ===
            redLineDraft.roadId,
        );

      if (!road) {
        return;
      }

      const startOffset =
        Math.min(
          redLineDraft.startOffset,
          redLineDraft.endOffset,
        );

      const endOffset =
        Math.max(
          redLineDraft.startOffset,
          redLineDraft.endOffset,
        );

      if (
        endOffset -
          startOffset <
        0.005
      ) {
        return;
      }

      const applied:
        RedLinePolicyData = {
          ...redLineDraft,

          id:
            `red-line-${Date.now()}`,

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

      setRedLineDraft(
        null,
      );
    };

  /* =======================================================
     SELECT ROAD
  ======================================================= */

  const handleSelectRoad =
    (
      roadId: string,
    ) => {
      /*
       * Parking / YouBike placement
       * 不應該因為誤點道路進入 Road Focus。
       */
      if (
        activeTool ===
          "parking" ||
        activeTool ===
          "youbike"
      ) {
        return;
      }

      const road =
        roads.find(
          (item) =>
            item.id === roadId,
        );

      if (!road) {
        return;
      }

      setSelectedIntersectionId(
        null,
      );

      setSelectedRoadId(
        roadId,
      );

      setActiveTool(
        "red-line",
      );

      setRedLineDraft(
        createRedLineDraft(
          roadId,
          "left",
        ),
      );
    };

  /* =======================================================
     SELECT INTERSECTION
  ======================================================= */

  const handleSelectIntersection =
    (
      intersectionId:
        string,
    ) => {
      setSelectedRoadId(
        null,
      );

      setRedLineDraft(
        null,
      );

      setSelectedIntersectionId(
        intersectionId,
      );

      setActiveTool(
        "traffic-control",
      );
    };

  /* =======================================================
     CHANGE TOOL
  ======================================================= */

  const handleChangeTool =
    (
      tool:
        PolicyTool,
    ) => {
      setActiveTool(
        tool,
      );

      /*
       * Placement tools：
       * 地圖回到 Overview。
       */
      if (
        tool ===
          "parking" ||
        tool ===
          "youbike"
      ) {
        setSelectedRoadId(
          null,
        );

        setSelectedIntersectionId(
          null,
        );

        setRedLineDraft(
          null,
        );
      }

      /*
       * Intersection tools
       */
      if (
        tool ===
          "traffic-control" ||
        tool ===
          "intersection" ||
        tool ===
          "signal"
      ) {
        setSelectedRoadId(
          null,
        );

        setRedLineDraft(
          null,
        );
      }

      /*
       * 離開停車工具，
       * 尚未 Confirm 的 Draft 取消。
       */
      if (
        tool !==
        "parking"
      ) {
        setParkingDraft(
          null,
        );
      }

      /*
       * 離開 Red Line，
       * 清掉尚未 Apply 的 Draft。
       */
      if (
        tool !==
          "red-line" &&
        tool !==
          "select"
      ) {
        setRedLineDraft(
          null,
        );
      }

      /*
       * 已經選了道路，
       * 再切回 Red Line 時重新建立 Draft。
       */
      if (
        tool ===
          "red-line" &&
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

  /* =======================================================
     RESET ROAD
  ======================================================= */

  const handleResetRoad =
    (
      roadId:
        string,
    ) => {
      const original =
        ROADS.find(
          (road) =>
            road.id === roadId,
        );

      if (!original) {
        return;
      }

      setRoads(
        (current) =>
          current.map(
            (road) =>
              road.id ===
              roadId
                ? structuredClone(
                    original,
                  )
                : road,
          ),
      );

      if (
        selectedRoadId ===
          roadId &&
        activeTool ===
          "red-line"
      ) {
        setRedLineDraft(
          createRedLineDraft(
            roadId,
            "left",
          ),
        );
      }
    };

  /* =======================================================
     BACK TO DISTRICT
  ======================================================= */

  const handleBackToDistrict =
    () => {
      setSelectedRoadId(
        null,
      );

      setSelectedIntersectionId(
        null,
      );

      setParkingDraft(
        null,
      );

      setRedLineDraft(
        null,
      );

      setActiveTool(
        "select",
      );
    };

  /* =======================================================
     INTERSECTION PHASE
  ======================================================= */

  const handleUpdateIntersectionPhase =
    (
      intersectionId:
        string,

      phaseIndex:
        number,

      seconds:
        number,
    ) => {
      setIntersections(
        (current) =>
          current.map(
            (
              intersection,
            ) => {
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
                    (
                      phase,
                      index,
                    ) =>
                      index ===
                      phaseIndex
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

  /* =======================================================
     ADD TURN RESTRICTION
  ======================================================= */

  const handleAddIntersectionRestriction =
    (
      intersectionId:
        string,

      type:
        TurnRestrictionType,

      targetRoadId:
        string,
    ) => {
      if (
        !targetRoadId
      ) {
        return;
      }

      setIntersections(
        (current) =>
          current.map(
            (
              intersection,
            ) => {
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

  /* =======================================================
     REMOVE TURN RESTRICTION
  ======================================================= */

  const handleRemoveIntersectionRestriction =
    (
      intersectionId:
        string,

      restrictionId:
        string,
    ) => {
      setIntersections(
        (current) =>
          current.map(
            (
              intersection,
            ) => {
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
                    (
                      restriction,
                    ) =>
                      restriction.id !==
                      restrictionId,
                  ),
              };
            },
          ),
      );
    };

  /* =======================================================
     PARKING - PICK LOCATION
  ======================================================= */

  const handlePickParkingLocation =
    (
      x: number,
      y: number,
    ) => {
      if (
        activeTool !==
        "parking"
      ) {
        return;
      }

      setParkingDraft({
        x,
        y,

        name:
          "新增停車場",

        spaces:
          30,
      });
    };

  /* =======================================================
     PARKING - UPDATE DRAFT
  ======================================================= */

  const handleUpdateParkingDraft =
    (
      patch:
        Partial<ParkingDraft>,
    ) => {
      setParkingDraft(
        (current) => {
          if (!current) {
            return null;
          }

          return {
            ...current,
            ...patch,
          };
        },
      );
    };

  /* =======================================================
     PARKING - CANCEL
  ======================================================= */

  const handleCancelParking =
    () => {
      setParkingDraft(
        null,
      );
    };

  /* =======================================================
     PARKING - CONFIRM
  ======================================================= */

  const handleConfirmParking =
    () => {
      if (
        !parkingDraft
      ) {
        return;
      }

      const parkingId =
        `parking-new-${Date.now()}`;

      const newParking:
        ParkingData = {
          id:
            parkingId,

          name:
            parkingDraft.name.trim() ||
            "新增停車場",

          x:
            parkingDraft.x,

          y:
            parkingDraft.y,

          spaces:
            Math.max(
              1,
              parkingDraft.spaces,
            ),

          status:
            "new",
        };

      setParkings(
        (current) => [
          ...current,
          newParking,
        ],
      );

      setParkingDraft(
        null,
      );
    };

  /* =======================================================
     SCENARIO DIFF

     Baseline 本身不是 Policy。
     只有和 Baseline 不同的狀態，
     才會進入 Scenario Policy List。
  ======================================================= */

  const scenarioEntries =
    useMemo(
      () =>
        buildScenarioDiff({
          intersections,

          redLinePolicies,

          parkings,

          roads,
        }),

      [
        intersections,
        redLinePolicies,
        parkings,
        roads,
      ],
    );

  /* =======================================================
     ANCHOR ROAD
  ======================================================= */

  const anchorRoad =
    useMemo(() => {
      const redLineEntry =
        scenarioEntries.find(
          (entry) =>
            entry.type ===
            "red-line",
        );

      const roadId =
        redLineEntry?.roadId ??
        selectedRoadId ??
        DEFAULT_ROAD_ID;

      const road =
        roads.find(
          (item) =>
            item.id ===
            roadId,
        ) ?? null;

      return {
        roadId,

        roadName:
          road?.roadName ??
          DEFAULT_ROAD_NAME,
      };
    }, [
      scenarioEntries,
      selectedRoadId,
      roads,
    ]);

  /* =======================================================
     BUILD SIMULATION REQUEST
  ======================================================= */

  const buildSimulationRequest =
    (): SimulationRequestPayload => ({
      scenario_id:
        SCENARIO_ID,

      day_type:
        DEFAULT_DAY_TYPE,

      time_slot:
        DEFAULT_TIME_SLOT,

      random_seed:
        DEFAULT_RANDOM_SEED,

      road_id:
        anchorRoad.roadId,

      road_name:
        anchorRoad.roadName,

      policies:
        toSimulationPolicies(
          scenarioEntries,
        ),

      /*
       * GoalConfigPanel 修改的目標
       * 會直接傳給 Python backend。
       */
      goals,
    });

  /* =======================================================
     CHANGE GOAL
  ======================================================= */

  const handleChangeGoal =
    (
      metric:
        GoalMetric,

      value:
        number | null,
    ) => {
      setGoals(
        (current) => {
          const next = {
            ...current,
          };

          if (
            value === null ||
            Number.isNaN(
              value,
            )
          ) {
            delete next[
              metric
            ];
          } else {
            next[
              metric
            ] = value;
          }

          return next;
        },
      );
    };

  /* =======================================================
     RUN PYTHON SIMULATION
  ======================================================= */

  const handleRunSimulation =
    async () => {
      setSimulationStatus(
        "running",
      );

      setSimulationError(
        null,
      );

      try {
        const result =
          await runSimulation(
            buildSimulationRequest(),
          );

        setSimulationResult(
          result,
        );

        setSimulationStatus(
          "success",
        );
      } catch (error) {
        setSimulationResult(
          null,
        );

        setSimulationStatus(
          "error",
        );

        setSimulationError(
          error instanceof
            Error
            ? error.message
            : "Unknown simulation error",
        );
      }
    };

  /* =======================================================
     RUN AI OPTIMIZATION
  ======================================================= */

  const handleRunOptimization =
    async () => {
      setOptimizerStatus(
        "running",
      );

      setOptimizerError(
        null,
      );

      try {
        const result =
          await runOptimization({
            /*
             * Scenario + Policy + Goals
             */
            initial_scenario:
              buildSimulationRequest(),

            goals,

            max_iterations:
              DEFAULT_MAX_ITERATIONS,
          });

        setOptimizerResult(
          result,
        );

        setOptimizerStatus(
          "success",
        );

        /*
         * Gemini / Optimizer 最後產生的 Scenario
         * 不只顯示在結果 Dashboard。
         *
         * 同時把結果重新套用回：
         * - 地圖
         * - Intersection
         * - Red Line
         * - Parking
         * - Policy List
         */
        const optimizedUi =
          applyOptimizedScenarioToUi({
            finalScenario:
              result.final_scenario,

            intersections,

            redLinePolicies,

            parkings,

            roads,
          });

        setIntersections(
          optimizedUi.intersections,
        );

        setRedLinePolicies(
          optimizedUi.redLinePolicies,
        );

        setParkings(
          optimizedUi.parkings,
        );

        setRedLineDraft(
          null,
        );

        setParkingDraft(
          null,
        );

        /*
         * 最後一輪 Optimization
         * 的 Simulation KPI
         * 同步到 Python Simulation Dashboard。
         */
        const lastIteration =
          result.iterations[
            result.iterations.length -
              1
          ];

        if (
          lastIteration
        ) {
          setSimulationResult(
            lastIteration.result,
          );

          setSimulationStatus(
            "success",
          );
        }
      } catch (error) {
        setOptimizerResult(
          null,
        );

        setOptimizerStatus(
          "error",
        );

        setOptimizerError(
          error instanceof
            Error
            ? error.message
            : "Unknown optimization error",
        );
      }
    };

  /* =======================================================
     UI
  ======================================================= */

  return (
    <main
      className={
        styles.page
      }
    >
      <SimulationHeader />

      <PolicyToolbar
        activeTool={
          activeTool
        }
        onChangeTool={
          handleChangeTool
        }
      />

      {/* ===================================================
          第一區

          左：商圈編輯
          中：地圖
          右：情境目標設定
      =================================================== */}

      <section
        className={`${styles.workspace} ${
          selectedRoad
            ? styles.workspaceRoadFocus
            : ""
        }`}
      >
        {/* ===============================================
            LEFT
        =============================================== */}

        <LeftSidebar
          selectedRoad={
            selectedRoad
          }
          selectedIntersection={
            selectedIntersection
          }
          activeTool={
            activeTool
          }
          roads={
            roads
          }
          parkingDraft={
            parkingDraft
          }
          redLineDraft={
            redLineDraft
          }
          selectedPolicy={
            null
          }
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

        {/* ===============================================
            CENTER MAP
        =============================================== */}

        <SimulationMap
          selectedRoadId={
            selectedRoadId
          }
          selectedIntersectionId={
            selectedIntersectionId
          }
          activeTool={
            activeTool
          }
          roads={
            roads
          }
          intersections={
            intersections
          }
          parkings={
            parkings
          }
          youbikes={
            YOUBIKES
          }
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

        {/* ===============================================
            RIGHT GOAL CONFIG
        =============================================== */}

        <GoalConfigPanel
          goals={
            goals
          }
          onChangeGoal={
            handleChangeGoal
          }
        />
      </section>

      {/* ===================================================
          第二區：POLICY LIST
      =================================================== */}

      <PolicyList
        scenarioName={
          SCENARIO_NAME
        }
        entries={
          scenarioEntries
        }
      />

      {/* ===================================================
          第三區

          Python Simulation
          +
          Policy Optimization
      =================================================== */}

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
        optimizerStatus={
          optimizerStatus
        }
        optimizerResult={
          optimizerResult
        }
        optimizerError={
          optimizerError
        }
        onRunOptimization={
          handleRunOptimization
        }
      />
    </main>
  );
}