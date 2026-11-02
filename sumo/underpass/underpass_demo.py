"""교차로 지하차도 데모.

동서 간선도로(편도 3차로)가 신호 교차로 앞에서 갈라진다.
  - 가운데 2차로 : 교차로 밑 지하차도(-6m)로 내려가 신호 없이 통과
  - 바깥 1차로   : 지상에 남아 신호 교차로에서 직진·우회전
교차로를 지나면 다시 3차로로 합쳐진다. 양방향 모두 같은 구조.

화면 표현 (sumo-gui는 위에서 내려다보는 2D):
  - 지하 구간 도로는 회색 덮개(다각형)로 표시
  - 지하로 내려간 차량(높이 < -1.5m)은 TraCI로 색을 반투명하게 바꿔
    "도로 밑을 지나간다"는 것을 보이게 한다.

실행:
    python underpass_demo.py           # sumo-gui로 보기 (자동 재생)
    python underpass_demo.py --nogui   # 화면 없이 10분 돌려서 통계만 출력
"""
import argparse
import os
import re
import subprocess

import traci
from sumolib import checkBinary

HERE = os.path.dirname(os.path.abspath(__file__))
UNDER_EDGES = ("e_under", "w_under")
UNDERGROUND_Z = -1.5        # 이 높이보다 낮으면 "지하"로 보고 반투명 처리
UNDERGROUND_ALPHA = 70      # 지하 차량 투명도 (0 = 투명, 255 = 불투명)

# ──────────────────────────────────────────────────────────────
# 1) 도로 파일
#    좌표 (x, y, z) 단위 m. 교차로 C는 x=600.
#    지하차도 엣지는 가운데선(y=0) 위에 놓이고, SUMO 기본 spreadType="right"라
#    동쪽 방향 차로는 y<0, 서쪽 방향 차로는 y>0 쪽에 그려진다.
#    지상 차로는 그 바깥(y=±9.6, 지하차도와 3.2m 간격)으로 벌어지게 shape를 준다.
# ──────────────────────────────────────────────────────────────
NODES = """<nodes>
    <node id="W" x="0"    y="0"/>
    <node id="A" x="250"  y="0"/>   <!-- 동쪽 방향 분기 / 서쪽 방향 합류 -->
    <node id="C" x="600"  y="0" type="traffic_light"/>   <!-- 지상 신호 교차로 (SUMO 기본 신호) -->
    <node id="B" x="950"  y="0"/>   <!-- 동쪽 방향 합류 / 서쪽 방향 분기 -->
    <node id="E" x="1200" y="0"/>
    <node id="N" x="600"  y="250"/>
    <node id="S" x="600"  y="-250"/>
</nodes>
"""

EDGES = """<edges>
    <!-- 동쪽 방향 (EB) -->
    <edge id="e_in"    from="W" to="A" numLanes="3" speed="16.67"/>
    <edge id="e_surf1" from="A" to="C" numLanes="1" speed="13.89" shape="250,0 310,-9.6 585,-9.6"/>
    <edge id="e_under" from="A" to="B" numLanes="2" speed="16.67"
          shape="250,0,0 330,0,0 430,0,-6 770,0,-6 870,0,0 950,0,0"/>   <!-- 지하차도: 경사 6% -->
    <edge id="e_surf2" from="C" to="B" numLanes="1" speed="13.89" shape="615,-9.6 890,-9.6 950,0"/>
    <edge id="e_out"   from="B" to="E" numLanes="3" speed="16.67"/>
    <!-- 서쪽 방향 (WB) -->
    <edge id="w_in"    from="E" to="B" numLanes="3" speed="16.67"/>
    <edge id="w_surf1" from="B" to="C" numLanes="1" speed="13.89" shape="950,0 890,9.6 615,9.6"/>
    <edge id="w_under" from="B" to="A" numLanes="2" speed="16.67"
          shape="950,0,0 870,0,0 770,0,-6 430,0,-6 330,0,0 250,0,0"/>
    <edge id="w_surf2" from="C" to="A" numLanes="1" speed="13.89" shape="585,9.6 310,9.6 250,0"/>
    <edge id="w_out"   from="A" to="W" numLanes="3" speed="16.67"/>
    <!-- 남북 교차 도로 (지상, 신호 교차로) -->
    <edge id="n_in"  from="N" to="C" numLanes="2" speed="13.89"/>
    <edge id="n_out" from="C" to="N" numLanes="2" speed="13.89"/>
    <edge id="s_in"  from="S" to="C" numLanes="2" speed="13.89"/>
    <edge id="s_out" from="C" to="S" numLanes="2" speed="13.89"/>
</edges>
"""

