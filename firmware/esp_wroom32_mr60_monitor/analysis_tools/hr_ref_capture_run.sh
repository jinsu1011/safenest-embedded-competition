#!/bin/bash
BASE="/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회"
PY="$BASE/firmware/esp_wroom32_mr60_monitor/.venv/bin/python"
OUT="$BASE/firmware/esp_wroom32_mr60_monitor/logs/kpi/2026-07-26_heartrate_ref_applewatch_run2_300s.jsonl"
SCR="/private/tmp/claude-501/-Users-kimjinsu-Desktop------/deca0af1-4fbf-4552-892c-762b185e2122/scratchpad"

START=$(date +%s)
echo "start_epoch=$START" > "$SCR/hr_ref2_start.txt"
date -r "$START" "+start_local=%Y-%m-%d %H:%M:%S" >> "$SCR/hr_ref2_start.txt"

afplay /System/Library/Sounds/Glass.aiff &
say -v Yuna "두 번째 심박 비교 시작합니다. 상체 고정해 주세요." &

"$PY" "$BASE/firmware/esp_wroom32_mr60_monitor/capture_serial.py" \
  --port /dev/cu.usbserial-10 --baud 115200 \
  --duration 300 --output "$OUT" > "$SCR/hr_ref2_capture.log" 2>&1 &
CAP=$!

"$PY" "$SCR/hr_watchdog.py" "$OUT" 295 > "$SCR/hr_ref2_watchdog.log" 2>&1 &
WD=$!

for i in $(seq 1 10); do
  TARGET=$((START + 30 * i))
  while [ "$(date +%s)" -lt "$TARGET" ]; do sleep 1; done
  afplay /System/Library/Sounds/Tink.aiff &
  say -v Yuna "체크 $i" &
done

wait $CAP
kill $WD 2>/dev/null
afplay /System/Library/Sounds/Hero.aiff &
say -v Yuna "캡처 완료. 열 개 숫자 알려주세요." &
echo "DONE" >> "$SCR/hr_ref2_start.txt"
