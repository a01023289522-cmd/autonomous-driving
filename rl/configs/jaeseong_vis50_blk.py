"""실험 vis50_blk (임재성): 작동하는 기준선 위에서 visibility 50 m.

1라운드(jaeseong_vis50, jaeseong_vis100)는 base.py를 그대로 물려받아
blocked_penalty가 0이었다. 그 값은 1차 점검 제안으로 꺼진 것인데, 이후 준수님이
그것 때문에 출발 직후 서부로에서 멈춘다는 것을 찾았다 (기록표 11/18: base v2
완주 55%·시간초과 45% 대 r_blocked 완주 85%·시간초과 10%).

실제로 1라운드 15만 스텝 중간 모델을 평가하니 vis50과 vis100 모두 10/10 시간초과였고
멈춘 자리가 경로 2~4번째 엣지, 즉 출발 직후 서부로였다. 위험 진입은 0/0으로
양보 연결에 한 번도 도달하지 못했다. visibility가 효과를 낼 일월로는 27번째 엣지라
비교 자체가 성립하지 않는다.

그래서 blocked_penalty를 준수님이 쓰는 0.02로 맞추고 다시 비교한다. 이 값은 두
설정에 똑같이 들어가므로 제 실험의 변수는 여전히 visibility 하나다 (작업 규칙 3).

대조군은 jaeseong_vis50_blk, 실험군은 jaeseong_vis100_blk이다.

    python -X utf8 rl/train_skku.py --config jaeseong_vis50_blk --no-train-eval
"""

TOTAL_TIMESTEPS = 200_000

OBSERVATION = {"visibility": 50.0}

REWARD = {"collision_penalty": 7.0,
          "blocked_penalty": 0.02}     # 준수님 r_blocked와 같은 값. 두 설정에 동일하게 적용
