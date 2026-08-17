import type {
  BuildingData,
  CameraBounds,
  IntersectionData,
  ParkData,
  ParkingData,
  RoadSegmentData,
  YouBikeData,
} from "@/features/simulation/simulation.types";

/* =========================================================
   WORLD
========================================================= */

export const WORLD_WIDTH = 1280;
export const WORLD_HEIGHT = 720;

/*
 * 整個信義商圈 Overview Camera
 */
export const DISTRICT_CAMERA: CameraBounds = {
  x: 0,
  y: 0,
  width: WORLD_WIDTH,
  height: WORLD_HEIGHT,
};

/*
 * 信義商圈模擬範圍
 *
 * 黑框／虛線框內才是目前 Sandbox World。
 */
export const DISTRICT_BOUNDARY = {
  x: 135,
  y: 80,
  width: 1000,
  height: 540,
};

/* =========================================================
   ROADS
========================================================= */

/*
 * 注意：
 *
 * 現階段先以「道路」為主要互動物件。
 *
 * 下一階段如果要做到：
 *
 * 市府路
 * ├─ 松壽路 → 松高路
 * └─ 松高路 → 忠孝東路五段
 *
 * 可以再把目前一條 RoadSegment 拆成多個 segment。
 */

export const ROADS: RoadSegmentData[] = [
  /* =======================================================
     市府路
  ======================================================= */

  {
    id: "shifu-road",

    roadName: "市府路",

    from: "松壽路",
    to: "忠孝東路五段",

    direction: "two-way",
    alignment: "vertical",

    points: [
      {
        x: 520,
        y: 120,
      },
      {
        x: 520,
        y: 270,
      },
      {
        x: 520,
        y: 410,
      },
      {
        x: 520,
        y: 560,
      },
    ],

    curb: {
      left: [
        { x: 502, y: 120 },
        { x: 502, y: 270 },
        { x: 502, y: 410 },
        { x: 502, y: 560 },
      ],
      right: [
        { x: 538, y: 120 },
        { x: 538, y: 270 },
        { x: 538, y: 410 },
        { x: 538, y: 560 },
      ],
    },

    intersectionIds: ["i-1", "i-4", "i-7"],

    turnRestrictions: [
      {
        id: "turn-shifu-right-1",
        type: "forbid-right-turn",
        targetRoadId: "zhongxiao-road",
        note: "平日 07:00-09:00 禁止右轉",
      },
    ],

    label: {
      x: 546,
      y: 366,
      rotate: 90,
    },

    /*
     * 點市府路後放大。
     *
     * 會保留：
     * - 松壽路
     * - 忠孝東路五段
     * - 左右建築
     * - Road Focus 操作空間
     */
    focusBounds: {
      x: 160,
      y: 60,
      width: 720,
      height: 560,
    },
  },

  /* =======================================================
     松智路
  ======================================================= */

  {
    id: "songzhi-road",

    roadName: "松智路",

    from: "松壽路",
    to: "忠孝東路五段",

    direction: "two-way",
    alignment: "vertical",

    points: [
      {
        x: 720,
        y: 120,
      },
      {
        x: 720,
        y: 270,
      },
      {
        x: 720,
        y: 410,
      },
      {
        x: 720,
        y: 560,
      },
    ],

    curb: {
      left: [
        { x: 702, y: 120 },
        { x: 702, y: 270 },
        { x: 702, y: 410 },
        { x: 702, y: 560 },
      ],
      right: [
        { x: 738, y: 120 },
        { x: 738, y: 270 },
        { x: 738, y: 410 },
        { x: 738, y: 560 },
      ],
    },

    intersectionIds: ["i-2", "i-5", "i-8"],

    label: {
      x: 746,
      y: 366,
      rotate: 90,
    },

    focusBounds: {
      x: 360,
      y: 60,
      width: 720,
      height: 560,
    },
  },

  /* =======================================================
     松仁路
  ======================================================= */

  {
    id: "songren-road",

    roadName: "松仁路",

    from: "松壽路",
    to: "忠孝東路五段",

    direction: "two-way",
    alignment: "vertical",

    points: [
      {
        x: 930,
        y: 120,
      },
      {
        x: 930,
        y: 270,
      },
      {
        x: 930,
        y: 410,
      },
      {
        x: 930,
        y: 560,
      },
    ],

    curb: {
      left: [
        { x: 912, y: 120 },
        { x: 912, y: 270 },
        { x: 912, y: 410 },
        { x: 912, y: 560 },
      ],
      right: [
        { x: 948, y: 120 },
        { x: 948, y: 270 },
        { x: 948, y: 410 },
        { x: 948, y: 560 },
      ],
    },

    intersectionIds: ["i-3", "i-6", "i-9"],

    label: {
      x: 956,
      y: 366,
      rotate: 90,
    },

    focusBounds: {
      x: 555,
      y: 60,
      width: 720,
      height: 560,
    },
  },

  /* =======================================================
     松壽路
  ======================================================= */

  {
    id: "songshou-road",

    roadName: "松壽路",

    from: "市府路",
    to: "松仁路",

    direction: "two-way",
    alignment: "horizontal",

    points: [
      {
        x: 150,
        y: 120,
      },
      {
        x: 300,
        y: 120,
      },
      {
        x: 520,
        y: 120,
      },
      {
        x: 720,
        y: 120,
      },
      {
        x: 930,
        y: 120,
      },
      {
        x: 1130,
        y: 120,
      },
    ],

    curb: {
      left: [
        { x: 150, y: 101 },
        { x: 300, y: 101 },
        { x: 520, y: 101 },
        { x: 720, y: 101 },
        { x: 930, y: 101 },
        { x: 1130, y: 101 },
      ],
      right: [
        { x: 150, y: 139 },
        { x: 300, y: 139 },
        { x: 520, y: 139 },
        { x: 720, y: 139 },
        { x: 930, y: 139 },
        { x: 1130, y: 139 },
      ],
    },

    intersectionIds: ["i-1", "i-2", "i-3"],

    label: {
      x: 650,
      y: 91,
    },

    focusBounds: {
      x: 210,
      y: 20,
      width: 850,
      height: 520,
    },
  },

  /* =======================================================
     松高路
  ======================================================= */

  {
    id: "songgao-road",

    roadName: "松高路",

    from: "市府路",
    to: "松仁路",

    direction: "two-way",
    alignment: "horizontal",

    points: [
      {
        x: 150,
        y: 270,
      },
      {
        x: 300,
        y: 270,
      },
      {
        x: 520,
        y: 270,
      },
      {
        x: 720,
        y: 270,
      },
      {
        x: 930,
        y: 270,
      },
      {
        x: 1130,
        y: 270,
      },
    ],

    curb: {
      left: [
        { x: 150, y: 251 },
        { x: 300, y: 251 },
        { x: 520, y: 251 },
        { x: 720, y: 251 },
        { x: 930, y: 251 },
        { x: 1130, y: 251 },
      ],
      right: [
        { x: 150, y: 289 },
        { x: 300, y: 289 },
        { x: 520, y: 289 },
        { x: 720, y: 289 },
        { x: 930, y: 289 },
        { x: 1130, y: 289 },
      ],
    },

    intersectionIds: ["i-4", "i-5", "i-6"],

    label: {
      x: 650,
      y: 242,
    },

    focusBounds: {
      x: 210,
      y: 70,
      width: 850,
      height: 520,
    },
  },

  /* =======================================================
     忠孝東路五段
  ======================================================= */

  {
    id: "zhongxiao-road",

    roadName: "忠孝東路五段",

    from: "市府路",
    to: "松仁路",

    direction: "two-way",
    alignment: "horizontal",

    points: [
      {
        x: 150,
        y: 560,
      },
      {
        x: 300,
        y: 560,
      },
      {
        x: 520,
        y: 560,
      },
      {
        x: 720,
        y: 560,
      },
      {
        x: 930,
        y: 560,
      },
      {
        x: 1130,
        y: 560,
      },
    ],

    curb: {
      left: [
        { x: 150, y: 541 },
        { x: 300, y: 541 },
        { x: 520, y: 541 },
        { x: 720, y: 541 },
        { x: 930, y: 541 },
        { x: 1130, y: 541 },
      ],
      right: [
        { x: 150, y: 579 },
        { x: 300, y: 579 },
        { x: 520, y: 579 },
        { x: 720, y: 579 },
        { x: 930, y: 579 },
        { x: 1130, y: 579 },
      ],
    },

    intersectionIds: ["i-7", "i-8", "i-9"],

    label: {
      x: 675,
      y: 600,
    },

    focusBounds: {
      x: 210,
      y: 200,
      width: 850,
      height: 500,
    },
  },
];

