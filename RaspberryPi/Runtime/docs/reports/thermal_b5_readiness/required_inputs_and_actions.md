# 차단 해제를 위한 입력과 작업

## 필요한 입력

- FLOAT reference: `/var/lib/safenest/artifacts/thermal/SMALL_CNN_BASELINE_V1_P1_float32.tflite`
  - SHA-256: `fbe891520f07e0534b1a7074dc819d8ed44bca58b27e35c78916c3ddae73a779`
  - 크기: 1,252,048 bytes
- 원본 실제 snapshot: `/var/lib/safenest/validation/thermal_b5/mi48_real_snapshot/`
- 저장 Runtime 프레임: `/var/lib/safenest/validation/thermal_b5/saved_runtime_frames.npz`
- 독립 라벨 고정 테스트 manifest: `/var/lib/safenest/validation/thermal_b5/locked_test/manifest.json`
- 이미지 증거: `/var/lib/safenest/validation/thermal_b5/scenarios/01_*.png`부터 `08_*.png`

원본 프레임·라벨·개인정보 가능 데이터는 Git에 추가하지 않는다.

## 입력 계약

- NPZ `frames`: `uint16[N,62,80]`
- NPZ `timestamps`: finite Unix seconds `[N]`
- NPZ `frame_sequences`: `uint32[N]`
- 센서 단위 근거: `MI48_UINT16_0P1_KELVIN`
- 방향 근거: `NATIVE_ROWS_62_COLS_80_MATCHES_TRAINING_CANONICAL`
- 라벨: `NOT_HUMAN`, `HUMAN_NORMAL`, `HUMAN_FALL`; 단 `HUMAN_FALL`은 실제 낙상 label이 아니라 LYING 파생 proxy라는 provenance를 유지한다.

## 승인 후 작업 순서

1. Pi/센서 읽기 중심 조사로 실제 repo 경로, Python/OS/CPU, venv, 실행 프로세스, 포트와 데이터 단위를 확인한다.
2. 위 입력을 승인된 저장소에 배치하고 SHA/manifest를 고정한다.
3. FLOAT↔INT8 동등성, 독립 라벨 정확도/recall/F1/혼동행렬/조건별 3회 이상 반복을 수행한다.
4. 후보 전용 saved-frame Pi benchmark로 latency p50/p95/p99, inference-only FPS, RSS, SoC 온도, saturation을 기록한다.
5. 운영 selector는 그대로 둔 채 shadow/diagnostic live sensor 30분 soak와 8개 시나리오를 수행한다.
6. 필수 전체 회귀를 green으로 만들고 rollback drill을 실행한다.
7. 모든 게이트 PASS 후 별도 승인을 받아 selector diff, 서비스 재시작, 보고서 갱신, commit/push/PR을 수행한다.

## 실센서 NPZ와 시나리오 증거 캡처 명령

Pi `.env`에서 승인된 데이터 루트를 설정하면 기존 `sensor_logger`가 아래와 같은 NPZ를 쓴다. Runtime과 서비스 재시작은 별도 승인 후 담당자가 수행한다.

```bash
SAFENEST_SENSOR_DATA_ROOT=/var/lib/safenest/validation/thermal_b5/runtime_capture
# 생성 위치:
# /var/lib/safenest/validation/thermal_b5/runtime_capture/thermal/YYYYMMDD_HHMMSS_ffffff_seq-seq.npz
```

OpenCV 사용 가능 여부를 먼저 확인한다. 실패하면 사용자 승인 없이 설치하지 않는다. 승인 시 설치 대상은 Pi의 SafeNest venv 안 `opencv-python-headless`다.

```bash
cd /home/pi/safenest/team-safenest-embedded/RaspberryPi/Runtime
../../.venv/bin/python -c 'import cv2; print(cv2.__version__)'
```

각 시나리오에서 운영자가 정답 자세와 프레임 index를 확인한 뒤 다음 명령을 실행한다. `--scenario`는 `scenario_evidence.csv`의 8개 값 중 하나다.

```bash
../../.venv/bin/python hil/thermal_b5_scenario_capture.py \
  --input-npz /var/lib/safenest/validation/thermal_b5/runtime_capture/thermal/APPROVED_CAPTURE.npz \
  --scenario EMPTY_ROOM --frame-index 0 \
  --output-dir /var/lib/safenest/validation/thermal_b5/scenarios \
  --raw-output-dir /var/lib/safenest/validation/thermal_b5/captures \
  --orientation-contract NATIVE_ROWS_62_COLS_80_MATCHES_TRAINING_CANONICAL \
  --physical-unit-contract MI48_UINT16_0P1_KELVIN
```

도구는 동일 프레임의 OpenCV PNG, 터미널 판정 PNG, 단일 프레임 NPZ, timestamp/confidence/latency/validity/identity JSON을 함께 만든다. saved-frame replay이므로 이 latency를 live end-to-end latency라고 기록하지 않는다.
