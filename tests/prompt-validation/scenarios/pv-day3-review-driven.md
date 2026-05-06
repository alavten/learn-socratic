# Case: pv-day3-review-driven

## Mode
scenarios

## Prompt
1. 第3天：请按最容易忘到最不容易忘安排我复习，覆盖前三天涉及的关键点。  
2. 我先给每题一个把握度百分比，你再看我答得对不对。  
3. 最后给我明天的复习计划，并说明先后顺序原因。

## Expected Contract
- required_fields:
  - summary
  - next_step
- methodology_hits:
  - spacing_first
  - metacognitive

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#day3
