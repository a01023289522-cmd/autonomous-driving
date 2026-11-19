"""신호 교차로 진입, 정차, 실패 근거를 고정 시드별 JSONL에 저장한다."""
import argparse
from collections import Counter, deque
from itertools import cycle, islice
import json
from pathlib import Path
from statistics import median

import config
import test_skku
from env.sumo_env import traci

GATE_EDGE = "5612296410"
GATE_TURN_LANE = 2
GATE_TLS = "520991292"
GATE_LINK = 10
RED = "rRu"
STOP_SPEED = 0.1
STOP_SECONDS = 5.0
STOP_RADIUS = 100.0
FAR_M = 20.0
AFTER_LINE_M = 15.0


def snapshot(env):
    ego = env.ego_id
    if ego not in traci.vehicle.getIDList():
        return None
    signals = traci.vehicle.getNextTLS(ego)
    leader = traci.vehicle.getLeader(ego, STOP_RADIUS)
    lane = traci.vehicle.getLaneID(ego)
    row = {
        "time_s": traci.simulation.getTime(),
        "edge": traci.vehicle.getRoadID(ego),
        "lane": lane,
        "lane_index": traci.vehicle.getLaneIndex(ego),
        "xy_m": traci.vehicle.getPosition(ego),
        "speed_mps": traci.vehicle.getSpeed(ego),
        "odometer_m": traci.vehicle.getDistance(ego),
        "leader_gap_m": None,
        "leader_speed_mps": None,
        "signal": None,
    }
    if leader and leader[0]:
        row["leader_gap_m"] = leader[1] + traci.vehicle.getMinGap(ego)
        row["leader_speed_mps"] = traci.vehicle.getSpeed(leader[0])
    if signals:
        tls, link, distance, state = signals[0]
        row["signal"] = {
            "id": tls, "link": link, "distance_m": distance, "state": state,
            "phase": traci.trafficlight.getPhase(tls),
            "phase_remaining_s": traci.trafficlight.getNextSwitch(tls) - row["time_s"],
        }
    return row


def gate_signal(row):
    signal = row["signal"]
    return bool(row["edge"] == GATE_EDGE and row["lane_index"] == GATE_TURN_LANE and signal
                and (signal["id"], signal["link"]) == (GATE_TLS, GATE_LINK))


def crossing(before, after, env):
    signal = before["signal"]
    if not signal or before["lane"].startswith(":"):
        return None
    if not after or after["lane"] == before["lane"]:
        return None
    links = traci.trafficlight.getControlledLinks(signal["id"])[signal["link"]]
    targets = {target for source, dest, via in links if source == before["lane"]
               for target in (dest, via) if target}
    # 차가 충돌로 제거된 스텝에서는 위치가 확인되지 않으므로 진입으로 세지 않는다.
    if after["lane"] not in targets:
        return None
    if signal["distance_m"] > env.vmax * env.step_length + 1.0:
        return None
    end_color = traci.trafficlight.getRedYellowGreenState(signal["id"])[signal["link"]]
    return {**before, "entry_time_s": after["time_s"], "entry_lane": after["lane"],
            "stop_line_odometer_m": before["odometer_m"] + signal["distance_m"],
            "end_color": end_color, "red_entry": signal["state"] in RED,
            "is_gate": gate_signal(before)}


def stop_kind(row, from_line=None):
    if row["speed_mps"] >= STOP_SPEED:
        return None
    if row["lane"].startswith(":"):
        return "inside_junction"
    if from_line is not None and 0 <= from_line <= AFTER_LINE_M:
        return "after_line"
    signal = row["signal"]
    if not signal or not 0 <= signal["distance_m"] <= STOP_RADIUS:
        return None
    ahead = row["leader_gap_m"] is not None and row["leader_gap_m"] < signal["distance_m"]
    if signal["state"] in RED + "yY":
        return "queue" if ahead else "signal_first"
    if signal["state"] in "gG" and not ahead:
        return "green_idle"
    return None


def cause(kind, row):
    if kind == "queue":
        return "정지선 전에 앞차가 관측됨. 대기열 차간거리 확인"
    if kind == "inside_junction":
        return "교차로 내부에 5초 이상 정차. 직전 진입 신호와 앞차 기록 확인"
    if kind == "after_line":
        return "정지선을 통과한 뒤 15 m 이내에서 5초 이상 정차. 진입 신호와 앞차 기록 확인"
    if kind == "green_idle":
        return "녹색이고 정지선까지 앞차가 관측되지 않는 상태에서 정차 유지"
    if row["signal"]["distance_m"] > FAR_M:
        return "앞차 없이 20 m 넘게 남겨 정차. 가감속 명령과 신호 관측 확인"
    return None


