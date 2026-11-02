"""성균관대역 일대 도로 (연결 구조는 직접 정의, 모양은 OSM 실제 도로선을 따라 꺾음).

노드(교차로)·엣지(도로)·차로·신호·주차장은 이 파일에서 직접 정의하고, 각 도로의 모양은
osm_shapes.py가 OSM 실제 도로선을 3m 오차로 단순화해 여러 번 꺾이는 선으로 만든다.
좌표 원점 = 성대역 사거리, 단위 m, x = 동쪽, y = 북쪽.

  ① 성대역 사거리 (SG)   : 4갈래, 차량 신호 전부 동시 녹색(서로 양보) ↔ 보행자 동시신호(차량 전부 정지)
  ② 서부로 고가도로      : 사거리 바로 남쪽(D0)에서 올라가 하부 교차로를 신호 없이 넘고 LD에서 착지 (양방향, +7m)
  ③ 고가 하부 (핵심)     : 지상 서부로 양방향 + 중앙(고가 밑) 공영주차장 3곳
                           갈림목 G1~G4: 양쪽 골목 진입 + 유턴 + 주차장 출입구가 몰려 있음, 가로변 버스 정류장
  ④ 학교                 : 차량 출입구는 정문(남쪽 일월로) 하나 (후문·북문은 차량 통행 막힘).
                           정문으로 들어와 오른쪽으로 일방통행, 시계 반대 방향으로 한 바퀴 돌아 정문으로 나간다.
                           (남쪽 도로 → 공자로 북쪽 → 북쪽 도로 서쪽 → 가운데 남북 도로 남쪽), 공자로 오른쪽 교내 주차장
  ⑤ 학교 둘레            : 서부로(서) · 일월로(남) · 정자천로13번길(동, 버스 정류장 밀집) · 화산로(북동),
                           남동쪽 모서리는 골목.
                           1호선 철길이 화산로(안쪽)와 덕영대로(바깥, 육교 너머)를 가른다 → 두 쪽은 바로 안 이어지고
                           사거리 쪽으로 돌거나 남동쪽 정천지하차도(정자천로 → 철길·덕영대로 밑)로만 건넌다
  ⑥ 봉담과천로 (고속화)  : 사당 방면 5km(실제 약 13km에서 축소)를 사거리 북쪽 서부로에 바로 잇는다
  ⑦ 골목·생활도로        : 사용자가 정한 범위(AREA) 안의 OSM 실제 골목을 minor_roads.py가 핵심 도로에 붙인다

실행:
    python build_schematic.py          # 파일 생성 + netconvert + 30분 헤드리스 점검
    python view_schematic.py           # sumo-gui로 보기
"""
import math
import os
import re
import subprocess
import sys

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))
import sumolib  # noqa: E402
from sumolib import checkBinary  # noqa: E402

import minor_roads  # noqa: E402
import osm_shapes as osm  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "skku"
P = lambda suffix: os.path.join(HERE, f"{NAME}.{suffix}")

KMH = lambda v: round(v / 3.6, 2)
SURFACE_OFFSET = 11.0   # 고가 하부 지상도로가 가운데선에서 떨어진 거리 (가운데 = 고가 + 주차장)
VIADUCT_Z = 7.0         # 고가 높이 (m)

# ──────────────────────────────────────────────────────────────
# 1) 노드 (x, y[, type])
# ──────────────────────────────────────────────────────────────
TL = "traffic_light"
NODES = {
    # ① 사거리와 네 갈래
    "SG": (0, 0, TL),            # 성대역 사거리
    "NN": (24, 273, TL),         # 서부로 × 하률로 · 서부로2181번길 = 고속화도로 끝 (여기부터 일반도로)
    "HW": (60, 5320),            # 봉담과천로 사당 방면 끝 (NN에서 5km)
    "WJ": (-450, 72),            # 덕영대로 서쪽, 고속화도로 진출입로 합류점
    "WW": (-800, 188),           # 덕영대로 서쪽 끝
    "DW": (-120, 12),            # 밤밭지하차도 서쪽 입구 (덕영대로 직진은 지하로, 회전 차만 사거리로)
    "DE": (60, -15),             # 밤밭지하차도 동쪽 입구
    "E1": (385, -120),           # 덕영대로 동쪽 (꺾이는 점)
    "YG": (566, -332),           # 덕영대로 육교 (화산로 연결)
    "E2": (815, -672),
    "EF": (1050, -1000),         # 덕영대로 × 정천지하차도 연결로
    "EX": (1211, -1227),         # 덕영대로 남동쪽 끝 (이후 다리로 철길을 넘음)
    # ②③ 서부로 고가 구간: 아래 CL(고가 가운데선) 위에 놓는다 (위치는 대략값 → CL에 투영)
    "D0": (-10, -85),            # 고가 진입/착지 분기점 (사거리에서 철길을 다리로 넘은 직후)
    "G1": (-30, -133, TL),       # 화산로 교차 (동: 화산로, 서: 화산로 서쪽)
    "G2": (-118, -266, TL),      # 율천동주민센터 앞: 양쪽 골목 + 유턴 + 주차장1 출구/2 입구
    "G3": (-197, -440, TL),      # 성균관대학교 정류장 앞: 서쪽 골목 + 동쪽 후문 + 유턴
    "G4": (-232, -640),          # 삼성아파트 앞: 비신호 유턴 + 주차장3 출구 + 서쪽 골목
    "LD": (-241, -800),          # 고가 착지 (합류) / 북쪽 방향 분기
    # 갈림목 양쪽 골목 끝
    "WA1": (-281, -63),          # 화산로 서쪽 끝
    # ⑤ 학교 둘레 (좌표는 OSM 도로 위치를 따름)
    "H1": (290, -189),           # 화산로
    "H2": (469, -358),           # 화산로 (북문 길 · 육교 쪽 연결)
    "H3": (597, -529),           # 화산로 (정자천로13번길로 가는 길)
    "H4": (688, -663),
    "H5": (918, -975),
    "JU": (990, -1100),          # 화산로 × 정자천로 × 정천지하차도 (철길 안쪽)
    "H6": (1073, -1204),         # 화산로 남동쪽 끝
    "UE": (1135, -1035),         # 정천지하차도 출구 (철길·덕영대로 너머)
    "JEX": (1370, -927),         # 정자천로 동쪽 끝
    "JC1": (739, -1230),         # 정자천로
    "JN": (511, -585),           # 정자천로13번길 북쪽 끝
    "JE": (553, -745),           # 정자천로13번길 × 학교 동쪽 출입구
    "JS1": (579, -873),
    "JSm": (535, -1030),         # 일월로90번길(골목) 합류
    "JSs": (510, -1170),         # 남동 골목 합류
    "JS3": (545, -1310),         # 정자천로13번길 남쪽 끝 × 정자천로
    "IE3": (439, -1363),         # 일월로 × 정자천로
    "IES": (500, -1480),         # 일월로 남쪽 끝
    "IW": (-250, -1080, TL),     # 서부로 × 일월로
    "SS": (-262, -1320),         # 서부로 남쪽 끝
    "IE1": (274, -1112),         # 일월로 (일월로90번길 갈림)
    "IE2": (381, -1256),
    # ④ 학교 (차량 출입구는 정문 하나)
    "JM": (125, -1090),          # 정문 (일월로)
    "CN1": (10, -504),           # 북쪽 교내 도로 × 가운데 남북 도로
    "CN2": (300, -505),          # 공자로 북쪽 끝
    "CE": (262, -780),           # 공자로 × 동쪽 출입구 길 (교내 주차장 앞)
    "C3": (250, -900),           # 공자로 남쪽 끝 × 남쪽 가로 도로
    "CJ": (159, -888),           # 정문 길 합류
    "CM": (54, -700),            # 가운데 남북 도로 (꺾이는 점)
    "CC": (27, -869),            # 가운데 남북 도로 × 남쪽 교내 도로
}
NODE_ATTRS = {}   # 노드 추가 속성 (예: rightOfWay)
CORRIDOR = ["D0", "G1", "G2", "G3", "G4", "LD"]
# 유턴 (카카오맵 길찾기로 확인, 2026-10-30): 남쪽 방향은 G3·IW(서부로×일월로), 북쪽 방향은 G2·G3. G4는 유턴 없음
#          G3 남행 유턴        G3 북행 유턴         G2 북행 유턴         IW 남행 유턴         덕영대로 E2(만석로) 동행 유턴
UTURNS = [("G2_G3", "G3_G2"), ("G4_G3", "G3_G4"), ("G3_G2", "G2_G3"), ("LD_IW", "IW_LD"), ("YG_E2", "E2_YG")]

