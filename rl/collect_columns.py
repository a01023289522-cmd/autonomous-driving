"""최종 데이터 수집기: 학습한 모델로 성대역 경로를 주행하고 모든 스텝을 CSV로 남긴다.

칼럼은 columns.py에 정의한다. 과제 예시 생성기(make_column_sample.py, 제출 후 삭제)와 다른 점:
  - 끝 8줄만 남기지 않고 에피소드 전체 스텝을 적는다
  - 규칙 정책이 아니라 학습한 모델(PPO 또는 BC)로 주행한다
  - 조건에 맞는 주행을 골라 다시 돌리지 않는다. 정해둔 시드 순서대로 나온 주행을 그대로 적는다

    python -X utf8 rl/collect_columns.py results/base_1115_230752/model.pt --episodes 1
    python -X utf8 rl/collect_columns.py results/.../model.pt --episodes 3 --gui
결과: data/columns_<설정>_<날짜시각>.csv (올리지 않는다. 작업 규칙 5)
"""
import argparse
import csv
import os
from datetime import datetime

import course
import config
import numpy as np

from columns import COLUMNS, step_row  # noqa: E402  칼럼 정의를 한 곳에서만 관리한다
from env import sumo_env  # noqa: E402
from test_skku import course_load_agent  # noqa: E402

# 학습(0~19)·평가(1000~1099)·collect_skku(3000~3499)·칼럼 예시(3000~3023)와 겹치지 않는 시드
COLLECT_SEEDS = list(range(4000, 4100))
traci = sumo_env.traci


def episode_rows(env, agent, episode):
    """한 에피소드를 끝까지 주행하며 스텝마다 한 줄씩 내보낸다."""
    obs, _ = env.reset()
    t = 0
    while True:
        row, next_obs, term, trunc, info = step_row(env, traci, episode, t, obs,
                                                    np.asarray(agent.predict(obs, deterministic=True), dtype=np.float32))
        yield row
        obs, t = next_obs, t + 1
        if term or trunc:
            end = "충돌" if info["collided"] else ("도착" if info["arrived"] else "시간초과")
            print(f"에피소드 {episode}: 시드 {env.seed_now}, {t}스텝, {end}", flush=True)
            return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model", help="학습 결과 폴더의 model.pt")
    ap.add_argument("--config", default="base", help="학습에 쓴 설정 이름과 같게 준다")
    ap.add_argument("--episodes", type=int, default=1)
    ap.add_argument("--out", help="저장할 CSV 경로 (기본 data/columns_<설정>_<날짜시각>.csv)")
    ap.add_argument("--gui", action="store_true", help="주행 화면을 보면서 수집한다")
    a = ap.parse_args()
    cfg = config.load(a.config)
    out = a.out or os.path.join(course.TEAM, "data", f"columns_{a.config}_{datetime.now():%m%d_%H%M%S}.csv")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    env = config.make_env(cfg, gui=a.gui)
    env.use_seeds(COLLECT_SEEDS)
    rows = 0
    try:
        agent = course_load_agent()(a.model, env.observation_space.shape[0], env.action_space.shape[0])
        if isinstance(agent, tuple):
            agent = agent[0]
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(COLUMNS)
            for episode in range(1, a.episodes + 1):
                for row in episode_rows(env, agent, episode):
                    w.writerow(row)
                    rows += 1
                f.flush()
    finally:
        env.close()
    print(f"{rows}줄 저장: {out} ({os.path.getsize(out) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
