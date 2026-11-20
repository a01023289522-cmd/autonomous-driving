"""두 모델의 가중치를 섞는다: 내 모델(41칸)의 견고함 + 팀원 모델(44칸, 정지선 관측)의 정지선 능력.

내 모델은 정지선 관측 3칸이 없으므로 그 입력 가중치를 0으로 늘려 44칸으로 맞춘 뒤 섞는다.
섞은 뒤 정지선 3칸의 입력 가중치는 팀원 것을 그대로 넣는다 (평균을 내면 팀원 값이 절반으로
깎여 정지선 능력이 사라진다: 11/20 mix50에서 일월로 10.3 m, 목표 정차 7%).

두 모델이 같은 출발점(best_1119_soupA)에서 갈라졌기 때문에 섞어도 둘의 장점이 남는다 (soup.py와 같은 원리).

    python rl/mix_models.py models/jaeseong_1119_traf30k.pt models/local_b/far_passed.pt models/jaeseong_1120_mix90f.pt --w 0.9
"""
import argparse

import torch

ap = argparse.ArgumentParser()
ap.add_argument("mine", help="내 모델 (41칸)")
ap.add_argument("teammate", help="팀원 모델 (44칸, obs_stop_line)")
ap.add_argument("out")
ap.add_argument("--w", type=float, default=0.9, help="내 모델 비중")
a = ap.parse_args()

m = torch.load(a.mine, map_location="cpu")
t = torch.load(a.teammate, map_location="cpu")
extra = t["trunk.0.weight"].shape[1] - m["trunk.0.weight"].shape[1]
m = dict(m, **{"trunk.0.weight": torch.nn.functional.pad(m["trunk.0.weight"], (0, extra))})
assert list(m) == list(t) and all(m[k].shape == t[k].shape for k in m), "키나 모양이 다르다"
out = {k: a.w * m[k] + (1 - a.w) * t[k] for k in m}
out["trunk.0.weight"][:, -extra:] = t["trunk.0.weight"][:, -extra:]
torch.save(out, a.out)
print(f"{a.out}: 내 모델 {a.w:.0%} + 팀원 {1 - a.w:.0%}, 정지선 {extra}칸은 팀원 그대로")
