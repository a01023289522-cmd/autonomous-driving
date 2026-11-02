"""성균관대역 일대 SUMO 도로 환경 만들기 (2차: 범위 조정 + 고속화도로 + 사거리 신호).

입력 : skku.osm.xml  (OpenStreetMap 공식 API로 받은 원본 지도)
출력 : skku_area.net.xml, skku_area.stops.add.xml, skku_area.parking.add.xml,
       skku_area.tls.add.xml, skku_area.bus.rou.xml, skku_area.cars.rou.xml,
       skku_area.parking.rou.xml, skku_area.highway.rou.xml, skku_area.sumocfg

범위 (실제 지도 기준, 아래 MAIN / CORRIDOR / HWY_LAT_MAX):
  - 학교 주변(MAIN): 성대역 사거리 ~ 서부로 남쪽 정문 방향 ~ 덕영대로 육교 동쪽 건너편까지 전부
  - 서쪽(CORRIDOR): 덕영대로와 고속화도로 진출입로만 남기고 의왕·1호선 쪽 골목은 제외
  - 고속화도로: 봉담과천로를 진출로에서 북쪽으로 약 2.6km만 실제 모양 그대로 사용
                (사당역까지 약 23km 중 학교 쪽 끝부분)
신호 : 성대역 사거리 = 방향별 신호 + 적색 우회전(s) + 보행자 동시신호(스크램블, 차량 전부 정지)
       그 밖의 큰 교차로 = SUMO 자동 배치 (--tls.guess). 실제 신호는 나중에 조사 후 수정.

실행:
    python build_area.py           # 파일 생성
    python build_area.py --check   # 생성 후 화면 없이 15분 돌려 검증
    sumo-gui -c skku_area.sumocfg  # 화면으로 보기
"""
import argparse
import math
import os
import random
import subprocess
import sys
import xml.etree.ElementTree as ET

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))
import sumolib  # noqa: E402
from sumolib import checkBinary  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda name: os.path.join(HERE, name)

# 범위 (경도 lon, 위도 lat): (서, 남, 동, 북)
MAIN = (126.9690, 37.2945, 126.9820, 37.3022)      # 학교 주변: 모든 도로 유지
CORRIDOR = (126.9590, 37.2998, 126.9700, 37.3050)  # 서쪽: 덕영대로와 진출입로만 유지
HWY_LAT_MAX = 37.3300                               # 고속화도로는 이 위도까지만 (진출로에서 약 2.6km)
HWY_LON_MIN = 126.9585                              # 진출로 남쪽으로 이어지는 본선은 이 경도까지만
BBOX = (126.9585, 37.2940, 126.9825, HWY_LAT_MAX + 0.001)   # netconvert 최종 자르기
STATION = (126.97118, 37.30029)        # 성균관대역
SAGEORI = (126.97268, 37.30055)        # 성대역 사거리 (OSM 신호 노드 4개의 중심)
SIM_END = 1800                          # 교통 수요를 만들 시간(초)
random.seed(42)

DRIVABLE = {"motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
            "secondary", "secondary_link", "tertiary", "tertiary_link", "unclassified",
            "residential", "living_street", "service"}


def inside(box, lon, lat):
    return box[0] <= lon <= box[2] and box[1] <= lat <= box[3]


