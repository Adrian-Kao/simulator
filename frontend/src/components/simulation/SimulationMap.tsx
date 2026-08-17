"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";

import {
  BUILDINGS,
  DISTRICT_BOUNDARY,
  DISTRICT_CAMERA,
  PARKS,
} from "@/data/xinyi";

import {
  curbPointsForRoad,
  nearestOffsetOnPolyline,
  pointAtOffset,
  roadLengthMeters,
  slicePolyline,
} from "@/features/simulation/curb.utils";

import type {
  CameraBounds,
  CurbSide,
  IntersectionData,
  ParkingData,
  ParkingDraft,
  PolicyTool,
  Point,
  RedLinePolicyData,
  RoadSegmentData,
  YouBikeData,
} from "@/features/simulation/simulation.types";

import styles from "@/styles/simulation.module.css";

type Props = {
  selectedRoadId: string | null;
  selectedIntersectionId: string | null;
  activeTool: PolicyTool;
  roads: RoadSegmentData[];
  intersections: IntersectionData[];
  parkings: ParkingData[];
  youbikes: YouBikeData[];
  parkingDraft: ParkingDraft | null;
  redLineDraft: RedLinePolicyData | null;
  redLinePolicies: RedLinePolicyData[];
  onSelectRoad: (roadId: string) => void;
  onSelectIntersection: (
    intersectionId: string,
  ) => void;
  onBackToDistrict: () => void;
  onPickParkingLocation: (
    x: number,
    y: number,
  ) => void;
  onPickYouBikeLocation: (
    x: number,
    y: number,
  ) => void;
  onUpdateRedLineDraft: (
    patch: Partial<RedLinePolicyData>,
  ) => void;
};

type RedLineHandle =
  | "start"
  | "end";

const CITY_BLOCKS = [
  { x: 145, y: 95, w: 130, h: 42 },
  { x: 295, y: 95, w: 135, h: 42 },
  { x: 555, y: 95, w: 115, h: 42 },
  { x: 755, y: 95, w: 120, h: 42 },
  { x: 970, y: 95, w: 130, h: 42 },
  { x: 145, y: 155, w: 95, h: 90 },
  { x: 255, y: 155, w: 105, h: 90 },
  { x: 375, y: 155, w: 105, h: 90 },
  { x: 555, y: 155, w: 120, h: 90 },
  { x: 755, y: 155, w: 120, h: 90 },
  { x: 970, y: 155, w: 125, h: 90 },
  { x: 145, y: 300, w: 125, h: 95 },
  { x: 285, y: 300, w: 120, h: 95 },
  { x: 420, y: 300, w: 60, h: 95 },
  { x: 555, y: 300, w: 125, h: 95 },
  { x: 755, y: 300, w: 120, h: 95 },
  { x: 970, y: 300, w: 125, h: 95 },
  { x: 145, y: 410, w: 125, h: 110 },
  { x: 285, y: 410, w: 120, h: 110 },
  { x: 420, y: 410, w: 60, h: 110 },
  { x: 555, y: 410, w: 125, h: 110 },
  { x: 755, y: 410, w: 120, h: 110 },
  { x: 970, y: 410, w: 125, h: 110 },
  { x: 145, y: 585, w: 130, h: 55 },
  { x: 295, y: 585, w: 135, h: 55 },
  { x: 555, y: 585, w: 115, h: 55 },
  { x: 755, y: 585, w: 120, h: 55 },
  { x: 970, y: 585, w: 130, h: 55 },
];

function pointsToPath(
  points: Point[],
) {
  return points
    .map(
      (point, index) =>
        `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`,
    )
    .join(" ");
}

function easeInOutCubic(t: number) {
  return t < 0.5
    ? 4 * t * t * t
    : 1 -
        Math.pow(
          -2 * t + 2,
          3,
        ) /
          2;
}

function interpolateCamera(
  from: CameraBounds,
  to: CameraBounds,
  progress: number,
): CameraBounds {
  return {
    x:
      from.x +
      (to.x - from.x) *
        progress,
    y:
      from.y +
      (to.y - from.y) *
        progress,
    width:
      from.width +
      (to.width - from.width) *
        progress,
    height:
      from.height +
      (to.height - from.height) *
        progress,
  };
}