export const INTERSECTIONS: IntersectionData[] = [
  {
    id: "i-1",
    name: "市府路 / 松壽路",
    x: 520,
    y: 120,
    connectedRoadIds: ["shifu-road", "songshou-road"],
    phases: [
      { name: "直行", seconds: 42, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-2",
    name: "松智路 / 松壽路",
    x: 720,
    y: 120,
    connectedRoadIds: ["songzhi-road", "songshou-road"],
    phases: [
      { name: "直行", seconds: 40, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-3",
    name: "松仁路 / 松壽路",
    x: 930,
    y: 120,
    connectedRoadIds: ["songren-road", "songshou-road"],
    phases: [
      { name: "直行", seconds: 44, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-4",
    name: "市府路 / 松高路",
    x: 520,
    y: 270,
    connectedRoadIds: ["shifu-road", "songgao-road"],
    phases: [
      { name: "直行", seconds: 38, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-5",
    name: "松智路 / 松高路",
    x: 720,
    y: 270,
    connectedRoadIds: ["songzhi-road", "songgao-road"],
    phases: [
      { name: "直行", seconds: 46, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-6",
    name: "松仁路 / 松高路",
    x: 930,
    y: 270,
    connectedRoadIds: ["songren-road", "songgao-road"],
    phases: [
      { name: "直行", seconds: 44, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-7",
    name: "市府路 / 忠孝東路五段",
    x: 520,
    y: 560,
    connectedRoadIds: ["shifu-road", "zhongxiao-road"],
    phases: [
      { name: "直行", seconds: 36, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-8",
    name: "松智路 / 忠孝東路五段",
    x: 720,
    y: 560,
    connectedRoadIds: ["songzhi-road", "zhongxiao-road"],
    phases: [
      { name: "直行", seconds: 42, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [],
  },
  {
    id: "i-9",
    name: "松仁路 / 忠孝東路五段",
    x: 930,
    y: 560,
    connectedRoadIds: ["songren-road", "zhongxiao-road"],
    phases: [
      { name: "直行", seconds: 40, color: "green" },
      { name: "黃燈", seconds: 4, color: "yellow" },
      { name: "全紅", seconds: 2, color: "red" },
    ],
    restrictions: [
      {
        id: "i-9-entry",
        type: "forbid-entry",
        targetRoadId: "songren-road",
        note: "17:00-19:00 禁止進入",
      },
    ],
  },
];

/* =========================================================
   PARKS
========================================================= */

export const PARKS: ParkData[] = [
  {
    id: "songzhi-park",

    name: "松智公園",

    /*
     * 示意圖中位於市府路西側、
     * 松壽路附近。
     */
    x: 165,
    y: 155,

    width: 305,
    height: 105,
  },
];

/* =========================================================
   BUILDINGS
========================================================= */

export const BUILDINGS: BuildingData[] = [
  /* =======================================================
     市府路西側
  ======================================================= */

  {
    id: "shinkong-a11",

    name: "新光三越 A11",

    x: 170,
    y: 305,

    width: 130,
    height: 170,
  },

  {
    id: "vieshow",

    name: "信義威秀影城",

    x: 325,
    y: 305,

    width: 155,
    height: 170,
  },

  /* =======================================================
     市府路東側
  ======================================================= */

  {
    id: "breeze-xinyi",

    name: "微風信義",

    x: 555,
    y: 305,

    width: 125,
    height: 165,
  },

  {
    id: "breeze-nanshan",

    name: "微風南山",

    x: 755,
    y: 305,

    width: 130,
    height: 165,
  },

  {
    id: "att-4-fun",

    name: "ATT 4 FUN",

    x: 970,
    y: 305,

    width: 125,
    height: 165,
  },

  /* =======================================================
     忠孝東路附近
  ======================================================= */

  {
    id: "taipei-city-hall",

    name: "信義市政府",

    x: 330,
    y: 585,

    width: 155,
    height: 80,
  },

  {
    id: "world-trade",

    name: "信義世貿",

    x: 555,
    y: 585,

    width: 125,
    height: 80,
  },

  {
    id: "taipei-101",

    name: "台北 101",

    x: 755,
    y: 585,

    width: 150,
    height: 82,
  },
];

/* =========================================================
   PARKING
========================================================= */

/*
 * status:
 *
 * existing = 現況停車場 → 藍色 P
 * new      = Scenario 新增 → 綠色 P
 *
 * 新增停車場真正建立後，
 * SimulationShell 會把新的 ParkingData push 進 state。
 */

export const PARKINGS: ParkingData[] = [
  {
    id: "parking-songshou",

    name: "松壽廣場停車場",

    x: 610,
    y: 185,

    spaces: 120,

    status: "existing",
  },

  {
    id: "parking-att",

    name: "ATT 4 FUN 停車場",

    x: 880,
    y: 360,

    spaces: 150,

    status: "existing",
  },

  {
    id: "parking-cityhall",

    name: "信義市政府停車場",

    x: 400,
    y: 500,

    spaces: 280,

    status: "existing",
  },

  {
    id: "parking-world-trade",

    name: "信義世貿停車場",

    x: 630,
    y: 510,

    spaces: 320,

    status: "existing",
  },
];

/* =========================================================
   YOUBIKE
========================================================= */

export const YOUBIKES: YouBikeData[] = [
  /*
   * 松壽路 / 商圈西側
   */
  {
    id: "bike-songshou-west",

    x: 250,
    y: 120,
  },

  /*
   * 市府路 / 松壽路附近
   */
  {
    id: "bike-shifu-north",

    x: 585,
    y: 120,
  },

  /*
   * 松智路 / 松壽路附近
   */
  {
    id: "bike-songzhi-north",

    x: 815,
    y: 120,
  },

  /*
   * 松仁路區域
   */
  {
    id: "bike-songren-east",

    x: 1040,
    y: 285,
  },

  /*
   * 市府路 / 忠孝東路五段
   */
  {
    id: "bike-shifu-south",

    x: 365,
    y: 560,
  },

  /*
   * 忠孝東路東側
   */
  {
    id: "bike-zhongxiao-east",

    x: 1015,
    y: 560,
  },
];
