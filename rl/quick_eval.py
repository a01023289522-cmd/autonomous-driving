"""빠른 평가: 충돌 대신 충돌 직전 행동을 재서 20 에피소드로 모델을 비교한다 (100 에피소드 평가 전 중간 판단용).

충돌은 에피소드당 약 0.1건이라 100 에피소드가 있어야 차이가 보이지만, 아래 지표는 훨씬 자주 생긴다 (11/18 r_idle_scaled 재생 분석).
  - 위험 진입: 양보해야 하는 연결에 들어가는 순간 우선 차량이 충돌 지점까지 3초 안 (에피소드당 약 0.7회, 그중 충돌 7.5%)
  - 앞차 시간 간격 위반: 앞차 6 m 이상, 시간 간격 2초 미만, 다가가는 중 (주행 1000스텝당 횟수)
  - 신호 앞 정지 위치: 빨강·노랑 앞에서 5초 넘게 섰을 때 정지선까지 거리 (앞차가 15 m 안에 있으면 뺀다)
우선 차량 목록은 getJunctionFoes(내가 양보, 아직 충돌 지점을 안 빠져나간 차) + lane.getFoes(우선권 있는 진입 차로)로,
관측 보완(obs_foe_fix)과 같다. 모델의 관측 설정과 상관없이 같은 기준으로 잰다.

    python -X utf8 rl/quick_eval.py results/<run>/model_150k.pt --config r_safe
    python -X utf8 rl/quick_eval.py A.pt B.pt --config r_safe --config r_idle_scaled     # 여러 모델 (설정은 모델 순서대로)
"""
import argparse
import collections
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TTC_RISK, HEADWAY, STOP_FAR = 3.0, 2.0, 20.0


def entry_risk(traci, e):
    """양보해야 하는 연결 앞이면 (차로, 우선 차량 최소 TTC 초), 아니면 None."""
    lane = traci.vehicle.getLaneID(e)
    links = traci.vehicle.getNextLinks(e)
    if lane.startswith(":") or not links or links[0][5] not in "mswg=":
        return None
    ttc = [max(x[2], 0.0) / max(traci.vehicle.getSpeed(x[0]), 0.1)
           for x in traci.vehicle.getJunctionFoes(e, 60) if x[7] and x[4] > 0]
    try:
        for fl in traci.lane.getFoes(lane, links[0][0]):
            length = traci.lane.getLength(fl)
            for v in traci.lane.getLastStepVehicleIDs(fl):
                d = length - traci.vehicle.getLanePosition(v)
                if d < 60:
                    ttc.append(d / max(traci.vehicle.getSpeed(v), 0.1))
    except traci.TraCIException:
        pass
    return lane, min(ttc, default=99.0)


def worker(model, cfgname, seeds, out):
    sys.path.insert(0, HERE)
    import course  # noqa: F401
    import config
    import test_skku
    from env import sumo_env
    traci = sumo_env.traci
    env = config.make_env(config.load(cfgname))
    ag = test_skku.course_load_agent()(model, env.observation_space.shape[0], env.action_space.shape[0])
    ag = ag[0] if isinstance(ag, tuple) else ag
    with open(out, "w", encoding="utf-8") as f:
        for seed in seeds:
            env.use_seeds([seed])
            obs, _ = env.reset()
            ep = dict(seed=seed, entries=[], hw=0, drive=0, stops=[], steps=0, edge="")
            stopped, info = 0, {}
            while True:
                e = env.ego_id
                risk = entry_risk(traci, e) if e in traci.vehicle.getIDList() else None
                obs, r, te, tr, info = env.step(ag.predict(obs, deterministic=True))
                ep["red"] = ep.get("red", 0) + int(bool(info.get("red_light")) and not info.get("collided"))
                ep["steps"] += 1
                if e in traci.vehicle.getIDList():
                    v, lane = traci.vehicle.getSpeed(e), traci.vehicle.getLaneID(e)
                    ep["edge"] = traci.vehicle.getRoadID(e)
                    lead = traci.vehicle.getLeader(e, 100)
                    if v > 1:
                        ep["drive"] += 1
                        if lead and lead[1] >= 6 and lead[1] < v * HEADWAY and v > traci.vehicle.getSpeed(lead[0]):
                            ep["hw"] += 1
                    if risk and lane.startswith(":") and lane != risk[0]:
                        ep["entries"].append([risk[0].rsplit("_", 1)[0], round(risk[1], 2), 0, traci.simulation.getTime()])
                    stopped = stopped + 1 if v < 0.1 else 0
                    if stopped == 10:
                        t = traci.vehicle.getNextTLS(e)
                        if t and t[0][3] in "rRyYu" and not (lead and lead[1] < 15):
                            ep["stops"].append(round(t[0][2], 1))
                elif info.get("collided") and risk:          # 진입하는 스텝에 충돌
                    ep["entries"].append([risk[0].rsplit("_", 1)[0], round(risk[1], 2), 1, traci.simulation.getTime()])
                if te or tr:
                    break
            if info.get("collided") and ep["entries"] and traci.simulation.getTime() - ep["entries"][-1][3] < 6:
                ep["entries"][-1][2] = 1           # 진입하고 6초 안에 충돌 (교차로 안 충돌)
            ep["result"] = "충돌" if info.get("collided") else "도착" if info.get("arrived") else "시간초과"
            f.write(json.dumps(ep, ensure_ascii=False) + "\n")
            f.flush()
    env.close()


