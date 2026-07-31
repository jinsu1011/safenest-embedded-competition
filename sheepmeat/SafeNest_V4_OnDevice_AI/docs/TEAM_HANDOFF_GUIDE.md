# SafeNest V4 온디바이스 AI 팀원 통합 인수인계 가이드

본 문서는 SafeNest V4 온디바이스 AI 패키지를 센서 하드웨어, Raspberry Pi 5, 웹 UI, QA 및 모델 재학습 담당자가 즉시 인수할 수 있도록 정리한 **현재 상태 설명서이자 복사·실행용 작업 프롬프트 모음**이다.

온디바이스 AI 패키지의 책임 범위는 다음과 같다.

```text
실제 센서 입력
→ 센서별 전처리
→ AI 모델 또는 규칙 추론
→ 공통 InferenceResult 생성
→ 멀티센서 위험도 융합
→ JSON Lines 출력
```

웹 서버, 웹 화면, 사용자 인증과 클라우드 전송은 온디바이스 AI 담당 범위가 아니다. 웹 UI 담당자는 온디바이스 노드의 구조화된 출력만 소비한다.

---

## 1. 반드시 먼저 알아야 할 현재 구현 상태

`--mode real`이라는 이름만으로 실센서 드라이버가 완성됐다고 판단하면 안 된다. 현재 저장소는 AI 모델, 공통 계약, 위험도 엔진과 mock 실행 기반을 제공하지만 실제 하드웨어 I/O는 팀별로 완성해야 한다.

| 영역 | 현재 상태 | 담당자가 완료할 작업 |
|---|---|---|
| Thermal-44 | `read_frame()`이 합성 열 프레임 반환 | 실제 I2C 초기화, SPI 프레임 수신, 프레임 검증 |
| mmWave | UART 연결부가 placeholder이며 ring buffer 인터페이스만 존재 | MR60BHA2 프로토콜 파싱, 파형 호환성 검증, 실제 sample 입력 |
| CO₂ | `read_raw_values()`가 고정값 `650ppm, 45%, 23.5°C` 반환 | SCD40 측정 명령, data-ready/CRC/warm-up 처리 |
| PIR | `read_gpio()`가 항상 `True` 반환 | 실제 GPIO 설정, edge 감지, 자원 해제 |
| 통합 노드 | mock/real 선택 및 JSON Lines 출력 구조 존재 | 실센서 드라이버 완성 후 장시간 운전 검증 |
| CLI 설정 | 현재 `--mode`, `--interval` 지원 | `--config`가 필요하면 구현·테스트 후 문서와 함께 추가 |
| 웹 UI | 미포함 | UI 팀이 JSON Lines 계약을 사용해 별도 구현 |

현재 placeholder를 실제 센서 결과로 오인하거나 성능 보고에 사용하지 않는다.

---

## 2. 시스템 공통 규격

### 2.1 센서 위험도

```text
S1: mmWave 호흡 이상/무호흡 점수
S2: CO₂ 환경 위험 점수
S3: PIR 장시간 무움직임 점수
S4: Thermal-44 낙상 점수
```

모든 센서 점수는 `0.0 ≤ S ≤ 1.0` 범위를 사용한다.

$$R = 100 \times (0.35S_1 + 0.35S_2 + 0.15S_3 + 0.15S_4)$$

| 점수 | 등급 |
|---:|---|
| `R < 30` | `NORMAL` |
| `30 ≤ R < 60` | `CAUTION` |
| `R ≥ 60` | `DANGER` |
| 핵심 입력 계산 불가 | `FAULT` 또는 명시적 fallback 결과 |

### 2.2 점수 매핑