# 서부로 고가 가운데선 (OSM 고가 두 방향 선의 가운데, 사거리에서 착지 지점까지)
CL = [(0, 0), (0, -25), (-6, -68), (-26, -127), (-39, -154), (-60, -188), (-91, -226), (-118, -266),
      (-138, -298), (-153, -326), (-169, -358), (-185, -396), (-197, -433), (-205, -465), (-221, -536),
      (-230, -598), (-234, -660), (-241, -797), (-244, -838)]
S = {n: osm.project(CL, NODES[n][:2]) for n in CORRIDOR}           # 가운데선 누적 거리
for n in CORRIDOR:
    NODES[n] = (*osm.point_at(CL, S[n]), *NODES[n][2:])
S["V1"], S["V3"] = S["D0"] + 120, S["LD"] - 110                     # 고가 오르막 끝 / 내리막 시작
NODES["V1"] = (*osm.point_at(CL, S["V1"]), None, VIADUCT_Z)
NODES["V3"] = (*osm.point_at(CL, S["V3"]), None, VIADUCT_Z)


def xy(n):
    return NODES[n][0], NODES[n][1]


# ──────────────────────────────────────────────────────────────
# 2) 엣지
#    road(a, b, ...) = 양방향 도로. SUMO 기본 spreadType="right"라 방향별로 가운데선 오른쪽에 그려진다.
#    고가 하부 지상도로는 방향마다 shape를 가운데선 오른쪽 SURFACE_OFFSET 만큼 띄워 중앙분리 공간(고가·주차장)을 만든다.
# ──────────────────────────────────────────────────────────────
EDGES = []   # (id, from, to, lanes, speed, priority, shape or None, name)


STRAIGHT = []   # OSM 선을 못 찾아 직선으로 둔 도로 (점검 출력용)


def road(a, b, lanes, kmh, prio, name, lanes_back=None, shape=None, osm_names=None, osm_types=None,
         oneway=False):
    """양방향 도로. osm_names/osm_types를 주면 그 OSM 길을 따라 꺾인 모양을 쓴다 (못 찾으면 직선)."""
    if shape is None and (osm_names or osm_types):
        shape = osm.path_shape(xy(a), xy(b), names=osm_names, highways=osm_types)
        if shape is None:
            STRAIGHT.append(f"{a}-{b}({name})")
    EDGES.append((f"{a}_{b}", a, b, lanes, KMH(kmh), prio, shape, name))
    if oneway:
        return
    back = list(reversed(shape)) if shape else None
    EDGES.append((f"{b}_{a}", b, a, lanes if lanes_back is None else lanes_back, KMH(kmh), prio, back, name))


def one(eid, a, b, lanes, kmh, prio, name, shape=None):
    EDGES.append((eid, a, b, lanes, KMH(kmh), prio, shape, name))


def bent(a, b, *mid):
    """a → (꺾이는 점들) → b shape."""
    return [xy(a), *mid, xy(b)]


ARTERIAL = {"primary", "secondary", "tertiary", "primary_link", "secondary_link", "tertiary_link"}

# ① 사거리 네 갈래
road("NN", "SG", 3, 50, 3, "서부로(북)", osm_names={"서부로"})
road("WW", "WJ", 2, 60, 3, "덕영대로(서)", osm_types=ARTERIAL)
# OSM에서 경로가 끊겨 있는 두 구간은 실제 좌표로 직접 꺾는다 (율전고가교 구간, 사거리 동쪽)
road("WJ", "DW", 3, 60, 3, "덕영대로(서)", shape=bent("WJ", "DW", (-332, 34), (-287, 30)))
road("DW", "SG", 2, 50, 3, "덕영대로(서)", shape=bent("DW", "SG", (-45, 10)))
# 사거리 동쪽 지상 차로: 동쪽 방향 1차로 (네이버 로드뷰 2026-07: 중앙선 옆 1차로, 라바콘 너머는 지하차도 출구), 서쪽 방향은 미확인 2차로
road("SG", "DE", 1, 50, 3, "덕영대로(동)", lanes_back=2)
road("DE", "E1", 3, 60, 3, "덕영대로(동)",
     shape=bent("DE", "E1", (103, -14), (162, -24), (218, -40), (275, -60), (323, -81), (369, -105)))
# 밤밭지하차도: 덕영대로 동서 직진은 사거리 밑으로 (카카오맵: "화서역 방면으로 지하차도 진입", OSM layer=-1)
BAMBAT = [(*xy("DW"), 0), (-70, 5, -4), (10, -5, -4), (*xy("DE"), 0)]
one("DW_DE", "DW", "DE", 2, 60, 3, "밤밭지하차도", BAMBAT)
one("DE_DW", "DE", "DW", 2, 60, 3, "밤밭지하차도", list(reversed(BAMBAT)))
for a, b in (("E1", "YG"), ("YG", "E2"), ("E2", "EF"), ("EF", "EX")):   # 철길 바깥 (육교 너머)
    road(a, b, 3, 60, 3, "덕영대로(동)", osm_names={"덕영대로"})
