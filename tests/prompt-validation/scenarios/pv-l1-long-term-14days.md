# Case: pv-l1-long-term-14days

## Mode
scenarios

## Prompt
14 天连续执行真实会话；每天 5-10 轮，每天至少一次 learn->quiz 或 quiz->review 切换，并每 3-5 轮触发一次元认知校准。

## Expected Contract
- duration_days: 14
- required_fields:
  - summary
  - next_step
- thresholds:
  - no_dead_routing
  - methodology_hit_rate_gte_90

## Evidence Refs
- conversation: <run_id>/turn:1..N
- state: <run_id>/state-snapshot#l1
