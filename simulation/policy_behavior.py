"""Deterministic policy-to-behaviour and downstream-impact model.

This module closes the loop between infrastructure policies and human agents:
policies change perceived mode costs, agents choose again, and their aggregate
choices become demand signals for traffic and longer-term planning.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List

from .commuter import CommuterAgent, CommuterProfile, ModeAlternative
from .visitor import VisitorAgent, VisitorProfile


@dataclass(frozen=True)
class ModeContext:
    drive_time: float = 14.0
    drive_cost: float = 45.0
    drive_walk: float = 3.0
    drive_available: float = 1.0
    transit_time: float = 18.0
    transit_cost: float = 20.0
    transit_walk: float = 4.0
    youbike_time: float = 16.0
    youbike_walk: float = 4.0
    youbike_available: float = 1.0


def policy_mode_context(policies: Iterable[object], green_seconds: int) -> ModeContext:
    """Translate policy payloads into costs perceived by human agents."""
    policy_list = list(policies)
    has_signal_policy = any(
        getattr(policy, "type", None) == "signal-timing"
        for policy in policy_list
    )
    drive_time = 14.0
    if has_signal_policy:
        drive_time += (40 - green_seconds) * 0.15
    drive_cost = 45.0
    drive_walk = 3.0
    drive_available = 1.0

    red_line_metres = sum(
        float(getattr(policy, "length_meters", 0) or 0)
        for policy in policy_list
        if getattr(policy, "type", None) == "red-line"
    )
    # Clear curb friction, but make door-to-door car access less convenient.
    drive_time -= min(red_line_metres / 250.0, 2.0)
    drive_walk += min(red_line_metres / 150.0, 4.0)

    added_spaces = sum(
        int(getattr(policy, "spaces", 0) or 0)
        for policy in policy_list
        if getattr(policy, "type", None) == "parking"
    )
    if added_spaces:
        drive_cost = max(25.0, drive_cost - added_spaces * 0.08)
        drive_walk = max(1.0, drive_walk - added_spaces / 100.0)

    restrictions = [
        policy for policy in policy_list
        if getattr(policy, "type", None) == "traffic-restriction"
    ]
    # A restricted movement represents a detour plus route uncertainty. Eight
    # minutes is intentionally large enough for some marginal agents to
    # reconsider their mode instead of changing only an invisible score.
    drive_time += 8.0 * len(restrictions)
    if any(getattr(policy, "restriction_type", None) == "forbid-entry" for policy in restrictions):
        drive_available = 0.0

    return ModeContext(
        drive_time=max(1.0, drive_time),
        drive_cost=drive_cost,
        drive_walk=drive_walk,
        drive_available=drive_available,
    )


def evaluate_population(context: ModeContext) -> Dict[str, float]:
    """Run a stable mixed commuter/visitor population and return person shares."""
    counts = {"drive": 0, "transit": 0, "youbike": 0}
    commuter_agent = CommuterAgent()
    visitor_agent = VisitorAgent()

    for index in range(70):
        profile = CommuterProfile(
            commuter_id=f"api-c{index}",
            origin_segment_id="origin",
            destination_segment_id="destination",
            preferred_departure="17:30",
            value_of_time=2.0 + (index % 6),
            price_sensitivity=0.5 + (index % 4) * 0.4,
            transit_preference=(index % 5) * 0.18,
        )
        choice = commuter_agent.choose_mode(profile, _alternatives(context))
        counts[choice.mode] += 1

    # Twelve visitor groups with repeating sizes 1–4 represent 30 people,
    # keeping the combined population at exactly 100 people.
    for index in range(12):
        group_size = 1 + index % 4
        profile = VisitorProfile(
            visitor_id=f"api-v{index}",
            origin_segment_id="origin",
            destination_segment_id="destination",
            preferred_departure="17:30",
            group_size=group_size,
            stay_duration_hours=1.0 + index % 4,
            value_of_time=3.0 + index % 5,
            price_sensitivity=0.7 + (index % 3) * 0.4,
            walk_penalty_multiplier=1.2 + (index % 4) * 0.3,
            transit_preference=(index % 4) * 0.2,
        )
        alternatives = _alternatives(
            context,
            youbike_available=(
                context.youbike_available if group_size <= 2 else 0.0
            ),
        )
        choice = visitor_agent.choose_mode(profile, alternatives)
        counts[choice.mode] += group_size

    population = float(sum(counts.values()))
    return {mode: count / population for mode, count in counts.items()}


def development_signals(
    baseline: Dict[str, float],
    scenario: Dict[str, float],
) -> List[str]:
    """Convert sustained demand shifts into explicit next-stage signals."""
    signals: List[str] = []
    drive_delta = scenario["drive"] - baseline["drive"]
    transit_delta = scenario["transit"] - baseline["transit"]
    bike_delta = scenario["youbike"] - baseline["youbike"]

    if drive_delta <= -0.03:
        signals.append("停車需求下降，可評估將路邊空間轉為步行或公共設施")
    elif drive_delta >= 0.03:
        signals.append("停車與接送需求上升，後續開發需預留交通管理容量")
    if transit_delta >= 0.03:
        signals.append("大眾運輸負荷上升，應評估班距與轉乘容量")
    if bike_delta >= 0.03:
        signals.append("YouBike 需求上升，應評估增設車柱與調度資源")
    if not signals:
        signals.append("運具選擇變化有限，暫不觸發新的設施開發需求")
    return signals


def _alternatives(
    context: ModeContext,
    youbike_available: float = 1.0,
) -> List[ModeAlternative]:
    return [
        ModeAlternative(
            "drive", context.drive_time, context.drive_cost,
            walk_time_minutes=context.drive_walk,
            availability=context.drive_available,
        ),
        ModeAlternative(
            "transit", context.transit_time, context.transit_cost,
            walk_time_minutes=context.transit_walk,
        ),
        ModeAlternative(
            "youbike", context.youbike_time, 0.0,
            walk_time_minutes=context.youbike_walk,
            availability=min(context.youbike_available, youbike_available),
        ),
    ]
