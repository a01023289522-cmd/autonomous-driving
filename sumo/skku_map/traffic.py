"""교통: 봉담과천로 흐름, randomTrips 일반 차량, 주차 차량, 버스, 시뮬레이션 설정 파일."""
import math
import os
import re
import subprocess
import sys

from common import SUMO_HOME, P, W


# 범위 경계에서 잘린 큰길 끝 (OSM 이름이 없는 길도 있어 위치로 찾는다)
ENDS = {"서부로 남쪽": (-260, -1240), "덕영대로 서쪽": (-350, 45), "덕영대로 동쪽": (1140, -1115),
        "정자천로 동쪽": (1194, -1010), "일월로 남쪽": (474, -1439), "화산로 남동쪽": (1054, -1181),
        "화산로 서쪽": (-955, 190), "율전로 서쪽": (-981, -595), "하률로 동쪽": (605, 333), "만석로 동쪽": (1034, -567)}


def fringe(net, p):
    """p 근처 범위 경계 끝에서 들어오는(src)/나가는(snk) 엣지."""
    ends = [n for n in net.getNodes() if math.dist(n.getCoord()[:2], p) < 40
            and len({e.getFromNode() for e in n.getIncoming()} | {e.getToNode() for e in n.getOutgoing()}) == 1]
    src = [e for n in ends for e in n.getOutgoing()]
    snk = [e for n in ends for e in n.getIncoming()]
    return (src[0].getID() if src else None), (snk[0].getID() if snk else None)


# 시간대별 교통량 배율 (5분마다, 1시간). 처음엔 많이 넣어 대기 줄을 빨리 만들고, 그 뒤엔 조금 줄여 쌓인 정도를 유지한다 (사용자 제안).
#   일정하게 넣으면 처음 5~10분은 사거리 남행에 평균 3대만 서 있다가 30분 뒤 8~10대로 계속 늘었다
#   무작위 일반 차량·상호작용 흐름에 DEMAND, 고속도로에서 동네로 드나드는 흐름에 HW_DEMAND를 곱한다.
#   버스·주차 차량·의왕TG 북쪽 고속도로 본선 흐름은 그대로
DEMAND = [1.3, 1.25, 1.1, 1.0, 1.0, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95]
# 고속도로 쪽은 처음 5분만: 고속도로가 약 5 km라 4~5분 늦게 사거리에 닿아, DEMAND를 그대로 쓰면 늘린 차가 10~20분에
#   사거리 남행에 한꺼번에 몰렸다 (평균 정지 45대, 순간이동)
HW_DEMAND = [1.15, 1.0, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95, 0.95]
SLICE = 3600 / len(DEMAND)


def timed(vph, prof):
    """[(begin, end, 시간당 대수)] — 배율이 같은 이웃 구간은 하나로."""
    out = []
    for k, m in enumerate(prof):
        if out and prof[k - 1] == m:
            out[-1] = (out[-1][0], (k + 1) * SLICE, out[-1][2])
        else:
            out.append((k * SLICE, (k + 1) * SLICE, vph * m))
    return out


def flow(rows, fid, src, dst, vph, typ, stop="", via="", profile=DEMAND):
    parts = timed(vph, profile) if profile else [(0, 3600, vph)]
    for k, (b, e, v) in enumerate(parts):
        head = (f'    <flow id="{fid if len(parts) == 1 else f"{fid}_{k}"}" type="{typ}" begin="{b:.0f}" end="{e:.0f}" '
                f'period="exp({v / 3600:.4f})" from="{src}" to="{dst}"' + (f' via="{via}"' if via else "")
                + ' departLane="best" departSpeed="max"')
        rows.append(f"{head}>{stop}</flow>\n" if stop else f"{head}/>\n")


