import { useMemo, useState } from "react";

import type {
  CurbSide,
  IntersectionData,
  ParkingDraft,
  PolicyTool,
  RedLinePolicyData,
  RoadSegmentData,
  ScenarioPolicyData,
  TurnRestrictionType,
} from "@/features/simulation/simulation.types";

import styles from "@/styles/simulation.module.css";

type Props = {
  selectedRoad: RoadSegmentData | null;
  selectedIntersection: IntersectionData | null;
  activeTool: PolicyTool;
  roads: RoadSegmentData[];
  parkingDraft: ParkingDraft | null;
  redLineDraft: RedLinePolicyData | null;
  selectedPolicy: ScenarioPolicyData | null;
  onUpdateParkingDraft: (
    patch: Partial<ParkingDraft>,
  ) => void;
  onCancelParking: () => void;
  onConfirmParking: () => void;
  onCreateRedLine: () => void;
  onUpdateRedLineDraft: (
    patch: Partial<RedLinePolicyData>,
  ) => void;
  onCancelRedLine: () => void;
  onApplyRedLine: () => void;
  onUpdateIntersectionPhase: (
    intersectionId: string,
    phaseIndex: number,
    seconds: number,
  ) => void;
  onAddIntersectionRestriction: (
    intersectionId: string,
    type: TurnRestrictionType,
    targetRoadId: string,
  ) => void;
  onRemoveIntersectionRestriction: (
    intersectionId: string,
    restrictionId: string,
  ) => void;
  onSaveIntersection: () => void;
  onResetRoad: (roadId: string) => void;
};

function statusLabel(
  status?: ScenarioPolicyData["status"],
) {
  switch (status) {
    case "active":
      return "啟用中";
    case "editing":
      return "編輯中";
    case "pending-remove":
      return "待移除";
    default:
      return "未加入";
  }
}

function restrictionLabel(
  type: TurnRestrictionType,
) {
  switch (type) {
    case "forbid-right-turn":
      return "禁止右轉";
    case "forbid-left-turn":
      return "禁止左轉";
    case "forbid-entry":
      return "禁止進入";
    default:
      return type;
  }
}

