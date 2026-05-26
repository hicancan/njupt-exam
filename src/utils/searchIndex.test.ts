import { describe, expect, it } from 'vitest';
import {
    parseSitegraphDocMeta,
    parseSitegraphManifest,
    recallSitegraphDocuments
} from './searchIndex';
import { SitegraphIndexBundle, SitegraphSearchManifest } from '@/types';

const artifact = (path: string, role: string, load = 'on_demand', count?: number) => ({
    path,
    sha256: '0123456789abcdef0123456789abcdef',
    bytes: 128,
    role,
    load,
    ...(count === undefined ? {} : { count })
});

const fullShard = {
    shard_id: 'policy__detail__2026__rules__b0',
    path: 'fixture-shard.0123456789abcdef.json',
    sha256: '0123456789abcdef0123456789abcdef',
    bytes: 256,
    count: 1,
    contains: 'full_documents' as const,
    facet_range: ['policy'],
    record_type_range: ['detail'],
    section_range: ['jwc_rules_root'],
    year_range: ['2026'],
    hash_bucket: 'b0'
};

const manifest: SitegraphSearchManifest = {
    generated_at: '2026-05-27T00:00:00Z',
    strategy: 'pure-sitegraph-code-search-v2',
    producer_repo: 'hicancan/njupt-search',
    producer_ref: 'fixture',
    site_id: 'jwc',
    artifact_path: 'index',
    upstream_generated_at: '2026-05-26T00:00:00Z',
    truth_counts: { detail_pages: 1, attachments: 1, external_links: 0, edges: 0 },
    total_documents: 1,
    record_counts: { detail: 1 },
    facet_counts: { policy: 1 },
    exam_vertical_preserved: true,
    core_search: {
        algorithm: 'static inverted index plus on-demand full shard ranking',
        execution_model: 'pure_frontend_worker',
        light_first_screen: true,
        first_screen_artifacts: ['doc_meta_light', 'light_inverted_index', 'query_aliases'],
        body_index_loading: 'on_deep_search',
        full_text_loading: 'on_demand_by_candidate_shard',
        search_worker: true
    },
    artifacts: {
        doc_meta_light: artifact('index/sitegraph/jwc/artifacts/doc_meta_light.0123456789abcdef.json', 'doc_meta_light', 'initial', 1),
        light_inverted_index: artifact('index/sitegraph/jwc/artifacts/light_inverted_index.0123456789abcdef.json', 'light_inverted_index', 'initial'),
        body_inverted_index: artifact('index/sitegraph/jwc/artifacts/body_inverted_index.0123456789abcdef.json', 'body_inverted_index', 'deep_search'),
        section_index: artifact('index/sitegraph/jwc/artifacts/section_index.0123456789abcdef.json', 'section_index', 'on_demand'),
        attachment_index: artifact('index/sitegraph/jwc/artifacts/attachment_index.0123456789abcdef.json', 'attachment_index', 'on_demand', 1),
        external_index: artifact('index/sitegraph/jwc/artifacts/external_index.0123456789abcdef.json', 'external_index', 'on_demand', 0),
        query_aliases: artifact('index/sitegraph/jwc/artifacts/query_aliases.0123456789abcdef.json', 'query_aliases', 'initial', 1),
        outcomes: artifact('index/sitegraph/jwc/artifacts/outcomes.0123456789abcdef.json', 'outcomes', 'audit'),
        size_report: artifact('index/sitegraph/jwc/artifacts/size_report.0123456789abcdef.json', 'size_report', 'audit')
    },
    sitegraph: {
        truth_counts: { detail_pages: 1, attachments: 1, external_links: 0, edges: 0 },
        quality: {
            errors: 0,
            all_discovered_urls_have_outcomes: true,
            attachment_policy: 'metadata_only',
            external_link_policy: 'record_only'
        },
        upstream_generated_at: '2026-05-26T00:00:00Z',
        detail_page_records: 1,
        attachment_metadata_records: 1,
        direct_attachment_records: 0,
        external_link_records: 0,
        external_document_records: 0,
        utility_link_records: 0,
        attachment_policy: 'metadata_only',
        external_link_policy: 'record_only',
        full_shards: [fullShard],
        shard_strategy: {
            version: 'locality-facet-record-year-section-hash-v1',
            dimensions: ['facet', 'record_type', 'year', 'top_nav_section', 'hash_bucket'],
            hash_bucket_count: 4,
            sequential_fixed_size_shards: false
        },
        indexes: {
            doc_meta_light: artifact('index/sitegraph/jwc/artifacts/doc_meta_light.0123456789abcdef.json', 'doc_meta_light', 'initial', 1),
            light_inverted_index: artifact('index/sitegraph/jwc/artifacts/light_inverted_index.0123456789abcdef.json', 'light_inverted_index', 'initial'),
            body_inverted_index: artifact('index/sitegraph/jwc/artifacts/body_inverted_index.0123456789abcdef.json', 'body_inverted_index', 'deep_search'),
            section_index: artifact('index/sitegraph/jwc/artifacts/section_index.0123456789abcdef.json', 'section_index', 'on_demand'),
            attachment_index: artifact('index/sitegraph/jwc/artifacts/attachment_index.0123456789abcdef.json', 'attachment_index', 'on_demand', 1),
            external_index: artifact('index/sitegraph/jwc/artifacts/external_index.0123456789abcdef.json', 'external_index', 'on_demand', 0),
            query_aliases: artifact('index/sitegraph/jwc/artifacts/query_aliases.0123456789abcdef.json', 'query_aliases', 'initial', 1),
            outcomes: artifact('index/sitegraph/jwc/artifacts/outcomes.0123456789abcdef.json', 'outcomes', 'audit'),
            size_report: artifact('index/sitegraph/jwc/artifacts/size_report.0123456789abcdef.json', 'size_report', 'audit')
        }
    }
};

