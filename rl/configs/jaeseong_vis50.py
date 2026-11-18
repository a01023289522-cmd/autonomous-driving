"""실험 vis50 (임재성): visibility 비교의 대조군. 지금 값 50 m 그대로.

왜 대조군이 따로 필요한가. 제 1~9차는 전부 환경 v1에서 돌렸고 지금 main은 v3이다
(경로 기준 차로 관측 2개 제거, 회전교차로 진입로 교통 추가). 관측 개수도 배경 교통도
다르므로 6차(벌점 7, v1)를 visibility 실험의 기준선으로 쓸 수 없다. 같은 v3에서
visibility만 다른 두 번을 같이 돌려 비교한다.

충돌 벌점은 1~9차에서 가장 좋았던 7로 고정한다. 학습 시드도 0으로 고정한다.
이 설정과 jaeseong_vis100.py의 차이는 visibility 한 값뿐이다 (작업 규칙 3).

    python -X utf8 rl/train_skku.py --config jaeseong_vis50
"""

TOTAL_TIMESTEPS = 200_000

OBSERVATION = {"visibility": 50.0}      # 수업 기본값. 명시해서 대조군임을 남긴다

REWARD = {"collision_penalty": 7.0}
