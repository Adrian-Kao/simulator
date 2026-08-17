import styles from "@/styles/simulation.module.css";

export default function SimulationHeader() {
  return (
    <>
      <header className={styles.header}>
        <div className={styles.brandArea}>
          <div className={styles.logoMark}>▣</div>

          <div>
            <div className={styles.brandTitle}>商圈政策沙盒模擬</div>
            <span className={styles.brandSubtitle}>政策編輯與情境設定</span>
          </div>
        </div>

        <div className={styles.headerActions}>
          <select className={styles.scenarioSelect} defaultValue="Scenario A">
            <option>Scenario A</option>
            <option>Scenario B</option>
            <option>Scenario C</option>
          </select>

          <span className={styles.savedText}>最後儲存：今天 10:30</span>

          <button className={styles.secondaryButton}>儲存情境</button>
          <button className={styles.primaryButton}>開始模擬</button>
          <button className={styles.iconButton}>⋯</button>
        </div>
      </header>

      <nav className={styles.tabs}>
        <button className={`${styles.tab} ${styles.activeTab}`}>道路</button>
        <button className={styles.tab}>UBIKE</button>
        <button className={styles.tab}>個人交通運輸</button>
        <button className={styles.tab}>情境目標</button>
      </nav>
    </>
  );
}
