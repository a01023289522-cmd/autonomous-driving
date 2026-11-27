"""실험 vis100_s1 (임재성): jaeseong_vis100와 모든 값이 같고 학습 시드만 0에서 1로.

visibility 비교의 2라운드. 1라운드(시드 0)에서 vis50과 vis100의 차이가 보이더라도,
그 차이가 값의 효과인지 학습 한 번의 운인지는 시드를 바꿔 다시 돌려야 알 수 있다.

근거는 충돌 벌점 실험이다. 같은 설정을 시드만 바꿔 돌린 6차와 9차가 충돌 1건과 5건,
위험 진입 9.1%와 19.3%로 갈렸고 그 차이가 유의 수준을 넘었다(Fisher 양측 p=0.028).
한 번씩 돌린 값들을 줄 세우면 안 된다는 것이 그때의 결론이다.

읽는 법: 시드 0과 1에서 vis50과 vis100의 대소가 같은 방향이면 그 차이를 믿는다.
방향이 뒤집히면 visibility 축도 이 측정으로는 가를 수 없다는 뜻이다.

    python -X utf8 rl/train_skku.py --config jaeseong_vis100_s1 --no-train-eval
"""

TOTAL_TIMESTEPS = 200_000

OBSERVATION = {"visibility": 100.0}

REWARD = {"collision_penalty": 7.0}

HPARAMS = {"seed": 1}                   # 1라운드와 다른 값은 이것 하나뿐
