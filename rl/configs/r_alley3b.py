"""r_alley3(근거리 관측 2개)을 골목 후보 r_alley2 30만에 붙여, 새 입력 열만 학습률 5e-4로 학습 (--new-cols 2).
11/22 r_alley3(r_s8 기반, 학습률 5e-5) 15만: 새 열 가중치 크기 0.014~0.023(기존 열 평균 0.094)로 거의 안 배움, 1200–1599 370/26/4 (r_s8 368/28/4).
새 입력은 앞차가 가까울 때만 0이 아니라 신호가 드묾 → 고정된 나머지는 그대로 두고 새 열 학습률만 키운다."""
from configs.r_alley3 import SCENARIO, REWARD  # noqa: F401
from configs.r_alley3 import HPARAMS as _H
HPARAMS = dict(_H, lr=5e-4)
