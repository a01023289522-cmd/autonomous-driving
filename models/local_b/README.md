# local_b 일월로 정차 재생

프로젝트의 SUMO·Python 환경과 수업 저장소를 준비한 뒤 Windows에서 `play_sumo.cmd`를 더블클릭한다. 수업 저장소 위치는 프로젝트 기본 방식 또는 환경 변수 `COURSE_REPO`로 지정할 수 있다.

기본값은 시연에 사용한 교통 시드 1054, 전체 경로, 1회 주행이다. 이 시드의 원본 기록은 일월로 정지선 2.967m 앞에서 녹색 전 12.5초 대기, 951스텝 완주다.

원본 시연에는 SUMO 1.27.1을 사용했다. 시드 1054에서는 함께 제공하는 `traffic_1054.xml.gz`에서 600초간 형성된 배경 교통과 난수 상태를 불러온 뒤, PPO 모델이 직접 주행한다. 다른 시드에서는 프로젝트의 기본 교통 생성 방식을 사용한다.

프로젝트 루트에서 화면 없이 확인하려면 `python models/local_b/replay.py --nogui`를 실행한다. 다른 교통을 보려면 `--seed 1096`처럼 시드를 지정한다. 재생기는 같은 폴더의 원본 가중치 `far_passed.pt`와 `config.json`을 사용한다.

## 추가 학습과 전체 경로 20회 평가

`local_env.py`에서 정지선 관측을 만들고, `train.py`에서 일월로 정차 보상으로 `far_passed.pt`를 이어 학습한다. 최초 모델의 단계별 학습 소스와 당시 실험 변경분은 [학습 당시 패치](history/local_b_training_changes.patch)에 보관했다. 최초 실험의 관측 샘플 `anchors.pt`는 이 패치에 포함되어 있지 않으며, 아래의 추가 학습에는 필요하지 않다.

프로젝트 루트에서 다음 명령을 순서대로 실행한다. 학습은 빈 결과 폴더를 새로 만들며 가중치는 그 안의 `model.pt`에 저장한다. 같은 명령을 다시 실행할 때는 새 결과 폴더를 지정한다.

```powershell
python models/local_b/train.py --output results/local_b_finetune
python models/local_b/evaluate.py results/local_b_finetune/model.pt --config results/local_b_finetune/config.json --seeds 1040-1059 --workers 4 --output results/local_b_finetune/eval20.json
```

학습과 평가는 같은 44개 관측을 사용한다. 학습에서는 일월로의 빈 적색 접근에서 정지선 2~5m 앞에 멈추고 녹색까지 유지하면 보상을 더한다. 평가는 일반 교통에서 기본 출발점부터 진행하며 각 시드의 완주·충돌·시간초과, 적색 진입 횟수, 일월로 정차 거리와 유지 여부를 기록한다. 두 명령 모두 SUMO 창 없이 실행된다. 새 모델을 직접 보려면 `python models/local_b/replay.py --model results/local_b_finetune/model.pt --seed 1054`를 실행한다.
