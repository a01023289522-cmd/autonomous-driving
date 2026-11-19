"""평가용: r_s19와 같고 제한 시간만 1200초 (시간초과가 느려서인지 갇혀서인지 판별)."""
from configs.r_s19 import SCENARIO, REWARD, HPARAMS  # noqa: F401
SIMULATION = {"max_steps": 2400}
