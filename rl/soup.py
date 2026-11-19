"""같은 모델에서 이어서 학습한 체크포인트들의 가중치를 평균해 모델 하나로 만든다 (model soup).
추가 학습 없이 체크포인트마다 흔들리는 성능을 줄인다. 출발점(--init)이 같은 체크포인트끼리만 섞을 것.

    python rl/soup.py models/best_1119_soupA.pt results/r_s3y_init_1119_021957/model_250k.pt results/r_s3y_init_1119_021957/model_300k.pt
"""
import sys
import torch

out, *paths = sys.argv[1:]
ds = [torch.load(p, map_location="cpu") for p in paths]
torch.save({k: sum(d[k] for d in ds) / len(ds) for k in ds[0]}, out)
print(out, "<-", len(ds), "개 평균")
