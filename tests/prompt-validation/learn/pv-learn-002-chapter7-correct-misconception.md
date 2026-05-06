# Case: pv-learn-002-chapter7-correct-misconception

## Mode
learn

## Prompt
1. 继续学软件工程章节，重点讲需求、设计、测试之间的关系。  
2. 我理解是：只要测试做得好，需求阶段可以弱一点。  
3. 请指出我这个理解哪里错，并让我再复述一次。

## Expected Contract
- mode: learn
- required_fields:
  - summary
  - next_step
- behavior:
  - clear_misconception_feedback
  - single_concept_focus

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#learn-chapter7
