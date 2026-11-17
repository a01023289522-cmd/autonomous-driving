"""1차 목표 보상 탐색: r_c10 + 속도 보상 2배 (충돌 벌점을 올렸을 때 멈춰 서는 정책을 막기 위해)."""
REWARD = {"collision_penalty": 10.0, "arrival_bonus": 10.0, "speed_weight": 0.2}
HPARAMS = {"gamma": 0.995}
