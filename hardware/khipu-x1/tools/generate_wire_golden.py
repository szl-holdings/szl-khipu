"""Generate or verify normative KIDS-BIN v0.1 golden vectors."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from khipu_x1 import Descriptor, Opcode
from khipu_x1.wire import decode_batch, decode_descriptor, encode_batch, encode_descriptor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "golden" / "kids-bin-v0.1.json"
MODEL = hashlib.sha256(b"khipu-x1-golden-model").hexdigest()
POLICY = hashlib.sha256(b"khipu-x1-golden-policy").hexdigest()
GRAPH = hashlib.sha256(b"khipu-x1-golden-graph").hexdigest()


def build_vectors() -> dict[str, object]:
    descriptors = [
        Descriptor(
            sequence=7,
            nonce=70,
            opcode=Opcode.GEMM_INT8,
            model_digest=MODEL,
            policy_digest=POLICY,
            inputs=("activation", "weight"),
            output="projected",
            attrs={"scale": 0.125, "graph_digest": GRAPH, "graph_node_id": "project"},
        ),
        Descriptor(
            sequence=8,
            nonce=71,
            opcode=Opcode.RMSNORM,
            model_digest=MODEL,
            policy_digest=POLICY,
            inputs=("projected",),
            output="normalized",
            attrs={"eps": 1e-6, "graph_digest": GRAPH, "graph_node_id": "normalize"},
        ),
        Descriptor(
            sequence=9,
            nonce=72,
            opcode=Opcode.SHA3_COMMIT,
            model_digest=MODEL,
            policy_digest=POLICY,
            inputs=("normalized",),
            attrs={"graph_digest": GRAPH, "graph_node_id": "commit"},
        ),
    ]
    buffer_ids = {
        "activation": 1,
        "weight": 2,
        "projected": 3,
        "normalized": 4,
    }
    single = encode_descriptor(descriptors[0], buffer_ids)
    batch = encode_batch(descriptors, buffer_ids)
    parsed_single = decode_descriptor(single)
    parsed_batch = decode_batch(batch)

    bad_descriptor_digest = bytearray(single)
    bad_descriptor_digest[64] ^= 1

    reserved_descriptor_flag = bytearray(single)
    current_flags = struct.unpack_from("<H", reserved_descriptor_flag, 8)[0]
    struct.pack_into("<H", reserved_descriptor_flag, 8, current_flags | (1 << 15))
    reserved_descriptor_flag[160:192] = hashlib.sha256(
        reserved_descriptor_flag[:160]
    ).digest()

    bad_batch_body = bytearray(batch)
    bad_batch_body[-1] ^= 1

    return {
        "schema": "kids-bin-golden/v0.1",
        "truth": "SOFTWARE_CONFORMANCE_REFERENCE",
        "hardware_status": "UNAVAILABLE",
        "model_digest": MODEL,
        "policy_digest": POLICY,
        "graph_digest": GRAPH,
        "buffer_ids": buffer_ids,
        "single": {
            "sha256": hashlib.sha256(single).hexdigest(),
            "hex": single.hex(),
            "decoded": parsed_single.as_dict(),
        },
        "batch": {
            "sha256": hashlib.sha256(batch).hexdigest(),
            "hex": batch.hex(),
            "decoded": parsed_batch.as_dict(),
        },
        "negative": [
            {
                "name": "descriptor_digest_mismatch",
                "decoder": "descriptor",
                "expected_error": "descriptor digest mismatch",
                "hex": bytes(bad_descriptor_digest).hex(),
            },
            {
                "name": "descriptor_reserved_flag",
                "decoder": "descriptor",
                "expected_error": "reserved flag",
                "hex": bytes(reserved_descriptor_flag).hex(),
            },
            {
                "name": "batch_body_digest_mismatch",
                "decoder": "batch",
                "expected_error": "batch body digest mismatch",
                "hex": bytes(bad_batch_body).hex(),
            },
        ],
    }


def render() -> bytes:
    return (json.dumps(build_vectors(), sort_keys=True, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.check:
        if not OUT.exists() or OUT.read_bytes() != expected:
            print(f"STALE: {OUT}")
            return 1
        print(f"CURRENT: {OUT}")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(expected)
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