# ──────────────────────────────────────────────────────────────
# 0) OSM 원본 거르기: 범위 밖 도로를 잘라낸 OSM 파일을 만든다
#    - 도로(way)마다 범위 안에 있는 연속 구간만 남긴다 (경계에서 끊긴 끝은 차량 출입구가 됨)
#    - 고속화도로(trunk, trunk_link)는 학교 범위 밖이어도 HWY_LAT_MAX까지 유지
# ──────────────────────────────────────────────────────────────
def filter_osm():
    tree = ET.parse(P("skku.osm.xml"))
    root = tree.getroot()
    pos = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.iter("node")}
    next_id = 9_000_000_000
    kept = {"local": 0, "corridor": 0, "highway": 0}
    for w in list(root.findall("way")):
        tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
        hw = tags.get("highway")
        if hw not in DRIVABLE:
            root.remove(w)
            continue
        is_hwy = hw in ("trunk", "trunk_link")
        is_corridor_road = is_hwy or "덕영대로" in tags.get("name", "")

        def keep_node(ref):
            if ref not in pos:
                return False
            lon, lat = pos[ref]
            if inside(MAIN, lon, lat):
                return True
            if is_corridor_road and inside(CORRIDOR, lon, lat):
                return True
            return is_hwy and lat <= HWY_LAT_MAX and lon >= HWY_LON_MIN
        refs = [nd.get("ref") for nd in w.findall("nd")]
        runs, cur = [], []
        for r in refs:
            if keep_node(r):
                cur.append(r)
            elif cur:
                runs.append(cur); cur = []
        if cur:
            runs.append(cur)
        runs = [r for r in runs if len(r) >= 2]
        root.remove(w)
        for i, run in enumerate(runs):
            nw = ET.SubElement(root, "way", w.attrib)
            if i > 0:                                   # 잘려서 두 조각이 되면 새 id
                nw.set("id", str(next_id)); next_id += 1
            for r in run:
                ET.SubElement(nw, "nd", ref=r)
            for t in w.findall("tag"):
                ET.SubElement(nw, "tag", t.attrib)
            kept["highway" if is_hwy else "corridor" if is_corridor_road and not inside(MAIN, *pos[run[0]]) else "local"] += 1
    for rel in list(root.findall("relation")):          # 지운 도로를 가리키는 회전 제한은 제거
        root.remove(rel)
    tree.write(P("skku_area.filtered.osm.xml"), encoding="utf-8", xml_declaration=True)
    return kept


# ──────────────────────────────────────────────────────────────
# 1) 도로망: OSM → SUMO
#    SUMO 문서 Networks/Import/OpenStreetMap.html 권장 옵션 사용.
#    OSM 높이(layer) 추정값이 틀려서(지하차도가 +30m) 높이는 넣지 않는다.
#    고가·지하차도는 아래 도로와 노드를 공유하지 않으므로 높이 없이도 서로 막지 않는다.
# ──────────────────────────────────────────────────────────────
def build_net():
    cmd = [checkBinary("netconvert"),
           "--osm-files", P("skku_area.filtered.osm.xml"),
           "--keep-edges.in-geo-boundary", ",".join(map(str, BBOX)),
           "--keep-edges.by-vclass", "passenger,bus",
           "--remove-edges.isolated", "--keep-edges.components", "1",
           "--geometry.remove", "--ramps.guess", "--junctions.join",
           "--tls.guess-signals", "--tls.discard-simple", "--tls.join",
           "--tls.guess", "--tls.guess.threshold", "50",                       # 큰 교차로에 기본 신호 자동 배치
           "--osm.turn-lanes", "--output.street-names", "--no-turnarounds",
           "--ptstop-output", P("skku_area.stops.add.xml"),
           "-o", P("skku_area.net.xml")]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr[-2000:])
    return sumolib.net.readNet(P("skku_area.net.xml"))


def lonlat_to_xy(net, lon, lat):
    """경위도 → 네트워크 좌표. sumolib는 pyproj가 필요해서, net.xml의
    projParameter(UTM 52구역, WGS84)와 netOffset을 이용해 직접 변환한다."""
    a, f, k0 = 6378137.0, 1 / 298.257223563, 0.9996
    e2 = f * (2 - f); ep2 = e2 / (1 - e2)
    lon0 = math.radians(52 * 6 - 183)                      # UTM 52구역 중앙 경선 129°
    phi, lam = math.radians(lat), math.radians(lon)
    N = a / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    T, C = math.tan(phi) ** 2, ep2 * math.cos(phi) ** 2
    A = math.cos(phi) * (lam - lon0)
    M = a * ((1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * phi
             - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * phi)
             + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * phi)
             - (35 * e2 ** 3 / 3072) * math.sin(6 * phi))
    E = k0 * N * (A + (1 - T + C) * A ** 3 / 6 + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120) + 500000
    Nn = k0 * (M + N * math.tan(phi) * (A ** 2 / 2 + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24
                                      + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720))
    ox, oy = net.getLocationOffset()
    return E + ox, Nn + oy


