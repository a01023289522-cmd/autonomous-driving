"""r_g2와 같고 학습률만 2배 (1e-4 → 5e-5). 11/22 밤: 같은 시간에 더 빨리 배우는지 비교."""
from configs.r_g2 import SCENARIO, REWARD, HPARAMS as _H  # noqa: F401
HPARAMS = dict(_H, lr=1e-4)
