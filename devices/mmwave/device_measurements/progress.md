# Progress

## Completed

- 메인 저장소를 read-only로 확인하고 기준 커밋을 `fdf34b804f35e5868356f0ed6f804a248aa69131`로 고정
- MR60/ESP raw field contract와 M-C0 session manifest 작성
- mmWave 연결 없이 가능한 범위와 hardware-required 범위를 분리
- dependency-free validator 작성 및 synthetic fixture 검증
- 별도 로컬 Git repository의 초기 커밋 생성: `365b6fe`
- 메인 `devices/mmwave/firmware/logs/` JSONL 78개를 read-only로 내려받아 실제 raw scan 수행
- 기존 final manifest, CSV delivery manifest, offline candidate lock과 대조
- raw 파일 scope 차이, schema 세대 혼합, invalid line, cadence/gap/validity 결과 기록
- CSV delivery 9개 실제 파일의 SHA-256·record count·timestamp·column 대조
- 현재 `MMWaveCSVAdapter`로 CSV 620개 window replay
- 현재 `MR60ESPAdapter`로 raw JSONL 78개 replay 및 strict provenance/fail-closed 결과 확인
- preprocessing/scaler/quantization identity와 raw phase domain 통계 대조
- 오프라인 추가 결과를 `reports/offline_remaining_audit.md`와 JSON 결과 파일로 기록
- M-B11 locked Butterworth BPF/filtfilt 정확 재실행
- 620개 window int8 quantization·dequantization smoke test
- 정상/상수/NaN·Inf/짧은 입력 synthetic edge-case 검증
- CSV/JSONL one-command bundle audit와 strict negative tests 추가
- 실제 측정용 session manifest·환경 metadata·capture checklist 템플릿 추가
- USB serial raw 저장과 1초 주기 상태 표시 monitor 작성 및 기존 raw replay dry-run

## Verification

- `python3 validators/validate_contract.py --manifest fixtures/session_manifest.example.json --raw-jsonl fixtures/example.raw.jsonl --check-files` → `PASS`
- JSON 파일 4개 파싱 확인
- raw scan: 78개 JSONL, 172,390줄, 정상 JSON 172,387개, invalid 3개
- schema 1.2 scan: 69,750 records, timestamp 역행/중복 0, 최대 gap 200 ms, `heart_verified=true` 0
- CSV audit: manifest SHA-256 9/9, record count 9/9, timestamp 위반 0, adapter window 620개
- ESP adapter replay: sensor-like 159,368개, schema mismatch 89,618개, output valid 31,328개, `heart_verified=true` 0
- BPF exact replay: 임시 runtime의 `scipy 1.18.0`으로 620개 window 실행, finite·clip·int8 saturation 모두 통과
- quantization: int8 범위 -12~9, saturation 0%, dequantization MAE 약 0.00865676
- negative tests: backward timestamp·malformed JSON·duplicate timestamp·privacy violation 4/4 검출
- TFLite 실제 `invoke` 완료: locked SHA-256 model로 620회 성공, host p95 latency 약 0.008333 ms; label alignment 부재로 accuracy/F1은 산출하지 않음
- live monitor dry-run: 10.00Hz, max gap 103ms, JSON/UART/checksum 오류 0/0/0, 30초 window READY
- 메인 작업 폴더의 기존 파일은 수정하지 않음. 별도 레포 디렉터리만 새로 생성됨.

## Pending: mmWave 연결 후

- 실제 MR60 → ESP32 → USB JSONL 기록
- 실제 cadence/gap/jitter/packet error와 phase semantics 확인
- 독립 reference 동기화가 필요한 세션 기록
- 실제 환경·거리·자세·방향·주변 움직임 metadata와 raw checksum 추가
- Pi end-to-end가 범위에 들어오면 별도 runtime evidence 추가

## Offline completion boundary

센서 없이 가능한 기존 자료 감사·CSV 대조·adapter replay·입력 계약 비교·locked preprocessing replay·quantization smoke test·negative test·측정 템플릿 작성은 완료했다. 새 환경 capture, 독립 reference 동기화, phase semantics, MR60→ESP32→USB→Pi E2E, 실제 장치 raw의 locked preprocessing 검증은 mmWave 연결 후 수행한다.
