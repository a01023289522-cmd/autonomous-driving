"""Fine-tune local_b on route traffic with an additional Ilwol-ro stop reward."""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import torch

from local_env import HERE, LocalBEnv, read_config, traci
from evaluate import ILWOL_EDGE, ILWOL_SIGNAL, MIN_WAIT_SECONDS, STOP_DISTANCE, STOP_SPEED, WAITING
from ppo_fix import PPOFixed
from utils.buffer import RolloutBuffer
from utils.logger import RunLogger


class TrainingEnv(LocalBEnv):
    def reset(self, **kwargs):
        self.last_distance = None
        self.held_steps = 0
        return super().reset(**kwargs)

    def step(self, action):
        obs, reward, done, timeout, info = super().step(action)
        signal = self._tls_ahead()
        if signal and signal[:2] == ILWOL_SIGNAL and 0 <= signal[2] <= 100 and traci.vehicle.getRoadID(self.ego_id) == ILWOL_EDGE:
            distance, state = signal[2:]
            leader = traci.vehicle.getLeader(self.ego_id, 100)
            clear = not (leader and leader[0] and leader[1] + traci.vehicle.getMinGap(self.ego_id) < distance)
            in_window = STOP_DISTANCE[0] <= distance <= STOP_DISTANCE[1]
            if clear and state in WAITING:
                error = abs(distance - 3.5)
                previous_error = abs(self.last_distance - 3.5) if self.last_distance is not None else error
                speed = info["speed"]
                desired_speed = min(6.0, math.sqrt(2 * max(distance - 3.5, 0)))
                shaping = 0.15 * (previous_error - error) - 0.10 * min(abs(speed - desired_speed) / 6, 1)
                shaping -= 0.05 * min(error / 12, 1)
                if in_window:
                    shaping += 0.15 * max(1 - speed / 0.45, 0)
                self.held_steps = self.held_steps + 1 if in_window and speed < STOP_SPEED else 0
                self.last_distance = distance
                return obs, reward + 0.6 * shaping, done, timeout, info
            if clear and state in ("g", "G") and in_window and self.held_steps * self.step_length >= MIN_WAIT_SECONDS:
                reward += 5.0
        self.last_distance = None
        self.held_steps = 0
        return obs, reward, done, timeout, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=16384)
    parser.add_argument("--lr", type=float, default=0.00005)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cfg = read_config()
    if args.steps <= 0 or args.steps % cfg["hparams"]["n_steps"] or args.lr <= 0:
        parser.error("--steps must be a positive rollout multiple and --lr must be positive")
    folder = args.output or HERE.parents[1] / "results" / datetime.now().strftime("local_b_route_%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=False)
    cfg["hparams"]["lr"] = args.lr
    cfg["total_timesteps"] = args.steps
    cfg["init"] = "models/local_b/far_passed.pt"
    cfg["scenario"]["start_mix"] = [cfg["scenario"]["start_edge"]] * 3 + [ILWOL_EDGE]
    env = TrainingEnv(cfg)
    logger = RunLogger(str(folder))
    try:
        agent = PPOFixed(obs_dim=env.observation_space.shape[0], act_dim=env.action_space.shape[0],
                         buffer=RolloutBuffer(), **cfg["hparams"])
        agent.load(str(HERE / "far_passed.pt"))
        # Start with the existing driver. Only the stop input columns and the critic learn.
        agent.policy.requires_grad_(False)
        first = agent.policy.trunk[0].weight
        first.requires_grad_(True)
        mask = torch.zeros_like(first)
        mask[:, -3:] = 1
        first.register_hook(lambda grad: grad * mask)
        agent.policy.v_head.requires_grad_(True)
        (folder / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        agent.learn(env, total_timesteps=args.steps, logger=logger, eval_interval=0)
        agent.save(str(folder / "model.pt"))
        print(folder, flush=True)
    finally:
        env.close()
        logger.close()


if __name__ == "__main__":
    main()
