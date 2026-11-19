"""Conda 환경에서 반복 학습, GUI 3회 재생, 평가 20회와 신호 진단을 실행한다."""
import argparse
from datetime import datetime, timezone
import hashlib
from itertools import cycle, islice
import json
import os
from pathlib import Path
import subprocess
import sys
from time import monotonic
from uuid import uuid4

import config
import course


def revision(folder):
    run = subprocess.run(["git", "rev-parse", "HEAD"], cwd=folder, capture_output=True, text=True)
    return run.stdout.strip() if run.returncode == 0 else None


def changes(before, after):
    result = {}
    for name in before.keys() | after.keys():
        a, b = before.get(name), after.get(name)
        if isinstance(a, dict) and isinstance(b, dict):
            diff = changes(a, b)
            if diff:
                result[name] = diff
        elif a != b:
            result[name] = {"before": a, "after": b}
    return result


def write_manifest(folder, info):
    temporary = folder / "run.tmp"
    temporary.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(folder / "run.json")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(64 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def stage(folder, manifest, name, script, *args, gui=False):
    command = [sys.executable, "-u", "-X", "utf8", f"rl/{script}", *map(str, args)]
    env = os.environ.copy()
    for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env.setdefault(key, "1")
    if gui:
        env.pop("LIBSUMO_AS_TRACI", None)
    log_path = folder / f"{name}.log"
    entry = {"command": command, "log": log_path.name, "status": "running",
             "backend": "traci" if gui or not env.get("LIBSUMO_AS_TRACI") else "libsumo"}
    manifest["stages"][name] = entry
    write_manifest(folder, manifest)
    print(f"{name} → {log_path}", flush=True)
    start = monotonic()
    try:
        with log_path.open("x", encoding="utf-8") as log:
            process = subprocess.run(command, cwd=course.TEAM, env=env, stdout=log, stderr=subprocess.STDOUT)
        entry["returncode"] = process.returncode
        entry["status"] = "ok" if process.returncode == 0 else "failed"
        process.check_returncode()
    except BaseException:
        entry["status"] = "failed"
        raise
    finally:
        entry["duration_s"] = round(monotonic() - start, 2)
        write_manifest(folder, manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="base")
    parser.add_argument("--compare-config", default="base", help="설정 변경값 기록 기준")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--timesteps", type=int)
    parser.add_argument("--seed", type=int, help="첫 학습의 난수 시드. 반복마다 1씩 증가")
    model = parser.add_mutually_exclusive_group()
    model.add_argument("--init", type=Path, help="이 모델에서 이어 학습")
    model.add_argument("--model", type=Path, help="학습 없이 기존 모델 평가")
    parser.add_argument("--ppo-fix", action="store_true")
    parser.add_argument("--lr-end", type=float)
    parser.add_argument("--ckpt-every", type=int, default=50000)
    parser.add_argument("--headless-replay", action="store_true", help="화면 없이 3회 재생 확인")
    parser.add_argument("--gui-delay", type=float, default=0)
    args = parser.parse_args()
    if args.repeat < 1 or (args.timesteps is not None and args.timesteps < 1):
        parser.error("--repeat와 --timesteps는 1 이상이어야 합니다.")
    cfg = config.load(args.config)
    seeds = list(islice(cycle(cfg["scenario"]["eval_seeds"]), 20))
    if not seeds:
        parser.error("설정의 평가 시드가 최소 하나 있어야 합니다.")
    initial = (args.init or args.model)
    if initial is not None:
        initial = initial.resolve(strict=True)
    reference = config.load(args.compare_config)
    for iteration in range(1, args.repeat + 1):
        timestamp = datetime.now(timezone.utc)
        folder = Path(course.TEAM) / "results" / "signal_experiments" / (
            f"{args.config}_{timestamp:%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}")
        folder.mkdir(parents=True)
        manifest = {
            "started_utc": timestamp.isoformat(), "iteration": iteration,
            "team_commit": revision(course.TEAM), "course_commit": revision(course.COURSE),
            "config": cfg, "comparison_config": args.compare_config,
            "config_changes": changes(reference, cfg),
            "input_model": str(initial) if initial else None,
            "input_model_sha256": digest(initial) if initial else None,
            "evaluation_seeds": seeds, "status": "running", "stages": {},
        }
        try:
            if args.model:
                checkpoint = initial
            else:
                train_dir = folder / "training"
                train_args = ["--config", args.config, "--run-dir", train_dir, "--ckpt-every", args.ckpt_every]
                if args.timesteps is not None:
                    train_args += ["--timesteps", args.timesteps]
                if args.seed is not None:
                    train_args += ["--seed", args.seed + iteration - 1]
                if args.init:
                    train_args += ["--init", initial]
                if args.ppo_fix:
                    train_args.append("--ppo-fix")
                if args.lr_end is not None:
                    train_args += ["--lr-end", args.lr_end]
                stage(folder, manifest, "training", "train_skku.py", *train_args)
                checkpoint = train_dir / "model.pt"
            manifest["checkpoint_sha256"] = digest(checkpoint)
            manifest["checkpoint"] = str(checkpoint)
            common = [checkpoint, "--config", args.config]
            replay = ["--nogui"] if args.headless_replay else ["--delay", args.gui_delay]
            replay_ok = True
            try:
                stage(folder, manifest, "replay_3", "test_skku.py", *common, "--episodes", 3, *replay,
                      gui=not args.headless_replay)
            except subprocess.CalledProcessError:
                replay_ok = False
                print("3회 재생 실행 실패. 다음 평가와 진단을 계속합니다.", flush=True)
            stage(folder, manifest, "evaluation_20", "test_skku.py", *common, "--episodes", 20, "--nogui")
            stage(folder, manifest, "signal_diagnostics", "eval_signals.py", *common,
                  "--episodes", 20, "--output", folder)
            manifest["status"] = "ok" if replay_ok else "partial"
        except BaseException:
            manifest["status"] = "failed"
            raise
        finally:
            write_manifest(folder, manifest)


if __name__ == "__main__":
    main()