export default function LeftSidebar({
  selectedRoad,
  selectedIntersection,
  activeTool,
  roads,
  parkingDraft,
  redLineDraft,
  selectedPolicy,
  onUpdateParkingDraft,
  onCancelParking,
  onConfirmParking,
  onCreateRedLine,
  onUpdateRedLineDraft,
  onCancelRedLine,
  onApplyRedLine,
  onUpdateIntersectionPhase,
  onAddIntersectionRestriction,
  onRemoveIntersectionRestriction,
  onSaveIntersection,
  onResetRoad,
}: Props) {
  const [
    newRestrictionType,
    setNewRestrictionType,
  ] =
    useState<TurnRestrictionType>(
      "forbid-right-turn",
    );

  const [
    newRestrictionTarget,
    setNewRestrictionTarget,
  ] = useState<string>("");

  const intersectionTargets =
    useMemo(() => {
      if (!selectedIntersection) {
        return roads;
      }

      const connected =
        selectedIntersection.connectedRoadIds
          .map((roadId) =>
            roads.find(
              (road) =>
                road.id === roadId,
            ),
          )
          .filter(
            (
              road,
            ): road is RoadSegmentData =>
              Boolean(road),
          );

      return connected.length > 0
        ? connected
        : roads;
    }, [roads, selectedIntersection]);

  const activeStatus = statusLabel(
    selectedPolicy?.status,
  );

  if (activeTool === "parking") {
    return (
      <aside
        className={styles.leftSidebar}
      >
        <div
          className={styles.panelHeader}
        >
          <strong>新增停車場</strong>
          <span
            className={styles.statusBadge}
          >
            佈點中
          </span>
        </div>

        {!parkingDraft ? (
          <div
            className={
              styles.parkingEmptyState
            }
          >
            <div
              className={
                styles.parkingBigIcon
              }
            >
              P
            </div>
            <h2>
              請在地圖上點選位置
            </h2>
            <p>
              先放置停車場，再回來設定名稱、車位數與費率。
              <br />
              這個版面會跟著 Scenario 即時更新。
            </p>
            <div
              className={styles.tipBox}
            >
              在地圖上點一下就能建立候選停車場，右側清單會同步加入 Scenario Data。
            </div>
          </div>
        ) : (
          <>
            <div
              className={
                styles.sidebarSection
              }
            >
              <div
                className={
                  styles.parkingSelectedTitle
                }
              >
                <div
                  className={
                    styles.newParkingIcon
                  }
                >
                  P
                </div>
                <div>
                  <h2>
                    {parkingDraft.name}
                  </h2>
                  <p>
                    X{" "}
                    {Math.round(
                      parkingDraft.x,
                    )}{" "}
                    / Y{" "}
                    {Math.round(
                      parkingDraft.y,
                    )}
                  </p>
                </div>
              </div>
            </div>

            <div
              className={
                styles.sidebarSection
              }
            >
              <h3>停車場資訊</h3>

              <label
                className={
                  styles.fieldLabel
                }
              >
                停車場名稱
              </label>
              <input
                type="text"
                className={
                  styles.formControl
                }
                value={
                  parkingDraft.name
                }
                onChange={(event) =>
                  onUpdateParkingDraft({
                    name:
                      event.target
                        .value,
                  })
                }
              />

              <label
                className={
                  styles.fieldLabel
                }
              >
                車位數
              </label>
              <input
                type="number"
                min={1}
                max={9999}
                className={
                  styles.formControl
                }
                value={
                  parkingDraft.spaces
                }
                onChange={(event) =>
                  onUpdateParkingDraft({
                    spaces: Math.max(
                      1,
                      Number(
                        event.target
                          .value,
                      ),
                    ),
                  })
                }
              />

              <div
                className={
                  styles.parkingCoordinate
                }
              >
                <span>座標</span>
                <strong>
                  {Math.round(
                    parkingDraft.x,
                  )}
                  ,{" "}
                  {Math.round(
                    parkingDraft.y,
                  )}
                </strong>
              </div>
            </div>

            <div
              className={
                styles.sidebarSection
              }
            >
              <h3>Scenario 狀態</h3>
              <div
                className={
                  styles.infoLabel
                }
              >
                目前狀態
              </div>
              <div
                className={
                  styles.lengthValue
                }
              >
                佈點
                <span>中</span>
              </div>

              <div
                className={
                  styles.sidebarActions
                }
              >
                <button
                  type="button"
                  className={
                    styles.cancelButton
                  }
                  onClick={
                    onCancelParking
                  }
                >
                  取消
                </button>
                <button
                  type="button"
                  className={
                    styles.applyButton
                  }
                  onClick={
                    onConfirmParking
                  }
                >
                  加入 Scenario
                </button>
              </div>
            </div>

            <div
              className={
                styles.sidebarHint
              }
            >
              這個停車場會同步進到 Scenario Data 與底部政策清單。
            </div>
          </>
        )}
      </aside>
    );
  }

  if (selectedIntersection) {
    return (
      <aside
        className={styles.leftSidebar}
      >
        <div
          className={styles.panelHeader}
        >
          <strong>
            Intersection Focus
          </strong>
          <span
            className={styles.statusBadge}
          >
            {activeStatus}
          </span>
        </div>

        <div
          className={
            styles.sidebarSection
          }
        >
          <div
            className={
              styles.selectedRoadTitle
            }
          >
            <span
              className={styles.roadIcon}
            >
              ◎
            </span>
            <div>
              <h2>
                {
                  selectedIntersection.name
                }
              </h2>
              <p>
                連接{" "}
                {
                  selectedIntersection
                    .connectedRoadIds
                    .length
                }{" "}
                條道路
              </p>
            </div>
          </div>
        </div>

        <div
          className={
            styles.sidebarSection
          }
        >
          <h3>
            紅綠燈 Phase / 秒數
          </h3>

          {selectedIntersection.phases.map(
            (phase, index) => (
              <div
                key={`${selectedIntersection.id}-${phase.name}`}
              >
                <label
                  className={
                    styles.fieldLabel
                  }
                >
                  {phase.name}
                </label>

                <div
                  className={
                    styles.timeRow
                  }
                >
                  <input
                    type="number"
                    min={1}
                    className={
                      styles.timeInput
                    }
                    value={
                      phase.seconds
                    }
                    onChange={(
                      event,
                    ) =>
                      onUpdateIntersectionPhase(
                        selectedIntersection.id,
                        index,
                        Number(
                          event.target
                            .value,
                        ),
                      )
                    }
                  />
                  <span>秒</span>
                  <div
                    className={
                      styles.infoLabel
                    }
                  >
                    {phase.color}
                  </div>
                </div>
              </div>
            ),
          )}
        </div>

        <div
          className={
            styles.sidebarSection
          }
        >
          <h3>
            禁止右轉 / 左轉 / 進入
          </h3>

          {selectedIntersection
            .restrictions.length ===
          0 ? (
            <div
              className={styles.tipBox}
            >
              目前沒有套用任何轉向或進入限制。
            </div>
          ) : (
            <div
              className={
                styles.intersectionRestrictionList
              }
            >
              {selectedIntersection.restrictions.map(
                (restriction) => {
                  const road =
                    roads.find(
                      (item) =>
                        item.id ===
                        restriction.targetRoadId,
                    );

                  return (
                    <div
                      key={
                        restriction.id
                      }
                      className={
                        styles.intersectionRestrictionRow
                      }
                    >
                      <div>
                        <strong>
                          {restrictionLabel(
                            restriction.type,
                          )}
                        </strong>
                        <p>
                          {road?.roadName ??
                            restriction.targetRoadId}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() =>
                          onRemoveIntersectionRestriction(
                            selectedIntersection.id,
                            restriction.id,
                          )
                        }
                      >
                        刪除
                      </button>
                    </div>
                  );
                },
              )}
            </div>
          )}

          <label
            className={styles.fieldLabel}
          >
            新增限制類型
          </label>

          <select
            className={styles.formControl}
            value={newRestrictionType}
            onChange={(event) =>
              setNewRestrictionType(
                event.target
                  .value as TurnRestrictionType,
              )
            }
          >
            <option value="forbid-right-turn">
              禁止右轉
            </option>
            <option value="forbid-left-turn">
              禁止左轉
            </option>
            <option value="forbid-entry">
              禁止進入
            </option>
          </select>

          <label
            className={styles.fieldLabel}
          >
            目標路段
          </label>

          <select
            className={styles.formControl}
            value={
              newRestrictionTarget ||
              intersectionTargets[0]
                ?.id ||
              ""
            }
            onChange={(event) =>
              setNewRestrictionTarget(
                event.target.value,
              )
            }
          >
            {intersectionTargets.map(
              (road) => (
                <option
                  key={road.id}
                  value={road.id}
                >
                  {road.roadName}
                </option>
              ),
            )}
          </select>

          <div
            className={
              styles.sidebarActions
            }
          >
            <button
              type="button"
              className={
                styles.cancelButton
              }
              onClick={() =>
                onAddIntersectionRestriction(
                  selectedIntersection.id,
                  newRestrictionType,
                  newRestrictionTarget ||
                    intersectionTargets[0]
                      ?.id ||
                    "",
                )
              }
            >
              加入限制
            </button>

            <button
              type="button"
              className={
                styles.applyButton
              }
              onClick={
                onSaveIntersection
              }
            >
              套用變更
            </button>
          </div>
        </div>
      </aside>
    );
  }

  if (!selectedRoad) {
    return (
      <aside
        className={styles.leftSidebar}
      >
        <div
          className={styles.panelHeader}
        >
          <strong>商圈編輯</strong>
          <span
            className={styles.statusBadge}
          >
            待選取
          </span>
        </div>

        <div
          className={
            styles.emptyRoadState
          }
        >
          <div
            className={
              styles.bigRoadIcon
            }
          >
            ☰
          </div>
          <h2>
            請從地圖上點選路段或路口
          </h2>
          <p>
            選取道路後可編輯左右 curb 紅線；
            <br />
            點選路口則可調整相位與轉向限制。
          </p>
          <div
            className={styles.tipBox}
          >
            Road Focus 內的紅線會以 curb 起點 / 終點 offset 儲存，不會再修改道路中心線。
          </div>
        </div>
      </aside>
    );
  }

  return (
    <aside className={styles.leftSidebar}>
      <div className={styles.panelHeader}>
        <strong>
          {activeTool === "red-line"
            ? "紅線編輯"
            : "路段設定"}
        </strong>
        <span
          className={styles.statusBadge}
        >
          {redLineDraft
            ? "編輯中"
            : activeStatus}
        </span>
      </div>

      <div
        className={styles.sidebarSection}
      >
        <div
          className={
            styles.selectedRoadTitle
          }
        >
          <span
            className={styles.roadIcon}
          >
            ▥
          </span>
          <div>
            <h2>
              {selectedRoad.roadName}
            </h2>
            <p>
              {selectedRoad.from} -{" "}
              {selectedRoad.to}
            </p>
          </div>
        </div>
      </div>

      {activeTool === "red-line" && (
        <div
          className={
            styles.sidebarSection
          }
        >
          <h3>curb 紅線區段</h3>

          {!redLineDraft ? (
            <>
              <div
                className={styles.tipBox}
              >
                目前沒有正在編輯的紅線。建立後可在地圖直接拖曳紅色起點與終點。
              </div>

              <div
                className={
                  styles.sidebarActions
                }
              >
                <button
                  type="button"
                  className={
                    styles.applyButton
                  }
                  onClick={
                    onCreateRedLine
                  }
                >
                  建立新紅線區段
                </button>
              </div>
            </>
          ) : (
            <>
              <label
                className={
                  styles.fieldLabel
                }
              >
                curb 側別
              </label>

              <select
                className={
                  styles.formControl
                }
                value={
                  redLineDraft.side
                }
                onChange={(event) =>
                  onUpdateRedLineDraft({
                    side:
                      event.target
                        .value as CurbSide,
                  })
                }
              >
                <option value="left">
                  左側 curb
                </option>
                <option value="right">
                  右側 curb
                </option>
              </select>

              <label
                className={
                  styles.fieldLabel
                }
              >
                起點位置
              </label>

              <div
                className={styles.timeRow}
              >
                <input
                  type="number"
                  min={0}
                  max={100}
                  className={
                    styles.timeInput
                  }
                  value={Math.round(
                    redLineDraft.startOffset *
                      100,
                  )}
                  onChange={(event) =>
                    onUpdateRedLineDraft({
                      startOffset:
                        Number(
                          event.target
                            .value,
                        ) / 100,
                    })
                  }
                />
                <span>%</span>
              </div>

              <label
                className={
                  styles.fieldLabel
                }
              >
                終點位置
              </label>

              <div
                className={styles.timeRow}
              >
                <input
                  type="number"
                  min={0}
                  max={100}
                  className={
                    styles.timeInput
                  }
                  value={Math.round(
                    redLineDraft.endOffset *
                      100,
                  )}
                  onChange={(event) =>
                    onUpdateRedLineDraft({
                      endOffset:
                        Number(
                          event.target
                            .value,
                        ) / 100,
                    })
                  }
                />
                <span>%</span>
              </div>

              <div
                className={
                  styles.infoLabel
                }
              >
                紅線長度
              </div>

              <div
                className={
                  styles.lengthValue
                }
              >
                {
                  redLineDraft.lengthMeters
                }
                <span> m</span>
              </div>

              <label
                className={
                  styles.fieldLabel
                }
              >
                生效時間
              </label>

              <div
                className={styles.timeRow}
              >
                <input
                  type="time"
                  className={
                    styles.timeInput
                  }
                  value={
                    redLineDraft.startTime ??
                    "00:00"
                  }
                  onChange={(event) =>
                    onUpdateRedLineDraft({
                      startTime:
                        event.target
                          .value,
                    })
                  }
                />

                <span>至</span>

                <input
                  type="time"
                  className={
                    styles.timeInput
                  }
                  value={
                    redLineDraft.endTime ??
                    "23:59"
                  }
                  onChange={(event) =>
                    onUpdateRedLineDraft({
                      endTime:
                        event.target
                          .value,
                    })
                  }
                />
              </div>

              <div
                className={
                  styles.sidebarActions
                }
              >
                <button
                  type="button"
                  className={
                    styles.cancelButton
                  }
                  onClick={
                    onCancelRedLine
                  }
                >
                  取消
                </button>

                <button
                  type="button"
                  className={
                    styles.applyButton
                  }
                  onClick={
                    onApplyRedLine
                  }
                >
                  加入 Scenario
                </button>
              </div>

              <div
                className={styles.tipBox}
              >
                地圖紅色圓點就是紅線起點與終點。也可以直接點 curb，把距離最近的端點移到該位置。
              </div>
            </>
          )}
        </div>
      )}

      <div
        className={styles.sidebarSection}
      >
        <h3>路段資訊</h3>

        <div
          className={styles.infoLabel}
        >
          路段長度
        </div>

        <div
          className={styles.lengthValue}
        >
          {selectedRoad.lengthMeters ??
            "—"}
          <span> m</span>
        </div>

        <div
          className={styles.infoLabel}
        >
          {selectedRoad.direction ===
          "two-way"
            ? "雙向道路"
            : "單向道路"}
        </div>

        <div
          className={styles.infoLabel}
        >
          左 curb / 右 curb：
          {selectedRoad.curb?.left
            .length ??
            selectedRoad.points.length}{" "}
          /{" "}
          {selectedRoad.curb?.right
            .length ??
            selectedRoad.points.length}
        </div>
      </div>

      <div
        className={styles.sidebarSection}
      >
        <h3>轉向限制</h3>

        {selectedRoad.turnRestrictions
          ?.length ? (
          <div
            className={
              styles.intersectionRestrictionList
            }
          >
            {selectedRoad.turnRestrictions.map(
              (restriction) => {
                const road =
                  roads.find(
                    (item) =>
                      item.id ===
                      restriction.targetRoadId,
                  );

                return (
                  <div
                    key={
                      restriction.id
                    }
                    className={
                      styles.intersectionRestrictionRow
                    }
                  >
                    <div>
                      <strong>
                        {restrictionLabel(
                          restriction.type,
                        )}
                      </strong>
                      <p>
                        {road?.roadName ??
                          restriction.targetRoadId}
                      </p>
                    </div>
                    <span>
                      {restriction.note}
                    </span>
                  </div>
                );
              },
            )}
          </div>
        ) : (
          <div
            className={styles.tipBox}
          >
            這條路目前沒有額外的轉向限制。
          </div>
        )}
      </div>

      <div
        className={styles.sidebarSection}
      >
        <h3>路段操作</h3>

        <div
          className={
            styles.sidebarActions
          }
        >
          <button
            type="button"
            className={
              styles.cancelButton
            }
            onClick={() =>
              onResetRoad(
                selectedRoad.id,
              )
            }
          >
            還原路段
          </button>
        </div>
      </div>

      <div
        className={styles.sidebarHint}
      >
        紅線現在綁定 road.curb.left / road.curb.right，Scenario 儲存的是 side、startOffset、endOffset、lengthMeters 與生效時間。
      </div>
    </aside>
  );
}
