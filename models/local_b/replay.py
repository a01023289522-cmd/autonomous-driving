"""Replay the original local_b checkpoint on the project's full SUMO route."""

import argparse
import os
from pathlib import Path


HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=HERE / "far_passed.pt")
    parser.add_argument("--seed", type=int, default=1054)
    parser.add_argument("--delay", type=float, default=65, help="SUMO GUI step delay in ms")
    parser.add_argument("--nogui", action="store_true")
    args = parser.parse_args()
    if not args.nogui:
        os.environ.pop("LIBSUMO_AS_TRACI", None)

    from local_env import LocalBEnv, read_config
    from test_skku import course_load_agent
    from utils.evaluator import evaluate_policy

    cfg = read_config()
    cfg["simulation"]["gui_delay"] = args.delay
    env = LocalBEnv(cfg, gui=not args.nogui)
    try:
        env.use_seeds([args.seed])
        agent = course_load_agent()(str(args.model),
                                    env.observation_space.shape[0], env.action_space.shape[0])
        if isinstance(agent, tuple):
            agent = agent[0]
        metrics = evaluate_policy(agent, env, n_episodes=1, deterministic=True)
        print(f"seed={args.seed} | {metrics.summary()} | {metrics.ep_length:.0f} steps")
    finally:
        env.close()


if __name__ == "__main__":
    main()
