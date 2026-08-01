# MR60BHA2 다음 세션 실행 체크리스트

이 파일은 다음 채팅 또는 다른 팀원이 **기존 시험을 반복하지 않고 남은 물리 검증만 이어가기 위한 단일 기준 문서**다.

## 0. 시작 상태

- Git branch: `codex/mmwave-phase-integration`
- 기준 commit: `f0561d688807b5ec4cd3f2dd7b82fb1ee228b77a`
- ESP 대상: ESP-WROOM-32 (`esp32dev`), MR60은 UART2 RX=GPIO16/TX=GPIO17
- 새 ESP firmware: `safenest-mr60-esp/1.1.0`
- ESP config SHA-256: `db2e2b0b87c093531b7312d09925d987d089c6cb344e166a094b2f41af64f0b2`
- 2026-08-01 해소: A·B단계 완료. 포트 `/dev/cu.usbserial-10` (CH340 `1A86:7523`), 칩 ESP32-D0WD-V3 rev v3.1, MAC `cc:7b:5c:f2:1f:ec`.
- 현재 blocker: 없음. C단계(빈 공간 30분)부터 이어서 진행한다.
- 주의: 2026-08-01 세션 중 ESP32-C6(`cu.usbmodem101`, ESP32-C6FH4)를 잠시 연결했으나 본 펌웨어와 비호환(`board=esp32dev`, `HardwareSerial(2)`, USB CDC 미설정)이라 원래 WROOM-32으로 되돌렸다. 보드를 바꾸려면 펌웨어 포팅과 config 해시 갱신이 선행되어야 한다.
- MR60 센서 자체 firmware는 승인 없이 업데이트하지 않는다.

## 1. 다시 하지 않을 작업

다음 항목은 완료됐으므로 처음부터 재수집하거나 임계값을 다시 고르지 않는다.

- [x] 빈 공간 6분과 0.8–1.0m 정지 1인 6분 기준선
- [x] 진입→정지→퇴장 20회 기존 기준선
- [x] 12/15/20rpm 각 60초 warmup+180초 측정
- [x] raw/이동평균/중앙값/EMA/중앙값+EMA 동일 로그 비교
- [x] vendor 호흡수 필터 미채택 결정
- [x] Pi `breath_phase` 30초 FFT 선택
- [x] 0/null/NaN/timeout/부재의 UNKNOWN/FAULT 처리
- [x] 심박 `UNVERIFIED`, 무호흡 `apnea_verified=false` 안전 계약
- [x] Pi 전체 회귀 80 PASS, 2 SKIP

채택된 원본 6개의 경로와 SHA-256은 `SafeNest_V4_OnDevice_AI/datasets/mmwave/mr60_20260728_manifest.json`이 기준이다. `preflight`, `attempt02`, `quickcheck`, `retry` 파일은 실패·진단 기록이므로 최종 통계에 넣지 않는다.

## 2. 사용자가 준비할 것

- [ ] ESP-WROOM-32 + MR60 기존 4선 배선 유지
- [ ] USB **데이터** 케이블
- [ ] 센서를 흔들리지 않게 고정할 거치대
- [ ] 가슴 중심과 센서 안테나 면을 같은 높이로 맞출 공간
- [ ] 바닥 거리표시 0.6/0.9/1.2/1.5m
- [ ] 전방 1.5m 안의 움직이는 물체·선풍기 바람·커튼 제거
- [ ] 심박 검증 단계에서 Apple Watch와 착용자 1명

금지 시험: 숨참기, 과호흡, 밀폐공간, 가스 주입. 평소처럼 자연 호흡한다.

## 3. 실행 순서

모든 명령은 저장소 최상위에서 실행한다. Python은 반드시 아래 프로젝트 가상환경을 사용한다.

```bash
firmware/esp_wroom32_mr60_monitor/.venv/bin/python
```

명령의 `YYYY-MM-DD`는 실제 시험일, `/dev/cu.usbserial-XXXX`는 A단계에서 확인한 실제 포트로 한 번만 치환한다.

### A. USB 포트 확인과 점유 해제

- [x] 2026-08-01 확인 완료: `/dev/cu.usbserial-10` 1개. 다음 명령에서 `/dev/cu.usb...` 포트 1개를 확인한다.

```bash
pio device list
ls /dev/cu.usb*
```

- [x] 2026-08-01 `lsof` 결과 점유 프로세스 없음. 대시보드·시리얼 모니터가 실행 중이면 `Ctrl+C`로 종료한다. 캡처와 대시보드는 같은 포트를 동시에 열지 않는다.

