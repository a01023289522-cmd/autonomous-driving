"""수업 환경(SumoHighwayEnv)을 성대역 도로망(sumo/skku_map)에서 돌리는 환경.

행동과 기본 보상은 수업 코드를 그대로 쓰고, 다음을 바꾼다:
  - 환경 v1 (SCENARIO["obs_v1"]): 관측 10개 추가(신호, 교차 차량, 제한속도), 신호 위반·과속 감점. 아래 _v1_obs
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
        # 교차 차량 관측 보완 (11/18 충돌 분석). 관측 차원은 그대로
        #  1) 교차로 안에서도 다음 교차로 기준으로 거리·양보 여부 계산 (연속 교차로에서 0으로 나오던 문제)
        #  2) 우선도로 접근 차량을 lane.getFoes로 직접 찾아 더함 (getJunctionFoes가 빠뜨림). userdoc/TraCI/Lane_Value_Retrieval.html "foes"
        #  3) 충돌 지점을 이미 빠져나간 차(foeExitDist < 0)는 뺌. 가장 가까운 차로 뽑혀 다가오는 차를 가리던 문제
        self.foe_lanes = bool(scenario.get("obs_foe_fix", False))
        if self.v1:
            self.obs_dim += self.V1_DIM
            self.observation_space = gym.spaces.Box(-1.0, 1.0, shape=(self.obs_dim,), dtype=np.float32)
        self.edges = route_edges(scenario["start_edge"], scenario["goal_edge"])
        self.warmup_seconds = float(scenario["warmup_seconds"])
        self.traffic_scale = float(scenario.get("traffic_scale", 1.0))   # 배경 교통량 배율 (난이도). sumo --scale
        self.extra_routes = list(scenario.get("extra_routes", []))         # 추가 교통 파일 (sumo/skku_map/scenarios.py)
        self.use_seeds(scenario["train_seeds"])

    def use_seeds(self, seeds):
        """이 목록의 시드를 처음부터 차례로 쓴다. 평가 전에 eval_seeds로 바꾼다."""
        self.seeds, self._next = list(seeds), 0

    def _state_file(self, seed):
        return os.path.join(STATES, f"s{seed}_w{self.warmup_seconds:.0f}_dt{self.step_length}_x{self.traffic_scale:g}"
                            + "".join(f"_{os.path.splitext(os.path.splitext(f)[0])[0]}" for f in self.extra_routes) + "_rng.xml.gz")

    def _state_ready(self, path):
        """저장한 상태가 있고 도로·교통 파일이 그 뒤로 바뀌지 않았는가."""
        return os.path.exists(path) and os.path.getmtime(path) >= max(os.path.getmtime(os.path.join(MAP, f)) for f in (*TRAFFIC_FILES, *self.extra_routes))

    def _start_sumo(self):
        seed = self.seeds[self._next % len(self.seeds)]
        self._next += 1
        self.seed_now = seed
        cmd = [checkBinary("sumo"), "-c", self.cfg_path, "--step-length", str(self.step_length),
               "--collision.action", "remove", "--collision.check-junctions", "true",
               "--no-warnings", "true", "--no-step-log", "true", "--seed", str(seed),
               "--save-state.rng", "true",   # 난수 상태까지 저장 (userdoc/Simulation/SaveAndLoad.html)
               "--scale", str(self.traffic_scale)]   # 교통량 배율: 차량을 지우거나 복제 (userdoc/sumo.html)
        state = self._state_file(seed)
        if not self._state_ready(state):
            self._make_state(cmd, state)
        if self.gui:
            cmd[0] = checkBinary("sumo-gui")
            cmd += ["--quit-on-end", "--delay", str(self.gui_delay), "--start", "-a", self._additional(True)]
        else:                                 # 화면이 없으면 배경 도형은 읽지 않는다
            cmd += ["-a", self._additional(False)]
        traci.start(cmd + ["--load-state", state, "--begin", str(self.warmup_seconds)])
        self._started = True

    def _additional(self, gui):
        files = ("vtypes.add.xml", "bus.stops.xml", "skku.add.xml") + (("bg.add.xml",) if gui else ()) + tuple(self.extra_routes)
        return ",".join(os.path.join(MAP, f) for f in files)

    def _make_state(self, cmd, state):
        """배경 교통을 warmup_seconds만큼 채운 상태를 파일로 만든다. 주행은 항상 이 파일을 불러와 시작한다.
        차로 변경 모델 내부 상태 등은 상태 파일에 저장되지 않으므로(SaveAndLoad.html Known Issues), 처음 만든 실행에서 바로
        주행하면 저장된 상태를 불러온 실행과 결과가 달라진다. 그래서 만드는 실행과 주행하는 실행을 나눈다."""
        traci.start(cmd + ["-a", self._additional(False)])
        traci.simulationStep(self.warmup_seconds)
        os.makedirs(STATES, exist_ok=True)
        tmp = f"{state}.{os.getpid()}.xml.gz"
        traci.simulation.saveState(tmp)
        traci.close()
        try:
            os.replace(tmp, state)            # 여러 학습을 동시에 돌려도 반쯤 쓴 파일을 읽지 않게
        except PermissionError:               # Windows: 다른 학습이 같은 파일을 먼저 만들어 읽는 중이면 그 파일을 쓴다
            if not os.path.exists(state):
                raise
            os.remove(tmp)

    def _insert_ego(self):
        """배경 교통을 채운 상태에서 AV를 넣는다. 들어갈 자리가 끝내 없으면 False."""
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

    @staticmethod
    def _vehicle_extra(vid):
        """차종, 진행 방향(도, 북쪽 0 시계 방향), 가속도, 방향지시등(+1 왼쪽, -1 오른쪽, 0 없음), 제동등.
        userdoc/TraCI/Vehicle_Signalling.html: bit0 오른쪽, bit1 왼쪽, bit3 제동등"""
        sig = traci.vehicle.getSignals(vid)
        return {"type": traci.vehicle.getTypeID(vid), "angle": float(traci.vehicle.getAngle(vid)),
                "accel": float(traci.vehicle.getAcceleration(vid)),
                "blinker": 1 if sig & 2 else -1 if sig & 1 else 0, "brake_light": int(bool(sig & 8))}

    def route_lane_changes(self):
        """경로를 따라가려면 필요한 차로 변경 수 (+는 행동 +1 방향 = 왼쪽, 교차로 안이면 0). getBestLanes의 offset."""
        if self.ego_id not in traci.vehicle.getIDList():
            return 0
        lane_id = traci.vehicle.getLaneID(self.ego_id)
        best = [b for b in traci.vehicle.getBestLanes(self.ego_id) if b[0] == lane_id]
        return int(best[0][3]) if best else 0

    def _road_info(self):
        """AV가 달리는 도로: 차로 수, 제한속도, 다음 교차로까지 거리, 그 교차로에서 양보해야 하는지 (도로망 파일 없이 읽을 수 있게)."""
        e = self.ego_id
        lane_id = traci.vehicle.getLaneID(e)
        links = traci.vehicle.getNextLinks(e)
        if lane_id.startswith(":") or not links:
            jd, yld = 0.0, False
        else:
            jd = traci.lane.getLength(lane_id) - traci.vehicle.getLanePosition(e)
            yld = links[0][5] in "mswg="          # 소문자 m/g, 정지(s), 전방향 정지(w): 다른 차에 양보하는 연결
        return {"ego_lane_count": int(traci.edge.getLaneNumber(traci.vehicle.getRoadID(e))),
                "ego_speed_limit": float(traci.lane.getMaxSpeed(lane_id)),
                "next_junction_m": float(jd), "next_junction_yield": bool(yld)}

    def get_privileged_state(self):
        """수업 코드와 같은 형식이되, 위치로 먼저 100 m 안 차량만 고른 뒤 나머지 값을 조회한다 (전체 약 400대를 다 조회하면 수집이 4배 느림)."""
        if self.ego_id not in traci.vehicle.getIDList():
            return {"ego_alive": False}
        ex, ey = traci.vehicle.getPosition(self.ego_id)
        vehicles = []
        for vid in traci.vehicle.getIDList():
            x, y = traci.vehicle.getPosition(vid)
            if (x - ex) ** 2 + (y - ey) ** 2 > STATE_RADIUS ** 2:
                continue
            vehicles.append({"id": vid, "x": float(x), "y": float(y), "speed": float(traci.vehicle.getSpeed(vid)),
                             "lane": int(traci.vehicle.getLaneIndex(vid)), "lane_id": traci.vehicle.getLaneID(vid),
                             "road_id": traci.vehicle.getRoadID(vid), "lane_pos": float(traci.vehicle.getLanePosition(vid)),
                             **self._vehicle_extra(vid)})
        ego = next(v for v in vehicles if v["id"] == self.ego_id)
        return {"ego_alive": True, "ego_x": ego["x"], "ego_y": ego["y"], "ego_speed": ego["speed"], "ego_lane": ego["lane"],
                "ego_lane_id": ego["lane_id"], "ego_road_id": ego["road_id"], "ego_lane_pos": ego["lane_pos"],
                "ego_angle": ego["angle"], "ego_accel": ego["accel"], **self._road_info(), "vehicles": vehicles,
                "simulation_time_s": float(traci.simulation.getTime())}

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
    # 환경 v2 관측: 수업 관측 31개 뒤에 10개를 붙인다 (SCENARIO["obs_v1"]가 False면 v0 그대로 31개)
    #   [31] 다음 신호까지 거리 /100 (신호가 없거나 100 m 밖이면 1)   [32] 빨간불  [33] 노란불
    #   [34] 현재 신호색이 바뀌기까지 남은 시간 /30
    #   [35] 다음 교차로까지 거리 /100   [36] 다음 교차로에서 양보해야 함 (신호 없는 비우선 연결)
    #   [37] 양보해야 할 교차 차량 중 가장 가까운 차의 충돌 지점까지 거리 /60 (없으면 1)  [38] 그 차 속도 /vmax
    #   [39] 양보해야 할 교차 차량 수 /3
    #   [40] 지금 차로 제한속도 /vmax
    # 경로에 필요한 차로 정보(getBestLanes)는 넣지 않는다 (v1에는 있었음): 11/17 교수님 공지 "큰 틀의 라우팅은 가능,
    #   어떤 차선으로 주행해야 하는지 등 세밀한 주행 정보는 안 됨". 차로는 수업 관측의 연결성 값과 보상으로 배운다
    # 쓰는 TraCI: getNextTLS, trafficlight.getNextSwitch, getNextLinks, getJunctionFoes
    #   (userdoc/TraCI/Vehicle_Value_Retrieval.html: next TLS, next links, junction foes)
    # ------------------------------------------------------------------
    V1_DIM = 10
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
        lane_id = traci.vehicle.getLaneID(e)
        links = traci.vehicle.getNextLinks(e)
        from_lane = lane_id                         # 다음 교차로 연결(links[0])이 시작하는 일반 차로
        if lane_id.startswith(":") and links and self.foe_lanes:
            # 교차로 안(내부 차로)에서도 getNextLinks[0]은 다음 교차로의 연결이다. 짧은 차로를 사이에 둔 연속 교차로에서
            # 거리·양보 여부가 0으로 나오던 문제 (11/18 율전로98번길 좌회전 충돌: 앞 교차로 내부 차로 약 25 m 동안 못 봄)
            out = traci.lane.getLinks(lane_id)
            from_lane = out[0][0] if out else None
        if not links or from_lane is None or from_lane.startswith(":"):
            jd, yld = 0.0, 0.0
        else:
            jd = traci.lane.getLength(from_lane) - (traci.vehicle.getLanePosition(e) if from_lane == lane_id else 0.0)
            if from_lane != lane_id:
                jd += traci.lane.getLength(lane_id) - traci.vehicle.getLanePosition(e)
            yld = float(links[0][5] in "mswg=")    # 소문자 m/g, 정지(s), 전방향 정지(w): 다른 차에 양보하는 연결
        foes = [x for x in traci.vehicle.getJunctionFoes(e, self.FOE_RANGE) if x[7]]   # egoResponse: 내가 양보할 차
        if self.foe_lanes:
            foes = [x for x in foes if x[4] > 0]   # foeExitDist: 충돌 지점을 빠져나가기까지 거리 (traci/_vehicle.py)
        if self.foe_lanes and yld and jd <= self.FOE_RANGE:
            seen = {x[0] for x in foes}
            try:
                foe_lanes = traci.lane.getFoes(from_lane, links[0][0])   # 내 연결보다 우선권이 있는 연결의 출발 차로
            except traci.TraCIException:   # 지금 차로에서 그 연결로 바로 못 감 (경로상 차로 변경이 남음)
                foe_lanes = []
            for fl in foe_lanes:
                length = traci.lane.getLength(fl)
                for v in traci.lane.getLastStepVehicleIDs(fl):
                    d = length - traci.vehicle.getLanePosition(v)        # 그 차의 정지선까지 거리 (충돌 지점 대신 근사)
                    if v not in seen and d <= self.FOE_RANGE:
                        foes.append((v, jd, d))
                        seen.add(v)
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
        # 정차 감점: 거의 서 있는데 앞이 비어 있으면 감점 (갈 수 있는데 안 가는 것).
        # 앞 = 같은 차로 앞차, 빨강·노랑 신호의 정지선 중 가까운 것. 양보할 교차 차량이 있으면 기다리는 게 맞으므로 감점 없음.
        # 막힘 감점(수업 코드)은 앞차 20 m 안에서만 붙어서 멀리 떨어져 서 있으면 피할 수 있었다 (11/18 정차 분석)
        idle = float(self.rw.get("idle_penalty", 0.0))
        info["idle"] = False
        if idle > 0 and info["speed"] is not None and self.ego_id in traci.vehicle.getIDList():
            e = self.ego_id
            lim = traci.lane.getMaxSpeed(traci.vehicle.getLaneID(e))
            if info["speed"] < self.rw.get("idle_speed_frac", 0.3) * lim:
                lead = traci.vehicle.getLeader(e, 100)
                free = lead[1] if lead else 100.0
                if after and after[3] in "rRyYu":
                    free = min(free, after[2])
                if any(f[7] for f in traci.vehicle.getJunctionFoes(e, 60)):
                    free = 0.0
                gap = self.rw.get("idle_gap", 15.0)
                if free > gap:
                    info["idle"] = True
                    # idle_scaled: 빈 공간에 비례 (15 m에서 0, 100 m에서 idle). 계단형이면 16 m든 80 m든 같은 감점이라
                    # 조금 다가가도 이득이 없어서 정지선 40–80 m 앞에 선다 (11/18 r_idle_s500 측정)
                    reward -= idle * ((min(free, 100.0) - gap) / (100.0 - gap) if self.rw.get("idle_scaled", False) else 1.0)
        info["tls_state"], info["tls_distance_m"] = (after[3], after[2]) if after else ("none", -1.0)
        info["arrived"] = info["arrived"] and not info["collided"]   # 충돌하면 차가 제거되어 도착으로도 잡힌다
        if info["lane_after"] is None:                               # 종료로 차가 사라진 스텝은 마지막 차로로 기록
            info["lane_after"] = info["lane_before"]
        # 수업 코드는 차로 유지(0) 명령도 applied=True로 돌려준다. 데이터 정의는 "차선 변경이 실제 적용되었는가"
        info["lane_change_applied"] = bool(info["lane_change_applied"] and info["lane_change"] != 0)
        return obs, reward, terminated, truncated, info