def episode(env, agent, seed):
    env.use_seeds([seed])
    obs, _ = env.reset()
    seed = env.seed_now
    row = snapshot(env)
    crossings, stops, last_steps = [], [], deque(maxlen=12)
    gate_reached = False
    reward_total = 0.0
    stop_key, stop_start, stop_action, stop_logged = None, 0.0, None, False
    stop_onset = []
    active_crossing = None
    while True:
        gate_reached |= row["edge"] == GATE_EDGE
        action = agent.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        reward_total += reward
        last_steps.append({**row, "accel_raw": info["accel_raw"],
                           "lane_change": info["lane_change"],
                           "lane_change_applied": info["lane_change_applied"]})
        after = snapshot(env)
        entry = crossing(row, after, env)
        if entry:
            if entry["red_entry"]:
                entry["preceding_steps"] = list(last_steps)
            crossings.append(entry)
            active_crossing = entry
        if after:
            gate_reached |= after["edge"] == GATE_EDGE
            from_line = None
            if active_crossing:
                from_line = after["odometer_m"] - active_crossing["stop_line_odometer_m"]
                if from_line > AFTER_LINE_M and not after["lane"].startswith(":"):
                    active_crossing, from_line = None, None
            kind = stop_kind(after, from_line)
            signal = after["signal"]
            key = (kind, after["lane"], signal["id"] if signal else None,
                   signal["link"] if signal else None)
            if kind and key != stop_key:
                stop_start, stop_action, stop_logged = row["time_s"], info["accel_raw"], False
                stop_onset = list(last_steps)
            if kind and not stop_logged and after["time_s"] - stop_start >= STOP_SECONDS:
                from_crossing = active_crossing if kind in ("inside_junction", "after_line") else None
                stops.append({**after, "kind": kind, "start_time_s": stop_start,
                              "accel_at_start": stop_action, "accel_raw": info["accel_raw"],
                              "is_gate": gate_signal(after) or bool(from_crossing and from_crossing["is_gate"]),
                              "entry_signal": from_crossing["signal"] if from_crossing else None,
                              "distance_past_line_m": from_line if from_crossing else None,
                              "preceding_steps": stop_onset if (kind != "signal_first" or signal["distance_m"] > FAR_M) else [],
                              "hypothesis": cause(kind, after)})
                stop_logged = True
            stop_key = key if kind else None
        if terminated or truncated:
            break
        row = after
    outcome = "collision" if info["collided"] else "arrived" if info["arrived"] else "timeout" if truncated else "other"
    failure = {}
    if outcome != "arrived":
        failure = {"last_seen": after or row, "preceding_steps": list(last_steps),
                   "red_flag_on_terminal_step": info["red_light"]}
        if outcome == "timeout" and after and after["edge"] == GATE_EDGE and after["lane_index"] != GATE_TURN_LANE:
            failure["hypothesis"] = "정문 좌회전 연결은 2번 차로에만 있음. 마지막 차로와 변경 명령 확인"
        elif outcome == "timeout" and after and after["speed_mps"] < STOP_SPEED:
            kind = stop_kind(after)
            failure["hypothesis"] = (cause(kind, after) if kind else None) or "제한 시간에 정차 상태. 마지막 감속 명령과 주변 교통 확인"
        elif outcome == "timeout" and after:
            failure["hypothesis"] = "종료 시 이동 중. 누적 대기·서행으로 주행 시간이 부족했는지 확인"
        elif outcome == "collision":
            for crash in traci.simulation.getCollisions():
                if env.ego_id in (crash.collider, crash.victim):
                    failure["collision_lane"] = crash.lane
                    failure["collision_lane_position_m"] = crash.pos
                    failure["collision_type"] = crash.type
                    failure["collision_vehicles"] = [crash.collider, crash.victim]
                    failure["hypothesis"] = "충돌 유형과 직전 속도·선행차·신호 시계열을 비교"
                    break
    return {"seed": seed, "outcome": outcome, "gate_reached": gate_reached, "crossings": crossings,
            "stops": stops, "failure": failure, "steps": env.step_count, "reward": reward_total}


def summarize(rows, gate_only):
    passes = [x for row in rows for x in row["crossings"] if not gate_only or x["is_gate"]]
    stops = [x for row in rows for x in row["stops"] if not gate_only or x["is_gate"]]
    first = [x["signal"]["distance_m"] for x in stops if x["kind"] == "signal_first"]
    queues = [x["leader_gap_m"] for x in stops if x["kind"] == "queue"]
    return {
        "crossings": len(passes), "red_entries": sum(x["red_entry"] for x in passes),
        "red_entry_rate": sum(x["red_entry"] for x in passes) / len(passes) if passes else None,
        "red_entry_phase_transition": sum(x["red_entry"] and x["end_color"] not in RED for x in passes),
        "first_stops": len(first), "far_stops": sum(x > FAR_M for x in first),
        "first_stop_median_m": round(median(first), 2) if first else None,
        "queue_stops": len(queues), "queue_gap_median_m": round(median(queues), 2) if queues else None,
        "green_idle": sum(x["kind"] == "green_idle" for x in stops),
        "inside_junction_stops": sum(x["kind"] == "inside_junction" for x in stops),
        "after_line_stops": sum(x["kind"] == "after_line" for x in stops),
    }


