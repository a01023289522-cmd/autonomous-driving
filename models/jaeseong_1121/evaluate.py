"""Evaluate learned stop-line behavior on the unchanged SUMO route."""

import argparse
import json
import math
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path


ILWOL_EDGE = "5612296410"
ILWOL_SIGNAL = ("520991292", 10)
RED = ("r", "R")
WAITING = (*RED, "u")
GREEN = ("g", "G")
STOP_DISTANCE = (2.0, 5.0)
STOP_SPEED = 0.1
MIN_WAIT_SECONDS = 2.0
MIN_OPPORTUNITY_SECONDS = 5.0


@dataclass
class Approach:
    initial_m: float
    started_step: int
    step_length: float
    clear_steps: int = 0
    waiting_steps: int = 0
    reached_window: bool = False
    closest_stop_m: float | None = None
    trace: list | None = field(default=None, repr=False)

    def sample(self, step, distance, speed, clear, state):
        if self.trace is not None:
            self.trace.append(dict(step=step, distance_m=round(distance, 3), speed_mps=round(speed, 3),
                                   clear=clear, signal=state))
        if clear:
            self.clear_steps += 1
            if speed < STOP_SPEED and (self.closest_stop_m is None or distance < self.closest_stop_m):
                self.closest_stop_m = distance
        in_window = clear and speed < STOP_SPEED and STOP_DISTANCE[0] <= distance <= STOP_DISTANCE[1]
        self.waiting_steps = self.waiting_steps + 1 if in_window else 0
        self.reached_window |= self.waiting_steps >= math.ceil(MIN_WAIT_SECONDS / self.step_length)

    def finish(self, reason):
        waited = self.waiting_steps * self.step_length
        clear_time = self.clear_steps * self.step_length
        result = dict(
            signal=ILWOL_SIGNAL[0],
            link=ILWOL_SIGNAL[1],
            initial_m=round(self.initial_m, 3),
            started_step=self.started_step,
            eligible=clear_time >= MIN_OPPORTUNITY_SECONDS or reason == "red_entry",
            reached_window=self.reached_window,
            held_to_green=reason == "green" and waited >= MIN_WAIT_SECONDS,
            closest_stop_m=round(self.closest_stop_m, 3) if self.closest_stop_m is not None else None,
            clear_red_seconds=round(clear_time, 3),
            final_wait_seconds=round(waited, 3),
            end=reason,
        )
        if self.trace is not None:
            result["trace"] = self.trace
        return result


class IlwolTracker:
    """Track signal approaches without changing the model's observations or actions."""

    def __init__(self, env, traci, trace=False):
        self.env = env
        self.vehicle = traci.vehicle
        self.trace = trace
        self.reset()

    def reset(self):
        self.approach = None
        self.events = []
        self.red_entries = 0

    def close(self, reason):
        if self.approach is not None:
            self.events.append(self.approach.finish(reason))
            self.approach = None

    def observe(self, info):
        # The environment can mark the disappearance of a collided ego as a red entry.
        red_entry = bool(info.get("red_light")) and not info.get("collided")
        self.red_entries += red_entry
        speed = info.get("speed")
        distance = info.get("tls_distance_m", -1)
        state = info.get("tls_state")
        if self.approach is None and (state not in RED or not 0 <= distance <= 100):
            return
        ego = self.env.ego_id
        if speed is None or not 0 <= distance <= 100 or self.vehicle.getRoadID(ego) != ILWOL_EDGE:
            self.close("red_entry" if red_entry else "left_approach")
            return
        tls = self.env._tls_ahead()
        if tls is None or tls[:2] != ILWOL_SIGNAL:
            self.close("red_entry" if red_entry else "signal_changed")
            return
        if state in GREEN:
            self.close("green")
            return
        if state not in WAITING:
            self.close("other_signal_state")
            return

        leader = self.vehicle.getLeader(ego, 100)
        # TraCI measures the leader distance from ego's front bumper plus its minGap.
        clear = not (leader and leader[0] and leader[1] + self.vehicle.getMinGap(ego) < distance)
        if self.approach is None and state in RED and clear:
            self.approach = Approach(distance, self.env.step_count, float(self.env.step_length),
                                     trace=[] if self.trace else None)
        if self.approach is not None:
            self.approach.sample(self.env.step_count, distance, speed, clear, state)


def _run_episodes(model_path, config, seeds, trace):
    from local_env import LocalBEnv, traci
    import test_skku

    path = Path(config)
    cfg = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else test_skku.config.load(config)
    # A requested seed can overlap a training seed. Always use the default route and traffic.
    cfg["scenario"] = dict(cfg["scenario"], train_seeds=[])
    env = LocalBEnv(cfg, gui=False)
    tracker = IlwolTracker(env, traci, trace)
    step = env.step

    def observed_step(action):
        result = step(action)
        tracker.observe(result[4])
        return result

    env.step = observed_step
    try:
        agent = test_skku.course_load_agent()(str(model_path), env.observation_space.shape[0], env.action_space.shape[0])
        if isinstance(agent, tuple):
            agent = agent[0]
        for seed in seeds:
            env.use_seeds([seed])
            tracker.reset()
            metrics = test_skku.evaluate_policy(agent, env, n_episodes=1, deterministic=True)
            tracker.close("episode_ended")
            if env.seed_now != seed:
                raise RuntimeError(f"Expected seed {seed}, but SUMO used {env.seed_now}.")
            outcome = "collision" if metrics.collision_rate else "finish" if metrics.success_rate else "timeout"
            yield dict(seed=seed, outcome=outcome, red_entries=tracker.red_entries, approaches=tracker.events,
                       metrics=metrics.as_dict())
    finally:
        env.close()


