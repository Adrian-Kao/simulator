import type {
  SimulationApiResult,
  SimulationStatus,
} from "@/lib/simulation-api";

import styles from "@/styles/simulation.module.css";

type Props = {
  simulationStatus: SimulationStatus;
  simulationResult: SimulationApiResult | null;
  simulationError: string | null;
  onRunSimulation: () => void;
};

const goals = [
  {
    icon: "⏱",
    title: "Travel Time",
    subtitle: "平均旅行時間",
    value: "降低 10%",
  },
  {
    icon: "🚗",
    title: "Travel Speed",
    subtitle: "平均旅行速度",
    value: "提升 8%",
  },
  {
    icon: "⚙",
    title: "壅塞程度",
    subtitle: "路段壅塞指數",
    value: "降低 15%",
  },
  {
    icon: "🚲",
    title: "UBIKE 使用率",
    subtitle: "站點使用率",
    value: "提升 10%",
  },
];

function formatNumber(
  value: number,
  digits = 2,
) {
  return Number.isFinite(value)
    ? value.toFixed(digits)
    : "-";
}

function formatDelta(
  value: number,
) {
  if (!Number.isFinite(value)) {
    return "-";
  }

  const prefix = value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}%`;
}

export default function GoalPanel({
  simulationStatus,
  simulationResult,
  simulationError,
  onRunSimulation,
}: Props) {
  return (
    <aside className={styles.rightSidebar}>
      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>Python Simulation</strong>

          <button
            type="button"
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
          <div className={styles.tipBox}>
            先用目前 Scenario 呼叫 Python FastAPI。
            第一版先驗證號誌秒數真的會影響 Queue KPI。
          </div>
        )}

        {simulationStatus === "error" && (
          <div className={styles.tipBox}>
            API 錯誤：
            {simulationError ??
              "Unknown error"}
          </div>
        )}

        {simulationResult && (
          <div className={styles.goalList}>
            <div className={styles.goalCard}>
              <div className={styles.goalIcon}>⏱</div>
              <div className={styles.goalText}>
                <strong>Travel Time</strong>
                <small>
                  baseline → scenario
                </small>
              </div>
              <div className={styles.goalValue}>
                {formatNumber(
                  simulationResult.baseline
                    .travel_time_minutes,
                )}
                {" → "}
                {formatNumber(
                  simulationResult.scenario
                    .travel_time_minutes,
                )}
                {" min "}
                {formatDelta(
                  simulationResult.delta
                    .travel_time_percent,
                )}
              </div>
            </div>

            <div className={styles.goalCard}>
              <div className={styles.goalIcon}>🚗</div>
              <div className={styles.goalText}>
                <strong>Travel Speed</strong>
                <small>
                  baseline → scenario
                </small>
              </div>
              <div className={styles.goalValue}>
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
                {" km/h "}
                {formatDelta(
                  simulationResult.delta
                    .travel_speed_percent,
                )}
              </div>
            </div>

            <div className={styles.goalCard}>
              <div className={styles.goalIcon}>⚙</div>
              <div className={styles.goalText}>
                <strong>V/C</strong>
                <small>
                  baseline → scenario
                </small>
              </div>
              <div className={styles.goalValue}>
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
            </div>

            <div className={styles.goalCard}>
              <div className={styles.goalIcon}>🚦</div>
              <div className={styles.goalText}>
                <strong>Queue</strong>
                <small>
                  baseline → scenario
                </small>
              </div>
              <div className={styles.goalValue}>
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
                {" 輛 "}
                {formatDelta(
                  simulationResult.delta
                    .queue_percent,
                )}
              </div>
            </div>

            <div className={styles.tipBox}>
              建議：
              {simulationResult.recommended}
              {simulationResult.warnings.length > 0
                ? ` · ${simulationResult.warnings[0]}`
                : ""}
            </div>
          </div>
        )}
      </section>

      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>情境目標設定</strong>
          <button type="button">
            編輯
          </button>
        </div>

        <div className={styles.goalList}>
          {goals.map((goal) => (
            <div
              className={styles.goalCard}
              key={goal.title}
            >
              <div className={styles.goalIcon}>
                {goal.icon}
              </div>
              <div className={styles.goalText}>
                <strong>
                  {goal.title}
                </strong>
                <small>
                  {goal.subtitle}
                </small>
              </div>
              <div className={styles.goalValue}>
                {goal.value}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.legendPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>政策圖例</strong>
          <button type="button">
            編輯
          </button>
        </div>

        <div className={styles.legendList}>
          <div>
            <span
              className={styles.redLineLegend}
            />
            紅線（現況）
          </div>
          <div>
            <span
              className={styles.redDashLegend}
            />
            紅線（編輯中）
          </div>
          <div>
            <span
              className={styles.legendBike}
            >
              ⓑ
            </span>
            UBIKE 站點
          </div>
          <div>
            <span
              className={styles.legendParking}
            >
              P
            </span>
            停車場
          </div>
          <div>
            <span
              className={styles.legendTraffic}
            >
              🚦
            </span>
            交通號誌
          </div>
          <div>
            <span
              className={styles.boundaryLegend}
            />
            商圈範圍
          </div>
        </div>
      </section>
    </aside>
  );
}