"""Shared 44-input SUMO environment for local_b training and driving."""
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
DEMO_STATE = HERE / "traffic_1054.xml.gz"
sys.path.insert(0, str(HERE.parents[1] / "rl"))
from skku_env import SkkuEnv, traci


def read_config(path=HERE / "config.json"):
    return json.loads(Path(path).read_text(encoding="utf-8"))


class LocalBEnv(SkkuEnv):
    V1_DIM = SkkuEnv.V1_DIM + 3

    def __init__(self, cfg, gui=False):
        # The subclass provides the extra three inputs on every supported checkout.
        scenario = dict(cfg["scenario"], obs_stop_line=False)
        super().__init__(scenario, cfg["simulation"], cfg["observation"], cfg["action"], cfg["reward"], gui=gui)

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
