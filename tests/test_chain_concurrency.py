# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""UnifiedReceiptChain under concurrent emitters (ThreadingHTTPServer shares one chain)."""

from __future__ import annotations

import json
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from szl_khipu.chain import ZERO, UnifiedReceiptChain


class _FastSwitch:
    def __enter__(self) -> None:
        self._old = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)

    def __exit__(self, *exc: object) -> None:
        sys.setswitchinterval(self._old)


class ChainConcurrencyTests(unittest.TestCase):
    def test_concurrent_emit_keeps_chain_intact(self) -> None:
        c = UnifiedReceiptChain()
        n_threads, per = 8, 300

        def work(t: int) -> None:
            for i in range(per):
                c.emit("k", "op", {"t": t, "i": i})

        with _FastSwitch():
            threads = [threading.Thread(target=work, args=(t,)) for t in range(n_threads)]
            for th in threads:
                th.start()
            for th in threads:
                th.join()

        total = n_threads * per
        self.assertEqual(c.verify(), (True, total, -1))
        recs = c.receipts
        self.assertEqual([r.seq for r in recs], list(range(total)))
        prev = ZERO
        for r in recs:
            self.assertEqual(r.prev, prev)
            prev = r.digest

    def test_verify_snapshot_during_emit(self) -> None:
        c = UnifiedReceiptChain()
        stop = threading.Event()
        results: list[bool] = []

        def emitter() -> None:
            for i in range(1500):
                c.emit("k", "op", {"i": i})
            stop.set()

        def verifier() -> None:
            while not stop.is_set():
                results.append(c.verify()[0])
            results.append(c.verify()[0])

        with _FastSwitch():
            e = threading.Thread(target=emitter)
            v = threading.Thread(target=verifier)
            v.start()
            e.start()
            e.join()
            v.join()

        self.assertTrue(results)
        self.assertTrue(all(results))

    def test_concurrent_http_posts_keep_version_chain_ok(self) -> None:
        from szl_khipu import http_app

        server = http_app.make_server(host="127.0.0.1", port=0)
        port = server.server_address[1]
        srv = threading.Thread(target=server.serve_forever, daemon=True)
        srv.start()
        try:
            body = json.dumps({}).encode()

            def post() -> None:
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}/api/lambda",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    r.read()

            with _FastSwitch():
                posters = [threading.Thread(target=post) for _ in range(16)]
                for p in posters:
                    p.start()
                for p in posters:
                    p.join()

            with urllib.request.urlopen(f"http://127.0.0.1:{port}/version", timeout=30) as r:
                info = json.loads(r.read())
            self.assertTrue(info["chain_ok"])
            self.assertEqual(info["chain_break"], -1)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()


class ChainCopyTests(unittest.TestCase):
    """gr.State deep-copies its initial value; the lock must not block that."""

    def test_deepcopy_gives_independent_intact_chain(self):
        from copy import deepcopy
        from szl_khipu.chain import UnifiedReceiptChain

        chain = UnifiedReceiptChain()
        chain.emit("k", "op", {"a": 1})
        clone = deepcopy(chain)
        self.assertEqual(clone.verify(), (True, 1, -1))
        self.assertEqual(clone.head, chain.head)
        clone.emit("k", "op", {"a": 2})
        self.assertEqual(len(chain.receipts), 1)
        self.assertEqual(clone.verify(), (True, 2, -1))
        self.assertIsNot(clone._lock, chain._lock)

    def test_pickle_round_trip_keeps_chain_and_lock_usable(self):
        import pickle
        from szl_khipu.chain import UnifiedReceiptChain

        chain = UnifiedReceiptChain()
        chain.emit("k", "op", {"a": 1})
        restored = pickle.loads(pickle.dumps(chain))
        self.assertEqual(restored.verify(), (True, 1, -1))
        restored.emit("k", "op", {"a": 2})
        self.assertEqual(restored.verify(), (True, 2, -1))