```bash
lsof /dev/cu.usb*
```

종료 기준: 포트가 보이고, 업로드 직전 다른 프로세스가 점유하지 않는다.

### B. 새 ESP firmware 업로드

- [x] 2026-08-01 업로드 완료(해시 검증 통과, RAM 6.7%/Flash 20.3%). MR60 firmware가 아니라 ESP firmware만 업로드한다.

```bash
cd firmware/esp_wroom32_mr60_monitor
pio run
pio run -t upload --upload-port /dev/cu.usbserial-XXXX
cd ../..
```

- [x] 2026-08-01 완료: `logs/final/2026-08-01_healthcheck_v110_15s.jsonl`, 통과 기준 5개 전부 충족. 업로드 후 15초 health check를 저장한다.

```bash
firmware/esp_wroom32_mr60_monitor/.venv/bin/python \
  firmware/esp_wroom32_mr60_monitor/capture_serial.py \
  --port /dev/cu.usbserial-XXXX --duration 15 \
  --output firmware/esp_wroom32_mr60_monitor/logs/final/YYYY-MM-DD_healthcheck_v110_15s.jsonl
```

통과 기준:

- boot event의 firmware가 `safenest-mr60-esp/1.1.0`
- config hash가 이 문서 0절과 동일
- JSON이 연속 출력됨
- `checksum_errors`, `parse_errors`가 증가하지 않음
- `sensor_state`가 계속 `FAULT`가 아님

실패 시: RX/TX 교차, 공통 GND, 5V, 포트 점유를 한 번씩 확인한다. 같은 업로드/배선을 두 번 확인해도 실패하면 반복하지 말고 로그와 원인을 `PROJECT_PROGRESS.md`에 기록한다.

### C. 빈 공간 30분

- [ ] 감지 원뿔에서 사람과 반려동물이 완전히 벗어난 상태로 1,800초 수집한다.

```bash
firmware/esp_wroom32_mr60_monitor/.venv/bin/python \
  firmware/esp_wroom32_mr60_monitor/capture_serial.py \
  --port /dev/cu.usbserial-XXXX --duration 1800 \
  --output firmware/esp_wroom32_mr60_monitor/logs/final/YYYY-MM-DD_empty_v110_30min.jsonl

firmware/esp_wroom32_mr60_monitor/.venv/bin/python \
  firmware/esp_wroom32_mr60_monitor/analyze_mmwave_log.py \
  firmware/esp_wroom32_mr60_monitor/logs/final/YYYY-MM-DD_empty_v110_30min.jsonl \
  --output firmware/esp_wroom32_mr60_monitor/analysis/final/YYYY-MM-DD_empty_v110_30min_summary.json
```

통과 기준: ESP reboot 0, UART checksum/parse 오류율 보고, stable presence 오탐 0 목표, 호흡·심박 0을 유효값으로 세지 않음.

### D. 정지 1인 30분

- [ ] 센서 안테나 면–가슴 0.9m, 정면, 평소 호흡으로 1,860초 수집한다. 처음 60초는 warmup이고 분석에서 제외한다.

```bash
firmware/esp_wroom32_mr60_monitor/.venv/bin/python \
  firmware/esp_wroom32_mr60_monitor/capture_serial.py \
  --port /dev/cu.usbserial-XXXX --duration 1860 \
  --output firmware/esp_wroom32_mr60_monitor/logs/final/YYYY-MM-DD_occupied_d09_v110_31min.jsonl

firmware/esp_wroom32_mr60_monitor/.venv/bin/python \
  firmware/esp_wroom32_mr60_monitor/analyze_mmwave_log.py \
  firmware/esp_wroom32_mr60_monitor/logs/final/YYYY-MM-DD_occupied_d09_v110_31min.jsonl \
  --skip-seconds 60 \
  --output firmware/esp_wroom32_mr60_monitor/analysis/final/YYYY-MM-DD_occupied_d09_v110_after60s_summary.json
```

통과 기준: 분석 30분, ESP reboot 0, stable presence 감지율 95% 이상, UART 오류율 보고. 자연호흡 vendor 값은 정확도 기준으로 사용하지 않고 Pi phase 추정의 유효률·표준편차를 함께 계산한다.

### E. 거리 4종

- [ ] 0.6/0.9/1.2/1.5m에서 각각 120초 수집한다. 각 거리의 처음 60초는 warmup, 뒤 60초만 비교한다.
- [ ] 자세, 높이, 방향은 고정하고 거리만 한 번에 하나씩 바꾼다.