| 센서 | 상태 | 점수 |
|---|---|---:|
| mmWave | NORMAL | 0.0 |
| mmWave | RAPID_OR_ABNORMAL | 0.5 |
| mmWave | APNEA | 1.0 |
| CO₂ | 정상 범위 | 0.0 |
| CO₂ | 주의 범위 | 0.5 |
| CO₂ | 고농도 | 1.0 |
| PIR | 움직임 감지 | 0.0 |
| PIR | 15초 이상 무움직임 | 1.0 |
| Thermal | NOT_HUMAN/HUMAN_NORMAL | 0.0 |
| Thermal | HUMAN_FALL | 1.0 |

CO₂ 임계값은 설정값이며 임상 진단 기준으로 표현하지 않는다. PIR의 무움직임 역시 낙상 확정이 아닌 보조 신호다.

### 2.3 Emergency Override

현재 위험도 엔진은 다음 이벤트를 즉시 `R=100`, `DANGER`로 처리한다.

- Thermal `HUMAN_FALL`, 즉 `S4=1.0`
- mmWave `APNEA`, 즉 `S1=1.0`

현장 오탐 억제를 위해 confidence, 연속 프레임, 무호흡 지속시간과 경보 latch 정책을 설정화하는 것을 권장한다. 정책을 추가할 때는 위험도 엔진과 테스트를 함께 변경하고 단일 노이즈 입력·경계 조건을 검증한다.

권장 설정 예시는 다음과 같다.

```yaml
emergency_overrides:
  thermal_fall:
    enabled: true
    minimum_confidence: 0.80
    consecutive_frames: 2
  mmwave_apnea:
    enabled: true
    minimum_confidence: 0.80
    minimum_duration_seconds: 2.0
  latch_seconds: 10.0
```

위 설정은 권장안이며 현재 코드에 전부 구현됐다는 뜻이 아니다.

### 2.4 공통 센서 계약

모든 실센서와 mock 센서는 `sensors.base_sensor.BaseSensor`를 구현한다.

```python
class BaseSensor:
    def connect(self) -> bool: ...
    def read(self) -> InferenceResult: ...
    def health(self) -> SensorHealth: ...
    def close(self) -> None: ...
```

모든 결과는 `inference.inference_result.InferenceResult`로 반환한다.

```python
InferenceResult(
    sensor_id="thermal44",
    timestamp=1722150000.0,
    score=1.0,
    state="HUMAN_FALL",
    confidence=0.97,
    valid=True,
    latency_ms=4.21,
    error=None,
    metadata={"frame_shape": [62, 80], "model_version": "0.1.0"},
)
```

공통 규칙:

- 단선, timeout, NaN, Inf, 잘못된 shape와 추론 실패는 `valid=False`로 반환한다.
- 장애 센서 값을 정상 `score=0.0`으로 위장하지 않는다.
- `score`와 `confidence`는 0~1 범위다.
- `timestamp`는 가능한 한 실제 센서 측정 시각을 사용한다.
- `latency_ms`는 전처리·추론·후처리를 포함한 범위를 문서화한다.
- `metadata`는 JSON 직렬화 가능한 값만 포함한다.
- 센서 하나의 예외로 통합 프로세스가 종료되지 않게 한다.

---

## 3. 프롬프트 1 — Thermal-44 하드웨어 담당자

