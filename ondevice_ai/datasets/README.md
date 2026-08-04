# `datasets/`

## 1. 디렉터리 목적
재현 가능한 전처리 데이터셋과 출처·shape·해시 매니페스트를 관리한다.

## 2. 시스템에서 담당하는 기능
모델 학습·검증에 사용할 CO2 재실 및 mmWave 호흡 데이터 표본을 제공한다.

## 3. 포함해야 하는 파일 유형
검수된 `.npz`, 데이터셋·수집 매니페스트 `.json`, 재현 가능한 빌드 스크립트와 의존성 목록을 포함한다.

## 4. 포함하면 안 되는 파일 유형
동의·출처가 불명확한 개인정보, 임시 다운로드, 캐시와 무매니페스트 원본은 포함하지 않는다.

## 5. 주요 하위 구성
`co2/processed/`, `mmwave/processed/`, `MANIFEST.json`, `build_processed_npz.py`로 구성한다.

## 6. 입력과 출력 인터페이스
입력은 명시적으로 지정한 원본 데이터 경로이며 출력은 고정 dtype·shape의 NPZ와 검증 메타데이터다.

## 7. 다른 기능 영역과의 관계
`ondevice_ai/src/training/`이 학습에 사용하고 `ondevice_ai/models/` artifact 생성 및 `ondevice_ai/tests/` 계약 검증의 근거가 된다.

## 8. 실행·학습·추론 또는 활용 방법
저장소 루트에서 `python3 ondevice_ai/datasets/build_processed_npz.py --help`로 사용법을 확인한다.

## 9. 현재 개발 상태 및 버전
SafeNest V4 가공 데이터셋 v1과 2026-07-28 MR60 수집 매니페스트를 포함한다.

## 10. 향후 파일 추가 및 관리 규칙
원본을 덮어쓰지 말고 새 버전 경로를 만들며 파일 hash·shape·source를 `MANIFEST.json`에 함께 기록한다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Junwoo Han (`@sheepmeat`), Jinsu Kim (`@jinsu1011`).
`origin/Ondevice_AI` (`d97df3e`)의 원본 경로 `datasets/`에 있던 가공 데이터와 `codex/mmwave-phase-integration` (`b0d3c95`)의 MR60 전달 매니페스트를 통합했다. 이동 커밋 `38274c0`.

## 기존 데이터셋 상세

본 디렉터리는 SafeNest V4 온디바이스 AI 모델을 위한 전처리 `.npz` 데이터셋 파일과 재현 가능한 파이프라인 생성 스크립트를 포함합니다.

---

## 1. 원시 데이터셋 Exclusion 정책

> [!IMPORTANT]
> GitHub 단일 파일 용량 제한(<100MB)을 준수하고 저장소 용량 팽창을 방지하기 위해 원시 데이터셋(`db_records/`, 원시 CSV, 대용량 zip 파일)은 **깃 버전 관리에서 엄격히 제외**되었습니다.
> 오직 압축 전처리된 `.npz` 파일 및 자동 재생성 스크립트만 저장소에 보관됩니다.

---

## 2. 전처리 데이터셋 명세

### ⓐ CO₂ 재실 및 농도 데이터셋 (`ondevice_ai/datasets/co2/processed/co2_occupancy_v1.npz`)
- **출처**: UCI Machine Learning Repository - Occupancy Detection Dataset
- **URL**: [https://archive.ics.uci.edu/dataset/357/occupancy%2Bdetection](https://archive.ics.uci.edu/dataset/357/occupancy%2Bdetection)
- **DOI**: `10.24432/C5X01N`
- **라이선스**: CC BY 4.0
- **피처 구조**: `CO2_slope` (ppm/min), `Humidity` (%), `CO2` (ppm)
- **데이터 분할**:
  - `Train`: 8,138 샘플
  - `Validation`: 2,660 샘플
  - `Test`: 9,747 샘플
- **정규화 정책**: 오직 `Train` 분할 기준의 `mean` 및 `std` 통계량 사용.

### ⓑ mmWave 호흡 파형 데이터셋 (`ondevice_ai/datasets/mmwave/processed/mmwave_respiration_v1.npz`)
- **출처**: Zenodo 60GHz FMCW Radar Respiratory Dataset (110 subjects)
- **URL**: [https://zenodo.org/records/18599983](https://zenodo.org/records/18599983)
- **DOI**: `10.5281/zenodo.18599983`
- **라이선스**: CC BY 4.0
- **입력 스펙**: 10Hz 샘플링, 300 샘플 (30초 롤링 윈도우), shape `(300, 1)`
- **클래스 라벨**:
  - `0: NORMAL` (1,401 윈도우)
  - `1: RAPID_OR_ABNORMAL` (1,717 윈도우 - 운동 후 빈호흡 대리 라벨)
  - `2: APNEA` (315 윈도우 - 자발적 참기 데이터)
- **피험자 분할**:
  - `Train`: 80 피험자 (2,491 윈도우)
  - `Validation`: 15 피험자 (474 윈도우)
  - `Test`: 15 피험자 (468 윈도우)
- **데이터 누출 방지**: Train, Validation, Test 간 피험자 교차 0% 보장.

---

## 3. 원시 소스로부터 NPZ 데이터셋 재생성 방법

위 공식 URL에서 원시 데이터를 다운로드한 후 NPZ 파일 재생성:

```bash
# CO2 NPZ 데이터셋 재생성
python3 ondevice_ai/datasets/build_processed_npz.py --dataset co2 --source-root /path/to/uci_occupancy

# mmWave NPZ 데이터셋 재생성
python3 ondevice_ai/datasets/build_processed_npz.py --dataset mmwave --source-root /path/to/db_records

# 전체 NPZ 데이터셋 재생성
python3 ondevice_ai/datasets/build_processed_npz.py --dataset all --co2-root /path/to/uci --mmwave-root /path/to/db_records
```
