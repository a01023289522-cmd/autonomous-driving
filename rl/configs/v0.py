"""환경 v0 (11/16까지의 학습): 관측 31개, 신호 위반·과속 감점 없음, blocked_penalty 수업 기본값.
v0으로 학습한 모델(예: results/base_1116_191213)을 평가할 때 --config v0 으로 쓴다."""

SCENARIO = {"obs_v1": False}
REWARD = {"red_light_penalty": 0.0, "overspeed_penalty": 0.0, "blocked_penalty": 0.05}
