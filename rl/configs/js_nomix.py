"""대조군 nomix (임재성): js_mix와 모든 값이 같고 출발점만 r_s3y 그대로.

이어서 학습하는 것 자체가 모델을 바꾸므로, 집중 연습 설정만 돌리면 개선이 연습 덕인지
추가 학습 덕인지 가릴 수 없다. 11/19 충돌 벌점 실험에서 대조군 덕에 "벌점이 아니라
이어서 학습 자체가 충돌을 늘린다"를 가려낼 수 있었다.

    python -X utf8 rl/train_skku.py --config js_nomix --init models/best_1119_soupA.pt \
        --ppo-fix --lr-end 2.5e-5 --no-train-eval --ckpt-every 10000

결과 (11/19): 시드 1100~1199 100 에피소드에서 3만 스텝 모델이 완주 89·충돌 9·시간 초과 2.
기준 모델 soupA(89·6·5)보다 충돌이 늘고 시간 초과가 줄었다. 오전 실험과 같은 방향이며
스텝을 15만에서 5만으로 줄여도 같다. 실패 위치도 495951447 3건, 8577251160 2건으로
기준과 같다. 이어서 학습만으로는 그 교차로가 나아지지 않는다는 뜻이다.
"""
from configs.r_s3y import SCENARIO, REWARD, HPARAMS  # noqa: F401

TOTAL_TIMESTEPS = 50_000
