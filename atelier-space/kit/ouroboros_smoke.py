# szl_khipu/ouroboros.py — MEASURED ms, DERIVED overhead, never fabricate joules.
from szl_khipu.ouroboros import loop_tax

r = loop_tax(
    [{"ok": False, "ms": 220}, {"ok": True, "ms": 900}],
    wall_ms=1300,
    max_budget=4,
)
print(r["exit"], r["modelMs"], r["overheadMs"], r["honesty"])
assert r["modelMs"] == 1120
assert r["overheadMs"] == 180
print("ok")
