"""대조군 c5 (임재성): soupA에서 이어서 학습, 충돌 벌점은 r_s3y 그대로 5.

왜 대조군이 필요한가. 이어서 학습하는 것 자체가 모델을 바꾼다. 충돌 벌점 7만 돌리면
좋아지거나 나빠져도 벌점 덕인지 추가 학습 덕인지 가릴 수 없다. visibility 실험에서
기준선을 잘못 잡아 1라운드를 버린 적이 있다.

js_c7.py와 이 설정의 차이는 collision_penalty 하나뿐이다 (작업 규칙 3).

    python -X utf8 rl/train_skku.py --config js_c5 --init models/best_1119_soupA.pt \
        --ppo-fix --lr-end 2.5e-5 --no-train-eval --ckpt-every 25000 --timesteps 150000

결과 (11/19): 시드 1100~1199 100 에피소드에서 5만 스텝 모델이 완주 88·충돌 12·시간 초과 0,
7.5만 모델이 85·15·0. 기준 모델 soupA는 89·6·5다. 충돌이 두 배로 늘고 시간 초과가 0이
되었다. 막히면 서던 것이 밀고 들어가는 쪽으로 바뀌었다는 뜻이다. 신호 앞 정지선까지는
20.5m에서 14.6m로 가까워졌다.
"""
from configs.r_s3y import SCENARIO, REWARD, HPARAMS  # noqa: F401

TOTAL_TIMESTEPS = 150_000