# AV 루트 판단 지점에서 상호작용이 생기도록 일부러 넣는 흐름 (2026-11-03). 무작위 일반 차량만으로는 회전교차로·골목 오거리·정문 앞이
#   거의 비어 있었다 (회전교차로 시간당 20~30대). (이름, 지나야 할 엣지들, 시간당 대수, 설명)
#   처음 값(오거리 100~120, 회전교차로 120~150)으로는 회전교차로에서 양보할 일이 거의 없어 1.5~3배로 올렸다.
#   회전교차로 흐름은 들어오는 길·나가는 길을 둘 다 적는다: 하나만 적었더니 extend()가 가장 긴 길을 골라
#   두 흐름 모두 율전로64번길 → 율전로 북동쪽으로 바로 빠져 AV 입구 앞을 지나지 않았다
#   출발·도착은 지나야 할 엣지의 앞뒤로 100 m 넘게 거슬러 올라간/내려간 길 (판단 지점 바로 앞에서 갑자기 생기지 않게)
INTERACTION_FLOWS = [
    ("ia_o6_ns", ["4526039580#2", "4526039580#3"], 180, "오거리(서부로2123번길·화산로233번길): 남행으로 AV 앞을 가로지름"),
    ("ia_o6_sn", ["-4526039580#3", "-4526039580#2"], 150, "오거리(서부로2123번길·화산로233번길): 북행으로 가로지름"),
    ("ia_o7_ns", ["-4694200430", "-4526039570#1"], 150, "오거리(율전로98번길·서부로2105번길): 가로지름"),
    ("ia_o7_sn", ["4526039570#1", "4694200430"], 150, "오거리(율전로98번길·서부로2105번길): 가로지름"),
    ("ia_o8_ns", ["4694200400", "4717154970"], 180, "오거리(율전로98번길·율전로): 남행으로 가로지름"),
    ("ia_x9_join", ["-4709208800#1", "5039133870#1"], 150, "비정형 사거리(율전로·율전로80번길): AV 맞은편으로 합류"),
    ("ia_rb_w", ["-3718967780#0", "-5039133830#3"], 450, "회전교차로: 율전로64번길에서 들어와 율전로 서쪽으로 (AV 입구 앞을 지나는 차)"),
    ("ia_rb_e", ["5039133830#3", "5039133870#0"], 300, "회전교차로: 율전로 서쪽에서 들어와 율전로 북동쪽으로"),
    ("ia_rb_n", ["-5039133870#0"], 250, "회전교차로: 율전로 북동쪽에서 들어와 서쪽으로 (AV와 같은 갈래로 진입)"),
    ("ia_gate_wb", ["-5612296410"], 250, "정문 앞 일월로 서행: AV가 정문으로 좌회전할 때 마주 오는 차"),
    ("ia_gate_in", ["-15379779810#1", "9239987550#3"], 60, "정문으로 들어가는 차 (AV 앞뒤)"),
    ("ia_gate_out", ["15379779810#1"], 60, "정문에서 나오는 차"),
]


def extend(net, eid, back, length=100):
    """엣지 eid에서 거슬러 올라가거나(back) 내려가 length m 넘게 떨어진 엣지 (가장 긴 쪽으로)."""
    e, acc = net.getEdge(eid), 0.0
    while acc < length:
        nxt = ([i for i in e.getFromNode().getIncoming() if i.allows("passenger") and i.getFromNode() != e.getToNode()] if back
               else [o for o in e.getToNode().getOutgoing() if o.allows("passenger") and o.getToNode() != e.getFromNode()])
        if not nxt:
            break
        e = max(nxt, key=lambda x: x.getLength())
        acc += e.getLength()
    return e.getID()


def interaction_flows(net, rows):
    for fid, via, vph, _ in INTERACTION_FLOWS:
        if not all(net.hasEdge(v) for v in via):
            print("  (상호작용 흐름 건너뜀, 엣지 없음):", fid)
            continue
        src, dst = extend(net, via[0], True), extend(net, via[-1], False)
        mid = [v for v in via if v not in (src, dst)]
        flow(rows, fid, src, dst, vph, "car", via=" ".join(mid))


CLASS_W = {"secondary": 3, "secondary_link": 1, "tertiary": 2, "tertiary_link": 1, "unclassified": 1,
           "residential": 1, "living_street": 0.4, "service": 0.2}
# 경계 큰길 차로 하나의 출발·도착 확률. 400(경계가 약 80%)일 때 경계끼리 오가는 차가 거의 다 성대역 사거리를 지나
#   그곳에만 정체가 몰렸다 → 150(약 60%)으로 낮춰 늘린 차가 동네 길(오거리·회전교차로)로 퍼지게 했다
FRINGE_W = 150


