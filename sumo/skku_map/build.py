"""성균관대역 일대 SUMO 시나리오 만들기.

  1) osm_clip   : OSM에서 구현 범위 안 차도만 잘라 옴 (차로 수 규칙 포함)
  2) netconvert : OSM 불러오기 (SUMO 권장 옵션, 원점 = 성대역 사거리, 단위 m)
  3) 수정 파일   : 사거리 신호, 유턴, 회전 금지, 고가 밑 공영주차장, 봉담과천로(고속화도로)
  4) 교통       : 고속화도로 흐름 + randomTrips(일반 차량) + 주차 차량 + 버스

    python build.py            # 만들고 1시간 점검
    python build.py --no-check
"""
import math
import os
import subprocess
import sys

from common import (SUMO_HOME, P, W, curb_shape, curve, fmt, heading, junction_near, netconvert, offset_fn, poly_point,
                    poly_project, smoothstep, square_shape, unit)
import sumolib  # noqa: E402
from sumolib import checkBinary  # noqa: E402
import osm_clip  # noqa: E402
from config import AREA, CLOSED_GATES, GAPS, KAKAO_ONEWAY, NB, OSM, PROJ, SAGEORI, UTURNS
from viaduct import VIA_NB, VIA_SB, lots_and_side_roads, viaduct_edges
from highway import highway
from drawing import write_additional
from traffic import write_cfg, write_routes


def north_stubs(net, x0=-200, x1=250, y0=235, max_len=120):
    """서부로 북쪽 끝(고속도로가 이어지는 곳) 옆에서 구현 범위 경계에 닿아 잘린 막다른 길과, 그걸 빼서 새로 막다른 길이 된
    짧은 길을 차례로 고른다 (서부로는 빼지 않는다)."""
    dead = set()
    alive = lambda n: [e for e in n.getIncoming() + n.getOutgoing() if e.getID() not in dead]
    changed = True
    while changed:
        changed = False
        for n in net.getNodes():
            x, y = n.getCoord()[:2]
            es = alive(n)
            if not (x0 < x < x1 and y > y0) or not es or any(e.getName() == "서부로" for e in es):
                continue
            other = {e.getFromNode() for e in es} | {e.getToNode() for e in es}
            if len(other - {n}) == 1 and all(e.getLength() < max_len for e in es):
                dead |= {e.getID() for e in es}
                changed = True
    return dead


# 분리 도로가 OSM에서 서로 겹치거나 엇갈려 그려진 곳 → 기준 차로 묶음(ref)에서 정해진 거리만큼 나란히 다시 그린다
#   (엣지, 기준 엣지, 기준 진행 방향 오른쪽으로 떨어진 거리 m (음수 = 왼쪽), 시작에서 몇 m에 걸쳐 그 거리까지 벌어지나)
#   거리 = 두 차로 묶음 폭의 반씩 + 분리대·여유. 차로 수는 그대로 (지도로 확인한 값)
#   덕영대로 사거리 동쪽: 동행 본선 3 / 동행 지상 1(남쪽) / 서행 본선 2 · 서행 연결로 2(북쪽)이 한 줄로 겹쳐 엇갈렸다
#   화산로: 양방향 1+1 남쪽에 붙은 동행 1차로가 같은 선 위에 겹쳐 있었다
PARALLEL = [("15371153870", "383158340", 3 * 1.6 + 1.6 + 0.5, 0),
            ("5552317800", "383158340", -(3 * 1.6 + 2 * 1.6 + 1.0), 0),
            ("5552317770", "383158340", -(3 * 1.6 + 3 * 1.6 + 1.0), 0),
            ("7754668950#0", "383158340", -(3 * 1.6 + 2 * 1.6 + 1.0 + 2 * 3.2 + 0.5), 40),
            ("1025323300#2", "-420073680#3", 3.2 + 1.6 + 0.4, 0),
            ("1025323300#3", "-420073680#3", 3.2 + 1.6 + 0.4, 0),
            ("1025323300#5", "-420073680#1", 3.2 + 1.6 + 0.4, 0)]


