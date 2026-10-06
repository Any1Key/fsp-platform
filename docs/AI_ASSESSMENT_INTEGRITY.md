# Assessment integrity and anti-AI design

## Goal

Protect comparability and make answer-sharing/outsourcing unattractive without pretending that automated “AI detection” can prove cheating.

## Threat model

- candidate receives leaked fixed questions/answer keys;
- two candidates collaborate and exchange answers;
- candidate copies the prompt into a generative AI system;
- candidate submits generated code/text without understanding it;
- candidate retries until memorizing a small bank;
- a public answer repository appears after the hackathon.

## Controls

### 1. Per-attempt unique form

Each attempt is assembled from a competency blueprint and template families. A secure server-side seed selects parameters, datasets, code fragments, values and ordering. Persist the exact generated form for reproducibility.

Two candidates can be tested on the same competency and difficulty while seeing different concrete instances.

### 2. Exposure control

For every item family track:
- exposure count;
- last exposure time;
- current version;
- retirement state;
- leak-risk flag.

Assembly avoids overexposed/recently seen families. An admin/demo control can retire a family without deleting historic attempts.

### 3. Calibrated anchors

Hidden anchor items connect different forms to the same scale. Anchors must have multiple equivalent surface variants so the anchor itself does not become a fixed leaked question.

### 4. Progressive verification

For selected tasks the candidate first submits an answer and then receives a short follow-up derived from the submitted state, for example:
- “Now latency is limited to X; what changes?”
- “Which invariant does your solution rely on?”
- “The index disappeared; diagnose the new bottleneck.”

The follow-up is scored with a small deterministic rubric. This tests understanding rather than prose style.

### 5. Session-specific artifacts

Code/debugging tasks may include a unique schema, dataset, function signature, failing test fixture or configuration generated for the attempt. Hidden tests validate behavior.

### 6. Integrity telemetry — advisory only

With explicit disclosure/consent, collect minimal events such as:
- unusually large paste into an answer field;
- repeated focus loss;
- implausibly short task duration;
- repeated reconnect/reset anomalies;
- high normalized similarity to another submission.

These create review flags. They never automatically fail a candidate or change a grade.

Do not use webcam surveillance, keystroke biometrics or covert fingerprinting for the MVP.

## Similarity analysis

For code:
- strip formatting/comments;
- normalize identifiers where appropriate;
- compare token/AST fingerprints;
- compare solution structure.

For text:
- normalize boilerplate;
- compare semantic/lexical similarity only as a weak signal.

A high similarity result creates a review flag with evidence; it is not proof of misconduct.

## AI use policy

The platform can support two explicit modes in the future:
- **verified baseline**: external AI use is prohibited by assessment rules and the above resistance controls are applied;
- **AI-assisted work simulation**: AI is allowed and the candidate is assessed on verification, correction and explanation of AI output.

For the hackathon, the verified baseline is the primary grade assessment.

## Candidate feedback

Show score, domain breakdown and grade decision. Do not immediately expose reusable answer keys/templates. Detailed canonical solutions are delayed until the item family/version is retired or a configured exposure window closes.

## Validation

Create synthetic/mocked behaviors for:
- legitimate strong/weak candidates;
- copied answer pair;
- large-paste/focus-change session;
- fast but correct attempt;
- inconsistent anchor performance.

Verify that integrity signals are produced without changing the deterministic grade unless an explicit human-reviewed policy says otherwise.
