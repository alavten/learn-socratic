# Case: pv-quiz-001-cross-chapter-retrieval

## Mode
quiz

## Prompt
1. 基于刚才三个章节，开始测验我。一次一题。  
2. 我这题答案是 XXX（故意给一个不完整答案）。  
3. 再来一题更难的。

## Expected Contract
- mode: quiz
- required_fields:
  - summary
  - next_step
- methodology_hits:
  - retrieval_first
  - SOLO_progression

## Evidence Refs
- conversation: <run_id>/turn:1..3
- state: <run_id>/state-snapshot#quiz-cross-doc