def write_report(folder, config_name, stats, rows):
    labels = {
        "crossings": "확인된 진입",
        "red_entries": "진입 직전 적색",
        "red_entry_phase_transition": "그중 스텝 내 적색에서 전환",
        "first_stops": "선두 정차",
        "first_stop_median_m": "선두 정차선 거리 중앙값 (m)",
        "far_stops": "정지선 20 m 초과 선두 정차",
        "queue_stops": "대기열 정차",
        "queue_gap_median_m": "대기열 앞차 간격 중앙값 (m)",
        "green_idle": "녹색에 전방이 빈 상태로 5초 정차",
        "inside_junction_stops": "교차로 내부 정차",
        "after_line_stops": "교차로 통과 직후 15 m 이내 정차",
    }
    lines = [f"# 신호 평가 · {config_name}", "", f"시드 {rows[0]['seed']}–{rows[-1]['seed']}, "
             f"{stats['episodes']}회 평가, 정문 앞 도달 {stats['gate_reached']}회", "",
             "| 완료 | 충돌 | 시간초과 | 기타 |", "| ---: | ---: | ---: | ---: |"]
    counts = (stats["outcomes"].get(key, 0) for key in ("arrived", "collision", "timeout", "other"))
    lines += ["| " + " | ".join(map(str, counts)) + " |", "", "| 지표 | 전체 | 정문 좌회전 |", "| --- | ---: | ---: |"]
    for key, label in labels.items():
        values = [stats[group][key] for group in ("all_signals", "main_gate")]
        lines.append(f"| {label} | " + " | ".join(str(value) if value is not None else "—" for value in values) + " |")
    failures = [row for row in rows if row["failure"]]
    if failures:
        lines += ["", "## 주행 실패", "", "| 시드 | 결과 | 엣지 | 차로 | 시간 (s) | 확인할 원인 |",
                  "| --- | --- | --- | --- | ---: | --- |"]
        for row in failures:
            failure = row["failure"]
            last = failure["last_seen"]
            lane = failure.get("collision_lane", last["lane"])
            hypothesis = failure.get("hypothesis", "직전 12스텝과 충돌·종료 정보를 확인")
            lines.append(f"| {row['seed']} | {row['outcome']} | {last['edge']} | {lane} | {last['time_s']:.1f} | {hypothesis} |")
    lines += ["", "신호 위반과 조기 정차의 시드별 근거는 `signal_episodes.jsonl`에 기록했다."]
    with (folder / "signal_report.md").open("x", encoding="utf-8") as file:
        print("\n".join(lines), file=file)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("--config", default="base")
    parser.add_argument("--seeds", help="설정의 평가 시드 대신 사용할 범위 (예: 1000-1019)")
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = config.load(args.config)
    seeds = list(islice(cycle(cfg["scenario"]["eval_seeds"]), args.episodes))
    if args.seeds:
        start, end = map(int, args.seeds.split("-"))
        seeds = range(start, end + 1)
    if not seeds:
        parser.error("평가 시드가 최소 하나 있어야 합니다.")
    args.output.mkdir(parents=True, exist_ok=True)
    env = config.make_env(cfg)
    try:
        agent = test_skku.course_load_agent()(args.model, env.observation_space.shape[0], env.action_space.shape[0])
        if isinstance(agent, tuple):
            agent = agent[0]
        rows = []
        with (args.output / "signal_episodes.jsonl").open("x", encoding="utf-8") as file:
            for seed in seeds:
                row = episode(env, agent, seed)
                rows.append(row)
                print(json.dumps(row, ensure_ascii=False), file=file, flush=True)
        stats = {"episodes": len(rows), "outcomes": dict(Counter(x["outcome"] for x in rows)),
                 "gate_reached": sum(x["gate_reached"] for x in rows),
                 "all_signals": summarize(rows, False), "main_gate": summarize(rows, True)}
        with (args.output / "signal_summary.json").open("x", encoding="utf-8") as file:
            print(json.dumps(stats, ensure_ascii=False, indent=2), file=file)
        write_report(args.output, args.config, stats, rows)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    finally:
        env.close()


if __name__ == "__main__":
    main()
