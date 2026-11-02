"""성균관대역 일대 단순화 도로를 sumo-gui로 띄운다 (자동 재생).

    python view_schematic.py            # 사거리 ~ 고가 하부 (핵심 구간)
    python view_schematic.py --campus   # 학교 · 덕영대로 육교
    python view_schematic.py --all      # 전체 (고속화도로 포함)
    python view_schematic.py --shot out.png --seconds 600   # 600초 뒤 화면 저장 후 종료

고가 위 차량은 하늘색 반투명으로 칠해 "아래 도로와 다른 층"임을 보인다.
창을 닫으면 종료된다.
"""
import argparse
import os
import sys

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))
import traci  # noqa: E402
from sumolib import checkBinary  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
VIADUCT_COLOR = (120, 200, 255, 110)   # 고가 위 차량 (반투명 하늘색)
VIEWS = {
    "core": (-260, -520, 60, -120),     # 고가 하부 (갈림목 G1~G3, 공영주차장)
    "campus": (-320, -1420, 1180, -300),
}

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true")
ap.add_argument("--campus", action="store_true")
ap.add_argument("--shot", help="이 경로에 화면을 저장하고 종료")
ap.add_argument("--seconds", type=int, default=600, help="--shot 사용 시 저장 시점 (s)")
args = ap.parse_args()

traci.start([checkBinary("sumo-gui"), "-c", os.path.join(HERE, "skku.sumocfg"),
             "--start", "--no-step-log", "true", "--no-warnings", "true"]
            + (["--delay", "0", "--quit-on-end", "true"] if args.shot else []))
view = traci.gui.DEFAULT_VIEW
traci.simulationStep()   # 창이 뜬 뒤에 화면 범위를 지정해야 적용된다
if args.all:
    (x0, y0), (x1, y1) = traci.simulation.getNetBoundary()
    traci.gui.setBoundary(view, x0, y0, x1, y1)
else:
    x0, y0, x1, y1 = VIEWS["campus" if args.campus else "core"]
    traci.gui.setOffset(view, (x0 + x1) / 2, (y0 + y1) / 2)
    traci.gui.setBoundary(view, x0, y0, x1, y1)

on_viaduct = set()
try:
    t = 0
    while True:
        traci.simulationStep()
        t += 1
        now = set()
        for v in traci.vehicle.getIDList():
            if traci.vehicle.getRoadID(v).startswith("via_V1_V3") or traci.vehicle.getRoadID(v) == "via_V3_V1":
                now.add(v)
        for v in now - on_viaduct:
            traci.vehicle.setColor(v, VIADUCT_COLOR)
        for v in on_viaduct - now:
            if v in traci.vehicle.getIDList():
                traci.vehicle.setColor(v, traci.vehicletype.getColor(traci.vehicle.getTypeID(v)))
        on_viaduct = now
        if args.shot and t >= args.seconds:
            traci.gui.screenshot(view, os.path.abspath(args.shot))
            traci.simulationStep()
            break
    traci.close()
except traci.exceptions.FatalTraCIError:
    pass   # 창을 닫으면 종료