road("SG", "D0", 4, 50, 3, "서부로", shape=osm.sub(CL, 0, S["D0"]))   # 오른쪽 2차로 = 지상, 왼쪽 2차로 = 고가

# ②③ 고가 하부 지상도로: 고가 가운데선을 방향별로 오른쪽 SURFACE_OFFSET만큼 띄운 선
for a, b in zip(CORRIDOR, CORRIDOR[1:]):
    one(f"{a}_{b}", a, b, 2, 50, 3, "서부로(지상)", osm.offset(osm.sub(CL, S[a], S[b]), SURFACE_OFFSET))
    one(f"{b}_{a}", b, a, 2, 50, 3, "서부로(지상)", osm.offset(osm.sub(CL, S[b], S[a]), SURFACE_OFFSET))


def viaduct_shape(a, b):
    """고가 shape: 가운데선 구간 + 높이 (오르막·내리막은 거리에 비례)."""
    pts = osm.sub(CL, S[a], S[b])
    za = VIADUCT_Z if a in ("V1", "V3") else 0.0
    zb = VIADUCT_Z if b in ("V1", "V3") else 0.0
    total, acc, out = osm.poly_len(pts), 0.0, []
    for i, q in enumerate(pts):
        if i:
            acc += math.dist(pts[i - 1], q)
        out.append((*q, za + (zb - za) * acc / total))
    return out


for a, b in (("D0", "V1"), ("V1", "V3"), ("V3", "LD")):
    shape = viaduct_shape(a, b)
    one(f"via_{a}_{b}", a, b, 2, 60, 4, "서부로 고가", shape)
    one(f"via_{b}_{a}", b, a, 2, 60, 4, "서부로 고가", list(reversed(shape)))
road("LD", "IW", 4, 60, 3, "서부로", osm_names={"서부로"})   # 착지 후 4차로 (지상 2 + 고가 2)
road("IW", "SS", 3, 60, 3, "서부로", osm_names={"서부로"})

# 고가 밑 공영주차장 (가운데, 갈림목 Ga에서 들어가 다음 갈림목 Gb로 나옴)
#   실제처럼 입구 → 고가 밑 폭 전체를 쓰는 주차장(가운데 통로 + 양쪽 직각 주차면) → 출구.
#   통로 3.2m + 양쪽 주차면 5m = 약 13m ≈ 고가 폭(4차로 12.8m)
LOTS = [("P1", "G1", "G2"), ("P2", "G2", "G3"), ("P3", "G3", "G4")]
LOT_GAP = 25    # 갈림목에서 주차장 입구·출구까지 거리 (m)
for lot, ga, gb in LOTS:
    S[f"{lot}i"], S[f"{lot}o"] = S[ga] + LOT_GAP, S[gb] - LOT_GAP
    NODES[f"{lot}i"] = osm.point_at(CL, S[f"{lot}i"])
    NODES[f"{lot}o"] = osm.point_at(CL, S[f"{lot}o"])
    one(f"{lot}_in", ga, f"{lot}i", 1, 20, 0, f"공영주차장{lot[1]} 입구", osm.sub(CL, S[ga], S[f"{lot}i"]))
    one(f"{lot}_aisle", f"{lot}i", f"{lot}o", 1, 15, 0, f"공영주차장{lot[1]}",
        osm.sub(CL, S[f"{lot}i"], S[f"{lot}o"]))
    one(f"{lot}_out", f"{lot}o", gb, 1, 20, 0, f"공영주차장{lot[1]} 출구", osm.sub(CL, S[f"{lot}o"], S[gb]))

# 갈림목 양쪽 골목
road("G1", "WA1", 1, 30, 1, "화산로(서쪽)", shape=bent("G1", "WA1", (-77, -93), (-219, -71)))


# ⑤ 학교 둘레
#   화산로는 철길 안쪽: 덕영대로(바깥)와는 직접 연결 없음
road("G1", "H1", 1, 40, 2, "화산로", shape=bent("G1", "H1", (33, -108), (88, -114), (159, -126), (227, -147)))
for a, b in (("H1", "H2"), ("H2", "H3"), ("H3", "H4"), ("H4", "H5"), ("H5", "JU"), ("JU", "H6")):
    road(a, b, 1, 40, 2, "화산로", osm_names={"화산로"})
road("H3", "JN", 1, 30, 2, "화산로141번길", osm_names={"화산로141번길"})
for a, b in (("JN", "JE"), ("JE", "JS1"), ("JS1", "JSm"), ("JSm", "JSs"), ("JSs", "JS3")):
    road(a, b, 1, 40, 2, "정자천로13번길", osm_names={"정자천로13번길"})
for a, b in (("IW", "JM"), ("JM", "IE1"), ("IE1", "IE2"), ("IE2", "IE3"), ("IE3", "IES")):
    road(a, b, 1, 40, 2, "일월로", osm_names={"일월로"})
road("IE3", "JS3", 1, 40, 2, "정자천로", osm_names={"정자천로"})
road("JS3", "JC1", 1, 40, 2, "정자천로", osm_names={"정자천로"})
road("JC1", "JU", 1, 40, 2, "정자천로", shape=bent("JC1", "JU", (812, -1190)))
# 정천지하차도: 철길과 덕영대로 밑으로 (-6m), 덕영대로와는 연결로(UE-EF)로 이어진다
TUNNEL = [(*xy("JU"), 0), (1050, -1071, -4), (1080, -1057, -4), (*xy("UE"), 0)]
one("JU_UE", "JU", "UE", 1, 40, 2, "정천지하차도", TUNNEL)
one("UE_JU", "UE", "JU", 1, 40, 2, "정천지하차도", list(reversed(TUNNEL)))
road("UE", "JEX", 1, 40, 2, "정자천로", osm_names={"정자천로"})
road("UE", "EF", 1, 30, 2, "정자천로-덕영대로 연결로")

# ④ 학교 내부: 정문으로 들어와 오른쪽(동쪽)으로 일방통행, 시계 반대 방향 한 바퀴 → 정문으로 나감
SERVICE = {"service"}
road("JM", "CJ", 1, 30, 1, "정문 진입로", osm_types=SERVICE)              # 정문 길만 양방향
CAMPUS_LOOP = [("CJ", "C3", dict(osm_types=SERVICE)), ("C3", "CE", dict(osm_names={"공자로"})),
               ("CE", "CN2", dict(osm_names={"공자로"})), ("CN2", "CN1", dict(osm_types=SERVICE)),
               ("CN1", "CM", dict(shape=bent("CN1", "CM", (71, -596)))), ("CM", "CC", {}),
               ("CC", "CJ", dict(osm_types=SERVICE))]
for a, b, geo in CAMPUS_LOOP:
    road(a, b, 1, 30, 1, "교내 순환로(일방)", oneway=True, **geo)

