# Ñan silhouette lab

This file is a pointer. The 19-cut Ñan lab (Draft through Huklla) was built in the Grok App Builder sandbox. It is **not** the Hugging Face Space catalog and it is **not** yet merged into `szl_khipu/`.

## Why you do not see it on HF / GitHub

- Grok preview is a closed sandbox. It has no git remote and no Hugging Face token.
- Canonical GitHub is [`szl-holdings/szl-khipu`](https://github.com/szl-holdings/szl-khipu). That tree still stops at the older kernels (yarqa, chaski, tilegrid, prefix, route). It does **not** contain Yawar / Wasi / Sami / Kancha / Rimay / Nina / Suyay / Huklla.
- GitHub org slug is `szl-holdings` (hyphen). `github.com/SZLHoldings` 404s.
- Hugging Face org is [`SZLHOLDINGS`](https://huggingface.co/SZLHOLDINGS). Models named SZL-Khipu-1.5B are weights. They are not this fail-close lab.
- `khipu-lab` on GitHub is archived and points here.

## What is live in the sandbox

19 djb2 silhouette cuts. Conjecture 1 OPEN. energy UNAVAILABLE. proven_trust false.

`python3 nan_lab.py --selftest` prints `OK 19`.

To land this on GitHub + HF: merge `nan_lab.py` and the new `szl_khipu/{yawar,wasi,sami,kancha,rimay,nina,suyay,huklla}.py` kernels into this repo, then sync the Space from GitHub. HF cannot be written from this Grok connector.
