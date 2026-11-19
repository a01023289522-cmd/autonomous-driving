"""r_s8에서 관측과 교통을 유지하고 적색 대기 감점만 시험한다."""
from configs.r_s8 import HPARAMS, REWARD as _REWARD, SCENARIO  # noqa: F401

REWARD = dict(_REWARD, red_wait_penalty=0.05)
