---
license: apache-2.0
library_name: kernels
tags:
  - kernels
  - governed-ai
  - khipu
  - lambda-gate
  - yarqa
  - numpy
---

<!-- SZL-CARD-PRESENTATION:v1 -->
<p><a href="https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab"><img src="https://raw.githubusercontent.com/szl-holdings/.github/main/profile/assets/szl/logos/szl_mark_holographic.svg" alt="SZL Holdings" width="112" /></a></p>

# SZL Khipu Kernels

Inspect NumPy reference kernels for advisory Λ decisions and YARQA attention.

**Artifact:** Reference kernel software in a model repository · **Stage:** Software / reference

[Explore in Command Lab](https://huggingface.co/spaces/SZLHOLDINGS/szl-command-lab) · [Build](https://github.com/szl-holdings/szl-khipu) · [Evidence](https://github.com/szl-holdings/szl-khipu/blob/8d06c9333b636a86a27d88feb49097906833af30/hf/szl-khipu-kernels/README.md)

## Before you use it

- First-class kernel release qualification is UNKNOWN. A model-repository README is not a qualified native kernel build.
- This source publisher updates the card only; card parity does not establish package API parity or a successful loader test.
- Λ remains advisory with Conjecture 1 OPEN and proven_trust=false. CUDA and energy measurement are UNAVAILABLE.

<details>
<summary>Technical details and evidence</summary>

<!-- SZL-CARD-TECHNICAL:v1:START -->

# szl-khipu-kernels

**SOFTWARE: NumPy reference kernels.** This card does not establish a trained-checkpoint release, production readiness or a current hosted service. Artifact presence alone does not establish trained-model validity.

Lambda is advisory: `proven_trust=false`; Conjecture 1 OPEN. CUDA / Triton and energy measurements are UNAVAILABLE in the reviewed evidence. No speedup, competitor superiority or production enforcement claim is made. Never a fabricated joule.

## Reviewed distribution and source scope

The 2026-09-30 read-only review inspected the model-type repository at
[`de8cb70313269b135cf6ea2a9a842d3a39426dd0`](https://huggingface.co/SZLHOLDINGS/szl-khipu-kernels/tree/de8cb70313269b135cf6ea2a9a842d3a39426dd0).
Its smaller NumPy reference package includes `evaluate_lambda` and `yarqa_attn`.
Extended anatomy, greenlight, chaski, ayni, shard, bay, prefix and route imports
from the former quickstart were absent from that reviewed package. They are not
examples for this distribution.

The inspected GitHub baseline is
[`szl-holdings/szl-khipu@e53e3d24b22e356eb986c373aee27b3b3e7947ec`](https://github.com/szl-holdings/szl-khipu/tree/e53e3d24b22e356eb986c373aee27b3b3e7947ec).
Its publisher reads `hf/szl-khipu-kernels/README.md` and uploads only this card to
the model-type repository. It does not publish or attest this kernel package's
file set. Equal README text and the shared version `0.1.0` do not establish
package API parity with the newer canonical source or the separate `szl-khipu`
model repository.

This evidence covers the card and selected small source files. It does not
establish install/import behavior, inference correctness, full-tree parity,
current CPU runtime health, a served revision or endpoint availability. Historical
receipts remain historical evidence; this correction does not supersede them or
qualify a new release.

## Guarded first-class kernel example

**First-class kernel release qualification: UNKNOWN.** No publication-qualified
first-class kernel revision or qualified `kernels` client was established by this
review. The model revision and GitHub baseline above are observations, not kernel
publication approval; neither is a default for this example.

Leave `QUALIFIED_KERNEL_REVISION` empty until the publisher has verified an
immutable first-class kernel release and compatible client. The example fails
before importing `kernels` until a 40-character lowercase hexadecimal revision
is supplied. This format guard does not verify hashes, publisher authorization
or compatibility.

**Execution warning:** `trust_remote_code=True` permits execution of the selected
repository's Python. Review that code and its release provenance before enabling
execution. Revision pinning does not establish safety or release qualification.

```python
import re

# Set only after publisher release and client qualification; not a model/GitHub SHA.
QUALIFIED_KERNEL_REVISION = ""
if not re.fullmatch(r"[0-9a-f]{40}", QUALIFIED_KERNEL_REVISION):
    raise ValueError("A qualified immutable first-class kernel revision is required.")

from kernels import get_kernel

k = get_kernel(
    "SZLHOLDINGS/szl-khipu-kernels",
    revision=QUALIFIED_KERNEL_REVISION,
    trust_remote_code=True,
)
```

This is a guarded API example, not a successful loader or runtime test. Source-only
work should use an independently reviewed local checkout and its matching API;
no provider loader is required to inspect the reference implementation.

## License and limits

The reviewed distribution declares Apache-2.0 and contains an Apache-2.0 LICENSE
file. Copyright 2026 SZL Holdings. Doctrine v11 LOCKED. Advisory reference behavior,
source review and receipt presence do not grant production or control authority.

<!-- SZL-CARD-TECHNICAL:v1:END -->

</details>
