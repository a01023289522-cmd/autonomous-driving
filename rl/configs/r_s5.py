"""best_1119_soupA(r_s3y)에서 이어서 학습. 11/19 측정 두 가지를 같이 고친다.
- 다차로 신호 앞 멀리 정차(정지선 50–68 m 앞): red_approach 1.0 (빨간불일 때 정지선 쪽으로 다가간 거리 보상, 신호당 최대 1)
- 남은 실패의 중심 495951447(서부로 5552317710#1 끝) 양보: 출발점 섞기에 5552317710#1 추가, 정문 앞 일월로 비중 2배
PPO는 r_s3과 같은 보수적 설정 (학습률 5e-5, epoch 5, minibatch 128). --ppo-fix --lr-end 2.5e-5로 돌린다."""
from configs.r_s3y import SCENARIO as _S, REWARD as _R, HPARAMS  # noqa: F401
SCENARIO = dict(_S, start_mix=list(_S["start_mix"]) + ["5552317710#1", "5552317710#1", "5612296410"])
REWARD = dict(_R, red_approach=1.0)
