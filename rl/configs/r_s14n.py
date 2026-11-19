"""평가용: r_s14에서 진행 방향 관측(obs_turn)을 뺀 것 (관측 41개). r_s14 15만의 첫 층에서 방향 입력 3개 열을 잘라낸 모델에 쓴다.
11/19 확인: r_s14 15만에서 방향 입력을 바꿔도 가속 명령 변화 ±0.04 — 사실상 안 쓰는 입력이라 규정 소지가 있는 관측을 빼고 같은 성능인지 본다."""
from configs.r_s14 import SCENARIO as _S, REWARD, HPARAMS  # noqa: F401
SCENARIO = dict(_S, obs_turn=False)
