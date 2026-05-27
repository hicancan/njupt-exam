import { z } from 'zod';

export interface Exam {
    id: string;
    class_name: string;
    course_name: string;
    location: string;
    start_timestamp: string | null;
    end_timestamp: string | null;
    duration_minutes: number;
    teacher?: string;
    notes?: string;
    campus?: string;
    course_code?: string;
    count?: number;
    raw_time?: string;
    school?: string;
    student_school?: string;
    major?: string;
    grade?: string;
    date?: string;
    parse_error?: string | null;
}

export interface Manifest {
    generated_at: string;
    files_processed: string[];
    total_records: number;
    source_url?: string;
    source_title?: string;
}

export const SitegraphRecordTypeSchema = z.enum(['detail', 'attachment', 'external', 'utility']);
export type SitegraphRecordType = z.infer<typeof SitegraphRecordTypeSchema>;

export const SitegraphFacetSchema = z.enum([
    'notice_article',
    'policy',
    'workflow',
    'download',
    'system',
    'exam',
    'news',
    'external'
]);
export type SitegraphFacet = z.infer<typeof SitegraphFacetSchema>;

export const SitegraphProvenanceSchema = z.object({
    site_id: z.string(),
    section_id: z.string().nullable().optional(),
    nav_path: z.array(z.string()).default([]),
    source_url: z.string().nullable().optional(),
    outcome: z.string(),
    external_category: z.string().nullable().optional()
}).passthrough();
export type SitegraphProvenance = z.infer<typeof SitegraphProvenanceSchema>;

export const SitegraphShardRefSchema = z.object({
    shard_id: z.string().min(1),
    path: z.string().optional(),
}).passthrough();
export type SitegraphShardRef = z.infer<typeof SitegraphShardRefSchema>;

export const SitegraphDocMetaSchema = z.object({
    doc_index: z.number(),
    id: z.string().min(1),
    record_type: SitegraphRecordTypeSchema,
    facet: SitegraphFacetSchema,
    title: z.string().min(1),
    url: z.string().min(1).optional(),
    source: z.string().min(1).optional(),
    section_id: z.string().nullable().optional(),
    section: z.string().min(1),
    nav_path: z.array(z.string()).default([]),
    nav_path_text: z.string().default(''),
    published_at: z.string().nullable().optional(),
    attachment_count: z.number().default(0).optional(),
    collection_method: z.string().min(1).optional(),
    shard: SitegraphShardRefSchema
}).passthrough();
export type SitegraphDocMeta = z.infer<typeof SitegraphDocMetaSchema>;

export const SitegraphAttachmentSchema = z.object({
    attachment_id: z.string().min(1),
    name: z.string().min(1),
    url: z.string().min(1),
    extension: z.string().nullable().optional(),
    parent_url: z.string().min(1),
    parent_doc_id: z.string().nullable().optional(),
    section_id: z.string().nullable().optional(),
    section: z.string().min(1),
    nav_path: z.array(z.string()).default([]),
    metadata_only: z.literal(true),
    position: z.number().nullable().optional()
}).passthrough();
export type SitegraphAttachment = z.infer<typeof SitegraphAttachmentSchema>;

export const SitegraphFullDocumentSchema = z.object({
    doc_index: z.number(),
    id: z.string().min(1),
    record_type: SitegraphRecordTypeSchema,
    page_type: z.string().min(1),
    facet: SitegraphFacetSchema,
    title: z.string().min(1),
    url: z.string().min(1),
    source: z.string().min(1),
    source_domain: z.string().min(1),
    section_id: z.string().nullable().optional(),
    section: z.string().min(1),
    nav_path: z.array(z.string()).default([]),
    nav_path_text: z.string().default(''),
    published_at: z.string().nullable().optional(),
    publisher: z.string().nullable().optional(),
    summary: z.string().default(''),
    attachment_count: z.number().default(0),
    hash: z.string().min(1),
    tags: z.array(z.string()).default([]),
    collection_method: z.string().min(1),
    provenance: SitegraphProvenanceSchema,
    content: z.string().min(1),
    attachments: z.array(SitegraphAttachmentSchema).default([])
}).passthrough();
export type SitegraphFullDocument = z.infer<typeof SitegraphFullDocumentSchema>;

