# SafeNest Pi 실행 절차 (필드용)

이 문서는 **실제 프로토타입 Pi**에서 SafeNest 런타임을 켜고 확인하는 절차만 정리한다.  
기준 경로: `/home/sandi/safenest-team-main`  
기준 커밋: 팀 `main` (`jinsu1011/safenest-embedded-competition`, Risk V1 / M-N9 포함본)

> Pi IP가 바뀌면 아래 `PI_IP`만 바꿔 읽으면 된다.  
> 현재 필드 IP: **`192.168.0.3`**

---

## 필드 모니터 (바로 실행)

`--once`를 **빼면** 계속 갱신, 넣으면 한 번만 보고 종료.

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py                 # 계속 보기 (기본 4초)
python3 hil/pi_field_monitor.py --once          # 한 번만
python3 hil/pi_field_monitor.py --interval 2    # 2초 간격 계속
# 종료: Ctrl+C
# 맥에서: python3 hil/pi_field_monitor.py --base http://192.168.0.3:8000
```

표 읽는 법 → **3-B**.

---

## 개발 규칙 (필수)

Pi에 손대기 전에 **로컬 worktree 브랜치 → GitHub PR → merge → Pi pull** 순서로 한다.

- `main` 체크아웃을 직접 수정하지 않는다.
- 팀원과 `main`을 공유하므로 **git worktree**로 작업 트리를 분리한다.
- Pi에서 `app.py` 등을 SSH로 핫패치하지 않는다 (긴급 복구 후 반드시 브랜치에 반영·PR).
- 배포 권한 레포: `jinsu1011/safenest-embedded-competition` (`/home/sandi/safenest-team-main`).


## 0. 이것만 쓴다

| 경로 | 용도 |
|---|---|
| `/home/sandi/safenest-team-main` | **정식 배포** (여기만 실행) |
| `/home/sandi/safenest-runtime` | 예전 클론. 참고용. **기동하지 말 것** |
| `/home/sandi/integration` 등 | 옛 진단/통합 클론. **기동하지 말 것** |

한 번에 하나만 띄운다. 예전 LCD 단독 `RaspberryPi/LCD/server.py` / 옛 `run_backend`를 따로 켜지 않는다.  
`:8000`은 **팀 런타임 백엔드만** 소유한다.

**중요:** `./run_safenest.sh`는 백엔드·센서 수신·웹 서빙까지다.  
LCD에 Chromium을 **자동으로 띄우지는 않는다** → 아래 **2-B**를 따로 실행한다.

---

## 1. 최초 1회 (이미 끝났으면 생략)

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git checkout main
git pull --ff-only origin main

# 의존성 + preflight
bash ./run_safenest.sh --install
```

확인:

- `.venv/bin/python` 존재
- `RaspberryPi/Runtime/risk/formula_v1.py` 존재
- `.env` 존재 (비밀값 포함 — git에 올리지 말 것)
- `RaspberryPi/LCD/static/display.html` 존재

### `/display` 라우트 (필드 필수)

팀 `main` 원본 `backend/app.py`에는 `/display`가 없을 수 있다.  
필드 Pi에는 LCD 정적 파일(`RaspberryPi/LCD/static`)을 `:8000`에서 서빙하도록 **로컬 패치**가 들어가 있다.

기동 후 반드시:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/display
# 기대: 200
```

`404`면 LCD HTML이 안 나온다. `app.py`에 `/display`, `/common.css` 라우트가 있는지 확인하고 백엔드를 재기동한다.  
`git pull` / `git reset` 하면 이 패치가 날아갈 수 있으니, pull 후 `/display`가 **200**인지 다시 확인한다.

---

## 2. 평소 기동

### 2-A. 백엔드 (런타임)

```bash
cd /home/sandi/safenest-team-main

# 이미 떠 있으면 중복 기동하지 말 것
pgrep -af run_backend.py || true
ss -ltnp | grep -E ":8000|:9000" || true
ss -lunp | grep 5005 || true