function focusBoundsForIntersection(
  intersection: IntersectionData,
): CameraBounds {
  return {
    x: intersection.x - 130,
    y: intersection.y - 110,
    width: 260,
    height: 220,
  };
}

function clientPointToSvgPoint(
  svg: SVGSVGElement,
  clientX: number,
  clientY: number,
): Point {
  const point =
    svg.createSVGPoint();

  point.x = clientX;
  point.y = clientY;

  const matrix =
    svg.getScreenCTM();

  if (!matrix) {
    return {
      x: clientX,
      y: clientY,
    };
  }

  const svgPoint =
    point.matrixTransform(
      matrix.inverse(),
    );

  return {
    x: svgPoint.x,
    y: svgPoint.y,
  };
}

export default function SimulationMap({
  selectedRoadId,
  selectedIntersectionId,
  activeTool,
  roads,
  intersections,
  parkings,
  youbikes,
  parkingDraft,
  redLineDraft,
  redLinePolicies,
  onSelectRoad,
  onSelectIntersection,
  onBackToDistrict,
  onPickParkingLocation,
  onPickYouBikeLocation,
  onUpdateRedLineDraft,
}: Props) {
  const selectedRoad = useMemo(
    () =>
      roads.find(
        (road) =>
          road.id ===
          selectedRoadId,
      ) ?? null,
    [roads, selectedRoadId],
  );

  const selectedIntersection =
    useMemo(
      () =>
        intersections.find(
          (item) =>
            item.id ===
            selectedIntersectionId,
        ) ?? null,
      [
        intersections,
        selectedIntersectionId,
      ],
    );

  const [camera, setCamera] =
    useState<CameraBounds>(
      DISTRICT_CAMERA,
    );

  const cameraRef =
    useRef<CameraBounds>(
      DISTRICT_CAMERA,
    );

  const svgRef =
    useRef<SVGSVGElement | null>(
      null,
    );

  const animationFrameRef =
    useRef<number | null>(null);

  const [
    hoveredRoadId,
    setHoveredRoadId,
  ] = useState<string | null>(
    null,
  );

  const [
    hoveredIntersectionId,
    setHoveredIntersectionId,
  ] = useState<string | null>(
    null,
  );

  const [
    tooltipPosition,
    setTooltipPosition,
  ] = useState({
    x: 0,
    y: 0,
  });

  const [
    draggingRedLineHandle,
    setDraggingRedLineHandle,
  ] =
    useState<RedLineHandle | null>(
      null,
    );

  const cameraTarget =
    useMemo(() => {
      if (selectedIntersection) {
        return focusBoundsForIntersection(
          selectedIntersection,
        );
      }

      return (
        selectedRoad?.focusBounds ??
        DISTRICT_CAMERA
      );
    }, [
      selectedIntersection,
      selectedRoad,
    ]);

  useEffect(() => {
    cameraRef.current = camera;
  }, [camera]);

  useEffect(() => {
    const from = {
      ...cameraRef.current,
    };

    const target = cameraTarget;
    const startTime =
      performance.now();
    const duration = 720;

    if (
      animationFrameRef.current !==
      null
    ) {
      cancelAnimationFrame(
        animationFrameRef.current,
      );
    }

    const animate = (
      time: number,
    ) => {
      const progress = Math.min(
        (time - startTime) /
          duration,
        1,
      );

      const eased =
        easeInOutCubic(progress);

      setCamera(
        interpolateCamera(
          from,
          target,
          eased,
        ),
      );

      if (progress < 1) {
        animationFrameRef.current =
          requestAnimationFrame(
            animate,
          );
      }
    };

    animationFrameRef.current =
      requestAnimationFrame(
        animate,
      );

    return () => {
      if (
        animationFrameRef.current !==
        null
      ) {
        cancelAnimationFrame(
          animationFrameRef.current,
        );
      }
    };
  }, [cameraTarget]);

  useEffect(() => {
    if (
      !draggingRedLineHandle ||
      !redLineDraft
    ) {
      return;
    }

    const road = roads.find(
      (item) =>
        item.id ===
        redLineDraft.roadId,
    );

    if (!road) {
      return;
    }

    const curb =
      curbPointsForRoad(
        road,
        redLineDraft.side,
      );

    const handleMove = (
      event: PointerEvent,
    ) => {
      const svg = svgRef.current;

      if (!svg) {
        return;
      }

      const point =
        clientPointToSvgPoint(
          svg,
          event.clientX,
          event.clientY,
        );

      const offset =
        nearestOffsetOnPolyline(
          curb,
          point,
        );

      if (
        draggingRedLineHandle ===
        "start"
      ) {
        onUpdateRedLineDraft({
          startOffset: offset,
        });
      } else {
        onUpdateRedLineDraft({
          endOffset: offset,
        });
      }
    };

    const handleUp = () => {
      setDraggingRedLineHandle(
        null,
      );
    };

    window.addEventListener(
      "pointermove",
      handleMove,
    );

    window.addEventListener(
      "pointerup",
      handleUp,
    );

    return () => {
      window.removeEventListener(
        "pointermove",
        handleMove,
      );

      window.removeEventListener(
        "pointerup",
        handleUp,
      );
    };
  }, [
    draggingRedLineHandle,
    redLineDraft,
    roads,
    onUpdateRedLineDraft,
  ]);

  const handlePointerMove = (
    event: ReactPointerEvent<SVGPathElement>,
    road: RoadSegmentData,
  ) => {
    const svg = svgRef.current;

    if (!svg) {
      return;
    }

    const rect =
      svg.getBoundingClientRect();

    setTooltipPosition({
      x:
        event.clientX -
        rect.left +
        16,
      y:
        event.clientY -
        rect.top +
        16,
    });

    setHoveredRoadId(road.id);
  };

  const handleIntersectionHover = (
    event: ReactPointerEvent<SVGGElement>,
    intersection: IntersectionData,
  ) => {
    const svg = svgRef.current;

    if (!svg) {
      return;
    }

    const rect =
      svg.getBoundingClientRect();

    setTooltipPosition({
      x:
        event.clientX -
        rect.left +
        16,
      y:
        event.clientY -
        rect.top +
        16,
    });

    setHoveredIntersectionId(
      intersection.id,
    );
  };

  const zoomCamera = (
    factor: number,
  ) => {
    setCamera((current) => {
      const centerX =
        current.x +
        current.width / 2;

      const centerY =
        current.y +
        current.height / 2;

      const width = Math.max(
        260,
        Math.min(
          1280,
          current.width * factor,
        ),
      );

      const height = Math.max(
        190,
        Math.min(
          720,
          current.height * factor,
        ),
      );

      return {
        x:
          centerX -
          width / 2,
        y:
          centerY -
          height / 2,
        width,
        height,
      };
    });
  };

  const resetCamera = () => {
    onBackToDistrict();
  };

  const handleBackgroundClick = (
  event: ReactPointerEvent<SVGSVGElement>,
) => {
  const svg = svgRef.current;

  if (!svg) {
    return;
  }

  const point =
    clientPointToSvgPoint(
      svg,
      event.clientX,
      event.clientY,
    );

  if (activeTool === "parking") {
    onPickParkingLocation(
      point.x,
      point.y,
    );
  }

  if (activeTool === "youbike") {
    onPickYouBikeLocation(
      point.x,
      point.y,
    );
  }
};

  const handleCurbClick = (
    event: ReactMouseEvent<SVGPathElement>,
    road: RoadSegmentData,
    side: CurbSide,
  ) => {
    event.stopPropagation();

    if (
      !redLineDraft ||
      redLineDraft.roadId !==
        road.id
    ) {
      return;
    }

    const svg = svgRef.current;

    if (!svg) {
      return;
    }

    const curb =
      curbPointsForRoad(
        road,
        side,
      );

    const point =
      clientPointToSvgPoint(
        svg,
        event.clientX,
        event.clientY,
      );

    const offset =
      nearestOffsetOnPolyline(
        curb,
        point,
      );

    const startDistance =
      Math.abs(
        offset -
          redLineDraft.startOffset,
      );

    const endDistance =
      Math.abs(
        offset -
          redLineDraft.endOffset,
      );

    if (
      startDistance <= endDistance
    ) {
      onUpdateRedLineDraft({
        side,
        startOffset: offset,
      });
    } else {
      onUpdateRedLineDraft({
        side,
        endOffset: offset,
      });
    }
  };

  const renderRoad = (
    road: RoadSegmentData,
  ) => {
    const isSelected =
      road.id === selectedRoadId;

    const isHovered =
      road.id === hoveredRoadId;

    const leftCurb =
      curbPointsForRoad(
        road,
        "left",
      );

    const rightCurb =
      curbPointsForRoad(
        road,
        "right",
      );

    const draftSide =
      redLineDraft?.roadId ===
      road.id
        ? redLineDraft.side
        : null;

    return (
      <g key={road.id}>
        <path
          d={pointsToPath(leftCurb)}
          fill="none"
          stroke={
            isSelected &&
            activeTool ===
              "red-line" &&
            draftSide === "left"
              ? "#ff9ca5"
              : "#f0f5f9"
          }
          strokeWidth={
            draftSide === "left"
              ? 4
              : 2
          }
          strokeLinecap="round"
          opacity="0.95"
          pointerEvents="none"
        />

        <path
          d={pointsToPath(rightCurb)}
          fill="none"
          stroke={
            isSelected &&
            activeTool ===
              "red-line" &&
            draftSide === "right"
              ? "#ff9ca5"
              : "#f0f5f9"
          }
          strokeWidth={
            draftSide === "right"
              ? 4
              : 2
          }
          strokeLinecap="round"
          opacity="0.95"
          pointerEvents="none"
        />

        <path
          d={pointsToPath(road.points)}
          fill="none"
          stroke={
            isSelected
              ? "#2cbcff"
              : "#7c8795"
          }
          strokeWidth={
            isSelected
              ? 22
              : isHovered
                ? 18
                : 14
          }
          strokeLinecap="round"
          strokeLinejoin="round"
          filter={
            isSelected
              ? "url(#roadGlow)"
              : undefined
          }
          opacity={
            isSelected
              ? 0.92
              : 0.8
          }
          className={
            styles.roadHitArea
          }
          onPointerEnter={() =>
            setHoveredRoadId(
              road.id,
            )
          }
          onPointerLeave={() =>
            setHoveredRoadId(null)
          }
          onPointerMove={(event) =>
            handlePointerMove(
              event,
              road,
            )
          }
          onClick={() =>
            onSelectRoad(road.id)
          }
        />

        {isSelected && (
          <path
            d={pointsToPath(
              road.points,
            )}
            fill="none"
            stroke="#ffffff"
            strokeWidth="3"
            strokeDasharray="10 9"
            strokeLinecap="round"
            opacity="0.95"
            pointerEvents="none"
          />
        )}

        {isSelected &&
          activeTool ===
            "red-line" &&
          redLineDraft && (
            <>
              <path
                d={pointsToPath(
                  leftCurb,
                )}
                fill="none"
                stroke="transparent"
                strokeWidth="18"
                className={
                  styles.roadHitArea
                }
                onClick={(event) =>
                  handleCurbClick(
                    event,
                    road,
                    "left",
                  )
                }
              />

              <path
                d={pointsToPath(
                  rightCurb,
                )}
                fill="none"
                stroke="transparent"
                strokeWidth="18"
                className={
                  styles.roadHitArea
                }
                onClick={(event) =>
                  handleCurbClick(
                    event,
                    road,
                    "right",
                  )
                }
              />
            </>
          )}
      </g>
    );
  };

const renderRedLine = (
  policy: RedLinePolicyData,
  draft = false,
) => {
  const road = roads.find(
    (item) => item.id === policy.roadId,
  );

  if (!road) {
    return null;
  }

  const curb = curbPointsForRoad(
    road,
    policy.side,
  );

  const section = slicePolyline(
    curb,
    policy.startOffset,
    policy.endOffset,
  );

  return (
    <g
      key={draft ? "red-line-draft" : policy.id}
      pointerEvents="none"
    >
      {/* 白色底框，讓紅線更清楚 */}
      <path
        d={pointsToPath(section)}
        fill="none"
        stroke="#ffffff"
        strokeWidth={draft ? 14 : 12}
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.98"
      />

      {/* 紅線主體：起點到終點中間這整段 */}
      <path
        d={pointsToPath(section)}
        fill="none"
        stroke={draft ? "#ff2b3a" : "#e32636"}
        strokeWidth={draft ? 10 : 8}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter={draft ? "url(#redLineGlow)" : undefined}
        opacity={1}
      />
    </g>
  );
};

  const renderRedLineHandles = () => {
    if (
      !redLineDraft ||
      !selectedRoad ||
      selectedRoad.id !==
        redLineDraft.roadId
    ) {
      return null;
    }

    const curb =
      curbPointsForRoad(
        selectedRoad,
        redLineDraft.side,
      );

    const start =
      pointAtOffset(
        curb,
        redLineDraft.startOffset,
      );

    const end =
      pointAtOffset(
        curb,
        redLineDraft.endOffset,
      );

    const renderHandle = (
      point: Point,
      handle: RedLineHandle,
      label: string,
    ) => (
      <g
        key={handle}
        className={
          styles.roadHitArea
        }
        onPointerDown={(event) => {
          event.stopPropagation();
          event.preventDefault();

          setDraggingRedLineHandle(
            handle,
          );
        }}
      >
        <circle
          cx={point.x}
          cy={point.y}
          r="12"
          fill="#ffffff"
          stroke="#ff2638"
          strokeWidth="3"
        />
        <circle
          cx={point.x}
          cy={point.y}
          r="5"
          fill="#ff2638"
        />
        <text
          x={point.x}
          y={point.y - 17}
          textAnchor="middle"
          className={
            styles.svgPoiLabel
          }
          fontSize="12"
        >
          {label}
        </text>
      </g>
    );

    return (
      <>
        {renderHandle(
          start,
          "start",
          "起點",
        )}
        {renderHandle(
          end,
          "end",
          "終點",
        )}
      </>
    );
  };

  const renderIntersection = (
    intersection: IntersectionData,
  ) => {
    const isSelected =
      intersection.id ===
      selectedIntersectionId;

    return (
      <g
        key={intersection.id}
        onPointerEnter={(event) =>
          handleIntersectionHover(
            event,
            intersection,
          )
        }
        onPointerLeave={() =>
          setHoveredIntersectionId(
            null,
          )
        }
        onClick={() =>
          onSelectIntersection(
            intersection.id,
          )
        }
        className={
          styles.roadHitArea
        }
      >
        <rect
          x={
            intersection.x - 21
          }
          y={
            intersection.y - 21
          }
          width="42"
          height="42"
          rx="6"
          fill="#d0d6db"
          opacity="0.9"
        />

        {[-11, -5, 1, 7, 13].map(
          (offset) => (
            <rect
              key={`${intersection.id}-top-${offset}`}
              x={
                intersection.x +
                offset -
                1.5
              }
              y={
                intersection.y - 20
              }
              width="3"
              height="11"
              rx="1"
              fill="#ffffff"
            />
          ),
        )}

        {[-11, -5, 1, 7, 13].map(
          (offset) => (
            <rect
              key={`${intersection.id}-bottom-${offset}`}
              x={
                intersection.x +
                offset -
                1.5
              }
              y={
                intersection.y + 9
              }
              width="3"
              height="11"
              rx="1"
              fill="#ffffff"
            />
          ),
        )}

        {[-11, -5, 1, 7, 13].map(
          (offset) => (
            <rect
              key={`${intersection.id}-left-${offset}`}
              x={
                intersection.x - 20
              }
              y={
                intersection.y +
                offset -
                1.5
              }
              width="11"
              height="3"
              rx="1"
              fill="#ffffff"
            />
          ),
        )}

        {[-11, -5, 1, 7, 13].map(
          (offset) => (
            <rect
              key={`${intersection.id}-right-${offset}`}
              x={
                intersection.x + 9
              }
              y={
                intersection.y +
                offset -
                1.5
              }
              width="11"
              height="3"
              rx="1"
              fill="#ffffff"
            />
          ),
        )}

        <circle
          cx={intersection.x}
          cy={intersection.y}
          r={
            isSelected ? 30 : 24
          }
          fill={
            isSelected
              ? "rgba(44,188,255,0.14)"
              : "transparent"
          }
          stroke={
            isSelected
              ? "#2cbcff"
              : "transparent"
          }
          strokeWidth="2"
        />

        <g
          transform={`translate(${intersection.x + 18} ${intersection.y - 18})`}
        >
          <rect
            x="0"
            y="0"
            width="10"
            height="24"
            rx="4"
            fill="#1f2937"
          />
          <circle
            cx="5"
            cy="5"
            r="2.8"
            fill="#ef4444"
          />
          <circle
            cx="5"
            cy="12"
            r="2.8"
            fill="#f59e0b"
          />
          <circle
            cx="5"
            cy="19"
            r="2.8"
            fill="#22c55e"
          />
        </g>

        <text
          x={intersection.x}
          y={
            intersection.y - 28
          }
          textAnchor="middle"
          className={
            styles.svgPoiLabel
          }
        >
          {intersection.name}
        </text>
      </g>
    );
  };

  const hoveredRoad =
    hoveredRoadId
      ? roads.find(
          (road) =>
            road.id ===
            hoveredRoadId,
        ) ?? null
      : null;

  const hoveredIntersection =
    hoveredIntersectionId
      ? intersections.find(
          (item) =>
            item.id ===
            hoveredIntersectionId,
        ) ?? null
      : null;

  const focusCard =
    selectedIntersection ??
    selectedRoad;

  return (
    <div
      className={styles.mapContainer}
    >
      <svg
        ref={svgRef}
        className={styles.mapSvg}
        viewBox={`${camera.x} ${camera.y} ${camera.width} ${camera.height}`}
        preserveAspectRatio="xMidYMid meet"
        onClick={
          handleBackgroundClick
        }
      >
        <defs>
          <filter
            id="roadGlow"
            x="-100%"
            y="-100%"
            width="300%"
            height="300%"
          >
            <feGaussianBlur
              stdDeviation="7"
              result="blur"
            />
            <feFlood
              floodColor="#39d5ff"
              floodOpacity="0.95"
            />
            <feComposite
              in2="blur"
              operator="in"
            />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <filter
            id="redLineGlow"
            x="-100%"
            y="-100%"
            width="300%"
            height="300%"
          >
            <feGaussianBlur
              stdDeviation="4"
              result="blur"
            />
            <feFlood
              floodColor="#ff2638"
              floodOpacity="0.75"
            />
            <feComposite
              in2="blur"
              operator="in"
            />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          <clipPath id="districtClip">
            <rect
              x={
                DISTRICT_BOUNDARY.x
              }
              y={
                DISTRICT_BOUNDARY.y
              }
              width={
                DISTRICT_BOUNDARY.width
              }
              height={
                DISTRICT_BOUNDARY.height
              }
            />
          </clipPath>
        </defs>

        <rect
          x={0}
          y={0}
          width={1280}
          height={720}
          fill="#f7f8f7"
        />

        <g clipPath="url(#districtClip)">
          {CITY_BLOCKS.map(
            (block, index) => (
              <rect
                key={`block-${index}`}
                x={block.x}
                y={block.y}
                width={block.w}
                height={block.h}
                fill={
                  index % 3 === 0
                    ? "#edf4ef"
                    : "#f5f1ec"
                }
                opacity="0.55"
              />
            ),
          )}

          {PARKS.map((park) => (
            <g key={park.id}>
              <rect
                x={park.x}
                y={park.y}
                width={park.width}
                height={park.height}
                rx="4"
                fill="#d8efce"
                opacity="0.85"
              />
              <text
                x={
                  park.x +
                  park.width / 2
                }
                y={
                  park.y +
                  park.height / 2 +
                  5
                }
                textAnchor="middle"
                className={
                  styles.svgParkLabel
                }
              >
                {park.name}
              </text>
            </g>
          ))}

          {BUILDINGS.map(
            (building) => (
              <g key={building.id}>
                <rect
                  x={building.x}
                  y={building.y}
                  width={
                    building.width
                  }
                  height={
                    building.height
                  }
                  rx="3"
                  fill="#e8ebef"
                  opacity="0.95"
                />
                <text
                  x={
                    building.x +
                    building.width /
                      2
                  }
                  y={
                    building.y +
                    building.height /
                      2 +
                    4
                  }
                  textAnchor="middle"
                  className={
                    styles.svgBuildingLabel
                  }
                >
                  {building.name}
                </text>
              </g>
            ),
          )}

          {roads.map((road) =>
            renderRoad(road),
          )}

          {redLinePolicies.map(
            (policy) =>
              renderRedLine(
                policy,
                false,
              ),
          )}

          {redLineDraft &&
            renderRedLine(
              redLineDraft,
              true,
            )}

          {renderRedLineHandles()}

          {roads.map((road) => {
            const label =
              road.label ?? {
                x:
                  road.points[0].x,
                y:
                  road.points[0].y -
                  12,
              };

            return (
              <text
                key={`${road.id}-label`}
                x={label.x}
                y={label.y}
                textAnchor="middle"
                className={
                  styles.svgRoadLabel
                }
                transform={
                  label.rotate
                    ? `rotate(${label.rotate} ${label.x} ${label.y})`
                    : undefined
                }
              >
                {road.roadName}
              </text>
            );
          })}

          {intersections.map(
            (intersection) =>
              renderIntersection(
                intersection,
              ),
          )}

          {parkings.map(
            (parking) => (
              <g key={parking.id}>
                <circle
                  cx={parking.x}
                  cy={parking.y}
                  r={
                    parking.status ===
                    "new"
                      ? 18
                      : 17
                  }
                  fill={
                    parking.status ===
                    "new"
                      ? "#0aa45b"
                      : "#2876ff"
                  }
                  stroke="#ffffff"
                  strokeWidth="3"
                />
                <text
                  x={parking.x}
                  y={
                    parking.y + 7
                  }
                  textAnchor="middle"
                  className={
                    styles.parkingText
                  }
                >
                  P
                </text>
                <text
                  x={
                    parking.x + 20
                  }
                  y={
                    parking.y - 10
                  }
                  className={
                    styles.svgPoiLabel
                  }
                >
                  {parking.name}
                </text>
              </g>
            ),
          )}

          {youbikes.map(
            (station) => (
              <g key={station.id}>
                <circle
                  cx={station.x}
                  cy={station.y}
                  r="15"
                  fill="#ffffff"
                  stroke="#1f7aff"
                  strokeWidth="2"
                />
                <text
                  x={station.x}
                  y={
                    station.y + 6
                  }
                  textAnchor="middle"
                  className={
                    styles.youBikeText
                  }
                >
                  ⓪
                </text>
                <text
                  x={
                    station.x + 18
                  }
                  y={
                    station.y - 10
                  }
                  className={
                    styles.svgPoiLabel
                  }
                >
                  {station.name ??
                    "UBIKE 站點"}
                </text>
              </g>
            ),
          )}
        </g>

        <rect
          x={DISTRICT_BOUNDARY.x}
          y={DISTRICT_BOUNDARY.y}
          width={
            DISTRICT_BOUNDARY.width
          }
          height={
            DISTRICT_BOUNDARY.height
          }
          fill="none"
          stroke="#2b82ff"
          strokeWidth="2"
          strokeDasharray="8 6"
          opacity="0.85"
        />

        <text
          x={
            DISTRICT_BOUNDARY.x +
            20
          }
          y={
            DISTRICT_BOUNDARY.y +
            26
          }
          className={
            styles.svgPoiLabel
          }
        >
          商圈範圍
        </text>
      </svg>

      {focusCard && (
        <div
          className={
            styles.roadFocusCard
          }
        >
          <button
            type="button"
            className={
              styles.backButton
            }
            onClick={
              onBackToDistrict
            }
          >
            ← 返回商圈
          </button>

          <div
            className={
              styles.focusDivider
            }
          />

          {selectedIntersection ? (
            <>
              <strong>
                {
                  selectedIntersection.name
                }
              </strong>

              <div
                className={
                  styles.focusMeta
                }
              >
                <span>
                  {
                    selectedIntersection
                      .connectedRoadIds
                      .length
                  }{" "}
                  條相連道路
                </span>

                <em>
                  {
                    selectedIntersection
                      .restrictions
                      .length
                  }{" "}
                  項管制
                </em>
              </div>

              <div
                className={
                  styles.focusDivider
                }
              />

              <div
                className={
                  styles.intersectionPhaseList
                }
              >
                {selectedIntersection.phases.map(
                  (phase) => (
                    <div
                      key={`${selectedIntersection.id}-${phase.name}`}
                      className={
                        styles.intersectionPhaseRow
                      }
                    >
                      <span>
                        {phase.name}
                      </span>
                      <b>
                        {
                          phase.seconds
                        }{" "}
                        秒
                      </b>
                    </div>
                  ),
                )}
              </div>
            </>
          ) : (
            <>
              <strong>
                {selectedRoad?.roadName}
              </strong>

              <div
                className={
                  styles.focusMeta
                }
              >
                <span>
                  {selectedRoad?.from} -{" "}
                  {selectedRoad?.to}
                </span>

                <b>
                  {selectedRoad
                    ? roadLengthMeters(
                        selectedRoad,
                      )
                    : 0}{" "}
                  m
                </b>

                <em>
                  {selectedRoad?.direction ===
                  "two-way"
                    ? "雙向道路"
                    : "單向道路"}
                </em>
              </div>

              <div
                className={
                  styles.focusDivider
                }
              />

              <div
                className={
                  styles.focusSmallText
                }
              >
                紅線綁定 road.curb.left / road.curb.right；拖曳紅色端點只會修改 offset，不會改道路中心線。
              </div>
            </>
          )}
        </div>
      )}

      {hoveredRoad &&
        !draggingRedLineHandle && (
          <div
            className={
              styles.roadTooltip
            }
            style={{
              left:
                tooltipPosition.x,
              top:
                tooltipPosition.y,
            }}
          >
            <strong>
              {hoveredRoad.roadName}
            </strong>
            <span>
              {hoveredRoad.from} -{" "}
              {hoveredRoad.to}
            </span>
            <b>
              {roadLengthMeters(
                hoveredRoad,
              )}{" "}
              m
            </b>
          </div>
        )}

      {hoveredIntersection &&
        !draggingRedLineHandle &&
        !hoveredRoad && (
          <div
            className={
              styles.roadTooltip
            }
            style={{
              left:
                tooltipPosition.x,
              top:
                tooltipPosition.y,
            }}
          >
            <strong>
              {
                hoveredIntersection.name
              }
            </strong>
            <span>
              {
                hoveredIntersection
                  .connectedRoadIds
                  .length
              }{" "}
              條道路
            </span>
            <b>
              {
                hoveredIntersection
                  .restrictions
                  .length
              }{" "}
              項管制
            </b>
          </div>
        )}

      <div
        className={styles.mapControls}
      >
        <button
          onClick={() =>
            zoomCamera(0.82)
          }
        >
          +
        </button>
        <button
          onClick={() =>
            zoomCamera(1.22)
          }
        >
          −
        </button>
        <button
          onClick={resetCamera}
        >
          ⌂
        </button>
      </div>

      <div
        className={
          styles.mapModeControl
        }
      >
        <button
          className={
            styles.mapModeActive
          }
        >
          2D
        </button>
        <button>3D</button>
      </div>

      <div
        className={styles.scaleBar}
      >
        <div />
        100 m
      </div>

      <div
        className={styles.miniMap}
      >
        <svg
          viewBox={`${DISTRICT_CAMERA.x} ${DISTRICT_CAMERA.y} ${DISTRICT_CAMERA.width} ${DISTRICT_CAMERA.height}`}
        >
          <rect
            x={
              DISTRICT_BOUNDARY.x
            }
            y={
              DISTRICT_BOUNDARY.y
            }
            width={
              DISTRICT_BOUNDARY.width
            }
            height={
              DISTRICT_BOUNDARY.height
            }
            fill="rgba(44,188,255,0.06)"
            stroke="#2b82ff"
            strokeWidth="2"
            strokeDasharray="10 6"
          />

          <rect
            x={camera.x}
            y={camera.y}
            width={camera.width}
            height={camera.height}
            fill="none"
            stroke="#2b82ff"
            strokeWidth="2.5"
          />
        </svg>
      </div>

      {parkingDraft &&
        activeTool === "parking" && (
          <div
            className={styles.mapHint}
          >
            點擊地圖可放置停車場，左側欄位可以立即編輯名稱與車位數。
          </div>
        )}

      {activeTool ===
        "youbike" && (
        <div className={styles.mapHint}>
          點擊地圖可直接新增 UBIKE 站點。
        </div>
      )}

      {activeTool ===
        "red-line" &&
        selectedRoad && (
          <div
            className={styles.mapHint}
          >
            {redLineDraft
              ? "拖曳紅色起點 / 終點，或直接點選左右 curb；紅線只修改 curb offset。"
              : "目前沒有編輯中的紅線，請在左側建立新紅線區段。"}
          </div>
        )}

      {activeTool ===
        "traffic-control" &&
        selectedIntersection && (
          <div
            className={styles.mapHint}
          >
            已選取路口，請在左側調整紅綠燈相位與轉向管制。
          </div>
        )}
    </div>
  );
}