export interface RankedSitegraphDocument extends SitegraphFullDocument {
    score: number;
    score_reason: string;
    query_stats?: SitegraphQueryStats;
}

export const SitegraphExternalRecordSchema = z.object({
    external_id: z.string().min(1),
    label: z.string().min(1),
    url: z.string().min(1),
    category: z.string().min(1),
    source_url: z.string().nullable().optional(),
    source_section_id: z.string().nullable().optional(),
    document_id: z.string().min(1),
    outcome: z.string().min(1)
}).passthrough();
export type SitegraphExternalRecord = z.infer<typeof SitegraphExternalRecordSchema>;

export const SitegraphInvertedPostingSchema = z.record(z.string(), z.array(z.number()));
export const SitegraphInvertedIndexSchema = z.object({
    version: z.string().min(1),
    tokenizer: z.string().min(1),
    field_codes: z.record(z.string(), z.string()),
    tokens: z.record(z.string(), SitegraphInvertedPostingSchema)
}).passthrough();
export type SitegraphInvertedIndex = z.infer<typeof SitegraphInvertedIndexSchema>;

export const SitegraphArtifactSchema = z.object({
    path: z.string().min(1),
    sha256: z.string().min(16),
    bytes: z.number(),
    role: z.string().min(1),
    load: z.string().min(1),
    count: z.number().optional()
}).passthrough();
export type SitegraphArtifact = z.infer<typeof SitegraphArtifactSchema>;

export const SitegraphFullShardSchema = z.object({
    shard_id: z.string().min(1),
    path: z.string().min(1),
    sha256: z.string().min(16),
    bytes: z.number(),
    count: z.number(),
    contains: z.literal('full_documents'),
    facet_range: z.array(z.string()),
    record_type_range: z.array(z.string()),
    section_range: z.array(z.string()),
    year_range: z.array(z.string()),
    hash_bucket: z.string().min(1)
}).passthrough();
export type SitegraphFullShard = z.infer<typeof SitegraphFullShardSchema>;

