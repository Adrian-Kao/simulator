"use client";

import { useSyncExternalStore } from "react";
import type { MapMode, PolicyType, SimulationState } from "./simulation.types";

const initialState: SimulationState = {
  mapMode: "district-overview",
  selectedRoadId: null,
  hoveredRoadId: null,
  activePolicyType: "red-line",
  goals: [
    { id: "travel-time", metric: "平均旅行時間", direction: "decrease", targetPercent: 10 },
    { id: "travel-speed", metric: "平均車速", direction: "increase", targetPercent: 8 },
    { id: "congestion", metric: "壅塞程度", direction: "decrease", targetPercent: 15 },
    { id: "ubike-usage", metric: "YouBike 使用率", direction: "increase", targetPercent: 10 },
    { id: "parking-turnover", metric: "停車週轉率", direction: "increase", targetPercent: 5 }
  ],
  policies: [
    {
      id: "policy-red-line-shifu",
      type: "red-line",
      name: "市府路紅線調整",
      status: "editing",
      roadSegmentId: "shifu-001",
      params: { lengthMeters: 180, side: "both" }
    }
  ]
};

let state = initialState;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}

export const simulationStore = {
  getSnapshot: () => state,
  subscribe: (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
  setMapMode: (mapMode: MapMode) => {
    state = { ...state, mapMode };
    emit();
  },
  setHoveredRoad: (hoveredRoadId: string | null) => {
    state = { ...state, hoveredRoadId };
    emit();
  },
  setSelectedRoad: (selectedRoadId: string | null) => {
    state = {
      ...state,
      selectedRoadId,
      mapMode: selectedRoadId ? "road-focus" : "district-overview"
    };
    emit();
  },
  setActivePolicyType: (activePolicyType: PolicyType) => {
    state = { ...state, activePolicyType };
    emit();
  }
};

export function useSimulationStore() {
  return useSyncExternalStore(simulationStore.subscribe, simulationStore.getSnapshot, simulationStore.getSnapshot);
}
