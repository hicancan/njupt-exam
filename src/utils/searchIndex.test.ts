import { describe, expect, it } from 'vitest';
import {
    parseSitegraphDocMeta,
    parseSitegraphManifest,
    recallSitegraphDocuments
} from './searchIndex';
import { SitegraphIndexBundle, SitegraphSearchManifest } from '@/types';

const manifest: SitegraphSearchManifest = {
    generated_at: '2026-05-27T00:00:00Z',
    strategy: 'pure-sitegraph-code-search-v1',
    site_id: 'jwc',
    source: 'D:/sitegraph',
    total_documents: 1,
    record_counts: { detail: 1 },
    facet_counts: { policy: 1 },
    exam_vertical_preserved: true,
    core_search: {
        algorithm: 'static inverted index plus on-demand full shard ranking',
        llm_in_core_path: false,
        old_hytask_removed: true,
        source_channel_production_enabled: false,
        github_resource_production_enabled: false,
        light_first_screen: true,
        full_text_loading: 'on_demand_by_shard'
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
        full_shards: [{ path: 'fixture-shard.json', count: 1, contains: 'full_documents' }],
        indexes: {
            doc_meta: 'index/doc_meta.json',
            inverted_index: 'index/inverted_index.json',
            section_index: 'index/section_index.json',
            attachment_index: 'index/attachment_index.json',
            external_index: 'index/external_index.json'
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
    provenance: { site_id: 'jwc', section_id: 'jwc_rules_root', nav_path: ['规章制度'], outcome: 'search_record' },
    shard: { path: 'fixture-shard.json', index: 0 },
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
        expect(() => parseSitegraphDocMeta([{ ...fullDocument, semantic_mode: 'sitegraph_rule' }], 'fixture')).toThrow();
    });

    it('ranks title and attachment matches after loading only candidate shard', async () => {
        const bundle: SitegraphIndexBundle = {
            manifest,
            docMeta: [fullDocument],
            invertedIndex: {
                version: 'sitegraph-inverted-v1',
                tokenizer: 'test',
                field_codes: { title: 't', attachment: 'a' },
                tokens: {
                    转专业: { t: [0], a: [0] },
                    申请表: { a: [0] }
                }
            },
            attachmentIndex: fullDocument.attachments,
            externalIndex: [],
            queryAliases: { 转专业: { aliases: ['专业变更'] } }
        };
        const originalFetch = globalThis.fetch;
        globalThis.fetch = (async () => new Response(JSON.stringify([fullDocument]))) as typeof fetch;
        try {
            const results = await recallSitegraphDocuments(bundle, '转专业申请表', new AbortController().signal);
            expect(results[0]?.id).toBe('jwc-detail-1');
            expect(results[0]?.score_reason).toContain('附件名命中');
        } finally {
            globalThis.fetch = originalFetch;
        }
    });
});
