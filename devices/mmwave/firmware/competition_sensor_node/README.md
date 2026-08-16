# SafeNest competition sensor node

The Arduino sketch in this directory collects the integrated SafeNest sensor
data and streams it to the Raspberry Pi runtime over Wi-Fi/TCP.

Before uploading the sketch, copy `secrets.example.h` to `secrets.h` locally
and configure the Wi-Fi credentials and Raspberry Pi address. `secrets.h` is
ignored by the repository and must not be committed.

The current matching receiver and dashboard live in `integration/`. Setup and
communication guides live in `docs/competition_runtime/`. The earlier duplicate
copy is retained only as historical reference under
`archive/legacy_prototypes/ondevice_ai_competition_runtime_20260816/`.
