# Prompt Validation Suite (Real Prompt Sessions)

## Purpose

Use real prompt sessions against `SKILL.md` + `modes/*.md` to validate the full loop:
`ingest -> learn -> quiz -> review` (including `shared` reroute).

## Baseline

- Knowledge source: `tests/assert/SoftwareEngineering` chapter materials.
- Methodology baseline: `docs/architecture-design.md` section 1.4.
- Validate routing contract (`mode/summary/next_step`) and methodology behavior.

## Execution Principles

- Validate **runtime behavior**, not test implementation details.
- Use real user prompts; do not replace with unit-test-only assertions.
- Scripts are allowed for **analysis/reporting only**, not scripted case execution.
- Every conclusion must map to conversation evidence and/or runtime state evidence.

## Cadence

- Run after every change to `SKILL.md` or `modes/*.md`.
- Weekly full regression.
- Mandatory full run before release.

## Pass Criteria

- Cover at least three docs (recommended: Chapter4/7/12) through learn+quiz+review.
- Total turns >= 20 (enhanced scenarios >= 60).
- Cross-day coverage >= 3 days (enhanced scenarios >= 14 days).
- Methodology hits:
  - learn: Feynman + UBD
  - quiz: retrieval-first + SOLO progression
  - review: spacing-first
  - cross-day: metacognitive calibration
- At least one successful loop:
  `learning_gap -> incremental_ingest -> relearn/requiz`.

## Run Rules

- Load full SoftwareEngineering chapter context.
- Keep balanced mode usage in larger runs.
- At least two mode switches per day in multi-day scenarios.
- Trigger at least one explicit incremental-ingest feedback loop.

## Evidence Template

For each run, produce:

- run metadata (`run_id`, `graph_id`, `plan_id`, timestamp, operator)
- prompt trace per turn
- contract snapshot per turn (`mode/summary/next_step`)
- methodology evidence map
- shared reroute evidence
- daily mode switch counts
- graph version progression
- delta vs previous run

## Verdict

- **Pass**: all hard thresholds satisfied, no blocking failures.
- **Conditional Pass**: hard thresholds met with minor regressions.
- **Fail**: any hard threshold missed.

## Output Artifacts

Runtime outputs are not tracked in git. Write reports to:

- `data/prompt-validation-runs/<run_id>/report.md`
- `data/prompt-validation-runs/<run_id>/report.json`

## Attestation

Every report must include:

`本次验收基于 SKILL.md 真实提示词会话执行，未使用单元测试代码或测试函数替代真实交互。所有结论均由对话证据与生产状态证据共同支持。`
