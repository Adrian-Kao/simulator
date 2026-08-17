import type {
  ParkingPolicyData,
  RedLinePolicyData,
  RoadSegmentData,
} from "@/features/simulation/simulation.types";

import styles from "@/styles/simulation.module.css";

type Props = {
  parkingPolicies: ParkingPolicyData[];
  redLinePolicies: RedLinePolicyData[];
  roads: RoadSegmentData[];
};

export default function PolicyList({
  parkingPolicies,
  redLinePolicies,
  roads,
}: Props) {
  const basePolicyCount = 3;

  const totalPolicyCount =
    basePolicyCount +
    parkingPolicies.length +
    redLinePolicies.length;

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
        {redLinePolicies.length === 0 ? (
          <div
            className={`${styles.policyCard} ${styles.selectedPolicyCard}`}
          >
            <div className={styles.policyCardTitle}>
              <span>Ⓡ</span>
              <strong>紅線政策</strong>
              <em>尚未建立</em>
            </div>

            <p>
              選取道路後可建立實際 curb 紅線區段
            </p>

            <b className={styles.redText}>
              Road Curb Policy
            </b>
          </div>
        ) : (
          redLinePolicies.map((policy) => {
            const road =
              roads.find(
                (item) =>
                  item.id === policy.roadId,
              ) ?? null;

            return (
              <div
                key={policy.id}
                className={styles.policyCard}
              >
                <div
                  className={
                    styles.policyCardTitle
                  }
                >
                  <span>Ⓡ</span>
                  <strong>紅線政策</strong>
                  <em>已套用</em>
                </div>

                <p>
                  {road?.roadName ??
                    policy.roadId}
                  {" · "}
                  {policy.side === "left"
                    ? "左側 curb"
                    : "右側 curb"}
                </p>

                <b
                  className={
                    styles.redText
                  }
                >
                  {policy.lengthMeters} m
                  {policy.startTime &&
                  policy.endTime
                    ? ` · ${policy.startTime}-${policy.endTime}`
                    : ""}
                </b>
              </div>
            );
          })
        )}

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
