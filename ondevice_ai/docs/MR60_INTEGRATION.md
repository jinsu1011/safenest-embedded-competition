# SafeNest MR60BHA2 → ESP-WROOM-32 → Raspberry Pi 통합 가이드

## 역할 경계

- ESP-WROOM-32: UART 프레임 파싱·체크섬, freshness/범위 검증, 재실 2-of-3 안정화, 상태와 원시값 패킷화.
- Raspberry Pi 5: `breath_phase` 30초 창 FFT, 센서융합, 위험도, AI, 저장·표시.
- MR60 vendor `breath_rate_raw`: 진단용이다. 실측에서 속도별 편향이 달라 고정 보정을 적용하지 않는다.
- MR60 `heart_rate_raw`: 외부 기준기기 동시 측정 전까지 표시용 `UNVERIFIED`이며 위험도에 반영하지 않는다.
- `0`, `null`, `NaN`, timeout, 재실 없음은 `UNKNOWN/FAULT`이다. 정상 호흡이나 무호흡으로 대체하지 않는다.

## 배선

전원을 끈 상태에서 교차 UART로 연결한다.

| ESP-WROOM-32 | MR60BHA2 |
|---|---|
| VIN/5V | 5V |
| GND | GND |
| GPIO16 / RX2 | TX |
| GPIO17 / TX2 | RX |

ESP는 Mac 또는 Pi USB에서 전원을 받을 수 있다. MR60 5V와 ESP GND는 반드시 공통이어야 하며, RX0/TX0는 USB 업로드·모니터와 충돌하므로 센서 UART에 사용하지 않는다.

## 재현 가능한 설정

- ESP 설정 원본: `devices/mmwave/firmware/config/mmwave_sensor_config.json`
- ESP 설정 SHA-256: `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`
- ESP 펌웨어: `safenest-mr60-esp/1.2.0`
- Pi 설정: `config/mmwave_processing.json`
- ESP UART: 115200 baud, 8N1, RX=GPIO16, TX=GPIO17
- ESP 상태: 1초 frame timeout, 연속 UART 오류 5회 FAULT, 재실 3개 중 2개, WARMUP 60초, 거리 40–150cm.
- Pi 호흡 추정: 10Hz, 30초 causal window, 5–40rpm band, gap 0.5초 초과 시 window reset.

## 빌드와 실행

저장소 최상위에서:

```bash
cd devices/mmwave/firmware
pio run
```

위 명령은 컴파일만 한다. ESP 업로드는 연결 포트를 확인하고 승인한 뒤 실행한다. MR60 자체 펌웨어는 업데이트하지 않는다.

Pi에서 ESP JSONL을 표준 `mmwave_mr60` 패킷으로 변환:

```bash
cd safenest-embedded-competition
python3 -m pip install -r requirements-pi.txt
python3 devices/mmwave/src/run_mr60_serial_adapter.py --port /dev/ttyUSB0
```

실제 ESP 입력을 통합 위험 엔진까지 전달하고 buffer·안전 metadata를 함께 확인:

```bash
python3 -m ondevice_ai.src.integrated_node.run_mr60_usb_node --port /dev/ttyUSB0
```

이 경로는 schema `1.2`, ESP firmware `safenest-mr60-esp/1.2.0`, ESP config
SHA-256을 엄격히 검사한다. 불일치·serial timeout·잘못된 JSON·timestamp
중복/역행·presence=false·0/null phase는 `UNKNOWN/FAULT`와 `DEGRADED`로
노출하고 통합 window를 비운다. 보존된 구형 로그만 재생할 때에는
`--allow-legacy-provenance`를 명시한다.

기존 실측 로그를 장비 없이 재생:

```bash
python3 devices/mmwave/src/run_mr60_serial_adapter.py \
  --allow-legacy-provenance \
  --replay devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl
```

## 유효 데이터와 검증

- manifest: `datasets/mmwave/mr60_20260728_manifest.json`
- 생성: `python3 devices/mmwave/firmware/build_valid_log_manifest.py`
- hash 검증: `python3 -m unittest tests/test_mr60_manifest.py -v`
- 어댑터/안전 계약: `python3 -m unittest tests.test_mr60_esp_adapter tests.test_risk_rules tests.test_mmwave_stream_adapter -v`

유효 데이터는 빈 공간 6분, 안정된 1인 6분, 진입/퇴장 20회, 12/15/20rpm 각각 워밍업 60초+측정 180초다. 사전 점검, 중단 시험, 실패 시험은 원본 보존 대상이지만 manifest와 학습/검증 집합에서는 제외한다.

## 실측 결과 요약

| 항목 | 결과 |
|---|---|
| 빈 공간 본 측정(워밍업 뒤 5분) | presence false 2999/2999 |
| 정지 1인 본 측정(워밍업 뒤 5분) | presence true 100%, 거리 약 86.1cm |
| UART checksum/parse | 채택 로그에서 0/0 |
| 진입 raw 지연 | 평균 1.134초, 최대 2.449초 |
| 2-of-3 적용 진입 목표 | 20/20이 2초 이내로 계산됨 |
| 퇴장 해제 raw 지연 | 평균 약 15.49초, 19/20 |
| phase 호흡 추정 | 12.34 / 15.01 / 20.01rpm |
| vendor 호흡수 | 목표별 MAE 2.61 / 3.80 / 5.02rpm; 최종값으로 부적합 |
| 심박수 | 외부 기준 없음; UNVERIFIED |

필터 비교에서 median+EMA는 raw 대비 pooled 표준편차 4.396→4.359rpm, MAE 3.804→3.791rpm에 그쳤고 평균 0.433초 지연과 추가 이상치를 만들었다. 따라서 단순성과 지연 기준에 따라 vendor rate 필터를 채택하지 않았다.

## 최종 물리 검증 상태

- schema 1.2 업로드·healthcheck: PASS.
- 빈 공간 30분: presence·생체·freeze 오탐 0, reboot·UART 오류 0으로 PASS.
- 정지 1인 30분: stable presence 98.77%, reboot·UART 오류 0으로 재실 KPI PASS.
- 자연호흡 장기 filtered 유효률: 21.58%로 FAIL. 유효하지 않은 구간은 DEGRADED/UNKNOWN으로 유지한다.
- 거리 0.6/0.9/1.2/1.5m와 진입·퇴장 20회: 기존 원본·해시·분석 검증 완료, 재수집 금지.
- 심박: 동기 기준기기가 없어 `UNVERIFIED`; 무호흡: 검증 데이터가 없어 `UNVERIFIED`.
- 남은 필수 통합 작업: 팀 통합 노드에서 실제 ESP USB JSONL 입력 확인.

의료 정확도, 심박 정확도, 무호흡 검출 완료로 발표하면 안 된다. 최종 근거는 `devices/mmwave/firmware/analysis/final/2026-08-01_mr60_final_validation_manifest.json`을 사용한다.
