# Case: pv-l2-large-scale

## Mode
scenarios

## Prompt
先 ingest 全量图谱（A 档 200+/800+ 或 B 档 500+/2000+），随后执行 >=30 轮混合学习会话，跨 5+ 主题切换，并至少 2 次增量补录。

## Expected Contract
- scale_tier: A_or_B
- required_fields:
  - summary
  - next_step
- thresholds:
  - flow_stable
  - key_fields_present
  - methodology_drift_lte_10_percent

## Evidence Refs
- conversation: <run_id>/turn:1..N
- state: <run_id>/state-snapshot#l2
