# final-report

제24회 임베디드SW경진대회(2026) 자유공모 부문 **개발완료보고서** 작업 폴더.

표지 1장 + 본문 20장 = 21슬라이드. PptxGenJS 로 생성하고 Keynote 로 PDF 변환한다.

---

## 산출물

| 파일 | 설명 |
|---|---|
| `2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx` | 제출용 PPTX (21슬라이드) |
| `2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf` | 제출용 PDF (21페이지) |
| `previews/pdf/p-01.png ~ p-21.png` | 페이지별 렌더 (레이아웃 검수용) |

**PPTX 를 직접 편집하지 마라.** 다음 재빌드 때 덮어써진다. 항상 `generator/build.js` 를 고친다.

---

## 폴더 구조

```
final-report/
├── HANDOFF.md              ★ 작업 인계 메모. 이어서 하려면 이것부터 읽는다
├── CONTINUE_PROMPT.md      ★ 다른 PC에서 Claude Code 로 이어서 할 때 붙여넣는 프롬프트
├── generator/
│   ├── build.js            ★ 슬라이드 편집 원본 (PptxGenJS). 모든 수정은 여기서
│   ├── rebuild.sh          PPTX 생성 → Keynote PDF export → PNG 렌더
│   ├── package.json
│   └── charts/
│       ├── make_charts.py         CO₂·mmWave 실측 차트 생성 (원본 증거 패키지 필요)
│       └── make_victims_chart.py  P1 재해 통계 도넛 생성 (입력 불필요)
├── assets/                 보고서에 삽입된 이미지 (배선도·완성품·LCD 6종·웹·CAD·QR)
├── previews/
│   ├── chart_co2.png       P11 삽입 (SCD40 실측)
│   ├── chart_mmwave.png    P11 삽입 (리플레이 정량)
│   ├── chart_victims.png   P1 삽입 (재해자 구성 도넛). 슬라이드 배치 비율 3.40:2.92 로 생성하므로
│   │                       배치 크기를 바꾸면 반드시 같은 비율을 유지한다. 어기면 글자가 눌린다.
│   └── pdf/                페이지별 렌더
└── docs/                   근거·감사 문서 (수정 전 필독)
    ├── 00_SUBMISSION_REQUIREMENTS.md   공식 요구사항
    ├── 01_EVIDENCE_AUDIT.md            주장별 증거·등급
    ├── 02_REQUIREMENT_MATRIX.md        공식항목·심사항목 ↔ 페이지 대응
    ├── 03_CLAIM_EVIDENCE_LEDGER.md     강한 주장의 허용/금지 표현
    ├── 04_SOURCE_CONFLICT_AUDIT.md     ★ 자료 충돌 18건 해소 결과. 수정 전 필독
    ├── 05_ASSET_INDEX.md               이미지·데이터 목록
    ├── 06_SOURCES.md                   출처·데이터셋·라이선스
    ├── 07_MISSING_EVIDENCE_PRIORITY.md 결손 증거 우선순위
    ├── 08_PAGE_PLAN.md                 표지+20p 페이지 설계
    └── 11_FINAL_SUBMISSION_CHECKLIST.md 제출 체크리스트
```

---

## 빌드

```bash
cd final-report/generator
npm install          # 최초 1회 (pptxgenjs)
bash rebuild.sh
```

`rebuild.sh` 가 하는 일 : `node build.js` → Keynote 로 PDF export → `previews/pdf/` 에 21장 PNG 렌더.

### macOS 전제
PowerPoint·LibreOffice 없이 **Keynote** 로 변환한다. macOS 가 아니면 이 스크립트는 동작하지 않는다.

### 알려진 함정
- 이전 실행에서 **Keynote 에 문서가 열린 채 남아 있으면 다음 export 가 AppleEvent 타임아웃(-1712)으로 실패**한다. 실패하면 `killall Keynote` 후 재시도한다.
- export 는 성공했는데 뒤의 `close`/`quit` 에서 타임아웃 나는 경우가 있다. 이때 **PDF 는 정상 생성되어 있으므로** PNG 렌더만 따로 돌리면 된다:
  ```bash
  cd final-report/previews/pdf && rm -f p-*.png
  pdftoppm -png -r 70 "../../2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pdf" p
  ```
- 한 번 빌드에 3~5분 걸린다.

**수정 후에는 반드시 `previews/pdf/*.png` 를 눈으로 확인한다.** 텍스트 넘침이 자주 난다.

---

## 편집 규칙

`build.js` 는 `/* ====== P1 ====== */` ~ `P20` 주석으로 슬라이드가 구분되어 있다.
공통 헬퍼: `page(n, title, sub)` 헤더 · `box()` · `badge()` 증거배지 · `hdr()` 표 헤더 · `sub()` 소제목 · `note()` 각주 · `cap()` 캡션.

