export type SimulationStatus =
  | "idle"
  | "running"
  | "success"
  | "error";

export type SignalPhasePayload = {
  name: string;
  seconds: number;
  color: "green" | "yellow" | "red";
};

export type SimulationPolicyPayload =
  | {
      type: "red-line";
      road_id: string;
      side: "left" | "right";
      start_offset: number;
      end_offset: number;
      length_meters: number;
      start_time?: string;
      end_time?: string;
    }
  | {
      type: "parking";
      parking_id: string;
      name: string;
      spaces: number;
    }
  | {
      type: "signal-timing";
      intersection_id: string;
      phases: SignalPhasePayload[];
    }
  | {
      type: "traffic-restriction";
      intersection_id: string;
      restriction_type:
        | "forbid-right-turn"
        | "forbid-left-turn"
        | "forbid-entry";
      target_road_id: string;
    };

export type SimulationRequestPayload = {
  scenario_id: string;
  day_type: "weekday" | "weekend" | "event";
  time_slot: string;
  random_seed: number;
  road_id?: string;
  road_name?: string;
  policies: SimulationPolicyPayload[];
};

export type SimulationKpiPayload = {
  travel_time_minutes: number;
  travel_speed_kph: number;
  congestion_vc: number;
  queue_vehicles: number;
};

export type SimulationApiResult = {
  scenario_id: string;
  baseline: SimulationKpiPayload;
  scenario: SimulationKpiPayload;
  delta: {
    travel_time_percent: number;
    travel_speed_percent: number;
    congestion_vc_percent: number;
    queue_percent: number;
  };
  recommended:
    | "baseline"
    | "scenario"
    | "tie"
    | string;
  warnings: string[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_SIMULATION_API_URL ??
  "http://localhost:8000";

export async function runSimulation(
  request: SimulationRequestPayload,
): Promise<SimulationApiResult> {
  const response = await fetch(
    `${API_BASE_URL}/api/simulations`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Simulation API ${response.status}: ${text}`,
    );
  }

  return response.json() as Promise<SimulationApiResult>;
}
