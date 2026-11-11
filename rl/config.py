"""실험 설정 불러오기: configs/base.py 위에 configs/<이름>.py 에 적은 값만 덮어쓴다."""
import copy
import importlib
import os
import sys

import course  # noqa: F401  수업 코드 경로

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from env.mdp_config import ACTION, OBSERVATION, SIMULATION  # noqa: E402
from train import HPARAMS, REWARD  # noqa: E402  수업 train.py의 기본값

DICT_KEYS = ("SCENARIO", "SIMULATION", "OBSERVATION", "ACTION_SAFETY", "REWARD", "HPARAMS")

# 경로 위 구간별 출발 엣지 (보기·구간별 학습용). test_skku.py --start 이름
SEGMENTS = {"사거리": "7754567510", "버스": "700812830", "오거리": "7755484380#1",
            "회전교차로": "-4526039590#0", "일월로": "3718967780#2", "정문": "-15379779810#1"}


def load(name):
    """이름의 설정을 합쳐 dict로 돌려준다. name이 base면 기본값 그대로."""
    base = importlib.import_module("configs.base")
    cfg = {k: dict(getattr(base, k)) for k in DICT_KEYS}
    cfg["TOTAL_TIMESTEPS"] = base.TOTAL_TIMESTEPS
    if name != "base":
        mod = importlib.import_module(f"configs.{name}")
        for k in DICT_KEYS:
            cfg[k].update(getattr(mod, k, {}))
        cfg["TOTAL_TIMESTEPS"] = getattr(mod, "TOTAL_TIMESTEPS", cfg["TOTAL_TIMESTEPS"])
    action = copy.deepcopy(ACTION)
    action["lane_change_safety"].update(cfg["ACTION_SAFETY"])
    return {"name": name, "scenario": cfg["SCENARIO"], "total_timesteps": cfg["TOTAL_TIMESTEPS"],
            "simulation": {**SIMULATION, **cfg["SIMULATION"]}, "observation": {**OBSERVATION, **cfg["OBSERVATION"]},
            "action": action, "reward": {**REWARD, **cfg["REWARD"]}, "hparams": {**HPARAMS, **cfg["HPARAMS"]}}


def make_env(cfg, gui=False):
    from skku_env import SkkuEnv
    return SkkuEnv(cfg["scenario"], cfg["simulation"], cfg["observation"], cfg["action"], cfg["reward"], gui=gui)
