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
    ap.add_argument("--init", help="이어서 학습할 model.pt (커리큘럼·추가 학습). 관측 차원이 같아야 한다")
    ap.add_argument("--ckpt-every", type=int, default=50000, help="이 스텝마다 중간 모델 model_<k>k.pt 저장 (0이면 안 함). quick_eval.py로 중간 판단")
    ap.add_argument("--no-train-eval", action="store_true",
                    help="학습 중 3 에피소드 평가를 끈다 (판단에 쓰기엔 적고 시뮬레이션 시간의 약 15%%를 쓴다)")
    a = ap.parse_args()
    cfg = config.load(a.config)
    run_dir = os.path.join(course.TEAM, "results", f"{a.config}{'_init' if a.init else ''}_{datetime.now():%m%d_%H%M%S}")
    os.makedirs(run_dir)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    logger = RunLogger(run_dir)
    if a.ckpt_every > 0:     # 수업 코드(algorithms/ppo.py)는 그대로 두고, 업데이트마다 불리는 로거에서 중간 모델을 저장한다
        log_train, last = logger.log_train, [0]

        def log_and_save(step, metrics, verbose=True):
            log_train(step, metrics, verbose)
            if step // a.ckpt_every > last[0]:
                last[0] = step // a.ckpt_every
                agent.save(os.path.join(run_dir, f"model_{last[0] * a.ckpt_every // 1000}k.pt"))
        logger.log_train = log_and_save
    env = config.make_env(cfg)
    agent = PPO(obs_dim=env.observation_space.shape[0], act_dim=env.action_space.shape[0],
                buffer=RolloutBuffer(), **cfg["hparams"])
    if a.init:
        agent.load(a.init)
        cfg["init"] = a.init
        with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    print(f"결과 폴더: {run_dir}\n경로 엣지 {len(env.edges)}개, 시작 {env.edges[0]}, 도착 {env.edges[-1]}")
    try:
        agent.learn(env, total_timesteps=a.timesteps or cfg["total_timesteps"], logger=logger,
                    eval_interval=0 if a.no_train_eval else EVAL_INTERVAL, eval_episodes=EVAL_EPISODES)
    finally:
        env.close()
        logger.close()
        model = os.path.join(run_dir, "model.pt")
        agent.save(model)
        print(f"저장: {model}\n평가: python rl/test_skku.py {os.path.relpath(model, course.TEAM)} --config {a.config} --nogui")


if __name__ == "__main__":
    main()
