"""한 대 폭 골목(bidi)의 일반 차량(HV) 통행 규칙: 반대 방향 차가 골목 구간에 있으면 입구 앞에서 기다린다.

왜 필요한가 (2026-11-21 측정, build.py ALLEY):
  SUMO 1.27은 bidi 도로에서 마주 오는 차를 앞차로 보고 멈추지만(정면충돌 감지 있음), 진입 판단은 믿을 수 없었다.
  서부로2123번길(28 m)에서 반대편 차가 들어간 지 1초 뒤 서부로에서 차가 들어와 서로 5 m 앞에서 멈춘 채 300초 뒤 순간이동
  (시드 1·2, 30분에 순간이동 6~18회). SUMO 차는 후진·비켜서기를 못 하므로, 실제 골목처럼 "입구에서 기다렸다 들어가기"를
  TraCI로 지킨다. AV에는 적용하지 않는다 — AV의 양보는 학습으로 한다 (규칙 기반 안전장치 금지, 11/17 컨설팅).

구간(block): 교차로와 교차로 사이 골목. 같은 구간 안에는 한 방향 차만 있을 수 있다.
  - 구간에 차가 있으면(교차로 안에서 그 구간으로 들어가는 중인 차 포함) 그 방향이 통행권을 갖는다
  - 비어 있으면 입구에 더 가까운 차의 방향이 통행권을 받는다
  - 통행권이 없는 방향의 차는 입구 앞에서 멈추도록 속도를 낮춘다 (감속 3 m/s², 이미 못 서는 거리면 그대로 진입)

쓰는 곳: rl/skku_env.py(매 스텝 step), 워밍업 상태 파일 만들기(python alley.py warmup ...).
"""
import math
import sys

# (AV 진행 방향 엣지들, 반대 방향 엣지들). 엣지 순서는 각 방향의 진행 순서
BLOCKS = (
    # 서부로2123번길 입구(서부로 ~ 플렁드 오거리)는 양방향 2차로라 구간이 아니다 (11/22 거리뷰: 노란 중앙선)
    # 한 대 폭 율전로98번길 전체(플렁드 오거리 ~ 율전로)를 한 구간으로 둔다. 중간 교차로 두 곳으로 옆 골목 차가 들어오므로 구간의
    # 모든 엣지를 입구로 본다. 11/22: 교차로마다 구간을 나눴더니 AV가 앞 구간을 나와 교차로에 있는 동안 반대 방향 차가 다음 구간에
    # 들어와 서로 기다림(시드 1080·1029 등 시간초과 5건). bidi 차로는 교차로 안에서도 겹쳐서 교차로가 비켜 설 곳이 되지 못한다
    (("4694200410", "-4526039590#2", "-4526039590#0"), ("4526039590#0", "4526039590#2", "-4694200410")),
)
LOOKAHEAD = 60.0      # 입구까지 이 거리 안의 차만 본다 (m)
STOP_DECEL = 4.0      # 입구 앞에서 멈출 때 감속도 (m/s², 승용차 decel 4.5보다 조금 작게)
STOP_MARGIN = 0.5     # 교차로 정지선 앞 여유 (m)
RESERVE_S = 6.0       # 입구 도착 이만큼 전부터 통행권을 예약한다 (s)
HOLD_DECEL = 2.5      # 세울 때 쓰는 감속도 (m/s²)
MAX_WAIT_S = 15.0
GRANT_S = 8.0         # 출발 허가가 유효한 시간 (s)
GRANT_MAX_S = 40.0    # 정지선 맨 앞에서 교차로 틈을 기다리는 차의 허가 유효 시간 (s)     # 반대쪽이 이만큼 기다리면 통행권을 넘긴다 (s)


