"""평가용: r_s8과 같고 제한 시간만 800초 → 1200초. 시간초과가 '느려서'인지 '갇혀서'인지 가르는 확인용 (학습에 쓰지 않음)."""
from configs.r_s8 import SCENARIO, REWARD, HPARAMS  # noqa: F401
SIMULATION = {"max_steps": 2400}
