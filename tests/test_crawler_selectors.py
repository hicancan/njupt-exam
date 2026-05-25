from datetime import datetime

from bs4 import BeautifulSoup

import scripts.update_search_index as indexer
from config.indexer_config import ChannelConfig, SelectorConfig, SourceConfig


def source_config() -> SourceConfig:
    return SourceConfig(
        id="jwc",
        name="教务处",
        base_url="https://jwc.njupt.edu.cn/",
        list_urls=("https://jwc.njupt.edu.cn/list.htm",),
        audience=("本科生",),
        source_weight=1.0,
        source_type="central_admin",
        include_patterns=("*page.htm",),
        channels=(),
    )


def test_collect_candidates_uses_channel_selectors(monkeypatch):
    html = """
    <ul>
      <li class="notice">
        <a class="notice-link" href="/2026/0524/c1/page.htm">关于2026年期末考试安排的通知</a>
        <span class="date">2026-05-24</span>
      </li>
    </ul>
    """
    monkeypatch.setattr(indexer, "fetch_html", lambda url, source=None: html)
    channel = ChannelConfig(
        id="jwc_exam",
        source_id="jwc",
        name="考试工作",
        list_urls=("https://jwc.njupt.edu.cn/list.htm",),
        student_value=1.0,
        selectors=SelectorConfig(list_item="li.notice", title=".notice-link", link=".notice-link", date=".date"),
    )

    candidates, errors = indexer.collect_candidates(source_config(), channel, datetime(2026, 5, 25, 12, 0, 0))

    assert errors == []
    assert candidates[0]["title"] == "关于2026年期末考试安排的通知"
    assert candidates[0]["published_at"] == "2026-05-24"
    assert candidates[0]["selector_strategy"] == "channel_list_selector"


def test_collect_candidates_records_selector_fallback(monkeypatch):
    html = """
    <a href="/2026/0524/c1/page.htm">关于2026年期末考试安排的通知</a>
    """
    monkeypatch.setattr(indexer, "fetch_html", lambda url, source=None: html)
    channel = ChannelConfig(
        id="jwc_exam",
        source_id="jwc",
        name="考试工作",
        list_urls=("https://jwc.njupt.edu.cn/list.htm",),
        student_value=1.0,
        selectors=SelectorConfig(list_item="li.notice", title=".missing", link=".missing"),
    )

    candidates, errors = indexer.collect_candidates(source_config(), channel, datetime(2026, 5, 25, 12, 0, 0))

    assert candidates[0]["selector_strategy"] == "global_anchor_fallback"
    assert any("selectors produced no usable candidates" in error for error in errors)


def test_content_and_attachment_selectors():
    soup = BeautifulSoup(
        """
        <article class="main-content">正文：学生须下载附件，并按照通知要求核对后提交。</article>
        <section class="attachments"><a href="/files/app.docx">申请表</a></section>
        """,
        "html.parser",
    )

    text, strategy = indexer.extract_article_text_with_strategy(soup, ".main-content")
    attachments = indexer.extract_attachments(soup, "https://jwc.njupt.edu.cn/2026/0524/c1/page.htm", ".attachments")

    assert strategy == "channel_content_selector"
    assert "学生须下载附件" in text
    assert attachments[0]["name"] == "申请表"
    assert attachments[0]["type"] == "docx"
