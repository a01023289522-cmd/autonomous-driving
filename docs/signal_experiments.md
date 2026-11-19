# 정문 신호·정지선 반복 실험

저장소 최상위에서 같은 Conda 환경으로 실행한다. 기본 학습량은 `base`의 20만 스텝이다. `--repeat 2`는 같은 설정으로 두 번 독립 학습하고 각각 평가한다. `--seed 42`를 같이 주면 각 학습에 42, 43을 적용한다.

```bash
conda activate sumo-rl
python -X utf8 rl/run_signal_experiments.py --config base --repeat 2
```

기존 팀 모델의 기준 수치를 먼저 얻고, 관측·지도·교통을 공유하는 후보를 비교할 수도 있다. 아래 후보에는 `r_s8` 대비 `red_wait_penalty`만 설정에서 추가했다. 이 실험의 결과는 새로 학습한 모델과 고정 모델을 비교한다. 보상 항의 효과를 분리하려면 같은 초기 모델에서 같은 학습 옵션으로 `r_s8`도 추가 학습해 비교한다.

```bash
python -X utf8 rl/run_signal_experiments.py --model models/best_1119_s8.pt --config r_s8 --compare-config r_s8
python -X utf8 rl/run_signal_experiments.py --config r_gate_wait --compare-config r_s8 \
  --init models/best_1119_s8.pt --timesteps 100000 --ppo-fix --ckpt-every 25000 --lr-end 0.000025
```

학습·평가 내역은 `results/signal_experiments/` 아래 실행마다 새 폴더에 남긴다. GUI는 첫 세 평가 시드에서 자동 재생하고, 속도를 늦추려면 `--gui-delay 30`처럼 스텝당 지연(ms)을 지정한다. 디스플레이 없는 Ubuntu 환경의 3회 실행 확인에는 `--headless-replay`를 붙인다. 수동 화면 검토 없이도 이후 20회 정량 평가와 사건 기록이 실행된다. `LIBSUMO_AS_TRACI=quiet`를 설정한 경우에도 GUI 단계에는 TraCI를 쓴다.

| 파일 | 내용 |
| --- | --- |
| `run.json` | 사용한 명령, 시작·최종 모델 해시, 코드 커밋, 설정 전체와 변경값, 시드, 단계별 소요 시간·종료 상태 |
| `training/` | 모델, 체크포인트, 학습 설정, 학습 곡선 |
| `evaluation_20.log` | 기존 평가기의 완주율, 충돌률, 시간초과율, 속도 등 |
| `signal_report.md`, `signal_summary.json` | 전체와 정문 진입 수, 적색 진입, 정지선 거리, 대기열 간격 요약 |
| `signal_episodes.jsonl` | 각 사건의 시드, 위치, 직전·직후 신호색, 정차 위치와 추정 원인. 실패 시 직전 12스텝의 속도·조작·신호·앞차 정보 |

## 판정 기준

- 정문은 접근 엣지 `5612296410`의 2번 차로, 신호 `520991292`의 좌회전 연결 10번이다. 정문 엣지 도달과 좌회전 진입은 둘 다 기록한다. 다른 차로의 정차는 전체 정차 및 실패 위치에 남고 정문 좌회전 정차 집계에서 제외된다.
- 적색 진입은 동일 연결의 진입 차로에서 내부 차로 또는 출구 차로로 바뀐 스텝을 기준으로 센다. 진입 직전 신호색을 쓴다. 스텝 중 신호가 바뀐 사례는 따로 집계한다. 진입과 동시에 차가 충돌 제거돼 위치 확인이 불가능하면 종료 시점의 신호 플래그와 충돌 정보를 남긴다.
- 정차는 속도 0.1 m/s 미만의 상태가 5초 지속된 사건이다. 적색·황색 때 정지선 앞에 앞차가 있는 경우에는 차간거리를, 선두이면 정지선까지 거리를 센다. 20 m 초과 정차 횟수는 선두 정차만 포함한다. 교차로 내부 정차, 교차로 통과 직후 정지선에서 15 m 이내 정차, 녹색에 앞이 비어 있는 정차도 기록한다.
- 20회는 개발 중 점검이다. 최종 팀 모델 판단에는 `docs/plan_1119.md`의 200회 기준을 적용한다. 진입·정차가 관측되지 않은 지표는 표본 수 0 및 비율이나 중앙값 없음으로 처리한다.
- 같은 정차라도 차량이 잠깐 이동하거나 선두·대기열 상태가 바뀌면 새로운 사건이 시작될 수 있다. 실패 원인 항목은 로그로 확인할 가설이다.

TraCI 값의 정의는 [Vehicle Value Retrieval](https://sumo.dlr.de/docs/TraCI/Vehicle_Value_Retrieval.html)과 [Traffic Lights Value Retrieval](https://sumo.dlr.de/docs/TraCI/Traffic_Lights_Value_Retrieval.html)을 참고한다.
