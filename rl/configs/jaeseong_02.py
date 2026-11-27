"""실험 02 (임재성): 환경 v1에서 충돌 벌점만 5 → 10.

실험 01(환경 v0, 5→20)은 완주율 60%→0%, 시간초과 5%→70%로 무너졌다. 관측에 신호와
교차 차량이 없어 정책이 고를 수 있는 답이 「안 가기」뿐이었기 때문이다.

환경 v1은 그 관측이 생겼으므로 전제가 달라졌다. 신호·교차 차량·경로 차로가 보이면
벌점 상향이 「정지」가 아니라 「회피」로 이어질 수 있다. 이번 실험은 그 전제를 확인한다.

값은 20이 아니라 10으로 둔다. 01에서 20은 과도함이 확인됐고, v1 base의
red_light_penalty 5.0과 같은 자릿수를 유지해 신호 위반보다 충돌이 분명히 나쁘되
완주를 포기할 만큼은 아닌 구간을 본다.

비교 대상: 11/17 박준수 `base` v1 (충돌 15%, 완주 80%, 시간초과 5%).
한 번에 한 값만 바꾼다 (작업 규칙 3).

    python -X utf8 rl/train_skku.py --config jaeseong_02
    python -X utf8 rl/test_skku.py results/jaeseong_02_<시각>/model.pt --config jaeseong_02 --episodes 300 --nogui
"""

TOTAL_TIMESTEPS = 200_000     # base v1 기록과 같은 스텝

REWARD = {"collision_penalty": 10.0}
