from __future__ import annotations

import math
from statistics import mean


def _erlang_c(offered_load: float, servers: int) -> float:
    """Numerically stable Erlang-C delay probability via Erlang-B recursion."""
    if offered_load <= 0 or servers <= 0:
        return 0.0
    utilization = offered_load / servers
    if utilization >= 1:
        return 1.0
    erlang_b = 1.0
    for server in range(1, servers + 1):
        erlang_b = offered_load * erlang_b / (server + offered_load * erlang_b)
    return erlang_b / (1 - utilization + utilization * erlang_b)


def build_queue_plan(
    forecast_sessions: list[float],
    counselor_count: int,
    daily_slot_capacity: float,
    current_waitlist: int,
) -> dict[str, float | int | str | None]:
    arrival_rate = mean(forecast_sessions) if forecast_sessions else 0.0
    planning_horizon_days = max(1, len(forecast_sessions))
    backlog = max(0, current_waitlist)
    capacity = max(0.0, daily_slot_capacity)
    servers = max(1, counselor_count)
    service_rate = capacity / servers if capacity else 0.0
    offered_load = arrival_rate / service_rate if service_rate else float(servers)
    utilization = arrival_rate / capacity if capacity else 1.0
    delay_probability = _erlang_c(offered_load, servers)
    steady_state_queue = 0.0
    if utilization >= 1:
        projected_backlog = backlog + max(0.0, arrival_rate - capacity) * planning_horizon_days
        backlog_clearance_days = None
        expected_queue = max(float(backlog), projected_backlog)
        expected_wait_days = expected_queue / max(capacity, 1.0)
    else:
        steady_state_queue = delay_probability * utilization / max(1e-9, 1 - utilization)
        steady_state_wait_days = steady_state_queue / max(arrival_rate, 1.0)
        net_daily_capacity = capacity - arrival_rate
        backlog_clearance_days = backlog / net_daily_capacity if backlog else 0.0
        projected_backlog = max(0.0, backlog - net_daily_capacity * planning_horizon_days)
        expected_queue = float(backlog) + steady_state_queue
        # A newly arriving case waits for the current queue to be served at the
        # full slot rate.  Backlog clearance uses only surplus capacity and is a
        # different operational horizon, so it must not be labeled as that
        # individual's expected wait.
        expected_wait_days = backlog / max(capacity, 1.0) + steady_state_wait_days
    planning_daily_demand = arrival_rate + backlog / planning_horizon_days
    target_capacity = planning_daily_demand / 0.85 if planning_daily_demand else 0.0
    additional_slots = max(0, math.ceil(target_capacity - capacity))
    waitlist_per_counselor = current_waitlist / servers

    if utilization >= 0.90 or waitlist_per_counselor >= 1.5:
        pressure = "높음"
    elif utilization >= 0.78 or waitlist_per_counselor >= 0.8:
        pressure = "주의"
    else:
        pressure = "안정"
    return {
        "method": "Erlang-C(M/M/c) 운영계획 근사",
        "forecast_daily_demand": round(arrival_rate, 1),
        "daily_slot_capacity": round(capacity, 1),
        "forecast_utilization_rate": round(min(utilization, 1.5) * 100, 1),
        "delay_probability": round(delay_probability * 100, 1),
        "current_waitlist": backlog,
        "steady_state_queue_sessions": round(steady_state_queue, 1),
        "expected_queue_sessions": round(expected_queue, 1),
        "expected_wait_days": round(expected_wait_days, 2),
        "projected_backlog_after_horizon": round(projected_backlog, 1),
        "backlog_clearance_days": round(backlog_clearance_days, 2) if backlog_clearance_days is not None else None,
        "planning_horizon_days": planning_horizon_days,
        "recommended_additional_daily_slots": additional_slots,
        "pressure_level": pressure,
        "assumption": "운영 참고용 M/M/c 근사입니다. 도착·상담시간·상담사 역량이 동일하다고 가정하고, 취소·노쇼·반복회기·전문분야 배정은 반영하지 않습니다. 전망 참여인원 1명을 슬롯 1건으로 보므로 부부·가족 동반상담은 별도 환산해야 합니다.",
    }
