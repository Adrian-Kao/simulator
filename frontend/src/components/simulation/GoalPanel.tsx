import type {
  SimulationApiResult,
  SimulationStatus,
} from "@/lib/simulation-api";

import {
  optimizerStatusLabel,
  type OptimizeApiResult,
  type OptimizerRunStatus,
  type ScenarioDiffPolicyPayload,
} from "@/lib/optimizer-api";

import styles from "@/styles/simulation.module.css";

type Props = {
  simulationStatus: SimulationStatus;
  simulationResult: SimulationApiResult | null;
  simulationError: string | null;
  onRunSimulation: () => void;

  /*
   * UI 執行狀態：
   * idle / running / success / error
   */
  optimizerStatus: OptimizerRunStatus;

  /*
   * API 回傳結果
   */
  optimizerResult: OptimizeApiResult | null;

  optimizerError: string | null;

  onRunOptimization: () => void;
};

function formatNumber(
  value: number,
  digits = 2,
) {
  if (!Number.isFinite(value)) {
    return "-";
  }

  return value.toFixed(digits);
}

function formatPercent(
  value: number,
  digits = 1,
) {
  if (!Number.isFinite(value)) {
    return "-";
  }

  const prefix = value > 0 ? "+" : "";

  return `${prefix}${value.toFixed(digits)}%`;
}

/*
 * 每個 optimizer iteration 的政策差異。
 */
function PolicyChange({
  policy,
}: {
  policy: ScenarioDiffPolicyPayload;
}) {
  switch (policy.type) {
    case "signal-timing":
      return (
        <div>
          <strong>Signal：</strong>

          {policy.baseline_seconds}
          {" → "}
          {policy.scenario_seconds}
          {" sec"}
        </div>
      );

    case "red-line":
      return (
        <div>
          <strong>Red Line：</strong>

          {policy.length_meters}
          {" m"}
        </div>
      );

    case "parking":
      return (
        <div>
          <strong>Parking：</strong>

          {policy.spaces}
          {" 格"}
        </div>
      );

    default:
      return null;
  }
}

