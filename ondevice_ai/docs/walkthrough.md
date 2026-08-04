# SafeNest V4 On-Device AI 요약 워크스루 (Walkthrough)

SafeNest V4 온디바이스 AI 시스템의 구성, 모델 검증 결과, 실시간 파이프라인 흐름 및 테스트 통과 내역을 요약한 한국어 기술 문서입니다.

---

## 1. 파이프라인 구성 요약

1. **센서 어댑터 층 (`devices/<device>/src/` + `shared/contracts/`)**:
   - `thermal44`: 80x62 IR thermal array 프레임 파서 및 드라이버.
   - `mmwave`: Seeed MR60BHA2 60GHz mmWave 바이탈 신호 링버퍼 파서 (300 샘플 윈도우).
   - `co2`: SCD40 CO2 센서 데이터 파서 (CO2 slope, 습도, CO2 ppm).
   - `pir`: PIR 인체 감지 센서 파서.

2. **TFLite 모델 추론 층 (`ondevice_ai/src/inference/`)**:
   - `thermal_interpreter.py`: Thermal-44 INT8 TFLite (`[1, 62, 80, 1]`) 추론 wrapper.
   - `mmwave_interpreter.py`: mmWave INT8 TFLite (`[1, 300, 1]`) 추론 wrapper.
   - `co2_interpreter.py`: CO2 INT8 TFLite (`[1, 3]`) 추론 wrapper.

3. **위험도 융합 엔진 (`ondevice_ai/src/risk/`)**:
   - 수식: $R = 100 \times (0.35 S_1 + 0.35 S_2 + 0.15 S_3 + 0.15 S_4)$
   - 비상 경보: $S_4=1.0$ (낙상) 또는 $S_1=1.0$ (무호흡) 감지 시 즉시 $R=100.0$ (`DANGER`) 강제 적용.
   - 폴백: 센서 고장, 데이터 타임아웃(3초), NaN 발생 시 보수적 감지 및 `DEGRADED` 시스템 상태 적용.

4. **통합 실행 노드 (`ondevice_ai/src/integrated_node/`)**:
   - Web UI / Web Server를 포함하지 않으며, UI 팀원이 즉시 사용할 수 있도록 표준 **JSON Lines (stdout)** 실시간 스트림 출력.

---

## 2. 유닛 및 통합 테스트 결과

```bash
cd safenest-embedded-competition
python3 -m unittest discover -s tests -p "test_*.py"
```

- **현재 구조 검증 결과**: 84개 테스트 **PASS**, 데이터셋 미포함 조건 2개 **SKIP** (2026-08-02, TensorFlow 2.19.1).

---

## 3. 팀원 인수인계 문서 목록

- [`TEAM_HANDOFF_GUIDE.md`](TEAM_HANDOFF_GUIDE.md): 센서·AI·라즈베리 파이 통합 인수인계
- [`MR60_INTEGRATION.md`](MR60_INTEGRATION.md): ESP USB 실측 및 재생 검증 절차
- [`../../docs/operations/HARDWARE_RUNBOOK.md`](../../docs/operations/HARDWARE_RUNBOOK.md): 하드웨어 설치·운용 절차
- [`../../docs/architecture/BRANCH_PROVENANCE.md`](../../docs/architecture/BRANCH_PROVENANCE.md): 원본 브랜치와 이동 이력