```text
[역할]
SafeNest Thermal-44 열화상 센서 및 Raspberry Pi 드라이버 담당자다.

[목표]
sensors/thermal44/thermal44_driver.py의 합성 프레임 placeholder를 실제 Thermal-44 I2C/SPI 드라이버로 교체한다. 기존 모델, 위험도 엔진, 모델 manifest는 임의로 수정하지 않는다.

[사전 확인]
1. 정확한 I2C 주소를 데이터시트 또는 i2cdetect로 확인한다. 현재 config의 0x33은 검증 대상이다.
2. SPI bus/device, clock, mode, byte order, 프레임 header/checksum을 데이터시트로 확인한다.
3. 실제 센서가 10Hz를 지원하는지 확인한다.
4. 픽셀 값이 Celsius, centi-Celsius 또는 raw ADC인지 확인한다.
5. Raspberry Pi의 BCM 번호와 물리 핀 번호를 구분한다.

[구현]
1. connect()에서 I2C/SPI 장치를 열고 센서를 초기화한다.
2. read_frame()에서 정확히 4,960픽셀을 수신한다.
3. 부족한 프레임, checksum 실패, timeout을 검출한다.
4. ThermalFrameParser로 (62,80) float32 배열을 만든다.
5. NaN, Inf 및 센서 데이터시트 범위를 벗어난 값을 거부한다.
6. ThermalInterpreter.predict(frame_62x80)를 호출한다.
7. NOT_HUMAN/HUMAN_NORMAL은 S4=0.0, HUMAN_FALL은 S4=1.0으로 반환한다.
8. close()에서 SPI/I2C 자원을 항상 해제한다.

[모델 계약]
입력: shape=(1,62,80,1), dtype=int8, scale=0.003814, zero_point=-128
출력: shape=(1,3), dtype=int8, scale=0.003906, zero_point=-128
클래스: 0=NOT_HUMAN, 1=HUMAN_NORMAL, 2=HUMAN_FALL

[금지]
- 입력 배열 축을 추측으로 전치하지 않는다.
- 손상 프레임을 정상 프레임으로 대체하지 않는다.
- 위험도 엔진 수식과 타 센서 코드를 수정하지 않는다.
- 원시 열 프레임을 무제한 로그에 저장하지 않는다.

[필수 테스트]
- 정상 4,960픽셀, 부족/초과 프레임, 축 순서
- NaN/Inf, timeout, disconnect/reconnect
- HUMAN_FALL → S4=1.0
- 모델 누락 및 SHA256 불일치
- close 이후 장치 자원 해제

[완료 산출물]
- 실제 thermal44_driver.py
- 검증된 주소·버스·핀맵 근거
- mock/real 계약 테스트
- Raspberry Pi 실측 latency와 연속 운전 결과
```

---

## 4. 프롬프트 2 — mmWave 담당자

> **모델 호환성 주의:** 기존 모델 학습 입력은 radar rFFT에서 추출한 10Hz 호흡 위상 파형이다. MR60BHA2가 제공하는 호흡수나 vendor 상태 코드는 같은 입력이 아니다. 호환성 확인 없이 기존 TFLite 모델에 넣지 않는다.

```text
[역할]
SafeNest mmWave 레이더 센서 통합 담당자다.

[목표]
Seeed Studio MR60BHA2를 sensors/mmwave/mmwave_adapter.py에 연결하고 실제 데이터 형식과 기존 모델 입력의 호환성을 검증한다.

[사전 확인]
1. TFLite interpreter에서 실제 input shape/dtype을 조회한다.
2. MR60BHA2 UART 출력이 raw radar, 호흡 파형, 호흡수, 상태 코드 중 무엇인지 확인한다.
3. /dev/ttyAMA0, 115200 baud는 기본 후보일 뿐이므로 실제 장치 문서에서 확인한다.
4. vendor frame header, length, checksum과 endian을 확인한다.

[운영 모드]
- model: 기존 학습과 호환되는 10Hz 호흡 파형을 얻을 수 있을 때만 사용한다.
- vendor_rule: 장치가 호흡수/무호흡 상태만 제공할 때 사용하며 모델을 우회했다는 사실을 metadata.input_mode에 기록한다.

[버퍼 및 전처리]
1. sample_rate=10Hz, window=300 samples, duration=30초를 유지한다.
2. 세션 재시작이나 sensor reconnect 경계를 넘는 window를 만들지 않는다.
3. 300개 미만 버퍼를 zero-padding해 정상 추론하지 말고 WARMING_UP, valid=False로 반환한다.
4. timestamp 누락, 역전, 중복, stale sample을 검사한다.
5. sensor_stats_metadata_v0.1.0.json의 mean/std를 사용한다.
6. metadata가 없거나 std=0이면 추론을 중단한다.

[점수]
NORMAL → S1=0.0
RAPID_OR_ABNORMAL → S1=0.5
APNEA → S1=1.0

[필수 metadata]
input_mode, buffer_samples, sample_rate_hz, model_version,
preprocessing_version, last_sample_age_ms

[금지]
- 호흡수 하나를 300회 복제해 모델에 입력하지 않는다.
- vendor 상태를 AI 모델 결과라고 표현하지 않는다.
- Post-exercise 대리 라벨을 임상 진단이라고 표현하지 않는다.
- 위험도 엔진과 타 센서 코드를 수정하지 않는다.

[필수 테스트]
- 300개 정상 buffer와 299개 warming-up
- UART partial frame, checksum failure, timeout
- NaN/Inf, timestamp 역전, reconnect buffer reset
- NORMAL/ABNORMAL/APNEA 점수 매핑
- model/vendor_rule 모드 구분

[완료 산출물]
- UART protocol parser와 실제 adapter
- 센서 출력·모델 입력 호환성 분석서
- 실센서 샘플과 장시간 buffer 안정성 결과
```

