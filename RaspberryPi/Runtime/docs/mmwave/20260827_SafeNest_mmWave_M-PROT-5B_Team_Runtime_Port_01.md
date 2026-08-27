# M-PROT-5B — Team repository Pi-runtime port (B23)

Software integration only. **No physical Raspberry Pi. No live MR60.**
`PI_TORCH_NOT_LIVE_VERIFIED`. M-PROT-5C remains deferred.

## Old active path

`RaspberryPi/Runtime/ai/mmwave_canonical_runtime.py` (M-N4, 30 s ~8 Hz **240** tensor)
→ spectral apnea contradiction
→ `LazyModel("mmwave")` / M-N9 INT8
→ `NORMAL / RAPID_OR_ABNORMAL / APNEA-proxy`

That path is **legacy / non-default**. Modules remain on disk for isolated tests.
There is no B23→M-N9 fallback, no spectral physiology override, and no vendor-RR model input.

## New active path

Team TCP telemetry (`breath_phase`, `ts_monotonic_ms - phase_age_ms`, sequence, `session_id`, `human_detected_raw`)
→ `ai/mmwave_b23_bridge.py` (SW-01 `StreamBundle`)
→ M-PROT-3 causal composer
→ R1 (owns resampling; exactly 300 @ 10 Hz)
→ R2 (621 features)
→ frozen B23 (`pytorch`)
→ existing `AIResult` / `/api` mmWave state

Presence comes only from explicit occupancy (`human_detected_raw` / `presence` + `presence_available`).
ABSENT ≠ APNEA. UNAVAILABLE ≠ NOT BREATHING. RR is not clamped.

## Risk semantic

B23 does not emit the old three classes. Eligible prototype output is mapped with
`score=0.0` and `risk_contribution_deferred=True`. No APNEA invention.
When B23 is unavailable, the existing vendor-RR **risk rule_fallback** still applies
(unchanged formula). That rule is not B23 model input.

## Identities (unchanged)

| Item | Value |
|---|---|
| Artifact SHA-256 | `8f7de6f50d6ff62ff9b0ebfaed0b1fccd8d194c7e33781bc5b93366fae251a2c` |
| Parameter SHA-256 | `6db949c242e25888dd20c3fc8e2305af03448aa229e3ca73e4159216a266d78e` |
| Scaler content SHA | `5a2583b5b5064be5480b0cf56f2a2c12d40a4a2d005eb087dc8e12106881159c` |
| Source repo / SHA | `https://github.com/sheepmeat/test.git` / `809b78626b442f146eccd73595f239b93de3ae2e` |
| Target base | `aea6083ef2dd6fea8d8e911ebec8dcdc2e3e89e9` |

## Source file classification

| Source | Team destination | Action |
|---|---|---|
| `adapters/mmwave_sw01_interface_checker.py` | `Runtime/ai/mmwave_prototype/` | COPY_AS_RUNTIME_MODULE (imports retargeted) |
| `adapters/mmwave_sw01_source.py` | same | COPY_AS_RUNTIME_MODULE |
| `adapters/mmwave_r1_sensor_independent_trace.py` | same | COPY_AS_RUNTIME_MODULE |
| `adapters/mmwave_r2_representation_features.py` | same | COPY_AS_RUNTIME_MODULE |
| `adapters/mmwave_m_prot_2_b23_runtime.py` | same | ADAPT_INTO_TEAM_RUNTIME (asset root = Ondevice_AI) |
| `adapters/mmwave_m_prot_3_integration_runtime.py` | same | ADAPT_INTO_TEAM_RUNTIME |
| `scripts/mmwave_m_pv2_candidate_training.py` | `Runtime/ai/mmwave_prototype/trace_model_support.py` | ADAPT — runtime extract only, **no sklearn** |
| `models/mmwave/m_pv2/family_b/candidate_seed_23.pt` | `Ondevice_AI/models/mmwave/m_prot_b23/` | COPY_AS_MODEL_ASSET |
| `datasets/mmwave/manifests/M-PV2_candidate_training/scaler_statistics.json` | same dir | COPY_AS_CONFIG |
| Team `ai/pipeline.py` | — | REPLACE_ACTIVE_MMWAVE |
| Team `ai/mmwave_canonical_runtime.py` | — | LEGACY_RETAIN_NONACTIVE |
| Team `ai/mmwave_spectral_runtime.py` | — | LEGACY_RETAIN_NONACTIVE (non-authoritative) |
| Thermal / CO2 / PIR / LCD / Web / risk formula | — | PRESERVE |

## Dependencies

- Mac/dev: `torch>=2.1.0` in `Ondevice_AI/requirements.txt` and `requirements-mac.txt`
- Pi install file: torch **commented**; scipy added for R1 resampling
- `SCIKIT_LEARN_RUNTIME_DEPENDENCY`: **NO** for the B23 path (runtime extract)

## What remains for M-PROT-5C

Install/verify PyTorch on the Pi, pull this branch, run live MR60 smoke.
Do not start M-PROT-5C from this report.