# ──────────────────────────────────────────────────────────────
# 1-1) 성대역 사거리 신호 (SUMO 문서 Simulation/Traffic_Lights.html)
#    대각선 횡단보도가 있는 사거리 → 보행자 동시신호(스크램블)로 해석:
#      ① 축 A 녹색 → 황색  ② 축 B 녹색 → 황색  ③ 차량 전부 정지(보행자 전 방향 횡단)
#    좌회전은 'g'(마주 오는 직진에 양보), 우회전은 다른 축 녹색 동안 's'
#    ('s' = 멈춘 뒤 안전하면 진행하는 우회전 — 한국 적색 신호 우회전 규칙).
#    시간(초)은 임의값. 실제 주기는 현장 확인 후 수정한다.
# ──────────────────────────────────────────────────────────────
GREEN_A, GREEN_B, YELLOW, SCRAMBLE = 40, 35, 4, 20


def build_sageori_tls(net):
    sx, sy = lonlat_to_xy(net, *SAGEORI)
    best = None
    for tls in net.getTrafficLights():
        conns = tls.getConnections()
        if not conns:
            continue
        cx = sum(c[0].getEdge().getToNode().getCoord()[0] for c in conns) / len(conns)
        cy = sum(c[0].getEdge().getToNode().getCoord()[1] for c in conns) / len(conns)
        d = math.hypot(cx - sx, cy - sy)
        if best is None or d < best[0]:
            best = (d, tls)
    dist, tls = best
    links = {}
    for in_lane, out_lane, idx in tls.getConnections():
        shape = in_lane.getShape()
        (x0, y0), (x1, y1) = shape[-2], shape[-1]
        axis = math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180      # 진행 방향(앞뒤 구분 없음)
        conn = [c for c in in_lane.getEdge().getConnections(out_lane.getEdge())
                if c.getFromLane() == in_lane and c.getToLane() == out_lane]
        links[idx] = (axis, conn[0].getDirection() if conn else "s")
    # 진행 방향 각도를 두 무리(축 A, 축 B)로 나눈다: 정렬 후 가장 큰 간격에서 자르기
    angles = sorted({round(a) for a, _ in links.values()})
    gaps = [((angles[(i + 1) % len(angles)] - angles[i]) % 180, i) for i in range(len(angles))]
    _, cut = max(gaps)
    start = angles[(cut + 1) % len(angles)]
    in_a = lambda a: ((round(a) - start) % 180) < ((angles[cut] - start) % 180) + 1
    n = max(links) + 1

    def state(phase):
        s = []
        for i in range(n):
            axis, d = links.get(i, (0, "s"))
            mine = in_a(axis) == (phase in ("A", "Ay"))
            right = d in ("r", "R")
            if phase == "X":                    # 스크램블: 차량 전부 정지
                s.append("r")
            elif mine:
                s.append("y" if phase.endswith("y") else ("g" if d in ("l", "L") else "G"))
            else:
                s.append("s" if right else "r")
        return "".join(s)
    phases = [(GREEN_A, state("A")), (YELLOW, state("Ay")), (GREEN_B, state("B")),
              (YELLOW, state("By")), (SCRAMBLE, state("X"))]
    with open(P("skku_area.tls.add.xml"), "w", encoding="utf-8") as f:
        f.write(f'<additional>\n    <!-- 성대역 사거리: 방향별 신호 + 적색 우회전(s) + 보행자 동시신호(차량 전부 r) -->\n'
                f'    <tlLogic id="{tls.getID()}" type="static" programID="sageori" offset="0">\n')
        for dur, st in phases:
            f.write(f'        <phase duration="{dur}" state="{st}"/>\n')
        f.write("    </tlLogic>\n</additional>\n")
    return tls.getID(), dist, n


