"""r_s12와 같고 빨간불 대기 감점만 0.1 (크기 비교용)."""
from configs.r_s12 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s12 import REWARD as _R
REWARD = dict(_R, red_wait_penalty=0.1)