# ⑥ 봉담과천로 (5km) → 사거리 북쪽 서부로로 바로 이어짐
road("HW", "NN", 2, 90, 5, "봉담과천로")

# ⑦ 골목·생활도로: 사용자가 지도에 빨간 선으로 그린 범위 (조금 넉넉하게)
AREA = [(-60, 345), (300, 350), (600, 345), (650, 200), (620, 60), (735, -160), (870, -395), (1025, -550), (1165, -825),
        (1200, -1060), (1065, -1170), (945, -1235), (670, -1345), (470, -1435), (230, -1350), (-20, -1290),
        (-215, -1270), (-460, -1070), (-540, -830), (-570, -530), (-520, -240), (-460, -40), (-320, 65),
        (-140, 240)]
CORE_NAMES = {"서부로", "덕영대로", "화산로", "일월로", "정자천로", "정자천로13번길", "화산로141번길", "공자로",
              "봉담과천로", "율전고가교", "성대역지하차도", "밤밭지하차도", "정천지하차도", "율전지하차도"}
CAMPUS_NODES = {"JM", "CJ", "C3", "CE", "CN2", "CN1", "CM", "CC"}
NO_ATTACH = {"SG", "D0", "LD", "V1", "V3", "HW"} | CAMPUS_NODES | {f"{lot}{k}" for lot, *_ in LOTS for k in "io"}
NO_SPLIT = {e[0] for e in EDGES if e[0].startswith(("via_", "P1_", "P2_", "P3_", "JU_UE", "UE_JU", "HW_", "NN_HW"))
            or (e[1] in CAMPUS_NODES and e[2] in CAMPUS_NODES)}
NO_SPLIT |= {"WJ_DW", "DW_WJ", "WW_WJ", "WJ_WW",          # 덕영대로 서쪽 = 율전고가교: 골목이 바로 못 붙음 (카카오맵 확인)
             "DW_SG", "SG_DW", "SG_DE", "DE_SG", "DW_DE", "DE_DW"}   # 사거리 바로 옆 · 밤밭지하차도
# 중앙분리대 큰길: 골목은 우회전으로만 드나든다 (카카오맵 확인: 서부로 북쪽 양쪽 골목은 북쪽 교차로에서만 건넘)
DIVIDED = {f"{a}_{b}" for a, b in (("SG", "NN"), ("NN", "SG"), ("DE", "E1"), ("E1", "DE"), ("E1", "YG"), ("YG", "E1"),
                                   ("YG", "E2"), ("E2", "YG"), ("E2", "EF"), ("EF", "E2"), ("EF", "EX"), ("EX", "EF"),
                                   ("LD", "IW"), ("IW", "LD"), ("IW", "SS"), ("SS", "IW"))}
SPLIT, N_MINOR = minor_roads.add_minor_roads(NODES, EDGES, AREA, CORE_NAMES, NO_ATTACH, NO_SPLIT, kmh=KMH,
                                             divided=DIVIDED)
first = lambda e: SPLIT.get(e, [e])[0]       # 나뉜 핵심 도로: 첫 조각 (출발 쪽)
last = lambda e: SPLIT.get(e, [e])[-1]       # 마지막 조각 (도착 쪽)
expand = lambda edges: " ".join(p for e in edges.split() for p in SPLIT.get(e, [e]))

# ──────────────────────────────────────────────────────────────
# 3) 연결 (connections)
#    - 고가 분기/합류 차로를 명시 (오른쪽 2 = 지상, 왼쪽 2 = 고가)
#    - 유턴은 UTURNS에 적은 곳에서만 (카카오맵 길찾기로 확인, 나머지는 삭제)
#    - 주차장: 입구는 서부로 양방향에서만(골목에서 바로 진입 X), 출구에서 좌회전·유턴 금지
# ──────────────────────────────────────────────────────────────
CONNS = []
DELETES = []
for i in range(4):
    CONNS.append(("SG_D0", "D0_G1" if i < 2 else "via_D0_V1", i, i % 2))
    CONNS.append(("IW_LD", "LD_G4" if i < 2 else "via_LD_V3", i, i % 2))
for src, base in (("G1_D0", 0), ("via_V1_D0", 2)):
    for i in range(2):
        CONNS.append((src, "D0_SG", i, base + i))
for src, base in (("G4_LD", 0), ("via_V3_LD", 2)):
    for i in range(2):
        CONNS.append((src, "LD_IW", i, base + i))
# 사거리 동쪽 동쪽 방향 합류: 지상 1차로는 중앙선 쪽(맨 왼쪽), 밤밭지하차도 출구 2차로는 오른쪽 (네이버 로드뷰 2026-07)
CONNS += [("DW_DE", "DE_E1", 0, 0), ("DW_DE", "DE_E1", 1, 1), ("SG_DE", "DE_E1", 0, 2)]
# 사거리 북쪽 방향 차로 (네이버 로드뷰 2026-06·07 확인): 0 직진·우회전("화서역"), 1 직진, 3(중앙분리대 옆) 직진.
#   좌회전 없음: 사거리 북쪽 신호등 옆 좌회전 금지 표지 + 카카오맵 길찾기도 동쪽으로 갔다 유턴해서 옴.
#   2차로 화살표와 서부로 북쪽(SG_NN) 차로 수는 미확인 → 고가 2차로가 SG_NN 2차로로 합류하는 것은 추정
CONNS += [("D0_SG", "SG_DE", 0, 0), ("D0_SG", "SG_NN", 0, 0), ("D0_SG", "SG_NN", 1, 1),
          ("D0_SG", "SG_NN", 2, 2), ("D0_SG", "SG_NN", 3, 2)]

CONNS = [(last(a), first(b), fl, tl) for a, b, fl, tl in CONNS]      # 골목이 붙어 나뉜 엣지 이름 반영
# 유턴 자리 양쪽이 골목 때문에 나뉘면 SUMO가 유턴을 자동으로 못 만든다 → main()에서 직접 지정 (fix_uturns)
_lanes = {e[0]: e[3] for e in EDGES}
_ends = {e[0]: (e[1], e[2]) for e in EDGES}
UTURN_EXPLICIT = [(last(a), first(b)) for a, b in UTURNS if _ends[last(a)][::-1] != _ends[first(b)]]

incoming, outgoing, nbrs = {}, {}, {}
for eid, a, b, *_ in EDGES:
    outgoing.setdefault(a, []).append(eid)
    incoming.setdefault(b, []).append(eid)
    nbrs.setdefault(a, set()).add(b)
    nbrs.setdefault(b, set()).add(a)
by_ends = {(e[1], e[2]): e[0] for e in EDGES}
UTURN_ALLOWED = {(last(a), first(b)) for a, b in UTURNS}
for e in EDGES:
    eid, a, b = e[0], e[1], e[2]
    rev = by_ends.get((b, a))
    if rev is None or len(nbrs[b]) == 1:         # 막다른 골목 끝에서는 돌아 나올 수 있게 둔다
        continue
    if (eid, rev) not in UTURN_ALLOWED:
        DELETES.append((eid, rev))
