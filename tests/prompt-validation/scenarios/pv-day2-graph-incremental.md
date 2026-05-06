# Case: pv-day2-graph-incremental

## Mode
scenarios

## Prompt
1. 第2天：昨天我发现“质量属性与架构策略”的关系不清楚，请补充到图谱再继续。  
2. 补充后先讲解这个新增关系，再让我用自己的话解释。  
3. 讲完后直接测一题应用题。

## Expected Contract
- required_fields:
  - summary
  - next_step
- path:
  - incremental_ingest_to_learn_to_quiz

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#day2
