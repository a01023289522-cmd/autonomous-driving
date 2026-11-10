"""모든 실험의 기본값. 직접 고치지 말고 configs/<내 이름>.py 를 만들어 바꿀 값만 적는다 (example.py 참고).

여기 없는 값은 수업 코드 기본값(env/mdp_config.py, train.py의 HPARAMS·REWARD)을 쓴다.
"""

TOTAL_TIMESTEPS = 200_000

SCENARIO = {
    "start_edge": "7754567510",      # 서부로 남행, 성대역 사거리 약 300 m 앞
    "goal_edge": "9669057440#0",     # 교내 L1 주차장 통로 (약 2.8 km)
    "warmup_seconds": 600,           # AV 투입 전 배경 교통을 채우는 시간
    "speed_limit": 13.89,            # 속도 정규화 기준 (시속 50 km)
    "accel": 3.0,                    # 행동 +1일 때 가속도 (m/s^2)
    "decel": 4.5,                    # 행동 -1일 때 감속도 (m/s^2)
    "train_seeds": list(range(20)),  # 학습 때 돌려 쓰는 교통 시드
    "eval_seeds": list(range(1000, 1100)),  # 평가용 고정 시드 (모든 실험 공통)
}

SIMULATION = {"max_steps": 1600}     # 800초. 경로 평균 약 8분 + 여유

OBSERVATION = {}

# 수업 코드의 spawn_protect는 "차로 위 위치"로 판단해서, 짧은 엣지가 많은 우리 도로에서는 차로 변경이 거의 막힌다
ACTION_SAFETY = {"spawn_protect": 0.0}

REWARD = {}

HPARAMS = {}
