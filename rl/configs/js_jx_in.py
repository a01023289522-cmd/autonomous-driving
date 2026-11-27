"""js_jx + 교차로 안 관측 (11/21 임재성, 로컬 실험용, 커밋하지 않음). 최종 조합과 같은 관측으로 학습할 때 쓴다."""
from configs.js_jx import REWARD, HPARAMS, TOTAL_TIMESTEPS  # noqa: F401
from configs.js_jx import SCENARIO as _S

SCENARIO = dict(_S, obs_inside_fix=True)
