import { z } from 'zod';

export interface Exam {
    id: string; // Generated unique id (filename-row)
    class_name: string; // e.g., "B250403"
    course_name: string; // e.g., "大学物理"
    location: string; // e.g., "教2-201"

    // Parsed time fields (from Python script)
    // NOTE: Timestamps might be null if parsing failed, but the record is still preserved.
    start_timestamp: string | null; // ISO string or null
    end_timestamp: string | null; // ISO string or null
    duration_minutes: number; // Exam duration in minutes

    // Optional fields
    teacher?: string;
    notes?: string;
    campus?: string;
    course_code?: string;
    count?: number; // Number of students
    raw_time?: string; // Original time string from Excel

    // Additional fields from Excel (optional, may not be in all files)
    school?: string; // 开课学院
    student_school?: string; // 学生所在学院
    major?: string; // 专业名称
    grade?: string; // 年级
    date?: string; // Parsed date string (YYYY-MM-DD)
    parse_error?: string | null; // Time parsing error message (if any)
}

export interface Manifest {
    generated_at: string; // ISO string
    files_processed: string[]; // List of processed Excel files
    total_records: number; // From Python script
    source_url?: string; // Original URL of the exam schedule
    source_title?: string; // Title of the news article
}

export const clamp01 = (value: number): number => {
    if (!Number.isFinite(value)) return 0;
    return Math.min(1, Math.max(0, value));
};

export const SearchDocumentKindSchema = z.enum(['notice', 'exam', 'resource']).catch('notice');
export type SearchDocumentKind = z.infer<typeof SearchDocumentKindSchema>;

export const SearchCategorySchema = z.enum([
    '考试', '选课', '竞赛', '奖助', '就业', '讲座', '生活', '学院', '研究生', '项目', '资料', '公告'
]).catch('公告');
export type SearchCategory = z.infer<typeof SearchCategorySchema>;

export const SearchDomainSchema = z.enum([
    'academic', 'exam', 'course', 'degree', 'scholarship', 'employment', 'competition',
    'project', 'international', 'life', 'library', 'security', 'logistics', 'lecture',
    'research', 'resource', 'news', 'policy'
]).catch('news');
export type SearchDomain = z.infer<typeof SearchDomainSchema>;

export const SearchIntentSchema = z.enum([
    'apply', 'register', 'submit', 'attend', 'check_result', 'publicity', 'download',
    'read', 'schedule', 'alert'
]).catch('read');
export type SearchIntent = z.infer<typeof SearchIntentSchema>;

export const SearchSourceTypeSchema = z.enum([
    'central_admin', 'central_notice', 'central_news', 'college', 'service_unit',
    'job_platform', 'github_resource', 'research_admin', 'policy', 'exam_vertical'
]).catch('central_admin');
export type SearchSourceType = z.infer<typeof SearchSourceTypeSchema>;

export const SearchLifecycleSchema = z.enum(['active', 'upcoming', 'expired', 'evergreen', 'unknown']).catch('unknown');
export type SearchLifecycle = z.infer<typeof SearchLifecycleSchema>;

export const SearchAttachmentSchema = z.object({
    name: z.string(),
    url: z.string(),
    type: z.string().optional(),
    role: z.string().nullable().optional(),
    description: z.string().nullable().optional(),
    sensitive: z.boolean().optional().default(false)
});
export type SearchAttachment = z.infer<typeof SearchAttachmentSchema>;

export const SearchDocumentLLMSchema = z.object({
    used: z.boolean().optional(),
    provider: z.string().nullable().optional(),
    model: z.string().nullable().optional(),
    prompt_version: z.string().optional(),
    confidence: z.number().nullable().optional(),
    review_required: z.boolean().optional()
}).passthrough();
export type SearchDocumentLLMMetadata = z.infer<typeof SearchDocumentLLMSchema>;

export const SearchDocumentSchema = z.object({
    id: z.string().min(1),
    kind: SearchDocumentKindSchema,
    status: z.string().optional(),
    title: z.string().min(1),
    url: z.string().min(1),
    source: z.string().min(1),
    source_domain: z.string().min(1),
    source_type: SearchSourceTypeSchema,
    category: SearchCategorySchema,
    domain: SearchDomainSchema,
    intent: SearchIntentSchema,
    lifecycle: SearchLifecycleSchema,
    evidence: z.array(z.string()).optional().default([]),
    confidence: z.number().nullable().optional(),
    sub_category: z.string().nullable().optional(),
    deadline: z.string().nullable().optional(),
    action_required: z.boolean().optional().default(false),
    action_type: z.string().nullable().optional(),
    action_summary: z.string().nullable().optional(),
    required_materials: z.array(z.string()).optional().default([]),
    sensitive: z.boolean().optional().default(false),
    sensitive_types: z.array(z.string()).optional().default([]),
    review_required: z.boolean().optional().default(false),
    risk_flags: z.array(z.string()).optional().default([]),
    audience: z.array(z.string()),
    published_at: z.string().nullable().optional(),
    content: z.string().min(1),
    summary: z.string().optional(),
    attachments: z.array(SearchAttachmentSchema).default([]),
    student_score: z.number().transform(clamp01),
    freshness_score: z.number().transform(clamp01),
    importance_score: z.number().transform(clamp01),
    source_weight: z.number().transform(clamp01).optional(),
    tags: z.array(z.string()),
    hash: z.string().min(1),
    cache_key: z.string().optional(),
    llm_schema_version: z.string().optional(),
    llm: SearchDocumentLLMSchema.optional(),
    class_name: z.string().optional(),
    exam_id: z.string().optional()
}).passthrough();
export type SearchDocument = z.infer<typeof SearchDocumentSchema>;

export interface RankedSearchDocument extends SearchDocument {
    score: number;
    score_reason: string;
}

export const SearchManifestSourceSchema = z.object({
    id: z.string().min(1),
    name: z.string().min(1),
    domain: z.string().min(1),
    source_type: z.enum([
        'central_admin', 'central_notice', 'central_news', 'college', 'service_unit',
        'job_platform', 'github_resource', 'research_admin', 'policy', 'exam_vertical'
    ]).optional(),
    priority: z.number().optional(),
    candidates: z.number().optional(),
    filtered_out: z.number().optional(),
    status: z.enum(['ok', 'error']).catch('error'),
    documents: z.number(),
    last_fetch_at: z.string().nullable().optional(),
    error: z.string().optional()
}).passthrough();
export type SearchManifestSource = z.infer<typeof SearchManifestSourceSchema>;

export const SearchManifestSchema = z.object({
    generated_at: z.string().min(1),
    total_documents: z.number(),
    strategy: z.string().min(1),
    llm_schema_version: z.string().optional(),
    llm_enabled: z.boolean().optional(),
    llm_provider: z.string().optional(),
    llm_model: z.string().nullable().optional(),
    llm_batch_size: z.number().optional(),
    llm_batch_max_chars: z.number().optional(),
    llm_batch_max_output_tokens: z.number().optional(),
    sources: z.array(SearchManifestSourceSchema)
}).passthrough();
export type SearchManifest = z.infer<typeof SearchManifestSchema>;

export type SearchMode = 'EMPTY' | 'NOT_FOUND' | 'LIST' | 'DETAIL';

export interface SearchResult {
    mode: SearchMode;
    classes: string[];
    exams: Exam[];
}
