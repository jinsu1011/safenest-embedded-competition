# SafeNest MR60BHA2 ESP 안정화 보고서

STATUS: **BLOCKED**

코드·재생 검증은 완료했으나 현재 Mac에서 ESP USB 장치가 인식되지 않아 새 펌웨어 업로드 후 30분 물리 검증을 수행하지 못했다. 의료 정확도 또는 무호흡 검출 완료 상태가 아니다.

## BASELINE

- 센서: Seeed MR60BHA2, ESP-WROOM-32 UART2(GPIO16 RX, GPIO17 TX), 115200 8N1.
- MR60 펌웨어 버전: 현재 protocol 응답과 기존 로그에서 값을 받지 못해 `UNKNOWN`. 승인 없는 MR60 펌웨어 업데이트는 하지 않았다.
- 기존 ESP collector: `tiny-frame-v1`; 새 ESP firmware: `safenest-mr60-esp/1.1.0`.
- 빌드 환경: PlatformIO Core, espressif32 7.0.1, Arduino-ESP32 3.20017.241212, Xtensa toolchain 8.4.0+2021r2-patch5.
- 수집 조건:
  - 빈 공간 360초(워밍업 60초 뒤 299.893초 분석).
  - 가슴 정면 약 0.8–1.0m 정지 1인 360초(워밍업 60초 뒤 299.831초 분석).
  - 진입→정지→퇴장 20회.
  - 12/15/20rpm: 각 60초 워밍업+180초 cue 기반 측정.
- 빈 공간: 2,999/2,999 presence=false, 거리/호흡/심박 양수값 0, checksum/parse 오류율 0/0, 관측 재부팅 0.
- 정지 1인: 2,998/2,998 presence=true, 거리 평균/중앙값/표준편차 85.46/86.10/1.80cm, checksum/parse 오류율 0/0, 관측 재부팅 0.
- 정지 1인 vendor 호흡수 평균/중앙값/표준편차 22.68/24.0/4.88rpm. 기준 호흡계가 없는 자연호흡 구간이므로 정확도 근거로 사용하지 않는다.
- 정지 1인 vendor 심박수 평균/중앙값/표준편차 83.56/84.0/13.38bpm. 기준 심박계가 없어 `UNVERIFIED`다.

## CHANGES

- ESP 상태 `WARMUP/VALID/UNKNOWN/FAULT`와 원시·stable 재실, field age, error code, firmware/config hash 텔레메트리를 구현했다.
- ESP 유효성 설정:
  - frame timeout 1,000ms(실측 frame rate 약 60–76 frame/s 대비 보수적 한계).
  - 연속 UART 오류 5회 시 FAULT.
  - 재실 최근 3샘플 중 2개.
  - 대상 재실 후 WARMUP 60초.
  - phase age 500ms, 거리 age 1,000ms, vital age 2,000ms.
  - 호흡 유효거리 40–150cm.
- vendor rate에 raw/MA5/median5/EMA0.3/median+EMA를 동일 로그로 비교했다.
- 평활 필터는 채택하지 않았다. 가장 좋은 median+EMA도 표준편차·MAE 개선이 미미하고 평균 0.433초 지연 및 추가 이상치를 만들었다.
- Pi adapter에서 30초 `breath_phase` FFT를 최종 호흡수로 선택했다. vendor 호흡수는 원시 진단값만 전달한다.
- 심박은 원시 표시값만 전달하고 `heart_verified=false`, confidence 최대 0.25로 제한했다.
- 0/NaN/null/timeout/부재/gap은 window를 초기화하고 UNKNOWN 또는 FAULT로 유지한다.
- 미검증 무호흡/AI 후보는 DEGRADED이며 `apnea_verified=true`인 별도 검증 경로만 위험 오버라이드를 허용한다.

## RESULTS

