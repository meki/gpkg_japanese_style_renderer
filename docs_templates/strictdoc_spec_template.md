# StrictDoc Documentation Template

First level heading `#` must be used once per document.

## Second level heading

Second level heading `##` is usually used for major sections of the document.
And third level heading `###` must be used for specificification (requirements, specifications, design items, or other specific items) within the document. It should not include numbering since Specification IDs or Design Item IDs should be used for that purpose.

### [Short Title]

**UID**: RQ-02-05 \
**STATUS**: Active \
**RELATIONS**:
- **Type**: Parent
  **ID**: RQ-02-01
- **Type**: Parent
  **ID**: SP-02-01

The statement / body of the node goes here (StrictDoc treats free prose after
the metadata as the STATEMENT).

Notes on the StrictDoc 0.24 `RELATIONS` format:

- `**RELATIONS**:` must have an empty inline value (no comma-separated UIDs).
- It must directly follow the metadata with no blank line before it.
- The first `- **Type**:` bullet must follow on the very next line (no blank line
  between `**RELATIONS**:` and the first bullet).
- Each relation is a dict: `- **Type**: Parent` then `  **ID**: <UID>` (indented
  continuation line). `Type` is one of `Parent` / `Child` / `File`.
- A blank line separates the last relation bullet from the STATEMENT prose.
- A node without parents (e.g. a top-level `RQ-`) simply omits the `RELATIONS`
  field entirely.

