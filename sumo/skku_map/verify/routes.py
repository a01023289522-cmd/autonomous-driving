import sys, warnings, math
warnings.filterwarnings("ignore")
sys.path.append(r"C:\Program Files (x86)\Eclipse\Sumo\tools")
import sumolib
import xml.etree.ElementTree as ET
net = sumolib.net.readNet("skku.net.xml", withPrograms=True)
rbn = set(ET.parse("skku.net.xml").getroot().find("roundabout").get("nodes").split())
tlsn = {n.getID() for n in net.getNodes() if n.getType() == "traffic_light"}
stops = {}
for s in ET.parse("bus.stops.xml").getroot().findall("busStop"):
    stops.setdefault(s.get("lane").rsplit("_", 1)[0], []).append(s.get("name"))
def E(i): return net.getEdge(i)
def edge_at(p, d):
    c = []
    for e, dist in net.getNeighboringEdges(p[0], p[1], 30):
        if not e.allows("passenger"): continue
        sh = e.getShape(); dx = sh[-1][0] - sh[0][0]; dy = sh[-1][1] - sh[0][1]; L = math.hypot(dx, dy) or 1
        if (dx * d[0] + dy * d[1]) / L > 0.6: c.append((dist, e))
    return min(c, key=lambda t: t[0])[1]
def route(pts):
    out = []
    for a, b in zip(pts, pts[1:]):
        p, _ = net.getShortestPath(a, b, vClass="passenger")
        if p is None: raise SystemExit(f"경로 없음 {a.getID()} → {b.getID()}")
        out += p if not out else p[1:]
    return out
def describe(name, edges):
    L = sum(e.getLength() for e in edges)
    tl, rb, rbl, pri, names, bs, lefts = [], 0, 0, 0, [], [], 0
    for a, b in zip(edges, edges[1:]):
        n = a.getToNode()
        if n.getID() in tlsn: tl.append(n.getID())
        if n.getID() in rbn: rb += 1
        if n.getType() == "right_before_left": rbl += 1
        elif n.getType() == "priority" and len(n.getIncoming()) >= 2: pri += 1
        cs = a.getConnections(b)
        if cs and cs[0].getDirection() in ("l", "L"): lefts += 1
    for e in edges:
        if e.getName() and (not names or names[-1] != e.getName()): names.append(e.getName())
        bs += stops.get(e.getID(), [])
    print(f"== {name}: {L:.0f} m")
    print("   길:", " → ".join(names))
    print(f"   신호 교차로 {len(tl)}, 회전교차로 통과 노드 {rb}, 우선순위 없는 교차로 {rbl}, 우선/양보 교차로 {pri}, 좌회전 {lefts}, 버스정류장 {len(bs)}")
    print("   출발/도착 엣지:", edges[0].getID(), "/", edges[-1].getID())
    return edges
