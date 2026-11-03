"""교통: 봉담과천로 흐름, randomTrips 일반 차량, 주차 차량, 버스, 시뮬레이션 설정 파일."""
import math
import os
import subprocess
import sys

from common import SUMO_HOME, P, W


# 범위 경계에서 잘린 큰길 끝 (OSM 이름이 없는 길도 있어 위치로 찾는다)
ENDS = {"서부로 남쪽": (-260, -1240), "덕영대로 서쪽": (-350, 45), "덕영대로 동쪽": (1140, -1115),
        "정자천로 동쪽": (1194, -1010), "일월로 남쪽": (474, -1439), "화산로 남동쪽": (1054, -1181),
        "화산로 서쪽": (-458, -39), "율전로 서쪽": (-569, -547), "하률로 동쪽": (605, 333), "만석로 동쪽": (1034, -567)}


def fringe(net, p):
    """p 근처 범위 경계 끝에서 들어오는(src)/나가는(snk) 엣지."""
    ends = [n for n in net.getNodes() if math.dist(n.getCoord()[:2], p) < 40
            and len({e.getFromNode() for e in n.getIncoming()} | {e.getToNode() for e in n.getOutgoing()}) == 1]
    src = [e for n in ends for e in n.getOutgoing()]
    snk = [e for n in ends for e in n.getIncoming()]
    return (src[0].getID() if src else None), (snk[0].getID() if snk else None)


def flow(rows, fid, src, dst, vph, typ, stop=""):
    head = (f'    <flow id="{fid}" type="{typ}" begin="0" end="3600" period="exp({vph / 3600:.4f})" '
            f'from="{src}" to="{dst}" departLane="best" departSpeed="max"')
    rows.append(f"{head}>{stop}</flow>\n" if stop else f"{head}/>\n")


CLASS_W = {"secondary": 3, "secondary_link": 1, "tertiary": 2, "tertiary_link": 1, "unclassified": 1,
           "residential": 1, "living_street": 0.4, "service": 0.2}


def write_trip_weights(net, prefix):
    """randomTrips 출발(src)·도착(dst) 확률. 경계 큰길: 차로 하나당 400, 안쪽: 길이 100 m당 길 종류 값."""
    src, dst = {}, {}
    for e in net.getEdges():
        eid, kind = e.getID(), e.getType().replace("highway.", "")
        if not e.allows("passenger") or eid.startswith(("hw_", "P1_", "P2_", "P3_")) or kind not in CLASS_W:
            continue
        inner = e.getLength() / 100 * CLASS_W[kind]
        big = e.getSpeed() > 10
        src[eid] = 400 * e.getLaneNumber() if big and not e.getFromNode().getIncoming() else inner
        dst[eid] = 400 * e.getLaneNumber() if big and not e.getToNode().getOutgoing() else inner
    for ext, w in (("src", src), ("dst", dst)):
        with open(f"{prefix}.{ext}.xml", "w", encoding="utf-8") as f:
            f.write('<edgedata>\n    <interval begin="0" end="3600">\n'
                    + "".join(f'        <edge id="{k}" value="{v:.2f}"/>\n' for k, v in w.items() if v > 0)
                    + "    </interval>\n</edgedata>\n")


def parking_caps():
    """skku.add.xml의 주차 구역별 칸 수 (<space> 개수)."""
    import xml.etree.ElementTree as ET
    return {pa.get("id"): len(pa.findall("space")) or int(pa.get("roadsideCapacity", 1))
            for pa in ET.parse(P("skku.add.xml")).getroot().findall("parkingArea")}