파일명:

```text
YYYY-MM-DD_occupied_d06_v110_120s.jsonl
YYYY-MM-DD_occupied_d09_v110_120s.jsonl
YYYY-MM-DD_occupied_d12_v110_120s.jsonl
YYYY-MM-DD_occupied_d15_v110_120s.jsonl
```

각 파일은 `capture_serial.py --duration 120`으로 수집하고 `analyze_mmwave_log.py --skip-seconds 60`으로 분석한다.

기록할 값: 줄자 거리, 센서 거리 평균/중앙값/표준편차, stable presence 감지율, phase 호흡 유효률, UART 오류율. 40–150cm 범위는 이 결과를 보기 전에는 변경하지 않는다.

### F. 새 firmware 진입·퇴장 20회

- [ ] 한 명만 진입하고 정지한 뒤 완전히 감지 원뿔 밖으로 나가는 시험을 20회 수행한다.

```bash
firmware/esp_wroom32_mr60_monitor/.venv/bin/python \
  firmware/esp_wroom32_mr60_monitor/entry_exit_trial.py \
  --port /dev/cu.usbserial-XXXX --trials 20 \
  --output firmware/esp_wroom32_mr60_monitor/logs/final/YYYY-MM-DD_entry_exit_v110_20.jsonl
```

기록할 값: raw와 stable 진입 지연, raw와 stable 퇴장 해제 지연, 미탐 횟수. 진입 전달 2초 목표를 확인한다. MR60 자체 퇴장 해제가 약 15초면 ESP 필터를 억지로 바꾸지 말고 `센서 한계/PI 융합 필요`로 기록한다.

### G. Apple Watch 심박 검증

- [ ] 위 C–F가 끝난 다음에만 수행한다.
- [ ] 0.9m 정면 고정, 60초 warmup 후 10분 자연호흡.
- [ ] ESP JSONL과 Apple Watch 심박을 같은 시계 기준으로 기록한다.
- [ ] Watch 심박은 최소 5초 간격으로 `timestamp, watch_bpm` CSV에 기록한다.
- [ ] MR60 표본과 최근접 시간으로 결합해 MAE, median absolute error, bias, Pearson correlation, 유효률을 계산한다.
- [ ] 데이터 확인 전 고정 오프셋이나 보정식을 만들지 않는다.
- [ ] 보정 전/후를 동일 원본으로 비교하고 개선될 때만 config/version을 갱신한다.

심박 채택 기준은 팀과 합의해 보고서에 명시한다. 기준을 통과하지 못하면 `heart_verified=false`를 유지하고 표시용으로만 사용한다.

## 4. 시험 중단 기준

- ESP reboot 발생
- `sensor_state=FAULT`가 연속 발생
- checksum/parse counter가 지속 증가
- 포트 연결 해제
- 사람이 없는 상태에서 stable presence가 계속 true
- 사용자 불편·어지러움·호흡 곤란

중단된 로그는 삭제하거나 덮어쓰지 않는다. 파일명에 `_failed_원인`을 붙이거나 manifest에서 `accepted=false`로 분리한다.

## 5. 최종 완료 조건

- [x] 새 ESP firmware 1.1.0 업로드 증거 (2026-08-01, 헬스체크 로그의 `firmware_version`·`config_hash`가 증거)
- [ ] 빈 공간 30분 reboot 0
- [ ] 정지 1인 30분 reboot 0, presence ≥95%
- [ ] UART frame/parse/checksum 오류율 계산
- [ ] 거리 4종 결과표
- [ ] 새 firmware 진입·퇴장 20회 결과
- [ ] 필터 전후 표준편차·결측률·유효률·지연표
- [ ] Apple Watch 심박 검증 또는 `UNVERIFIED 유지` 결론
- [ ] 새 로그 SHA-256 manifest 갱신
- [ ] `MMWAVE_TUNING_REPORT_2026-07-29.md` 결과 갱신
- [ ] 팀 통합 노드에서 실제 ESP USB JSONL 입력 확인

이 목록이 모두 끝나기 전 상태는 `BLOCKED`, 모두 근거와 함께 끝나면 `PASS`다.

## 6. 다음 세션에 보낼 한 줄

```text
MMWAVE_NEXT_SESSION_CHECKLIST.md를 먼저 읽고, 완료된 로그는 재수집하지 말고 A단계 USB 포트 확인부터 이어서 진행해. 각 단계가 끝날 때 PROJECT_PROGRESS.md와 이 체크리스트를 즉시 갱신해.
```
