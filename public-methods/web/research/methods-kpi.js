"use strict";
(async () => {
  const status = document.getElementById("kpi-status"), host = document.getElementById("kpi-results");
  const n = (tag, text, cls) => { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; };
  const section = (title, explanation) => { const e = n("section", undefined, "methods-kpi-section"); e.append(n("h2", title), n("p", explanation, "methods-muted")); host.append(e); return e; };
  const metric = (parent, label, value, note) => { const e = n("div", undefined, "methods-kpi-row");e.append(n("span", label),n("strong", value),n("small", note));parent.append(e); };
  try {
    const response = await fetch("/research/api/methods/evaluation/report", {credentials:"omit"});
    if (!response.ok) throw new Error("not_ready"); const report = await response.json(); const s = report.summary;
    status.textContent = `측정 시각 ${new Date(report.measured_at).toLocaleString("ko-KR", {timeZone:"Asia/Seoul"})} KST · 같은 편집자가 만든 개발 회귀 · ${report.environment || "고정된 공개 코퍼스"}`;
    const retrieval = section("상황과 목적에 맞는 방법 찾기", "표현을 바꾼 16개 질문과 범위 밖 질문 4개. 같은 코퍼스와 질문을 두 검색 방식에 적용했습니다.");
    for (const [mode,label] of [["hybrid","단어·의미 결합"],["lexical","단어 검색"]]) {
      const r = s[mode];metric(retrieval, `${label} · 첫 번째 후보`, `${r.top1} / ${r.positive_n}`, `5개 후보 내 ${r.top5}/${r.positive_n} · 범위 밖 정상 기권 ${r.valid_abstentions}/${r.negative_n} · 서비스 오류 ${r.service_errors}`);
      metric(retrieval, `${label} · 응답 시간`, `${r.median_seconds.toFixed(2)}초`, `중앙값 · p95 ${r.p95_seconds.toFixed(2)}초 · 이 회차의 관측치`);
    }
    if (report.legacy_regression) {
      const r = report.legacy_regression.summary.hybrid;
      const prior = section("이전 기술 질문을 다시 물었을 때", "과거에 평가한 질문을 55개로 확장된 코퍼스에 다시 적용했습니다. 새 독립 평가가 아닙니다. 불리한 결과도 같은 분모로 보존했습니다.");
      metric(prior,"의도한 방법 · 첫 번째 후보",`${r.top1} / ${r.positive_n}`,`5개 후보 내 ${r.top5}/${r.positive_n}`);
      metric(prior,"범위 밖 질문의 정상 기권",`${r.valid_abstentions} / ${r.no_material_n}`,"실패: 세부 기술 문제에도 일반 조언이나 다른 도구의 방법이 후보로 나옴");
      metric(prior,"명시적으로 충돌하는 방법 제외",`${r.excluded_absent} / ${r.conflict_n}`,"명시된 조건 충돌만 검사. 자유 문장의 모든 제약을 이해한 것은 아님");
      for (const failure of r.failures) prior.append(n("p",`${failure.case}: ${failure.titles.join(" / ") || "의도한 후보 누락"}`,"methods-meta"));
    }
    const graph = section("고유 ID를 따라 기록과 출처 읽기", "코퍼스의 모든 방법을 재조회해 연결 구조를 확인했습니다. 출처 내용의 진실성이나 전문가의 동의를 검증한 수치가 아닙니다.");
    for (const [field,label,denominator] of [["stable_graph","반복 조회 시 같은 연결 ID",s.graph.methods],["no_dangling_edges","사라진 대상이 없는 연결",s.graph.methods],["source_links_match_record","출처 링크와 원래 기록 일치",s.graph.source_methods],["exact_feedback_versions","적용·의견의 정확한 방법 버전",s.graph.feedback_methods]]) metric(graph,label,`${s.graph[field]} / ${denominator}`,"해당 연결이 있는 방법만 분모에 포함한 구조 검사");
    const c = s.context, context = section("에이전트에게 전달하는 문맥", "기대 정답 방법을 이미 안다는 가정으로 그 원문 1개를 추가 조회한 크기입니다. 에이전트가 실제로 선택하거나 같은 품질의 답변을 생성한 시험은 아닙니다.");
    metric(context,"문맥 상한과 토큰 계수 일치", c.all_within_cap?`${c.budget_checks} / ${c.budget_checks}`:"일부 실패", "256·1024·2048 상한 · o200k JSON 텍스트 계수");
    metric(context,"기대 방법의 참조 ID 유지",`${c.reference_retained_checks} / ${c.budget_checks}`,"참조가 있다는 뜻이며 답변에 충분하다는 뜻은 아님");
    metric(context,"상위 후보 5개 원문 합계",c.full_top5_tokens.toLocaleString()+" 토큰",`${c.cases}개 질문의 합계 · 비교 입력 자료`);
    metric(context,"1024 참조 묶음 + 선택한 원문 조회",c.compact_plus_fetch_tokens.toLocaleString()+" 토큰","실제 선택 결과의 품질과 청구 토큰은 미측정");
    if (report.incremental_index) { const i = report.incremental_index, e = section("바뀌지 않은 임베딩 재사용", "같은 코퍼스와 고정된 임베딩 설정으로 색인을 다시 실행했습니다."); metric(e,"기존 필드 재사용",String(i.reused_fields),`새 임베딩 ${i.embedded_fields} · 색인 바이트 ${i.index_unchanged?"유지":"변경"}`); }
  } catch (_) { status.textContent = "검토된 결과를 아직 불러올 수 없습니다. 잠시 후 다시 열어주세요. 미확인 수치를 0이나 성공으로 표시하지 않습니다."; }
})();