def parallel_fixes(net):
    rows = []
    for eid, rid, d, spread in PARALLEL:
        if not (net.hasEdge(eid) and net.hasEdge(rid)):
            print(f"  (분리 도로 맞춤 건너뜀: {eid} / {rid} 없음)")
            continue
        ref = [p[:2] for p in net.getEdge(rid).getShape()]
        sh = [p[:2] for p in net.getEdge(eid).getShape()]
        s0, s1 = poly_project(ref, sh[0]), poly_project(ref, sh[-1])
        if spread:                                        # 갈라지는 곳에서는 바로 옆 차로 묶음 자리에서 시작해 서서히 벌어진다
            base = d + (2 * 3.2 + 0.5) * (1 if d < 0 else -1)
            f = lambda s, s0=s0, base=base, d=d: base + (d - base) * smoothstep(abs(s - s0) / spread)
        else:
            f = lambda s, d=d: d
        rows.append(f'<edge id="{eid}" shape="{fmt(offset_fn(ref, f, s0, s1))}"/>')
    return rows


def import_osm():
    osm_clip.clip(OSM, AREA, W("clip.osm.xml"), KAKAO_ONEWAY)
    # 사거리는 OSM에서 일방통행 링크 네 개가 만든 '상자' 모양이라 하나의 교차로로 합친다
    import xml.etree.ElementTree as ET
    root = ET.parse(W("clip.osm.xml")).getroot()
    use = {}
    for w in root.findall("way"):
        for nd in w.findall("nd"):
            use[nd.get("ref")] = use.get(nd.get("ref"), 0) + 1
    box = [n.get("id") for n in root.findall("node") if use.get(n.get("id"), 0) >= 2
           and abs(osm_clip.xy(float(n.get("lat")), float(n.get("lon")))[0]) < 22
           and -30 < osm_clip.xy(float(n.get("lat")), float(n.get("lon")))[1] < 20]
    # 고가 밑 갈림목 G2·G3은 양쪽 지상도로 교차점을 넓은 교차로 하나로 묶는다 (실제로 고가 밑을 가로지르는 넓은 교차로, 신호 하나).
    #   G2를 두 교차점으로 두었더니 고가 밑 한가운데에 신호가 하나 더 있는 것처럼 보였다(사용자 지적). 면 모양은 turn_rules에서
    #   서부로2106번길 (-45, -327): 남쪽 길이 붙는 두 점(2 m 엣지)만 하나로 (넷을 다 묶었더니 덩어리 교차로가 됐다: 사용자 지적)
    joins = [box, ["726912991", "837163934", "1184134292"], ["4637428747", "495943443"], ["4658598447", "4658598448"]]
    with open(W("join.nod.xml"), "w", encoding="utf-8") as f:
        f.write("<nodes>\n" + "".join(f'    <join nodes="{" ".join(j)}"/>\n' for j in joins) + "</nodes>\n")
    netconvert(["--osm-files", W("clip.osm.xml"), "-n", W("join.nod.xml"),
                "--type-files", os.path.join(SUMO_HOME, "data", "typemap", "osmNetconvert.typ.xml") + "," + P("skku.typ.xml"),
                "-o", W("pass1.net.xml"), "--proj", PROJ, "--offset.disable-normalization", "true",
                # SUMO 권장 옵션 (userdoc/Networks/Import/OpenStreetMap.html)
                "--geometry.remove", "--junctions.join", "--tls.guess-signals", "--tls.discard-simple", "--tls.join",
                # 교차로 끝의 급한 꺾임을 펴서 찌그러짐·화살표 오류 방지
                "--geometry.min-radius.fix", "--junctions.corner-detail", "5",
                "--remove-edges.isolated", "--keep-edges.components", "1",
                "--no-turnarounds.except-deadend", "true",
                "--default.lanewidth", "3.2", "--output.street-names", "true",
                "--ptstop-output", W("pt.stops.xml"), "--ptline-output", W("pt.lines.xml")], "pass1.log")
    return sumolib.net.readNet(W("pass1.net.xml"))


