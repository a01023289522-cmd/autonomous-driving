"""실험 설정 예시. 복사해서 configs/<역할>_<번호>.py 로 저장하고, 바꿀 값만 적는다.

    python rl/train_skku.py --config example
"""

TOTAL_TIMESTEPS = 50_000     # 후보를 거를 때는 짧게

REWARD = {"collision_penalty": 20.0}

HPARAMS = {"gamma": 0.995}
