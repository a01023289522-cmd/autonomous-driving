"""NW7 데이터에 신호 숫자 칼럼 덧붙이기.
state.traffic_signals의 link_states 문자열에서 AV 경로 연결의 신호색(빨강 0, 노랑 0.5, 초록 1), 현시 번호, 남은 초를
신호 5곳마다 계산해 batch 폴더마다 signals.npz로 저장한다. 원본 파일은 바꾸지 않는다.
    python rl/add_signals.py data/nw7_10m [출력 폴더(기본: 같은 폴더)]
AV 경로 연결 번호: 실제 AV 경로(7754567510 → 9669057440#0, 34구간, traci.vehicle.getRoute)의 엣지 k → k+1을 잇는 신호 연결.
(verify/av_route_full.json은 왕복 경로라 정문에서 나가는 연결 1, 2번이 섞이므로 쓰지 않는다.)"""
import gzip, json, os, sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
TLS = [("hayul", "cluster_495951062_5357160054", [13, 14, 15]),
       ("sageori", "cluster_4650845824_4655421093_4662858740_4662858741_#2more", [1]),
       ("seobu2123", "cluster_1184134292_726912991_837163934", [0]),
       ("ilwol", "cluster_452394408_4871043595", [15, 16, 17]),
       ("gate", "520991292", [10])]
COLOR = {"r": 0.0, "R": 0.0, "u": 0.0, "y": 0.5, "Y": 0.5, "g": 1.0, "G": 1.0, "s": 1.0, "o": 1.0, "O": 1.0}


def one(args):
    src, dst = args
    rows = [json.loads(l) for l in gzip.open(os.path.join(src, "transitions.jsonl.gz"), "rt", encoding="utf-8")]
    out = {"episode": np.array([r["episode"] for r in rows], np.int32), "t": np.array([r["t"] for r in rows], np.int32)}
    for name, tid, links in TLS:
        c, p, m = [], [], []
        for r in rows:
            s = r["state"]["traffic_signals"][tid]
            c.append(max(COLOR.get(s["link_states"][i], 0.0) for i in links)); p.append(s["phase"]); m.append(s["remaining_s"])
        out[f"tls_{name}_color"] = np.array(c, np.float32)
        out[f"tls_{name}_phase"] = np.array(p, np.int16)
        out[f"tls_{name}_remain"] = np.array(m, np.float32)
    os.makedirs(dst, exist_ok=True)
    np.savez_compressed(os.path.join(dst, "signals.npz"), **out)
    return len(rows)


if __name__ == "__main__":
    src = sys.argv[1]; dst = sys.argv[2] if len(sys.argv) > 2 else src
    bs = sorted(d for d in os.listdir(src) if d.startswith("batch-"))
    with ProcessPoolExecutor(min(8, os.cpu_count() or 1)) as ex:
        n = sum(ex.map(one, [(os.path.join(src, b), os.path.join(dst, b)) for b in bs], chunksize=8))
    print("batches", len(bs), "rows", n)
