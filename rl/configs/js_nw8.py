"""js_nw7 + red_light_penalty 50 (11/25 임재성). nw7(30) 15만 학습 보상이 끝까지 오름(-24 → 16) → 벌점을 더 키운 갈래. js_nw7_150k에서 이어 학습."""
from configs.js_nw7 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, red_light_penalty=50.0)
