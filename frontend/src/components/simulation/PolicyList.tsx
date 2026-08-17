import type {
  ScenarioDiffEntry,
  ScenarioDiffType,
} from "@/features/simulation/simulation.types";

import styles from "@/styles/simulation.module.css";

type Props = {
  scenarioName: string;
  entries: ScenarioDiffEntry[];
};

/*
 * 這個清單只顯示 ScenarioDiff。
 *
 * Baseline（道路 / 號誌 / 停車場 / YouBike / 既有紅線）不是政策，
 * 所以初始狀態一定是 0 筆。
 */

function typeIcon(type: ScenarioDiffType) {
  switch (type) {
    case "signal-timing":
      return "🚦";
    case "red-line":
      return "Ⓡ";
    case "parking":
      return "Ⓟ";
    default:
      return "•";
  }
}

function typeLabel(type: ScenarioDiffType) {
  switch (type) {
    case "signal-timing":
      return "號誌";
    case "red-line":
      return "紅線";
    case "parking":
      return "停車";
    default:
      return type;
  }
}

export default function PolicyList({
  scenarioName,
  entries,
}: Props) {
  return (
    <div className={styles.policyList}>
      <div className={styles.policyListHeader}>
        <strong>政策清單（{scenarioName}）</strong>
        <span>{entries.length} 筆政策</span>
      </div>

      {entries.length === 0 ? (
        <div className={styles.policyEmptyState}>
          <strong>目前尚未設定政策</strong>
          <p>請從地圖或工具列新增政策</p>
        </div>
      ) : (
        <div className={styles.policyCards}>
          {entries.map((entry) => (
            <div
              key={entry.id}
              className={styles.policyCard}
            >
              <div className={styles.policyCardTitle}>
                <span>{typeIcon(entry.type)}</span>
                <strong>{entry.title}</strong>
                <em>{typeLabel(entry.type)}</em>
              </div>

              <p>{entry.description}</p>

              <b>
                {entry.baselineLabel}
                {" → "}
                {entry.scenarioLabel}
              </b>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
