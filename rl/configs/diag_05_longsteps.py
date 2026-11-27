"""진단용 (임재성, 11/18): 실험 05과 같은 보상에서 제한 시간만 1600 → 2400스텝.

학습용이 아니라 이미 학습한 실험 05 모델을 다시 재는 데만 쓴다. 제한 1600스텝에서는
시간 초과로 끝난 에피소드가 충돌할 기회를 잃어 충돌률이 낮게 나오므로, 벌점 실험은
두 조건으로 모두 재서 비교한다. 실험 기록표에는 올리지 않는다.

    python -X utf8 rl/test_skku.py results\jaeseong_05_...\model.pt --config diag_05_longsteps --episodes 20 --nogui
"""

TOTAL_TIMESTEPS = 200_000

REWARD = {"collision_penalty": 7.0}      # 실험 05과 같다

SIMULATION = {"max_steps": 2400}          # 1600 → 2400, 이 한 가지만 다르다
