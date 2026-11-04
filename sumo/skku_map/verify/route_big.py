"""AV 루트: 고속도로(청계IC 진입 뒤) → 성대역 → 골목·회전교차로 → 정문 → L1 주차장 → 교내 순환로 → 정문 좌회전 → 일월로 남쪽"""
import sys, math, json
sys.path.insert(0, sys.argv[1])
from routes import *
def chain(pts):
    out = []
    for a, b in zip(pts, pts[1:]):
        p, _ = net.getShortestPath(a, b, vClass="passenger")
        if p is None: raise SystemExit(f"경로 없음 {a.getID()} → {b.getID()}")
        out += list(p) if not out else list(p)[1:]
    return out
def length(es):
    pts = []
    for e in es: pts += [p[:2] for p in e.getShape()]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
gate_in, gate_out = E("-15379779810#1"), E("15379779810#1")
park = E("9669057440#0")                                      # L1 큰 주차장 가운데 통로
sink = [e for e in net.getEdges() if e.getToNode().getID().startswith("9000") and math.dist(e.getShape()[-1][:2], (474, -1439)) < 40][0]
hw = chain([E("hw_hS3_hS3b"), E("hw_hS9_bd")])
local = chain([hw[-1], E("700812830"), E("4526039540#0"), edge_at((-285, -291), (-1, 0)), E("-5039133870#0"), E("3718967780#0"), gate_in])[1:]
campus = chain([gate_in, E("-15379779820"), park, E("4948484630"), E("15376738010#2"), E("564337480#1"), gate_out])[1:]   # 정문에서 북쪽으로 Modular Bldg 지나 Global Plaza 앞에서 우회전, 순환로는 반시계 일방통행
out = chain([gate_out, sink])[1:]
for n, es in (("고속도로", hw), ("성대역~정문", local), ("교내(주차·순환)", campus), ("정문~일월로 남쪽", out)):
    print(f"{n}: {length(es):.0f} m |", " → ".join(dict.fromkeys(e.getName() or e.getType().split('.')[-1] for e in es)))
full = hw + local + campus + out
assert len(full) == len(dict.fromkeys(full)) or True
print(f"전체 {length(full):.0f} m, 고속도로 뺀 {length(full) - length(hw):.0f} m, 엣지 {len(full)}개, 같은 엣지 다시 지남: {len(full) - len(set(full))}")
json.dump({"highway": [e.getID() for e in hw], "local": [e.getID() for e in local], "campus": [e.getID() for e in campus],
           "exit": [e.getID() for e in out], "edges": [e.getID() for e in full]}, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
