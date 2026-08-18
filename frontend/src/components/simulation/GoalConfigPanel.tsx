"use client";

import type {
  GoalConfig,
  GoalMetric,
} from "@/features/simulation/simulation.types";

import styles from "@/styles/simulation.module.css";

type Props = {
  goals: GoalConfig;

  onChangeGoal: (
    metric: GoalMetric,
    value: number | null,
  ) => void;
};

const GOAL_ROWS: {
  metric: GoalMetric;
  icon: string;
  label: string;
  subtitle: string;
}[] = [
  {
    metric: "travel_time_percent",
    icon: "",
    label: "Travel Time",
    subtitle: "平均旅行時間",
  },
  {
    metric: "travel_speed_percent",
    icon: "",
    label: "Travel Speed",
    subtitle: "平均旅行速度",
  },
  {
    metric: "congestion_vc_percent",
    icon: "",
    label: "V/C",
    subtitle: "道路壅塞程度",
  },
  {
    metric: "queue_percent",
    icon: "",
    label: "Queue",
    subtitle: "排隊車輛",
  },
];

export default function GoalConfigPanel({
  goals,
  onChangeGoal,
}: Props) {
  return (
    <aside className={styles.goalSidebar}>
      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <div>
            <strong>情境目標設定</strong>

            <div className={styles.goalHeaderSubtitle}>
              Scenario Goal
            </div>
          </div>

          <span className={styles.goalHint}>
            相對 Baseline
          </span>
        </div>

        <div className={styles.goalConfigIntro}>
          設定希望政策模擬達成的 KPI 改善幅度。
        </div>

        <div className={styles.goalList}>
          {GOAL_ROWS.map((row) => {
            const value =
              goals[row.metric];

            return (
              <div
                key={row.metric}
                className={styles.goalConfigCard}
              >
                <div
                  className={
                    styles.goalConfigCardHeader
                  }
                >
                  <span
                    className={
                      styles.goalConfigIcon
                    }
                  >
                    {row.icon}
                  </span>

                  <div>
                    <strong>
                      {row.label}
                    </strong>

                    <small>
                      {row.subtitle}
                    </small>
                  </div>
                </div>

                <div
                  className={
                    styles.goalInputRow
                  }
                >
                  <input
                    type="number"
                    step={1}
                    className={
                      styles.goalInput
                    }
                    value={value ?? ""}
                    placeholder="未設定"
                    onChange={(event) => {
                      const raw =
                        event.target.value;

                      onChangeGoal(
                        row.metric,
                        raw === ""
                          ? null
                          : Number(raw),
                      );
                    }}
                  />

                  <span>%</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className={styles.goalDirectionHint}>
          <div>
            <b>負值</b>
            <span>希望下降</span>
          </div>

          <div>
            <b>正值</b>
            <span>希望上升</span>
          </div>
        </div>

        <div className={styles.tipBox}>
          例如 Travel Time 設為 -10，
          表示希望平均旅行時間至少降低 10%。
        </div>
      </section>
    </aside>
  );
}