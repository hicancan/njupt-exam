from njupt_search_indexer.sitegraph_text import (
    clean_text,
    normalize_text,
    sha1_text,
    sitegraph_tokens,
    stable_slug,
)


def test_sitegraph_text_helpers_are_deterministic() -> None:
    assert clean_text("  A\n B\tC  ") == "A B C"
    assert normalize_text("Ａ B　校 历") == "ab校历"
    assert stable_slug("考试 信息/2026", max_length=20) == "考试信息-2026"
    assert sha1_text("njupt", length=8) == "a9283010"


def test_sitegraph_tokens_keep_cjk_ngrams_and_ascii_terms() -> None:
    tokens = sitegraph_tokens("校历查询 MOOC", cjk_max_n=3)

    assert {"校历查询", "校历", "历查", "查询", "校历查", "历查询", "mooc"} <= tokens
