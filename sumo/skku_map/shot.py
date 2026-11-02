"""도로망 화면 캡처 (확인용).  python shot.py NET OUT.png CX CY WIDTH [ADDITIONAL]"""
import os
import sys

sys.path.append(os.path.join(os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo"), "tools"))
import traci  # noqa: E402
from sumolib import checkBinary  # noqa: E402

net, out, cx, cy, w = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:6])
cmd = [checkBinary("sumo-gui"), "-n", net, "--start", "--quit-on-end", "--no-step-log", "--no-warnings", "--end", "100"]
if len(sys.argv) > 6:
    cmd += ["-a", sys.argv[6]]
gui = os.path.join(os.path.dirname(os.path.abspath(__file__)), "skku.gui.xml")
if os.path.exists(gui):
    cmd += ["--gui-settings-file", gui]
traci.start(cmd)
traci.simulationStep()
v = traci.gui.DEFAULT_VIEW
traci.gui.setOffset(v, cx, cy)
traci.gui.setBoundary(v, cx - w / 2, cy - w / 4, cx + w / 2, cy + w / 4)
traci.simulationStep()
traci.gui.screenshot(v, os.path.abspath(out))
traci.simulationStep()
traci.close()
