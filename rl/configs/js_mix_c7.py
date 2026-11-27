"""실험 mix_c7 (임재성): 집중 연습(js_mix) 위에서 충돌 벌점만 5에서 7로.

왜 벌점을 다시 보는가. 11/19 오전에 soupA에서 벌점 5·7·10을 각각 15만 스텝 돌렸더니
시드 1100~1199 기준 완주 88·88·90, 충돌 12·12·10으로 차이가 없었다. 그때의 해석은
"충돌 벌점은 부딪힌 뒤에만 붙는데 위험 진입 중 실제 충돌이 7.5%뿐이라 신호가 드물다"
였다.

집중 연습은 그 전제를 바꾼다. 위험 진입이 몰린 두 교차로 앞에서 출발하므로 매 주행마다
그 상황을 겪고, 따라서 충돌도 훨씬 자주 난다. 신호가 조밀해지면 벌점 크기가 의미를
가질 수 있다.

js_mix와 이 설정의 차이는 collision_penalty 하나뿐이다 (작업 규칙 3).

    python -X utf8 rl/train_skku.py --config js_mix_c7 --init models/best_1119_soupA.pt         --ppo-fix --lr-end 2.5e-5 --no-train-eval --ckpt-every 10000

결과 (11/19): 시드 1100~1199 100 에피소드에서 2만 스텝 모델이 완주 88·충돌 7·시간 초과 5.
같은 연습에 벌점만 5인 js_mix가 충돌 3건이므로 벌점을 올리자 효과가 사라졌다.
위험 진입도 8.1%에서 6.6%로 줄었다. 벌점이 크면 교차로에 덜 들어가고 덜 들어가면
연습이 덜 되는 것으로 보인다.

가설이 틀렸다. 집중 연습으로 충돌이 자주 나면 벌점 신호가 조밀해져 값이 의미를 가질
것이라고 보았으나 반대였다.
"""
from configs.js_mix import SCENARIO, HPARAMS, TOTAL_TIMESTEPS  # noqa: F401
from configs.js_mix import REWARD as _R

REWARD = dict(_R, collision_penalty=7.0)
