"use client";

import type {
  GoalConfig,
  GoalMetric,
} from "@/features/simulation/simulation.types";

import {
  optimizerStatusLabel,
  type OptimizeApiResult,
  type OptimizerRunStatus,
} from "@/lib/optimizer-api";

import type {
  GoalStatusPayload,
  PolicyVariablesPayload,
  SimulationApiResult,
  SimulationKpiPayload,
  SimulationStatus,
} from "@/lib/simulation-api";

import styles from "@/styles/simulation.module.css";

type Props = {
  scenarioPolicyCount: number;

  simulationStatus: SimulationStatus;
  simulationResult: SimulationApiResult | null;
  simulationError: string | null;
  onRunSimulation: () => void;

  goals: GoalConfig;
  onChangeGoal: (metric: GoalMetric, value: number | null) => void;

  optimizerStatus: OptimizerRunStatus;
  optimizerResult: OptimizeApiResult | null;
  optimizerError: string | null;
  onRunOptimization: () => void;
};

type KpiRow = {
  metric: GoalMetric;
  label: string;
  icon: string;
  unit: string;
  digits: number;
  read: (kpi: SimulationKpiPayload) => number;
};

/*
 * 每個 KPI 的 baseline / scenario 數值都來自 Python backend，
 * 這裡只負責格式化，不做任何 KPI 計算。
 */
const KPI_ROWS: KpiRow[] = [
  {
    metric: "travel_time_percent",
    label: "Travel Time",
    icon: "⏱",
    unit: "min",
    digits: 2,
    read: (kpi) => kpi.travel_time_minutes,
  },
  {
    metric: "travel_speed_percent",
    label: "Travel Speed",
    icon: "🚗",
    unit: "km/h",
    digits: 1,
    read: (kpi) => kpi.travel_speed_kph,
  },
  {
    metric: "congestion_vc_percent",
    label: "V/C",
    icon: "⚙",
    unit: "",
    digits: 3,
    read: (kpi) => kpi.congestion_vc,
  },
  {
    metric: "queue_percent",
    label: "Queue",
    icon: "🚦",
    unit: "輛",
    digits: 1,
    read: (kpi) => kpi.queue_vehicles,
  },
];

const VARIABLE_ROWS: {
  key: keyof PolicyVariablesPayload;
  label: string;
  unit: string;
}[] = [
  { key: "signal_green_seconds", label: "Signal", unit: "sec" },
  { key: "red_line_meters", label: "Red Line", unit: "m" },
  { key: "parking_spaces", label: "Parking", unit: "spaces" },
];

function formatNumber(value: number, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : "-";
}

