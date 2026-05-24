import {
    Exam,
    RankedSearchDocument,
    SearchDocument,
    SearchDomain,
    SearchIntent,
    SearchLifecycle,
    SearchManifest,
    SearchSourceType,
    SearchDocumentSchema,
    SearchManifestSchema
} from '@/types';
import { z } from 'zod';

class SearchContractError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SearchContractError';
    }
}

const DOMAIN_LABELS: Record<SearchDomain, string> = {
    academic: '学业事务',
    exam: '考试',
    course: '课程选课',
    degree: '学位培养',
    scholarship: '资助评优',
    employment: '就业实习',
    competition: '竞赛活动',
    project: '项目机会',
    innovation_project: '大创项目',
    international: '国际交流',
    life: '校园生活',
    library: '图书馆',
    security: '安全保卫',
    logistics: '后勤服务',
    campus_network: '校园网络',
    subsidy: '资助补助',
    medical_insurance: '医保体检',
    archive: '档案服务',
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
    alert: '提醒',
    pay: '缴费',
    contact: '联系',
    export: '导出'
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



const daysFromNow = (dateLike: string | null | undefined): number | null => {
    if (!dateLike) return null;
    const date = new Date(dateLike);
    if (Number.isNaN(date.getTime())) return null;
    return (Date.now() - date.getTime()) / 86_400_000;
};

const calculateFreshness = (dateLike: string | null | undefined): number => {
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

const dateSortValue = (dateLike: string | null | undefined): number => {
    if (!dateLike) return 0;
    const date = new Date(dateLike);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
};

const overlapScore = (query: string, text: string): number => {
    const queryTokens = new Set(tokenize(query).map(normalize).filter(Boolean));
    if (queryTokens.size === 0) return 0;
    const candidate = normalize(text);
    let hits = 0;
    for (const token of queryTokens) {
        if (candidate.includes(token)) hits += 1;
    }
    return hits / queryTokens.size;
};

const scoreHybridTerms = (terms: Record<string, number>, query: string): number => {
    const tokens = tokenize(query).map(normalize).filter(Boolean);
    if (tokens.length === 0) return 0;
    let score = 0;
    for (const token of tokens) {
        score += Number(terms[token] || 0);
    }
    return Math.min(1, score / Math.max(12, tokens.length * 3));
};

const scoreHybridFields = (fields: Record<string, string>, query: string): number => {
    const weights: Record<string, number> = {
        title: 4,
        tags: 3,
        'task.what': 3,
        'task.action.summary': 2.8,
        evidence: 2.5,
        'materials.name': 2,
        source: 1.5,
        content: 1,
    };
    let score = 0;
    let maxScore = 0;
    for (const [field, value] of Object.entries(fields)) {
        const weight = weights[field] ?? 1;
        maxScore += weight;
        score += weight * overlapScore(query, String(value));
    }
    return maxScore > 0 ? Math.min(1, score / maxScore) : 0;
};

type QueryAliasPayload = {
    aliases?: unknown[];
    domains?: unknown[];
    intents?: unknown[];
};

const aliasPayloadsForQuery = (query: string, queryAliases: Record<string, unknown>): QueryAliasPayload[] => {
    const normalizedQuery = normalize(query);
    const payloads: QueryAliasPayload[] = [];
    for (const [key, rawPayload] of Object.entries(queryAliases)) {
        const payload = rawPayload as QueryAliasPayload;
        const aliases = Array.isArray(payload.aliases) ? payload.aliases.map(String) : [];
        const candidates = [key, ...aliases];
        if (candidates.some(candidate => normalize(candidate) && normalizedQuery.includes(normalize(candidate)))) {
            payloads.push(payload);
        }
    }
    return payloads;
};

const aliasTermsFromPayloads = (payloads: QueryAliasPayload[]): string[] => {
    const terms: string[] = [];
    for (const payload of payloads) {
        if (Array.isArray(payload.aliases)) {
            terms.push(...payload.aliases.map(String));
        }
    }
    return Array.from(new Set(terms.filter(Boolean)));
};

const targetDomainsFromPayloads = (payloads: QueryAliasPayload[]): Set<string> => {
    const domains: string[] = [];
    for (const payload of payloads) {
        if (Array.isArray(payload.domains)) {
            domains.push(...payload.domains.map(String));
        }
    }
    return new Set(domains.map(normalize).filter(Boolean));
};

const scoreTextMatch = (document: SearchDocument, query: string, expandedTerms: string[] = []): number => {
    const tokens = tokenize([query, ...expandedTerms].join(' '));
    if (tokens.length === 0) return 0;

    const title = normalize(document.title);
    const content = normalize(document.content);
    const channel = normalize(document.channel);
    const source = normalize(document.source);
    const domain = normalize(DOMAIN_LABELS[document.domain] || document.domain);
    const intent = normalize(INTENT_LABELS[document.intent] || document.intent);
    const sourceType = normalize(SOURCE_TYPE_LABELS[document.source_type] || document.source_type);
    const tags = normalize(document.tags.join(' '));
    const evidence = normalize((document.evidence || []).join(' '));
    const className = normalize(document.class_name || '');
    const taskText = normalize(document.task_frames.map(frame => [
        frame.what,
        frame.action.summary,
        frame.action.verb,
        frame.time.deadline,
        ...frame.materials.map(material => material.name),
        ...frame.evidence.map(item => item.text)
    ].filter(Boolean).join(' ')).join(' '));

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
        if (channel.includes(normalizedToken)) score += 3;
        if (source.includes(normalizedToken)) score += 3;
        if (evidence.includes(normalizedToken)) score += 2;
        if (taskText.includes(normalizedToken)) score += 5;
        if (content.includes(normalizedToken)) score += 1.5;
        if (className.includes(normalizedToken)) score += 8;
    }

    return score;
};

const buildScoreReason = (document: SearchDocument): string => {
    const parts = [
        DOMAIN_LABELS[document.domain] || document.domain,
        INTENT_LABELS[document.intent] || document.intent,
        document.channel
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
        read: 0.9,
        pay: 1.05,
        contact: 0.96,
        export: 0.98
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
        github_resource: 0.9,
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
            source_id: 'exam_vertical',
            channel_id: 'exam_schedule',
            channel: '考试安排',
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
            sub_category: null,
            deadline: null,
            action_required: false,
            action_type: null,
            action_summary: null,
            required_materials: [],
            sensitive: false,
            sensitive_types: [],
            review_required: false,
            risk_flags: [],
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
            canonical: {
                doc_id: `exam-${exam.id}`,
                canonical_url: `?class=${encodeURIComponent(exam.class_name)}`,
                content_hash: exam.id,
                dedupe_key: `exam-${exam.id}`
            },
            rule_guard: {
                restricted: false,
                sensitive: false,
                low_evidence: false,
                duplicate: false,
                expired: false,
                evergreen: false,
                risk_flags: [],
                allow_llm: false,
                allow_full_text_display: true,
                review_required: false
            },
            task_frames: [{
                task_id: `task-exam-${exam.id}`,
                doc_id: `exam-${exam.id}`,
                task_type: 'schedule',
                who: { audience: ['本科生'], college: [], grade: exam.grade ? [exam.grade] : [], major: exam.major ? [exam.major] : [], class_name: [exam.class_name] },
                what: `${exam.course_name} 考试安排`,
                action: { required: false, verb: '查看', object: '考试时间地点', summary: `${exam.raw_time || '时间待确认'} · ${exam.location || '地点待确认'}` },
                time: { published_at: exam.date || exam.start_timestamp, deadline: exam.start_timestamp, lifecycle: 'active', urgency_days: null },
                materials: [],
                location: { place: exam.location || null, online: null, contact: exam.teacher || null },
                source: { source_id: 'exam_vertical', channel_id: 'exam_schedule', authority: 1, official: true },
                evidence: [{ field: 'schedule', text: exam.raw_time || exam.location || title }],
                risk: { sensitive: false, restricted: false, low_evidence: false, review_required: false },
                confidence: exam.parse_error ? 0.6 : 0.98
            }],
            class_name: exam.class_name,
            exam_id: exam.id
        };
    });
};

