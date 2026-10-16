# 오늘의 진짜 정보판 (T04)

서울 시청 인근의 공개 2m 기온을 Open-Meteo에서 조회해 값·단위·출처·원천 관측 시각·조회 시각·Asia/Seoul 기준 날짜를 함께 보여주는 정적 웹 앱입니다. API 키와 사용자 계정이 필요 없습니다.

## 실행

`docs/`를 정적 서버로 제공하세요. 예: `python3 -m http.server 8765 --directory docs`. GitHub Pages는 `main` 브랜치의 `/docs`를 사용합니다.

## 저장과 실패

정상 응답은 `docs/core.mjs`에서 공개 계약의 정규화 형식으로 변환하고 검증합니다. `docs/store.mjs`는 IndexedDB의 한 트랜잭션에서 상태 전체를 읽고 갱신합니다. 일별 고유키는 `signal_id + record_date`입니다. 같은 KST 날짜는 같은 행을 갱신하고, 다음 날짜만 새 행을 만듭니다. 오류는 마지막 정상값을 보존하고 별도의 `stale / error_code` 상태를 저장합니다. 실제 조회와 합성 재생은 다른 저장 범위를 사용합니다.

고정 자산 원본은 `docs/assets/studio-task-assets/t04-real-information-board/`에 있으며, 공개 package ID와 파일별 SHA-256은 `node tests.mjs`에서 검증합니다. 다섯 실패와 복구는 합성 값으로만 재생합니다.

## 실제 날짜 기록

실제 두 날짜 조건은 합성 fixture로 대신할 수 없습니다. 공개 원천에서 서로 다른 Asia/Seoul 날짜에 실제 조회가 성공해야 합니다. 브라우저 IndexedDB의 일별 행 두 건과 화면 변화값을 비교하세요. 어제 대비는 전날 기록이 있을 때만 계산합니다. 화면의 **일별 기록 JSON 내려받기**는 원자료와 저장값을 함께 내보냅니다. 지금 저장된 날짜가 하나라면 다음 실제 날짜에 다시 조회해야 합니다. 기록을 조작하지 않습니다.

## 검사

`node tests.mjs`는 자산 해시, 같은 날 3회 갱신, 다음 날짜 새 행, 다섯 실패, 복구, KST 자정 경계와 정규화 값을 확인합니다. 브라우저 조작 검사 결과는 `evidence/browser-qa.md`에 적습니다.
