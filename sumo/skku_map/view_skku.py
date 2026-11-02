"""성대역 시뮬레이션 보기 (sumo-gui + TraCI).

sumo-gui는 차를 도로·도형보다 항상 위에 그려서, 지하차도나 고가 밑을 지나는 차도 맨 위에 보인다.
그래서 아래층에 있는 차(지하차도 차로, 고가 면 밑의 지상)는 반투명하게 칠해 고가 위·지상의 차와 구분한다.
(차 색 투명도: userdoc/TraCI/Change_Vehicle_State.html "color", 보기 설정에는 높이별 차 색이 없다: userdoc/sumo-gui.html)

    python -X utf8 view_skku.py [sumo 옵션 ...]      예: --begin 600 --seed 1
"""
import math
import os
import sys

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
import sumolib  # noqa: E402
import traci  # noqa: E402
from traci import constants as tc  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FADE = 90          # 아래층 차의 불투명도 (0~255)
CELL = 1.0         # 고가 면 칸 크기 (m)


def lower_layers(net):
    """(지하차도 차로 id 집합, 고가 면이 덮는 1 m 칸 집합)."""
    under, deck = set(), set()
    for e in net.getEdges(withInternal=True):
        for ln in e.getLanes():
            sh = ln.getShape3D()
            z = sh[0][2] if len(sh[0]) > 2 else 0.0
            if z < -3:
                under.add(ln.getID())
            elif z > 3:
                r = ln.getWidth() / 2 + 0.3
                pts = [p[:2] for p in sh]
                for a, b in zip(pts, pts[1:]):
                    n = max(1, int(math.dist(a, b) / 0.5))
                    for k in range(n + 1):
                        x, y = a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n
                        for i in range(int((x - r) // CELL), int((x + r) // CELL) + 1):
                            for j in range(int((y - r) // CELL), int((y + r) // CELL) + 1):
                                if math.hypot((i + 0.5) * CELL - x, (j + 0.5) * CELL - y) <= r:
                                    deck.add((i, j))
    return under, deck


def main():
    net = sumolib.net.readNet(os.path.join(HERE, "skku.net.xml"), withInternal=True)
    under, deck = lower_layers(net)
    elevated = {ln.getID() for e in net.getEdges(withInternal=True) for ln in e.getLanes()
                if len(ln.getShape3D()[0]) > 2 and ln.getShape3D()[0][2] > 3}
    traci.start([sumolib.checkBinary("sumo-gui"), "-c", os.path.join(HERE, "skku.sumocfg"), "--start",
                 "--quit-on-end"] + sys.argv[1:])
    color, faded = {}, set()
    try:
        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            for v in traci.simulation.getDepartedIDList():
                traci.vehicle.subscribe(v, [tc.VAR_LANE_ID, tc.VAR_POSITION])
            for v in traci.simulation.getArrivedIDList():
                color.pop(v, None)
                faded.discard(v)
            for v, r in traci.vehicle.getAllSubscriptionResults().items():
                lane, (x, y) = r[tc.VAR_LANE_ID], r[tc.VAR_POSITION]
                low = lane in under or (lane not in elevated and (int(x // CELL), int(y // CELL)) in deck)
                if low == (v in faded):
                    continue
                if v not in color:
                    color[v] = traci.vehicle.getColor(v)[:3]
                traci.vehicle.setColor(v, color[v] + ((FADE,) if low else (255,)))
                (faded.add if low else faded.discard)(v)
    except traci.exceptions.FatalTraCIError:
        pass                                    # 화면 창을 닫으면 끝
    finally:
        try:
            traci.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
