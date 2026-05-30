import {
    QueryDirectoryRoute,
    RankedSitegraphDocument,
    SitegraphDocMeta,
    SitegraphFullDocument,
    SitegraphFullShard,
    SitegraphLocalBodyIndex,
    SitegraphLocalIndexRef,
    SitegraphLocalLightIndex,
    SitegraphQueryPlan,
    SitegraphQueryStats,
    SitegraphRoutedSession,
    SitegraphSearchCoverage,
    SitegraphSearchEvent,
    SitegraphSearchFilters,
    SitegraphSearchPhase,
    SitegraphSortMode,
    SitegraphSourceManifest,
    SourceRegistryEntry
} from '@njupt-search/contracts';
import { fetchJson } from './fetchJson';
import {
    parseSitegraphFullDocuments,
    parseSitegraphLocalBodyIndex,
    parseSitegraphLocalLightIndex,
    parseSitegraphSourceManifest,
    SearchContractError
} from './sitegraphContract';
import { sitegraphDocumentMatchesFilters } from './sitegraphFilters';
import { rankingDateSortValue, rankSitegraphDocument, SITEGRAPH_FIELD_WEIGHTS } from './ranking/rankDocument';
import { detectQueryIntent } from './intent/queryIntent';
import { expandSitegraphQueryPhrases, normalizeSearchText as normalize, tokenizeSitegraphQuery } from './tokenizer';

const DEFAULT_CANDIDATE_LIMIT = 160;
const DEFAULT_MAX_SHARD_LOADS = 40;
const QUICK_MAX_SHARD_LOADS = 8;
const BODY_MAX_SHARD_LOADS = 18;
const HYDRATE_MAX_SHARD_LOADS = 40;
const SHARD_BATCH_SIZE = 4;
const LIGHT_SEARCH_FIELDS = ['title', 'section', 'nav_path', 'tags', 'attachments', 'external', 'system'];
const BODY_SEARCH_FIELDS = [...LIGHT_SEARCH_FIELDS, 'summary', 'content'];
const FULL_SCAN_FIELDS = ['title', 'section', 'nav_path', 'summary', 'content', 'attachments', 'url'];

type ShardFilterMap = Record<string, {
    bitset_base64: string;
    bit_count: number;
    hash_count: number;
    token_count: number;
    sha256: string;
    hash_algorithm: string;
}>;

interface LoadedPlanningScope {
    sourceManifests: SitegraphSourceManifest[];
    localRefs: SitegraphLocalIndexRef[];
    sourceManifestBytes: number;
    shardPathById: Map<string, string>;
    shardById: Map<string, SitegraphFullShard>;
}

interface SearchTelemetry {
    localMetaFallbackDocIndices: Set<number>;
    fullScanMatchDocIndices: Set<number>;
}

const sourceManifestCache = new Map<string, SitegraphSourceManifest>();
const localLightIndexCache = new Map<string, SitegraphLocalLightIndex>();
const localBodyIndexCache = new Map<string, SitegraphLocalBodyIndex>();
const shardFilterCache = new Map<string, ShardFilterMap>();
const shardCache = new Map<string, SitegraphFullDocument[]>();

