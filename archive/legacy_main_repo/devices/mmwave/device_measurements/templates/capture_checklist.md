# M-C0 Capture Checklist

이 문서는 실제 측정 때 작성한다. 정상적인 자발 호흡 관찰만 수행하며, 숨 참기·과호흡·극단적 동작·밀폐/가스 환경을 시험 조건으로 사용하지 않는다.

## 시작 전

- [ ] `subject_id`와 `operator_id`는 이름이 아닌 pseudonym으로 정함
- [ ] MR60BHA2 model, device id, ESP firmware, sensor firmware, config hash를 기록함
- [ ] MR60BHA2 → ESP32 UART2 → USB serial 경로를 확인함
- [ ] 거리, 높이, 각도, 방향, 대상 자세, 의복/이불을 기록함
- [ ] 주변인 유무, 센서 시야 내 여부, 대략적 거리와 움직임을 기록함
- [ ] 영상·얼굴·이름을 수집하지 않음
- [ ] 독립 respiration reference의 종류와 동기화 여부를 기록함. 없으면 `none/not_collected`로 명시함

## 기록 중

- [ ] 정상 자발 호흡 상태를 관찰함
- [ ] raw JSONL을 수정·필터링·보간하지 않고 저장함
- [ ] serial timeout, packet error, presence loss, 주변 움직임을 시간과 함께 메모함
- [ ] reference가 있으면 센서 timestamp와 동기화함

## 종료 후

- [ ] raw 파일을 immutable 원본으로 보관함
- [ ] raw 파일 SHA-256, byte count, record count를 계산함
- [ ] `templates/session_manifest.planned.json`을 실제 값으로 채움
- [ ] `templates/environment_metadata.template.json`을 실제 값으로 채움
- [ ] `python3 validators/validate_contract.py --strict-warnings ...` 실행
- [ ] phase 단위·스케일을 확인하지 못했으면 `UNKNOWN`으로 남김
- [ ] `heart_verified`, `apnea_verified`, `deployment_ready`를 reference 없이 true로 바꾸지 않음

## CAP-2 / CAP-3 실행 조건 (2026-08-18 추가)

M-N4 계약(`MMWAVE_MR60_COMPAT_INPUT_DATASET_V1`)과 펌웨어 1.2.0 실측에서 나온 조건이다.

- [ ] 대상이 자리를 잡은 뒤 **60 초 이상** 기다린 다음 기록을 시작한다
      (`kWarmupMs = 60000`; 그 전 구간은 `TARGET_WARMUP` 이라 상태 판정이 무의미하다)
- [ ] 세션 길이는 `60 s + N × 30 s` 로 잡는다. 기본값 **4 분 = 창 6개**
- [ ] 거리는 `kDistanceMinCm 40` / `kDistanceMaxCm 150` 안에 둔다.
      PR18 파일럿의 45.9 cm 는 하단이며 `BREATH_PHASE_LOW_AMPLITUDE` 가 지배적이었다.
      CAP-3 기하 변형은 **80–100 cm** 를 우선 시도한다
- [ ] 기록 중 `sensor_state` / `error_code` 를 눈으로 확인한다.
      `BREATH_PHASE_LOW_AMPLITUDE` 가 계속 뜨면 `breath_phase_std` 가
      `kBreathMinPhaseStd = 0.2` 아래라는 뜻이다. 세션을 버리지 말고 **그대로 보존**한 뒤
      조건을 바꾼 재시도를 별도 세션으로 추가한다
- [ ] 0.4 s 이상 끊김이 생기면 해당 30 s 창 전체가 M-N4 에서 폐기된다.
      USB 케이블·터미널 스크롤·절전을 건드리지 않는다
- [ ] 종료 후 `python3 tools/cap0_m_n4_feasibility.py <raw.jsonl>` 을 실행하고
      `windows_accepted`, `windows_rejected`, `producer_non_valid_fraction` 을 세션 노트에 남긴다
- [ ] CAP-3 재부팅 세션은 재부팅 **전/후를 각각 별도 세션 ID** 로 기록한다
      (M-N4 `boot.window_may_cross_boot_or_restart: false`)
