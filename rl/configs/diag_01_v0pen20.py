"""진단용 (임재성, 11/18): 실험 02(환경 v0, 충돌 벌점 20) 모델을 다시 평가하기 위한 설정.

당시에는 base.py가 환경 v0이었으므로 jaeseong_01.py에 SCENARIO를 적지 않았다. 지금은
base.py가 v1(관측 43개)이라 그 설정으로는 관측 31개로 학습한 모델을 불러올 수 없다.
v0 관측으로 되돌리고 충돌 벌점만 그때 값으로 맞춘다.

충돌 지점을 엣지 단위로 다시 모으기 위한 평가 전용 설정이다. 학습에 쓰지 않으며 실험
기록표에도 올리지 않는다.

    python -X utf8 rl/eval_detail.py results\jaeseong_01_1117_004409\model.pt --config diag_01_v0pen20 --episodes 20
"""

SCENARIO = {"obs_v1": False}

REWARD = {"red_light_penalty": 0.0, "overspeed_penalty": 0.0,
          "blocked_penalty": 0.05, "collision_penalty": 20.0}
