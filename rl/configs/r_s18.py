"""r_s8 10만에서 이어서 + 꼬리물기 감점(box_penalty 2, 양보 위반 감점과 같은 크기). 다른 변경 없음 — 495951447 대책만 따로 확인."""
from configs.r_s8 import SCENARIO, HPARAMS  # noqa: F401
from configs.r_s8 import REWARD as _R
REWARD = dict(_R, box_penalty=2.0)