export const SitegraphSearchManifestSchema = z.object({
    generated_at: z.string().min(1),
    strategy: z.literal('progressive-verifiable-static-search'),
    producer_repo: z.string().min(1),
    producer_ref: z.string().min(1),
    site_id: z.literal('jwc'),
    artifact_path: z.string().min(1),
    upstream_generated_at: z.string().min(1),
    truth_counts: z.record(z.string(), z.number()),
    total_documents: z.number(),
    record_counts: z.record(z.string(), z.number()),
    facet_counts: z.record(z.string(), z.number()),
    exam_vertical_preserved: z.literal(true),
    core_search: z.object({
        algorithm: z.string().min(1),
        execution_model: z.literal('pure_frontend_worker'),
        light_first_screen: z.literal(true),
        first_screen_artifacts: z.tuple([
            z.literal('doc_meta_light'),
            z.literal('light_inverted_index'),
            z.literal('query_aliases')
        ]),
        body_index_loading: z.literal('on_deep_search'),
        full_text_loading: z.literal('progressive_candidate_hydration_then_exhaustive_full_scan'),
        search_worker: z.literal(true)
    }).passthrough(),
    progressive_search: z.object({
        total_shards: z.number(),
        total_documents: z.number(),
        full_scan_supported: z.literal(true),
        progressive_events: z.literal(true),
        artifact_roles: z.array(z.string())
    }).passthrough(),
    coverage_contract: z.object({
        coverage_fields: z.array(z.string()),
        proof: z.object({
            indexed_fields: z.array(z.string()),
            full_scan_fields: z.array(z.string())
        }).passthrough(),
        total_shards: z.number(),
        total_documents: z.number()
    }).passthrough(),
    verification_contract: z.object({
        shard_filter_supported: z.literal(true),
        proved_skip_supported: z.literal(true),
        scan_fallback_supported: z.literal(true),
        filter_artifact: z.literal('shard_filter'),
        catalog_artifact: z.literal('shard_catalog')
    }).passthrough(),
    artifacts: z.object({
        doc_meta_light: SitegraphArtifactSchema,
        light_inverted_index: SitegraphArtifactSchema,
        body_inverted_index: SitegraphArtifactSchema,
        section_index: SitegraphArtifactSchema,
        attachment_index: SitegraphArtifactSchema,
        external_index: SitegraphArtifactSchema,
        query_aliases: SitegraphArtifactSchema,
        shard_catalog: SitegraphArtifactSchema,
        shard_filter: SitegraphArtifactSchema,
        outcomes: SitegraphArtifactSchema,
        size_report: SitegraphArtifactSchema
    }).passthrough(),
    sitegraph: z.object({
        truth_counts: z.record(z.string(), z.number()),
        quality: z.record(z.string(), z.unknown()),
        upstream_generated_at: z.string().nullable().optional(),
        detail_page_records: z.number(),
        attachment_metadata_records: z.number(),
        direct_attachment_records: z.number(),
        external_link_records: z.number(),
        external_document_records: z.number(),
        utility_link_records: z.number(),
        attachment_policy: z.literal('metadata_only'),
        external_link_policy: z.literal('record_only'),
        full_shards: z.array(SitegraphFullShardSchema),
        shard_strategy: z.object({
            version: z.string().min(1),
            dimensions: z.array(z.string()),
            hash_bucket_count: z.number(),
            sequential_fixed_size_shards: z.literal(false)
        }).passthrough(),
        indexes: z.record(z.string(), SitegraphArtifactSchema)
    }).passthrough()
}).passthrough();
export type SitegraphSearchManifest = z.infer<typeof SitegraphSearchManifestSchema>;

export interface SitegraphIndexBundle {
    manifest: SitegraphSearchManifest;
    docMeta: SitegraphDocMeta[];
    lightInvertedIndex: SitegraphInvertedIndex;
    bodyInvertedIndex?: SitegraphInvertedIndex;
    shardFilter?: Record<string, {
        bitset_base64: string;
        bit_count: number;
        hash_count: number;
        token_count: number;
        sha256: string;
        hash_algorithm: string;
    }>;
    queryAliases: Record<string, unknown>;
}

export type SitegraphSearchPhase =
    | 'quick_started'
    | 'quick_results'
    | 'body_started'
    | 'body_results'
    | 'hydrate_started'
    | 'hydrate_results'
    | 'verify_started'
    | 'verify_progress'
    | 'verify_results'
    | 'exhaustive_complete'
    | 'cancelled'
    | 'error';

export interface SitegraphSearchCoverage {
    phase: SitegraphSearchPhase;
    searched_fields: string[];
    proved_no_match_shards: number;
    scanned_shards: number;
    total_shards: number;
    searched_documents: number;
    total_documents: number;
    loaded_bytes: number;
    used_body_index: boolean;
    exhaustive_complete: boolean;
}

export interface SitegraphQueryStats {
    phase: SitegraphSearchPhase;
    coverage: SitegraphSearchCoverage;
    usedBodyIndex: boolean;
    loadedShardCount: number;
    loadedShardPaths: string[];
    candidateCount: number;
    exhaustiveComplete: boolean;
    resultCount: number;
}

export interface SitegraphSearchEvent {
    type: SitegraphSearchPhase;
    query: string;
    coverage: SitegraphSearchCoverage;
    results?: RankedSitegraphDocument[];
    stats?: SitegraphQueryStats;
    message?: string;
}

export interface SearchWorkerHandle {
    worker: Worker;
}

export type SearchMode = 'EMPTY' | 'NOT_FOUND' | 'LIST' | 'DETAIL';

export interface SearchResult {
    mode: SearchMode;
    classes: string[];
    exams: Exam[];
}
