import {
  INTERSECTIONS as BASELINE_INTERSECTIONS,
  PARKINGS as BASELINE_PARKINGS,
} from "@/data/xinyi";

import {
  roadLengthMeters,
} from "./curb.utils";

import type {
  IntersectionData,
  ParkingData,
  RedLinePolicyData,
  RoadSegmentData,
  ScenarioDiffEntry,
} from "./simulation.types";

import type { ScenarioDiffPayload } from "@/lib/optimizer-api";
import type { SimulationPolicyPayload } from "@/lib/simulation-api";

/*
 * Scenario = 相對 Baseline 的修改。
 *
 * Baseline（道路、號誌、停車場、YouBike、既有紅線）本身不是 policy，
 * 所以這個模組只會回報「真的和 baseline 不同」的項目。
 */

/**
 * 目前 MVP 只把「第一個 green 相位」當成 X1 (signal_green_seconds)。
 * 找不到 green 相位時回傳 null，代表這個路口無法作為號誌變量。
 */
export function greenSeconds(
  intersection: IntersectionData,
): number | null {
  const green = intersection.phases.find(
    (phase) => phase.color === "green",
  );

  return green ? green.seconds : null;
}

function baselineIntersection(id: string) {
  return (
    BASELINE_INTERSECTIONS.find(
      (item) => item.id === id,
    ) ?? null
  );
}

function baselineParkingIds() {
  return new Set(
    BASELINE_PARKINGS.map((parking) => parking.id),
  );
}

export function changedSignalEntries(
  intersections: IntersectionData[],
): ScenarioDiffEntry[] {
  const entries: ScenarioDiffEntry[] = [];

  for (const intersection of intersections) {
    const baseline = baselineIntersection(intersection.id);

    if (!baseline) {
      continue;
    }

    const current = greenSeconds(intersection);
    const original = greenSeconds(baseline);

    if (
      current === null ||
      original === null ||
      current === original
    ) {
      continue;
    }

    entries.push({
      id: `signal-${intersection.id}`,
      type: "signal-timing",
      title: "號誌綠燈秒數",
      description: intersection.name,
      targetId: intersection.id,
      intersectionId: intersection.id,
      baselineLabel: `${original} 秒`,
      scenarioLabel: `${current} 秒`,
      baselineValue: original,
      scenarioValue: current,
      unit: "秒",
    });
  }

  return entries;
}

export function redLineEntries(
  redLinePolicies: RedLinePolicyData[],
  roads: RoadSegmentData[],
): ScenarioDiffEntry[] {
  return redLinePolicies.map((policy) => {
    const road =
      roads.find((item) => item.id === policy.roadId) ??
      null;

    return {
      id: policy.id,
      type: "red-line",
      title: "紅線長度",
      description: `${road?.roadName ?? policy.roadId} · ${
        policy.side === "left" ? "左側 curb" : "右側 curb"
      }`,
      targetId: policy.roadId,
      roadId: policy.roadId,
      baselineLabel: "0 m",
      scenarioLabel: `${policy.lengthMeters} m`,
      baselineValue: 0,
      scenarioValue: policy.lengthMeters,
      unit: "m",
    };
  });
}

export function parkingEntries(
  parkings: ParkingData[],
): ScenarioDiffEntry[] {
  const baselineIds = baselineParkingIds();

  return parkings
    .filter((parking) => !baselineIds.has(parking.id))
    .map((parking) => ({
      id: `parking-${parking.id}`,
      type: "parking",
      title: "新增停車位",
      description: parking.name,
      targetId: parking.id,
      parkingId: parking.id,
      baselineLabel: "0 格",
      scenarioLabel: `${parking.spaces} 格`,
      baselineValue: 0,
      scenarioValue: parking.spaces,
      unit: "格",
    }));
}

export function buildScenarioDiff(args: {
  intersections: IntersectionData[];
  redLinePolicies: RedLinePolicyData[];
  parkings: ParkingData[];
  roads: RoadSegmentData[];
}): ScenarioDiffEntry[] {
  return [
    ...changedSignalEntries(args.intersections),
    ...redLineEntries(args.redLinePolicies, args.roads),
    ...parkingEntries(args.parkings),
  ];
}

/**
 * ScenarioDiff -> backend payload.
 *
 * 只送出真正改變過的項目，未修改的 baseline 不會出現在 payload 裡。
 */
export function toSimulationPolicies(
  entries: ScenarioDiffEntry[],
): SimulationPolicyPayload[] {
  return entries.map((entry) => {
    if (entry.type === "signal-timing") {
      return {
        type: "signal-timing",
        intersection_id:
          entry.intersectionId ?? entry.targetId,
        baseline_seconds: entry.baselineValue,
        scenario_seconds: entry.scenarioValue,
      };
    }

    if (entry.type === "red-line") {
      return {
        type: "red-line",
        road_id: entry.roadId ?? entry.targetId,
        length_meters: entry.scenarioValue,
      };
    }

    return {
      type: "parking",
      parking_id: entry.parkingId ?? entry.targetId,
      spaces: entry.scenarioValue,
    };
  });
}

/**
 * 目前 diff 對應到的三個變量值，用於在 UI 顯示 AI 建議的前後差異。
 */