class Patch:
    """netconvert 수정 파일 세 개(patch.nod/edg/con.xml)에 들어갈 줄과, 단계끼리 주고받는 표시."""

    def __init__(self):
        self.nod, self.edg, self.con = [], [], []
        self.touched = set()      # 새 길이 붙는 기존 교차로 → 들어오는 연결을 다시 계산 (reset)
        self.deleted = set()      # 지우고 조각으로 다시 만든 엣지
        self.fixed = set()        # 모양을 직접 정한 엣지 (높이 판정에서 뺀다)

    def write(self):
        for name, rows, tag in (("patch.nod.xml", self.nod, "nodes"), ("patch.edg.xml", self.edg, "edges"),
                                ("patch.con.xml", self.con, "connections")):
            with open(W(name), "w", encoding="utf-8") as f:
                f.write(f"<{tag}>\n" + "".join(f"    {r}\n" for r in rows) + f"</{tag}>\n")


def patch_signals(net, pt):
    # 신호 교차로 (사거리 + 고가 밑 갈림목 G1·G2·G3 + 서부로×일월로 + 서부로×하률로: 기존 모델과 동일)
    sg = junction_near(net, SAGEORI)
    for p in (*GAPS.values(), (-250, -1080), (24, 273)):
        pt.nod.append(f'<node id="{junction_near(net, p).getID()}" type="traffic_light"/>')
    pt.nod.append(f'<node id="{sg.getID()}" shape="{fmt(square_shape(sg))}"/>')
    return sg.getID()


def patch_highway(net, pt):
    # 봉담과천로 → 서부로 북쪽 끝(구현 범위 경계 노드)에 그대로 이어진다
    north = [n for n in net.getNodes() if n.getCoord()[1] > 250 and abs(n.getCoord()[0] - 25) < 40]
    src = [n for n in north if not n.getIncoming() and any(e.getName() == "서부로" for e in n.getOutgoing())][0]
    snk = [n for n in north if not n.getOutgoing() and any(e.getName() == "서부로" for e in n.getIncoming())][0]
    sb_out, nb_in = src.getOutgoing()[0], snk.getIncoming()[0]
    d_sb = unit(*[a - b for a, b in zip(sb_out.getShape()[0][:2], sb_out.getShape()[1][:2])])
    d_nb = unit(*[a - b for a, b in zip(nb_in.getShape()[-1][:2], nb_in.getShape()[-2][:2])])
    hn, he, hc, hshape, hzip = highway((src.getID(), src.getCoord()[:2]), (snk.getID(), snk.getCoord()[:2]),
                                       unit(d_sb[0] + d_nb[0], d_sb[1] + d_nb[1]))
    hc = [(nb_in.getID() if f == "_nb" else f, sb_out.getID() if t == "_sb" else t, i, j) for f, t, i, j in hc]
    pt.con += [f'<connection from="{f}" to="{t}" fromLane="{i}" toLane="{j}"/>' for f, t, i, j in hc]
    # 차로 수가 바뀌는 점(요금소·가속 차로 끝)은 깔때기 모양 교차로 면
    pt.nod += [f'<node id="{n}" x="{x}" y="{y}"' + (f' shape="{fmt(hshape[n])}"' if n in hshape else "")
            + (' type="zipper"' if n in hzip else "") + '/>' for n, (x, y) in hn.items()]
    for eid, a, b, lanes, kmh, shape in he:
        sh = f' shape="{fmt(shape)}"' if shape else ""
        if eid.startswith(("hw_h", "hw_bd")):               # 본선: 가운데선 양쪽으로 차로를 펼친다 (깔때기 모양과 맞춤)
            sh += ' spreadType="center"'
        pt.edg.append(f'<edge id="{eid}" from="{a}" to="{b}" numLanes="{lanes}" speed="{kmh / 3.6:.2f}" '
                   f'priority="13"{sh}/>')


