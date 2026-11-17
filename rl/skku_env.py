"""수업 환경(SumoHighwayEnv)을 성대역 도로망(sumo/skku_map)에서 돌리는 환경.

행동과 기본 보상은 수업 코드를 그대로 쓰고, 다음을 바꾼다:
  - 환경 v1 (SCENARIO["obs_v1"]): 관측 12개 추가(신호, 경로 차로, 교차 차량, 제한속도), 신호 위반·과속 감점. 아래 _v1_obs
  - 도로를 새로 만들지 않고 skku.sumocfg를 읽는다
  - 경로는 verify/av_route_full.json에서 start_edge ~ goal_edge를 잘라 쓴다
  - 시드를 정해 둔 목록에서 차례로 쓴다 (평가 조건을 똑같이 맞추기 위해)
  - 배경 교통을 warmup_seconds만큼 채운 뒤 AV를 넣는다. 채운 상태는 시드별로 저장해 두고 다음부터 불러온다
    (work/states/, 처음 한 번만 시드당 약 20초. userdoc/Simulation/SaveAndLoad.html)
  - 교차로 안 충돌도 검사한다 (기본값은 꺼짐, userdoc/sumo.html --collision.check-junctions)
"""
import json
import os

import course
from env import sumo_env
from env.sumo_env import SumoHighwayEnv

import gymnasium as gym  # noqa: E402
import numpy as np  # noqa: E402
from sumolib import checkBinary  # noqa: E402

traci = sumo_env.traci      # 수업 환경이 고른 것과 같은 모듈을 쓴다 (libsumo를 깔면 화면 없는 실행은 libsumo가 된다)

MAP = os.path.join(course.TEAM, "sumo", "skku_map")
STATES = os.path.join(MAP, "work", "states")
TRAFFIC_FILES = ("skku.net.xml", "skku.rou.xml", "bus.rou.xml", "parking.rou.xml", "random.rou.xml", "skku.sumocfg")
ROUTE_ID = "av_route"
STATE_RADIUS = 100.0        # state에 저장할 주변 차량 반경 (m). 전부 저장하면 스텝마다 약 400대가 된다


def route_edges(start, goal):
    edges = json.load(open(os.path.join(MAP, "verify", "av_route_full.json"), encoding="utf-8"))["edges"]
    return edges[edges.index(start):edges.index(goal) + 1]


