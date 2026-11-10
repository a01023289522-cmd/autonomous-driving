"""데이터 칼럼 과제용 CSV: 성대역 도로에서 실제로 주행해 필수 칼럼 + 팀별 추가 칼럼을 기록한다.

학습 전 단계라 규칙으로 움직이는 정책을 쓴다. 에피소드 끝부분만 남겨 도착·충돌·차로 변경이 들어가게 한다.
    python -X utf8 rl/make_column_sample.py 출력.csv
"""
import csv
import json
import sys

import config
import course  # noqa: F401
import numpy as np

COLUMNS = ["episode", "t", "observation", "action_raw", "action.accel_raw", "action.lane_change_raw", "action.lane_change",
           "action.lane_change_applied", "reward", "terminated", "truncated", "state", "detected_vehicles", "event.collided",
           "event.arrived", "event.lane_before", "event.lane_after", "next_observation", "next_state", "tls_state", "tls_distance_m"]
KEEP = 8


def rnd(x):
    if isinstance(x, (float, np.floating)):
        return round(float(x), 3)
    if isinstance(x, dict):
        return {k: rnd(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [rnd(v) for v in x]
    return x


def js(x):
    return json.dumps(rnd(x), ensure_ascii=False, separators=(",", ":"))


def run(env, episode, policy, want):
    """want(info, tail)을 만족하며 끝난 에피소드의 마지막 KEEP 줄."""
    for _ in range(12):
        obs, _info = env.reset()
        rows, t = [], 0
        while True:
            state, seen, (tls, dist) = env.get_privileged_state(), env.get_detected_vehicles(), env.signal_info()
            action = np.array(policy(t, obs), dtype=np.float32)
            next_obs, reward, term, trunc, info = env.step(action)
            rows.append([episode, t, js(obs), js(action), rnd(info["accel_raw"]), rnd(info["lane_change_raw"]), info["lane_change"],
                         info["lane_change_applied"], rnd(reward), term, trunc, js(state), js(seen), info["collided"], info["arrived"],
                         info["lane_before"], info["lane_after"], js(next_obs), js(env.get_privileged_state()), tls, rnd(dist)])
            obs, t = next_obs, t + 1
            if term or trunc:
                break
        tail = rows[-KEEP:]
        if want(info, tail):
            print(f"에피소드 {episode}: 시드 {env.seed_now}, {t}스텝, 충돌 {info['collided']}, 도착 {info['arrived']}, "
                  f"차로 변경 성공 {sum(r[7] for r in tail)}, 실패 {sum(r[6] != 0 and not r[7] for r in tail)}")
            return tail
    raise SystemExit(f"에피소드 {episode}: 조건에 맞는 주행을 못 얻었습니다")


def careful(t, obs):     # 앞차와 간격을 두고 천천히 간다. 1차로 교내에서 차로 변경 명령은 실패한다
    accel = -0.8 if obs[9] < 0.35 else (0.5 if obs[0] * 13.89 < 5 else 0.0)
    return [accel, 1.0 if t % 12 == 11 else 0.0]


def rushing(t, obs):     # 계속 가속하고 차로 변경을 번갈아 시도한다
    return [1.0, {1: 1.0, 3: -1.0, 5: 1.0, 7: -1.0}.get(t % 8, 0.0)]


def main():
    base = config.load("base")
    goal = base["scenario"]["goal_edge"]
    full = json.load(open(course.TEAM + "/sumo/skku_map/verify/av_route_full.json", encoding="utf-8"))["edges"]
    near = dict(base, scenario=dict(base["scenario"], start_edge=full[full.index(goal) - 3], train_seeds=list(range(3000, 3012))))
    main_route = dict(base, scenario=dict(base["scenario"], train_seeds=list(range(3012, 3024))))
    rows = []
    for episode, (cfg, policy, want) in enumerate(((near, careful, lambda i, tail: i["arrived"] and any(r[6] != 0 for r in tail)), (main_route, rushing, lambda i, tail: i["collided"] and any(r[7] for r in tail))), 1):
        env = config.make_env(cfg)
        try:
            rows += run(env, episode, policy, want)
        finally:
            env.close()
    with open(sys.argv[1], "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(COLUMNS)
        w.writerows(rows)
    print(f"{len(rows)}줄 저장: {sys.argv[1]}")


if __name__ == "__main__":
    main()
