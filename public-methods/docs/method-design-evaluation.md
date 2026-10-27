# Open-ended design application comparison

Public viewer: `/research/methods/design-lab/`. Two synthetic briefs (exhibition
introduction and workshop booking) were implemented under three conditions:
brief only, original public documents, and OpenAkashic method retrieval.
The same model selection (`gpt-6.1-sol`) and brief were assigned to separate
agents. Each authored one candidate per task without reading other conditions.
Original HTML hashes were frozen before evaluation, with no later repairs.

Six documented methods adapt the Anthropic frontend-design skill, GOV.UK
start/question/check-answer patterns, and W3C WAI form-label/error guidance.
They are original editorial summaries with linked sources, access dates and
limits, not successful real-world experiences. The skill is pinned to commit
`41bbe19d1a1a7eaab5e7bb9050a417e5c6cffc8f`, with its Apache-2.0 license retained
outside Git. GOV.UK software uses MIT; WAI is referenced as official guidance.
Full source texts, external images, fonts and downloaded code are not shipped.

The corpus now has 39 methods. Incremental indexing embedded 12 new fields and
reused 66 prior fields with unchanged model/spec/floors. The retrieval agent
formulated its own queries and fetched three exact versions per task. A CSV
method also appeared for the booking query and was rejected as irrelevant.
Similarity results remain candidates that require scope review.

All conditions passed the frozen seven exhibition and twelve workshop checks.
The parent exercised actual browser flows at 390 and 1440 CSS pixels: keyboard
disclosures, visit anchors, missing/email/count errors, three-person KRW84,000
total, review/edit preservation, mock completion and reload reset. Explicit
content/code inspection supplemented these flows. This is not full WCAG
conformance, a security certification or actual user success.

A separate model reviewed twelve anonymized desktop/mobile screenshots before
seeing the condition mapping. It retained ties: the retrieval exhibition made
the action/guide prominent, while the unaided editorial version had equally
strong craft. The retrieval workshop exposed time choices; the unaided version
tied on hierarchy/craft/readability. The direct-document mobile total placeholder
wrapped awkwardly; that weakness remains visible. These are model opinions,
not measured human preference or a causal condition effect.

The parent selected sources and wrote methods alongside the briefs. There are
only two synthetic tasks and one generation per condition. Prior model knowledge
and stochastic variation are confounds. Different input packages were not budget
matched. The direct pack has 66,960 unique reference-file bytes; retrieval
captured 41,789 successful API-response bytes including repeated search/fetch
content. Failed response bodies and some bookkeeping reads were not captured.
Actual provider tokens, total cost, user preference, rework and conversion are
unmeasured. Byte counts do not establish token or cost savings.

Two outcomes (one per applied task) and two linked alternative opinions were
published with authenticated idempotency and public readback. They are `partial`:
mechanics ran, but target-audience benefit is unknown. Each names its three
applied versions without counting them as independent executions. Server
provenance remains self-reported and not independently verified. Original artifact
hashes and the public comparison URL accompany the feedback.

Packaging only extracts inline style/scripts and converts inline style attributes
to equivalent classes for the existing CSP; original and packaged hashes remain.
Example routes use fixed allowlists and prohibit network/form submission. Only
the public synthetic examples permit same-origin framing; frames themselves use
`sandbox="allow-scripts allow-forms"` without same-origin permission. The form
permission allows local submit handlers; CSP still blocks actual form destinations.
Other routes retain
their original policy. The reviewed public report is one fixed runtime filename
beside the public archive; raw experiments and generated data stay outside Git.
The comparison responses use `no-store, no-transform` so the edge does not inject
analytics or rewrite synthetic email examples between the measured and public HTML.

Next evidence should separate reader preference and its reason from objective
information-finding/error-recovery tasks. Repeated independently chosen external
tasks with matched budgets are needed before claiming quality or efficiency
benefits. More attractive examples alone do not provide that evidence.
