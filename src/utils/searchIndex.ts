import {
    RankedSitegraphDocument,
    SitegraphAttachment,
    SitegraphAttachmentSchema,
    SitegraphDocMeta,
    SitegraphDocMetaSchema,
    SitegraphExternalRecord,
    SitegraphExternalRecordSchema,
    SitegraphFullDocument,
    SitegraphFullDocumentSchema,
    SitegraphIndexBundle,
    SitegraphInvertedIndex,
    SitegraphInvertedIndexSchema,
    SitegraphSearchManifest,
    SitegraphSearchManifestSchema
} from '@/types';
import { fetchJson } from '@/utils/fetch';
import { z } from 'zod';

class SearchContractError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'SearchContractError';
    }
}

const LEGACY_FIELDS = new Set(['llm', 'llm_provider', 'llm_schema_version', 'semantic_mode', 'task_frames']);

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

const parseArray = <T>(schema: z.ZodType<T>, payload: unknown, source: string): T[] => {
    try {
        return z.array(schema).parse(payload);
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

const assertNoLegacyFields = (payload: unknown, source: string, path = '$'): void => {
    if (Array.isArray(payload)) {
        payload.forEach((item, index) => assertNoLegacyFields(item, source, `${path}[${index}]`));
        return;
    }
    if (!payload || typeof payload !== 'object') return;
    for (const [key, value] of Object.entries(payload as Record<string, unknown>)) {
        if (LEGACY_FIELDS.has(key)) {
            throw new SearchContractError(`Validation failed for ${source}: ${path}.${key} is a legacy LLM/HyTask field`);
        }
        assertNoLegacyFields(value, source, `${path}.${key}`);
    }
};

export const parseSitegraphManifest = (payload: unknown, source = 'sitegraph manifest'): SitegraphSearchManifest => {
    try {
        assertNoLegacyFields(payload, source);
        return SitegraphSearchManifestSchema.parse(payload);
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

export const parseSitegraphDocMeta = (payload: unknown, source = 'sitegraph doc_meta'): SitegraphDocMeta[] => {
    assertNoLegacyFields(payload, source);
    const docs = parseArray(SitegraphDocMetaSchema, payload, source);
    const ids = new Set<string>();
    for (const item of docs) {
        if (ids.has(item.id)) throw new SearchContractError(`${source} contains duplicate id: ${item.id}`);
        ids.add(item.id);
    }
    return docs;
};

export const parseSitegraphFullDocuments = (payload: unknown, source = 'sitegraph full shard'): SitegraphFullDocument[] => {
    assertNoLegacyFields(payload, source);
    return parseArray(SitegraphFullDocumentSchema, payload, source);
};

export const parseSitegraphAttachmentIndex = (payload: unknown, source = 'sitegraph attachment_index'): SitegraphAttachment[] => {
    return parseArray(SitegraphAttachmentSchema, payload, source);
};

export const parseSitegraphExternalIndex = (payload: unknown, source = 'sitegraph external_index'): SitegraphExternalRecord[] => {
    return parseArray(SitegraphExternalRecordSchema, payload, source);
};

export const parseSitegraphInvertedIndex = (payload: unknown, source = 'sitegraph inverted_index'): SitegraphInvertedIndex => {
    try {
        return SitegraphInvertedIndexSchema.parse(payload);
    } catch (e) {
        if (e instanceof z.ZodError) {
            throw new SearchContractError(`Validation failed for ${source}: ${formatZodIssues(payload, e)}`);
        }
        throw new SearchContractError(`Validation failed for ${source}: ${e instanceof Error ? e.message : String(e)}`);
    }
};

const normalize = (value: unknown): string => String(value || '')
    .normalize('NFKC')
    .toLowerCase()
    .replace(/\s+/g, '');

const queryTokens = (query: string, queryAliases: Record<string, unknown>): string[] => {
    const candidates = [query];
    const normalizedQuery = normalize(query);
    for (const [key, rawPayload] of Object.entries(queryAliases)) {
        const payload = rawPayload && typeof rawPayload === 'object' ? rawPayload as { aliases?: unknown[] } : {};
        const terms = [key, ...(Array.isArray(payload.aliases) ? payload.aliases.map(String) : [])];
        if (terms.some(term => normalize(term) && normalizedQuery.includes(normalize(term)))) {
            candidates.push(...terms);
        }
    }

    const tokens = new Set<string>();
    for (const candidate of candidates) {
        const text = normalize(candidate);
        if (text.length >= 2) tokens.add(text);
        const matches = text.match(/[\u4e00-\u9fff]{2,}|[a-z0-9][a-z0-9._-]{1,}/g) || [];
        for (const part of matches) {
            if (/^[\u4e00-\u9fff]+$/.test(part)) {
                const maxSize = Math.min(5, part.length);
                for (let size = 2; size <= maxSize; size += 1) {
                    for (let index = 0; index <= part.length - size; index += 1) {
                        tokens.add(part.slice(index, index + size));
                    }
                }
            } else {
                tokens.add(part);
            }
        }
    }
    return Array.from(tokens).sort((a, b) => b.length - a.length);
};

const FIELD_WEIGHTS: Record<string, number> = {
    t: 120,
    a: 95,
    e: 95,
    s: 60,
    g: 45,
    b: 12
};

const shardCache = new Map<string, Promise<SitegraphFullDocument[]>>();

const loadShard = (path: string, signal: AbortSignal): Promise<SitegraphFullDocument[]> => {
    const existing = shardCache.get(path);
    if (existing) return existing;
    const promise = fetchJson(path, signal).then(payload => parseSitegraphFullDocuments(payload, path));
    shardCache.set(path, promise);
    return promise;
};

const textBlob = (document: SitegraphFullDocument | SitegraphDocMeta, fields: Array<keyof SitegraphFullDocument | keyof SitegraphDocMeta>): string => {
    const values: string[] = [];
    for (const field of fields) {
        const value = document[field as keyof typeof document];
        if (Array.isArray(value)) values.push(...value.map(String));
        else if (value !== null && value !== undefined) values.push(String(value));
    }
    return normalize(values.join(' '));
};

const attachmentBlob = (document: SitegraphFullDocument): string => normalize(
    document.attachments
        .map(attachment => [attachment.name, attachment.extension, attachment.section, attachment.parent_url].filter(Boolean).join(' '))
        .join(' ')
);

const dateSortValue = (dateLike: string | null | undefined): number => {
    if (!dateLike) return 0;
    const date = new Date(dateLike);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
};

const freshnessScore = (document: SitegraphFullDocument): number => {
    if (!['notice_article', 'exam', 'news'].includes(document.facet)) return 0;
    const value = dateSortValue(document.published_at);
    if (!value) return 0;
    const days = Math.max(0, (Date.now() - value) / 86_400_000);
    return Math.max(0, 30 - Math.min(days, 365) / 365 * 30);
};

const rankDocument = (
    document: SitegraphFullDocument,
    query: string,
    terms: string[],
    lightScore: number
): RankedSitegraphDocument => {
    const normalizedQuery = normalize(query);
    const title = textBlob(document, ['title']);
    const section = textBlob(document, ['section', 'nav_path_text']);
    const summary = textBlob(document, ['summary']);
    const content = textBlob(document, ['content']);
    const tags = textBlob(document, ['tags']);
    const attachment = attachmentBlob(document);
    const external = document.record_type === 'external' ? normalize(`${document.title} ${document.url} ${document.summary}`) : '';
    let score = lightScore;
    const reasons: string[] = [];

    if (normalizedQuery && title === normalizedQuery) {
        score += 5000;
        reasons.push('标题精确');
    } else if (normalizedQuery && title.includes(normalizedQuery)) {
        score += 520;
        reasons.push('标题包含');
    }
    if (normalizedQuery && attachment.includes(normalizedQuery)) {
        score += 360;
        reasons.push('附件名命中');
    }
    if (normalizedQuery && external.includes(normalizedQuery)) {
        score += 360;
        reasons.push('外部入口命中');
    }
    if (normalizedQuery && section.includes(normalizedQuery)) {
        score += 180;
        reasons.push('栏目路径命中');
    }
    if (normalizedQuery && content.includes(normalizedQuery)) {
        score += 120;
        reasons.push('正文命中');
    }
    if (normalizedQuery && tags.includes(normalizedQuery)) {
        score += 80;
        reasons.push('标签命中');
    }

    const matchedTerms: string[] = [];
    for (const term of terms.slice(0, 12)) {
        if (title.includes(term)) {
            score += 80;
            matchedTerms.push(term);
        } else if (attachment.includes(term)) {
            score += 70;
            matchedTerms.push(term);
        } else if (external.includes(term)) {
            score += 65;
            matchedTerms.push(term);
        } else if (section.includes(term)) {
            score += 45;
            matchedTerms.push(term);
        } else if (summary.includes(term) || content.includes(term)) {
            score += 12;
            matchedTerms.push(term);
        }
    }
    if (matchedTerms.length > 0) {
        reasons.push(`词项：${Array.from(new Set(matchedTerms)).sort((a, b) => b.length - a.length).slice(0, 6).join('、')}`);
    }
    if (document.facet === 'system' && ['系统', 'jwxt', '教务'].some(term => normalizedQuery.includes(term))) {
        score += 1500;
        reasons.push('系统入口');
    }
    if (document.facet === 'download' && ['附件', '下载', 'xlsx', 'xls', '表格'].some(term => normalizedQuery.includes(term))) {
        score += 120;
        reasons.push('下载资源');
    }
    score += freshnessScore(document);

    return {
        ...document,
        score,
        score_reason: reasons.join('；') || '倒排候选'
    };
};

export const recallSitegraphDocuments = async (
    bundle: SitegraphIndexBundle,
    query: string,
    signal: AbortSignal,
    limit = 30
): Promise<RankedSitegraphDocument[]> => {
    const trimmed = query.trim();
    if (trimmed.length < 2) return [];
    const terms = queryTokens(trimmed, bundle.queryAliases);
    const scores = new Map<number, number>();
    for (const term of terms) {
        const postings = bundle.invertedIndex.tokens[term];
        if (!postings) continue;
        for (const [field, ids] of Object.entries(postings)) {
            const weight = FIELD_WEIGHTS[field] || 8;
            for (const docIndex of ids) {
                scores.set(docIndex, (scores.get(docIndex) || 0) + weight + Math.min(term.length, 8));
            }
        }
    }

    const normalizedQuery = normalize(trimmed);
    if (scores.size < 8) {
        for (const meta of bundle.docMeta) {
            const haystack = textBlob(meta, ['title', 'summary', 'section', 'nav_path_text', 'tags']);
            if (normalizedQuery && haystack.includes(normalizedQuery)) {
                scores.set(meta.doc_index, (scores.get(meta.doc_index) || 0) + 90);
            }
        }
    }
    if (scores.size === 0) return [];

    const candidateIndices = Array.from(scores.entries())
        .sort((a, b) => b[1] - a[1])
        .slice(0, 120)
        .map(([docIndex]) => docIndex);
    const candidateMeta = candidateIndices
        .map(docIndex => bundle.docMeta[docIndex])
        .filter((meta): meta is SitegraphDocMeta => Boolean(meta));
    const shardPaths = Array.from(new Set(candidateMeta.map(meta => meta.shard.path)));
    const shardResults = await Promise.all(shardPaths.map(path => loadShard(path, signal)));
    const fullDocs = new Map<number, SitegraphFullDocument>();
    for (const shard of shardResults) {
        for (const document of shard) fullDocs.set(document.doc_index, document);
    }

    return candidateIndices
        .map(docIndex => {
            const document = fullDocs.get(docIndex);
            return document ? rankDocument(document, trimmed, terms, scores.get(docIndex) || 0) : null;
        })
        .filter((item): item is RankedSitegraphDocument => Boolean(item))
        .sort((a, b) => {
            const scoreDelta = b.score - a.score;
            if (scoreDelta !== 0) return scoreDelta;
            const dateDelta = dateSortValue(b.published_at) - dateSortValue(a.published_at);
            if (dateDelta !== 0) return dateDelta;
            return a.id.localeCompare(b.id);
        })
        .slice(0, limit);
};

export const formatSearchDate = (dateLike: string | null | undefined): string => {
    if (!dateLike) return '日期未标注';
    const date = new Date(dateLike);
    if (Number.isNaN(date.getTime())) return dateLike;

    return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    });
};
