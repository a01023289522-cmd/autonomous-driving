"""실험 traf_s1 (임재성): js_mix2에서 학습 교통량을 섞는다 (기본 1.0과 1.4배).

왜. 지금 학습 교통은 배율 1.0 하나뿐이다. 더 붐비는 상황을 겪어 본 적이 없으므로
평가에서 교통이 몰리면 대응이 약할 수 있다. 11/17 난이도별 평가에서 1.4배 교통일 때
완주율이 70%에서 30%로 떨어진 기록이 있다.

difficulty_mix로 시드마다 하나를 고정 선택한다. 짝수 시드는 기본, 홀수 시드는 1.4배다.
어려운 교통만으로 학습하면 기본 교통 성능이 떨어지므로(11/18 r_rb_stage1: 회전교차로
충돌이 18건으로 오히려 늘었음) 섞는다.

평가 시드(1000번대)는 difficulty_mix가 적용되지 않으므로 비교 조건은 그대로다.

js_mix2와 이 설정의 차이는 difficulty_mix 하나뿐이다 (작업 규칙 3).

주의: 교통 배율이 바뀌면 배경 교통 상태 파일 이름이 달라져 새로 만들어야 한다
(파일명에 _x1.4가 붙는다). 1.4배 시드 250개를 만드는 데 시간이 더 걸린다.

    python -X utf8 rl/train_skku.py --config js_traf --init models/best_1119_soupA.pt \
        --ppo-fix --lr-end 2.5e-5 --no-train-eval --ckpt-every 10000
"""
from configs.js_mix2 import REWARD, HPARAMS, TOTAL_TIMESTEPS  # noqa: F401
from configs.js_mix2 import SCENARIO as _S

SCENARIO = dict(_S, difficulty_mix=[{}, {"traffic_scale": 1.4}])   # 바뀌는 값은 이것 하나뿐

HPARAMS = {"lr": 5e-5, "n_epochs": 5, "minibatch_size": 128, "seed": 1}