# 백그라운드 기동
mkdir -p logs
nohup bash ./run_safenest.sh > logs/runtime.log 2>&1 &
echo $! > .runtime.pid
```

포그라운드로 보려면:

```bash
cd /home/sandi/safenest-team-main
bash ./run_safenest.sh
```

기동 직후 확인:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -s -o /dev/null -w "display:%{http_code}\n" http://127.0.0.1:8000/display
ss -ltnp | grep -E ":8000|:9000"
ss -lunp | grep 5005
```

기대 포트:

| 포트 | 역할 |
|---|---|
| TCP `:8000` | FastAPI / Web / **LCD `/display`** / admin |
| TCP `:9000` | ESP 스칼라 텔레메트리 (mmWave / CO₂ / PIR) |
| UDP `:5005` | ESP 열화상 프레임 |

URL:

- LCD / display: `http://192.168.0.3:8000/display`
- Admin: `http://192.168.0.3:8000/admin`
- Dashboard: `http://192.168.0.3:8000/dashboard`
- Health: `http://192.168.0.3:8000/health`
- Status: `http://192.168.0.3:8000/api/status`
- LCD state API: `http://192.168.0.3:8000/api/state`

### 2-B. LCD에 화면 띄우기 (Chromium 키오스크)

백엔드가 떠 있고 `/display`가 **200**인 다음, **Pi 본체 디스플레이(seat0 / `:0`)** 에서:

```bash
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
[ -f "$HOME/.Xauthority" ] && export XAUTHORITY="$HOME/.Xauthority"

# 이미 떠 있으면 재실행 전 종료
pkill -f "chromium.*8000/display" 2>/dev/null || true

nohup chromium --kiosk --noerrdialogs --disable-infobars \
  --check-for-update-interval=31536000 \
  --user-data-dir=/tmp/safenest-chromium-display \
  --ozone-platform=x11 \
  http://127.0.0.1:8000/display \
  >/tmp/chromium-display.log 2>&1 &
```

확인:

```bash
pgrep -af "chromium.*8000/display" | head -3
# 물리 LCD에 SafeNest 화면이 보이는지 확인
```

일반 창(키오스크 아님):

```bash
DISPLAY=:0 chromium http://127.0.0.1:8000/display &
```

SSH만으로는 LCD가 안 바뀐다. Chromium은 **Pi의 그래픽 세션(`DISPLAY=:0`)** 으로 띄워야 한다.

---

## 3. 중지 / 재시작

```bash
cd /home/sandi/safenest-team-main

# Chromium LCD
pkill -f "chromium.*8000/display" 2>/dev/null || true

# 백엔드
kill "$(cat .runtime.pid)" 2>/dev/null || true
pkill -f "backend/run_backend.py" || true

# 포트 비었는지 확인
ss -ltnp | grep -E ":8000|:9000" || echo "tcp free"
ss -lunp | grep 5005 || echo "udp free"

# 다시 기동: 2-A → 2-B
```

---

## 3-B. 필드 모니터 (저장 / AI 입력 / 통신 / LCD)

파일: `RaspberryPi/Runtime/hil/pi_field_monitor.py`  
실행(계속): `cd …/RaspberryPi/Runtime && python3 hil/pi_field_monitor.py`  
실행(한 번): 같은 명령 + `--once` / 종료: `Ctrl+C` / 맥 원격: `--base http://192.168.0.3:8000`

아래는 **화면에 나오는 표 4개를 읽는 법**이다. 위→아래 순서로 본다.

공통 기호:

| 기호 | 의미 |
|---|---|
| `Δ` | 직전 샘플 대비 **이번 간격(기본 4초) 동안 증가량**. `+12`면 늘었음, `0`이면 그 구간 유입 없음 |
| `-` | 값 없음 / 해당 없음 |
| `…` | 칸이 좁아 잘린 문자열 (중요하면 터미널을 넓히거나 그 행 `detail`/`note`를 본다) |
| 헤더 `Δ window Ns` | 지금 표의 Δ가 몇 초 간격인지 |

