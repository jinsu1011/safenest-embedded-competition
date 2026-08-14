# TFLite Offline Benchmark

센서 없이 기존 CSV delivery를 locked M-B11 preprocessing과 실제 int8 TFLite model에 통과시킨 결과다.

## 실행 대상

- TensorFlow `2.21.0`
- CPU, 1 thread, XNNPACK delegate
- model SHA-256: `6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5`
- input: `[1,300,1]`, `int8`, scale `0.041720833629369736`, zero-point `-3`
- output: `[1,3]`, `int8`, scale `0.00390625`, zero-point `-128`

## 실행 결과

- 입력 window: 620개
- 실제 `invoke`: 620회 모두 성공
- input saturation: 0%
- input quantized range: `-12 ~ 9`
- 평균 latency (`set_tensor + invoke`): `0.008197 ms`
- median/p50: `0.008041 ms`
- p95: `0.008333 ms`
- 최대: `0.052583 ms`
- 예측 결과: `NORMAL 0`, `RAPID_OR_ABNORMAL 0`, `APNEA 620`

`NORMAL_D06/D09/D12/D15`와 `BREATH_PACED_12/15/20` 모든 source label 그룹에서도 예측은 전부 APNEA였다. 따라서 현재 CSV delivery를 locked model에 직접 넣었을 때 **class collapse 또는 domain mismatch 의심 신호**가 확인됐다.

모든 입력이 APNEA로 나온 것은 성능 통과가 아니다. 기존 CSV의 `NORMAL_D06`, `BREATH_PACED_12` 같은 labels는 모델의 `NORMAL/RAPID_OR_ABNORMAL/APNEA`에 대한 독립 ground truth가 아니므로 accuracy·F1을 계산하지 않았다. 이 결과는 **실제 model invoke와 출력 편향 확인**이며, formal 성능 평가가 아니다.

또한 latency는 Apple Silicon 개발 host에서 측정한 값이다. Raspberry Pi 또는 ESP32의 배포 latency로 해석하면 안 된다.
