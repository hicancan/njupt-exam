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
import { routeQuery } from './queryRouter';
import rankingWeightsConfig from '../../config/ranking_weights.json';

class SearchContractError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SearchContractError';
    }
}

const valueAtPath = (payload: unknown, path: PropertyKey[]): unknown => {
    let current = payload;
    for (const part of path) {
        if (current === null || current === undefined) return undefined;
        current = (current as Record<PropertyKey, unknown>)[part];
    }
    return current;
};

const formatZodIssues = (payload: unknown, error: z.ZodError): string => {
    return error.issues.map(issue => {
        const fieldPath = issue.path.join('.') || '<root>';
        const invalidValue = valueAtPath(payload, issue.path);
        return `${fieldPath}: ${issue.message}; value=${JSON.stringify(invalidValue)}`;
    }).join('; ');
};

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

type RankingConfig = {
    weights?: Record<string, number>;
    field_weights?: Record<string, number>;
    text_match_weights?: Record<string, number>;
    intent_weights?: Record<string, number>;
    lifecycle_weights?: Record<string, number>;
    source_type_weights?: Record<string, number>;
    utility_weights?: Record<string, number>;
    risk_penalties?: Record<string, number>;
    tier_multipliers?: Record<string, number>;
    source_boosts?: Record<string, number>;
    deadline_urgency_weights?: Record<string, number>;
};

const RANKING_CONFIG = rankingWeightsConfig as RankingConfig;
const rankWeight = (section: keyof RankingConfig, key: string, fallback: number): number => {
    const value = RANKING_CONFIG[section]?.[key];
    return Number.isFinite(value) ? Number(value) : fallback;
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

const tokenizeHybridText = (text: string): string[] => {
    const matches = text.toLowerCase().match(/[A-Za-z][A-Za-z0-9_+\-.#]*|[0-9]+|[\u4e00-\u9fff]{1,4}/gu) || [];
    const expanded: string[] = [];
    for (const token of matches) {
        expanded.push(token);
        if (/^[\u4e00-\u9fff]{3,4}$/u.test(token)) {
            for (let index = 0; index < token.length - 1; index += 1) {
                expanded.push(token.slice(index, index + 2));
            }
        }
    }
    return expanded.filter(Boolean);
};

const scoreHybridBm25 = (hybridIndex: Record<string, unknown> | null, docId: string, query: string): number => {
    const documents = (hybridIndex?.documents || {}) as Record<string, { terms?: Record<string, number>, length?: number }>;
    const payload = documents[docId];
    if (!payload?.terms) return 0;
    const idf = (hybridIndex?.idf || {}) as Record<string, number>;
    const avgDocLen = Number(hybridIndex?.avg_doc_len || 1) || 1;
    const docLen = Number(payload.length || 1) || 1;
    const k1 = 1.5;
    const b = 0.75;
    let score = 0;
    for (const token of tokenizeHybridText(query)) {
        const tf = Number(payload.terms[token] || 0);
        if (tf <= 0) continue;
        const termIdf = Number(idf[token] || Math.log(1.2));
        score += termIdf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * docLen / avgDocLen));
    }
    return Math.min(1, score / 8);
};

const scoreHybridFields = (fields: Record<string, string>, query: string): number => {
    const weights = RANKING_CONFIG.field_weights || {};
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

    if (title === normalizedQuery) score += rankWeight('text_match_weights', 'exact_title', 18);
    if (title.includes(normalizedQuery)) score += rankWeight('text_match_weights', 'title_contains_query', 12);
    if (className && className === normalizedQuery) score += rankWeight('text_match_weights', 'class_exact', 16);

    for (const token of tokens) {
        const normalizedToken = normalize(token);
        if (!normalizedToken) continue;
        if (title.includes(normalizedToken)) score += rankWeight('text_match_weights', 'title', 8);
        if (tags.includes(normalizedToken)) score += rankWeight('text_match_weights', 'tags', 4);
        if (domain.includes(normalizedToken)) score += rankWeight('text_match_weights', 'domain', 4);
        if (intent.includes(normalizedToken)) score += rankWeight('text_match_weights', 'intent', 3);
        if (sourceType.includes(normalizedToken)) score += rankWeight('text_match_weights', 'source_type', 2);
        if (channel.includes(normalizedToken)) score += rankWeight('text_match_weights', 'channel', 3);
        if (source.includes(normalizedToken)) score += rankWeight('text_match_weights', 'source', 3);
        if (evidence.includes(normalizedToken)) score += rankWeight('text_match_weights', 'evidence', 2);
        if (taskText.includes(normalizedToken)) score += rankWeight('text_match_weights', 'task_text', 5);
        if (content.includes(normalizedToken)) score += rankWeight('text_match_weights', 'content', 1.5);
        if (className.includes(normalizedToken)) score += rankWeight('text_match_weights', 'class_name', 8);
    }

    return score;
};

const buildScoreReason = (document: SearchDocument, components?: Record<string, number>): string => {
    const parts = [
        DOMAIN_LABELS[document.domain] || document.domain,
        INTENT_LABELS[document.intent] || document.intent,
        document.channel
    ];

    if (document.attachments.length > 0) {
        parts.push(`${document.attachments.length}附件`);
    }

    const lead = parts.join('·');
    if (!components) return lead;

    const ranked = Object.entries(components)
        .filter(([, value]) => value > 0.01)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([name, value]) => `${name}:${value.toFixed(2)}`);

    const detail = ranked.join(' / ');
    return detail ? `${lead} · ${detail}` : lead;
};

