# 예외 지식 전이 시험 protocol v1

이 파일은 실행 계획이다. 참가자 답안 생성이나 답안 실행을 하지 않았다. 공개 원문에서 먼저 고정한 6카드에 맞춘 조건부 시험이며 OpenAkashic의 일반 효용을 대표하는 무작위 표본이 아니다. 실패 snippet은 진단용으로 작성한 상황이다. 실제 장애를 새로 재현한 기록이나 운영 개선 성과로 세지 않는다.

## 자료와 누출 차단

- corpus: ../corpus/source-cards.json 및 ../corpus/sources.md. 기준 JSON SHA256: 49e4a6fd64c0d8a7924f68d8e9171714b7991bc7765f37d510150e6e40cbb66c.
- 과제 작성자는 이 두 공개 파일과 거기에 연결된 고정 원문 9개만 읽었다. 이전 평가 답안, 개인 메모리, 다른 프로젝트는 사용하지 않았다.
- 원문 고정 commit을 직접 읽어 24개 gold 판정을 대조했다. 근거는 자체 설명이며 원문 문장 인용은 넣지 않았다. JSON의 과거 행번호 메모 대신 실제 원문에서 다시 확인한 행번호를 gold에 썼다.
- tasks.json/gold.json을 먼저 고정하고 SHA256을 기록한 뒤에만 24회 생성 실행을 시작한다. 생성 답안을 보고 문제, 정답, enum, rubric을 바꾸지 않는다.
- 참가자에게는 해당 task.prompt 문자열만 제공한다. task ID/제목, gold, rubric, 다른 문제, source ID, 특정 검색어 또는 정답 method를 제공하지 않는다. 답안 형식은 prompt에 완결되어 있다. answer_contract는 runner의 검증용 JSON Schema이다.
- retrieval arms에는 지정된 공개 source pool만 검색 가능한 도구를 제공한다. 참가자가 task에서 직접 검색어를 정한다. gold 또는 task를 검색 인덱스에 넣지 않는다. 풀 경로/도구 사용법은 runner 공통 안내로만 제공한다.

## 고정 설계

같은 Luna 모델을 사용하며 4 tasks × 3 arms × 2 repeats = 24 runs이다. 모든 run은 새 컨텍스트/독립 세션과 독립 임시 디렉터리를 사용한다. 앞선 run의 답, 캐시, 대화, 메모리, 검색 기록을 다음 run에 전달하지 않는다.

- base: 외부 검색 없이 동일한 task prompt와 공통 응답 지침을 받는다.
- flat: 같은 source-cards.json의 모든 정보와 source 메타데이터를 일반 문서 형태로 펼친 검색 풀을 사용한다.
- structured: flat과 동일한 정보량/원문 레코드/카드의 내용을 구조화한 OpenAkashic 검색 풀을 사용한다.

flat과 structured는 의미 내용이 같아야 한다. structured에만 추가 요약·해결책·정답을 넣지 않는다. 원문 접근이 허용되면 두 arm에 같은 고정 원문 범위를 허용하며 일반 웹과 다른 저장소 접근은 차단한다. 두 retrieval arm은 검색 횟수, 반환 텍스트 예산, 답변 토큰 예산, 도구 시간 제한을 같게 한다. 검색 표현/검색 결과 품질 차이는 평가 대상이지만 정보 추가와 혼동하지 않는다.

실행 전 별도 runner manifest에 정확한 Luna model/deployment/version, sampling/seed 정책, prompt hash, 공통 지침, 각 arm pool hash, 검색/텍스트/토큰/시간 예산, 도구 버전과 run 순서를 기록하고 고정한다. task별 repeat 블록 안에서 arm 순서를 균형 있게 배치하고 실행 순서를 보존한다. seed를 지원하면 같은 task/repeat의 arm들에 같은 seed를 쓰고, 미지원이면 미지원이라고 기록한다. 다른 모델이나 fallback 출력은 본시험에 섞지 않는다.

도구 실패와 모델 추론 실패를 구분한다. 모델 출력 전 인프라 오류만 같은 설정으로 재실행 가능하며 실패 로그도 보존한다. 답안을 보고 재시도하거나 교정 메시지를 보내지 않는다. schema 설명은 답안 예시/정답 피드백이 아니다.

## 점수

각 run의 객관 점수는 q1~q6의 정확한 JSON 값과 타입 일치 1점씩, 합계 0..6이다. bool과 0/1은 다르며 숫자와 숫자 문자열도 다르다. enum 별칭/동의어는 인정하지 않는다. unknown은 해당 enum에서만 허용한다. rationale/fix/limitations로 잘못된 decisions 값을 보정하지 않는다.

JSON 파싱 실패는 0점이다. 파싱되지만 schema 위반이면 위반 항목과 schema_valid=false를 별도로 기록하고, q1~q6 중 정확한 타입/값을 가진 항목만 채점한다. 누락 항목/허용하지 않은 값은 각 0점이며 불필요한 키는 해당 형식 위반을 기록한다. 따라서 형식 준수와 지식 판정을 별도로 확인할 수 있다.

실무 설명은 객관 점수와 별도의 전문성 보조지표로만 평가한다. arm/repeat/model을 가린 답안의 rationale/fix/limitations를 gold의 task별 rubric으로 평가한다. 조건 정확성, 수정 가능성, 불확실성 처리 각 0..2점, 합계 0..6이다. 정답 판정/인용 개수/문장 길이/출처 이름 자체는 추가 점수가 아니다. 출처를 많이 붙였다는 이유로 가점하지 않는다. 한 평가자가 모든 arm에 같은 기준을 적용하고 평가자와 판정 메모를 기록한다. 추가 평가자가 있으면 독립 판정과 불일치 조정 규칙을 실행 전 고정한다.

arm별 객관 평균(0..6), task별 두 반복 점수, flat-base/structured-flat의 같은 task/repeat 차이, schema 준수율, 보조지표를 각각 보고한다. 작은 표본에서 유의성이나 일반 실무 성능을 단정하지 않는다. retrieval 횟수/지연/반환 텍스트량도 비용 지표로 별도 보고한다. 점수나 출처 수는 운영 개선·서버 효과·실제 적용 성공을 입증하지 않는다.

## 파일

- tasks.json: 4개의 참가자용 prompt와 기계 검증 contract.
- gold.json: 24개 객관 정답, 원문 ID/행 근거/이유, task별 블라인드 설명 rubric.
- SHA256SUMS: 고정 파일의 SHA256. 실행 전 동일성을 다시 확인한다.

작성/검증 중 생성 답안을 실행하지 않았다. 패키지 실제 동작 테스트는 별도 검증이며, 이 문서의 사전 판정과 구분해서 보존해야 한다.