# 분기·합류 지점의 차로 연결: 바깥 차로(0) = 지상, 안쪽 차로(1, 2) = 지하차도
CONNECTIONS = """<connections>
    <connection from="e_in" to="e_surf1" fromLane="0" toLane="0"/>
    <connection from="e_in" to="e_under" fromLane="1" toLane="0"/>
    <connection from="e_in" to="e_under" fromLane="2" toLane="1"/>
    <connection from="e_surf2" to="e_out" fromLane="0" toLane="0"/>
    <connection from="e_under" to="e_out" fromLane="0" toLane="1"/>
    <connection from="e_under" to="e_out" fromLane="1" toLane="2"/>
    <connection from="w_in" to="w_surf1" fromLane="0" toLane="0"/>
    <connection from="w_in" to="w_under" fromLane="1" toLane="0"/>
    <connection from="w_in" to="w_under" fromLane="2" toLane="1"/>
    <connection from="w_surf2" to="w_out" fromLane="0" toLane="0"/>
    <connection from="w_under" to="w_out" fromLane="0" toLane="1"/>
    <connection from="w_under" to="w_out" fromLane="1" toLane="2"/>
</connections>
"""

# ──────────────────────────────────────────────────────────────
# 2) 차량: 색으로 구분
#    하늘색 = 지하차도 직진 / 흰색 = 지상 직진 / 주황 = 지상 우회전 / 노랑 = 남북 도로
# ──────────────────────────────────────────────────────────────
ROUTES = """<routes>
    <vType id="under"  color="0,200,255"   carFollowModel="IDM" speedDev="0.1"/>
    <vType id="surf"   color="255,255,255" carFollowModel="IDM" speedDev="0.1"/>
    <vType id="turn"   color="255,150,0"   carFollowModel="IDM" speedDev="0.1"/>
    <vType id="cross"  color="255,230,0"   carFollowModel="IDM" speedDev="0.1"/>

    <route id="eb_under" edges="e_in e_under e_out"/>
    <route id="wb_under" edges="w_in w_under w_out"/>
    <route id="eb_surf"  edges="e_in e_surf1 e_surf2 e_out"/>
    <route id="wb_surf"  edges="w_in w_surf1 w_surf2 w_out"/>
    <route id="eb_right" edges="e_in e_surf1 s_out"/>
    <route id="wb_right" edges="w_in w_surf1 n_out"/>
    <route id="ns"       edges="n_in s_out"/>
    <route id="sn"       edges="s_in n_out"/>
    <route id="n_right"  edges="n_in w_surf2 w_out"/>
    <route id="s_right"  edges="s_in e_surf2 e_out"/>

    <flow id="f_eb_under" type="under" route="eb_under" begin="0" end="3600" period="2.5" departLane="best" departSpeed="max"/>
    <flow id="f_wb_under" type="under" route="wb_under" begin="0" end="3600" period="2.5" departLane="best" departSpeed="max"/>
    <flow id="f_eb_surf"  type="surf"  route="eb_surf"  begin="0" end="3600" period="9"   departLane="best" departSpeed="max"/>
    <flow id="f_wb_surf"  type="surf"  route="wb_surf"  begin="0" end="3600" period="9"   departLane="best" departSpeed="max"/>
    <flow id="f_eb_right" type="turn"  route="eb_right" begin="0" end="3600" period="12"  departLane="best" departSpeed="max"/>
    <flow id="f_wb_right" type="turn"  route="wb_right" begin="0" end="3600" period="12"  departLane="best" departSpeed="max"/>
    <flow id="f_ns"       type="cross" route="ns"       begin="0" end="3600" period="6"   departLane="best" departSpeed="max"/>
    <flow id="f_sn"       type="cross" route="sn"       begin="0" end="3600" period="6"   departLane="best" departSpeed="max"/>
    <flow id="f_n_right"  type="turn"  route="n_right"  begin="0" end="3600" period="14"  departLane="best" departSpeed="max"/>
    <flow id="f_s_right"  type="turn"  route="s_right"  begin="0" end="3600" period="14"  departLane="best" departSpeed="max"/>
</routes>
"""


def build():
    """도로·차량 파일을 만들고 netconvert로 컴파일한다. sumocfg 경로를 반환."""
    files = {"underpass.nod.xml": NODES, "underpass.edg.xml": EDGES,
             "underpass.con.xml": CONNECTIONS, "underpass.rou.xml": ROUTES}
    for name, text in files.items():
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(text)
    subprocess.run(
        [checkBinary("netconvert"),
         "-n", os.path.join(HERE, "underpass.nod.xml"),
         "-e", os.path.join(HERE, "underpass.edg.xml"),
         "-x", os.path.join(HERE, "underpass.con.xml"),
         "-o", os.path.join(HERE, "underpass.net.xml"),
         "--no-turnarounds"],
        check=True, capture_output=True)
    write_roof()
    with open(os.path.join(HERE, "underpass.gui.xml"), "w", encoding="utf-8") as f:
        f.write("""<viewsettings>
    <scheme name="real world"/>
    <delay value="80"/>
</viewsettings>
""")
    cfg = os.path.join(HERE, "underpass.sumocfg")
    with open(cfg, "w", encoding="utf-8") as f:
        f.write("""<configuration>
    <input>
        <net-file value="underpass.net.xml"/>
        <route-files value="underpass.rou.xml"/>
        <additional-files value="underpass.roof.xml"/>
    </input>
    <gui_only>
        <gui-settings-file value="underpass.gui.xml"/>
    </gui_only>
    <processing>
        <step-length value="0.5"/>
    </processing>
</configuration>
""")
    return cfg


