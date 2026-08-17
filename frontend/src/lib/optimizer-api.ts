import type { GoalConfig } from "@/features/simulation/simulation.types";

import {
  postJson,
  type GoalStatusPayload,
  type PolicyVariablesPayload,
  type SimulationApiResult,
  type SimulationRequestPayload,
} from "./simulation-api";

export type OptimizerStatus =
  | "goal_reached"
  | "max_iterations"
  | "ai_unavailable"
  | "ai_error";

export type OptimizerRunStatus =
  | "idle"
  | "running"
  | "success"
  | "error";

export type ScenarioDiffPolicyPayload =
  | {
      type: "signal-timing";
      intersection_id: string;
      baseline_seconds: number;
      scenario_seconds: number;
    }
  | {
      type: "red-line";
      road_id: string;
      length_meters: number;
    }
  | {
      type: "parking";
      parking_id: string;
      spaces: number;
    };

export type ScenarioDiffPayload = {
  scenario_id: string;
  policies: ScenarioDiffPolicyPayload[];
};

export type OptimizationIterationPayload = {
  iteration: number;
  scenario: ScenarioDiffPayload;
  result: SimulationApiResult;
  goal_status: GoalStatusPayload[];
  goals_met: boolean;
  /*
   * 這一輪之後套用的 patch 的理由。
   * 最後一輪沒有 patch，所以 reasoning 為 null。
   */
  reasoning: string | null;
  recommendation: PolicyVariablesPayload | null;
  validation_notes: string[];
};

export type OptimizeApiResult = {
  status: OptimizerStatus;
  iterations: OptimizationIterationPayload[];
  final_scenario: ScenarioDiffPayload;
  final_result: SimulationApiResult;
  message: string | null;
  metadata: Record<string, unknown>;
};

export type OptimizeRequestPayload = {
  initial_scenario: SimulationRequestPayload;
  goals: GoalConfig;
  max_iterations: number;
};

export const DEFAULT_MAX_ITERATIONS = 5;

export async function runOptimization(
  request: OptimizeRequestPayload,
): Promise<OptimizeApiResult> {
  return postJson<OptimizeApiResult>(
    "/api/optimize",
    request,
  );
}

export function optimizerStatusLabel(
  status: OptimizerStatus,
): string {
  switch (status) {
    case "goal_reached":
      return "Goal Reached";
    case "max_iterations":
      return "Max Iterations Reached";
    case "ai_unavailable":
      return "AI Unavailable（未設定 GEMINI_API_KEY）";
    case "ai_error":
      return "AI Error";
    default:
      return status;
  }
}