---

## 5. 프롬프트 3 — SCD40 CO₂ 담당자

> **의미 구분:** UCI Occupancy 모델의 `OCCUPIED`는 재실 추정이며 CO₂ 위험 자체가 아니다. 현재 adapter의 `OCCUPIED → S2=1.0` 결합은 수정 검토가 필요한 정책이다.

```text
[역할]
SafeNest SCD40 CO₂ 센서 통합 담당자다.

[목표]
sensors/co2/co2_adapter.py의 고정 측정값 placeholder를 실제 SCD40 I2C 입력으로 교체하고 재실 추정과 CO₂ 환경 위험을 분리한다.

[센서 연결]
1. I2C 주소 후보 0x62를 i2cdetect와 데이터시트로 확인한다.
2. data-ready 확인, 측정 명령, warm-up, CRC와 read timeout을 구현한다.
3. CO₂ ppm, 상대습도 %, 온도 °C 단위를 유지한다.
4. SCD40이 약 5초 주기로 측정한다면 10Hz 센서처럼 취급하지 않는다.

[모델 입력]
feature 순서를 반드시 [CO2_slope, Humidity, CO2]로 유지한다.
CO2Interpreter의 실제 API와 모델 manifest를 확인하고 호출한다.

[slope]
최근 timestamp 기반 history를 유지한다.
co2_slope_ppm_per_min = (latest_ppm - oldest_ppm) / elapsed_seconds × 60
sample 개수 대신 실제 경과 시간을 사용한다.

[의미 분리]
VACANT/OCCUPIED는 occupancy_state metadata로 제공한다.
S2는 별도의 CO₂ 농도 정책으로 계산한다.

권장 초기 정책:
- CO2 < 1000ppm → S2=0.0
- 1000 ≤ CO2 < 1500ppm → S2=0.5
- CO2 ≥ 1500ppm → S2=1.0

임계값은 config로 관리하며 제품 안전 기준은 팀의 별도 검증을 거친다.

[상태]
VACANT_NORMAL, OCCUPIED_NORMAL, OCCUPIED_ELEVATED, HIGH_CO2,
SENSOR_WARMING_UP, SENSOR_FAULT

[오류]
warm-up 미완료, I2C/CRC 오류, NaN/Inf, 비정상 범위,
stale measurement, slope history 부족을 구분한다.

[금지]
- OCCUPIED 하나만으로 CO₂ 위험 확정 처리하지 않는다.
- occupancy 모델을 질식 위험 모델이라고 표현하지 않는다.
- feature 순서를 바꾸거나 위험도 엔진을 수정하지 않는다.

[필수 테스트]
- 정상값, 1000/1500ppm 경계
- timestamp 기반 slope와 history 부족
- warm-up, CRC, timeout, NaN/Inf
- occupancy_state와 S2 분리

[완료 산출물]
- 실제 SCD40 driver/adapter
- slope 단위 검증
- 임계값 설정과 센서 실측 결과
```

