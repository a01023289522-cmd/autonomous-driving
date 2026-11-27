"""r_h11 + 신호 무작위(tls_random_offset): 일반화 평가용. 정책·보상 변경 없음."""
from configs.r_h11 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, tls_random_offset=True)
