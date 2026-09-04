# Ñan silhouette lab

Doctrine v11 LOCKED. Conjecture 1 OPEN. energy UNAVAILABLE. proven_trust false. djb2 silhouette ≠ SHA3. Never a fabricated joule.

These original fail-close cuts now live in this repo on `main`:

| cut | module | job |
|---|---|---|
| YawarWitness | `szl_khipu/yawar.py` | parent-digest lineage |
| WasiWitness | `szl_khipu/wasi.py` | rooms named at seal |
| SamiWitness | `szl_khipu/sami.py` | energy stays UNAVAILABLE |
| KanchaWitness | `szl_khipu/kancha.py` | courtyard gates stay shut |
| RimayWitness | `szl_khipu/rimay.py` | spoken tokens stay spoken |
| NinaWitness | `szl_khipu/nina.py` | one spark, never a joule |
| SuyayWitness | `szl_khipu/suyay.py` | promised tick arrives on seal |
| HukllaWitness | `szl_khipu/huklla.py` | two receipts stay one pair |

Run:

```bash
PYTHONPATH=. python -m unittest tests.test_nan_witness -q
python -c "from szl_khipu import run_sami; print(run_sami(11))"
```

Honest mode holds. `mode=1` fail-closes. Mint is blocked while broken.

Canonical GitHub: https://github.com/szl-holdings/szl-khipu
Hugging Face Space sync is a separate publish step (no HF token from this sandbox).
