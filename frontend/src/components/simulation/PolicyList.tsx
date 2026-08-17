import type {
  ParkingPolicyData,
} from "@/features/simulation/simulation.types";

import styles from "@/styles/simulation.module.css";

type Props = {
  parkingPolicies: ParkingPolicyData[];
};

export default function PolicyList({
  parkingPolicies,
}: Props) {
  const basePolicyCount = 4;

  const totalPolicyCount =
    basePolicyCount + parkingPolicies.length;

  return (
    <div className={styles.policyList}>
      <div className={styles.policyListHeader}>
        <strong>
          政策清單（Scenario A）
        </strong>

        <span>
          {totalPolicyCount} 筆政策
        </span>
      </div>

      <div className={styles.policyCards}>
        {/* 紅線 */}

        <div
          className={`${styles.policyCard} ${styles.selectedPolicyCard}`}
        >
          <div className={styles.policyCardTitle}>
            <span>Ⓡ</span>

            <strong>紅線編輯</strong>

            <em>編輯中</em>
          </div>

          <p>
            市府路
          </p>

          <b className={styles.redText}>
            道路政策
          </b>
        </div>

        {/* YouBike */}

        <div className={styles.policyCard}>
          <div className={styles.policyCardTitle}>
            <span>◎</span>

            <strong>
              新增 YouBike 站點
            </strong>

            <em>新增</em>
          </div>

          <p>
            信義商圈
          </p>

          <b>
            Scenario Policy
          </b>
        </div>

        {/* 停車 */}

        <div className={styles.policyCard}>
          <div className={styles.policyCardTitle}>
            <span>Ⓟ</span>

            <strong>
              停車政策
            </strong>

            <em>設定</em>
          </div>

          <p>
            信義商圈停車設定
          </p>

          <b>
            Scenario Policy
          </b>
        </div>

        {/* 號誌 */}

        <div className={styles.policyCard}>
          <div className={styles.policyCardTitle}>
            <span>🚦</span>

            <strong>
              道路號誌
            </strong>

            <em>設定</em>
          </div>

          <p>
            路口號誌與轉向限制
          </p>

          <b>
            Signal Control
          </b>
        </div>

        {/* =================================================
            使用者新增的停車場
        ================================================= */}

        {parkingPolicies.map((policy) => (
          <div
            key={policy.id}
            className={styles.policyCard}
          >
            <div
              className={
                styles.policyCardTitle
              }
            >
              <span
                style={{
                  color: "#12a866",
                }}
              >
                Ⓟ
              </span>

              <strong>
                新增停車場
              </strong>

              <em>新增</em>
            </div>

            <p>
              {policy.name}
            </p>

            <b>
              汽車車位：
              {policy.spaces} 格
            </b>
          </div>
        ))}

        <button
          type="button"
          className={styles.addPolicyCard}
        >
          ＋ 新增政策
        </button>
      </div>
    </div>
  );
}