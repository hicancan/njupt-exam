import { useEffect, useState } from 'react';
import { RankedSitegraphDocument, SitegraphQueryStats } from '@/types';

type SearchState = {
    query: string;
    results: RankedSitegraphDocument[];
    stats: SitegraphQueryStats | null;
    error: string | null;
    settled: boolean;
};

export function useSearchEngine(
    worker: Worker | null,
    searchQuery: string
) {
    const [searchState, setSearchState] = useState<SearchState>({
        query: '',
        results: [],
        stats: null,
        error: null,
        settled: true
    });
    const trimmed = searchQuery.trim();
    const canSearch = Boolean(worker && trimmed.length >= 2);

    useEffect(() => {
        if (!worker || trimmed.length < 2) {
            return;
        }

        const requestId = Date.now() + Math.floor(Math.random() * 100000);
        const requestQuery = trimmed;
        let active = true;

        const handleMessage = (event: MessageEvent) => {
            const message = event.data as {
                type?: string;
                requestId?: number;
                results?: RankedSitegraphDocument[];
                stats?: SitegraphQueryStats;
                message?: string;
            };
            if (!active || message.requestId !== requestId) return;
            if (message.type === 'results') {
                setSearchState({
                    query: requestQuery,
                    results: message.results || [],
                    stats: message.stats || null,
                    error: null,
                    settled: true
                });
            } else if (message.type === 'error') {
                setSearchState({
                    query: requestQuery,
                    results: [],
                    stats: null,
                    error: message.message || '搜索 JWC sitegraph 失败',
                    settled: true
                });
            }
        };

        worker.addEventListener('message', handleMessage);
        worker.postMessage({ type: 'query', requestId, query: requestQuery, limit: 30 });

        return () => {
            active = false;
            worker.removeEventListener('message', handleMessage);
            worker.postMessage({ type: 'cancel', requestId });
        };
    }, [worker, trimmed]);

    const isCurrentResult = canSearch && searchState.query === trimmed;

    return {
        recalledResults: isCurrentResult ? searchState.results : [],
        queryStats: isCurrentResult ? searchState.stats : null,
        searching: canSearch ? !(isCurrentResult && searchState.settled) : false,
        searchError: isCurrentResult ? searchState.error : null
    };
}
