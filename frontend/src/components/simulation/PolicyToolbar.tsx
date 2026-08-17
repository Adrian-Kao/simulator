import type { PolicyTool } from "@/features/simulation/simulation.types";
import styles from "@/styles/simulation.module.css";

type Props = {
  activeTool: PolicyTool;
  onChangeTool: (tool: PolicyTool) => void;
};

export default function PolicyToolbar({
  activeTool,
  onChangeTool,
}: Props) {
  return (
    <div className={styles.toolbar}>
      <button className={styles.addPolicyButton}>+ 新增政策</button>

      <div className={styles.toolbarDivider} />

      <button
        className={`${styles.toolButton} ${
          activeTool === "red-line" ? styles.activeToolButton : ""
        }`}
        onClick={() => onChangeTool("red-line")}
      >
        紅線編輯
      </button>

      <button
        className={`${styles.toolButton} ${
          activeTool === "youbike" ? styles.activeToolButton : ""
        }`}
        onClick={() => onChangeTool("youbike")}
      >
        新增 UBIKE
      </button>

      <button
        className={`${styles.toolButton} ${
          activeTool === "parking" ? styles.activeToolButton : ""
        }`}
        onClick={() => onChangeTool("parking")}
      >
        新增停車場
      </button>

      <button
        className={`${styles.toolButton} ${
          activeTool === "traffic-control" ? styles.activeToolButton : ""
        }`}
        onClick={() => onChangeTool("traffic-control")}
      >
        道路管制
      </button>

      <button
        className={`${styles.toolButton} ${
          activeTool === "intersection" ? styles.activeToolButton : ""
        }`}
        onClick={() => onChangeTool("intersection")}
      >
        路口設定
      </button>

      <div className={styles.toolbarDivider} />

      <button className={styles.toolButton}>匯入方案</button>
    </div>
  );
}
