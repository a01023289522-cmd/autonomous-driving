"""r_s8 10만(시드 200개 95.0/2.5/2.5, 1차 목표 첫 통과)에서 이어서. 정문 앞 멀리 정차 대책 두 가지:
- obs_turn: 다음 교차로 진행 방향(좌·직·우) 관측 3개 추가(41 → 44). rl/expand_obs.py로 새 입력 가중치 0인 모델에서 시작
- red_wait_penalty 0.05: 빨간불이고 앞이 정지선까지 비었는데 멀리 서 있을 때만 정차 감점과 같은 비례로 더 감점
11/19 갈래 비교: 정지선까지 다가가는 이득이 할인 보상 평균 +0.5(범위 −0.3~+1.0)로 작아 가치 함수만 알고 행동은 안 바뀜."""
from configs.r_s8 import SCENARIO as _S, REWARD as _R, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_turn=True)
REWARD = dict(_R, red_wait_penalty=0.05)
