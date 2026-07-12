# Discovery Engine Schema Instructions

## Property-Level Discovery Engine Annotations

Discovery Engine flags field behavior using specific, boolean properties placed *directly* inside the parent property object block.

### Valid Field Flags:
* `"retrievable"`: (boolean) Controls if the field value is returned in search query payloads.
* `"indexable"`: (boolean) Controls if the field can be filtered, sorted, or leveraged as a facet.
* `"searchable"`: (boolean) Controls if the field text is indexed for unstructured natural language keyword search. Only valid for `"type": "string"` or arrays of strings.
* `"dynamicFacetable"`: (boolean) Enables automated structural faceting.

### Strict Array Constraint:
* **CRITICAL ERROR TO AVOID**: Never place `retrievable`, `indexable`, or `searchable` inside the nested `"items"` configuration block of an array type property.
* **CORRECT LOCATION**: Array field flags must reside at the property level alongside the `"type": "array"` declaration.

*Correct Array Pattern Example:*
```json
"example_tags": {
  "type": "array",
  "items": {
    "type": "string"
  },
  "retrievable": true,
  "indexable": true,
  "searchable": true
}
```

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