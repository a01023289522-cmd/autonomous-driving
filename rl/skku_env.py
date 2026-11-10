"""수업 환경(SumoHighwayEnv)을 성대역 도로망(sumo/skku_map)에서 돌리는 환경.

관측·행동·보상 계산은 수업 코드를 그대로 쓰고, 도로에 묶인 부분만 바꾼다:
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
from env.sumo_env import SumoHighwayEnv

import gymnasium as gym  # noqa: E402
import traci  # noqa: E402
from sumolib import checkBinary  # noqa: E402

MAP = os.path.join(course.TEAM, "sumo", "skku_map")
STATES = os.path.join(MAP, "work", "states")
TRAFFIC_FILES = ("skku.net.xml", "skku.rou.xml", "bus.rou.xml", "parking.rou.xml", "random.rou.xml", "skku.sumocfg")
ROUTE_ID = "av_route"


def route_edges(start, goal):
    edges = json.load(open(os.path.join(MAP, "verify", "av_route_full.json"), encoding="utf-8"))["edges"]
    return edges[edges.index(start):edges.index(goal) + 1]


class SkkuEnv(SumoHighwayEnv):
    def __init__(self, scenario, mdp_sim, mdp_obs, action, reward, gui=False):
        road = {"speed_limit": scenario["speed_limit"], "num_lanes": 3, "length": 1e9}
        ego = {"depart_lane": "best", "depart_speed": 0, "accel": scenario["accel"], "decel": scenario["decel"]}
        super().__init__(os.path.join(MAP, "skku.sumocfg"), road, ego, mdp_sim, mdp_obs, action, reward, gui=gui)
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

    def step(self, action):
        obs, reward, terminated, truncated, info = super().step(action)
        info["arrived"] = info["arrived"] and not info["collided"]   # 충돌하면 차가 제거되어 도착으로도 잡힌다
        return obs, reward, terminated, truncated, info
