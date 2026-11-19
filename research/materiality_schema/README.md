# Materiality Observation Schema (MOS v0.1) — DRAFT

Status: **draft v0.1.** This is an offered community instrument, not a result. It makes **no decipherment claims** and asserts nothing about what any khipu "means"; it is plumbing, offered to the field with no authorship or timeline attached.

## Why this exists

The OKR records the cord-structure channel (knots, values, positions) densely, and the materiality channel (fibre, spin, attachment, dye) sparsely: material descriptions exist for roughly 40% of khipus and a substantial fraction of "all-cotton" descriptions are contradicted under re-examination (Hyland 2026, personal communication; her SEM-identified camelid/deer admixture in a C14-dated Inka khipu is the strongest single demonstration that materiality may be primary-code data). Our own published analyses are deliberately **lower-bound claims over the recorded channel only** (see the main repo README and the Proof Loom provenance caveat), because the channel they do not record may be the one that matters.

The gap is not mainly scientific; it is infrastructural. Knot data got a relational database and KH numbers. Materiality data has, at best, free-text remarks. The purpose of MOS is to give materiality observations what knot data already has: a stable schema, per-record provenance, and hash-pinned source media, so that a lab can publish a materiality dataset the way the OKR published knot data.

## Design principles

1. **Observation, not interpretation.** A MOS record binds a measurement, an observer, a method, and a date. Cultural or functional interpretation is out of scope by construction.
2. **Per-record provenance, who-identified-what.** Every record names its observer, method, and instrument. "Who identified what" is a first-class field because material re-identification (e.g. all-cotton corrections) is exactly where the historical record went wrong.
3. **Disagreement is recorded, never averaged.** Multiple observers may record conflicting observations about the same cord. All are kept with their provenance; reconciliation is a separate, explicit step. This is the same doctrine our transcriber-divergence machinery applies to knot readings.
4. **Fail-closed ingestion.** Every source artifact (photograph, SEM image, lab report) is recorded with SHA-256 and license-checked at ingest; missing required fields make the record invalid, not silently partial.
5. **Complements the OKR, does not fork it.** Records reference KH numbers where assigned and may use cord identifiers compatible with the OKR tables; provisional identifiers are allowed for unregistered khipus.

## Record model (summary)

See `materiality.schema.json` (JSON Schema 2020-12) for the normative form, and `examples/` for illustrative records (fictional data, clearly marked).

| Field group | Contents |
|---|---|
| `record_id`, `khipu_id`, `cord_id` | Stable identifiers; KH number when assigned, provisional IDs allowed |
| `observation_class` | FIBRE, DYE, ATTACH, SPIN, DIAMETER, MICROSAMPLING, RADIOCARBON, OTHER |
| `observed_value` | Typed payload per class, controlled vocabularies where possible |
| `method`, `destructive` | visual, hand-lens, optical microscopy, SEM, FTIR, radiocarbon; whether the sample was consumed |
| `provenance` | observer identity (ORCID when available), institution, identification confidence, pointers to records this observation disagrees with |
| `source_media[]` | per-artifact SHA-256, license, capture date, custodian |
| `recorded_at`, `conditions` | Timestamps and environmental/conservation caveats |

## Adoption stance

- Offered under MIT, same as this repository.
- No claims about khipu decipherment, past or future. Nothing in MOS encodes or presumes a semantic theory of khipus.
- Designed against real field practice, with destructive-method flagging and museum-conservation constraints in mind (the British Museum / village conservation context is a motivating case).
- v0.1 is a draft for community comment. Field researchers who would never adopt a spec written for them are invited to break it first.

## Credit and contact

Motivated by Sabine Hyland's materiality critique (personal communication, Nov 2026) and by the Open Khipu Repository's open-data practice. Schema authors: SZL Holdings estate (AI-authored instrument, owner-signed merges), offered with no authorship ask to any user of the schema.
