import {
  INTERSECTIONS as BASELINE_INTERSECTIONS,
  PARKINGS as BASELINE_PARKINGS,
} from "@/data/xinyi";

import type {
  IntersectionData,
  ParkingData,
  RedLinePolicyData,
  RoadSegmentData,
  ScenarioDiffEntry,
} from "./simulation.types";

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
