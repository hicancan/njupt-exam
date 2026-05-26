import { useEffect, useState } from 'react';
import { RankedSitegraphDocument, SitegraphQueryStats } from '@/types';

export function useSearchEngine(
    worker: Worker | null,
    searchQuery: string
) {
    const [recalledResults, setRecalledResults] = useState<RankedSitegraphDocument[]>([]);
    const [queryStats, setQueryStats] = useState<SitegraphQueryStats | null>(null);
    const [searching, setSearching] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const trimmed = searchQuery.trim();
    const canSearch = Boolean(worker && trimmed.length >= 2);

    useEffect(() => {
        if (!worker || trimmed.length < 2) {
            setRecalledResults([]);
            setQueryStats(null);
            setSearching(false);
            setError(null);
            return;
        }

        const requestId = Date.now() + Math.floor(Math.random() * 100000);
        let active = true;
        setSearching(true);

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
                setRecalledResults(message.results || []);
                setQueryStats(message.stats || null);
                setError(null);
                setSearching(false);
            } else if (message.type === 'error') {
                setRecalledResults([]);
                setQueryStats(null);
                setError(message.message || '搜索 JWC sitegraph 失败');
                setSearching(false);
            }
        };

        worker.addEventListener('message', handleMessage);
        worker.postMessage({ type: 'query', requestId, query: trimmed, limit: 30 });

        return () => {
            active = false;
            worker.removeEventListener('message', handleMessage);
            worker.postMessage({ type: 'cancel', requestId });
        };
    }, [worker, trimmed]);

    return {
        recalledResults: canSearch ? recalledResults : [],
        queryStats: canSearch ? queryStats : null,
        searching: canSearch ? searching : false,
        searchError: canSearch ? error : null
    };
}