export default function GoalPanel({
  simulationStatus,
  simulationResult,
  simulationError,
  onRunSimulation,

  optimizerStatus,
  optimizerResult,
  optimizerError,
  onRunOptimization,
}: Props) {
  return (
    <section className={styles.analysisSection}>
      <div className={styles.analysisGrid}>
        {/* =========================================
            LEFT：PYTHON SIMULATION
        ========================================== */}

        <div className={styles.analysisCard}>
          <div className={styles.analysisCardHeader}>
            <div>
              <h2 className={styles.analysisCardTitle}>
                Python Simulation
              </h2>

              <p className={styles.analysisCardSubtitle}>
                執行目前 Scenario，取得後端模擬 KPI
              </p>
            </div>

            <button
              type="button"
              className={styles.analysisPrimaryButton}
              onClick={onRunSimulation}
              disabled={
                simulationStatus === "running"
              }
            >
              {simulationStatus === "running"
                ? "模擬中..."
                : "開始模擬"}
            </button>
          </div>

          {simulationStatus === "idle" && (
            <div className={styles.analysisHint}>
              請先設定政策，然後按下「開始模擬」取得後端 KPI。
            </div>
          )}

          {simulationStatus === "running" && (
            <div className={styles.analysisHint}>
              Python Simulation 執行中...
            </div>
          )}

          {simulationStatus === "error" && (
            <div className={styles.analysisError}>
              模擬失敗：
              {simulationError ??
                "Unknown error"}
            </div>
          )}

          {simulationResult && (
            <div className={styles.kpiGrid}>
              {/* Travel Time */}

              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>
                  Travel Time
                </div>

                <div className={styles.kpiValue}>
                  {formatNumber(
                    simulationResult.baseline
                      .travel_time_minutes,
                  )}

                  {" → "}

                  {formatNumber(
                    simulationResult.scenario
                      .travel_time_minutes,
                  )}

                  {" min"}
                </div>

                <div className={styles.kpiDelta}>
                  {formatPercent(
                    simulationResult.delta
                      .travel_time_percent,
                  )}
                </div>
              </div>

              {/* Travel Speed */}

              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>
                  Travel Speed
                </div>

                <div className={styles.kpiValue}>
                  {formatNumber(
                    simulationResult.baseline
                      .travel_speed_kph,
                    1,
                  )}

                  {" → "}

                  {formatNumber(
                    simulationResult.scenario
                      .travel_speed_kph,
                    1,
                  )}

                  {" km/h"}
                </div>

                <div className={styles.kpiDelta}>
                  {formatPercent(
                    simulationResult.delta
                      .travel_speed_percent,
                  )}
                </div>
              </div>

              {/* V/C */}

              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>
                  V/C
                </div>

                <div className={styles.kpiValue}>
                  {formatNumber(
                    simulationResult.baseline
                      .congestion_vc,
                  )}

                  {" → "}

                  {formatNumber(
                    simulationResult.scenario
                      .congestion_vc,
                  )}
                </div>

                <div className={styles.kpiDelta}>
                  {formatPercent(
                    simulationResult.delta
                      .congestion_vc_percent,
                  )}
                </div>
              </div>

              {/* Queue */}

              <div className={styles.kpiCard}>
                <div className={styles.kpiLabel}>
                  Queue
                </div>

                <div className={styles.kpiValue}>
                  {formatNumber(
                    simulationResult.baseline
                      .queue_vehicles,
                    1,
                  )}

                  {" → "}

                  {formatNumber(
                    simulationResult.scenario
                      .queue_vehicles,
                    1,
                  )}

                  {" 輛"}
                </div>

                <div className={styles.kpiDelta}>
                  {formatPercent(
                    simulationResult.delta
                      .queue_percent,
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* =========================================
            RIGHT：POLICY OPTIMIZATION
        ========================================== */}

        <div className={styles.analysisCard}>
          <div className={styles.analysisCardHeader}>
            <div>
              <h2 className={styles.analysisCardTitle}>
                Policy Optimization
              </h2>

              <p className={styles.analysisCardSubtitle}>
                Gemini 依據 Simulation KPI reasoning
                並自動修正政策
              </p>
            </div>

            <button
              type="button"
              className={styles.analysisPrimaryButton}
              onClick={onRunOptimization}
              disabled={
                optimizerStatus === "running"
              }
            >
              {optimizerStatus === "running"
                ? "最佳化中..."
                : "開始 AI 最佳化"}
            </button>
          </div>

          {/* IDLE */}

          {optimizerStatus === "idle" && (
            <div className={styles.analysisHint}>
              執行 AI Policy Optimization，
              Gemini 將根據模擬 KPI 自動調整政策。
            </div>
          )}

          {/* RUNNING */}

          {optimizerStatus === "running" && (
            <div className={styles.analysisHint}>
              Gemini 正在分析 KPI
              並產生下一輪政策...
            </div>
          )}

          {/* ERROR */}

          {optimizerStatus === "error" && (
            <div className={styles.analysisError}>
              最佳化失敗：
              {optimizerError ??
                "Unknown error"}
            </div>
          )}

          {/* RESULT */}

          {optimizerResult && (
            <>
              <div className={styles.optimizationCard}>
                <div
                  className={
                    styles.optimizationHeader
                  }
                >
                  Optimization Result
                </div>

                <div
                  className={
                    styles.optimizationReasoning
                  }
                >
                  <strong>Status：</strong>

                  {optimizerStatusLabel(
                    optimizerResult.status,
                  )}

                  {optimizerResult.message && (
                    <>
                      <br />
                      <br />
                      {optimizerResult.message}
                    </>
                  )}
                </div>
              </div>

              <div
                className={
                  styles.optimizationList
                }
              >
                {optimizerResult.iterations.map(
                  (iteration) => (
                    <div
                      key={iteration.iteration}
                      className={
                        styles.optimizationCard
                      }
                    >
                      <div
                        className={
                          styles.optimizationHeader
                        }
                      >
                        Iteration{" "}
                        {iteration.iteration}
                      </div>

                      {/* Policy changes */}

                      <div
                        className={
                          styles.optimizationVars
                        }
                      >
                        {iteration.scenario
                          .policies.length ===
                        0 ? (
                          <div>
                            No policy changes
                          </div>
                        ) : (
                          iteration.scenario.policies.map(
                            (
                              policy,
                              index,
                            ) => (
                              <PolicyChange
                                key={`${iteration.iteration}-${policy.type}-${index}`}
                                policy={policy}
                              />
                            ),
                          )
                        )}
                      </div>

                      {/* KPI */}

                      <div
                        className={
                          styles.optimizationVars
                        }
                      >
                        <div>
                          <strong>
                            Travel Time：
                          </strong>

                          {formatNumber(
                            iteration.result
                              .scenario
                              .travel_time_minutes,
                          )}
                          {" min"}
                        </div>

                        <div>
                          <strong>
                            Speed：
                          </strong>

                          {formatNumber(
                            iteration.result
                              .scenario
                              .travel_speed_kph,
                            1,
                          )}
                          {" km/h"}
                        </div>

                        <div>
                          <strong>
                            V/C：
                          </strong>

                          {formatNumber(
                            iteration.result
                              .scenario
                              .congestion_vc,
                          )}
                        </div>

                        <div>
                          <strong>
                            Queue：
                          </strong>

                          {formatNumber(
                            iteration.result
                              .scenario
                              .queue_vehicles,
                            1,
                          )}
                          {" 輛"}
                        </div>
                      </div>

                      {/* Gemini reasoning */}

                      <div
                        className={
                          styles.optimizationReasoning
                        }
                      >
                        <strong>
                          Gemini Reasoning
                        </strong>

                        <br />

                        {iteration.reasoning ??
                          (iteration.goals_met
                            ? "目標已達成，不需要再調整政策。"
                            : "此輪沒有產生新的政策建議。")}
                      </div>

                      {/* Validation */}

                      {iteration
                        .validation_notes
                        .length > 0 && (
                        <div
                          className={
                            styles.optimizationReasoning
                          }
                        >
                          <strong>
                            Validation
                          </strong>

                          {iteration.validation_notes.map(
                            (
                              note,
                              index,
                            ) => (
                              <div
                                key={index}
                              >
                                • {note}
                              </div>
                            ),
                          )}
                        </div>
                      )}
                    </div>
                  ),
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}