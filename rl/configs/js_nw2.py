"""js_nw1 + red_light_penalty 5 → 10. 대기 중 할인(γ=0.99, 0.5초/스텝)으로 잃는 미래 보상이 벌점 5보다 커서 빨간불을 지나치는지 본다."""
from configs.js_nw1 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, red_light_penalty=10.0)
