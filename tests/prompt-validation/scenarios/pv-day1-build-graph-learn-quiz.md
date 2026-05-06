# Case: pv-day1-build-graph-learn-quiz

## Mode
scenarios

## Prompt
1. 今天是第1天，请先导入这三章资料，然后带我学 Chapter4。  
2. 先讲一个核心概念，我复述后你纠正我。  
3. 现在切到测验模式，按由浅到深出一题。

## Expected Contract
- required_fields:
  - summary
  - next_step
- path:
  - ingest_to_learn_to_quiz

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#day1