class AlleyGate:
    def __init__(self, traci, ego_id=None):
        self.t = traci
        self.ego_id = ego_id
        self.held = set()
        self.owner = [None] * len(BLOCKS)     # 구간별 통행권 방향 (0 = AV 방향, 1 = 반대)
        self.wait_since = [None] * len(BLOCKS)  # 통행권 없는 쪽이 기다리기 시작한 시각
        self.stopped = {}                       # 정식 정지(stop)로 세운 차 → (엣지, 위치, 차로)
        self.granted = {}                       # 세웠다가 출발시킨 차 → 출발시킨 시각. GRANT_S초 동안 통행권을 요구하는 것으로 본다

    def _approaching(self, side, horizon):
        """구간의 한 방향(side: 엣지 목록)으로 곧 들어갈 차: (들어가기 전 교차로 정지선까지 거리, id).
        horizon=0이면 교차로 안(내부 차로)에서 들어가는 중인 차만. 이미 그 방향 엣지 위에 있거나, 그 방향 엣지에서 나와 다음 엣지로
        가는 교차로 안의 차는 '구간 안'이라 빼고 _inside에서 센다."""
        t, res, seen = self.t, [], set()
        members = set(side)
        for e in side:
            for src in (self._junction[e] if horizon == 0.0 else self._upstream[e]):
                for v in t.edge.getLastStepVehicleIDs(src):
                    if v in seen:
                        continue
                    seen.add(v)
                    r, i = t.vehicle.getRoute(v), t.vehicle.getRouteIndex(v)
                    if not (0 <= i < len(r)) or r[i] in members:
                        continue
                    nxt = [k for k in range(i + 1, min(i + 5, len(r))) if r[k] in members]
                    if not nxt:
                        continue
                    k = nxt[0]
                    if t.vehicle.getRoadID(v).startswith(":") and k == i + 1:
                        res.append((0.0, v))
                        continue
                    if horizon > 0.0:
                        # 거리는 들어가기 전 교차로의 정지선(바로 앞 엣지의 끝)까지. 11/21: 입구까지로 재면 교차로 길이만큼 늦게 서려다
                        # 교차로 안으로 들어가 버렸다
                        d = t.vehicle.getDrivingDistance(v, r[k - 1], t.lane.getLength(f"{r[k - 1]}_0"))
                        if 0 <= d <= horizon:
                            res.append((max(d, 0.01), v))
        return res

    def _inside(self, side):
        """그 방향 엣지 위의 차 + 그 방향 엣지에서 나와 아직 교차로 안에 있는 차 (11/22 시드 1076·1018: AV가 구간을 나와 교차로 안에
        있을 때 반대 방향 차가 들어가 교차로 안에서 정면충돌. bidi 구간 끝 교차로의 내부 차로도 두 방향이 겹친다)"""
        t, out = self.t, []
        members = set(side)
        for e in side:
            out += t.edge.getLastStepVehicleIDs(e)
            for lane_e in self._exit_lanes[e]:
                for x in t.edge.getLastStepVehicleIDs(lane_e):
                    r_, i_ = t.vehicle.getRoute(x), t.vehicle.getRouteIndex(x)
                    if 0 <= i_ < len(r_) and r_[i_] in members and x not in out:
                        out.append(x)
        return out

    def setup(self):
        """엣지마다 (1) 그 앞 교차로 내부 차로, (2) 그 교차로까지 LOOKAHEAD 안의 위쪽 엣지(내부 차로 포함, 구간 엣지 제외),
        (3) 그 엣지 끝 교차로의 내부 차로를 미리 찾아 둔다.
        11/21: 서부로 쪽 입구 앞 엣지가 12 m뿐이라 바로 앞 엣지만 보면 서부로 차를 너무 늦게 봐서 '못 서는 거리'로 들여보냈다."""
        t = self.t
        self._junction, self._upstream, self._exit_lanes = {}, {}, {}
        internal = [e for e in t.edge.getIDList() if e.startswith(":")]
        def node_internal(node):
            return {e for e in internal if e.rsplit("_", 1)[0] == f":{node}"}
        for fwd, rev in BLOCKS:
            block = set(fwd) | set(rev)
            for e in (*fwd, *rev):
                node = t.edge.getFromJunction(e)
                self._junction[e] = sorted(node_internal(node))
                self._exit_lanes[e] = sorted(node_internal(t.edge.getToJunction(e)))
                seen, frontier = set(self._junction[e]), [(node, 0.0)]
                while frontier:
                    n, dist = frontier.pop()
                    for x in t.junction.getIncomingEdges(n):
                        if x.startswith(":") or x in seen or x in block:
                            continue
                        seen.add(x)
                        length = t.lane.getLength(f"{x}_0")
                        up = t.edge.getFromJunction(x)
                        seen |= node_internal(up)
                        if dist + length < LOOKAHEAD:
                            frontier.append((up, dist + length))
                self._upstream[e] = sorted(seen)
        return self

    def step(self):
        """통행권 정하기.
        (1) 골목 안에 있거나 통행권을 요구하는 차(claims)가 한쪽에만 있으면 그쪽이 통행권
        (2) 양쪽 다 없으면 지금 통행권 유지, 통행권 쪽에 오는 차가 없을 때만 입구 도착이 빠른 쪽으로 넘긴다
        (3) 기다리는 쪽이 MAX_WAIT_S초를 넘으면 통행권 쪽은 새 차를 더 들이지 않고(설 수 있는 차는 세움) 비워지면 넘긴다
        11/21: 매 스텝 '가까운 쪽'으로 정하면 양쪽이 거의 같은 때 교차로에 들어가 교착, (3)이 없으면 한쪽 흐름이 이어질 때
        반대쪽이 최대 300초 기다렸다 (시드 1·4)."""
        t = self.t
        now = t.simulation.getTime()
        want = {}
        self._last_near = []
        for b, (fwd, rev) in enumerate(BLOCKS):
            yielding = self.owner[b] is not None and self.wait_since[b] is not None and now - self.wait_since[b] > MAX_WAIT_S
            near, committed, physical = [], [], []
            for k, d in enumerate((fwd, rev)):
                inside = len(self._inside(d))
                cand = sorted(self._approaching(d, LOOKAHEAD))
                reserve = not (yielding and k == self.owner[b])
                phys = [v for dist, v in cand if self._claims(dist, v, False)]
                claim = [v for dist, v in cand if self._claims(dist, v, reserve)]
                near.append(cand)
                self._last_near += [(v, dist) for dist, v in cand if dist > 0.0]
                physical.append(inside > 0 or bool(phys))
                committed.append(inside > 0 or bool(claim))
            if committed[0] != committed[1]:
                new = 0 if committed[0] else 1
            elif not committed[0]:
                new = self.owner[b]
                if new is None or not near[new] or yielding:
                    eta = [(c[0][0] / max(t.vehicle.getSpeed(c[0][1]), 1.0), k) for k, c in enumerate(near) if c]
                    new = min(eta)[1] if eta else None
                    if yielding and near[1 - self.owner[b]]:
                        new = 1 - self.owner[b]
                # 넘길 쪽의 반대편에 이미 못 서는 차가 있으면 넘기지 않는다 (11/22 시드 1219: 넘기는 순간 경합으로 교착)
                if new is not None and new != self.owner[b] and physical[1 - new]:
                    new = self.owner[b]
            else:
                new = self.owner[b]           # 양쪽 다 들어갔거나 못 섬(교착 또는 AV가 무시하고 들어옴): 그대로
            if new != self.owner[b]:
                self.wait_since[b] = None
            self.owner[b] = new
            if new is None:
                continue
            losers = [(d, v) for d, v in near[1 - new] if v != self.ego_id and d > 0.0]
            # AV도 기다리는 쪽으로 센다 (AV는 세우지 않지만, AV가 입구에서 기다리면 MAX_WAIT_S 뒤 통행권이 AV 쪽으로 넘어온다)
            if losers or any(v == self.ego_id for _, v in near[1 - new]):
                if self.wait_since[b] is None:
                    self.wait_since[b] = now
            else:
                self.wait_since[b] = None
            for d, v in losers:
                want[v] = d
            if yielding:                      # 통행권 쪽의 설 수 있는 새 차도 세운다
                for d, v in near[new]:
                    if v != self.ego_id and d > 0.0 and not self._claims(d, v, False):
                        want[v] = d
        alive_near = {v for v, _ in self._last_near} if hasattr(self, "_last_near") else set()
        # 구간에 들어갔거나 사라진 차, GRANT_S초가 지나도 못 들어간 차(11/22 시드 1202: 허가받은 버스가 서부로에서 다른 이유로 서 있어
        # 반대편 3대가 50초 넘게 묶임)는 뺀다
        # 단, 정지선 맨 앞(3 m 안)에서 교차로 틈을 기다리는 차는 GRANT_MAX_S까지 유지한다 (11/22 시드 1206: 서부로 우회전 틈을 기다리던
        # 버스가 8초 만에 허가를 잃고 다시 세워지기를 반복해 200초 넘게 갇힘)
        dist_now = dict(self._last_near) if hasattr(self, "_last_near") else {}
        def keep(v, t0):
            if v not in alive_near:
                return False
            at_line = dist_now.get(v, 99.0) < 3.0
            return now - t0 < (GRANT_MAX_S if at_line else GRANT_S)
        self.granted = {v: t0 for v, t0 in self.granted.items() if keep(v, t0)}
        for v in list(self.held):
            if v not in want:
                if v in t.vehicle.getIDList():
                    t.vehicle.setSpeed(v, -1)
                    self._unstop(v)
                    if v in alive_near:        # 아직 정지선 앞: 출발 허가 (들어갈 때까지 통행권 요구. 느려서 요구 안 하는 것으로 세던 문제)
                        self.granted[v] = now
                self.held.discard(v)
        for v, d in want.items():
            spd, room = t.vehicle.getSpeed(v), d - STOP_MARGIN
            if v not in self.held and spd * spd / (2 * STOP_DECEL) > room + 1.0:
                continue                       # 이미 못 서는 거리: 그대로 들어간다 (다음 스텝부터 그쪽이 통행권)
            # 세울 때는 HOLD_DECEL로 완만하게, 한 스텝 늦게 반영되는 것(0.5초)까지 빼고 계산 (11/22 시드 1219: 최대 감속에 딱 맞춘
            # 곡선이라 정지선을 넘어 교차로로 들어가 교착)
            room = room - spd * 0.5
            t.vehicle.setSpeed(v, math.sqrt(2 * HOLD_DECEL * room) if room > 0.3 else 0.0)
            self.held.add(v)
            # 교차로 바로 앞 엣지에 오면 정식 정지(stop)로 바꾼다. setSpeed로 세운 차는 SUMO가 '교차로로 다가오는 차'로 계속 보아서,
            # 골목에서 나가는 차가 우선도로에 세워 둔 그 차에 양보하며 서로 기다렸다 (11/22 시드 1222: 율전로 495951808, 300초).
            # 정지가 있으면 그 앞까지만 보고 교차로 진입을 요청하지 않는다. userdoc/TraCI/Change_Vehicle_State.html stop·resume
            if v not in self.stopped:
                lane = t.vehicle.getLaneID(v)
                if not lane.startswith(":"):
                    length = t.lane.getLength(lane)
                    if abs(length - t.vehicle.getLanePosition(v) - d) < 1.0:
                        edge, idx, pos = t.vehicle.getRoadID(v), t.vehicle.getLaneIndex(v), max(length - STOP_MARGIN, 0.1)
                        try:
                            t.vehicle.setStop(v, edge, pos=pos, laneIndex=idx, duration=86400.0)
                            self.stopped[v] = (edge, pos, idx)
                        except t.exceptions.TraCIException if hasattr(t, "exceptions") else Exception:
                            pass

    def _unstop(self, v):
        st = self.stopped.pop(v, None)
        if st is None:
            return
        t = self.t
        try:
            if t.vehicle.isStopped(v):
                t.vehicle.resume(v)
            else:
                t.vehicle.setStop(v, st[0], pos=st[1], laneIndex=st[2], duration=0.0)   # 아직 안 섰으면 정지 취소
        except Exception:
            pass

    def oncoming(self, ego):
        """AV가 골목 구간 입구에 다가가는 중(구간 밖)이면 (입구 정지선까지 거리, [(반대 방향 차, 그 차가 내 입구까지 남은 거리)]).
        반대 방향 차 = 구간 안에 있거나 통행권을 요구하며(교차로 안·못 서는 거리·도착 RESERVE_S초 안) 들어오는 차.
        해당 없으면 None. AV 관측(교차로 양보 상대 칸)과 양보 위반 판정에 쓴다 (rl/skku_env.py obs_alley)."""
        t = self.t
        for fwd, rev in BLOCKS:
            for d, v in self._approaching(fwd, LOOKAHEAD):
                if v != ego:
                    continue
                # 거리 = 그 차가 충돌 구역(한 대 폭 구간)까지 남은 거리. 구간 안에 있는 차는 0 (이미 충돌 구역 안. 교차로 관측에서 교차로
                # 안의 차를 0으로 넣는 것과 같은 뜻). 11/22: 직선 거리로 넣었더니 120 m 골목 반대편 끝의 차가 77~121 m로 관측 범위(50 m)
                # 밖이라 '양보 상대 없음'과 같아 보였고, r_s8이 시속 25 km로 들어가 골목 가운데서 정면충돌 (시드 1551·1287)
                cars = [(x, 0.0) for x in self._inside(rev)]
                cars += [(x, dd) for dd, x in self._approaching(rev, LOOKAHEAD) if self._claims(dd, x, True)]
                return d, cars
        return None

    def _claims(self, dist, v, reserve):
        """통행권을 요구하는 차: 교차로 안(dist 0), 제동 거리가 모자란 차, reserve면 입구까지 RESERVE_S초 안에 닿는 차도.
        붙잡힌 차, 정지선에 서서 양보 중인 차(0.5 m/s 미만)는 요구하지 않는다 (11/21: 서 있는 차가 통행권을 뺏던 문제).
        RESERVE_S 예약 이유: '못 서는 차'만 보면 양쪽 차가 거의 같은 때 각자 교차로에 들어가 둘 다 못 서서 교착."""
        if v in self.held:
            return False
        if dist <= 0.0 or v in self.granted:
            return True
        spd = self.t.vehicle.getSpeed(v)
        if spd < 0.5:
            return False
        return spd * spd / (2 * STOP_DECEL) > dist - STOP_MARGIN + 1.0 or (reserve and dist / spd < RESERVE_S)


def warmup(argv):
    """python alley.py warmup <end> <save_time> <state_file> <sumo 실행 파일> [sumo 인자...]
    배경 교통을 골목 규칙과 함께 채우고 상태를 저장한다 (TraCI 소켓 + sumo 실행 파일: 기존 상태 파일과 같은 방식)."""
    import os
    sys.path.append(os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
    import traci
    end, save_t, out, sumo_bin, *args = argv
    traci.start([sumo_bin, *args])
    gate = AlleyGate(traci).setup()
    save_t = float(save_t)
    while traci.simulation.getTime() < save_t - 1e-6:
        gate.step()
        traci.simulationStep()
    traci.simulation.saveState(out)
    traci.close()


if __name__ == "__main__":
    if sys.argv[1] == "warmup":
        warmup(sys.argv[2:])
