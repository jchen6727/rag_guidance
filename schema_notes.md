# Discovery Engine Schema Instructions

> **Sources (Google Cloud, verified 2026-07-12):**
> - [Configure field settings](https://docs.cloud.google.com/generative-ai-app-builder/docs/configure-field-settings)
> - [Provide or auto-detect a schema](https://docs.cloud.google.com/generative-ai-app-builder/docs/provide-schema)
>
> **Correction (2026-07-12):** the "Strict Array Constraint" section below previously stated that indexing flags must sit at the property level and never inside `items` for array fields. That was **inverted** — Google's documentation places the flags **inside `items`** for arrays of primitives. See the corrected section and `architecture_bootstrap.md` §0.

## Property-Level Discovery Engine Annotations

Discovery Engine flags field behavior using specific, boolean properties placed *directly* inside the parent property object block.

### Valid Field Flags:
* `"retrievable"`: (boolean) Controls if the field value is returned in search query payloads.
* `"indexable"`: (boolean) Controls if the field can be filtered, sorted, or leveraged as a facet.
* `"searchable"`: (boolean) Controls if the field text is indexed for unstructured natural language keyword search. Only valid for `"type": "string"` or arrays of strings.
* `"dynamicFacetable"`: (boolean) Enables automated structural faceting.

### Array Field Placement (arrays of primitives):
For an array of primitives (e.g. `array` of `string`), the indexing flags
(`retrievable`, `indexable`, `searchable`, `dynamicFacetable`, and
`keyPropertyMapping`) reside **inside the nested `"items"` block**, alongside the
element `"type"` — **not** at the property level. This is the placement Google
documents and that makes each array element value individually filterable /
searchable. See the [`amenities` example in *Configure field settings*](https://docs.cloud.google.com/generative-ai-app-builder/docs/configure-field-settings)
and the [`categories` / `keyPropertyMapping` example in *Provide or auto-detect a schema*](https://docs.cloud.google.com/generative-ai-app-builder/docs/provide-schema).

> **Do not** move these flags to the property level for arrays of primitives — that leaves the field unregistered as filterable and silently breaks any `ANY(...)` filter over it. (An earlier version of this note had this backwards.)

*Correct Array Pattern Example:*
```json
"example_tags": {
  "type": "array",
  "items": {
    "type": "string",
    "retrievable": true,
    "indexable": true,
    "searchable": true
  }
}
```

*As documented by Google (`Configure field settings`), all element-level flags — including `completable` and `dynamicFacetable` — live inside `items`:*
```json
"amenities": {
  "type": "array",
  "items": {
    "type": "string",
    "completable": true,
    "dynamicFacetable": true,
    "indexable": true,
    "retrievable": true,
    "searchable": true
  }
}
```

Note this is consistent with the "Document Hierarchy Structuring" section below:
flags always attach to the **leaf** element inside `items` (or inside a nested
object's `properties`), never to the array/object container itself.

## Custom Vector Search Embeddings (Hybrid/Vector Search)

To index pre-computed custom embeddings for vector or hybrid search, the property configuration must follow exact formatting guidelines.

1. **Data Type**: Custom vector fields must be configured as an array of numbers (`"type": "array"` with `"items": { "type": "number" }`).
2. **Dimension Annotation**: The property block must include a top-level `"dimension"` integer explicitly stating the size of the vector space (e.g., `768`, `1536`, `3072`).
3. **Property Flag Elimination**: Do NOT add `"searchable": true` to a vector embedding array field. In Discovery Engine, keyword search configuration (`searchable`) is strictly reserved for text fields.

*Correct Custom Vector Pattern Example:*
```json
"page_embedding": {
  "type": "array",
  "items": {
    "type": "number"
  },
  "dimension": 768,
  "retrievable": false,
  "indexable": true
}
```

## Document Hierarchy Structuring (Nested Objects)

Discovery Engine allows you to pass nested child structures (e.g., paragraphs within articles, comments under posts, or hierarchical object trees) using standard JSON schema object nesting.

1. **Explicit Object Declaration**: Deep hierarchies must use `"type": "object"` or an array of objects (`"type": "array"`, `"items": { "type": "object" }`).
2. **Downstream Custom Property Flags**: Nested primitive elements within a child object block *can* independently receive `"retrievable"`, `"indexable"`, and `"searchable"` flags.
3. **No Flag Leaks to Parent**: Do NOT add search property flags (`searchable`, `indexable`) to the structural container field itself (the parent object or parent array wrapper). Only apply them to the final leaf properties inside the child block.

*Correct Hierarchical Structure Example:*
```json
"session_segments": {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "segment_id": {
        "type": "string",
        "retrievable": true,
        "indexable": true
      },
      "transcript_chunk": {
        "type": "string",
        "retrievable": true,
        "searchable": true
      }
    },
    "required": ["segment_id", "transcript_chunk"]
  }
}
```

## System Key Requirements
Ensure your schemas supply standard target fields when matching common vertical use cases:
* **Enterprise Text Search**: Highly favors root fields named `title`, `uri`, `description`, and `categories`.
* **Required Properties**: Explicitly register mandatory primary keys inside the top-level `"required": []` array block.

## Output Directive
When instructed to create, alter, or optimize a schema under these rules:
1. Validate that no forbidden union configurations are written.
2. Ensure array structural field settings, vector dimensions, and nested hierarchy properties match the explicit block placement criteria detailed above.
3. Output exclusively clean, valid, un-truncated raw JSON code inside standard markdown code blocks.