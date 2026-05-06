# Case: pv-l3-user-noise

## Mode
scenarios

## Prompt
输入至少 20 条噪声提示词（错别字、半句、省略指代、冲突指令、跨主题跳转），覆盖 shared 澄清和重路由。

## Expected Contract
- noise_cases_gte: 20
- required_fields:
  - summary
  - next_step
- thresholds:
  - minimal_clarification
  - reroute_recovery
  - no_empty_loops

## Evidence Refs
- conversation: <run_id>/turn:1..N
- state: <run_id>/state-snapshot#l3
