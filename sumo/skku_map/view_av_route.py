"""AV 루트 주행 보기 (sumo-gui + TraCI): 루트를 달리는 차 한 대를 주황색으로 칠하고 화면이 따라간다.

구간마다 배속을 바꿔 보여준다 (발표 영상 배속 계획과 같은 값). TraCI로는 sumo-gui의 Delay를 바꿀 수 없어서
(userdoc/TraCI/Change_GUI_State.html) 스텝마다 쉬는 시간으로 배속을 맞춘다. 화면 그리기가 느리면 큰 배속은 덜 나온다.
차는 SUMO 기본 승용차(학습한 AV 아님), 경로는 verify/av_route_full.json, L1 주차장에서 20초 정차.

    python -X utf8 view_av_route.py [--warmup 600] [--zoom 400] [--speed 1.0]
      --speed: 모든 구간 배속에 곱하는 값 (0.5면 전부 절반 속도)
"""
import argparse
import json
import math
import os
import sys
import time

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
import sumolib  # noqa: E402
import traci  # noqa: E402
from traci import constants as tc  # noqa: E402
from view_skku import CELL, FADE, base_color, lower_layers  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
AV, AV_COLOR = "AV", (255, 90, 0, 255)
PARK_EDGE, PARK_SEC = "9669057440#0", 20     # L1 주차장 가운데 통로


def segments(net, R):
    """[(시작 경로 순번, 그 엣지 끝까지 남은 m 또는 None, 이름, 배속)] — 구간 경계는 경로 위 지점(좌표)에 가장 가까운 엣지.
    남은 m를 주면 그 엣지에서 끝까지 그만큼 남았을 때 구간이 바뀐다 (긴 엣지 끝의 교차로 앞에서 늦추기)."""
    edges, hw = R["edges"], R["highway"]

    def near(p):
        return min(range(len(edges)), key=lambda i: min(math.dist(p, q[:2]) for q in net.getEdge(edges[i]).getShape()))

    first = lambda pre: next(i for i, e in enumerate(hw) if e.startswith(pre))
    gate = len(hw) + len(R["local"]) - 1
    return [(0, None, "고속도로: 청계IC 합류 → 휴게소 합류", 4),
            (first("hw_hT0") - 1, None, "의왕TG 요금소 (3→10→3차로)", 4),
            (first("hw_hT1") + 1, None, "고속도로 → 서부로 (이동)", 16),
            (len(hw), None, "서부로 → 성대역 사거리 (신호)", 4),
            (near((2, 30)) + 1, None, "고가 분기 → 버스 구간 → 올리브영 사거리", 3),
            (near((-100, -245)), None, "골목 오거리 3곳 (눈치 게임)", 2),
            (near((-330, -300)), None, "회전교차로 (진입 양보)", 2),
            (near((-570, -600)), None, "회전교차로 뒤 → 율전로64번길 아파트 사이 (이동)", 8),
            (edges.index("3718967780#2"), 150, "서부로×일월로 사거리 (신호) → 정문 좌회전", 4),
            (gate, None, "정문 → Modular Bldg 지나 Global Plaza 앞 우회전 → L1 주차장", 8),
            (edges.index(PARK_EDGE), None, "L1 주차·출차", 3),
            (edges.index("4948484630"), None, "교내 순환로 한 바퀴 (일방통행)", 20),
            (len(edges) - len(R["exit"]) - 1, None, "정문 나가며 좌회전", 4),
            (len(edges) - len(R["exit"]), None, "일월로 → 도착", 8)]


def reached(net, edges, seg, idx, pos):
    i, rem = seg[0], seg[1]
    return idx > i or (idx == i and (rem is None or pos >= net.getEdge(edges[i]).getLength() - rem))


