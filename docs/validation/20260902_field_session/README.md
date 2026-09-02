# SafeNest 2026-09-02 현장 재검증

실기기 1시간판 검증 결과와 증적이다. 측정 장소는 `밀폐공간 A-01`, Raspberry Pi는
`192.168.0.8`, 평가 주기는 `1.0 s`였다.

## 포함 파일

- `00_RESULT.json`: `15_결과양식.json` 스키마에 맞춘 집계 결과
- `evidence/stream.slim.jsonl.gz`: 1초 API 캡처. 원본의 `heatmap_preview` 배열만 제거한 gzip본
- `evidence/marks.jsonl`: 단계 경계와 관측 이벤트
- `evidence/snapshots/`: V0 및 S3 단계 스냅샷
- `checksums.sha256`: 이 디렉터리 파일의 SHA-256

원본 `stream.jsonl`은 약 84.6 MB라서 Git 저장소 용량을 고려해 커밋하지 않았다. 슬림본은
`heatmap_preview`만 제거했으며 다른 필드는 유지했다. 원본은 로컬 전달 폴더의
`validation_runs/20260902_2230_live/evidence/stream.jsonl`에 보관되어 있다.

## 결과 요약

- V0 정합: PASS
- S1: 1,784개 폴링 스냅샷, 4채널 동시 LIVE 56.758%, 수신 연결 카운터 증가 220회
- S2: CO₂ 주의 진입은 관측됐으나 실제 `true → false` 해제 전이는 미관측
- S3: `INDETERMINATE`와 전채널 복구 127.809초 관측
- S0 환기 종료값은 1,552 ppm으로 900 ppm 목표를 초과

연결 불안정, S1 캡처 재개, S3 지연된 fail-closed 전파는 결과 JSON의 `anomalies`와
`not_performed`에 숨기지 않고 기록했다.

09-01 1차 현장 원본 결과 파일은 이 체크아웃에서 확인되지 않아 추정하거나 재생성하지 않았다.
