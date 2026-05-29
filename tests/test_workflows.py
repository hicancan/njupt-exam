from pathlib import Path


def test_collection_update_is_triggered_by_sitegraph_dispatch():
    workflow = Path(".github/workflows/update-collection-index.yml")
    assert workflow.exists()
    text = workflow.read_text(encoding="utf-8")
    assert "repository_dispatch:" in text
    assert "sitegraph-data-updated" in text
    assert "cron: '30 */6 * * *'" not in text
    assert "github.event.client_payload.sitegraph_ref" in text
    assert "ref: ${{ env.SITEGRAPH_REF }}" in text
    assert "DISPATCH_SITEGRAPH_REF" in text
    assert "DISPATCH_SOURCE_REPO" in text
    assert "DISPATCH_SOURCE_RUN_ID" in text
    assert "repository_dispatch missing client_payload.sitegraph_ref" in text
    assert "repository_dispatch source_repo must be hicancan/njupt-site-graph" in text
    assert "repository_dispatch missing client_payload.source_run_id" in text
    assert "Validate sitegraph ref exists" in text
    assert "repos/hicancan/njupt-site-graph/commits/$SITEGRAPH_REF" in text
    assert "sitegraph_ref $SITEGRAPH_REF is not a commit visible in hicancan/njupt-site-graph" in text


def test_collection_update_uses_configured_source_packages():
    workflow = Path(".github/workflows/update-collection-index.yml")
    text = workflow.read_text(encoding="utf-8")
    assert "NJUPT_SITEGRAPH_REPO: _sitegraph/njupt-site-graph" in text
    assert "--source-package \"$SITEGRAPH_JWC_INDEX\"" not in text
    assert "python -m njupt_search_indexer validate --skip-output" in text