# G4 서쪽 골목: 우회전으로만 드나든다 (카카오맵 확인: 북쪽 방향으로 바로 못 나감)
for src in incoming["G4"]:
    if src.startswith("m"):
        DELETES.append((src, first("G4_G3")))
for dst in outgoing["G4"]:
    if dst.startswith("m"):
        DELETES.append((last("LD_G4"), dst))
DELETES += [(last("G1_D0"), "via_D0_V1"), ("via_V1_D0", first("D0_G1")),     # 고가↔지상 역방향 꺾기 금지
            ("via_V3_LD", first("LD_G4")), (last("G4_LD"), "via_LD_V3")]
for lot, ga, gb in LOTS:
    i = CORRIDOR.index(ga)
    allowed = {last(f"{CORRIDOR[i - 1]}_{ga}"), last(f"{gb}_{ga}")}   # 남쪽 방향 직진 / 북쪽 방향 좌회전으로만 진입
    DELETES += [(src, f"{lot}_in") for src in incoming[ga] if src not in allowed]
    DELETES += [(f"{lot}_out", dst) for dst in outgoing[gb]
                if dst == first(f"{gb}_{ga}") or dst.endswith("_in")]  # 출구: 좌회전(북쪽 방향)·다음 주차장 직행 금지


# ──────────────────────────────────────────────────────────────
# 4) 정류장·주차장·라벨
# ──────────────────────────────────────────────────────────────
BUS_STOPS = [   # (id, edge, 이름)
    ("bs_N_s", "NN_SG", "율전성당.성균관대역"), ("bs_N_n", "SG_NN", "성균관대역.고용노동부"),
    ("bs_G1G2", "G1_G2", "성균관대역(마을)"), ("bs_G2G3", "G2_G3", "성균관대학교"),
    ("bs_G4LD", "G4_LD", "삼성아파트"), ("bs_G3G2", "G3_G2", "성균관대학교"),
    ("bs_G2G1", "G2_G1", "율천동주민센터"), ("bs_LDG4", "LD_G4", "삼성1차아파트"),
    ("bs_E1YG", "E1_YG", "비단마을입구"), ("bs_YGE1", "YG_E1", "비단마을입구"),
    ("bs_YGE2", "YG_E2", "경기체육고"), ("bs_E2YG", "E2_YG", "천천먹거리촌"),
    ("bs_E2EF", "E2_EF", "삼호진덕아파트"), ("bs_EFE2", "EF_E2", "일성아파트"),
    ("bs_H1H2", "H1_H2", "화산로"), ("bs_H2H1", "H2_H1", "화산로"),
    ("bs_IWJM", "IW_JM", "성균관대학교 정문"), ("bs_JMIW", "JM_IW", "성균관대학교 정문"),
    ("bs_JS1", "JSs_JSm", "정자천로13번길 1"), ("bs_JS1r", "JSm_JSs", "정자천로13번길 1"),
    ("bs_JS2", "JS1_JE", "정자천로13번길 2"), ("bs_JS2r", "JE_JS1", "정자천로13번길 2"),
    ("bs_JS3", "JE_JN", "정자천로13번길 3"), ("bs_JS3r", "JN_JE", "정자천로13번길 3"),
]
CAMPUS_LOT = ("PC", "C3_CE", 40)   # 공자로 동쪽 큰 주차장 (OSM 주차장 위치)
LABELS = [   # sumo-gui 한글 글꼴이 없어 영문 라벨
    ("SG", "Sageori (scramble)"), ("G1", "G1 Hwasan-ro"), ("G2", "G2 U-turn"), ("G3", "G3 U-turn"),
    ("G4", "G4 U-turn"), ("P1i", "Public parking 1"), ("P2i", "Public parking 2"),
    ("P3i", "Public parking 3"), ("JM", "Main gate (only car gate)"), ("CN1", "Campus one-way loop"),
    ("YG", "Footbridge (over rail)"), ("JU", "Jeongcheon underpass"),
    ("NN", "Highway end (Bongdam-Gwacheon-ro 5km)"), ("CE", "Campus parking"), ("JS1", "Jeongjacheon-ro 13"),
]

