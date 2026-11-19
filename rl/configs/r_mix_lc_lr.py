"""r_mix_lc + 학습률 1e-4 → 3e-5. 11/18: 이어서 학습할 때 체크포인트마다 충돌이 10–17%로 흔들린다(r_safe 25만 대 30만)."""
from configs.r_mix_lc import SCENARIO, REWARD  # noqa: F401
HPARAMS = {"lr": 3e-5}
