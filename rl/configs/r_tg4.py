"""r_tg3 수정: 멀리 섬 감점은 AV가 거의 서 있을 때(1 m/s 미만)만. r_tg3(범위 100 m)는 다가가는 중에도 감점이 붙어 충돌 5 → 58.
r_tg2 30만(1000–1199 195/5, 지금 최종과 같은 안전)에서 이어서."""
from configs.r_tg3 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_tg3 import REWARD as _R
REWARD = dict(_R, tg_far_speed=1.0)
