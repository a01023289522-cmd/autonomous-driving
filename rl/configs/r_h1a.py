"""r_h1 1단계: 새 관측 2열과 가치 함수만 학습률 5e-4 (--new-cols 2). 11/22 교훈: 새 열은 5e-5로는 거의 안 배움."""
from configs.r_h1 import SCENARIO, REWARD, HPARAMS as _H  # noqa: F401
HPARAMS = dict(_H, lr=5e-4)