### 지켜야 할 것
1. **콘텐츠 20페이지 초과 금지.** 표지 제외 20p 까지만 평가된다. 추가하려면 무언가를 빼야 한다.
2. **분량 배분 유지** : 개발개요 3p(P1–3) / 환경·프로그램·장애요인 10p(P4–13) / 차별성·파급력 5p(P14–18) / 일정·업무분장 2p(P19–20)
3. **날조 금지.** 정확도·지연·오탐률·가용성·시장규모·매출·테스트 결과·사진·팀 기여를 지어내지 않는다.
   증거가 없는 항목은 수치를 쓰지 말고 아예 언급하지 않거나 검증 범위를 명시한다.
   이 문서는 **개발완료보고서**이므로 `미완료` `미착수` `아직 ~하지 않았다` 같은 진행형 표기는 쓰지 않는다.
   남은 일은 `확장 계획` 으로 표기한다.
4. **문체** : 제목은 전부 명사형 + 번호 체계(`1.1`). em dash(`—`) 금지. `A가 아니라 B` 같은 패턴 금지.

### 자가 점검
```bash
cd final-report/generator
grep -c "—" build.js                                                    # 0
grep -nE "page\([0-9]+, *'[^']*다'" build.js                             # 결과 없음
grep -nE "이 아니라|가 아니라|핵심은|본질적으로|완벽하|혁신적" build.js      # 결과 없음
grep -nE "팀번호|DRAFT|1,483 tests|Express 5" build.js                     # 결과 없음
```
네 줄 모두 통과해야 한다.

---

## 이 폴더에 없는 것

- **`node_modules/`** — `npm install` 로 재생성한다.
- **`work/` 입력 패키지 (약 341 MB)** — 검증된 원본 증거 묶음. 그중 279 MB 는 이 저장소 자체의 스냅샷 복사본이라 저장소 안에 다시 넣지 않았다. `generator/charts/make_charts.py` 는 이 경로를 읽으므로 **차트를 재생성하려면 원본 패키지가 필요**하다. 다만 생성된 차트 PNG 3종이 이미 포함되어 있어 **보고서 빌드에는 필요 없다.**
- **`.HEIC` 사진 원본** — JPG 변환본만 포함했다. `build.js` 는 HEIC 를 참조하지 않는다.

---

## 2026-08-24 개정 요약

Thermal 담당 수정 반영 + 전체 레이아웃·문체 정리.

**사실관계**
- 하드웨어 명칭 `Thermal-44` → `Thermal-90` 전면 교체. 코드의 `Thermal44Sensor` · `thermal44_*` 는 레거시 식별자로만 설명한다.
- 열화상 전송 구조를 "송신측 요약(thermal_max_c)" 서술에서 "전용 UDP 경로 분리"로 교체.
  프로토콜 명칭은 저장소 펌웨어 실제 상수를 따른다 : magic `SNTR`, version `2`, 32 B 헤더,
  1,200 B 데이터그램 9 조각, CRC32. (근거 `research/thermal_ai/firmware/xiao_esp32c6_thermal90_udp_capture/`)
- 실기기 지연 실측(p50 162.70 / p95 173.90 ms)은 **레거시 `thermal_fall_int8@0.1.0` 경로 한정**으로 표기한다.
- 현재 Production 열화상 경로 = `per-frame min-max + thermal_fall_int8 v0.1.0`.
  `℃ 변환 → P1 z-score → FULL_INT8(B5)` 는 오프라인 진단·호환성 검증용으로 분리 관리한다.
- 9P 우측에 열화상 온디바이스 판정 예시 2×2 **빈 자리**를 확보했다. 이미지가 준비되면 같은 위치에 교체 삽입한다.
  각 행은 반드시 동일 시각·동일 실행에서 나온 열화상/판정화면 한 쌍이어야 한다.

**레이아웃**
- 9P 우측을 표(0.55~7.85) / 배지(7.97~9.29) / 이미지자리(9.41~12.77) 세 구역으로 고정했다. 좌표를 바꿀 때 겹침 주의.
- 5·7·8·10·11·13·14·16·17P 의 텍스트 넘침·박스 겹침·각주 충돌 해소.
- 그림 번호를 1~9 로 재정렬했다 (중복 있었음).
- `make_charts.py` 출력 경로 버그 수정. CO₂ 차트 범례·기준선 라벨, mmWave `lock loss` 주석의 겹침 해소.

**아직 비어 있는 칸 (본문 3페이지)**
- 소스코드 (GitHub) / 시연동영상 (YouTube). URL 확정 시 P3 의 해당 두 줄만 채우면 된다.

---

## 2026-08-24 2차 개정

