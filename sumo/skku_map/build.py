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

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))
import sumolib  # noqa: E402
from sumolib import checkBinary  # noqa: E402

import osm_clip  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda name: os.path.join(HERE, name)
OSM = [P("../skku_area/skku.osm.xml"), P("../skku_schematic/skku_se.osm.xml"), P("../skku_schematic/skku_ne.osm.xml")]
PROJ = "+proj=tmerc +lat_0=37.30055 +lon_0=126.97268 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"

# 구현 범위 (사용자가 지도에 그린 범위, 조금 넉넉하게)
AREA = [(-60, 345), (300, 350), (600, 345), (650, 200), (620, 60), (735, -160), (870, -395), (1025, -550),
        (1165, -825), (1200, -1060), (1065, -1170), (945, -1235), (670, -1345), (470, -1435), (230, -1350),
        (-20, -1290), (-215, -1270), (-460, -1070), (-540, -830), (-570, -530), (-520, -240), (-460, -40),
        (-320, 65), (-140, 240)]

# 카카오맵 길찾기로 확인한 일방통행 (OSM에는 양방향): 길 10%→90%, 30%→70% 두 번 다 한쪽만 바로 갈 수 있는 길
#   "yes" = OSM 길 방향으로만, "-1" = 반대 방향으로만 (route_check.py 결과)
#   경로 좌표로 다시 확인한 결과는 kakao_verified.txt. 화산로·만석로20번길·정자천로·일월로는 카카오가 출발·도착점을
#   옆 차로에 붙여 '돌아감'으로 나온 오판이라 뺐다 (길을 지나 긴 경로를 찍으면 양방향 모두 그 길을 지난다)
KAKAO_ONEWAY = {"383153390": "yes",   # 덕영대로535번길
                "3921803060": "yes"}  # 화산로125번길

# 지도로 확인한 위치 (원점 = 사거리, x 동쪽, y 북쪽)
SAGEORI = (0, -5)
GAPS = {"G1": (-30, -133), "G2": (-118, -266), "G3": (-197, -440)}          # 서부로 고가 밑 갈림목
SB, NB = (-0.3, -0.95), (0.3, 0.95)                                          # 서부로 고가 구간 진행 방향
# 유턴 (카카오맵 길찾기 확인): (위치, 들어오는 방향)
#   G2 북행, G3 북행·남행, 서부로×일월로 남행, 덕영대로 만석로 교차로 동행, 서부로×하률로 북행(사거리에서는 유턴 불가)
UTURNS = [(GAPS["G2"], NB), (GAPS["G3"], NB), (GAPS["G3"], SB), ((-250, -1080), (0, -1)), ((815, -672), (0.6, -0.8)),
          ((24, 273), (0.1, 1))]
# 막힌 캠퍼스 출입구 (사용자 확인 + 카카오 길찾기: 밖→안 경로가 2 km 넘게 돌아 정문으로 들어감) → 차량 통행 금지
CLOSED_GATES = {"700813270": "후문 (성대후문 정류장 옆)", "420073550": "서쪽 문 (서부로 쪽)"}
# 고가 가운데선 (OSM 고가 두 방향 선의 가운데)
CL = [(0, 0), (0, -25), (-6, -68), (-26, -127), (-39, -154), (-60, -188), (-91, -226), (-118, -266),
      (-138, -298), (-153, -326), (-169, -358), (-185, -396), (-197, -433), (-205, -465), (-221, -536),
      (-230, -598), (-234, -660), (-241, -797)]

# 서부로 고가(밤밭고가): 사거리에서 시작해 철길 위 다리를 지나 삼성아파트 앞까지 끊김 없이 한 방향 2차로씩 (위성사진 2+2).
#   OSM에는 철길 위 ~ G1 구간이 4차로로 적혀 두 방향이 서로 겹쳐 있었다 → 고가 가운데선(CL)에서 분리대 1 m를 두고
#   양쪽 2차로로 다시 그린다. 철길 위에서는 고가 바깥에 지상으로 내려가는 1차로가 맞닿아 붙는다 (한 덩어리 넓은 다리).
#   (사거리 쪽 엣지 → 남쪽 끝 엣지 순서, 중간 노드)
VIA_SB = ["6003174920", "6003174900", "4883925510"]
VIA_NB = ["4948457660", "6003174910", "6003174890"]
RAMP_SB, RAMP_NB = ("700812830", "4807018640"), ("4883933160", "4807018641")   # 다리 위 지상 내려가는 길 (엣지, 끝 노드)
VIA_S = (70, 135)                                           # OSM 중간 노드 위치 (CL 길이): 철길 남쪽 끝, G1 근처
GAP = 3.0               # 고가 양옆 지상 서부로를 고가에서 일부러 띄우는 거리 (m): 화면에서 다른 층으로 보이게 (사용자 지정 2026-11-02)
# 고가 밑 공영주차장 입구 (카카오맵 장소의 '입구' 좌표): P1 율전제3공영, P2 율전공영(다리밑). P3(율전 제2공영)은 로드뷰로 남쪽 끝
LOT_IN = {"P1": (-85, -237), "P2": (-140, -280)}


# ── 작은 도우미 ──────────────────────────────────────────────
def unit(dx, dy):
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L


def heading(edge, at_end):
    sh = [p[:2] for p in edge.getShape()]
    (x0, y0), (x1, y1) = (sh[-2], sh[-1]) if at_end else (sh[0], sh[1])
    return unit(x1 - x0, y1 - y0)


def junction_near(net, p, min_edges=3):
    cands = [n for n in net.getNodes() if len(n.getIncoming()) + len(n.getOutgoing()) >= min_edges]
    return min(cands, key=lambda n: math.dist(n.getCoord()[:2], p))


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


def square_shape(node, chamfer=2.5):
    """교차로 면을 도로 방향에 맞춘 직사각형(모서리만 조금 깎음)으로. 네 방향 길이 서로 거의 직각인 교차로에서
    netconvert가 만든 비뚤어진 면 대신 쓰면 정지선이 도로와 직각으로 가지런해진다 (노드 shape → 엣지가 그 면에서 잘림,
    userdoc/Networks/PlainXML.html). 남북 축 = 남북으로 드나드는 길 방향의 평균, 크기 = 원래 면을 감싸는 범위."""
    ds = [heading(e, True) for e in node.getIncoming()] + [heading(e, False) for e in node.getOutgoing()]
    ns = [(x, y) if y > 0 else (-x, -y) for x, y in ds if abs(y) > abs(x)]
    u = unit(sum(d[0] for d in ns), sum(d[1] for d in ns))          # 북쪽
    v = (u[1], -u[0])                                                 # 동쪽
    cx, cy = node.getCoord()[:2]
    pts = [p[:2] for p in node.getShape()]
    a = [(p[0] - cx) * u[0] + (p[1] - cy) * u[1] for p in pts]
    b = [(p[0] - cx) * v[0] + (p[1] - cy) * v[1] for p in pts]
    a0, a1, b0, b1 = min(a), max(a), min(b), max(b)
    c = chamfer
    corners = [(a1, b0 + c), (a1, b1 - c), (a1 - c, b1), (a0 + c, b1), (a0, b1 - c), (a0, b0 + c), (a0 + c, b0), (a1 - c, b0)]
    return [(cx + p * u[0] + q * v[0], cy + p * u[1] + q * v[1]) for p, q in corners]


def side_line(pts, d):
    """꺾은선을 진행 방향 왼쪽(+)으로 d m 옮긴 선 (꼭짓점에서는 앞뒤 점 방향)."""
    out = []
    for i, p in enumerate(pts):
        a, b = pts[max(0, i - 1)], pts[min(len(pts) - 1, i + 1)]
        ux, uy = unit(b[0] - a[0], b[1] - a[1])
        out.append((p[0] - uy * d, p[1] + ux * d))
    return out