---

## 6. 프롬프트 4 — PIR 담당자

```text
[역할]
SafeNest PIR GPIO 센서 담당자다.

[목표]
sensors/pir/pir_adapter.py의 상시 True placeholder를 Raspberry Pi GPIO 입력으로 교체한다.

[연결]
1. 기본 후보 BCM GPIO 17을 실제 배선과 config에서 확인한다.
2. BCM 번호와 물리 핀 번호를 구분한다.
3. active-high/low 및 pull-up/down을 센서 사양에 맞춘다.

[동작]
1. edge 또는 HIGH 입력에서 마지막 움직임 시각을 갱신한다.
2. 경과 시간은 wall clock이 아닌 monotonic clock으로 계산한다.
3. 15초 미만은 MOTION, 15초 이상은 LONG_NO_MOTION으로 처리한다.
4. MOTION → S3=0.0, LONG_NO_MOTION → S3=1.0으로 반환한다.
5. 초기화 실패, 읽기 예외, 비정상 stuck 입력은 valid=False로 반환한다.
6. close()에서 callback과 GPIO 자원을 해제한다.

[제약]
LONG_NO_MOTION은 낙상이나 사망 확정이 아니라 다른 센서를 보조하는 신호다.

[필수 테스트]
- motion edge, 14.9초, 정확히 15초, 15초 초과
- wall clock 변경 영향 없음
- GPIO fault/stuck, mock GPIO, close 자원 해제

[완료 산출물]
- 실제 pir_adapter.py
- mock/real 계약 테스트
- 검증된 배선표
```

---

## 7. 프롬프트 5 — Raspberry Pi 5 시스템 통합 담당자

```text
[역할]
SafeNest Raspberry Pi 5 시스템 통합 담당자다.

[목표]
센서별 real adapter를 통합하고 온디바이스 노드를 안정적으로 자동 실행한다.

[설치]
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv i2c-tools git

cd SafeNest_V4_OnDevice_AI
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-pi.txt

[인터페이스]
raspi-config에서 I2C, SPI, hardware serial을 활성화한다.
UART console이 센서 포트를 점유하지 않는지 확인한다.

[확인]
i2cdetect -y 1
ls -l /dev/spidev*
ls -l /dev/ttyAMA* /dev/serial*
gpioinfo

[검증 순서]
1. mock unit test
2. 센서별 단독 real test
3. 모델 manifest/SHA256 확인
4. integrated mock mode
5. integrated real mode
6. 센서별 단선/reconnect
7. SIGINT/SIGTERM 종료
8. 최소 1시간 soak test와 메모리 증가 확인

[현재 실행 명령]
python3 -m integrated_node.run_node --mode mock
python3 -m integrated_node.run_node --mode real

현재 CLI는 --mode와 --interval을 지원한다. --config를 문서만 보고 사용하지 말고,
필요하면 run_node에 config loader와 CLI 인자를 구현하고 테스트까지 추가한다.

[systemd]
비특권 사용자, 가상환경 Python 절대 경로, WorkingDirectory,
Restart=on-failure, RestartSec, SIGTERM 정상 종료와 journal logging을 설정한다.

[금지]
- root 상시 실행 금지
- 센서 장애 시 몰래 mock으로 전환 금지
- stdout JSON Lines에 일반 로그를 혼합하지 않는다. 일반 로그는 stderr를 사용한다.

[완료 조건]
부팅 자동 시작, 정상 JSON 출력, 안전 종료, 단일 센서 장애 격리,
재부팅 복구와 journal 오류 추적이 모두 확인돼야 한다.
```

---

## 8. 프롬프트 6 — 웹 UI 담당자

