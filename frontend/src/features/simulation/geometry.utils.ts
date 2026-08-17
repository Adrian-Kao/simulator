import type { Coordinate, Point } from "./simulation.types";

/*
 * 商圈地圖是示意圖，不是測量圖：世界座標是 1280 x 720 的抽象單位。
 *
 * 所有「公尺」都必須由這個常數換算，避免同一條路在地圖、tooltip 與
 * sidebar 出現三個互相矛盾的長度。
 */
export const METERS_PER_UNIT = 0.4;

export function polylineLength(points: Point[]) {
  return points.reduce((sum, point, index) => {
    if (index === 0) return sum;
    const previous = points[index - 1];
    return sum + Math.hypot(point.x - previous.x, point.y - previous.y);
  }, 0);
}

export function polylineLengthMeters(points: Point[]) {
  return Math.max(1, Math.round(polylineLength(points) * METERS_PER_UNIT));
}

export type Bounds = {
  minLng: number;
  minLat: number;
  maxLng: number;
  maxLat: number;
};

export function getBounds(coordinates: Coordinate[]): Bounds {
  return coordinates.reduce(
    (bounds, [lng, lat]) => ({
      minLng: Math.min(bounds.minLng, lng),
      minLat: Math.min(bounds.minLat, lat),
      maxLng: Math.max(bounds.maxLng, lng),
      maxLat: Math.max(bounds.maxLat, lat)
    }),
    { minLng: Infinity, minLat: Infinity, maxLng: -Infinity, maxLat: -Infinity }
  );
}

export function expandBounds(bounds: Bounds, ratio = 0.2): Bounds {
  const lngPadding = (bounds.maxLng - bounds.minLng) * ratio;
  const latPadding = (bounds.maxLat - bounds.minLat) * ratio;
  return {
    minLng: bounds.minLng - lngPadding,
    minLat: bounds.minLat - latPadding,
    maxLng: bounds.maxLng + lngPadding,
    maxLat: bounds.maxLat + latPadding
  };
}
