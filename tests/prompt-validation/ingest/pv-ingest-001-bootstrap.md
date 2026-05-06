# Case: pv-ingest-001-bootstrap

## Mode
ingest

## Prompt
1. 我会上传软件工程备考资料，请先帮我导入并建立知识图谱。  
2. 如果资料有格式问题，请按字段告诉我怎么修。

## Expected Contract
- mode: ingest
- required_fields:
  - summary
  - next_step
- status: success_or_needs_fix

## Evidence Refs
- conversation: <run_id>/turn:1..2
- state: <run_id>/state-snapshot#ingest
