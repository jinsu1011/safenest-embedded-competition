# ondevice_ai Integration Source Snapshot

- Standalone source repository: `https://github.com/sheepmeat/test`
- Standalone source SHA: `9a66a3b21baef9a6a51cb1a66942284c63d0b8a4`
- Team repository: `https://github.com/jinsu1011/safenest-embedded-competition`
- Team base SHA: `6baf38d8df936b694a1ff2e9b5e5fb2af2bfe50f`
- Destination: `ondevice_ai/`
- Branch: `feature/ondevice-ai-multisensor-sync`

## Included phase state

- mmWave: M-A0..M-A6, M-B0..M-B5
- CO₂: C-A0..C-A6
- Thermal: T-A0..T-A4

## Decision artifacts

- `collision_matrix.json`
- `collision_summary.md`
- `apply_plan.json`

## Intentionally excluded

- `.git/`, `.github/`, `archive/`, `hardware/`, `releases/`, `repro_test_dir/`
- `datasets/raw_archives/` and ignored raw/thermal payloads
- local caches, credentials, absolute-path metadata