**정정 (중요)**
- 열화상 UDP 프로토콜을 `SNTR` version 2 로 표기했던 것은 **오류**였다.
  정본 통합 노드(`ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino`)의 실제 상수는
  magic **`SNTU`**, version **1**, 포트 **5005**, 32 B 헤더, 1,200 B 데이터그램, 논리 payload **9,936 B**
  (메타 16 B + 4,960 × uint16), 조각마다 프레임 CRC32 반복이다. 7·12·19페이지를 이 값으로 정정했다.
  `SNTR` version 2 는 `research/thermal_ai/` 의 XIAO ESP32-C6 **수집 리그** 전용이며 제품 경로가 아니다.

**신규 내용**
- 17페이지를 적용 분야 3축으로 재구성했다 : ① 밀폐공간 ② **보안 통제구역(반도체 팹·군사·연구시설)** ③ 어린이 통학차량.
  최상단에 "카메라를 쓰지 않기 때문에 열리는 적용 영역" 논거를 배치했다.
- 18페이지를 **도입 비용 + 발전 가능성**으로 재구성했다.
  BOM 은 2026-07-02 실구매 결제액 기준이며, 관제 노드 1대가 다수 감지 노드를 수용하는 구조를 근거로
  공간 확장 시 단가가 내려가는 것을 감시인 인건비와 대비해 제시한다.
- 14페이지 차별성 3번에 보안 구역 적용 논거를 추가했다.

**저장소 경로 불일치 → 4차 개정에서 해소**
- 보고서가 인용하던 `devices/` · `integration/` · `ondevice_ai/` 경로를 `main` 정본 경로로 전부 치환했다.
  자세한 내용은 아래 `2026-08-25 4차 개정` 을 본다.

---

## 2026-08-24 3차 개정 : 공식 필수항목 대조 + 타이포그래피

**공식 필수항목(부문 세부 안내사항 4-나) 대조 결과 채운 것**
- 필수항목 3 의 **함수별 기능** 이 없었다. 6페이지를 `3.1 파일 구성과 함수별 기능` 으로 재구성하고
  ESP32·Pi 양쪽의 핵심 함수 9종을 기능과 함께 표로 넣었다.
- 필수항목 6 의 **판매가치 · 시장성** 이 없었다. 18페이지를 `6.2 판매가치 · 시장성 및 발전 가능성` 으로
  재구성하고, 도입 비용을 판매가치로, 법령이 수요를 만드는 세 시장을 시장성으로 명시했다.
  자리를 만들기 위해 18페이지의 외함 이미지 2장을 뺐다(완성품 사진은 16페이지에 있다).
  이에 따라 그림 번호는 1~6 이 되었다.

**헤더 타이포그래피**
- 제목과 구분선의 간격이 넓어 선이 떠 보였다. 제목을 내리고 선을 올려 간격을 0.38 → 0.24 in 으로 좁혔고,
  구분선 좌측에 1.15 in 파란 강조 세그먼트를 겹쳐 제목 블록에 묶었다. 본문 시작 y 좌표는 바뀌지 않았다.

**글자 잘림**
- 1페이지 `재해 통계 (최근 10년, 2014~2023)` 의 쉼표·괄호 아래가 잘렸다.
  원인은 박스 높이가 아니라 **도넛 이미지가 소제목 위에 그려진 것**이었다(이미지 y+0.20, 소제목 y+0.00).
  이미지를 y+0.40 으로 내리고 크기를 3.20 × 2.75 로 줄여 해소했다.
- 같은 위험이 있는 고정 높이 텍스트 상자 20여 곳의 높이를 폰트 대비 1.6배 이상으로 올렸다.
  **이미지·도형을 소제목 근처에 배치할 때는 소제목 아래 0.36 in 을 비워야 한다.**

**공식 규격 확인**
- 파일명 `2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서` ✅ · PDF ✅ · 표지 제외 20P ✅
- 분량 배분 3P / 10P / 5P / 2P ✅
- 저장소 명명 규칙은 `github.com/사용자이름/2026ESWContest_free_가만있어도SANDI` 이다.
- 시연동영상은 3분 이내 · 720p 이상 · 제목 `2026ESWContest_자유공모_가만있어도SANDI_시연동영상` 이다.
- 수상 시 저장소는 Public 유지 의무가 있다.

---

## 2026-08-25 4차 개정 : 저장소 경로를 `main` 정본으로 치환

3차까지의 보고서는 2026-08-17 canonical 재구성 **이전** 트리를 인용하고 있었다.
심사위원이 제출 저장소에서 그 경로를 열면 아무것도 나오지 않는다.
`archive/README.md` 의 canonical 대체표와 `COMPONENT_SOURCES.json` 을 기준으로 전부 치환했다.