def write_roof():
    """지하 구간 도로 위에 회색 덮개 다각형을 만든다.

    컴파일된 net.xml에서 지하차도 차선의 실제 좌표를 읽어, 높이가
    UNDERGROUND_Z보다 낮은 구간만 덮는다. 교차로 C 영역은 지상 도로가
    지나가는 곳이라 덮지 않는다. (다각형은 표시용이며 시뮬레이션과 무관)
    """
    with open(os.path.join(HERE, "underpass.net.xml"), encoding="utf-8") as f:
        net = f.read()
    pts = []
    for lane in re.findall(r'<lane id="(?:e_under|w_under)_\d"[^>]*shape="([^"]+)"', net):
        for p in lane.split():
            x, y, *z = map(float, p.split(","))    # 높이 0인 점은 z가 생략되어 저장됨
            if z and z[0] < UNDERGROUND_Z:
                pts.append((x, y))
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts) - 1.6, max(p[1] for p in pts) + 1.6   # 차선 폭 절반만큼 넓힘
    jshape = re.search(r'<junction id="C"[^>]*shape="([^"]+)"', net).group(1)
    jx = [float(p.split(",")[0]) for p in jshape.split()]
    jx0, jx1 = min(jx), max(jx)
    rect = lambda a, b: f"{a:.2f},{y0:.2f} {b:.2f},{y0:.2f} {b:.2f},{y1:.2f} {a:.2f},{y1:.2f}"
    with open(os.path.join(HERE, "underpass.roof.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<additional>
    <!-- 지하차도 덮개 (표시용, 콘크리트색). 색 = R,G,B,투명도 -->
    <poly id="roof_west" type="underpass_roof" color="205,205,195,150" fill="1" layer="10" shape="{rect(x0, jx0)}"/>
    <poly id="roof_east" type="underpass_roof" color="205,205,195,150" fill="1" layer="10" shape="{rect(jx1, x1)}"/>
</additional>
""")


def run(gui: bool, seconds: int):
    cfg = build()
    cmd = [checkBinary("sumo-gui" if gui else "sumo"), "-c", cfg,
           "--no-step-log", "true", "--collision.check-junctions", "true"]
    if gui:
        cmd += ["--start", "--delay", "80"]
    traci.start(cmd)
    if gui:
        # 화면을 도로 전체에 맞춘다 (TraCI gui boundary)
        x0, y0, x1, y1 = traci.simulation.getNetBoundary()[0] + traci.simulation.getNetBoundary()[1]
        traci.gui.setBoundary(traci.gui.DEFAULT_VIEW, x0 - 20, y0 - 20, x1 + 20, y1 + 20)

    base_color = {}
    stats = {"under": [], "surf": [], "cross": []}
    collisions = teleports = 0
    end = seconds / 0.5 if seconds else float("inf")
    step = 0
    try:
        while step < end and traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()
            step += 1
            collisions += traci.simulation.getCollidingVehiclesNumber()
            teleports += traci.simulation.getStartingTeleportNumber()
            for v in traci.vehicle.getIDList():
                vtype = traci.vehicle.getTypeID(v)
                if v not in base_color:
                    base_color[v] = traci.vehicletype.getColor(vtype)[:3]   # vType에 지정한 색
                x, y, z = traci.vehicle.getPosition3D(v)
                underground = traci.vehicle.getRoadID(v) in UNDER_EDGES and z < UNDERGROUND_Z
                if gui:
                    alpha = UNDERGROUND_ALPHA if underground else 255
                    traci.vehicle.setColor(v, base_color[v] + (alpha,))
                elif vtype in stats and abs(x - 600) < 60:   # 교차로 C 앞뒤 60m
                    stats[vtype].append(traci.vehicle.getSpeed(v))
    except traci.exceptions.FatalTraCIError:
        pass   # GUI 창을 닫으면 여기로 온다
    finally:
        try:
            traci.close()
        except Exception:
            pass

    if not gui:
        for key, name in [("under", "지하차도 직진"), ("surf", "지상 직진"), ("cross", "남북 도로")]:
            s = stats[key]
            print(f"{name:8s}: 교차로 부근 평균 속도 {sum(s)/len(s):5.1f} m/s, "
                  f"거의 정지(<1m/s) 비율 {sum(v < 1 for v in s)/len(s):4.0%}")
        print(f"충돌 {collisions}건, 순간이동 {teleports}건")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="교차로 지하차도 데모")
    ap.add_argument("--nogui", action="store_true", help="화면 없이 통계만")
    ap.add_argument("--seconds", type=int, default=None, help="시뮬레이션 길이(초). --nogui 기본 600초")
    args = ap.parse_args()
    run(gui=not args.nogui, seconds=args.seconds or (600 if args.nogui else 0))
