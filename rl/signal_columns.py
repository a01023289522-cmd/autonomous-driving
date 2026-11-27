"""공개 데이터의 신호 정보를 숫자 칼럼으로 바꾼다 (11/17 공지: 신호는 {R,Y,G} 대신 {0, 0.5, 1}, 신호 칼럼은 차원을 쪼개어).

수집기(collect_nw7.py)는 state.traffic_signals[신호ID].link_states에 SUMO 문자열("GGGgrrr")을 그대로 저장했다.
이 스크립트는 저장된 값만 규칙대로 바꾸며, 시뮬레이션을 다시 돌리지 않는다.

  JSONL (transitions.jsonl.gz)
    - state·next_state 안 traffic_signals[신호ID].link_states(문자열) → link_colors(연결마다 숫자: 빨강 0, 노랑 0.5, 초록 1)
    - 행마다 숫자 칼럼 17개 추가 (경로 순서)
        tls_<이름>_color  : AV 경로 방향 신호색 0 / 0.5 / 1 (경로 위 신호 5곳)
        tls_<이름>_phase  : 현재 현시 번호 (신호 6곳)
        tls_<이름>_remain : 현시가 바뀌기까지 남은 시간 s (신호 6곳)
  NPZ (transitions.npz) : 같은 17개를 signals (N, 17) float32 배열로 추가
  metadata.json         : signal_columns(칼럼 이름 순서) 추가, bytes 갱신

AV 경로 방향 연결 번호는 fc472d0 도로망(sumo/skku_map/skku.net.xml)에서 경로 엣지 k → k+1을 잇는 신호 연결로 찾았다.
공개 데이터의 교통 시드(4000~)는 학습 시드가 아니라 AV는 항상 전체 경로(start_edge~goal_edge)를 달린다.

  사용: python -X utf8 rl/signal_columns.py 입력.zip 출력.zip [바꿔 넣을 README.md]
"""
import gzip
import io
import json
import sys
import zipfile

import numpy as np

COLOR = {"r": 0.0, "y": 0.5, "g": 1.0, "G": 1.0}

# 이름: (신호 ID, AV 경로 방향 연결 번호). 경로 순서. 연결 번호가 없으면 경로 밖 신호라 색 칼럼을 두지 않는다
SIGNALS = {
    "hayul":     ("cluster_495951062_5357160054", [13, 14, 15]),   # 서부로×하률로 (출발 직후)
    "sageori":   ("cluster_4650845824_4655421093_4662858740_4662858741_#2more", [1]),  # 성대역 사거리
    "seobu2123": ("cluster_1184134292_726912991_837163934", [0]),  # 서부로×서부로2123번길 (골목 진입)
    "ilwol":     ("cluster_452394408_4871043595", [15, 16, 17]),   # 율전로64번길×일월로
    "gate":      ("520991292", [10]),                              # 일월로×학교 정문
    "seobu2105": ("cluster_4637428747_495943443", []),             # 서부로×서부로2105번길 (경로 밖)
}
COLUMNS = ([f"tls_{n}_color" for n, (_, links) in SIGNALS.items() if links]
           + [f"tls_{n}_{k}" for k in ("phase", "remain") for n in SIGNALS])


def link_colors(text):
    return [COLOR[ch] for ch in text]   # 모르는 글자가 있으면 KeyError로 멈춘다


def convert_state(state):
    for sig in state["traffic_signals"].values():
        sig["link_colors"] = link_colors(sig.pop("link_states"))
        sig["remaining_s"] = round(float(sig["remaining_s"]), 1)


def columns(state):
    ts = state["traffic_signals"]
    values = {}
    for name, (tid, links) in SIGNALS.items():
        sig = ts[tid]
        if links:
            values[f"tls_{name}_color"] = max(sig["link_colors"][i] for i in links)
        values[f"tls_{name}_phase"] = int(sig["phase"])
        values[f"tls_{name}_remain"] = sig["remaining_s"]
    return {c: values[c] for c in COLUMNS}


def convert_batch(jsonl_gz, npz_bytes):
    out, rows = [], []
    for line in gzip.decompress(jsonl_gz).decode("utf-8").splitlines():
        r = json.loads(line)
        convert_state(r["state"])
        if "next_state" in r:
            convert_state(r["next_state"])
        cols = columns(r["state"])
        rows.append([cols[c] for c in COLUMNS])
        new = {}
        for k, v in r.items():
            if k == "next_observation":
                new.update(cols)
            new[k] = v
        if "next_observation" not in r:
            new.update(cols)
        out.append(json.dumps(new, ensure_ascii=False, separators=(",", ":")))
    jsonl = gzip.compress(("\n".join(out) + "\n").encode("utf-8"), compresslevel=6, mtime=0)
    with np.load(io.BytesIO(npz_bytes), allow_pickle=False) as d:
        arrays = {k: d[k] for k in d.files}
    if len(arrays["episode"]) != len(rows):
        raise ValueError("JSONL 행 수와 NPZ 행 수가 다르다")
    arrays["signals"] = np.asarray(rows, dtype=np.float32)
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    return jsonl, buf.getvalue(), len(rows)


def main(src, dst, readme=None):
    zin = zipfile.ZipFile(src)
    names = zin.namelist()
    batches = sorted({n.rsplit("/", 1)[0] for n in names if n.endswith("/metadata.json")})
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            if "/batch-" not in n:
                info = zin.getinfo(n)
                body = zin.read(n)
                if readme and n.lower().endswith("readme.md"):
                    body = open(readme, "rb").read()   # 신호 칼럼 설명을 더한 README로 바꾼다
                zout.writestr(info, body)
        for i, b in enumerate(batches):
            meta = json.loads(zin.read(f"{b}/metadata.json"))
            jsonl, npz, count = convert_batch(zin.read(f"{b}/transitions.jsonl.gz"), zin.read(f"{b}/transitions.npz"))
            if count != meta["transitions"]:
                raise ValueError(f"{b}: transition 수 {count} != metadata {meta['transitions']}")
            meta["signal_columns"] = COLUMNS
            meta["bytes"] = {"transitions.jsonl.gz": len(jsonl), "transitions.npz": len(npz)}
            zout.writestr(f"{b}/metadata.json", json.dumps(meta, ensure_ascii=False, indent=2) + "\n", zipfile.ZIP_STORED)
            zout.writestr(f"{b}/transitions.npz", npz, zipfile.ZIP_STORED)
            zout.writestr(f"{b}/transitions.jsonl.gz", jsonl, zipfile.ZIP_STORED)
            if i % 20 == 0 or i == len(batches) - 1:
                print(f"{i + 1}/{len(batches)} {b}", flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
