# M-PROT-5C — Live Raspberry Pi + MR60 smoke

Live verification of merged M-PROT-5B B23 on the physical Pi.
**Not** scientific / clinical / final-selection validation.
ESP firmware was **not** modified. Runtime source on `main` was **not** hotpatched.
TFLite conversion was **not** performed. M-PROT-6 was **not** started.

Final gate: **BLOCKED** (`NO_LIVE_BREATH_PHASE`).
PyTorch, frozen B23 identity, offline tests, and canonical runtime start all passed.
Live ESP/MR60 telemetry never reached TEAM TCP `:9000`.

---

## Host / repo

| Item | Observed |
|---|---|
| Timestamp | `2026-08-27T23:05:32+09:00` |
| Target | `192.168.137.189` (`wlan0`, `192.168.137.189/24`) |
| Hostname / user | `sandi` / `sandi` |
| Hardware | Raspberry Pi 5 Model B Rev 1.0 |
| Arch | `aarch64` |
| OS | Debian GNU/Linux 13 (trixie) 13.6 |
| Kernel | `6.18.34+rpt-rpi-2712 #1 SMP PREEMPT Debian 1:6.18.34-1+rpt1 (2026-06-09)` |
| RAM | 7.9 Gi total, 2.0 Gi swap |
| Disk | `/dev/mmcblk0p2` 29 G, ~4.8 G free (83% used) after torch install |
| Repo | `/home/sandi/safenest-team-main` |
| Remote | `https://github.com/jinsu1011/safenest-embedded-competition.git` |
| `PI_TEAM_MAIN_SHA` | `1df0c178b02d700f4893728b0a9b5836941b6adc` |
| M-PROT-5B merge ancestor | **YES** (merge of authorized head `3068e1fa5a148976ede232249d57ffe5368ab224`) |
| GitHub `origin/main` at evidence time | **unchanged** `1df0c17` |

Worktree policy: Pi was previously on `feat/lcd-guide-display-control` (`582b056`) with a one-line `PI_RUNBOOK.md` edit and untracked `LCD_Showcase/`. No `git reset --hard`. Runbook edit stashed (`mprot5c-preserve: local PI_RUNBOOK.md one-line separator`). `LCD_Showcase/` left untracked. Then `git switch main` + `git pull --ff-only origin main`.

Historical clones `/home/sandi/integration` and `/home/sandi/safenest-runtime` were **not** started.

---

## Runtime Python / dependencies

Canonical entry: `./run_safenest.sh` → `RaspberryPi/Runtime/deployment/run_pi.sh`.
`--install` was **not** used (it falls through and starts the backend). Standard deps were installed into the existing venv with the same pip requirement files the installer uses.

| Item | Observed |
|---|---|
| `PI_RUNTIME_VENV` | `/home/sandi/safenest-team-main/.venv` |
| `PI_RUNTIME_PYTHON` | `/home/sandi/safenest-team-main/.venv/bin/python` |
| `PI_RUNTIME_PYTHON_VERSION` | Python 3.13.5 |
| pip | 26.2.1 |
| numpy | 1.26.4 (`>=1.24,<2` pin held) |
| scipy | 1.17.1 |
| fastapi / uvicorn | 0.141.1 / 0.52.4 |
| sklearn (other Pi deps; **not** B23 path) | 1.9.0 present |
| `STANDARD_PI_DEPENDENCIES` | **PASS** |

`run_safenest.sh --install` was not invoked. Newly installed for the Pi venv in this phase: `piper-tts 1.7.0`, `onnxruntime 1.29.0`, `pathvalidate 3.3.1`, plus PyTorch (below). pytest 8.2.2 was installed only to run offline tests.

---

## PyTorch

Default PyPI `torch==2.13.0` on this aarch64 / cp313 resolved to the **CUDA 13** manylinux wheel (`torch-2.13.0-cp313-cp313-manylinux_2_28_aarch64.whl`, 427.2 MB) plus NVIDIA CUDA toolkit packages. That download was **aborted before install** (SIGTERM): the Pi has no NVIDIA GPU and only ~5 G free disk.

Installed instead from the **official PyTorch CPU index** (not a third-party Pi wheel mirror):

