"""시간초과 원인 찾기: 모델로 주행하다 AV가 오래 서 있으면 그 순간의 차로, 앞차 줄, 다음 신호, 차로별 정지 차량 수를 출력한다.

    python -X utf8 rl/diag_stuck.py results/base_1117_161049/model.pt --config base --seeds 1002 1014 1015
시드는 eval_detail_<설정>.json의 시간초과 에피소드에서 고른다. --stop은 이만큼(초) 서 있으면 출력 (신호 대기와 구분하려고 기본 200초).
"""
import argparse
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import course, config, test_skku
from env import sumo_env
traci = sumo_env.traci
ap = argparse.ArgumentParser(); ap.add_argument("model"); ap.add_argument("--config", default="base")
ap.add_argument("--seeds", type=int, nargs="+", required=True); ap.add_argument("--stop", type=float, default=200)
a = ap.parse_args()
cfg = config.load(a.config); env = config.make_env(cfg)
agent = test_skku.course_load_agent()(a.model, env.observation_space.shape[0], env.action_space.shape[0])
agent = agent[0] if isinstance(agent, tuple) else agent
for seed in a.seeds:
    env.use_seeds([seed]); obs, _ = env.reset(); stopped = 0
    for t in range(1600):
        obs, r, term, trunc, info = env.step(agent.predict(obs, deterministic=True))
        if term or trunc: break
        v = traci.vehicle.getSpeed(env.ego_id)
        stopped = stopped + 1 if v < 0.1 else 0
        if stopped == int(a.stop / env.step_length):
            e = env.ego_id; lead = traci.vehicle.getLeader(e, 100)
            print(seed, "t", t, traci.vehicle.getLaneID(e), "pos", round(traci.vehicle.getLanePosition(e),1),
                  "lanes", traci.edge.getLaneNumber(traci.vehicle.getRoadID(e)),
                  "leader", lead and (lead[0], traci.vehicle.getTypeID(lead[0]), round(lead[1],1), round(traci.vehicle.getSpeed(lead[0]),1), traci.vehicle.getStopState(lead[0])),
                  "tls", traci.vehicle.getNextTLS(e)[:1], "obs_accel_cmd", round(float(agent.predict(obs, deterministic=True)[0]),2), flush=True)
            x = e
            for k in range(8):
                l = traci.vehicle.getLeader(x, 200)
                if not l: print("  끝 (앞차 없음)"); break
                x = l[0]; print("  ", x, traci.vehicle.getTypeID(x), traci.vehicle.getLaneID(x), round(traci.vehicle.getLanePosition(x),1), "v", round(traci.vehicle.getSpeed(x),1), "wait", round(traci.vehicle.getWaitingTime(x)), "stop", traci.vehicle.getStopState(x), "route_next", traci.vehicle.getRoute(x)[traci.vehicle.getRouteIndex(x):traci.vehicle.getRouteIndex(x)+2])
            print("  차로별 정지 차량:", [traci.lane.getLastStepHaltingNumber(f"{traci.vehicle.getRoadID(e)}_{i}") for i in range(traci.edge.getLaneNumber(traci.vehicle.getRoadID(e)))])
            break
env.close()
