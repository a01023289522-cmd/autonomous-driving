"""학습 폴더를 지켜보다가 새 중간 모델이 나오면 quick_eval.py로 평가해 한 줄 요약을 쌓는다 (밤새 돌리고 아침에 표만 본다).

    python -X utf8 rl/watch_ckpts.py results/<run1> results/<run2> --every 50 --until 1000 --out results/watch.tsv
    (--every: 몇 k 스텝마다 평가할지, --until: 이 k 스텝까지 평가하면 그 폴더는 끝. 폴더마다 다르게 주려면 run:every:until)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def evaluate(model, cfg, seeds, procs):
    out = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "quick_eval.py"), model, "--config", cfg,
                          "--seeds", seeds, "--procs", str(procs)], capture_output=True, text=True, encoding="utf-8").stdout
    get = lambda key: (re.search(rf"  {re.escape(key)}: (.*)", out) or [None, ""])[1]
    return [get(k) for k in ("결과", "위험 진입 비율", "TTC<1초 진입", "시간 간격 위반/1000스텝", "정지선까지 중앙값 m", "실패 위치")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--every", type=int, default=50)
    ap.add_argument("--until", type=int, default=1000)
    ap.add_argument("--seeds", default="1000-1019")
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--out", default="results/watch.tsv")
    a = ap.parse_args()
    plan = {}
    for r in a.runs:
        run, *rest = r.split(":")
        plan[run] = (int(rest[0]) if rest else a.every, int(rest[1]) if len(rest) > 1 else a.until, set())
    if not os.path.exists(a.out):
        with open(a.out, "w", encoding="utf-8") as f:
            f.write("시각\t학습\t스텝(k)\t결과\t위험 진입\tTTC<1초\t간격 위반/1000\t정지선 앞 m\t실패 위치\n")
    while any(max(done, default=0) < until for every, until, done in plan.values()):
        for run, (every, until, done) in plan.items():
            cfg = json.load(open(os.path.join(run, "config.json"), encoding="utf-8"))["name"]
            for k in range(every, until + 1, every):
                path = os.path.join(run, f"model_{k}k.pt")
                if k in done or not os.path.exists(path):
                    continue
                time.sleep(5)                       # 저장이 끝나도록
                row = evaluate(path, cfg, a.seeds, a.procs)
                done.add(k)
                with open(a.out, "a", encoding="utf-8") as f:
                    f.write("\t".join([time.strftime("%H:%M"), os.path.basename(run), str(k), *row]) + "\n")
                print(os.path.basename(run), k, row[:3], flush=True)
            if not os.path.exists(os.path.join(run, "config.json")):
                continue
            # 학습이 끝났는데(model.pt) 더 나올 중간 모델이 없으면 그 폴더는 끝
            if os.path.exists(os.path.join(run, "model.pt")):
                plan[run] = (every, max(done, default=0), done)
        time.sleep(30)


if __name__ == "__main__":
    main()