ESP 끄기 전: Verdict가 대부분 `NO` / LCD `OFFLINE`인 것이 정상이다.  
ESP 켠 뒤: **Δ가 양수인지**를 먼저 보면 된다.

---

### 표 1) `## Verdict` — 한눈에 YES/NO

열:

| 열 | 읽는 법 |
|---|---|
| `check` | 무엇을 판정했는지 |
| `ok?` | 판정 결과. 대부분 `YES`/`NO`. **LCD state 행만** 상태 문자열(`OFFLINE`, `NORMAL-EMPTY` 등) |
| `detail` | 판정에 쓰인 숫자·부가 설명 (`conn=`, `telem=`, `Δ=`, `fail=` …) |

행별로:

| check | ok? 읽는 법 | detail에서 볼 것 |
|---|---|---|
| `TCP telem flowing` | `YES` = 이번 구간에 ESP TCP 텔레메트리 패킷이 **증가** | `conn` 연결 수, `telem` 누적, `Δ` |
| `UDP thermal flowing` | `YES` = 열화상 **완성 프레임** 증가 | `frames`, `Δ` |
| `Storage mmWave write` | `YES` = mmWave가 디스크에 **써짐** | `written`, `Δ` |
| `Storage CO2 write` | 위와 동일 (CO₂) | `written`, `Δ` |
| `Storage thermal write` | 위와 동일 (thermal) | `written`, `Δ` |
| `DB snapshots grow` | `YES` = SQLite 스냅샷 행 증가 | `snapshots`, `events`, `Δsnap` |
| `Logging worker` | `YES` = 저장 워커 살아 있음 | `enabled`, 큐 `q=현재/용량`, `err` |
| `AI has usable input` | `YES` = 센서 중 하나라도 LIVE/DEGRADED 이면서 AI가 `INPUT_UNAVAILABLE`이 **아님** | `ok=mmwave,co2…` 또는 `fail=센서:status/ai_state` |
| `Risk formula` | `YES` = `formula_id`가 `SAFENEST_RISK_V1` | `score`, `level`, `evid`(증거 충분 여부) |
| `LCD state` | LCD가 보여주는 상태(대문자) | `room`, `rev` |

읽는 팁: 이상하면 **`ok?`가 NO인 행만** 보고, 그 행 `detail`의 `Δ=0`인지 `conn=0`인지부터 확인한다.

---

### 표 2) `## Link & storage` — 통신·저장 수치

열:

| 열 | 읽는 법 |
|---|---|
| `metric` | 항목 이름 |
| `now` | **지금 누적값** (또는 현재 상태 문자열) |
| `Δ` | 이번 간격 증가량. 흐름 판정의 핵심 |
| `note` | 부가 카운터·경로 |

행별로:

| metric | now | Δ가 의미하는 것 | note에서 볼 것 |
|---|---|---|---|
| `system` | `ONLINE/…` 또는 `OFFLINE/FAILED` | (보통 `-`) | `ready`, `offline` |
| `tcp:9000 conn` | ESP TCP 동시 연결 수 | 연결이 늘/줄었는지 | `disc` 끊김, `gaps` 시퀀스 갭, `proto_err` |
| `telemetry pkts` | 스칼라 텔레메트리 누적 패킷 | 패킷이 들어오는지 | unexpected thermal-on-TCP 등 |
| `udp:5005 frames` | 조립 완료된 열화상 프레임 누적 | 프레임이 들어오는지 | `dgram`, `incomplete`, `fps` |
| `log written mm/co2/thm` | 센서별 파일 기록 누적 | 저장이 도는지 | `accepted` vs `dropped` (드롭 많으면 큐/부하) |
| `db snapshots` | DB 스냅샷 개수 | 런타임이 주기적으로 기록하는지 | DB 경로 |
| `db events` | 이벤트 개수 | 이벤트 적재 | `schema`, `avail` |