def write_routes(net, groups):
    import xml.etree.ElementTree as ET
    ends = {k: fringe(net, p) for k, p in ENDS.items()}
    missing = [k for k, v in ends.items() if not (v[0] and v[1])]
    if missing:
        print("경계 끝을 못 찾음:", missing)
    ends = {k: v for k, v in ends.items() if v[0] and v[1]}
    rows = []
    # 봉담과천로 (정체파 실험용 IDM 차량). 고속도로가 서부로에 바로 이어져 있어 본선 차가 모두 사거리로 들어오면 막힌다
    #   → 요금소 북쪽 구간은 한 방향 약 1,000~1,200대/h, 대부분 청계IC·학의JC로 드나들고
    #     요금소를 지나 서부로로 들어오는 차는 한 방향 약 400대/h (사거리 직진 → 서부로 고가 → 서부로 남쪽 끝 포함)
    #   (서부로로 800대/h를 넣었을 때 서부로 남행이 사거리까지 막혀 지연 175~220초, 청계IC 1차로 진출로는 1,100대/h에서도 막힘 → 850대/h,
    #    1차로 진입로 하나에서 1,600대/h를 출발시키면 절반이 못 들어감 → 750대/h)
    sw_src, sw_snk = ends["서부로 남쪽"]
    flow(rows, "hw_s", "hw_hS0_hS1", sw_snk, 150, "hwcar")
    flow(rows, "hw_s_cgout", "hw_hS0_hS1", "hw_cg_out", 700, "hwcar")
    flow(rows, "hw_s_jc", "hw_jc_in", "hw_cg_out", 150, "hwcar")
    flow(rows, "hw_s_cg", "hw_cg_in", sw_snk, 60, "hwcar")
    flow(rows, "hw_s_rest", "hw_hS0_hS1", sw_snk, 60, "hwcar", '<stop parkingArea="RS" duration="300"/>')
    flow(rows, "hw_n", sw_src, "hw_hN1_hN0", 150, "car")
    flow(rows, "hw_n_cg", "hw_cg_in2", "hw_hN1_hN0", 600, "hwcar")
    flow(rows, "hw_n_jc", "hw_cg_in2", "hw_jc_out", 150, "hwcar")
    flow(rows, "hw_n_rest", sw_src, "hw_hN1_hN0", 40, "car", '<stop parkingArea="RN" duration="300"/>')
    for i, (src, snk) in enumerate(ends.values()):
        flow(rows, f"hw_in_{i}", "hw_hS0_hS1", snk, 15, "hwcar")       # 사당 → 의왕TG → 서부로 → 우리 지역
        flow(rows, f"hw_out_{i}", src, "hw_hN1_hN0", 12, "car")        # 우리 지역 → 서부로 → 의왕TG → 사당
    # 주차하러 오는 차 (parking.py): 고가 밑 공영주차장 3곳 각 20대/h, 교내·역 주변 주차장은 구역 10개당 6대/h
    import parking
    with open(P("parking.rou.xml"), "w", encoding="utf-8") as f:
        f.write("<routes>\n" + "".join(parking.vehicles(groups, ends, {"P1": 20, "P2": 20, "P3": 20, "L": 6}, caps=parking_caps()))
                + "</routes>\n")
    # 버스: 카카오맵 실제 노선 17개(성대역 주변 정류장을 지나는 노선)의 경로·정류장·배차 간격 (bus_lines.py)
    import bus_lines
    n_stop, n_run = bus_lines.build(P("skku.net.xml"), P("bus.rou.xml"), P("bus.stops.xml"), report=lambda m: None)
    print(f"버스: 정류장 {n_stop}곳, 노선 운행 {n_run}개")
    # 주차하러 오는 차(parker)만 고가 밑 공영주차장 통로(allow="taxi")를 쓰게 vClass를 taxi로 둔다 (모양은 승용차).
    #   통로를 모두에게 열어 두었더니 버스 노선 5개가 주차장 1 통로를 지름길로 지나갔다
    #   (vClass: userdoc/Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html)
    with open(P("vtypes.add.xml"), "w", encoding="utf-8") as f:
        f.write('<additional>\n'
                '    <vType id="car" sigma="0.5" impatience="0.5" color="255,220,0" guiShape="passenger"/>\n'
                '    <vType id="hwcar" carFollowModel="IDM" accel="1.0" decel="2.0" tau="1.2" impatience="0.5" '
                'lcStrategic="3" lcAssertive="1.5" '
                'color="100,200,255" guiShape="passenger/sedan"/>\n'
                '    <vType id="parker" vClass="taxi" sigma="0.5" impatience="1.0" color="255,120,0" guiShape="passenger/hatchback"/>\n'
                '    <vType id="bus" vClass="bus" color="0,160,80" guiShape="bus"/>\n</additional>\n')
    with open(P("skku.rou.xml"), "w", encoding="utf-8") as f:
        f.write("<routes>\n")
        f.writelines(rows)
        f.write("</routes>\n")
    # 일반 차량: SUMO 표준 도구 randomTrips (userdoc/Tools/Trip.html) + 출발·도착 확률 파일(--weights-prefix).
    #   범위 경계로 드나드는 큰길(시속 36 km 넘는 길)이 대부분(약 75%), 안쪽은 길 종류·길이에 비례해 조금.
    #   막다른 골목·교내·단지 도로에서는 거의 안 나오고, 고속화도로·주차장 통로는 0
    write_trip_weights(net, W("trip_w"))
    subprocess.run([sys.executable, os.path.join(SUMO_HOME, "tools", "randomTrips.py"), "-n", P("skku.net.xml"),
                    "-o", W("random.trips.xml"), "-r", W("random.validated.rou.xml"), "-b", "0", "-e", "3600", "-p", "3.5", "--weights-prefix", W("trip_w"),
                    "--min-distance", "300", "--seed", "42", "--edge-permission", "passenger", "--validate",
                    "-a", P("vtypes.add.xml"),
                    "--trip-attributes", 'type="car" departLane="best"', "--prefix", "r"],
                   capture_output=True, text=True, check=True)
    root = ET.parse(W("random.trips.xml")).getroot()
    bad = lambda e: e.startswith(("hw_", "P1_", "P2_", "P3_"))
    for t in list(root):
        if t.tag not in ("vehicle", "trip"):
            continue
        r = t.find("route")
        edges = (r.get("edges") if r is not None else f'{t.get("from")} {t.get("to")}').split()
        if bad(edges[0]) or bad(edges[-1]):
            root.remove(t)
    ET.ElementTree(root).write(P("random.rou.xml"), encoding="utf-8", xml_declaration=True)
    return ends


def write_cfg():
    with open(P("skku.sumocfg"), "w", encoding="utf-8") as f:
        f.write("""<configuration>
    <input>
        <net-file value="skku.net.xml"/>
        <route-files value="skku.rou.xml,bus.rou.xml,parking.rou.xml,random.rou.xml"/>
        <additional-files value="vtypes.add.xml,bus.stops.xml,skku.add.xml,bg.add.xml"/>
        <gui-settings-file value="skku.gui.xml"/>
    </input>
    <time><begin value="0"/><end value="3600"/><step-length value="0.2"/></time>
    <processing><time-to-teleport value="300"/><collision.action value="warn"/><ignore-route-errors value="true"/></processing>
    <random_number><seed value="42"/></random_number>
</configuration>
""")