# ──────────────────────────────────────────────────────────────
# 5) 교통 수요 (대/시). from/to만 주면 SUMO가 경로를 찾는다(정차가 있으면 정차 엣지를 경유).
# ──────────────────────────────────────────────────────────────
SURFACE_SB = "D0_G1 G1_G2 G2_G3 G3_G4 G4_LD"
SURFACE_NB = "LD_G4 G4_G3 G3_G2 G2_G1 G1_D0"
URBAN_SCALE = 0.6   # 수요 배율
FLOWS = [   # (id, from, to, veh/h, extra attrs, stop)
    # 서부로 통과 (대부분 고가 이용) + 지상 이용
    ("sb_thru", "NN_SG", "IW_SS", 250, "", None), ("nb_thru", "SS_IW", "SG_NN", 250, "", None),
    ("sb_surf", "NN_SG", "IW_SS", 80, f'via="{SURFACE_SB}"', None),
    ("nb_surf", "SS_IW", "SG_NN", 80, f'via="{SURFACE_NB}"', None),
    ("w_s", "WW_WJ", "IW_SS", 180, "", None), ("s_w", "SS_IW", "WJ_WW", 180, "", None),
    ("e_s", "EX_EF", "IW_SS", 120, "", None), ("s_e", "SS_IW", "EF_EX", 120, "", None),
    # 덕영대로 동서
    ("w_e", "WW_WJ", "EF_EX", 250, "", None), ("e_w", "EX_EF", "WJ_WW", 250, "", None),
    ("n_e", "NN_SG", "EF_EX", 120, "", None), ("e_n", "EX_EF", "SG_NN", 120, "", None),
    ("n_w", "NN_SG", "WJ_WW", 80, "", None), ("w_n", "WW_WJ", "SG_NN", 80, "", None),
    # 일월로 (정문 앞)
    ("n_ies", "NN_SG", "IE3_IES", 60, "", None), ("ies_n", "IES_IE3", "SG_NN", 60, "", None),
    ("w_ies", "WW_WJ", "IE3_IES", 40, "", None),
    # 철길 건너기 (정천지하차도): 학교 쪽 ↔ 덕영대로·정자천로 동쪽
    ("ies_e", "IES_IE3", "EF_EX", 40, "", None), ("e_ies", "EX_EF", "IE3_IES", 40, "", None),
    ("h6_jex", "H6_JU", "UE_JEX", 40, "", None), ("jex_n", "JEX_UE", "SG_NN", 40, "", None),
    ("n_jex", "NN_SG", "UE_JEX", 40, "", None), ("jex_h6", "JEX_UE", "JU_H6", 40, "", None),
    # 골목 출입 (갈림목에서 좌회전·유턴 발생)
    ("wa1_e", "WA1_G1", "EF_EX", 30, "", None),
    # 공영주차장 (고가 밑) — 북쪽 방향 차는 갈림목 좌회전 또는 유턴 후 진입
    ("p1_a", "NN_SG", "IW_SS", 40, "", ("P1", 300)), ("p1_b", "SS_IW", "SG_NN", 30, "", ("P1", 300)),
    ("p1_c", "WW_WJ", "SG_NN", 20, "", ("P1", 300)),
    ("p2_a", "EX_EF", "IW_SS", 30, "", ("P2", 300)), ("p2_b", "SS_IW", "SG_NN", 30, "", ("P2", 300)),
    ("p3_a", "NN_SG", "IW_SS", 30, "", ("P3", 300)), ("p3_b", "SS_IW", "SG_NN", 30, "", ("P3", 300)),
    # 학교 (후문·정문 → 교내 주차장)
    ("c_w", "WW_WJ", "IW_SS", 40, "", ("PC", 600)), ("c_e", "EX_EF", "SG_NN", 40, "", ("PC", 600)),
    ("c_s", "SS_IW", "EF_EX", 40, "", ("PC", 600)),
    # 교내 한 바퀴 (주차 없이 정문 → 순환 → 정문)
    ("c_loop", "SS_IW", "IW_SS", 40, 'via="JM_CJ CJ_C3 C3_CE CE_CN2 CN2_CN1 CN1_CM CM_CC CC_CJ CJ_JM"', None),
    ("c_loop2", "WW_WJ", "SG_NN", 30, 'via="JM_CJ CJ_C3 C3_CE CE_CN2 CN2_CN1 CN1_CM CM_CC CC_CJ CJ_JM"', None),
]
# 골목 출입: 골목 30곳을 골라 큰길 끝(북쪽 고속화도로·서부로 남쪽·덕영대로 양끝·일월로·정자천로)과 오가게 한다
_rng = __import__("random").Random(7)
_alleys = sorted(e[0] for e in EDGES if e[0].startswith("m") and osm.poly_len([p[:2] for p in e[6]]) > 40)
_fringe_out = ["SG_NN", "IW_SS", "EF_EX", "WJ_WW", "IE3_IES", "UE_JEX"]
_fringe_in = ["NN_SG", "SS_IW", "EX_EF", "WW_WJ", "IES_IE3", "JEX_UE"]
for k, e in enumerate(_rng.sample(_alleys, min(30, len(_alleys)))):
    FLOWS.append((f"al{k}_out", e, _rng.choice(_fringe_out), 12, "", None))
    FLOWS.append((f"al{k}_in", _rng.choice(_fringe_in), e, 12, "", None))
FLOWS = [(fid, "HW_NN" if src == "NN_SG" else src, "NN_HW" if dst == "SG_NN" else dst, vph, extra, stop)
         for fid, src, dst, vph, extra, stop in FLOWS]      # 북쪽 출발·도착 = 고속화도로 끝
BUS_LINES = [   # (id, 경로, 정류장, 배차 간격 s)
    ("bus_sb", "NN_SG SG_D0 " + SURFACE_SB + " LD_IW IW_SS", ["bs_N_s", "bs_G1G2", "bs_G2G3", "bs_G4LD"], 300),
    ("bus_nb", "SS_IW IW_LD " + SURFACE_NB + " D0_SG SG_NN", ["bs_LDG4", "bs_G3G2", "bs_G2G1", "bs_N_n"], 300),
    ("bus_eb", "WW_WJ WJ_DW DW_DE DE_E1 E1_YG YG_E2 E2_EF EF_EX", ["bs_E1YG", "bs_YGE2", "bs_E2EF"], 240),
    ("bus_wb", "EX_EF EF_E2 E2_YG YG_E1 E1_DE DE_DW DW_WJ WJ_WW", ["bs_EFE2", "bs_E2YG", "bs_YGE1"], 240),
    # 학교 둘레 순환: 정문 → 정자천로13번길 → 화산로 → 사거리
    ("bus_gate", "SS_IW IW_JM JM_IE1 IE1_IE2 IE2_IE3 IE3_JS3 JS3_JSs JSs_JSm JSm_JS1 JS1_JE JE_JN JN_H3 H3_H2 "
     "H2_H1 H1_G1 G1_D0 D0_SG SG_NN", ["bs_IWJM", "bs_JS1", "bs_JS2", "bs_JS3", "bs_H2H1"], 600),
    ("bus_gate_r", "NN_SG SG_D0 D0_G1 G1_H1 H1_H2 H2_H3 H3_JN JN_JE JE_JS1 JS1_JSm JSm_JSs JSs_JS3 JS3_IE3 "
     "IE3_IE2 IE2_IE1 IE1_JM JM_IW IW_SS", ["bs_H1H2", "bs_JS3r", "bs_JS2r", "bs_JS1r", "bs_JMIW"], 600),
    # 화산로 → 정천지하차도 → 덕영대로
    ("bus_hwasan", "NN_SG SG_D0 D0_G1 G1_H1 H1_H2 H2_H3 H3_H4 H4_H5 H5_JU JU_UE UE_EF EF_EX", ["bs_H1H2"], 600),
]


# ──────────────────────────────────────────────────────────────
# 파일 쓰기
# ──────────────────────────────────────────────────────────────
def fmt(pts):
    return " ".join(",".join(f"{v:.2f}" for v in p) for p in pts)


def write_plain():
    with open(P("nod.xml"), "w", encoding="utf-8") as f:
        f.write("<nodes>\n")
        for n, v in NODES.items():
            typ = v[2] if len(v) > 2 and v[2] else None
            zz = f' z="{v[3]}"' if len(v) > 3 else ""
            extra = f" {NODE_ATTRS[n]}" if n in NODE_ATTRS else ""
            f.write(f'    <node id="{n}" x="{v[0]:.2f}" y="{v[1]:.2f}"{zz}' + (f' type="{typ}"' if typ else "")
                    + extra + "/>\n")
        f.write("</nodes>\n")
    with open(P("edg.xml"), "w", encoding="utf-8") as f:
        f.write("<edges>\n")
        for eid, a, b, lanes, speed, prio, shape, name in EDGES:
            sh = f' shape="{fmt(shape)}"' if shape else ""
            f.write(f'    <edge id="{eid}" from="{a}" to="{b}" numLanes="{lanes}" speed="{speed}" '
                    f'priority="{prio}" name="{name}"{sh}/>\n')
        f.write("</edges>\n")
    with open(P("con.xml"), "w", encoding="utf-8") as f:
        f.write("<connections>\n")
        for src, dst, fl, tl in CONNS:
            f.write(f'    <connection from="{src}" to="{dst}" fromLane="{fl}" toLane="{tl}"/>\n')
        for src, dst in DELETES:
            f.write(f'    <delete from="{src}" to="{dst}"/>\n')
        f.write("</connections>\n")


