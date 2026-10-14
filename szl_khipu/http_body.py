# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 SZL Holdings
"""One strict, bounded JSON request-body parser for the stdlib HTTP surfaces.

``szl_khipu.http_app``, ``szl_khipu.nan_lab`` and the Space ``server.py`` all read
POST bodies through :func:`read_json_object`. stdlib only, so the Space can load
this file even when the numpy-backed package does not import.

* ``Content-Length`` is required and must be one run of ASCII digits. Missing it,
  or sending ``Transfer-Encoding`` (no chunked bodies), is 411. A malformed,
  negative or repeated value is 400.
* The declared length is checked against ``MAX_BODY_BYTES`` before any byte is
  read: 413.
* The body is read against a total deadline, on top of the handler's per-socket
  ``SOCKET_TIMEOUT_S``. A body that stalls is 408. A short read (the client closed
  before sending the declared length) is 400.
* The bytes must be strict UTF-8 and strict JSON (no NaN/Infinity, no number that
  overflows a float, no duplicate keys), and the top level must be an object: 400.
* ``Content-Length: 0`` is the one explicit "no body" case. It returns ``{}``, so the
  demo defaults stay reachable on purpose. Invalid input is never replaced by ``{}``.

The field helpers below apply the same rule to values: an absent key takes the
route's default, and a present but invalid value is a 400, never the default.
"""

from __future__ import annotations

import json
import math
import re
import time
from typing import Any, Callable, Iterable

# The largest legitimate body is a few hundred bytes (13 Λ axes, a handful of flags).
MAX_BODY_BYTES = 64 * 1024
# Total time allowed to receive a declared body, however it trickles in.
BODY_DEADLINE_S = 10.0
# Per-socket-operation timeout for the request handlers (BaseHTTPRequestHandler.timeout).
SOCKET_TIMEOUT_S = 10.0

_LENGTH = re.compile(r"[0-9]+")
_INTEGER_TEXT = re.compile(r"[+-]?[0-9]{1,20}")
_CHUNK = 16 * 1024


class RequestRejected(ValueError):
    """A request the reference surfaces refuse, carrying its HTTP status and reason."""

    def __init__(self, status: int, reason: str) -> None:
        super().__init__(reason)
        self.status = int(status)
        self.reason = reason

    def payload(self) -> dict[str, Any]:
        return {"error": self.reason, "status": self.status, "blocked": True, "proven_trust": False}


def _header_values(headers: Any, name: str) -> list[str]:
    get_all = getattr(headers, "get_all", None)
    if callable(get_all):
        return [str(v) for v in (get_all(name) or [])]
    value = headers.get(name)
    return [] if value is None else [str(value)]


def content_length(headers: Any, *, max_bytes: int = MAX_BODY_BYTES) -> int:
    """The declared body length, or a 411/400/413 :class:`RequestRejected`."""
    if _header_values(headers, "Transfer-Encoding"):
        raise RequestRejected(411, "Transfer-Encoding is not accepted; send a Content-Length body")
    values = _header_values(headers, "Content-Length")
    if not values:
        raise RequestRejected(411, "Content-Length is required")
    if len(values) != 1:
        raise RequestRejected(400, "exactly one Content-Length header is required")
    text = values[0].strip(" \t")
    if not _LENGTH.fullmatch(text):
        raise RequestRejected(400, "Content-Length must be a non-negative decimal integer")
    digits = text.lstrip("0") or "0"
    # Compare by digit count first: an absurd length is a 413, never a big-int parse.
    if len(digits) > len(str(max_bytes)) or int(digits) > max_bytes:
        raise RequestRejected(413, f"request body exceeds {max_bytes} bytes")
    return int(digits)


def read_exact(rfile: Any, length: int, *, deadline_s: float = BODY_DEADLINE_S) -> bytes:
    """Read exactly ``length`` bytes or raise 408 (stalled) / 400 (short read)."""
    if length <= 0:
        return b""
    read = getattr(rfile, "read1", None) or rfile.read
    deadline = time.monotonic() + deadline_s
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        if time.monotonic() > deadline:
            raise RequestRejected(408, "request body was not received in time")
        try:
            chunk = read(min(remaining, _CHUNK))
        except TimeoutError:
            raise RequestRejected(408, "request body was not received in time") from None
        except OSError:
            raise RequestRejected(400, "request body could not be read") from None
        if not chunk:
            raise RequestRejected(
                400, f"truncated request body: received {length - remaining} of {length} bytes"
            )
        # The final blocking read can return after the total deadline, too.
        # Keep EOF and I/O failures above on their existing error paths.
        if time.monotonic() > deadline:
            raise RequestRejected(408, "request body was not received in time")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _reject_constant(name: str) -> Any:
    raise RequestRejected(400, f"body is not strict JSON: {name} is not a JSON number")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise RequestRejected(400, f"body is not strict JSON: {text} overflows a float")
    return value


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise RequestRejected(400, f"body is not strict JSON: duplicate key {key!r}")
        out[key] = value
    return out


