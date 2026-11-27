"""환경 비교용: r_h11 + ignore_junction_blocker 100 (지도 기본 60초). 정책·보상 변경 없음."""
from configs.r_h11 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, ignore_junction_blocker=100)
