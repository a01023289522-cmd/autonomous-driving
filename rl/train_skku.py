"""성대역 도로에서 PPO 학습.

    python rl/train_skku.py --config example
    python rl/train_skku.py --config example --timesteps 4096     # 돌아가는지만 확인
결과: results/<설정이름>_<날짜시각>/ (model.pt, config.json, TensorBoard 기록)
"""
import argparse
import json
import os
from datetime import datetime

import course
import config

from algorithms.ppo import PPO  # noqa: E402
from utils.buffer import RolloutBuffer  # noqa: E402
from utils.logger import RunLogger  # noqa: E402

EVAL_INTERVAL, EVAL_EPISODES = 10, 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="base")
    ap.add_argument("--timesteps", type=int)
    a = ap.parse_args()
    cfg = config.load(a.config)
    run_dir = os.path.join(course.TEAM, "results", f"{a.config}_{datetime.now():%m%d_%H%M%S}")
    os.makedirs(run_dir)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    logger = RunLogger(run_dir)
    env = config.make_env(cfg)
    agent = PPO(obs_dim=env.observation_space.shape[0], act_dim=env.action_space.shape[0],
                buffer=RolloutBuffer(), **cfg["hparams"])
    print(f"결과 폴더: {run_dir}\n경로 엣지 {len(env.edges)}개, 시작 {env.edges[0]}, 도착 {env.edges[-1]}")
    try:
        agent.learn(env, total_timesteps=a.timesteps or cfg["total_timesteps"], logger=logger,
                    eval_interval=EVAL_INTERVAL, eval_episodes=EVAL_EPISODES)
    finally:
        env.close()
        logger.close()
        model = os.path.join(run_dir, "model.pt")
        agent.save(model)
        print(f"저장: {model}\n평가: python rl/test_skku.py {os.path.relpath(model, course.TEAM)} --config {a.config} --nogui")


if __name__ == "__main__":
    main()
