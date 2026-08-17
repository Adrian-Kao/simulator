import type { GoalConfig, GoalMetric } from "@/features/simulation/simulation.types";

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
      side?: "left" | "right";
      start_offset?: number;
      end_offset?: number;
      length_meters: number;
      start_time?: string;
      end_time?: string;
    }
  | {
      type: "parking";
      parking_id: string;
      name?: string;
      spaces: number;
    }
  | {
      type: "signal-timing";
      intersection_id: string;
      baseline_seconds: number;
      scenario_seconds: number;
      phases?: SignalPhasePayload[];
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
  goals?: GoalConfig;
};

export type SimulationKpiPayload = {
  travel_time_minutes: number;
  travel_speed_kph: number;
  congestion_vc: number;
  queue_vehicles: number;
};

export type SimulationDeltaPayload = {
  travel_time_percent: number;
  travel_speed_percent: number;
  congestion_vc_percent: number;
  queue_percent: number;
};

export type PolicyVariablesPayload = {
  signal_green_seconds: number;
  red_line_meters: number;
  parking_spaces: number;
};

export type GoalStatusPayload = {
  metric: GoalMetric;
  label: string;
  direction: "decrease" | "increase";
  target_percent: number;
  current_percent: number;
  gap_percent: number;
  met: boolean;
};

export type SimulationApiResult = {
  scenario_id: string;
  baseline: SimulationKpiPayload;
  scenario: SimulationKpiPayload;
  delta: SimulationDeltaPayload;
  recommended: "baseline" | "scenario" | "tie" | string;
  baseline_variables: PolicyVariablesPayload;
  scenario_variables: PolicyVariablesPayload;
  goal_status: GoalStatusPayload[];
  goals_met: boolean;
  warnings: string[];
  metadata: Record<string, unknown>;
};

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_SIMULATION_API_URL ??
  "http://localhost:8000";

export async function postJson<T>(
  path: string,
  body: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `${path} ${response.status}: ${text}`,
    );
  }

  return response.json() as Promise<T>;
}

export async function runSimulation(
  request: SimulationRequestPayload,
): Promise<SimulationApiResult> {
  return postJson<SimulationApiResult>(
    "/api/simulations",
    request,
  );
}
