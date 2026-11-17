"""평가 시드로 모델을 돌리며 에피소드별 결과, 끝난 위치, 신호 위반, 과속, 차로 변경을 기록한다.
test_skku.py의 지표만으로는 실패 원인을 알 수 없어서 점검 문서용으로 쓴다.

    python rl/eval_detail.py results/base_1117_120000/model.pt --config base --episodes 20
    python rl/eval_detail.py results/base_1116_191213/model.pt --config v0 --episodes 20     # v0 모델
결과: 화면 출력 + 모델 폴더의 eval_detail.json
"""
import argparse
import collections
import json
import os

import course  # noqa: F401
import config
import test_skku
from env import sumo_env

traci = sumo_env.traci


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--config", default="base")
    ap.add_argument("--episodes", type=int, default=20)
    a = ap.parse_args()
    cfg = config.load(a.config)
    env = config.make_env(cfg)
    env.use_seeds(cfg["scenario"]["eval_seeds"])
    agent = test_skku.course_load_agent()(a.model, env.observation_space.shape[0], env.action_space.shape[0])
    if isinstance(agent, tuple):
        agent = agent[0]
    rows = []
    try:
        for _ in range(a.episodes):
            obs, _ = env.reset()
            steps = red = over = moving = lc = 0
            last_edge, last_lane, speeds = None, None, []
            while True:
                if env.ego_id in traci.vehicle.getIDList():
                    e = traci.vehicle.getRoadID(env.ego_id)
                    v = traci.vehicle.getSpeed(env.ego_id)
                    speeds.append(v)
                    if not e.startswith(":"):
                        last_edge, last_lane = e, traci.vehicle.getLaneIndex(env.ego_id)
                        moving += 1
                        over += v > traci.lane.getMaxSpeed(traci.vehicle.getLaneID(env.ego_id)) * 1.1
                obs, r, term, trunc, info = env.step(agent.predict(obs, deterministic=True))
                steps += 1
                red += info.get("red_light", False)
                lc += info["lane_change_applied"]
                if term or trunc:
                    break
            end_v = speeds[-1] if speeds else 0.0
            out = "충돌" if info["collided"] else "도착" if info["arrived"] else "시간초과" if trunc else "기타"
            rows.append({"seed": env.seed_now, "result": out, "steps": steps, "red_light": red, "lane_changes": lc,
                         "overspeed_ratio": round(over / max(moving, 1), 3),
                         "mean_speed": round(sum(speeds) / max(len(speeds), 1), 2), "end_speed": round(end_v, 2),
                         "edge_idx": env.edges.index(last_edge) if last_edge in env.edges else -1,
                         "edge": last_edge, "lane": last_lane})
            print(rows[-1], flush=True)
    finally:
        env.close()
    n = len(rows)
    print("\n결과:", dict(collections.Counter(r["result"] for r in rows)))
    print(f"빨간불 진입: 에피소드당 평균 {sum(r['red_light'] for r in rows) / n:.1f}회, 위반 없는 에피소드 {sum(r['red_light'] == 0 for r in rows)}개")
    print(f"제한속도 10% 초과 주행 비율 평균 {100 * sum(r['overspeed_ratio'] for r in rows) / n:.0f}%, "
          f"평균 속도 {sum(r['mean_speed'] for r in rows) / n * 3.6:.0f} km/h, 차로 변경 평균 {sum(r['lane_changes'] for r in rows) / n:.1f}회")
    for kind in ("충돌", "시간초과"):
        where = collections.Counter((r["edge_idx"], r["edge"]) for r in rows if r["result"] == kind)
        if where:
            print(f"{kind} 위치(경로 엣지 순번, 엣지): " + ", ".join(f"{i}번 {e} ×{c}" for (i, e), c in sorted(where.items())))
    with open(os.path.join(os.path.dirname(os.path.abspath(a.model)), "eval_detail.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
