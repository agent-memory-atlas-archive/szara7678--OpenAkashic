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
    const verdict = section("효과가 있는가? 현재의 결론", "방법 검색과 근거 연결은 작동합니다. 더 좋은 산출물을 만든다는 일반적인 효과는 아직 입증되지 않았습니다.");
    verdict.classList.add("methods-kpi-verdict");
    verdict.append(n("p", "그래프는 연결을 탐색하는 화면과 API입니다. 에이전트가 모든 그래프를 읽도록 요구하지 않습니다. 상황·목적으로 짧게 검색하고 필요한 방법만 조회하는 흐름을 우선 사용합니다.", "methods-muted"));
    if (report.application_evaluation) {
      const q=report.application_evaluation;
      const e=section("새 실험 · 6개 과제, 18개 실제 답변", "장애 대응·인터뷰·팀 결정·안내문·학습·오픈소스 기여 과제를 답변 생성 전에 동결했습니다. Luna 세 조건: 자료 없음 / 동일 기록 평면 JSON / 동일 기록 중첩 JSON. 조건을 가린 Sol 평가입니다. 자료는 수동으로 골랐으며 검색이나 그래프 UI의 효과 시험은 아닙니다.");
      metric(e,"방법 적합성 · 실행 가능성 · 근거 경계", "세 조건 모두 35 / 36", "모델 평가, 과제당 1회. 실제 업무 수행·사람의 평가·통계적 우위가 아닙니다.");
      metric(e,"의미 기준 원점수 · 무자료 / 평면 / 중첩", "24 / 23 / 23 (각 24점)", "채점 해석 불일치 1개를 별도 감사. 같은 엄격 기준은 모두 23점, 같은 완화 기준은 모두 24점. 원점수와 불리한 결과 보존.");
      metric(e,"220단어 제한 준수", "6 / 6 · 3 / 6 · 6 / 6", "같은 순서. 평면형 초과 4·12·6단어. 작은 단일 실행 관측입니다.");
      metric(e,"같은 자료의 입력 표현 크기", "6,857 → 5,959 추정 토큰", "평면 leaf-path JSON 대비 일반 중첩 JSON 13.1% 감소. 직렬화 차이이며 그래프·검색·웹 문맥 복사의 절감률이 아닙니다. 실제 사용량·비용 미측정.");
      e.append(n("p","자료가 있는 두 조건은 안내문의 근거 없는 최상급을 제거했습니다. 하지만 인터뷰의 유도 질문과 의사결정 기한을 놓치는 위험도 남았습니다. 전반적인 산출물 품질 우위는 확인되지 않았습니다.","methods-muted"));
      const a=n("a","과제·18개 답변·원채점·감사·재현 자료 보기 ↗");a.href="https://github.com/szara7678/OpenAkashic/tree/main/public-methods/benchmarks/application-2026-10-28";a.target="_blank";a.rel="noopener noreferrer";e.append(a);
      const details=n("details");details.append(n("summary","실제 안내문 답변 나란히 읽기"));
      for(const [label,answer] of Object.entries(q.example_outputs||{})){details.append(n("h3",label),n("p",answer));}e.append(details);
    }
    if (report.navigation_workload) {
      const nav = report.navigation_workload, v=nav.summary;
      const e = section("새 측정 · 연결을 따라 기록 찾기", `측정 ${new Date(nav.measured_at).toLocaleString("ko-KR",{timeZone:"Asia/Seoul"})} KST · 현재 코퍼스의 정확한 URL·ID 조회. 자연어 답변 생성이나 사람의 탐색 시험이 아닙니다.`);
      metric(e,"같은 출처를 등록한 방법 모두 찾기",`${v.source_success} / ${v.source_tasks}`,"등록된 ID·버전을 평면 원기록과 대조했습니다. 출처의 진실성 검증이 아닙니다.");
      metric(e,"정확한 버전의 적용 보고·의견 찾기",`${v.feedback_success} / ${v.feedback_tasks}`,"보고와 의견의 ID·버전을 비교. 보고된 성공을 독립적으로 검증한 것은 아닙니다.");
      metric(e,"출처 탐색 · 그래프 응답 합계",`${v.shared_graph_tokens.toLocaleString()} 토큰`,`${v.source_tasks}개 출처 · 반복 메타데이터 포함 · o200k JSON 자료`);
      metric(e,"강한 비교 기준 · 평면 URL 색인 한 번 읽기",`${v.flat_index_once_tokens.toLocaleString()} 토큰`,"같은 공개 원기록으로 실제 구성한 전체 URL→방법 참조 색인. 메모리에서 재사용할 수 있습니다.");
      e.append(n("p","이 과제에서는 재사용 가능한 평면 색인이 더 작았습니다. 그래프가 항상 토큰을 줄인다는 근거로 쓰지 않습니다.","methods-muted"));
      metric(e,"적용 기록 읽기 · 그래프 / 방법 전체",`${v.feedback_graph_tokens.toLocaleString()} / ${v.feedback_direct_tokens.toLocaleString()}`,`같은 ${v.feedback_tasks}개 방법 합계. 필요한 필드만 남긴 평면 투영은 ${v.feedback_flat_projection_tokens.toLocaleString()} 토큰으로 더 작음. 답변 품질·청구량 비교 아님.`);
    }
    if (report.output_quality_comparison) {
      const q=report.output_quality_comparison;
      const e=section("실제 산출물 비교 · 우위는 관찰되지 않음",`기존 공개 실험 ${q.generated_at} · 합성 디자인 과제 2개에 자료 없음 / 원문 직접 참조 / 아카식 검색의 세 조건을 적용했습니다. 이번 회차에 새로 생성한 결과가 아닙니다.`);
      metric(e,"전시 페이지 기능 과제", "세 조건 모두 7 / 7", "기능 차이 없음. 시각 검토는 모델 의견이며 동률 항목도 있었습니다.");
      metric(e,"공방 예약 페이지 기능 과제", "세 조건 모두 12 / 12", "사람의 선호·수정 시간·실제 예약 성과·청구 토큰은 미측정.");
      const a=n("a","여섯 산출물과 비교 기준 직접 보기 →");a.href="/research/methods/design-lab/";e.append(a);
    }
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
