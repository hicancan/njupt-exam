from collections import Counter, defaultdict
from math import log
from typing import Any

from core.bm25_indexer import tokenize_text


def build_hybrid_index(
    documents: list[dict[str, Any]],
    task_frames: list[dict[str, Any]],
    *,
    ranking_weights: dict[str, Any],
    query_aliases: dict[str, Any],
    ontology: dict[str, Any],
) -> dict[str, Any]:
    task_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame in task_frames:
        task_by_doc[str(frame.get("doc_id", ""))].append(frame)

    doc_terms: dict[str, Counter[str]] = {}
    doc_lengths: dict[str, int] = {}
    document_frequency: Counter[str] = Counter()
    doc_fields: dict[str, dict[str, Any]] = {}

    for document in documents:
        doc_id = str(document.get("id") or document.get("doc_id"))
        fields = build_search_fields(document, task_by_doc.get(doc_id, []))
        tokens = tokenize_text(" ".join(str(value) for value in fields.values()))
        counter = Counter(tokens)
        doc_terms[doc_id] = counter
        doc_lengths[doc_id] = sum(counter.values())
        document_frequency.update(counter.keys())
        doc_fields[doc_id] = {
            "source_id": document.get("source_id"),
            "channel_id": document.get("channel_id"),
            "domain": document.get("domain"),
            "intent": document.get("intent"),
            "lifecycle": document.get("lifecycle"),
            "student_score": document.get("student_score"),
            "importance_score": document.get("importance_score"),
            "source_weight": document.get("source_weight"),
            "risk_flags": document.get("risk_flags", []),
            "task_count": len(task_by_doc.get(doc_id, [])),
            "fields": fields,
        }

    doc_count = len(documents)
    avg_doc_len = round(sum(doc_lengths.values()) / doc_count, 4) if doc_count else 0
    idf = {
        term: round(log(1 + (doc_count - df + 0.5) / (df + 0.5)), 6)
        for term, df in document_frequency.items()
    }

    return {
        "version": "hytask-hybrid-index-v1",
        "doc_count": doc_count,
        "task_frame_count": len(task_frames),
        "avg_doc_len": avg_doc_len,
        "weights": ranking_weights,
        "query_alias_count": len(query_aliases),
        "ontology_version": ontology.get("version", 1),
        "idf": dict(sorted(idf.items())),
        "documents": {
            doc_id: {
                "length": doc_lengths[doc_id],
                "terms": dict(doc_terms[doc_id].most_common(160)),
                **doc_fields[doc_id],
            }
            for doc_id in sorted(doc_terms)
        },
    }


def build_search_fields(document: dict[str, Any], task_frames: list[dict[str, Any]]) -> dict[str, str]:
    task_what = " ".join(str(frame.get("what") or "") for frame in task_frames)
    task_action = " ".join(
        str((frame.get("action") or {}).get("summary") or (frame.get("action") or {}).get("verb") or "")
        for frame in task_frames
    )
    task_evidence = " ".join(
        str(item.get("text") or "")
        for frame in task_frames
        for item in (frame.get("evidence") or [])
        if isinstance(item, dict)
    )
    materials = " ".join(
        str(item.get("name") or "")
        for frame in task_frames
        for item in (frame.get("materials") or [])
        if isinstance(item, dict)
    )
    return {
        "title": str(document.get("title") or ""),
        "tags": " ".join(str(item) for item in document.get("tags", [])),
        "task.what": task_what,
        "task.action.summary": task_action,
        "evidence": " ".join([*(str(item) for item in document.get("evidence", [])), task_evidence]),
        "materials.name": " ".join([*(str(item) for item in document.get("required_materials", [])), materials]),
        "source": " ".join(str(document.get(key) or "") for key in ("source", "channel", "source_id", "channel_id")),
        "content": str(document.get("content") or ""),
    }