const intentWeight = (intent: SearchIntent): number => {
    return rankWeight('intent_weights', intent, 1);
};

const lifecycleWeight = (lifecycle: SearchLifecycle): number => {
    return rankWeight('lifecycle_weights', lifecycle, 1);
};

const sourceTypeWeight = (sourceType: SearchSourceType): number => {
    return rankWeight('source_type_weights', sourceType, 1);
};

const deadlineUrgencyWeight = (deadline: string | null | undefined): number => {
    if (!deadline) return 1;
    const date = new Date(deadline);
    if (Number.isNaN(date.getTime())) return 1;
    const days = (date.getTime() - Date.now()) / 86_400_000;
    if (days < 0) return rankWeight('deadline_urgency_weights', 'expired', 0.82);
    if (days <= 1) return rankWeight('deadline_urgency_weights', 'within_1_day', 1.18);
    if (days <= 3) return rankWeight('deadline_urgency_weights', 'within_3_days', 1.14);
    if (days <= 7) return rankWeight('deadline_urgency_weights', 'within_7_days', 1.08);
    return rankWeight('deadline_urgency_weights', 'future', 1.02);
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
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

export const parseSearchManifest = (payload: unknown, source = 'search manifest'): SearchManifest => {
    try {
        return SearchManifestSchema.parse(payload) as unknown as SearchManifest;
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
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
                source_mode: 'exam_structured_data',
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

    const routeObj = routeQuery(trimmed);
    const targetDomains = new Set(routeObj.target_domains);
    const targetIntents = new Set(routeObj.target_intents);
    const blockedDomains = new Set(routeObj.blocked_domains_for_top5);
    const blockedSources = new Set(routeObj.blocked_sources_for_top5);
    const preferredSources = new Set(routeObj.preferred_sources);
    const allowResourceTop5 = routeObj.allow_resource_top5;

    const badResultTerms = routeObj.bad_result_terms || [];
    const mustIncludeTerms = routeObj.must_include_terms_for_top_results || [];
    const allowBlockedFallback = routeObj.allow_blocked_fallback && mustIncludeTerms.length === 0;
    const top1Exact = routeObj.top1_prefer_exact_title || false;

    const hybridDocuments = (hybridIndex?.documents || {}) as Record<string, { terms?: Record<string, number>, fields?: Record<string, string> }>;

    const aliasPayloads = aliasPayloadsForQuery(trimmed, queryAliases);
    const expandedTerms = aliasTermsFromPayloads(aliasPayloads);

    const candidates = documents.map(document => {
        const textScore = scoreTextMatch(document, trimmed, expandedTerms);
        const hybridPayload = hybridDocuments[document.id];
        const queryWithAliases = [trimmed, ...expandedTerms].join(' ');
        const bm25Proxy = hybridPayload?.terms ? scoreHybridBm25(hybridIndex, document.id, queryWithAliases) : textScore / 24;
        const fieldScore = hybridPayload?.fields ? scoreHybridFields(hybridPayload.fields, queryWithAliases) : Math.min(1, textScore / 24);
        const tagScore = overlapScore(queryWithAliases, document.tags.join(' '));
        const taskFrameScore = document.task_frames.length > 0 ? overlapScore(
            queryWithAliases,
            document.task_frames.map(frame => `${frame.what} ${frame.action.summary || ''} ${frame.evidence.map(item => item.text).join(' ')}`).join(' ')
        ) : 0;

        const domain = normalize(document.domain);
        const intent = normalize(document.intent);
        const source = normalize(document.source);
        const sourceId = normalize(document.source_id);
        const title = normalize(document.title);
        const content = normalize(document.content);
        const fullText = title + ' ' + content;

        let isExactTitle = title.includes(normalize(trimmed));

        // class_exam_lookup: also match class_name for "B250403 高数" style queries
        if (!isExactTitle && routeObj.query_type === 'class_exam_lookup' && top1Exact) {
            const docClass = (document.class_name || '').toLowerCase();
            if (docClass) {
                for (const word of trimmed.toLowerCase().split(/\s+/)) {
                    if (word.length >= 7 && docClass.includes(word)) {
                        isExactTitle = true;
                        break;
                    }
                }
            }
        }

        let tier = 'C';
        if (top1Exact && isExactTitle) {
            tier = 'A';
        } else if (targetDomains.has(domain) && targetIntents.has(intent)) {
            tier = 'A';
        } else if (targetDomains.has(domain) || targetIntents.has(intent) || isExactTitle) {
            tier = 'B';
        } else if (targetDomains.size === 0 && targetIntents.size === 0) {
            tier = 'A';
        }

        let isBlocked = false;
        if ((blockedDomains.has(domain) || blockedSources.has(source) || blockedSources.has(sourceId)) && !isExactTitle) {
            isBlocked = true;
        }
        if (!allowResourceTop5 && document.source_type === 'github_resource') isBlocked = true;

        for (const term of badResultTerms) {
            if (fullText.includes(normalize(term))) {
                isBlocked = true;
                break;
            }
        }

        if (mustIncludeTerms.length > 0) {
            let hasAny = false;
            for (const term of mustIncludeTerms) {
                if (fullText.includes(normalize(term))) {
                    hasAny = true;
                    break;
                }
            }
            if (!hasAny) isBlocked = true;
        }

        let tierMultiplier = 1.0;
        if (tier === 'A') tierMultiplier = rankWeight('tier_multipliers', 'A', 2.0);
        else if (tier === 'B') tierMultiplier = rankWeight('tier_multipliers', 'B', 1.2);
        else if (tier === 'C') tierMultiplier = rankWeight('tier_multipliers', 'C', 0.1);

        let sourceBoost = 1.0;
        if (preferredSources.has(source) || preferredSources.has(sourceId)) {
            sourceBoost = rankWeight('source_boosts', 'preferred', 1.25);
            if (routeObj.query_type === 'class_exam_lookup') {
                sourceBoost = rankWeight('source_boosts', 'class_exam_lookup', 10.0);
                tierMultiplier = rankWeight('tier_multipliers', 'A', 2.0);
                tier = 'A';
            }
        }

        const rawMatchScore =
            rankWeight('weights', 'bm25', 0.26) * Math.min(1, bm25Proxy) +
            rankWeight('weights', 'field', 0.22) * fieldScore +
            rankWeight('weights', 'tag', 0.15) * tagScore +
            rankWeight('weights', 'task_frame', 0.15) * Math.max(taskFrameScore, overlapScore(expandedTerms.join(' '), document.content));

        const hasMatch = textScore > 0 || rawMatchScore > 0;

        let utilityScore =
            (rankWeight('utility_weights', 'student_score', 0.42) * document.student_score) +
            (rankWeight('utility_weights', 'importance_score', 0.3) * document.importance_score) +
            (rankWeight('utility_weights', 'source_weight', 0.2) * (document.source_weight ?? 0.8));

        const riskPenalty =
            (document.sensitive ? rankWeight('risk_penalties', 'sensitive', 0.5) : 0) +
            (document.review_required ? rankWeight('risk_penalties', 'review_required', 0.25) : 0) +
            (document.status === 'restricted' ? rankWeight('risk_penalties', 'restricted', 0.5) : 0);
        utilityScore = Math.max(0, utilityScore - riskPenalty);

        const hybridScore = hasMatch
            ? rawMatchScore + rankWeight('utility_weights', 'utility_multiplier', 0.2) * Math.min(1, utilityScore) - rankWeight('weights', 'risk_penalty', 0.05) * Math.min(1, riskPenalty)
            : 0;

        let weightedScore = hasMatch ? (textScore + hybridScore * 32) *
            sourceBoost *
            (0.55 + document.student_score * 0.45) *
            (0.72 + document.freshness_score * 0.28) *
            (0.7 + document.importance_score * 0.3) *
            intentWeight(document.intent) *
            lifecycleWeight(document.lifecycle) *
            sourceTypeWeight(document.source_type) *
            deadlineUrgencyWeight(document.deadline) *
            tierMultiplier : 0;

        if (top1Exact && isExactTitle) {
            weightedScore += 10.0;
            if (routeObj.query_type === 'class_exam_lookup' && document.source_id === 'exam_vertical') {
                weightedScore += 20.0;
            }
        }

        const components = {
            bm25: Math.min(1, bm25Proxy),
            field: fieldScore,
            tag: tagScore,
            task_frame: taskFrameScore,
            utility: Math.min(1, utilityScore),
            risk_penalty: Math.min(1, riskPenalty),
            tier: tierMultiplier
        };

        if (weightedScore <= 0) return null;

        return {
            ...document,
            score: Number(weightedScore.toFixed(4)),
            score_reason: buildScoreReason(document, components) + ` [${tier}]`,
            isBlocked,
            tierCategory: tier,
            score_components: {
                ...components,
                bm25: Number(components.bm25.toFixed(4)),
                field: Number(components.field.toFixed(4)),
                tag: Number(components.tag.toFixed(4)),
                task_frame: Number(components.task_frame.toFixed(4)),
                utility: Number(components.utility.toFixed(4)),
                risk_penalty: Number(components.risk_penalty.toFixed(4)),
                tier: Number(tierMultiplier.toFixed(2))
            }
        } as RankedSearchDocument & { isBlocked: boolean, tierCategory: string };
    });

    // 4-bucket assembly for degraded fallback
    const strong: (RankedSearchDocument & { isBlocked: boolean; tierCategory: string })[] = [];
    const weak: (RankedSearchDocument & { isBlocked: boolean; tierCategory: string })[] = [];
    const fallbackCandidates: (RankedSearchDocument & { isBlocked: boolean; tierCategory: string })[] = [];
    const blockedCandidates: (RankedSearchDocument & { isBlocked: boolean; tierCategory: string })[] = [];

    for (const doc of candidates) {
        if (!doc) continue;
        if (doc.isBlocked) {
            blockedCandidates.push(doc);
        } else if (doc.tierCategory === 'A') {
            strong.push(doc);
        } else if (doc.tierCategory === 'B') {
            weak.push(doc);
        } else {
            fallbackCandidates.push(doc);
        }
    }

    const sortFn = (a: RankedSearchDocument, b: RankedSearchDocument) => {
        if (b.score !== a.score) return b.score - a.score;
        return dateSortValue(b.published_at) - dateSortValue(a.published_at);
    };
    strong.sort(sortFn);
    weak.sort(sortFn);
    fallbackCandidates.sort(sortFn);
    blockedCandidates.sort(sortFn);

    const MAX_RESULTS = 30;
    const validCandidates: (RankedSearchDocument & { isBlocked: boolean; tierCategory: string })[] = [
        ...strong,
        ...weak,
        ...fallbackCandidates,
    ].slice(0, MAX_RESULTS);

    if (allowBlockedFallback && validCandidates.length < MAX_RESULTS) {
        for (const doc of blockedCandidates) {
            if (validCandidates.length >= MAX_RESULTS) break;
            doc.degraded_fallback = true;
            doc.score_reason += "，目标候选不足，作为降级补位";
            validCandidates.push(doc);
        }
    }

    return validCandidates;
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
                source_mode: 'heuristic_rule_frame',
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