# ──────────────────────────────────────────────────────────────
# 1-2) 고속화도로 교통 (봉담과천로 남쪽 방향, 사당 쪽에서 내려오는 차)
#    정체파(유령체증) 재현용으로 IDM 차량을 촘촘히 넣는다 (링 실험: IDM + 높은 밀도에서 발생).
#    일부는 진출로로 내려와 덕영대로 → 성대역 사거리로, 나머지는 본선 직진.
# ──────────────────────────────────────────────────────────────
def build_highway_flow(net):
    hw = [e for e in net.getEdges() if e.getType().endswith(".trunk")]
    entry = max((e for e in hw if not [i for i in e.getIncoming() if i.getType().endswith(".trunk")]),
                key=lambda e: e.getFromNode().getCoord()[1])          # 가장 북쪽에서 시작하는 본선
    sx, sy = lonlat_to_xy(net, *STATION)
    to_station = min((e for e in net.getEdges() if e.getFunction() != "internal"
                      and "서부로" in e.getName() and e.getFromNode().getCoord()[1] < sy - 80
                      and e.allows("passenger")),
                     key=lambda e: math.hypot(e.getFromNode().getCoord()[0] - sx, e.getFromNode().getCoord()[1] - sy))
    exits_hw = [e for e in hw if not e.getOutgoing()]
    routes = {}
    p, _ = net.getShortestPath(entry, to_station, vClass="passenger")
    if p:
        routes["to_school"] = [e.getID() for e in p]
    for e in exits_hw:
        p, _ = net.getShortestPath(entry, e, vClass="passenger")
        if p and all("trunk" in x.getType() for x in p):
            routes["through"] = [x.getID() for x in p]
            break
    length = sum(net.getEdge(e).getLength() for e in routes.get("through", []))
    with open(P("skku_area.highway.rou.xml"), "w", encoding="utf-8") as f:
        f.write('<routes>\n    <vType id="hwcar" carFollowModel="IDM" color="200,200,255" speedDev="0.1"/>\n')
        for rid, edges in routes.items():
            f.write(f'    <route id="hw_{rid}" edges="{" ".join(edges)}"/>\n')
        if "through" in routes:
            f.write(f'    <flow id="hw_through" type="hwcar" route="hw_through" begin="0" end="{SIM_END}" '
                    f'vehsPerHour="1800" departLane="random" departSpeed="max"/>\n')
        if "to_school" in routes:
            f.write(f'    <flow id="hw_school" type="hwcar" route="hw_to_school" begin="0" end="{SIM_END}" '
                    f'vehsPerHour="360" departLane="random" departSpeed="max"/>\n')
        f.write("</routes>\n")
    return entry.getID(), list(routes), length


def drivable_lane(edge, vclass="passenger"):
    """차량이 다닐 수 있는 가장 오른쪽 차선."""
    for lane in edge.getLanes():
        if lane.allows(vclass):
            return lane
    return None


# ──────────────────────────────────────────────────────────────
# 2) 주차장: OSM 주차장 영역 중 역과 가까운 3곳 → 가장 가까운 도로에 출입구(parkingArea)
#    SUMO 문서 Simulation/ParkingArea.html
# ──────────────────────────────────────────────────────────────
def build_parking(net):
    root = ET.parse(P("skku.osm.xml")).getroot()
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.iter("node")}
    lots = []
    for w in root.iter("way"):
        tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
        if tags.get("amenity") != "parking":
            continue
        pts = [nodes[nd.get("ref")] for nd in w.findall("nd") if nd.get("ref") in nodes]
        if not pts:
            continue
        lon = sum(p[0] for p in pts) / len(pts)
        lat = sum(p[1] for p in pts) / len(pts)
        if not (BBOX[0] < lon < BBOX[2] and BBOX[1] < lat < BBOX[3]):
            continue
        d = math.hypot((lon - STATION[0]) * 88000, (lat - STATION[1]) * 111000)
        lots.append((d, lon, lat, tags.get("name", "")))
    areas = []
    used_edges = set()
    for d, lon, lat, name in sorted(lots):
        x, y = lonlat_to_xy(net, lon, lat)
        cands = sorted(net.getNeighboringEdges(x, y, 80), key=lambda c: c[1])
        for edge, dist in cands:
            lane = drivable_lane(edge)
            if lane is None or edge.getID() in used_edges or lane.getLength() < 30 \
                    or edge.getFunction() == "internal":
                continue
            L = lane.getLength()
            start = max(5.0, L / 2 - 15)
            areas.append(dict(id=f"pa{len(areas)}", lane=lane.getID(), edge=edge.getID(),
                              start=start, end=min(L - 5, start + 30), name=name, dist=d))
            used_edges.add(edge.getID())
            break
        if len(areas) == 3:
            break
    with open(P("skku_area.parking.add.xml"), "w", encoding="utf-8") as f:
        f.write("<additional>\n")
        for a in areas:
            f.write(f'    <parkingArea id="{a["id"]}" lane="{a["lane"]}" startPos="{a["start"]:.1f}" '
                    f'endPos="{a["end"]:.1f}" roadsideCapacity="8" name="{a["name"] or a["id"]}"/>'
                    f'   <!-- 역에서 {a["dist"]:.0f}m 주차장 -->\n')
        f.write("</additional>\n")
    return areas