```text
python -m pip install "torch==2.13.0" \
  --index-url https://download.pytorch.org/whl/cpu \
  --extra-index-url https://pypi.org/simple
```

Wheel: `torch-2.13.0+cpu-cp313-cp313-manylinux_2_28_aarch64.whl` (155.0 MB).

The venv/pip configuration also lists `https://www.piwheels.org/simple` as an extra index. The torch wheel itself came from `download.pytorch.org`, not piwheels. numpy stayed 1.26.4 (no silent numpy 2 upgrade).

| Item | Observed |
|---|---|
| `PI_TORCH_VERSION` | `2.13.0+cpu` |
| `PI_TORCH_INSTALL_SOURCE` | official `https://download.pytorch.org/whl/cpu` |
| Import | **PASS** (~1273 ms first import in a short diagnostic) |
| Basic op | **PASS** (`torch.ones(3,3)` sum = 18.0) |
| Threads | `torch.get_num_threads() = 4` |
| Built from source | **NO** |

---

## Frozen B23 identity (isolated load)

CWD: `RaspberryPi/Runtime` with the runtime venv. Real modules: `ai.mmwave_prototype.mmwave_m_prot_2_b23_runtime`.

| Item | Observed |
|---|---|
| Artifact | `models/mmwave/m_prot_b23/candidate_seed_23.pt` (76473 bytes) |
| Artifact SHA-256 | `8f7de6f50d6ff62ff9b0ebfaed0b1fccd8d194c7e33781bc5b93366fae251a2c` **MATCH** |
| Parameter SHA-256 | `6db949c242e25888dd20c3fc8e2305af03448aa229e3ca73e4159216a266d78e` **MATCH** |
| Scaler file SHA-256 | `9555c8c954078b80e26fbcd3bc5d5a70b9a2e04620946118709ec95418b2ac36` **MATCH** |
| Scaler content SHA-256 | `5a2583b5b5064be5480b0cf56f2a2c12d40a4a2d005eb087dc8e12106881159c` **MATCH** |
| Construction | `TraceModel`, 17915 parameters, `state_dict` strict load |
| sklearn required for B23 load | **NO** (`sklearn` absent from `sys.modules` during load) |
| Isolated load | **PASS** |
| `B23_MODEL_LOAD_MS` | **5.5–5.6 ms** for `load_b23_model()` after modules imported; first-process import+verify+load **2321 ms** |
| Isolated forward | heads `breathing`, `rr`, `quality` |
| Isolated inference (dummy `[1,621]`, 20 reps after warmup) | median **0.53 ms**, min 0.52, max 0.77, mean 0.56 |

No B23 weights, scaler, or thresholds were changed.

---

## Offline Pi pytest

Same venv, `cd RaspberryPi/Runtime`.

| Suite | Result |
|---|---|
| `tests/test_mmwave_m_prot_5b_b23_runtime.py` | **37 passed** in 2.94 s |
| `tests/test_gateway_protocol.py` | **23 passed** in 0.60 s |
| `tests/test_sensor_state_manager.py` | **19 passed** in 0.05 s |
| `tests/test_ai_pipeline.py` | **12 passed** in 2.24 s |
| `tests/test_gateway_state_pipeline.py` | **1 passed** in 0.04 s |
| Totals | **92 passed, 0 failed, 0 skipped** |

---

## Canonical runtime start

`PI_MEMORY_BEFORE_RUNTIME`: 1.2 Gi used / 6.6 Gi available of 7.9 Gi (swap 0).

Started from repo root:

```text
nohup bash ./run_safenest.sh > logs/runtime.log 2>&1 &
```

`--install` was not used.

| Item | Observed |
|---|---|
| PID | `2262` (single backend; still running at evidence capture) |
| Command | `/home/sandi/safenest-team-main/.venv/bin/python backend/run_backend.py` |
| CWD | `/home/sandi/safenest-team-main/RaspberryPi/Runtime` |
| Preflight | `PI_START_PREFLIGHT` `ok: true` (Pi 5, Python 3.13.5, B23 + historical M-N9 SHA checks both present) |
| Listeners | TCP `0.0.0.0:8000`, TCP `0.0.0.0:9000`, UDP `0.0.0.0:5005` all owned by PID 2262 |
| `/health` | `ok: true`, `ready: true`, `runtime_started: true` |
| `SAFE_NEST_RUNTIME_START` | **PASS** |
| RSS | **318–319 MiB** (`VmRSS` 325184 → 325792 KiB) |
| `%MEM` | 3.9% |
| CPU | ~2.1% while idle with no ESP |
| `PI_MEMORY_WITH_RUNTIME` | 1.5 Gi used / 6.3 Gi available of 7.9 Gi (swap 0) |
| Torch in live process | **YES** (`libtorch` / `libarm_compute*` mapped under the venv) |