const publicAssetPath = (path: string): string => {
    if (/^https?:\/\//.test(path) || path.startsWith('/')) return path;
    return `/${path}`;
};

const throwIfAborted = (signal: AbortSignal): void => {
    if (signal.aborted) {
        throw new DOMException('Search cancelled', 'AbortError');
    }
};

const yieldToWorker = async (): Promise<void> => {
    await new Promise(resolve => setTimeout(resolve, 0));
};

const firstScreenBytes = (session: SitegraphRoutedSession): number => {
    const artifacts = session.manifest.artifacts;
    return artifacts.source_registry.bytes + artifacts.global_query_directory.bytes + artifacts.query_aliases.bytes;
};

const activeFilters = (filters: SitegraphSearchFilters): boolean => {
    return (filters.sourceId || 'all') !== 'all'
        || (filters.facet || 'all') !== 'all'
        || (filters.dateRange || 'all') !== 'all';
};

const dateRangeFloorYear = (dateRange: SitegraphSearchFilters['dateRange'], now: number): number => {
    if (!dateRange || dateRange === 'all' || dateRange === 'undated') return 0;
    const years = dateRange === 'past_year' ? 1 : dateRange === 'past_3_years' ? 3 : 5;
    return new Date(now - years * 365 * 86_400_000).getFullYear();
};

const scopeMatchesFilters = (
    scope: SitegraphLocalIndexRef['scope'],
    filters: SitegraphSearchFilters,
    now: number
): boolean => {
    const sourceId = filters.sourceId || 'all';
    if (sourceId !== 'all' && scope.source_id !== sourceId) return false;
    const facet = filters.facet || 'all';
    if (facet !== 'all' && scope.facet !== facet) return false;
    const dateRange = filters.dateRange || 'all';
    if (dateRange === 'undated') return scope.year === 'undated';
    const floor = dateRangeFloorYear(dateRange, now);
    if (floor > 0) {
        const year = Number(scope.year);
        if (!Number.isFinite(year) || year < floor) return false;
    }
    return true;
};

const shardMatchesFilters = (
    shard: SitegraphFullShard,
    filters: SitegraphSearchFilters,
    now: number
): boolean => {
    const shardSourceId = String(shard.source_id || '');
    const sourceId = filters.sourceId || 'all';
    if (sourceId !== 'all' && shardSourceId !== sourceId) return false;
    const facet = filters.facet || 'all';
    if (facet !== 'all' && !shard.facet_range.includes(facet)) return false;
    const dateRange = filters.dateRange || 'all';
    if (dateRange === 'undated') return shard.year_range.includes('undated');
    const floor = dateRangeFloorYear(dateRange, now);
    if (floor > 0) {
        return shard.year_range.some(year => Number.isFinite(Number(year)) && Number(year) >= floor);
    }
    return true;
};

const sourceEntriesById = (session: SitegraphRoutedSession): Map<string, SourceRegistryEntry> => {
    return new Map(session.sourceRegistry.sources.map(source => [source.source_id, source]));
};

const routeForTerms = (
    session: SitegraphRoutedSession,
    terms: string[],
    intent: string
): QueryDirectoryRoute[] => {
    const routes: QueryDirectoryRoute[] = [];
    const seen = new Set<QueryDirectoryRoute>();
    for (const term of terms) {
        const route = session.globalQueryDirectory.entries[normalize(term)];
        if (route && !seen.has(route)) {
            seen.add(route);
            routes.push(route);
        }
    }
    const intentRoute = session.globalQueryDirectory.intents[intent];
    if (intentRoute && !seen.has(intentRoute)) routes.push(intentRoute);
    return routes;
};

const uniqueOrdered = (values: string[]): string[] => {
    const seen = new Set<string>();
    const result: string[] = [];
    for (const value of values) {
        if (!value || seen.has(value)) continue;
        seen.add(value);
        result.push(value);
    }
    return result;
};

const buildQueryPlan = (
    session: SitegraphRoutedSession,
    query: string,
    terms: string[],
    filters: SitegraphSearchFilters
): SitegraphQueryPlan => {
    const profile = detectQueryIntent(query);
    const routes = routeForTerms(session, terms, profile.intent);
    const routeSources = routes.flatMap(route => route.likely_sources);
    const routeLocalIndexes = routes.flatMap(route => route.local_index_ids);
    const routeResultTypes = routes.flatMap(route => route.expected_result_types);
    const allSources = session.sourceRegistry.sources.map(source => source.source_id);
    const filteredSource = filters.sourceId && filters.sourceId !== 'all' ? [filters.sourceId] : [];
    const sourceIds = uniqueOrdered([
        ...filteredSource,
        ...profile.authoritySources,
        ...routeSources,
        ...allSources,
    ]).filter(sourceId => allSources.includes(sourceId));
    const verificationSourceIds = filteredSource.length > 0 ? filteredSource : allSources;
    return {
        normalized_query: normalize(query),
        aliases: expandSitegraphQueryPhrases(query, session.queryAliases),
        intent: profile.intent,
        authority_sources: profile.authoritySources,
        expected_result_types: uniqueOrdered(routeResultTypes),
        source_ids: sourceIds,
        local_index_ids: uniqueOrdered(routeLocalIndexes),
        verification_source_ids: verificationSourceIds,
    };
};

const loadSourceManifest = async (
    entry: SourceRegistryEntry,
    signal: AbortSignal
): Promise<SitegraphSourceManifest> => {
    const path = entry.artifact_manifest.path;
    const existing = sourceManifestCache.get(path);
    if (existing) return existing;
    const payload = await fetchJson(publicAssetPath(path), signal, 'index');
    const parsed = parseSitegraphSourceManifest(payload, path);
    sourceManifestCache.set(path, parsed);
    return parsed;
};

const loadPlanningScope = async (
    session: SitegraphRoutedSession,
    plan: SitegraphQueryPlan,
    filters: SitegraphSearchFilters,
    now: number,
    signal: AbortSignal
): Promise<LoadedPlanningScope> => {
    const entries = sourceEntriesById(session);
    const sourceManifests: SitegraphSourceManifest[] = [];
    let sourceManifestBytes = 0;
    for (const sourceId of plan.source_ids) {
        const entry = entries.get(sourceId);
        if (!entry) continue;
        const manifest = await loadSourceManifest(entry, signal);
        sourceManifests.push(manifest);
        sourceManifestBytes += entry.artifact_manifest.bytes;
    }

    const plannedIndexIds = new Set(plan.local_index_ids);
    const plannedIndexOrder = new Map(plan.local_index_ids.map((indexId, index) => [indexId, index]));
    let localRefs = sourceManifests
        .flatMap(sourceManifest => sourceManifest.local_indexes)
        .filter(ref => scopeMatchesFilters(ref.scope, filters, now));
    if (plannedIndexIds.size > 0) {
        const routedRefs = localRefs.filter(ref => plannedIndexIds.has(ref.index_id));
        if (routedRefs.length > 0) {
            localRefs = routedRefs
                .sort((a, b) => {
                    const orderDelta = (plannedIndexOrder.get(a.index_id) ?? Number.MAX_SAFE_INTEGER)
                        - (plannedIndexOrder.get(b.index_id) ?? Number.MAX_SAFE_INTEGER);
                    if (orderDelta !== 0) return orderDelta;
                    return b.doc_count - a.doc_count || a.index_id.localeCompare(b.index_id);
                })
                .slice(0, 48);
        }
    }
    if (plannedIndexIds.size === 0 || localRefs.every(ref => !plannedIndexIds.has(ref.index_id))) {
        localRefs = localRefs
            .sort((a, b) => {
                const yearDelta = Number(b.scope.year) - Number(a.scope.year);
                if (Number.isFinite(yearDelta) && yearDelta !== 0) return yearDelta;
                return b.doc_count - a.doc_count || a.index_id.localeCompare(b.index_id);
            })
            .slice(0, 48);
    }

    const shardPathById = new Map<string, string>();
    const shardById = new Map<string, SitegraphFullShard>();
    for (const sourceManifest of sourceManifests) {
        for (const shard of sourceManifest.full_shards) {
            shardPathById.set(shard.shard_id, shard.path);
            shardById.set(shard.shard_id, shard);
        }
    }

    return {
        sourceManifests,
        localRefs,
        sourceManifestBytes,
        shardPathById,
        shardById,
    };
};

const loadLocalLightIndex = async (
    ref: SitegraphLocalIndexRef,
    signal: AbortSignal
): Promise<SitegraphLocalLightIndex> => {
    const path = ref.light_index.path;
    const existing = localLightIndexCache.get(path);
    if (existing) return existing;
    const payload = await fetchJson(publicAssetPath(path), signal, 'index');
    const parsed = parseSitegraphLocalLightIndex(payload, path);
    localLightIndexCache.set(path, parsed);
    return parsed;
};

const loadLocalBodyIndex = async (
    ref: SitegraphLocalIndexRef,
    signal: AbortSignal
): Promise<SitegraphLocalBodyIndex> => {
    const path = ref.body_index.path;
    const existing = localBodyIndexCache.get(path);
    if (existing) return existing;
    const payload = await fetchJson(publicAssetPath(path), signal, 'index');
    const parsed = parseSitegraphLocalBodyIndex(payload, path);
    localBodyIndexCache.set(path, parsed);
    return parsed;
};

const loadShardFilter = async (
    sourceManifest: SitegraphSourceManifest,
    signal: AbortSignal
): Promise<ShardFilterMap> => {
    const artifact = sourceManifest.artifacts.shard_filter;
    if (!artifact) {
        throw new SearchContractError(`Source manifest ${sourceManifest.source_id} is missing shard_filter`);
    }
    const path = artifact.path;
    const existing = shardFilterCache.get(path);
    if (existing) return existing;
    const payload = await fetchJson(publicAssetPath(path), signal, 'index');
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
        throw new SearchContractError(`Validation failed for ${path}: shard_filter must be an object`);
    }
    shardFilterCache.set(path, payload as ShardFilterMap);
    return payload as ShardFilterMap;
};