const fullDocument = {
    doc_index: 0,
    id: 'jwc-detail-1',
    record_type: 'detail' as const,
    page_type: 'detail_article_page',
    facet: 'policy' as const,
    title: '南京邮电大学本科生转专业管理办法',
    url: 'https://jwc.njupt.edu.cn/1/page.htm',
    source: '本科生院 / 教务处',
    source_domain: 'jwc.njupt.edu.cn',
    section_id: 'jwc_rules_root',
    section: '规章制度',
    nav_path: ['规章制度'],
    nav_path_text: '规章制度',
    published_at: '2026-05-20',
    publisher: '综合科',
    summary: '转专业政策摘要',
    attachment_count: 1,
    hash: 'hash',
    tags: ['policy'],
    collection_method: 'search_record',
    provenance: { site_id: 'jwc', section_id: 'jwc_rules_root', nav_path: ['规章制度'], outcome: 'search_record' },
    shard: { shard_id: fullShard.shard_id, path: fullShard.path },
    content: '学生申请转专业需要符合管理办法。',
    attachments: [{
        attachment_id: 'att-1',
        name: '转专业申请表.doc',
        url: 'https://jwc.njupt.edu.cn/a.doc',
        extension: 'doc',
        parent_url: 'https://jwc.njupt.edu.cn/1/page.htm',
        parent_doc_id: 'jwc-detail-1',
        section_id: 'jwc_rules_root',
        section: '规章制度',
        nav_path: ['规章制度'],
        metadata_only: true as const,
        position: 1
    }]
};

describe('sitegraph search contract', () => {
    it('rejects llm_provider=null instead of masking schema errors', () => {
        expect(() => parseSitegraphManifest({ ...manifest, llm_provider: null })).toThrow(/unrecognized|llm_provider|Validation/);
    });

    it('rejects old semantic fields in doc meta', () => {
        const { content: _content, summary: _summary, attachments: _attachments, provenance: _provenance, ...docMeta } = fullDocument;
        expect(() => parseSitegraphDocMeta([{ ...docMeta, semantic_mode: 'sitegraph_rule' }], 'fixture')).toThrow();
        expect(() => parseSitegraphDocMeta([{ ...docMeta, content: 'must stay in body index' }], 'fixture')).toThrow(/doc_meta_light/);
    });

    it('ranks title and attachment matches after loading only candidate shard', async () => {
        const { content: _content, summary: _summary, attachments: _attachments, provenance: _provenance, page_type: _pageType, source_domain: _sourceDomain, publisher: _publisher, hash: _hash, tags: _tags, ...docMeta } = fullDocument;
        const bundle: SitegraphIndexBundle = {
            manifest,
            docMeta: [docMeta],
            lightInvertedIndex: {
                version: 'sitegraph-light-inverted-v2',
                tokenizer: 'test',
                field_codes: { title: 't', attachment: 'a' },
                tokens: {
                    转专业: { t: [0], a: [0] },
                    申请表: { a: [0] }
                }
            },
            queryAliases: { 转专业: { aliases: ['专业变更'] } }
        };
        const originalFetch = globalThis.fetch;
        globalThis.fetch = (async () => new Response(JSON.stringify([fullDocument]))) as typeof fetch;
        try {
            const { results, stats } = await recallSitegraphDocuments(bundle, '转专业申请表', new AbortController().signal);
            expect(results[0]?.id).toBe('jwc-detail-1');
            expect(results[0]?.score_reason).toContain('附件名命中');
            expect(stats.loadedShardCount).toBe(1);
            expect(stats.loadedShardPaths).toEqual([fullShard.path]);
        } finally {
            globalThis.fetch = originalFetch;
        }
    });
});
