import type { ScenarioPolicyData } from "@/features/simulation/simulation.types";
import styles from "@/styles/simulation.module.css";

type Props = {
  scenarioName: string;
  policies: ScenarioPolicyData[];
  canUndo: boolean;
  onUndo: () => void;
  onEditPolicy: (policy: ScenarioPolicyData) => void;
  onDeletePolicy: (policyId: string) => void;
};

function typeLabel(type: ScenarioPolicyData["type"]) {
  switch (type) {
    case "red-line":
      return "紅線";
    case "ubike-add":
      return "UBIKE";
    case "parking-add":
      return "停車場";
    case "parking-remove":
      return "移除";
    case "traffic-control":
      return "管制";
    case "intersection-control":
      return "路口";
    default:
      return type;
  }
}

function statusLabel(status: ScenarioPolicyData["status"]) {
  switch (status) {
    case "active":
      return "啟用中";
    case "editing":
      return "編輯中";
    case "pending-remove":
      return "待移除";
    default:
      return status;
  }
}

export default function PolicyList({
  scenarioName,
  policies,
  canUndo,
  onUndo,
  onEditPolicy,
  onDeletePolicy,
}: Props) {
  return (
    <div className={styles.policyList}>
      <div className={styles.policyListHeader}>
        <strong>政策清單（{scenarioName}）</strong>
        <span>{policies.length} 筆政策</span>
        <button
          type="button"
          className={styles.policyUndoButton}
          disabled={!canUndo}
          onClick={onUndo}
        >
          Undo
        </button>
      </div>

      <div className={styles.policyCards}>
        {policies.map((policy) => (
          <div key={policy.id} className={styles.policyCard}>
            <div className={styles.policyCardTitle}>
              <span>{typeLabel(policy.type)}</span>
              <strong>{policy.title}</strong>
              <em>{statusLabel(policy.status)}</em>
            </div>

            <p>{policy.description}</p>
            <b>
              {Object.entries(policy.params)
                .map(([key, value]) => `${key}: ${value}`)
                .join(" · ")}
            </b>

            <div className={styles.policyCardActions}>
              <button type="button" onClick={() => onEditPolicy(policy)}>
                編輯
              </button>
              <button type="button" onClick={() => onDeletePolicy(policy.id)}>
                刪除
              </button>
            </div>
          </div>
        ))}

        <button className={styles.addPolicyCard} type="button">
          + 新增政策
        </button>
      </div>
    </div>
  );
}
