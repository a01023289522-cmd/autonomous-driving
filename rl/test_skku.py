"""학습한 모델을 고정 시드로 평가한다. 모든 실험 비교는 이 스크립트로 한다.

    python rl/test_skku.py results/example_1117_120000/model.pt --config example --episodes 100 --nogui   # 지표
    python rl/test_skku.py results/example_1117_120000/model.pt --config example --episodes 3             # 주행 보기
"""
import argparse
import importlib.util
import os

import course
import config

from utils.evaluator import evaluate_policy  # noqa: E402


def course_load_agent():
    spec = importlib.util.spec_from_file_location("course_test", os.path.join(course.COURSE, "test.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.load_agent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--config", default="base")
    ap.add_argument("--episodes", type=int, default=100)
    ap.add_argument("--nogui", action="store_true")
    a = ap.parse_args()
    cfg = config.load(a.config)
    env = config.make_env(cfg, gui=not a.nogui)
    env.use_seeds(cfg["scenario"]["eval_seeds"])
    try:
        agent = course_load_agent()(a.model, env.observation_space.shape[0], env.action_space.shape[0])
        if isinstance(agent, tuple):
            agent = agent[0]
        m = evaluate_policy(agent, env, n_episodes=a.episodes, deterministic=True)
    finally:
        env.close()
    print(f"\n{a.episodes} 에피소드 | {m.summary()}\n시간초과율={m.timeout_rate:.0%}  평균길이={m.ep_length:.0f}스텝")


if __name__ == "__main__":
    main()
