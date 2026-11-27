"""js_nw1 + red_light_penalty 5 → 15 (js_nw2와 크기 비교)."""
from configs.js_nw1 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, red_light_penalty=15.0)
