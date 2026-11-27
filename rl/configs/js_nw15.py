"""js_nw7 + tg_red_stop_bonus 5 (11/25 임재성). js_nw14와 보너스 크기만 다름."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_red_stop_bonus=5.0, tg_red_stop_max=6.0)
