import type {
  CurbSide,
  Point,
  RoadSegmentData,
} from "./simulation.types";

export function clampOffset(value: number) {
  return Math.max(0, Math.min(1, value));
}

export function polylineLength(points: Point[]) {
  let total = 0;

  for (let index = 1; index < points.length; index += 1) {
    const previous = points[index - 1];
    const current = points[index];

    total += Math.hypot(
      current.x - previous.x,
      current.y - previous.y,
    );
  }

  return total;
}

export function pointAtOffset(
  points: Point[],
  offset: number,
): Point {
  if (points.length === 0) {
    return { x: 0, y: 0 };
  }

  if (points.length === 1) {
    return points[0];
  }

  const total = polylineLength(points);

  if (total <= 0) {
    return points[0];
  }

  const target = clampOffset(offset) * total;
  let travelled = 0;

  for (let index = 1; index < points.length; index += 1) {
    const start = points[index - 1];
    const end = points[index];
    const segmentLength = Math.hypot(
      end.x - start.x,
      end.y - start.y,
    );

    if (segmentLength <= 0) {
      continue;
    }

    if (travelled + segmentLength >= target) {
      const local =
        (target - travelled) / segmentLength;

      return {
        x: start.x + (end.x - start.x) * local,
        y: start.y + (end.y - start.y) * local,
      };
    }

    travelled += segmentLength;
  }

  return points[points.length - 1];
}

export function nearestOffsetOnPolyline(
  points: Point[],
  target: Point,
) {
  if (points.length < 2) {
    return 0;
  }

  const total = polylineLength(points);

  if (total <= 0) {
    return 0;
  }

  let bestDistanceSquared = Number.POSITIVE_INFINITY;
  let bestDistanceAlong = 0;
  let travelled = 0;

  for (let index = 1; index < points.length; index += 1) {
    const start = points[index - 1];
    const end = points[index];

    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const segmentLengthSquared = dx * dx + dy * dy;
    const segmentLength = Math.sqrt(segmentLengthSquared);

    if (segmentLengthSquared <= 0) {
      continue;
    }

    const rawT =
      ((target.x - start.x) * dx +
        (target.y - start.y) * dy) /
      segmentLengthSquared;

    const t = Math.max(0, Math.min(1, rawT));

    const projected = {
      x: start.x + dx * t,
      y: start.y + dy * t,
    };

    const distanceSquared =
      (target.x - projected.x) ** 2 +
      (target.y - projected.y) ** 2;

    if (distanceSquared < bestDistanceSquared) {
      bestDistanceSquared = distanceSquared;
      bestDistanceAlong =
        travelled + segmentLength * t;
    }

    travelled += segmentLength;
  }

  return clampOffset(bestDistanceAlong / total);
}

export function slicePolyline(
  points: Point[],
  firstOffset: number,
  secondOffset: number,
): Point[] {
  if (points.length < 2) {
    return points;
  }

  const total = polylineLength(points);

  if (total <= 0) {
    return [points[0], points[points.length - 1]];
  }

  const startOffset = Math.min(
    clampOffset(firstOffset),
    clampOffset(secondOffset),
  );

  const endOffset = Math.max(
    clampOffset(firstOffset),
    clampOffset(secondOffset),
  );

  const result: Point[] = [
    pointAtOffset(points, startOffset),
  ];

  let travelled = 0;

  for (let index = 1; index < points.length - 1; index += 1) {
    const previous = points[index - 1];
    const current = points[index];

    travelled += Math.hypot(
      current.x - previous.x,
      current.y - previous.y,
    );

    const normalized = travelled / total;

    if (
      normalized > startOffset &&
      normalized < endOffset
    ) {
      result.push(current);
    }
  }

  result.push(pointAtOffset(points, endOffset));

  return result;
}

function fallbackCurb(
  road: RoadSegmentData,
  side: CurbSide,
) {
  const offset = side === "left" ? -10 : 10;

  return road.points.map((point) =>
    road.alignment === "vertical"
      ? {
          x: point.x + offset,
          y: point.y,
        }
      : {
          x: point.x,
          y: point.y + offset,
        },
  );
}

export function curbPointsForRoad(
  road: RoadSegmentData,
  side: CurbSide,
) {
  return (
    road.curb?.[side] ??
    fallbackCurb(road, side)
  );
}

export function roadLengthMeters(
  road: RoadSegmentData,
) {
  return Math.max(
    1,
    Math.round(
      road.lengthMeters ??
        polylineLength(road.points),
    ),
  );
}

export function redLineLengthMeters(
  road: RoadSegmentData,
  startOffset: number,
  endOffset: number,
) {
  return Math.max(
    1,
    Math.round(
      roadLengthMeters(road) *
        Math.abs(
          clampOffset(endOffset) -
            clampOffset(startOffset),
        ),
    ),
  );
}
