"""안전 묶음: r_idle_scaled + 관측 보완(obs_foe_fix) + 양보 위반 감점 2(yield_penalty) + 앞차 시간 간격 2초(headway_s).
11/18 r_idle_scaled 재생 56 에피소드: 충돌 6건 = 율전로98번길 진입 3(상대 TTC 0.2–0.5초, 1건은 기존 관측에 안 보임),
출발 직후 추돌 2, 교차로 안 정지 중 피추돌 1. 위험 진입(TTC<3초) 중 충돌 7.5%로 손익분기(약 8%)와 같아 양보를 못 배움.
양보 감점은 양보 연결 진입 순간(진입의 10%), 시간 간격은 앞차 접근(주행 스텝의 0.6%)에만 붙어 서로 겹치지 않아 묶었다."""
SCENARIO = {"train_seeds": list(range(500)), "obs_foe_fix": True}
REWARD = {"blocked_penalty": 0.02, "idle_penalty": 0.02, "idle_scaled": True, "yield_penalty": 2.0, "headway_s": 2.0}