def summarize(episodes):
    events = [item for row in episodes for item in row["approaches"] if item["eligible"]]
    distances = [item["closest_stop_m"] for item in events if item["closest_stop_m"] is not None]
    held = sum(item["held_to_green"] for item in events)
    return dict(
        episodes=len(episodes),
        finishes=sum(row["outcome"] == "finish" for row in episodes),
        collisions=sum(row["outcome"] == "collision" for row in episodes),
        timeouts=sum(row["outcome"] == "timeout" for row in episodes),
        red_entries=sum(row["red_entries"] for row in episodes),
        eligible_approaches=len(events),
        window_reached=sum(item["reached_window"] for item in events),
        held_to_green=held,
        held_to_green_rate=held / len(events) if events else None,
        stop_distance_samples=len(distances),
        closest_stop_median_m=statistics.median(distances) if distances else None,
    )


def evaluate_full(model_path, seeds, config=Path(__file__).with_name("config.json"), *, workers=1, trace=False):
    """Run a fixed set of full-route seeds, optionally in separate SUMO processes."""
    model_path = Path(model_path).resolve(strict=True)
    seeds = list(seeds)
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("Provide at least one seed, with no duplicates.")
    if workers < 1:
        raise ValueError("workers must be positive.")
    config = str(config)
    config_path = Path(config)
    if config_path.is_file():
        config = str(config_path.resolve())
    worker_count = min(workers, len(seeds))
    if worker_count == 1:
        episodes = list(_run_episodes(model_path, config, seeds, trace))
    else:
        def run(chunk):
            command = [sys.executable, "-X", "utf8", "-u", str(Path(__file__).resolve()), str(model_path),
                       "--config", config, "--worker", *map(str, chunk)]
            if trace:
                command.append("--trace")
            result = subprocess.run(command, capture_output=True, encoding="utf-8", errors="replace")
            if result.returncode:
                raise RuntimeError(f"Evaluation worker failed for seeds {chunk}:\n{result.stderr}{result.stdout}")
            return [json.loads(line.removeprefix("EPISODE ")) for line in result.stdout.splitlines()
                    if line.startswith("EPISODE ")]

        with ThreadPoolExecutor(max_workers=worker_count) as pool:
            chunks = [seeds[i::worker_count] for i in range(worker_count)]
            rows = {row["seed"]: row for group in pool.map(run, chunks) for row in group}
        if set(rows) != set(seeds):
            raise RuntimeError(f"Missing evaluation seeds: {sorted(set(seeds) - rows.keys())}.")
        episodes = [rows[seed] for seed in seeds]
    return dict(model=str(model_path), config=config, summary=summarize(episodes), episodes=episodes)


def parse_seeds(value):
    seeds = []
    try:
        for item in value.split(","):
            parts = item.split("-")
            if len(parts) == 1:
                seeds.append(int(item))
            elif len(parts) == 2:
                first, last = map(int, parts)
                if last < first:
                    raise ValueError("range end is smaller than its start")
                seeds.extend(range(first, last + 1))
            else:
                raise ValueError("invalid seed range")
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use seeds such as 1040-1059 or 1040,1044,1050-1059.") from error
    return seeds


def print_report(report):
    from local_env import LocalBEnv  # noqa: F401  Set up the project and course imports.
    from utils.evaluator import DrivingMetrics

    episodes = report["episodes"]
    for row in episodes:
        metrics = DrivingMetrics(**row["metrics"])
        print(f"seed={row['seed']} | {metrics.summary()} | {metrics.ep_length:.0f} steps")

    s = report["summary"]
    total = s["episodes"]
    print(f"\n전체 {total}회 | 완주 {s['finishes']}회 ({s['finishes']/total:.0%}) | "
          f"충돌 {s['collisions']}회 ({s['collisions']/total:.0%}) | "
          f"시간초과 {s['timeouts']}회 | 적색 신호 진입 {s['red_entries']}회")
    if not s["eligible_approaches"]:
        print("일월로 | 정차를 평가할 수 있는 적색 접근 0회")
        return
    distance = s["closest_stop_median_m"]
    median = f"{distance:.2f}m" if distance is not None else "측정값 없음"
    print(f"일월로 | 녹색까지 목표 정차 {s['held_to_green']}/{s['eligible_approaches']}회 "
          f"({s['held_to_green_rate']:.0%}) | 정지선 거리 중앙값 {median}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("--config", default=str(Path(__file__).with_name("config.json")), help="Experiment name or saved config.json.")
    parser.add_argument("--seeds", type=parse_seeds, default="1040-1059")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--json", action="store_true", help="콘솔에 JSON 요약 출력")
    parser.add_argument("--trace", action="store_true", help="Record per-step diagnostics for each Ilwol approach.")
    parser.add_argument("--worker", type=int, nargs="+", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        for row in _run_episodes(args.model, args.config, args.worker, args.trace):
            print("EPISODE " + json.dumps(row), flush=True)
        return

    report = evaluate_full(args.model, args.seeds, args.config, workers=args.workers, trace=args.trace)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report["summary"], indent=2))
    else:
        print_report(report)
        if args.output:
            print(f"상세 결과 저장: {args.output}")


if __name__ == "__main__":
    main()