def netconvert(tls_file=None):
    log = P("netconvert.log")
    r = subprocess.run([checkBinary("netconvert"), "-n", P("nod.xml"), "-e", P("edg.xml"), "-x", P("con.xml"),
                        *(["-i", tls_file] if tls_file else []),
                        "-o", P("net.xml"), "--offset.disable-normalization", "true",
                        "--default.lanewidth", "3.2", "--junctions.corner-detail", "5",
                        "--tls.default-type", "static", "--tls.left-green.time", "6",
                        "--no-warnings", "false", "--log", log], capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout, r.stderr)
        raise SystemExit("netconvert 실패")
    warns = [ln for ln in open(log, encoding="utf-8", errors="replace")
             if ln.startswith("Warning") and "cannot be reset" not in ln and "total messages" not in ln]
    return warns


# 사거리 신호: 남북 → 동서 → 보행자 동시신호(차량 전부 정지). 비보호 좌회전 g, 다른 축이 녹색일 때 우회전은 s(멈춘 뒤 진행)
# 차량: 네 방향 동시에 녹색. 서로 부딪히는 흐름은 서부로(남북) 직진·우회전이 우선(G), 나머지는 양보하며 진행(g)
#   → 이 신호 계획을 netconvert에 다시 넣어(-i) 사거리 통행 우선권을 신호에 맞게 다시 계산한다
# 보행자: 동시신호 약 45초 (실제 40~50초) 동안 차량 전부 정지
SG_PHASES = [("ALL", 70), ("ALLy", 3), ("X", 45)]
SG_AXIS = {"NN_SG": "NS", "D0_SG": "NS", "DW_SG": "EW", "DE_SG": "EW"}


def write_sg_tls(net):
    tls = net.getTLSSecure("SG")
    links = {}
    for in_lane, out_lane, idx in tls.getConnections():
        c = [c for c in in_lane.getEdge().getConnections(out_lane.getEdge())
             if c.getFromLane() == in_lane and c.getToLane() == out_lane][0]
        links[idx] = ({last(k): v for k, v in SG_AXIS.items()}[in_lane.getEdge().getID()], c.getDirection())
    n = max(links) + 1
    # 같은 차로로 합쳐지는 우선(G) 흐름이 둘이면 바깥쪽(왼쪽) 차로에서 오는 쪽은 양보(g)
    merge_minor, seen = set(), {}
    for in_lane, out_lane, idx in sorted(tls.getConnections(), key=lambda c: c[0].getIndex()):
        if links[idx][0] == "NS" and links[idx][1] not in ("l", "L"):
            if out_lane.getID() in seen:
                merge_minor.add(idx)
            seen[out_lane.getID()] = idx

    def state(ph):
        s = ""
        for i in range(n):
            axis, d = links[i]
            if ph == "X":
                s += "r"
            elif ph == "ALLy":
                s += "y"
            else:
                s += "G" if axis == "NS" and d not in ("l", "L") and i not in merge_minor else "g"
        return s
    with open(P("tls.add.xml"), "w", encoding="utf-8") as f:
        f.write('<additional>\n    <!-- 성대역 사거리: 차량 전부 동시 녹색 → 황색 → 보행자 동시신호 (차량 전부 정지) -->\n'
                '    <tlLogic id="SG" type="static" programID="scramble" offset="0">\n')
        for ph, dur in SG_PHASES:
            f.write(f'        <phase duration="{dur}" state="{state(ph)}"/>\n')
        f.write("    </tlLogic>\n</additional>\n")


def lot_spaces(lot, pitch=2.6, gap=2.5):
    """통로(고가 가운데선을 따라 굽음) 양쪽 직각 주차면 중심 좌표와 방향 (통로 가운데선에서 1.6 + 2.5 = 4.1m)."""
    s0, s1 = S[f"{lot}i"], S[f"{lot}o"]
    out = []
    d = s0 + gap + pitch / 2
    while d < s1 - gap:
        cx, cy = osm.point_at(CL, d)
        (ax, ay), (bx, by) = osm.point_at(CL, d - 1), osm.point_at(CL, d + 1)
        L = math.hypot(bx - ax, by - ay)
        ux, uy = (bx - ax) / L, (by - ay) / L
        heading = (90 - math.degrees(math.atan2(uy, ux))) % 360  # SUMO 각도 (북쪽 0, 시계 방향)
        for side in (1, -1):                                      # 오른쪽, 왼쪽 줄
            out.append((cx + uy * 4.1 * side, cy - ux * 4.1 * side, (heading + 90 * side) % 360))
        d += pitch
    return out


def write_additional(net):
    with open(P("stops.add.xml"), "w", encoding="utf-8") as f:
        f.write("<additional>\n")
        for sid, edge, name in BUS_STOPS:
            edge = max(SPLIT.get(edge, [edge]), key=lambda e: net.getEdge(e).getLength())   # 나뉘었으면 가장 긴 조각
            L = net.getEdge(edge).getLength()
            s = max(5.0, L * 0.35)
            f.write(f'    <busStop id="{sid}" lane="{edge}_0" startPos="{s:.1f}" endPos="{min(L - 2, s + 25):.1f}" '
                    f'name="{name}" friendlyPos="true"/>\n')
        for lot, _ga, _gb in LOTS:
            f.write(f'    <parkingArea id="{lot}" lane="{lot}_aisle_0" startPos="1" endPos="-1" '
                    f'roadsideCapacity="0" name="공영주차장{lot[1]}" friendlyPos="true">\n')
            for x, y, ang in lot_spaces(lot):
                f.write(f'        <space x="{x:.2f}" y="{y:.2f}" width="2.5" length="5" angle="{ang:.1f}"/>\n')
            f.write("    </parkingArea>\n")
        pid, edge, cap = CAMPUS_LOT
        f.write(f'    <parkingArea id="{pid}" lane="{edge}_0" startPos="20" endPos="-20" '
                f'roadsideCapacity="{cap}" angle="90" name="교내주차장" friendlyPos="true"/>\n')
        for i, line in enumerate(osm.rail_lines((-900, -1450, 1450, 400))):
            f.write(f'    <poly id="rail_{i}" type="rail" color="150,70,200" fill="0" lineWidth="2.5" layer="-1" '
                    f'shape="{fmt(line)}"/>\n')
        for node, text in LABELS:
            x, y = NODES[node][0], NODES[node][1]
            f.write(f'    <poi id="lbl_{node}" type="{text}" x="{x + 12:.1f}" y="{y + 12:.1f}" '
                    f'color="0,0,0,0" layer="100"/>\n')
        f.write("</additional>\n")


