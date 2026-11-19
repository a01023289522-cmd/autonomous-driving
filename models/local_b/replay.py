"""Replay the original local_b checkpoint on the project's full SUMO route."""

import argparse
import json
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
DEMO_STATE = HERE / "traffic_1054.xml.gz"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=1054)
    parser.add_argument("--delay", type=float, default=65, help="SUMO GUI step delay in ms")
    parser.add_argument("--nogui", action="store_true")
    args = parser.parse_args()
    if not args.nogui:
        os.environ.pop("LIBSUMO_AS_TRACI", None)

    sys.path.insert(0, str(HERE.parents[1] / "rl"))
    from skku_env import SkkuEnv, traci
    from test_skku import course_load_agent
    from utils.evaluator import evaluate_policy

    class LocalBEnv(SkkuEnv):
        V1_DIM = SkkuEnv.V1_DIM + 3

        def _state_file(self, seed):
            if seed == 1054:
                return str(DEMO_STATE)
            return super()._state_file(seed)

        def _state_ready(self, path):
            if path == str(DEMO_STATE):
                if not DEMO_STATE.is_file():
                    raise FileNotFoundError(DEMO_STATE)
                return True
            return super()._state_ready(path)

        def _v1_obs(self):
            features = super()._v1_obs()
            signals = traci.vehicle.getNextTLS(self.ego_id)
            if signals and signals[0][2] <= 100 and signals[0][3] in "rRu":
                remaining = signals[0][2] - 3.5
                speed = traci.vehicle.getSpeed(self.ego_id)
                features.extend((remaining / 25, (remaining - speed ** 2 / 4) / 25, speed / 6))
            else:
                features.extend((0.0, 0.0, 0.0))
            return features

    cfg = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    # This adapter supplies the three stop-line features, including on local
    # checkouts that also implement the optional features in the base class.
    scenario = dict(cfg["scenario"], obs_stop_line=False)
    sim = dict(cfg["simulation"], gui_delay=args.delay)
    env = LocalBEnv(scenario, sim, cfg["observation"], cfg["action"], cfg["reward"], gui=not args.nogui)
    try:
        env.use_seeds([args.seed])
        agent = course_load_agent()(str(HERE / "far_passed.pt"),
                                    env.observation_space.shape[0], env.action_space.shape[0])
        if isinstance(agent, tuple):
            agent = agent[0]
        metrics = evaluate_policy(agent, env, n_episodes=1, deterministic=True)
        print(f"seed={args.seed} | {metrics.summary()} | {metrics.ep_length:.0f} steps")
    finally:
        env.close()


if __name__ == "__main__":
    main()
