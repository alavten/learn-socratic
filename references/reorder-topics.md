# Reorder Topics Mode Contract

## Trigger Conditions

- User asks to fix chapter order, reorder sections, or navigation feels wrong after ingest.
- Large-document ingest finished but `get-knowledge-graph` topic order does not match the book TOC.

Required context: `graph_id`, `payload` JSON for `reorder-graph-topics` (see below).

## Runtime Execution Chain

1. Preflight (once per session): `get-api-spec --api-name reorder-graph-topics`.
2. `get-knowledge-graph --graph-id <id>` (and `--topic-id` when inspecting one subtree).
3. Agent supplies topic list to the LLM (titles, `topic_id`, `topic_type`, optional source TOC). LLM returns the **complete** ordered `topic_ids` for one sibling group.
4. `reorder-graph-topics --graph-id <id> --payload-file <path>`.
5. Check `validation_summary.ok`; on success, optionally re-fetch graph to confirm order.

## Payload Shape

Inner payload only (CLI adds `graph_id` via flag):

```json
{
  "parent_topic_id": null,
  "topic_ids": ["intro-ch1", "intro-ch2", "m01"]
}
```

- `parent_topic_id`: `null` for root-level chapters; string for sections under that parent.
- Provide **either** `topic_ids` (order = array sequence, assigned sort_order 1..N) **or** `topic_order` with explicit `{ "topic_id", "sort_order" }` per row.
- **Full sibling set required**: every topic under that parent in the DB must appear exactly once. Partial lists are rejected.

## Per-Parent Groups

Root chapters and each parent's children are **separate** reorder calls. Do not assume one call reorders the entire tree.

Example: reorder all root `chapter` nodes with `parent_topic_id: null`, then reorder each chapter's `section` children with `parent_topic_id` set to that chapter's `topic_id`.

## AI Execution Directives

- Do not add book-order JSON or manifest files to the skill repository.
- Do not guess missing `topic_id`s; if the LLM output count mismatches `get-knowledge-graph`, fix the list before calling reorder.
- Prefer `topic_ids` when the model outputs a simple ordered list; use `topic_order` only when explicit gaps or renumbering is needed.
- After reorder, report `topics_updated` and the first entries from `topics_preview`.

## Turn Contract

- One reorder attempt per parent group per turn.
- Return `validation_summary` errors verbatim (top 5) when `ok` is false.

## Mode Exit Rule

- Stay in this flow until `validation_summary.ok` is true for each parent group that needs fixing.
- Then hand off to `learn` / `quiz` / `review` or back to `ingest` if content is still missing.

## Output

- `graph_id`, `parent_topic_id`, `topics_updated`, `validation_summary`, `topics_preview`
- `next_step`: confirm with user or continue to next parent group / learning mode

## Retry / Fallback

- `missing topic_id(s)`: add omitted ids from `get-knowledge-graph`.
- `unknown topic_id(s)`: remove ids not in DB or fix typos.
- `duplicate` in `topic_ids`: dedupe while preserving intended order.

## Next Hop

- `learn` when the user wants to study with the corrected order.
- `ingest` when chapters are still missing from the graph.
