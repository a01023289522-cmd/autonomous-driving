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
import random
import subprocess
import sys

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
        self.close_fix = bool(scenario.get("obs_close_fix", False))
        self.close_signed = bool(scenario.get("obs_close_signed", False))
        self.inside_fix = bool(scenario.get("obs_inside_fix", False))
        self._prev_lane, self._entry_yield = "", 0.0
        self.turn_obs = bool(scenario.get("obs_turn", False))
        if self.v1:
            self.obs_dim += self.V1_DIM + (3 if self.turn_obs else 0)
            self.observation_space = gym.spaces.Box(-1.0, 1.0, shape=(self.obs_dim,), dtype=np.float32)
        self.edges = route_edges(scenario["start_edge"], scenario["goal_edge"])
        self.warmup_seconds = float(scenario["warmup_seconds"])
        self.traffic_scale = float(scenario.get("traffic_scale", 1.0))   # 배경 교통량 배율 (난이도). sumo --scale
        self.extra_routes = list(scenario.get("extra_routes", []))         # 추가 교통 파일 (sumo/skku_map/scenarios.py)
        # 난이도 섞기: [{"traffic_scale": 1.4}, {"extra_routes": [...]} ...]. 시드마다 하나를 고정으로 고른다 (seed % 개수).
        # 비어 있으면 위의 traffic_scale·extra_routes 하나만 쓴다. 11/18 r_rb_stage1: 어려운 교통만으로 학습하면 기본 교통 성능이
        # 나빠졌다(충돌 20% → 28%) → 기본 교통과 섞어서 학습한다
        self.mix = [dict(m) for m in scenario.get("difficulty_mix", [])]
        self._base_traffic = (self.traffic_scale, list(self.extra_routes))
        # 출발점 섞기: 학습 시드마다 출발 엣지를 이 목록에서 하나 고른다 (같은 엣지를 여러 번 넣으면 비중이 커진다).
        # 11/18: 위험 진입은 에피소드당 약 1회라 30만 스텝에도 300번 정도만 겪는다. r_segment(율전로98번길 출발만)는 회전교차로 충돌
        # 12 → 1이었지만 앞 구간 신호를 잊고(빨간불 위반 0.9회) 달려 들어오는 상황에 약했다 → 전체 경로 출발과 섞는다.
        # 중간 출발은 mid_depart_speed(기본 "max", userdoc/Definition_of_Vehicles... departSpeed)로 투입해 달려 들어오는 상황을 만든다.
        # 섞기 두 가지 모두 학습 시드(train_seeds)에만 적용한다. 평가 시드는 항상 기본 출발·기본 교통
        self.start_mix = list(scenario.get("start_mix", []))
        self.start_delay_max = float(scenario.get("start_delay_max", 0.0))
        # alley_gate: 한 대 폭 골목(bidi)에서 일반 차량은 반대 방향 차가 있으면 입구에서 기다린다 (sumo/skku_map/alley.py).
        # AV에는 적용하지 않는다 (양보는 학습). 워밍업 상태 파일도 이 규칙으로 만든다 (파일 이름 끝 _ag)
        self.alley_gate = bool(scenario.get("alley_gate", False))
        self._gate = None
        self.mid_depart_speed = str(scenario.get("mid_depart_speed", "max"))
        self._full_edges = list(self.edges)
        self._train_seeds = set(scenario.get("train_seeds", []))
        self.use_seeds(scenario["train_seeds"])

    def use_seeds(self, seeds):
        """이 목록의 시드를 처음부터 차례로 쓴다. 평가 전에 eval_seeds로 바꾼다."""
        self.seeds, self._next = list(seeds), 0

    def _state_file(self, seed):
        return os.path.join(STATES, f"s{seed}_w{self.warmup_seconds:.0f}_dt{self.step_length}_x{self.traffic_scale:g}"
                            + "".join(f"_{os.path.splitext(os.path.splitext(f)[0])[0]}" for f in self.extra_routes)
                            + ("_ag" if self.alley_gate else "") + "_rng.xml.gz")

    def _state_ready(self, path):
        """저장한 상태가 있고 도로·교통 파일이 그 뒤로 바뀌지 않았는가."""
        return os.path.exists(path) and os.path.getmtime(path) >= max(os.path.getmtime(os.path.join(MAP, f)) for f in (*TRAFFIC_FILES, *self.extra_routes))

    def _start_sumo(self):
        seed = self.seeds[self._next % len(self.seeds)]
        self._next += 1
        self.seed_now = seed
        train = seed in self._train_seeds
        m = self.mix[seed % len(self.mix)] if self.mix and train else {}
        self.traffic_scale = float(m.get("traffic_scale", self._base_traffic[0]))
        self.extra_routes = list(m.get("extra_routes", self._base_traffic[1]))
        self.edges = self._full_edges
        if self.start_mix and train:
            start = self.start_mix[random.Random(f"start{seed}").randrange(len(self.start_mix))]
            self.edges = self._full_edges[self._full_edges.index(start):]
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
        self._gate = None
        if self.alley_gate:
            sys.path.insert(0, MAP) if MAP not in sys.path else None
            from alley import AlleyGate
            self._gate = AlleyGate(traci, self.ego_id).setup()
        # start_delay_max: 경로 중간 출발(start_mix)일 때 AV 투입을 0~start_delay_max초 무작위로 늦춘다 (학습 시드만, 시드별 고정).
        # 11/19 측정: 정문 앞 출발 에피소드 8개가 모두 t≈621초, 빨간불 남은 17~18초에 정문에 닿음 (신호 주기 87초 고정, 투입 시각 고정)
        #   → 학습 중 정문 빨간불은 늘 곧 끝나는 빨간불이라 멀리 서도 손해가 몇 초뿐 (갈래 비교 이득 평균 +0.6에 그침)
        dmax = self.start_delay_max
        if dmax > 0 and self.start_mix and train and self.edges is not self._full_edges:
            delay = random.Random(f"delay{seed}").uniform(0.0, dmax)
            target = self.warmup_seconds + round(delay / self.step_length) * self.step_length
            if self._gate is None:
                traci.simulationStep(target)
            while self._gate is not None and traci.simulation.getTime() < target - 1e-6:
                self._gate.step()
                traci.simulationStep()
        self._started = True

    def _additional(self, gui):
        files = ("vtypes.add.xml", "bus.stops.xml", "skku.add.xml") + (("bg.add.xml",) if gui else ()) + tuple(self.extra_routes)
        return ",".join(os.path.join(MAP, f) for f in files)

    def _make_state(self, cmd, state):
        """배경 교통을 warmup_seconds만큼 채운 상태를 파일로 만든다. 주행은 항상 이 파일을 불러와 시작한다.
        차로 변경 모델 내부 상태 등은 상태 파일에 저장되지 않으므로(SaveAndLoad.html Known Issues), 처음 만든 실행에서 바로
        주행하면 저장된 상태를 불러온 실행과 결과가 달라진다. 그래서 만드는 실행과 주행하는 실행을 나눈다."""
        # TraCI가 아니라 sumo 실행 파일을 직접 돌려 저장한다 (--save-state.times, userdoc/Simulation/SaveAndLoad.html).
        # 11/19 확인: libsumo로 만든 상태 파일은 난수 상태(rngState)가 TraCI로 만든 것과 달라서, 캐시가 없는 PC에서 libsumo로
        # 처음 평가하면 같은 시드라도 교통이 달라졌다. 실행 파일로 만들면 TraCI로 만든 기존 캐시와 내용이 같다(직접 비교).
        os.makedirs(STATES, exist_ok=True)
        tmp = f"{state}.{os.getpid()}.xml.gz"
        if self.alley_gate:                   # 골목 규칙을 지키며 채운다: TraCI 소켓 + sumo 실행 파일 (아래 방식과 같은 난수 상태)
            subprocess.run([sys.executable, os.path.join(MAP, "alley.py"), "warmup", str(self.warmup_seconds + 1),
                            str(self.warmup_seconds), tmp, checkBinary("sumo"), *cmd[1:], "-a", self._additional(False)],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run([checkBinary("sumo"), *cmd[1:], "-a", self._additional(False), "--end", str(self.warmup_seconds + 1),
                            "--save-state.times", str(self.warmup_seconds), "--save-state.files", tmp],
                           check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        traci.vehicle.add(self.ego_id, ROUTE_ID, typeID="ego_type", departLane="best", departPos="free",
                          departSpeed="0" if self.edges[0] == self._full_edges[0] else self.mid_depart_speed)
        traci.vehicle.setSpeedMode(self.ego_id, 0)            # 수업 환경과 같음: 안전 제어는 정책 몫
        traci.vehicle.setLaneChangeMode(self.ego_id, 0)
        for _ in range(240):
            traci.simulationStep()
            if self.ego_id in traci.vehicle.getIDList():
                return True
        return False

    def reset(self, seed=None, options=None):
        gym.Env.reset(self, seed=seed)
        self._prev_lane, self._entry_yield = "", 0.0
        self._box_prev_lane = ""
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
        self._prev_accel = None
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
            # obs_inside_fix (접근 단계): 이미 교차로 안(내 연결의 내부 차로와 교차하는 내부 차로)에 있는 차. 위의 출발 차로 목록과
            # getJunctionFoes 둘 다 이 차를 놓칠 때가 있다 (11/19 시드 1112: 5갈래 교차로 4493735400, 교차 차량 관측 '없음'인 채
            # 시속 21 km로 진입해 교차로 안 차와 충돌). 거리는 그 차가 자기 내부 차로 끝까지 남은 거리로 근사
            via = links[0][4] if len(links[0]) > 4 else ""
            if self.inside_fix and via:
                try:
                    cross = traci.lane.getFoes(via, "")
                except traci.TraCIException:
                    cross = []
                for fl in cross:
                    length = traci.lane.getLength(fl)
                    for v in traci.lane.getLastStepVehicleIDs(fl):
                        if v not in seen and v != e:
                            foes.append((v, jd, max(0.0, length - traci.vehicle.getLanePosition(v))))
                            seen.add(v)
        if self.inside_fix:
            ins = self._inside_foes(e, lane_id)
            if ins is not None:                    # 양보 연결로 들어온 교차로 안: 그 교차로 기준으로 바꿔 준다
                jd, yld, foes = 0.0, 1.0, ins
        # 한 대 폭 골목 입구 (alley_gate, 11/21): 골목 안에 반대 방향 차가 있거나 들어오는 중이면 입구를 '양보할 교차로'로 보고
        # 그 차를 양보 상대 칸에 넣는다 (거리 = 그 차가 내 입구까지 남은 거리). 관측 개수는 그대로. 골목 안에 들어선 뒤에는
        # 마주 오는 차가 앞차 관측으로 보인다 (getLeader가 bidi 차로의 반대 방향 차를 돌려줌, 11/21 확인)
        onc = self._gate.oncoming(e) if self._gate is not None else None
        if onc is not None and onc[1]:
            jd, yld = onc[0], 1.0
            foes = [(v, onc[0], dist) for v, dist in onc[1]]
        if foes:
            near = min(foes, key=lambda x: x[2])
            f += [min(jd, 100) / 100, yld, min(near[2], self.FOE_RANGE) / self.FOE_RANGE,
                  traci.vehicle.getSpeed(near[0]) / self.vmax, min(len(foes), 3) / 3]
        else:
            f += [min(jd, 100) / 100, yld, 1.0, 0.0, 0.0]
        f.append(traci.lane.getMaxSpeed(lane_id) / self.vmax)
        if self.turn_obs:
            # obs_turn: 경로상 다음 교차로에서 갈 방향 (좌, 직진, 우) 원핫. 내비게이션의 "앞에서 좌회전" 수준 (차로 지시는 아님).
            # 11/19: 정문 앞 일월로(3차로 맨 왼쪽, 좌회전)가 서부로 5552317710#2(3차로, 직진)와 관측이 같아 정문 앞에서만 멀리 섬.
            # getNextLinks의 direction: s 직진, l/L 좌, r/R 우, t 유턴 (userdoc/TraCI/Vehicle_Value_Retrieval.html next links)
            d = links[0][6] if links and len(links[0]) > 6 else "s"
            f += [float(d in "lLt"), float(d == "s"), float(d in "rR")]
        return f

    def _get_obs(self):
        base = super()._get_obs()
        if not self.v1:
            return base
        if self.ego_id not in traci.vehicle.getIDList():
            return np.zeros(self.obs_dim, dtype=np.float32)
        if self.close_fix:
            base = self._close_fix(base)
        return np.clip(np.concatenate([base, np.array(self._v1_obs(), dtype=np.float32)]), -1.0, 1.0)

    def _inside_foes(self, e, lane_id):
        """obs_inside_fix: 양보해야 하는 연결로 교차로에 들어온 뒤, 그 교차로 안에서 교차하는 차를 관측에 넣는다.
        기존 관측은 내부 차로에 들어서면 다음 교차로 기준(양보 0, 교차 차량은 getJunctionFoes)으로 바뀌는데, 지금 있는 교차로 안에서
        내 경로와 교차하는 내부 차로의 차는 getJunctionFoes에 안 나올 때가 있다. 11/19 측정: 율전로98번길 좌회전 495951808 충돌
        (시드 1110, 1174)이 이것 — 들어선 직후 '양보 0, 교차 차량 없음'이 되고 AV가 가속(+0.95).
        lane.getFoes(내부 차로, "") = 교차하는 내부 차로 목록 (userdoc/TraCI/Lane_Value_Retrieval.html foes).
        반환: None(해당 없음) 또는 [(차, 0, 그 차가 자기 내부 차로 끝까지 남은 거리)]"""
        if not lane_id.startswith(":"):
            if self._prev_lane != lane_id:
                self._prev_lane, self._entry_yield = lane_id, 0.0
            return None
        junction = lane_id[1:].rsplit("_", 2)[0]
        if not self._prev_lane.startswith(":"):    # 방금 들어옴: 들어온 연결의 신호 상태로 양보 여부 기록
            st = [lk[5] for lk in traci.lane.getLinks(self._prev_lane) if lk[4] == lane_id] if self._prev_lane else []
            self._entry_yield = float(bool(st) and st[0] in "mswg=")
            self._entry_junction = junction
        self._prev_lane = lane_id
        if not self._entry_yield or getattr(self, "_entry_junction", None) != junction:
            return None
        out = []
        try:
            foe_lanes = traci.lane.getFoes(lane_id, "")
        except traci.TraCIException:
            foe_lanes = []
        for fl in foe_lanes:
            length = traci.lane.getLength(fl)
            for v in traci.lane.getLastStepVehicleIDs(fl):
                if v != e:
                    out.append((v, 0.0, max(0.0, length - traci.vehicle.getLanePosition(v))))
        return out

    def _close_fix(self, base):
        """obs_close_fix: 내 차로 앞뒤 차가 minGap보다 가까우면 '없음'(1, −1)이 아니라 거리 0으로 준다.
        SUMO getLeader/getFollower 거리는 내 앞범퍼 + minGap에서 잰다(userdoc/TraCI/Vehicle_Value_Retrieval.html)라 아주 가까우면
        음수인데, 수업 코드 _neighbor는 gap < 0을 None(없음)으로 버린다. 11/19 측정: 교차로 495951447 충돌 4건이 모두 이것 —
        합류하던 차에 다가가다 거리가 음수가 되는 순간 관측이 '앞차 없음'으로 바뀌고 AV가 가속(+0.99)해 추돌.
        관측 [9],[10] = 현재 차로 앞차 거리·상대속도, [11],[12] = 뒤차 (수업 obs_offsets 순서 +2,+1,0,−1,−2)."""
        e, v = self.ego_id, traci.vehicle.getSpeed(self.ego_id)
        lead = traci.vehicle.getLeader(e, self.visibility)
        # obs_close_signed: 0으로 고정하지 않고 음수 거리 그대로 (minGap 2.5 m면 닿는 순간 약 −0.05). 0 고정은 2.5 m를 다가가는 동안
        # 관측이 안 변해서 AV가 시속 3~4 km로 기어가다 닿았다 (11/19 r_s9 15만 시드 1014·1027)
        sg = (lambda g: g / self.visibility) if self.close_signed else (lambda g: 0.0)
        if lead and lead[0] and lead[1] < 0:
            base[9], base[10] = sg(lead[1]), float(np.clip((traci.vehicle.getSpeed(lead[0]) - v) / self.vmax, -1.0, 1.0))
        foll = traci.vehicle.getFollower(e, self.visibility)
        if foll and foll[0] and foll[1] < 0:
            base[11], base[12] = -sg(foll[1]), float(np.clip((traci.vehicle.getSpeed(foll[0]) - v) / self.vmax, -1.0, 1.0))
        return base

    def _tls_ahead(self):
        if self.ego_id in traci.vehicle.getIDList():
            tls = traci.vehicle.getNextTLS(self.ego_id)
            if tls:
                return tls[0][0], tls[0][1], float(tls[0][2]), tls[0][3]
        return None

    YIELD_TTC = 3.0

    def _yield_risk(self):
        """양보해야 하는 연결 앞이면 (지금 차로, 우선 차량이 충돌 지점에 오기까지 가장 짧은 시간 s), 아니면 None.
        우선 차량 = getJunctionFoes 중 egoResponse(내가 양보)이고 아직 충돌 지점을 빠져나가지 않은 차 (foeExitDist > 0).
        충돌 지점 안에 있는 차(foeDist < 0)는 0초. traci/_vehicle.py getJunctionFoes"""
        e = self.ego_id
        if e not in traci.vehicle.getIDList():
            return None
        lane = traci.vehicle.getLaneID(e)
        links = traci.vehicle.getNextLinks(e)
        if lane.startswith(":") or not links or links[0][5] not in "mswg=":
            return None
        ttc = [max(x[2], 0.0) / max(traci.vehicle.getSpeed(x[0]), 0.1)
               for x in traci.vehicle.getJunctionFoes(e, self.FOE_RANGE) if x[7] and x[4] > 0]
        if self.foe_lanes:   # 관측 보완과 같은 차량 목록: getJunctionFoes가 빠뜨리는 우선도로 접근 차량 (11/18 seed 1024: TTC 99 → 0.4초)
            try:
                for fl in traci.lane.getFoes(lane, links[0][0]):
                    length = traci.lane.getLength(fl)
                    for v in traci.lane.getLastStepVehicleIDs(fl):
                        d = length - traci.vehicle.getLanePosition(v)
                        if d <= self.FOE_RANGE:
                            ttc.append(d / max(traci.vehicle.getSpeed(v), 0.1))
            except traci.TraCIException:
                pass
        return lane, min(ttc, default=float("inf"))

    def step(self, action):
        before = self._tls_ahead()
        ywt = float(self.rw.get("yield_penalty", 0.0))
        yrisk = self._yield_risk() if ywt > 0 else None
        # 골목 입구 직전(아직 교차로 밖)에서만 본다: 교차로 안에서 계속 보면 들어선 뒤 스텝마다 감점된다
        alley_before = self._gate.oncoming(self.ego_id) if (self._gate is not None and ywt > 0
                                                            and self.ego_id in traci.vehicle.getIDList()
                                                            and not traci.vehicle.getLaneID(self.ego_id).startswith(":")) else None
        if self._gate is not None:
            self._gate.step()
        obs, reward, terminated, truncated, info = super().step(action)
        # 양보 위반: 양보해야 하는 연결 앞에서, 우선 차량이 YIELD_TTC초 안에 오는데 교차로에 들어갔으면 1회 감점.
        # 충돌 감점은 실제로 부딪힐 때만 붙어 드물다 (11/18 임재성: 충돌 감점 크기로는 양보 실패가 안 줄어듦).
        # 신호 위반 감점(red_light_penalty)을 무신호 교차로·회전교차로에 적용한 것
        info["yield_violation"] = False
        # 골목: 반대 방향 차가 골목 안에 있거나 들어오는 중인데 입구 교차로에 들어서면 양보 위반 (같은 감점)
        if ywt > 0 and alley_before and alley_before[1] and self.ego_id in traci.vehicle.getIDList():
            if traci.vehicle.getLaneID(self.ego_id).startswith(":") and alley_before[0] < 15.0:
                info["yield_violation"] = True
                reward -= ywt
        if yrisk and not info["yield_violation"] and self.ego_id in traci.vehicle.getIDList():
            now = traci.vehicle.getLaneID(self.ego_id)
            if now != yrisk[0] and now.startswith(":") and yrisk[1] < self.rw.get("yield_ttc", self.YIELD_TTC):
                info["yield_violation"] = True
                reward -= ywt
        # box_penalty (꼬리물기): 이번 스텝에 교차로(내부 차로)에 들어섰는데, 바로 앞 차가 서 있고 교차로를 빠져나간 뒤 내 차가 설
        # 자리(5 m)가 없으면 1회 감점. 도로교통법 교차로 통행 방법(앞이 막혀 교차로를 빠져나갈 수 없으면 진입하지 않음)을 보상으로.
        # 11/19 재생: 495951447 충돌(r_s5·r_s9·r_s13·r_s17)이 모두 출구 차로 시작점에 선 합류 차 뒤로 교차로에 들어가 그 안에서 추돌.
        # AV를 움직이게 하는 보상(정차 감점·빨간불 접근 등)을 키울 때마다 여기 충돌이 늘었다 (r_s16 시드 200개 9건, r_s17 시드 100개 3~9건)
        info["box_block"] = False
        bw = float(self.rw.get("box_penalty", 0.0))
        if bw > 0 and not terminated and self.ego_id in traci.vehicle.getIDList():
            now = traci.vehicle.getLaneID(self.ego_id)
            prev = getattr(self, "_box_prev_lane", "")
            if now.startswith(":") and prev and not prev.startswith(":"):
                ld = traci.vehicle.getLeader(self.ego_id, 60)
                if ld and ld[0] and traci.vehicle.getSpeed(ld[0]) < 0.5:
                    rem = traci.lane.getLength(now) - traci.vehicle.getLanePosition(self.ego_id)
                    if ld[1] < rem + 5.0:
                        info["box_block"] = True
                        reward -= bw
            self._box_prev_lane = now
        # 신호 위반: 직전 스텝에 15 m 안의 빨간불이었는데 이번 스텝에 그 신호를 지나쳤으면 (교차로 진입)
        after = self._tls_ahead() if not terminated else None
        info["red_light"] = bool(before and before[3] in "rRu" and before[2] < 15
                                 and (after is None or after[:2] != before[:2]) and not info["arrived"])
        if info["red_light"]:
            reward -= float(self.rw.get("red_light_penalty", 0.0))
        # 빨간불 접근: 같은 빨간불(100 m 안)을 사이에 두고 정지선 쪽으로 다가간 거리 × red_approach / 100. 신호 하나당 최대
        # red_approach. 11/19 측정: 다차로 접근로(정문 앞 일월로, 출발지 서부로)에서 앞이 비었는데도 정지선 50–68 m 앞에 섬.
        # 정차 감점(스텝당 약 0.02)을 받으면서도 섬 — 다가가는 이득(속도 보상 약 0.7)이 학습에 너무 약함. 지나치면 신호 위반 −5
        ra = float(self.rw.get("red_approach", 0.0))
        if ra > 0 and before and after and after[:2] == before[:2] and before[3] in "rRu" and after[3] in "rRu"                 and before[2] <= 100:
            reward += ra * max(0.0, before[2] - after[2]) / 100.0
        # 과속: 지금 차로 제한속도를 넘은 만큼 감점 (수업 보상의 속도 기준은 vmax 하나라서 교내 시속 20 km 구간도 50 km까지 보상)
        if info["speed"] is not None and self.ego_id in traci.vehicle.getIDList():
            lim = traci.lane.getMaxSpeed(traci.vehicle.getLaneID(self.ego_id))
            over = max(0.0, info["speed"] - lim)
            info["overspeed"] = over
            reward -= float(self.rw.get("overspeed_penalty", 0.0)) * over / self.vmax
        # 앞차 시간 간격: 수업 코드의 close_gap은 6 m 고정이라 시속 20 km 이상으로 다가가면 6 m 안에 들어온 순간 이미 늦다
        # (11/18 r_idle_scaled 출발 직후 추돌: 10 m 앞 앞차에 상대속도 -3 m/s로 접근). headway_s를 주면 기준을
        # max(6 m, 내 속도 × headway_s)로 넓혀 같은 close_gap_penalty를 준다. 6 m 안은 수업 코드가 이미 감점
        hw = float(self.rw.get("headway_s", 0.0))
        if hw > 0 and info["gap"] is not None and info["speed"] is not None:
            if float(self.rw["close_gap_threshold"]) <= info["gap"] < info["speed"] * hw:
                reward -= float(self.rw["close_gap_penalty"])
        # 앞차 TTC: 같은 차로 앞차에 다가가는 중이고 TTC(간격 / 접근 속도)가 ttc_s 미만이면 ttc_penalty × (ttc_s − TTC)/ttc_s.
        # 11/18 측정(r_q2 10만, 12 시드): 정상 에피소드에서 TTC<3초는 앞차 있는 스텝의 0.57%(그중 59%는 이미 감속 중),
        # 충돌 3건(초록불 직후 회전하며 느려지는 앞차 추돌)은 충돌 약 3초 전부터 계속 3초 미만. 시간 간격 감점은 저속에서
        # 기준 거리가 짧아(4 m/s → 8 m) 충돌 2초 전에야 붙었다. 교차로 양보 상대에는 쓰지 않는다 (같은 차로 앞차만)
        tp = float(self.rw.get("ttc_penalty", 0.0))
        if tp > 0 and not terminated and info["gap"] is not None and self.ego_id in traci.vehicle.getIDList():
            lead = traci.vehicle.getLeader(self.ego_id, self.visibility)
            if lead:
                closing = info["speed"] - traci.vehicle.getSpeed(lead[0])
                ts = float(self.rw.get("ttc_s", 3.0))
                if closing > 0.1 and lead[1] / closing < ts:
                    reward -= tp * (ts - lead[1] / closing) / ts
        # queue_fix: 앞차가 서 있으면(신호 대기열 등) 수업 코드의 막힘 감점을 되돌리고, 나도 서 있으면 6 m 간격 감점도 되돌린다.
        # 11/18 측정(r_idle_scaled 5 시드): AV와 앞차가 둘 다 서 있던 1045스텝 모두 간격 15 m 이상(중앙값 41 m). 막힘 감점(앞차 20 m 안,
        # 느림)과 6 m 간격 감점(정상 대기 간격 2.5 m에서 80초 대기 −16, 충돌 −5보다 큼)이 대기열에 붙어 서는 것을 벌하고,
        # 정차 감점은 앞으로 밀어서 그 사이(약 40 m)에서 섰다. 달리는 중에는 두 감점 그대로 (꼬리물기 방지, 느린 차 추월)
        if self.rw.get("queue_fix", False) and not terminated and info["gap"] is not None and self.ego_id in traci.vehicle.getIDList():
            lead = traci.vehicle.getLeader(self.ego_id, self.visibility)
            # 정류장에 선 버스도 대기열과 같이 본다: 율전성당·성균관대역 정류장 바로 뒤(약 60 m)는 0번 차로로만 경로가 이어져서
            # 추월하면 돌아오지 못하고 갇힌다 (11/18 r_safe_mix: 5552317710#2 왼쪽 차로 끝 시간초과 15/20). 버스 뒤에 붙어서 기다리게 한다.
            # 이전 모델은 정류장 버스 17–24 m 뒤에 섰다(버스 20 m 안 막힘 감점 회피)
            if lead and traci.vehicle.getSpeed(lead[0]) < 0.5:
                g, v = info["gap"], info["speed"]
                if g < float(self.rw.get("blocked_gap", 20.0)) and v < float(self.rw.get("blocked_speed_frac", 0.7)) * self.vmax:
                    reward += float(self.rw.get("blocked_penalty", 0.0))
                # queue_approach: 서 있는 앞차에 '세울 수 있는 속도'로 다가가는 중이면 6 m 간격 감점도 되돌린다 (간격 0 이상일 때만,
                # 0 = 앞범퍼에서 minGap 2.5 m). 11/19 갈래 비교(r_s8, 시드 1003): 앞차 10 m 뒤에서 3 m 뒤까지 다가가면 간격 감점이
                # 스텝마다 약 −0.085 붙어 할인합 −0.68 (그대로 서 있으면 +0.18) → 서 있는 앞차 뒤 정지 간격 중앙값 약 16 m
                # queue_min_gap·queue_max_speed: 11/19 r_s13(간격 0 이상, 최대 3 m/s 허용) 재생에서 서 있는 앞차에 0.7~2 m/s로 다가가다
                # 가속 명령 −0.01~−0.05(거의 안 멈춤)로 추돌 3건 → 다가갈 수 있는 간격·속도를 좁히는 값
                qmin = float(self.rw.get("queue_min_gap", 0.0)); qmax = float(self.rw.get("queue_max_speed", 3.0))
                creep = self.rw.get("queue_approach", False) and g >= qmin and v <= min(qmax, (2 * 2.0 * (g - qmin)) ** 0.5)
                # queue_strict: 아직 움직이는데(0.1 m/s 이상) 서 있는 앞차까지 1.5 m 안이면 되돌리지 않는다. 11/19 새 시드 재생(r_s21,
                # 회전교차로 진입로 충돌 3건 1210·1272·1282): 대기열에서 0.2~1.8 m/s로 기어가 앞차에 닿음, 가속 명령 −0.01~+0.12.
                # 0.5 m/s 미만이면 간격 감점을 되돌려 줘서 0.2~0.4 m/s로 앞차 1 m 안까지 기어가는 것이 감점 없이 가능했다
                stopped_ok = v < 0.5 and not (self.rw.get("queue_strict", False) and v >= 0.1 and g < 1.5)
                if g < float(self.rw["close_gap_threshold"]) and (stopped_ok or creep):
                    reward += float(self.rw["close_gap_penalty"])
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
                gap = self.rw.get("idle_gap", 15.0)
                # idle_gap_queue: 앞을 막는 것이 '서 있는 앞차'면 이 기준을 쓴다 (queue_approach와 함께). 8 m 기준은 6 m 간격 감점과
                # 부딪히지 않게 정한 값인데, queue_approach가 그 충돌을 없앤다
                if lead and lead[0] and "idle_gap_queue" in self.rw and traci.vehicle.getSpeed(lead[0]) < 0.5:
                    gap = float(self.rw["idle_gap_queue"])
                if after and after[3] in "rRyYu" and after[2] < free:
                    free = after[2]
                    # idle_gap_tls: 앞을 막는 것이 정지선이면 다른 기준을 쓴다. idle_gap(8 m)은 앞차 간격 기준이라 정지선 앞에서도
                    # 8 m 안으로 다가갈 이유가 없었다 (11/19 r_s5: 정지선까지 중앙값 8.5 m). 앞차 기준을 줄이면 수업 코드의
                    # 6 m 근접 감점과 부딪히므로 정지선에만 적용
                    gap = self.rw.get("idle_gap_tls", gap)
                fix = self.rw.get("idle_fix", False)
                # idle_fix: 면제는 실제 양보 상대만 (아직 충돌 지점을 안 빠져나갔고 60 m 안). 고치기 전에는 이미 지나간 차·먼 차도
                # 면제 사유가 됐다 (getJunctionFoes 특성, 11/18 관측 점검과 같은 문제)
                foes = [f for f in traci.vehicle.getJunctionFoes(e, 60) if f[7] and (not fix or (f[4] > 0 and f[2] < 60))]
                if foes:
                    free = 0.0
                if free > gap:
                    info["idle"] = True
                    # idle_scaled: 빈 공간에 비례 (15 m에서 0, 100 m에서 idle). 계단형이면 16 m든 80 m든 같은 감점이라
                    # 조금 다가가도 이득이 없어서 정지선 40–80 m 앞에 선다 (11/18 r_idle_s500 측정)
                    scale = (min(free, 100.0) - gap) / (100.0 - gap) if self.rw.get("idle_scaled", False) else 1.0
                    # idle_fix: 교차로 안에서 서 있으면 빈 거리와 상관없이 최대 감점 (교차로를 막고 섬. 11/18 측정: 정지 71회 중
                    # 11회가 서부로 합류 교차로 등 무신호 교차로 안, 멀리 있는 빨간불을 보고 그 자리에 섬)
                    if fix and traci.vehicle.getLaneID(e).startswith(":"):
                        scale = 1.0
                    reward -= idle * scale
                    # red_wait: 빨간불이고 앞을 막는 게 정지선(앞차 아님)인데 멀리 서 있으면 같은 비례로 더 감점. 11/19 갈래 비교(정문 앞,
                    # 학습 시드 12개): 정지선까지 다가가면 할인 보상이 평균 +0.5뿐(범위 −0.3~+1.0)이라 가치 함수는 알아도 행동은 안 바뀜.
                    # 전체 정차 감점이나 빨간불 접근 보상을 키우면 다른 곳 충돌이 늘어서(r_s6, r_s7b) 이 상황에만 준다
                    rw_ = float(self.rw.get("red_wait_penalty", 0.0))
                    if rw_ > 0 and after and after[3] in "rRu" and free == after[2]:
                        reward -= rw_ * scale
        # 승차감: jerk_penalty × max(0, |Δa| − jerk_deadzone)², a는 −1~1 가속 명령. 11/18 측정: 급제동(≤−3 m/s²) 5.4회/km,
        # 가속↔감속 전환 19회/km, 명령 변화량 중앙값 0.01, 0.5 넘게 급변하는 스텝 4.3%.
        # 문턱을 두는 이유: 문턱 없이 Δa²로 하면 학습 노이즈(std 0.28)만으로 감점이 속도 보상의 27%가 되어(실측) 정책이
        # 매끄럽게 달리는 법보다 탐색 노이즈를 줄이는 법을 먼저 배운다
        jp = float(self.rw.get("jerk_penalty", 0.0))
        a_now = float(np.clip(info["accel_raw"], -1.0, 1.0)) if info.get("accel_raw") is not None else None
        if jp > 0 and a_now is not None and self._prev_accel is not None and not terminated:
            reward -= jp * max(0.0, abs(a_now - self._prev_accel) - float(self.rw.get("jerk_deadzone", 0.5))) ** 2
        self._prev_accel = a_now
        info["tls_state"], info["tls_distance_m"] = (after[3], after[2]) if after else ("none", -1.0)
        info["arrived"] = info["arrived"] and not info["collided"]   # 충돌하면 차가 제거되어 도착으로도 잡힌다
        if info["lane_after"] is None:                               # 종료로 차가 사라진 스텝은 마지막 차로로 기록
            info["lane_after"] = info["lane_before"]
        # 수업 코드는 차로 유지(0) 명령도 applied=True로 돌려준다. 데이터 정의는 "차선 변경이 실제 적용되었는가"
        info["lane_change_applied"] = bool(info["lane_change_applied"] and info["lane_change"] != 0)
        return obs, reward, terminated, truncated, info
