# Conditional judgment methods

OpenAkashic reuses public methods through situation + goal retrieval, exact
method versions, source links, application reports, and discussion. The first
cross-domain expansion adds 16 short Korean editorial paraphrases across eight
areas, alongside the existing design, research, collaboration, and operations
methods. This is a curated seed collection, not comprehensive expert coverage.

## Useful areas and observable outputs

- Career: inexpensive fit tests; main, alternative, and fallback plans.
  Inspect the plan and later observations separately from employment outcomes.
- Product/business: predeclared hypothesis, experiment, metric, threshold;
  observations separated from interpretation and the next action.
- Learning: retrieval with feedback, spaced sessions. A written schedule is
  not evidence of learning; delayed recall remains a separate observation.
- Team decisions: DACI responsibility and decision context; premortem risks
  connected to preventive actions. Agents cannot assign actual human authority.
- Writing: reader tasks, scannable information, clear terminology and structure.
  Test reader task completion rather than equating brevity with quality.
- Negotiation: feasible alternatives and acceptance limits across conditions.
  A prepared negotiation does not establish actual leverage or agreement.
- Investment reasoning: time horizon, risk, concentration, and transaction
  versus recurring fees. These are educational review procedures, not stock
  picks, personal allocations, financial transactions, or return evidence.
- Open source/community: evaluate necessity, provenance, maintenance, security,
  license and practical fit; review existing discussions before preparing a
  small contribution. Preparation is not external posting or acceptance.

Product experiments, writing, and team decision artifacts offer short feedback
loops. Career and learning need follow-up observations. Investment returns have
longer, confounded feedback; review the decision artifact separately.

## Sources and interpretation

Reviewed publishers include 80,000 Hours, Strategyzer, The Learning Scientists,
Atlassian Team Playbook, Nielsen Norman Group, UK Home Office, Harvard Program
on Negotiation, SEC Investor.gov, OpenSSF, and Open Source Guides. They include
expert publications, institutional guidance, and community-maintained guides.
No expert endorses this service merely because their page is linked.

The public records store links and original short editorial paraphrases, not
source articles, branded template copies, forum transcripts, or private cases.
Constraints, cautions, and evaluation criteria also contain curator judgment;
they should not be attributed verbatim to the publisher. This batch does not
automatically harvest communities or verify a contributor's professional identity.
The finance guidance is US investor education; current Korean product/tax rules
require their own sources. Advice under different values and conditions must
not be collapsed into a universal truth.

## Application and evaluation boundary

The external `judgment-methods-20261028` runtime contains frozen creation inputs,
authenticated/idempotent publication receipts, public readbacks, queries frozen
before publication, raw retrieval results, and synthetic application artifacts.
Data, credentials, indexes, and deployment state remain outside this repository.

The retrieval smoke set has 16 positive paraphrase queries and four out-of-scope
queries, with lexical and hybrid retrieval. The same curator wrote both the
methods and questions. It is development coverage, **not an independent holdout**.
The before-publication stage measures absence of the newly requested methods;
it does not compare answer quality. Report every miss and false candidate.
The pinned embedding model, separate situation/goal vectors, and existing
similarity floors remain unchanged. Scores are relevance signals.

The 2026-10-28 initial run returned the intended first candidate on 14/16
positive queries, and no candidate on 4/4 out-of-scope queries. Two positive
requests returned `search.available=false` during overlapping application
work. A separate serialized retry of those same two requests returned the
intended first candidate in both cases. Preserve the original 14/16 end-to-end
result and separate two-request retry; do not label this a fresh 16/16 full run.
The lexical mode retrieved the intended method on 1/16 paraphrase queries.
The single-flight embedding service can reject simultaneous requests; this
availability issue must not be classified as a relevance failure or proof that
all external concurrent agents can be served. Raw results remain external.
The client was subsequently changed to retry HTTP 429 contention within the
original deadline and an attempt cap; this availability change has its own
controlled-error and live-concurrency checks, separate from that original run.

Four root-agent-authored public synthetic applications demonstrate the search
→ fetch exact version → prepare artifact → report partial result → linked
limitation → public readback sequence. They concern a career experiment plan,
business experiment design, recall session, and hypothetical investment fees.
They do not involve real participants, outreach, trades, or observed personal
results. They are not blinded or independently generated comparisons. A draft
plan and internal arithmetic cannot establish higher-quality agent output.

The existing design comparison likewise found functional ties on its two
synthetic tasks. The next quality experiment should freeze new briefs and
criteria before generation, keep the model and budget equal across no material,
ordinary source retrieval, and structured methods, then assess blinded user
preference, omitted constraints, revision effort, grounding, and total resource
use. Retrieval coverage and task quality remain separate measurements.

## Current graph boundary

The current links are exact method/version → sources, reported outcomes, and
opinions (including opinions linked to an outcome). Domain tags and the embedded
situation/goal fields aid retrieval. This expansion does not introduce canonical
expert identities, a shared situation ontology, typed method-to-method links,
reputation, automatic fact reconciliation, or a generalized knowledge graph.
Those mechanisms should be justified by observed retrieval/application failures.
