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
    "extra_routes": ["scenario_rb_av.rou.xml"],   # 환경 v3: 회전교차로 AV 진입로 교통 추가 (sumo/skku_map/scenarios.py)
    "obs_v1": True,                  # 환경 v1 관측 12개 추가 (신호, 경로 차로, 교차 차량, 제한속도. rl/skku_env.py)
}

SIMULATION = {"max_steps": 2400}     # 1200초 (11/19 사용자 결정: 800초 → 1200초. 평가 기준에 시간 제한 없음, 교통이 많은 시드에서 800초는 갇힘이 아닌데도 시간초과)

OBSERVATION = {}

# 수업 코드의 spawn_protect는 "차로 위 위치"로 판단해서, 짧은 엣지가 많은 우리 도로에서는 차로 변경이 거의 막힌다
ACTION_SAFETY = {"spawn_protect": 0.0}

REWARD = {
    "red_light_penalty": 5.0,        # 빨간불에 교차로 진입 1회당 감점 (충돌 벌점과 같은 크기에서 시작)
    "overspeed_penalty": 0.3,        # 스텝당 0.3 × (제한속도 초과 m/s ÷ 13.89). 시속 20 km 구간을 50 km로 달리면 속도 보상(0.1)보다 큼
    "blocked_penalty": 0.0,          # 수업 기본 0.05는 신호 대기·골목 서행도 감점하므로 끔 (1차 점검 제안)
}

HPARAMS = {}
