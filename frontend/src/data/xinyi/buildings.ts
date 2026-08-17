import type { Building } from "@/features/simulation/simulation.types";

export const buildings: Building[] = [
  {
    id: "taipei-101",
    name: "台北101",
    kind: "landmark",
    footprint: [
      [121.56845, 25.03445],
      [121.56915, 25.03445],
      [121.56915, 25.03375],
      [121.56845, 25.03375]
    ]
  },
  {
    id: "vie-show",
    name: "信義威秀",
    kind: "mall",
    footprint: [
      [121.56665, 25.03625],
      [121.56755, 25.03625],
      [121.56755, 25.03535],
      [121.56665, 25.03535]
    ]
  },
  {
    id: "att-4-fun",
    name: "ATT 4 FUN",
    kind: "mall",
    footprint: [
      [121.56905, 25.03462],
      [121.56995, 25.03462],
      [121.56995, 25.03372],
      [121.56905, 25.03372]
    ]
  }
];
