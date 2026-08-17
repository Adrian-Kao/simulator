import styles from "@/styles/simulation.module.css";

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

export default function GoalPanel() {
  return (
    <aside className={styles.rightSidebar}>
      <section className={styles.goalPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>情境目標設定</strong>
          <button type="button">編輯</button>
        </div>

        <div className={styles.goalList}>
          {goals.map((goal) => (
            <div className={styles.goalCard} key={goal.title}>
              <div className={styles.goalIcon}>{goal.icon}</div>
              <div className={styles.goalText}>
                <strong>{goal.title}</strong>
                <small>{goal.subtitle}</small>
              </div>
              <div className={styles.goalValue}>{goal.value}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.legendPanel}>
        <div className={styles.rightPanelHeader}>
          <strong>政策圖例</strong>
          <button type="button">編輯</button>
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