def write_trip_weights(net, prefix):
    """randomTrips 출발(src)·도착(dst) 확률. 경계 큰길: 차로 하나당 FRINGE_W, 안쪽: 길이 100 m당 길 종류 값."""
    src, dst = {}, {}
    for e in net.getEdges():
        eid, kind = e.getID(), e.getType().replace("highway.", "")
        if not e.allows("passenger") or eid.startswith(("hw_", "via_", "P1_", "P2_", "P3_")) or kind not in CLASS_W:   # 고가(via_) 위에서 생기는 차 없음
            continue
        inner = e.getLength() / 100 * CLASS_W[kind]
        big = e.getSpeed() > 10
        src[eid] = FRINGE_W * e.getLaneNumber() if big and not e.getFromNode().getIncoming() else inner
        dst[eid] = FRINGE_W * e.getLaneNumber() if big and not e.getToNode().getOutgoing() else inner
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
    flow(rows, "hw_s", "hw_hS0_hS1", sw_snk, 100, "hwcar", profile=HW_DEMAND)    # 150 → 100: 교통을 늘린 뒤 성대역 사거리 남행이 1시간 끝 무렵 넘침
    # 의왕TG 북쪽 본선만 오가는 흐름(청계IC·학의JC)은 시간대 배율 없이 일정하게 (유령 체증 실험용)
    flow(rows, "hw_s_cgout", "hw_hS0_hS1", "hw_cg_out", 700, "hwcar", profile=None)
    flow(rows, "hw_s_jc", "hw_jc_in", "hw_cg_out", 150, "hwcar", profile=None)
    flow(rows, "hw_s_cg", "hw_cg_in", sw_snk, 60, "hwcar", profile=HW_DEMAND)
    flow(rows, "hw_s_rest", "hw_hS0_hS1", sw_snk, 60, "hwcar", '<stop parkingArea="RS" duration="300"/>', profile=HW_DEMAND)
    flow(rows, "hw_n", sw_src, "hw_hN1_hN0", 150, "car", profile=HW_DEMAND)
    flow(rows, "hw_n_cg", "hw_cg_in2", "hw_hN1_hN0", 600, "hwcar", profile=None)
    flow(rows, "hw_n_jc", "hw_cg_in2", "hw_jc_out", 150, "hwcar", profile=None)
    flow(rows, "hw_n_rest", sw_src, "hw_hN1_hN0", 40, "car", '<stop parkingArea="RN" duration="300"/>', profile=HW_DEMAND)
    for i, (src, snk) in enumerate(ends.values()):
        # 사당 → 의왕TG → 서부로 → 우리 지역: 경계마다 15대/h였으나 교통을 늘린 뒤 성대역 사거리 남행이 넘쳐 8대/h로 줄였다
        flow(rows, f"hw_in_{i}", "hw_hS0_hS1", snk, 8, "hwcar", profile=HW_DEMAND)
        flow(rows, f"hw_out_{i}", src, "hw_hN1_hN0", 12, "car", profile=HW_DEMAND)        # 우리 지역 → 서부로 → 의왕TG → 사당
    interaction_flows(net, rows)
    # 주차하러 오는 차 (parking.py): 고가 밑 공영주차장 3곳 각 20대/h, 교내·역 주변 주차장은 구역 10개당 6대/h,
    #   AV가 주차하는 교내 큰 주차장(L1, Global Plaza 동쪽)은 40대/h (주차·출차하는 차와 마주치게)
    import parking
    with open(P("parking.rou.xml"), "w", encoding="utf-8") as f:
        f.write("<routes>\n" + "".join(parking.vehicles(groups, ends, {"P1": 20, "P2": 20, "P3": 20, "L": 6, "L1": 40}, caps=parking_caps()))
                + "</routes>\n")
    # 버스: 카카오맵 실제 노선 17개(성대역 주변 정류장을 지나는 노선)의 경로·정류장·배차 간격 (bus_lines.py)
    import bus_lines
    n_stop, n_run = bus_lines.build(P("skku.net.xml"), P("bus.rou.xml"), P("bus.stops.xml"), report=lambda m: None)
    print(f"버스: 정류장 {n_stop}곳, 노선 운행 {n_run}개")
    # 주차하러 오는 차(parker)만 고가 밑 공영주차장 통로(allow="taxi")를 쓰게 vClass를 taxi로 둔다 (모양은 승용차).
    #   통로를 모두에게 열어 두었더니 버스 노선 5개가 주차장 1 통로를 지름길로 지나갔다
    #   (vClass: userdoc/Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html)
    # 일반 승용차 lcStrategic 3 (기본 1, 클수록 목적 차로로 일찍 옮김, 같은 문서의 lane-changing 표): 교통을 늘리자
    #   성대역 사거리 남행에서 지상행 차가 사거리 바로 앞 고가행 차로에서 끼어들려고 멈춰 두 차로가 다 막혔다
    #   (지상행 차로 15분 84대, 고가행 42대, 고가는 비어 있음 → 서부로→사거리 최대 574초, 순간이동)
    #   lcAssertive 1.5 (기본 1, 목표 차로에서 받아들이는 앞뒤 간격 = 필요 간격 / 이 값): 대기 줄이 찼을 때 사거리 바로 앞
    #   고가행 차로에서 지상·좌회전 차로로 못 끼어들어 순간이동(wrong lane)하던 것
    with open(P("vtypes.add.xml"), "w", encoding="utf-8") as f:
        f.write('<additional>\n'
                '    <vType id="car" sigma="0.5" impatience="0.5" lcStrategic="3" lcAssertive="1.5" color="255,220,0" guiShape="passenger"/>\n'
                '    <vType id="hwcar" carFollowModel="IDM" accel="1.0" decel="2.0" tau="1.2" impatience="0.5" '
                'lcStrategic="3" lcAssertive="1.5" '
                'color="100,200,255" guiShape="passenger/sedan"/>\n'
                '    <vType id="parker" vClass="taxi" sigma="0.5" impatience="1.0" color="255,120,0" guiShape="passenger/hatchback"/>\n'
                '    <vType id="bus" vClass="bus" color="0,160,80" guiShape="bus"/>\n</additional>\n')
    # 출발 시각 순서로: SUMO는 경로 파일을 시간 순서대로 조금씩 읽어서, 시간대별로 나눈 흐름(begin=300 …) 뒤에 나온
    #   begin=0 흐름들은 들어가지 못했다 (userdoc/Definition_of_Vehicles,_Vehicle_Types,_and_Routes.html: "the route file always has to be sorted by departure / begin time")
    rows.sort(key=lambda r: float(re.search(r'begin="([\d.]+)"', r).group(1)))
    with open(P("skku.rou.xml"), "w", encoding="utf-8") as f:
        f.write("<routes>\n")
        f.writelines(rows)
        f.write("</routes>\n")
    # 일반 차량: SUMO 표준 도구 randomTrips (userdoc/Tools/Trip.html) + 출발·도착 확률 파일(--weights-prefix).
    #   범위 경계로 드나드는 큰길(시속 36 km 넘는 길)이 대부분(약 75%), 안쪽은 길 종류·길이에 비례해 조금.
    #   막다른 골목·교내·단지 도로에서는 거의 안 나오고, 고속화도로·주차장 통로는 0
    #   -p 3.5(시간당 약 1,030대)는 AV 루트가 거의 막히지 않아 -p 2.5(약 1,440대, 여기에 DEMAND 시간대 배율)로 늘렸다 (2026-11-03). -p 2.0(약 1,800대)은 늘어난 차가 거의 다 성대역 사거리로 몰려 서부로→사거리가 최대 7~10분 걸렸다
    write_trip_weights(net, W("trip_w"))
    subprocess.run([sys.executable, os.path.join(SUMO_HOME, "tools", "randomTrips.py"), "-n", P("skku.net.xml"),
                    "-o", W("random.trips.xml"), "-r", W("random.validated.rou.xml"), "-b", "0", "-e", "3600", "-p", ",".join(f"{2.5 / m:.3f}" for m in DEMAND), "--weights-prefix", W("trip_w"),
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
    # ignore-junction-blocker 60: 교차로를 막고 60초 넘게 선 차는 무시하고 지나간다 ("결국 막은 차를 비켜 가는 실제 행동",
    #   userdoc/Simulation/Intersections.html). G2 동쪽 골목 교차로(우측 우선)에서 네 방향이 서로 양보하다 멈춰 G2까지 막혔다
    with open(P("skku.sumocfg"), "w", encoding="utf-8") as f:
        f.write("""<configuration>
    <input>
        <net-file value="skku.net.xml"/>
        <route-files value="skku.rou.xml,bus.rou.xml,parking.rou.xml,random.rou.xml"/>
        <additional-files value="vtypes.add.xml,bus.stops.xml,skku.add.xml,bg.add.xml"/>
        <gui-settings-file value="skku.gui.xml"/>
    </input>
    <time><begin value="0"/><end value="3600"/><step-length value="0.2"/></time>
    <processing><time-to-teleport value="300"/><ignore-junction-blocker value="60"/><collision.action value="warn"/><ignore-route-errors value="true"/></processing>
    <random_number><seed value="42"/></random_number>
</configuration>
""")
