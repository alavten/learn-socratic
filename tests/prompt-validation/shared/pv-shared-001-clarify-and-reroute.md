# Case: pv-shared-001-clarify-and-reroute

## Mode
shared

## Prompt
1. 继续。  
2. 换成测试模式。  
3. 我其实想先回去补一下讲解。

## Expected Contract
- mode: shared
- required_fields:
  - summary
  - next_step
- behavior:
  - clarification_then_reroute

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#shared-reroute
