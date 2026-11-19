"""r_s3에서 양보 위반 판정 기준만 3초 → 4초 (yield_ttc). GPT 교차검증 권고: 상대 차를 15 m 전부터 보면서도 시속 15 km로
진입하므로 더 이른 진입 결정에도 신호를 준다. 감점 크기(2)는 그대로. 앞차 TTC 감점은 쓰지 않는다 (r_q2ct에서 차로 갇힘)."""
from configs.r_s3 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s3 import REWARD as _R
REWARD = dict(_R, yield_ttc=4.0)