def summarize(eps):
    E = [x for e in eps for x in e["entries"]]
    risky = [x for x in E if x[1] < TTC_RISK]
    stops = [s for e in eps for s in e["stops"]]
    drive = sum(e["drive"] for e in eps)
    res = collections.Counter(e["result"] for e in eps)
    where = collections.Counter(e["edge"] for e in eps if e["result"] != "도착")
    loc = collections.Counter(x[0] for x in risky)
    return {
        "에피소드": len(eps), "결과": dict(res),
        "위험 진입/에피소드": round(len(risky) / len(eps), 2),
        "위험 진입 비율": f"{len(risky)}/{len(E)} ({len(risky) / max(len(E), 1):.1%})",
        "TTC<1초 진입": sum(x[1] < 1 for x in E),
        "진입 뒤 충돌 (위험 진입 중)": f"{sum(x[2] for x in E)} ({sum(x[2] for x in risky)})",
        "위험 진입 위치": dict(loc.most_common(4)),
        "시간 간격 위반/1000스텝": round(1000 * sum(e["hw"] for e in eps) / max(drive, 1), 1),
        "신호 앞 정지": len(stops),
        "정지선까지 중앙값 m": round(float(np.median(stops)), 1) if stops else None,
        f"{STOP_FAR:.0f} m 넘게 떨어져 정지": f"{sum(s > STOP_FAR for s in stops)}/{len(stops)}",
        "평균 주행 시간 s": round(float(np.mean([e["steps"] for e in eps if e["result"] == "도착"] or [0])) * 0.5, 1),
        "실패 위치": dict(where),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--config", action="append", required=True, help="모델마다 하나, 또는 하나만 주면 모두 같은 설정")
    ap.add_argument("--seeds", default="1000-1019", help="평가 시드 범위 (기본 1000–1019, 100 에피소드 평가 시드의 앞 20개)")
    ap.add_argument("--procs", type=int, default=4, help="모델마다 동시에 돌릴 프로세스 수")
    ap.add_argument("--worker", nargs=3, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.worker:
        worker(a.models[0], a.config[0], list(map(int, a.worker[0].split(","))), a.worker[2])
        return
    if "," in a.seeds:                       # 실패 시드 목록 (11/22: 이전 모델 실패 시드부터 먼저 확인)
        seeds = [int(x) for x in a.seeds.split(",")]
    else:
        lo, hi = map(int, a.seeds.split("-"))
        seeds = list(range(lo, hi + 1))
    cfgs = a.config if len(a.config) == len(a.models) else a.config * len(a.models)
    tmp = tempfile.mkdtemp(prefix="quick_eval_")
    jobs = []
    for m, c in zip(a.models, cfgs):
        for k in range(a.procs):
            out = os.path.join(tmp, f"{len(jobs)}.jsonl")
            chunk = ",".join(map(str, seeds[k::a.procs]))
            jobs.append((m, out, subprocess.Popen([sys.executable, "-X", "utf8", os.path.abspath(__file__), m, "--config", c,
                                                    "--worker", chunk, "-", out], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)))
    for _, _, p in jobs:
        p.wait()
    for m, c in zip(a.models, cfgs):
        eps = [json.loads(l) for mm, out, _ in jobs if mm == m and os.path.exists(out) for l in open(out, encoding="utf-8")]
        print(f"\n== {m} (--config {c})")
        if not eps:
            print("결과 없음 (오류). --procs 1로 직접 실행해 확인")
            continue
        for k, v in summarize(eps).items():
            print(f"  {k}: {v}")
        print("  빨간불 진입:", sum(e.get("red", 0) for e in eps), [e["seed"] for e in eps if e.get("red")])
        print("  실패 시드:", sorted((e["seed"], e["result"], e["edge"]) for e in eps if e["result"] != "도착"))


if __name__ == "__main__":
    main()