읽는 팁:

- **흐름**은 `now`보다 **`Δ`** 를 본다. `now`만 크고 `Δ=0`이면 “예전에 쌓였고 지금은 안 들어옴”.
- `conn≥1`인데 `telemetry Δ=0`이면 소켓만 있고 페이로드가 안 오는 경우.
- `written Δ>0`이면 “AI 입력 전 단계인 저장”은 통과.

---

### 표 3) `## Sensors / AI / risk component` — 센서 한 줄씩

센서마다 한 행 (`mmwave` / `thermal` / `co2` / `pir`).  
**이 열에 뜨는 문자열은 코드에 정해진 집합**이다. 아래 “경우별”을 보면 된다.

| 열 | 의미 | 좋은 예 | 나쁜 예 |
|---|---|---|---|
| `sensor` | 센서 ID | — | — |
| `status` | 센서 수신/신선도 상태 | `LIVE` (허용 `DEGRADED`는 시스템 쪽) | `NO_DATA`, `STALE`, `DISCONNECTED`, `INVALID` |
| `age_s` | 마지막 유효 데이터 나이(초) | TTL 안쪽 | `-` / 큰 값 |
| `ai_state` | AI·룰 **출력 라벨** (센서별 집합 다름) | 아래 센서별 표 | `INPUT_UNAVAILABLE` |
| `ai_err` | AI가 막힌 이유 코드 | `-` | `SENSOR_NO_DATA`, `WINDOW_CONTAINS_LARGE_GAP` … |
| `ai_score` | AI/성분 점수 | 숫자 | `-` |
| `ai_ms` | 추론 지연(ms) | 작은 숫자 | `-` |
| `risk_st` | Risk **성분 state** (formula_v1이 붙인 라벨) | 센서별 risk 표 | `UNAVAILABLE` |
| `risk_sc` | Risk 성분 점수 | 숫자 | `-` |
| `values` | 원시 힌트 | `presence=…`, `co2_ppm=…` | `-` |

읽는 팁: 왼쪽→오른쪽 `status` → `ai_state`/`ai_err` → `risk_st`/`risk_sc` → `values`.

---

#### 표 3 · `status` (모든 센서 공통)

| 값 | 의미 |
|---|---|
| `LIVE` | 최근 TTL 안 유효 데이터 수신 |
| `NO_DATA` | 아직/전혀 유효 샘플 없음 (ESP 미연결·미수신) |
| `STALE` | 예전에 왔지만 TTL 초과로 신선하지 않음 |
| `DISCONNECTED` | 연결 끊김으로 표시 |
| `INVALID` | 수신은 됐으나 유효성 실패 |

---

#### 표 3 · `ai_state` — **thermal** (모델 `thermal_fall_int8`, 3클래스)

`probabilities` 순서 = `[NOT_HUMAN, HUMAN_NORMAL, HUMAN_FALL]`.

| ai_state | 의미 | 필드에서 흔한 상황 |
|---|---|---|
| `NOT_HUMAN` | 배경/비인간으로 분류 (class 0) | 사람 없음·화각 밖·대비 약함·도메인 미보정 시 **자주** |
| `HUMAN_NORMAL` | 사람 정상 자세 (class 1) | 서 있/앉아 있는 사람 |
| `HUMAN_FALL` | 전도/누움 위험 (class 2) | 낙상·누운 자세로 모델이 판단 |
| `INPUT_UNAVAILABLE` | 모델 입력 없음 | `status`가 LIVE가 아니거나 프레임 불가 |

---

#### 표 3 · `ai_state` — **co2** (C-B6, 2클래스)

| ai_state | 의미 |
|---|---|
| `VACANT` | 공실 쪽 분류 |
| `OCCUPIED` | 재실 쪽 분류 |
| `INPUT_UNAVAILABLE` | CO₂ 입력/윈도우 불가 |

---

#### 표 3 · `ai_state` — **mmwave** (M-N9 / 호흡 계열)

