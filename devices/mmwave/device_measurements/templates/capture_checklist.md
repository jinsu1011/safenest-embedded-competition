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
