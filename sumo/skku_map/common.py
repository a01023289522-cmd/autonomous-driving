"""여러 단계가 같이 쓰는 도우미: 경로, netconvert 실행, 꺾은선 계산, 교차로 면 모양."""
import math
import os
import subprocess
import sys

SUMO_HOME = os.environ.get("SUMO_HOME", r"C:\Program Files (x86)\Eclipse\Sumo")
sys.path.append(os.path.join(SUMO_HOME, "tools"))
from sumolib import checkBinary  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def P(name):
    """이 폴더 안의 파일 경로 (시뮬레이션에 쓰는 최종 파일)."""
    return os.path.join(HERE, name)


def W(name):
    """만드는 도중의 파일 경로: work/ (중간 도로망·수정 파일·로그. 저장소에 올리지 않는다)."""
    os.makedirs(os.path.join(HERE, "work"), exist_ok=True)
    return os.path.join(HERE, "work", name)


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


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def offset_fn(ref, f, s0, s1, step=6.0):
    """꺾은선 ref의 길이 s0~s1 구간을, 각 지점 s에서 진행 방향 오른쪽으로 f(s) m 옮긴 점들 (s1 < s0이면 거꾸로)."""
    L = sum(math.dist(a, b) for a, b in zip(ref, ref[1:]))
    s0, s1 = max(0.0, min(L, s0)), max(0.0, min(L, s1))
    n = max(2, int(abs(s1 - s0) / step))
    out = []
    for k in range(n + 1):
        s = s0 + (s1 - s0) * k / n
        a, b = poly_point(ref, max(0.0, s - 1)), poly_point(ref, min(L, s + 1))
        ux, uy = unit(b[0] - a[0], b[1] - a[1])
        x, y = poly_point(ref, s)
        out.append((x + uy * f(s), y - ux * f(s)))
    return out


def curb_shape(node, min_len=0.5):
    """교차로 면을 실제 교차로처럼: 갈래 길마다 차로 끝의 양쪽 가장자리(연석) 두 점을 잡고, 이웃 갈래끼리는
    두 연석선을 교차로 안쪽으로 늘여 만나는 점을 꼭짓점으로 하는 곡선(모서리 깎기)으로 잇는다.
    두 연석선이 거의 나란하면(같은 길의 두 방향, 분리대) 곧게 잇는다."""
    pts = []                                              # (점, 교차로 안쪽을 향하는 방향)
    for e, at_end in [(e, True) for e in node.getIncoming()] + [(e, False) for e in node.getOutgoing()]:
        if e.getLength() < min_len:                       # 길이 0에 가까운 토막은 방향이 엉터리
            continue
        lanes = e.getLanes()
        for ln, side in ((lanes[0], -1), (lanes[-1], 1)):
            sh = [p[:2] for p in ln.getShape()]
            a, b = (sh[-2], sh[-1]) if at_end else (sh[1], sh[0])
            ux, uy = unit(b[0] - a[0], b[1] - a[1])
            w = ln.getWidth() / 2 * side * (1 if at_end else -1)
            pts.append(((b[0] - uy * w, b[1] + ux * w), (ux, uy), e.getID()))
    cx, cy = sum(p[0] for p, _, _ in pts) / len(pts), sum(p[1] for p, _, _ in pts) / len(pts)
    pts.sort(key=lambda t: math.atan2(t[0][1] - cy, t[0][0] - cx))
    out = []
    for (p, dp, ep), (q, dq, eq) in zip(pts, pts[1:] + pts[:1]):
        out.append(p)
        if ep == eq:
            continue
        den = dp[0] * dq[1] - dp[1] * dq[0]               # 두 연석선 p + t·dp, q + s·dq 의 교점
        if abs(den) < 0.2:
            continue
        t = ((q[0] - p[0]) * dq[1] - (q[1] - p[1]) * dq[0]) / den
        s = ((q[0] - p[0]) * dp[1] - (q[1] - p[1]) * dp[0]) / den
        if 0 < t < 40 and 0 < s < 40:
            out += curve([p, (p[0] + dp[0] * t, p[1] + dp[1] * t), q], n=6)[1:-1]
    return out


def fmt(pts):
    return " ".join(",".join(f"{c:.2f}" for c in p) for p in pts)


def netconvert(args, log):
    r = subprocess.run([checkBinary("netconvert"), *args, "--log", W(log)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])


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


def lane_z(ln):
    return ln.getShape3D()[0][2]