function formatPercent(value: number, digits = 1) {
  if (!Number.isFinite(value)) {
    return "-";
  }
  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(digits)}%`;
}

function goalStatusFor(
  result: SimulationApiResult | null,
  metric: GoalMetric,
): GoalStatusPayload | null {
  if (!result) {
    return null;
  }
  return (
    result.goal_status.find((status) => status.metric === metric) ??
    null
  );
}

function deltaFor(
  result: SimulationApiResult,
  metric: GoalMetric,
): number {
  return result.delta[metric];
}

export default function GoalPanel({
  scenarioPolicyCount,
  simulationStatus,
  simulationResult,
  simulationError,
  onRunSimulation,
  goals,
  onChangeGoal,
  optimizerStatus,
  optimizerResult,
  optimizerError,
  onRunOptimization,
}: Props) {
  const usesFallback = Boolean(
    simulationResult?.metadata?.["uses_fallback"],
  );

  return (
    <aside className={styles.rightSidebar}>
      {/* ================= KPI Dashboard ================= */}

      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>Python Simulation</strong>

          <button
            type="button"
            onClick={onRunSimulation}
            disabled={simulationStatus === "running"}
          >
            {simulationStatus === "running"
              ? "模擬中..."
              : "開始模擬"}
          </button>
        </div>

        {simulationStatus === "idle" && (
          <div className={styles.tipBox}>
            {scenarioPolicyCount === 0
              ? "目前 Scenario 是 0 筆政策，模擬結果會等於 baseline。先在地圖上修改號誌、紅線或停車，再按「開始模擬」。"
              : `目前 Scenario 有 ${scenarioPolicyCount} 筆政策，按「開始模擬」由 Python backend 計算 KPI。`}
          </div>
        )}

        {simulationStatus === "error" && (
          <div className={styles.tipBox}>
            API 錯誤：{simulationError ?? "Unknown error"}
          </div>
        )}

        {simulationResult && (
          <div className={styles.kpiList}>
            {KPI_ROWS.map((row) => {
              const status = goalStatusFor(
                simulationResult,
                row.metric,
              );
              const delta = deltaFor(
                simulationResult,
                row.metric,
              );

              return (
                <div
                  key={row.metric}
                  className={styles.kpiCard}
                >
                  <div className={styles.kpiCardHeader}>
                    <span>{row.icon}</span>
                    <strong>{row.label}</strong>
                    {status && (
                      <em
                        className={
                          status.met
                            ? styles.goalMet
                            : styles.goalUnmet
                        }
                      >
                        {status.met
                          ? "✓ 已達標"
                          : "尚未達標"}
                      </em>
                    )}
                  </div>

                  <div className={styles.kpiRow}>
                    <span>Baseline</span>
                    <b>
                      {formatNumber(
                        row.read(simulationResult.baseline),
                        row.digits,
                      )}{" "}
                      {row.unit}
                    </b>
                  </div>

                  <div className={styles.kpiRow}>
                    <span>Scenario</span>
                    <b>
                      {formatNumber(
                        row.read(simulationResult.scenario),
                        row.digits,
                      )}{" "}
                      {row.unit}
                    </b>
                  </div>

                  <div className={styles.kpiRow}>
                    <span>Delta</span>
                    <b>{formatPercent(delta)}</b>
                  </div>

                  {status ? (
                    <>
                      <div className={styles.kpiRow}>
                        <span>Target</span>
                        <b>
                          {formatPercent(
                            status.target_percent,
                          )}
                        </b>
                      </div>

                      <div className={styles.kpiRow}>
                        <span>Gap</span>
                        <b>
                          {formatNumber(
                            status.gap_percent,
                            1,
                          )}
                          %
                        </b>
                      </div>
                    </>
                  ) : (
                    <div className={styles.kpiRow}>
                      <span>Target</span>
                      <b>未設定</b>
                    </div>
                  )}
                </div>
              );
            })}

            {usesFallback && (
              <div className={styles.tipBox}>
                注意：本次模擬使用 fallback 預設值（非觀測歷史資料），
                且政策效果為未校準的 MVP proxy 模型。
              </div>
            )}

            <div className={styles.kpiCard}>
              <div className={styles.kpiCardHeader}>
                <span>🧑</span>
                <strong>Agent 運具判斷</strong>
              </div>
              {Object.entries(
                simulationResult.behavior.scenario_mode_share,
              ).map(([mode, share]) => (
                <div className={styles.kpiRow} key={mode}>
                  <span>{mode}</span>
                  <b>{formatNumber(share * 100, 1)}%</b>
                </div>
              ))}
              <div className={styles.kpiRow}>
                <span>改變選擇</span>
                <b>{simulationResult.behavior.shifted_people} 人</b>
              </div>
            </div>

            <div className={styles.kpiCard}>
              <div className={styles.kpiCardHeader}>
                <span>🏙</span>
                <strong>後續發展需求</strong>
              </div>
              <div className={styles.kpiRow}>
                <span>停車</span>
                <b>{formatPercent(simulationResult.development.parking_demand_percent)}</b>
              </div>
              <div className={styles.kpiRow}>
                <span>大眾運輸</span>
                <b>{formatPercent(simulationResult.development.transit_demand_percent)}</b>
              </div>
              <div className={styles.kpiRow}>
                <span>YouBike</span>
                <b>{formatPercent(simulationResult.development.youbike_demand_percent)}</b>
              </div>
            </div>

            <div className={styles.tipBox}>
              {simulationResult.development.signals.join("；")}
            </div>

            {simulationResult.warnings.length > 0 && (
              <ul className={styles.warningList}>
                {simulationResult.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </section>

      {/* ================= Goal Config ================= */}

      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>情境目標設定</strong>
          <span className={styles.goalHint}>
            相對 baseline 的 %
          </span>
        </div>

        <div className={styles.goalList}>
          {KPI_ROWS.map((row) => {
            const value = goals[row.metric];

            return (
              <label
                key={row.metric}
                className={styles.goalConfigRow}
              >
                <span className={styles.goalIcon}>
                  {row.icon}
                </span>

                <span className={styles.goalConfigLabel}>
                  {row.label}
                </span>

                <input
                  type="number"
                  step={1}
                  className={styles.goalInput}
                  value={value ?? ""}
                  placeholder="未設定"
                  onChange={(event) => {
                    const raw = event.target.value;
                    onChangeGoal(
                      row.metric,
                      raw === ""
                        ? null
                        : Number(raw),
                    );
                  }}
                />

                <span className={styles.goalConfigUnit}>
                  %
                </span>
              </label>
            );
          })}
        </div>

        <div className={styles.tipBox}>
          負值代表要下降，正值代表要上升。留空表示不列為目標。
        </div>
      </section>

      {/* ================= AI Optimization ================= */}

      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>AI Policy Optimization</strong>

          <button
            type="button"
            onClick={onRunOptimization}
            disabled={optimizerStatus === "running"}
          >
            {optimizerStatus === "running"
              ? "最佳化中..."
              : "AI 最佳化"}
          </button>
        </div>

        {optimizerStatus === "idle" && (
          <div className={styles.tipBox}>
            Gemini 只會提出下一輪的三個政策變量（號誌秒數 / 紅線長度 /
            停車位），所有 KPI 仍由 Python 模擬計算。
          </div>
        )}

        {optimizerStatus === "error" && (
          <div className={styles.tipBox}>
            最佳化錯誤：{optimizerError ?? "Unknown error"}
          </div>
        )}

        {optimizerResult && (
          <div className={styles.iterationList}>
            <div
              className={
                optimizerResult.status === "goal_reached"
                  ? styles.optimizerStatusOk
                  : styles.optimizerStatusWarn
              }
            >
              {optimizerStatusLabel(optimizerResult.status)}
            </div>

            {optimizerResult.message && (
              <div className={styles.optimizerMessage}>
                {optimizerResult.message}
              </div>
            )}

            {optimizerResult.iterations.map(
              (iteration, index) => {
                const previous =
                  index === 0
                    ? iteration.result.baseline_variables
                    : optimizerResult.iterations[index - 1]
                        .result.scenario_variables;

                const current =
                  iteration.result.scenario_variables;

                return (
                  <div
                    key={iteration.iteration}
                    className={styles.iterationCard}
                  >
                    <div
                      className={styles.iterationHeader}
                    >
                      <strong>
                        Iteration {iteration.iteration}
                      </strong>
                      <em
                        className={
                          iteration.goals_met
                            ? styles.goalMet
                            : styles.goalUnmet
                        }
                      >
                        {iteration.goals_met
                          ? "✓ 已達標"
                          : "尚未達標"}
                      </em>
                    </div>

                    {VARIABLE_ROWS.map((variable) => (
                      <div
                        key={variable.key}
                        className={styles.kpiRow}
                      >
                        <span>{variable.label}</span>
                        <b>
                          {previous[variable.key]}
                          {" → "}
                          {current[variable.key]}{" "}
                          {variable.unit}
                        </b>
                      </div>
                    ))}

                    <div
                      className={styles.iterationDivider}
                    />

                    {iteration.goal_status.map((status) => (
                      <div
                        key={status.metric}
                        className={styles.kpiRow}
                      >
                        <span>{status.label}</span>
                        <b>
                          {formatPercent(
                            status.current_percent,
                          )}{" "}
                          / target{" "}
                          {formatPercent(
                            status.target_percent,
                          )}{" "}
                          {status.met ? "✓" : "✕"}
                        </b>
                      </div>
                    ))}

                    {iteration.reasoning && (
                      <div
                        className={styles.reasoningBlock}
                      >
                        <span>Reasoning</span>
                        <p>{iteration.reasoning}</p>
                      </div>
                    )}

                    {iteration.validation_notes.length >
                      0 && (
                      <ul className={styles.warningList}>
                        {iteration.validation_notes.map(
                          (note) => (
                            <li key={note}>{note}</li>
                          ),
                        )}
                      </ul>
                    )}
                  </div>
                );
              },
            )}
          </div>
        )}
      </section>

      {/* ================= Legend ================= */}

      <section className={styles.legendPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>政策圖例</strong>
        </div>

        <div className={styles.legendList}>
          <div>
            <span className={styles.redLineLegend} />
            紅線（現況）
          </div>
          <div>
            <span className={styles.redDashLegend} />
            紅線（編輯中）
          </div>
          <div>
            <span className={styles.legendBike}>ⓑ</span>
            UBIKE 站點
          </div>
          <div>
            <span className={styles.legendParking}>P</span>
            停車場
          </div>
          <div>
            <span className={styles.legendTraffic}>🚦</span>
            交通號誌
          </div>
          <div>
            <span className={styles.boundaryLegend} />
            商圈範圍
          </div>
        </div>
      </section>
    </aside>
  );
}
