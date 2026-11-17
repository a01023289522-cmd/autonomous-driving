"""1차 목표 보상 탐색: 충돌 벌점 10, 도착 보상 10, gamma 0.995 (경로가 길어 도착 보상이 앞쪽까지 전달되게)."""
REWARD = {"collision_penalty": 10.0, "arrival_bonus": 10.0}
HPARAMS = {"gamma": 0.995}
