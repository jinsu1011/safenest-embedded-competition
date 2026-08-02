# 브랜치 및 자산 provenance

## 통합 기준

| 영역 | 원본 ref | 원본 경로 | 최종 경로 |
|---|---|---|---|
| V4 센서·추론·위험도·테스트 | `origin/Ondevice_AI` (`d97df3e`) | `./` | `src/`, `models/`, `datasets/`, `config/`, `tests/` |
| MR60 AI/ESP 보강 | `codex/mmwave-phase-integration` (`b0d3c95`) | `./`, `firmware/` | `src/`, `firmware/`, `datasets/`, `config/`, `docs/` |
| CAD 4종 | `origin/3D_Print` (`35c1e1f`) | 루트 STL 4종 | `hardware/3d_print/` |
| 초기 위험도 엔진 | `origin/main` 계보 | `pi/` | `archive/legacy_prototypes/pi/` |
| 기획 PDF | `66eb105` | `docs/ai/roadmap_and_setup/` | `docs/planning/` |

통합 기준 브랜치는 fetch 후 `origin/main`의 `01a4acb`이며, 작업 시작 전 로컬 복구 지점과 전체 해시는 루트 `INTEGRATION_PROGRESS.md`에 기록했다.

## 중복 처리 원칙

- 팀원명 디렉터리의 파일은 삭제 전 기능 브랜치 tree와 비교했다.
- 최신 끝점에 없는 고유 자산은 별도 복원했으며, legacy 구현은 `archive/`로 이관했다.
- V4 `config/risk_rules.yaml`만 공식 위험 규칙 원본으로 사용한다. JSON 사본은 실행 경로 밖 archive에 둔다.
- 모델, NPZ, JSONL, STL은 이름이 같아도 blob 또는 내용 비교 없이 덮어쓰지 않는다.

## 현재 확인할 수 없는 자산

프롬프트에 언급된 `.docx`와 dashboard `index.html`은 접근 가능한 모든 로컬·원격 ref에서 발견되지 않았다. 원본이 제공될 때까지 결손으로 유지하며 임의 재생성하지 않는다.