# ──────────────────────────────────────────────────────────────
# 3) 버스: OSM 정류장을 지나는 노선 2개 (남북, 동서)
#    SUMO 문서 Simulation/Public_Transport.html (busStop + stop)
# ──────────────────────────────────────────────────────────────
def read_stops():
    root = ET.parse(P("skku_area.stops.add.xml")).getroot()
    stops = []
    for s in root.iter("busStop"):
        stops.append(dict(id=s.get("id"), lane=s.get("lane"), edge=s.get("lane").rsplit("_", 1)[0],
                          start=float(s.get("startPos")), end=float(s.get("endPos")),
                          name=s.get("name", "")))
    return stops


def build_bus(net, stops):
    def pos(s):
        return net.getLane(s["lane"]).getShape()[0]
    lines = []
    for axis, label in [(1, "남북"), (0, "동서")]:
        ordered = sorted(stops, key=lambda s: pos(s)[axis])
        best = None
        # 축 방향 양 끝 정류장 쌍 중, 경로 위에 정류장이 가장 많이 놓이는 조합
        for a in ordered[:6]:
            for b in ordered[-6:]:
                ea, eb = net.getEdge(a["edge"]), net.getEdge(b["edge"])
                path, _ = net.getShortestPath(ea, eb, vClass="bus")
                if not path:
                    continue
                ids = [e.getID() for e in path]
                on = [s for s in stops if s["edge"] in ids]
                on.sort(key=lambda s: (ids.index(s["edge"]), s["start"]))
                if best is None or len(on) > len(best[1]):
                    best = (ids, on)
        if best:
            lines.append((label, *best))
    with open(P("skku_area.bus.rou.xml"), "w", encoding="utf-8") as f:
        f.write('<routes>\n    <vType id="bus" vClass="bus" color="0,160,80" length="11" carFollowModel="IDM"/>\n')
        for i, (label, edges, on) in enumerate(lines):
            f.write(f'    <!-- 버스 {label} 노선: 정류장 {len(on)}곳 -->\n')
            f.write(f'    <flow id="bus{i}" type="bus" begin="0" end="{SIM_END}" period="150">\n')
            f.write(f'        <route edges="{" ".join(edges)}"/>\n')
            for s in on:
                f.write(f'        <stop busStop="{s["id"]}" duration="20"/>   <!-- {s["name"]} -->\n')
            f.write("    </flow>\n")
        f.write("</routes>\n")
    return lines


# ──────────────────────────────────────────────────────────────
# 4) 일반 차량: SUMO 공식 도구 randomTrips.py (문서 Tools/Trip.html)
#    바깥(fringe)에서 들어와 나가는 차를 많이 만들어 통과 교통을 흉내 낸다.
# ──────────────────────────────────────────────────────────────
def build_cars():
    subprocess.run([sys.executable, os.path.join(SUMO_HOME, "tools", "randomTrips.py"),
                    "-n", P("skku_area.net.xml"), "-o", P("skku_area.trips.xml"),
                    "-r", P("skku_area.cars.rou.xml"),
                    "-e", str(SIM_END), "--period", "1.6", "--fringe-factor", "10",
                    "--min-distance", "400", "--vehicle-class", "passenger",
                    "--prefix", "car", "--seed", "42", "--validate",
                    "--trip-attributes", 'departLane="best" departSpeed="max"'],
                   check=True, capture_output=True)


