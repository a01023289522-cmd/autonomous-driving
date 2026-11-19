"""실험 traf3 (임재성): js_traf에서 1.4배 교통의 비중만 절반에서 3분의 1로 낮춘다.

js_traf 30k는 시드 1000~1199 200 에피소드에서 완주 96.0·충돌 2.0으로 팀 신규 모델
best_1119_s8(95.0·2.5)을 넘었고 정지선도 15.2m로 가깝다. 모델 교체 기준 1번과 2번을
만족한다.

3번(급제동 3.0/km, 급가속 10~13/km 이하)에서 떨어졌다. 급제동 3.2, 급가속 14.8이다.
무신호 교차로 안에 서는 정지도 6회에서 18회로 늘었다. 붐비는 교통에서 빨리 가고 비집고
들어가는 쪽으로 배운 결과로 본다.

승차감 감점(jerk_penalty 0.5)으로 잡으려 했으나 실패했다. 완주가 91~92.5%로 떨어지고
정지선이 23~29m로 멀어졌다. 정지선에 바짝 다가가려면 마지막에 확실히 멈춰야 하는데
그것이 급제동이라 감점을 받는다. 멀찍이서 천천히 서는 쪽이 유리해진다.

그래서 원인 쪽을 줄인다. 어려운 교통의 비중을 절반에서 3분의 1로 낮춘다. 거칠어지는
정도만 줄이고 완주·충돌 이득은 지키는 것이 목표다.

js_traf와 이 설정의 차이는 difficulty_mix의 구성 하나뿐이다 (작업 규칙 3).

    python -X utf8 rl/train_skku.py --config js_traf3 --init models/best_1119_soupA.pt \
        --ppo-fix --lr-end 2.5e-5 --no-train-eval --ckpt-every 10000
"""
from configs.js_traf import REWARD, HPARAMS, TOTAL_TIMESTEPS  # noqa: F401
from configs.js_traf import SCENARIO as _S

# 시드 % 3 으로 고르므로 셋 중 하나만 1.4배가 된다 (js_traf는 둘 중 하나로 절반이었다)
SCENARIO = dict(_S, difficulty_mix=[{}, {}, {"traffic_scale": 1.4}])
