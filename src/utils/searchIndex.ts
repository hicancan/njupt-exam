import { z } from 'zod';
import {
    Exam,
    RankedSearchDocument,
    SearchCategory,
    SearchDocument,
    SearchDomain,
    SearchIntent,
    SearchLifecycle,
    SearchManifest,
    SearchSourceType
} from '@/types';

class SearchContractError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SearchContractError';
    }
}

const CATEGORY_ORDER: SearchCategory[] = [
    '考试',
    '竞赛',
    '奖助',
    '就业',
    '讲座',
    '生活',
    '研究生',
    '选课',
    '学院',
    '项目',
    '资料',
    '公告'
];

const DOMAIN_LABELS: Record<SearchDomain, string> = {
    academic: '学业事务',
    exam: '考试',
    course: '课程选课',
    degree: '学位培养',
    scholarship: '奖助评优',
    employment: '就业实习',
    competition: '竞赛',
    project: '项目机会',
    international: '国际交流',
    life: '校园生活',
    library: '图书馆',
    security: '安全保卫',
    logistics: '后勤服务',
    lecture: '讲座活动',
    research: '科研事务',
    resource: '学习资料',
    news: '校园新闻',
    policy: '政策制度'
};

const INTENT_LABELS: Record<SearchIntent, string> = {
    apply: '申请',
    register: '报名',
    submit: '提交',
    attend: '参加',
    check_result: '查结果',
    publicity: '公示',
    download: '下载',
    read: '阅读',
    schedule: '安排',
    alert: '提醒'
};

const SOURCE_TYPE_LABELS: Record<SearchSourceType, string> = {
    central_admin: '校级部门',
    central_notice: '校级通知',
    central_news: '校园新闻',
    college: '学院站',
    service_unit: '服务单位',
    job_platform: '就业平台',
    github_resource: '资料仓库',
    research_admin: '科研管理',
    policy: '信息公开',
    exam_vertical: '考试频道'
};

const LIFECYCLE_LABELS: Record<SearchLifecycle, string> = {
    active: '进行中',
    upcoming: '即将开始',
    expired: '已过期',
    evergreen: '长期有效',
    unknown: '时效未知'
};

const RESOURCE_INTENT_KEYWORDS = [
    '高数',
    '数学',
    '线代',
    '概率',
    '电路',
    '大物',
    '物理',
    'c语言',
    'C语言',
    '数据结构',
    '算法',
    '实验',
    '复习',
    '题',
    '考试',
    '项目',
    '竞赛'
];



const clamp01 = (value: number): number => {
    if (!Number.isFinite(value)) return 0;
    return Math.min(1, Math.max(0, value));
};

const normalize = (value: string): string => {
    return value.toLowerCase().replace(/\s+/g, '');
};

const tokenize = (query: string): string[] => {
    const normalized = query.trim();
    if (!normalized) return [];

    const parts = normalized
        .split(/[\s,，、/|]+/)
        .map(part => part.trim())
        .filter(Boolean);

    return parts.length > 0 ? parts : [normalized];
};

const SearchAttachmentSchema = z.object({
    name: z.string(),
    url: z.string(),
    type: z.string().optional(),
    role: z.string().nullable().optional(),
    description: z.string().nullable().optional(),
    sensitive: z.boolean().optional().default(false)
});

const SearchDocumentLLMSchema = z.object({
    used: z.boolean().optional(),
    model: z.string().nullable().optional(),
    prompt_version: z.string().optional(),
    confidence: z.number().nullable().optional(),
    review_required: z.boolean().optional()
}).passthrough();

