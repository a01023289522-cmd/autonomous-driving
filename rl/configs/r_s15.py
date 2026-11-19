"""r_s11s + 신호 단계 다양화(start_delay_max 90)만. 정문 앞 멀리 정차 대책의 효과를 앞차 대책과 떼어 확인한다 (r_s14는 둘 다 섞임)."""
from configs.r_s11s import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, start_delay_max=90.0)