| 보고서 구 인용 | 치환한 정본 경로 |
|---|---|
| `devices/esp32_node/firmware/` | `ESP32/Arduino/esp32_sensor_node/` |
| `integration/pi_lcd/server.py` | `RaspberryPi/LCD/server.py` |
| `ondevice_ai/…` | `RaspberryPi/Ondevice_AI/…` |
| `devices/{mmwave,co2,pir,thermal}/src/` | `RaspberryPi/Ondevice_AI/sensors/` |
| `shared/contracts/base_sensor.py` | `RaspberryPi/Ondevice_AI/sensors/base_sensor.py` |
| `integration/web/` | `RaspberryPi/Runtime/backend/` + `RaspberryPi/Web/` |
| `models/model_manifest.json` | `RaspberryPi/Ondevice_AI/models/model_manifest.json` |
| `03_Evidence/Thermal/phase4_6_inference_report.md` | `archive/legacy_main_repo/docs/thermal/v5_validation/reports/…` |
| `replay_v5/benchmark_summary.csv` | `archive/legacy_main_repo/devices/mmwave/validation_results/replay_v5/…` |
| `devices/thermal/ · docs/thermal/` (P20) | `RaspberryPi/Ondevice_AI/sensors/thermal44/ · research/thermal_ai/` |

측정 증거는 `archive/legacy_main_repo/` 안에만 있으므로 그 경로를 그대로 인용한다.
`archive/README.md` 가 "재현 불가능한 측정 증거라서 보존한다" 고 밝히고 있어 근거로 성립한다.

**경로 치환 때문에 같이 바로잡은 사실관계**

- **`FastAPI` 금지 해제.** `04_SOURCE_CONFLICT_AUDIT.md` 의 C1 은 FastAPI·SQLite·WebSocket 이
  정본 401개 코드 파일에 0건이던 스냅샷을 근거로 "언급 금지" 라고 결론냈다. 그 판단은 더 이상 유효하지 않다.
  현재 `main` 의 `COMPONENT_SOURCES.json` 은 `canonical_runtime_entrypoint` 를
  `./run_safenest.sh → RaspberryPi/Runtime/deployment/run_pi.sh → RaspberryPi/Runtime/backend/run_backend.py`
  로 명시하고, `fastapi_backend` · `sqlite` · `web_dashboard` 를 `INTEGRATION_OWNED` 컴포넌트로 등록해 두었다.
  반대로 Express 5 관제 웹(`bcryptjs`·`jsonwebtoken`·`qrcode`)은 `archive/legacy_main_repo/integration/web/` 로 내려갔다.
  따라서 4페이지 개발환경 표의 `웹 관제` 행과 6페이지 오픈소스 고지, 3페이지 구성도, 17페이지 그림 6 캡션에서
  Express 표기를 걷어내고 정본 스택으로 바꿨다. **이제 금지어는 `Express 5` 쪽이다.**
- **`esp32_sensor_node.ino` 741줄 → 1,042줄.** 741 은 구 트리 기준이었다. 정본 파일 실측이 1,042 줄이다.
  6페이지 파일 구성표와 20페이지 산출물 칸을 같이 고쳤다.
- **LCD 테스트 13건 → 4건.** 13 건은 `archive/legacy_main_repo/integration/pi_lcd/tests`
  (`test_sensor_receiver` 11 + `test_buzzer` 2) 기준이었다. 정본 `RaspberryPi/LCD/tests` 를
  실제로 실행하면 `Ran 4 tests … OK` 다. 8페이지 각주를 실행 결과대로 4건으로 낮추고,
  포함 항목도 실제 테스트 이름(텔레메트리·열화상 패킷 수신, 스키마 위반 거부, 연결 종료 시 STALE 전환, 최신값 스냅샷)에 맞췄다.
- **저장소 파일 수 1,904개(commit `3f22fb1`) → 4,316개(main `8413d2f`).**
  `3f22fb1` 은 이 저장소에 존재하지 않는 커밋이라 심사위원이 확인할 수 없었다.
  4,316개 중 2,253개가 `archive/` 라는 점을 각주에 함께 적었다.
- **20페이지 표 머리글 `책임 영역 (CODEOWNERS)` → `책임 영역 (저장소 경로)`.**
  `.github/CODEOWNERS` 에는 thermal·pir 개별 규칙이 없어(주석에 그 이유가 적혀 있다)
  머리글을 CODEOWNERS 라고 쓰면 표의 일부가 근거를 넘어선다.

**레이아웃**
- 4페이지 개발환경 표는 경로가 길어져 열 폭을 `[1.72, 4.13, 1.82, 4.56]`, 글자를 11.5 → 10.5 pt 로 조정했다.
- 6페이지 파일 구성표는 `shared/contracts` 행을 `sensors/` 행에 합쳐 9행을 유지했다.
- 10페이지 fail-closed 라벨은 경로가 길어져 11 → 10 pt.

**아직 비어 있는 칸은 그대로다** (본문 3페이지) : 소스코드(GitHub) · 시연동영상(YouTube).