Firewall: iptables INPUT/FORWARD/OUTPUT policy **ACCEPT**. Not the cause of missing ESP.

---

## Active mmWave path (software, running process)

Do not treat API `model_id` as live proof: with no packets the mmWave AI result is `SENSOR_NO_DATA` / `source=unavailable` / `model_id=null`.

Evidence that the **running** backend is the B23 PyTorch path, not M-N9:

- Deployed tree is M-PROT-5B `main` (`1df0c17`).
- `OnDeviceAIPipeline` constructs `B23TeamRuntime` (M-PROT-3 → R1 300 @ 10 Hz → R2 621 → frozen B23).
- Manifest selector: `runtime_role=ACTIVE_B23_PROTOTYPE`, `active_runtime_selector=true`, `HISTORICAL_M_N9_NOT_ACTIVE=true`, path `models/mmwave/m_prot_b23/candidate_seed_23.pt`.
- Live process has official CPU torch mapped; M-N9 TFLite was not observed as the mmWave evaluate path.
- `/api/status` `mmwave.runtime_status.artifact_status = PRESENT`.
- Offline 5B tests on this Pi (37/37) reject M-N9 fallback.

| Item | Observed |
|---|---|
| `ACTIVE_MMWAVE_RUNTIME` | **B23** (software path). Live `AIResult` not yet emitted |
| `M_N9_DEFAULT_ACTIVE` | **NO** |
| `M_N9_FALLBACK_OBSERVED` | **NO** |
| `VENDOR_RR_USED_AS_B23_MODEL_INPUT` | **NO** |
| Double-age subtraction in B23 path | **NO** (`Sample.t = ts_monotonic_ms / 1000.0`; `phase_age_ms` freshness only). Live packet arithmetic **not** observed |

Frozen 5B metadata still hard-codes `PI_TORCH_NOT_LIVE_VERIFIED: true` and `LIVE_HARDWARE_EXECUTED: false` on B23 `AIResult` objects. Those flags were **not** rewritten (code-change boundary). Classify as **CURRENT_COMPATIBILITY_BEHAVIOR** until Sol authorizes a metadata update. They do not mean torch failed to import on this Pi.

Risk formula was **not** rewritten. With no mmWave packets, risk component is `UNAVAILABLE` / `MMWAVE_SENSOR_NO_DATA`. Historical vendor-RR `rule_fallback` is still the TEAM compatibility behavior when B23 is unavailable; it is **not** B23 model input.

---

## Live ESP / MR60

Observed continuously after runtime start for **>5 minutes** (plus later re-checks; still zero packets at ~9 minutes). No fake TCP packets were injected. Firmware was not flashed or edited.