def main():
    ap = argparse.ArgumentParser()
    # 300초로는 성대역 사거리에 차가 덜 쌓여 너무 쉽게 지나갔다. 교통을 처음에 많이 넣는 배율(traffic.py DEMAND)을 넣은 뒤
    #   600초에 출발하면 사거리에서 약 2분 기다린다 (900초 3분, 1200·1500초 1~1.5분)
    ap.add_argument("--warmup", type=float, default=600, help="AV를 넣기 전 배경 교통을 채우는 시간(초, 최대 속도로 돈다)")
    ap.add_argument("--zoom", type=float, default=400)
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()

    net = sumolib.net.readNet(os.path.join(HERE, "skku.net.xml"), withInternal=True)
    R = json.load(open(os.path.join(HERE, "verify", "av_route_full.json"), encoding="utf-8"))
    segs = segments(net, R)
    under, deck = lower_layers(net)
    elevated = {ln.getID() for e in net.getEdges(withInternal=True) for ln in e.getLanes()
                if len(ln.getShape3D()[0]) > 2 and ln.getShape3D()[0][2] > 3}
    traci.start([sumolib.checkBinary("sumo-gui"), "-c", os.path.join(HERE, "skku.sumocfg"), "--start", "--delay", "0",
                 "--window-size", "1600,1000", "--no-warnings"])
    view, step = traci.gui.DEFAULT_VIEW, traci.simulation.getDeltaT()
    traci.gui.setOffset(view, 0, 60)                    # 차를 채우는 동안 성대역 사거리(원점)와 북쪽 대기 줄을 비춘다
    traci.gui.setZoom(view, a.zoom)
    color, faded, cur, t_av = {}, set(), -1, None
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            t0 = time.perf_counter()
            traci.simulationStep()
            now = traci.simulation.getTime()
            if t_av is None and now % 100 < step / 2:
                print(f"배경 교통 채우는 중 {now:.0f}/{a.warmup:.0f}초, 차 {traci.vehicle.getIDCount()}대")
            if t_av is None and now >= a.warmup:
                traci.route.add("av_route", R["edges"])
                traci.vehicle.add(AV, "av_route", depart="now", departLane="best", departSpeed="max")
                traci.vehicle.setColor(AV, AV_COLOR)
                traci.vehicle.setStop(AV, PARK_EDGE, pos=net.getEdge(PARK_EDGE).getLength() * 0.6, duration=PARK_SEC)
                t_av = now
            for v in traci.simulation.getDepartedIDList():
                if v != AV:
                    traci.vehicle.subscribe(v, [tc.VAR_LANE_ID, tc.VAR_POSITION])
                else:
                    traci.gui.trackVehicle(view, AV)
                    traci.gui.setZoom(view, a.zoom)
            if AV in traci.simulation.getArrivedIDList():
                print(f"도착: 출발 뒤 {now - t_av:.0f}초 (실제 시간)")
                break
            for v in traci.simulation.getArrivedIDList():
                color.pop(v, None)
                faded.discard(v)
            for v, r in traci.vehicle.getAllSubscriptionResults().items():   # 아래층 차 반투명 (view_skku.py와 같음)
                lane, (x, y) = r[tc.VAR_LANE_ID], r[tc.VAR_POSITION]
                low = lane in under or (lane not in elevated and (int(x // CELL), int(y // CELL)) in deck)
                if low == (v in faded):
                    continue
                if v not in color:
                    color[v] = base_color(v)
                traci.vehicle.setColor(v, color[v] + ((FADE,) if low else (255,)))
                (faded.add if low else faded.discard)(v)
            speed = 0                                           # 0 = AV 출발 전, 최대한 빨리
            if t_av is not None and AV in traci.vehicle.getIDList():
                idx, pos = traci.vehicle.getRouteIndex(AV), traci.vehicle.getLanePosition(AV)
                if traci.vehicle.getRoadID(AV).startswith(":"):     # 교차로 안: 위치가 교차로 내부 차로 기준이라 엣지를 다 지난 것으로
                    pos = math.inf
                k = max(i for i, s in enumerate(segs) if reached(net, R["edges"], s, idx, pos))
                if k != cur:
                    cur = k
                    print(f"[{now - t_av:5.0f}초] {segs[k][2]}  ×{segs[k][3]}")
                speed = segs[k][3] * a.speed
            if speed:
                time.sleep(max(0.0, step / speed - (time.perf_counter() - t0)))
    except traci.exceptions.FatalTraCIError:
        pass                                    # 화면 창을 닫으면 끝
    finally:
        try:
            traci.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
