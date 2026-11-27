"""r_s8 + obs_tls_foe (빨간불·노란불이면 교차 차량 칸 비움). 학습 없이 s8 모델에 관측 수정만 (11/22 정문 멀리 정지 진단)."""
from configs.r_s8 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_tls_foe=True)