```text
[역할]
SafeNest 웹 UI 담당자다.

[목표]
integrated_node.run_node의 한 줄 단위 JSON Lines를 소비해 별도 웹 대시보드를 구현한다. 온디바이스 모델과 위험도 엔진은 수정하지 않는다.

[입력 실행]
python3 -m integrated_node.run_node --mode mock

[계약]
- stdout: JSON 객체 한 줄
- stderr: 일반 로그
- risk_score: 0~100
- level: NORMAL/CAUTION/DANGER/FAULT
- is_emergency: 비상 UI 트리거
- reasons: 위험/장애 사유
- sensors: 센서별 score/state/confidence/valid/latency/error/metadata

[예시]
{
  "timestamp": 1722150000.0,
  "risk_score": 100.0,
  "level": "DANGER",
  "is_emergency": true,
  "reasons": ["EMERGENCY_HUMAN_FALL"],
  "system_status": "OK",
  "fallback_used": false,
  "sensors": {
    "thermal44": {
      "score": 1.0,
      "state": "HUMAN_FALL",
      "confidence": 0.97,
      "valid": true,
      "latency_ms": 4.21,
      "error": null
    }
  }
}

[화면]
- risk_score gauge
- NORMAL 초록, CAUTION 노랑, DANGER 빨강, FAULT 회색
- emergency popup
- reasons와 fallback 표시
- 센서별 valid, 마지막 갱신, 오류, stale 상태

[오류 처리]
JSON parse 실패, 프로세스 종료, 일정 시간 무수신, schema 불일치,
센서 누락과 valid=False를 처리한다.

[금지]
- UI에서 위험도를 재계산하지 않는다.
- invalid 센서를 정상으로 표시하지 않는다.
- 프론트엔드에 모델 로직을 복제하지 않는다.
```

---

## 9. 프롬프트 7 — QA 및 모델 재학습 담당자

```text
[역할]
SafeNest QA 및 모델 재학습 담당자다.

[목표]
전체 테스트를 검증하고 CO₂/mmWave NPZ로 재학습·독립 평가·INT8 변환·manifest 갱신을 수행한다.

[테스트]
python3 -m unittest discover -s tests -p "test_*.py" -v

테스트 개수를 74개로 미리 단정하지 않는다. 실제 discovery 결과의 개수와 통과/실패/skip을 보고한다.

[NPZ]
datasets/co2/processed/co2_occupancy_v1.npz
datasets/mmwave/processed/mmwave_respiration_v1.npz

[CO₂ 기준]
- train=(8138,3), validation=(2660,3), test=(9747,3)
- feature=[CO2_slope, Humidity, CO2]
- 공식 시간 분할 유지, train 통계만 사용, NaN/Inf 없음 확인

[mmWave 기준]
- X=(3433,300,1), 10Hz, 30초
- NORMAL=1401, RAPID_OR_ABNORMAL=1717, APNEA=315
- split window train=2491, validation=474, test=468
- 피험자 train/validation/test=80/15/15, 피험자 중복 없음 확인
- 세션 경계를 넘지 않고 train 통계만 사용

[평가]
accuracy, macro precision/recall/F1, 클래스별 지표, confusion matrix,
loss, 모델 크기, Float32/INT8 성능 차이와 latency를 기록한다.

[INT8]
representative dataset은 train split에서만 추출한다.
validation/test를 calibration에 사용하지 않는다.
변환 후 실제 TFLite interpreter로 input/output dtype, shape, scale, zero point와 test 성능을 검증한다.

[manifest]
version, path, SHA256, file size, tensor 규격, quantization,
feature/class mapping, preprocessing, test metrics, 날짜와 한계를 갱신한다.

[보고 원칙]
NPZ가 추가됐다는 사실만으로 정확도가 향상됐다고 쓰지 않는다.
동일 test split과 preprocessing으로 기존/신규 모델을 비교한 경우에만 개선을 주장한다.
재학습하지 않았다면 “재현 가능한 데이터 기반은 확보됐으나 정확도 개선은 독립 평가되지 않았다”고 기록한다.

[의미 제약]
Post-exercise는 RAPID_OR_ABNORMAL의 대리 라벨이며 임상 진단이 아니다.
UCI Occupancy는 재실 라벨이며 CO₂ 질식 위험 라벨이 아니다.
```

