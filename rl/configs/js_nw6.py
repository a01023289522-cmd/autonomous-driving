"""js_nw4 + red_light_penalty 20 (11/24 임재성). 5만 평가(시드 1000–1199, 가상 차 끔): 벌점 5·10·15에서 빨간불 진입 407~482건, 충돌 29~70건.
벌점을 키울수록 충돌 감소(nw1 70 → nw2 37 → nw3 29)라 더 크게. tg_far_red 0 유지 (대기 감점과의 경쟁 제거). 15만 스텝."""
from configs.js_nw4 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, red_light_penalty=20.0)