def write_routes(net):
    with open(P("rou.xml"), "w", encoding="utf-8") as f:
        f.write("<routes>\n"
                '    <vType id="DEFAULT_VEHTYPE" sigma="0.5" impatience="0.5" color="255,220,0"/>\n'
                '    <vType id="hwcar" carFollowModel="IDM" accel="1.0" decel="2.0" tau="1.2" impatience="0.5" color="100,200,255"/>\n'
                '    <vType id="bus" vClass="bus" color="0,160,80"/>\n'
                '    <vType id="parker" sigma="0.5" impatience="0.5" color="255,120,0"/>\n')
        for bid, edges, stops, _period in BUS_LINES:
            f.write(f'    <route id="r_{bid}" edges="{expand(edges)}">\n')
            for s in stops:
                f.write(f'        <stop busStop="{s}" duration="20"/>\n')
            f.write("    </route>\n")
        for bid, _e, _s, period in BUS_LINES:
            f.write(f'    <flow id="{bid}" type="bus" begin="0" end="3600" period="{period}" route="r_{bid}"/>\n')
        dropped = []
        for fid, src, dst, vph, extra, stop in FLOWS:
            if fid.startswith("al") and net.getShortestPath(net.getEdge(last(src)), net.getEdge(first(dst)))[0] is None:
                dropped.append(fid)                 # 일방통행 등으로 갈 수 없는 골목 수요는 뺀다
                continue
            typ = ' type="parker"' if stop and "type=" not in extra else ""
            if src.startswith("HW_") and not stop:
                typ = ' type="hwcar"'               # 고속화도로에서 오는 차는 IDM (정체파 실험용)
            vph *= URBAN_SCALE
            extra = re.sub(r'via="([^"]*)"', lambda m: f'via="{expand(m.group(1))}"', extra)
            head = (f'    <flow id="{fid}" begin="0" end="3600" period="exp({vph / 3600:.4f})" '
                    f'from="{last(src)}" to="{first(dst)}"{typ} departLane="best" departSpeed="max" {extra}')
            if stop:
                f.write(head + f'>\n        <stop parkingArea="{stop[0]}" duration="{stop[1]}"/>\n    </flow>\n')
            else:
                f.write(head + "/>\n")
        f.write("</routes>\n")
    if dropped:
        print(f"경로가 없어 뺀 골목 수요 {len(dropped)}개: {', '.join(dropped)}")


def write_cfg():
    with open(P("sumocfg"), "w", encoding="utf-8") as f:
        f.write(f"""<configuration>
    <input>
        <net-file value="{NAME}.net.xml"/>
        <route-files value="{NAME}.rou.xml"/>
        <additional-files value="{NAME}.stops.add.xml"/>
        <gui-settings-file value="{NAME}.gui.xml"/>
    </input>
    <time><begin value="0"/><end value="3600"/></time>
    <processing>
        <time-to-teleport value="300"/>
        <collision.action value="warn"/>
    </processing>
    <random_number><seed value="42"/></random_number>
</configuration>
""")
    with open(P("gui.xml"), "w", encoding="utf-8") as f:
        f.write('<viewsettings>\n    <scheme name="skku">\n'
                '        <background backgroundColor="245,245,240" showGrid="0"/>\n'
                '        <pois poiType_show="1" poiType_size="70" poiType_color="20,20,120" poiType_constantSize="1"/>\n'
                '    </scheme>\n    <delay value="40"/>\n</viewsettings>\n')


def check(seconds=1800):
    """헤드리스로 돌려 투입·도착·순간이동·충돌·대기를 확인한다."""
    stat = P("stats.xml")
    r = subprocess.run([checkBinary("sumo"), "-c", P("sumocfg"), "--end", str(seconds), "--no-step-log", "true",
                        "--statistic-output", stat, "--duration-log.statistics", "true"],
                       capture_output=True, text=True)
    out = r.stdout + r.stderr
    for ln in out.splitlines():
        if ln.startswith("Error"):
            print("   !!", ln)
    warn = [ln for ln in out.splitlines() if ln.startswith("Warning")]
    kinds = {}
    for ln in warn:
        key = ("teleport" if "Teleporting" in ln else "collision" if "ollision" in ln
               else "parking" if "parking" in ln.lower() else "other")
        kinds[key] = kinds.get(key, 0) + 1
    print(f"[{seconds}s] 경고 {len(warn)}건 {kinds}")
    for ln in out.splitlines():
        if any(k in ln for k in ("Inserted", "Running", "Waiting", "Teleports", "Collisions", "Halting",
                                 "Duration", "TimeLoss", "WaitingTime", "Speed")):
            print("   ", ln.strip())
    others = [w for w in warn if "Teleporting" not in w and "ollision" not in w][:8]
    for w in others:
        print("    *", w[:160])
    tele = [w for w in warn if "Teleporting" in w][:8]
    for w in tele:
        print("    T", w[:160])


def fix_uturns(net):
    """직접 지정해야 하는 유턴: 연결을 하나라도 직접 주면 그 엣지의 나머지 연결은 자동으로 안 만들어지므로,
    처음 변환에서 만들어진 연결을 모두 옮겨 적고 유턴(가장 안쪽 차로끼리)을 더한다."""
    for src, dst in UTURN_EXPLICIT:
        e = net.getEdge(src)
        for to_edge, conns in e.getOutgoing().items():
            for c in conns:
                CONNS.append((src, to_edge.getID(), c.getFromLane().getIndex(), c.getToLane().getIndex()))
        CONNS.append((src, dst, _lanes[src] - 1, _lanes[dst] - 1))
    return bool(UTURN_EXPLICIT)


def main():
    write_plain()
    netconvert()
    if fix_uturns(sumolib.net.readNet(P("net.xml"))):
        write_plain()
    warns = netconvert()
    print(f"netconvert 경고 {len(warns)}건")
    for w in warns[:15]:
        print("   ", w.strip()[:170])
    print(f"OSM 선을 못 찾아 직선으로 둔 도로 {len(STRAIGHT)}개: {', '.join(STRAIGHT)}")
    print(f"골목 {N_MINOR}개 엣지 추가, 골목이 붙어 나뉜 핵심 도로 {len(SPLIT)}개")
    net = sumolib.net.readNet(P("net.xml"), withPrograms=True)
    print(f"노드 {len(net.getNodes())}, 엣지 {len(net.getEdges())}, 신호 {len(net.getTrafficLights())}")
    write_sg_tls(net)
    netconvert(P("tls.add.xml"))        # 사거리 신호 계획을 넣어 다시 변환 (통행 우선권을 신호에 맞춤)
    net = sumolib.net.readNet(P("net.xml"), withPrograms=True)
    write_additional(net)
    write_routes(net)
    write_cfg()
    check(int(sys.argv[1]) if len(sys.argv) > 1 else 1800)


if __name__ == "__main__":
    main()
