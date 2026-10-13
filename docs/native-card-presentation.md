# Native card presentation

## Preserved contract

This change adds the approved SZL Orbit identity to nine existing artifact-card
sources. It changes presentation only. Every YAML frontmatter byte, technical
body, receipt reference, array schema, historical review statement, advisory
boundary, and publication hold remains unchanged.

The five `hf/` cards keep their existing artifact/stage summaries, visible
limits, and technical disclosure. Their old 112-pixel image from a moving URL
is replaced by the exact native 48-pixel icon. Navigation distinguishes the
Command Lab, canonical source, and reviewed evidence. Four reference cards
gain the same compact identity after their existing SOFTWARE / REFERENCE /
TEST FIXTURE lead; that lead remains the first visible text. The original
reference-card prose stays in place, including licensing and ownership limits.

The artwork is pinned to
[`szl-brand@27d12e77fc0f9f1a0e5fae8b34adf2380d51d070`](https://github.com/szl-holdings/szl-brand/blob/27d12e77fc0f9f1a0e5fae8b34adf2380d51d070/kit/logos/orbit-v2/suite/szl-icon-32.svg).
Its public URL was read back on 2026-10-11: 2,969 bytes, SHA-256
`6e2b7d72a3af3d9602b79de41df0194ede6496a9661f057108ec224c0efc92e6`.
The footer attributes that artwork under CC BY 4.0. It does not grant new
rights in the model artifacts. Cards use ordinary Markdown and an image;
they add no custom CSS, scripts, executable loaders, or model metadata.

## Source and writer scope

| Artifact | Card-authoring path | Established writer and remaining boundary |
| --- | --- | --- |
| Moons-Nano | `hf/Moons-Nano/README.md` | `publish-hf.yml` / `scripts/publish_hf.py`, fixed nano loop |
| MiniEmbed-Nano | `hf/MiniEmbed-Nano/README.md` | Same fixed nano loop; the 64 × 12 fixture stays distinct from the separate SVD artifact |
| TinyKhipu-Nano | `hf/TinyKhipu-Nano/README.md` | Current served source matches Khipu; a separate Forge card profile also targets this ID |
| ReceiptAgent-Nano | `hf/ReceiptAgent-Nano/README.md` | Current served source matches Khipu; a separate Forge card profile also targets this ID |
| szl-khipu-kernels | `hf/szl-khipu-kernels/README.md` | Card-only `_put` to the **model-type** repository; no native-kernel build or package-parity claim |
| chakana | `atelier/hf/chakana.md` | Existing `scripts/publish_reference_card.py`; exact current-main source, reviewed Hub parent and README digest required |
| qantu | `atelier/hf/qantu.md` | Same existing four-target card-only publisher |
| tinku | `atelier/hf/tinku.md` | Same existing four-target card-only publisher |
| waman | `atelier/hf/waman.md` | Same existing four-target card-only publisher; all artifact and intended-organ limits remain |

The four nano cards have exact document copies in both `atelier/hf/` and
`atelier-space/cards/`. The four reference cards have exact paired copies in
`atelier-space/cards/`. This accounts for **21 changed card files** and **12
copy relationships**. Other Atelier documents, differently scoped kernel
copies, the root README, runtime frontends, artifacts, training receipts,
publisher scripts, and workflows are not part of this change.

### Observed publication before this change

The accepted source baseline is
[`991889a248b8c633fa758e34a4e01f5937294524`](https://github.com/szl-holdings/szl-khipu/tree/991889a248b8c633fa758e34a4e01f5937294524).
The existing
[`publish-hf` run 38130586773](https://github.com/szl-holdings/szl-khipu/actions/runs/38130586773)
passed on that source. Job `114443897599` records uploads of all four nano
cards and the model-type kernels card at 10:03:47–10:03:49 UTC. Independent
immutable README reads at 10:36–10:37 UTC matched those five accepted source
cards exactly:

| Model-type Hub ID | Observed immutable revision |
| --- | --- |
| Moons-Nano | `4186a5233d07d5ce9bdefef0da1a2cbcff153da8` |
| MiniEmbed-Nano | `2a5992c4db8a2dc177891247211aff6cc3d524e6` |
| TinyKhipu-Nano | `ec01cfdfc449e6ac4fa1deb67521215a9c353d78` |
| ReceiptAgent-Nano | `19a384c9d15d6c07c4120898d4c6819e265d244f` |
| szl-khipu-kernels | `6abf9917281f388c530e43e8f3314547399bba25` |

These observations establish the old card delivery only. They do not verify
training, archive contents, native-kernel release qualification, or the new
presentation's publication. The model-software and Space receipts produced
by that run cover separate scopes and are not substituted for card readback.

The Forge closed card registry also includes TinyKhipu-Nano and
ReceiptAgent-Nano, with different source README bytes. The current Hub cards
match Khipu's accepted source, not those alternate Forge documents. This
change preserves both existing writer configurations and every current
technical byte; it does not resolve or expand their overlapping authority.
Any later Forge publication must be reviewed against that overlap before
overwriting the currently served Khipu bodies.

The four reference targets were absent from the observed 48-entry public
model catalog, and the 2026-10-11 public metadata/card requests returned HTTP
401. Visibility and a current parent could not be qualified. Their source
presentation is prepared; their explicit card-only publication remains held.
The current-main, paired-copy, metadata, parent-CAS, exact-client, and immutable
readback controls in `publish_reference_card.py` remain unchanged.

## Verification

The invariants were captured before editing. All **311 tracked files outside
the 21 card paths** remained byte-identical to the accepted baseline. Every
frontmatter hash and protected technical-body hash matched; all required
copies remained byte-identical. For the four reference cards, removing only
the two marked presentation additions reconstructs the entire old body.

| Canonical body | Preserved SHA-256 |
| --- | --- |
| Moons-Nano technical region | `194455993f990d243b12312e529a83460a46b430c8dce9374a791e1d22dc9913` |
| MiniEmbed-Nano technical region | `7b20e64291e0bbfdb39cd7cfa8801c336b83f04dddf702c2e825d923853ab075` |
| TinyKhipu-Nano technical region | `688795d4ae0d2bb9ed6081fe4d432c7eeaeef8bdbd84f19895b31570304ea2be` |
| ReceiptAgent-Nano technical region | `0209deaa30ef2ebddf48bb711cb1b97b7f27851cc99d9c4abc06fb7b9b1ffbfd` |
| Model-type Khipu kernels technical region | `dfe89644c4f1d55450d0b3f3575de4c8ab546004e58d83f9e4dc2bd7ed8b407d` |
| chakana original body | `997e6c5220b5dad480a7864b48eeb0f63431684252d488904ffcd389ad209015` |
| qantu original body | `c4a4e4b924e4557baf0407e583af2aec82178f57f85ee557030b01c22f85527a` |
| tinku original body | `6af6ecee6dba311a8926a85940260f700c4e1940550cc65be535adaf7a85efb6` |
| waman original body | `26bdf54a6125a9d7f6d681d663c500a210a90d68b92aaf99f4dd1235c31e75fc` |

All **43 existing metadata, honesty, reference-publisher, and model-software
tests passed**, with provider transports denied and zero unmocked transport
attempts. The reference-publisher
test uses its reviewed Hub client version 1.29.0 and mocked provider methods;
it validates operation/parent semantics without contacting the Hub.

A local CommonMark preview using `markdown-it-py==3.0.0` passed **37 checks**:
nine cards at 320 and 1280 pixels in light and dark presentation, exact 48-pixel
artwork, document overflow, native technical-disclosure keyboard behavior,
and zero page errors, external requests, or attempted writes. Representative
desktop/mobile renders were visually inspected. Preview styles approximate a
document host; this is not a claim that the Hugging Face renderer or live
model page was browser-qualified.

Normal source review and repository gates precede publication. Existing
writers must supply new exact-source and immutable card readbacks after
acceptance. This source-only change neither replays training nor modifies
fixtures, inference contracts, model admission, or provider access.
