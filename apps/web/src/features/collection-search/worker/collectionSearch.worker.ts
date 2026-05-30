import { APP_CONFIG } from '@/app/config/constants';
import {
    SitegraphRoutedSession,
    SitegraphSearchFilters,
    SitegraphSearchCoverage,
    SitegraphSearchManifest,
    SitegraphSortMode,
} from '@/shared/lib/contracts';
import { fetchJson } from '@/shared/lib/fetch';
import {
    parseSitegraphGlobalQueryDirectory,
    parseSitegraphManifest,
    parseSitegraphSourceRegistry,
    searchSitegraphProgressively,
} from '@njupt-search/search-core';

type InitMessage = { type: 'init'; requestId: number };
type QueryMessage = {
    type: 'query';
    requestId: number;
    query: string;
    limit?: number;
    sortMode?: SitegraphSortMode;
    filters?: SitegraphSearchFilters;
};
type CancelMessage = { type: 'cancel'; requestId: number };
type IncomingMessage = InitMessage | QueryMessage | CancelMessage;

let manifest: SitegraphSearchManifest | null = null;
let session: SitegraphRoutedSession | null = null;
let activeController: AbortController | null = null;
let activeRequestId: number | null = null;
let lastCoverage: SitegraphSearchCoverage | null = null;

const post = (payload: Record<string, unknown>) => {
    self.postMessage(payload);
};

const publicPath = (path: string): string => {
    if (/^https?:\/\//.test(path) || path.startsWith('/')) return path;
    return `/${path}`;
};

const init = async (requestId: number) => {
    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;
    activeRequestId = requestId;
    const manifestPath = publicPath(APP_CONFIG.DATA_URLS.SEARCH_MANIFEST);
    const manifestPayload = await fetchJson(manifestPath, controller.signal, 'manifest');
    manifest = parseSitegraphManifest(manifestPayload, manifestPath);
    const artifacts = manifest.artifacts;
    const [sourceRegistryPayload, queryDirectoryPayload, aliasesPayload] = await Promise.all([
        fetchJson(publicPath(artifacts.source_registry.path), controller.signal, 'index'),
        fetchJson(publicPath(artifacts.global_query_directory.path), controller.signal, 'index'),
        fetchJson(publicPath(artifacts.query_aliases.path), controller.signal, 'index'),
    ]);
    const sourceRegistry = parseSitegraphSourceRegistry(sourceRegistryPayload, artifacts.source_registry.path);
    session = {
        manifest,
        sourceRegistry,
        globalQueryDirectory: parseSitegraphGlobalQueryDirectory(queryDirectoryPayload, artifacts.global_query_directory.path),
        queryAliases: aliasesPayload as Record<string, unknown>,
    };
    post({
        type: 'ready',
        requestId,
        manifest,
        filterOptions: sourceRegistry.filter_options,
        firstScreenBytes: artifacts.source_registry.bytes + artifacts.global_query_directory.bytes + artifacts.query_aliases.bytes,
    });
};

const query = async (
    requestId: number,
    queryText: string,
    limit = 30,
    sortMode: SitegraphSortMode = 'relevance',
    filters: SitegraphSearchFilters = {}
) => {
    if (!session) {
        throw new Error('Search worker is not initialized');
    }
    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;
    activeRequestId = requestId;
    await searchSitegraphProgressively(session, queryText, controller.signal, event => {
        lastCoverage = event.coverage;
        post({ ...event, requestId });
    }, { limit, sortMode, filters });
};

self.onmessage = (event: MessageEvent<IncomingMessage>) => {
    const message = event.data;
    if (message.type === 'cancel') {
        if (message.requestId === activeRequestId) {
            activeController?.abort();
            activeController = null;
            activeRequestId = null;
        }
        post({
            type: 'cancelled',
            requestId: message.requestId,
            coverage: lastCoverage ? { ...lastCoverage, phase: 'cancelled', coverage_state: 'cancelled', exhaustive_complete: false } : null,
        });
        return;
    }

    const run = message.type === 'init'
        ? init(message.requestId)
        : query(message.requestId, message.query, message.limit, message.sortMode, message.filters);

    run.catch(error => {
        if (error instanceof DOMException && error.name === 'AbortError') return;
        post({
            type: 'error',
            requestId: message.requestId,
            message: error instanceof Error ? error.message : String(error),
            coverage: lastCoverage ? { ...lastCoverage, phase: 'error', coverage_state: 'error', exhaustive_complete: false } : null,
        });
    });
};
