import { useEffect, useState } from 'react';
import { APP_CONFIG } from '@/constants';
import { SearchDocument, SearchManifest } from '@/types';
import { parseSearchDocuments, parseSearchManifest } from '@/utils/searchIndex';
import { fetchJson } from '@/utils/fetch';

interface UseSearchIndexResult {
    documents: SearchDocument[];
    manifest: SearchManifest | null;
    queryAliases: Record<string, unknown>;
    ontology: Record<string, unknown> | null;
    optionalUnavailable: string[];
    loading: boolean;
    error: string | null;
}

const sitegraphShardPaths = (manifest: SearchManifest): string[] => {
    const sitegraph = (manifest as SearchManifest & { sitegraph?: { shards?: unknown[] } }).sitegraph;
    const shards = Array.isArray(sitegraph?.shards) ? sitegraph.shards : [];
    return shards
        .map(shard => {
            if (!shard || typeof shard !== 'object') return '';
            return String((shard as { path?: unknown }).path || '').trim();
        })
        .filter(Boolean);
};

const mergeDocumentsById = (baseDocuments: SearchDocument[], fullDocuments: SearchDocument[]): SearchDocument[] => {
    const merged = new Map<string, SearchDocument>();
    for (const document of baseDocuments) {
        merged.set(document.id, document);
    }
    for (const document of fullDocuments) {
        merged.set(document.id, document);
    }
    return Array.from(merged.values());
};

export function useSearchIndex(): UseSearchIndexResult {
    const [documents, setDocuments] = useState<SearchDocument[]>([]);
    const [manifest, setManifest] = useState<SearchManifest | null>(null);
    const [queryAliases, setQueryAliases] = useState<Record<string, unknown>>({});
    const [ontology, setOntology] = useState<Record<string, unknown> | null>(null);
    const [optionalUnavailable, setOptionalUnavailable] = useState<string[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const controller = new AbortController();

        const load = async () => {
            const [documentPayload, manifestPayload] = await Promise.all([
                fetchJson(APP_CONFIG.DATA_URLS.SEARCH_INDEX, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.SEARCH_MANIFEST, controller.signal)
            ]);

            const parsedDocuments = parseSearchDocuments(documentPayload, APP_CONFIG.DATA_URLS.SEARCH_INDEX);
            const parsedManifest = parseSearchManifest(manifestPayload, APP_CONFIG.DATA_URLS.SEARCH_MANIFEST);

            const optionalResults = await Promise.allSettled([
                fetchJson(APP_CONFIG.DATA_URLS.QUERY_ALIASES, controller.signal),
                fetchJson(APP_CONFIG.DATA_URLS.ONTOLOGY, controller.signal)
            ]);
            const unavailable: string[] = [];
            const [aliasesResult, ontologyResult] = optionalResults;

            if (aliasesResult?.status === 'fulfilled') {
                setQueryAliases(aliasesResult.value as Record<string, unknown>);
            } else {
                setQueryAliases({});
                unavailable.push('query_aliases');
            }

            if (ontologyResult?.status === 'fulfilled') {
                setOntology(ontologyResult.value as Record<string, unknown>);
            } else {
                setOntology(null);
                unavailable.push('ontology');
            }

            setOptionalUnavailable(unavailable);
            if (unavailable.length > 0) {
                console.warn(`Optional search features unavailable: ${unavailable.join(', ')}`);
            }

            setDocuments(parsedDocuments);
            setManifest(parsedManifest);
            setError(null);
            const shardPaths = sitegraphShardPaths(parsedManifest);
            if (shardPaths.length > 0) {
                void Promise.allSettled(
                    shardPaths.map(async path => {
                        const payload = await fetchJson(path, controller.signal);
                        return parseSearchDocuments(payload, path);
                    })
                ).then(results => {
                    if (controller.signal.aborted) return;
                    const shardUnavailable: string[] = [];
                    const fullDocuments: SearchDocument[] = [];
                    results.forEach((result, index) => {
                        if (result.status === 'fulfilled') {
                            fullDocuments.push(...result.value);
                        } else {
                            shardUnavailable.push(`sitegraph_shard:${shardPaths[index]}`);
                            console.warn(`Optional sitegraph full-text shard unavailable: ${shardPaths[index]}`, result.reason);
                        }
                    });
                    if (fullDocuments.length > 0) {
                        setDocuments(current => mergeDocumentsById(current, fullDocuments));
                    }
                    if (shardUnavailable.length > 0) {
                        setOptionalUnavailable(current => Array.from(new Set([...current, ...shardUnavailable])));
                    }
                });
            }
        };

        load()
            .catch(err => {
                if (err instanceof DOMException && err.name === 'AbortError') {
                    return;
                }
                console.error(err);
                setDocuments([]);
                setManifest(null);
                setQueryAliases({});
                setOntology(null);
                setOptionalUnavailable([]);
                setError(err instanceof Error ? err.message : '无法加载校园搜索索引');
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            });

        return () => controller.abort();
    }, []);

    return { documents, manifest, queryAliases, ontology, optionalUnavailable, loading, error };
}