| ai_state | 의미 |
|---|---|
| `NORMAL` | 호흡 정상 쪽 분류 (모델 출력이 있을 때) |
| `RAPID_OR_ABNORMAL` | 빠름/이상 호흡 쪽 |
| `APNEA` | 무호흡 쪽 |
| `WINDOW_UNAVAILABLE` | 30s 등 **정규 윈도우 미구성** (갭·샘플 부족). LIVE여도 흔함 → Risk는 룰 폴백 |
| `INPUT_UNAVAILABLE` | 센서 입력 자체 없음 |

`ai_err` 예: `WINDOW_CONTAINS_LARGE_GAP` = 윈도우 안 큰 간격 때문에 정규 추론 스킵.

---

#### 표 3 · `ai_state` — **pir** (룰, 모델 없음)

| ai_state | 의미 |
|---|---|
| `MOTION` | 움직임 감지 |
| `NO_MOTION` | 움직임 없음 |
| `INPUT_UNAVAILABLE` | PIR 입력 없음 |

---

#### 표 3 · `risk_st` — Risk 성분이 붙이는 state (formula_v1)

모니터 `risk_st`는 주로 **성분 state**다. (Verdict의 `component_status`의 `AI`/`RULE`/`RULE_FALLBACK`과는 별개 열.)

**thermal**

| risk_st | 의미 |
|---|---|
| `NOT_HUMAN` / `HUMAN_NORMAL` / `HUMAN_FALL` | AI `ai_state`를 그대로 성분 state로 사용 |
| `UNAVAILABLE` | 센서 비LIVE 또는 AI 차단/미지 클래스 |

**mmwave**

| risk_st | 의미 |
|---|---|
| `RESPIRATION_NORMAL` | 호흡 정상으로 점수화 (AI 또는 룰 폴백) |
| `RESPIRATION_ABNORMAL` | 호흡 이상 |
| `UNAVAILABLE` | 입력 부족 |

필드에서 mmWave AI가 `WINDOW_UNAVAILABLE`이면 Risk는 **`RULE_FALLBACK` 경로**로 `RESPIRATION_*`를 내는 경우가 많다 (허용된 DEGRADED).

**co2**

| risk_st | 의미 |
|---|---|
| `CO2_NORMAL` | ppm·기울기 정상 구간 |
| `CO2_WARNING` | 경고 구간 (`HIGH_CO2_WARNING` 등) |
| `CO2_DANGER` | 위험 구간 |
| `CO2_IMMEDIATE_DANGER` | 즉시 위험 |
| `UNAVAILABLE` | CO₂ 입력 없음 |

**pir**

| risk_st | 의미 |
|---|---|
| `MOTION` | 움직임 있음 → 위험 기여 낮음 |
| `NO_MOTION` | 단시간 무움직임 |
| `NO_MOTION_RISING` | 무움직임이 위험 쪽으로 점수 상승 중 |
| `LONG_NO_MOTION` | 장시간 무움직임 (고위험 쪽) |
| `UNAVAILABLE` | PIR 입력 없음 |

---

#### 표 3 · 지금 필드에서 자주 보는 조합

| 행 | status | ai_state | risk_st | 해석 |
|---|---|---|---|---|
| thermal | `LIVE` | `NOT_HUMAN` | `NOT_HUMAN` | 프레임은 오는데 모델이 비인간. 통신 OK, **분류 결과** |
| thermal | `LIVE` | `HUMAN_NORMAL` | `HUMAN_NORMAL` | 열화상 재실·정상 |
| thermal | `LIVE` | `HUMAN_FALL` | `HUMAN_FALL` | 열화상 전도/고위험 클래스 |
| mmwave | `LIVE` | `WINDOW_UNAVAILABLE` | `RESPIRATION_NORMAL` 등 | 텔레메트리는 LIVE, 정규 AI 윈도우만 실패 → 룰 폴백 |
| co2 | `LIVE` | `OCCUPIED` | `CO2_WARNING` | 재실 AI + ppm 경고 구간 동시 |
| pir | `LIVE` | `NO_MOTION` | `NO_MOTION_RISING` | 움직임 없음이 위험 점수로 반영 중 |
| * | `NO_DATA` | `INPUT_UNAVAILABLE` | `UNAVAILABLE` | ESP/해당 채널 미수신 |

