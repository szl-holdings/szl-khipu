"""SZL Khipu-Yachay v0: typed evidence-first cord arithmetic (NOT historical decipherment)."""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

MAX_CORDS = 16
MAX_VALUE = 999999
_INTENTS = ("NUMERACY", "RECORDS", "RESEARCH_LIMITS", "DATA_RIGHTS", "METHODS")
WORDS = re.compile(r"[a-záéíóúñü]+|[0-9]+", re.IGNORECASE)


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def tokenize(text: str) -> list[str]:
    if not isinstance(text, str) or len(text) > 500:
        raise ValueError("QUESTION_LENGTH")
    return WORDS.findall(text.lower())[:80]


def evaluate_cords(cords: object, declared_total: object) -> dict:
    if not isinstance(cords, list) or not 1 <= len(cords) <= MAX_CORDS:
        raise ValueError("CORD_COUNT")
    if type(declared_total) is not int or not 0 <= declared_total <= MAX_VALUE * MAX_CORDS:
        raise ValueError("DECLARED_TOTAL")
    for n in cords:
        if n is not None and (type(n) is not int or not 0 <= n <= MAX_VALUE):
            raise ValueError("CORD_VALUE")
    if any(n is None for n in cords):
        status, observed_sum = "UNAVAILABLE_INCOMPLETE_RECORD", None
    else:
        observed_sum = sum(cords)
        status = ("ARITHMETIC_EQUAL_ONLY" if observed_sum == declared_total
                  else "REVIEW_MISMATCH")
    result = {
        "schema": "szl.khipu-yachay.arithmetic/v0",
        "state": status,
        "declared_total": declared_total,
        "visible_cords": cords,
        "observed_sum": observed_sum,
        "complete": all(n is not None for n in cords),
        "source_class": "USER_ENTERED_MODERN_DEMONSTRATION",
        "historical_transcription": False,
        "archaeological_meaning_verified": False,
        "training_authority": "NONE",
    }
    result["receipt_sha256"] = sha256(canonical(result))
    return result


def load_model(path: str | Path) -> dict:
    path = Path(path)
    if path.stat().st_size > 150000:
        raise ValueError("MODEL_BYTE_LIMIT")
    def pairs_unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("DUPLICATE_MODEL_KEY")
            result[k] = v
        return result
    obj = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs_unique)
    if obj.get("schema") != "szl.khipu-yachay.nb/v0" or obj.get("classes") != list(_INTENTS):
        raise ValueError("MODEL_SCHEMA")
    vocab = obj["vocab"]
    if not isinstance(vocab, dict) or len(vocab) > 4000 or len(vocab) < 20:
        raise ValueError("MODEL_VOCAB")
    if set(obj["log_likelihood"]) != set(_INTENTS) or set(obj["log_prior"]) != set(_INTENTS):
        raise ValueError("MODEL_CLASSES")
    for label in _INTENTS:
        if not isinstance(obj["log_likelihood"][label], list) or len(obj["log_likelihood"][label]) != len(vocab):
            raise ValueError("MODEL_SHAPE")
        if any(type(x) not in (int, float) or not math.isfinite(x)
               for x in obj["log_likelihood"][label] + [obj["log_prior"][label]]):
            raise ValueError("MODEL_NONFINITE")
    if sorted(vocab.values()) != list(range(len(vocab))):
        raise ValueError("MODEL_INDEX")
    return obj


def route_question(question: str, model: dict) -> dict:
    tokens = tokenize(question)
    features = [model["vocab"].get(w) for w in tokens]
    known = [f for f in features if f is not None]
    if len(known) < 2:
        return {"intent": "ABSTAIN", "score": None, "evidence": "UNKNOWN_WORDS"}
    scores = {}
    for label in _INTENTS:
        row = model["log_likelihood"][label]
        scores[label] = model["log_prior"][label] + sum(row[i] for i in known)
    best = max(scores, key=scores.get)
    top = scores[best]
    exp = {k: math.exp(v - top) for k, v in scores.items()}
    probability = exp[best] / sum(exp.values())
    if probability < 0.72:
        return {"intent": "ABSTAIN", "score": round(probability, 6), "evidence": "LOW_ROUTING_SCORE"}
    return {"intent": best, "score": round(probability, 6),
            "evidence": "SYNTHETIC_INTENT_MODEL_NOT_FACTUAL_CONFIDENCE"}


KNOWLEDGE = {
    "NUMERACY": {"short": "Some numeric khipus use decimal place-value knots; this demo is not a historical transcription.",
                 "source_id": "NIST_KHIPU", "claim": "CURATED_SOURCE_SUMMARY"},
    "RECORDS": {"short": "The Open Khipu Repository v2.1.0 provides KH identifiers and a published digital archive. A KH number alone does not reveal a khipu's meaning.",
                "source_id": "OKR_2_1", "claim": "CURATED_SOURCE_SUMMARY"},
    "RESEARCH_LIMITS": {"short": "Many khipu meanings remain unsettled. Structural patterns or a model score do not establish decipherment.",
                        "source_id": "OKR_2_1", "claim": "CURATED_SOURCE_SUMMARY"},
    "DATA_RIGHTS": {"short": "Research data and cultural heritage need attribution, rights checks, Indigenous participation, and limits on derivative training.",
                    "source_id": "OKR_2_1", "claim": "ETHICAL_RESEARCH_POLICY"},
    "METHODS": {"short": "A sum check and an immutable source digest answer different questions: arithmetic agreement is not evidence of historical authenticity.",
                "source_id": "SZL_METHOD", "claim": "SZL_MODERN_ENGINEERING_EXPLANATION"},
}


def answer(question: str, model: dict, sources: dict) -> dict:
    prediction = route_question(question, model)
    label = prediction["intent"]
    if label == "ABSTAIN":
        return {"state": "UNAVAILABLE", "text": "Not enough grounded evidence to answer. Try a narrower question or consult the cited research.",
                "prediction": prediction, "citations": [], "truth_qualified": False}
    item = KNOWLEDGE[label]
    source = sources.get(item["source_id"], {})
    return {"state": "CURATED_REFERENCE_ONLY", "text": item["short"],
            "prediction": prediction, "citations": [{"id": item["source_id"],
                                                      "url": source.get("url", "") }],
            "truth_qualified": False, "model_route_is_advisory": True}
