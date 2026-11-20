"""r_s21 + queue_strict: 서 있는 앞차 1.5 m 안에서 아직 움직이면(0.1 m/s 이상) 6 m 간격 감점을 되돌리지 않는다. r_s21 5만에서 이어서.
11/19 새 시드 재생: 남은 충돌의 주 유형이 대기열에서 앞차에 0.2~1.8 m/s로 기어가 닿는 저속 추돌(회전교차로 진입로 3건 등)."""
from configs.r_s21 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s21 import REWARD as _R
REWARD = dict(_R, queue_strict=True)
