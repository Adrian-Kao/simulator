import type { RoadSegment } from "@/features/simulation/simulation.types";

export const roads: RoadSegment[] = [
  {
    id: "shifu-001",
    roadId: "shifu",
    name: "市府路",
    start: "松壽路",
    end: "忠孝東路五段",
    direction: "two-way",
    roadWidthMeters: 20,
    lengthMeters: 180,
    coordinates: [
      [121.5662, 25.0366],
      [121.5662, 25.03495],
      [121.5662, 25.03315]
    ]
  },
  {
    id: "songgao-001",
    roadId: "songgao",
    name: "松高路",
    start: "市府路",
    end: "松仁路",
    direction: "two-way",
    roadWidthMeters: 22,
    lengthMeters: 420,
    coordinates: [
      [121.5662, 25.0366],
      [121.568, 25.0366],
      [121.57035, 25.0366]
    ]
  },
  {
    id: "songshou-001",
    roadId: "songshou",
    name: "松壽路",
    start: "市府路",
    end: "松仁路",
    direction: "two-way",
    roadWidthMeters: 20,
    lengthMeters: 390,
    coordinates: [
      [121.5662, 25.03495],
      [121.568, 25.03495],
      [121.57035, 25.03495]
    ]
  },
  {
    id: "zhongxiao-001",
    roadId: "zhongxiao",
    name: "忠孝東路五段",
    start: "市府路",
    end: "松仁路",
    direction: "two-way",
    roadWidthMeters: 30,
    lengthMeters: 410,
    coordinates: [
      [121.5662, 25.03315],
      [121.568, 25.03315],
      [121.57035, 25.03315]
    ]
  },
  {
    id: "songzhi-001",
    roadId: "songzhi",
    name: "松智路",
    start: "松高路",
    end: "忠孝東路五段",
    direction: "two-way",
    roadWidthMeters: 20,
    lengthMeters: 210,
    coordinates: [
      [121.568, 25.0366],
      [121.568, 25.03495],
      [121.568, 25.03315]
    ]
  }
];