| 항목 | raw/기준 | 채택 결과 |
|---|---:|---:|
| vendor pooled 표준편차 | 4.396rpm | 필터 미채택(phase FFT 사용) |
| median+EMA pooled 표준편차 | 4.359rpm | 미채택 |
| vendor pooled MAE | 3.804rpm | 필터 미채택 |
| median+EMA pooled MAE | 3.791rpm | 미채택 |
| raw 유효률 | 99.481% | 결측 보간 안 함 |
| median+EMA 유효률 | 99.296% | 결측 보간 안 함 |
| median+EMA 추가 지연 | - | 약 0.433초 |
| phase FFT 12/15/20rpm | - | 12.34/15.01/20.01rpm |
| 빈 공간 오탐 | 0/2,999 | 0 |
| 정지 1인 미탐 | 0/2,998 | 0; 100% 감지 |
| 진입 raw 지연 | 평균 1.134초, 최대 2.449초 | 2-of-3 계산상 20/20이 2초 이내 |
| 퇴장 raw 해제 | 평균 약 15.49초 | MR60 내부 지연 한계, 19/20 완료 |
| UART checksum/parse 오류율 | 채택 로그 | 0% / 0% |
| 30분 ESP 안정성 | 미수행 | BLOCKED |

테스트 결과:

- ESP PlatformIO build 성공: RAM 22,088/327,680 bytes(6.7%), Flash 266,577/1,310,720 bytes(20.3%).
- Pi 전체 회귀: LiteRT 2.1.6 환경에서 80 tests PASS, Thermal NPZ 미포함 테스트 2개 SKIP.
- 실측 로그 replay: 12/15/20rpm 중앙 추정값이 각 목표 ±1rpm 이내.

## FILES

- ESP firmware/config: `firmware/esp_wroom32_mr60_monitor/src/main.cpp`, `include/mmwave_config.h`, `config/mmwave_sensor_config.json`.
- filter 분석: `compare_breath_filters.py`, `analysis/breath/2026-07-28_breath_filter_comparison.json`.
- Pi adapter/config: `SafeNest_V4_OnDevice_AI/adapters/mr60_esp_adapter.py`, `run_mr60_serial_adapter.py`, `config/mmwave_processing.json`.
- 위험도 안전 계약: `SafeNest_V4_OnDevice_AI/risk/`, `integrated_node/safenest_risk_engine.py`, `sensors/mmwave/mmwave_adapter.py`.
- 원본 manifest: `SafeNest_V4_OnDevice_AI/datasets/mmwave/mr60_20260728_manifest.json`.
- 통합 절차: `SafeNest_V4_OnDevice_AI/docs/MR60_INTEGRATION.md`.
- 채택 원본 로그: manifest에 SHA-256과 함께 명시된 6개 JSONL. 중단·사전시험 로그는 보존하되 제출 manifest에서 제외했다.

## RISKS

- MR60 vendor 호흡수는 실측 속도별 편향이 달라 고정 보정할 수 없다.
- phase FFT는 30초 창이 필요하므로 대상 진입 직후에는 WARMUP이며 즉시 생체값을 제공하지 않는다.
- MR60 자체 퇴장 해제 지연이 약 15초로, ESP 시간필터만으로 2초 퇴장 목표를 달성할 수 없다. Pi에서 PIR/Thermal과 융합해야 한다.
- 심박은 외부 기준기기 동시 로그 전까지 정확도를 주장하거나 단독 위험 근거로 사용할 수 없다.
- 현재 데이터는 1인 정면 축소 프로토타입 조건이다. 천장/광각/다인 환경으로 일반화할 수 없다.
- 무호흡 실험은 수행하지 않았으며 위험한 숨참기 시험을 해서는 안 된다.

## NEXT

ESP를 USB 데이터 케이블로 다시 연결한 뒤, 기본 채팅에서 **ESP firmware 1.1.0 업로드 및 빈 공간 30분 검증 실행** 승인을 받는다. MR60 센서 자체 펌웨어는 업데이트하지 않는다.
