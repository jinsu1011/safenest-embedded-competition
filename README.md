# SafeNest Embedded Competition

팀원별 작업 브랜치를 `main`에서 한눈에 확인할 수 있도록 GitHub 사용자명 기준의 최상위 폴더로 정리한 통합본입니다.

## 팀원별 폴더

| 폴더 | 원본 브랜치 | 원본 커밋 | 주요 작업 |
| --- | --- | --- | --- |
| [`jinsu1011/`](./jinsu1011/) | `codex/mmwave-phase-integration` | `e177886` | MR60 mmWave 통합, 실측·분석 및 On-Device AI 연동 |
| [`yuname121/`](./yuname121/) | `3D_Print` | `df2b12f` | 3D 프린팅 하우징 및 패널 모델 |
| [`sheepmeat/`](./sheepmeat/) | `main` + `Ondevice_AI` | `34ae6c5` + `d97df3e` | 기존 공통 기반과 SafeNest V4 On-Device AI 통합 |

각 폴더는 해당 팀원의 작업 상태를 독립적으로 확인하고 재현할 수 있도록 원본 브랜치의 디렉터리 구조를 보존합니다. 기존 브랜치는 삭제하지 않았습니다.

## 통합 원칙

- 기존 `main`의 파일은 `sheepmeat/` 아래로 이동해 보존했습니다.
- `Ondevice_AI`의 파일은 `sheepmeat/`에 합쳐 기존 `main` 전용 문서와 설정을 유지했습니다.
- 다른 두 작업 브랜치는 각각의 사용자명 폴더에 전체 스냅샷으로 보존했습니다.
- 브랜치별 실행 및 검증 방법은 각 폴더의 `README.md`와 관련 문서를 참고하세요.