const loadShard = (path: string, signal: AbortSignal): Promise<SitegraphFullDocument[]> => {
    const existing = shardCache.get(path);
    if (existing) return Promise.resolve(existing);
    return fetchJson(publicAssetPath(path), signal, 'shard')
        .then(payload => {
            const documents = parseSitegraphFullDocuments(payload, path);
            shardCache.set(path, documents);
            return documents;
        });
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

const fullScanBlob = (document: SitegraphFullDocument): string => normalize([
    document.title,
    document.section,
    document.nav_path_text,
    document.nav_path.join(' '),
    document.summary,
    document.content,
    document.url,
    document.attachments
        .map(attachment => [attachment.name, attachment.extension, attachment.url, attachment.section, attachment.parent_url].filter(Boolean).join(' '))
        .join(' ')
].join(' '));

const applyPostings = (
    scores: Map<number, number>,
    tokens: SitegraphLocalLightIndex['tokens'] | SitegraphLocalBodyIndex['tokens'],
    terms: string[]
): void => {
    for (const term of terms) {
        const postings = tokens[term];
        if (!postings) continue;
        for (const [field, ids] of Object.entries(postings)) {
            const weight = SITEGRAPH_FIELD_WEIGHTS[field] || 8;
            for (const docIndex of ids) {
                scores.set(docIndex, (scores.get(docIndex) || 0) + weight + Math.min(term.length, 8));
            }
        }
    }
};

const applyLocalMetaFallback = (
    docsByIndex: Map<number, SitegraphDocMeta>,
    scores: Map<number, number>,
    normalizedQuery: string,
    filters: SitegraphSearchFilters,
    now: number
): number[] => {
    if (!normalizedQuery) return [];
    let filteredScoreCount = 0;
    for (const docIndex of scores.keys()) {
        const meta = docsByIndex.get(docIndex);
        if (meta && sitegraphDocumentMatchesFilters(meta, filters, now)) filteredScoreCount += 1;
        if (filteredScoreCount >= 8) return [];
    }
    const matchedIndices: number[] = [];
    for (const meta of docsByIndex.values()) {
        if (!sitegraphDocumentMatchesFilters(meta, filters, now)) continue;
        const haystack = textBlob(meta, ['title', 'section', 'nav_path_text']);
        if (haystack.includes(normalizedQuery)) {
            scores.set(meta.doc_index, (scores.get(meta.doc_index) || 0) + 90);
            matchedIndices.push(meta.doc_index);
        }
    }
    return matchedIndices;
};

const sortedScoreEntries = (scores: Map<number, number>): Array<[number, number]> => {
    return Array.from(scores.entries()).sort((a, b) => {
        const scoreDelta = b[1] - a[1];
        if (scoreDelta !== 0) return scoreDelta;
        return a[0] - b[0];
    });
};

const candidateShardPaths = (
    docsByIndex: Map<number, SitegraphDocMeta>,
    scores: Map<number, number>,
    shardPathById: Map<string, string>,
    candidateLimit: number,
    maxShardLoads: number,
    filters: SitegraphSearchFilters,
    now: number
): { indices: number[]; paths: string[] } => {
    const indices: number[] = [];
    const paths: string[] = [];
    const seenPaths = new Set<string>();
    for (const [docIndex] of sortedScoreEntries(scores).slice(0, candidateLimit)) {
        const meta = docsByIndex.get(docIndex);
        if (!meta?.shard?.shard_id) continue;
        if (!sitegraphDocumentMatchesFilters(meta, filters, now)) continue;
        const shardPath = meta.shard.path || shardPathById.get(meta.shard.shard_id);
        if (!shardPath) continue;
        const isNewShard = !seenPaths.has(shardPath);
        if (isNewShard && seenPaths.size >= maxShardLoads) continue;
        indices.push(docIndex);
        if (isNewShard) {
            seenPaths.add(shardPath);
            paths.push(shardPath);
        }
    }
    return { indices, paths };
};

const loadShardBatch = async (
    paths: string[],
    signal: AbortSignal,
    loadedShardPaths: Set<string>,
    fullDocsByIndex: Map<number, SitegraphFullDocument>
): Promise<void> => {
    for (let index = 0; index < paths.length; index += SHARD_BATCH_SIZE) {
        throwIfAborted(signal);
        const batch = paths.slice(index, index + SHARD_BATCH_SIZE);
        const shardResults = await Promise.all(batch.map(path => loadShard(path, signal)));
        shardResults.forEach((documents, batchIndex) => {
            const path = batch[batchIndex];
            if (path) loadedShardPaths.add(path);
            for (const document of documents) {
                fullDocsByIndex.set(document.doc_index, document);
            }
        });
        await yieldToWorker();
    }
};

const sortRankedResults = (
    results: RankedSitegraphDocument[],
    sortMode: SitegraphSortMode = 'relevance'
): RankedSitegraphDocument[] => {
    return results.sort((a, b) => {
        const dateDelta = rankingDateSortValue(b) - rankingDateSortValue(a);
        if (sortMode === 'date_desc' && dateDelta !== 0) return dateDelta;
        const scoreDelta = b.score - a.score;
        if (scoreDelta !== 0) return scoreDelta;
        if (dateDelta !== 0) return dateDelta;
        return a.id.localeCompare(b.id);
    });
};

const mergeRankedResults = (
    resultMap: Map<string, RankedSitegraphDocument>,
    incoming: RankedSitegraphDocument[]
): number => {
    let addedOrImproved = 0;
    for (const result of incoming) {
        const existing = resultMap.get(result.id);
        if (!existing || result.score > existing.score) {
            resultMap.set(result.id, result);
            addedOrImproved += 1;
        }
    }
    return addedOrImproved;
};

const loadedBytesFor = (
    session: SitegraphRoutedSession,
    localIndexBytes: number,
    hydratedShardBytes: number,
    filterBytes: number
): number => firstScreenBytes(session) + localIndexBytes + hydratedShardBytes + filterBytes;

const rankedSnapshot = (
    resultMap: Map<string, RankedSitegraphDocument>,
    stats: SitegraphQueryStats,
    limit: number,
    sortMode: SitegraphSortMode
): RankedSitegraphDocument[] => {
    return sortRankedResults(Array.from(resultMap.values()), sortMode)
        .slice(0, limit)
        .map(result => ({ ...result, query_stats: stats }));
};

const coverageFor = (
    session: SitegraphRoutedSession,
    phase: SitegraphSearchPhase,
    searchedFields: string[],
    provedNoMatchShards: number,
    scannedShards: number,
    searchedDocuments: number,
    totalShards: number,
    totalDocuments: number,
    localIndexBytes: number,
    hydratedShardBytes: number,
    filterBytes: number,
    usedBodyIndex: boolean,
    exhaustiveComplete: boolean,
    scoped: boolean
): SitegraphSearchCoverage => ({
    phase,
    coverage_state: phase,
    scope: scoped ? 'scoped' : 'global',
    searched_fields: searchedFields,
    proved_no_match_shards: provedNoMatchShards,
    scanned_shards: scannedShards,
    total_shards: totalShards,
    searched_documents: searchedDocuments,
    total_documents: totalDocuments,
    loaded_bytes: loadedBytesFor(session, localIndexBytes, hydratedShardBytes, filterBytes),
    first_screen_bytes: firstScreenBytes(session),
    local_index_bytes: localIndexBytes,
    hydrated_shard_bytes: hydratedShardBytes,
    used_body_index: usedBodyIndex,
    exhaustive_complete: exhaustiveComplete,
});

const statsFor = (
    phase: SitegraphSearchPhase,
    coverage: SitegraphSearchCoverage,
    plan: SitegraphQueryPlan,
    loadedLocalIndexIds: Set<string>,
    loadedShardPaths: Set<string>,
    candidateCount: number,
    resultMap: Map<string, RankedSitegraphDocument>,
    telemetry: SearchTelemetry
): SitegraphQueryStats => ({
    phase,
    coverage,
    plan,
    usedBodyIndex: coverage.used_body_index,
    loadedLocalIndexCount: loadedLocalIndexIds.size,
    loadedLocalIndexIds: Array.from(loadedLocalIndexIds).sort(),
    loadedShardCount: loadedShardPaths.size,
    loadedShardPaths: Array.from(loadedShardPaths).sort(),
    candidateCount,
    exhaustiveComplete: coverage.exhaustive_complete,
    resultCount: resultMap.size,
    localIndexBytes: coverage.local_index_bytes,
    hydratedShardBytes: coverage.hydrated_shard_bytes,
    fallbacks: {
        localMetaFallbackDocuments: telemetry.localMetaFallbackDocIndices.size,
        snippetFallbackResults: Array.from(resultMap.values()).filter(result => result.match_snippet?.fallback === true).length,
        verifiedFullScanMatches: telemetry.fullScanMatchDocIndices.size,
    },
});

const documentMatchesFullScan = (document: SitegraphFullDocument, matchPhrases: string[]): boolean => {
    const blob = fullScanBlob(document);
    return matchPhrases.some(term => blob.includes(term));
};

const rankHydratedCandidates = (
    indices: number[],
    fullDocsByIndex: Map<number, SitegraphFullDocument>,
    scores: Map<number, number>,
    query: string,
    terms: string[],
    matchPhrases: string[],
    filters: SitegraphSearchFilters,
    now: number
): RankedSitegraphDocument[] => {
    return indices
        .map(docIndex => {
            const document = fullDocsByIndex.get(docIndex);
            return document
                && sitegraphDocumentMatchesFilters(document, filters, now)
                && documentMatchesFullScan(document, matchPhrases)
                ? rankSitegraphDocument(document, query, terms, scores.get(docIndex) || 0)
                : null;
        })
        .filter((item): item is RankedSitegraphDocument => Boolean(item));
};

const hydrateCandidatePhase = async (
    docsByIndex: Map<number, SitegraphDocMeta>,
    shardPathById: Map<string, string>,
    scores: Map<number, number>,
    query: string,
    terms: string[],
    signal: AbortSignal,
    loadedShardPaths: Set<string>,
    fullDocsByIndex: Map<number, SitegraphFullDocument>,
    candidateLimit: number,
    maxShardLoads: number,
    matchPhrases: string[],
    filters: SitegraphSearchFilters,
    now: number
): Promise<{ ranked: RankedSitegraphDocument[]; candidateCount: number }> => {
    const candidates = candidateShardPaths(docsByIndex, scores, shardPathById, candidateLimit, maxShardLoads, filters, now);
    const pathsToLoad = candidates.paths.filter(path => !loadedShardPaths.has(path));
    await loadShardBatch(pathsToLoad, signal, loadedShardPaths, fullDocsByIndex);
    return {
        ranked: rankHydratedCandidates(candidates.indices, fullDocsByIndex, scores, query, terms, matchPhrases, filters, now),
        candidateCount: candidates.indices.length,
    };
};

const filterTokenHashInt = (text: string, seed: number): number => {
    let value = (2166136261 ^ seed) >>> 0;
    const bytes = new TextEncoder().encode(text);
    for (const byte of bytes) {
        value ^= byte;
        value = Math.imul(value, 16777619) >>> 0;
    }
    return value;
};

const decodedFilterCache = new WeakMap<object, Uint8Array>();

const decodeBase64Bytes = (value: string): Uint8Array => {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
};

const decodedFilterBytes = (filter: ShardFilterMap[string]): Uint8Array => {
    const cached = decodedFilterCache.get(filter);
    if (cached) return cached;
    const decoded = decodeBase64Bytes(filter.bitset_base64);
    decodedFilterCache.set(filter, decoded);
    return decoded;
};

const bloomMayContain = (filter: ShardFilterMap[string], term: string): boolean => {
    const bytes = decodedFilterBytes(filter);
    for (let seed = 0; seed < filter.hash_count; seed += 1) {
        const bit = filterTokenHashInt(term, seed) % filter.bit_count;
        if (((bytes[Math.floor(bit / 8)] ?? 0) & (1 << (bit % 8))) === 0) {
            return false;
        }
    }
    return true;
};

const shardFilterProvesNoMatch = (
    shardId: string,
    shardFilter: ShardFilterMap,
    terms: string[]
): boolean => {
    const filter = shardFilter[shardId];
    if (!filter || filter.hash_algorithm !== 'bloom-fnv1a32-utf8') return false;
    return terms.every(term => !bloomMayContain(filter, term));
};

export interface ProgressiveSearchOptions {
    limit?: number;
    candidateLimit?: number;
    maxShardLoads?: number;
    sortMode?: SitegraphSortMode;
    filters?: SitegraphSearchFilters;
    now?: number;
}

export const searchSitegraphProgressively = async (
    session: SitegraphRoutedSession,
    query: string,
    signal: AbortSignal,
    emit: (event: SitegraphSearchEvent) => void,
    options: ProgressiveSearchOptions = {}
): Promise<void> => {
    const trimmed = query.trim();
    const limit = options.limit ?? 60;
    const candidateLimit = options.candidateLimit ?? DEFAULT_CANDIDATE_LIMIT;
    const maxShardLoads = options.maxShardLoads ?? DEFAULT_MAX_SHARD_LOADS;
    const sortMode = options.sortMode ?? 'relevance';
    const filters = options.filters ?? {};
    const now = options.now ?? Date.now();
    const terms = tokenizeSitegraphQuery(trimmed, session.queryAliases);
    const normalizedQuery = normalize(trimmed);
    const matchPhrases = expandSitegraphQueryPhrases(trimmed, session.queryAliases);
    const plan = buildQueryPlan(session, trimmed, terms, filters);
    const scores = new Map<number, number>();
    const resultMap = new Map<string, RankedSitegraphDocument>();
    const loadedShardPaths = new Set<string>();
    const loadedLocalIndexIds = new Set<string>();
    const docsByIndex = new Map<number, SitegraphDocMeta>();
    const fullDocsByIndex = new Map<number, SitegraphFullDocument>();
    const telemetry: SearchTelemetry = {
        localMetaFallbackDocIndices: new Set<number>(),
        fullScanMatchDocIndices: new Set<number>(),
    };
    let candidateCount = 0;
    let usedBodyIndex = false;
    let localIndexBytes = 0;
    let hydratedShardBytes = 0;
    let filterBytes = 0;
    let totalScopeShards = session.manifest.progressive_search.total_shards;
    let totalScopeDocuments = session.manifest.progressive_search.total_documents;
    const scoped = activeFilters(filters);

    const emitResults = (
        type: SitegraphSearchPhase,
        coverage: SitegraphSearchCoverage,
        includeResults: boolean
    ) => {
        const stats = statsFor(type, coverage, plan, loadedLocalIndexIds, loadedShardPaths, candidateCount, resultMap, telemetry);
        emit({
            type,
            query: trimmed,
            coverage,
            stats,
            ...(includeResults ? { results: rankedSnapshot(resultMap, stats, limit, sortMode) } : {}),
        });
    };

    const startedCoverage = coverageFor(
        session,
        'plan_started',
        [],
        0,
        0,
        0,
        totalScopeShards,
        totalScopeDocuments,
        0,
        0,
        0,
        false,
        false,
        scoped
    );
    emitResults('plan_started', startedCoverage, false);
    throwIfAborted(signal);

    if (trimmed.length < 2) {
        const completePhase = scoped ? 'scoped_exhaustive_complete' : 'global_exhaustive_complete';
        const completeCoverage = coverageFor(session, completePhase, FULL_SCAN_FIELDS, 0, 0, 0, totalScopeShards, totalScopeDocuments, 0, 0, 0, false, true, scoped);
        emitResults(completePhase, completeCoverage, true);
        return;
    }

    const planningScope = await loadPlanningScope(session, plan, filters, now, signal);
    localIndexBytes += planningScope.sourceManifestBytes;
    const localIndexStartedCoverage = coverageFor(
        session,
        'local_index_started',
        [],
        0,
        0,
        0,
        totalScopeShards,
        totalScopeDocuments,
        localIndexBytes,
        hydratedShardBytes,
        filterBytes,
        false,
        false,
        scoped
    );
    emitResults('local_index_started', localIndexStartedCoverage, false);

    const localLightIndexes = await Promise.all(planningScope.localRefs.map(ref => loadLocalLightIndex(ref, signal)));
    planningScope.localRefs.forEach(ref => {
        loadedLocalIndexIds.add(ref.index_id);
        localIndexBytes += ref.light_index.bytes;
    });
    for (const localIndex of localLightIndexes) {
        for (const document of localIndex.documents) {
            docsByIndex.set(document.doc_index, document);
        }
        applyPostings(scores, localIndex.tokens, terms);
    }
    for (const docIndex of applyLocalMetaFallback(docsByIndex, scores, normalizedQuery, filters, now)) {
        telemetry.localMetaFallbackDocIndices.add(docIndex);
    }

    const quick = await hydrateCandidatePhase(
        docsByIndex,
        planningScope.shardPathById,
        scores,
        trimmed,
        terms,
        signal,
        loadedShardPaths,
        fullDocsByIndex,
        Math.min(candidateLimit, 48),
        Math.min(maxShardLoads, QUICK_MAX_SHARD_LOADS),
        matchPhrases,
        filters,
        now
    );
    candidateCount = quick.candidateCount;
    for (const path of loadedShardPaths) {
        const shard = Array.from(planningScope.shardById.values()).find(item => item.path === path);
        hydratedShardBytes += shard?.bytes || 0;
    }
    mergeRankedResults(resultMap, quick.ranked);
    const firstTrustedCoverage = coverageFor(
        session,
        'first_trusted_results',
        LIGHT_SEARCH_FIELDS,
        0,
        loadedShardPaths.size,
        fullDocsByIndex.size,
        totalScopeShards,
        totalScopeDocuments,
        localIndexBytes,
        hydratedShardBytes,
        filterBytes,
        false,
        false,
        scoped
    );
    emitResults('first_trusted_results', firstTrustedCoverage, true);

    const bodyStartedCoverage = coverageFor(
        session,
        'body_index_started',
        LIGHT_SEARCH_FIELDS,
        0,
        loadedShardPaths.size,
        fullDocsByIndex.size,
        totalScopeShards,
        totalScopeDocuments,
        localIndexBytes,
        hydratedShardBytes,
        filterBytes,
        false,
        false,
        scoped
    );
    emitResults('body_index_started', bodyStartedCoverage, false);
    throwIfAborted(signal);
    const bodyIndexes = await Promise.all(planningScope.localRefs.map(ref => loadLocalBodyIndex(ref, signal)));
    planningScope.localRefs.forEach(ref => {
        localIndexBytes += ref.body_index.bytes;
    });
    usedBodyIndex = true;
    for (const bodyIndex of bodyIndexes) {
        applyPostings(scores, bodyIndex.tokens, terms);
    }
    for (const docIndex of applyLocalMetaFallback(docsByIndex, scores, normalizedQuery, filters, now)) {
        telemetry.localMetaFallbackDocIndices.add(docIndex);
    }
    const beforeBodyShardPaths = new Set(loadedShardPaths);
    const body = await hydrateCandidatePhase(
        docsByIndex,
        planningScope.shardPathById,
        scores,
        trimmed,
        terms,
        signal,
        loadedShardPaths,
        fullDocsByIndex,
        Math.min(candidateLimit, 96),
        Math.min(maxShardLoads, BODY_MAX_SHARD_LOADS),
        matchPhrases,
        filters,
        now
    );
    candidateCount = body.candidateCount;
    for (const path of loadedShardPaths) {
        if (beforeBodyShardPaths.has(path)) continue;
        const shard = Array.from(planningScope.shardById.values()).find(item => item.path === path);
        hydratedShardBytes += shard?.bytes || 0;
    }
    mergeRankedResults(resultMap, body.ranked);

    const beforeHydrateShardPaths = new Set(loadedShardPaths);
    const hydrate = await hydrateCandidatePhase(
        docsByIndex,
        planningScope.shardPathById,
        scores,
        trimmed,
        terms,
        signal,
        loadedShardPaths,
        fullDocsByIndex,
        candidateLimit,
        Math.min(maxShardLoads, HYDRATE_MAX_SHARD_LOADS),
        matchPhrases,
        filters,
        now
    );
    candidateCount = hydrate.candidateCount;
    for (const path of loadedShardPaths) {
        if (beforeHydrateShardPaths.has(path)) continue;
        const shard = Array.from(planningScope.shardById.values()).find(item => item.path === path);
        hydratedShardBytes += shard?.bytes || 0;
    }
    mergeRankedResults(resultMap, hydrate.ranked);
    const hydratedCoverage = coverageFor(
        session,
        'top_results_hydrated',
        BODY_SEARCH_FIELDS,
        0,
        loadedShardPaths.size,
        fullDocsByIndex.size,
        totalScopeShards,
        totalScopeDocuments,
        localIndexBytes,
        hydratedShardBytes,
        filterBytes,
        usedBodyIndex,
        false,
        scoped
    );
    emitResults('top_results_hydrated', hydratedCoverage, true);

    const verificationEntries = sourceEntriesById(session);
    const verificationManifests: SitegraphSourceManifest[] = [];
    for (const sourceId of plan.verification_source_ids) {
        const entry = verificationEntries.get(sourceId);
        if (!entry) continue;
        const sourceManifest = await loadSourceManifest(entry, signal);
        verificationManifests.push(sourceManifest);
        if (!planningScope.sourceManifests.some(item => item.source_id === sourceManifest.source_id)) {
            localIndexBytes += entry.artifact_manifest.bytes;
        }
    }
    const inScopeShards = verificationManifests
        .flatMap(sourceManifest => sourceManifest.full_shards)
        .filter(shard => shardMatchesFilters(shard, filters, now));
    totalScopeShards = inScopeShards.length;
    totalScopeDocuments = inScopeShards.reduce((sum, shard) => sum + shard.count, 0);
    const verificationStartedCoverage = coverageFor(
        session,
        'verification_started',
        FULL_SCAN_FIELDS,
        0,
        0,
        0,
        totalScopeShards,
        totalScopeDocuments,
        localIndexBytes,
        hydratedShardBytes,
        filterBytes,
        usedBodyIndex,
        false,
        scoped
    );
    emitResults('verification_started', verificationStartedCoverage, false);

    const shardFiltersBySource = new Map<string, ShardFilterMap>();
    for (const sourceManifest of verificationManifests) {
        const filter = await loadShardFilter(sourceManifest, signal);
        shardFiltersBySource.set(sourceManifest.source_id, filter);
        filterBytes += sourceManifest.artifacts.shard_filter?.bytes || 0;
    }

    let provedNoMatchShards = 0;
    let scannedShards = 0;
    let searchedDocuments = 0;
    const shardBytesByPath = new Map(inScopeShards.map(shard => [shard.path, shard.bytes]));
    for (let shardIndex = 0; shardIndex < inScopeShards.length; shardIndex += SHARD_BATCH_SIZE) {
        throwIfAborted(signal);
        const shardBatch = inScopeShards.slice(shardIndex, shardIndex + SHARD_BATCH_SIZE);
        const scanBatch = shardBatch.filter(shard => {
            const canSkip = shardFilterProvesNoMatch(shard.shard_id, shardFiltersBySource.get(String(shard.source_id || '')) || {}, terms);
            if (canSkip) provedNoMatchShards += 1;
            return !canSkip;
        });
        const shardResults = await Promise.all(scanBatch.map(shard => loadShard(shard.path, signal)));
        const verifyMatches: RankedSitegraphDocument[] = [];
        shardResults.forEach((documents, batchIndex) => {
            const shard = scanBatch[batchIndex];
            if (!shard) return;
            const firstLoad = !loadedShardPaths.has(shard.path);
            loadedShardPaths.add(shard.path);
            if (firstLoad) hydratedShardBytes += shardBytesByPath.get(shard.path) || 0;
            scannedShards += 1;
            for (const document of documents) {
                fullDocsByIndex.set(document.doc_index, document);
                searchedDocuments += 1;
                if (sitegraphDocumentMatchesFilters(document, filters, now) && documentMatchesFullScan(document, matchPhrases)) {
                    telemetry.fullScanMatchDocIndices.add(document.doc_index);
                    const baseScore = scores.get(document.doc_index) ?? 24;
                    verifyMatches.push(rankSitegraphDocument(document, trimmed, terms, baseScore));
                }
            }
        });

        const progressCoverage = coverageFor(
            session,
            'partial_verified',
            FULL_SCAN_FIELDS,
            provedNoMatchShards,
            scannedShards,
            searchedDocuments,
            totalScopeShards,
            totalScopeDocuments,
            localIndexBytes,
            hydratedShardBytes,
            filterBytes,
            usedBodyIndex,
            false,
            scoped
        );
        if (mergeRankedResults(resultMap, verifyMatches) > 0) {
            emitResults('partial_verified', progressCoverage, true);
        } else {
            emitResults('partial_verified', progressCoverage, false);
        }
        await yieldToWorker();
    }

    const completePhase = scoped ? 'scoped_exhaustive_complete' : 'global_exhaustive_complete';
    const completeCoverage = coverageFor(
        session,
        completePhase,
        FULL_SCAN_FIELDS,
        provedNoMatchShards,
        scannedShards,
        searchedDocuments,
        totalScopeShards,
        totalScopeDocuments,
        localIndexBytes,
        hydratedShardBytes,
        filterBytes,
        usedBodyIndex,
        true,
        scoped
    );
    emitResults(completePhase, completeCoverage, true);
};

export const recallSitegraphDocuments = async (
    session: SitegraphRoutedSession,
    query: string,
    signal: AbortSignal,
    limit = 30
): Promise<{ results: RankedSitegraphDocument[]; stats: SitegraphQueryStats }> => {
    const resultEvents: SitegraphSearchEvent[] = [];
    await searchSitegraphProgressively(session, query, signal, event => {
        if (event.results) resultEvents.push(event);
    }, { limit });
    const finalEvent = resultEvents[resultEvents.length - 1];
    if (!finalEvent?.stats) {
        throw new SearchContractError('Progressive routed search completed without a result event');
    }
    return {
        results: finalEvent.results || [],
        stats: finalEvent.stats,
    };
};
