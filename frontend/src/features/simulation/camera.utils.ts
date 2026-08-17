import type { DistrictBoundary, RoadSegment } from "./simulation.types";
import { expandBounds, getBounds } from "./geometry.utils";

export function getDistrictCameraBounds(district: DistrictBoundary) {
  return expandBounds(getBounds(district.coordinates), 0.08);
}

export function getRoadFocusBounds(road: RoadSegment) {
  return expandBounds(getBounds(road.coordinates), 0.7);
}
