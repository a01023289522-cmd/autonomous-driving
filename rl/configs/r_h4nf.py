"""r_h4에서 obs_tls_foe만 끔 (진단용)."""
from configs.r_h4 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_tls_foe=False)