# ──────────────────────────────────────────────────────────────
# 5) 주차장 이용 차량: 바깥 → 주차장(60~180초 정차) → 바깥
# ──────────────────────────────────────────────────────────────
def build_parking_visitors(net, areas):
    fringe = [e for e in net.getEdges() if e.is_fringe() and drivable_lane(e)]
    entries = [e for e in fringe if not e.getIncoming()]
    exits = [e for e in fringe if not e.getOutgoing()]
    with open(P("skku_area.parking.rou.xml"), "w", encoding="utf-8") as f:
        f.write('<routes>\n    <vType id="visitor" color="255,120,0" carFollowModel="IDM"/>\n')
        n = 0
        for t in range(0, SIM_END, 45):
            a = areas[n % len(areas)]
            pe = net.getEdge(a["edge"])
            for _ in range(10):
                src, dst = random.choice(entries), random.choice(exits)
                p1, _ = net.getShortestPath(src, pe, vClass="passenger")
                p2, _ = net.getShortestPath(pe, dst, vClass="passenger")
                if p1 and p2:
                    edges = [e.getID() for e in p1] + [e.getID() for e in p2[1:]]
                    f.write(f'    <vehicle id="visit{n}" type="visitor" depart="{t}" departLane="best">\n'
                            f'        <route edges="{" ".join(edges)}"/>\n'
                            f'        <stop parkingArea="{a["id"]}" duration="{random.randint(60, 180)}"/>\n'
                            f'    </vehicle>\n')
                    n += 1
                    break
        f.write("</routes>\n")


def write_cfg():
    with open(P("skku_area.gui.xml"), "w", encoding="utf-8") as f:
        f.write('<viewsettings>\n    <scheme name="real world"/>\n    <delay value="50"/>\n</viewsettings>\n')
    with open(P("skku_area.sumocfg"), "w", encoding="utf-8") as f:
        f.write("""<configuration>
    <input>
        <net-file value="skku_area.net.xml"/>
        <route-files value="skku_area.bus.rou.xml,skku_area.cars.rou.xml,skku_area.parking.rou.xml,skku_area.highway.rou.xml"/>
        <additional-files value="skku_area.stops.add.xml,skku_area.parking.add.xml,skku_area.tls.add.xml"/>
    </input>
    <processing>
        <step-length value="0.5"/>
        <time-to-teleport value="180"/>
    </processing>
    <gui_only>
        <gui-settings-file value="skku_area.gui.xml"/>
    </gui_only>
</configuration>
""")


def check():
    """화면 없이 15분 돌려서 안정성 확인."""
    r = subprocess.run([checkBinary("sumo"), "-c", P("skku_area.sumocfg"), "--end", "900",
                        "--no-step-log", "true", "--duration-log.statistics", "true",
                        "--collision.check-junctions", "true"],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    warn = [l for l in out.splitlines() if l.startswith("Warning")]
    kinds = {}
    for l in warn:
        k = ("teleport" if "Teleporting" in l else "collision" if "ollision" in l
             else "emergency braking" if "emergency" in l else "기타")
        kinds[k] = kinds.get(k, 0) + 1
    stats = [l for l in out.splitlines() if l.startswith((" Inserted", " Running", " Waiting",
                                                          " Teleports", " Collisions", " Emergency"))]
    return kinds, stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    kept = filter_osm()
    net = build_net()
    tls_id, tls_dist, tls_links = build_sageori_tls(net)
    hw_entry, hw_routes, hw_len = build_highway_flow(net)
    stops = read_stops()
    areas = build_parking(net)
    lines = build_bus(net, stops)
    build_cars()
    build_parking_visitors(net, areas)
    write_cfg()
    tls = len(net.getTrafficLights())
    print(f"OSM 거르기: 학교 주변 {kept['local']}개, 서쪽 덕영대로 {kept['corridor']}개, 고속화도로 {kept['highway']}개 도로 조각 유지")
    print(f"성대역 사거리 신호: {tls_id} (지점과 {tls_dist:.0f}m), 연결 {tls_links}개 → 스크램블 신호 적용")
    print(f"고속화도로: 시작 엣지 {hw_entry}, 노선 {hw_routes}, 본선 길이 {hw_len:.0f}m")
    print(f"도로 구간 {len(net.getEdges())}개, 교차로 {len(net.getNodes())}개, 신호 교차로 {tls}개, "
          f"버스 정류장 {len(stops)}곳, 주차장 {len(areas)}곳, 버스 노선 {len(lines)}개 "
          f"(정류장 {[len(l[2]) for l in lines]}곳 경유)")
    if args.check:
        kinds, stats = check()
        print("경고 종류:", kinds)
        print("\n".join(stats))
