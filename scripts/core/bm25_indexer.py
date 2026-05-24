import re
from collections import Counter
from math import log
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+\-.#]*|[0-9]+|[\u4e00-\u9fff]{1,4}")


def tokenize_text(text: str) -> list[str]:
    normalized = str(text or "").lower()
    tokens = TOKEN_RE.findall(normalized)
    expanded: list[str] = []
    for token in tokens:
        expanded.append(token)
        if re.fullmatch(r"[\u4e00-\u9fff]{3,4}", token):
            expanded.extend(token[index:index + 2] for index in range(len(token) - 1))
    return [token for token in expanded if token.strip()]


def bm25_scores(
    query_tokens: list[str],
    hybrid_index: dict[str, Any],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> dict[str, float]:
    documents = hybrid_index.get("documents", {})
    avg_len = float(hybrid_index.get("avg_doc_len", 0) or 1)
    idf = hybrid_index.get("idf", {})
    scores: dict[str, float] = {}
    for doc_id, payload in documents.items():
        terms = Counter(payload.get("terms", {}))
        doc_len = float(payload.get("length", 0) or 1)
        score = 0.0
        for token in query_tokens:
            tf = float(terms.get(token, 0))
            if tf <= 0:
                continue
            term_idf = float(idf.get(token, log(1.2)))
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avg_len)
            score += term_idf * numerator / denominator
        if score > 0:
            scores[doc_id] = score
    return scores
