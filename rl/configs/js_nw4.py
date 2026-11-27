"""js_nw1 + tg_far_red 0 (11/24 임재성). 빨간불 정지선 앞 '멀리 섬' 감점(tg_far 0.5, 스텝마다 쌓임)만 끈다. 앞차·양보·교차로 입구 대상은 그대로.
근거: 정지선 d m 앞 정지 1분(120스텝, γ 0.99 할인합 약 70)이면 감점 0.5·(d−3)/15·70 → d 5.1 m에서 빨간불 진입 −5와 같아짐.
가상 차(obs_red_wall) 금지 뒤 접근 보상과 신호 벌점의 경쟁을 시간에 비례하지 않게 만드는 실험. 변수 1개 (비교 대상 js_nw1)."""
from configs.js_nw1 import SCENARIO, HPARAMS, REWARD as _R  # noqa: F401
REWARD = dict(_R, tg_far_red=0.0)
