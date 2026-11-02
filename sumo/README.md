# SUMO 도로망 (성균관대역 일대)

박준수 작업물. **지금 쓰는 것은 `skku_map/`** 이고, 나머지는 앞선 시도라 참고용으로 남겼다.

| 폴더 | 내용 |
|---|---|
| [`skku_map/`](skku_map/) | **현재 도로망.** 사용법은 [`skku_map/README.md`](skku_map/README.md) |
| [`skku_map/HISTORY.md`](skku_map/HISTORY.md) | ⭐ **만든 과정과 시행착오** (1차 → 2차 → 3차, 무엇이 왜 안 됐는지) |
| [`skku_map/WORKLOG.md`](skku_map/WORKLOG.md) | 날짜별 작업 기록, 위성사진 차로 조사 결과 |
| `skku_area/` | 1차 시도: OSM 통째로 불러오기 (버림) |
| `skku_schematic/` | 2차 시도: 연결은 손으로, 모양만 OSM (버림) |
| `underpass/` | 지하차도 표현 실험 |
| `course_repo_changes/` | 수업 저장소(bmil-ssu) 코드에 한 수정분: `course_repo.patch`(`env/`, `view_road.py`), 학습률 실험 스크립트. `BASE_COMMIT.txt`의 커밋 위에 `git apply`로 적용 |

## 바로 보기
SUMO 1.27.1 설치 후 (Windows):
```
cd sumo/skku_map
run_skku.bat
```
또는 `sumo-gui -c skku.sumocfg`. 도로망을 다시 만들려면 `python -X utf8 build.py` (OSM 원본은 `skku_area/`, `skku_schematic/`에 있어 같이 받아야 한다).