`ai_err=SENSOR_NO_DATA` 이면 모델 버그가 아니라 **센서 미수신**이다.

### 표 4) `## Risk / LCD (display)` — 위험도·LCD 문구

키-값 표. LCD 화면과 맞춰 볼 때 쓴다.

| field | 읽는 법 |
|---|---|
| `formula_id` | `SAFENEST_RISK_V1`이어야 함 |
| `formula_version` | 공식 버전 문자열 |
| `risk_score / level` | 점수 / 레벨(`warning`·`danger` 등). 센서 없으면 `None` |
| `effective_weight` | 가용 성분 가중 합. `0`이면 성분 없음 |
| `evidence_sufficient` | 증거 충분한지 (`True`/`False`) |
| `presence` | 재실 판정과 출처 (`UNCONFIRMED` 등) |
| `degraded_mode` | 저하 모드 여부 |
| `reasons` | Risk가 그렇게 나온 **이유 코드** 나열 (디버그 핵심) |
| `LCD state` | LCD가 쓰는 상태 키 (`offline`, `normal-empty`, `warning` …) — 물리 LCD와 동일해야 함 |
| `LCD room` | 표시 공간 이름 |
| `LCD revision` | LCD 상태 revision |
| `pub_revision` | 백엔드 publication revision (내부 갱신 카운트) |

읽는 팁:

- LCD에 “통신 오류”면 여기 `LCD state=offline` + `reasons`에 `*_SENSOR_NO_DATA`가 같이 있는 경우가 많다.
- `formula_id`는 YES인데 `risk_score=None`이면 **엔진은 떠 있고 입력만 없는** 상태.

---

### 네 표를 이어서 읽는 짧은 순서

1. **Verdict**에서 NO인 행만 고른다.  
2. 통신 NO → **Link & storage**의 `tcp:9000 conn` / `telemetry`·`udp frames`의 **Δ**.  
3. 저장 NO → 같은 표의 `log written *` **Δ** / `Logging worker`.  
4. AI NO → **Sensors** 표에서 해당 센서 `status`·`ai_err`.  
5. LCD 문구 이상 → **Risk / LCD**의 `LCD state` + `reasons`.


## 4. ESP 켜기 전 / 후

### ESP 켜기 전

- Pi 런타임만 먼저 올려 두면 된다 (`:9000` / `:5005` listen).
- 이 상태에서는 `/api/status`가 `NO_DATA` / `OFFLINE`인 것이 정상이다.
- LCD는 `offline` / 센서 연결 대기처럼 보일 수 있다.

### ESP 목표 주소 (필수)

ESP 펌웨어 / 설정의 Pi 주소를 **현재 Pi IP**로 맞춘다.

```text
TCP  → 192.168.0.3:9000
UDP  → 192.168.0.3:5005
```

IP가 또 바뀌면 ESP 쪽도 같이 갱신한다.

### ESP 켠 뒤 (3~4분 warm-up)

```bash
# 연결 여부
ss -Htn state established "( sport = :9000 or dport = :9000 )"

# 상태 스냅샷
curl -fsS http://127.0.0.1:8000/api/status | python3 -m json.tool | less
```

짧게 증가량만 보려면:

