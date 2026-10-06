# Status

Current phase: IMPLEMENTATION  
Current milestone: M02 — resume parser and review-before-save
Last verified run: none (external supervisor required)

The current work block extends the private candidate PDF upload with bounded
CPU-only text extraction, structured field provenance/confidence, and an
explicit candidate review step. Parser output stays `needs_review` until the
candidate accepts or rejects it; accepted professional fields reuse the
candidate profile boundary and contacts are never imported.

Requirement status for this block: IMPLEMENTED pending supervisor evidence:
CAND-002. Existing assessment implementation remains recorded in the backlog
and matrix; AST-003 remains IN_PROGRESS until employer-visible category wiring
exists, and AST-005 remains IN_PROGRESS until synthetic calibration validation
exists.

Important open scope: standardized profile PDF and candidate dashboard, taxonomy
data/model and assessment UI/history, FSP evidence, ProofMatch,
invitations/match/chat, employer pipeline, load testing and complete responsive
journey remain unimplemented.
