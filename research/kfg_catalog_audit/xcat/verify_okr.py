"""Check the published single-group extraction against the pinned SZL enumerator."""
from contextlib import redirect_stdout
import hashlib
from io import StringIO
from pathlib import Path

assert hashlib.sha256(Path("okr_khipu.py").read_bytes()).hexdigest() == (
    "8cd4ba65f10806db9d3c13e9c2aed1ba618d22b4306ec85b4c6091072d1c35f7"
)
import okr_khipu

with redirect_stdout(StringIO()):
    import compare
corpus = okr_khipu.load_corpus("corpus.json.gz", expected_sha256=compare.HASHES["corpus.json.gz"])
recomputed = set()
multigroup = 0
for artifact in corpus["khipus"]:
    for row in okr_khipu.find_relations(artifact):
        if row["type"] != "R2":
            continue
        if len(row["clusters"]) == 1:
            recomputed.add((artifact["id"], row["target"], tuple(sorted(row["summands"])), row["target_value"]))
        else:
            multigroup += 1
assert recomputed == compare.ok_pos
assert multigroup == compare.multi
print(f"Across {len(corpus['khipus'])} artifacts, replayed {len(recomputed)} single-group and {multigroup} multigroup exact R2 relations.")
