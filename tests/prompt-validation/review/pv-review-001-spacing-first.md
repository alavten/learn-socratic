# Case: pv-review-001-spacing-first

## Mode
review

## Prompt
1. 现在做复习，请优先安排我最容易忘的内容。  
2. 这题我不确定，但我猜是 XXX。  
3. 请告诉我下一次复习这三个章节的顺序。

## Expected Contract
- mode: review
- required_fields:
  - summary
  - next_step
- methodology_hits:
  - spacing_first

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#review-priority