class SkkuEnv(SumoHighwayEnv):
    def __init__(self, scenario, mdp_sim, mdp_obs, action, reward, gui=False):
        road = {"speed_limit": scenario["speed_limit"], "num_lanes": 3, "length": 1e9}
        ego = {"depart_lane": "best", "depart_speed": 0, "accel": scenario["accel"], "decel": scenario["decel"]}
        super().__init__(os.path.join(MAP, "skku.sumocfg"), road, ego, mdp_sim, mdp_obs, action, reward, gui=gui)
        self.v1 = bool(scenario.get("obs_v1", False))
        if self.v1:
            self.obs_dim += self.V1_DIM
            self.observation_space = gym.spaces.Box(-1.0, 1.0, shape=(self.obs_dim,), dtype=np.float32)
        self.edges = route_edges(scenario["start_edge"], scenario["goal_edge"])
        self.warmup_seconds = float(scenario["warmup_seconds"])
        self.use_seeds(scenario["train_seeds"])

    def use_seeds(self, seeds):
        """이 목록의 시드를 처음부터 차례로 쓴다. 평가 전에 eval_seeds로 바꾼다."""
        self.seeds, self._next = list(seeds), 0

    def _state_file(self, seed):
        return os.path.join(STATES, f"s{seed}_w{self.warmup_seconds:.0f}_dt{self.step_length}.xml.gz")

    def _state_ready(self, path):
        """저장한 상태가 있고 도로·교통 파일이 그 뒤로 바뀌지 않았는가."""
        return os.path.exists(path) and os.path.getmtime(path) >= max(os.path.getmtime(os.path.join(MAP, f)) for f in TRAFFIC_FILES)

    def _start_sumo(self):
        seed = self.seeds[self._next % len(self.seeds)]
        self._next += 1
        self.seed_now = seed
        cmd = [checkBinary("sumo-gui" if self.gui else "sumo"), "-c", self.cfg_path, "--step-length", str(self.step_length),
               "--collision.action", "remove", "--collision.check-junctions", "true",
               "--no-warnings", "true", "--no-step-log", "true", "--seed", str(seed)]
        if self.gui:
            cmd += ["--quit-on-end", "--delay", str(self.gui_delay), "--start"]
        else:                                 # 화면이 없으면 배경 도형은 읽지 않는다
            cmd += ["-a", ",".join(os.path.join(MAP, f) for f in ("vtypes.add.xml", "bus.stops.xml", "skku.add.xml"))]
        self._state, self._loaded = self._state_file(seed), self._state_ready(self._state_file(seed))
        if self._loaded:
            cmd += ["--load-state", self._state, "--begin", str(self.warmup_seconds)]
        traci.start(cmd)
        self._started = True

    def _insert_ego(self):
        """배경 교통을 채운 뒤 AV를 넣는다. 들어갈 자리가 끝내 없으면 False."""
        if not self._loaded:
            traci.simulationStep(self.warmup_seconds)
            os.makedirs(STATES, exist_ok=True)
            tmp = f"{self._state}.{os.getpid()}.xml.gz"
            traci.simulation.saveState(tmp)
            os.replace(tmp, self._state)      # 여러 학습을 동시에 돌려도 반쯤 쓴 파일을 읽지 않게
        traci.route.add(ROUTE_ID, self.edges)
        traci.vehicletype.copy("DEFAULT_VEHTYPE", "ego_type")
        traci.vehicletype.setColor("ego_type", (255, 0, 0, 255))
        traci.vehicle.add(self.ego_id, ROUTE_ID, typeID="ego_type", departLane="best", departPos="free", departSpeed="0")
        traci.vehicle.setSpeedMode(self.ego_id, 0)            # 수업 환경과 같음: 안전 제어는 정책 몫
        traci.vehicle.setLaneChangeMode(self.ego_id, 0)
        for _ in range(240):
            traci.simulationStep()
            if self.ego_id in traci.vehicle.getIDList():
                return True
        return False

    def reset(self, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        for _ in range(3):
            if self._started:
                traci.close()
                self._started = False
            self._start_sumo()
            if self._insert_ego():
                break
        else:
            raise RuntimeError("AV 투입 실패: 출발 엣지가 계속 막혀 있습니다. warmup_seconds 또는 교통량을 확인하세요.")
        if self.gui:
            view = traci.gui.getIDList()[0]
            traci.gui.trackVehicle(view, self.ego_id)
            traci.gui.setZoom(view, 800)
        self.step_count = 0
        return self._get_obs(), {}

    def get_privileged_state(self):
        s = super().get_privileged_state()
        if s.get("ego_alive"):
            ex, ey = s["ego_x"], s["ego_y"]
            s["vehicles"] = [v for v in s["vehicles"] if (v["x"] - ex) ** 2 + (v["y"] - ey) ** 2 <= STATE_RADIUS ** 2]
            s["simulation_time_s"] = float(traci.simulation.getTime())
        return s

    def get_detected_vehicles(self):
        out = super().get_detected_vehicles()
        for v in out:
            v["type"] = traci.vehicle.getTypeID(v["id"])
        return out

    def signal_info(self):
        """AV 경로의 다음 신호: (색 r/y/G/g 또는 none, 거리 m 또는 -1). userdoc/TraCI/Vehicle_Value_Retrieval.html "next TLS"."""
        if self.ego_id in traci.vehicle.getIDList():
            tls = traci.vehicle.getNextTLS(self.ego_id)
            if tls:
                return tls[0][3], float(tls[0][2])
        return "none", -1.0

    # ------------------------------------------------------------------
    # 환경 v1 관측: 수업 관측 31개 뒤에 12개를 붙인다 (SCENARIO["obs_v1"]가 False면 v0 그대로 31개)
    #   [31] 다음 신호까지 거리 /100 (신호가 없거나 100 m 밖이면 1)   [32] 빨간불  [33] 노란불
    #   [34] 현재 신호색이 바뀌기까지 남은 시간 /30
    #   [35] 경로에 필요한 차로 변경 수 /2 (+는 행동의 +1 방향)        [36] 지금 차로로 더 갈 수 있는 거리 /200
    #   [37] 다음 교차로까지 거리 /100   [38] 다음 교차로에서 양보해야 함 (신호 없는 비우선 연결)
    #   [39] 양보해야 할 교차 차량 중 가장 가까운 차의 충돌 지점까지 거리 /60 (없으면 1)  [40] 그 차 속도 /vmax
    #   [41] 양보해야 할 교차 차량 수 /3
    #   [42] 지금 차로 제한속도 /vmax
    # 쓰는 TraCI: getNextTLS, trafficlight.getNextSwitch, getBestLanes, getNextLinks, getJunctionFoes
    #   (userdoc/TraCI/Vehicle_Value_Retrieval.html: next TLS, best lanes, next links, junction foes)
    # ------------------------------------------------------------------
    V1_DIM = 12
    FOE_RANGE = 60.0

    def _v1_obs(self):
        e, f = self.ego_id, []
        tls = traci.vehicle.getNextTLS(e)
        if tls and tls[0][2] <= 100:
            tid, _, dist, state = tls[0]
            left = traci.trafficlight.getNextSwitch(tid) - traci.simulation.getTime()
            f += [dist / 100, float(state in "rRu"), float(state in "yY"), min(left, 30) / 30]
        else:
            f += [1.0, 0.0, 0.0, 1.0]
        lane_id, lane_idx = traci.vehicle.getLaneID(e), traci.vehicle.getLaneIndex(e)
        best = [b for b in traci.vehicle.getBestLanes(e) if b[0] == lane_id]
        if best:
            f += [max(-1.0, min(1.0, best[0][3] / 2)), min(best[0][1] - traci.vehicle.getLanePosition(e), 200) / 200]
        else:                                      # 교차로 안 (내부 차로): 변경 불가, 그대로 진행
            f += [0.0, 1.0]
        links = traci.vehicle.getNextLinks(e)
        if lane_id.startswith(":") or not links:
            jd, yld = 0.0, 0.0
        else:
            jd = traci.lane.getLength(lane_id) - traci.vehicle.getLanePosition(e)
            yld = float(links[0][5] in "mswg=")    # 소문자 m/g, 정지(s), 전방향 정지(w): 다른 차에 양보하는 연결
        foes = [x for x in traci.vehicle.getJunctionFoes(e, self.FOE_RANGE) if x[7]]   # egoResponse: 내가 양보할 차
        if foes:
            near = min(foes, key=lambda x: x[2])
            f += [min(jd, 100) / 100, yld, min(near[2], self.FOE_RANGE) / self.FOE_RANGE,
                  traci.vehicle.getSpeed(near[0]) / self.vmax, min(len(foes), 3) / 3]
        else:
            f += [min(jd, 100) / 100, yld, 1.0, 0.0, 0.0]
        f.append(traci.lane.getMaxSpeed(lane_id) / self.vmax)
        return f

    def _get_obs(self):
        base = super()._get_obs()
        if not self.v1:
            return base
        if self.ego_id not in traci.vehicle.getIDList():
            return np.zeros(self.obs_dim, dtype=np.float32)
        return np.clip(np.concatenate([base, np.array(self._v1_obs(), dtype=np.float32)]), -1.0, 1.0)

    def _tls_ahead(self):
        if self.ego_id in traci.vehicle.getIDList():
            tls = traci.vehicle.getNextTLS(self.ego_id)
            if tls:
                return tls[0][0], tls[0][1], float(tls[0][2]), tls[0][3]
        return None

    def step(self, action):
        before = self._tls_ahead()
        obs, reward, terminated, truncated, info = super().step(action)
        # 신호 위반: 직전 스텝에 15 m 안의 빨간불이었는데 이번 스텝에 그 신호를 지나쳤으면 (교차로 진입)
        after = self._tls_ahead() if not terminated else None
        info["red_light"] = bool(before and before[3] in "rRu" and before[2] < 15
                                 and (after is None or after[:2] != before[:2]) and not info["arrived"])
        if info["red_light"]:
            reward -= float(self.rw.get("red_light_penalty", 0.0))
        # 과속: 지금 차로 제한속도를 넘은 만큼 감점 (수업 보상의 속도 기준은 vmax 하나라서 교내 시속 20 km 구간도 50 km까지 보상)
        if info["speed"] is not None and self.ego_id in traci.vehicle.getIDList():
            lim = traci.lane.getMaxSpeed(traci.vehicle.getLaneID(self.ego_id))
            over = max(0.0, info["speed"] - lim)
            info["overspeed"] = over
            reward -= float(self.rw.get("overspeed_penalty", 0.0)) * over / self.vmax
        info["tls_state"], info["tls_distance_m"] = (after[3], after[2]) if after else ("none", -1.0)
        info["arrived"] = info["arrived"] and not info["collided"]   # 충돌하면 차가 제거되어 도착으로도 잡힌다
        if info["lane_after"] is None:                               # 종료로 차가 사라진 스텝은 마지막 차로로 기록
            info["lane_after"] = info["lane_before"]
        # 수업 코드는 차로 유지(0) 명령도 applied=True로 돌려준다. 데이터 정의는 "차선 변경이 실제 적용되었는가"
        info["lane_change_applied"] = bool(info["lane_change_applied"] and info["lane_change"] != 0)
        return obs, reward, terminated, truncated, info
