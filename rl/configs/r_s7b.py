"""r_s7a + 빨간불 접근 보상 1 → 2. 정문 앞 멀리 정차에 보상 크기가 모자란지 r_s7a와 비교."""
from configs.r_s7a import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s7a import REWARD as _R
REWARD = dict(_R, red_approach=2.0)
