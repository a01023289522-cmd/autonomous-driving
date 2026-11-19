"""주행 품질 측정: 정지 원인 분류와 가감속 품질 (11/18 사용자 지적 4가지: 정류장 앞 의미 없는 정지, 정지선 넘어/위 정지,
너무 일찍 정지, 가감속).

정지 = 5초(10스텝) 넘게 0.1 m/s 미만. 정지가 시작될 때 원인을 하나로 분류한다 (위에서부터 먼저 맞는 것).
  교차로 안 (신호)     : 신호 교차로 내부 차로에서 섬 = 정지선을 넘어서 섬
  교차로 안 (무신호)   : 무신호 교차로·회전교차로 내부에서 섬
  신호 정지선 위       : 빨강·노랑 신호 정지선까지 0–1 m (앞범퍼가 선에 걸침)
  신호 정상 위치       : 정지선까지 1–20 m
  신호 대기열          : 앞차 15 m 안이고 앞에 빨강·노랑 신호
  신호 멀리서          : 정지선까지 20 m 넘고 앞차도 15 m 넘게 떨어짐
  정류장 버스 뒤       : 앞차(40 m 안)가 정류장에 선 버스 (신호보다 먼저 본다)
  정류장 근처 이유 없음 : 정류장 30 m 안, 앞차 없거나 15 m 넘음, 신호·양보 상대 없음
  앞차 대기열          : 앞차 15 m 안 (신호 아님)
  양보 대기            : 양보할 교차 차량 있음
  이유 없음            : 그 밖
가감속: 내 속도 1 m/s 넘는 구간에서 가속도(Δv/0.5초), 저크(Δa/0.5초).

    python -X utf8 rl/drive_quality.py results/<run>/model.pt --config <설정> [--seeds 1000-1019] [--procs 4]
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def bus_stops(team):
    x = open(os.path.join(team, "sumo", "skku_map", "bus.stops.xml"), encoding="utf-8").read()
    out = {}
    for m in re.finditer(r"<busStop [^>]*>", x):
        t = m.group(0)
        lane = re.search(r'lane="([^"]+)"', t).group(1)
        out.setdefault(lane, []).append((float(re.search(r'startPos="([^"]+)"', t).group(1)),
                                         float(re.search(r'endPos="([^"]+)"', t).group(1)),
                                         re.search(r'name="([^"]*)"', t).group(1)))
    return out


def worker(model, cfgname, seeds, out):
    sys.path.insert(0, HERE)
    import course
    import config
    import test_skku
    from env import sumo_env
    traci = sumo_env.traci
    env = config.make_env(config.load(cfgname))
    ag = test_skku.course_load_agent()(model, env.observation_space.shape[0], env.action_space.shape[0])
    ag = ag[0] if isinstance(ag, tuple) else ag
    stops_xml = bus_stops(course.TEAM)
    tls_junctions = None
    with open(out, "w", encoding="utf-8") as f:
        for seed in seeds:
            env.use_seeds([seed])
            obs, _ = env.reset()
            if tls_junctions is None:
                tls_junctions = {lk[0][2].rsplit("_", 1)[0][1:].rsplit("_", 1)[0]
                                 for t in traci.trafficlight.getIDList() for lk in traci.trafficlight.getControlledLinks(t) if lk}
            ep = dict(seed=seed, stops=[], acc=[], jerk=[], dist=0.0, steps=0)
            run, prev_v, prev_a, info = 0, None, None, {}
            while True:
                obs, r, te, tr, info = env.step(ag.predict(obs, deterministic=True))
                ep["steps"] += 1
                if te or tr:
                    break
                e = env.ego_id
                if e not in traci.vehicle.getIDList():
                    continue
                v = traci.vehicle.getSpeed(e)
                ep["dist"] += v * 0.5
                if prev_v is not None and (v > 1 or prev_v > 1):
                    a = (v - prev_v) / 0.5
                    ep["acc"].append(round(a, 2))
                    if prev_a is not None:
                        ep["jerk"].append(round((a - prev_a) / 0.5, 2))
                    prev_a = a
                else:
                    prev_a = None
                prev_v = v
                run = run + 1 if v < 0.1 else 0
                if run != 10:
                    continue
                lane = traci.vehicle.getLaneID(e)
                pos = traci.vehicle.getLanePosition(e)
                lead = traci.vehicle.getLeader(e, 100)
                t = traci.vehicle.getNextTLS(e)
                red = t[0] if t and t[0][3] in "rRyYu" and t[0][2] < 120 else None
                foes = [x for x in traci.vehicle.getJunctionFoes(e, 60) if x[7] and x[4] > 0 and x[2] < 60]
                near_stop = [s for s in stops_xml.get(lane, []) if s[0] - 30 <= pos <= s[1] + 30]
                # 앞차가 정류장에 선 버스이고 40 m 안 (stop state의 atBusStop). 11/18: AV는 버스 17–24 m 뒤에 서서 15 m 기준으로는
                # "신호 멀리서"로 잘못 셌다. 그래서 신호보다 먼저 본다
                lead_bus = bool(lead and lead[1] < 40 and traci.vehicle.isAtBusStop(lead[0]))
                if lead_bus and not lane.startswith(":"):
                    kind = "정류장 버스 뒤"
                elif lane.startswith(":"):
                    j = lane[1:].rsplit("_", 2)[0]
                    kind = "교차로 안 (신호)" if j in tls_junctions else "교차로 안 (무신호)"
                elif red and red[2] < 1:
                    kind = "신호 정지선 위"
                elif red and red[2] <= 20:
                    kind = "신호 정상 위치"
                elif red and lead and lead[1] < 15:
                    kind = "신호 대기열"
                elif red:
                    kind = "신호 멀리서"
                elif near_stop and not (lead and lead[1] < 15) and not foes:
                    kind = "정류장 근처 이유 없음"
                elif lead and lead[1] < 15:
                    kind = "앞차 대기열"
                elif foes:
                    kind = "양보 대기"
                else:
                    kind = "이유 없음"
                ep["stops"].append(dict(kind=kind, edge=traci.vehicle.getRoadID(e), lane=traci.vehicle.getLaneIndex(e),
                                        tls=red and round(red[2], 1), lead=lead and round(lead[1], 1),
                                        stop=near_stop[0][2] if near_stop else "", t=traci.simulation.getTime()))
            ep["result"] = "충돌" if info.get("collided") else "도착" if info.get("arrived") else "시간초과"
            f.write(json.dumps(ep, ensure_ascii=False) + "\n")
            f.flush()
    env.close()


def summarize(eps):
    S = [s for e in eps for s in e["stops"]]
    kinds = collections.Counter(s["kind"] for s in S)
    acc = np.array([a for e in eps for a in e["acc"]])
    jerk = np.array([j for e in eps for j in e["jerk"]])
    km = sum(e["dist"] for e in eps) / 1000
    flips = sum(int(np.sum(np.diff(np.sign(np.array(e["acc"])[np.abs(e["acc"]) > 0.3])) != 0)) for e in eps if len(e["acc"]) > 2)
    lines = [f"에피소드 {len(eps)}, 결과 {dict(collections.Counter(e['result'] for e in eps))}, 주행 {km:.1f} km",
             f"정지 {len(S)}회 (에피소드당 {len(S) / len(eps):.1f})"]
    for k, n in kinds.most_common():
        where = collections.Counter(f"{s['edge']}#{s['lane']}" + (f"({s['stop']})" if s["stop"] else "") for s in S if s["kind"] == k)
        lines.append(f"  {k}: {n}  위치 {dict(where.most_common(3))}")
    far = [s["tls"] for s in S if s["kind"] == "신호 멀리서"]
    if far:
        lines.append(f"  신호 멀리서 정지선까지 중앙값 {np.median(far):.0f} m")
    if len(acc):
        lines += [f"가속도: 급제동(≤−3 m/s²) {np.sum(acc <= -3)}회 = {np.sum(acc <= -3) / km:.1f}/km, 강한 감속(≤−2) {np.sum(acc <= -2) / km:.1f}/km, "
                  f"급가속(≥2) {np.sum(acc >= 2) / km:.1f}/km",
                  f"저크: |저크| 평균 {np.mean(np.abs(jerk)):.2f} m/s³, 4 m/s³ 넘는 스텝 {np.mean(np.abs(jerk) > 4):.1%}",
                  f"가속↔감속 전환 {flips / km:.1f}회/km"]
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="+")
    ap.add_argument("--config", action="append", required=True)
    ap.add_argument("--seeds", default="1000-1019")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--worker", nargs=3, help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.worker:
        worker(a.models[0], a.config[0], list(map(int, a.worker[0].split(","))), a.worker[2])
        return
    lo, hi = map(int, a.seeds.split("-"))
    seeds = list(range(lo, hi + 1))
    cfgs = a.config if len(a.config) == len(a.models) else a.config * len(a.models)
    tmp, jobs = tempfile.mkdtemp(prefix="drive_quality_"), []
    for m, c in zip(a.models, cfgs):
        for k in range(a.procs):
            out = os.path.join(tmp, f"{len(jobs)}.jsonl")
            jobs.append((m, out, subprocess.Popen([sys.executable, "-X", "utf8", os.path.abspath(__file__), m, "--config", c, "--worker",
                                                   ",".join(map(str, seeds[k::a.procs])), "-", out],
                                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)))
    for _, _, p in jobs:
        _, err = p.communicate()
        if p.returncode:
            print(err.decode("utf-8", "replace")[-1500:])
    for m, c in zip(a.models, cfgs):
        eps = [json.loads(l) for mm, out, _ in jobs if mm == m and os.path.exists(out) for l in open(out, encoding="utf-8")]
        print(f"\n== {m} (--config {c})")
        for line in summarize(eps) if eps else ["결과 없음"]:
            print(line)


if __name__ == "__main__":
    main()