export function scenarioVariables(
  entries: ScenarioDiffEntry[],
) {
  const signal = entries.find(
    (entry) => entry.type === "signal-timing",
  );

  const redLineMeters = entries
    .filter((entry) => entry.type === "red-line")
    .reduce((sum, entry) => sum + entry.scenarioValue, 0);

  const parkingSpaces = entries
    .filter((entry) => entry.type === "parking")
    .reduce((sum, entry) => sum + entry.scenarioValue, 0);

  return {
    signalGreenSeconds: signal?.scenarioValue ?? null,
    redLineMeters,
    parkingSpaces,
  };
}

/*
 * AI optimizer 最終結果要同步回實際地圖 state，而不只更新右側 KPI。
 * 這裡把 backend 的 final ScenarioDiff 轉回目前 UI 的三個狀態來源：
 * intersections / redLinePolicies / parkings。
 */

type OptimizedScenarioUiState = {
  intersections: IntersectionData[];
  redLinePolicies: RedLinePolicyData[];
  parkings: ParkingData[];
};

function applyOptimizedSignal(
  intersections: IntersectionData[],
  finalScenario: ScenarioDiffPayload,
): IntersectionData[] {
  const signalPolicies = finalScenario.policies.filter(
    (policy) => policy.type === "signal-timing",
  );

  if (signalPolicies.length === 0) {
    return intersections;
  }

  const secondsByIntersection = new Map(
    signalPolicies.map((policy) => [
      policy.intersection_id,
      policy.scenario_seconds,
    ]),
  );

  return intersections.map((intersection) => {
    const seconds = secondsByIntersection.get(intersection.id);

    if (seconds === undefined) {
      return intersection;
    }

    const greenIndex = intersection.phases.findIndex(
      (phase) => phase.color === "green",
    );

    if (greenIndex < 0) {
      return intersection;
    }

    return {
      ...intersection,
      phases: intersection.phases.map((phase, index) =>
        index === greenIndex
          ? {
              ...phase,
              seconds,
            }
          : phase,
      ),
    };
  });
}

function redLineOffsetsForLength(
  road: RoadSegmentData,
  preferredStartOffset: number,
  targetMeters: number,
) {
  const fraction = Math.max(
    0,
    Math.min(1, targetMeters / roadLengthMeters(road)),
  );

  let startOffset = Math.max(
    0,
    Math.min(1, preferredStartOffset),
  );
  let endOffset = startOffset + fraction;

  if (endOffset > 1) {
    endOffset = 1;
    startOffset = Math.max(0, 1 - fraction);
  }

  return {
    startOffset,
    endOffset,
  };
}

function applyOptimizedRedLine(
  current: RedLinePolicyData[],
  roads: RoadSegmentData[],
  finalScenario: ScenarioDiffPayload,
): RedLinePolicyData[] {
  const policy = finalScenario.policies.find(
    (item) => item.type === "red-line",
  );

  if (!policy || policy.length_meters <= 0) {
    return [];
  }

  const road = roads.find(
    (item) => item.id === policy.road_id,
  );

  if (!road) {
    return current;
  }

  const existing =
    current.find((item) => item.roadId === policy.road_id) ??
    current[0] ??
    null;

  const preferredStartOffset = existing?.startOffset ?? 0.25;
  const { startOffset, endOffset } = redLineOffsetsForLength(
    road,
    preferredStartOffset,
    policy.length_meters,
  );

  const next: RedLinePolicyData = {
    id: existing?.id ?? `ai-red-line-${policy.road_id}`,
    roadId: policy.road_id,
    side: existing?.side ?? "left",
    startOffset,
    endOffset,
    // PolicyList / next API call must reflect the exact backend policy value.
    // Offsets are only the best-effort map visualization of that length.
    lengthMeters: policy.length_meters,
    startTime: existing?.startTime ?? "00:00",
    endTime: existing?.endTime ?? "23:59",
  };

  return [next];
}

function applyOptimizedParking(
  current: ParkingData[],
  finalScenario: ScenarioDiffPayload,
): ParkingData[] {
  const baselineIds = baselineParkingIds();
  const baselineParkings = current.filter((parking) =>
    baselineIds.has(parking.id),
  );
  const scenarioParkings = current.filter(
    (parking) => !baselineIds.has(parking.id),
  );

  const policy = finalScenario.policies.find(
    (item) => item.type === "parking",
  );

  if (!policy || policy.spaces <= 0) {
    return baselineParkings;
  }

  const existing =
    scenarioParkings.find(
      (parking) => parking.id === policy.parking_id,
    ) ??
    scenarioParkings[0] ??
    null;

  // AI 只能調整「車位數」，不能憑空決定新停車場座標。
  // 若沒有使用者先建立的停車場 anchor，就維持原 state。
  if (!existing) {
    return current;
  }

  return [
    ...baselineParkings,
    {
      ...existing,
      id: policy.parking_id || existing.id,
      spaces: policy.spaces,
      status: "new",
    },
  ];
}

export function applyOptimizedScenarioToUi(args: {
  finalScenario: ScenarioDiffPayload;
  intersections: IntersectionData[];
  redLinePolicies: RedLinePolicyData[];
  parkings: ParkingData[];
  roads: RoadSegmentData[];
}): OptimizedScenarioUiState {
  return {
    intersections: applyOptimizedSignal(
      args.intersections,
      args.finalScenario,
    ),
    redLinePolicies: applyOptimizedRedLine(
      args.redLinePolicies,
      args.roads,
      args.finalScenario,
    ),
    parkings: applyOptimizedParking(
      args.parkings,
      args.finalScenario,
    ),
  };
}
