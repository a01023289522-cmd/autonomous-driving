"""Collect NW7 POMDP transitions in resumable batches on Windows."""

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import zipfile


REPO = Path(__file__).resolve().parents[1]
REVISION = "fc472d0c3552f16f9653cbf9d5b0c451fbe41bbc"
MODEL = "models/jaeseong_1125_nw7.pt"
FIRST_SEED = 4000
BATCH = 5
JSONL = "transitions.jsonl.gz"
NPZ = "transitions.npz"


def read_completed(output):
    completed = {}
    for folder in output.glob("batch-*"):
        meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
        index = int(folder.name.removeprefix("batch-"))
        first_seed = FIRST_SEED + index * BATCH
        if (meta["revision"] != REVISION or meta["model"] != MODEL
                or meta["seeds"] != list(range(first_seed, first_seed + BATCH))
                or meta["transitions"] <= 0
                or any((folder / name).stat().st_size != meta["bytes"][name]
                       for name in (JSONL, NPZ))):
            raise ValueError(f"완료 묶음의 기록과 파일이 일치하지 않습니다: {folder}")
        completed[index] = meta["transitions"]
    return completed


def setup_worker(source):
    # Load the map and environment from the same commit as the checkpoint.
    sys.path.insert(0, str(source / "rl"))
    import course  # resolves COURSE_REPO before importing the course environment
    from env import sumo_env
    import libsumo
    import torch

    sumo_env.traci = libsumo
    torch.set_num_threads(1)


def collect_batch(index, source, output):
    import collect_pomdp_data as collector
    import config
    import libsumo
    import numpy as np
    import skku_env
    from skku_env import SkkuEnv

    class CollectionEnv(SkkuEnv):
        def reset(self, *, seed, options=None):
            # A retry of AV insertion must also use this episode's traffic seed.
            self.use_seeds([seed])
            result = super().reset(seed=seed, options=options)
            self.signal_ids = libsumo.trafficlight.getIDList()
            return result

        def get_privileged_state(self):
            state = super().get_privileged_state()
            state["sumo_seed"] = self.seed_now
            now = libsumo.simulation.getTime()
            state["traffic_signals"] = {
                tid: {
                    "phase": libsumo.trafficlight.getPhase(tid),
                    "link_states": libsumo.trafficlight.getRedYellowGreenState(tid),
                    "remaining_s": libsumo.trafficlight.getNextSwitch(tid) - now,
                }
                for tid in self.signal_ids
            }
            return state

    cfg = config.load("js_nw7")

    def make_env(**_):
        return CollectionEnv(cfg["scenario"], cfg["simulation"], cfg["observation"],
                             cfg["action"], cfg["reward"], gui=False)

    collector.SumoHighwayEnv = make_env
    first = index * BATCH
    episodes = range(first, first + BATCH)
    args = SimpleNamespace(policy="ppo", model=str(source / MODEL), device="cpu",
                           stochastic=False, seed=FIRST_SEED, workers=1, gui=False,
                           ndigits=4, episodes=episodes.stop)
    with tempfile.TemporaryDirectory(dir=output, prefix=".writing-") as staging:
        # Each seed is used once. Release its warm-up files after the batch.
        skku_env.STATES = str(Path(staging) / "states")
        part = Path(staging) / "data"
        part.mkdir()
        count = collector.collect(args, None, episodes, 0, str(part / JSONL), str(part / NPZ))
        with gzip.open(part / JSONL, "rb") as stream:
            lines = sum(1 for _ in stream)
        with np.load(part / NPZ, allow_pickle=False) as data:
            ids = data["episode"]
            ends = data["terminated"] | data["truncated"]
            if (not count or count != lines or count != len(ids)
                    or not np.array_equal(ids[ends], episodes)
                    or data["detected_offsets"][-1] != len(data["detected_xy"])):
                raise ValueError(f"저장된 transition 수 또는 에피소드 경계 불일치: {index}")
        meta = {"model": MODEL, "revision": REVISION, "config": "js_nw7",
                "seeds": [FIRST_SEED + ep for ep in episodes], "transitions": count,
                "bytes": {name: (part / name).stat().st_size for name in (JSONL, NPZ)}}
        (part / "metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        part.rename(output / f"batch-{index:06d}")
    return count


def run(args, output):
    completed = read_completed(output)
    total = sum(completed.values())
    print(f"저장된 transition: {total:,} / {args.steps:,}", flush=True)
    if total >= args.steps:
        return
    os.environ.setdefault("COURSE_REPO", str(Path.home() / "Artificial-Intelligence-and-Control-for-Autonomous-Driving"))
    with tempfile.TemporaryDirectory(prefix="nw7-source-") as temp:
        source = Path(temp)
        archive = source / "source.zip"
        subprocess.run(["git", "-C", str(REPO), "archive", "--format=zip",
                        f"--output={archive}", REVISION, "rl", "sumo", MODEL], check=True)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(source)
        with ProcessPoolExecutor(args.workers, initializer=setup_worker, initargs=(source,)) as pool:
            index = 0
            while total < args.steps:
                # Limit the last wave to one batch when close to the target.
                workers = 1 if total and args.steps - total < args.workers * total / len(completed) else args.workers
                jobs = {}
                while len(jobs) < workers:
                    if index not in completed:
                        jobs[index] = pool.submit(collect_batch, index, source, output)
                    index += 1
                for batch, job in jobs.items():
                    completed[batch] = job.result()
                    total += completed[batch]
                    print(f"묶음 {batch} 저장 · {total:,} / {args.steps:,} transitions", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, default=10_000_000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--out", type=Path, default=REPO / "data" / "nw7_10m")
    args = parser.parse_args()
    if args.steps < 1 or args.workers < 1:
        parser.error("--steps and --workers must be positive")
    output = args.out.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".collector.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            parser.exit(1, f"같은 폴더를 사용하는 수집기가 실행 중입니다: {output}\n")
        run(args, output)


if __name__ == "__main__":
    main()
