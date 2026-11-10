"""성대역 도로에서 주행 데이터 수집. 수업의 collect_pomdp_data.py를 환경만 바꿔 그대로 쓴다.

    python rl/collect_skku.py --config example --model results/.../model.pt --episodes 100
    python rl/collect_skku.py --policy keep-lane --episodes 1
결과: data/ (.jsonl, .npz). 수업 스크립트의 나머지 옵션도 그대로 쓸 수 있다. --workers는 1만 지원.
"""
import argparse
import os
import sys

import course
import config

import collect_pomdp_data as collect  # noqa: E402


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--config", default="base")
    a, rest = ap.parse_known_args()
    cfg = config.load(a.config)
    cfg["scenario"]["train_seeds"] = list(range(3000, 3500))   # 학습·평가와 겹치지 않는 시드

    def make(gui=False, **_):
        return config.make_env(cfg, gui=gui)

    collect.SumoHighwayEnv = make
    collect.road_builder.build = lambda *_a, **_k: "skku"
    collect.REWARD = cfg["reward"]
    if "--out-dir" not in rest:
        rest += ["--out-dir", os.path.join(course.TEAM, "data")]
    sys.argv = [sys.argv[0]] + rest
    collect.main()


if __name__ == "__main__":
    main()
