"""주차장: 통로 양옆 한 칸 한 칸 주차면(<space>)과, 그 주차장에 들렀다 가는 차.

- 고가 밑 공영주차장(P1~P3)과 교내·역 주변 OSM 주차장(amenity=parking 면 안의 통로 엣지).
- 주차면: 통로 가장자리에서 0.2 m 떨어져 깊이 5 m, 2.5 m 간격, 통로와 직각으로 나란히 (userdoc/Simulation/ParkingArea.html).
  <space x y>는 칸 가운데가 아니라 바깥 끝이다 (가운데로 알고 놓았더니 칸이 통로와 마주 보는 줄에 겹쳤다: 화면 확인).
  다른 도로와 겹치는 칸은 뺀다.
- SUMO는 한 주차 구역 안에서 빈칸을 앞에서부터 채운다 → 구역을 6칸씩 잘게 나누고 차마다 구역을 무작위로 골라
  주차가 흩어지게 한다.
"""
import math
import random
import xml.etree.ElementTree as ET

from sumolib import geomhelper

import osm_clip

PITCH, DEPTH, CHUNK = 2.5, 5.0, 6
PLACED = []                         # 이미 놓은 칸 가운데 (교내 주차장 통로끼리 칸이 겹치지 않게)


def lot_polygons(osm_files, area):
    polys = []
    for f in osm_files:
        root = ET.parse(f).getroot()
        pos = {n.get("id"): osm_clip.xy(float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
        for w in root.findall("way"):
            t = {x.get("k"): x.get("v") for x in w.findall("tag")}
            refs = [r.get("ref") for r in w.findall("nd")]
            if t.get("amenity") == "parking" and refs[0] == refs[-1] and all(r in pos for r in refs):
                p = [pos[r] for r in refs[:-1]]
                if osm_clip.inside(area, (sum(x for x, _ in p) / len(p), sum(y for _, y in p) / len(p))):
                    polys.append(p)
    return polys


def height(edge):
    return edge.getLanes()[0].getShape3D()[0][2]


def spaces_along(net, edge, sides):
    """엣지 첫 차로를 따라 주차면 (거리, x, y, 각도). sides: 1 = 오른쪽, -1 = 왼쪽."""
    lane = edge.getLanes()[0]
    sh = [p[:2] for p in lane.getShape()]
    L = geomhelper.polyLength(sh)
    off = lane.getWidth() / 2 + DEPTH + 0.2         # <space x y>는 칸의 바깥 끝 (칸은 거기서 통로 쪽으로 DEPTH만큼: 화면 확인)
    out, d = [], 6 + PITCH / 2
    others = {edge.getID()} | {e.getID() for e in edge.getToNode().getOutgoing() if e.getToNode() == edge.getFromNode()}
    while d < L - 6:
        cx, cy = geomhelper.positionAtShapeOffset(sh, d)
        ax, ay = geomhelper.positionAtShapeOffset(sh, max(d - 1, 0))
        bx, by = geomhelper.positionAtShapeOffset(sh, min(d + 1, L))
        n = math.hypot(bx - ax, by - ay) or 1
        ux, uy = (bx - ax) / n, (by - ay) / n
        # <space angle>: sumo-gui는 주차면의 긴 변을 (angle + 90)도(수학 각도, 동쪽 0·반시계) 방향으로 그린다 (화면으로 확인).
        #   통로와 직각인 칸 = angle을 통로 방향의 수학 각도로. 오른쪽·왼쪽 칸은 180도 차이 (차 머리가 칸 안쪽을 향하게)
        ang = math.degrees(math.atan2(uy, ux))
        # 통로가 꺾이는 곳(앞뒤 3 m 방향 차이 15도 넘음)에는 칸을 두지 않는다: 꺾인 곳 칸은 서로 겹치고 비뚤어졌다
        p0, p1 = geomhelper.positionAtShapeOffset(sh, max(d - 3, 0)), geomhelper.positionAtShapeOffset(sh, min(d + 3, L))
        h0 = math.atan2(cy - p0[1], cx - p0[0]) if math.dist(p0, (cx, cy)) > 0.5 else math.radians(ang)
        h1 = math.atan2(p1[1] - cy, p1[0] - cx) if math.dist(p1, (cx, cy)) > 0.5 else math.radians(ang)
        if abs((h1 - h0 + math.pi) % (2 * math.pi) - math.pi) > math.radians(15):
            d += PITCH
            continue
        for s in sides:
            x, y = cx + uy * off * s, cy - ux * off * s
            mx, my = cx + uy * (off - DEPTH / 2) * s, cy - ux * (off - DEPTH / 2) * s     # 칸 가운데
            if not any(e.getID() not in others and dist < 3.0 and abs(height(e)) < 3      # 고가 밑은 겹쳐도 된다
                       for q in ((x, y), (mx, my)) for e, dist in net.getNeighboringEdges(q[0], q[1], 4))                     and not any(math.dist((mx, my), c) < 2.3 for c in PLACED):          # 이웃 통로의 칸과 겹치지 않게
                PLACED.append((mx, my))
                out.append((d, x, y, (ang + (0 if s > 0 else 180)) % 360))
        d += PITCH
    return out


def roadside_spaces(net, edge):
    """고가 옆 공영주차장 통로: 고가 반대쪽(지상 도로 쪽) 한 줄에 통로와 직각인 주차 칸 (거리, x, y, 각도).
    마주 보는 두 줄은 고가 면과 겹쳐 구분이 안 됐고(사용자 지정: 고가 바깥 도로 쪽으로), 평행 주차는 실제(직각)와 달랐다."""
    lane = edge.getLanes()[0]
    sh = [p[:2] for p in lane.getShape()]
    L = geomhelper.polyLength(sh)
    off = lane.getWidth() / 2 + DEPTH + 0.2         # <space x y>는 칸의 바깥 끝 (spaces_along 참고)
    via = [[q[:2] for q in net.getEdge(v).getShape()] for v in ("via_sb", "via_nb") if net.hasEdge(v)]

    def frame(d):
        cx, cy = geomhelper.positionAtShapeOffset(sh, d)
        ax, ay = geomhelper.positionAtShapeOffset(sh, max(d - 1, 0))
        bx, by = geomhelper.positionAtShapeOffset(sh, min(d + 1, L))
        n = math.hypot(bx - ax, by - ay) or 1
        return cx, cy, (bx - ax) / n, (by - ay) / n

    cx, cy, ux, uy = frame(L / 2)                         # 고가에서 먼 쪽 = 도로 쪽
    side = max((1, -1), key=lambda s: min(geomhelper.distancePointToPolygon((cx + uy * off * s, cy - ux * off * s), v)
                                          for v in via))
    out, d = [], 5 + PITCH / 2
    while d < L - 5:
        cx, cy, ux, uy = frame(d)
        ang = math.degrees(math.atan2(uy, ux))           # spaces_along과 같은 각도 규칙 (통로와 직각)
        out.append((d, cx + uy * off * side, cy - ux * off * side, (ang + (0 if side > 0 else 180)) % 360))
        d += PITCH
    return out


def areas_for_edge(net, edge, sides, prefix, name, roadside=False):
    """주차면을 CHUNK칸씩 묶어 parkingArea 여러 개로. roadside: 도로 쪽 한 줄 (roadside_spaces).
    width 0.3: 도로변 주차 자리(쓰지 않음)를 sumo-gui가 기본 폭 3.2 m 파란 띠로 칸 위에 그려 지저분했다."""
    sp = roadside_spaces(net, edge) if roadside else spaces_along(net, edge, sides)
    per = CHUNK * (1 if roadside else len(sides))
    rows, ids = [], []
    for k in range(0, len(sp), per):
        part = sp[k:k + per]
        if len(part) < 3:                                 # 짧은 통로에 한두 칸만 흩어져 놓이던 것은 뺀다
            continue
        aid = f"{prefix}_{len(ids)}"
        a, b = max(part[0][0] - PITCH, 0.5), min(part[-1][0] + PITCH, edge.getLength() - 0.5)
        rows.append(f'    <parkingArea id="{aid}" lane="{edge.getLanes()[0].getID()}" startPos="{a:.1f}" endPos="{b:.1f}" '
                    f'roadsideCapacity="0" width="0.3" name="{name}" friendlyPos="true">\n'
                    + "".join(f'        <space x="{x:.2f}" y="{y:.2f}" width="2.4" length="{DEPTH}" angle="{ang:.1f}"/>\n'
                              for _, x, y, ang in part)
                    + "    </parkingArea>\n")
        ids.append(aid)
    return rows, ids


def build(net, osm_files, area, campus_poly):
    """반환: (additional 줄들, {주차장 이름: [parkingArea id...]})."""
    PLACED.clear()
    rows, groups = [], {}
    # 고가 밑 공영주차장: 통로 엣지 P1_aisle ~ P3_aisle, 도로 쪽 한 줄 직각 주차
    for lot in ("P1", "P2", "P3"):
        if net.hasEdge(f"{lot}_aisle"):
            r, ids = areas_for_edge(net, net.getEdge(f"{lot}_aisle"), (1,), lot, f"공영주차장{lot[1]}", roadside=True)
            rows += r
            if ids:
                groups[lot] = ids
    # OSM 주차장 면 안의 통로들
    for i, poly in enumerate(lot_polygons(osm_files, area)):
        cx, cy = sum(x for x, _ in poly) / len(poly), sum(y for _, y in poly) / len(poly)
        name = "교내 주차장" if campus_poly and osm_clip.inside(campus_poly, (cx, cy)) else "주차장"
        ids = []
        for e in net.getEdges():
            sh = e.getShape()
            if (not e.allows("passenger") or e.getID().startswith(("hw_", "P1_", "P2_", "P3_"))
                    or not e.getType().endswith("service") or abs(height(e)) > 3):      # 주차 통로만 (다리·큰길 제외)
                continue
            mid = sh[len(sh) // 2][:2]
            if not osm_clip.inside(poly, mid) or e.getLength() < 15:
                continue
            two_way = any(o.getToNode() == e.getFromNode() for o in e.getToNode().getOutgoing())
            r, got = areas_for_edge(net, e, (1,) if two_way else (1, -1), f"L{i}_{e.getID().replace('#', '_')}", name)
            rows += r
            ids += got
        if ids:
            groups[f"L{i}"] = ids
    return rows, groups


def vehicles(groups, ends, per_hour, seed=7, caps=None):
    """주차하러 오는 차: 경계 큰길에서 와서 무작위 구역에 세웠다가 다른 경계로 나간다.
    고가 밑 공영주차장은 잠깐(5~20분), 교내·역 주변 주차장은 길게(20~60분).
    caps(구역 → 칸 수)를 주면 빈 칸이 남은 구역에만 배정한다 (꽉 찬 구역에 온 차는 막다른 통로에서 기다리다 순간이동했다)."""
    rnd = random.Random(seed)
    busy = {}                                   # 구역 → [(차지 시작, 끝)]
    srcs = [v[0] for v in ends.values()]
    snks = [v[1] for v in ends.values()]
    out = []
    for lot, ids in groups.items():
        n = per_hour.get(lot[:2] if lot.startswith("P") else "L", 0)
        n = round(n * (len(ids) / 10 if not lot.startswith("P") else 1))
        dur = (300, 1200) if lot.startswith("P") else (1200, 3600)
        for k in range(n):
            t = rnd.uniform(0, 3600)
            src, snk, d = rnd.choice(srcs), rnd.choice(snks), rnd.randint(*dur)
            # 도착 시각은 모르니 출발부터 (출발 + 10분 + 주차 시간)까지 한 칸을 차지한다고 넉넉히 본다
            free = [a for a in ids if caps is None
                    or sum(1 for b, e in busy.get(a, []) if b < t + 600 + d and t < e) < caps.get(a, 1)]
            area = rnd.choice(free or ids)
            busy.setdefault(area, []).append((t, t + 600 + d))
            out.append((t, f'    <trip id="park_{lot}_{k}" type="parker" depart="{t:.1f}" from="{src}" '
                           f'to="{snk}" departLane="best">'
                           f'<stop parkingArea="{area}" duration="{d}"/></trip>\n'))
    return [r for _, r in sorted(out)]
