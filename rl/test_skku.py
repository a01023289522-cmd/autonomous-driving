"""학습한 모델을 고정 시드로 평가한다. 모든 실험 비교는 이 스크립트로 한다.

    python rl/test_skku.py results/example_1117_120000/model.pt --config example --episodes 100 --nogui   # 지표
    python rl/test_skku.py results/example_1117_120000/model.pt --config example --episodes 3             # 주행 보기
    python rl/test_skku.py results/.../model.pt --start 회전교차로 --delay 20 --episodes 3                 # 회전교차로부터, 빠르게
구간 이름은 config.SEGMENTS (사거리, 버스, 오거리, 회전교차로, 일월로, 정문). 엣지 ID를 직접 줘도 된다.
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
    ap.add_argument("--start", help="출발 구간 이름 또는 엣지 ID (보기용. 평가 지표는 기본 출발로 잰다)")
    ap.add_argument("--delay", type=float, help="화면 한 스텝당 쉬는 시간(ms). 작을수록 빠르다 (기본 100)")
    a = ap.parse_args()
    cfg = config.load(a.config)
    if a.start:
        cfg["scenario"]["start_edge"] = config.SEGMENTS.get(a.start, a.start)
    if a.delay is not None:
        cfg["simulation"]["gui_delay"] = a.delay
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