export const rankSearchDocuments = (
    documents: SearchDocument[],
    query: string,
    hybridIndex: Record<string, unknown> | null = null,
    queryAliases: Record<string, unknown> = {}
): RankedSearchDocument[] => {
    const trimmed = query.trim();

    if (trimmed.length < 2) {
        return [...documents]
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

    const aliasPayloads = aliasPayloadsForQuery(trimmed, queryAliases);
    const expandedTerms = aliasTermsFromPayloads(aliasPayloads);
    const targetDomains = targetDomainsFromPayloads(aliasPayloads);
    const hybridDocuments = (hybridIndex?.documents || {}) as Record<string, { terms?: Record<string, number>, fields?: Record<string, string> }>;

    return documents
        .map(document => {
            const textScore = scoreTextMatch(document, trimmed, expandedTerms);
            const hybridPayload = hybridDocuments[document.id];
            const bm25Proxy = hybridPayload?.terms ? scoreHybridTerms(hybridPayload.terms, [trimmed, ...expandedTerms].join(' ')) : textScore / 24;
            const fieldScore = hybridPayload?.fields ? scoreHybridFields(hybridPayload.fields, [trimmed, ...expandedTerms].join(' ')) : Math.min(1, textScore / 24);
            const tagScore = overlapScore([trimmed, ...expandedTerms].join(' '), document.tags.join(' '));
            const taskFrameScore = document.task_frames.length > 0 ? overlapScore(
                [trimmed, ...expandedTerms].join(' '),
                document.task_frames.map(frame => `${frame.what} ${frame.action.summary || ''} ${frame.evidence.map(item => item.text).join(' ')}`).join(' ')
            ) : 0;
            const sourceWeight = document.source_weight ?? 0.8;
            const utilityScore =
                (0.42 * document.student_score) +
                (0.3 * document.importance_score) +
                (0.2 * sourceWeight) +
                (document.task_frames.length > 0 ? 0.08 : 0);
            const riskPenalty = (document.sensitive ? 0.5 : 0) + (document.review_required ? 0.25 : 0) + (document.status === 'restricted' ? 0.5 : 0);
            const domainMatched = targetDomains.has(normalize(document.domain));
            const officialDomainBoost = domainMatched && document.source_type !== 'github_resource' ? 1.24 : 1;
            const resourceDomainPenalty = targetDomains.size > 0 && !domainMatched && document.source_type === 'github_resource' ? 0.76 : 1;

            const rawMatchScore =
                0.26 * Math.min(1, bm25Proxy) +
                0.22 * fieldScore +
                0.15 * tagScore +
                0.1 * Math.max(Number(document.domain.includes(trimmed) || document.intent.includes(trimmed)), overlapScore(trimmed, document.source)) +
                0.12 * Math.max(taskFrameScore, overlapScore(expandedTerms.join(' '), document.content));

            const hasMatch = textScore > 0 || rawMatchScore > 0;
            
            const hybridScore = hasMatch 
                ? rawMatchScore + 0.2 * Math.min(1, utilityScore) - 0.05 * Math.min(1, riskPenalty)
                : 0;

            const weightedScore = hasMatch ? (textScore + hybridScore * 32) *
                (0.55 + document.student_score * 0.45) *
                (0.72 + document.freshness_score * 0.28) *
                (0.7 + document.importance_score * 0.3) *
                (0.78 + sourceWeight * 0.22) *
                intentWeight(document.intent) *
                lifecycleWeight(document.lifecycle) *
                sourceTypeWeight(document.source_type) *
                deadlineUrgencyWeight(document.deadline) *
                officialDomainBoost *
                resourceDomainPenalty *
                (document.sensitive ? 0.92 : 1) : 0;

            return {
                ...document,
                score: Number(weightedScore.toFixed(4)),
                score_reason: buildScoreReason(document),
                score_components: {
                    bm25: Number(Math.min(1, bm25Proxy).toFixed(4)),
                    field: Number(fieldScore.toFixed(4)),
                    tag: Number(tagScore.toFixed(4)),
                    task_frame: Number(taskFrameScore.toFixed(4)),
                    utility: Number(Math.min(1, utilityScore).toFixed(4)),
                    risk_penalty: Number(Math.min(1, riskPenalty).toFixed(4))
                }
            };
        })
        .filter(document => document.score > 0)
        .sort((a, b) => {
            if (b.score !== a.score) return b.score - a.score;
            return dateSortValue(b.published_at) - dateSortValue(a.published_at);
        });
};

export const getDomainLabel = (domain: SearchDomain): string => DOMAIN_LABELS[domain] || domain;

export const getIntentLabel = (intent: SearchIntent): string => INTENT_LABELS[intent] || intent;

export const getSourceTypeLabel = (sourceType: SearchSourceType): string => SOURCE_TYPE_LABELS[sourceType] || sourceType;

export const getLifecycleLabel = (lifecycle: SearchLifecycle): string => LIFECYCLE_LABELS[lifecycle] || lifecycle;

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

export const formatSearchDate = (dateLike: string | null | undefined): string => {
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
            source_id: 'learning_resource',
            channel_id: 'learning_resource_video',
            channel: '学习资源',
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
            sub_category: null,
            deadline: null,
            action_required: false,
            action_type: null,
            action_summary: null,
            required_materials: [],
            sensitive: false,
            sensitive_types: [],
            review_required: false,
            risk_flags: [],
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
            hash: 'resource-exam-review',
            canonical: {
                doc_id: 'resource-exam-review',
                canonical_url: 'https://space.bilibili.com/1144561698',
                content_hash: 'resource-exam-review',
                dedupe_key: 'resource-exam-review'
            },
            rule_guard: {
                restricted: false,
                sensitive: false,
                low_evidence: false,
                duplicate: false,
                expired: false,
                evergreen: true,
                risk_flags: ['evergreen'],
                allow_llm: false,
                allow_full_text_display: true,
                review_required: false
            },
            task_frames: [{
                task_id: 'task-resource-exam-review',
                doc_id: 'resource-exam-review',
                task_type: 'download',
                who: { audience: ['本科生'], college: [], grade: [], major: [], class_name: [] },
                what: '课程期末复习与习题讲解',
                action: { required: false, verb: '查看', object: '复习资源', summary: '按课程名匹配复习与习题讲解资源。' },
                time: { published_at: null, deadline: null, lifecycle: 'evergreen', urgency_days: null },
                materials: [],
                location: { place: null, online: 'https://space.bilibili.com/1144561698', contact: null },
                source: { source_id: 'learning_resource', channel_id: 'learning_resource_video', authority: 0.68, official: false },
                evidence: [{ field: 'materials', text: '高数 C语言 数据结构 电路 物理 期末 复习 习题 讲解 视频' }],
                risk: { sensitive: false, restricted: false, low_evidence: false, review_required: false },
                confidence: 0.72
            }]
        }
    ];

    return rankSearchDocuments(resources, query);
};