def patch_cleanup(net, pt):
    # 고속도로가 이어지는 서부로 북쪽 끝 옆 골목들이 구현 범위 경계에서 잘려 끊긴 채 보이던 것 → 경계에 닿는 짧은 막다른 길은 뺀다
    for eid in north_stubs(net):
        pt.edg.append(f'<delete id="{eid}"/>')
    # 서부로2106번길: 비스듬히 가로질러 X자로 겹치던 이름 없는 22 m 연결로, 남쪽에 나란히 붙어 고리 모양이던 서비스 길은
    #   지도·로드뷰에 없는 길이라 뺀다 (사용자 지적). 2106번길은 한 길로 쭉 이어진다
    pt.edg += [f'<delete id="{eid}"/>' for eid in ("4716974720", "-4716974720", "4716974730", "-4716974730") if net.hasEdge(eid)]
    # 구현 범위 경계에서 잘려 15 m도 안 남은 토막(경계 노드 9000000000…에 닿음): 끝에 돌아 나오는 부채꼴만 남아 깨져 보였다
    #   골목(주거·서비스·소로)만: 큰길의 경계 끝은 차가 드나드는 출발·도착점이라 남긴다
    stubs = {e.getID() for e in net.getEdges() if e.getLength() < 15
             and e.getType() in ("highway.residential", "highway.service", "highway.unclassified", "highway.living_street")
             and any(n.getID().startswith("9000000000") for n in (e.getFromNode(), e.getToNode()))}
    pt.edg += [f'<delete id="{eid}"/>' for eid in sorted(stubs - set(north_stubs(net)))]