const SearchDocumentSchema = z.object({
    id: z.string().min(1),
    kind: z.enum(['notice', 'exam', 'resource']).catch('notice'),
    status: z.string().optional(),
    title: z.string().min(1),
    url: z.string().min(1),
    source: z.string().min(1),
    source_domain: z.string().min(1),
    source_type: z.enum([
        'central_admin', 'central_notice', 'central_news', 'college', 'service_unit',
        'job_platform', 'github_resource', 'research_admin', 'policy', 'exam_vertical'
    ]).catch('central_admin'),
    category: z.enum([
        '考试', '选课', '竞赛', '奖助', '就业', '讲座', '生活', '学院', '研究生', '项目', '资料', '公告'
    ]).catch('公告'),
    domain: z.enum([
        'academic', 'exam', 'course', 'degree', 'scholarship', 'employment', 'competition',
        'project', 'international', 'life', 'library', 'security', 'logistics', 'lecture',
        'research', 'resource', 'news', 'policy'
    ]).catch('news'),
    intent: z.enum([
        'apply', 'register', 'submit', 'attend', 'check_result', 'publicity', 'download',
        'read', 'schedule', 'alert'
    ]).catch('read'),
    lifecycle: z.enum(['active', 'upcoming', 'expired', 'evergreen', 'unknown']).catch('unknown'),
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

const SearchManifestSourceSchema = z.object({
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

const SearchManifestSchema = z.object({
    generated_at: z.string().min(1),
    total_documents: z.number(),
    strategy: z.string().min(1),
    llm_schema_version: z.string().optional(),
    llm_enabled: z.boolean().optional(),
    sources: z.array(SearchManifestSourceSchema)
}).passthrough();

const daysFromNow = (dateLike: string | null): number | null => {
    if (!dateLike) return null;
    const date = new Date(dateLike);
    if (Number.isNaN(date.getTime())) return null;
    return (Date.now() - date.getTime()) / 86_400_000;
};

const calculateFreshness = (dateLike: string | null): number => {
    const days = daysFromNow(dateLike);
    if (days === null) return 0.45;
    if (days < -120) return 0.66;
    if (days < 0) return 0.95;
    if (days <= 3) return 1;
    if (days <= 7) return 0.92;
    if (days <= 30) return 0.78;
    if (days <= 180) return 0.58;
    return 0.42;
};

const dateSortValue = (dateLike: string | null): number => {
    if (!dateLike) return 0;
    const date = new Date(dateLike);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
};

const scoreTextMatch = (document: SearchDocument, query: string): number => {
    const tokens = tokenize(query);
    if (tokens.length === 0) return 0;

    const title = normalize(document.title);
    const content = normalize(document.content);
    const source = normalize(document.source);
    const domain = normalize(DOMAIN_LABELS[document.domain] || document.domain);
    const intent = normalize(INTENT_LABELS[document.intent] || document.intent);
    const sourceType = normalize(SOURCE_TYPE_LABELS[document.source_type] || document.source_type);
    const tags = normalize(document.tags.join(' '));
    const evidence = normalize((document.evidence || []).join(' '));
    const className = normalize(document.class_name || '');

    let score = 0;
    const normalizedQuery = normalize(query);

    if (title === normalizedQuery) score += 18;
    if (title.includes(normalizedQuery)) score += 12;
    if (className && className === normalizedQuery) score += 16;

    for (const token of tokens) {
        const normalizedToken = normalize(token);
        if (!normalizedToken) continue;
        if (title.includes(normalizedToken)) score += 8;
        if (tags.includes(normalizedToken)) score += 4;
        if (domain.includes(normalizedToken)) score += 4;
        if (intent.includes(normalizedToken)) score += 3;
        if (sourceType.includes(normalizedToken)) score += 2;
        if (source.includes(normalizedToken)) score += 3;
        if (evidence.includes(normalizedToken)) score += 2;
        if (content.includes(normalizedToken)) score += 1.5;
        if (className.includes(normalizedToken)) score += 8;
    }

    return score;
};

const buildScoreReason = (document: SearchDocument): string => {
    const parts = [
        DOMAIN_LABELS[document.domain] || document.category,
        INTENT_LABELS[document.intent] || document.intent
    ];

    if (document.attachments.length > 0) {
        parts.push(`${document.attachments.length} 个附件`);
    }

    return parts.join(' · ');
};

const intentWeight = (intent: SearchIntent): number => {
    const weights: Record<SearchIntent, number> = {
        apply: 1.14,
        register: 1.13,
        submit: 1.12,
        check_result: 1.08,
        publicity: 1.05,
        schedule: 1.06,
        alert: 1.08,
        attend: 1.04,
        download: 0.98,
        read: 0.9
    };
    return weights[intent] ?? 1;
};

const lifecycleWeight = (lifecycle: SearchLifecycle): number => {
    const weights: Record<SearchLifecycle, number> = {
        active: 1.08,
        upcoming: 1.04,
        evergreen: 0.98,
        unknown: 0.96,
        expired: 0.76
    };
    return weights[lifecycle] ?? 1;
};

const sourceTypeWeight = (sourceType: SearchSourceType): number => {
    const weights: Record<SearchSourceType, number> = {
        central_admin: 1.08,
        central_notice: 1.04,
        job_platform: 1.05,
        college: 1.02,
        service_unit: 1,
        github_resource: 0.98,
        central_news: 0.86,
        research_admin: 0.88,
        policy: 0.84,
        exam_vertical: 1.12
    };
    return weights[sourceType] ?? 1;
};

const deadlineUrgencyWeight = (deadline: string | null | undefined): number => {
    if (!deadline) return 1;
    const date = new Date(deadline);
    if (Number.isNaN(date.getTime())) return 1;
    const days = (date.getTime() - Date.now()) / 86_400_000;
    if (days < 0) return 0.82;
    if (days <= 1) return 1.18;
    if (days <= 3) return 1.14;
    if (days <= 7) return 1.08;
    return 1.02;
};

export const parseSearchDocuments = (payload: unknown, source = 'search documents'): SearchDocument[] => {
    try {
        const docs = z.array(SearchDocumentSchema).parse(payload);
        const ids = new Set<string>();
        for (const item of docs) {
            if (ids.has(item.id)) {
                throw new SearchContractError(`${source} contains duplicate id: ${item.id}`);
            }
            ids.add(item.id);
        }
        return docs as unknown as SearchDocument[];
    } catch (e) {
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

export const parseSearchManifest = (payload: unknown, source = 'search manifest'): SearchManifest => {
    try {
        return SearchManifestSchema.parse(payload) as unknown as SearchManifest;
    } catch (e) {
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

export const buildExamDocuments = (exams: Exam[]): SearchDocument[] => {
    return exams.map(exam => {
        const title = `${exam.class_name} ${exam.course_name} 考试安排`;
        const content = [
            exam.class_name,
            exam.course_name,
            exam.course_code,
            exam.teacher,
            exam.location,
            exam.raw_time,
            exam.campus,
            exam.school,
            exam.student_school,
            exam.major,
            exam.grade,
            exam.notes
        ].filter(Boolean).join(' ');

        return {
            id: `exam-${exam.id}`,
            kind: 'exam',
            title,
            url: `?class=${encodeURIComponent(exam.class_name)}`,
            source: '考试垂直频道',
            source_domain: 'jwc.njupt.edu.cn',
            source_type: 'exam_vertical',
            category: '考试',
            domain: 'exam',
            intent: 'schedule',
            lifecycle: 'active',
            evidence: [exam.raw_time || exam.location || title],
            confidence: exam.parse_error ? 0.6 : 0.98,
            audience: ['本科生'],
            published_at: exam.date || exam.start_timestamp,
            content: content || title,
            summary: `${exam.raw_time || '时间待确认'} · ${exam.location || '地点待确认'}`,
            attachments: [],
            student_score: 1,
            freshness_score: calculateFreshness(exam.date || exam.start_timestamp),
            importance_score: 0.94,
            source_weight: 1,
            tags: ['考试', '期末', exam.class_name, exam.course_name, exam.campus || '', exam.major || ''].filter(Boolean),
            hash: exam.id,
            class_name: exam.class_name,
            exam_id: exam.id
        };
    });
};

export const rankSearchDocuments = (
    documents: SearchDocument[],
    query: string,
    category: SearchCategory | '全部'
): RankedSearchDocument[] => {
    const trimmed = query.trim();
    const categoryFiltered = category === '全部'
        ? documents
        : documents.filter(document => document.category === category);

    if (trimmed.length < 2) {
        return [...categoryFiltered]
            .sort((a, b) => {
                const aPriority = a.importance_score * intentWeight(a.intent) * lifecycleWeight(a.lifecycle) * sourceTypeWeight(a.source_type) * deadlineUrgencyWeight(a.deadline);
                const bPriority = b.importance_score * intentWeight(b.intent) * lifecycleWeight(b.lifecycle) * sourceTypeWeight(b.source_type) * deadlineUrgencyWeight(b.deadline);
                if (bPriority !== aPriority) return bPriority - aPriority;
                const dateDelta = dateSortValue(b.published_at) - dateSortValue(a.published_at);
                if (dateDelta !== 0) return dateDelta;
                return b.importance_score - a.importance_score;
            })
            .slice(0, 30)
            .map(document => ({
                ...document,
                score: Number((document.importance_score * intentWeight(document.intent) * lifecycleWeight(document.lifecycle)).toFixed(4)),
                score_reason: buildScoreReason(document)
            }));
    }

    return categoryFiltered
        .map(document => {
            const textScore = scoreTextMatch(document, trimmed);
            const sourceWeight = document.source_weight ?? 0.8;
            const weightedScore = textScore *
                (0.55 + document.student_score * 0.45) *
                (0.72 + document.freshness_score * 0.28) *
                (0.7 + document.importance_score * 0.3) *
                (0.78 + sourceWeight * 0.22) *
                intentWeight(document.intent) *
                lifecycleWeight(document.lifecycle) *
                sourceTypeWeight(document.source_type) *
                deadlineUrgencyWeight(document.deadline) *
                (document.sensitive ? 0.92 : 1);

            return {
                ...document,
                score: Number(weightedScore.toFixed(4)),
                score_reason: buildScoreReason(document)
            };
        })
        .filter(document => document.score > 0)
        .sort((a, b) => {
            if (b.score !== a.score) return b.score - a.score;
            return dateSortValue(b.published_at) - dateSortValue(a.published_at);
        })
        .slice(0, 80);
};

export const getCategoryOrder = (): SearchCategory[] => [...CATEGORY_ORDER];

export const getDomainLabel = (domain: SearchDomain): string => DOMAIN_LABELS[domain] || domain;

export const getIntentLabel = (intent: SearchIntent): string => INTENT_LABELS[intent] || intent;

export const getSourceTypeLabel = (sourceType: SearchSourceType): string => SOURCE_TYPE_LABELS[sourceType] || sourceType;

export const getLifecycleLabel = (lifecycle: SearchLifecycle): string => LIFECYCLE_LABELS[lifecycle] || lifecycle;

export const getCategoryCounts = (documents: SearchDocument[]): Record<SearchCategory, number> => {
    return CATEGORY_ORDER.reduce((accumulator, category) => {
        accumulator[category] = documents.filter(document => document.category === category).length;
        return accumulator;
    }, {} as Record<SearchCategory, number>);
};

export const getRecentDocuments = (documents: SearchDocument[], limit: number): SearchDocument[] => {
    return [...documents]
        .sort((a, b) => dateSortValue(b.published_at) - dateSortValue(a.published_at))
        .slice(0, limit);
};

export const getUpdateStats = (documents: SearchDocument[]) => {
    const noticeDocuments = documents.filter(document => document.kind !== 'exam');
    const today = noticeDocuments.filter(document => {
        const days = daysFromNow(document.published_at);
        return days !== null && days >= 0 && days <= 1;
    }).length;
    const sevenDays = noticeDocuments.filter(document => {
        const days = daysFromNow(document.published_at);
        return days !== null && days >= 0 && days <= 7;
    }).length;

    return { today, sevenDays };
};

export const formatSearchDate = (dateLike: string | null): string => {
    if (!dateLike) return '日期待确认';
    const date = new Date(dateLike);
    if (Number.isNaN(date.getTime())) return dateLike;

    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
};

const NEGATIVE_RESOURCE_KEYWORDS = [
    '报名', '通知', '结果', '名单', '缴费', '公示', '安排', '成绩', '获奖', '选拔', '录取', '审核'
];

export const getLearningResources = (query: string): SearchDocument[] => {
    const normalizedQuery = normalize(query);
    if (normalizedQuery.length < 2) return [];
    
    const hasNegativeIntent = NEGATIVE_RESOURCE_KEYWORDS.some(keyword => normalizedQuery.includes(normalize(keyword)));
    if (hasNegativeIntent) return [];

    const hasResourceIntent = RESOURCE_INTENT_KEYWORDS.some(keyword => normalizedQuery.includes(normalize(keyword)));
    if (!hasResourceIntent) return [];

    const resources: SearchDocument[] = [
        {
            id: 'resource-exam-review',
            kind: 'resource',
            title: '课程期末复习与习题讲解入口',
            url: 'https://space.bilibili.com/1144561698',
            source: 'hicancan 学习资源',
            source_domain: 'space.bilibili.com',
            source_type: 'github_resource',
            category: '资料',
            domain: 'resource',
            intent: 'read',
            lifecycle: 'evergreen',
            evidence: ['高数 C语言 数据结构 电路 物理 期末 复习 习题 讲解 视频'],
            confidence: 0.72,
            audience: ['本科生'],
            published_at: null,
            content: '高数 C语言 数据结构 电路 物理 期末 复习 习题 讲解 视频',
            summary: '按课程名、考试名、实验和题型触发，作为搜索结果后的学习资源推荐。',
            attachments: [],
            student_score: 0.82,
            freshness_score: 0.7,
            importance_score: 0.74,
            source_weight: 0.68,
            tags: ['复习', '习题', '视频', '课程资料'],
            hash: 'resource-exam-review'
        }
    ];

    return rankSearchDocuments(resources, query, '全部');
};
