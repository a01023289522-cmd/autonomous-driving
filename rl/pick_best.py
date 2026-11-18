"""watch_ckpts.py가 쌓은 20 에피소드 빠른 평가 표에서 학습마다 상위 체크포인트를 골라 100 에피소드로 다시 평가한다.

순위: (충돌 + 시간초과) 적은 순 → 위험 진입 비율 낮은 순 → 스텝 큰 순. 20 에피소드는 운이 크므로 후보를 넉넉히 뽑아 100으로 가른다.

    python -X utf8 rl/pick_best.py results/watch_1118_q2.tsv r_q2c_init_1118_234817 r_q2ct_init_1118_235621 --top 3 --out results/morning_1119.txt
"""
import argparse
import ast
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("table")
    ap.add_argument("runs", nargs="+", help="results 아래 학습 폴더 이름")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--seeds", default="1000-1099")
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--out", default="results/pick_best.txt")
    a = ap.parse_args()
    rows = [l.rstrip("\n").split("\t") for l in open(a.table, encoding="utf-8")][1:]
    picks = []
    for run in a.runs:
        cand = []
        for r in rows:
            if len(r) < 6 or r[1] != run:
                continue
            res = ast.literal_eval(r[3]) if r[3].startswith("{") else {}
            bad = res.get("충돌", 0) + res.get("시간초과", 0) + res.get("기타", 0)
            risky = float(re.search(r"\(([\d.]+)%\)", r[4]).group(1)) if "(" in r[4] else 99
            cand.append((bad, risky, -int(r[2]), r))
        cand.sort()
        picks += [(run, int(c[3][2]), c[3]) for c in cand[:a.top]]
    with open(a.out, "a", encoding="utf-8") as f:
        f.write("후보 (20 에피소드 기준):\n" + "".join(f"  {run} {k}k: {r[3]} 위험 진입 {r[4]}\n" for run, k, r in picks))
    for run, k, _ in picks:
        cfg = __import__("json").load(open(os.path.join("results", run, "config.json"), encoding="utf-8"))["name"]
        model = os.path.join("results", run, f"model_{k}k.pt")
        out = subprocess.run([sys.executable, "-X", "utf8", os.path.join(HERE, "quick_eval.py"), model, "--config", cfg,
                              "--seeds", a.seeds, "--procs", str(a.procs)], capture_output=True, text=True, encoding="utf-8").stdout
        with open(a.out, "a", encoding="utf-8") as f:
            f.write(f"\n== {run} {k}k ({a.seeds})\n" + "".join(l + "\n" for l in out.splitlines() if l.startswith("  ")))
        print(run, k, "끝", flush=True)


if __name__ == "__main__":
    main()
