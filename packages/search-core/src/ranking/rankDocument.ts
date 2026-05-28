import type { RankedSitegraphDocument, SitegraphFullDocument } from '@njupt-search/contracts';
import { detectQueryIntent, sourceIdForDocument } from '../intent/queryIntent';
import { normalizeSearchText as normalize } from '../tokenizer';

export const SITEGRAPH_FIELD_WEIGHTS: Record<string, number> = {
    t: 120,
    a: 95,
    e: 95,
    y: 95,
    s: 60,
    n: 55,
    g: 45,
    m: 16,
    c: 10
};

const textBlob = (document: SitegraphFullDocument, fields: Array<keyof SitegraphFullDocument>): string => {
    const values: string[] = [];
    for (const field of fields) {
        const value = document[field];
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

export const dateSortValue = (dateLike: string | null | undefined): number => {
    if (!dateLike) return 0;
    const date = new Date(dateLike);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
};

export const rankingDateSortValue = (document: SitegraphFullDocument): number => {
    return dateSortValue(document.published_at) || dateSortValue(document.version_date);
};

const ageDays = (timestamp: number): number => Math.max(0, (Date.now() - timestamp) / 86_400_000);

const decayedFreshness = (timestamp: number, maxScore: number, horizonDays: number): number => {
    if (!timestamp) return 0;
    return Math.max(0, maxScore - Math.min(ageDays(timestamp), horizonDays) / horizonDays * maxScore);
};

const freshnessScore = (document: SitegraphFullDocument, freshnessMode: ReturnType<typeof detectQueryIntent>['freshnessMode']): number => {
    if (freshnessMode === 'official_entry') return document.facet === 'system' ? 220 : 0;
    if (freshnessMode === 'form_version') {
        return decayedFreshness(dateSortValue(document.version_date) || dateSortValue(document.published_at), 2800, 3650);
    }
    if (freshnessMode === 'current_policy') {
        return decayedFreshness(dateSortValue(document.published_at) || dateSortValue(document.version_date), 4200, 2920);
    }
    if (freshnessMode === 'current_term') {
        return decayedFreshness(dateSortValue(document.published_at) || dateSortValue(document.version_date), 7200, 1460);
    }
    if (freshnessMode === 'current_notice') {
        return decayedFreshness(dateSortValue(document.published_at) || dateSortValue(document.version_date), 5200, 1825);
    }
    return decayedFreshness(dateSortValue(document.published_at) || dateSortValue(document.version_date), 900, 3650);
};

const stalePenalty = (document: SitegraphFullDocument, freshnessMode: ReturnType<typeof detectQueryIntent>['freshnessMode']): number => {
    if (!['current_notice', 'current_term', 'current_policy'].includes(freshnessMode)) return 0;
    const value = dateSortValue(document.published_at) || dateSortValue(document.version_date);
    if (!value) return 0;
    const days = ageDays(value);
    if (days > 3650) return 4200;
    if (days > 2190) return 3000;
    if (days > 1460) return 1800;
    return 0;
};

const isShortLandingPage = (document: SitegraphFullDocument, normalizedQuery: string, title: string): boolean => {
    return title === normalizedQuery
        && ['workflow', 'news', 'notice_article'].includes(document.facet)
        && !dateSortValue(document.published_at)
        && normalize(document.content).length < 220;
};

export const rankSitegraphDocument = (
    document: SitegraphFullDocument,
    query: string,
    terms: string[],
    lightScore: number
): RankedSitegraphDocument => {
    const profile = detectQueryIntent(query);
    const normalizedQuery = normalize(query);
    const title = textBlob(document, ['title']);
    const canonicalTitle = textBlob(document, ['canonical_title']);
    const section = textBlob(document, ['section', 'nav_path_text']);
    const summary = textBlob(document, ['summary']);
    const content = textBlob(document, ['content']);
    const tags = textBlob(document, ['tags']);
    const attachment = attachmentBlob(document);
    const url = normalize(document.url);
    const external = document.record_type === 'external' ? normalize(`${document.title} ${document.url} ${document.summary}`) : '';
    const sourceId = sourceIdForDocument(document);
    const taskKind = normalize(document.task_kind || '');
    let score = lightScore;
    const reasons: string[] = [];

    if (normalizedQuery && (title === normalizedQuery || canonicalTitle === normalizedQuery)) {
        score += document.facet === 'system' ? 5200 : 2400;
        reasons.push('标题精确');
    } else if (normalizedQuery && (title.includes(normalizedQuery) || canonicalTitle.includes(normalizedQuery))) {
        score += 1000;
        reasons.push('标题包含');
    }
    if (normalizedQuery && attachment.includes(normalizedQuery)) {
        score += 520;
        reasons.push('附件名命中');
    }
    if (normalizedQuery && external.includes(normalizedQuery)) {
        score += 440;
        reasons.push('外部入口命中');
    }
    if (normalizedQuery && url.includes(normalizedQuery)) {
        score += 220;
        reasons.push('URL 命中');
    }
    if (normalizedQuery && section.includes(normalizedQuery)) {
        score += 260;
        reasons.push('栏目路径命中');
    }
    if (normalizedQuery && content.includes(normalizedQuery)) {
        score += 120;
        reasons.push('正文命中');
    }
    if (normalizedQuery && tags.includes(normalizedQuery)) {
        score += 120;
        reasons.push('标签命中');
    }

    const matchedTerms: string[] = [];
    for (const term of terms.slice(0, 12)) {
        if (title.includes(term) || canonicalTitle.includes(term)) {
            score += 92;
            matchedTerms.push(term);
        } else if (attachment.includes(term)) {
            score += 78;
            matchedTerms.push(term);
        } else if (external.includes(term)) {
            score += 68;
            matchedTerms.push(term);
        } else if (url.includes(term)) {
            score += 55;
            matchedTerms.push(term);
        } else if (section.includes(term)) {
            score += 48;
            matchedTerms.push(term);
        } else if (summary.includes(term) || content.includes(term)) {
            score += 12;
            matchedTerms.push(term);
        }
    }
    if (matchedTerms.length > 0) {
        reasons.push(`词项：${Array.from(new Set(matchedTerms)).sort((a, b) => b.length - a.length).slice(0, 6).join('、')}`);
    }

    if (profile.authoritySources.includes(sourceId)) {
        score += profile.intent === 'broad_exploratory' ? 260 : 1900;
        reasons.push('权威来源');
    } else if (profile.authoritySources.length === 1 && profile.intent !== 'broad_exploratory') {
        score -= 650;
    }
    if (document.facet === 'system' && profile.intent === 'system_entry') {
        score += 2100;
        reasons.push('系统入口');
    }
    if (document.facet === 'download' && profile.intent === 'form_download') {
        score += 1150;
        reasons.push('下载资源');
    }
    if (document.facet === 'policy' && ['academic_policy', 'scholarship_aid'].includes(profile.intent)) {
        score += 1050;
        reasons.push('政策制度');
    }
    if (document.facet === 'workflow' && ['form_download', 'course_grade_credit'].includes(profile.intent)) {
        score += 520;
        reasons.push('办事流程');
    }
    if (document.facet === 'exam' && profile.intent === 'exam_schedule') {
        score += 1250;
        reasons.push('考试相关');
    }
    if (taskKind === normalize(profile.intent)) {
        score += 900;
        reasons.push('任务匹配');
    }

    const freshness = freshnessScore(document, profile.freshnessMode);
    if (freshness > 0) {
        score += freshness;
        reasons.push(profile.freshnessMode === 'official_entry' ? '官方入口' : profile.freshnessMode === 'form_version' ? '版本较新' : '时间较新');
    }
    const penalty = stalePenalty(document, profile.freshnessMode);
    if (penalty > 0) {
        score -= penalty;
        reasons.push('历史内容降权');
    }
    if (profile.intent === 'academic_policy' && isShortLandingPage(document, normalizedQuery, title)) {
        score -= 2600;
        reasons.push('短入口降权');
    }
    if (profile.intent === 'scholarship_aid' && title.includes(normalize('学业困难')) && !title.includes(normalize('家庭经济困难'))) {
        score -= 1800;
        reasons.push('非资助困难降权');
    }

    return {
        ...document,
        score,
        score_reason: reasons.join('；') || '倒排候选'
    };
};
