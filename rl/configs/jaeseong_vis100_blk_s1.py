"""실험 vis100_blk_s1 (임재성): jaeseong_vis100_blk와 모든 값이 같고 학습 시드만 1.

2라운드에서 완주율이 대각선으로 나왔다. visibility 50은 막힘 감점 0에서 65%,
0.02에서 0%. visibility 100은 0에서 20%, 0.02에서 55%. 두 값이 서로 맞물려야
작동한다는 해석이 가능하지만, 각 칸이 학습 한 번씩이다.

충돌 벌점 실험에서 같은 설정을 시드만 바꿔 돌린 6차와 9차가 완주 75%와 60%,
충돌 1건과 5건으로 갈린 전례가 있다. 65%와 0%는 그보다 큰 차이지만 한 번씩으로는
단정할 수 없다. 이 라운드는 막힘 감점 0.02 줄을 시드 1로 다시 재는 것이다.

읽는 법: 시드 1에서도 vis100_blk이 vis50_blk보다 완주율이 높으면 대각선을 믿는다.
순서가 뒤집히면 2라운드 결과가 학습 분산이었다는 뜻이고, visibility 축 역시
이 측정으로는 가를 수 없다는 결론이 된다.

    python -X utf8 rl/train_skku.py --config jaeseong_vis100_blk_s1 --no-train-eval
"""

TOTAL_TIMESTEPS = 200_000

OBSERVATION = {"visibility": 100.0}

REWARD = {"collision_penalty": 7.0, "blocked_penalty": 0.02}

HPARAMS = {"seed": 1}                   # 2라운드와 다른 값은 이것 하나뿐
