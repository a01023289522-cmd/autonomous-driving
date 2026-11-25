"""js_nw4 + red_light_penalty 30 (11/24 임재성). js_nw6(20)과 벌점 크기만 다름. 15만 스텝."""
from configs.js_nw4 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, red_light_penalty=30.0)
