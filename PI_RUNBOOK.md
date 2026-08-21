# SafeNest Pi 실행 절차 (필드용)

이 문서는 **실제 프로토타입 Pi**에서 SafeNest 런타임을 켜고 확인하는 절차만 정리한다.  
기준 경로: `/home/sandi/safenest-team-main`  
기준 커밋: 팀 `main` (`jinsu1011/safenest-embedded-competition`, Risk V1 / M-N9 포함본)

> Pi IP가 바뀌면 아래 `PI_IP`만 바꿔 읽으면 된다.  
> 현재 필드 IP: **`192.168.0.3`**

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

표로 한 화면에 **통신·저장·AI 입력·Risk·LCD** 상태를 요약한다.  
ESP 켜기 전(전부 NO여도 정상) / 켠 뒤(YES로 바뀌는지) 모두 쓴다.

| 항목 | 값 |
|---|---|
| 파일 | `RaspberryPi/Runtime/hil/pi_field_monitor.py` |
| 읽는 API | `GET /health`, `/api/status`, `/api/state` (읽기 전용) |
| 기본 갱신 | 4초 (`--interval`로 변경) |
| 현재 Pi | `192.168.0.3` (IP 바뀌면 `--base` / 문서 IP만 갱신) |

### 전제

1. 백엔드가 떠 있어야 한다 (`./run_safenest.sh` → `:8000` health 200).
2. 모니터는 **LCD Chromium과 별개**다. 터미널에 표를 띄운다.
3. 첫 화면은 Δ(증가량)를 위해 **한 주기 warm-up** 후 표가 나온다.

---

### 보는 법 (Pi에서 — 권장)

#### 1) SSH로 파이 접속

```bash
ssh sandi@192.168.0.3
```

#### 2) 계속 보기 (실시간)

`--once`를 **빼면** 지속 모드다. 기본 4초마다 화면을 지우고 표를 다시 그린다.

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py
```

- 종료: 터미널에서 **`Ctrl+C`**
- 다른 작업할 SSH가 필요하면 창을 하나 더 열거나 `tmux`/`screen` 사용

#### 3) 한 번만 스냅샷

연결이 늘었는지 빠르게 확인할 때:

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py --once
```

약 4초(기본 interval) 대기 후 Δ 포함 표를 **한 번** 출력하고 종료한다.

#### 4) 갱신 간격 바꾸기

```bash
# 2초마다 계속 보기
python3 hil/pi_field_monitor.py --interval 2

# 2초 간격으로 한 번만
python3 hil/pi_field_monitor.py --once --interval 2
```

#### 5) 절대 경로로 실행 (cwd 상관없을 때)

```bash
python3 /home/sandi/safenest-team-main/RaspberryPi/Runtime/hil/pi_field_monitor.py
python3 /home/sandi/safenest-team-main/RaspberryPi/Runtime/hil/pi_field_monitor.py --once
```

#### 6) 옵션 요약

| 옵션 | 의미 |
|---|---|
| (없음) | 계속 갱신 |
| `--once` | Δ 한 번 찍고 종료 |
| `--interval N` | 샘플 간격(초). 기본 `4` |
| `--base URL` | API 주소. Pi 로컬 기본 `http://127.0.0.1:8000` |
| `--timeout N` | HTTP 타임아웃(초). 기본 `5` |
| `--no-clear` | 화면 clear 안 함 (로그로 흘릴 때) |

---

### 보는 법 (맥에서 — 원격)

파이와 **같은 Wi‑Fi**에 맥이 있어야 `192.168.0.3:8000`에 닿는다.

```bash
# 팀 worktree 예
cd "/Users/junwoo/Library/Mobile Documents/com~apple~CloudDocs/대학/2026/safenest-team-pi-field/RaspberryPi/Runtime"

# 계속 보기
python3 hil/pi_field_monitor.py --base http://192.168.0.3:8000

# 한 번만
python3 hil/pi_field_monitor.py --base http://192.168.0.3:8000 --once
```

integration worktree에 복사본이 있으면:

```bash
cd ".../safenest-pi-field-ops"
python3 hil/pi_field_monitor.py --base http://192.168.0.3:8000
```

연결 실패 시: 파이 IP/방화벽, 백엔드 기동, 맥·파이 동일 SSID를 확인한다.

---

### 화면에 나오는 것 (읽는 순서)

매번 위→아래 네 블록이다.

1. **Verdict** (가장 중요)  
   `ok?` 열의 `YES` / `NO`만 봐도 된다.  
   - ESP 끄기 전: 대부분 `NO` + LCD `OFFLINE` → **정상**  
   - ESP 켠 뒤 1~4분: `TCP telem` / `UDP thermal` / `Storage *` / `AI has usable input` 가 `YES`로 바뀌는지 본다

2. **Link & storage**  
   `now` = 누적값, `Δ` = 방금 간격 동안 증가량.  
   `Δ`가 `0`이면 그 구간에는 패킷/저장이 안 들어온 것.

3. **Sensors / AI / risk**  
   센서별 `status`(`LIVE`/`NO_DATA`…), `ai_state`, `ai_err`, risk 성분.

4. **Risk / LCD**  
   `formula_id`가 `SAFENEST_RISK_V1`인지, LCD `state`(`offline` / `normal-empty` 등).

#### Verdict 열 의미

| check | YES 의미 |
|---|---|
| TCP telem flowing | `:9000` 텔레메트리 패킷 증가 (ESP TCP 붙음) |
| UDP thermal flowing | `:5005` 완성 프레임 증가 |
| Storage * write | `sensor_logging.written` 증가 (디스크 저장) |
| DB snapshots grow | SQLite 스냅샷 증가 |
| Logging worker | 저장 워커 `running` |
| AI has usable input | LIVE/DEGRADED + AI가 `INPUT_UNAVAILABLE` 아님 |
| Risk formula | `SAFENEST_RISK_V1` 엔진 동작 중 |
| LCD state | `/api/state` 디스플레이 상태 (값 자체 표시) |

#### 자주 보는 패턴

| 증상 | 해석 | 다음 |
|---|---|---|
| 전부 NO, LCD OFFLINE | ESP 미연결 | ESP IP=`192.168.0.3`, 포트 9000/5005 |
| TCP YES, Storage NO | 수신은 되나 로거 이슈 | `Logging worker`, `errors` 확인 |
| Storage YES, AI NO | 데이터는 오는데 윈도우/모델 입력 부족 | warm-up 3~4분, `ai_err` 열 |
| `cannot fetch` | 백엔드 다운/IP 틀림 | `curl http://…:8000/health` |

---

### 스크립트 위치

- 파이(배포): `/home/sandi/safenest-team-main/RaspberryPi/Runtime/hil/pi_field_monitor.py`
- 맥 팀 worktree: `safenest-team-pi-field/RaspberryPi/Runtime/hil/pi_field_monitor.py`
- 맥 integration worktree: `safenest-pi-field-ops/hil/pi_field_monitor.py`


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
