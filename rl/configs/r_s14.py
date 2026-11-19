"""r_s13(앞차 간격 대책) + start_delay_max 90: 경로 중간 출발 때 AV 투입을 0~90초 무작위로 늦춘다 (신호 주기 87초를 다 덮음).
11/19 측정: 정문 앞 출발 학습 에피소드가 모두 같은 신호 단계(빨간불 남은 17~18초)에 정문에 닿아, 긴 빨간불에서 멀리 서는 손해를
학습 중에 한 번도 겪지 않음."""
from configs.r_s13 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, start_delay_max=90.0)
