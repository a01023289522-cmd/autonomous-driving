"""관측을 뒤에 n개 늘릴 때 기존 모델을 그대로 쓰도록 첫 층 가중치에 0 열을 붙인다. 새 입력은 처음엔 출력에 영향이 없고,
이어서 학습하면서 쓰는 법을 배운다.
    python rl/expand_obs.py <입력 모델> <출력 모델> <늘릴 개수>"""
import sys
import torch
src, dst, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
sd = torch.load(src, map_location="cpu")
w = sd["trunk.0.weight"]
sd["trunk.0.weight"] = torch.cat([w, torch.zeros(w.shape[0], n, dtype=w.dtype)], dim=1)
torch.save(sd, dst)
print(f"{src}: 입력 {w.shape[1]} → {w.shape[1] + n}")
