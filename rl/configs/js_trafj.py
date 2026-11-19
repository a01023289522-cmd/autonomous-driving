"""실험 trafj (임재성): js_traf에 승차감 감점만 켠다.

js_traf 30k는 시드 1000~1199 200 에피소드에서 완주 96.0·충돌 2.0으로 팀 신규 모델
best_1119_s8(95.0·2.5)을 넘었다. 신호 앞 정지 위치도 15.2m로 더 가깝다. 모델 교체
기준 1번과 2번을 만족한다.

그런데 3번에서 떨어졌다. 급제동이 3.2/km(기준 3.0 이하), 급가속이 14.8/km(기준 10~13)
로 둘 다 넘는다. 무신호 교차로 안에 서는 정지도 6회에서 18회로 늘었다. 교통량을 섞어
학습하면서 붐비는 상황에서 빨리 가고 비집고 들어가는 쪽으로 배운 결과로 본다.

js_traf는 r_q2_nojerk 계보라 jerk_penalty가 0이다. 팀의 r_q2에는 0.5(문턱 0.7)로 켜져
있다. 그 값을 그대로 가져와 거친 주행만 잡는다. 11/18 기록에 따르면 처음부터 학습에서는
승차감 감점이 탐색 노이즈를 벌해서 뺐지만, 이어서 학습은 탐색 폭이 작아 해당하지 않는다.

js_traf와 이 설정의 차이는 jerk_penalty 하나뿐이다 (작업 규칙 3).
판단은 급제동·급가속이 기준 안으로 들어오면서 완주 96·충돌 2가 유지되는지로 한다.

    python -X utf8 rl/train_skku.py --config js_trafj --init models/best_1119_soupA.pt \
        --ppo-fix --lr-end 2.5e-5 --no-train-eval --ckpt-every 10000
"""
from configs.js_traf import SCENARIO, HPARAMS, TOTAL_TIMESTEPS  # noqa: F401
from configs.js_traf import REWARD as _R

REWARD = dict(_R, jerk_penalty=0.5, jerk_deadzone=0.7)   # 바뀌는 값은 이것 하나뿐
