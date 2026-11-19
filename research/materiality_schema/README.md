# Materiality Observation Schema (MOS v0.2) — DRAFT

MOS is a draft format for sharing material observations of khipu cords. It is not an archaeological result or a claim of decipherment, and it implies no endorsement by the cited institutions or researchers.

## Why this exists

The [Open Khipu Repository (OKR)](https://doi.org/10.5281/zenodo.18025748) provides open data and metadata for extant Inka-style khipus. Material observations also appear in other public records: a [Dallas Museum of Art catalogue record](https://dma.org/art/collection/object/5328374) lists fibre categories, and [published conservation work](https://faculty.up.edu.pe/en/publications/documentation-as-conservation-the-treatment-of-an-archaeological-/) documents how an object was examined and recorded. These sources motivate a way to preserve observations and their methods across catalogues and studies. They do not establish corpus-wide completeness, how frequently identifications change, or what a material feature meant.

MOS complements OKR by supplying a record format for material observations (such as fibre, dye, spin and diameter) with per-record provenance, explicit timing and source media references where those are available and permissible to share.

## Design principles

1. **Observation, not interpretation.** Record what an observer identified, the method used, and when the observation occurred if known. Cultural or functional interpretations are outside this schema.
2. **Trace each identification.** Record an observer and method for each identification. Record an instrument where known and disclose observer details only where appropriate for publication.
3. **Keep disagreement visible.** Retain conflicting observations as separate records; an optional reference links them without resolving or averaging them.
4. **Check sources and rights.** Include a SHA-256 digest and provenance for each attached source-media item. A valid JSON record is not proof of identity, permission, accuracy or successful ingest. Rights to publish any media and metadata must be checked separately; do not include private communications or unpublished source details without permission.
5. **Complement OKR.** Use a KH identifier where one exists; a provisional identifier is permitted for an unregistered object.

## Record model

See [the JSON Schema](materiality.schema.json) (Draft 2020-12) and [fictional examples](examples/mos-example.json). The example wrapper is not a MOS record; validate each element of its `records` array separately, with format checking enabled.

| Field group | Contents |
|---|---|
| `record_id`, `khipu_id`, `cord_id` | Record and object identifiers; KH number when assigned |
| `observation_class`, `observed_value` | Observation category and value |
| `method` | Technique and whether it consumed the sample; optional instrument and protocol reference |
| `provenance` | Observer, reported identification and confidence; optional conflict links |
| `source_media[]` | Optional media references with digest, license, capture date and custodian |
| `observed_at` | When the examination or measurement occurred: a date, an offset-bearing RFC 3339 date-time, or explicit `null` when unknown |
| `recorded_at` | Optional offset-bearing RFC 3339 date-time when the MOS record was entered |
| `conditions` | Optional environment, conservation or handling caveats |

New records use `schema_version: "mos/0.2"` and must include `observed_at`. Use a date if only the day is known; don't invent a time or a date. A catalogue, media capture, transcription or ingest date must not be substituted for an unknown observation date. Set `observed_at` to `null` and supply `recorded_at` only if the entry time is known.

Existing `mos/0.1` records still validate without `observed_at`. To migrate, change the version to `mos/0.2` and use independently supported observation timing or `null`. If the meaning of a legacy `recorded_at` is not established, preserve the original record and omit the ambiguous date from the migrated field; do not reinterpret it as observation timing.

## Validation

With `jsonschema[format]` installed:

```sh
python -m unittest discover -s research/materiality_schema/tests -v
```

## Adoption

The MOS draft is offered under MIT for community feedback. Destructive-method flagging documents a procedure; it does not authorize sampling or publication. Cite public sources and follow relevant collection, conservation and community permissions.
