import type { RoadSegment } from "./simulation.types";

export function findRoadById(roads: RoadSegment[], roadId: string | null) {
  return roads.find((road) => road.id === roadId) ?? null;
}

export function getRoadLabel(road: RoadSegment) {
  return `${road.name}（${road.start} - ${road.end}）`;
}

export function isRoadSelected(road: RoadSegment, selectedRoadId: string | null) {
  return road.id === selectedRoadId;
}