| Item | Observed |
|---|---|
| `LIVE_ESP_CONNECTED` | **NO** |
| `LIVE_MR60_CONNECTED` | **NO** (no telemetry from which to infer MR60) |
| TCP `:9000` established | **none** |
| `receiver.connections` | 0 |
| `receiver.disconnects` | 0 |
| `receiver.telemetry_packets` | 0 |
| `receiver.thermal_packets` | 0 |
| `receiver.protocol_errors` | 0 |
| USB serial (`ttyUSB*` / `ttyACM*`) | **absent** on the Pi |
| mmWave `/api/status` | `NO_DATA`, `connected: false`, `boot_id: null` |
| `LIVE_BREATH_PHASE` | **FAIL** (no packets) |
| `LIVE_NESTED_MMWAVE_SEQ` | **FAIL** (no packets) |
| `LIVE_PHYSICAL_TIMESTAMP` | **FAIL** (no packets) |
| `LIVE_BOOT_ID` | **FAIL** (no packets) |
| `LIVE_PRESENCE_TRI_STATE` | **UNVERIFIED** |
| `LIVE_PHASE_EVENT_COUNT` | 0 |
| `LIVE_OBSERVATION_DURATION_S` | ~320 s of runtime observation with zero phase events, still 0 at ~9 min |
| `LIVE_PHASE_CADENCE_HZ` | n/a |
| Nested seq jump counters | n/a (never armed) |
| Window warmup / 30 s ready | **not reached** (`WINDOW_NOT_READY` never even entered; sensor is `NO_DATA`) |
| `R1_SAMPLE_COUNT` live | n/a |
| `R2_ASSEMBLED_DIM` live | n/a |
| `B23_LIVE_INFERENCE` | **FAIL** (no live window) |
| Live B23 state / heads | n/a |
| `B23_INFERENCE_LATENCY_MS` live | n/a (isolated dummy median 0.53 ms only) |
| `STALE_SOURCE_FAIL_CLOSED` | **UNVERIFIED** live; **PASS** in Pi offline 5B tests |
| `BOOT_CHANGE_RESETS_WINDOW` | **UNVERIFIED** live; **PASS** in Pi offline 5B tests |
| `ABSENT_IS_NOT_APNEA` | **PASS** in software/offline mapping (B23 does not emit APNEA). Live ABSENT not observed |

LAN neighbors seen from the Pi: `192.168.137.1` (gateway, STALE) and `192.168.137.25` (REACHABLE/DELAY, MAC `0e:12:48:d3:fb:40`). `.25` answers ping and has **no** common listening ports (22/80/3232/9000/…). Identity was **not** proven to be the ESP. ESP `RPI_HOST` lives in local `secrets.h` (not on this Pi; not dumped). Historical field runbook still documents Pi IP `192.168.0.3`; this host is `192.168.137.189`. Firmware was not changed to retarget.

Blocking condition from the M-PROT-5C contract: **`NO_LIVE_BREATH_PHASE`**.

Operator action required (outside this phase): power/associate ESP+MR60 on this Wi-Fi and ensure flashed `RPI_HOST` is `192.168.137.189` port 9000. That is an ESP secrets/flash step, **not** authorized in M-PROT-5C.

---

## What this phase proved vs what it did not

Proved:

1. Team repo on the Pi is current `main` including merged M-PROT-5B.
2. Canonical venv/Python is the one `run_safenest.sh` uses.
3. Official CPU PyTorch 2.13.0 imports and runs a basic op on aarch64 / cp313.
4. Frozen B23 artifact + scaler + parameter SHA load on that stack without sklearn.
5. Focused 5B/gateway/state/pipeline tests pass on the Pi.
6. SafeNest starts, binds 8000/9000/5005, and keeps torch/B23 as the mmWave software path.
7. Prototype RAM (~319 MiB RSS, ~3.9% of 8 Gi) and isolated inference (~0.5 ms dummy forward) are operationally usable **if** live phase arrives.

Not proved (blocked):

- Live `breath_phase` / nested `mmwave.seq` / physical timestamp / `boot_id` / presence tri-state
- ~30 s causal accumulation, R1=300, R2=621 on live data
- Live B23 breathing / RR / quality through `/api`
- Live fail-closed (stale source, boot reset) on hardware
- Live phase-seq jump / republish / cadence statistics

---

## Boundaries kept

```text
ESP_FIRMWARE_CHANGED: NO
TFLITE_CONVERSION_PERFORMED: NO
CODE_CHANGED: NO
M_PROT_6_STARTED: NO
B23_WEIGHTS_CHANGED: NO
SCALER_CHANGED: NO
RISK_FORMULA_CHANGED: NO
FAKE_TCP_PACKETS_INJECTED: NO
```

Secrets, `.env`, SSH password, and raw telemetry dumps are **not** in this report.

---

## Gate

```text
FINAL_GATE: BLOCKED
LIVE_BLOCKER: NO_LIVE_BREATH_PHASE
TERMINAL_RESULT: M_PROT_5C_LIVE_PI_MR60_SMOKE_BLOCKED
```

Sol review required. Do not merge this evidence as if live MR60 smoke passed. Do not start M-PROT-6 from this report. Re-run the live-sensor half of 5C only after ESP/MR60 actually attach to `192.168.137.189:9000` (firmware/secrets change needs separate owner/Sol authorization).
