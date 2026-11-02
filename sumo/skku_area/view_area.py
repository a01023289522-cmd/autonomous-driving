"""성균관대역 일대 시뮬레이션을 sumo-gui로 띄운다 (성대역 주변을 확대한 상태로 자동 재생).

    python view_area.py            # 성대역 주변
    python view_area.py --all      # 전체 영역
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

ap = argparse.ArgumentParser()
ap.add_argument("--all", action="store_true")
args = ap.parse_args()

traci.start([checkBinary("sumo-gui"), "-c", os.path.join(HERE, "skku_area.sumocfg"),
             "--start", "--delay", "50", "--no-step-log", "true", "--no-warnings", "true"])
view = traci.gui.DEFAULT_VIEW
if args.all:
    (x0, y0), (x1, y1) = traci.simulation.getNetBoundary()
    traci.gui.setBoundary(view, x0, y0, x1, y1)
else:
    sx, sy = traci.simulation.convertGeo(126.97118, 37.30029, fromGeo=True)   # 성균관대역
    traci.gui.setBoundary(view, sx - 420, sy - 300, sx + 420, sy + 300)
try:
    while True:
        traci.simulationStep()
except traci.exceptions.FatalTraCIError:
    pass   # 창을 닫으면 종료