def patch_heights(net, pt):
    # 고가·다리(+6 m)와 지하차도(-6 m) 높이: OSM layer 태그가 있는 길만. 화면에서 높이별 색으로 겹친 도로를 구분 (skku.gui.xml)
    #   (netconvert --osm.layer-elevation은 이웃 길까지 경사로 높이를 퍼뜨리고 사거리 같은 합친 교차로 전체를 띄워 쓰지 않음)
    #   엣지가 여러 OSM 길을 합쳐 만들어지기도 해서, 엣지 모양의 대부분이 OSM 고가·지하차도 선과 3 m 안에서 겹치는지로 판단
    import xml.etree.ElementTree as ET
    root = ET.parse(W("clip.osm.xml")).getroot()
    npos = {n.get("id"): osm_clip.xy(float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
    layered, under = [], []
    for w in root.findall("way"):
        z = next((int(t.get("v")) for t in w.findall("tag") if t.get("k") == "layer"), 0)
        if z:
            layered.append((z, [npos[r.get("ref")] for r in w.findall("nd")]))
    for e in net.getEdges():
        if e.getID() in pt.fixed or e.getLength() < 20:        # 직접 그린 고가, 고가 밑 짧은 연결로(유턴 등)는 제외
            continue
        sh = [p[:2] for p in e.getShape()]
        pts = [poly_point(sh, d) for d in range(0, int(sum(math.dist(a, b) for a, b in zip(sh, sh[1:]))) + 1, 5)] or sh
        for z, line in layered:
            near = sum(1 for p in pts if sumolib.geomhelper.distancePointToPolygon(p, line) < 3)
            if near >= 0.6 * len(pts):
                pt.edg.append(f'<edge id="{e.getID()}" shape="{fmt([(x, y, 6 * z) for x, y in sh])}"/>')
                if z < 0:
                    under.append(sh)
                break
    # 지하차도 입구 위를 건너는 짧은 연결로(유턴)는 OSM 선이 지그재그로 꺾여 깨져 보였다
    #   → 들어오는 길 방향으로 6 m 나갔다가 돌아 나오는 U자 곡선으로
    def crosses(p, q):
        def ccw(a, b, c):
            return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return any(ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0
                   for a, b in zip(p, p[1:]) for c, d in zip(q, q[1:]))
    for e in net.getEdges():
        sh = [p[:2] for p in e.getShape()]
        if e.getID() not in pt.fixed and e.getLength() < 40 and len(sh) > 2 and any(crosses(sh, u) for u in under):
            ins = [i for i in e.getFromNode().getIncoming() if i.getFromNode() != e.getToNode()]
            arc = [sh[0], sh[-1]]
            if ins:
                d = heading(max(ins, key=lambda i: i.getLength()), True)
                arc = curve([sh[0], (sh[0][0] + d[0] * 6, sh[0][1] + d[1] * 6),
                             (sh[-1][0] + d[0] * 6, sh[-1][1] + d[1] * 6), sh[-1]], n=6)
            pt.edg.append(f'<edge id="{e.getID()}" shape="{fmt(arc)}"/>')


def patch_gates(net, pt):
    # 막힌 캠퍼스 출입구: 길은 남기되(사람만 통행) 차는 못 지나가게
    for wid in CLOSED_GATES:
        for e in net.getEdges():
            if e.getID().lstrip("-").split("#")[0] == wid:
                pt.edg.append(f'<edge id="{e.getID()}" allow="pedestrian"/>')



def write_patches(net):
    pt = Patch()
    sg_id = patch_signals(net, pt)
    lots_and_side_roads(net, pt)              # viaduct.py: 공영주차장 띠 + 고가 옆 지상 도로 띄우기
    patch_highway(net, pt)
    patch_cleanup(net, pt)
    for nid in pt.touched:
        for e in net.getNode(nid).getIncoming():
            if e.getID() not in pt.deleted and e.getID() not in VIA_SB + VIA_NB:
                pt.con.append(f'<connection from="{e.getID()}" reset="true"/>')
    pt.con += [f'<connection from="{e}" reset="true"/>' for e in ("P1_out", "P2_out", "P3_out", "hw_hS9_bd")]
    viaduct_edges(net, pt)                    # viaduct.py: 서부로 고가 엣지
    patch_heights(net, pt)
    pt.edg += parallel_fixes(net)
    patch_gates(net, pt)
    pt.write()
    return sg_id


def turn_rules(net):
    """지도로 확인한 회전 규칙 (연결을 다시 계산한 뒤 적용): 유턴 허용 지점, 사거리 북쪽 방향 좌회전 금지."""
    con, allowed = [], set()
    for p, d in UTURNS:
        j = junction_near(net, p)
        ins = [e for e in j.getIncoming() if sum(a * b for a, b in zip(heading(e, True), d)) > 0.8]
        outs = [e for e in j.getOutgoing() if sum(a * b for a, b in zip(heading(e, False), d)) < -0.8
                and not e.getID().startswith(("P1_", "P2_", "P3_"))]
        for i in ins[:1]:
            for o in outs[:1]:
                allowed.add((i.getID(), o.getID()))
                if not i.getConnections(o):
                    con.append(f'<connection from="{i.getID()}" to="{o.getID()}" '
                               f'fromLane="{i.getLaneNumber() - 1}" toLane="{o.getLaneNumber() - 1}"/>')
    # 그 밖의 유턴은 모두 삭제 (막다른 골목 끝에서 돌아 나오는 것은 둔다).
    # 들어온 길 바로 옆을 나란히 되돌아가는 연결(분리 도로·램프 사이)도 사실상 유턴이라 함께 지운다 (예: 성대역지하차도 양 끝).
    # 둘 중 하나가 일방 램프일 때만 본다 (양방향 골목이 U자로 꺾이는 곳은 실제 길이다)
    def one_way(e):
        return not any(x.getToNode() == e.getFromNode() for x in e.getToNode().getOutgoing())

    def hairpin(i, o):
        if not (one_way(i) or one_way(o)) or sum(a * b for a, b in zip(heading(i, True), heading(o, False))) > -0.6:
            return False
        node, back, sh = i.getToNode().getCoord()[:2], [p[:2] for p in i.getShape()], [p[:2] for p in o.getShape()]
        pts = [(a[0] + (b[0] - a[0]) * k / 5, a[1] + (b[1] - a[1]) * k / 5) for a, b in zip(sh, sh[1:]) for k in range(6)]
        far = [p for p in pts if math.dist(p, node) > 20]
        return bool(far) and all(sumolib.geomhelper.distancePointToPolygon(p, back) < 25 for p in far)

    for n in net.getNodes():
        if len({e.getFromNode() for e in n.getIncoming()} | {e.getToNode() for e in n.getOutgoing()}) <= 1:
            continue
        for i in n.getIncoming():
            for o in i.getOutgoing():
                if ((i.getID(), o.getID()) not in allowed and not o.getID().endswith("_in")
                        and (hairpin(i, o) or any(c.getDirection() == "t" for c in i.getConnections(o)))):
                    con.append(f'<delete from="{i.getID()}" to="{o.getID()}"/>')
    # 공영주차장2 출구: 좌회전(북쪽 방향) 금지 (로드뷰: "좌회전 금지 · 주차장 출구전용" 표지). 지금은 남행 도로에 합류만 해서
    #   갈 곳이 하나뿐이지만, 출구가 교차로로 바뀌어도 지켜지게 둔다
    outs = net.getEdge("P2_out").getOutgoing()
    for o in outs:
        if len(outs) > 1 and sum(a * b for a, b in zip(heading(o, False), NB)) > 0.5:
            con.append(f'<delete from="P2_out" to="{o.getID()}"/>')
    # 사거리: 남쪽에서 올라오는 차는 좌회전·유턴 불가 (로드뷰 직진 화살표, 네이버·카카오 길찾기: 하률로 교차로에서 유턴)
    sg = junction_near(net, SAGEORI)
    for i in sg.getIncoming():
        if heading(i, True)[1] > 0.7:
            for o in i.getOutgoing():
                if heading(o, False)[0] < -0.7 or heading(o, False)[1] < -0.7:
                    con.append(f'<delete from="{i.getID()}" to="{o.getID()}"/>')
    with open(W("rules.con.xml"), "w", encoding="utf-8") as f:
        f.write("<connections>\n" + "".join(f"    {r}\n" for r in con) + "</connections>\n")
    # 큰 교차로 면(G2: 고가 밑을 가로지르는 넓은 교차로, 사거리): 실제 교차로처럼 연석선을 늘여 만나는 모서리를 깎은 모양
    #   (netconvert 면은 띄운 도로 쪽으로 쐐기처럼 일그러졌고, 볼록 다각형·덩어리 모양은 큰 도형을 박아 넣은 것 같았다: 사용자 지적)
    shaped = [junction_near(net, GAPS["G2"]), junction_near(net, SAGEORI)]
    with open(W("rules.nod.xml"), "w", encoding="utf-8") as f:
        f.write("<nodes>\n" + "".join(f'    <node id="{n.getID()}" shape="{fmt(curb_shape(n))}"/>\n' for n in shaped)
                + "</nodes>\n")
    netconvert(["-s", W("pass2.net.xml"), "-n", W("rules.nod.xml"), "-x", W("rules.con.xml"), "-o", W("pass2.net.xml"),
                "--offset.disable-normalization", "true", "--tls.rebuild", "true"], "pass2b.log")   # 주차장 출구까지 신호에 넣어 다시 계산
    return sumolib.net.readNet(W("pass2.net.xml"), withPrograms=True), len(con)


def apply_patches():
    netconvert(["-s", W("pass1.net.xml"), "-n", W("patch.nod.xml"), "-e", W("patch.edg.xml"), "-x", W("patch.con.xml"),
                "-o", W("pass2.net.xml"), "--offset.disable-normalization", "true", "--junctions.corner-detail", "5",
                "--no-turnarounds.except-deadend", "true"], "pass2.log")
    return sumolib.net.readNet(W("pass2.net.xml"), withPrograms=True)


def sageori_tls(net, sg_id):
    """사거리 신호 (사용자 지정): 차량 네 방향 동시 녹색 70초 → 황색 3초 → 보행자 동시신호 45초(차량 전부 정지).
    동시 녹색일 때 부딪히는 흐름은 서부로(남북) 직진·우회전이 우선(G), 나머지는 양보(g).
    이 계획을 netconvert에 다시 넣어(-i) 교차로 우선권을 신호에 맞게 계산한다."""
    tls = net.getTLSSecure(sg_id)
    links, seen, merge = {}, {}, set()
    for in_lane, out_lane, idx in sorted(tls.getConnections(), key=lambda c: c[0].getIndex()):
        c = [c for c in in_lane.getEdge().getConnections(out_lane.getEdge())
             if c.getFromLane() == in_lane and c.getToLane() == out_lane][0]
        hx, hy = heading(in_lane.getEdge(), True)
        ns = abs(hy) > abs(hx)
        major = ns and c.getDirection() not in ("l", "L")
        if major and out_lane.getID() in seen:
            merge.add(idx)                                # 같은 차로로 합쳐지는 우선 흐름 둘 → 바깥쪽은 양보
        seen[out_lane.getID()] = idx
        links[idx] = major
    n = max(links) + 1
    green = "".join("G" if links[i] and i not in merge else "g" for i in range(n))
    with open(W("sageori.tll.xml"), "w", encoding="utf-8") as f:
        f.write(f'<tlLogics>\n    <tlLogic id="{sg_id}" type="static" programID="0" offset="0">\n'
                f'        <phase duration="70" state="{green}"/>\n        <phase duration="3" state="{"y" * n}"/>\n'
                f'        <phase duration="45" state="{"r" * n}"/>\n    </tlLogic>\n')
        f.write('</tlLogics>\n')
    netconvert(["-s", W("pass2.net.xml"), "-i", W("sageori.tll.xml"), "-o", P("skku.net.xml"),
                "--offset.disable-normalization", "true"], "pass3.log")
    return sumolib.net.readNet(P("skku.net.xml"), withPrograms=True)


def check(seeds=(42, 1, 2)):
    for seed in seeds:
        r = subprocess.run([checkBinary("sumo"), "-c", P("skku.sumocfg"), "--seed", str(seed), "--no-step-log",
                            "--duration-log.statistics", "--no-warnings"], capture_output=True, text=True)
        keep = [ln.strip() for ln in (r.stdout + r.stderr).splitlines()
                if ln.strip().startswith(("Inserted", "Teleports", "Collisions", "TimeLoss", "Error"))]
        print(f"seed {seed}: " + " | ".join(keep))


def main():
    net1 = import_osm()
    sg_id = write_patches(net1)
    apply_patches()
    net2, _ = turn_rules(sumolib.net.readNet(W("pass2.net.xml")))
    net = sageori_tls(net2, sg_id)
    print(f"도로망: 노드 {len(net.getNodes())}, 엣지 {len(net.getEdges())}, 신호 {len(net.getTrafficLights())}")
    groups = write_additional(net)
    import background
    n_poly, n_lbl = background.write(OSM, AREA, P("bg.add.xml"))
    print(f"배경: 면 {n_poly}개, 지명 {n_lbl}개")
    ends = write_routes(net, groups)
    print("범위 경계 큰길:", ", ".join(ends))
    write_cfg()
    if "--no-check" not in sys.argv:
        check()


if __name__ == "__main__":
    main()
