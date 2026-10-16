# 고정 자산 확인

- 공개 package ID: `aleph-t04-real-information-board-public-contract-v2`
- 원본 위치: `docs/assets/studio-task-assets/t04-real-information-board/`
- `asset-manifest.json`의 17개 파일을 파일 크기와 SHA-256으로 대조: 17/17 PASS (`node tests.mjs`)
- 업로드된 동일 이름의 README, public-contract, asset-manifest 중복 사본: SHA-256이 각각 일치
- 정상 D1-A→D1-B→D2, 실패 다섯 종류, TIMEOUT→RECOVER-D2: `node tests.mjs` PASS

고정 자산의 날짜와 값은 합성 자료이며 실제 날짜 기록과 분리했습니다.
