"""Check published single-group extraction against the pinned SZL enumerator.

Importing this module performs no data or enumerator loading.
"""
import hashlib
import importlib.util
from pathlib import Path

ENUMERATOR_SHA256 = "8cd4ba65f10806db9d3c13e9c2aed1ba618d22b4306ec85b4c6091072d1c35f7"


def verify(input_dir=Path(".")):
    from compare import HASHES, load_analysis

    input_dir = Path(input_dir)
    path = input_dir / "okr_khipu.py"
    if not path.is_file():
        raise FileNotFoundError(f"Required pinned enumerator is missing: {path}")
    if hashlib.sha256(path.read_bytes()).hexdigest() != ENUMERATOR_SHA256:
        raise ValueError(f"SHA256 mismatch for pinned enumerator: {path}")
    _, expected, expected_multi = load_analysis(input_dir)
    spec = importlib.util.spec_from_file_location("_pinned_okr_khipu", path)
    enumerator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(enumerator)
    corpus = enumerator.load_corpus(input_dir / "corpus.json.gz", expected_sha256=HASHES["corpus.json.gz"])
    recomputed = set()
    multigroup = 0
    for artifact in corpus["khipus"]:
        for row in enumerator.find_relations(artifact):
            if row["type"] != "R2":
                continue
            if len(row["clusters"]) == 1:
                recomputed.add((artifact["id"], row["target"], tuple(sorted(row["summands"])), row["target_value"]))
            else:
                multigroup += 1
    if recomputed != expected or multigroup != expected_multi:
        raise ValueError("Native OKR enumeration differs from the pinned published extraction")
    return f"Across {len(corpus['khipus'])} artifacts, replayed {len(recomputed)} single-group and {multigroup} multigroup exact R2 relations."


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    print(verify(args.input_dir))


if __name__ == "__main__":
    main()
