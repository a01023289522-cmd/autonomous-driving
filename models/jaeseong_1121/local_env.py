"""jaeseong_1121_final용 환경 (11/21 임재성). 팀원(mingi) models/local_b/local_env.py를 바탕으로 관측 처리를 더했다.
기본값이 최종 설정이다 (46칸). 각 처리는 AD_* 환경 변수로 끄거나 바꿀 수 있다. 자세한 내용은 README.md."""
import json
import numpy as np
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEMO_STATE = HERE / "traffic_1054.xml.gz"
STOP_OFFSET = float(os.environ.get("AD_STOP_OFFSET", "4.5"))
QUEUE_MODE = int(os.environ.get("AD_QUEUE_MODE", "3"))
QUEUE_OFFSET = float(os.environ.get("AD_QUEUE_OFFSET", "7"))   # 앞차 꽁무니에서 이만큼 뒤가 목표
LEAD_STOPPED = float(os.environ.get("AD_LEAD_STOPPED", "1.0"))
MASK_MIN = float(os.environ.get("AD_MASK_MIN", "10"))
YELLOW_FIX = int(os.environ.get("AD_YELLOW_FIX", "1"))
BOX_GUARD = int(os.environ.get("AD_BOX_GUARD", "1"))
SPEED_OBS = int(os.environ.get("AD_SPEED_OBS", "1"))
FAR_LEAD = int(os.environ.get("AD_FAR_LEAD", "0"))
TLS_RANGE = float(os.environ.get("AD_TLS_RANGE", "70"))
TLS_RANGE_VMIN = float(os.environ.get("AD_TLS_RANGE_VMIN", "5"))   # 이 속도(m/s) 넘게 달릴 때만 먼 신호를 숨긴다   # 이 거리보다 먼 신호는 관측에서 숨긴다 (11/21)     # 1: 같은 차로 100 m 안 앞차 거리·상대속도 2칸 더 (48칸, 11/21)   # 1: 앞 50 m 안 제한 속도와 거리 2칸을 관측 끝에 더한다 (46칸, 11/21)   # 1: 교차로 건너편에 들어갈 자리가 없으면 교차로 입구를 정지선으로 (11/21)  # 1: 노란불 다음 단계를 보고 빨강/초록으로 바로잡는다 (11/21)   # 모드 3: 앞차가 이 거리(범퍼, m) 안이면 실제 관측으로 돌린다  # 앞차가 이 속도(m/s) 미만이면 서 있다고 본다
sys.path.insert(0, str(HERE.parents[1] / "rl"))
from skku_env import SkkuEnv, traci


