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
    ap.add_argument("--ppo-fix", action="store_true", help="수업 PPO의 시간초과 GAE 버그를 고친 rl/ppo_fix.py PPOFixed를 쓴다")
    ap.add_argument("--lr-end", type=float, help="학습률을 이 값까지 선형으로 낮춘다 (수업 PPO에는 스케줄이 없어 업데이트마다 optimizer에 넣는다)")
    ap.add_argument("--no-train-eval", action="store_true",
                    help="학습 중 3 에피소드 평가를 끈다 (판단에 쓰기엔 적고 시뮬레이션 시간의 약 15%%를 쓴다)")
    ap.add_argument("--log-std", type=float, help="이어서 학습할 때 가감속 탐험 폭 log σ를 이 값으로 다시 연다 (11/23: 학습된 모델 −1.24, σ 0.29라 "서 있다가 조금 앞으로"를 거의 시도하지 않음)")
    ap.add_argument("--new-cols", type=int, default=0,
                    help="관측 뒤 n개(새로 붙인 입력)의 첫 층 가중치와 가치 머리만 학습하고 나머지는 고정 (팀원 local_b 방식: 기존 운전은 그대로, 새 입력 쓰는 법만)")
    a = ap.parse_args()
    cfg = config.load(a.config)
    run_dir = os.path.join(course.TEAM, "results", f"{a.config}{'_init' if a.init else ''}_{datetime.now():%m%d_%H%M%S}")
    os.makedirs(run_dir)
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=1)
    logger = RunLogger(run_dir)
    total = a.timesteps or cfg["total_timesteps"]
    # 수업 코드(algorithms/ppo.py)는 그대로 두고, 업데이트마다 불리는 로거에서 중간 모델 저장과 학습률 감소를 한다
    log_train, last = logger.log_train, [0]

    def log_and_save(step, metrics, verbose=True):
        if a.lr_end is not None:
            lr0 = cfg["hparams"].get("lr", 1e-4)
            lr = lr0 + (a.lr_end - lr0) * min(1.0, step / total)
            for g in agent.optimizer.param_groups:
                g["lr"] = lr
            metrics = dict(metrics, lr=lr)
        log_train(step, metrics, verbose)
        if a.ckpt_every > 0 and step // a.ckpt_every > last[0]:
            last[0] = step // a.ckpt_every
            agent.save(os.path.join(run_dir, f"model_{last[0] * a.ckpt_every // 1000}k.pt"))
    logger.log_train = log_and_save
    env = config.make_env(cfg)
    if a.ppo_fix:
        from ppo_fix import PPOFixed
        cfg["ppo_fix"] = True
    agent = (PPOFixed if a.ppo_fix else PPO)(obs_dim=env.observation_space.shape[0], act_dim=env.action_space.shape[0],
                buffer=RolloutBuffer(), **cfg["hparams"])
    if a.init:
        agent.load(a.init)
        cfg["init"] = a.init
        if a.log_std is not None:
            import torch
            with torch.no_grad():
                agent.policy.log_std.data[0] = a.log_std        # 0번 = 가감속 (차선 쪽은 그대로)
            cfg["log_std_reset"] = a.log_std
        if a.new_cols:
            import torch
            agent.policy.requires_grad_(False)
            first = agent.policy.trunk[0].weight
            first.requires_grad_(True)
            mask = torch.zeros_like(first)
            mask[:, -a.new_cols:] = 1
            first.register_hook(lambda grad: grad * mask)
            agent.policy.v_head.requires_grad_(True)
            cfg["new_cols"] = a.new_cols
        with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=1)
    print(f"결과 폴더: {run_dir}\n경로 엣지 {len(env.edges)}개, 시작 {env.edges[0]}, 도착 {env.edges[-1]}")
    try:
        agent.learn(env, total_timesteps=total, logger=logger,
                    eval_interval=0 if a.no_train_eval else EVAL_INTERVAL, eval_episodes=EVAL_EPISODES)
    finally:
        env.close()
        logger.close()
        model = os.path.join(run_dir, "model.pt")
        agent.save(model)
        print(f"저장: {model}\n평가: python rl/test_skku.py {os.path.relpath(model, course.TEAM)} --config {a.config} --nogui")


if __name__ == "__main__":
    main()
