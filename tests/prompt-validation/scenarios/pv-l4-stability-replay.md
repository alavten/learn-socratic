# Case: pv-l4-stability-replay

## Mode
scenarios

## Prompt
同一提示词套件完整回放 5 次，比较每次通过项、失败项、方法论命中率与波动。

## Expected Contract
- replay_times: 5
- required_fields:
  - summary
  - next_step
- thresholds:
  - hard_checks_100_percent
  - methodology_variance_lte_10_percent
  - no_new_high_priority_regression

## Evidence Refs
- conversation: <run_id>/turn:1..N
- state: <run_id>/state-snapshot#l4