def dashes(pts, on, off):
    """꺾은선을 on m 칠하고 off m 비우는 토막들로."""
    L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    out, s = [], 0.0
    while s < L:
        e = min(L, s + on)
        k = [poly_point(pts, s)] + [p for p in pts if s < poly_project(pts, p) < e] + [poly_point(pts, e)]
        out.append(k)
        s += on + off
    return out


def poly_point(pts, s):
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        if acc + L >= s:
            t = (s - acc) / L
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        acc += L
    return pts[-1]


def poly_project(pts, p):
    best, acc = (1e18, 0.0), 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.dist(a, b)
        t = max(0.0, min(1.0, ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (L * L)))
        d = math.dist(p, (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        best = min(best, (d, acc + t * L))
        acc += L
    return best[1]



def offset_line(pts, d, s0, s1, step=10.0):
    """꺾은선 pts의 길이 s0~s1 구간을 진행 방향 오른쪽으로 d m 옮긴 점들 (s1 < s0이면 거꾸로)."""
    L = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    s0, s1 = max(0.0, min(L, s0)), max(0.0, min(L, s1))
    n = max(1, int(abs(s1 - s0) / step))
    out = []
    for k in range(n + 1):
        s = s0 + (s1 - s0) * k / n
        a, b = poly_point(pts, max(0.0, s - 1)), poly_point(pts, min(L, s + 1))
        ux, uy = unit(b[0] - a[0], b[1] - a[1])
        x, y = poly_point(pts, s)
        out.append((x + uy * d, y - ux * d))
    return out

def corridor_moves(net, cl):
    """고가 양옆을 나란히 달리는 지상 엣지를 고가 가운데선(cl)에서 GAP만큼 바깥으로 옮긴 모양 {엣지: 점들}."""
    L = sum(math.dist(a, b) for a, b in zip(cl, cl[1:]))
    out = {}
    for e in net.getEdges():
        if (e.getID() in (RAMP_SB[0], RAMP_NB[0], *VIA_SB, *VIA_NB)
                or abs(e.getShape()[0][2] if len(e.getShape()[0]) > 2 else 0) > 3):
            continue
        sh = [p[:2] for p in e.getShape()]
        ss = [poly_project(cl, p) for p in sh]
        near = [math.dist(p, poly_point(cl, s)) for p, s in zip(sh, ss)]
        if not (max(near) < 22 and min(ss) > 1 and max(ss) < L - 1 and math.dist(sh[0], sh[-1]) > 3):
            continue
        a, b = poly_point(cl, ss[0]), poly_point(cl, ss[-1])
        if abs(sum(x * y for x, y in zip(unit(sh[-1][0] - sh[0][0], sh[-1][1] - sh[0][1]),
                                         unit(b[0] - a[0], b[1] - a[1])))) < 0.85:
            continue                                      # 가로지르는 길은 그대로
        moved = []
        for p, s, d in zip(sh, ss, near):
            q = poly_point(cl, s)
            moved.append((p[0] + (p[0] - q[0]) / d * GAP, p[1] + (p[1] - q[1]) / d * GAP) if d > 1 else p)
        out[e.getID()] = moved
    return out


def road_cut(net, moved, p, d):
    """점 p에서 가장 가까운, d 방향으로 달리는 지상 서부로 엣지와 그 위의 길이 (양 끝 4 m는 피함)."""
    best = None
    for e in net.getEdges():
        if e.getName() != "서부로" or e.getID() in (RAMP_SB[0], RAMP_NB[0], *VIA_SB, *VIA_NB) or abs(lane_z(e.getLanes()[0])) > 3:
            continue
        sh = moved.get(e.getID()) or [q[:2] for q in e.getShape()]
        L = sum(math.dist(a, b) for a, b in zip(sh, sh[1:]))
        s = poly_project(sh, p)
        a, b = poly_point(sh, max(0.0, s - 2)), poly_point(sh, min(L, s + 2))
        if L < 10 or sum(x * y for x, y in zip(unit(b[0] - a[0], b[1] - a[1]), d)) < 0.7:
            continue
        dist = math.dist(p, poly_point(sh, s))
        if best is None or dist < best[0]:
            best = (dist, e.getID(), max(4.0, min(L - 4.0, s)))
    return best[1], best[2]


def fmt(pts):
    return " ".join(",".join(f"{c:.2f}" for c in p) for p in pts)


def netconvert(args, log):
    r = subprocess.run([checkBinary("netconvert"), *args, "--log", P(log)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])


# ── 1·2) OSM 자르기 + 불러오기 ───────────────────────────────────
def import_osm():
    osm_clip.clip(OSM, AREA, P("clip.osm.xml"), KAKAO_ONEWAY)
    # 사거리는 OSM에서 일방통행 링크 네 개가 만든 '상자' 모양이라 하나의 교차로로 합친다
    import xml.etree.ElementTree as ET
    root = ET.parse(P("clip.osm.xml")).getroot()
    use = {}
    for w in root.findall("way"):
        for nd in w.findall("nd"):
            use[nd.get("ref")] = use.get(nd.get("ref"), 0) + 1
    box = [n.get("id") for n in root.findall("node") if use.get(n.get("id"), 0) >= 2
           and abs(osm_clip.xy(float(n.get("lat")), float(n.get("lon")))[0]) < 22
           and -30 < osm_clip.xy(float(n.get("lat")), float(n.get("lon")))[1] < 20]
    with open(P("join.nod.xml"), "w", encoding="utf-8") as f:
        f.write(f'<nodes>\n    <join nodes="{" ".join(box)}"/>\n</nodes>\n')
    netconvert(["--osm-files", P("clip.osm.xml"), "-n", P("join.nod.xml"),
                "--type-files", os.path.join(SUMO_HOME, "data", "typemap", "osmNetconvert.typ.xml") + "," + P("skku.typ.xml"),
                "-o", P("pass1.net.xml"), "--proj", PROJ, "--offset.disable-normalization", "true",
                # SUMO 권장 옵션 (userdoc/Networks/Import/OpenStreetMap.html)
                "--geometry.remove", "--junctions.join", "--tls.guess-signals", "--tls.discard-simple", "--tls.join",
                # 교차로 끝의 급한 꺾임을 펴서 찌그러짐·화살표 오류 방지
                "--geometry.min-radius.fix", "--junctions.corner-detail", "5",
                "--remove-edges.isolated", "--keep-edges.components", "1",
                "--no-turnarounds.except-deadend", "true",
                "--default.lanewidth", "3.2", "--output.street-names", "true",
                "--ptstop-output", P("pt.stops.xml"), "--ptline-output", P("pt.lines.xml")], "pass1.log")
    return sumolib.net.readNet(P("pass1.net.xml"))


# ── 3) 수정 파일 ────────────────────────────────────────────
TOLL_BOOTHS = 10        # 의왕TG 한 방향 부스 수 (요금소는 실제 크기로, 줄인 것은 직선 구간뿐)
MERGE_AT = {"hS1", "hS3", "hS5", "hN4", "hN2"}      # 진입로가 바깥 차로(0번)로 합류하는 곳 (가속 차로)


def curve(pts, n=8):
    """꺾은선 → 부드러운 곡선 (꼭짓점 사이 가운데점을 잇는 2차 베지에, 끝점은 그대로). 3차원 점(z)도 그대로 보간."""
    if len(pts) < 3:
        return pts
    mids = [tuple((a + b) / 2 for a, b in zip(p, q)) for p, q in zip(pts, pts[1:])]
    out = [pts[0]]
    for k in range(1, len(pts) - 1):
        a, c, b = (pts[0] if k == 1 else mids[k - 1]), pts[k], (pts[-1] if k == len(pts) - 2 else mids[k])
        for i in range(1, n + 1):
            t = i / n
            out.append(tuple((1 - t) ** 2 * x + 2 * (1 - t) * t * y + t * t * z for x, y, z in zip(a, c, b)))
    return out


def plaza(y_from, booth=40, sign=-1):
    """요금소: 3차로가 한 번에 부드럽게 부스 수만큼 넓어지고(깔때기 모양 교차로 면), 부스 구간(40 km/h), 다시 3차로로 좁아진다.
    반환: [(노드 이름 뒤 번호, 그 노드에서 시작하는 구간의 y, 차로 수, km/h)], 끝 y (sign=-1 남쪽 방향, +1 북쪽 방향)"""
    t = taper_len(3, TOLL_BOOTHS)
    y0 = y_from + sign * t / 2                       # 넓어지는 깔때기 가운데
    y1 = y0 + sign * (t / 2 + booth + t / 2)         # 좁아지는 깔때기 가운데
    return [("0", y0, TOLL_BOOTHS, 40), ("1", y1, 3, 80)], y1 + sign * t / 2


def taper_len(n1, n2):
    """차로 수가 바뀌는 깔때기 길이: 차로 하나당 16 m (최소 40 m)."""
    return max(40.0, 16.0 * abs(n2 - n1))


def smooth(t):
    return t * t * (3 - 2 * t)


HW_LEAD = 350           # 고속도로 남쪽 끝: 서부로 북쪽 끝에서 서부로 방향 그대로 뻗는 길이 (그 뒤 곧게 북쪽으로)


def highway(sb_end, nb_start, north):
    """봉담과천로(사당 방면) 축소판. 실제 순서(카카오맵 길찾기·로드뷰 확인):
    과천 → 학의JC(합류) → 청계IC(진출·진입) → 의왕휴게소 → 의왕TG(톨게이트) → 서부로 → 사거리.
    본선 한 방향 3차로(로드뷰). 직선 구간만 줄였고 요금소는 실제처럼 부스 수만큼 넓어졌다 줄어든다.
    차로 수가 바뀌는 곳은 교차로 면을 깔때기 모양(노드 shape, userdoc/Networks/PlainXML.html)으로 만들어
    계단 없이 매끄럽게 넓어지고 좁아진다. 중앙분리대 쪽 가장자리는 곧게 두고 바깥쪽만 벌어진다.
    남쪽 끝은 서부로 북쪽 끝(구현 범위 경계 노드)에 그대로 이어진 일자 도로 (사용자 지정: 연결부는 사실적일 필요 없이
    일자 고속도로 역할만). 예전 의왕IC·서부로 연결로는 뺐다.
    sb_end / nb_start: (서부로 노드 id, (x, y)), north: 서부로 북쪽 방향 단위 벡터.
    반환: 노드 {이름: (x, y)}, 엣지, 차로 연결, 노드 모양 {이름: [(x, y)...]}, zipper 노드"""
    # 본선은 x = 상수인 세로선. 서부로 끝에서 north 방향으로 HW_LEAD 간 점의 x를 쓰고, 아래 좌표(램프 등)는 남쪽 방향 x = -258
    # 기준으로 적은 뒤 마지막에 통째로 옮긴다
    a_s = (sb_end[1][0] + north[0] * HW_LEAD, sb_end[1][1] + north[1] * HW_LEAD)
    a_n = (nb_start[1][0] + north[0] * HW_LEAD, nb_start[1][1] + north[1] * HW_LEAD)
    dx = a_s[0] + 258
    xs, xn = -258, -258 + (a_n[0] - a_s[0])
    W = 3.2

    def x_of(base, lanes, sgn):          # sgn: 남쪽 방향은 바깥이 서쪽(-), 북쪽 방향은 동쪽(+)
        return base + sgn * (lanes - 3) * W / 2

    nodes, E, shapes, zipper = {}, [], {}, set()

    C = []   # 본선 차로 연결 (from, to, fromLane, toLane): 0번이 가장 오른쪽(바깥) 차로

    def funnel(base, sgn, dy, yb, n1, n2):
        """차로 n1 → n2로 바뀌는 깔때기 모양 교차로 면 (가운데 yb, 진행 방향 dy = ±1)."""
        t = taper_len(n1, n2)
        inner = base - sgn * 1.5 * W
        outer = lambda n: base + sgn * (n - 1.5) * W
        side = [(outer(n1) + (outer(n2) - outer(n1)) * smooth(k / 10), yb - dy * t / 2 + dy * t * k / 10)
                for k in range(11)]
        return [(inner, side[0][1])] + side + [(inner, side[-1][1])]

    def chain(points, base, sgn, dy):
        """points: [(노드 이름, y, 이 노드에서 시작하는 구간 차로 수, km/h)] 차례로 잇는다.
        진입로 합류(MERGE_AT)는 바깥쪽(0번)에 가속 차로가 생긴다(기존 i → i+1).
        그 밖에 차로 수가 바뀌는 곳은 깔때기 교차로: 크게 바뀌면(요금소) 차로를 고르게 나눠 잇고,
        한 차로만 줄면 바깥 두 차로(0·1번)가 0번으로 합쳐진다. 줄어드는 곳은 zipper 교차로(번갈아 끼어들기,
        userdoc/Networks/PlainXML.html): 보통 교차로로 두면 합류 차로가 정지선에서 긴 깔때기 끝까지 비기를 기다려 막힌다."""
        segs = list(zip(points, points[1:]))
        for (a, ya, n, v), (b, yb, _, _) in segs:
            xa = x_of(base, n, sgn)
            E.append((f"hw_{a}_{b}", a, b, n, v, [(xa, ya), (xa, yb)]))
        for ((a, _, n1, _), (b, yb, _, _)), ((_, _, n2, _), (c, _, _, _)) in zip(segs, segs[1:]):
            e1, e2 = f"hw_{a}_{b}", f"hw_{b}_{c}"
            if n2 == n1:
                C.extend((e1, e2, i, i) for i in range(n1))
                continue
            if b in MERGE_AT:
                C.extend((e1, e2, i, i + n2 - n1) for i in range(n1))
                continue
            shapes[b] = funnel(base, sgn, dy, yb, n1, n2)
            if abs(n2 - n1) > 1:                            # 요금소: 차로를 고르게 나눠 펼치고 모은다
                lo, hi = min(n1, n2), max(n1, n2)
                pairs = [(j * lo // hi, j) for j in range(hi)]
                C.extend((e1, e2, i, j) if n2 > n1 else (e1, e2, j, i) for i, j in pairs)
            elif n2 > n1:
                C.extend((e1, e2, i, i + 1) for i in range(n1))
                C.append((e1, e2, 0, 0))
            else:
                C.extend((e1, e2, i, max(i - 1, 0)) for i in range(n1))
            if n2 < n1:
                zipper.add(b)
        for name, y, _, _ in points:
            nodes[name] = (base, y)

    # 남쪽 방향(사당 → 봉담)
    sb = [("hS0", 5600, 3, 90), ("hS1", 4400, 4, 90), ("hS1b", 4100, 3, 90), ("hS2", 3600, 3, 90),
          ("hS3", 3300, 4, 90), ("hS3b", 3100, 3, 90), ("hS4", 2700, 3, 90), ("hS5", 2450, 4, 90), ("hS5b", 2300, 3, 80)]
    steps, _ = plaza(2250, sign=-1)
    sb += [(f"hT{k}", y0, n, v) for k, y0, n, v in steps]
    sb += [("hS8", 1400, 3, 90), ("hS9", 1000, 3, 60), (sb_end[0], 0, 3, 60)]
    chain(sb, xs, -1, -1)
    # 북쪽 방향(봉담 → 사당)
    nb = [(nb_start[0], 0, 3, 60), ("hN9", 1000, 3, 90), ("hN8", 1400, 3, 90), ("hY2", 1720, 3, 80)]
    steps, _ = plaza(1750, sign=+1)
    nb += [(f"hU{k}", y0, n, v) for k, y0, n, v in steps]
    nb += [("hN5", 2450, 3, 90), ("hN4", 2700, 4, 90), ("hN4b", 2800, 3, 90),
           ("hN3", 3300, 3, 90), ("hN2", 3600, 4, 90), ("hN2b", 3800, 3, 90), ("hN1", 4400, 3, 90), ("hN0", 5600, 3, 90)]
    chain(nb, xn, +1, +1)
    # 이름 맞추기 (서부로와 잇는 끝 엣지: hw_hS9_bd, hw_bd_hN9)
    ren = {f"hw_hS9_{sb_end[0]}": "hw_hS9_bd", f"hw_{nb_start[0]}_hN9": "hw_bd_hN9"}
    E = [(ren.get(e, e), a, b, n, v, s) for e, a, b, n, v, s in E]
    C = [(ren.get(f, f), ren.get(t, t), i, j) for f, t, i, j in C]

    def lead_in(end, anchor, top):
        """서부로 끝 → anchor까지 서부로 방향 그대로 곧게 → 부드럽게 꺾여 → (본선 x, top)까지 곧게. 남쪽 방향 차례."""
        ax, ay = anchor[0] - dx, anchor[1]
        p0 = (end[0] - dx, end[1])
        v = (ax + (p0[0] - ax) * 120 / HW_LEAD, ay + (p0[1] - ay) * 120 / HW_LEAD)
        return curve([(ax, top), (ax, ay + 120), (ax, ay), v, p0], n=12)
    E = [(e, a, b, n, v, lead_in(sb_end[1], a_s, 1000) if e == "hw_hS9_bd"
          else lead_in(nb_start[1], a_n, 1000)[::-1] if e == "hw_bd_hN9" else s) for e, a, b, n, v, s in E]
    nodes.pop(sb_end[0])
    nodes.pop(nb_start[0])

    def ramp(eid, a, b, via, lanes, kmh):
        E.append((eid, a, b, lanes, kmh, curve([nodes[a], *via, nodes[b]])))

    nodes |= {"hJCs": (-700, 4800), "hJCn": (100, 4700),              # 학의JC (북행 진출은 오른쪽=동쪽으로)
              "hCGo": (250, 3450), "hCGi": (250, 3750),               # 청계IC 동쪽
              "hCGo2": (-650, 3450), "hCGi2": (-650, 3150),           # 청계IC 서쪽
              "hRs1": (-330, 2650), "hRs2": (-330, 2500), "hRn1": (-170, 2500), "hRn2": (-170, 2650)}  # 휴게소
    ramp("hw_jc_in", "hJCs", "hS1", [(-450, 4650), (-300, 4480)], 1, 60)
    ramp("hw_jc_out", "hN1", "hJCn", [(-215, 4500), (-120, 4640)], 1, 60)
    ramp("hw_cg_out", "hS2", "hCGo2", [(-285, 3520), (-420, 3460)], 1, 50)
    ramp("hw_cg_in", "hCGi2", "hS3", [(-420, 3170), (-285, 3240)], 1, 50)
    ramp("hw_cg_out2", "hN3", "hCGo", [(-215, 3380), (60, 3440)], 1, 50)
    ramp("hw_cg_in2", "hCGi", "hN2", [(60, 3740), (-215, 3660)], 1, 50)
    ramp("hw_rest_s_in", "hS4", "hRs1", [(-290, 2670)], 1, 40)
    ramp("hw_rest_s", "hRs1", "hRs2", [], 1, 20)
    ramp("hw_rest_s_out", "hRs2", "hS5", [(-290, 2470)], 1, 40)
    ramp("hw_rest_n_in", "hN5", "hRn1", [(-210, 2480)], 1, 40)
    ramp("hw_rest_n", "hRn1", "hRn2", [], 1, 20)
    ramp("hw_rest_n_out", "hRn2", "hN4", [(-210, 2680)], 1, 40)
    # 진입로 → 본선 바깥 차로(0번), 본선 바깥 차로 → 진출로
    after = {a: e for e, a, b, n, v, s in E if e.startswith("hw_h") and not e.startswith(("hw_hR",))}
    for ramp_id, node in (("hw_jc_in", "hS1"), ("hw_cg_in", "hS3"), ("hw_rest_s_out", "hS5"),
                          ("hw_rest_n_out", "hN4"), ("hw_cg_in2", "hN2")):
        C.append((ramp_id, after[node], 0, 0))
    before = {b: e for e, a, b, n, v, s in E if e.startswith("hw_h")}
    for ramp_id, node in (("hw_cg_out", "hS2"), ("hw_rest_s_in", "hS4"), ("hw_cg_out2", "hN3"),
                          ("hw_rest_n_in", "hN5"), ("hw_jc_out", "hN1")):
        C.append((before[node], ramp_id, 0, 0))
    C += [("hw_rest_s_in", "hw_rest_s", 0, 0), ("hw_rest_s", "hw_rest_s_out", 0, 0),
          ("hw_rest_n_in", "hw_rest_n", 0, 0), ("hw_rest_n", "hw_rest_n_out", 0, 0)]
    # 서부로와 잇는 끝: 서부로 차로 그대로 (i → i)
    C += [("hw_hS9_bd", "_sb", i, i) for i in range(3)] + [("_nb", "hw_bd_hN9", i, i) for i in range(3)]
    # 통째로 옮기기
    mv = lambda pts: [(p[0] + dx, *p[1:]) for p in pts]
    nodes = {k: (x + dx, y) for k, (x, y) in nodes.items()}
    E = [(e, a, b, n, v, mv(s)) for e, a, b, n, v, s in E]
    shapes = {k: mv(s) for k, s in shapes.items()}
    return nodes, E, C, shapes, zipper


def write_patches(net):
    nod, edg, con = [], [], []
    # 신호 교차로 (사거리 + 고가 밑 갈림목 G1·G2·G3 + 서부로×일월로 + 서부로×하률로: 기존 모델과 동일)
    sg = junction_near(net, SAGEORI)
    for p in (*GAPS.values(), (-250, -1080), (24, 273)):
        nod.append(f'<node id="{junction_near(net, p).getID()}" type="traffic_light"/>')
    nod.append(f'<node id="{sg.getID()}" shape="{fmt(square_shape(sg))}"/>')

    touched = set()                                       # 새 길이 붙는 기존 교차로 → 연결을 다시 계산 (reset)

    # 고가 옆 지상 서부로(양쪽)를 고가에서 GAP만큼 바깥으로 띄운다: 화면에서 고가와 다른 층이라는 게 보이도록 (사용자 지정)
    cl = CL + [(-244, -850)]
    moved = corridor_moves(net, cl)
    # 고가 밑 공영주차장 3곳 (카카오맵 장소 좌표·'입구' 표시 + 사용자 로드뷰 사진 2026-10-29). 통로는 고가 밑 가운데,
    #   들고 나는 곳은 양옆 지상 서부로를 그 자리에서 잘라 붙인다 (신호 교차로로 바로 드나들면 신호 계획에 칸이 없어 막힌다)
    #   P1 율전제3공영 (G1~G2): G2 북쪽 북행 도로에서 좌회전으로 들어가(카카오 입구, 로드뷰) 북쪽으로 → G1 앞 북행 도로로 우회전 (출구는 미확인)
    #   P2 율전공영(다리밑) (G2~G3): G2 남쪽 남행 도로에서 좌회전으로 들어가(카카오 입구) 남쪽으로 → G3 지나 남행 도로로 (로드뷰 '출구전용·좌회전 금지')
    #   P3 율전 제2공영 (G3 남쪽): 남쪽 끝에서 남행 도로 좌회전으로 들어가(로드뷰) 북쪽으로 → G3 남쪽 북행 도로로 우회전 (로드뷰, 차단기)
    S = {k: poly_project(CL, p) for k, p in GAPS.items()}
    s1, s2 = poly_project(CL, LOT_IN["P1"]), poly_project(CL, LOT_IN["P2"])
    #       (주차장, 통로 시작 s, 통로 끝 s, 입구 쪽 도로 방향·도로 위 s, 출구 쪽 도로 방향·도로 위 s)
    lots = [("P1", s1, S["G1"] + 25, (NB, s1 + 10), (NB, S["G1"] + 15)),
            ("P2", s2, S["G3"] - 25, (SB, s2 - 10), (SB, S["G3"] + 25)),
            ("P3", S["G3"] + 200, S["G3"] + 30, (SB, S["G3"] + 195), (NB, S["G3"] + 22))]
    cuts = {}                                             # 도로 엣지 → [(엣지 위 길이, 새 노드)]
    lot_shapes, lot_edges = {}, []
    for lot, a_s, b_s, (d_in, r_in), (d_out, r_out) in lots:
        a, b = poly_point(CL, a_s), poly_point(CL, b_s)
        nod += [f'<node id="{lot}i" x="{a[0]:.2f}" y="{a[1]:.2f}"/>', f'<node id="{lot}o" x="{b[0]:.2f}" y="{b[1]:.2f}"/>']
        aisle = [poly_point(CL, a_s + (b_s - a_s) * k / 10) for k in range(11)]
        lot_shapes[lot] = aisle
        for tag, d, r in (("e", d_in, r_in), ("x", d_out, r_out)):
            eid, s = road_cut(net, moved, poly_point(CL, r), d)
            cuts.setdefault(eid, []).append((s, f"{lot}{tag}"))
        lot_edges += [f'<edge id="{lot}_in" from="{lot}e" to="{lot}i" numLanes="1" speed="5.56" allow="taxi"/>',
                      f'<edge id="{lot}_aisle" from="{lot}i" to="{lot}o" numLanes="1" speed="4.17" allow="taxi" '
                      f'shape="{fmt(aisle)}"/>',
                      f'<edge id="{lot}_out" from="{lot}o" to="{lot}x" numLanes="1" speed="5.56" priority="1" allow="taxi"/>']
    edg += lot_edges
    deleted = set(cuts)
    for eid in sorted(set(moved) | set(cuts)):
        e = net.getEdge(eid)
        sh = moved.get(eid) or [p[:2] for p in e.getShape()]
        if eid not in cuts:
            edg.append(f'<edge id="{eid}" shape="{fmt(sh)}"/>')
            continue
        # 엣지를 자른 점마다 노드를 두고 조각 엣지로 다시 만든다 (차로·속도·허용 차종은 그대로)
        perm = " ".join(sorted(e.getLanes()[0].getPermissions()))
        common = (f'numLanes="{e.getLaneNumber()}" speed="{e.getSpeed():.2f}" priority="{e.getPriority()}" allow="{perm}" '
                  f'name="{e.getName()}" spreadType="center"')     # OSM 일방 도로와 같게 (빠뜨리면 차로가 한 칸 옆으로 밀린다)
        marks = sorted(cuts[eid])
        ends = [e.getFromNode().getID()] + [n for _, n in marks] + [e.getToNode().getID()]
        pos = [0.0] + [s for s, _ in marks] + [None]
        for (s, n) in marks:
            # 교차로 면은 도로 방향에 맞춘 폭 2 m 직사각형 (그대로 두면 비스듬히 붙는 주차장 길 때문에 면이 비뚤어져 정지선이 계단처럼 보였다)
            m = poly_point(sh, s)
            ux, uy = unit(*[q - p for p, q in zip(poly_point(sh, s - 1), poly_point(sh, s + 1))])
            w = e.getLaneNumber() * 3.2 / 2 + 0.2
            box = [(m[0] + ux * a - uy * b, m[1] + uy * a + ux * b) for a, b in ((-1, -w), (1, -w), (1, w), (-1, w))]
            nod.append(f'<node id="{n}" x="{m[0]:.2f}" y="{m[1]:.2f}" type="priority" shape="{fmt(box)}"/>')
        edg.append(f'<delete id="{eid}"/>')
        for k in range(len(ends) - 1):
            lo, hi = pos[k], pos[k + 1] if pos[k + 1] is not None else 1e9
            piece = ([poly_point(sh, lo)] + [p for p in sh if lo + 0.5 < poly_project(sh, p) < hi - 0.5]
                     + [poly_point(sh, min(hi, sum(math.dist(p, q) for p, q in zip(sh, sh[1:]))))])
            edg.append(f'<edge id="{eid}_{"abcdefg"[k]}" from="{ends[k]}" to="{ends[k + 1]}" {common} shape="{fmt(piece)}"/>')
            con.append(f'<connection from="{eid}_{"abcdefg"[k]}" reset="true"/>')
        touched |= {e.getFromNode().getID(), e.getToNode().getID()}
    fixed = set(moved) | {f"{eid}_{c}" for eid in cuts for c in "abcdefg"}
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
    con += [f'<connection from="{f}" to="{t}" fromLane="{i}" toLane="{j}"/>' for f, t, i, j in hc]
    # 차로 수가 바뀌는 점(요금소·가속 차로 끝)은 깔때기 모양 교차로 면
    nod += [f'<node id="{n}" x="{x}" y="{y}"' + (f' shape="{fmt(hshape[n])}"' if n in hshape else "")
            + (' type="zipper"' if n in hzip else "") + '/>' for n, (x, y) in hn.items()]
    for eid, a, b, lanes, kmh, shape in he:
        sh = f' shape="{fmt(shape)}"' if shape else ""
        if eid.startswith(("hw_h", "hw_bd")):               # 본선: 가운데선 양쪽으로 차로를 펼친다 (깔때기 모양과 맞춤)
            sh += ' spreadType="center"'
        edg.append(f'<edge id="{eid}" from="{a}" to="{b}" numLanes="{lanes}" speed="{kmh / 3.6:.2f}" '
                   f'priority="13"{sh}/>')
    new_in = {"P1_out", "P2_out", "P3_out", "hw_hS9_bd"}
    # 고속도로가 이어지는 서부로 북쪽 끝 옆 골목들이 구현 범위 경계에서 잘려 끊긴 채 보이던 것 → 경계에 닿는 짧은 막다른 길은 뺀다
    for eid in north_stubs(net):
        edg.append(f'<delete id="{eid}"/>')
    for nid in touched:
        for e in net.getNode(nid).getIncoming():
            if e.getID() not in deleted and e.getID() not in VIA_SB + VIA_NB:
                con.append(f'<connection from="{e.getID()}" reset="true"/>')
    con += [f'<connection from="{e}" reset="true"/>' for e in sorted(new_in)]
    # 서부로 고가: 가운데선에서 분리대 1 m + 2차로(남쪽 방향은 서쪽, 북쪽 방향은 동쪽), 높이 6 m로 끊김 없이.
    #   철길 위(s 0~70)에서는 바깥에 지상으로 내려가는 1차로가 맞닿아 붙는다 (높이 0으로 두어 고가와 색으로 구분)
    cl = CL + [(-244, -850)]
    L = sum(math.dist(a, b) for a, b in zip(cl, cl[1:]))
    half = 0.5 + 3.2                                        # 분리대 반 + 차로 하나 = 2차로 엣지 가운데선
    for ids in (VIA_SB, VIA_NB, RAMP_SB, RAMP_NB):
        for i in ids:
            if not (net.hasEdge(i) or net.hasNode(i)):
                raise SystemExit(f"서부로 고가 구성 요소를 못 찾음: {i} (OSM이 바뀌었으면 VIA_* 다시 확인)")
    sb_end = poly_project(cl, net.getEdge(VIA_SB[-1]).getToNode().getCoord()[:2])
    nb_end = poly_project(cl, net.getEdge(VIA_NB[0]).getFromNode().getCoord()[:2])
    # OSM은 고가를 방향마다 세 토막(사거리~철길 남쪽 끝~G1~남쪽 끝)으로 나눴는데, 중간 노드 둘은 OSM에서 다른 길과
    # 겹쳐 있어 dead_end로 잡혀 고가가 거기서 끊겨 있었고(연결 없음), 이어 붙여도 노드 자리에 줄이 남는다
    # → 방향마다 사거리에서 남쪽 끝까지 엣지 하나(via_sb, via_nb)로 다시 만든다
    first, last = net.getEdge(VIA_SB[0]), net.getEdge(VIA_SB[-1])
    common = (f'numLanes="2" speed="{first.getSpeed():.2f}" priority="{first.getPriority()}" type="{first.getType()}" '
              f'name="서부로" spreadType="center"')
    sh = offset_line(cl, half, 0, sb_end)
    edg += [f'<delete id="{e}"/>' for e in VIA_SB + VIA_NB]
    edg.append(f'<edge id="via_sb" from="{first.getFromNode().getID()}" to="{last.getToNode().getID()}" {common} '
               f'shape="{fmt([(x, y, 6) for x, y in sh])}"/>')
    first, last = net.getEdge(VIA_NB[0]), net.getEdge(VIA_NB[-1])
    sh = offset_line(cl, -half, nb_end, 0)
    edg.append(f'<edge id="via_nb" from="{first.getFromNode().getID()}" to="{last.getToNode().getID()}" {common} '
               f'shape="{fmt([(x, y, 6) for x, y in sh])}"/>')
    fixed |= {"via_sb", "via_nb", *VIA_SB, *VIA_NB}
    for nid in (net.getEdge(VIA_SB[0]).getFromNode().getID(), net.getEdge(VIA_SB[-1]).getToNode().getID(),
                net.getEdge(VIA_NB[0]).getFromNode().getID()):    # 새 엣지가 붙는 교차로: 연결 다시 계산
        con += [f'<connection from="{e.getID()}" reset="true"/>' for e in net.getNode(nid).getIncoming()
                if e.getID() not in VIA_SB + VIA_NB]
    ramp_off = 0.5 + 6.4 + 1.6 + GAP                      # 고가 2차로 바깥 1차로 가운데선 (다른 지상도로처럼 GAP만큼 띄움)
    for (eid, nid), d, s0, s1 in ((RAMP_SB, ramp_off, 0, VIA_S[0]), (RAMP_NB, -ramp_off, VIA_S[0], 0)):
        sh = offset_line(cl, d, s0, s1)
        end = sh[-1] if s1 else sh[0]
        nod.append(f'<node id="{nid}" x="{end[0]:.2f}" y="{end[1]:.2f}"/>')
        edg.append(f'<edge id="{eid}" shape="{fmt([(x, y, 0) for x, y in sh])}"/>')
        fixed.add(eid)
    # 고가·다리(+6 m)와 지하차도(-6 m) 높이: OSM layer 태그가 있는 길만. 화면에서 높이별 색으로 겹친 도로를 구분 (skku.gui.xml)
    #   (netconvert --osm.layer-elevation은 이웃 길까지 경사로 높이를 퍼뜨리고 사거리 같은 합친 교차로 전체를 띄워 쓰지 않음)
    #   엣지가 여러 OSM 길을 합쳐 만들어지기도 해서, 엣지 모양의 대부분이 OSM 고가·지하차도 선과 3 m 안에서 겹치는지로 판단
    import xml.etree.ElementTree as ET
    root = ET.parse(P("clip.osm.xml")).getroot()
    npos = {n.get("id"): osm_clip.xy(float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
    layered, under = [], []
    for w in root.findall("way"):
        z = next((int(t.get("v")) for t in w.findall("tag") if t.get("k") == "layer"), 0)
        if z:
            layered.append((z, [npos[r.get("ref")] for r in w.findall("nd")]))
    for e in net.getEdges():
        if e.getID() in fixed or e.getLength() < 20:        # 직접 그린 고가, 고가 밑 짧은 연결로(유턴 등)는 제외
            continue
        sh = [p[:2] for p in e.getShape()]
        pts = [poly_point(sh, d) for d in range(0, int(sum(math.dist(a, b) for a, b in zip(sh, sh[1:]))) + 1, 5)] or sh
        for z, line in layered:
            near = sum(1 for p in pts if sumolib.geomhelper.distancePointToPolygon(p, line) < 3)
            if near >= 0.6 * len(pts):
                edg.append(f'<edge id="{e.getID()}" shape="{fmt([(x, y, 6 * z) for x, y in sh])}"/>')
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
        if e.getID() not in fixed and e.getLength() < 40 and len(sh) > 2 and any(crosses(sh, u) for u in under):
            ins = [i for i in e.getFromNode().getIncoming() if i.getFromNode() != e.getToNode()]
            arc = [sh[0], sh[-1]]
            if ins:
                d = heading(max(ins, key=lambda i: i.getLength()), True)
                arc = curve([sh[0], (sh[0][0] + d[0] * 6, sh[0][1] + d[1] * 6),
                             (sh[-1][0] + d[0] * 6, sh[-1][1] + d[1] * 6), sh[-1]], n=6)
            edg.append(f'<edge id="{e.getID()}" shape="{fmt(arc)}"/>')
    # 막힌 캠퍼스 출입구: 길은 남기되(사람만 통행) 차는 못 지나가게
    for wid in CLOSED_GATES:
        for e in net.getEdges():
            if e.getID().lstrip("-").split("#")[0] == wid:
                edg.append(f'<edge id="{e.getID()}" allow="pedestrian"/>')

    for name, rows, tag in (("patch.nod.xml", nod, "nodes"), ("patch.edg.xml", edg, "edges"),
                            ("patch.con.xml", con, "connections")):
        with open(P(name), "w", encoding="utf-8") as f:
            f.write(f"<{tag}>\n" + "".join(f"    {r}\n" for r in rows) + f"</{tag}>\n")
    return sg.getID(), lot_shapes


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
    with open(P("rules.con.xml"), "w", encoding="utf-8") as f:
        f.write("<connections>\n" + "".join(f"    {r}\n" for r in con) + "</connections>\n")
    netconvert(["-s", P("pass2.net.xml"), "-x", P("rules.con.xml"), "-o", P("pass2.net.xml"),
                "--offset.disable-normalization", "true", "--tls.rebuild", "true"], "pass2b.log")   # 주차장 출구까지 신호에 넣어 다시 계산
    return sumolib.net.readNet(P("pass2.net.xml"), withPrograms=True), len(con)


def apply_patches():
    netconvert(["-s", P("pass1.net.xml"), "-n", P("patch.nod.xml"), "-e", P("patch.edg.xml"), "-x", P("patch.con.xml"),
                "-o", P("pass2.net.xml"), "--offset.disable-normalization", "true", "--junctions.corner-detail", "5",
                "--no-turnarounds.except-deadend", "true"], "pass2.log")
    return sumolib.net.readNet(P("pass2.net.xml"), withPrograms=True)


def lot_exit_programs(net):
    """고가 밑 공영주차장 출구(P*_out)가 신호 교차로로 들어가는데 netconvert가 만든 신호 계획에는 그 출구 칸이 없어('o')
    끝없이 틈을 기다린다 → 같은 방향으로 나란히 들어오는 지상 서부로 신호를 따라 양보 녹색(g)을 준다."""
    out = []
    for tls in net.getTrafficLights():
        conns = tls.getConnections()
        exits = [(lane, to, i) for lane, to, i in conns if lane.getEdge().getID().endswith("_out")]
        if not exits or not tls.getPrograms():
            continue
        pid, prog = next(iter(tls.getPrograms().items()))
        phases = [[ph.duration, list(ph.state)] for ph in prog.getPhases()]
        for lane, to, j in exits:
            hx, hy = heading(lane.getEdge(), True)
            cands = [(sum(a * b for a, b in zip(heading(l.getEdge(), True), (hx, hy))), i)
                     for l, t, i in conns if not l.getEdge().getID().endswith("_out") and t.getEdge() == to.getEdge()]
            cands = cands or [(sum(a * b for a, b in zip(heading(l.getEdge(), True), (hx, hy))), i)
                              for l, t, i in conns if not l.getEdge().getID().endswith("_out")]
            p = max(cands)[1]
            for ph in phases:
                ph[1][j] = "g" if ph[1][p] in "Gg" else "y" if ph[1][p] == "y" else "r"
        out.append(f'    <tlLogic id="{tls.getID()}" type="static" programID="{pid}" offset="0">\n'
                   + "".join(f'        <phase duration="{d:.0f}" state="{"".join(s)}"/>\n' for d, s in phases)
                   + "    </tlLogic>\n")
    return out


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
    with open(P("sageori.tll.xml"), "w", encoding="utf-8") as f:
        f.write(f'<tlLogics>\n    <tlLogic id="{sg_id}" type="static" programID="0" offset="0">\n'
                f'        <phase duration="70" state="{green}"/>\n        <phase duration="3" state="{"y" * n}"/>\n'
                f'        <phase duration="45" state="{"r" * n}"/>\n    </tlLogic>\n')
        f.writelines(lot_exit_programs(net))
        f.write('</tlLogics>\n')
    netconvert(["-s", P("pass2.net.xml"), "-i", P("sageori.tll.xml"), "-o", P("skku.net.xml"),
                "--offset.disable-normalization", "true"], "pass3.log")
    return sumolib.net.readNet(P("skku.net.xml"), withPrograms=True)


# ── 4) 정류장·주차장·화면 ───────────────────────────────────────
def toll_booths(net):
    """요금소 모양: 부스 구간(시속 40 km) 차로 사이에 부스 섬(회색), 위에 반투명 지붕."""
    rows = []
    for e in net.getEdges():
        if not e.getID().startswith(("hw_hT", "hw_hU")) or e.getSpeed() > 12:
            continue
        lanes = [[p[:2] for p in ln.getShape()] for ln in e.getLanes()]
        (x0, y0), (x1, y1) = lanes[0][0], lanes[0][-1]
        ux, uy = unit(x1 - x0, y1 - y0)
        L = math.dist((x0, y0), (x1, y1))
        mid = [((ln[0][0] + ln[-1][0]) / 2, (ln[0][1] + ln[-1][1]) / 2) for ln in lanes]
        for k in range(len(mid) + 1):              # 차로 사이 + 양 끝 바깥쪽
            if k == 0:
                c = (2 * mid[0][0] - mid[1][0] + mid[0][0], 2 * mid[0][1] - mid[1][1] + mid[0][1])
                c = ((mid[0][0] + c[0]) / 2, (mid[0][1] + c[1]) / 2)
            elif k == len(mid):
                c = ((mid[-1][0] * 3 - mid[-2][0]) / 2, (mid[-1][1] * 3 - mid[-2][1]) / 2)
            else:
                c = ((mid[k - 1][0] + mid[k][0]) / 2, (mid[k - 1][1] + mid[k][1]) / 2)
            hl, hw = L * 0.35, 0.6
            box = [(c[0] + ux * a - uy * b, c[1] + uy * a + ux * b) for a, b in ((-hl, -hw), (hl, -hw), (hl, hw), (-hl, hw))]
            rows.append(f'    <poly id="booth_{e.getID()}_{k}" type="요금소 부스" color="150,150,155" fill="1" layer="5" '
                        f'shape="{fmt(box + box[:1])}"/>\n')
        a, b = mid[0], mid[-1]
        span = math.dist(a, b) / 2 + 3
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        roof = [(cx + ux * s1 * 6 - uy * s2 * span, cy + uy * s1 * 6 + ux * s2 * span) for s1, s2 in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        rows.append(f'    <poly id="roof_{e.getID()}" type="의왕TG 지붕" color="80,110,160,90" fill="1" layer="6" '
                    f'shape="{fmt(roof + roof[:1])}"/>\n')
    return rows


# 층 표현 (사용자 지정: 겹치는 곳에서는 높이(z)가 낮은 도로가 뒤쪽에, 낮은 층의 도로와 차는 옅게. 방안 A~D 화면 비교 후 'B 지도식' 선택)
#   sumo-gui는 도로망(차로·교차로 면)을 모두 같은 층(layer 0)에 그려 높이로 앞뒤를 가릴 수 없다
#   (userdoc/Simulation/Shapes.html "The network itself is drawn as layer 0").
#   → 보기 설정에서 고가(+3 m 넘음)·지하차도(-3 m 밑) 차로는 투명하게 두고, 그 두 층은 도형으로 직접 그린다.
#     지하차도 면: layer -0.5, 옅은 도로색 (배경 위, 도로망 밑 → 지상 도로·교차로 면에 가려짐)
#     지하차도 차선: layer 3.2 점선 (지상 도로·교차로 면 위로 비쳐 보이는 '숨은 선')
#     고가: 그림자 layer 15 + 불투명 면 15.5 + 진한 테두리·차선 15.6~15.8.
#       (layer 3.5에 두었더니 신호 교차로 면이 고가 위에 그려져 G1~G3에서 고가가 끊겨 보였다: 화면 확인 → 15로 올림)
#   차량은 도형보다 항상 위에 그려진다 → 아래층(지하차도, 고가 밑)의 차는 view_skku.py가 TraCI로 반투명하게 칠한다
BG_COLOR = (238, 236, 230)
ROAD_COLOR = (62, 62, 66)
UNDER_COLOR = ROAD_COLOR + (120,)          # 지하차도 면: 도로색을 바탕 위에 옅게 (불투명으로 변환해 씀)
UNDER_LINE = "95,95,100,230"
VIA_COLOR = (92, 100, 178)                # 고가 면 (불투명)
VIA_EDGE = "30,32,70"                     # 고가 테두리
VIA_SHADOW = "0,0,0,70"
VIA_LINE = "255,255,255,210"


def blend(c):
    a = c[3] / 255
    return ",".join(str(round(a * x + (1 - a) * b)) for x, b in zip(c[:3], BG_COLOR))


def lane_z(ln):
    return ln.getShape3D()[0][2]


def layer_shapes(net):
    rows = []
    poly = lambda pid, kind, color, layer, pts, fill=True, lw=0.0: rows.append(
        f'    <poly id="{pid}" type="{kind}" color="{color}" fill="{int(fill)}" layer="{layer}"'
        + ("" if fill else f' lineWidth="{lw}"') + f' shape="{fmt(pts)}"/>\n')
    via = ",".join(map(str, VIA_COLOR))
    for e in net.getEdges():
        lanes = e.getLanes()
        z = lane_z(lanes[0])
        if -3 <= z <= 3:
            continue
        sh = [[p[:2] for p in ln.getShape()] for ln in lanes]
        right = side_line(sh[0], -lanes[0].getWidth() / 2)
        left = side_line(sh[-1], lanes[-1].getWidth() / 2)
        if z < -3:
            poly(f"under_{e.getID()}", "지하차도", blend(UNDER_COLOR), -0.5, left + right[::-1])
            lines = [left, right] + [side_line(s, ln.getWidth() / 2) for s, ln in zip(sh[:-1], lanes[:-1])]
            for i, ln_pts in enumerate(lines):
                for k, d in enumerate(dashes(ln_pts, 1.5, 1.5)):
                    poly(f"under_{e.getID()}_l{i}_{k}", "지하차도 (숨은 선)", UNDER_LINE, 3.2, d, False, 0.25)
        else:
            outline = left + right[::-1]
            poly(f"via_{e.getID()}_sh", "고가 그림자", VIA_SHADOW, 15.0, [(x + 1.6, y - 1.6) for x, y in outline])
            poly(f"via_{e.getID()}", "고가", via, 15.5, outline)
            poly(f"via_{e.getID()}_bl", "고가 테두리", VIA_EDGE, 15.6, left, False, 0.6)
            poly(f"via_{e.getID()}_br", "고가 테두리", VIA_EDGE, 15.6, right, False, 0.6)
            for i, (s, ln) in enumerate(zip(sh[:-1], lanes[:-1])):
                for k, d in enumerate(dashes(side_line(s, ln.getWidth() / 2), 3, 5)):
                    poly(f"via_{e.getID()}_l{i}_{k}", "고가 차선", VIA_LINE, 15.8, d, False, 0.15)
    # 같은 층 엣지끼리만 만나는 노드의 교차로 면 (보기 설정에서 교차로 면은 지상 색이라 그 위를 같은 층 색으로 덮는다)
    for n in net.getNodes():
        es = n.getIncoming() + n.getOutgoing()
        if len(n.getShape()) < 3 or not es:
            continue
        zs = [lane_z(e.getLanes()[0]) for e in es]
        if all(z > 3 for z in zs):
            poly(f"via_j_{n.getID()}", "고가", via, 15.4, [p[:2] for p in n.getShape()])
        elif all(z < -3 for z in zs):
            poly(f"under_j_{n.getID()}", "지하차도", blend(UNDER_COLOR), -0.5, [p[:2] for p in n.getShape()])
    return rows


def write_additional(net):
    """주차장(parking.py) · 휴게소 · 지명 표시. 반환: 주차장별 parkingArea id 목록."""
    import json
    import parking
    rows, groups = parking.build(net, OSM, AREA, [tuple(p) for p in json.load(open(P("campus_poly.json")))])
    with open(P("skku.add.xml"), "w", encoding="utf-8") as f:
        f.write("<additional>\n")
        f.writelines(rows)
        for rest, lane in (("RS", "hw_rest_s_0"), ("RN", "hw_rest_n_0")):
            f.write(f'    <parkingArea id="{rest}" lane="{lane}" startPos="5" endPos="-5" roadsideCapacity="25" angle="45" '
                    f'name="의왕휴게소" friendlyPos="true"/>\n')
        dx = net.getNode("hS8").getCoord()[0] + 258                  # 고속도로를 옮긴 만큼 (highway())
        for pid, (x, y), text in (("sg", (25, 10), "SKKU Stn. Intersection"),
                                  ("tg", (-345 + dx, 2000), "Uiwang TG (toll)"),
                                  ("rest", (-330 + dx, 2580), "Uiwang rest area"), ("jc", (-258 + dx, 4400), "Hakui JC"),
                                  ("cg", (-258 + dx, 3450), "Cheonggye IC")):
            f.write(f'    <poi id="lbl_{pid}" type="{text}" x="{x + 15}" y="{y}" color="0,0,0,0" layer="100"/>\n')
        f.writelines(toll_booths(net))
        f.writelines(layer_shapes(net))
        f.write("</additional>\n")
    # 화면 설정 (userdoc/sumo-gui.html): 지상 차로만 진회색으로 그리고, 고가·지하차도 차로는 투명 ("by height at start").
    #   고가·지하차도는 layer_shapes()의 도형으로 층에 맞게 그린다. (예전 '지상만'·'고가만' 보기는 도형을 숨길 수 없어 뺐다)
    # 차는 실제 크기의 자동차 모양(simple shapes, 크기 고정 안 함)
    def scheme(name, under, ground, up):
        return (f'    <scheme name="{name}">\n        <background backgroundColor="238,236,230" showGrid="0"/>\n'
                f'        <edges laneEdgeMode="21" laneShowBorders="1">\n'
                f'            <colorScheme name="by height at start" interpolated="0">'
                f'<entry color="{under}" threshold="-100.00"/><entry color="{ground}" threshold="-3.00"/>'
                f'<entry color="{up}" threshold="3.00"/></colorScheme>\n        </edges>\n'
                f'        <junctions junctionMode="0"><colorScheme name="uniform"><entry color="{ground}"/>'
                f'<entry color="150,200,200" name="waterway"/><entry color="invisible" name="railway"/>'
                f'<entry color="200,240,240" name="airway"/></colorScheme></junctions>\n'   # 교차로 면도 도로와 같은 색
                '        <vehicles vehicleMode="0" vehicleQuality="2" vehicle_minSize="1.00" vehicle_exaggeration="1.00" '
                'vehicle_constantSize="0" showBlinker="1"/>\n'
                '        <pois poiType_show="1" poiType_size="55" poiType_color="45,45,60" poiType_constantSize="1"/>\n'
                '    </scheme>\n')
    with open(P("skku.gui.xml"), "w", encoding="utf-8") as f:
        f.write('<viewsettings>\n'
                + scheme("skku", "0,0,0,0", "62,62,66,255", "0,0,0,0")
                + '    <delay value="100"/>\n</viewsettings>\n')   # 한 스텝(0.2 s)마다 0.1 s 쉼 = 실제의 2배 빠르기
    return groups


# ── 5) 교통 ────────────────────────────────────────────────
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
    write_trip_weights(net, P("trip_w"))
    subprocess.run([sys.executable, os.path.join(SUMO_HOME, "tools", "randomTrips.py"), "-n", P("skku.net.xml"),
                    "-o", P("random.trips.xml"), "-b", "0", "-e", "3600", "-p", "3.0", "--weights-prefix", P("trip_w"),
                    "--min-distance", "300", "--seed", "42", "--edge-permission", "passenger", "--validate",
                    "-a", P("vtypes.add.xml"),
                    "--trip-attributes", 'type="car" departLane="best"', "--prefix", "r"],
                   capture_output=True, text=True, check=True)
    root = ET.parse(P("random.trips.xml")).getroot()
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


def check(seeds=(42, 1, 2)):
    for seed in seeds:
        r = subprocess.run([checkBinary("sumo"), "-c", P("skku.sumocfg"), "--seed", str(seed), "--no-step-log",
                            "--duration-log.statistics", "--no-warnings"], capture_output=True, text=True)
        keep = [ln.strip() for ln in (r.stdout + r.stderr).splitlines()
                if ln.strip().startswith(("Inserted", "Teleports", "Collisions", "TimeLoss", "Error"))]
        print(f"seed {seed}: " + " | ".join(keep))


def main():
    net1 = import_osm()
    sg_id, lot_shapes = write_patches(net1)
    apply_patches()
    net2, _ = turn_rules(sumolib.net.readNet(P("pass2.net.xml")))
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