---

## 10. 담당 범위와 수정 경계

| 담당자 | 주 수정 범위 | 임의 수정 금지 |
|---|---|---|
| Thermal | `sensors/thermal44/` | 위험도 수식, 타 모델 |
| mmWave | `sensors/mmwave/`, 필요 시 protocol parser | Thermal/CO₂, 위험도 수식 |
| CO₂ | `sensors/co2/` | 타 모델, 위험도 수식 |
| PIR | `sensors/pir/` | AI 모델, 위험도 수식 |
| Pi 통합 | config, 실행 노드, systemd/권한 | 모델 구조와 학습 결과 |
| UI | 별도 웹 프로젝트 | 온디바이스 추론·위험도 로직 |
| QA | tests, 학습 코드, manifest | 평가 결과 조작, test leakage |

공통 인터페이스 변경이 필요하면 개인이 독단적으로 바꾸지 말고 온디바이스 AI 담당자와 계약 변경을 합의한다.

---

## 11. 통합 검수 시나리오

| 시나리오 | 예상 결과 |
|---|---|
| 전체 센서 정상 | `NORMAL` |
| CO₂ 1,000~1,499ppm | 설정에 따른 `S2=0.5` 후보 |
| CO₂ 1,500ppm 이상 | `S2=1.0` |
| PIR 15초 이상 무움직임 | `S3=1.0`, 단독 낙상 확정 금지 |
| Thermal 낙상 확정 | Emergency `DANGER` |
| mmWave 무호흡 확정 | Emergency `DANGER` |
| 센서 하나 단선 | fallback 및 장애 센서 표시 |
| 모든 핵심 센서 단선 | `FAULT` |
| NaN/Inf 입력 | 해당 센서 `valid=False` |
| stale 입력 | 해당 센서 제외 또는 명시적 fallback |
| SIGINT/SIGTERM | 모든 장치 자원 해제 후 종료 |
| UI 연결 종료 | 온디바이스 노드는 계속 실행 |

위험도 경계값 `29.999`, `30`, `59.999`, `60`과 모든 센서 score의 0/1 범위를 반드시 테스트한다.

---

## 12. 최종 완료 체크리스트

- [ ] 실제 하드웨어 주소, 포트, baudrate와 핀맵을 확인했다.
- [ ] placeholder 메서드가 실제 I/O로 교체됐다.
- [ ] mock 테스트와 센서별 real 테스트가 통과했다.
- [ ] 모델 manifest와 SHA256이 실제 파일과 일치한다.
- [ ] 장애 센서가 정상 `score=0.0`으로 은폐되지 않는다.
- [ ] 위험도 30/60 경계 및 Emergency Override를 검증했다.
- [ ] stdout에는 JSON Lines만, 일반 로그는 stderr에 출력된다.
- [ ] systemd 시작·중지·재시작과 재부팅 복구를 검증했다.
- [ ] Mac mock 성능과 Raspberry Pi real 성능을 구분해 기록했다.
- [ ] 실제 실행한 테스트 개수와 결과를 기록했다.
- [ ] 웹 UI가 위험도를 중복 계산하지 않는다.
- [ ] CO₂ occupancy와 환경 위험을 구분했다.
- [ ] mmWave 실센서 출력과 학습 모델 입력의 호환성을 확인했다.
- [ ] 미검증 항목을 통과했다고 표현하지 않았다.

이 체크리스트를 모두 충족한 후에만 “Raspberry Pi 5 실센서 통합 완료”로 판정한다.