```bash
python3 - <<'PY'
import json, time, urllib.request
def get(p):
    return json.load(urllib.request.urlopen("http://127.0.0.1:8000"+p, timeout=5))
a=get("/health"); time.sleep(4); b=get("/health")
ra,rb=a["receiver"],b["receiver"]
print("tcp_conn", ra.get("connections"), "->", rb.get("connections"))
print("telemetry", ra.get("telemetry_packets"), "->", rb.get("telemetry_packets"))
ua,ub=ra.get("thermal_udp") or {}, rb.get("thermal_udp") or {}
print("thermal_frames", ua.get("completed_frames"), "->", ub.get("completed_frames"))
s=get("/api/status")
print("system", s.get("system"), s.get("system_health"))
r=s.get("risk") or {}
print("risk", r.get("formula_id"), r.get("risk_score"), r.get("risk_level"), r.get("component_status"))
for name in ("mmwave","thermal","co2","pir"):
    st=(s.get(name) or {}).get("state") or {}
    print(name, st.get("status"), "age", st.get("age_seconds") or st.get("age_s"))
PY
```

---

## 5. 프로토타입 PASS 기준 (필드)

모두 만족해야 PASS:

1. mmWave / Thermal / CO₂ / PIR → **LIVE** (또는 허용된 DEGRADED만)
2. 저장(`sensor_logging.written`)이 증가
3. Risk가 **`SAFENEST_RISK_V1`**으로 연속 산출
4. **물리 LCD**에 `/display` 화면 + admin / health / status 사용 가능

허용:

- mmWave `RULE_FALLBACK`
- 일부 `DEGRADED`
- `DEVICE_VALIDATED=false`

권장 펌웨어:

- ESP ≥ **1.3.0**, 텔레메트리에 `human_detected_raw` 포함

---

## 6. 업데이트 (코드만 최신으로)

런타임이 떠 있으면 먼저 중지한 뒤:

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git pull --ff-only origin main
# 의존성이 바뀌었을 때만
bash ./run_safenest.sh --install
# 다시 기동 (2-A) 후 /display 200 확인 → 2-B
```

**주의:**

- `data/` 와 `.env` 는 지우거나 `git reset --hard`로 날리지 않는다.
- pull 후 `/display`가 404면 LCD 라우트 패치를 다시 넣고 백엔드를 재기동한다.

---

## 7. 로그 / 데이터 위치

| 경로 | 내용 |
|---|---|
| `logs/runtime.log` | nohup 기동 로그 |
| `.runtime.pid` | 백그라운드 PID |
| `/tmp/chromium-display.log` | LCD Chromium 로그 |
| `RaspberryPi/Runtime/data/` | SQLite·필드 데이터 (보존) |
| `RaspberryPi/LCD/static/` | LCD HTML/CSS (백엔드가 서빙) |
| `.env` | 로컬 설정 (git 제외) |

---

## 8. 자주 막히는 것

| 증상 | 확인 |
|---|---|
| `:8000` 이미 사용 | 예전 `run_backend` / LCD `server.py` 남아 있음 → `pkill` 후 재기동 |
| `/display` → **404** | `app.py`에 LCD 라우트 없음 / pull로 패치 소실 → 패치 후 재기동 |
| Chromium은 떴는데 LCD 검정/빈 화면 | `curl`로 `/display`·`/common.css`·`/api/state`가 200인지 확인 |
| Chromium이 안 뜸 / 즉시 종료 | `DISPLAY=:0`, `XDG_RUNTIME_DIR=/run/user/1000`, `/tmp/chromium-display.log` |
| ESP 연결 0 | ESP 목표 IP가 옛 주소(`192.168.137.x` 등)인지 확인 |
| 센서 NO_DATA | ESP 전원/와이파이, `:9000` established, warm-up 3~4분 |
| Risk UNAVAILABLE | 센서 유입 없음 → 수신부터 해결 |

---

## 9. 한 줄 요약

```bash
cd /home/sandi/safenest-team-main
bash ./run_safenest.sh --install   # 최초만
bash ./run_safenest.sh             # 2-A 백엔드
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/display   # 200이어야 함
# 2-B LCD
DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 \
  chromium --kiosk --ozone-platform=x11 \
  --user-data-dir=/tmp/safenest-chromium-display \
  http://127.0.0.1:8000/display &
# ESP → 192.168.0.3:9000 / :5005
```
