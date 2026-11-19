"""r_s17(빨간불 대기 감점 + 투입 시각 무작위) + 꼬리물기 감점 2. r_s17은 정지선 거리 중앙값 5~6 m로 좋아졌지만 495951447 충돌이 늘었다."""
from configs.r_s17 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s17 import REWARD as _R
REWARD = dict(_R, box_penalty=2.0)