def _json_type(value: Any) -> str:
    if isinstance(value, list):
        return "an array"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, bool):
        return "a boolean"
    if value is None:
        return "null"
    return "a number"


def parse_json_object(raw: bytes) -> dict[str, Any]:
    """Strict UTF-8, strict JSON, object at the top level. ``b""`` is the explicit ``{}``."""
    if raw == b"":
        return {}
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RequestRejected(400, f"body is not valid UTF-8 (byte {exc.start})") from None
    try:
        value = json.loads(
            text,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
            object_pairs_hook=_unique_object,
        )
    except RequestRejected:
        raise
    except (ValueError, RecursionError) as exc:
        raise RequestRejected(400, f"body is not valid JSON: {exc}") from None
    if not isinstance(value, dict):
        raise RequestRejected(400, f"body must be a JSON object, not {_json_type(value)}")
    return value


def read_json_object(
    headers: Any,
    rfile: Any,
    *,
    max_bytes: int = MAX_BODY_BYTES,
    deadline_s: float = BODY_DEADLINE_S,
) -> dict[str, Any]:
    """The one entry point: bounded length, bounded read, strict JSON object."""
    length = content_length(headers, max_bytes=max_bytes)
    return parse_json_object(read_exact(rfile, length, deadline_s=deadline_s))


def int_field(
    body: dict[str, Any],
    key: str,
    default: int,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """An integer field. Absent → ``default``; present but invalid → 400."""
    if key not in body:
        return default
    value = body[key]
    if isinstance(value, bool):
        raise RequestRejected(400, f"{key} must be an integer, not a boolean")
    if isinstance(value, int):
        number = value
    elif isinstance(value, float) and math.isfinite(value) and value.is_integer():
        number = int(value)
    elif isinstance(value, str) and _INTEGER_TEXT.fullmatch(value):
        number = int(value)  # query-string values arrive as text
    else:
        raise RequestRejected(400, f"{key} must be an integer")
    if minimum is not None and number < minimum:
        raise RequestRejected(400, f"{key} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise RequestRejected(400, f"{key} must be <= {maximum}")
    return number


def real_field(body: dict[str, Any], key: str, default: float) -> float:
    """A finite real-number field. Absent → ``default``; present but invalid → 400."""
    if key not in body:
        return default
    value = body[key]
    if isinstance(value, bool):
        raise RequestRejected(400, f"{key} must be a number, not a boolean")
    try:
        number = float(value) if isinstance(value, (int, float, str)) else math.nan
    except (ValueError, OverflowError):
        number = math.nan
    if not math.isfinite(number):
        raise RequestRejected(400, f"{key} must be a finite number")
    return number


def real_list_field(body: dict[str, Any], key: str, default: Iterable[float]) -> list[float]:
    """A non-empty array of real numbers. Absent → ``default``; present but invalid → 400.

    Range and finiteness stay with the kernel that consumes the list (e.g. the
    szl.lambda/v1 codes), so a well-shaped out-of-range vector keeps its kernel verdict.
    """
    if key not in body:
        return [float(x) for x in default]
    value = body[key]
    if not isinstance(value, list) or not value:
        raise RequestRejected(400, f"{key} must be a non-empty array of numbers")
    out: list[float] = []
    for i, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise RequestRejected(400, f"{key}[{i}] must be a number")
        try:
            out.append(float(item))
        except OverflowError:
            raise RequestRejected(400, f"{key}[{i}] overflows a float") from None
    return out


def guarded(call: Callable[[], Any]) -> tuple[int, Any]:
    """Run ``call``; a :class:`RequestRejected` becomes (status, payload), anything else 400.

    The reference surfaces never answer a malformed request with a fake 200 or a 500.
    """
    try:
        return 200, call()
    except RequestRejected as exc:
        return exc.status, exc.payload()
    except Exception as exc:  # noqa: BLE001 — kernel fail-closed: an explicit 400 with its reason
        return 400, {"error": str(exc), "status": 400, "blocked": True, "proven_trust": False}
