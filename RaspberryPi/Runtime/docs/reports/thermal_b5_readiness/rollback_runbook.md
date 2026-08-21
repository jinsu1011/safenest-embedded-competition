# Thermal B5 운영 전환 rollback runbook

상태: **NOT EXECUTED**. 현재는 selector를 변경하지 않았으므로 즉시 rollback할 변경도 없다.

## 전환 전 필수 백업

Pi의 실제 저장소 경로와 프로세스 소유자를 먼저 확인한다. 현재 문서의 `/home/pi/safenest/team-safenest-embedded`는 승인 후 사용할 표준 제안 경로이며, 실제 운영 경로라고 주장하지 않는다.

```bash
cd /home/pi/safenest/team-safenest-embedded
git rev-parse HEAD
git status --short
sha256sum RaspberryPi/Ondevice_AI/config/models.yaml \
  RaspberryPi/Ondevice_AI/models/model_manifest.json \
  RaspberryPi/Ondevice_AI/models/thermal/thermal_fall_int8_v0.1.0.tflite
mkdir -p /var/lib/safenest/rollback/thermal-b5/pre-switch
cp -p RaspberryPi/Ondevice_AI/config/models.yaml \
  /var/lib/safenest/rollback/thermal-b5/pre-switch/models.yaml
cp -p RaspberryPi/Ondevice_AI/models/model_manifest.json \
  /var/lib/safenest/rollback/thermal-b5/pre-switch/model_manifest.json
```

`mkdir`, `cp`, 프로세스 중지/재시작은 운영 변경이므로 별도 승인 후 담당자가 실행한다.

## rollback 절차

1. SafeNest 실행 프로세스의 실제 supervisor를 확인하고 새 입력 수신을 안전하게 중지한다. 이 저장소는 systemd unit을 정의하지 않으므로 임의의 service 이름을 사용하지 않는다.
2. selector 두 파일을 백업본으로 복원한다.
3. diff와 모델 SHA를 확인한다.
4. 담당자가 기존 실행 방식으로 Runtime을 다시 시작한다. 저장소 표준 수동 실행은 `./run_safenest.sh`다.
5. `/health`, `/api/status`, TCP `:9000`, UDP `:5005`, 네 센서 freshness, 위험 레벨, logger drop 증가 여부를 확인한다.

```bash
cd /home/pi/safenest/team-safenest-embedded
cp -p /var/lib/safenest/rollback/thermal-b5/pre-switch/models.yaml \
  RaspberryPi/Ondevice_AI/config/models.yaml
cp -p /var/lib/safenest/rollback/thermal-b5/pre-switch/model_manifest.json \
  RaspberryPi/Ondevice_AI/models/model_manifest.json
git diff -- RaspberryPi/Ondevice_AI/config/models.yaml \
  RaspberryPi/Ondevice_AI/models/model_manifest.json
sha256sum RaspberryPi/Ondevice_AI/models/thermal/thermal_fall_int8_v0.1.0.tflite
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/api/status
```

## rollback 성공 기준

- production manifest가 기존 `thermal_fall_int8_v0.1.0.tflite`를 선택한다.
- 기존 모델 SHA가 manifest와 일치한다.
- Runtime health와 네 센서 상태가 전환 전 수준으로 회복한다.
- Thermal AI가 stale/invalid frame을 사용하지 않는다.
- 새 DANGER/emergency 또는 logger drop이 rollback 때문에 발생하지 않는다.

