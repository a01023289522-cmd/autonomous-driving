"""실험 vis100 (임재성): 관측 거리 visibility를 50 m에서 100 m로 늘린다.

근거. visibility는 수업 관측에서 두 가지를 정한다. 앞뒤 차를 감지하는 거리이고,
차선 연결성과 밀도를 정규화하는 기준이다. 연결성 계산(env/sumo_env.py의
_lane_connectivity)은 남은 거리가 visibility보다 멀면 무조건 1.0, 즉 계속 이어진다고
돌려준다. 정문 직전 일월로는 358 m라 앞 308 m 동안 차선이 끊기는지 판단 자체를 하지
않는다. 완주 실패의 46%가 이 엣지에서 났다.

100 m로 늘리면 판단 구간이 두 배가 된다. 대신 선행차 거리와 밀도의 정규화 기준도 같이
늘어나 가까운 차에 대한 민감도가 떨어질 수 있다. 그 손해가 이득보다 큰지를 보는 것이
이 실험이다.

판단 기준은 일월로에서 끝난 시간 초과 건수, 완주율, 그리고 위험 진입 비율이다.
대조군은 jaeseong_vis50.py이며 두 설정의 차이는 visibility 한 값뿐이다 (작업 규칙 3).

    python -X utf8 rl/train_skku.py --config jaeseong_vis100
"""

TOTAL_TIMESTEPS = 200_000

OBSERVATION = {"visibility": 100.0}     # 바뀌는 값은 이것 하나뿐

REWARD = {"collision_penalty": 7.0}
