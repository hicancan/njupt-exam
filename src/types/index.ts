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
    path: z.string(),
    index: z.number()
}).passthrough();
export type SitegraphShardRef = z.infer<typeof SitegraphShardRefSchema>;

export const SitegraphDocMetaSchema = z.object({
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
    provenance: SitegraphProvenanceSchema,
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

export const SitegraphFullDocumentSchema = SitegraphDocMetaSchema.extend({
    content: z.string().min(1),
    attachments: z.array(SitegraphAttachmentSchema).default([])
}).passthrough();
export type SitegraphFullDocument = z.infer<typeof SitegraphFullDocumentSchema>;

export interface RankedSitegraphDocument extends SitegraphFullDocument {
    score: number;
    score_reason: string;
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

export const SitegraphSearchManifestSchema = z.object({
    generated_at: z.string().min(1),
    strategy: z.literal('pure-sitegraph-code-search-v1'),
    site_id: z.literal('jwc'),
    source: z.string().min(1),
    total_documents: z.number(),
    record_counts: z.record(z.string(), z.number()),
    facet_counts: z.record(z.string(), z.number()),
    exam_vertical_preserved: z.literal(true),
    core_search: z.object({
        algorithm: z.string().min(1),
        llm_in_core_path: z.literal(false),
        old_hytask_removed: z.literal(true),
        source_channel_production_enabled: z.literal(false),
        github_resource_production_enabled: z.literal(false),
        light_first_screen: z.literal(true),
        full_text_loading: z.literal('on_demand_by_shard')
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
        full_shards: z.array(z.object({
            path: z.string().min(1),
            count: z.number(),
            contains: z.literal('full_documents')
        }).passthrough()),
        indexes: z.record(z.string(), z.string())
    }).passthrough()
}).passthrough();
export type SitegraphSearchManifest = z.infer<typeof SitegraphSearchManifestSchema>;

export interface SitegraphIndexBundle {
    manifest: SitegraphSearchManifest;
    docMeta: SitegraphDocMeta[];
    invertedIndex: SitegraphInvertedIndex;
    attachmentIndex: SitegraphAttachment[];
    externalIndex: SitegraphExternalRecord[];
    queryAliases: Record<string, unknown>;
}

export type SearchMode = 'EMPTY' | 'NOT_FOUND' | 'LIST' | 'DETAIL';

export interface SearchResult {
    mode: SearchMode;
    classes: string[];
    exams: Exam[];
}