def read_config(path=HERE / "config.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalBEnv(SkkuEnv):
    V1_DIM = SkkuEnv.V1_DIM + 3 + (2 if SPEED_OBS else 0) + (2 if FAR_LEAD else 0)

    def __init__(self, cfg, gui=False):
        # The subclass provides the extra three inputs on every supported checkout.
        scenario = dict(cfg["scenario"], obs_stop_line=False)
        super().__init__(scenario, cfg["simulation"], cfg["observation"], cfg["action"], cfg["reward"], gui=gui)

    def _state_file(self, seed):
        if seed == 1054:
            return str(DEMO_STATE)
        return super()._state_file(seed)

    def _state_ready(self, path):
        if path == str(DEMO_STATE):
            if not DEMO_STATE.is_file():
                raise FileNotFoundError(DEMO_STATE)
            return True
        return super()._state_ready(path)

    def _v1_obs(self):
        features = super()._v1_obs()
        e = self.ego_id
        signals = traci.vehicle.getNextTLS(e)
        speed = traci.vehicle.getSpeed(e)
        red = bool(signals and signals[0][2] <= 100 and signals[0][3] in "rRu")
        remaining = signals[0][2] - STOP_OFFSET if red else None   # 원본 3.5. AD_STOP_OFFSET로 기준점을 옮긴다
        # 11/20 임재성: 앞차 목표 (AD_QUEUE_MODE). 서 있는 앞차 꽁무니 뒤를 정지 목표로 알려 준다.
        #   0 = 원본 (빨간불 정지선만)
        #   1 = 빨간불일 때, 서 있는 앞차가 정지선보다 가까우면 앞차 뒤를 목표로
        #   2 = 빨간불이 아니어도 서 있는 앞차가 있으면 앞차 뒤를 목표로
        if QUEUE_MODE and (red or QUEUE_MODE >= 2):
            lead = traci.vehicle.getLeader(e, 100)
            if lead and lead[0] and traci.vehicle.getSpeed(lead[0]) < LEAD_STOPPED:
                gap = lead[1] + traci.vehicle.getMinGap(e)             # 범퍼 사이 거리 (getLeader는 minGap을 뺀 값)
                q = gap - QUEUE_OFFSET
                remaining = q if remaining is None else min(remaining, q)
        if remaining is not None:
            features.extend((remaining / 25, (remaining - speed ** 2 / 4) / 25, speed / 6))
        else:
            features.extend((0.0, 0.0, 0.0))
        if SPEED_OBS:
            features.extend(self._speed_preview(e))
        if FAR_LEAD:
            # 수업 관측의 앞차는 visibility 50 m까지만 보여서 50 m를 넘는 순간 '없음'에서 '49 m'로 튄다.
            # 11/21 급제동 추적: 44~51 m 앞차가 나타날 때 −3~−4 m/s²로 세게 밟는 경우가 반복됨
            ld = traci.vehicle.getLeader(e, 100)
            if ld and ld[0]:
                rel = (traci.vehicle.getSpeed(ld[0]) - speed) / 13.89
                features.extend((min(ld[1] / 100, 1.0), max(min(rel, 1.0), -1.0)))
            else:
                features.extend((1.0, 0.0))
        return features

    def _speed_preview(self, e):
        """앞 50 m 안(경로상)의 가장 낮은 제한 속도 / 지금 차로 제한, 그 지점까지 거리 / 50.
        제한이 낮아지지 않으면 (1, 1). 11/21: 급제동 82회 중 28회가 제한 속도가 낮아지기 직전 (45→40, 50→30 km/h)."""
        lane = traci.vehicle.getLaneID(e)
        now = traci.lane.getMaxSpeed(lane)
        left = traci.lane.getLength(lane) - traci.vehicle.getLanePosition(e)
        rt, ri = traci.vehicle.getRoute(e), traci.vehicle.getRouteIndex(e)
        best, dist = now, 50.0
        if not lane.startswith(":"):
            links = traci.lane.getLinks(lane)
            nxt_via = None
            for l in links:
                if ri + 1 < len(rt) and l[0].rsplit("_", 1)[0] == rt[ri + 1]:
                    nxt_via = l[4] if len(l) > 4 else None
            if nxt_via and left < 50:
                v = traci.lane.getMaxSpeed(nxt_via)
                if v < best:
                    best, dist = v, left
                left += traci.lane.getLength(nxt_via)
        for nx in rt[ri + 1:ri + 4]:
            if left >= 50:
                break
            v = traci.lane.getMaxSpeed(nx + "_0")
            if v < best - 0.1:
                best, dist = v, left
            left += traci.lane.getLength(nx + "_0")
        return [min(best / max(now, 0.1), 1.0), min(dist / 50.0, 1.0)]

    def _get_obs(self):
        """AD_QUEUE_MODE=3 (11/21 임재성): 같은 차로에 서 있는 앞차가 실제 빨간불 정지선보다 가까우면
        그 앞차 꽁무니를 '빨간불 정지선'으로 보이게 한다. 팀원 모델에서 가져온 정지선 접근 능력을 대기열에 그대로 쓰려는 것.
        앞차 거리·속도 칸(9, 10)은 '앞차 없음'으로, 신호 칸(31~34)은 앞차 꽁무니의 빨간불로, 정지선 칸(41~43)은 앞차 기준으로.
        앞차가 LEAD_STOPPED(m/s) 넘게 움직이면 원래 관측으로 돌아간다."""
        obs = self._box_guard(self._yellow_fix(self._tls_range(super()._get_obs())))
        if QUEUE_MODE != 3 or self.ego_id not in traci.vehicle.getIDList():
            return obs
        e = self.ego_id
        lead = traci.vehicle.getLeader(e, 60)
        if not (lead and lead[0] and traci.vehicle.getSpeed(lead[0]) < LEAD_STOPPED):
            return obs
        edge = traci.vehicle.getRoadID(e)
        if edge.startswith(":") or traci.vehicle.getRoadID(lead[0]) != edge:
            return obs   # 앞차가 교차로 건너편이면 교차로 앞에 서는 게 맞다 (11/21 추돌 9건 중 7건이 교차로 495951447 안)
        gap = lead[1] + traci.vehicle.getMinGap(e)              # 범퍼 사이 거리
        sig = traci.vehicle.getNextTLS(e)
        if sig and sig[0][3] in "rRuyY" and sig[0][2] <= gap:   # 실제 정지선이 더 가까우면 그대로
            return obs
        if gap <= MASK_MIN:                                     # 마지막 구간은 실제 앞차 관측으로 (11/21 모드 3 추돌 6건 대책)
            return obs
        v = traci.vehicle.getSpeed(e)
        obs = np.array(obs, dtype=np.float32, copy=True)
        obs[9], obs[10] = 1.0, 1.0
        obs[31], obs[32], obs[33], obs[34] = min(gap / 100, 1.0), 1.0, 0.0, 1.0
        rem = gap - QUEUE_OFFSET
        obs[41], obs[42], obs[43] = rem / 25, (rem - v ** 2 / 4) / 25, v / 6
        return np.clip(obs, -1.0, 1.0)

    def _yellow_fix(self, obs):
        """AD_YELLOW_FIX=1 (11/21 임재성): 노란불일 때 신호 프로그램의 다음 단계를 보고 관측을 바로잡는다.
        정류장 다음 신호(cluster_4650845824 연결 1)는 초록→노랑→다시 초록→노랑→빨강이라 노란불의 절반이 초록으로 돌아간다.
        후보 모델의 빨간불 진입 19건 중 9건이 이 신호였고 그중 6건은 7~9.6 m/s로 노란불을 그대로 지나친 것이었다.
        - 다음이 빨강이고 멈출 수 있는 거리면: 빨간불로 보여 주고 정지선 3칸도 켠다
        - 다음이 초록이면: 노란불 표시를 지운다
        - 멈추기 어려운 거리면(급정거로 교차로 안에 서게 되면) 그대로 둔다"""
        if not YELLOW_FIX or self.ego_id not in traci.vehicle.getIDList():
            return obs
        e = self.ego_id
        sig = traci.vehicle.getNextTLS(e)
        if not sig or sig[0][2] > 100 or sig[0][3] not in "yY":
            return obs
        tid, link, dist, _ = sig[0]
        try:
            cur = traci.trafficlight.getProgram(tid)
            logic = next(l for l in traci.trafficlight.getAllProgramLogics(tid) if l.programID == cur)
            nxt = logic.phases[(traci.trafficlight.getPhase(tid) + 1) % len(logic.phases)].state[link]
        except Exception:
            return obs
        v = traci.vehicle.getSpeed(e)
        obs = np.array(obs, dtype=np.float32, copy=True)
        if nxt in "rR" and dist >= v * v / (2 * 4.0) + 1.0:
            obs[32], obs[33], obs[34] = 1.0, 0.0, 1.0
            rem = dist - STOP_OFFSET
            obs[41], obs[42], obs[43] = rem / 25, (rem - v ** 2 / 4) / 25, v / 6
        elif nxt in "gG":
            obs[33] = 0.0
        return np.clip(obs, -1.0, 1.0)

    def _box_guard(self, obs):
        """AD_BOX_GUARD=1 (11/21 임재성): 꼬리물기 방지.
        교차로 입구 30 m 안인데 교차로 건너편(다른 엣지 또는 교차로 안)의 앞차가 서 있고, 그 꽁무니 뒤에
        차 한 대 자리(7.5 m)가 없으면 교차로 입구에 빨간불 정지선이 있는 것처럼 보여 준다.
        최종 조합 기본 교통 50개에서 교차로 안 정지 7회 중 4회가 이 상황 (1184134297: 12 m짜리 다음 엣지에 앞차)."""
        if not BOX_GUARD or self.ego_id not in traci.vehicle.getIDList():
            return obs
        e = self.ego_id
        edge = traci.vehicle.getRoadID(e)
        if edge.startswith(":"):
            return obs
        lane = traci.vehicle.getLaneID(e)
        d_end = traci.lane.getLength(lane) - traci.vehicle.getLanePosition(e)
        if d_end > 30:
            return obs
        lead = traci.vehicle.getLeader(e, 60)
        if not (lead and lead[0]) or traci.vehicle.getSpeed(lead[0]) >= 1.0:
            return obs
        le = traci.vehicle.getRoadID(lead[0])
        if le == edge:
            return obs                                            # 같은 엣지 앞차는 모드 3 몫
        rear = traci.vehicle.getLanePosition(lead[0]) - traci.vehicle.getLength(lead[0])
        if not le.startswith(":") and rear >= 7.5:
            return obs                                            # 건너편에 들어갈 자리가 있다
        sig = traci.vehicle.getNextTLS(e)
        if sig and sig[0][3] in "rRuyY" and sig[0][2] <= d_end:
            return obs                                            # 실제 빨간불이 더 가깝다
        v = traci.vehicle.getSpeed(e)
        obs = np.array(obs, dtype=np.float32, copy=True)
        obs[31], obs[32], obs[33], obs[34] = min(d_end / 100, 1.0), 1.0, 0.0, 1.0
        rem = d_end - STOP_OFFSET
        obs[41], obs[42], obs[43] = rem / 25, (rem - v ** 2 / 4) / 25, v / 6
        return np.clip(obs, -1.0, 1.0)

    def _tls_range(self, obs):
        """AD_TLS_RANGE (11/21 임재성): 신호 관측(31~34, 정지선 41~43)을 이 거리 안에서만 보여 준다.
        정류장 다음 신호 교차로 안쪽 급제동 19회가 전부 다음 신호(726912998) 빨간불이 90~100 m에서 관측에 처음 뜰 때였다.
        11 m/s에서 편하게 서는 데 30 m면 충분해서 100 m 앞 빨간불에 급히 반응할 필요가 없다."""
        if TLS_RANGE >= 100 or self.ego_id not in traci.vehicle.getIDList():
            return obs
        sig = traci.vehicle.getNextTLS(self.ego_id)
        if not sig or sig[0][2] <= TLS_RANGE:
            return obs
        # 대기열에서 기어갈 때는 먼 빨간불이 '지금은 서 있어라' 역할을 한다 (70 m 제한에서 정류장 버스 추돌 4건)
        if traci.vehicle.getSpeed(self.ego_id) <= TLS_RANGE_VMIN:
            return obs
        obs = np.array(obs, dtype=np.float32, copy=True)
        obs[31], obs[32], obs[33], obs[34] = 1.0, 0.0, 0.0, 1.0
        obs[41], obs[42], obs[43] = 0.0, 0.0, 0.0
        return obs
